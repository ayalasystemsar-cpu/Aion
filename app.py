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

# Configuración de página
st.set_page_config(page_title="AION-YAROKU | CORE", page_icon="🛡️", layout="wide")

# --- CONEXIONES ---
ID_MAESTRO_DB = "1Md0VkOnwUJWldq0S1fB9UrmOKv4MG__JVG3tQsda0Uw"

def conectar_google():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        return gspread.authorize(creds)
    except: return None

# --- FUNCIONES LÓGICAS ---
def obtener_hora_argentina():
    tz = pytz.timezone("America/Argentina/Buenos_Aires")
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

@st.cache_data(ttl=20)
def leer_matriz_nube(pestana):
    gc = conectar_google()
    if gc:
        try:
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
            datos = hoja.get_all_values()
            return pd.DataFrame(datos[1:], columns=[h.upper().strip() for h in datos[0]]) if datos else pd.DataFrame()
        except: return pd.DataFrame()
    return pd.DataFrame()

def obtener_comisaria_mas_cercana(lat_obj, lon_obj):
    df = leer_matriz_nube("COMISARIAS")
    if df.empty: return None
    
    # Normalización de coordenadas
    df['LATITUD'] = pd.to_numeric(df['LATITUD'].astype(str).str.replace(',', '.'), errors='coerce')
    df['LONGITUD'] = pd.to_numeric(df['LONGITUD'].astype(str).str.replace(',', '.'), errors='coerce')
    
    mejor_com = None
    dist_min = float('inf')
    
    for _, c in df.dropna(subset=['LATITUD', 'LONGITUD']).iterrows():
        # Distancia Haversine
        a = math.sin(((c['LATITUD'] - lat_obj) * math.pi/180)/2)**2 + \
            math.cos(lat_obj * math.pi/180) * math.cos(c['LATITUD'] * math.pi/180) * \
            math.sin(((c['LONGITUD'] - lon_obj) * math.pi/180)/2)**2
        dist = 2 * 6371 * math.asin(math.sqrt(a))
        if dist < dist_min:
            dist_min = dist
            mejor_com = {"NOMBRE": c['NOMBRE'], "LAT": c['LATITUD'], "LON": c['LONGITUD'], "DIST": round(dist, 2)}
    return mejor_com

# --- INTERFAZ TÁCTICA (MONITOREO RESUMIDO) ---
if st.session_state.get('rol_sel', 'MONITOREO') == "MONITOREO":
    st.markdown("## 🛰️ CENTRAL DE INTELIGENCIA")
    df_alertas = leer_matriz_nube("ALERTAS")
    
    # Radar con despliegue de rutas
    if not df_alertas.empty:
        pendientes = df_alertas[df_alertas['ESTADO'].str.upper() == 'PENDIENTE']
        if not pendientes.empty:
            for _, al in pendientes.iterrows():
                carga = al['CARGA_UTIL']
                lat = float(carga.split("LAT:")[1].split("|")[0])
                lon = float(carga.split("LON:")[1].split("|")[0])
                
                m = folium.Map(location=[lat, lon], zoom_start=15, tiles="CartoDB dark_matter")
                folium.Marker([lat, lon], icon=folium.Icon(color="red", icon="exclamation-triangle")).add_to(m)
                
                comisaria = obtener_comisaria_mas_cercana(lat, lon)
                if comisaria:
                    folium.Marker([comisaria['LAT'], comisaria['LON']], icon=folium.Icon(color="blue", icon="shield")).add_to(m)
