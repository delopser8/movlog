'''
    endpoints de la API con llamadas a sus funciones handler
'''

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from api.controllers.controllers import (
    ctrl_buscar_assets,
    ctrl_listar_seguimientos,
    ctrl_añadir_seguimiento,
    ctrl_eliminar_seguimiento,
    ctrl_get_detalles,
    ctrl_get_velas,
)
 
router = APIRouter()


# --- Assets (carga del catálogo de símbolos) ---
@router.get("/assets/search")
def buscar_assets(q: str = Query(..., min_length=1), limite: int = 10):
    # busca activos por ticker o nombre en la lista local de Alpaca
    return ctrl_buscar_assets(q, limite)


# ------------------------------ SEGUIMIENTOS ------------------------------
# --- Seguimientos ---
@router.get("/seguimientos")
def listar_seguimientos():
    # lista los activos en seguimiento
    return ctrl_listar_seguimientos()

class SeguimientoIn(BaseModel):
    ticker: str
    nombre: str

@router.post("/seguimientos")
def añadir_seguimiento(body: SeguimientoIn):
    # añade un activo al seguimiento
    resultado = ctrl_añadir_seguimiento(body.ticker, body.nombre)
    if not resultado["ok"]:
        raise HTTPException(status_code=409, detail=resultado["mensaje"])
    return resultado

@router.delete("/seguimientos/{ticker}")
def eliminar_seguimiento(ticker: str):
    # elimina un activo del seguimiento
    resultado = ctrl_eliminar_seguimiento(ticker)
    if not resultado["ok"]:
        raise HTTPException(status_code=404, detail=resultado["mensaje"])
    return resultado


# --- Detalles del activo ---
@router.get("/activos/{ticker:path}/detalles")
def get_detalles(ticker: str):
    # devuelve los detalles completos de un activo desde DuckDB
    resultado = ctrl_get_detalles(ticker)
    if not resultado:
        raise HTTPException(status_code=404, detail=f"{ticker} no encontrado en DuckDB")
    return resultado
 
 
# --- Velas OHLC ---
@router.get("/activos/{ticker:path}/velas")
def get_velas(
    ticker: str,
    timeframe: str = Query("1Min", description="1Min | 5Min | 1Day | 1Week | 1Month"),
    limite: int = Query(500, description="Número máximo de velas a devolver"),
):
    # devuelve las últimas N velas OHLC de un activo
    return ctrl_get_velas(ticker, timeframe, limite)
# ------------------------------------------------------------------------------