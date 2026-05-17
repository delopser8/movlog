'''
    UI de la sección de monitorización de Modelos de IA
    - distribución de sentimiento por activo (donut chart)
    - correlación sentimiento vs precio (gráfico dual-axis)
    - tabla de últimas inferencias
'''

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime

from backend.services.ui.user_service import listar_seguimientos, get_noticias


# --- CSS ---
CSS = '''
<style>
.modelos-section-title {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    color: rgb(139 146 157);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 8px;
    padding-bottom: 4px;
    border-bottom: 1px solid #1e2329;
}
.modelos-card {
    background: #111417;
    border: 1px solid #1e2329;
    border-radius: 8px;
    padding: 14px 16px;
    margin-bottom: 12px;
}
.modelos-stat {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 12px;
    background: #0d0f11;
    border: 1px solid #1e2329;
    border-radius: 6px;
    font-family: 'IBM Plex Mono', monospace;
}
.modelos-stat-val {
    font-size: 22px;
    font-weight: 600;
    color: #e8eaed;
}
.modelos-stat-label {
    font-size: 10px;
    color: rgb(139 146 157);
    margin-top: 2px;
    text-align: center;
}
.modelo-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: #1a2236;
    border: 1px solid #1e2329;
    border-radius: 6px;
    padding: 6px 10px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    color: #3b82f6;
    margin-bottom: 8px;
}
</style>
'''


def _color_score(score: float) -> str:
    if score > 0.2:  return "#22c55e"
    if score < -0.2: return "#ef4444"
    return "#6b7280"

def _fmt_fecha(fecha) -> str:
    try:
        if isinstance(fecha, str):
            fecha = datetime.fromisoformat(fecha)
        delta = datetime.now() - fecha
        h = int(delta.total_seconds() / 3600)
        m = int((delta.total_seconds() % 3600) / 60)
        if h > 0:
            return f"hace {h}h {m}min"
        return f"hace {m}min"
    except Exception:
        return str(fecha)

def _grafico_donut(positivo: int, neutral: int, negativo: int) -> go.Figure:
    fig = go.Figure(go.Pie(
        labels=["Positivo", "Neutral", "Negativo"],
        values=[positivo, neutral, negativo],
        hole=0.6,
        marker=dict(colors=["#22c55e", "#6b7280", "#ef4444"]),
        textinfo="percent",
        textfont=dict(family="IBM Plex Mono", size=11, color="#e8eaed"),
        hovertemplate="%{label}: %{value} noticias<extra></extra>",
    ))
    fig.update_layout(
        paper_bgcolor="#111417",
        plot_bgcolor="#111417",
        font=dict(family="IBM Plex Mono", color="#6b7280", size=11),
        margin=dict(l=0, r=0, t=8, b=8),
        height=220,
        legend=dict(
            orientation="v", x=1.0, y=0.5,
            font=dict(size=10, color="#9ca3af"),
        ),
        showlegend=True,
    )
    return fig


