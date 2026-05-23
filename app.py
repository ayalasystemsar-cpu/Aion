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

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="AION-YAROKU | CORE", page_icon="🛡️", layout="wide", initial_sidebar_state="expanded")

# --- LÓGICA DE DATOS ---
def conectar_google():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        return gspread.authorize(creds)
    except: return None

def leer_matriz_nube(pestana):
    gc = conectar_google()
    if gc:
        try:
            hoja = gc.open_by_key("1Md0VkOnwUJWldq0S1fB9UrmOKv4MG__JVG3tQsda0Uw").worksheet(pestana)
            data = hoja.get_all_values()
            return pd.DataFrame(data[1:], columns=[str(h).upper() for h in data[0]]) if data else pd.DataFrame()
        except: return pd.DataFrame()
    return pd.DataFrame()

# --- CSS E IDENTIDAD ---
st.markdown("""<style>
    .stApp { background: radial-gradient(circle at top, #0A0F1E 0%, #030305 100%) !important; color: #E0E0E0; font-family: 'Rajdhani', sans-serif; }
    @keyframes pulse { 0% { fill: #FF0000; stroke-width: 2; } 50% { fill: #B30000; stroke-width: 15; stroke-opacity: 0.3; } 100% { fill: #FF0000; stroke-width: 2; } }
    .panic-pulse { animation: pulse 1s infinite; }
</style>""", unsafe_allow_html=True)

# --- ESTADO Y SIDEBAR ---
if 'rol_sel' not in st.session_state: st.session_state.rol_sel = "MONITOREO"
with st.sidebar:
    if st.button("🛰️ MONITOREO"): st.session_state.rol_sel = "MONITOREO"; st.rerun()
    if st.button("📋 JEFE OPERACIONES"): st.session_state.rol_sel = "JEFE DE OPERACIONES"; st.rerun()
    if st.button("🏢 GERENCIA"): st.session_state.rol_sel = "GERENCIA"; st.rerun()
    if st.button("👮 VIGILADOR"): st.session_state.rol_sel = "VIGILADOR"; st.rerun()
    if st.button("⚙️ ADMINISTRADOR"): st.session_state.rol_sel = "ADMINISTRADOR"; st.rerun()

# --- FLUJO POR ROLES ---
if st.session_state.rol_sel == "MONITOREO":
    df_alertas = leer_matriz_nube("ALERTAS")
    pendientes = df_alertas[df_alertas['ESTADO'].astype(str).str.upper() == 'PENDIENTE'] if not df_alertas.empty else pd.DataFrame()
    sos_activos = len(pendientes)
    
    st.metric("🚨 S.O.S ACTIVOS", sos_activos)
    # Lógica de mapa con KEY DINÁMICO para titileo
    df_obj = leer_matriz_nube("OBJETIVOS")
    m = folium.Map(location=[-34.6, -58.4], zoom_start=11, tiles="CartoDB dark_matter")
    for _, r in df_obj.iterrows():
        es_panico = r['OBJETIVO'] in pendientes['CARGA_UTIL'].astype(str).values
        folium.CircleMarker([float(r['LATITUD']), float(r['LONGITUD'])], radius=12 if es_panico else 7, 
                            color="red" if es_panico else "cyan", className="panic-pulse" if es_panico else "").add_to(m)
    st_folium(m, key=f"mapa_{sos_activos}", width="100%")

elif st.session_state.rol_sel == "GERENCIA":
    st.subheader("🏢 COMANDO ESTRATÉGICO: GERENCIA")
    t1, t2 = st.tabs(["📊 AUDITORÍA", "📩 COMUNICACIÓN"])
    with t1: st.write("Tablero de KPIs y Desgaste de Flota.")
    with t2: st.text_area("Envío de directivas a la red.")

elif st.session_state.rol_sel == "ADMINISTRADOR":
    st.subheader("⚙️ NÚCLEO MAESTRO")
    if "admin_ok" not in st.session_state: st.session_state.admin_ok = False
    
    if not st.session_state.admin_ok:
        u = st.text_input("Usuario:")
        p = st.text_input("Pass:", type="password")
        if st.button("ACCEDER"):
            if u == "admin" and p == "aion2026": st.session_state.admin_ok = True; st.rerun()
    else:
        st.success("Acceso Maestro Autorizado.")
        if st.button("CERRAR SESIÓN"): st.session_state.admin_ok = False; st.rerun()
        st.write("Configuraciones del sistema, logs de acceso y gestión de base de datos.")

elif st.session_state.rol_sel == "JEFE DE OPERACIONES":
    st.write("Panel de control de alta/baja de objetivos y recursos.")

elif st.session_state.rol_sel == "VIGILADOR":
    st.write("Terminal de fichaje biométrico y novedades de puesto.")
