# --- 1. CONFIGURACIÓN E IDENTIDAD VISUAL (AION-YAROKU CORE) ---
import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
from datetime import datetime
import pytz
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ✅ CORRECCIÓN GEOLOCALIZACIÓN
try:
    from streamlit_js_eval import get_geolocation
except ImportError:
    get_geolocation = None

st.set_page_config(
    page_title="AION-YAROKU | CORE",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CONEXIONES (GOOGLE MATRIZ INTEGRAL) ---
ID_MAESTRO_DB = "1Md0VkOnwUJWldq0S1fB9UrmOKv4MG__JVG3tQsda0Uw"

def conectar_google():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        return gspread.authorize(creds)
    except: return None

# --- 3. FUNCIONES DE LÓGICA Y NORMALIZACIÓN MAESTRA ---
def obtener_hora_argentina():
    tz = pytz.timezone("America/Argentina/Buenos_Aires")
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

@st.cache_data(ttl=15)
def leer_matriz_nube(pestana):
    gc = conectar_google()
    if gc:
        try:
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
            df = pd.DataFrame(hoja.get_all_records())
            # ✅ NORMALIZACIÓN TOTAL: Mayúsculas y sin espacios en encabezados
            df.columns = df.columns.str.strip().str.upper()
            return df
        except: return pd.DataFrame()
    return pd.DataFrame()

def escribir_registro_nube(pestana, datos_fila):
    try:
        gc = conectar_google()
        if gc:
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
            hoja.append_row(datos_fila)
            return True
    except: return False

def actualizar_celda(pestana, fila, columna, valor):
    try:
        gc = conectar_google()
        if gc:
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
            hoja.update_acell(f"{columna}{fila}", valor)
            return True
    except: return False

# --- 4. DISEÑO ALPHA ---
def aplicar_identidad_alfa():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@300;500;700&display=swap');
        .stApp { background: radial-gradient(circle at top, #0A0F1E 0%, #030305 100%) !important; color: #E0E0E0; font-family: 'Rajdhani', sans-serif; }
        [data-testid="stSidebar"] { background-color: #050507 !important; border-right: 1px solid rgba(0, 229, 255, 0.3) !important; }
        .contenedor-logo-central { display: flex; justify-content: center; width: 100%; margin-bottom: 20px; }
        .logo-phoenix { width: 520px !important; border: 2px solid #00e5ff !important; box-shadow: 0 0 35px rgba(0, 229, 255, 0.5); border-radius: 4px; }
        .stButton > button[kind="primary"] { 
            background: radial-gradient(circle, #FF0000 0%, #8B0000 100%) !important; 
            border-radius: 50% !important; width: 105px !important; height: 105px !important; 
            font-family: 'Orbitron', sans-serif; font-size: 11px !important; color: white !important;
        }
        h1, h2, h3, .stSubheader { font-family: 'Orbitron', sans-serif; color: #00E5FF !important; }
        </style>
        """, unsafe_allow_html=True
    )

aplicar_identidad_alfa()
st.markdown('<div class="contenedor-logo-central"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" class="logo-phoenix"></div>', unsafe_allow_html=True)

# --- 5. PANEL DE CONTROL (SIDEBAR) ---
if 'rol_sel' not in st.session_state: st.session_state.rol_sel = "SUPERVISOR"
if 'user_sel' not in st.session_state: st.session_state.user_sel = "BRIAN AYALA"

with st.sidebar:
    st.subheader("🛡️ PANEL DE CONTROL")
    st.session_state.rol_sel = st.selectbox("NIVEL DE ACCESO", ["SUPERVISOR", "MONITOREO", "JEFE DE OPERACIONES", "GERENCIA", "ADMINISTRADOR"])
    st.session_state.user_sel = st.selectbox("IDENTIDAD", ["BRIAN AYALA", "DARÍO CECILIA", "LUIS BONGIORNO", "SANOJA LUIS", "MAZACOTTE CLAUDIO"])
    st.markdown("---")
    if st.button("ACTIVAR\nPÁNICO", type="primary"):
        escribir_registro_nube("ALERTAS", [obtener_hora_argentina(), st.session_state.user_sel, "PÁNICO", "PENDIENTE"])
        st.error("❗ SOS TRANSMITIDO")

# --- 6. FLUJO POR ROLES ---

# A. SUPERVISOR
if st.session_state.rol_sel == "SUPERVISOR":
    st.subheader(f"📱 Estación: {st.session_state.user_sel}")
    t1, t2, t3 = st.tabs(["📍 RADAR", "📝 NOVEDADES", "💬 COMUNICACIÓN"])
    
    with t2:
        df_obj = leer_matriz_nube("OBJETIVOS")
        with st.form("nov_sup"):
            f_dest = st.selectbox("Objetivo:", df_obj['OBJETIVO'].unique()) if not df_obj.empty else "N/A"
            f_nov = st.text_area("Informe de Novedad")
            if st.form_submit_button("🚀 TRANSMITIR"):
                escribir_registro_nube("ACTAS_FLOTAS", [obtener_hora_argentina(), st.session_state.user_sel, "", "", "", "", "", f_dest, f_nov, "VERDE"])
                st.success("Acta enviada.")

# B. MONITOREO
elif st.session_state.rol_sel == "MONITOREO":
    st.header("🛰️ CENTRAL DE INTELIGENCIA")
    df_alertas = leer_matriz_nube("ALERTAS")
    sos_activos = len(df_alertas[df_alertas['ESTADO'] == 'PENDIENTE']) if not df_alertas.empty else 0
    st.metric("🚨 S.O.S ACTIVOS", sos_activos)

    t_radar, t_chat = st.tabs(["🚨 RADAR S.O.S", "💬 COMUNICACIÓN"])
    
    with t_radar:
        if sos_activos > 0:
            last_sos = df_alertas[df_alertas['ESTADO'] == 'PENDIENTE'].iloc[-1]
            # Mapeo dinámico de columna de usuario
            u_col = next((c for c in df_alertas.columns if any(k in c for k in ["USUARIO", "OPERADOR", "EMISOR"])), df_alertas.columns[1])
            st.error(f"🚨 ALERTA CRÍTICA: {last_sos[u_col]}")
            if st.button("✅ FINALIZAR EMERGENCIA"):
                fila = df_alertas[df_alertas['ESTADO'] == 'PENDIENTE'].index[-1] + 2
                actualizar_celda("ALERTAS", fila, "D", "RESUELTO")
                st.rerun()
        else: st.success("Vigilancia Pasiva OK")

    with t_chat:
        df_m = leer_matriz_nube("MENSAJERIA")
        if not df_m.empty:
            c_emi = next((c for c in df_m.columns if "EMISOR" in c or "OPERADOR" in c), None)
            c_con = next((c for c in df_m.columns if "CONTENIDO" in c or "MENSAJE" in c), None)
            if c_emi and c_con:
                for _, m in df_m.tail(15).iloc[::-1].iterrows():
                    with st.chat_message("user"): st.write(f"**{m[c_emi]}**: {m[c_con]}")

# C. JEFE DE OPERACIONES
elif st.session_state.rol_sel == "JEFE DE OPERACIONES":
    st.header("📋 COMANDO TÁCTICO")
    df_actas = leer_matriz_nube("ACTAS_FLOTAS")
    st.dataframe(df_actas.tail(30), use_container_width=True)

# D. GERENCIA
elif st.session_state.rol_sel == "GERENCIA":
    st.header("📈 DASHBOARD GERENCIAL")
    st.subheader("Estructura de Servicios")
    st.dataframe(leer_matriz_nube("ESTRUCTURA"), use_container_width=True)

# E. ADMINISTRADOR
elif st.session_state.rol_sel == "ADMINISTRADOR":
    st.header("⚙️ NÚCLEO MAESTRO")
    u = st.text_input("ADMIN_USER")
    p = st.text_input("ADMIN_PASS", type="password")
    if u == "admin" and p == "aion2026":
        if st.button("REINICIAR CACHÉ DE MATRIZ"):
            st.cache_data.clear()
            st.success("Datos actualizados desde la nube.")
