export type OrganismName =
  | "HUMAN"
  | "MOUSE"
  | "ALPACA"
  | "CYNO"
  | "CHICKEN"
  | "RABBIT"
  | "LLAMA";

export type AnnotationName =
  | "ECD"
  | "CHAIN"
  | "TM"
  | "SIGNAL"
  | "CYTO"
  | "GLYCOSYLATION";

export interface CustomOrganismIn {
  scientific_name: string;
  tax_id: number;
}

export interface JobRequest {
  protein_id: string;
  protein_name: string;
  organism_names?: OrganismName[] | null;
  custom_organisms?: CustomOrganismIn[];
}

export interface FeatureOut {
  annotation: AnnotationName | string;
  start: number;
  end: number;
  note: string;
}

export interface PassportTableData {
  rec_name: string;
  aliases: string[] | string;
  gene_id: string;
  length: number;
  mass: number;
  target_type: string;
  exp_pdbs: string[];
  known_activity: string | null;
  exp_pattern: string | null;
}

export interface ProteinOut {
  id: string;
  organism: string;
  scientific_name: string;
  name: string;
  seq: string;
  features: FeatureOut[];
  fasta_url: string | null;
  pdb_url: string | null;
  gff_url: string | null;
  rmsd: number | null;
  structure_alignment_image_url: string | null;
  aligned_pdb_url: string | null;
}

export interface HumanProteinOut extends ProteinOut {
  passport_table_data: PassportTableData;
  genbank_url: string | null;
  alignment_fasta_url: string | null;
  annotated_structure_image_url: string | null;
  string_image_url: string | null;
  reference_pdb_url: string | null;
}

export interface WarningOut {
  stage: string;
  message: string;
  organism: string | null;
}

export interface JobResponse {
  job_id: string;
  status: "completed" | "completed_with_warnings";
  human: HumanProteinOut;
  orthologs: ProteinOut[];
  warnings: WarningOut[];
}

export interface ApiErrorBody {
  kind:
    | "invalid_input"
    | "not_found"
    | "upstream"
    | "missing_dependency"
    | "pipeline"
    | "internal";
  stage: string | null;
  message: string;
  hint: string | null;
}
