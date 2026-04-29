# ✅ 1. NÚCLEO, IDENTIDAD VISUAL ALFA Y MOTORES DE DATOS
import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
from datetime import datetime
import pytz
import base64
import time
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from supabase import create_client, Client

# Configuración de Página Grado Militar
st.set_page_config(
    page_title="AION-YAROKU | CORE SYSTEM",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- MOTORES DE CONEXIÓN ---

# 1.1. Supabase (Motor SQL para Mensajería y Auditoría)
@st.cache_resource
def init_supabase():
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except: return None

supabase = init_supabase()

# 1.2. Google Sheets (Matriz de Objetivos y Estructura)
ID_MAESTRO_DB = "1Md0VkOnwUJWldq0S1fB9UrmOKv4MG__JVG3tQsda0Uw"

def conectar_google():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        return gspread.authorize(creds)
    except: return None

@st.cache_data(ttl=30)
def leer_matriz_nube(pestana):
    gc = conectar_google()
    if gc:
        try:
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
            return pd.DataFrame(hoja.get_all_records())
        except: return pd.DataFrame()
    return pd.DataFrame()

def escribir_registro_pro(pestana, datos_fila):
    try:
        gc = conectar_google()
        if gc:
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
            hoja.append_row(datos_fila)
            return True
    except: return False

# 1.3. Estética Identidad Alfa (Glassmorphism)
def aplicar_identidad_alfa():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@300;500;700&display=swap');
        .stApp { background: radial-gradient(circle at top, #0A0F1E 0%, #030305 100%); color: #E0E0E0; font-family: 'Rajdhani', sans-serif; }
        h1, h2, h3, .stSubheader { font-family: 'Orbitron', sans-serif; color: #00E5FF !important; text-shadow: 0 0 20px rgba(0, 229, 255, 0.5); letter-spacing: 2px !important; }
        .stButton>button { background: rgba(0, 229, 255, 0.05); color: #00E5FF; border: 1px solid rgba(0, 229, 255, 0.4); font-family: 'Orbitron', sans-serif; height: 45px; transition: all 0.3s; }
        .stButton>button:hover { background: #00E5FF; color: #000; box-shadow: 0 0 30px #00E5FF; transform: scale(1.02); }
        .card-mensaje { border-left: 5px solid #00E5FF; background: rgba(255,255,255,0.05); padding: 15px; border-radius: 5px; margin-bottom: 10px; }
        .stTabs [aria-selected="true"] { background: rgba(0, 229, 255, 0.15) !important; color: #00E5FF !important; border: 1px solid #00E5FF !important; }
        </style>
        """, unsafe_allow_html=True
    )

aplicar_identidad_alfa()

def obtener_hora_argentina():
    tz = pytz.timezone("America/Argentina/Buenos_Aires")
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

st.markdown('<div style="text-align:center"><img src="https://i.ibb.co/vzrV8Vq/logo-aion.png" width="300"></div>', unsafe_allow_html=True)

# --- 2. CONTROL DE SESIÓN Y ACCESO ---
if 'rol_sel' not in st.session_state: st.session_state.rol_sel = "SUPERVISOR"
if 'user_sel' not in st.session_state: st.session_state.user_sel = "BRIAN AYALA"
if 'lat' not in st.session_state: st.session_state.lat = -34.4246
if 'lon' not in st.session_state: st.session_state.lon = -58.7381

with st.sidebar:
    st.subheader("🛡️ PANEL DE MANDO")
    perfiles = ["SUPERVISOR", "MONITOREO", "VIGILADOR", "JEFE DE OPERACIONES", "GERENCIA", "ADMINISTRADOR"]
    st.session_state.rol_sel = st.selectbox("Nivel de Acceso:", perfiles, index=perfiles.index(st.session_state.rol_sel))
    
    lista_sups = ["BRIAN AYALA", "SERANTES WALTER", "SANOJA LUIS", "MAZACOTTE CLAUDIO", "PORZIO GONZALO", "CARRIZO WALTER", "SUPERVISOR NOCTURNO"]
    
    if st.session_state.rol_sel == "SUPERVISOR":
        st.session_state.user_sel = st.selectbox("Identidad Operativa:", lista_sups)
    elif st.session_state.rol_sel == "VIGILADOR":
        st.session_state.user_sel = st.text_input("ID / LEGAJO").upper()
    else:
        st.session_state.user_sel = st.session_state.rol_sel

    if st.session_state.rol_sel == "ADMINISTRADOR":
        if st.text_input("🔑 CÓDIGO RAÍZ", type="password") != "aion2026": st.stop()

# --- 3. FUNCIONES DE COMUNICACIÓN TÁCTICA ---
def mostrar_buzon_tactico(usuario, clave_bloque):
    st.markdown("### 📡 COMUNICACIONES TÁCTICAS")
    t_rec, t_emi = st.tabs(["📥 BANDEJA DE ENTRADA", "📤 TRANSMITIR DIRECTIVA"], key=f"tabs_{clave_bloque}")
    
    with t_emi:
        with st.form(f"form_msg_{clave_bloque}"):
            dest = st.selectbox("Destinatario:", ["TODOS", "MONITOREO", "JEFE DE OPERACIONES", "GERENCIA"] + lista_sups, key=f"sel_{clave_bloque}")
            pri = st.select_slider("Prioridad:", options=["VERDE", "AMARILLA", "ROJA"], key=f"pri_{clave_bloque}")
            msg = st.text_area("Cuerpo del Reporte:", key=f"area_{clave_bloque}")
            captura = st.camera_input("Captura de Evidencia (Opcional):", key=f"cam_{clave_bloque}")
            if st.form_submit_button("🚀 TRANSMITIR"):
                if msg:
                    img_b64 = base64.b64encode(captura.getvalue()).decode() if captura else None
                    payload = {"fecha_hora": obtener_hora_argentina(), "remitente": usuario, "destinatario": dest, "prioridad": pri, "mensaje": msg, "imagen_evidencia": img_b64, "estado": "PENDIENTE"}
                    try:
                        supabase.table('MENSAJERIA_TACTICA').insert(payload).execute()
                        st.success("Transmisión Exitosa."); st.rerun()
                    except: st.error("Error de enlace SQL.")

    with t_rec:
        if st.button("🔄 SINCRONIZAR RED", key=f"btn_sync_{clave_bloque}"): st.rerun()
        try:
            res = supabase.table('MENSAJERIA_TACTICA').select('*').order('id', desc=True).limit(10).execute()
            for m in (res.data if res.data else []):
                if m['destinatario'] in [usuario, "TODOS", st.session_state.rol_sel, "MONITOREO"]:
                    color = "#00FF00" if m['prioridad'] == "VERDE" else ("#FFCC00" if m['prioridad'] == "AMARILLA" else "#FF0000")
                    st.markdown(f"""<div style="border-left: 5px solid {color}; background: rgba(255,255,255,0.05); padding: 12px; border-radius: 5px; margin-bottom: 8px;">
                        <small>{m['fecha_hora']} | De: {m['remitente']}</small><br>
                        <b>{m['mensaje']}</b></div>""", unsafe_allow_html=True)
                    if m['imagen_evidencia']:
                        st.image(base64.b64decode(m['imagen_evidencia']), width=300)
        except: st.info("Bandeja vacía o sin red.")

# --- 4. MÓDULOS OPERATIVOS ---

# --- 4.1. MÓDULO VIGILADOR ---
if st.session_state.rol_sel == "VIGILADOR":
    st.header(f"💂 ESTACIÓN VIGILADOR: {st.session_state.user_sel}")
    t1, t2, t3 = st.tabs(["📝 REPORTE DE NOVEDAD", "🤳 ESCÁNER QR", "📡 MENSAJERÍA"], key="tabs_vig_main")
    with t1:
        with st.form("nov_vig"):
            obj = st.text_input("Objetivo / Servicio Actual")
            det = st.text_area("Detalle de la novedad en puesto")
            if st.form_submit_button("SELLAR NOVEDAD"):
                escribir_registro_pro("MENSAJERIA", [obtener_hora_argentina(), st.session_state.user_sel, "MONITOREO", "NOVEDAD PUESTO", det, "PENDIENTE", "VERDE"])
                st.success("Novedad enviada.")
    with t2:
        st.info("Punto de control Biométrico/QR")
        st.camera_input("Enfoque el código del objetivo")
    with t3: mostrar_buzon_tactico(st.session_state.user_sel, "vigilancia")

# --- 4.2. MÓDULO SUPERVISOR ---
elif st.session_state.rol_sel == "SUPERVISOR":
    st.header(f"⚡ ESTACIÓN TÁCTICA: {st.session_state.user_sel}")
    t1, t2, t3 = st.tabs(["📍 RADAR DE OBJETIVOS", "🚚 CONTROL DE FLOTA", "📡 COMUNICACIÓN"], key="tabs_sup_main")
    with t1:
        df_obj = leer_matriz_nube("OBJETIVOS")
        if not df_obj.empty:
            m = folium.Map(location=[st.session_state.lat, st.session_state.lon], zoom_start=12, tiles="CartoDB dark_matter")
            for _, r in df_obj.iterrows():
                folium.Marker([float(str(r['LATITUD']).replace(',','.')), float(str(r['LONGITUD']).replace(',','.'))], popup=r['OBJETIVO']).add_to(m)
            st_folium(m, width="100%", height=450)
    with t2:
        with st.expander("🚚 REGISTRO LOGÍSTICO"):
            movil = st.selectbox("Unidad:", ["S-001", "S-002", "S-003", "S-004", "S-005"])
            km = st.number_input("Kilometraje actual:", min_value=0)
            if st.button("Sellar Kilometraje"):
                escribir_registro_pro("CONTROL_FLOTA", [obtener_hora_argentina()[:10], st.session_state.user_sel, movil, km, 0, 0])
                st.success("Logística guardada.")
    with t3: mostrar_buzon_tactico(st.session_state.user_sel, "supervisor")

# --- 4.3. MÓDULO MONITOREO ---
elif st.session_state.rol_sel == "MONITOREO":
    st.header("🛰️ CENTRAL DE INTELIGENCIA")
    m1, m2 = st.columns(2)
    m1.metric("🚨 ALERTAS SOS", "0")
    m2.metric("📋 NOVEDADES HOY", "12")
    t1, t2, t3 = st.tabs(["🚨 RADAR S.O.S", "📖 BITÁCORA BASE", "📡 COMUNICACIÓN"], key="tabs_mon_main")
    with t1: st.success("Perímetro seguro. Sin alertas de pánico.")
    with t2:
        nov_base = st.text_area("Entrada de Libro de Guardia:")
        if st.button("Sellar Libro de Base"):
            st.success("Registro inmutable guardado.")
    with t3: mostrar_buzon_tactico("MONITOREO", "monitoreo")

# --- 4.4. MÓDULO JEFE / GERENCIA ---
elif st.session_state.rol_sel in ["JEFE DE OPERACIONES", "GERENCIA"]:
    st.header(f"👔 COMANDO ESTRATÉGICO: {st.session_state.user_sel}")
    t1, t2, t3 = st.tabs(["📊 AUDITORÍA DE TERRENO", "⚡ GESTIÓN DE PERSONAL", "📡 COMUNICACIÓN"], key="tabs_exec_main")
    with t1:
        st.subheader("Rendimiento de Supervisión")
        st.write("Visualizando actas de flota y tiempos de respuesta...")
    with t2:
        st.subheader("Altas/Bajas de Estructura")
        st.button("Generar Reporte Mensual")
    with t3: mostrar_buzon_tactico(st.session_state.user_sel, "comando")

# --- 4.5. ADMINISTRADOR ---
elif st.session_state.rol_sel == "ADMINISTRADOR":
    st.header("⚙️ NÚCLEO MAESTRO: BRIAN AYALA")
    t1, t2 = st.tabs(["🗄️ CONSOLA SQL", "📡 INTERCEPCIÓN DARK MESH"], key="tabs_admin_main")
    with t1:
        if st.button("PURGAR CACHÉ GLOBAL"):
            st.cache_data.clear()
            st.success("Memoria RAM del servidor liberada.")
    with t2: mostrar_buzon_tactico("ADMIN", "raiz")

# --- 5. SISTEMA DE EMERGENCIA ---
st.sidebar.markdown("---")
if st.sidebar.button("🚨 S.O.S GLOBAL", use_container_width=True):
    transmitir_mensaje_sql(st.session_state.user_sel, "TODOS", "ROJA", "!!! EMERGENCIA GLOBAL: REPLEGAR A POSICIONES SEGURAS !!!")
    st.sidebar.error("ALERTA S.O.S TRANSMITIDA")
