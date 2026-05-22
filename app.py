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

# --- CONFIGURACIÓN DE PÁGINA ---
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

def escribir_registro_nube(pestana, datos_fila):
    try:
        gc = conectar_google()
        if gc:
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
            hoja.append_row(datos_fila)
            return True
    except: return False

@st.cache_data(ttl=5)
def cargar_objetivos():
    try:
        df = pd.DataFrame(conectar_google().open_by_key(ID_MAESTRO_DB).worksheet("OBJETIVOS").get_all_records())
        if not df.empty:
            df.columns = df.columns.str.strip().str.upper()
            df = df[df['OBJETIVO'].astype(str).str.strip() != ""]
            df['SUPERVISOR'] = df['SUPERVISOR'].astype(str).str.strip().str.upper()
            df['OBJETIVO'] = df['OBJETIVO'].astype(str).str.strip().str.upper()
            df['LATITUD'] = pd.to_numeric(df['LATITUD'].astype(str).str.replace(',', '.'), errors='coerce')
            df['LONGITUD'] = pd.to_numeric(df['LONGITUD'].astype(str).str.replace(',', '.'), errors='coerce')
            return df
    except: pass
    return pd.DataFrame()

# --- 4. DISEÑO E IDENTIDAD VISUAL ---
def aplicar_identidad_alfa():
    st.markdown("""<style>
    .stApp { background: radial-gradient(circle at top, #0A0F1E 0%, #030305 100%) !important; color: #E0E0E0; font-family: 'Rajdhani', sans-serif; }
    .estacion-titulo { font-family: 'Orbitron', sans-serif; color: #00E5FF !important; font-size: 24px; text-align: center; margin-bottom: 20px; }
    .radar-box { border: 1px solid #1A1A1B; border-radius: 12px; padding: 10px; background: rgba(10, 10, 11, 0.9); }
    .titulo-seccion-admin { color: #00E5FF; font-family: 'Orbitron', sans-serif; font-size: 22px; font-weight: bold; margin-top: 25px; margin-bottom: 15px; }
    .panel-novedad { border: 1px solid #333; border-radius: 8px; padding: 15px; margin-top: 20px; background-color: rgba(10, 10, 11, 0.9); }
    </style>""", unsafe_allow_html=True)

aplicar_identidad_alfa()

# --- 5. SIDEBAR TÁCTICO ---
df_objetivos = cargar_objetivos()
LISTA_SUPS_TACTICOS = ["AYALA BRIAN", "SUPERVISOR 1", "SUPERVISOR 2", "SUPERVISOR 3", "SUPERVISOR 4", "SUPERVISOR 5", "SUPERVISOR NOCTURNO"]

if 'rol_sel' not in st.session_state: st.session_state.rol_sel = "MONITOREO"
with st.sidebar:
    if st.button("🛰️ MONITOREO"): st.session_state.rol_sel = "MONITOREO"; st.rerun()
    if st.button("📋 JEFE DE OPERACIONES"): st.session_state.rol_sel = "JEFE DE OPERACIONES"; st.rerun()
    if st.button("🏢 GERENCIA"): st.session_state.rol_sel = "GERENCIA"; st.rerun()
    with st.expander("👤 SUPERVISORES"):
        nom_sup = st.selectbox("RESPONSABLE:", LISTA_SUPS_TACTICOS)
        user = st.text_input("USUARIO:")
        pwd = st.text_input("PASS:", type="password")
        if st.button("INGRESAR"):
            if user.lower() == (nom_sup.split(" ")[1].lower() if " " in nom_sup else "admin") and pwd == "1234":
                st.session_state.rol_sel = "SUPERVISOR"; st.session_state.user_sel = nom_sup; st.rerun()
    if st.button("⚙️ ADMINISTRADOR"): st.session_state.rol_sel = "ADMINISTRADOR"; st.rerun()

# --- 7. FLUJO POR ROLES ---

# A. ROL SUPERVISOR (FILTRADO DIRECTO POR EXCEL)
if st.session_state.rol_sel == "SUPERVISOR":
    sup_norm = str(st.session_state.user_sel).strip().upper()
    df_f = df_objetivos[df_objetivos['SUPERVISOR'] == sup_norm]
    
    st.markdown(f'<div class="estacion-titulo">📱 ESTACIÓN: {sup_norm}</div>', unsafe_allow_html=True)
    if not df_f.empty:
        m = folium.Map(location=[df_f['LATITUD'].mean(), df_f['LONGITUD'].mean()], zoom_start=13, tiles="CartoDB dark_matter")
        for _, r in df_f.iterrows(): folium.Marker([r['LATITUD'], r['LONGITUD']], tooltip=r['OBJETIVO']).add_to(m)
        st_folium(m, width="100%", height=500)
        st.selectbox("SERVICIO ACTUAL:", df_f['OBJETIVO'].unique())
    else: st.warning(f"⚠️ No se encontraron objetivos para {sup_norm}. Revisa el Excel.")

# B. ROL MONITOREO
elif st.session_state.rol_sel == "MONITOREO":
    st.markdown('<div class="estacion-titulo">🛰️ CENTRAL DE INTELIGENCIA</div>', unsafe_allow_html=True)
    st.dataframe(df_objetivos)

# C. ROL JEFE
elif st.session_state.rol_sel == "JEFE DE OPERACIONES":
    st.markdown('<div class="estacion-titulo">📋 COMANDO DE OPERACIONES</div>', unsafe_allow_html=True)
    st.dataframe(df_objetivos)

# D. ROL GERENCIA
elif st.session_state.rol_sel == "GERENCIA":
    st.markdown('<div class="estacion-titulo">🏢 DIRECCIÓN GENERAL</div>', unsafe_allow_html=True)
    st.dataframe(df_objetivos)

# E. ROL ADMINISTRADOR
elif st.session_state.rol_sel == "ADMINISTRADOR":
    st.markdown('<div class="titulo-seccion-admin">⚙️ NÚCLEO MAESTRO</div>', unsafe_allow_html=True)
    if st.text_input("PASSWORD:", type="password") == "aion2026":
        if st.button("REGISTRAR"): st.success("Acceso al núcleo habilitado.")
        st.dataframe(df_objetivos)
