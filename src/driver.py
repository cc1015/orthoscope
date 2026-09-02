import os
import re
from pathlib import Path

from client.uniprot_client import UniProtClient
from client.alphafold_client import AlphaFoldClient
from client.string_client import StringClient
from client.ncbi_client import NCBIClient
from client.therasabdab_client import TherasabdabClient
from errors import InvalidInput, NotFound, OrthoScopeError, PipelineError, stage
from models.protein_model.protein import Protein
from models.organism import Organism
from ortholog_finders.ncbi_ortholog_finder import NCBIOrthologFinder
from ortholog_finders.uniref_ortholog_finder import UniRefOrthologFinder
from services.protein_store import ProteinFileStore


PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Root for pipeline artefacts (the output_<protein>/ trees). Defaults to the
# repository root so local runs behave as before; containers set
# ORTHOSCOPE_DATA_DIR to a mounted volume so results survive a redeploy and the
# static file mount does not expose the source tree.
DATA_ROOT = Path(os.environ.get("ORTHOSCOPE_DATA_DIR") or PROJECT_ROOT).resolve()

ACCESSION_RE = re.compile(
    r"^([OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2})$"
)

# The protein name becomes a directory name (output_<protein_name>/ and the
# per-organism subdirectories), so it must not contain path separators or
# relative segments. Requiring an alphanumeric first character rules out
# ".." and leading dots.
PROTEIN_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,31}$")


def validate_protein_name(protein_name: str) -> str:
    candidate = (protein_name or "").strip()
    if not candidate:
        raise InvalidInput("A protein name is required.", stage="request")
    if not PROTEIN_NAME_RE.match(candidate):
        raise InvalidInput(
            f"{candidate!r} is not a valid protein name.",
            stage="request",
            hint="Use up to 32 letters, digits, dots, hyphens or underscores, "
                 "starting with a letter or digit — e.g. EGFR.",
        )
    return candidate


def validate_accession(protein_id: str) -> str:
    candidate = (protein_id or "").strip().upper()
    if not candidate:
        raise InvalidInput("A UniProt accession is required.", stage="request")
    if not ACCESSION_RE.match(candidate):
        raise InvalidInput(
            f"{candidate!r} is not a valid UniProt accession.",
            stage="request",
            hint="Accessions look like P00533 or A0A0B4J2F0.",
        )
    return candidate


