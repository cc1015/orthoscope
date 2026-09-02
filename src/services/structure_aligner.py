from pymol import cmd

from errors import PipelineError
from models.annotation import Annotation
from utils.file_utils import ensure_directory
from services.protein_store import ProteinFileStore


class StructureAligner:
    """
    Drives PyMOL to annotate and align predicted protein structures.
    Reads PDBs and writes PNG/PSE outputs through a ProteinFileStore.
    """

    def __init__(self, store: ProteinFileStore):
        self.store = store
        self.warnings: list[dict] = []
        self.reference_pdb = None

    def annotate_3d_structure(self, protein) -> str | None:
        pdb_path = self.store.pdb_path(protein)
        if not pdb_path or not pdb_path.exists():
            return None

        try:
            cmd.load(str(pdb_path))
            for annotation, idxs in protein.annotations.items():
                for (start, end) in idxs:
                    cmd.color(annotation.color, f"resi {start}-{end}")
            cmd.orient()

            png_path = self.store.dir_for(protein) / f"{protein.name}_structure_ss.png"
            pse_path = self.store.dir_for(protein) / f"{protein.name}_annotated_structure.pse"
            cmd.png(str(png_path), width=2000, ray=1)
            cmd.save(str(pse_path))
        except Exception as e:
            raise PipelineError(
                f"PyMOL could not render the annotated structure: "
                f"{type(e).__name__}: {e}",
                stage="structure",
            ) from e
        finally:
            cmd.delete("all")

        if not png_path.exists():
            raise PipelineError(
                "PyMOL reported success but wrote no structure image.",
                stage="structure",
            )
        return str(png_path)

    def align(self, target, mobiles: list) -> dict:
        """
        Aligns each mobile protein's structure against `target`. Prioritizes
        aligning domains of interest (ECD/CHAIN) when annotations exist.

        Returns:
            dict mapping each mobile protein -> dict with keys
            image, rmsd and aligned_pdb.
        """
        pse_path = self.store.alignment_pse_path()
        target_pdb = self.store.pdb_path(target)
        if not target_pdb or not target_pdb.exists():
            return {}

        target_label = target.organism.name + "_" + target.id
        target_length = target.passport_table_data.get('length') or len(target.seq)
        (target_start, target_end) = (1, target_length)

        domains = target.annotations.get(Annotation.ECD) or target.annotations.get(Annotation.CHAIN)
        if domains:
            (target_start, target_end) = (target_length, 1)
            for (start, end) in domains:
                target_start = min(target_start, start)
                target_end = max(target_end, end)

        try:
            cmd.load(str(target_pdb), target_label)
            cmd.select(f"{target_label}_sele", f"{target_label} and resi {target_start}-{target_end}")
            cmd.create(f"{target_label}_chain", f"{target_label}_sele")
            cmd.delete(f"{target_label}_sele")
            cmd.delete(f"{target_label}")
        except Exception as e:
            cmd.delete("all")
            raise PipelineError(
                f"PyMOL could not prepare the reference structure: "
                f"{type(e).__name__}: {e}",
                stage="structure",
            ) from e

        image_dir = self.store.structure_image_dir()
        ensure_directory(image_dir)
        ensure_directory(self.store.aligned_dir())

        reference_pdb = self.store.reference_pdb_path()
        try:
            cmd.save(str(reference_pdb), f"{target_label}_chain")
        except Exception:
            reference_pdb = None

        self.reference_pdb = reference_pdb

        rmsd_dict = {}
        try:
            for mobile in mobiles:
                if mobile.from_ncbi:
                    continue
                mobile_pdb = self.store.pdb_path(mobile)
                if not mobile_pdb or not mobile_pdb.exists():
                    continue

                mobile_label = mobile.organism.name + "_" + mobile.id
                try:
                    result = self._align_one(
                        mobile, mobile_label, mobile_pdb, target_label,
                        target_start, target_end, target_length,
                        image_dir, pse_path,
                    )
                except Exception as e:
                    self.warnings.append({
                        "stage": "structure",
                        "organism": mobile.organism.name,
                        "message": (
                            f"Structural alignment failed: "
                            f"{type(e).__name__}: {e}"
                        ),
                    })
                    cmd.delete(f"{mobile_label}_sele")
                    cmd.delete(mobile_label)
                    cmd.delete(f"{mobile_label}_chain")
                    continue

                if result is not None:
                    rmsd_dict[mobile] = result
        finally:
            cmd.delete("all")

        return rmsd_dict

    def _align_one(self, mobile, mobile_label, mobile_pdb, target_label,
                   target_start, target_end, target_length, image_dir, pse_path):
        cmd.load(str(mobile_pdb), mobile_label)

        (mobile_start, mobile_end) = (target_start, target_end)
        ecd = mobile.annotations.get(Annotation.ECD)
        if ecd:
            (mobile_start, mobile_end) = ecd[0]
            if mobile_end == target_length:
                mobile_end = target_end

        cmd.select(f"{mobile_label}_sele", f"{mobile_label} and resi {mobile_start}-{mobile_end}")
        cmd.create(f"{mobile_label}_chain", f"{mobile_label}_sele")
        cmd.delete(f"{mobile_label}_sele")
        cmd.delete(f"{mobile_label}")

        result = cmd.align(
            f"polymer and name CA and {mobile_label}_chain",
            f"polymer and name CA and {target_label}_chain",
        )
        if not result:
            raise RuntimeError("PyMOL returned no alignment result")

        rmsd = round(result[0], 2)
        mobile.rmsd = rmsd

        aligned_pdb = self.store.aligned_pdb_path(mobile)
        cmd.save(str(aligned_pdb), f"{mobile_label}_chain")

        png_path = image_dir / f"{mobile_label}_human_aligned_ss.png"
        cmd.disable("all")
        cmd.enable(mobile_label)
        cmd.enable(target_label)
        cmd.color("green", target_label)
        cmd.zoom()
        cmd.png(str(png_path), width=3000, ray=1)
        cmd.save(str(pse_path))

        return {
            "image": str(png_path),
            "rmsd": rmsd,
            "aligned_pdb": str(aligned_pdb),
        }
