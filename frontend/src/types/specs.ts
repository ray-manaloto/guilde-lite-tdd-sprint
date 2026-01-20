export interface Spec {
  id: string;
  user_id?: string | null;
  title: string;
  task: string;
  complexity: string;
  status: string;
  phases: string[];
  artifacts: Record<string, unknown>;
  created_at: string;
  updated_at?: string | null;
}

export interface SpecPlanningQuestion {
  question: string;
  rationale?: string | null;
}

export interface SpecPlanningAnswer {
  question: string;
  answer: string;
}

export interface SpecPlanningCreate {
  title?: string | null;
  task: string;
  max_questions?: number;
}

export interface SpecPlanningAnswers {
  answers: SpecPlanningAnswer[];
}

export interface SpecPlanningPayload {
  status: string;
  questions: SpecPlanningQuestion[];
  answers: SpecPlanningAnswer[];
  metadata: SpecPlanningMetadata;
}

export interface SpecPlanningTelemetryLink {
  provider?: string | null;
  model_name?: string | null;
  trace_id?: string | null;
  trace_url?: string | null;
  error?: string | null;
}

export interface SpecPlanningMetadata {
  mode?: string;
  provider?: string | null;
  model_name?: string | null;
  max_questions?: number;
  question_count?: number;
  trace_id?: string | null;
  trace_url?: string | null;
  candidates?: SpecPlanningTelemetryLink[];
  judge?: {
    provider?: string | null;
    model_name?: string | null;
    trace_id?: string | null;
    trace_url?: string | null;
    score?: number | null;
    rationale?: string | null;
  };
  selected_candidate?: {
    provider?: string | null;
    model_name?: string | null;
  };
}

export interface SpecPlanningResponse {
  spec: Spec;
  planning: SpecPlanningPayload;
}
