# --- 1. CONFIGURACIÓN E IDENTIDAD VISUAL CORPORATIVA (AION-YAROKU CORE) ---
import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
from datetime import datetime
import pytz
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from supabase import create_client, Client
import base64
import time

# ✅ CORRECCIÓN GEOLOCALIZACIÓN: Evita caídas de interfaz[cite: 2]
try:
    from streamlit_js_eval import get_geolocation
except ImportError:
    get_geolocation = None

# Configuración de página OLED[cite: 2]
st.set_page_config(
    page_title="AION-YAROKU | CORE",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CONEXIONES (SUPABASE & GOOGLE MATRIZ) ---
ID_MAESTRO_DB = "1Md0VkOnwUJWldq0S1fB9UrmOKv4MG__JVG3tQsda0Uw"[cite: 1]

@st.cache_resource
def init_connection():
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except Exception: return None

supabase = init_connection()

def conectar_google():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"][cite: 1]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)[cite: 1]
        return gspread.authorize(creds)[cite: 1]
    except: return None

# --- 3. FUNCIONES DE LÓGICA, DATOS Y COMANDOS ---
def obtener_hora_argentina():
    tz = pytz.timezone("America/Argentina/Buenos_Aires")[cite: 1]
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")[cite: 1]

def actualizar_celda(pestana, fila, columna, valor):
    try:
        gc = conectar_google()[cite: 1]
        if gc:
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)[cite: 1]
            hoja.update_acell(f"{columna}{fila}", valor)[cite: 1]
            return True
    except: return False

def escribir_registro_nube(pestana, datos_fila):
    try:
        gc = conectar_google()[cite: 1]
        if gc:
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)[cite: 1]
            hoja.append_row(datos_fila)[cite: 1]
            return True
    except: return False

@st.cache_data(ttl=15)
def leer_matriz_nube(pestana):
    gc = conectar_google()[cite: 1]
    if gc:
        try:
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)[cite: 1]
            return pd.DataFrame(hoja.get_all_records())[cite: 1]
        except: return pd.DataFrame()
    return pd.DataFrame()

@st.cache_data(ttl=60)
def cargar_objetivos():
    df = leer_matriz_nube("OBJETIVOS")[cite: 1]
    if not df.empty:
        df.columns = df.columns.str.strip().str.upper()[cite: 1]
        df['LATITUD'] = pd.to_numeric(df['LATITUD'].astype(str).str.replace(',', '.'), errors='coerce')[cite: 1]
        df['LONGITUD'] = pd.to_numeric(df['LONGITUD'].astype(str).str.replace(',', '.'), errors='coerce')[cite: 1]
        return df.dropna(subset=['LATITUD', 'LONGITUD'])[cite: 1]
    return pd.DataFrame()

