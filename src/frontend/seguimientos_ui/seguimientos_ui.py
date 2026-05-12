'''
    UI de la sección de seguimientos
'''

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


# --- MOCK DATA (luego cambiar por los resultados reales) ---
ACTIVOS_SEGUIMIENTO = [
    {
        "simbolo": "BTC-USD",
        "nombre": "Bitcoin",
        "tipo": "Criptomoneda",
        "ultimo": 70000.23,
        "var_abs": -5.02,
        "var_rel": -2.02,
        "ultima_act": "01:59 GMT+2",
        "mercado_abierto": True,
        "sector": "—",
        "industria": "—",
        "url": "bitcoin.org",
        "ticker": "BTC-USD",
        "cierre_diario": 70005.25, "cierre_semanal": 68200.00, "cierre_mensual": 62100.00,
        "apertura_diaria": 70100.00, "apertura_semanal": 68500.00, "apertura_mensual": 61800.00,
        "maximo_diario": 71200.00, "maximo_semanal": 72000.00, "maximo_mensual": 73500.00,
        "minimo_diario": 69500.00, "minimo_semanal": 67000.00, "minimo_mensual": 58000.00,
        "ratio_pe": "—", "eps": "—", "market_cap": "1.38T", "dividend_yield": "—",
        "esg_score": "—", "operacion_recomendada": "Compra", "target_price": 75000.00,
        "fecha_dividendo": "—", "splits": "—",
    },
    {
        "simbolo": "BRK.B",
        "nombre": "Berkshire Hathaway Inc. Class B",
        "tipo": "Finanzas",
        "ultimo": 450.23,
        "var_abs": -8.02,
        "var_rel": -2.02,
        "ultima_act": "01:59 GMT+2",
        "mercado_abierto": False,
        "sector": "Finanzas",
        "industria": "Seguros patrimoniales y de accidentes",
        "url": "berkshirehathaway.com",
        "ticker": "BRK.B",
        "cierre_diario": 458.25, "cierre_semanal": 455.00, "cierre_mensual": 440.00,
        "apertura_diaria": 459.00, "apertura_semanal": 453.00, "apertura_mensual": 438.00,
        "maximo_diario": 461.00, "maximo_semanal": 465.00, "maximo_mensual": 470.00,
        "minimo_diario": 448.00, "minimo_semanal": 445.00, "minimo_mensual": 430.00,
        "ratio_pe": "21.4", "eps": "21.07", "market_cap": "985.2B", "dividend_yield": "—",
        "esg_score": "62 / 100", "operacion_recomendada": "Holdea", "target_price": 480.00,
        "fecha_dividendo": "—", "splits": "—",
    },
]

RESULTADOS_BUSQUEDA = ["BITCOIN", "SP500", "NASDAQ", "GOLD", "AAPL"]

def _mock_velas(simbolo: str) -> pd.DataFrame:          # <-- GENERADOR DE DATOS DE PRUEBA PARA EL GRÁFICO DE VELAS (OHLCV)
    """Genera datos OHLCV de prueba para el gráfico de velas."""
    np.random.seed(hash(simbolo) % 9999)
    n = 120
    fechas = [datetime.today() - timedelta(days=n - i) for i in range(n)]
    base = 70000 if "BTC" in simbolo else 455
    precios = base + np.cumsum(np.random.randn(n) * (base * 0.012))
    datos = []
    for i, fecha in enumerate(fechas):
        open_ = precios[i]
        close = precios[i] + np.random.randn() * base * 0.008
        high = max(open_, close) + abs(np.random.randn()) * base * 0.005
        low = min(open_, close) - abs(np.random.randn()) * base * 0.005
        vol = abs(np.random.randn()) * 1e6
        datos.append({"fecha": fecha, "open": open_, "high": high, "low": low, "close": close, "vol": vol})
    return pd.DataFrame(datos)


# --- HELPERS VISUALES ---
# color número -> POSITIVO (verde) | NEGATIVO (rojo) | NEUTRO (gris)
def _color_var(val: float) -> str:
    if val > 0:
        return "#22c55e"
    if val < 0:
        return "#ef4444"
    return "#6b7280"

# formato número -> añade signo +/-, separador de 'miles', 2 decimales, opcionalmente añade % al final
def _fmt_var(val: float, pct: bool = False) -> str: 
    signo = "+" if val > 0 else ""
    sufijo = "%" if pct else ""
    return f"{signo}{val:,.2f}{sufijo}"

