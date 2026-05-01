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

# --- 3. FUNCIONES DE LÓGICA Y DATOS ---
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

# --- 4. DISEÑO E IDENTIDAD VISUAL ---
def aplicar_identidad_alfa():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@300;500;700&display=swap');
        .stApp { background: radial-gradient(circle at top, #0A0F1E 0%, #030305 100%) !important; color: #E0E0E0; font-family: 'Rajdhani', sans-serif; }
        [data-testid="stSidebar"] { background-color: #050507 !important; border-right: 1px solid rgba(0, 229, 255, 0.3) !important; }
        .contenedor-logo-sidebar { display: flex; justify-content: center; align-items: center; padding: 10px; margin-bottom: 20px; }
        .logo-sidebar { width: 180px !important; filter: drop-shadow(0 0 10px rgba(0, 229, 255, 0.4)); border: 1.5px solid #00e5ff; border-radius: 4px; background: #000; }
        .contenedor-logo-central { display: flex; justify-content: center; align-items: center; width: 100%; margin-top: -10px; margin-bottom: 20px; }
        .logo-phoenix { width: 520px !important; border: 2px solid #00e5ff !important; box-shadow: 0 0 35px rgba(0, 229, 255, 0.5) !important; border-radius: 4px !important; background-color: #000 !important; }
        .panico-container { display: flex !important; justify-content: center !important; align-items: center !important; width: 100% !important; margin: 20px 0 !important; }
        .stButton > button[kind="primary"] { 
            background: radial-gradient(circle, #FF0000 0%, #8B0000 100%) !important; 
            color: white !important; border-radius: 50% !important; width: 105px !important; height: 105px !important; 
            border: 3px solid #333 !important; box-shadow: 0 0 25px rgba(255, 0, 0, 0.5) !important; 
            font-family: 'Orbitron', sans-serif; font-size: 11px !important; font-weight: bold; line-height: 1.1; text-transform: uppercase;
        }
        .radar-box { border: 1px solid #1A1A1B; border-radius: 12px; padding: 10px; background: rgba(10, 10, 11, 0.9); }
        .estacion-titulo { font-family: 'Orbitron', sans-serif; color: #00E5FF !important; font-size: 24px; margin-top: 15px; display: flex; align-items: center; justify-content: center; gap: 12px; }
        h1, h2, h3, .stSubheader { font-family: 'Orbitron', sans-serif; color: #00E5FF !important; text-shadow: 0 0 15px rgba(0, 229, 255, 0.4); }
        </style>
        """, unsafe_allow_html=True
    )

aplicar_identidad_alfa()

# --- 5. SIDEBAR TÁCTICO ---
df_objetivos = cargar_objetivos()

if 'rol_sel' not in st.session_state: st.session_state.rol_sel = "MONITOREO"
if 'user_sel' not in st.session_state: st.session_state.user_sel = "BRIAN AYALA"

with st.sidebar:
    st.markdown('<div class="contenedor-logo-sidebar"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" class="logo-sidebar"></div>', unsafe_allow_html=True)
    st.subheader("🛡️ PANEL DE CONTROL")
    st.session_state.rol_sel = st.selectbox("NIVEL DE ACCESO", ["SUPERVISOR", "MONITOREO", "JEFE DE OPERACIONES", "ADMINISTRADOR"])
    st.session_state.user_sel = st.selectbox("IDENTIDAD OPERATIVA", ["BRIAN AYALA", "SANOJA LUIS P.", "DARÍO CECILIA", "LUIS BONGIORNO", "SERANTES WALTER", "MAZACOTTE CLAUDIO"])
    
    st.write("---")
    st.markdown("**🚨 CONFIGURACIÓN DE EMERGENCIA**")
    obj_panico = st.selectbox("🎯 SELECCIONAR OBJETIVO", df_objetivos['OBJETIVO'].unique() if not df_objetivos.empty else ["N/A"])
    sup_panico = st.selectbox("👤 SUPERVISOR DE ZONA", ["BRIAN AYALA", "GONZALO PORZIO", "EDGAR VERA", "OTRO"])
    
    loc = get_geolocation()
    lat_act = loc['coords']['latitude'] if loc else 0.0
    lon_act = loc['coords'].get('longitude', 0.0) if loc else 0.0

    st.markdown('<div class="panico-container">', unsafe_allow_html=True)
    if st.button("ACTIVAR\nPÁNICO", type="primary"):
        carga_sos = f"LAT:{lat_act}|LON:{lon_act}|OBJ:{obj_panico}|SUP:{sup_panico}"
        escribir_registro_nube("ALERTAS", [obtener_hora_argentina(), st.session_state.user_sel, "PÁNICO", "PENDIENTE", carga_sos])
        st.error(f"🚨 S.O.S ENVIADO: {obj_panico}")
    st.markdown('</div>', unsafe_allow_html=True)

# --- 6. LOGO CENTRAL ---
st.markdown('<div class="contenedor-logo-central"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" class="logo-phoenix"></div>', unsafe_allow_html=True)

# --- 7. FLUJO POR ROLES ---

# A. ROL: SUPERVISOR (MAPA RESTAURADO)
if st.session_state.rol_sel == "SUPERVISOR":
    st.markdown(f'<div class="estacion-titulo">📱 Estación de Control: {st.session_state.user_sel}</div>', unsafe_allow_html=True)
    st.markdown(f'<div style="text-align:center; color:#00E5FF; font-weight:bold;">Servicio Actual: {obj_panico}</div>', unsafe_allow_html=True)
    
    t1, t2 = st.tabs(["📍 RADAR GPS", "📝 REPORTE"])
    with t1:
        st.markdown('<div class="radar-box">', unsafe_allow_html=True)
        m_sup = folium.Map(location=[lat_act if lat_act != 0 else -34.6, lon_act if lon_act != 0 else -58.4], zoom_start=12, tiles="CartoDB dark_matter")
        for _, r in df_objetivos.iterrows():
            folium.Marker(
                [r['LATITUD'], r['LONGITUD']], 
                tooltip=f"OBJETIVO: {r['OBJETIVO']}", 
                icon=folium.Icon(color="blue", icon="shield", prefix="fa")
            ).add_to(m_sup)
        if lat_act != 0:
            folium.Marker([lat_act, lon_act], icon=folium.Icon(color="red", icon="user", prefix="fa")).add_to(m_sup)
        st_folium(m_sup, width="100%", height=400, key="map_supervisor")
        st.markdown('</div>', unsafe_allow_html=True)

# B. ROL: MONITOREO (MAPA + CIERRE + LÓGICA DE COLOR)
elif st.session_state.rol_sel == "MONITOREO":
    st.header("🛰️ CENTRAL DE INTELIGENCIA OPERATIVA")
    df_emergencias = leer_matriz_nube("ALERTAS")
    sos_activos = len(df_emergencias[df_emergencias['ESTADO'].astype(str).str.upper() == 'PENDIENTE']) if not df_emergencias.empty else 0
    
    m1, m2, m3 = st.columns(3)
    m1.metric("🚨 S.O.S ACTIVOS", sos_activos)
    m2.metric("📡 RED", "OPERATIVA")
    m3.metric("🕒 HORA LOCAL", obtener_hora_argentina().split(" ")[1])

    t_radar, t_gestion = st.tabs(["🚨 RADAR S.O.S", "📖 LIBRO DE BASE"])
    with t_radar:
        lat_mapa, lon_mapa = -34.6, -58.4
        obj_en_panico = ""
        
        if sos_activos > 0:
            datos_sos = df_emergencias[df_emergencias['ESTADO'].astype(str).str.upper() == 'PENDIENTE'].iloc[-1]
            try:
                partes = datos_sos.get('CARGA_UTIL', '').split("|")
                lat_mapa = float(partes[0].split(":")[1])
                lon_mapa = float(partes[1].split(":")[1])
                obj_en_panico = partes[2].split(":")[1]
                sup_reportado = partes[3].split(":")[1]
                st.error(f"🚨 EMERGENCIA: {datos_sos['USUARIO']} | 🎯 {obj_en_panico} | 👤 SUP: {sup_reportado}")
            except: pass
        else:
            st.success("✅ Vigilancia Pasiva - Radar Operativo")

        st.markdown('<div class="radar-box">', unsafe_allow_html=True)
        m_mon = folium.Map(location=[lat_mapa, lon_mapa], zoom_start=13, tiles="CartoDB dark_matter")
        
        for _, r in df_objetivos.iterrows():
            # CAMBIO DE COLOR DINÁMICO: Si es el objetivo reportado, se pone rojo
            color_final = "red" if r['OBJETIVO'] == obj_en_panico else "blue"
            
            folium.Marker(
                [r['LATITUD'], r['LONGITUD']], 
                tooltip=f"OBJETIVO: {r['OBJETIVO']} | SUPERVISOR: {r.get('SUPERVISOR', 'N/A')}", 
                icon=folium.Icon(color=color_final, icon="shield", prefix="fa")
            ).add_to(m_mon)
        
        if sos_activos > 0:
            html_pulse = """<div style="position: relative;"><div style="position: absolute; width: 25px; height: 25px; background: red; border-radius: 50%; animation: pulse 1.2s infinite;"></div></div><style>@keyframes pulse { 0% { transform: scale(1); opacity: 1; } 100% { transform: scale(3.5); opacity: 0; } }</style>"""
            folium.Marker([lat_mapa, lon_mapa], icon=folium.DivIcon(html=html_pulse)).add_to(m_mon)

        st_folium(m_mon, width="100%", height=450, key="map_monitoreo_full")
        st.markdown('</div>', unsafe_allow_html=True)

        # PROTOCOLO DE CIERRE (RESTAURADO)
        if sos_activos > 0:
            st.subheader("📝 PROTOCOLO DE CIERRE")
            inf_neu = st.text_area("INFORME DE NEUTRALIZACIÓN", placeholder="Escriba el detalle aquí...")
            if st.button("FINALIZAR OPERATIVO", use_container_width=True):
                if inf_neu.strip():
                    fila_idx = df_emergencias[df_emergencias['ESTADO'].astype(str).str.upper() == 'PENDIENTE'].index[-1] + 2
                    actualizar_celda("ALERTAS", fila_idx, "D", "RESUELTO")
                    actualizar_celda("ALERTAS", fila_idx, "F", inf_neu)
                    st.success("Operativo Finalizado.")
                    st.rerun()
                else:
                    st.warning("Debe completar el informe.")

# C. ROL: ADMINISTRADOR
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
