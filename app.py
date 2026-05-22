import streamlit as st
import datetime
from datetime import datetime
import pandas as pd
import pytz
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from streamlit_js_eval import get_geolocation

# --- IMPORTACIONES CRÍTICAS DE MAPAS ---
import folium
from folium.plugins import AntPath
from streamlit_folium import st_folium
import math

# Configuración de página OLED
st.set_page_config(
    page_title="AION-YAROKU | CORE",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CONEXIONES (GOOGLE MATRIZ) ---
ID_MAESTRO_DB = "1Md0VkOnwUJWldq0S1fB9UrmOKv4MG__JVG3tQsda0Uw"

def conectar_google():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        return gspread.authorize(creds)
    except: return None

# --- 3. FUNCIONES DE LÓGICA Y DATOS ---
def obtener_hora_argentina():
    tz = pytz.timezone("America/Argentina/Buenos_Aires")
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

def actualizar_celda(pestana, fila, columna, valor):
    try:
        gc = conectar_google()
        if gc:
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
            hoja.update_acell(f"{columna}{fila}", valor)
            return True
    except: return False

def escribir_registro_nube(pestana, datos_fila):
    try:
        gc = conectar_google()
        if gc:
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
            hoja.append_row(datos_fila)
            return True
    except: return False

@st.cache_data(ttl=15)
def leer_matriz_nube(pestana):
    gc = conectar_google()
    if gc:
        try:
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
            data = hoja.get_all_records()
            if not data:
                return pd.DataFrame()
            return pd.DataFrame(data)
        except: return pd.DataFrame()
    return pd.DataFrame()

@st.cache_data(ttl=60)
def cargar_objetivos():
    df = leer_matriz_nube("OBJETIVOS")
    if not df.empty:
        df.columns = df.columns.str.strip().str.upper()
        df = df[df['OBJETIVO'].astype(str).str.strip() != ""]
        df = df[df['OBJETIVO'].notna()]
        if 'SUPERVISOR' in df.columns:
            df['SUPERVISOR'] = df['SUPERVISOR'].astype(str).str.strip().str.upper()
        df['LATITUD'] = df['LATITUD'].astype(str).str.replace(',', '.')
        df['LONGITUD'] = df['LONGITUD'].astype(str).str.replace(',', '.')
        df['LATITUD'] = pd.to_numeric(df['LATITUD'], errors='coerce')
        df['LONGITUD'] = pd.to_numeric(df['LONGITUD'], errors='coerce')
        return df 
    return pd.DataFrame()

# --- 4. DISEÑO E IDENTIDAD VISUAL ---
def aplicar_identidad_alfa():
    st.markdown("""<style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@300;500;700&display=swap');
        .stApp { background: radial-gradient(circle at top, #0A0F1E 0%, #030305 100%) !important; color: #E0E0E0; font-family: 'Rajdhani', sans-serif; }
        .estacion-titulo { font-family: 'Orbitron', sans-serif; color: #00E5FF !important; font-size: 24px; text-align: center; margin-top: 15px; text-shadow: 0 0 15px rgba(0, 229, 255, 0.4); text-transform: uppercase; }
        .titulo-seccion-admin { color: #00E5FF; font-family: 'Orbitron', sans-serif; font-size: 22px; font-weight: bold; margin-top: 25px; margin-bottom: 15px; }
        </style>""", unsafe_allow_html=True)
aplicar_identidad_alfa()

df_objetivos = cargar_objetivos()
LISTA_SUPS_TACTICOS = ["AYALA BRIAN", "SUPERVISOR 1", "SUPERVISOR 2", "SUPERVISOR 3", "SUPERVISOR 4", "SUPERVISOR 5", "SUPERVISOR NOCTURNO"]

if 'rol_sel' not in st.session_state: st.session_state.rol_sel = "MONITOREO"
if 'user_sel' not in st.session_state: st.session_state.user_sel = "OPERADOR CENTRAL"
if 'sup_autenticado' not in st.session_state: st.session_state.sup_autenticado = False

# --- SIDEBAR ---
with st.sidebar:
    if st.button("🛰️ MONITOREO"): st.session_state.rol_sel = "MONITOREO"; st.rerun()
    if st.button("📋 JEFE DE OPERACIONES"): st.session_state.rol_sel = "JEFE DE OPERACIONES"; st.rerun()
    if st.button("🏢 GERENCIA"): st.session_state.rol_sel = "GERENCIA"; st.rerun()
    with st.expander("👤 SUPERVISORES"):
        nom_sup = st.selectbox("RESPONSABLE:", LISTA_SUPS_TACTICOS)
        user_sup = st.text_input("USUARIO:")
        pass_sup = st.text_input("CONTRASEÑA:", type="password")
        if st.button("AUTENTICAR"):
            if user_sup.lower() == (nom_sup.split(" ")[1].lower() if " " in nom_sup else "admin") and pass_sup == "1234":
                st.session_state.rol_sel = "SUPERVISOR"; st.session_state.user_sel = nom_sup; st.session_state.sup_autenticado = True; st.rerun()
    if st.button("⚙️ ADMINISTRADOR"): st.session_state.rol_sel = "ADMINISTRADOR"; st.rerun()

# --- LÓGICA DE ROLES ---
if st.session_state.rol_sel == "SUPERVISOR":
    sup_norm = str(st.session_state.user_sel).strip().upper()
    df_f = df_objetivos[df_objetivos['SUPERVISOR'] == sup_norm]
    st.markdown(f'<div class="estacion-titulo">📱 ESTACIÓN: {sup_norm}</div>', unsafe_allow_html=True)
    if not df_f.empty:
        st.dataframe(df_f)
    else: st.warning("No hay datos asignados.")

elif st.session_state.rol_sel == "MONITOREO":
    st.markdown('<div class="estacion-titulo">🛰️ MONITOREO</div>', unsafe_allow_html=True)
    st.dataframe(df_objetivos)

elif st.session_state.rol_sel == "JEFE DE OPERACIONES":
    st.markdown('<div class="estacion-titulo">📋 JEFE DE OPERACIONES</div>', unsafe_allow_html=True)
    st.dataframe(df_objetivos)

elif st.session_state.rol_sel == "GERENCIA":
    st.markdown('<div class="estacion-titulo">🏢 GERENCIA</div>', unsafe_allow_html=True)
    st.dataframe(df_objetivos)

elif st.session_state.rol_sel == "ADMINISTRADOR":
    st.markdown('<div class="titulo-seccion-admin">⚙️ ADMINISTRADOR</div>', unsafe_allow_html=True)
    if st.text_input("PASS:", type="password") == "aion2026":
        st.dataframe(df_objetivos)
