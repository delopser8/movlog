'''
    este es el único servicio que gestiona las llamadas HTTP del Frontend con el Backend
'''


import os
import httpx
from loguru import logger
from urllib.parse import quote

FASTAPI_URL = os.getenv("FASTAPI_URL", "http://localhost:8000")

# --- Helpers de llamadas HTTP al backend ---
def _get(endpoint: str, params: dict = {}) -> list | dict | None:
    try:
        r = httpx.get(f"{FASTAPI_URL}/api{endpoint}", params=params, timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.error(f"GET {endpoint}: {e}")
        return None

def _post(endpoint: str, body: dict) -> dict | None:
    try:
        r = httpx.post(f"{FASTAPI_URL}/api{endpoint}", json=body, timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.error(f"POST {endpoint}: {e}")
        return None

def _delete(endpoint: str) -> dict | None:
    try:
        r = httpx.delete(f"{FASTAPI_URL}/api{endpoint}", timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.error(f"DELETE {endpoint}: {e}")
        return None


# --- Assets (carga del catálogo de símbolos) ---
def buscar_assets(query: str, limite: int = 10) -> list[dict]:
    resultado = _get("/assets/search", {"q": query, "limite": limite})
    return resultado if isinstance(resultado, list) else []


# --- Seguimientos ---
def listar_seguimientos() -> list[dict]:
    resultado = _get("/seguimientos")
    return resultado if isinstance(resultado, list) else []

def añadir_seguimiento(ticker: str, nombre: str) -> bool:
    resultado = _post("/seguimientos", {"ticker": ticker, "nombre": nombre})
    return bool(resultado and resultado.get("ok"))

def eliminar_seguimiento(ticker: str) -> bool:
    ticker_encoded = quote(ticker, safe="")
    resultado = _delete(f"/seguimientos/{ticker_encoded}")
    return bool(resultado and resultado.get("ok"))


# --- Detalles y velas ---
def get_detalles(ticker: str) -> dict | None:
    ticker_encoded = quote(ticker, safe="")
    return _get(f"/activos/{ticker_encoded}/detalles")

def get_velas(ticker: str, timeframe: str = "1Min", limite: int = 500) -> list[dict]:
    ticker_encoded = quote(ticker, safe="")
    resultado = _get(f"/activos/{ticker_encoded}/velas", {"timeframe": timeframe, "limite": limite})
    return resultado if isinstance(resultado, list) else []


# --- Noticias ---
def get_noticias(ticker: str, limite: int = 20) -> list[dict]:
    resultado = _get(f"/activos/{quote(ticker, safe='')}/noticias", {"limite": limite})
    return resultado if isinstance(resultado, list) else []

def get_fluctuaciones(ticker: str, limite: int = 10) -> list[dict]:
    resultado = _get(f"/activos/{quote(ticker, safe='')}/fluctuaciones", {"limite": limite})
    return resultado if isinstance(resultado, list) else []


# --- Infraestructura (sección) ---
def get_infra_stats() -> dict:
    return _get("/infra/stats") or {}

