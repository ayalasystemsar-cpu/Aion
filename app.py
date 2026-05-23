
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

# [MANTIENE TU CONFIGURACIÓN E IDENTIDAD ALFA QUE PASASTE]
st.set_page_config(page_title="AION-YAROKU | CORE", page_icon="🛡️", layout="wide", initial_sidebar_state="expanded")
# ... (Aquí iría todo tu CSS de aplicar_identidad_alfa que ya tenías) ...

ID_MAESTRO_DB = "1Md0VkOnwUJWldq0S1fB9UrmOKv4MG__JVG3tQsda0Uw"

# [TUS FUNCIONES DE CONEXIÓN SE MANTIENEN IGUAL]
def leer_matriz_nube(pestana):
    gc = conectar_google()
    if gc:
        try:
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
            todas_filas = hoja.get_all_values()
            return pd.DataFrame(todas_filas[1:], columns=[h.upper().strip() for h in todas_filas[0]])
        except: return pd.DataFrame()
    return pd.DataFrame()

# --- CORRECCIÓN EN EL RADAR (Aquí es donde estaba el error) ---
def renderizar_radar_propio():
    df_obj = leer_matriz_nube("OBJETIVOS")
    df_com = leer_matriz_nube("COMISARIAS ")
    
    m = folium.Map(location=[-34.6, -58.4], zoom_start=11, tiles="CartoDB dark_matter")
    
    # 1. OBJETIVOS (Tus marcadores azules con nombre y super)
    if not df_obj.empty and 'LATITUD' in df_obj.columns:
        df_obj['LATITUD'] = pd.to_numeric(df_obj['LATITUD'].str.replace(',', '.'), errors='coerce')
        df_obj['LONGITUD'] = pd.to_numeric(df_obj['LONGITUD'].str.replace(',', '.'), errors='coerce')
        for _, r in df_obj.dropna(subset=['LATITUD', 'LONGITUD']).iterrows():
            folium.Marker(
                [r['LATITUD'], r['LONGITUD']],
                tooltip=f"🎯 <b>OBJ:</b> {r['OBJETIVO']}<br>👤 <b>SUP:</b> {r.get('SUPERVISOR', 'N/A')}",
                icon=folium.Icon(color="blue", icon="shield", prefix="fa")
            ).add_to(m)

    # 2. COMISARIAS (Tus marcadores rojos con icono edificio)
    if not df_com.empty and 'LATITUD' in df_com.columns:
        df_com['LATITUD'] = pd.to_numeric(df_com['LATITUD'].str.replace(',', '.'), errors='coerce')
        df_com['LONGITUD'] = pd.to_numeric(df_com['LONGITUD'].str.replace(',', '.'), errors='coerce')
        for _, c in df_com.dropna(subset=['LATITUD', 'LONGITUD']).iterrows():
            folium.Marker(
                [c['LATITUD'], c['LONGITUD']],
                tooltip=f"🚓 <b>COMISARIA:</b> {c['NOMBRE']}",
                icon=folium.Icon(color="red", icon="building", prefix="fa")
            ).add_to(m)
            
    st_folium(m, width="100%", height=500)

# [EL RESTO DE TU CÓDIGO DE TABS Y ROLES SIGUE IGUAL]
# En tu sección de MONITOREO, reemplaza tu mapa anterior por: renderizar_radar_propio()

