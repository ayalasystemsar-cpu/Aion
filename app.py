import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import folium
from streamlit_folium import st_folium
import math

# Configuración básica
st.set_page_config(layout="wide")
ID_MAESTRO_DB = "1Md0VkOnwUJWldq0S1fB9UrmOKv4MG__JVG3tQsda0Uw"

def conectar():
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])
        return gspread.authorize(creds)
    except: return None

@st.cache_data(ttl=60)
def cargar_datos(pestana):
    gc = conectar()
    if not gc: return pd.DataFrame()
    try:
        hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
        data = hoja.get_all_values()
        return pd.DataFrame(data[1:], columns=[h.upper().strip() for h in data[0]])
    except: return pd.DataFrame()

# --- INTERFAZ ---
st.title("🛡️ AION-YAROKU | PANEL DE CONTROL")
rol = st.sidebar.radio("ROL:", ["MONITOREO", "VIGILADOR"])

if rol == "MONITOREO":
    st.subheader("RADAR Y ALERTAS")
    df_obj = cargar_datos("OBJETIVOS")
    
    if not df_obj.empty and 'LATITUD' in df_obj.columns:
        df_obj['LATITUD'] = pd.to_numeric(df_obj['LATITUD'].str.replace(',', '.'), errors='coerce')
        df_obj['LONGITUD'] = pd.to_numeric(df_obj['LONGITUD'].str.replace(',', '.'), errors='coerce')
        
        m = folium.Map(location=[-34.6, -58.4], zoom_start=11, tiles="CartoDB dark_matter")
        for _, r in df_obj.dropna(subset=['LATITUD', 'LONGITUD']).iterrows():
            folium.Marker([r['LATITUD'], r['LONGITUD']], tooltip=f"{r['OBJETIVO']}").add_to(m)
        st_folium(m, width="100%", height=400)
    
    st.subheader("TABLAS MAESTRAS")
    c1, c2 = st.columns(2)
    with c1: st.write("Presentismo", cargar_datos("PRESENTISMO"))
    with c2: st.write("Novedades", cargar_datos("NOVEDADES_GUARDIA"))

elif rol == "VIGILADOR":
    st.header("FICHAJE")
    with st.form("fichaje"):
        nombre = st.text_input("Nombre")
        dni = st.text_input("DNI")
        obj = st.text_input("Objetivo")
        if st.form_submit_button("REGISTRAR"):
            gc = conectar()
            if gc:
                hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet("PRESENTISMO")
                hoja.append_row(["2026-05-23", "13:20", dni, nombre, obj, "OK", "INGRESO"])
                st.success("Registrado")
