import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="AION-YAROKU | CORE", layout="wide")
ID_MAESTRO_DB = "1Md0VkOnwUJWldq0S1fB9UrmOKv4MG__JVG3tQsda0Uw"

# --- FUNCIONES ---
@st.cache_data(ttl=60) # Aumentado a 60s para evitar disparos constantes
def obtener_datos(pestana):
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])
        gc = gspread.authorize(creds)
        hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
        datos = hoja.get_all_values()
        return pd.DataFrame(datos[1:], columns=[h.upper().strip() for h in datos[0]])
    except: return pd.DataFrame()

# --- RADAR TÁCTICO ---
def mostrar_radar():
    df_obj = obtener_datos("OBJETIVOS")
    df_com = obtener_datos("COMISARIAS")
    
    m = folium.Map(location=[-34.6, -58.4], zoom_start=11, tiles="CartoDB dark_matter")
    
    # 1. OBJETIVOS Y SUPERVISORES
    if not df_obj.empty:
        for _, r in df_obj.dropna(subset=['LATITUD', 'LONGITUD']).iterrows():
            # Tooltip con icono
            texto = f"🎯 <b>OBJ:</b> {r['OBJETIVO']}<br>👤 <b>SUP:</b> {r.get('SUPERVISOR', 'N/A')}"
            folium.Marker(
                [float(r['LATITUD'].replace(',', '.')), float(r['LONGITUD'].replace(',', '.'))],
                tooltip=folium.Tooltip(texto),
                icon=folium.Icon(color="blue", icon="shield")
            ).add_to(m)

    # 2. COMISARIAS
    if not df_com.empty:
        for _, c in df_com.dropna(subset=['LATITUD', 'LONGITUD']).iterrows():
            folium.Marker(
                [float(c['LATITUD'].replace(',', '.')), float(c['LONGITUD'].replace(',', '.'))],
                tooltip=f"🚓 <b>COMISARIA:</b> {c['NOMBRE']}",
                icon=folium.Icon(color="red", icon="building", prefix="fa")
            ).add_to(m)

    st_folium(m, width="100%", height=500)

# --- FLUJO ---
st.title("🛡️ AION-YAROKU | RADAR TÁCTICO")
mostrar_radar()

# Tablas informativas sin refresco constante
with st.expander("VER DETALLE DE ALERTAS"):
    st.table(obtener_datos("ALERTAS").tail(5))


