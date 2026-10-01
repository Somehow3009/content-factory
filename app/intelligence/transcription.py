"""Transcription §9: faster-whisper khi có model, fallback mock giữ timestamp."""
from __future__ import annotations


class Transcriber:
    def __init__(self, model: str = "tiny"):
        self.model = model
        self._impl = None

    def _load(self):
        if self._impl is not None:
            return self._impl
        try:
            from faster_whisper import WhisperModel
            self._impl = WhisperModel(self.model)
        except Exception:
            self._impl = False
        return self._impl

    def transcribe_file(self, path: str) -> dict:
        try:
            impl = self._load()
            if impl:
                segments, info = impl.transcribe(path)
                segs = [{"start": float(s.start), "end": float(s.end), "text": s.text}
                        for s in segments]
                if segs:
                    return {"language": info.language, "segments": segs}
        except Exception:
            pass  # file không phải audio/video thật (vd HTML) -> mock để pipeline chạy
        # mock: 1 segment để pipeline MVP vẫn chạy khi chưa có model/ffmpeg
        return {"language": "unknown",
                "segments": [{"start": 0.0, "end": 5.0, "text": f"[transcript-placeholder] {path}"}]}


def transcribe_content(content_id: str, source_path: str) -> dict:
    return Transcriber().transcribe_file(source_path)
