'''
    funciones handler de cada endpoint + llamada a servicios correspondientes
'''


from loguru import logger
from services.ingesta.alpaca_client import buscar_assets
from services.db.mongodb_client import (
    activos_elegidos_listar,
    activos_elegidos_añadir,
    activos_elegidos_eliminar,
)


# --- Assets (carga del catálogo de símbolos) ---
def ctrl_buscar_assets(query: str, limite: int = 10) -> list[dict]:
    if not query or len(query) < 1:
        return []
    return buscar_assets(query, limite)


# --- Seguimientos ---
def ctrl_listar_seguimientos() -> list[dict]:
    return activos_elegidos_listar()

def ctrl_añadir_seguimiento(ticker: str, nombre: str) -> dict:
    ok = activos_elegidos_añadir(ticker, nombre)
    if ok:
        return {"ok": True, "ticker": ticker}
    return {"ok": False, "mensaje": f"{ticker} ya está en seguimiento"}

def ctrl_eliminar_seguimiento(ticker: str) -> dict:
    ok = activos_elegidos_eliminar(ticker)
    if ok:
        return {"ok": True, "ticker": ticker}
    return {"ok": False, "mensaje": f"{ticker} no encontrado"}