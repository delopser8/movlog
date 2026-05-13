'''
    servicio del Cliente de Alpaca Markets
    - carga diaria del catálogo de assets negociables → (/db_data/alpaca_assets.json)
    - búsqueda de símbolos sobre alpaca_assets.json
'''

import os
import json
from pathlib import Path
from datetime import datetime

import schedule
import time
import threading
from loguru import logger
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetAssetsRequest
from alpaca.trading.enums import AssetClass, AssetStatus
from dotenv import load_dotenv


ALPACA_API_KEY    = os.getenv("ALPACA_API_KEY", "")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY", "")
ASSETS_PATH       = Path("db_data/alpaca_assets.json")


def _get_client() -> TradingClient:
    load_dotenv()
    api_key = os.getenv("ALPACA_API_KEY", "")
    secret_key = os.getenv("ALPACA_SECRET_KEY", "")
    return TradingClient(api_key, secret_key, paper=True)


# --- Carga de assets (catálogo de símbolos) ---
def cargar_assets() -> bool:
    # descarga todos los assets negociables de Alpaca y los guarda en disco
    try:
        client = _get_client()
        request = GetAssetsRequest(
            status=AssetStatus.ACTIVE,
            asset_class=AssetClass.US_EQUITY,
        )
        assets = client.get_all_assets(request)

        datos = [
            {
                "ticker": a.symbol,
                "nombre": a.name,
                "exchange": a.exchange.value if a.exchange else "—",
                "clase": a.asset_class.value,
            }
            for a in assets
            if a.tradable
        ]

        ASSETS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(ASSETS_PATH, "w") as f:
            json.dump({
                "actualizado": datetime.utcnow().isoformat(),
                "total": len(datos),
                "assets": datos,
            }, f)

        logger.info(f"Assets Alpaca cargados: {len(datos)} símbolos")
        return True

    except Exception as e:
        logger.error(f"Error cargando assets Alpaca: {e}")
        return False

def assets_disponibles() -> list[dict]:
    #lee la lista de assets desde disco
    if not ASSETS_PATH.exists():
        logger.warning("alpaca_assets.json no encontrado, ejecutando carga inicial")
        cargar_assets()

    try:
        with open(ASSETS_PATH) as f:
            data = json.load(f)
        return data.get("assets", [])
    except Exception as e:
        logger.error(f"Error leyendo alpaca_assets.json: {e}")
        return []

def buscar_assets(query: str, limite: int = 10) -> list[dict]:
    q = query.upper()
    assets = assets_disponibles()
    
    # 1. ticker empieza por q (más relevante)
    exactos = [a for a in assets if a["ticker"].startswith(q)]
    
    # 2. ticker contiene q pero no empieza por él
    contiene_ticker = [a for a in assets if q in a["ticker"] and not a["ticker"].startswith(q)]
    
    # 3. solo aparece en el nombre
    solo_nombre = [a for a in assets if q not in a["ticker"] and q in a["nombre"].upper()]
    
    resultados = exactos + contiene_ticker + solo_nombre
    return resultados[:limite]


# --- Schedule diario ---
def _schedule_loop():
    schedule.every().day.at("06:00").do(cargar_assets)
    logger.info("Schedule Alpaca assets: carga diaria a las 06:00 UTC")
    while True:
        schedule.run_pending()
        time.sleep(60)

def iniciar_schedule():
    if not ASSETS_PATH.exists() or ASSETS_PATH.stat().st_size == 0:
        logger.info("Carga inicial de assets Alpaca...")
        cargar_assets()

    hilo = threading.Thread(target=_schedule_loop, daemon=True, name="alpaca-schedule")
    hilo.start()
    logger.info("Schedule Alpaca iniciado")