# gráfico de velas (Plotly), con colores personalizados y diseño adaptado al tema oscuro
def _grafico_velas(df: pd.DataFrame, simbolo: str) -> go.Figure:
    fig = go.Figure()

    colores_subida = "#22c55e"
    colores_bajada = "#ef4444"

    fig.add_trace(go.Candlestick(
        x=df["fecha"],
        open=df["open"],
        high=df["high"],
        low=df["low"],
        close=df["close"],
        name=simbolo,
        increasing_line_color=colores_subida,
        decreasing_line_color=colores_bajada,
        increasing_fillcolor=colores_subida,
        decreasing_fillcolor=colores_bajada,
        line=dict(width=1),
    ))

    fig.add_trace(go.Bar(
        x=df["fecha"],
        y=df["vol"],
        name="Volumen",
        marker_color=[
            colores_subida if c >= o else colores_bajada
            for c, o in zip(df["close"], df["open"])
        ],
        opacity=0.35,
        yaxis="y2",
    ))

    fig.update_layout(
        paper_bgcolor="#0d0f11",
        plot_bgcolor="#0d0f11",
        font=dict(family="IBM Plex Mono", color="#6b7280", size=11),
        margin=dict(l=0, r=0, t=8, b=0),
        height=320,
        xaxis=dict(
            rangeslider=dict(visible=False),
            gridcolor="#1e2329",
            showgrid=True,
            zeroline=False,
            tickfont=dict(size=10),
        ),
        yaxis=dict(
            gridcolor="#1e2329",
            showgrid=True,
            zeroline=False,
            tickfont=dict(size=10),
            side="right",
        ),
        yaxis2=dict(
            overlaying="y",
            side="left",
            showgrid=False,
            showticklabels=False,
        ),
        legend=dict(
            orientation="h",
            x=0, y=1.02,
            font=dict(size=10),
        ),
        xaxis_rangeslider_visible=False,
    )
    return fig


# --- CSS de SEGUIMIENTOS ---
CSS = """
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
    color: #e8eaed;
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
    color: #4b5563;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 3px;
}
.info-value {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 12px;
    color: #c9cdd4;
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
    color: #e8eaed;
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
    color: rgb(112 113 114);
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

/* Botones de fila — sel y del */
.st-emotion-cache-3pwa5w.e1rw0b1u1:in(.seg-row) + .st-emotion-cache-18kf3ut .stHorizontalBlock.st-emotion-cache-1permvm.e1rw0b1u3 {
    scale: 0.7;
}
.st-emotion-cache-3pwa5w.e1rw0b1u1:in(.seg-row) + .st-emotion-cache-18kf3ut .stHorizontalBlock.st-emotion-cache-1permvm.e1rw0b1u3 p{
    font-size: 1.1em;
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
    color: #6b7280;
    margin-bottom: 8px;
}
.activo-card-tipo {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10px;
    color: #4b5563;
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
    color: #4b5563;
    margin-bottom: 4px;
}
.badge-mercado-open   { background: #052e16; color: #22c55e; font-size: 10px; padding: 2px 8px; border-radius: 20px; font-family: 'IBM Plex Mono', monospace; }
.badge-mercado-closed { background: #4f4200; color: #dab600; font-size: 10px; padding: 2px 8px; border-radius: 20px; font-family: 'IBM Plex Mono', monospace; }
</style>
"""


