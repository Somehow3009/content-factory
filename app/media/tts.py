"""TTS §12: edge-tts free default + interface VoiceEngine. Fallback wav silent khi offline."""
from __future__ import annotations

import asyncio
import struct
import wave


async def _edge_synthesize(text: str, out_path: str, voice: str) -> str:
    import edge_tts
    tts = edge_tts.Communicate(text, voice)
    await tts.save(out_path)
    return out_path


def _silent_wav(out_path: str, seconds: int = 3) -> str:
    import pathlib
    pathlib.Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    framerate = 16000
    n = framerate * seconds
    with wave.open(out_path, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(framerate)
        w.writeframes(struct.pack("<" + "h" * n, *([0] * n)))
    return out_path


def synthesize(script: dict, out_path: str, voice: str = "vi-VN-HoaiMyNeural") -> str:
    text = " ".join([script.get("hook", ""), *script.get("body", []),
                     script.get("ending", ""), script.get("cta", "")])[:2000] or "Xin chào"
    try:
        asyncio.run(_edge_synthesize(text, out_path, voice))
    except Exception:
        _silent_wav(out_path)
    return out_path
