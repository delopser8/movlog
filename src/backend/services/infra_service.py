'''
    servicio que maneja la lógica de la sección de Infraestructura
    - métricas del host (RAM, CPU)
    - healthcheck de servicios
    - stats de DuckDB y MongoDB
'''


import os
import socket
import psutil
import httpx
import duckdb
from loguru import logger
import subprocess


# -- Helpers ---
def _docker_health(container_name: str) -> bool:
    try:
        result = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.Health.Status}}", container_name],
            capture_output=True, text=True, timeout=3
        )
        return result.stdout.strip() == "healthy"
    except Exception:
        return False


# --- Búsqueda de todas las estadísticas del sistema ---
def get_infra_stats() -> dict:
    stats = {}

    # --- Host ---
    try:
        mem = psutil.virtual_memory()
        stats["host"] = {
            "nombre":       socket.gethostname(),
            "ram_total_gb": round(mem.total / 1e9, 1),
            "ram_usada_gb": round(mem.used  / 1e9, 1),
            "ram_pct":      mem.percent,
            "cpu_pct":      psutil.cpu_percent(interval=0.5),
        }
    except Exception as e:
        stats["host"] = {"error": str(e)}

    # --- Servicios ---
    # (redpanda está quitado)
    servicios_config = [
        {"nombre": "FastAPI",   "container": None,                  "url_ui": None,    "url_interna": "http://localhost:8000/health"},
        {"nombre": "MongoDB",   "container": "movlog_mongodb",      "url_ui": None},
        {"nombre": "Langfuse",  "container": "movlog_langfuse",     "url_ui": "13000"},
        {"nombre": "Ollama",    "container": "movlog_ollama",       "url_ui": "11434"},
    ]
    stats["servicios"] = []
    for s in servicios_config:
        if s.get("container"):
            ok = _docker_health(s["container"])
        else:
            try:
                r = httpx.get(s["url_interna"], timeout=2)
                ok = r.status_code < 400
            except Exception:
                ok = False
        stats["servicios"].append({
            "nombre": s["nombre"],
            "ok":     ok,
            "url_ui": s.get("url_ui"),
        })

    # --- DuckDB ---
    db_path = "db_data/movlog.duckdb"
    try:
        size_mb = round(os.path.getsize(db_path) / 1e6, 1) if os.path.exists(db_path) else 0
        con = duckdb.connect(db_path, read_only=True)
        activos  = con.execute("SELECT COUNT(DISTINCT ticker) FROM activos_detalles").fetchone()[0]
        velas    = con.execute("SELECT COUNT(*) FROM activos_precios").fetchone()[0]
        noticias = con.execute("SELECT COUNT(*) FROM noticias_historial").fetchone()[0]
        sentim   = con.execute("SELECT COUNT(*) FROM noticias_sentimientos").fetchone()[0]
        row = con.execute("""
            SELECT ns.var_pct, nh.fecha_noticia
            FROM noticias_sentimientos ns
            JOIN noticias_historial nh ON ns.noticia_id = nh.noticia_id
            WHERE ns.var_pct IS NOT NULL AND ns.explicacion IS NOT NULL
            ORDER BY nh.fecha_noticia DESC LIMIT 1
        """).fetchone()
        ultima_fluct = {"var_pct": row[0], "fecha": str(row[1])} if row else None
        con.close()
        stats["duckdb"] = {
            "size_mb":      size_mb,
            "activos":      activos,
            "velas":        velas,
            "noticias":     noticias,
            "sentimientos": sentim,
            "ultima_fluct": ultima_fluct,
        }
    except Exception as e:
        logger.warning(f"infra_service DuckDB: {e}")
        stats["duckdb"] = {"error": str(e)}

    # --- MongoDB ---
    try:
        from services.db.mongodb_client import activos_elegidos_listar, alertas_listar
        stats["mongodb"] = {
            "activos": len(activos_elegidos_listar()),
            "alertas": len(alertas_listar()),
        }
    except Exception as e:
        stats["mongodb"] = {"error": str(e)}

    return stats