# --- RENDER PRINCIPAL ---
def render():
    st.markdown(CSS, unsafe_allow_html=True)

    # estado de sesión
    if "seg_tab" not in st.session_state:
        st.session_state.seg_tab = "general"
    if "seg_activo_idx" not in st.session_state:
        st.session_state.seg_activo_idx = 0
    if "seg_activos" not in st.session_state:
        st.session_state.seg_activos = ACTIVOS_SEGUIMIENTO.copy()
    if "seg_busqueda" not in st.session_state:
        st.session_state.seg_busqueda = ""
    if "seg_resultados" not in st.session_state:
        st.session_state.seg_resultados = []

    activos = st.session_state.seg_activos
    idx = min(st.session_state.seg_activo_idx, len(activos) - 1) if activos else 0
    activo = activos[idx] if activos else None

    # Layout: col izquierda (2/3) + col derecha (1/3)
    col_izq, col_der = st.columns([2, 1], gap="large")

    # +++ BLOQUE IZQUIERDO +++
    with col_izq:

        # Tabs General / Noticias
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
                    "</div>",
                    unsafe_allow_html=True,
                )
            else:
                # Gráfico de velas
                with st.container():
                    st.markdown('<div class="chart-wrap">', unsafe_allow_html=True)
                    df = _mock_velas(activo["simbolo"])
                    fig = _grafico_velas(df, activo["simbolo"])
                    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
                    st.markdown("</div>", unsafe_allow_html=True)

                # Info del activo
                st.markdown(
                    f'<div class="activo-titulo">Sobre {activo["nombre"]}</div>',
                    unsafe_allow_html=True,
                )

                rec = activo["operacion_recomendada"].lower()
                badge_cls = f"badge-{rec}"
                badge_html = f'<span class="{badge_cls}">{activo["operacion_recomendada"]}</span>'

                # formateo de números seguro según si es número eltero-decimal / string  
                def safe_fmt(val):
                    if isinstance(val, (int, float)):
                        return f"{val:,.2f}"
                    return str(val)

                grid_html = f"""
                <div class="info-grid">
                    <div class="info-cell">
                        <div class="info-label">Ticker</div>
                        <div class="info-value">{activo["ticker"]}</div>
                    </div>
                    <div class="info-cell">
                        <div class="info-label">Sitio web</div>
                        <div class="info-value"><a href="https://{activo['url']}" target="_blank">{activo['url']} ↗</a></div>
                    </div>
                    <div class="info-cell">
                        <div class="info-label">Sector</div>
                        <div class="info-value">{activo["sector"]}</div>
                    </div>
                    <div class="info-cell">
                        <div class="info-label">Industria</div>
                        <div class="info-value">{activo["industria"]}</div>
                    </div>
                    <div class="info-cell">
                        <div class="info-label">Cierre ajust. diario</div>
                        <div class="info-value">{safe_fmt(activo["cierre_diario"])}</div>
                    </div>
                    <div class="info-cell">
                        <div class="info-label">Cierre ajust. semanal</div>
                        <div class="info-value">{safe_fmt(activo["cierre_semanal"])}</div>
                    </div>
                    <div class="info-cell">
                        <div class="info-label">Cierre ajust. mensual</div>
                        <div class="info-value">{safe_fmt(activo["cierre_mensual"])}</div>
                    </div>
                    <div class="info-cell">
                        <div class="info-label">Apertura diaria</div>
                        <div class="info-value">{safe_fmt(activo["apertura_diaria"])}</div>
                    </div>
                    <div class="info-cell">
                        <div class="info-label">Ratio P/E</div>
                        <div class="info-value">{activo["ratio_pe"]}</div>
                    </div>
                    <div class="info-cell">
                        <div class="info-label">Market Cap</div>
                        <div class="info-value">{activo["market_cap"]}</div>
                    </div>
                    <div class="info-cell">
                        <div class="info-label">Recomendación</div>
                        <div class="info-value">{badge_html}</div>
                    </div>
                    <div class="info-cell">
                        <div class="info-label">Precio objetivo</div>
                        <div class="info-value">{safe_fmt(activo["target_price"])}</div>
                    </div>
                </div>
                """
                st.markdown(grid_html, unsafe_allow_html=True)

        # --- TAB NOTICIAS ---
        else:
            st.markdown(
                "<div style='color:#4b5563;font-size:13px;padding:2rem 0;text-align:center'>"
                "Sección de noticias — próximamente."
                "</div>",
                unsafe_allow_html=True,
            )

    # +++ BLOQUE DERECHO +++
    with col_der:

        # Título
        st.markdown('<div class="panel-titulo">Activos en seguimiento</div>', unsafe_allow_html=True)
        st.markdown('<hr class="panel-sep">', unsafe_allow_html=True)

        # Tabla de activos en seguimiento
        if activos:
            # Cabecera
            st.markdown("""
            <div class="seg-row seg-header">
                <div class="seg-cell seg-cell-sym">Símbolo</div>
                <div class="seg-cell seg-cell-num">Último</div>
                <div class="seg-cell seg-cell-num">Var. Abs.</div>
                <div class="seg-cell seg-cell-num">Var. Rel.</div>
                <div class="seg-cell seg-cell-x"></div>
            </div>
            """, unsafe_allow_html=True)

            for i, a in enumerate(activos):
                sel_style = "seg-row-selected" if i == idx else ""
                color_abs = _color_var(a["var_abs"])
                color_rel = _color_var(a["var_rel"])

                st.markdown(f"""
                <div class="seg-row {sel_style}">
                    <div class="seg-cell seg-cell-sym" style="color:rgb(112 113 114);font-weight:500">{a["simbolo"]}</div>
                    <div class="seg-cell seg-cell-num">{a["ultimo"]:,.2f}</div>
                    <div class="seg-cell seg-cell-num" style="color:{color_abs}">{_fmt_var(a["var_abs"])}</div>
                    <div class="seg-cell seg-cell-num" style="color:{color_rel}">{_fmt_var(a["var_rel"], pct=True)}</div>
                </div>
                """, unsafe_allow_html=True)

                csel, cx = st.columns([2, 1])
                with csel:
                    if i != idx:
                        if st.button("seleccionar", key=f"sel_{i}", use_container_width=True,
                                     type="secondary"):
                            st.session_state.seg_activo_idx = i
                            st.rerun()
                with cx:
                    if st.button("eliminar", key=f"del_{i}", use_container_width=True):
                        st.session_state.seg_activos.pop(i)
                        st.session_state.seg_activo_idx = max(0, idx - 1)
                        st.rerun()
        else:
            st.markdown(
                "<div style='color:#4b5563;font-size:12px;font-family:IBM Plex Mono,monospace;"
                "padding:12px 0'>Sin activos en seguimiento.</div>",
                unsafe_allow_html=True,
            )

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        # Buscador
        buscar_col, btn_col = st.columns([5, 1])
        with buscar_col:
            query = st.text_input(
                "buscar",
                placeholder="buscar activo...",
                label_visibility="collapsed",
                key="seg_busqueda_input",
            )
        with btn_col:
            buscar = st.button("🔍", key="btn_buscar", use_container_width=True)

        if buscar and query:
            # Mock: filtra por texto. Aquí irá la llamada real a yfinance/Alpaca.
            st.session_state.seg_resultados = [
                r for r in RESULTADOS_BUSQUEDA if query.upper() in r
            ] or ["Sin resultados"]

        # Resultados de búsqueda
        if st.session_state.seg_resultados:
            items_html = '<div class="resultados-wrap">'
            for r in st.session_state.seg_resultados:
                items_html += f'<div class="resultado-item">{r}</div>'
            items_html += "</div>"
            st.markdown(items_html, unsafe_allow_html=True)

            # Botones para añadir resultado (uno por resultado)
            for r in st.session_state.seg_resultados:
                if r == "Sin resultados":
                    continue
                if st.button(f"+ Añadir {r}", key=f"add_{r}", use_container_width=True):
                    nuevo = {
                        "simbolo": r, "nombre": r, "tipo": "—",
                        "ultimo": 0.0, "var_abs": 0.0, "var_rel": 0.0,
                        "ultima_act": "—", "mercado_abierto": False,
                        "sector": "—", "industria": "—", "url": "—", "ticker": r,
                        "cierre_diario": 0, "cierre_semanal": 0, "cierre_mensual": 0,
                        "apertura_diaria": 0, "apertura_semanal": 0, "apertura_mensual": 0,
                        "maximo_diario": 0, "maximo_semanal": 0, "maximo_mensual": 0,
                        "minimo_diario": 0, "minimo_semanal": 0, "minimo_mensual": 0,
                        "ratio_pe": "—", "eps": "—", "market_cap": "—", "dividend_yield": "—",
                        "esg_score": "—", "operacion_recomendada": "Holdea", "target_price": 0,
                        "fecha_dividendo": "—", "splits": "—",
                    }
                    st.session_state.seg_activos.append(nuevo)
                    st.session_state.seg_resultados = []
                    st.rerun()

        # Card activo seleccionado (fondo del panel)
        if activo:
            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
            color_abs = _color_var(activo["var_abs"])
            color_rel = _color_var(activo["var_rel"])
            mercado_badge = (
                '<span class="badge-mercado-open">● Mercado abierto</span>'
                if activo["mercado_abierto"]
                else '<span class="badge-mercado-closed">● Mercado cerrado</span>'
            )

            card_html = f"""
            <div class="activo-card">
                <div class="activo-card-simbolo">{activo["simbolo"]}</div>
                <div class="activo-card-nombre">{activo["nombre"]}</div>
                <div class="activo-card-tipo">{activo["tipo"]}</div>
                <div class="activo-card-precio">{activo["ultimo"]:,.2f} <span style="font-size:13px;color:#6b7280">USD</span></div>
                <div class="activo-card-vars">
                    <span style="color:{color_abs}">{_fmt_var(activo["var_abs"])}</span>
                    &nbsp;
                    <span style="color:{color_rel}">{_fmt_var(activo["var_rel"], pct=True)}</span>
                </div>
                <div class="activo-card-meta">Última act. {activo["ultima_act"]}</div>
                {mercado_badge}
            </div>
            """
            st.markdown(card_html, unsafe_allow_html=True)