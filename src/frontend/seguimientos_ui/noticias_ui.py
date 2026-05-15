'''
    UI de la sección de noticias (tab "noticias" dentro de seguimientos)
    - gráfico de líneas 5Min con marcadores de fluctuaciones explicadas
    - listas de noticias (fluctuaciones explicadas y noticias recientes)
'''

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta

from backend.services.ui.user_service import get_velas


# --- MOCK DATA (reemplazar con datos reales cuando el pipeline de noticias esté listo) ---
MOCK_NOTICIAS = [
    {
        "noticia_id": "a1b2c3",
        "titulo": "Fed mantiene tipos pero señala posibles recortes en Q3",
        "url": "https://bloomberg.com/fed-rates-2026",
        "origen": "NewsAPI / Bloomberg",
        "body": "La Reserva Federal mantuvo los tipos de interés sin cambios pero abrió la puerta a recortes en el tercer trimestre, lo que impulsó al mercado de renta variable con fuerza.",
        "fecha_noticia": datetime.utcnow() - timedelta(hours=3),
        "score": 0.82,
        "tipo": "positivo",
        "var_pct": 3.2,
        "explicacion": "La señal dovish de la Fed redujo el riesgo percibido en renta variable. Los inversores interpretaron el comunicado como un catalizador de subida para activos de riesgo, especialmente tecnología.",
        "es_fluctuacion": True,
    },
    {
        "noticia_id": "d4e5f6",
        "titulo": "Resultados trimestrales superan expectativas en un 12%",
        "url": "https://wsj.com/earnings-q1-2026",
        "origen": "NewsAPI / Wall Street Journal",
        "body": "Los resultados del primer trimestre han superado las estimaciones de los analistas en un 12%, impulsados por el crecimiento en servicios en la nube y márgenes récord.",
        "fecha_noticia": datetime.utcnow() - timedelta(hours=8),
        "score": 0.91,
        "tipo": "positivo",
        "var_pct": 5.1,
        "explicacion": "Los resultados por encima de consenso generaron un gap al alza en la apertura. El mercado descontó rápidamente la mejora de guidance para el resto del año fiscal.",
        "es_fluctuacion": True,
    },
    {
        "noticia_id": "g7h8i9",
        "titulo": "Reguladores europeos abren investigación antimonopolio",
        "url": "https://ft.com/antitrust-eu-2026",
        "origen": "Yahoo Finance RSS",
        "body": "La Comisión Europea ha abierto una investigación formal por posibles prácticas anticompetitivas en el mercado de servicios digitales.",
        "fecha_noticia": datetime.utcnow() - timedelta(hours=12),
        "score": -0.74,
        "tipo": "negativo",
        "var_pct": -1.8,
        "explicacion": "La incertidumbre regulatoria en Europa generó presión vendedora. Los inversores temen multas y cambios estructurales en el modelo de negocio.",
        "es_fluctuacion": True,
    },
    {
        "noticia_id": "j1k2l3",
        "titulo": "Análisis: perspectivas del sector tecnológico para 2026",
        "url": "https://forbes.com/tech-outlook-2026",
        "origen": "NewsAPI / Forbes",
        "body": "Los analistas prevén un año de consolidación para el sector tecnológico, con foco en rentabilidad frente al crecimiento.",
        "fecha_noticia": datetime.utcnow() - timedelta(hours=18),
        "score": 0.05,
        "tipo": "neutral",
        "var_pct": None,
        "explicacion": None,
        "es_fluctuacion": False,
    },
    {
        "noticia_id": "m4n5o6",
        "titulo": "Volúmenes de trading al alza en sesión asiática",
        "url": "https://reuters.com/asia-trading-2026",
        "origen": "Yahoo Finance RSS",
        "body": "Los mercados asiáticos registraron volúmenes superiores a la media en la sesión nocturna, con foco en semiconductores y energía.",
        "fecha_noticia": datetime.utcnow() - timedelta(hours=22),
        "score": 0.12,
        "tipo": "neutral",
        "var_pct": None,
        "explicacion": None,
        "es_fluctuacion": False,
    },
]


# --- FUNCIONES HELPERS ---
def _fmt_fecha(dt: datetime) -> str:
    delta = datetime.utcnow() - dt
    horas = int(delta.total_seconds() / 3600)
    if horas < 1:
        return "hace menos de 1h"
    if horas < 24:
        return f"hace {horas}h"
    return dt.strftime("%-d de %B")

def _color_score(score: float) -> str:
    if score > 0.2:  return "#22c55e"
    if score < -0.2: return "#ef4444"
    return "#6b7280"

def _color_var(var: float) -> str:
    if var > 0:  return "#22c55e"
    if var < 0:  return "#ef4444"
    return "#6b7280"

