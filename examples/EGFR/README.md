# Example output: EGFR (human `P00533`)

Real, unedited output from a pipeline run against human EGFR, kept in the
repository so you can see what OrthoScope produces without installing PyMOL,
MAFFT, or waiting on the external APIs.

Reproduce it with:

```bash
curl -X POST http://localhost:8000/jobs \
  -H 'Content-Type: application/json' \
  -d '{"protein_id": "P00533", "protein_name": "EGFR",
       "organism_names": ["MOUSE", "CHICKEN"]}'
```

…or enter `EGFR` / `P00533` in the web UI.

## What's here

| File | What it is |
| --- | --- |
| `annotated_seq_human.gb` | Human EGFR as GenBank, 1210 aa, 18 annotated features (Biopython) |
| `combined_seqs.fasta` | The MAFFT input |
| `alignment.fasta` | The MAFFT alignment, 1212 columns |
| `<organism>_EGFR/*_seq.fasta` | Retrieved sequence per organism |
| `<organism>_EGFR/*_annotations.gff` | Feature track per organism (18 human / 15 mouse / 16 chicken) |
| `human_EGFR/EGFR_structure_ss.png` | AlphaFold model, colored by annotated feature |
| `structure_alignment_images/*.png` | Each ortholog superposed on human — human in green, ortholog in magenta |
| `string_network.png` | STRING-DB interaction network |

Orthologs resolved: **mouse** `Q01279` (1210 aa) and **chicken** `P13387`
(703 aa).

## Two things this sample does not include

**PDB structures and PyMOL sessions.** The run also produced AlphaFold `.pdb`
models, superposed copies under `aligned_structures/`, and `.pse` session
files. They're excluded to keep a clone small — they are re-downloaded and
regenerated on any run. This means the interactive Mol\* viewer can't be
demoed from this directory alone; run the pipeline for that.

**RMSD values.** The structural alignment computes an RMSD per ortholog, but
the pipeline only returns it in the API response and the UI — it is never
written to disk, so there is no file here to show it.

## A real inconsistency, preserved

Chicken appears in the structural alignment (there is a
`CHICKEN_P13387_human_aligned_ss.png`) but *not* in the sequence alignment —
`combined_seqs.fasta` and `alignment.fasta` contain only human and mouse.

This is what the run actually produced and is left as-is rather than tidied
up. Structural and sequence alignment are independent optional stages in
`src/api.py`, and a per-organism failure in one is reported as a warning
without blocking the other, so the two can legitimately disagree about which
organisms they covered.

Renders have been downsampled to 1400px and quantized to a 256-color palette
to keep the directory under 1 MB. All text files are byte-for-byte as the
pipeline wrote them.