class Driver:
    def __init__(self, protein_id, custom_organisms=None):
        self.uniprot_client = UniProtClient()
        self.af_client = AlphaFoldClient()
        self.string_client = StringClient()
        self.ncbi_client = NCBIClient()
        self.therasabdab_client = TherasabdabClient()
        self.ncbi_ortholog_finder = NCBIOrthologFinder()
        self.uniref_ortholog_finder = UniRefOrthologFinder()
        self.store: ProteinFileStore | None = None
        self.warnings: list[dict] = []
        self._set_protein_information(protein_id, custom_organisms)

    def warn(self, message: str, *, stage: str, organism: str | None = None) -> None:
        self.warnings.append({"stage": stage, "message": message, "organism": organism})

    def _set_protein_information(self, protein_id, custom_organisms=None):
        self.protein_information = {o: None for o in Organism}
        if custom_organisms:
            for custom_org in custom_organisms:
                self.protein_information[custom_org] = None

        with stage("uniprot"):
            human_data = self.uniprot_client.get_entry(protein_id)

        if not human_data or not human_data.get('primaryAccession'):
            raise NotFound(
                f"UniProt returned no usable entry for {protein_id}.",
                stage="uniprot",
                hint="Check the accession at https://www.uniprot.org.",
            )

        if human_data.get('entryType') == 'Inactive':
            reason = (human_data.get('inactiveReason') or {})
            detail = reason.get('deletedReason') or reason.get('inactiveReasonType') or 'inactive'
            merged = reason.get('mergeDemergeTo') or []
            hint = (
                f"It was replaced by {', '.join(merged)}."
                if merged
                else "Find the current accession at https://www.uniprot.org."
            )
            raise NotFound(
                f"UniProt accession {protein_id} is no longer active ({detail}).",
                stage="uniprot",
                hint=hint,
            )

        if not human_data.get('sequence', {}).get('value'):
            raise NotFound(
                f"UniProt entry {protein_id} has no sequence.",
                stage="uniprot",
                hint="The pipeline needs a sequence to align against.",
            )

        self.protein_information[Organism.HUMAN] = human_data

    def _gene_id(self) -> str:
        human = self.protein_information[Organism.HUMAN]
        refs = human.get('uniProtKBCrossReferences') or []
        gene_id = next(
            (entry["id"] for entry in refs if entry.get("database") == "GeneID"),
            None,
        )
        if gene_id is None:
            raise PipelineError(
                f"UniProt entry {human.get('primaryAccession')} has no NCBI "
                "GeneID cross-reference, so orthologs cannot be looked up.",
                stage="orthologs",
                hint="This is common for unreviewed entries. Try the reviewed "
                     "(Swiss-Prot) accession for this protein.",
            )
        return gene_id

    def drive(self, protein_name, protein_id, selected_organisms=None):
        self.store = ProteinFileStore(DATA_ROOT, protein_name)

        gene_id = self._gene_id()
        excluded = Organism.HUMAN

        if selected_organisms is None:
            organisms_to_process = [o for o in Organism if o != excluded]
        else:
            organisms_to_process = selected_organisms

        organism_list = [o.tax_id for o in organisms_to_process]

        try:
            with stage("orthologs"):
                ncbi_ids = self.ncbi_ortholog_finder.get_orthologs(gene_id, organism_list)
        except OrthoScopeError as e:
            self.warn(
                f"NCBI ortholog lookup failed ({e.message}); falling back to UniRef.",
                stage="orthologs",
            )
            ncbi_ids = {}

        tax_id_to_organism = {str(org.tax_id): org for org in organisms_to_process}

        for organism_tax_id, ref in ncbi_ids.items():
            o = tax_id_to_organism.get(organism_tax_id)
            if not (o and (selected_organisms is None or o in selected_organisms)):
                continue
            label, ident = ref
            try:
                if 'uniprot' in label:
                    self.protein_information[o] = self.uniprot_client.get_entry(ident)
                elif 'ncbi' in label:
                    self.protein_information[o] = self.ncbi_client.get_entry(ident)
            except OrthoScopeError as e:
                self.warn(e.message, stage="orthologs", organism=o.name)

        organisms_to_check = organisms_to_process if selected_organisms is not None else [o for o in Organism if o != excluded]

        for organism in organisms_to_check:
            if organism == Organism.HUMAN or self.protein_information.get(organism):
                continue
            try:
                with stage("orthologs"):
                    data = self.uniref_ortholog_finder.get_ortholog_ids(
                        protein_id,
                        organism,
                        selection_callback=getattr(self, '_ortholog_selection_callback', None),
                    )
                if data:
                    self.protein_information[organism] = data
            except OrthoScopeError as e:
                self.warn(e.message, stage="orthologs", organism=organism.name)

        proteins = self._create_proteins(protein_name, protein_id, selected_organisms)

        for organism in organisms_to_check:
            if organism != Organism.HUMAN and organism not in proteins:
                self.warn(
                    "No ortholog with a predicted structure was found.",
                    stage="orthologs",
                    organism=organism.name,
                )

        with stage("write"):
            for protein in proteins.values():
                self.store.save(protein)
        return proteins

    def _create_proteins(self, protein_name, protein_id, selected_organisms=None):
        proteins = {}
        organisms_to_create = [Organism.HUMAN]

        if selected_organisms is not None:
            organisms_to_create.extend(selected_organisms)
        else:
            organisms_to_create.extend([o for o in Organism if o != Organism.HUMAN])

        for organism in organisms_to_create:
            results = self.protein_information.get(organism)
            if not (organism and results):
                continue

            is_human = organism == Organism.HUMAN
            try:
                if 'ncbi' in results:
                    proteins[organism] = Protein.from_ncbi_result(
                        protein_name=protein_name,
                        protein_id=protein_id,
                        organism=organism,
                        fasta=results[1],
                    )
                    continue

                uniprot_results = self._enrich_uniprot_features(results)
                accession = uniprot_results['primaryAccession']

                af_pdb = self._get_af_pdb(accession)
                if not af_pdb:
                    if is_human:
                        raise NotFound(
                            f"AlphaFold has no predicted structure for {accession}.",
                            stage="structure",
                            hint="The pipeline needs a predicted structure for "
                                 "the human protein.",
                        )
                    continue

                proteins[organism] = Protein.from_uniprot_result(
                    protein_name=protein_name,
                    uniprot_results=uniprot_results,
                    af_results=af_pdb,
                    organism=organism,
                    fasta=self._get_fasta_content(accession),
                )
            except OrthoScopeError:
                if is_human:
                    raise
                self.warn(
                    "Could not assemble this ortholog.",
                    stage="orthologs",
                    organism=organism.name,
                )
            except Exception as e:
                if is_human:
                    raise PipelineError(
                        f"Failed to assemble the human protein: {type(e).__name__}: {e}",
                        stage="assemble",
                    ) from e
                self.warn(
                    f"Could not assemble this ortholog ({type(e).__name__}).",
                    stage="orthologs",
                    organism=organism.name,
                )
        return proteins

    def _enrich_uniprot_features(self, uniprot_results):
        """Fetch annotation features and graft them onto the UniProt entry so the factory has everything it needs."""
        if 'features' not in uniprot_results or not uniprot_results['features']:
            annotations = self.uniprot_client.get_annotations(protein_id=uniprot_results['primaryAccession'])
            uniprot_results = {**uniprot_results, 'features': annotations.get('features') or []}
        return uniprot_results

    def _get_fasta_content(self, protein_id) -> str:
        return self.uniprot_client.get_fasta(protein_id=protein_id)

    def _get_af_pdb(self, protein_id) -> dict:
        return self.af_client.get_af_pdb(protein_id=protein_id)

    def _get_string_db_interactions(self, protein_name, string_id):
        return self.string_client.fetch(protein_name, string_id=string_id)

    def _get_therasabdab_info(self, protein_name):
        return self.therasabdab_client.fetch(protein_name)

    def set_ortholog_selection_callback(self, callback):
        self._ortholog_selection_callback = callback
