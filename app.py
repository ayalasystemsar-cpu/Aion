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

# --- CONFIGURACIÓN E IDENTIDAD ALFA (TU DISEÑO ORIGINAL) ---
st.set_page_config(page_title="AION-YAROKU | CORE", page_icon="🛡️", layout="wide", initial_sidebar_state="expanded")

def aplicar_identidad_alfa():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@300;500;700&display=swap');
        .stApp { background: radial-gradient(circle at top, #0A0F1E 0%, #030305 100%) !important; color: #E0E0E0; font-family: 'Rajdhani', sans-serif; }
        .logo-phoenix { width: 520px !important; border: 2px solid #00e5ff !important; box-shadow: 0 0 35px rgba(0, 229, 255, 0.5) !important; border-radius: 4px !important; }
        </style>
        """, unsafe_allow_html=True)

aplicar_identidad_alfa()

# --- FUNCIONES BASE ---
ID_MAESTRO_DB = "1Md0VkOnwUJWldq0S1fB9UrmOKv4MG__JVG3tQsda0Uw"

def conectar_google():
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])
        return gspread.authorize(creds)
    except: return None

@st.cache_data(ttl=60)
def leer_matriz_nube(pestana):
    gc = conectar_google()
    if gc:
        try:
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
            datos = hoja.get_all_values()
            return pd.DataFrame(datos[1:], columns=[h.upper().strip() for h in datos[0]])
        except: return pd.DataFrame()
    return pd.DataFrame()

# --- RADAR TÁCTICO CON ICONOS RECONOCIBLES ---
def renderizar_radar():
    df_obj = leer_matriz_nube("OBJETIVOS")
    df_com = leer_matriz_nube("COMISARIAS ") 
    
    m = folium.Map(location=[-34.6, -58.4], zoom_start=11, tiles="CartoDB dark_matter")
    
    # Marcadores Objetivos (Escudo Azul)
    if not df_obj.empty and 'LATITUD' in df_obj.columns:
        for _, r in df_obj.dropna(subset=['LATITUD', 'LONGITUD']).iterrows():
            folium.Marker(
                [float(r['LATITUD'].replace(',', '.')), float(r['LONGITUD'].replace(',', '.'))],
                tooltip=f"🎯 {r['OBJETIVO']} | 👤 {r.get('SUPERVISOR', 'N/A')}",
                icon=folium.Icon(color="blue", icon="shield", prefix="fa")
            ).add_to(m)
            
    # Marcadores Comisarías (Edificio Rojo)
    if not df_com.empty and 'LATITUD' in df_com.columns:
        for _, c in df_com.dropna(subset=['LATITUD', 'LONGITUD']).iterrows():
            folium.Marker(
                [float(c['LATITUD'].replace(',', '.')), float(c['LONGITUD'].replace(',', '.'))],
                tooltip=f"🚓 {c['NOMBRE']}",
                icon=folium.Icon(color="red", icon="building", prefix="fa")
            ).add_to(m)
            
    st_folium(m, width="100%", height=500)

# --- FLUJO PRINCIPAL ---
# [AQUÍ MANTIENES TU SIDEBAR, TABS Y ROLES ORIGINALES]
# Solo cambia la llamada a tu mapa por: renderizar_radar()

