'''
    servicio del Cliente de Alpaca Markets
    - carga diaria / al iniciar el entorno del catálogo de assets negociables → (/db_data/alpaca_assets.json)
    - búsqueda de símbolos sobre el catálogo de assets (alpaca_assets.json)
    - carga inicial de velas históricas (2 semanas, 1Min)
    - polling de velas en tiempo real (REST, sin WebSocket)
'''


import os
import json
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import schedule
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetAssetsRequest
from alpaca.trading.enums import AssetClass, AssetStatus
from alpaca.data.historical import StockHistoricalDataClient, CryptoHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, CryptoBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

from services.db.duckdb_client import (
    get_activo_id,
    insertar_velas,
    get_ultima_vela,
)


ALPACA_API_KEY    = os.getenv("ALPACA_API_KEY", "")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY", "")
ASSETS_PATH       = Path("db_data/alpaca_assets.json")

# intervalo de polling en segundos
POLLING_INTERVAL  = 15

# mapeo de timeframe string a objeto Alpaca TimeFrame
TIMEFRAME_MAP = {
    "1Min":   TimeFrame(1,  TimeFrameUnit.Minute),
    "5Min":   TimeFrame(5,  TimeFrameUnit.Minute),
    "1Day":   TimeFrame(1,  TimeFrameUnit.Day),
    "1Week":  TimeFrame(1,  TimeFrameUnit.Week),
    "1Month": TimeFrame(1,  TimeFrameUnit.Month),
}

HISTORICO_POR_TIMEFRAME = {
    "1Min":   14,
    "5Min":   60,
    "1Day":   365,
    "1Week":  1095,
    "1Month": 1825,
}

# --- Clientes ---
def _trading_client() -> TradingClient:
    from dotenv import load_dotenv
    load_dotenv()
    return TradingClient(
        os.getenv("ALPACA_API_KEY", ""),
        os.getenv("ALPACA_SECRET_KEY", ""),
        paper=True,
    )

def _stock_client() -> StockHistoricalDataClient:
    from dotenv import load_dotenv
    load_dotenv()
    return StockHistoricalDataClient(
        os.getenv("ALPACA_API_KEY", ""),
        os.getenv("ALPACA_SECRET_KEY", ""),
    )

def _crypto_client() -> CryptoHistoricalDataClient:
    from dotenv import load_dotenv
    load_dotenv()
    return CryptoHistoricalDataClient(
        os.getenv("ALPACA_API_KEY", ""),
        os.getenv("ALPACA_SECRET_KEY", ""),
    )

def _es_crypto(ticker: str) -> bool:
    # detecta si un ticker es crypto por la barra (BTC/USD) o consultando el catálogo
    if "/" in ticker:
        return True
    for a in assets_disponibles():
        if a["ticker"] == ticker:
            return a.get("clase") == "crypto"
    return False


# --- Assets (catálogo) ---
def cargar_assets() -> bool:
    # descarga el catálogo completo: US Equity (IEX, fractionable) + Crypto (tradable)
    try:
        client = _trading_client()

        # US Equity
        eq_request = GetAssetsRequest(
            status=AssetStatus.ACTIVE,
            asset_class=AssetClass.US_EQUITY,
        )
        equity_assets = client.get_all_assets(eq_request)

        # Crypto
        cr_request = GetAssetsRequest(
            status=AssetStatus.ACTIVE,
            asset_class=AssetClass.CRYPTO,
        )
        crypto_assets = client.get_all_assets(cr_request)

        datos = []

        for a in equity_assets:
            if a.tradable and a.fractionable:
                datos.append({
                    "ticker":       a.symbol,
                    "nombre":       a.name,
                    "exchange":     a.exchange.value if a.exchange else "--",
                    "clase":        "us_equity",
                    "fractionable": a.fractionable,
                })

        for a in crypto_assets:
            if a.tradable:
                datos.append({
                    "ticker":       a.symbol,
                    "nombre":       a.name,
                    "exchange":     a.exchange.value if a.exchange else "--",
                    "clase":        "crypto",
                    "fractionable": False,
                })

        ASSETS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(ASSETS_PATH, "w") as f:
            json.dump({
                "actualizado":  datetime.now().isoformat(),
                "total":        len(datos),
                "feed_fuente":  "Alpaca Market Data Free (IEX + Crypto)",
                "assets":       datos,
            }, f, indent=4)

        logger.info(f"Catálogo actualizado: {len(datos)} activos (equity + crypto)")
        return True

    except Exception as e:
        logger.error(f"Error cargando catálogo Alpaca: {e}")
        return False

def assets_disponibles() -> list[dict]:
    if not ASSETS_PATH.exists() or ASSETS_PATH.stat().st_size == 0:
        logger.warning("alpaca_assets.json no encontrado o vacío, cargando...")
        cargar_assets()
    try:
        with open(ASSETS_PATH) as f:
            return json.load(f).get("assets", [])
    except Exception as e:
        logger.error(f"Error leyendo alpaca_assets.json: {e}")
        return []

def buscar_assets(query: str, limite: int = 10) -> list[dict]:
    q = query.upper()
    assets = assets_disponibles()
    # para crypto (BTC/USD) también busca sin la barra (BTC)
    exactos         = [a for a in assets if a["ticker"].startswith(q) or a["ticker"].replace("/", "").startswith(q)]
    contiene_ticker = [a for a in assets if q in a["ticker"] and not a["ticker"].startswith(q)]
    solo_nombre     = [a for a in assets if q not in a["ticker"] and q in a["nombre"].upper()]
    return (exactos + contiene_ticker + solo_nombre)[:limite]


