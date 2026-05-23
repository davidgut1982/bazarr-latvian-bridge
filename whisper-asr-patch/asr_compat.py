"""
/asr compatibility route for asr-transcription-lv.

Bazarr's WhisperAI provider POSTs to /asr with multipart form:
  - audio_file: binary audio
  - task: transcribe|translate
  - language: lv
  - output: srt
  - encode: false

The asr-transcription-lv service exposes POST /transcribe with different params.
This module adds a /asr route that accepts Bazarr's format and delegates to /transcribe.

Usage: import and include this router in asr-transcription-lv's main.py

    from asr_compat import router as asr_compat_router
    app.include_router(asr_compat_router)
"""

from fastapi import APIRouter

# TODO: implement
router = APIRouter()
