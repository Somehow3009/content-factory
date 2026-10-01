"""Video Engine §13-14: FFmpeg 9:16 1080x1920 + template + variants A/B/C.

- Source là video thật -> crop/scale 9:16 + voice + subtitle burn-in.
- Source không phải video (vd RSS chữ) -> sinh mp4 thật: nền màu + voice + subtitle
  (format voice-over-slideshow, §41: 1 content format). Không bao giờ ghi placeholder
  vì TikTok/YouTube từ chối file không phải video (file_format_check_failed).
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

TEMPLATES = {
    "9x16-default": {"aspect_ratio": "9:16", "resolution": "1080x1920", "fps": 30,
                     "subtitle": {"enabled": True, "position": "center-bottom"},
                     "voice": {"enabled": True}},
}

VARIANTS = [
    {"code": "A", "max_seconds": 60},
    {"code": "B", "max_seconds": 45},
    {"code": "C", "max_seconds": 30},
]


def _voice_seconds(voice_path: str, default: int) -> int:
    ffprobe = shutil.which("ffprobe")
    try:
        if ffprobe and Path(voice_path).exists():
            r = subprocess.run([ffprobe, "-v", "error", "-show_entries", "format=duration",
                                "-of", "default=noprint_wrappers=1:nokey=1", voice_path],
                               capture_output=True, text=True, timeout=30)
            return max(3, min(int(float((r.stdout or "0").strip() or 0)) + 1, default))
    except Exception:
        pass
    return default


def _esc_sub(path: str) -> str:
    # escape cho filter subtitles trên Windows (dấu \ : ')
    return path.replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


def render(source_path: str, voice_path: str, srt_path: str, out_path: str,
           template_id: str = "9x16-default", max_seconds: int = 60) -> str:
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg not found")
    # 1. source là video thật -> re-encode 9:16
    if Path(source_path).exists() and Path(source_path).stat().st_size > 4096:
        vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
        if Path(srt_path).exists():
            vf += f",subtitles='{_esc_sub(srt_path)}'"
        cmd = [ffmpeg, "-y", "-i", source_path, "-i", voice_path,
               "-filter:v", vf, "-t", str(max_seconds),
               "-c:v", "libx264", "-preset", "veryfast", "-c:a", "aac", "-shortest", out_path]
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=300)
            return out_path
        except Exception:
            pass  # source không decode được -> xuống slideshow
    # 2. slideshow thật: nền + voice + subtitle
    dur = _voice_seconds(voice_path, max_seconds)
    base = [ffmpeg, "-y", "-f", "lavfi", "-i", f"color=c=0x141414:s=1080x1920:d={dur}",
            "-i", voice_path, "-t", str(dur),
            "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-shortest", out_path]
    if Path(srt_path).exists():
        with_sub = base.copy()
        with_sub.insert(-5, "-vf")
        with_sub.insert(-5, f"subtitles='{_esc_sub(srt_path)}'")
        try:
            subprocess.run(with_sub, check=True, capture_output=True, timeout=300)
            return out_path
        except Exception:
            pass
    subprocess.run(base, check=True, capture_output=True, timeout=300)
    return out_path
