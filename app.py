# --- 1. CONFIGURACIÓN E IDENTIDAD VISUAL CORPORATIVA (AION-YAROKU CORE) ---
import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
from folium.plugins import AntPath
from datetime import datetime
import pytz
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from streamlit_js_eval import get_geolocation
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

# --- 3. FUNCIONES DE LÓGICA TÁCTICA ---
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

@st.cache_data(ttl=15)
def leer_matriz_nube(pestana):
    gc = conectar_google()
    if gc:
        try:
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
            return pd.DataFrame(hoja.get_all_records())
        except: return pd.DataFrame()
    return pd.DataFrame()

# CÁLCULO DE DISTANCIA (Fórmula Haversine)
def calcular_distancia(lat1, lon1, lat2, lon2):
    rad = math.pi / 180
    dlat = (lat2 - lat1) * rad
    dlon = (lon2 - lon1) * rad
    a = math.sin(dlat/2)**2 + math.cos(lat1*rad) * math.cos(lat2*rad) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return 6371 * c # Resultado en Km

# --- 4. DISEÑO E IDENTIDAD VISUAL ---
def aplicar_identidad_alfa():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@300;500;700&display=swap');
        .stApp { background: radial-gradient(circle at top, #0A0F1E 0%, #030305 100%) !important; color: #E0E0E0; font-family: 'Rajdhani', sans-serif; }
        .contenedor-logo-central { display: flex; justify-content: center; align-items: center; width: 100%; margin-bottom: 5px; margin-top: 10px; }
        .logo-phoenix { width: 520px !important; border: 2px solid #00e5ff !important; box-shadow: 0 0 35px rgba(0, 229, 255, 0.5) !important; border-radius: 4px !important; background-color: #000 !important; }
        .estacion-titulo { font-family: 'Orbitron', sans-serif; color: #00E5FF !important; font-size: 24px; text-align: center; text-shadow: 0 0 15px rgba(0, 229, 255, 0.4); text-transform: uppercase; margin-top: 10px; }
        .radar-box { border: 1px solid #1A1A1B; border-radius: 12px; padding: 10px; background: rgba(10, 10, 11, 0.9); }
        .stButton > button[kind="primary"] { 
            background: radial-gradient(circle, #FF0000 0%, #8B0000 100%) !important; 
            color: white !important; border-radius: 50% !important; width: 105px !important; height: 105px !important; 
            border: 3px solid #333 !important; box-shadow: 0 0 25px rgba(255, 0, 0, 0.5) !important; font-family: 'Orbitron', sans-serif; font-size: 11px !important; font-weight: bold;
        }
        </style>
        """, unsafe_allow_html=True
    )

aplicar_identidad_alfa()

# --- 5. CARGA DE DATOS ---
df_objetivos = leer_matriz_nube("OBJETIVOS")
if not df_objetivos.empty:
    df_objetivos.columns = df_objetivos.columns.str.strip().str.upper()
    df_objetivos['LATITUD'] = pd.to_numeric(df_objetivos['LATITUD'].astype(str).str.replace(',', '.'), errors='coerce')
    df_objetivos['LONGITUD'] = pd.to_numeric(df_objetivos['LONGITUD'].astype(str).str.replace(',', '.'), errors='coerce')

# Carga de Comisarías (Asegurate de tener esta pestaña en tu Excel)
df_comisarias = leer_matriz_nube("COMISARIAS")
if not df_comisarias.empty:
    df_comisarias.columns = df_comisarias.columns.str.strip().str.upper()
    df_comisarias['LATITUD'] = pd.to_numeric(df_comisarias['LATITUD'].astype(str).str.replace(',', '.'), errors='coerce')
    df_comisarias['LONGITUD'] = pd.to_numeric(df_comisarias['LONGITUD'].astype(str).str.replace(',', '.'), errors='coerce')

# --- 6. SIDEBAR ---
with st.sidebar:
    st.markdown('<img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" style="width:180px; border:1px solid #00e5ff; border-radius:4px;">', unsafe_allow_html=True)
    rol_sel = st.selectbox("ACCESO", ["MONITOREO", "SUPERVISOR", "JEFE DE OPERACIONES", "GERENCIA", "ADMINISTRADOR"])
    user_sel = st.selectbox("IDENTIDAD", ["BRIAN AYALA", "SANOJA LUIS", "DARÍO CECILIA", "LUIS BONGIORNO", "SERANTES WALTER", "MAZACOTTE CLAUDIO", "SUPERVISOR NOCTURNO"])
    st.write("---")
    obj_p = st.selectbox("🎯 OBJETIVO", df_objetivos['OBJETIVO'].unique() if not df_objetivos.empty else ["N/A"])
    
    if st.button("ACTIVAR\nPÁNICO", type="primary"):
        carga = f"LAT:0|LON:0|OBJ:{obj_p}|SUP:AUTO"
        escribir_registro_nube("ALERTAS", [obtener_hora_argentina(), user_sel, "PÁNICO", "PENDIENTE", carga])
        st.error(f"🚨 S.O.S: {obj_p}")

# --- 7. CABECERA ---
st.markdown('<div class="contenedor-logo-central"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" class="logo-phoenix"></div>', unsafe_allow_html=True)
st.markdown(f'<div class="estacion-titulo">SISTEMA TÁCTICO DE COMANDO</div>', unsafe_allow_html=True)

# --- 8. MONITOREO CON COMISARÍA MÁS CERCANA ---
if rol_sel == "MONITOREO":
    df_emergencias = leer_matriz_nube("ALERTAS")
    sos_activos = len(df_emergencias[df_emergencias['ESTADO'].astype(str).str.upper() == 'PENDIENTE']) if not df_emergencias.empty else 0
    
    t_radar, t_base = st.tabs(["🚨 RADAR S.O.S", "📖 LIBRO DE BASE"])
    
    with t_radar:
        lat_f, lon_f, obj_n = -34.6, -58.4, ""
        
        if sos_activos > 0:
            alerta = df_emergencias[df_emergencias['ESTADO'].astype(str).str.upper() == 'PENDIENTE'].iloc[-1]
            obj_n = alerta.get('CARGA_UTIL', '').split("|")[2].split(":")[1]
            st.error(f"🚨 EMERGENCIA ACTIVA: {obj_n}")
            
            # Ubicación del Objetivo
            t_data = df_objetivos[df_objetivos['OBJETIVO'] == obj_n].iloc[0]
            lat_f, lon_f = t_data['LATITUD'], t_data['LONGITUD']
            
            # LÓGICA DE COMISARÍA MÁS CERCANA
            comisaria_cercana = None
            dist_min = float('inf')
            
            if not df_comisarias.empty:
                for _, com in df_comisarias.iterrows():
                    d = calcular_distancia(lat_f, lon_f, com['LATITUD'], com['LONGITUD'])
                    if d < dist_min:
                        dist_min = d
                        comisaria_cercana = com
            
            if comisaria_cercana is not None:
                st.warning(f"🚓 COMISARÍA MÁS CERCANA: {comisaria_cercana['NOMBRE']} a {dist_min:.2f} Km")

        # MAPA
        st.markdown('<div class="radar-box">', unsafe_allow_html=True)
        m = folium.Map(location=[lat_f, lon_f], zoom_start=14, tiles="CartoDB dark_matter")
        
        # Dibujar objetivos
        for _, r in df_objetivos.iterrows():
            es_alerta = (r['OBJETIVO'] == obj_n)
            folium.Marker(
                [r['LATITUD'], r['LONGITUD']], 
                tooltip=f"OBJ: {r['OBJETIVO']}", 
                icon=folium.Icon(color="red" if es_alerta else "blue", icon="shield", prefix="fa")
            ).add_to(m)
        
        # Si hay alerta y comisaría, trazar ruta
        if sos_activos > 0 and comisaria_cercana is not None:
            # Icono de Comisaría
            folium.Marker(
                [comisaria_cercana['LATITUD'], comisaria_cercana['LONGITUD']],
                tooltip=f"COMISARÍA: {comisaria_cercana['NOMBRE']}",
                icon=folium.Icon(color="darkblue", icon="balance-scale", prefix="fa")
            ).add_to(m)
            
            # TRAZADO DE RUTA (Línea animada)
            AntPath(
                locations=[[comisaria_cercana['LATITUD'], comisaria_cercana['LONGITUD']], [lat_f, lon_f]],
                dash_array=[10, 20], delay=1000, color='#00E5FF', weight=5, opacity=0.8
            ).add_to(m)

        st_folium(m, width="100%", height=500, key="mapa_monitoreo_tactico")
        st.markdown('</div>', unsafe_allow_html=True)
