'''
    cliente de NewsAPI
    - polling periódico de noticias financieras por ticker
    - guardado en noticias_historial en DuckDB
'''


import os
import hashlib
import threading
import time
from datetime import datetime, timedelta

import schedule
from newsapi import NewsApiClient
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from services.db.duckdb_client import insertar_noticia


NEWSAPI_KEY      = os.getenv("NEWSAPI_KEY", "")
POLLING_INTERVAL = 300  # (5 minutos)


# --- Cliente ---
def _get_client() -> NewsApiClient:
    from dotenv import load_dotenv
    load_dotenv()
    return NewsApiClient(api_key=os.getenv("NEWSAPI_KEY", ""))


# --- Helpers ---
def _noticia_id(titulo: str) -> str:
    # hash del título para evitar duplicados
    return hashlib.md5(titulo.encode()).hexdigest()


# --- Fetch de noticias ---
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=False,
)
def _fetch_noticias(query: str, desde: datetime) -> list[dict]:
    client = _get_client()
    try:
        resp = client.get_everything(
            q=query,
            language="en",
            sort_by="publishedAt",
            page_size=20,
        )
        articulos = resp.get("articles", [])
        return [
            {
                "noticia_id":    _noticia_id(a["title"]),
                "titulo":        a["title"],
                "url":           a.get("url", ""),
                "origen":        a.get("source", {}).get("name", "NewsAPI"),
                "body":          a.get("description") or a.get("content") or "",
                "fecha_noticia": datetime.strptime(
                    a["publishedAt"], "%Y-%m-%dT%H:%M:%SZ"
                ) if a.get("publishedAt") else datetime.utcnow(),
            }
            for a in articulos
            if a.get("title") and a["title"] != "[Removed]"
        ]
    except Exception as e:
        logger.warning(f"NewsAPI fetch fallido para '{query}': {e}")
        return []

def fetch_y_guardar(ticker: str) -> int:
    # descarga noticias del último intervalo de polling para un ticker y las guarda en DuckDB
    # usa el nombre del activo desde DuckDB como query
    from services.db.duckdb_client import get_activo_detalles
    detalles = get_activo_detalles(ticker)
    if detalles and detalles.get("nombre"):
        query = detalles["nombre"].split()[0] 
    else:
        query = ticker.split(".")[0].split("/")[0]  

    desde = datetime.utcnow() - timedelta(seconds=POLLING_INTERVAL + 60)
    noticias = _fetch_noticias(query, desde)

    if not noticias:
        return 0

    insertadas = 0
    for n in noticias:
        if insertar_noticia(n):
            insertadas += 1

    if insertadas > 0:
        logger.info(f"NewsAPI: {ticker} ({query}) → {insertadas} noticias nuevas")
    return insertadas


# --- Polling loop ---
def _polling_loop(get_tickers_fn):
    logger.info(f"Polling NewsAPI iniciado (intervalo: {POLLING_INTERVAL}s)")
    while True:
        tickers = get_tickers_fn()
        for ticker in tickers:
            try:
                fetch_y_guardar(ticker)
                time.sleep(2)  # evitar rate limiting entre tickers
            except Exception as e:
                logger.warning(f"NewsAPI polling error {ticker}: {e}")
        time.sleep(POLLING_INTERVAL)

def iniciar_polling(get_tickers_fn):
    # arranca el polling de noticias en un thread daemon
    hilo = threading.Thread(
        target=_polling_loop,
        args=(get_tickers_fn,),
        daemon=True,
        name="newsapi-polling",
    )
    hilo.start()
    logger.info("Polling NewsAPI iniciado")
