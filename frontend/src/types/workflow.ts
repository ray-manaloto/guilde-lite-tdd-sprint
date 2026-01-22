/**
 * Types for sprint workflow visualization.
 * These types match the backend WorkflowTracker schemas.
 */

// Status enums as union types
export type WorkflowStatus = "planned" | "active" | "completed" | "failed";
export type PhaseStatus = "pending" | "in_progress" | "completed" | "failed" | "skipped";
export type CandidateStatus = "pending" | "running" | "completed" | "failed";

// Token tracking (matches backend TokenUsage schema)
export interface TokenUsage {
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
}

export interface TokenCost {
  input_cost: string;
  output_cost: string;
  total_cost: string;
}

// Candidate types
export interface Candidate {
  id: string;
  provider: string;
  model: string;
  status: CandidateStatus;
  started_at?: string | null;
  completed_at?: string | null;
  duration_ms?: number | null;
  tokens?: TokenUsage | null;
  cost?: TokenCost | null;
  response?: Record<string, unknown> | null;
  error?: string | null;
  trace_id?: string | null;
  trace_url?: string | null;
}

export interface CandidateSummary {
  provider: string;
  model: string;
  status: CandidateStatus;
  duration_ms?: number | null;
  success: boolean;
}

// Judge decision
export interface JudgeDecision {
  model: string;
  winner: string;
  score?: number | null;
  rationale: string;
  trace_id?: string | null;
  trace_url?: string | null;
}

// Timeline event
export interface TimelineEvent {
  sequence: number;
  event_type: string;
  timestamp: string;
  state?: string | null;
  phase?: string | null;
  checkpoint_id?: string | null;
  trace_id?: string | null;
  trace_url?: string | null;
  duration_ms?: number | null;
  metadata: Record<string, unknown>;
}

// Phase record (matches backend PhaseResponse schema)
export interface Phase {
  phase: string;
  sequence: number;
  start_time?: string | null;
  end_time?: string | null;
  duration_ms?: number | null;
  status: PhaseStatus;
  checkpoint_before?: string | null;
  checkpoint_after?: string | null;
  llm_config?: Record<string, unknown>;
  input_data?: Record<string, unknown>;
  output_data?: Record<string, unknown>;
  candidates: CandidateSummary[];
  judge_result?: JudgeDecision | null;
  trace_id?: string | null;
  trace_url?: string | null;
}

// Full workflow (matches backend WorkflowResponse schema)
export interface Workflow {
  sprint_id: string;
  spec_id?: string | null;
  status: WorkflowStatus;
  current_phase?: string | null;
  current_checkpoint?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  total_duration_ms?: number | null;
  phases: Phase[];
  timeline: TimelineEvent[];
  aggregated_tokens?: TokenUsage;
  aggregated_cost?: TokenCost;
  logfire_project_url?: string | null;
}

// Timeline response
export interface TimelineResponse {
  sprint_id: string;
  total_duration_ms?: number | null;
  events: TimelineEvent[];
}

// Artifact types
export interface Artifact {
  name: string;
  path: string;
  type: "json" | "text" | "code" | "directory";
  size_bytes?: number | null;
  created_at?: string | null;
}

export interface ArtifactsResponse {
  sprint_id: string;
  base_path: string;
  artifacts: Artifact[];
}

// Utility functions

/**
 * Format a duration in milliseconds to a human-readable string.
 * @param ms - Duration in milliseconds
 * @returns Formatted duration string (e.g., "1.5s", "2m 30s", "1h 15m")
 */
export function formatDuration(ms: number): string {
  if (ms < 1000) {
    return `${ms}ms`;
  }

  const seconds = ms / 1000;
  if (seconds < 60) {
    return `${seconds.toFixed(1)}s`;
  }

  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.round(seconds % 60);

  if (minutes < 60) {
    return remainingSeconds > 0 ? `${minutes}m ${remainingSeconds}s` : `${minutes}m`;
  }

  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;

  return remainingMinutes > 0 ? `${hours}h ${remainingMinutes}m` : `${hours}h`;
}

/**
 * Format a cost value to a currency string.
 * @param cost - Cost as string or number
 * @returns Formatted cost string (e.g., "$0.0012")
 */
export function formatCost(cost: string | number): string {
  const numCost = typeof cost === "string" ? parseFloat(cost) : cost;

  if (isNaN(numCost)) {
    return "$0.00";
  }

  // For very small costs, show more decimal places
  if (numCost < 0.01) {
    return `$${numCost.toFixed(4)}`;
  }

  return `$${numCost.toFixed(2)}`;
}
