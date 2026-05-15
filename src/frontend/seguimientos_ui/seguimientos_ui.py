'''
    UI de la sección de seguimientos
'''


import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

from backend.services.ui.user_service import (
    buscar_assets,
    listar_seguimientos,
    añadir_seguimiento,
    eliminar_seguimiento,
    get_detalles,
    get_velas,
)
from backend.services.preprocesamiento.analytics_service import formatear_detalles

from seguimientos_ui.noticias_ui import render_noticias


# --- HELPERS VISUALES ---
# color número -> POSITIVO (verde) | NEGATIVO (rojo) | NEUTRO (gris)
def _color_var(val) -> str:
    try:
        f = float(val)
        if f > 0: return "#22c55e"
        if f < 0: return "#ef4444"
    except (TypeError, ValueError):
        pass
    return "#6b7280"

# formato número -> +1,234.56 | -123.45 | +1.23% (pct=true) | -- (si no es número)
def _fmt_var(val, pct: bool = False) -> str:
    try:
        f = float(val)
        signo = "+" if f > 0 else ""
        sufijo = "%" if pct else ""
        return f"{signo}{f:,.2f}{sufijo}"
    except (TypeError, ValueError):
        return "--"

# activo vacío para mostrar en la tabla de seguimientos mientras se carga el activo real desde mongoDB
def _activo_vacio(ticker: str, nombre: str) -> dict: 
    return {"simbolo": ticker, "nombre": nombre, "ticker": ticker}


# --- CONSTANTES ---
# cantidad de velas en proporción al timeframe
LIMITE_POR_TIMEFRAME = {
    "1Min":   500,
    "5Min":   500,
    "1Day":   365,
    "1Week":  200,
    "1Month": 60,
}


# --- Gráfico de velas (Plotly) ---
def _grafico_velas(df: pd.DataFrame, simbolo: str) -> go.Figure:
    fig = go.Figure()
    up, dn = "#22c55e", "#ef4444"
    fig.add_trace(go.Candlestick(
        x=df["timestamp"], open=df["apertura"], high=df["maximo"],
        low=df["minimo"], close=df["cierre"], name=simbolo,
        increasing_line_color=up, decreasing_line_color=dn,
        increasing_fillcolor=up, decreasing_fillcolor=dn,
        line=dict(width=1),
    ))
    fig.add_trace(go.Bar(
        x=df["timestamp"], y=df["volumen"], name="Volumen",
        marker_color=[up if c >= o else dn for c, o in zip(df["cierre"], df["apertura"])],
        opacity=0.35, yaxis="y2",
    ))
    fig.update_layout(
        paper_bgcolor="#0d0f11", plot_bgcolor="#0d0f11",
        font=dict(family="IBM Plex Mono", color="#6b7280", size=11),
        margin=dict(l=0, r=0, t=8, b=0), height=320,
        xaxis=dict(rangeslider=dict(visible=False), gridcolor="#1e2329", showgrid=True, zeroline=False, tickfont=dict(size=10)),
        yaxis=dict(gridcolor="#1e2329", showgrid=True, zeroline=False, tickfont=dict(size=10), side="right"),
        yaxis2=dict(overlaying="y", side="left", showgrid=False, showticklabels=False),
        legend=dict(orientation="h", x=0, y=1.02, font=dict(size=10)),
        xaxis_rangeslider_visible=False,
    )
    return fig

def _grafico_vacio(msg: str = "Sin datos de velas disponibles") -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        paper_bgcolor="#0d0f11", plot_bgcolor="#0d0f11", height=320,
        margin=dict(l=0, r=0, t=8, b=0),
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        annotations=[dict(
            text=msg, x=0.5, y=0.5, xref="paper", yref="paper",
            showarrow=False, font=dict(color="#4b5563", size=13, family="IBM Plex Mono"),
        )],
    )
    return fig


