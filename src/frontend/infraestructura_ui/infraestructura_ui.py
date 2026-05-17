'''
    UI de la sección de Infraestructura
    - métricas del host (RAM, CPU)
    - estado de servicios (healthcheck)
    - pipeline de datos (activos, velas, noticias)
    - bases de datos (DuckDB, MongoDB)
'''


import os
import streamlit as st
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh

from backend.services.ui.user_service import get_infra_stats


# --- CSS ---
CSS = '''
<style>
.infra-section-title {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    color: #4b5563;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 8px;
    padding-bottom: 4px;
    border-bottom: 1px solid #1e2329;
}
.infra-card {
    background: #111417;
    border: 1px solid #1e2329;
    border-radius: 8px;
    padding: 14px 16px;
    margin-bottom: 12px;
}
.infra-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 5px 0;
    border-bottom: 1px solid #1a1f26;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 12px;
    color: #c9cdd4;
}
.infra-row:last-child { border-bottom: none; }
.infra-label { color: #8d939b; font-size: 11px; }
.infra-value { color: #e8eaed; }
.infra-value-green { color: #22c55e; }
.infra-value-red   { color: #ef4444; }
.infra-value-yellow{ color: #f59e0b; }

/* Servicio badge */
.svc-grid {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 8px;
    margin-bottom: 4px;
}
.svc-item {
    background: #0d0f11;
    border: 1px solid #1e2329;
    border-radius: 6px;
    padding: 8px 10px;
    display: flex;
    align-items: center;
    gap: 6px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
}
.svc-dot {
    width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0;
}
.svc-name { color: #c9cdd4; flex: 1; }
.svc-link { color: rgb(39 140 236) !important; font-size: 10px; text-decoration: none; }
.svc-link:hover { text-decoration: underline; }

/* Barra de progreso RAM/CPU */
.progress-bar-bg {
    background: #1e2329;
    border-radius: 4px;
    height: 6px;
    width: 100%;
    margin-top: 4px;
    overflow: hidden;
}
.progress-bar-fill {
    height: 6px;
    border-radius: 4px;
    transition: width 0.3s;
}
</style>
'''


# --- Helpers ---
def _fmt_hace(fecha_str: str) -> str:
    try:
        fecha = datetime.fromisoformat(fecha_str)
        delta = datetime.utcnow() - fecha
        h = int(delta.total_seconds() / 3600)
        m = int((delta.total_seconds() % 3600) / 60)
        if h > 0:
            return f"hace {h}h {m}min"
        return f"hace {m}min"
    except Exception:
        return fecha_str

def _color_pct(pct: float) -> str:
    if pct > 85: return "#ef4444"
    if pct > 60: return "#f59e0b"
    return "#22c55e"

def _fmt_num(n: int) -> str:
    if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
    if n >= 1_000:     return f"{n/1_000:.1f}k"
    return str(n)


