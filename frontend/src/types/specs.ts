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
  metadata: Record<string, unknown>;
}

export interface SpecPlanningResponse {
  spec: Spec;
  planning: SpecPlanningPayload;
}
