/**
 * Types for TDD-style multi-agent runs.
 */

export type TddProvider = "openai" | "anthropic" | "openrouter";

export interface AgentTddSubagentConfig {
  name: string;
  provider: TddProvider;
  model_name?: string | null;
  temperature?: number | null;
  system_prompt?: string | null;
}

export interface AgentTddJudgeConfig {
  provider?: TddProvider | null;
  model_name?: string | null;
  temperature?: number | null;
  system_prompt?: string | null;
}

export interface AgentTddSubagentError {
  agent_name: string;
  provider: string;
  model_name?: string | null;
  error: string;
}

export interface AgentTddRunCreate {
  message: string;
  history?: Array<{ role: string; content: string }>;
  run_id?: string | null;
  checkpoint_id?: string | null;
  subagents?: AgentTddSubagentConfig[];
  judge?: AgentTddJudgeConfig | null;
  workspace_ref?: string | null;
  metadata?: Record<string, unknown>;
  fork_label?: string | null;
  fork_reason?: string | null;
}

export interface AgentRun {
  id: string;
  user_id?: string | null;
  status: string;
  input_payload: Record<string, unknown>;
  model_config: Record<string, unknown>;
  workspace_ref?: string | null;
  parent_run_id?: string | null;
  parent_checkpoint_id?: string | null;
  fork_label?: string | null;
  fork_reason?: string | null;
  trace_id?: string | null;
  span_id?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface AgentCandidate {
  id: string;
  run_id: string;
  agent_name: string;
  provider?: string | null;
  model_name?: string | null;
  output?: string | null;
  tool_calls: Record<string, unknown>;
  metrics: Record<string, unknown>;
  trace_id?: string | null;
  span_id?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface AgentDecision {
  id: string;
  run_id: string;
  candidate_id?: string | null;
  score?: number | null;
  rationale?: string | null;
  model_name?: string | null;
  trace_id?: string | null;
  span_id?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface AgentCheckpoint {
  id: string;
  run_id: string;
  sequence: number;
  label?: string | null;
  state: Record<string, unknown>;
  workspace_ref?: string | null;
  trace_id?: string | null;
  span_id?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface AgentTddRunResult {
  run: AgentRun;
  candidates: AgentCandidate[];
  decision?: AgentDecision | null;
  checkpoints: AgentCheckpoint[];
  errors: AgentTddSubagentError[];
}
