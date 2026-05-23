import streamlit as st
import datetime
from datetime import datetime
import pandas as pd
import pytz
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import folium
from streamlit_folium import st_folium

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="AION-YAROKU | CORE", page_icon="🛡️", layout="wide", initial_sidebar_state="expanded")
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

def escribir_registro_nube(pestana, datos_fila):
    gc = conectar_google()
    if gc:
        try:
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
            hoja.append_row(datos_fila)
        except: pass

# --- RADAR TÁCTICO CON ICONOS ---
def renderizar_radar():
    df_obj = leer_matriz_nube("OBJETIVOS")
    df_com = leer_matriz_nube("COMISARIAS ")
    
    m = folium.Map(location=[-34.6, -58.4], zoom_start=11, tiles="CartoDB dark_matter")
    
    # 1. OBJETIVOS (Escudo Azul)
    if not df_obj.empty and 'LATITUD' in df_obj.columns:
        df_obj['LATITUD'] = pd.to_numeric(df_obj['LATITUD'].str.replace(',', '.'), errors='coerce')
        df_obj['LONGITUD'] = pd.to_numeric(df_obj['LONGITUD'].str.replace(',', '.'), errors='coerce')
        for _, r in df_obj.dropna(subset=['LATITUD', 'LONGITUD']).iterrows():
            folium.Marker(
                [r['LATITUD'], r['LONGITUD']],
                tooltip=f"🎯 {r['OBJETIVO']} | 👤 {r.get('SUPERVISOR', 'N/A')}",
                icon=folium.Icon(color="blue", icon="shield", prefix="fa")
            ).add_to(m)
            
    # 2. COMISARIAS (Edificio Rojo)
    if not df_com.empty and 'LATITUD' in df_com.columns:
        df_com['LATITUD'] = pd.to_numeric(df_com['LATITUD'].str.replace(',', '.'), errors='coerce')
        df_com['LONGITUD'] = pd.to_numeric(df_com['LONGITUD'].str.replace(',', '.'), errors='coerce')
        for _, c in df_com.dropna(subset=['LATITUD', 'LONGITUD']).iterrows():
            folium.Marker(
                [c['LATITUD'], c['LONGITUD']],
                tooltip=f"🚓 COMISARIA: {c['NOMBRE']}",
                icon=folium.Icon(color="red", icon="building", prefix="fa")
            ).add_to(m)
    st_folium(m, width="100%", height=500)

# --- FLUJO PRINCIPAL ---
if 'rol_sel' not in st.session_state: st.session_state.rol_sel = "MONITOREO"

st.sidebar.title("🛡️ AION-YAROKU")
rol = st.sidebar.radio("SELECCIONAR ROL:", ["MONITOREO", "VIGILADOR", "JEFE", "GERENCIA", "ADMINISTRADOR"])

if rol == "MONITOREO":
    st.header("🛰️ CENTRAL DE INTELIGENCIA OPERATIVA")
    renderizar_radar()
    t1, t2, t3, t4 = st.tabs(["PRESENTISMO", "VIGILADORES", "NOVEDADES", "ALERTAS"])
    with t1: st.dataframe(leer_matriz_nube("PRESENTISMO"), use_container_width=True)
    with t2: st.dataframe(leer_matriz_nube("VIGILADORES"), use_container_width=True)
    with t3: st.dataframe(leer_matriz_nube("NOVEDADES_GUARDIA"), use_container_width=True)
    with t4: st.dataframe(leer_matriz_nube("ALERTAS"), use_container_width=True)

elif rol == "VIGILADOR":
    st.header("👮 FICHAJE")
    with st.form("fichaje_form"):
        nombre = st.text_input("Nombre")
        dni = st.text_input("DNI")
        obj = st.text_input("Objetivo")
        if st.form_submit_button("REGISTRAR"):
            escribir_registro_nube("PRESENTISMO", [datetime.now().strftime("%Y-%m-%d"), datetime.now().strftime("%H:%M:%S"), dni, f"{nombre} - {obj}", obj, "OK", "INGRESO"])
            st.success("Registrado")

elif rol == "JEFE":
    st.header("📋 COMANDO DE OPERACIONES")
    st.dataframe(leer_matriz_nube("NOVEDADES_GUARDIA").tail(20), use_container_width=True)

elif rol == "GERENCIA":
    st.header("🏢 COMANDO ESTRATÉGICO")
    st.metric("Total Novedades", len(leer_matriz_nube("NOVEDADES_GUARDIA")))
    st.dataframe(leer_matriz_nube("PETICIONES"), use_container_width=True)

elif rol == "ADMINISTRADOR":
    st.header("⚙️ NÚCLEO MAESTRO")
    pwd = st.text_input("PASSWORD", type="password")
    if pwd == "aion2026":
        st.success("Acceso total")
        st.write(leer_matriz_nube("ALERTAS").tail(10))

