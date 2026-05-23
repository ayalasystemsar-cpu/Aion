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

# --- FUNCIONES DE CONEXIÓN Y DATOS ---
def conectar_google():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        return gspread.authorize(creds)
    except: return None

def obtener_hora_argentina():
    tz = pytz.timezone("America/Argentina/Buenos_Aires")
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

def leer_matriz_nube(pestana):
    gc = conectar_google()
    if gc:
        try:
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
            data = hoja.get_all_records()
            return pd.DataFrame(data) if data else pd.DataFrame()
        except: return pd.DataFrame()
    return pd.DataFrame()

def escribir_registro_nube(pestana, datos_fila):
    gc = conectar_google()
    if gc:
        hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
        hoja.append_row(datos_fila)

def cargar_objetivos():
    df = leer_matriz_nube("OBJETIVOS")
    if not df.empty:
        df.columns = df.columns.str.strip().str.upper()
        df = df[df['OBJETIVO'].notna()]
        if 'SUPERVISOR' in df.columns:
            df['SUPERVISOR'] = df['SUPERVISOR'].astype(str).str.strip().str.upper()
        df['LATITUD'] = pd.to_numeric(df['LATITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        df['LONGITUD'] = pd.to_numeric(df['LONGITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        return df
    return pd.DataFrame()

# --- FUNCIÓN UNIFICADA DE COMUNICACIONES ---
def renderizar_comunicaciones():
    st.markdown('<h3>📥 BANDEJA DE INTELIGENCIA</h3>', unsafe_allow_html=True)
    df_chats = leer_matriz_nube("CHATS")
    if not df_chats.empty:
        for _, msg in df_chats.tail(10).iloc[::-1].iterrows():
            es_rojo = msg.get("PRIORIDAD", "VERDE") == "ROJA"
            st.markdown(f'<div class="{"message-box-red" if es_rojo else "message-box"}"><div class="{"message-info-red" if es_rojo else "message-info"}">{msg.get("HORA")} De: {msg.get("USUARIO")}</div><div class="message-text">{msg.get("TEXTO")}</div></div>', unsafe_allow_html=True)
    else:
        st.info("Sin comunicaciones.")

# --- INICIALIZACIÓN ---
if 'rol_sel' not in st.session_state: st.session_state.rol_sel = "MONITOREO"
if 'user_sel' not in st.session_state: st.session_state.user_sel = "OPERADOR CENTRAL"
if 'sup_autenticado' not in st.session_state: st.session_state.sup_autenticado = False

df_objetivos = cargar_objetivos()

# --- 7. FLUJO POR ROLES ---
if st.session_state.rol_sel == "MONITOREO":
    df_emergencias = leer_matriz_nube("ALERTAS")
    t_radar, t_gestion, t_comunicacion, t_pres = st.tabs(["🚨 RADAR S.O.S", "📖 LIBRO DE BASE", "💬 COMUNICACIÓN", "📋 PRESENTISMO"])
    with t_radar: st.info("📡 Radar Activo")
    with t_gestion:
        if not df_emergencias.empty: st.dataframe(df_emergencias.iloc[::-1], use_container_width=True)
    with t_comunicacion: renderizar_comunicaciones()
    with t_pres: st.write("Gestión de presentismo")

elif st.session_state.rol_sel == "JEFE DE OPERACIONES":
    t_crisis, t_ejecucion, t_auditoria = st.tabs(["Centro de Crisis", "Ejecución", "Auditoría"])
    with t_crisis:
        st.subheader("Radar de Objetivos")
        # Aquí iría tu lógica de Folium...
    with t_ejecucion: st.write("Panel de Gestión")
    with t_auditoria: st.write("Reportes")

elif st.session_state.rol_sel == "SUPERVISOR":
    t_vis_qr, t_car_tac, t_com_sup, t_pres_sup = st.tabs(["Visita QR", "Carga Táctica", "Comunicación", "📋 PRESENTISMO"])
    with t_com_sup:
        renderizar_comunicaciones()
    # ... Resto de la lógica del supervisor

elif st.session_state.rol_sel == "GERENCIA":
    st.write("Panel de Dirección")

elif st.session_state.rol_sel == "ADMINISTRADOR":
    st.write("Panel de Administración")
