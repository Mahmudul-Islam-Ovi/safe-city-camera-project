"""Centralised, validated configuration for the AI engine.

Every threshold used by the pipeline lives here and can be overridden by an
environment variable of the same name (case-insensitive), e.g.
``LOITERING_TIME_SECONDS=90``. Values are read, in increasing priority, from:

1. defaults in this file
2. ``<project-root>/.env``
3. ``ai-engine/.env``
4. real environment variables (used by Docker / CI)
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

AI_ENGINE_DIR: Path = Path(__file__).resolve().parents[2]
PROJECT_ROOT: Path = Path(os.getenv("SAFE_CITY_ROOT", str(AI_ENGINE_DIR.parent))).resolve()

RiskLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]

# COCO class names YOLO can detect that are relevant to Safe City (subset).
SUPPORTED_CLASSES: frozenset[str] = frozenset(
    {
        "person", "bicycle", "car", "motorcycle", "bus", "truck", "dog", "cat",
        "backpack", "handbag", "suitcase", "umbrella", "bottle", "cell phone", "laptop",
    }
)


class Settings(BaseSettings):
    """AI engine settings. Field names map 1:1 to upper-case env variables."""

    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", AI_ENGINE_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---------- General ----------
    service_name: str = "ai-engine"
    environment: Literal["development", "test", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_format: Literal["console", "json"] = "console"

    # ---------- Service / integration ----------
    ai_engine_host: str = "0.0.0.0"
    ai_engine_port: int = Field(8001, ge=1, le=65535)
    api_url: str = "http://localhost:8000"
    redis_url: str = "redis://localhost:6379/0"
    internal_api_key: str = "dev-only-internal-key-change-me"
    default_camera_id: str = Field("CAM-001", min_length=1, max_length=64)
    use_webcam: bool = False
    webcam_index: int = Field(0, ge=0)

    # ---------- Models ----------
    yolo_model: str = "yolo11n.pt"
    yolo_pose_model: str = "yolo11n-pose.pt"
    models_dir: Path = AI_ENGINE_DIR / "models"
    device: str = "auto"
    half_precision: bool = False

    # ---------- Detection ----------
    confidence_threshold: float = Field(0.40, ge=0.01, le=1.0)
    iou_threshold: float = Field(0.50, ge=0.01, le=1.0)
    inference_image_size: int = Field(640, ge=160, le=1920)
    detection_classes: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: [
            "person", "bicycle", "car", "motorcycle", "bus", "truck", "dog", "cat",
            "backpack", "handbag", "suitcase",
        ]
    )

    # ---------- Tracking ----------
    tracker_type: Literal["bytetrack", "botsort"] = "bytetrack"
    track_history_size: int = Field(90, ge=5, le=2000)
    track_lost_timeout_seconds: float = Field(3.0, gt=0)

    # ---------- Performance ----------
    inference_fps: float = Field(10.0, gt=0, le=120)
    frame_skip: int = Field(0, ge=0, le=30)
    process_width: int = Field(960, ge=0, le=3840)
    stream_jpeg_quality: int = Field(70, ge=10, le=100)
    pose_enabled: bool = True

    # ---------- Movement (pixel based) ----------
    stationary_speed_px: float = Field(15.0, ge=0)
    running_speed_px: float = Field(180.0, gt=0)
    speed_normalize_by_height: bool = True

    # ---------- Loitering ----------
    loitering_time_seconds: float = Field(120.0, gt=0)
    loitering_radius_pixels: float = Field(100.0, gt=0)

    # ---------- Crowd ----------
    crowd_threshold: int = Field(20, ge=1)
    crowd_critical_threshold: int = Field(40, ge=2)

    # ---------- Abandoned object ----------
    abandoned_object_seconds: float = Field(60.0, gt=0)
    abandoned_owner_distance_px: float = Field(150.0, gt=0)

    # ---------- Events / alerts ----------
    event_cooldown_seconds: float = Field(30.0, ge=0)
    alert_min_risk_level: RiskLevel = "MEDIUM"
    risk_rules_file: Path = Path("configs/risk_rules.yaml")

    # ---------- Privacy ----------
    face_blur_enabled: bool = True
    store_raw_video: bool = False
    evidence_dir: Path = Path("evidence")
    evidence_retention_days: int = Field(30, ge=1)

    # ---------- Validators ----------
    @field_validator("use_webcam", mode="before")
    @classmethod
    def _parse_use_webcam(cls, value: object) -> bool:
        if isinstance(value, str):
            clean = value.strip().lower()
            return clean in {"true", "1", "yes", "on", "t"}
        return bool(value)

    @field_validator("detection_classes", mode="before")
    @classmethod
    def _parse_classes(cls, value: object) -> list[str]:
        """Accept a comma-separated string (env friendly) or a list."""
        if isinstance(value, str):
            items = [v.strip().lower() for v in value.split(",") if v.strip()]
        elif isinstance(value, (list, tuple, set)):
            items = [str(v).strip().lower() for v in value if str(v).strip()]
        else:
            raise ValueError("DETECTION_CLASSES must be a comma-separated string or list")
        unknown = sorted(set(items) - SUPPORTED_CLASSES)
        if unknown:
            raise ValueError(f"Unsupported detection classes: {unknown}. Supported: {sorted(SUPPORTED_CLASSES)}")
        if not items:
            raise ValueError("DETECTION_CLASSES cannot be empty")
        return list(dict.fromkeys(items))  # de-duplicate, keep order

    @field_validator("device")
    @classmethod
    def _validate_device(cls, value: str) -> str:
        value = value.strip().lower()
        if value in {"auto", "cpu", "cuda", "mps"} or value.startswith("cuda:") or value.isdigit():
            return value
        raise ValueError("DEVICE must be one of: auto, cpu, cuda, cuda:N, mps")

    @model_validator(mode="after")
    def _validate_relations(self) -> Settings:
        if self.running_speed_px <= self.stationary_speed_px:
            raise ValueError("RUNNING_SPEED_PX must be greater than STATIONARY_SPEED_PX")
        if self.crowd_critical_threshold <= self.crowd_threshold:
            raise ValueError("CROWD_CRITICAL_THRESHOLD must be greater than CROWD_THRESHOLD")
        return self

    @staticmethod
    def resolve_path(path: str | Path) -> Path:
        """Resolve relative paths against the project root (not the CWD)."""
        p = Path(path)
        return p if p.is_absolute() else (PROJECT_ROOT / p).resolve()

    @property
    def evidence_path(self) -> Path:
        return self.resolve_path(self.evidence_dir)

    @property
    def risk_rules_path(self) -> Path:
        return self.resolve_path(self.risk_rules_file)

    @property
    def models_path(self) -> Path:
        return self.resolve_path(self.models_dir)

    def model_file(self, name: str) -> Path:
        """Absolute path for a model weight file inside ``models_dir``."""
        candidate = Path(name)
        return candidate if candidate.is_absolute() else self.models_path / candidate

    @property
    def min_frame_interval(self) -> float:
        """Minimum seconds between two inferences (derived from INFERENCE_FPS)."""
        return 1.0 / self.inference_fps


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings singleton."""
    return Settings()