def _fmt_var(var: float) -> str:
    signo = "+" if var > 0 else ""
    return f"{signo}{var:.2f}%"


# --- GRÁFICO DE LÍNEAS 5Min ---
def _grafico_lineas(df: pd.DataFrame, simbolo: str, noticias_fluct: list) -> go.Figure:
    fig = go.Figure()

    # línea de precio (cierre) con hover personalizado
    fig.add_trace(go.Scatter(
        x=df["timestamp"],
        y=df["cierre"],
        mode="lines",
        name=simbolo,
        line=dict(color="#3b82f6", width=1.5),
        hovertemplate="<b>%{x}</b><br>Precio: %{y:,.2f}<extra></extra>",
    ))

    # marcadores de fluctuaciones explicadas
    if noticias_fluct:
        # aproximar el timestamp de la noticia al punto más cercano del gráfico
        for n in noticias_fluct:
            # busca la vela más cercana a la fecha de la noticia
            if df.empty:
                continue
            idx = (df["timestamp"] - n["fecha_noticia"]).abs().idxmin()
            row = df.iloc[idx]
            color_m = _color_var(n["var_pct"] or 0)

            fig.add_trace(go.Scatter(
                x=[row["timestamp"]],
                y=[row["cierre"]],
                mode="markers",
                name="",
                marker=dict(color=color_m, size=10, symbol="circle",
                            line=dict(color="#0d0f11", width=1.5)),
                hovertemplate=(
                    f"<b>{n['titulo'][:60]}...</b><br>"
                    f"Impacto: {_fmt_var(n['var_pct'] or 0)}<br>"
                    f"Score: {n['score']:+.2f}<extra></extra>"
                ),
                showlegend=False,
            ))

    fig.update_layout(
        paper_bgcolor="#0d0f11",
        plot_bgcolor="#0d0f11",
        font=dict(family="IBM Plex Mono", color="#6b7280", size=11),
        margin=dict(l=0, r=0, t=8, b=0),
        height=280,
        xaxis=dict(gridcolor="#1e2329", showgrid=True, zeroline=False, tickfont=dict(size=10)),
        yaxis=dict(gridcolor="#1e2329", showgrid=True, zeroline=False,
                   tickfont=dict(size=10), side="right"),
        legend=dict(orientation="h", x=0, y=1.02, font=dict(size=10)),
        hovermode="x unified",
    )
    return fig

def _grafico_vacio_lineas(msg: str) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        paper_bgcolor="#0d0f11", plot_bgcolor="#0d0f11", height=280,
        margin=dict(l=0, r=0, t=8, b=0),
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        annotations=[dict(
            text=msg, x=0.5, y=0.5, xref="paper", yref="paper",
            showarrow=False, font=dict(color="#4b5563", size=12, family="IBM Plex Mono"),
        )],
    )
    return fig


# --- CSS DE NOTICIAS ---
CSS_NOTICIAS = """
<style>
/* Info badge timeframe */
.tf-info-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    color: #4b5563;
    margin-bottom: 8px;
}
.tf-info-badge span.tf-label {
    background: #1a2236;
    color: #3b82f6;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
}

/* Columnas de noticias */
.noticias-col-titulo {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    color: #4b5563;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 8px;
    padding-bottom: 4px;
    border-bottom: 1px solid #1e2329;
}

/* Card de noticia */
.noticia-card {
    background: #111417;
    border: 1px solid #1e2329;
    border-radius: 8px;
    padding: 12px 14px;
    margin-bottom: 8px;
    transition: border-color 0.15s;
}
.noticia-card:hover { border-color: #2d3748; }
.noticia-card-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 8px;
    margin-bottom: 6px;
}
.noticia-titulo {
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 13px;
    font-weight: 500;
    color: #e8eaed;
    flex: 1;
    line-height: 1.4;
}
.noticia-badge-var {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 12px;
    font-weight: 500;
    padding: 2px 8px;
    border-radius: 4px;
    white-space: nowrap;
    flex-shrink: 0;
}
.noticia-meta {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10px;
    color: #4b5563;
    margin-bottom: 4px;
    display: flex;
    align-items: center;
    gap: 8px;
}
.noticia-score-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    display: inline-block;
    flex-shrink: 0;
}
.noticia-explicacion {
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 12px;
    color: #9ca3af;
    line-height: 1.5;
    margin-top: 8px;
    padding-top: 8px;
    border-top: 1px solid #1e2329;
}
.noticia-link {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10px;
    color: #3b82f6;
    text-decoration: none;
    margin-top: 6px;
    display: inline-block;
}
.noticia-link:hover { text-decoration: underline; }
</style>
"""


