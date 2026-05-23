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
    .estacion-titulo { font-family: 'Orbitron', sans-serif; color: #00E5FF !important; font-size: 24px; margin-top: 15px; display: flex; align-items: center; justify-content: center; gap: 12px; text-shadow: 0 0 15px rgba(0, 229, 255, 0.4); letter-spacing: 2px; text-transform: uppercase; }
    .titulo-seccion-admin { color: #00E5FF; font-family: 'Orbitron', sans-serif; font-size: 22px; font-weight: bold; margin-top: 25px; margin-bottom: 15px; display: flex; align-items: center; gap: 10px; letter-spacing: 1px; text-shadow: 0 0 10px rgba(0, 229, 255, 0.3); }
    .radar-box { border: 1px solid #1A1A1B; border-radius: 12px; padding: 10px; background: rgba(10, 10, 11, 0.9); }
    .panel-novedad { border: 1px solid #333; border-radius: 8px; padding: 15px; margin-top: 20px; background-color: rgba(10, 10, 11, 0.9); }
    </style>""", unsafe_allow_html=True)

aplicar_identidad_alfa()

# --- 5. SIDEBAR TÁCTICO ---
df_objetivos = cargar_objetivos()
LISTA_SUPS_TACTICOS = ["AYALA BRIAN", "SUPERVISOR 1", "SUPERVISOR 2", "SUPERVISOR 3", "SUPERVISOR 4", "SUPERVISOR 5", "SUPERVISOR NOCTURNO"]

if 'rol_sel' not in st.session_state: st.session_state.rol_sel = "MONITOREO"
if 'user_sel' not in st.session_state: st.session_state.user_sel = "OPERADOR CENTRAL"
if 'sup_autenticado' not in st.session_state: st.session_state.sup_autenticado = False

with st.sidebar:
    st.subheader("🛡️ PANEL DE CONTROL")
    if st.button("🛰️ MONITOREO", use_container_width=True): st.session_state.rol_sel = "MONITOREO"; st.rerun()
    if st.button("👤 VIGILADOR", use_container_width=True): st.session_state.rol_sel = "VIGILADOR"; st.rerun()
    if st.button("📋 JEFE DE OPERACIONES", use_container_width=True): st.session_state.rol_sel = "JEFE DE OPERACIONES"; st.rerun()
    if st.button("🏢 GERENCIA", use_container_width=True): st.session_state.rol_sel = "GERENCIA"; st.rerun()
    
    with st.expander("👤 SUPERVISORES"):
        nom_sup = st.selectbox("RESPONSABLE:", LISTA_SUPS_TACTICOS)
        user_sup = st.text_input("USUARIO:")
        pass_sup = st.text_input("PASSWORD:", type="password")
        if st.button("AUTENTICAR"):
            st.session_state.rol_sel = "SUPERVISOR"; st.session_state.user_sel = nom_sup; st.session_state.sup_autenticado = True; st.rerun()
    if st.button("⚙️ ADMINISTRADOR", use_container_width=True): st.session_state.rol_sel = "ADMINISTRADOR"; st.rerun()

# --- 7. FLUJO POR ROLES ---

if st.session_state.rol_sel == "VIGILADOR":
    st.markdown('<div class="estacion-titulo">🛡️ PANEL DE VIGILADOR</div>', unsafe_allow_html=True)
    nombre_v = st.text_input("DNI o Apellido:")
    obj_v = st.selectbox("Objetivo:", df_objetivos['OBJETIVO'].unique() if not df_objetivos.empty else ["CARGANDO..."])
    
    st.subheader("📷 Presentismo Facial")
    foto = st.camera_input("Fichar Entrada")
    if foto:
        escribir_registro_nube("PRESENTISMO", [obtener_hora_argentina(), nombre_v, obj_v, "PRESENTE"])
        st.success("¡Presentismo registrado correctamente!")

    st.write("---")
    if st.button("🚨 SOLICITAR CAMBIO DE GUARDIA"):
        info_sup = df_objetivos[df_objetivos['OBJETIVO'].str.upper() == obj_v.upper()]
        if not info_sup.empty:
            sup = info_sup['SUPERVISOR'].iloc[0]
            escribir_registro_nube("NOVEDADES_GUARDIA", [obtener_hora_argentina(), obj_v, nombre_v, "SOLICITUD", sup])
            st.success(f"Solicitud enviada al Supervisor: {sup}")
        else: st.error("No se encontró supervisor.")

elif st.session_state.rol_sel == "MONITOREO":
    st.markdown('<div class="estacion-titulo">🛰️ MONITOREO</div>', unsafe_allow_html=True)

elif st.session_state.rol_sel == "JEFE DE OPERACIONES":
    st.markdown('<div class="estacion-titulo">📋 JEFE DE OPERACIONES</div>', unsafe_allow_html=True)

elif st.session_state.rol_sel == "SUPERVISOR":
    st.markdown(f'<div class="estacion-titulo">📱 SUPERVISOR: {st.session_state.user_sel}</div>', unsafe_allow_html=True)
    t1, t2 = st.tabs(["Control Táctico", "🚨 BANDEJA NOVEDADES GUARDIA"])
    with t1:
        st.write("Interfaz original de supervisor...")
    with t2:
        st.subheader("Bandeja de Cambios de Guardia")
        df_ng = leer_matriz_nube("NOVEDADES_GUARDIA")
        if not df_ng.empty:
            df_ng.columns = df_ng.columns.str.strip().str.upper()
            sup_act = st.session_state.user_sel.strip().upper()
            st.dataframe(df_ng[df_ng['SUPERVISOR_ASIGNADO'].str.upper() == sup_act], use_container_width=True)

elif st.session_state.rol_sel == "GERENCIA":
    st.markdown('<div class="estacion-titulo">🏢 GERENCIA</div>', unsafe_allow_html=True)

elif st.session_state.rol_sel == "ADMINISTRADOR":
    st.markdown('<div class="estacion-titulo">⚙️ ADMINISTRADOR</div>', unsafe_allow_html=True)
