"""Content Intelligence §10-11: transcript -> summary -> script VI voice-ready + hook/caption/hashtags.

MVP: rule-based + LLM-provider hook (khi có LLM_API_KEY sẽ gọi, chưa có thì template).
Không gọi LLM 1 lần làm mọi thứ — tách hàm rõ ràng.
"""
from __future__ import annotations

import json
import os

HOOK_STYLES = [
    "Bạn có biết...",
    "Điều này thực sự kỳ lạ...",
    "Ít người biết rằng...",
]


def summarize(transcript: dict, max_points: int = 3) -> dict:
    segs = transcript.get("segments", [])
    full = " ".join(s.get("text", "") for s in segs)[:2000]
    # MVP extractive: lấy N câu đầu làm key points
    points = [s.get("text", "") for s in segs[:max_points] if s.get("text")]
    return {"summary": full[:500], "key_points": points}


def localize_to_vi(summary: dict) -> dict:
    """SOURCE MEANING -> VI CONTEXT -> NATURAL SCRIPT. Dùng Gemini khi có key, fallback template."""
    points = summary.get("key_points", []) or [summary.get("summary", "")]
    try:
        from app.config.settings import settings
        if settings.llm_api_key:
            import httpx
            prompt = ("Chuyển nội dung sau thành kịch bản video ngắn tiếng Việt tự nhiên, "
                      "giọng nói ngắn gọn dễ nghe, giữ ý chính, có hook rõ. "
                      "Trả về JSON đúng format {\"hook\":...,\"body\":[3 câu],\"ending\":...,\"cta\":...}. "
                      f"Nội dung: {' | '.join(points)[:1500]}")
            r = httpx.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{settings.llm_model}:generateContent?key={settings.llm_api_key}",
                json={"contents": [{"parts": [{"text": prompt}]}],
                      "generationConfig": {"responseMimeType": "application/json"}},
                timeout=60)
            r.raise_for_status()
            txt = r.json()["candidates"][0]["content"]["parts"][0]["text"]
            data = json.loads(txt)
            if "hook" in data and "body" in data:
                data.setdefault("ending", "Đó là toàn bộ nội dung đáng chú ý.")
                data.setdefault("cta", "Follow kênh để xem thêm!")
                data.setdefault("estimated_seconds", 42)
                return data
    except Exception:
        pass
    body = [f"Ý chính {i+1}: {p[:200]}" for i, p in enumerate(points[:3])]
    return {
        "hook": HOOK_STYLES[0] + " " + (points[0][:120] if points else "xem hết video này"),
        "body": body,
        "ending": "Đó là toàn bộ nội dung đáng chú ý.",
        "cta": "Follow kênh để xem thêm!",
        "estimated_seconds": 42,
    }


def build_caption(script: dict) -> dict:
    hook = script.get("hook", "")
    return {
        "caption": f"{hook}\n\nXem full giải thích trong video 👇",
        "hashtags": ["#shorts", "#kienthuc", "#xuhuong", "#vietnam"],
    }


def save_script_files(content_id: str, script: dict) -> dict:
    from app.media.storage import put_bytes
    key = f"content/{content_id}/script/vi.json"
    put_bytes(key, json.dumps(script, ensure_ascii=False, indent=2).encode("utf-8"),
              content_type="application/json")
    return {"storage_key": key}
