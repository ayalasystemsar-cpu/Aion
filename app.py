
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

# --- FUNCIONES BASE ---
def conectar_google():
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])
        return gspread.authorize(creds)
    except: return None

@st.cache_data(ttl=60)
def leer_matriz_nube(pestana):
    gc = conectar_google()
    if not gc: return pd.DataFrame()
    try:
        hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
        datos = hoja.get_all_values()
        if not datos: return pd.DataFrame()
        return pd.DataFrame(datos[1:], columns=[h.upper().strip() for h in datos[0]])
    except: return pd.DataFrame()

def escribir_registro_nube(pestana, datos):
    gc = conectar_google()
    if gc:
        try:
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
            hoja.append_row(datos)
        except: pass

# --- RADAR TÁCTICO CON CORRECCIONES ---
def mostrar_radar():
    st.subheader("📡 RADAR GLOBAL")
    df_obj = leer_matriz_nube("OBJETIVOS")
    df_alertas = leer_matriz_nube("ALERTAS")
    
    if not df_obj.empty:
        df_obj['LATITUD'] = pd.to_numeric(df_obj['LATITUD'].str.replace(',', '.'), errors='coerce')
        df_obj['LONGITUD'] = pd.to_numeric(df_obj['LONGITUD'].str.replace(',', '.'), errors='coerce')
        
        m = folium.Map(location=[-34.6, -58.4], zoom_start=11, tiles="CartoDB dark_matter")
        
        for _, r in df_obj.dropna(subset=['LATITUD', 'LONGITUD']).iterrows():
            folium.Marker(
                [r['LATITUD'], r['LONGITUD']], 
                tooltip=f"🎯 {r['OBJETIVO']} | 👤 {r.get('SUPERVISOR', 'N/A')}",
                icon=folium.Icon(color="blue", icon="shield")
            ).add_to(m)
            
        st_folium(m, width="100%", height=500)

# --- FLUJO PRINCIPAL ---
if 'rol_sel' not in st.session_state: st.session_state.rol_sel = "MONITOREO"

st.sidebar.title("🛡️ AION-YAROKU")
rol = st.sidebar.radio("SELECCIONAR ROL:", ["MONITOREO", "SUPERVISOR", "VIGILADOR"])

if rol == "MONITOREO":
    mostrar_radar()
    st.dataframe(leer_matriz_nube("PRESENTISMO"), use_container_width=True)

elif rol == "VIGILADOR":
    st.header("👮 FICHAJE VIGILADOR")
    with st.form("fichaje_form"):
        nombre = st.text_input("Nombre y Apellido")
        dni = st.text_input("DNI")
        obj = st.selectbox("Objetivo", leer_matriz_nube("OBJETIVOS")['OBJETIVO'].unique())
        if st.form_submit_button("REGISTRAR"):
            escribir_registro_nube("PRESENTISMO", [datetime.now().strftime("%Y-%m-%d"), datetime.now().strftime("%H:%M:%S"), dni, f"{nombre} - {obj}", obj, "OK", "INGRESO"])
            st.success("Registrado correctamente")
