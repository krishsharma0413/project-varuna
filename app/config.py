"""Configuration loaded from config.yaml.

`get_config()` reads and validates the file on every call (no caching), so manual edits apply
immediately. Connection settings (mongo.uri, redis.*) are used when a connection is first opened,
so changing those needs a restart of the containers holding the connection.
"""

from __future__ import annotations

import sys
import threading
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

# Docker mounts the repo root at /config; local runs fall back to the working directory.
CONFIG_CANDIDATES = (Path("/config/config.yaml"), Path("config.yaml"))


class _Section(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AppSection(_Section):
    name: str = "varuna"
    public_base_url: str = "http://localhost:8080"


class NetworkSection(_Section):
    trusted_proxy_cidrs: list[str] = ["127.0.0.0/8", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]
    client_ip_header: str = "X-Real-IP"


class GoogleSection(_Section):
    client_id: str = ""
    client_secret: str = ""  # not needed for the ID-token sign-in flow; accepted so it can live here


class JwtSection(_Section):
    secret: str = Field(min_length=32)
    algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"
    ttl_hours: float = Field(24, gt=0)
    cookie_name: str = "varuna_session"
    cookie_secure: bool = False


class InvitedSection(_Section):
    instagram: list[str] = []
    mail: list[str] = []


class AuthSection(_Section):
    google: GoogleSection = GoogleSection()
    jwt: JwtSection
    invited: InvitedSection = InvitedSection()
    admins: list[str] = []


class MongoSection(_Section):
    uri: str
    database: str = "varuna"


class RedisSection(_Section):
    queue_url: str = "redis://redis-queue:6379/0"
    cache_url: str = "redis://redis-cache:6379/0"


class CacheSection(_Section):
    ttl_seconds: int = Field(60, ge=0)
    hero_ttl_seconds: int = Field(60, ge=0)


class RateLimitsSection(_Section):
    read: list[str] = ["120/minute"]
    search: list[str] = ["30/minute"]
    auth: list[str] = ["10/minute"]
    jobs: list[str] = ["60/minute"]
    dispute: list[str] = ["3/hour"]
    submit: list[str] = ["5/hour", "20/day"]


class BudgetSection(_Section):
    daily_check_cap: int = Field(50, ge=0)


class FrameInterval(_Section):
    max_seconds: float
    every: float = Field(gt=0)


class FramesSection(_Section):
    intervals: list[FrameInterval] = [
        FrameInterval(max_seconds=15, every=0.5),
        FrameInterval(max_seconds=60, every=1),
        FrameInterval(max_seconds=180, every=2),
        FrameInterval(max_seconds=100_000, every=4),
    ]
    max_frames: int = Field(60, gt=0)
    dedupe_distance: int = Field(6, ge=0)
    width: int = Field(720, gt=0)


class OcrSection(_Section):
    engine: Literal["vision", "none"] = "vision"
    max_frames: int = Field(8, gt=0)


class TranscriptionSection(_Section):
    api: Literal["stt", "chat"] = "stt"
    language: str = ""
    chunk_seconds: int = Field(90, gt=0)


class PipelineSection(_Section):
    lock_ttl_seconds: int = Field(900, gt=0)
    max_video_seconds: int = Field(180, gt=0)
    max_video_mb: int = Field(100, gt=0)
    work_dir: str = "/tmp/varuna-jobs"
    max_claims_per_reel: int = Field(6, gt=0)
    frames: FramesSection = FramesSection()
    ocr: OcrSection = OcrSection()
    transcription: TranscriptionSection = TranscriptionSection()


class InstaloaderSection(_Section):
    username: str = ""
    password: str = ""
    session_dir: str = "/data/instaloader"
    login_cooldown_minutes: int = Field(360, ge=0)


class YtDlpSection(_Section):
    cookies_file: str = ""


class DownloaderSection(_Section):
    order: list[Literal["instaloader", "yt-dlp"]] = ["instaloader", "yt-dlp"]
    timeout_seconds: float = Field(30, gt=0)  # per network request; the video download itself gets twice this
    instaloader: InstaloaderSection = InstaloaderSection()
    yt_dlp: YtDlpSection = YtDlpSection()


class ModelsSection(_Section):
    small: str
    strong: str
    transcription: str
    vision: str
    embedding: str = ""


Effort = Literal["default", "none", "minimal", "low", "medium", "high", "xhigh", "max"]


class ReasoningSection(_Section):
    """Reasoning effort per pipeline step. "default" leaves it to the model; "none" switches it off."""

    topic_gate: Effort = "none"
    cleanup: Effort = "none"
    claims: Effort = "default"
    ocr: Effort = "none"
    transcription: Effort = "none"  # only used with pipeline.transcription.api: chat
    verdict: Effort = "default"


class ProviderRoutingSection(_Section):
    # OpenRouter serves one model through several providers, which don't all behave the same.
    require_parameters: bool = True   # only route to providers that support every parameter sent
    ignore: list[str] = []            # provider names never to use, e.g. ["StreamLake"]


class OpenRouterSection(_Section):
    api_key: str = ""
    base_url: str = "https://openrouter.ai/api/v1"
    timeout_seconds: float = Field(120, gt=0)
    max_attempts: int = Field(3, ge=1, le=10)  # tries per call on timeouts, 429s and 5xx errors
    models: ModelsSection
    reasoning: ReasoningSection = ReasoningSection()
    provider: ProviderRoutingSection = ProviderRoutingSection()


class SearxngSection(_Section):
    url: str = "http://searxng:8080"
    engines: list[str] = ["google", "duckduckgo"]
    timeout_seconds: float = Field(15, gt=0)


class ApiKeySection(_Section):
    api_key: str = ""


class SeleniumSection(_Section):
    engines: list[Literal["duckduckgo", "bing", "google"]] = ["duckduckgo", "bing", "google"]
    page_timeout_seconds: float = Field(20, gt=0)


class SearchSection(_Section):
    providers: list[Literal["searxng", "serper", "tavily", "brave", "selenium"]] = ["searxng", "serper", "selenium"]
    failure_cooldown_seconds: int = Field(600, ge=0)
    max_parallel: int = Field(2, gt=0)
    results_per_query: int = Field(5, gt=0)
    max_queries_per_claim: int = Field(4, gt=0)
    api_timeout_seconds: float = Field(20, gt=0)  # serper, tavily, brave and Google Fact Check requests
    country: str = "in"
    language: str = "en"
    searxng: SearxngSection = SearxngSection()
    serper: ApiKeySection = ApiKeySection()
    tavily: ApiKeySection = ApiKeySection()
    brave: ApiKeySection = ApiKeySection()
    selenium: SeleniumSection = SeleniumSection()


class FactCheckSection(_Section):
    google_api_key: str = ""
    language: str = "en"
    max_results: int = Field(5, gt=0)


class ResearchSection(_Section):
    max_rounds: int = Field(3, ge=1, le=5)            # search rounds per claim, the first included
    queries_per_round: int = Field(2, ge=1, le=4)     # follow-up searches the model may ask for per round
    new_evidence_per_round: int = Field(6, ge=1, le=20)


class VerificationSection(_Section):
    official_sites: list[str] = []
    factcheck_sites: list[str] = []
    min_independent_sources: int = Field(2, ge=1)
    max_evidence: int = Field(12, gt=0)
    research: ResearchSection = ResearchSection()
    source_rankings_file: str = "data/source_rankings.yaml"
    default_rank: str = "D"


class TtlSection(_Section):
    breaking_hours: float = Field(12, gt=0)
    ongoing_hours: float = Field(72, gt=0)
    settled_hours: float = Field(720, gt=0)
    default_hours: float = Field(72, gt=0)


class HistorySection(_Section):
    max_entries: int = Field(0, ge=0)
    keep_raw_text: bool = False


class CreatorsSection(_Section):
    min_sample: int = Field(5, ge=0)


class HeroSection(_Section):
    window_hours: float = Field(6, gt=0)


class RetentionSection(_Section):
    jobs_days: int = Field(7, gt=0)
    requests_days: int = Field(30, gt=0)
    sweep_minutes: int = Field(60, gt=0)


class WorkerSection(_Section):
    concurrency: int = Field(2, gt=0)
    max_retries: int = Field(2, ge=0)
    retry_backoff_seconds: list[int] = [30, 120]


class TopicGateSection(_Section):
    enabled: bool = True
    empty_caption: Literal["reject", "allow"] = "reject"
    max_caption_chars: int = Field(2000, gt=0)
    remember_hours: float = Field(168, ge=0)


class LoggingSection(_Section):
    level: Literal["debug", "info", "error"] = "info"
    stdout: bool = True
    queue_key: str = "logs:events"
    business_critical_key: str = "logs:business_critical"
    max_backlog: int = Field(100_000, gt=0)
    batch_size: int = Field(500, gt=0)
    sqlite_path: str = "/data/logs/varuna_logs.sqlite"


class Config(_Section):
    app: AppSection = AppSection()
    network: NetworkSection = NetworkSection()
    auth: AuthSection
    mongo: MongoSection
    redis: RedisSection = RedisSection()
    cache: CacheSection = CacheSection()
    rate_limits: RateLimitsSection = RateLimitsSection()
    budget: BudgetSection = BudgetSection()
    pipeline: PipelineSection = PipelineSection()
    downloader: DownloaderSection = DownloaderSection()
    openrouter: OpenRouterSection
    search: SearchSection = SearchSection()
    factcheck: FactCheckSection = FactCheckSection()
    verification: VerificationSection = VerificationSection()
    ttl: TtlSection = TtlSection()
    history: HistorySection = HistorySection()
    creators: CreatorsSection = CreatorsSection()
    hero: HeroSection = HeroSection()
    retention: RetentionSection = RetentionSection()
    worker: WorkerSection = WorkerSection()
    logging: LoggingSection = LoggingSection()
    topics: list[str] = []
    topic_gate: TopicGateSection = TopicGateSection()

    def is_invited_email(self, email: str) -> bool:
        wanted = email.strip().lower()
        return any(wanted == m.strip().lower() for m in self.auth.invited.mail) or self.is_admin(email)

    def is_admin(self, email: str) -> bool:
        wanted = email.strip().lower()
        return bool(wanted) and any(wanted == a.strip().lower() for a in self.auth.admins)

    def is_invited_instagram(self, handle: str) -> bool:
        wanted = handle.strip().lstrip("@").lower()
        return any(wanted == h.strip().lstrip("@").lower() for h in self.auth.invited.instagram)


_lock = threading.Lock()
_last_good: Config | None = None
_last_error: str | None = None


def config_path() -> Path:
    for candidate in CONFIG_CANDIDATES:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("config.yaml not found. Copy config.example.yaml to config.yaml and fill it in.")


def resolve_path(value: str) -> Path:
    """Resolve a path from the config: relative paths are relative to config.yaml's folder."""
    path = Path(value)
    return path if path.is_absolute() else config_path().parent / path


def load_config(path: Path) -> Config:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return Config.model_validate(raw)


class ConfigError(Exception):
    pass


def describe_error(exc: Exception) -> str:
    """Error text that names the offending keys but never echoes values (the file holds secrets)."""
    if isinstance(exc, ValidationError):
        return "; ".join(
            f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors(include_input=False)
        )
    if isinstance(exc, yaml.YAMLError) and getattr(exc, "problem_mark", None) is not None:
        mark = exc.problem_mark
        return f"YAML syntax error at line {mark.line + 1}, column {mark.column + 1}: {getattr(exc, 'problem', '')}"
    return f"{type(exc).__name__}: {exc}" if isinstance(exc, OSError) else type(exc).__name__


def get_config() -> Config:
    """Read config.yaml now. Falls back to the last valid version if the file is currently invalid."""
    global _last_good, _last_error
    try:
        config = load_config(config_path())
    except (OSError, yaml.YAMLError, ValidationError) as exc:
        with _lock:
            detail = describe_error(exc)
            if _last_good is None:
                raise ConfigError(f"config.yaml is invalid: {detail}") from None
            message = f"config.yaml is invalid, using the last valid version: {detail}"
            if message != _last_error:
                _last_error = message
                print(message, file=sys.stderr, flush=True)
            return _last_good
    with _lock:
        _last_good = config
        _last_error = None
    return config
