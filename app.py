import streamlit as st
import datetime
from datetime import datetime
import pandas as pd
import pytz
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from streamlit_folium import st_folium
import folium
from branca.element import Element

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="AION-YAROKU | CORE", page_icon="🛡️", layout="wide")
ID_MAESTRO_DB = "1Md0VkOnwUJWldq0S1fB9UrmOKv4MG__JVG3tQsda0Uw"

# --- CONEXIONES ---
def conectar_google():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        return gspread.authorize(creds)
    except: return None

# --- LECTURA FORZADA DE DATOS ---
@st.cache_data(ttl=30)
def leer_matriz_nube(pestana):
    gc = conectar_google()
    if not gc: return pd.DataFrame()
    try:
        hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
        datos = hoja.get_all_values()
        if len(datos) < 2: return pd.DataFrame() # Solo encabezados o vacío
        
        df = pd.DataFrame(datos[1:], columns=[str(h).strip().upper() for h in datos[0]])
        df = df.loc[:, ~df.columns.duplicated()] # Quita duplicados
        return df.dropna(how='all') # Quita filas totalmente vacías
    except: return pd.DataFrame()

# --- FLUJO DE VISUALIZACIÓN (MONITOREO) ---
if st.session_state.get('rol_sel') == "MONITOREO":
    t_radar, t_nov = st.tabs(["🚨 RADAR", "🔄 NOVEDADES Y FICHAJES"])
    
    with t_nov:
        st.subheader("🔄 HISTORIAL DE NOVEDADES")
        df_nov = leer_matriz_nube("NOVEDADES_GUARDIA")
        if not df_nov.empty:
            # Mostramos el DataFrame crudo para verificar qué llega
            st.dataframe(df_nov.sort_index(ascending=False), use_container_width=True)
        else:
            st.error("No se detectaron datos en la hoja 'NOVEDADES_GUARDIA'.")
            st.info("Verifica que la hoja tenga datos escritos debajo de los encabezados.")

# --- FLUJO DE VISUALIZACIÓN (SUPERVISOR) ---
elif st.session_state.get('rol_sel') == "SUPERVISOR":
    t_pres = st.tabs(["📋 NOVEDADES Y RELEVOS"])[0]
    with t_pres:
        st.subheader("📋 REPORTE DE NOVEDADES")
        df_v = leer_matriz_nube("NOVEDADES_GUARDIA")
        if not df_v.empty:
            st.dataframe(df_v, use_container_width=True)
        else:
            st.warning("La base de datos de novedades está vacía.")
