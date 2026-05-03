"""
Lingarr-protocol shim that bridges Bazarr's translation requests to a
custom Helsinki-NLP/NLLB translation service.

Bazarr -> POST /api/translate/content (Lingarr protocol, ISO lang codes)
  -> back-translator-lv -> POST /translate/batch (FLORES-200 codes)
"""
from fastapi import FastAPI
# TODO: implement
app = FastAPI(title="lingarr-shim")
