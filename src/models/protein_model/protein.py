from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional, Union

from models.organism import Organism, CustomOrganism
from models.annotation import Annotation


@dataclass
class ProteinFeature:
    """A single annotation feature parsed from UniProt: an Annotation type with location and note."""
    annotation: Annotation
    start: int
    end: int
    note: str = ""


@dataclass(eq=False)
class Protein:
    """
    Pure data container for a protein (human or ortholog). Persisting and
    aligning are handled by services (ProteinFileStore, StructureAligner,
    SequenceAligner) — this class has no I/O or PyMOL dependencies.

    Features are stored as a list of ProteinFeature; the `annotations`
    property derives the structural-coloring index on demand.
    """

    id: str
    organism: Union[Organism, CustomOrganism]
    name: str
    seq: str = ""
    fasta: str = ""
    features: list = field(default_factory=list)
    pred_pdb_filename: Optional[str] = None
    pred_pdb_content: Optional[bytes] = None
    pred_pdb_id: Optional[str] = None
    string_id: Optional[list] = None
    rmsd: Optional[float] = None
    similarity: Optional[float] = None
    passport_table_data: dict = field(default_factory=dict)

    @property
    def from_ncbi(self) -> bool:
        return self.pred_pdb_filename is None

    @property
    def annotations(self) -> dict:
        """
        Annotation enum -> list of (start, end) int tuples, for structural coloring.

        Drops SIGNAL and CHAIN entries when ECD is present — those overlap
        visually with the ECD and would muddle the rendered structure.
        """
        out = defaultdict(list)
        for f in self.features:
            out[f.annotation].append((f.start, f.end))
        if Annotation.ECD in out:
            out.pop(Annotation.SIGNAL, None)
            out.pop(Annotation.CHAIN, None)
        return dict(out)

    @classmethod
    def from_uniprot_result(cls, protein_name, uniprot_results, af_results, organism, fasta):
        features = _parse_uniprot_features(uniprot_results.get('features') or [])

        pdb_filename = af_results['file_name'] if af_results else None
        pdb_content = af_results['content'] if af_results else None
        pdb_id = pdb_filename[:-4] if pdb_filename else None

        string_id = [entry["id"] for entry in uniprot_results.get('uniProtKBCrossReferences') or []
                     if entry.get("database") == "STRING"]

        return cls(
            id=uniprot_results['primaryAccession'],
            organism=organism,
            name=protein_name,
            seq=uniprot_results['sequence']['value'],
            fasta=fasta,
            features=features,
            pred_pdb_filename=pdb_filename,
            pred_pdb_content=pdb_content,
            pred_pdb_id=pdb_id,
            string_id=string_id,
            passport_table_data=_build_passport_table(protein_name, uniprot_results),
        )

    @classmethod
    def from_ncbi_result(cls, protein_name, protein_id, organism, fasta):
        seq = fasta.split('\n', 1)[1].strip() if '\n' in fasta else ""
        return cls(
            id=protein_id,
            organism=organism,
            name=protein_name,
            seq=seq,
            fasta=fasta,
        )


def features_to_gff(protein: Protein) -> str:
    """Render a protein's features back to GFF text for persistence."""
    lines = ["##gff-version 3"]
    for f in protein.features:
        lines.append(
            f"{protein.id}\tUniProtKB\t{f.annotation.name}\t{f.start}\t{f.end}\t.\t.\t.\t{f.note}"
        )
    return "\n".join(lines) + "\n"


def _parse_uniprot_features(uniprot_features: list) -> list:
    """Map UniProt feature JSON entries to the Annotation enum, dropping anything we don't track."""
    result = []
    for f in uniprot_features:
        feature_type = f.get('type')
        description = f.get('description', '') or ''
        for annotation in Annotation:
            if feature_type == annotation.feature and (annotation.attr is None or annotation.attr in description):
                location = f.get('location') or {}
                start_v = (location.get('start') or {}).get('value')
                end_v = (location.get('end') or {}).get('value')
                if start_v is None or end_v is None:
                    break
                start = int(start_v)
                end = int(end_v)
                result.append(ProteinFeature(
                    annotation=annotation,
                    start=start,
                    end=end,
                    note=description,
                ))
                break
    return result


def _recommended_name(uniprot_results: dict) -> str:
    """Best available display name: recommendedName, else submittedName."""
    desc = uniprot_results.get('proteinDescription') or {}

    recommended = desc.get('recommendedName') or {}
    value = (recommended.get('fullName') or {}).get('value')
    if value:
        return value

    for submitted in desc.get('submittedNames') or []:
        value = (submitted.get('fullName') or {}).get('value')
        if value:
            return value

    return uniprot_results.get('primaryAccession', '')


def _build_passport_table(protein_name: str, uniprot_results: dict) -> dict:
    rec_name = _recommended_name(uniprot_results)
    aliases = [item["fullName"]["value"]
               for item in (uniprot_results.get("proteinDescription") or {}).get("alternativeNames", [])] or ""
    sequence = uniprot_results.get('sequence') or {}
    length = sequence.get('length', 0)
    mass = round(sequence.get('molWeight', 0) * 10**-3, 1)
    exp_pdbs = [entry["id"] for entry in uniprot_results.get('uniProtKBCrossReferences') or []
                if entry.get("database") == "PDB"]

    comments = uniprot_results.get('comments') or []

    subcellular_location = next((d for d in comments if d.get('commentType') == 'SUBCELLULAR LOCATION'), None)
    if subcellular_location:
        locations = subcellular_location.get('subcellularLocations', [])
        if locations and locations[0].get('topology'):
            subcellular_location = locations[0].get('topology').get('value')
        else:
            subcellular_location = ""

    function = next((d for d in comments if d.get('commentType') == 'FUNCTION'), None)
    if function:
        texts = function.get('texts', [])
        function = texts[0].get('value') if texts else None

    tissue_specificity = next((d for d in comments if d.get('commentType') == 'TISSUE SPECIFICITY'), None)
    if tissue_specificity:
        texts = tissue_specificity.get('texts', [])
        tissue_specificity = texts[0].get('value') if texts else None

    return {
        "rec_name": rec_name,
        "aliases": aliases,
        "gene_id": protein_name,
        "length": length,
        "mass": mass,
        "target_type": subcellular_location,
        "exp_pdbs": exp_pdbs,
        "known_activity": function,
        "exp_pattern": tissue_specificity,
    }
