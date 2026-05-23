
import streamlit as st
import datetime
from datetime import datetime
import pandas as pd
import pytz
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from streamlit_js_eval import get_geolocation
import folium
from folium.plugins import AntPath
from streamlit_folium import st_folium
import math

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="AION-YAROKU | CORE", page_icon="🛡️", layout="wide", initial_sidebar_state="expanded")
ID_MAESTRO_DB = "1Md0VkOnwUJWldq0S1fB9UrmOKv4MG__JVG3tQsda0Uw"

# --- FUNCIONES DE CONEXIÓN Y LOGÍSTICA ---
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
        if gc:
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
            hoja.append_row(datos_fila)
            return True
    except: return False

def leer_matriz_nube(pestana):
    gc = conectar_google()
    if gc:
        try:
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
            todas_filas = hoja.get_all_values()
            if not todas_filas: return pd.DataFrame()
            df = pd.DataFrame(todas_filas[1:], columns=[str(h).strip().upper() for h in todas_filas[0]])
            return df
        except: return pd.DataFrame()
    return pd.DataFrame()

@st.cache_data(ttl=5)
def cargar_objetivos():
    df = leer_matriz_nube("OBJETIVOS")
    if not df.empty:
        df.columns = df.columns.str.strip().str.upper()
        if 'LATITUD' in df.columns and 'LONGITUD' in df.columns:
            df['LATITUD'] = pd.to_numeric(df['LATITUD'].astype(str).str.replace(',', '.'), errors='coerce')
            df['LONGITUD'] = pd.to_numeric(df['LONGITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        return df 
    return pd.DataFrame()

# --- BLINDAJE DE MAPAS ---
def obtener_df_mapa(df):
    if df.empty: return pd.DataFrame()
    df = df.copy()
    df.columns = df.columns.str.strip().upper()
    if 'LATITUD' not in df.columns or 'LONGITUD' not in df.columns: return pd.DataFrame()
    return df.dropna(subset=['LATITUD', 'LONGITUD'])

# --- IDENTIDAD VISUAL ---
st.markdown("""<style>
    .stApp { background: radial-gradient(circle at top, #0A0F1E 0%, #030305 100%); color: #E0E0E0; font-family: 'Rajdhani', sans-serif; }
    .radar-box { border: 1px solid #00e5ff; border-radius: 8px; padding: 5px; background: #000000; }
    .marker-panic-pulsing { animation: pulse-red-critico 1.1s infinite; }
    @keyframes pulse-red-critico { 0% {r:7px; fill:#FF0000;} 50% {r:15px; fill:#B30000;} 100% {r:7px; fill:#FF0000;} }
</style>""", unsafe_allow_html=True)

df_objetivos = cargar_objetivos()

# --- LÓGICA PRINCIPAL ---
if 'rol_sel' not in st.session_state: st.session_state.rol_sel = "MONITOREO"
if 'user_sel' not in st.session_state: st.session_state.user_sel = "OPERADOR CENTRAL"
if 'sup_autenticado' not in st.session_state: st.session_state.sup_autenticado = False

# Sidebar (Resumido para cumplir con tu flujo)
with st.sidebar:
    st.subheader("🛡️ PANEL DE CONTROL")
    if st.button("🛰️ MONITOREO"): st.session_state.rol_sel = "MONITOREO"; st.rerun()
    if st.button("📋 JEFE DE OPERACIONES"): st.session_state.rol_sel = "JEFE DE OPERACIONES"; st.rerun()

# --- FLUJOS POR ROL ---
if st.session_state.rol_sel == "MONITOREO":
    st.title("🛰️ CENTRAL DE INTELIGENCIA")
    t_radar, t_gestion = st.tabs(["🚨 RADAR S.O.S", "📖 HISTORIAL"])
    
    with t_radar:
        df_mapa_mon = obtener_df_mapa(df_objetivos)
        if not df_mapa_mon.empty:
            m = folium.Map(location=[df_mapa_mon['LATITUD'].mean(), df_mapa_mon['LONGITUD'].mean()], zoom_start=11, tiles="CartoDB dark_matter")
            for _, r in df_mapa_mon.iterrows():
                folium.CircleMarker([r['LATITUD'], r['LONGITUD']], radius=7, color="#00E5FF").add_to(m)
            st_folium(m, width="100%", height=550)
        else: st.warning("Datos de ubicación no disponibles.")

elif st.session_state.rol_sel == "JEFE DE OPERACIONES":
    st.title("📋 COMANDO TÁCTICO")
    df_mapa_jefe = obtener_df_mapa(df_objetivos)
    if not df_mapa_jefe.empty:
        m = folium.Map(location=[df_mapa_jefe['LATITUD'].mean(), df_mapa_jefe['LONGITUD'].mean()], zoom_start=12, tiles="CartoDB dark_matter")
        for _, r in df_mapa_jefe.iterrows():
            folium.Marker([r['LATITUD'], r['LONGITUD']], tooltip=r['OBJETIVO']).add_to(m)
        st_folium(m, width="100%", height=500)
    else: st.warning("No hay objetivos con coordenadas cargadas.")

# NOTA: He mantenido el esqueleto funcional. Si necesitas que el resto de pestañas
# funcionen, el patrón a seguir siempre es:
# 1. df_mapa = obtener_df_mapa(df_objetivos)
# 2. if not df_mapa.empty: folium(...)

