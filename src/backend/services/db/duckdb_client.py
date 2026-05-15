'''
    servicio del cliente de DuckDB para consultas SQL a su base de datos
'''


import threading
from pathlib import Path
from datetime import datetime
import math
from datetime import timedelta

import duckdb
import pandas as pd
from loguru import logger


DB_PATH   = Path("db_data/movlog.duckdb")
PARQUET_PATH = Path("db_data/db_historicos")

# DuckDB permite múltiples readers pero un solo writer
# se usa un lock global para serializar las escrituras
_write_lock = threading.Lock()


def _conn(read_only: bool = False) -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(DB_PATH), read_only=read_only)


# --- activos_detalles ---
def get_siguiente_activo_id() -> int:
    with _conn() as con:
        result = con.execute("SELECT COALESCE(MAX(activo_id), 0) + 1 FROM activos_detalles").fetchone()
        return result[0]

def upsert_activo_detalles(datos: dict) -> int:
    # inserta o actualiza los detalles de un activo (devuelve el activo_id)
    with _write_lock:
        with _conn() as con:
            # comprueba si ya existe
            row = con.execute(
                "SELECT activo_id FROM activos_detalles WHERE ticker = ?",
                [datos["ticker"]]
            ).fetchone()

            if row:
                activo_id = row[0]
                con.execute('''
                    UPDATE activos_detalles SET
                        nombre = ?, sector = ?, industria = ?, url = ?,
                        cierre_ajustado_diario = ?, cierre_ajustado_semanal = ?, cierre_ajustado_mensual = ?,
                        apertura_diaria = ?, apertura_semanal = ?, apertura_mensual = ?,
                        maximo_diario = ?, maximo_semanal = ?, maximo_mensual = ?,
                        minimo_diario = ?, minimo_semanal = ?, minimo_mensual = ?,
                        ratio_pe = ?, eps = ?, market_cap = ?, dividend_yield = ?, esg_score = ?,
                        operacion_recomendada = ?, target_price = ?,
                        actualizado_en = CURRENT_TIMESTAMP,
                        clase = ?
                    WHERE ticker = ?
                ''', [
                    datos.get("nombre"), datos.get("sector"), datos.get("industria"), datos.get("url"), datos.get("clase", "us_equity"),
                    datos.get("cierre_ajustado_diario"), datos.get("cierre_ajustado_semanal"), datos.get("cierre_ajustado_mensual"),
                    datos.get("apertura_diaria"), datos.get("apertura_semanal"), datos.get("apertura_mensual"),
                    datos.get("maximo_diario"), datos.get("maximo_semanal"), datos.get("maximo_mensual"),
                    datos.get("minimo_diario"), datos.get("minimo_semanal"), datos.get("minimo_mensual"),
                    datos.get("ratio_pe"), datos.get("eps"), datos.get("market_cap"),
                    datos.get("dividend_yield"), datos.get("esg_score"),
                    datos.get("operacion_recomendada"), datos.get("target_price"),
                    datos["ticker"]
                ])
                logger.info(f"activos_detalles actualizado: {datos['ticker']}")
            else:
                activo_id = get_siguiente_activo_id()
                con.execute('''
                    INSERT INTO activos_detalles (
                        activo_id, ticker, nombre, sector, industria, url, clase,
                        cierre_ajustado_diario, cierre_ajustado_semanal, cierre_ajustado_mensual,
                        apertura_diaria, apertura_semanal, apertura_mensual,
                        maximo_diario, maximo_semanal, maximo_mensual,
                        minimo_diario, minimo_semanal, minimo_mensual,
                        ratio_pe, eps, market_cap, dividend_yield, esg_score,
                        operacion_recomendada, target_price
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', [
                    activo_id, datos["ticker"], datos.get("nombre"), datos.get("sector"),
                    datos.get("industria"), datos.get("url"), datos.get("clase", "us_equity"),
                    datos.get("cierre_ajustado_diario"), datos.get("cierre_ajustado_semanal"), datos.get("cierre_ajustado_mensual"),
                    datos.get("apertura_diaria"), datos.get("apertura_semanal"), datos.get("apertura_mensual"),
                    datos.get("maximo_diario"), datos.get("maximo_semanal"), datos.get("maximo_mensual"),
                    datos.get("minimo_diario"), datos.get("minimo_semanal"), datos.get("minimo_mensual"),
                    datos.get("ratio_pe"), datos.get("eps"), datos.get("market_cap"),
                    datos.get("dividend_yield"), datos.get("esg_score"),
                    datos.get("operacion_recomendada"), datos.get("target_price"),
                ])
                logger.info(f"activos_detalles insertado: {datos['ticker']} (id={activo_id})")

            return activo_id

def get_activo_detalles(ticker: str) -> dict | None:
    with _conn() as con:
        row = con.execute(
            "SELECT * FROM activos_detalles WHERE ticker = ?", [ticker]
        ).fetchdf()
        if row.empty:
            return None
        d = row.iloc[0].to_dict()
        for k, v in d.items():
            if hasattr(v, 'isoformat'):   
                d[k] = v.isoformat()
            elif hasattr(v, 'item'):   
                d[k] = v.item()
            if isinstance(d[k], float) and math.isnan(d[k]):  
                d[k] = None
        return d

def get_activo_id(ticker: str) -> int | None:
    with _conn() as con:
        row = con.execute(
            "SELECT activo_id FROM activos_detalles WHERE ticker = ?", [ticker]
        ).fetchone()
        return row[0] if row else None

def eliminar_activo_detalles(ticker: str) -> bool:
    with _write_lock:
        with _conn() as con:
            con.execute("DELETE FROM activos_precios WHERE activo_id = (SELECT activo_id FROM activos_detalles WHERE ticker = ?)", [ticker])
            con.execute("DELETE FROM activos_detalles WHERE ticker = ?", [ticker])
            logger.info(f"activos_detalles eliminado: {ticker}")
            return True


# --- activos_precios ---
def insertar_velas(activo_id: int, velas: list[dict]) -> int:
    # inserta velas OHLC
    # ignora duplicados por activo_id, timestamp, timeframe
    # devuelve el número de velas insertadas
    if not velas:
        return 0

    df = pd.DataFrame(velas)
    df["activo_id"] = activo_id

    with _write_lock:
        with _conn() as con:
            # INSERT OR IGNORE: INSERT con ON CONFLICT DO NOTHING
            con.execute('''
                INSERT INTO activos_precios (activo_id, timestamp, timeframe, apertura, maximo, minimo, cierre, volumen)
                SELECT activo_id, timestamp, timeframe, apertura, maximo, minimo, cierre, volumen
                FROM df
                ON CONFLICT (activo_id, timestamp, timeframe) DO NOTHING
            ''')
            logger.debug(f"Velas insertadas: activo_id={activo_id}, n={len(velas)}")
            return len(velas)

def get_velas(ticker: str, timeframe: str = "1Min", limite: int = 500) -> pd.DataFrame:
    # devuelve las últimas N velas de un activo para el timeframe dado
    with _conn() as con:
        df = con.execute('''
            SELECT ap.timestamp, ap.apertura, ap.maximo, ap.minimo, ap.cierre, ap.volumen
            FROM activos_precios ap
            JOIN activos_detalles ad ON ap.activo_id = ad.activo_id
            WHERE ad.ticker = ? AND ap.timeframe = ?
            ORDER BY ap.timestamp DESC
            LIMIT ?
        ''', [ticker, timeframe, limite]).fetchdf()

    if df.empty:
        return df

    return df.sort_values("timestamp").reset_index(drop=True)

def get_ultima_vela(ticker: str, timeframe: str = "1Min") -> dict | None:
    # devuelve la vela más reciente de un activo
    with _conn() as con:
        row = con.execute('''
            SELECT ap.timestamp, ap.apertura, ap.maximo, ap.minimo, ap.cierre, ap.volumen
            FROM activos_precios ap
            JOIN activos_detalles ad ON ap.activo_id = ad.activo_id
            WHERE ad.ticker = ? AND ap.timeframe = ?
            ORDER BY ap.timestamp DESC
            LIMIT 1
        ''', [ticker, timeframe]).fetchone()

    if not row:
        return None
    return {
        "timestamp": row[0], "apertura": row[1], "maximo": row[2],
        "minimo": row[3], "cierre": row[4], "volumen": row[5]
    }


# --- .parquet (datos históricos) ---
def exportar_parquet(ticker: str, timeframe: str = "1Min") -> Path | None:
    # exporta las velas de un activo a .parquet en db_historicos (para uso futuro en análisis OLAP)
    df = get_velas(ticker, timeframe, limite=100_000)
    if df.empty:
        return None

    destino = PARQUET_PATH / ticker
    destino.mkdir(parents=True, exist_ok=True)
    archivo = destino / f"{timeframe}_{datetime.now().strftime('%Y%m%d')}.parquet"
    df.to_parquet(archivo, index=False)
    logger.info(f"Parquet exportado: {archivo}")
    return archivo

def leer_parquet(ticker: str, timeframe: str = "1Min") -> pd.DataFrame:
    # lee todos los .parquet históricos de un activo
    ruta = PARQUET_PATH / ticker
    if not ruta.exists():
        return pd.DataFrame()

    archivos = list(ruta.glob(f"{timeframe}_*.parquet"))
    if not archivos:
        return pd.DataFrame()

    with _conn() as con:
        df = con.execute(f"SELECT * FROM read_parquet('{ruta}/{timeframe}_*.parquet')").fetchdf()
    return df.sort_values("timestamp").reset_index(drop=True)

# --- noticias ---
def insertar_noticia(noticia: dict) -> bool:
    # inserta una noticia en noticias_historial
    # ignora duplicados por noticia_id
    # devuelve True si se insertó, False si ya existía
    with _write_lock:
        with _conn() as con:
            existente = con.execute(
                "SELECT noticia_id FROM noticias_historial WHERE noticia_id = ?",
                [noticia["noticia_id"]]
            ).fetchone()
            if existente:
                return False
            con.execute('''
                INSERT INTO noticias_historial (noticia_id, titulo, url, origen, body, fecha_noticia)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', [
                noticia["noticia_id"],
                noticia["titulo"],
                noticia.get("url", ""),
                noticia.get("origen", ""),
                noticia.get("body", ""),
                noticia["fecha_noticia"],
            ])
            return True

