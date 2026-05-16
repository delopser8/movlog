'''
    servicio de explicabilidad de fluctuaciones con Qwen 3.5:0.8b (Ollama)
    - genera una explicación en español del movimiento brusco de un activo
    - se llama solo cuando hay fluctuación fuerte (trigger desde el pipeline)
    - recibe noticias del periodo y contexto del movimiento
'''


import os
import time
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import httpx

from services.ai_models.observabilidad import trazar_explicacion


OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")
MODEL       = "qwen3.5:0.8b"

PROMPT_TEMPLATE = '''Financial analyst. Stock: {ticker}. Price change: {var_pct:+.2f}% in 5 minutes.

News:
{noticias_texto}

Explain in Spanish why this happened (max 80 words):'''


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=3, max=15),
    retry=retry_if_exception_type(Exception),
    reraise=False,
)
def _llamar_ollama(prompt: str) -> str | None:
    try:
        resp = httpx.post(
            f"{OLLAMA_HOST}/api/generate",
            json={"model": MODEL, "prompt": prompt, "stream": False, "think": False},
            timeout=60, 
        )
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except Exception as e:
        logger.warning(f"Ollama explicabilidad error: {e}")
        return None

def generar_explicacion(ticker: str, var_pct: float, noticias: list[dict]) -> str | None:
    '''
        genera una explicación del movimiento brusco de un activo
        args:
            ticker,
            var_pct: variación porcentual del precio,
            noticias: lista de dicts con titulo y body de las noticias recientes
        return explicación en español o None si falla
    '''
    if not noticias:
        return None

    noticias_texto = "\n\n".join([
        f"- {n.get('titulo', '')}: {n.get('body', '')[:200]}"
        for n in noticias[:5]
    ])

    prompt = PROMPT_TEMPLATE.format(
        ticker=ticker,
        var_pct=var_pct,
        noticias_texto=noticias_texto,
    )

    logger.info(f"Generando explicación para {ticker} ({var_pct:+.2f}%)")
    t0 = time.time()
    explicacion = _llamar_ollama(prompt)
    latencia = (time.time() - t0) * 1000

    if explicacion:
        trazar_explicacion(ticker, prompt, explicacion, latencia)
        logger.info(f"Explicación generada para {ticker}")
        return explicacion

    logger.warning(f"No se pudo generar explicación para {ticker}")
    return None