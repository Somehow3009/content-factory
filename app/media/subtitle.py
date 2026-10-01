"""Subtitle §13: segments + script -> vi.srt (giữ timestamp §9)."""
from __future__ import annotations


def _fmt(t: float) -> str:
    ms = int(t * 1000)
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def to_srt(segments: list[dict]) -> str:
    out = []
    for i, s in enumerate(segments, 1):
        out.append(f"{i}\n{_fmt(float(s.get('start', 0)))} --> {_fmt(float(s.get('end', 1)))}\n{s.get('text','')}\n")
    return "\n".join(out)


def script_to_srt(script: dict, total_seconds: float = 42) -> str:
    lines = [script.get("hook", "")] + list(script.get("body", [])) + [script.get("ending", "")]
    lines = [x for x in lines if x]
    per = max(total_seconds / max(len(lines), 1), 1.0)
    segs = [{"start": i * per, "end": (i + 1) * per, "text": t} for i, t in enumerate(lines)]
    return to_srt(segs)
