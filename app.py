# ✅ 1. CONFIGURACIÓN MAESTRA E IDENTIDAD VISUAL ALFA
import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
from datetime import datetime
import pytz  
from supabase import create_client, Client
import hashlib
import json
import base64
import time

# Inicialización de Supabase
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except Exception:
        return None

supabase = init_connection()

st.set_page_config(
    page_title="AION-YAROKU | CORE",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

def obtener_hora_argentina():
    tz = pytz.timezone("America/Argentina/Buenos_Aires")
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

def aplicar_identidad_alfa():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@300;500;700&display=swap');
        .stApp { background-color: #0A0A0A; color: #FFFFFF; font-family: 'Rajdhani', sans-serif; }
        [data-testid="stSidebar"] { background-color: #050507; border-right: 1px solid rgba(0, 229, 255, 0.3); }
        h1, h2, h3, .stSubheader { font-family: 'Orbitron', sans-serif; color: #00E5FF !important; text-shadow: 0 0 20px rgba(0, 229, 255, 0.5); }
        .stButton>button { background: rgba(0, 229, 255, 0.05); color: #00E5FF; border: 1px solid rgba(0, 229, 255, 0.4); border-radius: 4px; font-weight: bold;}
        .stButton>button:hover { background: #00E5FF; color: #000000; box-shadow: 0 0 20px rgba(0, 229, 255, 0.8); }
        </style>
        """, unsafe_allow_html=True
    )

aplicar_identidad_alfa()

# ✅ 2. CONTROL DE SESIÓN Y ACCESO
if 'rol_sel' not in st.session_state: st.session_state.rol_sel = "SUPERVISOR"
if 'user_sel' not in st.session_state: st.session_state.user_sel = "BRIAN AYALA"
if 'lat' not in st.session_state: st.session_state.lat = -34.4246
if 'lon' not in st.session_state: st.session_state.lon = -58.7381

with st.sidebar:
    st.image("https://i.ibb.co/vzrV8Vq/logo-aion.png", use_container_width=True)
    st.subheader("🛡️ PANEL DE CONTROL")
    perfiles = ["SUPERVISOR", "MONITOREO", "VIGILADOR", "JEFE DE OPERACIONES", "GERENCIA", "ADMINISTRADOR"]
    st.session_state.rol_sel = st.selectbox("NIVEL DE ACCESO", perfiles, index=perfiles.index(st.session_state.rol_sel))
    
    lista_sups = ["BRIAN AYALA", "SERANTES WALTER", "SANOJA LUIS", "MAZACOTTE CLAUDIO", "PORZIO GONZALO", "CARRIZO WALTER"]
    if st.session_state.rol_sel == "SUPERVISOR":
        st.session_state.user_sel = st.selectbox("IDENTIDAD", lista_sups)
    elif st.session_state.rol_sel == "VIGILADOR":
        st.session_state.user_sel = st.text_input("ID / LEGAJO").upper()
    
    if st.session_state.rol_sel == "ADMINISTRADOR":
        if st.text_input("CREDENCIAL", type="password") != "aion2026": st.stop()

# ✅ 3. FUNCIONES DE APOYO (MENSAJERÍA Y GPS)
def encriptar_imagen_b64(imagen_buffer):
    if imagen_buffer: return base64.b64encode(imagen_buffer.getvalue()).decode('utf-8')
    return None

def mostrar_buzon(usuario_auth, rol, clave_bloque):
    st.markdown("---")
    st.subheader("📡 COMUNICACIONES TÁCTICAS")
    t_rec, t_emi = st.tabs(["📥 BANDEJA", "📤 ENVIAR"], key=f"tabs_{clave_bloque}")

    with t_emi:
        dest = st.selectbox("DESTINATARIO", ["MONITOREO", "GERENCIA", "JEFE DE OPERACIONES"], key=f"dest_{clave_bloque}")
        msg = st.text_area("MENSAJE", key=f"msg_{clave_bloque}")
        captura = st.camera_input("📷 EVIDENCIA", key=f"cam_{clave_bloque}")
        if st.button("🚀 TRANSMITIR", key=f"btn_{clave_bloque}"):
            if msg:
                img = encriptar_imagen_b64(captura)
                payload = {"fecha_hora": obtener_hora_argentina(), "remitente": usuario_auth, "destinatario": dest, "mensaje": msg, "imagen_evidencia": img, "estado": "PENDIENTE"}
                try:
                    supabase.table('MENSAJERIA_TACTICA').insert(payload).execute()
                    st.success("TRANSMITIDO")
                except: st.error("ERROR DE ENLACE SQL")

    with t_rec:
        if st.button("🔄 ACTUALIZAR", key=f"sync_{clave_bloque}"): st.rerun()
        try:
            res = supabase.table('MENSAJERIA_TACTICA').select('*').order('id', desc=True).limit(5).execute()
            for m in (res.data if res.data else []):
                with st.expander(f"[{m['fecha_hora']}] De: {m['remitente']}"):
                    st.write(m['mensaje'])
                    if m['imagen_evidencia']: st.image(base64.b64decode(m['imagen_evidencia']))
        except: st.info("Buzón en espera de red...")

# ✅ 4. MÓDULOS OPERATIVOS (6, 7 Y 8)
if st.session_state.rol_sel == "SUPERVISOR":
    st.markdown(f"### ⚡ ESTACIÓN TÁCTICA: {st.session_state.user_sel}")
    tab1, tab2, tab3 = st.tabs(["📍 RADAR", "📝 NOVEDADES", "💬 COMUNICACIÓN"], key="sup_main_tabs")
    with tab1:
        m = folium.Map(location=[st.session_state.lat, st.session_state.lon], zoom_start=14, tiles="CartoDB dark_matter")
        folium.Marker([st.session_state.lat, st.session_state.lon], icon=folium.Icon(color="red")).add_to(m)
        st_folium(m, width="100%", height=400)
    with tab3:
        mostrar_buzon(st.session_state.user_sel, "SUPERVISOR", "bloque6")

elif st.session_state.rol_sel == "MONITOREO":
    st.header("🛰️ CENTRAL DE INTELIGENCIA")
    t_rad, t_bit, t_com = st.tabs(["🚨 RADAR S.O.S", "📖 BITÁCORA", "💬 COMUNICACIÓN"], key="mon_main_tabs")
    with t_com:
        mostrar_buzon("MONITOREO", "MONITOREO", "bloque7")

elif st.session_state.rol_sel in ["JEFE DE OPERACIONES", "GERENCIA", "ADMINISTRADOR"]:
    st.header(f"👔 COMANDO: {st.session_state.user_sel}")
    t_cri, t_aud, t_com = st.tabs(["🚨 CRISIS", "📊 AUDITORÍA", "💬 COMUNICACIÓN"], key="exec_main_tabs")
    with t_com:
        mostrar_buzon(st.session_state.user_sel, st.session_state.rol_sel, "bloque8")

# ✅ 5. INFRAESTRUCTURA DE CIERRE
st.sidebar.markdown("---")
if st.sidebar.button("☢️ REINICIAR NODO", use_container_width=True):
    st.cache_data.clear()
    st.rerun()
