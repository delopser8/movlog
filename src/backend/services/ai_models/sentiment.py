'''
    servicio de análisis de sentimiento financiero con FinBERT (ProsusAI/finbert)
    - clasifica textos (positivo | neutral | negativo)
    - devuelve score de -1 a 1
    - usa Hugging Face Inference API
    - el texto debe estar en inglés (usar translation.py antes)
'''


import os
import time
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import httpx

from services.ai_models.observabilidad import trazar_sentimiento


MODEL_ID = "ProsusAI/finbert"
API_URL  = f"https://api-inference.huggingface.co/models/{MODEL_ID}"

LABEL_MAP = {
    "positive": ("positivo",  1.0),
    "neutral":  ("neutral",   0.0),
    "negative": ("negativo", -1.0),
}


def _headers() -> dict:
    from dotenv import load_dotenv
    load_dotenv()
    return {"Authorization": f"Bearer {os.getenv('HF_API_TOKEN', '')}"}

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=False,
)
def _llamar_api(texto: str) -> list | None:
    try:
        resp = httpx.post(
            API_URL,
            headers=_headers(),
            json={"inputs": texto[:512]},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.warning(f"FinBERT API error: {e}")
        return None

def analizar_sentimiento(texto_en_ingles: str, ticker: str = "") -> dict:
    # analiza el sentimiento de un texto financiero en inglés (return dict con: score (-1 a 1), tipo (positivo/neutral/negativo))
    resultado_default = {"score": 0.0, "tipo": "neutral"}

    if not texto_en_ingles or not texto_en_ingles.strip():
        return resultado_default

    t0 = time.time()
    data = _llamar_api(texto_en_ingles)
    latencia = (time.time() - t0) * 1000

    if not data:
        logger.warning("FinBERT: sin respuesta, usando neutral por defecto")
        return resultado_default

    try:
        predicciones = data[0] if isinstance(data[0], list) else data
        mejor = max(predicciones, key=lambda x: x["score"])
        label = mejor["label"].lower()
        confianza = mejor["score"]

        tipo, score_base = LABEL_MAP.get(label, ("neutral", 0.0))
        score = round(score_base * confianza, 4)

        resultado = {"score": score, "tipo": tipo}
        trazar_sentimiento(ticker, texto_en_ingles, resultado, latencia)

        logger.debug(f"FinBERT: {label} ({confianza:.2f}) → score {score:.2f}")
        return resultado

    except Exception as e:
        logger.warning(f"FinBERT: error parseando respuesta: {e}")
        return resultado_default

def analizar_batch(textos: list[str], ticker: str = "") -> list[dict]:
    # analiza el sentimiento de una lista de textos en inglés
    return [analizar_sentimiento(t, ticker) for t in textos]