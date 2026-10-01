---
title: Content Factory
emoji: 🏭
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
---

# Content Factory — MVP v1.0

Cloud-first: laptop chỉ dev, production chạy Cloud (spec §55 Principle 7).

## Công nghệ đã chốt (cho phép tùy biến, spec cho phép)

| Lớp | Chọn cho MVP | Vì sao | Thay thế được |
|---|---|---|---|
| App | Python 3.12 + FastAPI + SQLAlchemy 2.0 + Pydantic v2 + httpx | đúng spec §3 | — |
| DB | Postgres prod (Neon/Supabase free) + SQLite local, cùng SQLAlchemy URL | zero-cost local, prod serverless | — |
| Storage | S3-compatible `boto3` → R2 prod, MinIO local | R2 free 10GB + no egress (§3.2) | AWS S3 |
| Queue | **DB-backed `jobs` table, không Redis** | 0 chi phí, đủ MVP, `SKIP LOCKED` claim | Redis/Celery sau |
| Scheduler | APScheduler (chỉ `CREATE JOB`) | tách control/data plane (§4, §32) | Cloud Scheduler |
| Worker | Docker `python:3.12-slim + ffmpeg`, `python -m app.jobs.worker` → Cloud Run Jobs | stateless (§23-24) | Fly Machines |
| Transcribe | `faster-whisper` local trong worker + interface `Transcriber` | free, giữ timestamp (§9) | Whisper API |
| LLM | abstraction `LLM_PROVIDER/LLM_MODEL`, default `gemini-1.5-flash` free | không lock-in (§3.1) | Groq/OpenRouter |
| TTS | `edge-tts` `vi-VN-HoaiMyNeural` free + interface `VoiceEngine` | free, voice-ready (§11-12) | Azure/Google |
| Video | FFmpeg CLI + template JSON 1080x1920 | core (§13) | — |
| Deploy control | Fly.io/Render/Cloud Run | free tier | Workers/Pages cho dashboard tĩnh |
| CI | GitHub Actions | 2000 phút/tháng (§3.2) | — |

Heavy compute **không bao giờ** chạy trong API (§55-P6).

## Chạy local

```powershell
Copy-Item .env.example .env
docker compose up --build
# API: http://localhost:8000/health
# MinIO: http://localhost:9001
```

Không Docker:

```powershell
pip install -r requirements.txt
uvicorn app.main:app --reload
python -m app.jobs.worker
```

## Sprint 1 (done scaffold)
FastAPI, settings, DB models (9 bảng §39), queue + worker + retry + idempotency, storage signed URL, encryption skeleton, Docker + compose.
