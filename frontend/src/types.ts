export type EditableAgent = {
  name: string;
  kind: string;
  command: string;
  timeout_minutes: number;
  network: string;
};

export type SnippetCheck = {
  path: string;
  snippets: string[];
};

export type CommandCheck = {
  label: string;
  command: string;
  expected: string;
  timeout_seconds?: number;
};

export type ExpectedOutcome = {
  summary?: string | null;
  forbidden_paths?: string[];
  acceptance_points?: string[];
  files?: {
    path: string;
    change_type?: string;
    must_change?: boolean;
    expected_snippets?: string[];
    forbidden_snippets?: string[];
  }[];
};

export type HardEvaluation = {
  enabled: boolean;
  require_validation_pass?: boolean;
  max_changed_files?: number | null;
  required_paths?: string[];
  forbidden_paths?: string[];
  expected_snippets?: SnippetCheck[];
  forbidden_snippets?: SnippetCheck[];
  command_checks?: CommandCheck[];
};

export type SoftRubricItem = {
  name: string;
  weight: number;
  description: string;
};

export type SoftEvaluation = {
  enabled: boolean;
  mode: 'payload-only';
  max_score?: number;
  rubric?: SoftRubricItem[];
};

export type EditableTask = {
  id: string;
  title?: string | null;
  prompt: string;
  category?: string | null;
  difficulty?: string | null;
  repo_ref?: string | null;
  validation_commands: string[];
  expected_outcome?: ExpectedOutcome | null;
  hard_evaluation?: HardEvaluation | null;
  soft_evaluation?: SoftEvaluation | null;
  extra_fields?: Record<string, unknown>;
};

export type EditableVariant = {
  name: string;
  description: string;
  overlays: { source: string; target: string }[];
};

export type EditableConfig = {
  repo: { path: string; base_ref: string };
  agent: EditableAgent;
  agent_shape: string;
  agents: EditableAgent[];
  tasks_path: string;
  variants: EditableVariant[];
  tasks: EditableTask[];
  evaluation_commands: string[];
  evaluation_timeout_seconds?: number | null;
  output_dir?: string | null;
};

export type LoadedConfig = {
  config_path: string;
  tasks_path: string;
  config_yaml: string;
  tasks_yaml: string;
  editable: EditableConfig;
  resolved: {
    repo_path: string;
    output_dir: string;
    agents: string[];
    variants: string[];
    tasks: string[];
  };
};

export type SaveResponse = {
  config_path: string;
  tasks_path: string;
  reloaded?: LoadedConfig;
};

export type WorkspaceState = {
  state: 'empty' | 'configured';
  has_config: boolean;
  default_config_path: string;
  config_path?: string | null;
  workspace_root?: string;
};

export type BootstrapResponse = WorkspaceState & {
  loaded?: LoadedConfig;
  config_path?: string | null;
  tasks_path?: string | null;
};

export type RunPlan = {
  case_count: number;
  cleanup_policy: string;
  jobs: number;
  trials: number;
  output_dir: string;
  agents: string[];
  tasks: string[];
  variants: string[];
  cases: {
    case_id: string;
    agent_name: string;
    agent_kind: string;
    task_id: string;
    variant: string;
    trial_index: number;
    repo_ref: string;
    command_preview: string;
    expected_outcome_summary?: string | null;
    hard_evaluation_enabled?: boolean;
    soft_evaluation_enabled?: boolean;
  }[];
};

export type RunScope = {
  task_ids: string[];
  variants: string[];
  agents: string[];
};

export type RunStatus = {
  app_run_id: string;
  status: string;
  run_dir: string | null;
  case_count: number;
  completed_cases: number;
  error?: string | null;
};

export type ManualReview = {
  case_id: string;
  decision: string;
  confidence: string;
  reviewer: string;
  notes: string;
  updated_at?: string | null;
};

export type HardEvaluationCheck = {
  name: string;
  status: string;
  message: string;
  evidence?: Record<string, unknown>;
};

export type HardEvaluationPayload = {
  status?: string;
  path?: string | null;
  error?: string;
  passed?: boolean;
  score?: number | null;
  max_score?: number | null;
  summary?: string;
  checks?: HardEvaluationCheck[];
};

export type SoftEvaluationPayload = {
  status: string;
  payload_path?: string | null;
  result_path?: string | null;
};

export type ResultCase = {
  case_id: string;
  agent_name: string;
  task_id: string;
  variant: string;
  status: string;
  validation_status: string;
  confidence: string;
  telemetry_status?: string;
  telemetry_source?: string;
  telemetry_error?: string | null;
  agent_duration_seconds?: number | null;
  total_tokens?: number | null;
  reasoning_tokens?: number | null;
  reasoning_step_count?: number | null;
  tool_call_count?: number | null;
  changed_files?: number;
  hard_evaluation_status?: string;
  hard_evaluation_score?: number | null;
  hard_evaluation_max_score?: number | null;
  hard_evaluation_passed_checks?: number | null;
  hard_evaluation_failed_checks?: number | null;
  hard_evaluation?: HardEvaluationPayload | null;
  soft_evaluation_status?: string;
  soft_evaluation_payload_path?: string | null;
  soft_evaluation_result_path?: string | null;
  soft_evaluation?: SoftEvaluationPayload | null;
  patch_path?: string | null;
  stdout_path?: string | null;
  stderr_path?: string | null;
  manual_review?: ManualReview;
};

export type EvaluationExplanation = {
  local_only: string;
  validation_confidence: {
    high: string;
    medium: string;
    low: string;
  };
  hard_evaluation: {
    score_meaning: string;
    skipped_meaning: string;
  };
  soft_evaluation: {
    mode: 'payload-only';
    meaning: string;
  };
  manual_review: {
    meaning: string;
  };
  evidence_limits: string[];
};

export type CompareEvidenceGap = {
  code: string;
  variant: string;
  case_id?: string | null;
  message: string;
  next_step: string;
};

export type CompareGroup = {
  group_id: string;
  task_id: string;
  agent_name: string;
  trial_index: number;
  baseline_variant: string;
  comparison_variant: string;
  baseline_case_id: string;
  comparison_case_id: string;
  verdict: string;
  validation_delta: number;
  hard_check_delta: number | null;
  total_tokens_delta?: number | null;
  summary: string;
  evidence_gaps: CompareEvidenceGap[];
  experiment_variant?: string;
  experiment_case_id?: string;
  hard_delta: number;
};

export type ResultsPayload = {
  overview: {
    case_count: number;
    failed_count: number;
    timeout_count: number;
    low_confidence_count: number;
    telemetry_gap_count: number;
  };
  selected_baseline_variant?: string | null;
  available_baseline_variants?: string[];
  baseline_selection_notice?: string | null;
  evaluation_explanation?: EvaluationExplanation;
  compare_groups?: CompareGroup[];
  cases: ResultCase[];
};

export type ArtifactContent = {
  path: string;
  content: string;
  exists: boolean;
  error?: string;
};

export type CaseDetailPayload = {
  case: ResultCase;
  patch?: ArtifactContent | null;
  prompt?: ArtifactContent | null;
  logs: (ArtifactContent & { kind: string })[];
  hard_evaluation?: HardEvaluationPayload | null;
  soft_evaluation?: SoftEvaluationPayload | null;
  manual_review: ManualReview;
};

export type LogPayload = {
  console: string[];
  files: { path: string; tail: string }[];
};
