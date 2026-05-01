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

# --- 4. DISEÑO E IDENTIDAD VISUAL (ESTILO OLED CÁLIDO) ---
def aplicar_identidad_alfa():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@300;500;700&display=swap');
        
        .stApp { background: radial-gradient(circle at top, #0A0A0A 0%, #030303 100%) !important; color: #E0E0E0; font-family: 'Rajdhani', sans-serif; }
        [data-testid="stSidebar"] { background-color: #050505 !important; border-right: 1px solid rgba(212, 175, 55, 0.2) !important; }
        
        /* Botón de Pánico (Rojo táctico suave) */
        .stButton > button[kind="primary"] { 
            background: radial-gradient(circle, #B22222 0%, #4B0000 100%) !important; 
            color: white !important; border-radius: 50% !important; width: 110px !important; height: 110px !important; 
            border: 1px solid #333 !important; box-shadow: 0 0 15px rgba(178, 34, 34, 0.4) !important; 
            font-family: 'Orbitron', sans-serif; font-size: 11px !important; font-weight: bold;
        }
        
        /* BOTÓN RECTANGULAR FINO (Color Cálido Ámbar/Dorado Suave) */
        .stButton > button[kind="secondary"] {
            background-color: transparent !important;
            color: #D4AF37 !important;
            border: 1px solid rgba(212, 175, 55, 0.5) !important;
            border-radius: 2px !important;
            width: 100% !important;
            height: 32px !important;
            font-family: 'Rajdhani', sans-serif;
            font-weight: 500;
            font-size: 13px !important;
            text-transform: uppercase;
            letter-spacing: 2px;
            transition: 0.3s;
        }
        .stButton > button[kind="secondary"]:hover {
            background-color: rgba(212, 175, 55, 0.1) !important;
            border-color: #D4AF37 !important;
            box-shadow: 0 0 10px rgba(212, 175, 55, 0.2);
        }

        .radar-box { border: 1px solid #1A1A1A; border-radius: 4px; padding: 15px; background: rgba(5, 5, 5, 0.9); }
        h1, h2, h3, .stSubheader { font-family: 'Orbitron', sans-serif; color: #D4AF37 !important; font-weight: 400; }
        
        /* Input de Informe táctico */
        .stTextArea textarea { 
            background-color: #0A0A0A !important; 
            color: #D4AF37 !important; 
            border: 1px solid rgba(212, 175, 55, 0.3) !important; 
            border-radius: 2px;
        }
        </style>
        """, unsafe_allow_html=True
    )

aplicar_identidad_alfa()

# --- 5. PANEL DE CONTROL ---
USUARIOS = ["BRIAN AYALA", "SANOJA LUIS", "MAZACOTTE CLAUDIO", "DARÍO CECILIA", "LUIS BONGIORNO", "PORZIO GONZALO"]

with st.sidebar:
    st.markdown('<div class="contenedor-logo-sidebar"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" style="width:100%"></div>', unsafe_allow_html=True)
    st.subheader("🛡️ PANEL DE CONTROL")
    st.session_state.rol_sel = st.selectbox("NIVEL DE ACCESO", ["MONITOREO", "SUPERVISOR", "JEFE DE OPERACIONES", "GERENCIA", "ADMINISTRADOR"])
    st.session_state.user_sel = st.selectbox("IDENTIDAD OPERATIVA", USUARIOS)

    loc = get_geolocation()
    lat_act, lon_act = (loc['coords']['latitude'], loc['coords']['longitude']) if loc and 'coords' in loc else (-34.6037, -58.3816)

    st.markdown('<div style="display:flex; justify-content:center; margin-top:40px;">', unsafe_allow_html=True)
    if st.button("ACTIVAR\nPÁNICO", type="primary"):
        escribir_registro_nube("ALERTAS", [obtener_hora_argentina(), st.session_state.user_sel, "PÁNICO", "PENDIENTE", f"LAT: {lat_act} | LON: {lon_act}"])
        st.toast("🚨 S.O.S ENVIADO", icon="⚠️")
    st.markdown('</div>', unsafe_allow_html=True)

# --- 6. FLUJO CENTRAL ---
df_objetivos = cargar_objetivos()
st.markdown('<div class="contenedor-logo-central"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" style="width:400px; opacity:0.8"></div>', unsafe_allow_html=True)

# --- ROL: MONITOREO ---
if st.session_state.rol_sel == "MONITOREO":
    st.subheader("🛰️ CENTRAL DE INTELIGENCIA OPERATIVA")
    df_alertas = leer_matriz_nube("ALERTAS")
    pendientes = df_alertas[df_alertas['ESTADO'].astype(str).str.upper() == 'PENDIENTE'] if not df_alertas.empty else pd.DataFrame()
    
    if not pendientes.empty:
        alerta = pendientes.iloc[-1]
        st.warning(f"ALERTA ACTIVA: {alerta['USUARIO']}")
        
        st.markdown("### Informe de Neutralización")
        inf_texto = st.text_area("Resolución:", placeholder="Escriba aquí...", label_visibility="collapsed")
        
        if st.button("CERRAR ALERTA", type="secondary"):
            if inf_texto: st.success("Alerta procesada.")
            else: st.error("Falta informe.")
    else: st.success("✅ Vigilancia Pasiva")

# --- ROL: SUPERVISOR ---
elif st.session_state.rol_sel == "SUPERVISOR":
    st.subheader(f"⚡ ESTACIÓN TÁCTICA: {st.session_state.user_sel}")
    apellido = st.session_state.user_sel.split()[-1].upper()
    df_zona = df_objetivos[df_objetivos['SUPERVISOR'].str.upper().str.contains(apellido, na=False)] if not df_objetivos.empty else pd.DataFrame()
    
    t_map, t_rep = st.tabs(["📍 RADAR GPS", "📝 REPORTE"])
    with t_map:
        st.markdown('<div class="radar-box">', unsafe_allow_html=True)
        m_sup = folium.Map(location=[lat_act, lon_act], zoom_start=13, tiles="CartoDB dark_matter")
        folium.Marker([lat_act, lon_act], popup="MI POSICIÓN", icon=folium.Icon(color="red", icon="car", prefix="fa")).add_to(m_sup)
        for _, r in df_zona.iterrows():
            folium.Marker([r['LATITUD'], r['LONGITUD']], popup=r['OBJETIVO'], icon=folium.Icon(color="blue", icon="shield", prefix="fa")).add_to(m_sup)
        st_folium(m_sup, width="100%", height=450, key="map_sup")
        st.markdown('</div>', unsafe_allow_html=True)

# --- ROL: JEFE DE OPERACIONES ---
elif st.session_state.rol_sel == "JEFE DE OPERACIONES":
    st.subheader("📋 COMANDO DE OPERACIONES TÁCTICAS")
    df_actas = leer_matriz_nube("ACTAS_FLOTAS")
    if not df_actas.empty: st.dataframe(df_actas.tail(20), use_container_width=True)

# --- ROL: GERENCIA ---
elif st.session_state.rol_sel == "GERENCIA":
    st.subheader("📈 DASHBOARD ESTRATÉGICO")
    df_al = leer_matriz_nube("ALERTAS")
    if not df_al.empty: st.write(df_al['ESTADO'].value_counts())

# --- ROL: ADMINISTRADOR (AL FINAL) ---
elif st.session_state.rol_sel == "ADMINISTRADOR":
    st.header("⚙️ NÚCLEO MAESTRO")
    u_admin = st.text_input("ADMIN_USER")
    p_admin = st.text_input("ADMIN_PASS", type="password")
    
    if u_admin == "admin" and p_admin == "aion2026":
        st.success("SISTEMA DESBLOQUEADO")
        tipo = st.radio("Alta de:", ["SUPERVISOR", "SERVICIO"], horizontal=True)
        nombre = st.text_input(f"Nombre {tipo}:").upper()
        if st.button("PROCESAR ALTA", type="secondary"):
            if nombre:
                escribir_registro_nube("ESTRUCTURA", [obtener_hora_argentina(), tipo, nombre, "ACTIVO", st.session_state.user_sel])
                st.success("Alta Exitosa")