def render():
    st.markdown(CSS, unsafe_allow_html=True)

    # selector de activo
    seguimientos = listar_seguimientos()
    tickers = [s["ticker"] for s in seguimientos]
    if not tickers:
        st.markdown('<div style="color:rgb(139 146 157);font-family:IBM Plex Mono,monospace;font-size:12px">No hay activos en seguimiento.</div>', unsafe_allow_html=True)
        return

    ticker = st.selectbox("Activo", tickers, label_visibility="collapsed")

    noticias = get_noticias(ticker, limite=100)

    # --- stats globales ---
    con_score   = [n for n in noticias if n.get("score") and n["score"] != 0]
    con_expl    = [n for n in noticias if n.get("explicacion")]
    positivos   = len([n for n in con_score if (n.get("score") or 0) > 0.1])
    negativos   = len([n for n in con_score if (n.get("score") or 0) < -0.1])
    neutrales   = len([n for n in con_score if abs(n.get("score") or 0) <= 0.1])
    score_medio = sum(n["score"] for n in con_score) / len(con_score) if con_score else 0

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="modelos-stat"><div class="modelos-stat-val">{len(noticias)}</div><div class="modelos-stat-label">Noticias totales</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="modelos-stat"><div class="modelos-stat-val">{len(con_score)}</div><div class="modelos-stat-label">Analizadas FinBERT</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="modelos-stat"><div class="modelos-stat-val">{len(con_expl)}</div><div class="modelos-stat-label">Explicadas Qwen</div></div>', unsafe_allow_html=True)
    with col4:
        color_medio = _color_score(score_medio)
        st.markdown(f'<div class="modelos-stat"><div class="modelos-stat-val" style="color:{color_medio}">{score_medio:+.2f}</div><div class="modelos-stat-label">Score medio</div></div>', unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    col_izq, col_der = st.columns([1, 1], gap="large")

    with col_izq:
        st.markdown('<div class="modelos-section-title">Distribución de sentimiento</div>', unsafe_allow_html=True)
        if con_score:
            fig_donut = _grafico_donut(positivos, neutrales, negativos)
            st.plotly_chart(fig_donut, use_container_width=True, config={"displayModeBar": False})
        else:
            st.markdown('<div style="color:rgb(139 146 157);font-size:12px;font-family:IBM Plex Mono,monospace">Sin datos de sentimiento aún.</div>', unsafe_allow_html=True)

    with col_der:
        st.markdown('<div class="modelos-section-title">Modelos activos</div>', unsafe_allow_html=True)
        st.markdown('''
        <div class="modelos-card">
            <div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #1a1f26;font-family:IBM Plex Mono,monospace;font-size:12px">
                <span style="color:rgb(139 146 157);font-size:11px">Sentimiento</span><span style="color:#e8eaed">ProsusAI/FinBERT · HF Inference API</span>
            </div>
            <div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #1a1f26;font-family:IBM Plex Mono,monospace;font-size:12px">
                <span style="color:rgb(139 146 157);font-size:11px">Traducción</span><span style="color:#e8eaed">Qwen3.5 (0.8b) · Ollama</span>
            </div>
            <div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #1a1f26;font-family:IBM Plex Mono,monospace;font-size:12px">
                <span style="color:rgb(139 146 157);font-size:11px">Explicabilidad</span><span style="color:#e8eaed">Qwen3.5 (0.8b) · Ollama</span>
            </div>
            <div style="display:flex;justify-content:space-between;padding:5px 0;font-family:IBM Plex Mono,monospace;font-size:12px">
                <span style="color:rgb(139 146 157);font-size:11px">Observabilidad</span><span style="color:#e8eaed">Langfuse v2</span>
            </div>
        </div>
        ''', unsafe_allow_html=True)

    # --- tabla últimas inferencias ---
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    st.markdown('<div class="modelos-section-title">Últimas inferencias FinBERT</div>', unsafe_allow_html=True)

    if con_score:
        recientes = sorted(con_score, key=lambda x: x.get("fecha_noticia", ""), reverse=True)[:10]
        rows = []
        for n in recientes:
            score = n.get("score", 0)
            tipo  = n.get("tipo", "neutral")
            color = _color_score(score)
            rows.append({
                "Título":  n.get("titulo", "")[:60] + "...",
                "Origen":  n.get("origen", "--"),
                "Score":   f"{score:+.2f}",
                "Tipo":    tipo.capitalize(),
                "Fecha":   _fmt_fecha(n.get("fecha_noticia")),
            })
        df_tabla = pd.DataFrame(rows)
        st.dataframe(
            df_tabla,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Título": st.column_config.TextColumn(width="large"),
                "Score":  st.column_config.TextColumn(width="small"),
                "Tipo":   st.column_config.TextColumn(width="small"),
                "Fecha":  st.column_config.TextColumn(width="small"),
            }
        )
    else:
        st.markdown('<div style="color:rgb(139 146 157);font-size:12px;font-family:IBM Plex Mono,monospace">Sin inferencias recientes.</div>', unsafe_allow_html=True)