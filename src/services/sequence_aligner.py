import shutil
import subprocess

from Bio import SeqIO
from Bio.SeqFeature import SeqFeature, FeatureLocation

from errors import MissingDependency, PipelineError
from services.protein_store import ProteinFileStore

MAFFT_TIMEOUT = 300


class SequenceAligner:
    """
    Builds an annotated GenBank record for the human protein and runs a MAFFT
    multiple sequence alignment of human + orthologs through a ProteinFileStore.
    """

    def __init__(self, store: ProteinFileStore):
        self.store = store

    def annotate_align(self, human, orthologs: list) -> tuple[str, str]:
        gb_path = self._write_annotated_genbank(human)
        aligned_fasta = self._run_mafft(human, orthologs)
        return str(gb_path), str(aligned_fasta)

    def _read_record(self, protein):
        path = self.store.fasta_path(protein)
        try:
            return SeqIO.read(path, "fasta")
        except (ValueError, FileNotFoundError) as e:
            raise PipelineError(
                f"Could not read the FASTA for {protein.organism.name} "
                f"{protein.id}: {e}",
                stage="alignment",
            ) from e

    def _write_annotated_genbank(self, human):
        record = self._read_record(human)
        record.id = human.id
        record.name = human.id
        record.description = human.name
        record.annotations["molecule_type"] = "protein"

        for f in human.features:
            record.features.append(
                SeqFeature(
                    FeatureLocation(f.start - 1, f.end),
                    type=f.annotation.name,
                    qualifiers={"note": [f.note]},
                )
            )

        gb_path = self.store.annotated_genbank_path()
        try:
            SeqIO.write([record], gb_path, "genbank")
        except Exception as e:
            raise PipelineError(
                f"Could not write the annotated GenBank record: {e}",
                stage="alignment",
            ) from e
        return gb_path

    def _run_mafft(self, human, orthologs: list):
        if shutil.which("mafft") is None:
            raise MissingDependency(
                "MAFFT is not installed or not on PATH.",
                stage="alignment",
                hint="Install it with `brew install mafft` or "
                     "`conda install -c bioconda mafft`.",
            )

        combined_path = self.store.combined_fasta_path()
        human_record = self._read_record(human)
        human_record.id = f"HUMAN_{human.id}"
        human_record.description = human.name
        records = [human_record]

        for p in orthologs:
            p_fasta = self.store.fasta_path(p)
            if not p_fasta.exists():
                continue
            rec = self._read_record(p)
            rec.id = f"{p.organism.name}_{p.id}"
            rec.description = ""
            records.append(rec)

        SeqIO.write(records, combined_path, "fasta")

        try:
            result = subprocess.run(
                ["mafft", "--auto", str(combined_path)],
                capture_output=True,
                text=True,
                timeout=MAFFT_TIMEOUT,
            )
        except subprocess.TimeoutExpired as e:
            raise PipelineError(
                f"MAFFT did not finish within {MAFFT_TIMEOUT}s.",
                stage="alignment",
            ) from e

        if result.returncode != 0:
            tail = (result.stderr or "").strip().splitlines()[-3:]
            raise PipelineError(
                "MAFFT alignment failed: " + " ".join(tail),
                stage="alignment",
            )

        aligned_path = self.store.alignment_fasta_path()
        aligned_path.write_text(result.stdout)
        return aligned_path
