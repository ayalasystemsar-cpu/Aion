import streamlit as st
import datetime
from datetime import datetime
import pandas as pd
import pytz
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from streamlit_js_eval import get_geolocation
import folium
from streamlit_folium import st_folium
import math

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="AION-YAROKU | CORE", page_icon="🛡️", layout="wide", initial_sidebar_state="expanded")

# --- CONEXIONES ---
ID_MAESTRO_DB = "1Md0VkOnwUJWldq0S1fB9UrmOKv4MG__JVG3tQsda0Uw"

def conectar_google():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        return gspread.authorize(creds)
    except: return None

def obtener_hora_argentina():
    tz = pytz.timezone("America/Argentina/Buenos_Aires")
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

def escribir_registro_nube(pestana, datos_fila):
    try:
        gc = conectar_google()
        hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
        hoja.append_row(datos_fila)
        return True
    except: return False

@st.cache_data(ttl=15)
def leer_matriz_nube(pestana):
    gc = conectar_google()
    try:
        hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
        data = hoja.get_all_records()
        return pd.DataFrame(data) if data else pd.DataFrame()
    except: return pd.DataFrame()

@st.cache_data(ttl=60)
def cargar_objetivos():
    df = leer_matriz_nube("OBJETIVOS")
    if not df.empty:
        df.columns = df.columns.str.strip().str.upper()
        df = df[df['OBJETIVO'].notna()]
        df['LATITUD'] = pd.to_numeric(df['LATITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        df['LONGITUD'] = pd.to_numeric(df['LONGITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        return df
    return pd.DataFrame()

# --- ESTILOS CSS ---
st.markdown("""
<style>
.estacion-titulo { font-family: 'Orbitron'; color: #00E5FF; font-size: 24px; text-align: center; margin: 15px 0; }
.message-box { border-left: 3px solid #00e5ff; padding: 10px; margin: 5px; background: rgba(255,255,255,0.05); }
.message-box-red { border-left: 3px solid #ff0000; padding: 10px; margin: 5px; background: rgba(255,0,0,0.1); }
.message-info { color: #00e5ff; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- INICIALIZACIÓN ---
if 'rol_sel' not in st.session_state: st.session_state.rol_sel = "MONITOREO"
df_objetivos = cargar_objetivos()

# --- SIDEBAR ---
with st.sidebar:
    if st.button("🛰️ MONITOREO"): st.session_state.rol_sel = "MONITOREO"; st.rerun()
    if st.button("📋 JEFE DE OPERACIONES"): st.session_state.rol_sel = "JEFE DE OPERACIONES"; st.rerun()
    if st.button("🏢 GERENCIA"): st.session_state.rol_sel = "GERENCIA"; st.rerun()
    if st.button("👤 SUPERVISOR"): st.session_state.rol_sel = "SUPERVISOR"; st.rerun()
    if st.button("⚙️ ADMINISTRADOR"): st.session_state.rol_sel = "ADMINISTRADOR"; st.rerun()

# --- LÓGICA DE ROLES ---

if st.session_state.rol_sel == "MONITOREO":
    st.markdown('<div class="estacion-titulo">🛰️ CENTRAL DE INTELIGENCIA OPERATIVA</div>', unsafe_allow_html=True)
    df_emergencias = leer_matriz_nube("ALERTAS")
    
    t1, t2, t3, t4 = st.tabs(["🚨 RADAR S.O.S", "📖 LIBRO", "💬 COMUNICACIÓN", "📋 PRESENTISMO"])
    
    with t1:
        st.subheader("Radar Operativo")
        lat_foco, lon_foco = -34.6, -58.4
        df_activos = df_emergencias[df_emergencias['ESTADO'] == 'PENDIENTE'] if not df_emergencias.empty else pd.DataFrame()
        
        m = folium.Map(location=[lat_foco, lon_foco], zoom_start=13, tiles="CartoDB dark_matter")
        for _, r in df_objetivos.iterrows():
            es_panico = not df_activos.empty and any(df_activos['CARGA_UTIL'].str.contains(r['OBJETIVO']))
            folium.Marker([r['LATITUD'], r['LONGITUD']], icon=folium.Icon(color="red" if es_panico else "blue")).add_to(m)
        st_folium(m, width="100%", height=400)

    with t3:
        df_chats = leer_matriz_nube("CHATS")
        for _, msg in df_chats.tail(10).iterrows():
            es_rojo = str(msg.get("PRIORIDAD", "")).upper() == "ROJA"
            st.markdown(f'<div class="{"message-box-red" if es_rojo else "message-box"}"><b>{msg.get("USUARIO")}</b>: {msg.get("TEXTO")}</div>', unsafe_allow_html=True)

elif st.session_state.rol_sel == "JEFE DE OPERACIONES":
    st.markdown('<div class="estacion-titulo">📋 COMANDO DE OPERACIONES</div>', unsafe_allow_html=True)
    # Aquí iría el código de Jefe que tenías

elif st.session_state.rol_sel == "SUPERVISOR":
    st.markdown('<div class="estacion-titulo">📱 ESTACIÓN DE SUPERVISIÓN</div>', unsafe_allow_html=True)
    # Aquí iría el código de Supervisor con Pestañas

elif st.session_state.rol_sel == "GERENCIA":
    st.markdown('<div class="estacion-titulo">🏢 DIRECCIÓN GENERAL</div>', unsafe_allow_html=True)

elif st.session_state.rol_sel == "ADMINISTRADOR":
    st.markdown('<div class="estacion-titulo">⚙️ NÚCLEO MAESTRO</div>', unsafe_allow_html=True)
