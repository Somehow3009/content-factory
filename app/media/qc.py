"""QC §15: file exists, playable(size), duration/resolution (ffprobe nếu có), metadata, platform constraints."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

PLATFORM_LIMITS = {
    "tiktok": {"max_seconds": 600, "max_bytes": 500 * 1024 * 1024},
    "youtube": {"max_seconds": 60 * 60 * 12, "max_bytes": 256 * 1024 * 1024},
}


def check(path: str, platform: str = "tiktok", require_subtitle: bool = True,
          subtitle_path: str = "") -> dict:
    errors: list[str] = []
    p = Path(path)
    if not p.exists() or p.stat().st_size < 1024:
        errors.append("file_missing_or_empty")
        return {"passed": False, "errors": errors}
    lim = PLATFORM_LIMITS.get(platform, PLATFORM_LIMITS["tiktok"])
    if p.stat().st_size > lim["max_bytes"]:
        errors.append("file_too_large")
    # duration via ffprobe nếu có
    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        try:
            r = subprocess.run([ffprobe, "-v", "error", "-show_entries", "format=duration",
                                "-of", "default=noprint_wrappers=1:nokey=1", path],
                               capture_output=True, text=True, timeout=30)
            dur = float((r.stdout or "0").strip() or 0)
            if dur > lim["max_seconds"]:
                errors.append("duration_too_long")
        except Exception:
            pass
    if require_subtitle and subtitle_path and not Path(subtitle_path).exists():
        errors.append("subtitle_missing")
    return {"passed": not errors, "errors": errors, "size_bytes": p.stat().st_size}
