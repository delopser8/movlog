'''
    pipeline que orquesta el flujo completo de noticias
    - arranca los pollings de NewsAPI y RSS scraper
    - en cada ciclo de polling de velas detecta fluctuaciones fuertes
    - si hay fluctuación fuerte: traduce → FinBERT → Qwen → guarda en DuckDB
    - se llama desde app.py en el lifespan
'''


import threading
import time
from loguru import logger
import pandas as pd
from datetime import datetime, timedelta

from services.db.duckdb_client import (
    get_activo_id,
    get_activo_detalles,
    get_velas,
    get_noticias_recientes,
    get_noticias_por_activo,  
    insertar_sentimiento,
    insertar_noticia,
)
from services.db.mongodb_client import alertas_listar
from services.ai_models.translation import traducir_si_necesario
from services.ai_models.sentiment import analizar_sentimiento
from services.ai_models.explicabilidad import generar_explicacion
from services.ingesta.news_api import iniciar_polling as iniciar_newsapi
from services.ingesta.rss_scraper import iniciar_polling as iniciar_rss
from services.ingesta.news_api import _fetch_noticias, _get_client
from services.db.duckdb_client import insertar_noticia
from services.db.duckdb_client import get_activo_detalles


# --- Umbral de fluctuación proporcional ---
def _get_umbral() -> float:
    try:
        for a in alertas_listar():
            if a["alerta_id"] == "fluctuacion_brusca" and a["estado"] == "ON":
                umbral = a.get("umbral", [0.30, 10])
                return float(umbral[0]) if isinstance(umbral, list) else float(umbral)
    except Exception:
        pass
    return 3.0


# --- Detección de fluctuación ---
def _calcular_var_pct(ticker: str) -> float | None:
    try:
        df = get_velas(ticker, timeframe="5Min", limite=2)
        if isinstance(df, list):
            df = pd.DataFrame(df)
        if df.empty or len(df) < 2:
            return None
        actual   = df.iloc[-1]["cierre"]
        anterior = df.iloc[-2]["cierre"]
        if anterior == 0:
            return None
        return ((actual - anterior) / anterior) * 100
    except Exception as e:
        logger.warning(f"Error calculando var_pct para {ticker}: {e}")
        return None


# --- Pipeline de análisis ---
def procesar_ticker(ticker: str) -> bool:
    # comprueba si hay fluctuación fuerte y ejecuta el pipeline completo si es así
    # (return True si hubo fluctuación y se procesó)
    umbral  = _get_umbral()
    var_pct = _calcular_var_pct(ticker)

    if var_pct is None or abs(var_pct) < umbral:
        return False

    logger.info(f"Fluctuación detectada: {ticker} {var_pct:+.2f}% (umbral: {umbral}%)")

    activo_id = get_activo_id(ticker)
    if not activo_id:
        return False

    noticias = get_noticias_recientes(activo_id, minutos=4800)
    if not noticias:
        logger.info(f"Fluctuación en {ticker} sin noticias recientes")
        return False

    logger.info(f"Procesando {len(noticias)} noticias para {ticker}")

    noticias_procesadas = []
    for n in noticias:
        body = n.get("body") or n.get("titulo") or ""
        if not body:
            continue

        texto_en    = traducir_si_necesario(body)
        sentimiento = analizar_sentimiento(texto_en, ticker)

        insertar_sentimiento({
            "noticia_id":  n["noticia_id"],
            "activo_id":   activo_id,
            "score":       sentimiento["score"],
            "tipo":        sentimiento["tipo"],
            "explicacion": None,
            "var_pct":     var_pct,
        })
        noticias_procesadas.append({**n, "sentimiento": sentimiento})

    # explicación Qwen para la fluctuación
    if noticias_procesadas:
        explicacion = generar_explicacion(ticker, var_pct, noticias_procesadas)
        if explicacion:
            # asignar la explicación a la noticia con mayor score absoluto
            principal = max(noticias_procesadas, key=lambda x: abs(x["sentimiento"]["score"]))
            insertar_sentimiento({
                "noticia_id":  principal["noticia_id"],
                "activo_id":   activo_id,
                "score":       principal["sentimiento"]["score"],
                "tipo":        principal["sentimiento"]["tipo"],
                "explicacion": explicacion,
                "var_pct":     var_pct,
            })

    logger.info(f"Pipeline noticias completado para {ticker}")
    return True


# --- Loop de detección continua ---
def _procesar_noticias_nuevas(ticker: str):
    # procesa el sentimiento de noticias nuevas sin fluctuación
    activo_id = get_activo_id(ticker)
    if not activo_id:
        return

    # noticias recientes sin sentimiento aún
    noticias = get_noticias_recientes(activo_id, minutos=4800) 
    sin_sentimiento = [
        n for n in noticias 
        if n.get("score") is None and n.get("tipo") is None
    ]

    for n in sin_sentimiento:
        body = n.get("body") or n.get("titulo") or ""
        if not body:
            continue
        texto_en = traducir_si_necesario(body)
        sentimiento = analizar_sentimiento(texto_en, ticker)
        insertar_sentimiento({
            "noticia_id":  n["noticia_id"],
            "activo_id":   activo_id,
            "score":       sentimiento["score"],
            "tipo":        sentimiento["tipo"],
            "explicacion": None,
            "var_pct":     None,
        })

