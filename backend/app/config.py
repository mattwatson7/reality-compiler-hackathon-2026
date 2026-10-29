import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    fixture_dir: Path = ROOT / "fixtures"
    max_upload_bytes: int = 100 * 1024 * 1024
    max_duration_s: int = 300
    media_ttl_s: int = 3600
    cleanup_interval_s: float = 30
    provider_mode: str = "fixture"
    meta_paid_enabled: bool = False
    meta_smoke_approved: bool = False
    compiler_mode: str = "local_rules"
    spark_visual_enabled: bool = False

    @classmethod
    def from_env(cls) -> "Settings":
        local = dotenv_values(ROOT / ".env", interpolate=False)

        def setting(name: str, default: str) -> str:
            return os.getenv(name) or local.get(name) or default

        mode = setting("PROVIDER_MODE", "fixture")
        if mode not in {"fixture", "local_cv", "meta_sam"}:
            raise ValueError("Only PROVIDER_MODE=fixture, local_cv or meta_sam is supported")
        settings = cls(
            data_dir=Path(os.getenv("DATA_DIR", str(ROOT / "data"))).resolve(),
            max_upload_bytes=int(os.getenv("MAX_UPLOAD_MB", "100")) * 1024 * 1024,
            max_duration_s=int(os.getenv("MAX_VIDEO_SECONDS", "300")),
            media_ttl_s=int(os.getenv("MEDIA_TTL_SECONDS", "3600")),
            provider_mode=mode,
            meta_paid_enabled=setting("META_ENABLE_PAID_INFERENCE", "false") == "true",
            meta_smoke_approved=setting("META_SMOKE_TEST_APPROVED", "false") == "true",
            compiler_mode=setting("META_COMPILER", "local_rules"),
            spark_visual_enabled=setting("META_SPARK_VISUAL", "false") == "true",
        )
        if min(settings.max_upload_bytes, settings.max_duration_s, settings.media_ttl_s) <= 0:
            raise ValueError("Media limits and expiration must be positive")
        if settings.compiler_mode not in {"local_rules", "muse_wonder"}:
            raise ValueError("META_COMPILER must be local_rules or muse_wonder")
        return settings
