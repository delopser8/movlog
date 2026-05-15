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
from backend.services.ui.user_service import get_velas, get_noticias, get_fluctuaciones


# --- HELPERS ---
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

def _color_var(var) -> str:
    if var and var > 0: return "#22c55e"
    if var and var < 0: return "#ef4444"
    return "#6b7280"

def _fmt_var(var: float) -> str:
    signo = "+" if var > 0 else ""
    return f"{signo}{var:.2f}%"


# --- GRÁFICO DE LÍNEAS ---
def _grafico_lineas(df: pd.DataFrame, simbolo: str, noticias_fluct: list) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["timestamp"], y=df["cierre"],
        mode="lines", name=simbolo,
        line=dict(color="#3b82f6", width=1.5),
        hovertemplate="<b>%{x}</b><br>Precio: %{y:,.2f}<extra></extra>",
    ))
    for n in noticias_fluct:
        if df.empty:
            continue
        idx = (df["timestamp"] - n["fecha_noticia"]).abs().idxmin()
        row = df.iloc[idx]
        color_m = _color_var(n["var_pct"] or 0)
        fig.add_trace(go.Scatter(
            x=[row["timestamp"]], y=[row["cierre"]],
            mode="markers", name="",
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
        paper_bgcolor="#0d0f11", plot_bgcolor="#0d0f11",
        font=dict(family="IBM Plex Mono", color="#6b7280", size=11),
        margin=dict(l=0, r=0, t=8, b=0), height=280,
        xaxis=dict(gridcolor="#1e2329", showgrid=True, zeroline=False, tickfont=dict(size=10)),
        yaxis=dict(gridcolor="#1e2329", showgrid=True, zeroline=False, tickfont=dict(size=10), side="right"),
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
        annotations=[dict(text=msg, x=0.5, y=0.5, xref="paper", yref="paper",
                          showarrow=False, font=dict(color="#4b5563", size=12, family="IBM Plex Mono"))],
    )
    return fig


# --- CSS ---
CSS_NOTICIAS = '''
<style>
.tf-info-badge {
    display: inline-flex; align-items: center; gap: 6px;
    font-family: 'IBM Plex Mono', monospace; font-size: 11px;
    color: #4b5563; margin-bottom: 8px;
}
.tf-label {
    background: #1a2236; color: #3b82f6;
    padding: 2px 8px; border-radius: 4px; font-size: 11px;
}
.noticias-col-titulo {
    font-family: 'IBM Plex Mono', monospace; font-size: 11px;
    color: #4b5563; text-transform: uppercase; letter-spacing: 0.05em;
    margin-bottom: 8px; padding-bottom: 4px; border-bottom: 1px solid #1e2329;
}
.noticia-card {
    background: #111417; border: 1px solid #1e2329;
    border-radius: 8px; padding: 12px 14px; margin-bottom: 4px;
}
.noticia-card-expanded {
    background: #111417; border: 1px solid #1e2329;
    border-top: none; border-radius: 0 0 8px 8px;
    padding: 12px 14px; margin-top: 0; margin-bottom: 8px;
}
.noticia-header {
    display: flex; justify-content: space-between;
    align-items: flex-start; gap: 8px; margin-bottom: 6px;
}
.noticia-titulo {
    font-family: 'IBM Plex Sans', sans-serif; font-size: 13px;
    font-weight: 500; color: #e8eaed; line-height: 1.4; flex: 1;
}
.noticia-badge {
    font-family: 'IBM Plex Mono', monospace; font-size: 11px;
    font-weight: 500; padding: 2px 6px; border-radius: 4px;
    white-space: nowrap; flex-shrink: 0;
}
.noticia-meta {
    font-family: 'IBM Plex Mono', monospace; font-size: 10px; color: #4b5563;
}
.ndot {
    width: 7px; height: 7px; border-radius: 50%;
    display: inline-block; margin-right: 4px; vertical-align: middle;
}
.noticia-explicacion {
    font-family: 'IBM Plex Sans', sans-serif; font-size: 12px;
    color: #9ca3af; line-height: 1.5;
}
.noticia-sep {
    border-top: 1px solid rgba(49, 51, 63, 0.2) !important; 
    margin: 5px 0 !important;
}
.noticia-link {
    font-family: 'IBM Plex Mono', monospace; font-size: 10px;
    color: #3b82f6; text-decoration: none; margin-top: 8px; display: inline-block;
}
.noticia-link:hover { text-decoration: underline; }
</style>
'''


# --- CARD ---
def _card_noticia(n: dict, key_prefix: str = ""):
    estado_key = f"noticia_expandida_{n['noticia_id']}"
    if estado_key not in st.session_state:
        st.session_state[estado_key] = False
    expandida = st.session_state[estado_key]

    color_sc = _color_score(n["score"])
    fecha_str = _fmt_fecha(n["fecha_noticia"])
    score_str = f"{n['score']:+.2f}"

    badge = ""
    if n["var_pct"] is not None:
        cv = _color_var(n["var_pct"])
        bg = "#052e16" if n["var_pct"] > 0 else "#1f0707"
        badge = f'<span class="noticia-badge" style="color:{cv};background:{bg}">{_fmt_var(n["var_pct"])}</span>'

    html = (
        '<div class="noticia-card">'
        '<div class="noticia-header">'
        f'<div class="noticia-titulo">{n["titulo"]}</div>'
        f'{badge}'
        '</div>'
        '<div class="noticia-meta">'
        f'<span class="ndot" style="background:{color_sc}"></span>'
        f'{n["origen"]} &middot; {fecha_str} &middot; score {score_str}'
        '</div>'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)

    if expandida:
        texto = n["explicacion"] or n["body"] or ""
        link = ""
        if n.get("url"):
            link = f'<a href="{n["url"]}" target="_blank" class="noticia-link">&#8599; Ver artículo original</a>'
        exp_html = (
            '<div class="noticia-card-expanded">'
            f'<div class="noticia-explicacion">{texto}</div>'
            f'{link}'
            '</div>'
        )
        st.markdown(exp_html, unsafe_allow_html=True)

    label = "▲ Ver menos" if expandida else "▼ Ver más"
    if st.button(label, key=f"{key_prefix}_{n['noticia_id']}"):
        st.session_state[estado_key] = not expandida
        st.rerun()
    
    # -- <hr> --
    st.markdown('<hr class="noticia-sep">', unsafe_allow_html=True)


# --- RENDER ---
def render_noticias(ticker: str):
    st.markdown(CSS_NOTICIAS, unsafe_allow_html=True)

    # datos desde FastAPI
    fluctuaciones      = get_fluctuaciones(ticker, limite=10)
    noticias_recientes = get_noticias(ticker, limite=20)

    # filtrar noticias recientes que no sean fluctuaciones explicadas
    ids_fluct = {n["noticia_id"] for n in fluctuaciones}
    noticias_recientes = [n for n in noticias_recientes if n["noticia_id"] not in ids_fluct]

    def _normalizar(n: dict, es_fluctuacion: bool) -> dict:
        from datetime import datetime
        fecha = n.get("fecha_noticia")
        if isinstance(fecha, str):
            try:
                fecha = datetime.fromisoformat(fecha)
            except Exception:
                fecha = datetime.utcnow()
        return {
            "noticia_id":    n.get("noticia_id", ""),
            "titulo":        n.get("titulo", ""),
            "url":           n.get("url", ""),
            "origen":        n.get("origen", ""),
            "body":          n.get("body", ""),
            "fecha_noticia": fecha,
            "score":         n.get("score") or 0.0,
            "tipo":          n.get("tipo") or "neutral",
            "var_pct":       n.get("var_pct"),
            "explicacion":   n.get("explicacion"),
            "es_fluctuacion": es_fluctuacion,
        }

    fluct_norm    = [_normalizar(n, True)  for n in fluctuaciones]
    recientes_norm = [_normalizar(n, False) for n in noticias_recientes]

    noticias_fluct    = fluct_norm
    noticias_recientes = recientes_norm

    st.markdown(
        '<div class="tf-info-badge">Gráfico en formato de velas de<span class="tf-label">5Min</span>'
        ' <span title="El timeframe de 5 minutos ofrece el mejor balance entre granularidad'
        ' y legibilidad para correlacionar noticias con movimientos de precio.">'
        'ℹ️</span></div>',
        unsafe_allow_html=True,
    )

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

    # --- COLUMNAS: (noticias de fluctuaciones explicadas / noticias recientes) ---
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