# --- CSS de SEGUIMIENTOS ---
CSS = '''
<style>
/* Default de botones*/
.stMainBlockContainer button[kind="primary"] {
    background-color: #3b82f6;
    color: #ffffff;
    border: 1px solid #1f1fc9;
}
.stMainBlockContainer button[kind="primary"]:hover {
    background-color: #6399f1;
    border: 1px solid #1f1fc9;
}
.stMainBlockContainer button[kind="secondary"] {
    color: #333333;
}

/* Tabs General / Noticias */
.seg-tabs { display: flex; gap: 0; margin-bottom: 1.25rem; border-bottom: 1px solid #1e2329; }
.seg-tab {
    padding: 8px 18px;
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 13px;
    font-weight: 400;
    color: #4b5563;
    cursor: pointer;
    border: none;
    background: transparent;
    border-bottom: 2px solid transparent;
    margin-bottom: -1px;
    transition: all 0.15s;
}
.seg-tab.active { color: #e8eaed; border-bottom-color: #3b82f6; font-weight: 500; }
.seg-tab:hover:not(.active) { color: #9ca3af; }

/* Gráfico container */
.chart-wrap {
    background: #111417;
    border: 1px solid #1e2329;
    border-radius: 8px;
    padding: 12px 12px 4px;
    margin-bottom: 1.25rem;
}

/* Info del activo */
.activo-titulo {
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 14px;
    font-weight: 500;
    color: #666666;
    margin-bottom: 1rem;
}
.info-grid {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 1px;
    background: #1e2329;
    border: 1px solid #1e2329;
    border-radius: 8px;
    overflow: hidden;
    margin-bottom: 1rem;
}
.info-cell {
    background: #111417;
    padding: 10px 12px;
}
.info-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10px;
    color: #818a98;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 3px;
}
.info-value {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 12px;
    color: #d6dae0;
}
.info-value a { color: #3b82f6; text-decoration: none; }
.info-value a:hover { text-decoration: underline; }

/* Badge recomendación */
.badge-compra  { color: #22c55e; background: #052e16; padding: 2px 8px; border-radius: 4px; font-size: 11px; }
.badge-holdea  { color: #f59e0b; background: #1c1208; padding: 2px 8px; border-radius: 4px; font-size: 11px; }
.badge-vende   { color: #ef4444; background: #1f0707; padding: 2px 8px; border-radius: 4px; font-size: 11px; }

/* Panel derecho */
.panel-titulo {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 13px;
    font-weight: 500;
    color: #666666;
    font-size: 0.9em;
    margin-bottom: 0.5rem;
}
.panel-sep { border: none; border-top: 1px solid #1e2329; margin: 0 0 0.75rem; }

/* Tabla de seguimiento */
.seg-table { width: 100%; border-collapse: collapse; }
.seg-table th {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10px;
    color: #4b5563;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding: 0 6px 6px;
    text-align: right;
    font-weight: 400;
}
.seg-table th:first-child { text-align: left; }
.seg-table td {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 12px;
    color: #c9cdd4;
    padding: 6px 6px;
    text-align: right;
    border-top: 1px solid #1a1f26;
}
.seg-table td:first-child { text-align: left; font-weight: 500; color: #e8eaed; }
.seg-table tr.selected td { background: #0f1a2e; }
.seg-table tr.selected td:first-child { border-left: 2px solid #3b82f6; }

/* Filas simuladas */
.seg-row {
    display: flex;
    align-items: center;
    border-top: 1px solid #1a1f26;
    padding: 0;
}
.seg-row .seg-cell {
    color: rgb(160 160 160);
}
.seg-row-selected {
    background: #0f1a2e;
    border-left: 2px solid #3b82f6;
}
.seg-header {
    border-top: none;
}
.seg-header .seg-cell {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10px;
    color: #4b5563;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding-bottom: 6px;
}
.seg-cell {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 12px;
    color: #c9cdd4;
    padding: 6px 4px;
}
.seg-cell-x   { width: 24px; flex-shrink: 0; text-align: center; }
.seg-cell-sym { flex: 2; }
.seg-cell-num { flex: 1.5; text-align: right; }

/* Botones de fila (sel y del) */
.st-emotion-cache-3pwa5w.e1rw0b1u1:has(.seg-row) + .st-emotion-cache-18kf3ut .stHorizontalBlock.st-emotion-cache-1permvm.e1rw0b1u3 {
    scale: 0.5;
}
.st-emotion-cache-3pwa5w.e1rw0b1u1:has(.seg-row) + .st-emotion-cache-18kf3ut .stHorizontalBlock.st-emotion-cache-1permvm.e1rw0b1u3 p{
    font-size: 1.4em;
}

/* Buscador */
.buscar-wrap { margin: 1rem 0 0.5rem; display: flex; gap: 6px; }

/* Resultados búsqueda */
.resultado-item {
    padding: 7px 10px;
    background: #111417;
    border-bottom: 1px solid #1e2329;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 12px;
    color: #c9cdd4;
    cursor: pointer;
    transition: background 0.1s;
}
.resultado-item:first-child { border-top: 1px solid #1e2329; border-radius: 6px 6px 0 0; }
.resultado-item:last-child  { border-radius: 0 0 6px 6px; border-bottom: none; }
.resultado-item:hover { background: #1a1f26; color: #e8eaed; }
.resultados-wrap { border: 1px solid #1e2329; border-radius: 6px; overflow: hidden; margin-bottom: 1rem; }

/* Panel inferior activo seleccionado */
.activo-card {
    border: 1px solid #1e2329;
    border-radius: 8px;
    padding: 12px 14px;
    background: #111417;
    margin-top: auto;
}
.activo-card-simbolo {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 13px;
    font-weight: 500;
    color: #e8eaed;
}
.activo-card-nombre {
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 12px;
    color: #8f96a5;
    margin-bottom: 8px;
}
.activo-card-tipo {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10px;
    color: #8f96a5;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 6px;
}
.activo-card-precio {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 22px;
    font-weight: 500;
    color: #e8eaed;
    margin-bottom: 2px;
}
.activo-card-vars {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 12px;
    margin-bottom: 6px;
}
.activo-card-meta {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10px;
    color: #8f96a5;
    margin-bottom: 4px;
}
.badge-mercado-open   { background: #052e16; color: #22c55e; font-size: 10px; padding: 2px 8px; border-radius: 20px; font-family: 'IBM Plex Mono', monospace; }
.badge-mercado-closed { background: #4f4200; color: #dab600; font-size: 10px; padding: 2px 8px; border-radius: 20px; font-family: 'IBM Plex Mono', monospace; }

/* Estado cargando */
.cargando-msg {
    color: #4b5563;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 12px;
    padding: 1rem 0;
}

/* Badge sin recomendación */
.badge- {
    color: #6b7280;
    background: #1a1f26;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
}
</style>
'''


