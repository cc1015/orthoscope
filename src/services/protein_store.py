from pathlib import Path
from utils.file_utils import ensure_directory, safe_write_text, safe_write_bytes
from models.protein_model.protein import features_to_gff


class ProteinFileStore:
    """
    Owns the on-disk layout for a single protein-name run.

    Directory layout:
        <root>/output_<protein_name>/
            <organism_lower>_<protein_name>/
                <ORGANISM>_<id>_seq.fasta
                <id>_annotations.gff
                <pdb_filename>
            alignments.pse
            alignment.fasta
            combined_seqs.fasta
            annotated_seq_human.gb
            structure_alignment_images/
    """

    def __init__(self, root: Path, protein_name: str):
        self.root = Path(root).resolve()
        self.protein_name = protein_name
        self.protein_root = self.root / f"output_{protein_name}"

        # Callers are expected to have validated protein_name, but the store
        # owns these paths, so it refuses to be pointed outside its root
        # regardless of who constructed it.
        if not self.protein_root.resolve().is_relative_to(self.root):
            raise ValueError(
                f"protein_name {protein_name!r} escapes the output root"
            )

    def dir_for(self, protein) -> Path:
        return self.protein_root / f"{protein.organism.name.lower()}_{protein.name}"

    def fasta_path(self, protein) -> Path:
        return self.dir_for(protein) / f"{protein.organism.name}_{protein.id}_seq.fasta"

    def gff_path(self, protein) -> Path:
        return self.dir_for(protein) / f"{protein.id}_annotations.gff"

    def pdb_path(self, protein) -> Path | None:
        if not protein.pred_pdb_filename:
            return None
        return self.dir_for(protein) / protein.pred_pdb_filename

    def aligned_dir(self) -> Path:
        return self.protein_root / "aligned_structures"

    def aligned_pdb_path(self, protein) -> Path:
        return self.aligned_dir() / f"{protein.organism.name}_{protein.id}_aligned.pdb"

    def reference_pdb_path(self) -> Path:
        return self.aligned_dir() / "reference.pdb"

    def structure_image_dir(self) -> Path:
        return self.protein_root / "structure_alignment_images"

    def alignment_pse_path(self) -> Path:
        return self.protein_root / "alignments.pse"

    def combined_fasta_path(self) -> Path:
        return self.protein_root / "combined_seqs.fasta"

    def alignment_fasta_path(self) -> Path:
        return self.protein_root / "alignment.fasta"

    def annotated_genbank_path(self) -> Path:
        return self.protein_root / "annotated_seq_human.gb"

    def save(self, protein) -> None:
        ensure_directory(self.dir_for(protein))
        safe_write_text(self.fasta_path(protein), protein.fasta or "")
        if protein.features:
            safe_write_text(self.gff_path(protein), features_to_gff(protein))
        if protein.pred_pdb_filename and protein.pred_pdb_content:
            safe_write_bytes(self.pdb_path(protein), protein.pred_pdb_content)
