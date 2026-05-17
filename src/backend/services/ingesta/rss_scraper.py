'''
    servicio scraper de Yahoo Finance RSS
    - scraping periódico de noticias financieras por ticker
    - guardado en noticias_historial en DuckDB
'''


import hashlib
import threading
import time
from datetime import datetime
from email.utils import parsedate_to_datetime

import feedparser
from loguru import logger

from services.db.duckdb_client import insertar_noticia


POLLING_INTERVAL = 300  # (5 minutos)
RSS_BASE_URL     = "https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"


# --- Helpers ---
def _noticia_id(titulo: str) -> str:
    return hashlib.md5(titulo.encode()).hexdigest()

def _parse_fecha(entry) -> datetime:
    try:
        if hasattr(entry, "published"):
            return parsedate_to_datetime(entry.published).replace(tzinfo=None)
    except Exception:
        pass
    return datetime.now()


# --- Fetch ---
def fetch_y_guardar(ticker: str) -> int:
    # scraping del feed RSS de Yahoo Finance para un ticker (return número de noticias insertadas)
    # Yahoo Finance RSS usa el ticker directamente sin normalización
    url = RSS_BASE_URL.format(ticker=ticker)
    try:
        feed = feedparser.parse(url)
        if feed.bozo and not feed.entries:
            logger.warning(f"RSS Yahoo Finance: feed vacío o error para {ticker}")
            return 0

        insertadas = 0
        for entry in feed.entries:
            titulo = entry.get("title", "").strip()
            if not titulo:
                continue

            noticia = {
                "noticia_id":    _noticia_id(titulo),
                "titulo":        titulo,
                "url":           entry.get("link", ""),
                "origen":        "Yahoo Finance RSS",
                "body":          entry.get("summary", ""),
                "fecha_noticia": _parse_fecha(entry),
            }
            if insertar_noticia(noticia):
                insertadas += 1

        if insertadas > 0:
            logger.info(f"RSS Yahoo Finance: {ticker} → {insertadas} noticias nuevas")
        return insertadas

    except Exception as e:
        logger.warning(f"RSS Yahoo Finance error {ticker}: {e}")
        return 0


# --- Polling loop ---
def _polling_loop(get_tickers_fn):
    logger.info(f"Polling RSS Yahoo Finance iniciado (intervalo: {POLLING_INTERVAL}s)")
    while True:
        tickers = get_tickers_fn()
        for ticker in tickers:
            try:
                fetch_y_guardar(ticker)
                time.sleep(1)
            except Exception as e:
                logger.warning(f"RSS polling error {ticker}: {e}")
        time.sleep(POLLING_INTERVAL)

def iniciar_polling(get_tickers_fn):
    # arranca el polling de noticias en un thread daemon
    hilo = threading.Thread(
        target=_polling_loop,
        args=(get_tickers_fn,),
        daemon=True,
        name="rss-polling",
    )
    hilo.start()
    logger.info("Polling RSS Yahoo Finance iniciado")