def _detection_loop(get_tickers_fn, intervalo: int = 15):
    # cada `intervalo` segundos procesa sentimiento de noticias nuevas
    # y detecta fluctuaciones fuertes para lanzar la explicación con Qwen
    while True:
        for ticker in get_tickers_fn():
            try:
                _procesar_noticias_nuevas(ticker)  # sentimiento continuo
                procesar_ticker(ticker)  # fluctuación + Qwen
            except Exception as e:
                logger.warning(f"Pipeline noticias error {ticker}: {e}")
        time.sleep(intervalo)

# --- Backfill inicial de noticias ---
def backfill_activo(ticker: str):
    '''
        al añadir un activo nuevo:
        1. Carga noticias de las últimas 48h desde NewsAPI
        2. Analiza velas de 5Min de las últimas 48h buscando fluctuaciones
        3. Para cada fluctuación, procesa noticias del periodo con FinBERT + Qwen
    '''

    logger.info(f"Backfill iniciado: {ticker}")

    # 1. carga noticias 48h desde NewsAPI
    detalles = get_activo_detalles(ticker)
    nombre = detalles.get("nombre", "") if detalles else ""
    query = nombre.split()[0] if nombre else ticker.split(".")[0].split("/")[0]

    desde_48h = datetime.utcnow() - timedelta(hours=48)
    noticias = _fetch_noticias(query, desde_48h)
    for n in noticias:
        insertar_noticia(n)
    logger.info(f"Backfill: {len(noticias)} noticias cargadas para {ticker}")

    # usar todas las noticias de DuckDB para el matching (más completo que solo las de NewsAPI)
    noticias_duck = get_noticias_por_activo(ticker, limite=100)

    # 2. analiza velas 5Min de las últimas 48h buscando fluctuaciones
    activo_id = get_activo_id(ticker)
    if not activo_id:
        return

    df = get_velas(ticker, timeframe="5Min", limite=576)
    if not isinstance(df, pd.DataFrame):
        df = pd.DataFrame(df) if df else pd.DataFrame()
    if df.empty or len(df) < 2:
        logger.info(f"Backfill: sin velas 5Min para {ticker}")
        return

    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)  
    umbral = _get_umbral()

    for i in range(1, len(df)):
        anterior = df.iloc[i-1]["cierre"]
        actual   = df.iloc[i]["cierre"]
        if anterior == 0:
            continue
        var_pct = ((actual - anterior) / anterior) * 100

        if abs(var_pct) < umbral:
            continue

        # fluctuación detectada — busca noticias del periodo en DuckDB
        ts_fluctuacion = df.iloc[i]["timestamp"]
        noticias_periodo = [
            n for n in noticias_duck
            if abs((pd.Timestamp(n["fecha_noticia"]).to_pydatetime().replace(tzinfo=None) - ts_fluctuacion.to_pydatetime().replace(tzinfo=None)).total_seconds()) < 21600  
        ]

        if not noticias_periodo:
            continue

        logger.info(f"Backfill fluctuación {ticker}: {var_pct:+.2f}% en {ts_fluctuacion}")

        for n in noticias_periodo:
            texto_en    = traducir_si_necesario(n.get("body") or n.get("titulo") or "")
            sentimiento = analizar_sentimiento(texto_en, ticker)
            insertar_sentimiento({
                "noticia_id":  n["noticia_id"],
                "activo_id":   activo_id,
                "score":       sentimiento["score"],
                "tipo":        sentimiento["tipo"],
                "explicacion": None,
                "var_pct":     None,  
            })

        # Qwen para la fluctuación
        explicacion = generar_explicacion(ticker, var_pct, noticias_periodo)
        if explicacion and noticias_periodo:
            principal = max(noticias_periodo, key=lambda x: abs(x.get("score") or 0))
            insertar_sentimiento({
                "noticia_id":  principal["noticia_id"],
                "activo_id":   activo_id,
                "score":       principal.get("score") or 0,
                "tipo":        principal.get("tipo") or "neutral",
                "explicacion": explicacion,
                "var_pct":     var_pct,
            })

    logger.info(f"Backfill completado: {ticker}")

# --- Arranque completo en nuevo hilo daemon ---
def iniciar_pipeline_noticias(get_tickers_fn):
    '''
        arranca todos los componentes del pipeline de noticias en threads daemon:
        - polling NewsAPI (cada 5min)
        - polling RSS Yahoo Finance (cada 5min)
        - loop de detección de fluctuaciones (cada 15s)
    '''
    iniciar_newsapi(get_tickers_fn)
    iniciar_rss(get_tickers_fn)

    hilo = threading.Thread(
        target=_detection_loop,
        args=(get_tickers_fn,),
        daemon=True,
        name="noticias-detection",
    )
    hilo.start()
    logger.info("Pipeline de noticias iniciado (NewsAPI + RSS + detección fluctuaciones)")

