'''
    servicio de traducción de textos al inglés usando Qwen 3.5:0.8b (Ollama)
    - detecta si el texto está en inglés o no (basado en palabras comunes)
    - traduce si es necesario (FinBERT solo funciona en inglés)
'''


import os
import time
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import httpx

from services.ai_models.observabilidad import trazar_traduccion


OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")
MODEL = "qwen3.5:0.8b"

_ES = {"que", "los", "las", "del", "una", "por", "con", "para", "como", "este", "esta", "pero", "más", "también"}
_FR = {"les", "des", "une", "dans", "pour", "avec", "sur", "qui", "est", "pas", "mais", "plus", "tout"}
_DE = {"die", "der", "das", "und", "ist", "von", "mit", "dem", "den", "ein", "eine", "nicht", "auch"}
_PT = {"que", "não", "para", "uma", "com", "dos", "pelo", "pela", "mais", "também", "são", "está"}


def _detectar_idioma(texto: str) -> str:
    palabras = set(texto.lower().split())
    scores = {
        "es": len(palabras & _ES),
        "fr": len(palabras & _FR),
        "de": len(palabras & _DE),
        "pt": len(palabras & _PT),
    }
    mejor = max(scores, key=scores.get)
    return mejor if scores[mejor] >= 2 else "en"


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=2, max=8),
    retry=retry_if_exception_type(Exception),
    reraise=False,
)
def _llamar_ollama(texto: str) -> str | None:
    prompt = (
        "Translate the following text to English. "
        "Be concise, keep the meaning intact, maximum 150 words. "
        "Return only the translation, nothing else:\n\n"
        f"{texto}"
    )
    try:
        resp = httpx.post(
            f"{OLLAMA_HOST}/api/generate",
            json={"model": MODEL, "prompt": prompt, "stream": False},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except Exception as e:
        logger.warning(f"Ollama traducción error: {e}")
        return None

def traducir_si_necesario(texto: str) -> str:
    if not texto or not texto.strip():
        return texto

    idioma = _detectar_idioma(texto)
    if idioma == "en":
        return texto

    logger.info(f"Traduciendo de {idioma} a inglés ({len(texto)} chars)")
    t0 = time.time()
    traducido = _llamar_ollama(texto) 
    latencia = (time.time() - t0) * 1000

    if traducido:
        trazar_traduccion(texto, traducido, latencia)
        logger.info("Traducción completada")
        return traducido

    logger.warning("Traducción fallida, usando texto original")
    return texto