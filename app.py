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

# --- 3. FUNCIONES DE LÓGICA Y DATOS ---
def obtener_hora_argentina():
    tz = pytz.timezone("America/Argentina/Buenos_Aires")
    return datetime.now(tz).strftime("%H:%M:%S")

def escribir_registro_nube(pestana, datos_fila):
    try:
        gc = conectar_google()
        if gc:
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
            hoja.append_row(datos_fila)
            return True
    except: return False

@st.cache_data(ttl=10)
def leer_matriz_nube(pestana):
    gc = conectar_google()
    if gc:
        try:
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
            return pd.DataFrame(hoja.get_all_records())
        except: return pd.DataFrame()
    return pd.DataFrame()

def cargar_objetivos():
    df = leer_matriz_nube("OBJETIVOS")
    if not df.empty:
        df.columns = df.columns.str.strip().str.upper()
        # Limpieza de coordenadas para asegurar que sean numéricas
        df['LATITUD'] = pd.to_numeric(df['LATITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        df['LONGITUD'] = pd.to_numeric(df['LONGITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        return df.dropna(subset=['LATITUD', 'LONGITUD'])
    return pd.DataFrame()

# --- 4. DISEÑO E IDENTIDAD VISUAL (ESTILO OLED CIAN) ---
def aplicar_identidad_alfa():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@300;500;700&display=swap');
        .stApp { background: radial-gradient(circle at top, #0A0F1E 0%, #030305 100%) !important; color: #E0E0E0; font-family: 'Rajdhani', sans-serif; }
        [data-testid="stSidebar"] { background-color: #050507 !important; border-right: 1px solid rgba(0, 229, 255, 0.3) !important; }
        .contenedor-logo-sidebar { display: flex; justify-content: center; margin-bottom: 20px; padding: 10px; border: 1px solid #00e5ff; border-radius: 4px; background: #000; }
        .logo-sidebar { width: 100% !important; filter: drop-shadow(0 0 5px rgba(0, 229, 255, 0.4)); }
        .contenedor-logo-central { display: flex; justify-content: center; margin-top: 10px; margin-bottom: 30px; }
        .logo-phoenix { width: 500px !important; border: 2px solid #00e5ff !important; box-shadow: 0 0 30px rgba(0, 229, 255, 0.4) !important; border-radius: 4px; background-color: #000; padding: 5px; }
        .stButton > button[kind="primary"] { 
            background: radial-gradient(circle, #FF0000 0%, #8B0000 100%) !important; 
            color: white !important; border-radius: 50% !important; width: 110px !important; height: 110px !important; 
            border: 2px solid #333 !important; box-shadow: 0 0 20px rgba(255, 0, 0, 0.5) !important; 
            font-family: 'Orbitron', sans-serif; font-size: 12px !important; font-weight: bold;
        }
        .stButton > button[kind="secondary"] {
            background: #121212 !important; color: #00E5FF !important; border: 1px solid #00E5FF !important;
            border-radius: 4px !important; width: 100% !important; height: 35px !important; font-family: 'Orbitron', sans-serif;
        }
        .banner-emergencia { background: #FF0000; color: white; padding: 15px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 10px; border: 2px solid #FFF; }
        h1, h2, h3, .stSubheader { font-family: 'Orbitron', sans-serif; color: #00E5FF !important; text-shadow: 0 0 10px rgba(0, 229, 255, 0.4); }
        .stTextArea textarea { background-color: #121212 !important; color: #E0E0E0 !important; border: 1px solid #FF0000 !important; }
        </style>
        """, unsafe_allow_html=True
    )

aplicar_identidad_alfa()

# --- 5. PANEL DE CONTROL Y CONFIGURACIÓN DE ACCESO ---
# Se mantiene la lista de usuarios para identificación, pero se libera la vista en secciones clave
USUARIOS_SISTEMA = ["BRIAN AYALA", "SANOJA LUIS", "MAZACOTTE CLAUDIO", "DARÍO CECILIA", "LUIS BONGIORNO", "PORZIO GONZALO"]

with st.sidebar:
    st.markdown('<div class="contenedor-logo-sidebar"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" class="logo-sidebar"></div>', unsafe_allow_html=True)
    st.subheader("🛡️ PANEL DE CONTROL")
    
    st.session_state.rol_sel = st.selectbox("NIVEL DE ACCESO", ["MONITOREO", "SUPERVISOR", "JEFE DE OPERACIONES", "GERENCIA", "ADMINISTRADOR"])
    st.session_state.user_sel = st.selectbox("IDENTIDAD OPERATIVA", USUARIOS_SISTEMA)

    loc = get_geolocation()
    lat_act, lon_act = (loc['coords']['latitude'], loc['coords']['longitude']) if loc and 'coords' in loc else (-34.6037, -58.3816)

    st.markdown('<div style="display:flex; justify-content:center; margin-top:40px;">', unsafe_allow_html=True)
    if st.button("ACTIVAR\nPÁNICO", type="primary"):
        escribir_registro_nube("ALERTAS", [obtener_hora_argentina(), st.session_state.user_sel, "PÁNICO", "PENDIENTE", f"LAT: {lat_act} | LON: {lon_act}"])
        st.error("🚨 S.O.S ENVIADO")
    st.markdown('</div>', unsafe_allow_html=True)

# --- 6. FLUJO CENTRAL ---
st.markdown('<div class="contenedor-logo-central"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" class="logo-phoenix"></div>', unsafe_allow_html=True)
df_objetivos = cargar_objetivos()

# --- SECCIÓN: MONITOREO (ACCESO LIBERADO) ---
if st.session_state.rol_sel == "MONITOREO":
    st.subheader("🛰️ CENTRAL DE INTELIGENCIA OPERATIVA")
    df_alertas = leer_matriz_nube("ALERTAS")
    pendientes = df_alertas[df_alertas['ESTADO'].astype(str).str.upper() == 'PENDIENTE'] if not df_alertas.empty else pd.DataFrame()
    
    m1, m2, m3 = st.columns(3)
    m1.metric("🚨 S.O.S ACTIVOS", len(pendientes))
    m2.metric("📡 ESTADO DE RED", "OPERATIVO")
    m3.metric("🕒 HORA LOCAL", obtener_hora_argentina())

    tab_radar, tab_base = st.tabs(["🚨 RADAR S.O.S", "📖 MAPA DE OBJETIVOS"])
    
    with tab_radar:
        if not pendientes.empty:
            alerta = pendientes.iloc[-1]
            st.markdown(f'<div class="banner-emergencia">ALERTA ACTIVA: {alerta["USUARIO"]}</div>', unsafe_allow_html=True)
            # Mapa de monitoreo con objetivos visibles
            m_mon = folium.Map(location=[lat_act, lon_act], zoom_start=12, tiles="CartoDB dark_matter")
            for _, r in df_objetivos.iterrows():
                folium.Marker([r['LATITUD'], r['LONGITUD']], popup=r['OBJETIVO'], icon=folium.Icon(color="blue", icon="shield", prefix="fa")).add_to(m_mon)
            st_folium(m_mon, width="100%", height=450, key="mapa_monitoreo_sos")
        else:
            st.success("✅ Vigilancia Pasiva - Sin Emergencias")

    with tab_base:
        if not df_objetivos.empty:
            m_base = folium.Map(location=[df_objetivos['LATITUD'].mean(), df_objetivos['LONGITUD'].mean()], zoom_start=11, tiles="CartoDB dark_matter")
            for _, r in df_objetivos.iterrows():
                folium.Marker([r['LATITUD'], r['LONGITUD']], popup=r['OBJETIVO'], icon=folium.Icon(color="blue", icon="shield", prefix="fa")).add_to(m_base)
            st_folium(m_base, width="100%", height=500, key="mapa_monitoreo_base")

# --- SECCIÓN: SUPERVISOR ---
elif st.session_state.rol_sel == "SUPERVISOR":
    st.subheader(f"⚡ ESTACIÓN TÁCTICA: {st.session_state.user_sel}")
    
    # Filtro para mostrar objetivos asignados a este supervisor (basado en apellido)
    apellido = st.session_state.user_sel.split()[-1].upper()
    df_zona = df_objetivos[df_objetivos['SUPERVISOR'].str.upper().str.contains(apellido, na=False)] if not df_objetivos.empty else pd.DataFrame()
    
    st.info(f"🛰️ TELEMETRÍA GPS ACTIVA | Lat: {lat_act} | Lon: {lon_act}")

    t_map, t_rep = st.tabs(["📍 RADAR GPS", "📝 REPORTE"])
    with t_map:
        st.markdown('<div class="radar-box">', unsafe_allow_html=True)
        m_sup = folium.Map(location=[lat_act, lon_act], zoom_start=13, tiles="CartoDB dark_matter")
        # Marcador de posición actual
        folium.Marker([lat_act, lon_act], popup="MI POSICIÓN", icon=folium.Icon(color="red", icon="car", prefix="fa")).add_to(m_sup)
        # Mostrar todos los objetivos de su zona en el mapa
        for _, r in df_zona.iterrows():
            folium.Marker([r['LATITUD'], r['LONGITUD']], popup=r['OBJETIVO'], icon=folium.Icon(color="blue", icon="shield", prefix="fa")).add_to(m_sup)
        st_folium(m_sup, width="100%", height=450, key="map_supervisor")
        st.markdown('</div>', unsafe_allow_html=True)

# --- SECCIÓN: JEFE DE OPERACIONES (ACCESO LIBERADO) ---
elif st.session_state.rol_sel == "JEFE DE OPERACIONES":
    st.subheader("📋 COMANDO DE OPERACIONES TÁCTICAS")
    df_actas = leer_matriz_nube("ACTAS_FLOTAS")
    
    t_inf, t_map = st.tabs(["📄 INFORMES DE FLOTA", "🌍 MAPA ESTRATÉGICO"])
    with t_inf:
        if not df_actas.empty: st.dataframe(df_actas.tail(20), use_container_width=True)
        else: st.info("No hay informes registrados.")
        
    with t_map:
        st.markdown('<div class="radar-box">', unsafe_allow_html=True)
        if not df_objetivos.empty:
            m_ops = folium.Map(location=[df_objetivos['LATITUD'].mean(), df_objetivos['LONGITUD'].mean()], zoom_start=11, tiles="CartoDB dark_matter")
            # En esta vista se ven todos los objetivos del sistema
            for _, r in df_objetivos.iterrows():
                folium.Marker([r['LATITUD'], r['LONGITUD']], popup=f"OBJETIVO: {r['OBJETIVO']}", icon=folium.Icon(color="blue", icon="shield", prefix="fa")).add_to(m_ops)
            st_folium(m_ops, width="100%", height=500, key="map_jefe_ops")
        st.markdown('</div>', unsafe_allow_html=True)

# --- SECCIÓN: GERENCIA / ADMINISTRADOR ---
elif st.session_state.rol_sel in ["GERENCIA", "ADMINISTRADOR"]:
    if st.session_state.rol_sel == "GERENCIA":
        st.header("📈 DASHBOARD ESTRATÉGICO")
        df_al = leer_matriz_nube("ALERTAS")
        if not df_al.empty: st.write("Resumen de Estados:", df_al['ESTADO'].value_counts())
        st.dataframe(leer_matriz_nube("ESTRUCTURA"), use_container_width=True)
    else:
        st.header("⚙️ NÚCLEO MAESTRO")
        u_ing = st.text_input("ADMIN_USER")
        p_ing = st.text_input("ADMIN_PASS", type="password")
        if u_ing == "admin" and p_ing == "aion2026":
            st.success("Acceso Autorizado")
            # Lógica de administración...
