"""Runtime settings, read from environment variables (all optional)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except ValueError:
        return default


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    db_path: Path
    match_threshold: float  # max face distance to count as a match (lower = stricter)
    low_attendance_pct: float  # students under this % are flagged "at risk"
    timezone: str  # used only for displaying timestamps
    demo_mode: bool  # shows a "try the demo" button on the login page
    max_image_side: int  # photos are downscaled to this many pixels on the long side
    upsample: int  # detector upsampling; raise for large classes / small faces
    min_face_score: float  # drop detections below this confidence (false positives)


def get_settings() -> Settings:
    return Settings(
        db_path=Path(os.environ.get("SNAP_DB_PATH", "data/snapclass.db")),
        match_threshold=_float("SNAP_MATCH_THRESHOLD", 0.5),
        low_attendance_pct=_float("SNAP_LOW_ATTENDANCE", 75.0),
        timezone=os.environ.get("SNAP_TIMEZONE", "Asia/Kolkata"),
        demo_mode=os.environ.get("SNAP_DEMO_MODE", "0").lower() in {"1", "true", "yes"},
        max_image_side=_int("SNAP_MAX_IMAGE_SIDE", 1800),
        upsample=_int("SNAP_UPSAMPLE", 1),
        min_face_score=_float("SNAP_MIN_FACE_SCORE", 0.25),
    )
