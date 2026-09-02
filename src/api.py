"""
OrthoScope HTTP API — synchronous scaffold.

Wraps the existing Driver pipeline behind a single POST /jobs endpoint so a
Next.js (or any) frontend can drive analyses over HTTP. Runs synchronously
for now; the next step is to push pipeline execution into an RQ worker so
the endpoint returns immediately and the frontend streams progress.

Install:
    pip install fastapi uvicorn[standard]

Run (from this directory):
    uvicorn api:app --reload --host 0.0.0.0 --port 8000
"""
import logging
import os
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from driver import DATA_ROOT, Driver, validate_accession, validate_protein_name
from errors import InvalidInput, OrthoScopeError
from models.organism import Organism, CustomOrganism
from services.sequence_aligner import SequenceAligner
from services.structure_aligner import StructureAligner

log = logging.getLogger("orthoscope")

app = FastAPI(title="OrthoScope API", version="0.2.0")

# Comma-separated list of allowed frontend origins; defaults to local dev.
CORS_ORIGINS = [
    o.strip()
    for o in os.environ.get("ORTHOSCOPE_CORS_ORIGINS", "http://localhost:3000").split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

DATA_ROOT.mkdir(parents=True, exist_ok=True)
app.mount("/files", StaticFiles(directory=str(DATA_ROOT)), name="files")


@app.exception_handler(OrthoScopeError)
async def orthoscope_error_handler(request: Request, exc: OrthoScopeError):
    log.warning("pipeline error [%s] %s", exc.stage, exc.message)
    return JSONResponse(status_code=exc.status, content={"error": exc.as_dict()})


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    log.exception("unhandled error during %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "kind": "internal",
                "stage": None,
                "message": f"Unexpected {type(exc).__name__} in the pipeline.",
                "hint": "This is a bug. The server log has the traceback.",
            }
        },
    )


class CustomOrganismIn(BaseModel):
    scientific_name: str
    tax_id: int


class JobRequest(BaseModel):
    protein_id: str = Field(..., description="UniProt accession, e.g. P00533")
    protein_name: str = Field(..., description="Gene symbol / display name")
    organism_names: Optional[list[str]] = Field(
        default=None,
        description="Predefined Organism enum names. Omit/null = all non-human predefined.",
    )
    custom_organisms: list[CustomOrganismIn] = Field(default_factory=list)


class FeatureOut(BaseModel):
    annotation: str
    start: int
    end: int
    note: str


class WarningOut(BaseModel):
    stage: str
    message: str
    organism: Optional[str] = None


class ProteinOut(BaseModel):
    id: str
    organism: str
    scientific_name: str
    name: str
    seq: str
    features: list[FeatureOut]
    fasta_url: Optional[str] = None
    pdb_url: Optional[str] = None
    gff_url: Optional[str] = None
    rmsd: Optional[float] = None
    structure_alignment_image_url: Optional[str] = None
    aligned_pdb_url: Optional[str] = None


class HumanProteinOut(ProteinOut):
    passport_table_data: dict
    genbank_url: Optional[str] = None
    alignment_fasta_url: Optional[str] = None
    annotated_structure_image_url: Optional[str] = None
    string_image_url: Optional[str] = None
    reference_pdb_url: Optional[str] = None


class JobResponse(BaseModel):
    job_id: str
    status: str
    human: HumanProteinOut
    orthologs: list[ProteinOut]
    warnings: list[WarningOut] = Field(default_factory=list)


def _resolve_organisms(names: Optional[list[str]]):
    if names is None:
        return [o for o in Organism if o != Organism.HUMAN]
    out = []
    for n in names:
        try:
            out.append(Organism[n])
        except KeyError:
            valid = ", ".join(o.name for o in Organism if o != Organism.HUMAN)
            raise InvalidInput(
                f"Unknown organism {n!r}.",
                stage="request",
                hint=f"Valid names are: {valid}.",
            )
    return out


def _resolve_custom(entries: list[CustomOrganismIn]):
    out = []
    for c in entries:
        if not c.scientific_name.strip():
            raise InvalidInput(
                "Custom organisms need a scientific name.", stage="request"
            )
        if c.tax_id <= 0:
            raise InvalidInput(
                f"{c.tax_id} is not a valid NCBI taxonomic ID.",
                stage="request",
                hint="Look the taxon up at https://www.ncbi.nlm.nih.gov/taxonomy.",
            )
        out.append(CustomOrganism(c.scientific_name.strip(), c.tax_id))
    return out


def _file_url(path: Optional[Path]) -> Optional[str]:
    if not path:
        return None
    try:
        if not Path(path).exists():
            return None
        return f"/files/{Path(path).relative_to(DATA_ROOT)}"
    except (OSError, ValueError):
        return None


