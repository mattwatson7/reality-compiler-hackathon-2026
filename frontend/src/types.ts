export type Verdict = "PASS" | "FAIL" | "UNKNOWN";
export interface LegacyTaskGraph {
  version: "1.0";
  procedure: string;
  objects: { id: string; label: string }[];
  steps: { id: string; instruction: string; object_ids: string[] }[];
  constraints: { id: string; before: string; after: string }[];
}
export interface SourceSpan {
  start: number;
  end: number;
  quote: string;
}
export interface Observability {
  observability: "SUPPORTED" | "AMBIGUOUS" | "UNSUPPORTED";
  reason: string | null;
}
export type Predicate =
  | { type: "object_visible"; object_id: string }
  | { type: "object_entered_region" | "object_exited_region"; object_id: string; region_id: string }
  | { type: "visually_confirmed_state_change"; object_id: string; state_dimension: string; from_state: string; to_state: string; visual_criteria: string };
export interface SemanticEvent extends Observability {
  id: string;
  instruction: string;
  source: SourceSpan;
  predicate: Predicate | null;
  required: boolean;
}
export interface SemanticCondition extends SemanticEvent {
  scope: "during" | "final";
}
export interface SemanticTaskGraph {
  version: "2.0";
  procedure: string;
  compilation_source: "fixture" | "local_rules" | "muse" | "legacy";
  objects: { id: string; label: string; description: string; grounding_prompt: string | null }[];
  regions: (Observability & { id: string; description: string; grounding_prompt: string; coordinate_semantics: "visible_image_region" })[];
  events: SemanticEvent[];
  constraints: { id: string; operator: "BEFORE" | "AFTER"; first: string; second: string; source: SourceSpan }[];
  conditions: SemanticCondition[];
}
export type TaskGraph = LegacyTaskGraph | SemanticTaskGraph;
export type Constraint = TaskGraph["constraints"][number];
export function constraintLabel(constraint: Constraint): string {
  return "operator" in constraint
    ? `${constraint.first} ${constraint.operator} ${constraint.second}`
    : `${constraint.before} BEFORE ${constraint.after}`;
}
export interface Health {
  compiler_source: "fixture" | "local_rules" | "muse" | "legacy";
  real_muse_compilation: boolean;
  real_video_verification: boolean;
  live_inference: boolean;
  meta?: { credential_configured: boolean; catalog_authenticated: boolean; models: string[];
    paid_inference_enabled: boolean; sam_selectable: boolean; wonder_selectable: boolean;
    spark_selectable: boolean; reason: string };
}
export interface Evidence {
  id: string;
  start_s: number;
  end_s: number;
  description: string;
  source: "fixture" | "model" | "local_cv" | "meta_sam" | "muse_spark";
  model_id?: string | null;
  frame_indices?: number[];
  frame_reference?: string | null;
}
export interface CheckResult {
  id: string;
  verdict: Verdict;
  reason: string;
  evidence_ids: string[];
  required?: boolean;
}
export interface Evaluation {
  verdict: Verdict;
  reason: string;
  steps: CheckResult[];
  constraints: CheckResult[];
  conditions?: CheckResult[];
  evidence: Evidence[];
}
export interface Job {
  id: string;
  status: "queued" | "processing" | "awaiting_initialization" | "completed" | "failed" | "expired";
  progress: number;
  message: string;
  mode: "fixture" | "mock-upload" | "local_cv" | "meta_sam";
  procedure: string;
  footage_origin?: "unknown" | "genuine_camera" | "generated";
  execution_mode?: "offline_capture_review";
  expires_at: number;
  graph: TaskGraph | null;
  result: Evaluation | null;
  duration_s: number | null;
  media_url: string | null;
  error: string | null;
  preview_url?: string | null;
  frame_reference?: string | null;
  initialization?: Initialization | null;
  tracks?: VisualTrack[];
  observations?: { occurrence_id: string; event_id: string; start_s: number; end_s: number;
    usable: boolean; confidence: number; evidence: Evidence; frame_indices: number[] }[];
  saved_frame_indices?: number[];
  media_metadata?: { width: number; height: number; fps: number; normalized_sha256: string;
    source_timing?: { source_time_base: string; source_sha256: string;
      frames: { normalized_index: number; normalized_time_s: number; source_index: number; source_pts: number; source_time_s: number }[] } } | null;
  provenance?: Record<string, string>;
  inference_usage?: { model: string; reserved_microusd: number; actual_microusd: number | null; usage_verified: boolean }[];
}
export interface Box { x: number; y: number; width: number; height: number }
export interface Initialization {
  frame_reference: string;
  objects: Record<string, Box>;
  regions: Record<string, Box>;
}
export interface VisualSample {
  frame_index: number; time_s: number; box: Box | null;
  contour: [number, number][]; quality_components: Record<string, number>;
  confidence: number; status: "reliable" | "missing" | "ambiguous";
  region_overlap: Record<string, number>;
}
export interface VisualTrack {
  object_id: string; source: string; samples: VisualSample[];
  diagnostics: string[]; invalid_intervals: Record<string, number | string>[]; provenance: string;
  model_id?: string | null;
}
export interface Fixture {
  id: string;
  title: string;
  description: string;
  procedure: string;
}
export interface Ledger {
  committed_microusd: number;
  cap_microusd: number;
  remaining_microusd: number;
  reservations: number;
}

export interface EvaluationSnapshot {
  id: string;
  job_id: string;
  created_at: number;
  procedure: string;
  graph: TaskGraph;
  result: Evaluation;
  reuse_status: "original" | "reused" | "needs_perception";
  reuse_reasons: string[];
  evidence_fingerprint: string;
  provenance: Record<string, string>;
}
