'''
    servicio de preprocesamiento de los datos para el frontend
    - prepara DataFrames de velas para Plotly
    - formatea detalles del activo para la UI
'''


import os
import httpx
import pandas as pd
from loguru import logger

FASTAPI_URL = os.getenv("FASTAPI_URL", "http://localhost:8000")

# --- Helpers ---
def _get(endpoint: str, params: dict = {}) -> dict | list | None:
    try:
        r = httpx.get(f"{FASTAPI_URL}/api{endpoint}", params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.error(f"analytics_service GET {endpoint}: {e}")
        return None


# --- Velas ---
def get_velas_df(ticker: str, timeframe: str = "1Min", limite: int = 500) -> pd.DataFrame:
    # devuelve un DataFrame de velas OHLC listo para Plotly
    # columnas: timestamp, apertura, maximo, minimo, cierre, volumen
    datos = _get(f"/activos/{ticker}/velas", {"timeframe": timeframe, "limite": limite})

    if not datos:
        return pd.DataFrame()

    df = pd.DataFrame(datos)
    if df.empty:
        return df

    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df


# --- Detalles ---
def get_detalles(ticker: str) -> dict | None:
    # devuelve los detalles del activo desde DuckDB a través de FastAPI
    return _get(f"/activos/{ticker}/detalles")

def formatear_market_cap(valor: float | None) -> str: 
    if valor is None:
        return "--"
    if valor >= 1e12:
        return f"{valor / 1e12:.2f}T"
    if valor >= 1e9:
        return f"{valor / 1e9:.2f}B"
    if valor >= 1e6:
        return f"{valor / 1e6:.2f}M"
    return f"{valor:,.0f}"

def formatear_detalles(raw: dict) -> dict:
    # normaliza y formatea los detalles del activo para la UI
    # rellena con '--' los campos ausentes
    def fmt_float(val, decimales=2) -> str:
        if val is None:
            return "--"
        try:
            return f"{float(val):,.{decimales}f}"
        except (TypeError, ValueError):
            return "--"

    def fmt_pct(val) -> str:
        if val is None:
            return "--"
        try:
            return f"{float(val) * 100:.2f}%"
        except (TypeError, ValueError):
            return "--"

    rec = (raw.get("operacion_recomendada") or "holdea").lower()

    return {
        "ticker":   raw.get("ticker", "--"),
        "nombre":   raw.get("nombre", "--"),
        "sector":   raw.get("sector", "--"),
        "industria":raw.get("industria", "--"),
        "url":      raw.get("url", "--"),

        "cierre_diario":   fmt_float(raw.get("cierre_ajustado_diario")),
        "cierre_semanal":  fmt_float(raw.get("cierre_ajustado_semanal")),
        "cierre_mensual":  fmt_float(raw.get("cierre_ajustado_mensual")),
        "apertura_diaria": fmt_float(raw.get("apertura_diaria")),
        "apertura_semanal":fmt_float(raw.get("apertura_semanal")),
        "apertura_mensual":fmt_float(raw.get("apertura_mensual")),
        "maximo_diario":   fmt_float(raw.get("maximo_diario")),
        "maximo_semanal":  fmt_float(raw.get("maximo_semanal")),
        "maximo_mensual":  fmt_float(raw.get("maximo_mensual")),
        "minimo_diario":   fmt_float(raw.get("minimo_diario")),
        "minimo_semanal":  fmt_float(raw.get("minimo_semanal")),
        "minimo_mensual":  fmt_float(raw.get("minimo_mensual")),

        "ratio_pe":       fmt_float(raw.get("ratio_pe")),
        "eps":            fmt_float(raw.get("eps")),
        "market_cap":     formatear_market_cap(raw.get("market_cap")),
        "dividend_yield": fmt_pct(raw.get("dividend_yield")),
        "esg_score":      fmt_float(raw.get("esg_score"), 0) if raw.get("esg_score") else "--",

        "operacion_recomendada": rec,
        "target_price": fmt_float(raw.get("target_price")),
    }