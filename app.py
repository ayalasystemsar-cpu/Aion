import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import pytz
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="AION-YAROKU | CORE", page_icon="🛡️", layout="wide")

# --- LÓGICA DE DATOS (COMISARÍAS COMPLETAS) ---
@st.cache_data
def cargar_datos_comisarias():
    data = {
        "COMISARIA": ["COMISARÍA SAN MARTÍN 1RA", "COMISARÍA VECINAL 14C", "COMISARÍA AVELLANEDA 1RA", "COMISARÍA CAMPANA 1RA", "COMISARÍA SAN FERNANDO 1RA", "COMISARÍA TIGRE 1RA", "COMISARÍA PILAR 6TA (VILLA ROSA)", "COMISARÍA VECINAL 1B", "COMISARÍA VECINAL 14A", "COMISARÍA LANÚS 2DA", "COMISARÍA VECINAL 13A", "COMISARÍA LA MATANZA 2DA", "COMISARÍA LA MATANZA 3RA", "COMISARÍA VECINAL 2A", "COMISARÍA VECINAL 12A", "COMISARÍA VECINAL 12B", "COMISARÍA VECINAL 6A", "COMISARÍA VECINAL 1D", "COMISARÍA RAMOS MEJÍA 2DA"],
        "LATITUD": [-34.580139, -34.587773, -34.664119, -34.163693, -34.440154, -34.424196, -34.417041, -34.617133, -34.587773, -34.708819, -34.557454, -34.700147, -34.717182, -34.589886, -34.554321, -34.568459, -34.613045, -34.603847, -34.646589],
        "LONGITUD": [-58.541410, -58.416056, -58.368073, -58.961418, -58.556134, -58.579789, -58.868209, -58.378734, -58.416056, -58.385311, -58.461144, -58.575608, -58.608301, -58.401918, -58.472147, -58.482012, -58.437198, -58.381577, -58.564571]
    }
    return pd.DataFrame(data)

# --- IDENTIDAD VISUAL ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@300;500;700&display=swap');
    .stApp { background: radial-gradient(circle at top, #0A0F1E 0%, #030305 100%) !important; color: #E0E0E0; font-family: 'Rajdhani', sans-serif; }
    .estacion-titulo { font-family: 'Orbitron', sans-serif; color: #00E5FF; text-align: center; font-size: 24px; text-transform: uppercase; margin: 20px 0; }
    .radar-box { border: 1px solid #00e5ff; border-radius: 8px; padding: 15px; background: #000000; }
    .btn-panico-tactico {
        background: radial-gradient(circle, #ff0000 0%, #4a0000 100%) !important;
        color: white !important; border: 1px solid #ff5555 !important;
        padding: 15px !important; border-radius: 8px !important;
        font-family: 'Orbitron', sans-serif !important;
        text-transform: uppercase !important; width: 100% !important;
        box-shadow: 0 0 20px rgba(255, 0, 0, 0.5) !important;
        animation: pulso-panico 1.5s infinite !important;
    }
    @keyframes pulso-panico {
        0% { transform: scale(1); box-shadow: 0 0 0 0 rgba(255, 0, 0, 0.7); }
        70% { transform: scale(1.02); box-shadow: 0 0 0 15px rgba(255, 0, 0, 0); }
        100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(255, 0, 0, 0); }
    }
    </style>
""", unsafe_allow_html=True)

# --- SIDEBAR ESTRATÉGICO ---
if 'rol_sel' not in st.session_state: st.session_state.rol_sel = "MONITOREO"
with st.sidebar:
    st.subheader("🛡️ PANEL DE CONTROL")
    roles = ["MONITOREO", "SUPERVISOR", "VIGILADOR", "JEFE DE OPERACIONES", "GERENCIA", "ADMINISTRADOR"]
    for rol in roles:
        if st.button(rol, use_container_width=True):
            st.session_state.rol_sel = rol
            st.rerun()

# --- NÚCLEO POR ROL ---
st.markdown(f'<div class="estacion-titulo">{st.session_state.rol_sel}</div>', unsafe_allow_html=True)

# 1. ROL: MONITOREO
if st.session_state.rol_sel == "MONITOREO":
    df_com = cargar_datos_comisarias()
    m = folium.Map(location=[-34.6037, -58.3816], zoom_start=11, tiles="CartoDB dark_matter")
    for _, c in df_com.iterrows():
        folium.Marker(
            location=[c['LATITUD'], c['LONGITUD']],
            tooltip=c['COMISARIA'],
            icon=folium.DivIcon(html=f"""<div style="font-size: 20px; color: #0000FF;"><i class="fa fa-shield"></i></div>""")
        ).add_to(m)
    st_folium(m, width="100%", height=600)

# 2. ROL: SUPERVISOR
elif st.session_state.rol_sel == "SUPERVISOR":
    st.markdown('<div class="radar-box">', unsafe_allow_html=True)
    if st.button("🚨 S.O.S", key="btn_panico"):
        st.error("🚨 ALERTA PÁNICO TRANSMITIDA")
    st.markdown("<script>document.getElementById('btn_panico').className = 'btn-panico-tactico';</script>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# 3. ROL: VIGILADOR
elif st.session_state.rol_sel == "VIGILADOR":
    st.subheader("Terminal de Registro")
    st.text_input("DNI / Legajo")
    if st.button("CONSIGNAR INGRESO"):
        st.success("Presencia registrada correctamente.")

# 4. ROL: JEFE DE OPERACIONES
elif st.session_state.rol_sel == "JEFE DE OPERACIONES":
    st.subheader("Centro de Gestión Táctica")
    st.info("Visualización de flota y novedades críticas.")

# 5. ROL: GERENCIA
elif st.session_state.rol_sel == "GERENCIA":
    st.subheader("Tablero Estratégico")
    c1, c2, c3 = st.columns(3)
    c1.metric("Cobertura", "92%")
    c2.metric("Incidentes", "0")
    c3.metric("Flota Activa", "100%")

# 6. ROL: ADMINISTRADOR
elif st.session_state.rol_sel == "ADMINISTRADOR":
    st.subheader("⚙️ NÚCLEO MAESTRO")
    if st.text_input("PASSWORD", type="password") == "aion2026":
        st.success("Acceso al núcleo habilitado. Sistema listo para configuración.")
    else:
        st.warning("Acceso restringido a personal autorizado.")