# --- 4. DISEÑO E IDENTIDAD VISUAL (PUNTO MEDIO Y LUCES) ---
def aplicar_identidad_alfa():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@300;500;700&display=swap');
        
        .stApp { background: radial-gradient(circle at top, #0A0F1E 0%, #030305 100%) !important; color: #E0E0E0; font-family: 'Rajdhani', sans-serif; }
        
        [data-testid="stSidebar"] { background-color: #050507 !important; border-right: 1px solid rgba(0, 229, 255, 0.3) !important; }
        
        /* LOGO CENTRAL CON MARCO Y GLOW */
        .contenedor-logo-central { display: flex; justify-content: center; align-items: center; width: 100%; margin-top: -10px; margin-bottom: 20px; }
        .logo-phoenix { width: 520px !important; border: 2px solid #00e5ff !important; box-shadow: 0 0 35px rgba(0, 229, 255, 0.5) !important; border-radius: 4px !important; background-color: #000 !important; }
        
        /* BOTÓN DE PÁNICO: CENTRADO ABSOLUTO */
        .panico-container { display: flex !important; justify-content: center !important; align-items: center !important; width: 100% !important; margin: 20px 0 !important; padding: 0 !important; }
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div { display: flex !important; justify-content: center !important; width: 100% !important; }
        div[data-testid="stButton"] { display: flex !important; justify-content: center !important; width: 100% !important; }
        
        .stButton > button[kind="primary"] { 
            background: radial-gradient(circle, #FF0000 0%, #8B0000 100%) !important; 
            color: white !important; 
            border-radius: 50% !important; 
            width: 105px !important; 
            height: 105px !important; 
            border: 3px solid #333 !important; 
            box-shadow: 0 0 25px rgba(255, 0, 0, 0.5) !important; 
            font-family: 'Orbitron', sans-serif; 
            font-size: 11px !important; 
            font-weight: bold; 
            line-height: 1.1; 
            text-transform: uppercase; 
            margin: 0 auto !important; 
        }

        .radar-box { border: 1px solid #1A1A1B; border-radius: 12px; padding: 20px; background: rgba(10, 10, 11, 0.8); }
        h1, h2, h3, .stSubheader { font-family: 'Orbitron', sans-serif; color: #00E5FF !important; text-shadow: 0 0 15px rgba(0, 229, 255, 0.4); }
        </style>
        """, unsafe_allow_html=True
    )

aplicar_identidad_alfa()

# Render Logo Central[cite: 2]
st.markdown('<div class="contenedor-logo-central"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" class="logo-phoenix"></div>', unsafe_allow_html=True)

# --- 5. MEMORIA DE SESIÓN Y SIDEBAR ---
if 'rol_sel' not in st.session_state: st.session_state.rol_sel = "SUPERVISOR"[cite: 1]
if 'user_sel' not in st.session_state: st.session_state.user_sel = "BRIAN AYALA"[cite: 1]

with st.sidebar:
    st.markdown('<div style="margin-top: 50px;"></div>', unsafe_allow_html=True)
    st.subheader("🛡️ PANEL DE CONTROL")
    perfiles = ["SUPERVISOR", "MONITOREO", "JEFE DE OPERACIONES", "GERENCIA", "ADMINISTRADOR"][cite: 1, 2]
    st.session_state.rol_sel = st.selectbox("NIVEL DE ACCESO", perfiles)[cite: 2]
    
    lista_sups = ["BRIAN AYALA", "DARÍO CECILIA", "LUIS BONGIORNO", "SUPERVISOR NOCTURNO", "SERANTES WALTER", "SANOJA LUIS", "MAZACOTTE CLAUDIO"][cite: 1, 2]
    st.session_state.user_sel = st.selectbox("IDENTIDAD OPERATIVA", lista_sups)[cite: 1, 2]
    
    st.markdown("---")
    st.markdown('<div class="panico-container">', unsafe_allow_html=True)
    if st.button("ACTIVAR\nPÁNICO", type="primary"):[cite: 2]
        datos_sos = [obtener_hora_argentina(), st.session_state.user_sel, "PÁNICO", "PENDIENTE"][cite: 1, 2]
        if escribir_registro_nube("ALERTAS", datos_sos):[cite: 1, 2]
            st.error("❗ SOS TRANSMITIDO")[cite: 2]
    st.markdown('</div>', unsafe_allow_html=True)

# --- 6. INTERFAZ OPERATIVA ---
df_objetivos = cargar_objetivos()[cite: 1]

# MÓDULO SUPERVISOR[cite: 1]
if st.session_state.rol_sel == "SUPERVISOR":
    st.subheader(f"📱 Estación: {st.session_state.user_sel}")[cite: 2]
    
    # Lógica de filtrado de zona[cite: 1]
    apellido = st.session_state.user_sel.split()[-1].upper()[cite: 1]
    df_zona = df_objetivos[df_objetivos['SUPERVISOR'].str.upper().str.contains(apellido, na=False)] if not df_objetivos.empty else pd.DataFrame()[cite: 1]
    if df_zona.empty: df_zona = df_objetivos[cite: 1]

    t1, t2, t3 = st.tabs(["📍 RADAR & GPS", "📝 NOVEDADES", "💬 COMUNICACIÓN"])[cite: 1]

    with t1:
        st.markdown('<div class="radar-box">', unsafe_allow_html=True)[cite: 2]
        if not df_zona.empty:
            m = folium.Map(location=[df_zona['LATITUD'].mean(), df_zona['LONGITUD'].mean()], zoom_start=12, tiles="CartoDB dark_matter")[cite: 1, 2]
            for _, r in df_zona.iterrows():
                folium.Marker([r['LATITUD'], r['LONGITUD']], popup=r['OBJETIVO'], icon=folium.Icon(color="blue", icon="shield", prefix="fa")).add_to(m)[cite: 1, 2]
            st_folium(m, width="100%", height=350)[cite: 1, 2]
        st.markdown('</div>', unsafe_allow_html=True)

    with t2:
        st.subheader("📝 REPORTE DE NOVEDADES")[cite: 1]
        with st.form("acta_tactica"):
            f_dest = st.selectbox("Objetivo:", df_zona['OBJETIVO'].unique()) if not df_zona.empty else "N/A"[cite: 1]
            f_vig = st.text_input("Personal en Puesto")[cite: 1]
            f_nov = st.text_area("Informe de Novedad")[cite: 1]
            gravedad = st.select_slider("GRAVEDAD:", options=["VERDE", "AMARILLO", "ROJO"])[cite: 1]
            if st.form_submit_button("🚀 TRANSMITIR ACTA"):[cite: 1]
                datos = [obtener_hora_argentina(), st.session_state.user_sel, "", "", "", "", f_vig, f_dest, f_nov, gravedad][cite: 1]
                if escribir_registro_nube("ACTAS_FLOTAS", datos):[cite: 1]
                    st.success("Acta derivada a la matriz.")[cite: 1]

    with t3:
        st.info("Bandeja de Mensajería Sincronizada con Matriz Nube")

# MÓDULO MONITOREO[cite: 1]
elif st.session_state.rol_sel == "MONITOREO":
    st.header("🛰️ CENTRAL DE INTELIGENCIA OPERATIVA")[cite: 1]
    
    m1, m2, m3 = st.columns(3)[cite: 1]
    df_emergencias = leer_matriz_nube("ALERTAS")[cite: 1]
    sos_activos = len(df_emergencias[df_emergencias['ESTADO'].astype(str).str.upper() == 'PENDIENTE']) if not df_emergencias.empty else 0[cite: 1]
    
    m1.metric("🚨 S.O.S ACTIVOS", sos_activos)[cite: 1]
    m2.metric("📡 ESTADO DE RED", "OPERATIVO")
    m3.metric("🕒 HORA LOCAL", obtener_hora_argentina().split(" ")[1])

    t_radar, t_gestion, t_chat = st.tabs(["🚨 RADAR S.O.S", "📖 LIBRO DE BASE", "💬 COMUNICACIÓN"])[cite: 1]

    with t_radar:
        if sos_activos > 0:
            datos_sos = df_emergencias[df_emergencias['ESTADO'].astype(str).str.upper() == 'PENDIENTE'].iloc[-1][cite: 1]
            op_en_riesgo = datos_sos['OPERADOR'][cite: 1]
            st.error(f"🚨 ALERTA CRÍTICA: {op_en_riesgo}")[cite: 1]
            
            with st.form("cierre_crisis"):[cite: 1]
                res_acta = st.text_area("Informe de Neutralización")[cite: 1]
                if st.form_submit_button("✅ CERRAR ALERTA"):[cite: 1]
                    fila_real = df_emergencias[df_emergencias['ESTADO'].astype(str).str.upper() == 'PENDIENTE'].index[-1] + 2[cite: 1]
                    if actualizar_celda("ALERTAS", fila_real, "D", "RESUELTO"):[cite: 1]
                        actualizar_celda("ALERTAS", fila_real, "E", res_acta)
                        st.success("Resuelto"); st.cache_data.clear(); st.rerun()[cite: 1]
        else:
            st.success("✅ Sistema en Vigilancia Pasiva")

    with t_gestion:
        with st.form("acta_base"):[cite: 1]
            op_nombre = st.text_input("Operador de Turno:", value=st.session_state.user_sel)[cite: 1]
            nov = st.text_area("Novedades de Guardia")[cite: 1]
            if st.form_submit_button("🔒 SELLAR LIBRO"):[cite: 1]
                escribir_registro_nube("MENSAJERIA", [obtener_hora_argentina(), op_nombre, "DARÍO CECILIA", "LIBRO BASE", nov, "ENVIADO", "VERDE"])[cite: 1]
                st.success("Sellado."); st.rerun()[cite: 1]

# MÓDULO ADMINISTRADOR[cite: 1]
elif st.session_state.rol_sel == "ADMINISTRADOR":
    st.header("⚙️ NÚCLEO MAESTRO")[cite: 1]
    with st.expander("🔐 CREDENCIALES DE INFRAESTRUCTURA"):[cite: 1]
        u_ingreso = st.text_input("ADMIN_USER", key="input_admin_u").lower()[cite: 1]
        p_ingreso = st.text_input("ADMIN_PASS", type="password", key="input_admin_p")[cite: 1]
        if u_ingreso == "admin" and p_ingreso == "aion2026":[cite: 1]
            st.subheader("🏗️ GESTIÓN DE ESTRUCTURA")[cite: 1]
            tipo = st.radio("Categoría:", ["SUPERVISOR", "SERVICIO"], horizontal=True)[cite: 1]
            nuevo_nombre = st.text_input(f"Nombre del {tipo}:").upper()[cite: 1]
            if st.button(f"PROCESAR ALTA"):[cite: 1]
                if nuevo_nombre:
                    escribir_registro_nube("ESTRUCTURA", [obtener_hora_argentina(), tipo, nuevo_nombre, "ACTIVO", st.session_state.user_sel])[cite: 1]
                    st.success("Alta Exitosa")[cite: 1]