# --- Velas históricas ---
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=False,
)
def _fetch_bars(ticker: str, timeframe_str: str, inicio: datetime, fin: datetime) -> list[dict]:
    # descarga velas OHLC de Alpaca REST para un rango de fechas elegido
    # usa StockHistoricalDataClient (feed IEX) para equity y CryptoHistoricalDataClient para crypto
    tf = TIMEFRAME_MAP.get(timeframe_str)
    if not tf:
        logger.error(f"Timeframe desconocido: {timeframe_str}")
        return []

    try:
        if _es_crypto(ticker):
            client = _crypto_client()
            request = CryptoBarsRequest(
                symbol_or_symbols=ticker,
                timeframe=tf,
                start=inicio,
                end=fin,
            )
            bars = client.get_crypto_bars(request)
        else:
            client = _stock_client()
            request = StockBarsRequest(
                symbol_or_symbols=ticker,
                timeframe=tf,
                start=inicio,
                end=fin,
                feed="iex",
            )
            bars = client.get_stock_bars(request)

        data = bars.data.get(ticker, [])
        return [
            {
                "timestamp": bar.timestamp.replace(tzinfo=None),  # sin tz para DuckDB
                "timeframe": timeframe_str,
                "apertura":  float(bar.open),
                "maximo":    float(bar.high),
                "minimo":    float(bar.low),
                "cierre":    float(bar.close),
                "volumen":   int(bar.volume),
            }
            for bar in data
        ]

    except Exception as e:
        logger.warning(f"Error fetch_bars {ticker}: {e}")
        return []

def cargar_velas_iniciales(ticker: str, timeframe_str: str = "1Min") -> int:
    # carga las últimas 2 semanas de velas al añadir un activo al seguimiento (devuelve el número de velas insertadas)
    activo_id = get_activo_id(ticker)
    if activo_id is None:
        logger.error(f"cargar_velas_iniciales: activo_id no encontrado para {ticker}")
        return 0

    dias = HISTORICO_POR_TIMEFRAME.get(timeframe_str, 14)
    fin    = datetime.now(timezone.utc)
    inicio = fin - timedelta(days=dias)

    logger.info(f"Cargando velas iniciales {ticker} ({timeframe_str}): {inicio.date()} → {fin.date()}")
    velas = _fetch_bars(ticker, timeframe_str, inicio, fin)

    if not velas:
        logger.warning(f"Sin velas para {ticker} (puede ser fin de semana, after-hours o sin cobertura)")
        return 0

    insertadas = insertar_velas(activo_id, velas)
    logger.info(f"Velas iniciales insertadas: {ticker} → {insertadas}")
    return insertadas

def actualizar_velas(ticker: str, timeframe_str: str = "1Min") -> int:
    # polling: descarga las velas desde la última guardada hasta ahora
    # si no hay velas previas, carga las últimas 2 semanas
    activo_id = get_activo_id(ticker)
    if activo_id is None:
        return 0

    ultima = get_ultima_vela(ticker, timeframe_str)
    if ultima:
        inicio = ultima["timestamp"].replace(tzinfo=timezone.utc) + timedelta(seconds=1)
    else:
        inicio = datetime.now(timezone.utc) - timedelta(days=14)

    fin = datetime.now(timezone.utc)

    # si el mercado está cerrado (fin de semana / after-hours) Alpaca devuelve []
    if inicio >= fin:
        return 0

    velas = _fetch_bars(ticker, timeframe_str, inicio, fin)
    if not velas:
        return 0

    return insertar_velas(activo_id, velas)


# --- Polling en tiempo real ---
def _polling_loop(get_tickers_fn):
    # polling REST cada POLLING_INTERVAL segundos para todos los activos en seguimiento
    # get_tickers_fn: callable que devuelve la lista actual de tickers
    logger.info(f"Polling Alpaca iniciado (intervalo: {POLLING_INTERVAL}s)")
    while True:
        tickers = get_tickers_fn()
        for ticker in tickers:
            try:
                n = actualizar_velas(ticker, "1Min")
                if n > 0:
                    logger.debug(f"Polling: {ticker} → {n} velas nuevas")
            except Exception as e:
                logger.warning(f"Polling error {ticker}: {e}")
        time.sleep(POLLING_INTERVAL)

def iniciar_polling(get_tickers_fn):
    # arranca el polling en un thread daemon
    hilo = threading.Thread(
        target=_polling_loop,
        args=(get_tickers_fn,),
        daemon=True,
        name="alpaca-polling",
    )
    hilo.start()
    logger.info("Polling Alpaca iniciado")


# --- Schedule diario de assets ---
def _schedule_loop():
    schedule.every().day.at("06:00").do(cargar_assets)
    logger.info("Schedule Alpaca assets: carga diaria a las 06:00 UTC")
    while True:
        schedule.run_pending()
        time.sleep(60)

def iniciar_schedule():
    # arranca el schedule de assets y el polling
    if not ASSETS_PATH.exists() or ASSETS_PATH.stat().st_size == 0:
        logger.info("Carga inicial de assets Alpaca...")
        cargar_assets()

    hilo = threading.Thread(target=_schedule_loop, daemon=True, name="alpaca-schedule")
    hilo.start()
    logger.info("Schedule Alpaca iniciado")