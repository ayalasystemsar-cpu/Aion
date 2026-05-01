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

# --- 5. PANEL DE CONTROL Y ACCESO RESTRINGIDO ---
PERMISOS = {
    "SUPERVISOR": ["BRIAN AYALA", "DARÍO CECILIA", "LUIS BONGIORNO", "SANOJA LUIS", "MAZACOTTE CLAUDIO"],
    "MONITOREO": ["PORZIO GONZALO", "MAZACOTTE CLAUDIO", "LUIS BONGIORNO"],
    "JEFE DE OPERACIONES": ["LUIS BONGIORNO", "BRIAN AYALA"],
    "GERENCIA": ["BRIAN AYALA"],
    "ADMINISTRADOR": ["BRIAN AYALA"]
}

with st.sidebar:
    st.markdown('<div class="contenedor-logo-sidebar"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" class="logo-sidebar"></div>', unsafe_allow_html=True)
    st.subheader("🛡️ PANEL DE CONTROL")
    
    rol_elegido = st.selectbox("NIVEL DE ACCESO", list(PERMISOS.keys()))
    usuario_elegido = st.selectbox("IDENTIDAD OPERATIVA", ["BRIAN AYALA", "SANOJA LUIS", "MAZACOTTE CLAUDIO", "DARÍO CECILIA", "LUIS BONGIORNO", "PORZIO GONZALO"])
    
    if usuario_elegido in PERMISOS[rol_elegido]:
        st.session_state.rol_sel = rol_elegido
        st.session_state.user_sel = usuario_elegido
    else:
        st.error(f"ACCESO DENEGADO: {usuario_elegido} no es {rol_elegido}")
        st.stop()

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

# --- ROL: SUPERVISOR ---
if st.session_state.rol_sel == "SUPERVISOR":
    st.subheader(f"⚡ ESTACIÓN TÁCTICA: {st.session_state.user_sel}")
    apellido = st.session_state.user_sel.split()[-1].upper()
    df_zona = df_objetivos[df_objetivos['SUPERVISOR'].str.upper().str.contains(apellido, na=False)] if not df_objetivos.empty else pd.DataFrame()
    
    st.write("DESLICE PARA ACTIVAR S.O.S.")
    val_sos = st.slider("SOS", 0, 100, 0, label_visibility="collapsed")
    if val_sos == 100:
        escribir_registro_nube("ALERTAS", [obtener_hora_argentina(), st.session_state.user_sel, "PÁNICO", "PENDIENTE", f"LAT: {lat_act} | LON: {lon_act}"])
        st.error("🚨 S.O.S ENVIADO")

    if st.button("🔄 REFRESCAR SISTEMA", use_container_width=True): st.rerun()
    st.info(f"🛰️ TELEMETRÍA GPS ACTIVA\n\nLat: {lat_act}\n\nLon: {lon_act}")

    t_map, t_rep = st.tabs(["📍 RADAR GPS", "📝 REPORTE"])
    with t_map:
        st.markdown('<div class="radar-box">', unsafe_allow_html=True)
        m_sup = folium.Map(location=[lat_act, lon_act], zoom_start=13, tiles="CartoDB dark_matter")
        folium.Marker([lat_act, lon_act], popup="MÓVIL", icon=folium.Icon(color="red", icon="car", prefix="fa")).add_to(m_sup)
        for _, r in df_zona.iterrows():
            folium.Marker([r['LATITUD'], r['LONGITUD']], popup=r['OBJETIVO'], icon=folium.Icon(color="blue", icon="shield", prefix="fa")).add_to(m_sup)
        st_folium(m_sup, width="100%", height=450, key="map_supervisor")
        st.markdown('</div>', unsafe_allow_html=True)

# --- ROL: MONITOREO ---
elif st.session_state.rol_sel == "MONITOREO":
    st.subheader("🛰️ CENTRAL DE INTELIGENCIA OPERATIVA")
    df_alertas = leer_matriz_nube("ALERTAS")
    pendientes = df_alertas[df_alertas['ESTADO'].astype(str).str.upper() == 'PENDIENTE'] if not df_alertas.empty else pd.DataFrame()
    
    if not pendientes.empty:
        alerta = pendientes.iloc[-1]
        st.markdown(f'<div class="banner-emergencia">ALERTA ACTIVA: {alerta["USUARIO"]}</div>', unsafe_allow_html=True)
        st.markdown("### Informe de Neutralización")
        inf_texto = st.text_area("Resolución táctica:", placeholder="Escriba aquí...", label_visibility="collapsed")
        if st.button("CERRAR ALERTA", type="secondary", use_container_width=True):
            if inf_texto: st.success("Alerta neutralizada.")
            else: st.warning("Informe obligatorio.")
    else: st.success("✅ Vigilancia Pasiva")

# --- ROL: JEFE DE OPERACIONES ---
elif st.session_state.rol_sel == "JEFE DE OPERACIONES":
    st.subheader("📋 COMANDO DE OPERACIONES TÁCTICAS")
    df_actas = leer_matriz_nube("ACTAS_FLOTAS")
    t_inf, t_map = st.tabs(["📄 INFORMES", "🌍 MAPA"])
    with t_inf:
        if not df_actas.empty: st.dataframe(df_actas.tail(20), use_container_width=True)
    with t_map:
        st.markdown('<div class="radar-box">', unsafe_allow_html=True)
        if not df_objetivos.empty:
            m_ops = folium.Map(location=[df_objetivos['LATITUD'].mean(), df_objetivos['LONGITUD'].mean()], zoom_start=11, tiles="CartoDB dark_matter")
            st_folium(m_ops, width="100%", height=450, key="map_jefe")
        st.markdown('</div>', unsafe_allow_html=True)

# --- ROL: GERENCIA ---
elif st.session_state.rol_sel == "GERENCIA":
    st.header("📈 DASHBOARD ESTRATÉGICO")
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("⚠️ ALERTAS SOS")
        df_al = leer_matriz_nube("ALERTAS")
        if not df_al.empty: st.write(df_al['ESTADO'].value_counts())
    with col2:
        st.subheader("🏢 ESTRUCTURA AGENCIA")
        df_est = leer_matriz_nube("ESTRUCTURA")
        if not df_est.empty: st.dataframe(df_est, use_container_width=True)

# --- ROL: ADMINISTRADOR ---
elif st.session_state.rol_sel == "ADMINISTRADOR":
    st.header("⚙️ NÚCLEO MAESTRO")
    u_ing = st.text_input("ADMIN_USER")
    p_ing = st.text_input("ADMIN_PASS", type="password")
    if u_ing == "admin" and p_ing == "aion2026":
        st.success("Acceso Autorizado")
        tipo = st.radio("Alta de:", ["SUPERVISOR", "SERVICIO"], horizontal=True)
        nombre = st.text_input("Nombre:").upper()
        if st.button("PROCESAR ALTA"):
            escribir_registro_nube("ESTRUCTURA", [obtener_hora_argentina(), tipo, nombre, "ACTIVO", st.session_state.user_sel])
            st.success("Alta exitosa.")