# --- FUNCIONES de BÚSQUEDA ---
def _ejecutar_busqueda(query: str):
    if query:
        resultados = buscar_assets(query, limite=8)
        st.session_state.seg_resultados = resultados if resultados else [{"ticker": "Sin resultados", "nombre": ""}]
    else:
        st.session_state.seg_resultados = []

def _on_busqueda_change():
    _ejecutar_busqueda(st.session_state.seg_busqueda_input)


# --- RENDER PRINCIPAL ---
def render():

    # --- Auto-refresh de UI (cada 20s) ---
    if st.session_state.get("seg_activos"):
        st_autorefresh(interval=20000, key="seg_autorefresh")

    st.markdown(CSS, unsafe_allow_html=True)

    if "seg_tab" not in st.session_state:
        st.session_state.seg_tab = "general"
    if "seg_activo_idx" not in st.session_state:
        st.session_state.seg_activo_idx = 0
    if "seg_activos" not in st.session_state:
        raw = listar_seguimientos()
        st.session_state.seg_activos = [
            _activo_vacio(a["ticker"], a.get("nombre", a["ticker"])) for a in raw
        ]
    if "seg_busqueda" not in st.session_state:
        st.session_state.seg_busqueda = ""
    if "seg_resultados" not in st.session_state:
        st.session_state.seg_resultados = []
    if "seg_timeframe" not in st.session_state:
        st.session_state.seg_timeframe = "1Min"
 
    activos = st.session_state.seg_activos
    idx = min(st.session_state.seg_activo_idx, len(activos) - 1) if activos else 0
    activo = activos[idx] if activos else None

    # Layout: col izquierda (2/3) + col derecha (1/3)
    col_izq, col_der = st.columns([2, 1], gap="large")

    # +++ BLOQUE IZQUIERDO +++
    with col_izq:

        # --- Tabs General / Noticias ---
        tab_col1, tab_col2, _ = st.columns([1, 1, 6])
        with tab_col1:
            if st.button("General", key="tab_general",
                         type="primary" if st.session_state.seg_tab == "general" else "secondary",
                         use_container_width=True):
                st.session_state.seg_tab = "general"
                st.rerun()
        with tab_col2:
            if st.button("Noticias", key="tab_noticias",
                         type="primary" if st.session_state.seg_tab == "noticias" else "secondary",
                         use_container_width=True):
                st.session_state.seg_tab = "noticias"
                st.rerun()
 
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

        # --- TAB GENERAL ---
        if st.session_state.seg_tab == "general":
 
            if not activo:
                st.markdown(
                    "<div style='color:#4b5563;font-size:13px;padding:2rem 0;text-align:center'>"
                    "No hay activos en seguimiento.<br>Añade uno desde el panel derecho."
                    "</div>", unsafe_allow_html=True,
                )
            else:
                ticker = activo["ticker"]
 
                # Gráfico de velas
                tf_opciones = ["1Min", "5Min", "1Day", "1Week", "1Month"]
                tf_labels   = {"1Min": "1m", "5Min": "5m", "1Day": "1D", "1Week": "1W", "1Month": "1M"}

                cols_tf = st.columns(len(tf_opciones))
                for col, tf in zip(cols_tf, tf_opciones):
                    with col:
                        activo_btn = "primary" if st.session_state.seg_timeframe == tf else "secondary"
                        if st.button(tf_labels[tf], key=f"tf_{tf}", type=activo_btn, use_container_width=True):
                            st.session_state.seg_timeframe = tf
                            st.rerun()

                limite = LIMITE_POR_TIMEFRAME.get(st.session_state.seg_timeframe, 500)
                velas_raw = get_velas(ticker, timeframe=st.session_state.seg_timeframe, limite=limite)
                with st.container():
                    st.markdown('<div class="chart-wrap">', unsafe_allow_html=True)
                    if velas_raw:
                        df = pd.DataFrame(velas_raw)
                        df["timestamp"] = pd.to_datetime(df["timestamp"])
                        df = df.sort_values("timestamp").reset_index(drop=True)
                        fig = _grafico_velas(df, ticker)
                    else:
                        fig = _grafico_vacio("Cargando velas... (puede tardar unos segundos)")
                    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
                    st.markdown("</div>", unsafe_allow_html=True)
 
                #--- <hr> ---
                st.markdown('<hr class="panel-sep">', unsafe_allow_html=True)
                
                # Detalles
                raw = get_detalles(ticker)
                if raw:
                    d = formatear_detalles(raw)
                    rec = d["operacion_recomendada"]
                    badge_html = f'<span class="badge-{rec}">{rec.capitalize()}</span>'
                    url = d["url"]
                    url_html = f'<a href="https://{url}" target="_blank">{url} ↗</a>' if url != "--" else "--"
 
                    st.markdown(f'<div class="activo-titulo">Sobre {d["nombre"]}</div>', unsafe_allow_html=True)
                    st.markdown(f'''
                    <div class="info-grid">
                        <div class="info-cell"><div class="info-label">Ticker</div><div class="info-value">{d["ticker"]}</div></div>
                        <div class="info-cell"><div class="info-label">Sitio web</div><div class="info-value">{url_html}</div></div>
                        <div class="info-cell"><div class="info-label">Sector</div><div class="info-value">{d["sector"]}</div></div>
                        <div class="info-cell"><div class="info-label">Industria</div><div class="info-value">{d["industria"]}</div></div>
                        <div class="info-cell"><div class="info-label">Clase</div><div class="info-value">{d["clase"]}</div></div>
                        <div class="info-cell"><div class="info-label">Cierre ajust. diario</div><div class="info-value">{d["cierre_diario"]}</div></div>
                        <div class="info-cell"><div class="info-label">Cierre ajust. semanal</div><div class="info-value">{d["cierre_semanal"]}</div></div>
                        <div class="info-cell"><div class="info-label">Cierre ajust. mensual</div><div class="info-value">{d["cierre_mensual"]}</div></div>
                        <div class="info-cell"><div class="info-label">Apertura diaria</div><div class="info-value">{d["apertura_diaria"]}</div></div>
                        <div class="info-cell"><div class="info-label">Apertura semanal</div><div class="info-value">{d["apertura_semanal"]}</div></div>
                        <div class="info-cell"><div class="info-label">Apertura mensual</div><div class="info-value">{d["apertura_mensual"]}</div></div>
                        <div class="info-cell"><div class="info-label">Máximo diario</div><div class="info-value">{d["maximo_diario"]}</div></div>
                        <div class="info-cell"><div class="info-label">Máximo semanal</div><div class="info-value">{d["maximo_semanal"]}</div></div>
                        <div class="info-cell"><div class="info-label">Máximo mensual</div><div class="info-value">{d["maximo_mensual"]}</div></div>
                        <div class="info-cell"><div class="info-label">Mínimo diario</div><div class="info-value">{d["minimo_diario"]}</div></div>
                        <div class="info-cell"><div class="info-label">Mínimo semanal</div><div class="info-value">{d["minimo_semanal"]}</div></div>
                        <div class="info-cell"><div class="info-label">Mínimo mensual</div><div class="info-value">{d["minimo_mensual"]}</div></div>
                        <div class="info-cell"><div class="info-label">Ratio P/E</div><div class="info-value">{d["ratio_pe"]}</div></div>
                        <div class="info-cell"><div class="info-label">EPS</div><div class="info-value">{d["eps"]}</div></div>
                        <div class="info-cell"><div class="info-label">Market Cap</div><div class="info-value">{d["market_cap"]}</div></div>
                        <div class="info-cell"><div class="info-label">Dividend Yield</div><div class="info-value">{d["dividend_yield"]}</div></div>
                        <div class="info-cell"><div class="info-label">ESG Score</div><div class="info-value">{d["esg_score"]}</div></div>
                        <div class="info-cell"><div class="info-label">Recomendación</div><div class="info-value">{badge_html}</div></div>
                        <div class="info-cell"><div class="info-label">Precio objetivo</div><div class="info-value">{d["target_price"]}</div></div>
                    </div>
                    ''', unsafe_allow_html=True)
                else:
                    st.markdown(
                        "<div class='cargando-msg'>Cargando detalles... (puede tardar unos segundos la primera vez)</div>",
                        unsafe_allow_html=True,
                    )
        
        # --- TAB NOTICIAS ---
        else:
            if activo:
                from seguimientos_ui.noticias_ui import render_noticias
                render_noticias(activo["ticker"])
            else:
                st.markdown(
                    "<div style='color:#4b5563;font-size:13px;padding:2rem 0;text-align:center'>"
                    "No hay activos en seguimiento.<br>Añade uno desde el panel derecho.</div>",
                    unsafe_allow_html=True,
                )

    # +++ BLOQUE DERECHO +++
    with col_der:

        # Título
        st.markdown('<div class="panel-titulo">Activos en seguimiento</div>', unsafe_allow_html=True)

        #--- <hr> ---
        st.markdown('<hr class="panel-sep">', unsafe_allow_html=True)

        # Tabla de activos en seguimiento
        if activos:
            # Cabecera
            st.markdown('''
            <div class="seg-row seg-header">
                <div class="seg-cell seg-cell-sym">Símbolo</div>
                <div class="seg-cell seg-cell-num">Último</div>
                <div class="seg-cell seg-cell-num">Var. Abs.</div>
                <div class="seg-cell seg-cell-num">Var. Rel.</div>
            </div>
            ''', unsafe_allow_html=True)

            # Filas de activos
            for i, a in enumerate(activos):
                sel_style = "seg-row-selected" if i == idx else ""
                ultimo_precio = var_abs_str = var_rel_str = "--"
                color_abs = color_rel = "#6b7280"
 
                velas = get_velas(a["ticker"], timeframe="1Min", limite=2)
                if velas and len(velas) >= 2:
                    ultimo = velas[-1]["cierre"]
                    anterior = velas[-2]["cierre"]
                    var_abs = ultimo - anterior
                    var_rel = (var_abs / anterior * 100) if anterior else 0
                    ultimo_precio = f"{ultimo:,.2f}"
                    var_abs_str = _fmt_var(var_abs)
                    var_rel_str = _fmt_var(var_rel, pct=True)
                    color_abs = _color_var(var_abs)
                    color_rel = _color_var(var_rel)
                elif velas and len(velas) == 1:
                    ultimo_precio = f"{velas[-1]['cierre']:,.2f}"
 
                st.markdown(f"""
                <div class="seg-row {sel_style}">
                    <div class="seg-cell seg-cell-sym" style="color:rgb(184 184 184);font-weight:500">{a["simbolo"]}</div>
                    <div class="seg-cell seg-cell-num">{ultimo_precio}</div>
                    <div class="seg-cell seg-cell-num" style="color:{color_abs}">{var_abs_str}</div>
                    <div class="seg-cell seg-cell-num" style="color:{color_rel}">{var_rel_str}</div>
                </div>
                """, unsafe_allow_html=True)
 
                csel, cx = st.columns([2, 1])
                with csel:
                    if i != idx:
                        if st.button("seleccionar", key=f"sel_{i}", use_container_width=True, type="secondary"):
                            st.session_state.seg_activo_idx = i
                            st.rerun()
                with cx:
                    if st.button("eliminar", key=f"del_{i}", use_container_width=True):
                        eliminar_seguimiento(a["ticker"])
                        st.session_state.seg_activos = [
                            _activo_vacio(x["ticker"], x.get("nombre", x["ticker"]))
                            for x in listar_seguimientos()
                        ]
                        st.session_state.seg_activo_idx = max(0, idx - 1)
                        st.rerun()
        else:
            st.markdown(
                "<div style='color:#4b5563;font-size:12px;font-family:IBM Plex Mono,monospace;padding:12px 0'>"
                "Sin activos en seguimiento.</div>",
                unsafe_allow_html=True,
            )

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        # Card activo seleccionado
        if activo:
            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
 
            velas_card = get_velas(activo["ticker"], timeframe="1Min", limite=2)
            precio_str = "--"
            var_abs_card = var_rel_card = None
 
            if velas_card and len(velas_card) >= 2:
                ultimo = velas_card[-1]["cierre"]
                anterior = velas_card[-2]["cierre"]
                var_abs_card = ultimo - anterior
                var_rel_card = (var_abs_card / anterior * 100) if anterior else 0
                precio_str = f"{ultimo:,.2f}"
            elif velas_card and len(velas_card) == 1:
                precio_str = f"{velas_card[-1]['cierre']:,.2f}"
 
            det = get_detalles(activo["ticker"])
            tipo = det.get("sector", "--") if det else "--"
            nombre = det.get("nombre", activo["nombre"]) if det else activo["nombre"]
            color_abs = _color_var(var_abs_card)
            color_rel = _color_var(var_rel_card)
 
            st.markdown(f"""
            <div class="activo-card">
                <div class="activo-card-simbolo">{activo["ticker"]}</div>
                <div class="activo-card-nombre">{nombre}</div>
                <div class="activo-card-tipo">{tipo}</div>
                <div class="activo-card-precio">{precio_str} <span style="font-size:13px;color:#6b7280">USD</span></div>
                <div class="activo-card-vars">
                    <span style="color:{color_abs}">{_fmt_var(var_abs_card)}</span>
                    &nbsp;
                    <span style="color:{color_rel}">{_fmt_var(var_rel_card, pct=True)}</span>
                </div>
                <div class="activo-card-meta">Última act. {datetime.utcnow().strftime('%H:%M UTC')}</div>
                <!-- <span class="badge-mercado-open">● Mercado abierto</span> -->
            </div>
            """, unsafe_allow_html=True)

        #--- <hr> ---
        st.markdown('<hr class="panel-sep">', unsafe_allow_html=True)

        # Buscador
        buscar_col, btn_col = st.columns([5, 1])
        with buscar_col:
            query = st.text_input(
                "buscar", placeholder="Buscar símbolo...",
                label_visibility="collapsed", key="seg_busqueda_input",
                on_change=_on_busqueda_change,
            )
        with btn_col:
            if st.button("🔍", key="btn_buscar", use_container_width=True):
                _ejecutar_busqueda(query)

        # Resultados de búsqueda
        if st.session_state.seg_resultados:
            for r in st.session_state.seg_resultados:
                if r["ticker"] == "Sin resultados":
                    st.markdown(
                        '<div class="resultado-item" style="color:rgb(134 151 174)">Sin resultados</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    label = f"{r['ticker']} - {r['nombre']}" if r.get("nombre") else r["ticker"]
                    if st.button(label, key=f"add_{r['ticker']}", use_container_width=True):
                        ok = añadir_seguimiento(r["ticker"], r.get("nombre", r["ticker"]))
                        if ok:
                            st.session_state.seg_activos = [
                                _activo_vacio(x["ticker"], x.get("nombre", x["ticker"]))
                                for x in listar_seguimientos()
                            ]
                            st.session_state.seg_resultados = []
                            st.session_state.seg_activo_idx = len(st.session_state.seg_activos) - 1
                        st.rerun()
