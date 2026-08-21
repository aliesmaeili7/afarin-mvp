export type SummaryObservation = {
  run_id: string;
  case_id: string;
  category: string | null;
  style_id: string;
  template_id: string;
  recipe: string;
  label: string | null;
  prompt_version: string | null;
  mode: string;
  image_model: string | null;
  overall: number | null;
  identity: number | null;
  commercial: number | null;
  hard_failed: boolean | null;
};
