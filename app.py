
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

@st.cache_data(ttl=5)
def leer_matriz_nube(pestana):
    gc = conectar_google()
    if gc:
        try:
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
            todas_filas = hoja.get_all_values()
            if not todas_filas or len(todas_filas) == 0: return pd.DataFrame()
            encabezados = [str(h).strip().upper() for h in todas_filas[0]]
            datos_cuerpo = todas_filas[1:]
            if len(datos_cuerpo) == 0: return pd.DataFrame(columns=encabezados)
            return pd.DataFrame(datos_cuerpo, columns=encabezados)
        except: return pd.DataFrame()
    return pd.DataFrame()

@st.cache_data(ttl=60)
def cargar_objetivos():
    df = leer_matriz_nube("OBJETIVOS")
    if not df.empty:
        df.columns = df.columns.str.strip().str.upper()
        # Blindaje aquí también
        if 'LATITUD' in df.columns and 'LONGITUD' in df.columns:
            df = df[df['OBJETIVO'].notna()]
            df['LATITUD'] = pd.to_numeric(df['LATITUD'].astype(str).str.replace(',', '.'), errors='coerce')
            df['LONGITUD'] = pd.to_numeric(df['LONGITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        return df 
    return pd.DataFrame()

# --- 4. DISEÑO E IDENTIDAD VISUAL ---
def aplicar_identidad_alfa():
    st.markdown("""
        <style>
        .stApp { background: radial-gradient(circle at top, #0A0F1E 0%, #030305 100%) !important; color: #E0E0E0; font-family: 'Rajdhani', sans-serif; }
        .logo-phoenix { width: 520px !important; border: 2px solid #00e5ff !important; box-shadow: 0 0 35px rgba(0, 229, 255, 0.5) !important; border-radius: 4px !important; background-color: #000 !important; }
        .estacion-titulo { font-family: 'Orbitron', sans-serif; color: #00E5FF !important; font-size: 24px; margin-top: 15px; display: flex; align-items: center; justify-content: center; gap: 12px; }
        </style>
        """, unsafe_allow_html=True)

aplicar_identidad_alfa()
df_objetivos = cargar_objetivos()

# --- FUNCION CORRECCIÓN: Evita el KeyError ---
def preparar_df_mapa(df):
    if df.empty: return pd.DataFrame()
    df = df.copy()
    df.columns = df.columns.str.strip().str.upper()
    if 'LATITUD' in df.columns and 'LONGITUD' in df.columns:
        return df.dropna(subset=['LATITUD', 'LONGITUD'])
    return pd.DataFrame()

# --- 5. SIDEBAR Y FLUJOS ---
# (He mantenido toda tu estructura de sidebar intacta)
# ... [AQUÍ VA TU CÓDIGO DE SIDEBAR ORIGINAL] ...

# --- DONDE ESTABA EL ERROR (EJEMPLO MONITOREO) ---
# Reemplaza tu línea 565 y similares por:
df_mapa_monitoreo = preparar_df_mapa(df_objetivos)
if not df_mapa_monitoreo.empty:
    m_mon = folium.Map(location=[df_mapa_monitoreo['LATITUD'].mean(), df_mapa_monitoreo['LONGITUD'].mean()], zoom_start=11, tiles="CartoDB dark_matter")
    # ... tu lógica de folium ...
    st_folium(m_mon, width="100%", height=550)

# --- CORRECCIÓN EN JEFE DE OPERACIONES ---
df_obj_maps_jefe = preparar_df_mapa(df_objetivos)
if not df_obj_maps_jefe.empty:
    m_visor = folium.Map(location=[df_obj_maps_jefe['LATITUD'].mean(), df_obj_maps_jefe['LONGITUD'].mean()], zoom_start=12, tiles="CartoDB dark_matter")
    # ... tu lógica de folium ...
    st_folium(m_visor, width="100%", height=500)
