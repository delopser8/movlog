'''
    servicio de observabilidad de modelos IA con Langfuse
    - traza latencia y outputs de FinBERT y Qwen (traducción y explicabilidad)
    - permite auditar el pipeline de IA desde la UI de Langfuse
'''

import os
from loguru import logger

_client = None


def _get_client():
    global _client
    if _client is not None:
        return _client
    try:
        from langfuse import Langfuse
        from dotenv import load_dotenv
        load_dotenv()
        _client = Langfuse(
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY", ""),
            secret_key=os.getenv("LANGFUSE_SECRET_KEY", ""),
            host=os.getenv("LANGFUSE_HOST", "http://langfuse:3000"),
        )
        return _client
    except Exception as e:
        logger.warning(f"Langfuse no disponible: {e}")
        return None

def _registrar(modelo: str, tipo: str, input_texto: str, output, latencia_ms: float, ticker: str = ""):
    client = _get_client()
    if not client:
        return
    try:
        metadata = {"latencia_ms": round(latencia_ms, 2), "modelo": modelo}
        if ticker:
            metadata["ticker"] = ticker
        client.generation(
            name=f"movlog-{tipo}",
            model=modelo,
            input=input_texto[:1000],
            output=str(output)[:1000],
            metadata=metadata,
        )
    except Exception as e:
        logger.warning(f"Langfuse registro fallido: {e}")

def trazar_sentimiento(ticker: str, texto: str, resultado: dict, latencia_ms: float):
    _registrar("ProsusAI/finbert", "sentimiento", texto, resultado, latencia_ms, ticker)

def trazar_traduccion(texto_original: str, texto_traducido: str, latencia_ms: float):
    _registrar("qwen3.5:0.8b", "traduccion", texto_original, texto_traducido, latencia_ms)

def trazar_explicacion(ticker: str, prompt: str, explicacion: str, latencia_ms: float):
    _registrar("qwen3.5:0.8b", "explicacion", prompt, explicacion, latencia_ms, ticker)