# --- CARD DE NOTICIA ---
def _card_noticia(n: dict, key_prefix: str = ""):
    color_var = _color_var(n["var_pct"] or 0)
    color_sc  = _color_score(n["score"])
    estado_key = f"noticia_expandida_{n['noticia_id']}"
    
    if estado_key not in st.session_state:
        st.session_state[estado_key] = False

    badge_var_html = ""
    if n["var_pct"] is not None:
        bg = "#052e16" if n["var_pct"] > 0 else "#1f0707"
        badge_var_html = f'<span class="noticia-badge-var" style="color:{color_var};background:{bg}">{_fmt_var(n["var_pct"])}</span>'

    expandida = st.session_state[estado_key]
    
    explicacion_html = ""
    if expandida:
        link_html = f'<a href="{n["url"]}" target="_blank" class="noticia-link">↗ Ver artículo original</a>' if n.get("url") else ""
        explicacion_html = f"""
        <div class="noticia-explicacion">{n["explicacion"] or n["body"]}</div>
        {link_html}
        """

    st.markdown(f"""
    <div class="noticia-card">
        <div class="noticia-card-header">
            <div class="noticia-titulo">{n["titulo"]}</div>
            {badge_var_html}
        </div>
        <div class="noticia-meta">
            <span class="noticia-score-dot" style="background:{color_sc}"></span>
            <span>{n["origen"]}</span>
            <span>&nbsp;·&nbsp;</span>
            <span>{_fmt_fecha(n["fecha_noticia"])}</span>
            <span>&nbsp;·&nbsp;</span>
            <span>score {n["score"]:+.2f}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    label = "▲ Ver menos" if expandida else "▼ Ver más"
    if st.button(label, key=f"{key_prefix}_{n['noticia_id']}", use_container_width=False):
        st.session_state[estado_key] = not st.session_state[estado_key]
        st.rerun()

    if expandida:
        link_html = f'<a href="{n["url"]}" target="_blank" class="noticia-link">↗ Ver artículo original</a>' if n.get("url") else ""
        st.markdown(f"""
        <div class="noticia-card" style="border-top:none;border-radius:0 0 8px 8px;margin-top:-8px">
            <div class="noticia-explicacion">{n["explicacion"] or n["body"]}</div>
            {link_html}
        </div>
        """, unsafe_allow_html=True)


# --- RENDER PRINCIPAL ---
def render_noticias(ticker: str):
    st.markdown(CSS_NOTICIAS, unsafe_allow_html=True)

    noticias_fluct  = [n for n in MOCK_NOTICIAS if n["es_fluctuacion"]]
    noticias_recientes = [n for n in MOCK_NOTICIAS if not n["es_fluctuacion"]]

    # badge de timeframe con info
    st.markdown("""
    <div class="tf-info-badge">
        Gráfico en
        <span class="tf-label">5Min</span>
        <span title="El timeframe de 5 minutos ofrece el mejor balance entre granularidad y legibilidad para correlacionar noticias con movimientos de precio. Timeframes menores generan demasiado ruido y los mayores pierden el impacto inmediato de la noticia.">ℹ️</span>
    </div>
    """, unsafe_allow_html=True)

    # gráfico de líneas
    velas_raw = get_velas(ticker, timeframe="5Min", limite=500)
    with st.container():
        st.markdown('<div class="chart-wrap">', unsafe_allow_html=True)
        if velas_raw:
            df = pd.DataFrame(velas_raw)
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.sort_values("timestamp").reset_index(drop=True)
            fig = _grafico_lineas(df, ticker, noticias_fluct)
        else:
            fig = _grafico_vacio_lineas("Cargando datos de precio...")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # --- COLUMNAS: fluctuaciones explicadas | noticias recientes ---
    col_fluct, col_recientes = st.columns([1, 1], gap="large")

    with col_fluct:
        st.markdown('<div class="noticias-col-titulo">📍 Fluctuaciones explicadas</div>', unsafe_allow_html=True)
        if noticias_fluct:
            for n in noticias_fluct:
                _card_noticia(n, key_prefix="fluct")
        else:
            st.markdown(
                "<div style='color:#4b5563;font-size:12px;font-family:IBM Plex Mono,monospace'>"
                "Sin fluctuaciones explicadas aún.</div>",
                unsafe_allow_html=True,
            )

    with col_recientes:
        st.markdown('<div class="noticias-col-titulo">📰 Noticias recientes</div>', unsafe_allow_html=True)
        if noticias_recientes:
            for n in noticias_recientes:
                _card_noticia(n, key_prefix="rec")
        else:
            st.markdown(
                "<div style='color:#4b5563;font-size:12px;font-family:IBM Plex Mono,monospace'>"
                "Sin noticias recientes.</div>",
                unsafe_allow_html=True,
            )