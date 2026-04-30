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

# ✅ CORRECCIÓN GEOLOCALIZACIÓN
try:
    from streamlit_js_eval import get_geolocation
except ImportError:
    get_geolocation = None

# Configuración de página OLED
st.set_page_config(
    page_title="AION-YAROKU | CORE",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CONEXIONES (SUPABASE & GOOGLE MATRIZ) ---
ID_MAESTRO_DB = "1Md0VkOnwUJWldq0S1fB9UrmOKv4MG__JVG3tQsda0Uw"

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
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        return gspread.authorize(creds)
    except: return None

# --- 3. FUNCIONES DE LÓGICA, DATOS Y COMANDOS ---
def obtener_hora_argentina():
    tz = pytz.timezone("America/Argentina/Buenos_Aires")
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

def actualizar_celda(pestana, fila, columna, valor):
    try:
        gc = conectar_google()
        if gc:
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
            hoja.update_acell(f"{columna}{fila}", valor)
            return True
    except: return False

def escribir_registro_nube(pestana, datos_fila):
    try:
        gc = conectar_google()
        if gc:
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
            hoja.append_row(datos_fila)
            return True
    except: return False

@st.cache_data(ttl=15)
def leer_matriz_nube(pestana):
    gc = conectar_google()
    if gc:
        try:
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
            return pd.DataFrame(hoja.get_all_records())
        except: return pd.DataFrame()
    return pd.DataFrame()

@st.cache_data(ttl=60)
def cargar_objetivos():
    df = leer_matriz_nube("OBJETIVOS")
    if not df.empty:
        df.columns = df.columns.str.strip().str.upper()
        df['LATITUD'] = pd.to_numeric(df['LATITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        df['LONGITUD'] = pd.to_numeric(df['LONGITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        return df.dropna(subset=['LATITUD', 'LONGITUD'])
    return pd.DataFrame()

# --- 4. DISEÑO E IDENTIDAD VISUAL (PUNTO MEDIO Y LUCES) ---
def aplicar_identidad_alfa():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@300;500;700&display=swap');
        
        .stApp { background: radial-gradient(circle at top, #0A0F1E 0%, #030305 100%) !important; color: #E0E0E0; font-family: 'Rajdhani', sans-serif; }
        
        [data-testid="stSidebar"] { background-color: #050507 !important; border-right: 1px solid rgba(0, 229, 255, 0.3) !important; }
        
        .contenedor-logo-central { display: flex; justify-content: center; align-items: center; width: 100%; margin-top: -10px; margin-bottom: 20px; }
        .logo-phoenix { width: 520px !important; border: 2px solid #00e5ff !important; box-shadow: 0 0 35px rgba(0, 229, 255, 0.5) !important; border-radius: 4px !important; background-color: #000 !important; }
        
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

st.markdown('<div class="contenedor-logo-central"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" class="logo-phoenix"></div>', unsafe_allow_html=True)

# --- 5. MEMORIA DE SESIÓN Y SIDEBAR ---
if 'rol_sel' not in st.session_state: st.session_state.rol_sel = "SUPERVISOR"
if 'user_sel' not in st.session_state: st.session_state.user_sel = "BRIAN AYALA"

with st.sidebar:
    st.markdown('<div style="margin-top: 50px;"></div>', unsafe_allow_html=True)
    st.subheader("🛡️ PANEL DE CONTROL")
    perfiles = ["SUPERVISOR", "MONITOREO", "JEFE DE OPERACIONES", "GERENCIA", "ADMINISTRADOR"]
    st.session_state.rol_sel = st.selectbox("NIVEL DE ACCESO", perfiles)
    
    lista_sups = ["BRIAN AYALA", "DARÍO CECILIA", "LUIS BONGIORNO", "SUPERVISOR NOCTURNO", "SERANTES WALTER", "SANOJA LUIS", "MAZACOTTE CLAUDIO"]
    st.session_state.user_sel = st.selectbox("IDENTIDAD OPERATIVA", lista_sups)
    
    st.markdown("---")
    st.markdown('<div class="panico-container">', unsafe_allow_html=True)
    if st.button("ACTIVAR\nPÁNICO", type="primary"):
        datos_sos = [obtener_hora_argentina(), st.session_state.user_sel, "PÁNICO", "PENDIENTE"]
        if escribir_registro_nube("ALERTAS", datos_sos):
            st.error("❗ SOS TRANSMITIDO")
    st.markdown('</div>', unsafe_allow_html=True)

# --- 6. INTERFAZ OPERATIVA ---
df_objetivos = cargar_objetivos()

if st.session_state.rol_sel == "SUPERVISOR":
    st.subheader(f"📱 Estación: {st.session_state.user_sel}")
    
    apellido = st.session_state.user_sel.split()[-1].upper()
    df_zona = df_objetivos[df_objetivos['SUPERVISOR'].str.upper().str.contains(apellido, na=False)] if not df_objetivos.empty else pd.DataFrame()
    if df_zona.empty: df_zona = df_objetivos

    t1, t2, t3 = st.tabs(["📍 RADAR & GPS", "📝 NOVEDADES", "💬 COMUNICACIÓN"])

    with t1:
        st.markdown('<div class="radar-box">', unsafe_allow_html=True)
        if not df_zona.empty:
            m = folium.Map(location=[df_zona['LATITUD'].mean(), df_zona['LONGITUD'].mean()], zoom_start=12, tiles="CartoDB dark_matter")
            for _, r in df_zona.iterrows():
                folium.Marker([r['LATITUD'], r['LONGITUD']], popup=r['OBJETIVO'], icon=folium.Icon(color="blue", icon="shield", prefix="fa")).add_to(m)
            st_folium(m, width="100%", height=350)
        st.markdown('</div>', unsafe_allow_html=True)

    with t2:
        st.subheader("📝 REPORTE DE NOVEDADES")
        with st.form("acta_tactica"):
            f_dest = st.selectbox("Objetivo:", df_zona['OBJETIVO'].unique()) if not df_zona.empty else "N/A"
            f_vig = st.text_input("Personal en Puesto")
            f_nov = st.text_area("Informe de Novedad")
            gravedad = st.select_slider("GRAVEDAD:", options=["VERDE", "AMARILLO", "ROJO"])
            if st.form_submit_button("🚀 TRANSMITIR ACTA"):
                datos = [obtener_hora_argentina(), st.session_state.user_sel, "", "", "", "", f_vig, f_dest, f_nov, gravedad]
                if escribir_registro_nube("ACTAS_FLOTAS", datos):
                    st.success("Acta derivada a la matriz.")

    with t3:
        st.info("Bandeja de Mensajería Sincronizada con Matriz Nube")

elif st.session_state.rol_sel == "MONITOREO":
    st.header("🛰️ CENTRAL DE INTELIGENCIA OPERATIVA")
    
    m1, m2, m3 = st.columns(3)
    df_emergencias = leer_matriz_nube("ALERTAS")
    sos_activos = len(df_emergencias[df_emergencias['ESTADO'].astype(str).str.upper() == 'PENDIENTE']) if not df_emergencias.empty else 0
    
    m1.metric("🚨 S.O.S ACTIVOS", sos_activos)
    m2.metric("📡 ESTADO DE RED", "OPERATIVO")
    m3.metric("🕒 HORA LOCAL", obtener_hora_argentina().split(" ")[1])

    t_radar, t_gestion, t_chat = st.tabs(["🚨 RADAR S.O.S", "📖 LIBRO DE BASE", "💬 COMUNICACIÓN"])

    with t_radar:
        if sos_activos > 0:
            # Filtramos las que dicen 'PENDIENTE' en la columna ESTADO[cite: 1]
            datos_sos = df_emergencias[df_emergencias['ESTADO'].astype(str).str.upper() == 'PENDIENTE'].iloc[-1]
            
            # 🚨 CAMBIO CLAVE: Usamos 'USUARIO' porque así está en tu GSheet[cite: 1]
            op_en_riesgo = datos_sos['USUARIO'] 
            st.error(f"🚨 ALERTA CRÍTICA: {op_en_riesgo}")
            
            with st.form("cierre_crisis"):
                res_acta = st.text_area("Informe de Neutralización")
                if st.form_submit_button("✅ CERRAR ALERTA"):
                    # Buscamos la fila (index + 2)[cite: 1]
                    fila_real = df_emergencias[df_emergencias['ESTADO'].astype(str).str.upper() == 'PENDIENTE'].index[-1] + 2
                    # 'D' es la columna ESTADO en tu archivo[cite: 1]
                    if actualizar_celda("ALERTAS", fila_real, "D", "RESUELTO"):
                        actualizar_celda("ALERTAS", fila_real, "E", res_acta)
                        st.success("Emergencia Resuelta")
                        st.cache_data.clear()
                        st.rerun()
        else:
            st.success("✅ Sistema en Vigilancia Pasiva")

    with t_gestion:
        with st.form("acta_base"):
            op_nombre = st.text_input("Operador de Turno:", value=st.session_state.user_sel)
            nov = st.text_area("Novedades de Guardia")
            if st.form_submit_button("🔒 SELLAR LIBRO"):
                escribir_registro_nube("MENSAJERIA", [obtener_hora_argentina(), op_nombre, "DARÍO CECILIA", "LIBRO BASE", nov, "ENVIADO", "VERDE"])
                st.success("Sellado."); st.rerun()

elif st.session_state.rol_sel == "ADMINISTRADOR":
    st.header("⚙️ NÚCLEO MAESTRO")
    with st.expander("🔐 CREDENCIALES DE INFRAESTRUCTURA"):
        u_ingreso = st.text_input("ADMIN_USER", key="input_admin_u").lower()
        p_ingreso = st.text_input("ADMIN_PASS", type="password", key="input_admin_p")
        if u_ingreso == "admin" and p_ingreso == "aion2026":
            st.subheader("🏗️ GESTIÓN DE ESTRUCTURA")
            tipo = st.radio("Categoría:", ["SUPERVISOR", "SERVICIO"], horizontal=True)
            nuevo_nombre = st.text_input(f"Nombre del {tipo}:").upper()
            if st.button(f"PROCESAR ALTA"):
                if nuevo_nombre:
                    escribir_registro_nube("ESTRUCTURA", [obtener_hora_argentina(), tipo, nuevo_nombre, "ACTIVO", st.session_state.user_sel])
                    st.success("Alta Exitosa")