def get_noticias_recientes(activo_id: int, minutos: int = 30) -> list[dict]:
    # devuelve las noticias de los últimos X minutos vinculadas a un activo
    # (join con noticias_sentimientos si existe, sino solo historial)
    desde = datetime.utcnow() - timedelta(minutes=minutos)
    with _conn() as con:
        df = con.execute('''
            SELECT
                nh.noticia_id, nh.titulo, nh.url, nh.origen, nh.body, nh.fecha_noticia,
                ns.score, ns.tipo, ns.explicacion, ns.var_pct
            FROM noticias_historial nh
            LEFT JOIN noticias_sentimientos ns
                ON nh.noticia_id = ns.noticia_id AND ns.activo_id = ?
            WHERE nh.fecha_noticia >= ?
            ORDER BY nh.fecha_noticia DESC
        ''', [activo_id, desde]).fetchdf()
    if df.empty:
        return []
    df["fecha_noticia"] = df["fecha_noticia"].astype(str)
    return df.to_dict(orient="records")

def get_noticias_por_activo(ticker: str, limite: int = 20) -> list[dict]:
    # devuelve las últimas noticias para un ticker buscando por nombre en el historial
    # incluye sentimiento si existe, si no los campos van como None
    with _conn() as con:
        row = con.execute(
            "SELECT nombre FROM activos_detalles WHERE ticker = ?", [ticker]
        ).fetchone()
        nombre = row[0] if row else None
        termino1 = nombre.split()[0].lower() if nombre else ticker.split(".")[0].split("/")[0].lower()
        termino2 = ticker.split(".")[0].split("/")[0].lower()

        df = con.execute('''
            SELECT
                nh.noticia_id, nh.titulo, nh.url, nh.origen, nh.body, nh.fecha_noticia,
                ns.score, ns.tipo, ns.explicacion, ns.var_pct
            FROM noticias_historial nh
            LEFT JOIN noticias_sentimientos ns ON nh.noticia_id = ns.noticia_id
            WHERE LOWER(nh.titulo) LIKE ? OR LOWER(nh.body) LIKE ?
               OR LOWER(nh.titulo) LIKE ? OR LOWER(nh.body) LIKE ?
            ORDER BY nh.fecha_noticia DESC
            LIMIT ?
        ''', [
            f"%{termino1}%", f"%{termino1}%",
            f"%{termino2}%", f"%{termino2}%",
            limite,
        ]).fetchdf()

    if df.empty:
        return []
    df["fecha_noticia"] = df["fecha_noticia"].astype(str)
    df = df.where(df.notna(), None)
    return df.to_dict(orient="records")

def insertar_sentimiento(sentimiento: dict) -> bool:
    # inserta o actualiza el sentimiento de una noticia para un activo
    with _write_lock:
        with _conn() as con:
            con.execute('''
                INSERT INTO noticias_sentimientos (noticia_id, activo_id, score, tipo, explicacion, var_pct)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT (noticia_id, activo_id) DO UPDATE SET
                    score = excluded.score,
                    tipo = excluded.tipo,
                    explicacion = excluded.explicacion,
                    var_pct = excluded.var_pct
            ''', [
                sentimiento["noticia_id"],
                sentimiento["activo_id"],
                sentimiento.get("score"),
                sentimiento.get("tipo"),
                sentimiento.get("explicacion"),
                sentimiento.get("var_pct"),
            ])
            return True
