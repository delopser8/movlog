'''
    UI del panel de alertas
    - muestra las alertas configuradas en MongoDB
    - estado ON/OFF, umbral y descripción
    - banner sutil en la UI cuando hay alertas activas
'''


import streamlit as st
import psutil
from backend.services.ui.user_service import get_alertas


# --- CSS ---
CSS = '''
<style>
.alerta-card {
    background: #111417;
    border: 1px solid #1e2329;
    border-radius: 8px;
    padding: 16px 18px;
    margin-bottom: 10px;
}
.alerta-card-warning {
    border-left: 3px solid #f59e0b;
}
.alerta-card-critico {
    border-left: 3px solid #ef4444;
}
.alerta-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 6px;
}
.alerta-nombre {
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 13px;
    font-weight: 500;
    color: #e8eaed;
}
.alerta-badge-on {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10px;
    padding: 2px 8px;
    border-radius: 4px;
    background: #052e16;
    color: #22c55e;
}
.alerta-badge-off {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10px;
    padding: 2px 8px;
    border-radius: 4px;
    background: #1a1f26;
    color: #6b7280;
}
.alerta-desc {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    color: #6b7280;
    margin-bottom: 8px;
}
.alerta-umbral {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    color: #9ca3af;
}
.alerta-umbral-val {
    color: #f59e0b;
    font-weight: 500;
}
.alerta-tipo-badge {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10px;
    padding: 2px 6px;
    border-radius: 4px;
}
.section-title {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    color: #4b5563;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 10px;
    padding-bottom: 4px;
    border-bottom: 1px solid #1e2329;
}
.banner-warning {
    background: #1c1500;
    border: 1px solid #f59e0b;
    border-radius: 6px;
    padding: 8px 14px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    color: #f59e0b;
    margin-bottom: 12px;
}
.banner-critico {
    background: #1f0707;
    border: 1px solid #ef4444;
    border-radius: 6px;
    padding: 8px 14px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    color: #ef4444;
    margin-bottom: 8px;
}
</style>
'''


def _fmt_umbral(umbral) -> str:
    if umbral is None:
        return "—"
    if isinstance(umbral, list):
        return f"{umbral[0]} – {umbral[1]}"
    return str(umbral)

def _check_alertas_activas(alertas: list) -> list:
    # comprueba qué alertas están disparadas en este momento
    disparadas = []
    try:
        mem = psutil.virtual_memory()
        ram_pct = mem.percent
        for a in alertas:
            if a.get("estado") != "ON":
                continue
            alerta_id = a.get("alerta_id", "")
            umbral = a.get("umbral")
            if alerta_id == "ram_alta" and isinstance(umbral, list):
                if ram_pct >= umbral[0]:
                    disparadas.append({
                        "nombre": a["nombre"],
                        "tipo": a.get("tipo", "warning"),
                        "mensaje": f"RAM al {ram_pct:.1f}% (umbral: {umbral[0]}%)",
                    })
            elif alerta_id == "ram_critica":
                umbral_val = umbral[0] if isinstance(umbral, list) else umbral
                if umbral_val and ram_pct >= float(umbral_val):
                    disparadas.append({
                        "nombre": a["nombre"],
                        "tipo": "critico",
                        "mensaje": f"RAM crítica al {ram_pct:.1f}%",
                    })
    except Exception:
        pass
    return disparadas


def render():
    st.markdown(CSS, unsafe_allow_html=True)

    alertas = get_alertas()

    # --- banners de alertas activas ---
    disparadas = _check_alertas_activas(alertas)
    for d in disparadas:
        css_class = "banner-critico" if d["tipo"] == "critico" else "banner-warning"
        icono = "🔴" if d["tipo"] == "critico" else "⚠️"
        st.markdown(
            f'<div class="{css_class}">{icono} <b>{d["nombre"]}</b> — {d["mensaje"]}</div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="section-title">Alertas del sistema</div>', unsafe_allow_html=True)

    if not alertas:
        st.markdown('<div style="color:#4b5563;font-family:IBM Plex Mono,monospace;font-size:12px">No hay alertas configuradas.</div>', unsafe_allow_html=True)
        return

    col1, col2 = st.columns(2, gap="large")

    for i, a in enumerate(alertas):
        col = col1 if i % 2 == 0 else col2
        with col:
            tipo      = a.get("tipo", "warning")
            estado    = a.get("estado", "OFF")
            nombre    = a.get("nombre", "—")
            desc      = a.get("descripcion", "")
            umbral    = a.get("umbral")
            card_cls  = "alerta-card-critico" if tipo == "critico" else "alerta-card-warning"
            badge_cls = "alerta-badge-on" if estado == "ON" else "alerta-badge-off"
            tipo_color = "#ef4444" if tipo == "critico" else "#f59e0b"
            umbral_html = ""
            if umbral is not None:
                umbral_html = f'<div class="alerta-umbral">Umbral: <span class="alerta-umbral-val">{_fmt_umbral(umbral)}</span></div>'

            st.markdown(f'''
            <div class="alerta-card {card_cls}">
                <div class="alerta-header">
                    <span class="alerta-nombre">{nombre}</span>
                    <div style="display:flex;gap:6px;align-items:center">
                        <span class="alerta-tipo-badge" style="background:{tipo_color}22;color:{tipo_color}">{tipo}</span>
                        <span class="{badge_cls}">{estado}</span>
                    </div>
                </div>
                <div class="alerta-desc">{desc}</div>
                {umbral_html}
            </div>
            ''', unsafe_allow_html=True)

    st.markdown(
        '<div style="font-family:IBM Plex Mono,monospace;font-size:10px;color:#4b5563;margin-top:8px">'
        'Los umbrales se configuran en MongoDB · fluctuacion_brusca activa el pipeline de IA</div>',
        unsafe_allow_html=True,
    )