# whisper-asr-patch

Adds a `/asr` compatibility route to the `asr-transcription-lv` Whisper service so Bazarr's WhisperAI provider can communicate with it.

## The Problem

Bazarr's WhisperAI provider sends:
```
POST /asr
Content-Type: multipart/form-data

audio_file: <binary>
task: transcribe | translate
language: lv
output: srt
encode: false
```

The `asr-transcription-lv` service exposes `POST /transcribe` with different parameters.

## The Fix

`asr_compat.py` provides a FastAPI `APIRouter` with a `/asr` endpoint that:
1. Accepts Bazarr's multipart form format
2. Translates parameters to what `asr-transcription-lv` expects
3. Delegates to the existing `/transcribe` handler
4. Returns the response in the format Bazarr expects

## Installation

On `latvian-vm`, in the `asr-transcription-lv` project directory:

```bash
# Copy the compat module
cp asr_compat.py /path/to/asr-transcription-lv/

# In asr-transcription-lv's main.py, add these two lines:
#   from asr_compat import router as asr_compat_router
#   app.include_router(asr_compat_router)

# Restart the service (example with systemd)
sudo systemctl restart asr-transcription-lv
# or with PM2:
pm2 restart asr-transcription-lv
```

## Verification

```bash
# Check the /asr route is registered
curl http://192.168.1.11:9000/docs

# Test with a sample audio file
curl -X POST http://192.168.1.11:9000/asr \
  -F "audio_file=@test.wav" \
  -F "task=transcribe" \
  -F "language=lv" \
  -F "output=srt"
```
