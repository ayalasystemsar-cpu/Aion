
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

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="AION-YAROKU | CORE", page_icon="🛡️", layout="wide")
ID_MAESTRO_DB = "1Md0VkOnwUJWldq0S1fB9UrmOKv4MG__JVG3tQsda0Uw"

def conectar_google():
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])
        return gspread.authorize(creds)
    except: return None

@st.cache_data(ttl=30)
def leer_matriz_nube(pestana):
    gc = conectar_google()
    if not gc: return pd.DataFrame()
    try:
        hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
        datos = hoja.get_all_values()
        if not datos: return pd.DataFrame()
        return pd.DataFrame(datos[1:], columns=[h.upper().strip() for h in datos[0]])
    except: return pd.DataFrame()

# --- INTERFAZ ---
st.title("🛡️ AION-YAROKU CORE")

# Selector de Roles
rol = st.sidebar.radio("ROL:", ["MONITOREO", "SUPERVISOR", "VIGILADOR", "JEFE", "GERENCIA"])

if rol == "MONITOREO":
    st.header("🛰️ CENTRAL DE INTELIGENCIA")
    
    # Pestañas
    tab1, tab2, tab3, tab4 = st.tabs(["RADAR", "PRESENTISMO", "VIGILADORES", "ALERTAS"])
    
    with tab1:
        st.subheader("Mapa Táctico")
        df_obj = leer_matriz_nube("OBJETIVOS")
        if not df_obj.empty and 'LATITUD' in df_obj.columns:
            # Limpieza para evitar errores de tipo
            df_obj['LATITUD'] = pd.to_numeric(df_obj['LATITUD'].str.replace(',', '.'), errors='coerce')
            df_obj['LONGITUD'] = pd.to_numeric(df_obj['LONGITUD'].str.replace(',', '.'), errors='coerce')
            
            m = folium.Map(location=[-34.6, -58.4], zoom_start=11)
            for _, r in df_obj.dropna(subset=['LATITUD', 'LONGITUD']).iterrows():
                folium.Marker([r['LATITUD'], r['LONGITUD']], tooltip=f"{r['OBJETIVO']} | {r.get('SUPERVISOR', '')}").add_to(m)
            st_folium(m, width="100%")
            
    with tab2:
        df_pres = leer_matriz_nube("PRESENTISMO")
        if not df_pres.empty:
            st.dataframe(df_pres, use_container_width=True)
        else:
            st.warning("No se encontraron registros de presentismo.")

    with tab3:
        df_vig = leer_matriz_nube("VIGILADORES")
        if not df_vig.empty:
            st.dataframe(df_vig, use_container_width=True)

    with tab4:
        df_alt = leer_matriz_nube("ALERTAS")
        if not df_alt.empty:
            st.dataframe(df_alt, use_container_width=True)

elif rol == "VIGILADOR":
    st.header("👮 TERMINAL VIGILADOR")
    with st.form("fichaje"):
        nombre = st.text_input("Nombre")
        dni = st.text_input("DNI")
        obj = st.text_input("Objetivo")
        if st.form_submit_button("Registrar"):
            # Registro directo y simple para no perder datos
            escribir_registro_nube("PRESENTISMO", [datetime.now().strftime("%Y-%m-%d"), datetime.now().strftime("%H:%M:%S"), dni, nombre, obj, "PRESENTE", "INGRESO"])
            st.success("Registrado")

# --- LÓGICA DE ESCRITURA ---
def escribir_registro_nube(pestana, datos):
    gc = conectar_google()
    if gc:
        try:
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
            hoja.append_row(datos)
        except Exception as e:
            st.error(f"Error al escribir: {e}")
