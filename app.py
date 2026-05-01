# --- 1. CONFIGURACIÓN E IDENTIDAD VISUAL CORPORATIVA (AION-YAROKU CORE) ---
import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
from folium.plugins import AntPath
from datetime import datetime
import pytz
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from streamlit_js_eval import get_geolocation

# Configuración de página OLED
st.set_page_config(
    page_title="AION-YAROKU | CORE",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CONEXIONES (GOOGLE MATRIZ) ---
ID_MAESTRO_DB = "1Md0VkOnwUJWldq0S1fB9UrmOKv4MG__JVG3tQsda0Uw"

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

# --- 4. DISEÑO E IDENTIDAD VISUAL ---
def aplicar_identidad_alfa():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@300;500;700&display=swap');
        .stApp { background: radial-gradient(circle at top, #0A0F1E 0%, #030305 100%) !important; color: #E0E0E0; font-family: 'Rajdhani', sans-serif; }
        [data-testid="stSidebar"] { background-color: #050507 !important; border-right: 1px solid rgba(0, 229, 255, 0.3) !important; }
        .contenedor-logo-sidebar { display: flex; justify-content: center; align-items: center; width: 100%; margin-bottom: 20px; padding: 10px; border: 1px solid #00e5ff; border-radius: 4px; background: #000; }
        .logo-sidebar { width: 100% !important; filter: drop-shadow(0 0 5px rgba(0, 229, 255, 0.4)); }
        .contenedor-logo-central { display: flex; justify-content: center; align-items: center; width: 100%; margin-top: 10px; margin-bottom: 30px; }
        .logo-phoenix { width: 500px !important; border: 2px solid #00e5ff !important; box-shadow: 0 0 30px rgba(0, 229, 255, 0.4) !important; border-radius: 4px !important; background-color: #000 !important; padding: 5px; }
        .panico-container { display: flex !important; justify-content: center !important; align-items: center !important; width: 100% !important; margin-top: 40px !important; }
        .stButton > button[kind="primary"] { 
            background: radial-gradient(circle, #FF0000 0%, #8B0000 100%) !important; 
            color: white !important; border-radius: 50% !important; width: 110px !important; height: 110px !important; 
            border: 2px solid #333 !important; box-shadow: 0 0 20px rgba(255, 0, 0, 0.5) !important; 
            font-family: 'Orbitron', sans-serif; font-size: 12px !important; font-weight: bold; line-height: 1.1; text-transform: uppercase; 
        }
        .radar-box { border: 1px solid #1A1A1B; border-radius: 12px; padding: 15px; background: rgba(10, 10, 11, 0.8); }
        h1, h2, h3, .stSubheader { font-family: 'Orbitron', sans-serif; color: #00E5FF !important; text-shadow: 0 0 10px rgba(0, 229, 255, 0.4); }
        </style>
        """, unsafe_allow_html=True
    )

aplicar_identidad_alfa()

# --- 5. SIDEBAR Y SEGURIDAD GPS ---
if 'rol_sel' not in st.session_state: st.session_state.rol_sel = "MONITOREO"
if 'user_sel' not in st.session_state: st.session_state.user_sel = "BRIAN AYALA"

with st.sidebar:
    st.markdown('<div class="contenedor-logo-sidebar"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" class="logo-sidebar"></div>', unsafe_allow_html=True)
    st.subheader("🛡️ PANEL DE CONTROL")
    perfiles = ["SUPERVISOR", "MONITOREO", "JEFE DE OPERACIONES", "GERENCIA", "ADMINISTRADOR"]
    st.session_state.rol_sel = st.selectbox("NIVEL DE ACCESO", perfiles)
    lista_sups = ["BRIAN AYALA", "DARÍO CECILIA", "LUIS BONGIORNO", "SERANTES WALTER", "SANOJA LUIS", "MAZACOTTE CLAUDIO"]
    st.session_state.user_sel = st.selectbox("IDENTIDAD OPERATIVA", lista_sups)
    
    loc = get_geolocation()
    if loc and 'coords' in loc:
        lat_act = loc['coords'].get('latitude', 0.0)
        lon_act = loc['coords'].get('longitude', 0.0)
    else:
        lat_act, lon_act = -34.6037, -58.3816 

    st.markdown('<div class="panico-container">', unsafe_allow_html=True)
    if st.button("ACTIVAR\nPÁNICO", type="primary"):
        carga_sos = f"LAT: {lat_act} | LON: {lon_act}"
        escribir_registro_nube("ALERTAS", [obtener_hora_argentina(), st.session_state.user_sel, "PÁNICO", "PENDIENTE", carga_sos])
    st.markdown('</div>', unsafe_allow_html=True)

# --- 6. FLUJO CENTRAL ---
st.markdown('<div class="contenedor-logo-central"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" class="logo-phoenix"></div>', unsafe_allow_html=True)
df_objetivos = cargar_objetivos()

# --- A. ROL: SUPERVISOR ---
if st.session_state.rol_sel == "SUPERVISOR":
    st.subheader(f"⚡ ESTACIÓN TÁCTICA: {st.session_state.user_sel}")
    apellido = st.session_state.user_sel.split()[-1].upper()
    df_zona = df_objetivos[df_objetivos['SUPERVISOR'].str.upper().str.contains(apellido, na=False)] if not df_objetivos.empty else pd.DataFrame()
    if df_zona.empty: df_zona = df_objetivos
    t1, t2 = st.tabs(["📍 RADAR GPS", "📝 REPORTE"])
    with t1:
        st.markdown('<div class="radar-box">', unsafe_allow_html=True)
        m = folium.Map(location=[df_zona['LATITUD'].mean(), df_zona['LONGITUD'].mean()], zoom_start=12, tiles="CartoDB dark_matter")
        for _, r in df_zona.iterrows():
            folium.Marker([r['LATITUD'], r['LONGITUD']], popup=r['OBJETIVO'], icon=folium.Icon(color="blue", icon="shield", prefix="fa")).add_to(m)
        st_folium(m, width="100%", height=400, key="mapa_supervisor")
        st.markdown('</div>', unsafe_allow_html=True)

# --- B. ROL: MONITOREO ---
elif st.session_state.rol_sel == "MONITOREO":
    st.header("🛰️ CENTRAL DE INTELIGENCIA")
    st.success("✅ Sistema en Vigilancia Pasiva")
    st.markdown('<div class="radar-box">', unsafe_allow_html=True)
    if not df_objetivos.empty:
        m_pass = folium.Map(location=[df_objetivos['LATITUD'].mean(), df_objetivos['LONGITUD'].mean()], zoom_start=12, tiles="CartoDB dark_matter")
        for _, r in df_objetivos.iterrows():
            folium.CircleMarker(location=[r['LATITUD'], r['LONGITUD']], radius=5, color="#00E5FF", fill=True).add_to(m_pass)
        st_folium(m_pass, width="100%", height=450, key="mapa_mon_pasivo")
    st.markdown('</div>', unsafe_allow_html=True)

# --- C. ROL: JEFE DE OPERACIONES ---
elif st.session_state.rol_sel == "JEFE DE OPERACIONES":
    st.subheader("📋 COMANDO DE OPERACIONES")
    df_actas = leer_matriz_nube("ACTAS_FLOTAS")
    t_inf, t_mapa = st.tabs(["📄 INFORMES", "🌍 MAPA"])
    with t_inf:
        if not df_actas.empty: st.dataframe(df_actas.tail(20), use_container_width=True)
    with t_mapa:
        st.markdown('<div class="radar-box">', unsafe_allow_html=True)
        if not df_objetivos.empty:
            m_ops = folium.Map(location=[df_objetivos['LATITUD'].mean(), df_objetivos['LONGITUD'].mean()], zoom_start=11, tiles="CartoDB dark_matter")
            for _, r in df_objetivos.iterrows():
                folium.Marker(location=[r['LATITUD'], r['LONGITUD']], icon=folium.Icon(color="blue", icon="shield", prefix="fa")).add_to(m_ops)
            st_folium(m_ops, width="100%", height=450, key="mapa_jefe_iconos")
        st.markdown('</div>', unsafe_allow_html=True)

# --- D. ROL: GERENCIA (MÓDULO DE ANÁLISIS ESTRATÉGICO)[cite: 1] ---
elif st.session_state.rol_sel == "GERENCIA":
    st.header("📈 DASHBOARD ESTRATÉGICO")
    col_g1, col_g2 = st.columns([1, 2])
    
    with col_g1:
        st.subheader("⚠️ ALERTAS SOS")
        df_al = leer_matriz_nube("ALERTAS")
        if not df_al.empty:
            # Conteo de estados de alertas para toma de decisiones[cite: 1]
            st.write(df_al['ESTADO'].value_counts())
        else:
            st.info("Sin registros de alertas.")
            
    with col_g2:
        st.subheader("🏢 ESTRUCTURA AGENCIA")
        df_est = leer_matriz_nube("ESTRUCTURA")
        if not df_est.empty:
            # Visualización de la estructura operativa actual[cite: 1]
            st.dataframe(df_est, use_container_width=True)
        else:
            st.info("Estructura no definida.")

# --- E. ROL: ADMINISTRADOR ---
elif st.session_state.rol_sel == "ADMINISTRADOR":
    st.header("⚙️ NÚCLEO MAESTRO")
    u_ing = st.text_input("ADMIN_USER")
    p_ing = st.text_input("ADMIN_PASS", type="password")
    if u_ing == "admin" and p_ing == "aion2026":
        tipo = st.radio("Categoría:", ["SUPERVISOR", "SERVICIO"], horizontal=True)
        nuevo_nombre = st.text_input(f"Nombre del {tipo}:").upper()
        if st.button("PROCESAR ALTA"):
            escribir_registro_nube("ESTRUCTURA", [obtener_hora_argentina(), tipo, nuevo_nombre, "ACTIVO", st.session_state.user_sel])
            st.success("Alta Exitosa")
