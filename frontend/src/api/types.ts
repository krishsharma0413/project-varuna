// Response shapes of the varuna API (see app/api/routes_*.py).

export type Verdict = "true" | "false" | "misleading" | "unverified" | "outdated" | "opinion";
export type ClaimType = "verifiable" | "contested" | "opinion" | "prediction";
export type JobStatus = "queued" | "processing" | "done" | "failed" | "rejected";

export interface Source {
  url: string;
  domain: string;
  title: string;
  snippet: string;
  tier: number;
  kind: string;
  rank: string;
  found_via: string;
  stance?: "supports" | "contradicts" | "related" | "";
  published?: string;
}

export interface ClaimResult {
  claim_id: string;
  text: string;
  original: string;
  delivery?: "literal" | "sarcastic" | "hyperbole" | "quoted";
  type: ClaimType;
  volatility: "breaking" | "ongoing" | "settled";
  topic_tags: string[];
  resolution_date: string | null;
  verdict: Verdict;
  explanation: string;
  sources: Source[];
  queries?: string[];
  search_rounds?: number;
  checked_at: string;
  expires_at: string;
  reused: boolean;
}

export interface Summary {
  verdict: Verdict;
  claim_text: string;
  counts: Record<Verdict, number>;
  claim_count: number;
}

export interface CheckResult {
  checked_at: string;
  expires_at: string;
  claims: ClaimResult[];
  summary: Summary | null;
  inputs_used: string[];
  extraction: {
    caption?: string;
    transcript?: string;
    ocr_text?: string;
    cleaned_text: string;
    frames_used: number;
  };
  pipeline_version: string;
  models: Record<string, string>;
}

export interface ReelCard {
  reel_id: string;
  permalink: string;
  creator_handle: string | null;
  duration_s: number | null;
  topic_tags: string[];
  request_count: number;
  checked_at: string;
  expires_at: string;
  stale: boolean;
  summary: Summary | null;
}

export interface ReelPage {
  items: ReelCard[];
  next_before: string | null;
}

export interface ReelDetail {
  reel_id: string;
  permalink: string;
  creator_handle: string | null;
  caption: string;
  duration_s: number | null;
  topic_tags: string[];
  request_count: number;
  stale: boolean;
  current: CheckResult;
  history: CheckResult[];
}

export interface Hero {
  claim: ClaimResult;
  reel_id: string;
  checks: number;
  unique_people: number | null;
  distinct_reels: number;
  last_checked_at: string;
  window_hours: number | null;
  fallback: boolean;
}

export interface Creator {
  handle: string;
  reels_checked: number;
  claims_checked: number;
  counts: Partial<Record<Verdict, number>>;
  record_visible: boolean;
  min_sample: number;
}

export interface Job {
  job_id: string;
  reel_id: string;
  status: JobStatus;
  step: string | null;
  error: string | null;
  attempts: number;
}

export interface SubmitResult {
  status: JobStatus;
  reel_id: string;
  job_id: string | null;
  reason?: string;
}

export interface Me {
  email: string | null;
  invited: boolean;
  is_admin: boolean;
}

export interface LogRow {
  trace_id: string;
  timestamp: string;
  log_level: "debug" | "info" | "error";
  message: string;
}

export interface LogsResponse {
  mode: "trace" | "reel" | "range";
  items: LogRow[];
  trace_ids: string[];
  next_before: string | null;
  reel_id?: string;
  since?: string;
  until?: string | null;
}

export interface BusinessCriticalRow {
  timestamp: string;
  trace_id: string;
  search_engine: string;
  event: string;
  detail: string;
}

export interface PublicConfig {
  google_client_id: string;
  hero_window_hours: number;
  min_creator_sample: number;
  max_video_seconds: number;
  submit_limits: string[];
  min_independent_sources: number;
  topics: string[];
}

export interface Transparency {
  pipeline_version: string;
  prompt_version: string;
  provider: string;
  models: { role: string; slug: string; url: string; step: string; receives: string; returns: string; reasoning: string }[];
  topic_gate: { enabled: boolean; topics: string[]; empty_caption: "reject" | "allow"; remember_hours: number };
  download: { tools: string[]; max_video_seconds: number; max_video_mb: number };
  extraction: {
    frame_intervals: { up_to_seconds: number; every_seconds: number }[];
    max_frames: number;
    ocr_engine: "vision" | "none";
    ocr_frames: number;
    transcription_api: "stt" | "chat";
    transcription_language: string;
    chunk_seconds: number;
    max_claims_per_reel: number;
  };
  verification: {
    search_chain: string[];
    results_per_query: number;
    max_queries_per_claim: number;
    factcheck_api_enabled: boolean;
    official_sites: string[];
    factcheck_sites: string[];
    min_independent_sources: number;
    max_evidence: number;
    research_rounds: number;
    follow_up_queries_per_round: number;
    new_evidence_per_round: number;
    default_rank: string;
  };
  ttl_hours: { breaking: number; ongoing: number; settled: number; default: number };
  retention: { history_max_entries: number; history_keeps_raw_text: boolean; jobs_days: number; requests_days: number };
  creators_min_sample: number;
  hero_window_hours: number;
  limits: { submit: string[]; daily_check_cap: number };
  prompts: { name: string; text: string }[];
}

export interface Rankings {
  version: number | null;
  ranks: Record<string, string>;
  sources: { domain: string; rank: string; kind: string; rationale: string }[];
}

export interface RecordRow {
  reel_id: string;
  creator_handle: string;
  permalink: string | null;
  state: "checked" | "stale" | "rejected" | "empty";
  summary: Summary | null;
  claim_count: number;
  history_count: number;
  request_count: number;
  checked_at: string | null;
  expires_at: string | null;
  gate_reason: string | null;
  last_activity: string | null;
}

export interface DeletePlan {
  reel_id: string;
  history_entries: number;
  delete_claims: string[];
  expire_shared_claims: string[];
  creator: string | null;
  creator_inc: Record<string, number>;
}

export interface RecordDetail {
  record: Record<string, unknown>;
  jobs: { job_id: string; status: JobStatus; step: string | null; error: string | null; trace_id: string | null; created_at: string; finished_at: string | null }[];
  claims: { claim_id: string; text: string; reels: number }[];
  requests: number;
  disputes: number;
  running_job: string | null;
  plan: DeletePlan;
}
