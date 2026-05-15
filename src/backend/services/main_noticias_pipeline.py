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

from services.db.duckdb_client import (
    get_activo_id,
    get_velas,
    get_noticias_recientes,
    insertar_sentimiento,
)
from services.db.mongodb_client import alertas_listar
from services.ai_models.translation import traducir_si_necesario
from services.ai_models.sentiment import analizar_sentimiento
from services.ai_models.explicabilidad import generar_explicacion
from services.ingesta.news_api import iniciar_polling as iniciar_newsapi
from services.ingesta.rss_scraper import iniciar_polling as iniciar_rss


# --- Umbral de fluctuación proporcional ---
def _get_umbral() -> float:
    try:
        for a in alertas_listar():
            if a["alerta_id"] == "fluctuacion_brusca" and a["estado"] == "ON":
                umbral = a.get("umbral", [3, 10])
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

    noticias = get_noticias_recientes(activo_id, minutos=30)
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
def _detection_loop(get_tickers_fn, intervalo: int = 15):
    # comprueba fluctuaciones en todos los activos en seguimiento
    # cada `intervalo` segundos (en sincronía con el polling de velas de Alpaca)
    logger.info(f"Loop de detección de fluctuaciones iniciado (intervalo: {intervalo}s)")
    while True:
        for ticker in get_tickers_fn():
            try:
                procesar_ticker(ticker)
            except Exception as e:
                logger.warning(f"Pipeline noticias error {ticker}: {e}")
        time.sleep(intervalo)


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