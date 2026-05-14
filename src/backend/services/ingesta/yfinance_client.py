'''
    servicio del cliente de yfinance
    - carga de detalles del activo al añadirlo al seguimiento
    - schedule diario de actualización de detalles
'''


import threading
import time
from datetime import datetime
import re

import schedule
import yfinance as yf
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from services.db.duckdb_client import upsert_activo_detalles


# --- Helpers ---
def _safe_float(val) -> float | None:
    try:
        f = float(val)
        return None if (f != f) else f  # NaN check
    except (TypeError, ValueError):
        return None

def _recomendar(info: dict) -> str:
    # mapea la recomendación de analistas de yfinance a compra | holdea | vende
    rec = (info.get("recommendationKey") or "").lower()
    mapping = {
        "strong_buy": "compra",
        "buy": "compra",
        "hold": "holdea",
        "underperform": "vende",
        "sell": "vende",
        "strong_sell": "vende",
    }
    return mapping.get(rec, "holdea")


# --- Carga de detalles ---
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def _fetch_info(ticker: str) -> dict:
    return yf.Ticker(ticker).info

def _fetch_historico(ticker_yf: str) -> dict:
    # obtiene cierres ajustados, aperturas, máximos y mínimos por periodo
    t = yf.Ticker(ticker_yf)
    datos = {}

    try:
        hist_d = t.history(period="5d",  interval="1d")
        hist_w = t.history(period="1mo", interval="1wk")
        hist_m = t.history(period="6mo", interval="1mo")

        if not hist_d.empty:
            datos["cierre_ajustado_diario"] = _safe_float(hist_d["Close"].iloc[-1])
            datos["apertura_diaria"]        = _safe_float(hist_d["Open"].iloc[-1])
            datos["maximo_diario"]          = _safe_float(hist_d["High"].iloc[-1])
            datos["minimo_diario"]          = _safe_float(hist_d["Low"].iloc[-1])

        if not hist_w.empty:
            datos["cierre_ajustado_semanal"] = _safe_float(hist_w["Close"].iloc[-1])
            datos["apertura_semanal"]        = _safe_float(hist_w["Open"].iloc[-1])
            datos["maximo_semanal"]          = _safe_float(hist_w["High"].iloc[-1])
            datos["minimo_semanal"]          = _safe_float(hist_w["Low"].iloc[-1])

        if not hist_m.empty:
            datos["cierre_ajustado_mensual"] = _safe_float(hist_m["Close"].iloc[-1])
            datos["apertura_mensual"]        = _safe_float(hist_m["Open"].iloc[-1])
            datos["maximo_mensual"]          = _safe_float(hist_m["High"].iloc[-1])
            datos["minimo_mensual"]          = _safe_float(hist_m["Low"].iloc[-1])

    except Exception as e:
        logger.warning(f"yfinance histórico fallido para {ticker_yf}: {e}")

    return datos

def _normalizar_ticker_yf(ticker: str) -> str:
    # convierte ticker Alpaca a formato yfinance
        # (BRK.B → BRK-B)
        # (BTC/USD → BTC-USD)
    return ticker.replace(".", "-").replace("/", "-")

def cargar_detalles_activo(ticker: str) -> dict | None:
    # carga los detalles completos de un activo desde yfinance y los persiste en DuckDB
    # devuelve el dict de detalles o None si falla
    try:
        ticker_yf = _normalizar_ticker_yf(ticker)
        logger.info(f"Cargando detalles yfinance: {ticker} (yf: {ticker_yf})")
        info = _fetch_info(ticker_yf)

        if not info or not (info.get("shortName") or info.get("longName") or info.get("symbol")):
            logger.warning(f"yfinance no devolvió datos válidos para {ticker}")
            return None

        historico = _fetch_historico(ticker_yf)

        # URL limpia
        website = info.get("website", "") or ""
        url = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', website) # RegEx por si viene en formato Markdown
        url = url.replace("https://", "").replace("http://", "").rstrip("/")

        datos = {
            "ticker":   ticker,
            "clase":    "crypto" if "/" in ticker else "us_equity",
            "nombre":   info.get("longName") or info.get("shortName") or ticker,
            "sector":   info.get("sector")   or "--",
            "industria":info.get("industry") or "--",
            "url":      url or "--",

            # fundamentales
            "ratio_pe":      _safe_float(info.get("trailingPE")),
            "eps":           _safe_float(info.get("trailingEps")),
            "market_cap":    _safe_float(info.get("marketCap")),
            "dividend_yield":_safe_float(info.get("dividendYield")),
            "esg_score":     _safe_float(info.get("totalEsg")),

            # recomendación
            "operacion_recomendada": _recomendar(info),
            "target_price": _safe_float(info.get("targetMeanPrice")),

            **historico,
        }

        activo_id = upsert_activo_detalles(datos)
        datos["activo_id"] = activo_id
        logger.info(f"Detalles guardados: {ticker} (activo_id={activo_id})")
        return datos

    except Exception as e:
        logger.error(f"Error cargando detalles de {ticker}: {e}")
        return None


# --- Schedule diario ---
def _actualizar_todos(tickers: list[str]):
    # actualiza los detalles de todos los activos en seguimiento
    logger.info(f"Schedule diario yfinance: actualizando {len(tickers)} activos")
    for ticker in tickers:
        cargar_detalles_activo(ticker)
        time.sleep(1)  # evitar rate limiting

def _schedule_loop(get_tickers_fn):
    # ejecuta el schedule diario
    # get_tickers_fn: callable que devuelve la lista actual de tickers en seguimiento
    schedule.every().day.at("07:00").do(
        lambda: _actualizar_todos(get_tickers_fn())
    )
    logger.info("Schedule yfinance: actualización diaria a las 07:00 UTC")
    while True:
        schedule.run_pending()
        time.sleep(60)

def iniciar_schedule(get_tickers_fn):
    # arranca el schedule diario en un thread daemon
    # get_tickers_fn: callable que devuelve la lista de tickers activos (se evalúa en cada ejecución)
    hilo = threading.Thread(
        target=_schedule_loop,
        args=(get_tickers_fn,),
        daemon=True,
        name="yfinance-schedule",
    )
    hilo.start()
    logger.info("Schedule yfinance iniciado")