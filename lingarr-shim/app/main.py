"""
Lingarr-protocol shim: bridges Bazarr's Lingarr translation requests to
the self-hosted NLLB-200 1.3B back-translator at 192.168.1.30:8104.

Bazarr -> POST /api/translate/content (Lingarr protocol, ISO 639-1 codes)
       -> POST /translate/batch (NLLB-200, FLORES-200 codes, max 64/batch)
"""

import logging
import os
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("lingarr-shim")

app = FastAPI(
    title="lingarr-shim",
    version="1.0.0",
    description="Lingarr-protocol adapter for NLLB-200 back-translator",
)

BACK_TRANSLATOR_URL = os.getenv("BACK_TRANSLATOR_URL", "http://192.168.1.30:8104")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "64"))
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "120"))

# ISO 639-1 (Bazarr) -> FLORES-200 (NLLB-200) language code mapping
# Covers all languages supported by NLLB-200 that Bazarr may send
ISO_TO_FLORES = {
    "af": "afr_Latn",
    "ak": "aka_Latn",
    "am": "amh_Ethi",
    "ar": "arb_Arab",
    "as": "asm_Beng",
    "ay": "ayr_Latn",
    "az": "azj_Latn",
    "bm": "bam_Latn",
    "be": "bel_Cyrl",
    "bn": "ben_Beng",
    "bho": "bho_Deva",
    "bs": "bos_Latn",
    "bg": "bul_Cyrl",
    "ca": "cat_Latn",
    "ceb": "ceb_Latn",
    "cs": "ces_Latn",
    "ckb": "ckb_Arab",
    "tt": "crh_Latn",
    "cy": "cym_Latn",
    "da": "dan_Latn",
    "de": "deu_Latn",
    "el": "ell_Grek",
    "en": "eng_Latn",
    "eo": "epo_Latn",
    "et": "est_Latn",
    "eu": "eus_Latn",
    "ee": "ewe_Latn",
    "fa": "pes_Arab",
    "fi": "fin_Latn",
    "fr": "fra_Latn",
    "gl": "glg_Latn",
    "gu": "guj_Gujr",
    "ha": "hau_Latn",
    "he": "heb_Hebr",
    "hi": "hin_Deva",
    "hr": "hrv_Latn",
    "hu": "hun_Latn",
    "hy": "hye_Armn",
    "id": "ind_Latn",
    "ig": "ibo_Latn",
    "ilo": "ilo_Latn",
    "is": "isl_Latn",
    "it": "ita_Latn",
    "ja": "jpn_Jpan",
    "jv": "jav_Latn",
    "ka": "kat_Geor",
    "kn": "kan_Knda",
    "km": "khm_Khmr",
    "ko": "kor_Hang",
    "lo": "lao_Laoo",
    "lt": "lit_Latn",
    "lv": "lvs_Latn",
    "lb": "ltz_Latn",
    "mk": "mkd_Cyrl",
    "mg": "plt_Latn",
    "ml": "mal_Mlym",
    "mr": "mar_Deva",
    "ms": "zsm_Latn",
    "mt": "mlt_Latn",
    "my": "mya_Mymr",
    "ne": "npi_Deva",
    "nl": "nld_Latn",
    "no": "nob_Latn",
    "ny": "nya_Latn",
    "om": "gaz_Latn",
    "or": "ory_Orya",
    "pa": "pan_Guru",
    "pl": "pol_Latn",
    "pt": "por_Latn",
    "pb": "por_Latn",
    "ro": "ron_Latn",
    "ru": "rus_Cyrl",
    "rw": "kin_Latn",
    "sa": "san_Deva",
    "si": "sin_Sinh",
    "sk": "slk_Latn",
    "sl": "slv_Latn",
    "sn": "sna_Latn",
    "so": "som_Latn",
    "sq": "als_Latn",
    "sr": "srp_Cyrl",
    "st": "sot_Latn",
    "su": "sun_Latn",
    "sv": "swe_Latn",
    "sw": "swh_Latn",
    "ta": "tam_Taml",
    "te": "tel_Telu",
    "tg": "tgk_Cyrl",
    "th": "tha_Thai",
    "ti": "tir_Ethi",
    "tk": "tuk_Latn",
    "tl": "fil_Latn",
    "tr": "tur_Latn",
    "uk": "ukr_Cyrl",
    "ur": "urd_Arab",
    "uz": "uzn_Latn",
    "vi": "vie_Latn",
    "wo": "wol_Latn",
    "xh": "xho_Latn",
    "yi": "ydd_Hebr",
    "yo": "yor_Latn",
    "zh": "zho_Hans",
    "zt": "zho_Hant",
    "zu": "zul_Latn",
}


def to_flores(iso_code: str) -> str:
    """Convert ISO 639-1 code to FLORES-200 code. Raises ValueError if unknown."""
    flores = ISO_TO_FLORES.get(iso_code.lower())
    if not flores:
        raise ValueError(f"Unknown ISO 639-1 language code: {iso_code!r}")
    return flores


class TranslateLine(BaseModel):
    position: int
    line: str


class TranslateRequest(BaseModel):
    arrMediaId: int | None = None
    title: str | None = None
    sourceLanguage: str
    targetLanguage: str
    mediaType: str | None = None
    lines: list[TranslateLine]


@app.get("/health")
def health():
    return {"status": "ok", "back_translator": BACK_TRANSLATOR_URL}


@app.post("/api/translate/content")
async def translate_content(req: TranslateRequest) -> list[dict[str, Any]]:
    if not req.lines:
        return []

    try:
        src_flores = to_flores(req.sourceLanguage)
        tgt_flores = to_flores(req.targetLanguage)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    logger.info(
        f"Translating {len(req.lines)} lines "
        f"{req.sourceLanguage}({src_flores}) -> {req.targetLanguage}({tgt_flores}) "
        f"for {req.title!r}"
    )

    # Split into batches of BATCH_SIZE (NLLB-200 hard limit: 64)
    positions = [entry.position for entry in req.lines]
    texts = [entry.line for entry in req.lines]
    translated: list[str] = []

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        for i in range(0, len(texts), BATCH_SIZE):
            chunk = texts[i : i + BATCH_SIZE]
            try:
                resp = await client.post(
                    f"{BACK_TRANSLATOR_URL}/translate/batch",
                    json={
                        "texts": chunk,
                        "source_lang": src_flores,
                        "target_lang": tgt_flores,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                batch_translations = data.get("translations", [])
                if len(batch_translations) != len(chunk):
                    raise ValueError(
                        f"Back-translator returned {len(batch_translations)} "
                        f"translations for {len(chunk)} inputs"
                    )
                translated.extend(batch_translations)
                logger.debug(f"Batch {i // BATCH_SIZE + 1}: {len(chunk)} lines translated")
            except httpx.HTTPError as e:
                logger.error(f"Back-translator HTTP error: {e}")
                raise HTTPException(status_code=502, detail=f"Back-translator error: {e}") from e

    # Reconstruct Lingarr-protocol response: [{position, line}]
    return [
        {"position": pos, "line": text} for pos, text in zip(positions, translated, strict=False)
    ]
