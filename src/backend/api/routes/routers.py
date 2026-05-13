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
)

router = APIRouter()


# --- Assets (carga del catálogo de símbolos) ---
@router.get("/assets/search")
def buscar_assets(q: str = Query(..., min_length=1), limite: int = 10):
    # busca activos por ticker o nombre en la lista local de Alpaca
    return ctrl_buscar_assets(q, limite)


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