# --- Render ---
def render():
    st_autorefresh(interval=5000, key="infra_autorefresh")
    st.markdown(CSS, unsafe_allow_html=True)

    data = get_infra_stats()

    codespace = os.getenv("CODESPACE_NAME", "")

    col1, col2 = st.columns([1, 1], gap="large")

    # --- COLUMNA IZQUIERDA ---
    with col1:

        # --- Host ---
        st.markdown('<div class="infra-section-title">Host</div>', unsafe_allow_html=True)
        host = data.get("host", {})
        if "error" not in host:
            ram_pct = host.get("ram_pct", 0)
            cpu_pct = host.get("cpu_pct", 0)
            ram_color = _color_pct(ram_pct)
            cpu_color = _color_pct(cpu_pct)
            st.markdown(f'''
            <div class="infra-card">
                <div class="infra-row">
                    <span class="infra-label">Máquina</span>
                    <span class="infra-value">{host.get("nombre", "--")}</span>
                </div>
                <div class="infra-row">
                    <span class="infra-label">RAM usada</span>
                    <span class="infra-value" style="color:{ram_color}">
                        {host.get("ram_usada_gb", 0)} / {host.get("ram_total_gb", 0)} GB
                        &nbsp;({ram_pct:.1f}%)
                    </span>
                </div>
                <div class="progress-bar-bg">
                    <div class="progress-bar-fill" style="width:{ram_pct}%;background:{ram_color}"></div>
                </div>
                <div class="infra-row" style="margin-top:8px">
                    <span class="infra-label">CPU</span>
                    <span class="infra-value" style="color:{cpu_color}">{cpu_pct:.1f}%</span>
                </div>
                <div class="progress-bar-bg">
                    <div class="progress-bar-fill" style="width:{cpu_pct}%;background:{cpu_color}"></div>
                </div>
            </div>
            ''', unsafe_allow_html=True)
        else:
            st.markdown('<div class="infra-card"><span style="color:#4b5563;font-size:12px">Sin datos del host</span></div>', unsafe_allow_html=True)

        # --- Servicios ---
        st.markdown('<div class="infra-section-title">Servicios</div>', unsafe_allow_html=True)
        servicios = data.get("servicios", [])
        if servicios:
            items_html = ""
            for s in servicios:
                dot_color = "#22c55e" if s["ok"] else "#ef4444"
                link_html = ""
                if s.get("url_ui") and codespace:
                    url = f"https://{codespace}-{s['url_ui']}.app.github.dev"
                    link_html = f'<a href="{url}" target="_blank" class="svc-link">↗</a>'
                elif s.get("url_ui"):
                    url = f"http://localhost:{s['url_ui']}"
                    link_html = f'<a href="{url}" target="_blank" class="svc-link">↗</a>'
                items_html += (
                    f'<div class="svc-item">'
                    f'<div class="svc-dot" style="background:{dot_color}"></div>'
                    f'<span class="svc-name">{s["nombre"]}</span>'
                    f'{link_html}'
                    f'</div>'
                )
            st.markdown(f'<div class="svc-grid">{items_html}</div>', unsafe_allow_html=True)

        # DuckDB como servicio adicional
        duckdb_data = data.get("duckdb", {})
        duckdb_ok = "error" not in duckdb_data
        duckdb_color = "#22c55e" if duckdb_ok else "#ef4444"
        st.markdown(f'''
        <div class="svc-grid" style="margin-top:0">
            <div class="svc-item">
                <div class="svc-dot" style="background:{duckdb_color}"></div>
                <span class="svc-name">DuckDB</span>
            </div>
        </div>
        ''', unsafe_allow_html=True)

    # --- COLUMNA DERECHA ---
    with col2:

        # --- Pipeline de datos ---
        st.markdown('<div class="infra-section-title">Pipeline de datos</div>', unsafe_allow_html=True)
        db = data.get("duckdb", {})
        mdb = data.get("mongodb", {})

        if "error" not in db:
            ultima_fluct = db.get("ultima_fluct")
            fluct_html = "--"
            if ultima_fluct:
                signo = "+" if ultima_fluct["var_pct"] > 0 else ""
                color = "#22c55e" if ultima_fluct["var_pct"] > 0 else "#ef4444"
                hace  = _fmt_hace(ultima_fluct["fecha"])
                fluct_html = f'<span style="color:{color}">{signo}{ultima_fluct["var_pct"]:.2f}%</span> · {hace}'

            st.markdown(f'''
            <div class="infra-card">
                <div class="infra-row">
                    <span class="infra-label">Activos en seguimiento</span>
                    <span class="infra-value">{db.get("activos", "--")}</span>
                </div>
                <div class="infra-row">
                    <span class="infra-label">Velas totales</span>
                    <span class="infra-value">{_fmt_num(db.get("velas", 0))}</span>
                </div>
                <div class="infra-row">
                    <span class="infra-label">Noticias historial</span>
                    <span class="infra-value">{_fmt_num(db.get("noticias", 0))}</span>
                </div>
                <div class="infra-row">
                    <span class="infra-label">Sentimientos calculados</span>
                    <span class="infra-value">{_fmt_num(db.get("sentimientos", 0))}</span>
                </div>
                <div class="infra-row">
                    <span class="infra-label">Última fluctuación fuerte</span>
                    <span class="infra-value">{fluct_html}</span>
                </div>
            </div>
            ''', unsafe_allow_html=True)
        else:
            st.markdown('<div class="infra-card"><span style="color:#4b5563;font-size:12px">DuckDB no disponible</span></div>', unsafe_allow_html=True)

        # --- Bases de datos ---
        st.markdown('<div class="infra-section-title">Bases de datos</div>', unsafe_allow_html=True)
        st.markdown(f'''
        <div class="infra-card">
            <div class="infra-row">
                <span class="infra-label">DuckDB — tamaño en disco</span>
                <span class="infra-value">{db.get("size_mb", "--")} MB</span>
            </div>
            <div class="infra-row">
                <span class="infra-label">MongoDB — activos</span>
                <span class="infra-value">{mdb.get("activos", "--")}</span>
            </div>
            <div class="infra-row">
                <span class="infra-label">MongoDB — alertas configuradas</span>
                <span class="infra-value">{mdb.get("alertas", "--")}</span>
            </div>
        </div>
        ''', unsafe_allow_html=True)

        # --- Timestamp último refresh ---
        st.markdown(
            f'<div style="font-family:IBM Plex Mono,monospace;font-size:10px;color:#4b5563;text-align:right;margin-top:4px">'
            f'Actualizado {datetime.utcnow().strftime("%H:%M:%S")} UTC · refresco cada 5s</div>',
            unsafe_allow_html=True,
        )