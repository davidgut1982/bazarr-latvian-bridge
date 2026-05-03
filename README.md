# bazarr-latvian-bridge

Bridge services connecting [Bazarr](https://www.bazarr.media/) to self-hosted Latvian ASR and translation services running on `latvian-vm` (192.168.1.11).

## Prerequisites

- Docker and Docker Compose (for lingarr-shim)
- Network access to `latvian-vm` at `192.168.1.11`
- `back-translator-lv` service running on `latvian-vm:8104`
- `asr-transcription-lv` service running on `latvian-vm:9000`

## Services

### 1. lingarr-shim

A FastAPI service that speaks Bazarr's Lingarr translation protocol but calls the custom Helsinki-NLP/NLLB translation service (`back-translator-lv`) on latvian-vm.

**The mismatch it solves:**
- Bazarr sends ISO language codes (`lv`, `en`) to the Lingarr endpoint
- `back-translator-lv` expects FLORES-200 codes (`lav_Latn`, `eng_Latn`)
- lingarr-shim maps between them

**Setup:**

```bash
cd lingarr-shim
cp .env.example .env
# Edit .env if your back-translator-lv runs on a different host/port

# From repo root:
docker compose up -d lingarr-shim
```

Then configure Bazarr:
- Provider: Lingarr
- URL: `http://<this-host>:8200`

### 2. whisper-asr-patch

A small patch for the `asr-transcription-lv` Whisper service on latvian-vm. Adds a `/asr` compatibility route so Bazarr's WhisperAI provider can communicate with the existing service.

**The mismatch it solves:**
- Bazarr's WhisperAI provider POSTs to `/asr`
- `asr-transcription-lv` exposes `POST /transcribe`
- The patch adds a `/asr` route that accepts Bazarr's format and delegates to `/transcribe`

**Setup:**

On `latvian-vm`, in the `asr-transcription-lv` project:

```bash
# Copy asr_compat.py into the service directory
cp whisper-asr-patch/asr_compat.py /path/to/asr-transcription-lv/

# In asr-transcription-lv's main.py, add:
# from asr_compat import router as asr_compat_router
# app.include_router(asr_compat_router)

# Restart the service
```

Then configure Bazarr:
- Provider: WhisperAI
- Endpoint: `http://192.168.1.11:9000`
