'''
    Mock data de AAPL y TSLA
    Inserta velas y detalles en DuckDB para poder trabajar offline
    Se ejecuta al arrancar si está MOCK_MODE=true en el .env o si se confirma en terminal
    Si ya hay datos previos los reemplaza
'''


import sys
from pathlib import Path
from datetime import datetime, timedelta

import numpy as np

# asegura que el path de backend esté disponible
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src" / "backend"))

from src.backend.services.db.duckdb_client import (
    upsert_activo_detalles,
    insertar_velas,
    get_activo_id,
    eliminar_activo_detalles,
)


# --- Detalles mock ---
MOCK_DETALLES = {
    "AAPL": {
        "ticker": "AAPL",
        "nombre": "Apple Inc.",
        "sector": "Technology",
        "industria": "Consumer Electronics",
        "url": "apple.com",
        "cierre_ajustado_diario": 189.30,
        "cierre_ajustado_semanal": 187.50,
        "cierre_ajustado_mensual": 182.00,
        "apertura_diaria": 188.50,
        "apertura_semanal": 185.00,
        "apertura_mensual": 179.00,
        "maximo_diario": 190.20,
        "maximo_semanal": 192.00,
        "maximo_mensual": 195.00,
        "minimo_diario": 187.80,
        "minimo_semanal": 184.00,
        "minimo_mensual": 175.00,
        "ratio_pe": 28.5,
        "eps": 6.43,
        "market_cap": 2_950_000_000_000,
        "dividend_yield": 0.0055,
        "esg_score": 72.0,
        "operacion_recomendada": "compra",
        "target_price": 210.00,
    },
    "TSLA": {
        "ticker": "TSLA",
        "nombre": "Tesla, Inc.",
        "sector": "Consumer Cyclical",
        "industria": "Auto Manufacturers",
        "url": "tesla.com",
        "cierre_ajustado_diario": 172.50,
        "cierre_ajustado_semanal": 168.00,
        "cierre_ajustado_mensual": 155.00,
        "apertura_diaria": 170.00,
        "apertura_semanal": 165.00,
        "apertura_mensual": 150.00,
        "maximo_diario": 175.00,
        "maximo_semanal": 178.00,
        "maximo_mensual": 180.00,
        "minimo_diario": 169.00,
        "minimo_semanal": 162.00,
        "minimo_mensual": 145.00,
        "ratio_pe": 48.2,
        "eps": 3.58,
        "market_cap": 550_000_000_000,
        "dividend_yield": None,
        "esg_score": 38.0,
        "operacion_recomendada": "holdea",
        "target_price": 195.00,
    },
}


# --- Generador de velas mock ---
def _generar_velas(ticker: str, n: int = 2000) -> list[dict]:
    # genera N velas de 1 minuto realistas para el ticker dado
    np.random.seed({"AAPL": 42, "TSLA": 99}.get(ticker, 0))

    base = MOCK_DETALLES[ticker]["cierre_ajustado_diario"]
    volatilidad = base * 0.003

    ahora = datetime.now().replace(second=0, microsecond=0)
    # empieza hace N minutos en días laborables (aproximado)
    inicio = ahora - timedelta(minutes=n)

    precios = base + np.cumsum(np.random.randn(n) * volatilidad)
    velas = []

    for i in range(n):
        ts = inicio + timedelta(minutes=i)
        open_ = float(precios[i])
        close = float(precios[i] + np.random.randn() * volatilidad * 0.5)
        high  = float(max(open_, close) + abs(np.random.randn()) * volatilidad * 0.3)
        low   = float(min(open_, close) - abs(np.random.randn()) * volatilidad * 0.3)
        vol   = int(abs(np.random.randn()) * 100_000 + 50_000)

        velas.append({
            "timestamp": ts,
            "timeframe": "1Min",
            "apertura":  round(open_, 4),
            "maximo":    round(high, 4),
            "minimo":    round(low, 4),
            "cierre":    round(close, 4),
            "volumen":   vol,
        })

    return velas


# --- Inserción ---
def insertar_mock_data(verbose: bool = True):
    # inserta detalles y velas de AAPL y TSLA en DuckDB
    # elimina datos previos de estos tickers para asegurar datos frescos
    for ticker, detalles in MOCK_DETALLES.items():
        if verbose:
            print(f"  → Insertando mock data: {ticker}")

        # elimina datos previos si existen
        eliminar_activo_detalles(ticker)

        # inserta detalles
        activo_id = upsert_activo_detalles(detalles)

        # inserta velas
        velas = _generar_velas(ticker)
        n = insertar_velas(activo_id, velas)

        if verbose:
            print(f"    ✅ {ticker}: detalles OK, {n} velas insertadas (activo_id={activo_id})")


# --- main ---
if __name__ == "__main__":
    print("\n  Insertando mock data de AAPL y TSLA en DuckDB...")
    insertar_mock_data()
    print("  ✅ Mock data lista\n")