def _features_out(features) -> list[FeatureOut]:
    return [
        FeatureOut(annotation=f.annotation.name, start=f.start, end=f.end, note=f.note)
        for f in features
    ]


def _serialize_ortholog(p, store, alignment_image: Optional[Path],
                        aligned_pdb: Optional[Path] = None) -> ProteinOut:
    return ProteinOut(
        id=p.id,
        organism=p.organism.name,
        scientific_name=p.organism.value[0],
        name=p.name,
        seq=p.seq,
        features=_features_out(p.features),
        fasta_url=_file_url(store.fasta_path(p)),
        pdb_url=_file_url(store.pdb_path(p)),
        gff_url=_file_url(store.gff_path(p)),
        rmsd=p.rmsd,
        structure_alignment_image_url=_file_url(alignment_image),
        aligned_pdb_url=_file_url(aligned_pdb),
    )


def _serialize_human(p, store, annotated_structure: Optional[Path],
                     string_image: Optional[Path],
                     reference_pdb: Optional[Path] = None) -> HumanProteinOut:
    return HumanProteinOut(
        id=p.id,
        organism=p.organism.name,
        scientific_name=p.organism.value[0],
        name=p.name,
        seq=p.seq,
        features=_features_out(p.features),
        fasta_url=_file_url(store.fasta_path(p)),
        pdb_url=_file_url(store.pdb_path(p)),
        gff_url=_file_url(store.gff_path(p)),
        passport_table_data=p.passport_table_data,
        genbank_url=_file_url(store.annotated_genbank_path()),
        alignment_fasta_url=_file_url(store.alignment_fasta_path()),
        annotated_structure_image_url=_file_url(annotated_structure),
        string_image_url=_file_url(string_image),
        reference_pdb_url=_file_url(reference_pdb),
    )


def _run_optional(warnings, stage_name, fn, default):
    try:
        return fn()
    except OrthoScopeError as e:
        warnings.append({
            "stage": e.stage or stage_name,
            "message": e.message,
            "organism": None,
        })
    except Exception as e:
        log.exception("optional stage %s failed", stage_name)
        warnings.append({
            "stage": stage_name,
            "message": f"{type(e).__name__}: {e}",
            "organism": None,
        })
    return default


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/jobs", response_model=JobResponse)
def create_job(req: JobRequest) -> JobResponse:
    protein_id = validate_accession(req.protein_id)
    protein_name = validate_protein_name(req.protein_name)

    predefined = _resolve_organisms(req.organism_names)
    custom = _resolve_custom(req.custom_organisms)
    selected_organisms = predefined + custom

    if not selected_organisms:
        raise InvalidInput(
            "Select at least one organism to compare against.", stage="request"
        )

    driver = Driver(protein_id=protein_id, custom_organisms=custom)
    proteins = driver.drive(
        protein_name=protein_name,
        protein_id=protein_id,
        selected_organisms=selected_organisms,
    )

    human = proteins.get(Organism.HUMAN)
    if not human:
        raise OrthoScopeError(
            "The pipeline produced no human protein.", stage="assemble"
        )

    orthologs = [p for org, p in proteins.items() if org != Organism.HUMAN]
    store = driver.store
    warnings = list(driver.warnings)

    def optional(stage_name, fn, default=None):
        return _run_optional(warnings, stage_name, fn, default)

    optional("alignment", lambda: SequenceAligner(store).annotate_align(human, orthologs))

    structure_aligner = StructureAligner(store)
    annotated_img = optional(
        "structure", lambda: structure_aligner.annotate_3d_structure(human)
    )
    rmsd_map = optional(
        "structure", lambda: structure_aligner.align(human, orthologs), {}
    )
    warnings.extend(structure_aligner.warnings)

    string_img = None
    if human.string_id:
        string_img = optional(
            "network",
            lambda: driver._get_string_db_interactions(protein_name, human.string_id),
        )
    else:
        warnings.append({
            "stage": "network",
            "message": "This entry has no STRING cross-reference, so no "
                       "interaction network was retrieved.",
            "organism": None,
        })

    alignment_images = {o: Path(v["image"]) for o, v in rmsd_map.items() if v.get("image")}
    aligned_pdbs = {o: Path(v["aligned_pdb"]) for o, v in rmsd_map.items() if v.get("aligned_pdb")}
    reference_pdb = structure_aligner.reference_pdb

    return JobResponse(
        job_id=str(uuid4()),
        status="completed_with_warnings" if warnings else "completed",
        human=_serialize_human(
            human, store,
            Path(annotated_img) if annotated_img else None,
            Path(string_img) if string_img else None,
            Path(reference_pdb) if reference_pdb else None,
        ),
        orthologs=[
            _serialize_ortholog(
                o, store, alignment_images.get(o), aligned_pdbs.get(o)
            )
            for o in orthologs
        ],
        warnings=[WarningOut(**w) for w in warnings],
    )
