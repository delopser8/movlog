'''
    entrada principal de Streamlit (UI principal de Movlog)

    desde aquí se llama a cada sección de la UI de manera centralizada:
        - seguimientos_ui.py
        - alertas_ui.py
        - infraestructura_ui.py
        - ai_models_ui.py
        - configuracion_ui.py
'''

import streamlit as st

from seguimientos_ui.seguimientos_ui import render as render_seguimientos
from infraestructura_ui.infraestructura_ui import render as render_infraestructura
from ai_models_ui.ai_models_ui import render as render_modelos
from alertas_ui.alertas_ui import render as render_alertas
from configuracion_ui.configuracion_ui import render as render_configuracion


# --- configuración de página ---
st.set_page_config(
    page_title="Movlog",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- CSS global ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@300;400;500&display=swap');

/* Reset y base */
html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif;
    background-color: #0d0f11;
    color: #c9cdd4;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #111417 !important;
    border-right: 1px solid #1e2329 !important;
    min-width: 200px !important;
    max-width: 200px !important;
}
[data-testid="stSidebar"] > div:first-child {
    padding: 1.5rem 1rem 1rem;
}

/* Logo sidebar */
.sidebar-logo {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 18px;
    font-weight: 500;
    letter-spacing: 0.08em;
    color: #e8eaed;
    margin-bottom: 2rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid #1e2329;
}
.sidebar-logo span {
    color: #3b82f6;
}

/* Botones de navegación */
.nav-btn {
    display: flex;
    align-items: center;
    gap: 10px;
    width: 100%;
    padding: 8px 10px;
    margin-bottom: 2px;
    border-radius: 6px;
    border: none;
    background: transparent;
    color: #6b7280;
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 13px;
    font-weight: 400;
    cursor: pointer;
    text-align: left;
    transition: all 0.15s ease;
}
.nav-btn:hover, button[kind="secondary"]:hover {
    background-color: rgb(151 166 195 / 32%);
    color: white;
}
.nav-btn.active, button[kind="secondary"]:hover {
    background: #1a2236;
    color: #3b82f6;
    font-weight: 500;
}
.nav-icon {
    font-size: 15px;
    width: 18px;
    text-align: center;
}

/* ocultar botón de colapso */
[data-testid="stSidebarCollapseButton"] { display: none !important; }

/* sidebar como columna flex para poder empujar items al fondo */
[data-testid="stSidebar"] > div:first-child {
    padding: 1.5rem 1rem 1rem;
    display: flex;
    flex-direction: column;
    height: 100%;
}
            
/* Ocultar elementos nativos de Streamlit */
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stSidebarNav"] { display: none; }
            
/* Área de contenido principal */
.main .block-container {
    padding: 2rem 2.5rem;
    max-width: 100%;
}

/* Títulos de sección */
h2 {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 20px !important;
    font-weight: 500 !important;
    color: #e8eaed !important;
    letter-spacing: 0.02em;
    margin-bottom: 0.25rem !important;
}
.stCaption {
    color: #4b5563 !important;
    font-size: 12px !important;
}

/* Separador lateral del sidebar inferior */
.sidebar-footer {
    position: absolute;
    bottom: 1.5rem;
    left: 1rem;
    right: 1rem;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10px;
    color: #2d3748;
    text-align: left;
}
</style>
""", unsafe_allow_html=True)


# --- estado de sesión ---
if "seccion_activa" not in st.session_state:
    st.session_state.seccion_activa = "seguimientos"


# --- sidebar ---
with st.sidebar:
    st.markdown('<div class="sidebar-logo">MOV<span>LOG</span></div>', unsafe_allow_html=True)

    nav_top = [
        ("seguimientos",    "", "Seguimientos"),
        ("infraestructura", "", "Infraestructura"),
        ("modelos",         "", "Modelos"),
    ]

    nav_bottom = [
        ("alertas",        "", "Alertas"),
        ("configuracion",  "", "Configuración"),
    ]

    for key, icon, label in nav_top:
        clicked = st.button(f"{icon}  {label}", key=f"nav_{key}", use_container_width=True)
        if clicked:
            st.session_state.seccion_activa = key
            st.rerun()

    # empuja alertas y configuración al fondo
    st.markdown('<div style="flex: 1;"></div>', unsafe_allow_html=True)

    for key, icon, label in nav_bottom:
        clicked = st.button(f"{icon}  {label}", key=f"nav_{key}", use_container_width=True)
        if clicked:
            st.session_state.seccion_activa = key
            st.rerun()


# --- renderizado de sección activa ---
seccion = st.session_state.seccion_activa

if seccion == "seguimientos":
    render_seguimientos()
elif seccion == "infraestructura":
    render_infraestructura()
elif seccion == "modelos":
    render_modelos()
elif seccion == "alertas":
    render_alertas()
elif seccion == "configuracion":
    render_configuracion()