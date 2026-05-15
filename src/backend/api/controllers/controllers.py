'''
    funciones handler de cada endpoint + llamada a servicios correspondientes
'''


import threading
from loguru import logger
from services.ingesta.alpaca_client import buscar_assets, cargar_velas_iniciales
from services.ingesta.yfinance_client import cargar_detalles_activo
from services.db.mongodb_client import (
    activos_elegidos_listar,
    activos_elegidos_añadir,
    activos_elegidos_eliminar,
)
from services.db.duckdb_client import (
    get_activo_detalles,
    get_velas,
    eliminar_activo_detalles,
    get_noticias_por_activo,
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
    if not ok:
        return {"ok": False, "mensaje": f"{ticker} ya está en seguimiento"}
 
    # carga detalles desde yfinance y velas iniciales desde Alpaca en background
    import threading
    def _cargar():
        cargar_detalles_activo(ticker)
        cargar_velas_iniciales(ticker, "1Min")
 
    threading.Thread(target=_cargar, daemon=True, name=f"carga-{ticker}").start()
    logger.info(f"Carga inicial lanzada en background: {ticker}")
 
    return {"ok": True, "ticker": ticker}

def ctrl_eliminar_seguimiento(ticker: str) -> dict:
    ok_mongo = activos_elegidos_eliminar(ticker)
    if not ok_mongo:
        return {"ok": False, "mensaje": f"{ticker} no encontrado"}
 
    # elimina de DuckDB (cascade: precios + detalles)
    eliminar_activo_detalles(ticker)
    return {"ok": True, "ticker": ticker}


# --- Detalles ---
def ctrl_get_detalles(ticker: str) -> dict | None:
    return get_activo_detalles(ticker)
 
 
# --- Velas ---
def ctrl_get_velas(ticker: str, timeframe: str = "1Min", limite: int = 500) -> list[dict]:
    df = get_velas(ticker, timeframe, limite)
    if df.empty and timeframe != "1Min":
        # carga bajo demanda para timeframes distintos de 1Min
        import threading
        threading.Thread(
            target=cargar_velas_iniciales,
            args=(ticker, timeframe),
            daemon=True
        ).start()
    if df.empty:
        return []
    df["timestamp"] = df["timestamp"].astype(str)
    return df.to_dict(orient="records")


# --- Noticias ---
def ctrl_get_noticias(ticker: str, limite: int = 20) -> list[dict]:
    # devuelve todas las noticias con sentimiento para un activo
    return get_noticias_por_activo(ticker, limite)
 
def ctrl_get_fluctuaciones(ticker: str, limite: int = 10) -> list[dict]:
    # devuelve solo las noticias con fluctuación fuerte explicada por IA
    noticias = get_noticias_por_activo(ticker, limite * 3)
    return [
        n for n in noticias
        if n.get("var_pct") is not None and n.get("explicacion")
    ][:limite]

def ctrl_añadir_seguimiento(ticker: str, nombre: str) -> dict:
    ok = activos_elegidos_añadir(ticker, nombre)
    if not ok:
        return {"ok": False, "mensaje": f"{ticker} ya está en seguimiento"}

    def _cargar():
        cargar_detalles_activo(ticker)
        cargar_velas_iniciales(ticker, "1Min")
        # carga inicial de noticias 24h + backfill de fluctuaciones
        from services.main_noticias_pipeline import backfill_activo
        backfill_activo(ticker)

    # lanza la carga inicial en background
    threading.Thread(target=_cargar, daemon=True, name=f"carga-{ticker}").start()
    return {"ok": True, "ticker": ticker}