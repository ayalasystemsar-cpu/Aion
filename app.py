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

def calcular_emergencia(lat, lon, df_obj):
    if df_obj.empty or lat == 0.0: return "Sin datos", "Sin datos", None
    df_temp = df_obj.copy()
    df_temp['distancia'] = np.sqrt((df_temp['LATITUD'] - lat)**2 + (df_temp['LONGITUD'] - lon)**2)
    cercano = df_temp.loc[df_temp['distancia'].idxmin()]
    return cercano['OBJETIVO'], cercano.get('POLICIA', '911'), (cercano['LATITUD'], cercano['LONGITUD'])

# --- 4. DISEÑO E IDENTIDAD VISUAL (ESTILO OLED TÁCTICO) ---
def aplicar_identidad_alfa():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@300;500;700&display=swap');
        .stApp { background: radial-gradient(circle at top, #0A0F1E 0%, #030305 100%) !important; color: #E0E0E0; font-family: 'Rajdhani', sans-serif; }
        [data-testid="stSidebar"] { background-color: #050507 !important; border-right: 1px solid rgba(0, 229, 255, 0.3) !important; }
        
        .contenedor-logo-sidebar { display: flex; justify-content: center; align-items: center; padding: 15px; margin-bottom: 10px; }
        .logo-sidebar { 
            width: 100% !important; max-width: 200px !important;
            border: 1.5px solid #00e5ff !important; 
            box-shadow: 0 0 15px rgba(0, 229, 255, 0.4) !important; 
            border-radius: 4px; background-color: #000 !important; padding: 2px;
        }
        
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
        h1, h2, h3, .stSubheader { font-family: 'Orbitron', sans-serif; color: #00E5FF !important; text-shadow: 0 0 15px rgba(0, 229, 255, 0.4); }
        </style>
        """, unsafe_allow_html=True
    )

aplicar_identidad_alfa()

# --- 5. MEMORIA DE SESIÓN Y SIDEBAR ---
if 'rol_sel' not in st.session_state: st.session_state.rol_sel = "MONITOREO"
if 'user_sel' not in st.session_state: st.session_state.user_sel = "BRIAN AYALA"

with st.sidebar:
    st.markdown('<div class="contenedor-logo-sidebar"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" class="logo-sidebar"></div>', unsafe_allow_html=True)
    st.subheader("🛡️ PANEL DE CONTROL")
    st.session_state.rol_sel = st.selectbox("NIVEL DE ACCESO", ["SUPERVISOR", "MONITOREO", "JEFE DE OPERACIONES", "GERENCIA", "ADMINISTRADOR"])
    st.session_state.user_sel = st.selectbox("IDENTIDAD OPERATIVA", ["BRIAN AYALA", "SANOJA LUIS P.", "DARÍO CECILIA", "LUIS BONGIORNO", "SERANTES WALTER", "MAZACOTTE CLAUDIO"])
    
    # GPS SEGURO
    loc = get_geolocation()
    lat_act, lon_act = 0.0, 0.0
    if loc and 'coords' in loc:
        lat_act = loc['coords'].get('latitude', 0.0)
        lon_act = loc['coords'].get('longitude', 0.0)

    st.markdown('<div class="panico-container">', unsafe_allow_html=True)
    if st.button("ACTIVAR\nPÁNICO", type="primary"):
        carga_sos = f"LAT: {lat_act} | LON: {lon_act}"
        exito = escribir_registro_nube("ALERTAS", [obtener_hora_argentina(), st.session_state.user_sel, "PÁNICO", "PENDIENTE", carga_sos])
        if exito:
            st.error("🚨 S.O.S ENVIADO")
            st.toast("Señal transmitida a central", icon="🛡️")
        else:
            st.warning("⚠️ Fallo en red SOS")
    st.markdown('</div>', unsafe_allow_html=True)

# --- 6. LOGO CENTRAL ---
st.markdown('<div class="contenedor-logo-central"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" class="logo-phoenix"></div>', unsafe_allow_html=True)

df_objetivos = cargar_objetivos()

# --- 7. FLUJO DE INTERFAZ POR ROLES ---

# A. SUPERVISOR
if st.session_state.rol_sel == "SUPERVISOR":
    st.markdown(f'<div style="background:#0A1628; padding:10px; border-radius:5px; color:#00E5FF; border:1px solid #00E5FF; text-align:center; margin-bottom:20px;">Coordenadas: {lat_act} | {lon_act}</div>', unsafe_allow_html=True)
    
    apellido = st.session_state.user_sel.split()[-1].upper()
    df_zona = df_objetivos[df_objetivos['SUPERVISOR'].str.upper().str.contains(apellido, na=False)] if not df_objetivos.empty else pd.DataFrame()
    if df_zona.empty: df_zona = df_objetivos

    t1, t2 = st.tabs(["📍 RADAR GPS", "📝 REPORTE"])
    with t1:
        st.markdown('<div class="radar-box">', unsafe_allow_html=True)
        m = folium.Map(location=[lat_act if lat_act != 0 else -34.6, lon_act if lon_act != 0 else -58.4], zoom_start=12, tiles="CartoDB dark_matter")
        for _, r in df_zona.iterrows():
            folium.Marker([r['LATITUD'], r['LONGITUD']], popup=r['OBJETIVO'], icon=folium.Icon(color="blue", icon="shield", prefix="fa")).add_to(m)
        if lat_act != 0:
            folium.Marker([lat_act, lon_act], icon=folium.Icon(color="red", icon="user", prefix="fa")).add_to(m)
        st_folium(m, width="100%", height=400, key="map_sup")
        st.markdown('</div>', unsafe_allow_html=True)
    with t2:
        with st.form("nov_sup"):
            f_dest = st.selectbox("Objetivo:", df_zona['OBJETIVO'].unique()) if not df_zona.empty else "N/A"
            f_nov = st.text_area("Informe de Novedad")
            if st.form_submit_button("🚀 TRANSMITIR"):
                escribir_registro_nube("ACTAS_FLOTAS", [obtener_hora_argentina(), st.session_state.user_sel, "", "", "", "", "", f_dest, f_nov, "VERDE"])
                st.success("Reporte enviado.")

# B. MONITOREO
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
        lat_m, lon_m = -34.6037, -58.3816
        if not df_objetivos.empty: lat_m, lon_m = df_objetivos['LATITUD'].mean(), df_objetivos['LONGITUD'].mean()

        info_sos = None
        if sos_activos > 0:
            datos_sos = df_emergencias[df_emergencias['ESTADO'].astype(str).str.upper() == 'PENDIENTE'].iloc[-1]
            try:
                lat_m = float(str(datos_sos['CARGA_UTIL']).split("|")[0].split(":")[1])
                lon_m = float(str(datos_sos['CARGA_UTIL']).split("|")[1].split(":")[1])
                info_sos = {"user": datos_sos['USUARIO'], "lat": lat_m, "lon": lon_m}
                obj_c, pol, coo = calcular_emergencia(lat_m, lon_m, df_objetivos)
                st.error(f"🚨 EMERGENCIA: {info_sos['user']} | OBJETIVO: {obj_c} | POLICÍA: {pol}")
            except: pass

        st.markdown('<div class="radar-box">', unsafe_allow_html=True)
        m_sos = folium.Map(location=[lat_m, lon_m], zoom_start=13, tiles="CartoDB dark_matter")
        for _, r in df_objetivos.iterrows():
            folium.Marker([r['LATITUD'], r['LONGITUD']], tooltip=r['OBJETIVO'], icon=folium.Icon(color="blue", icon="shield", prefix="fa")).add_to(m_sos)
        if info_sos:
            folium.Marker([lat_m, lon_m], icon=folium.Icon(color="red", icon="warning")).add_to(m_sos)
        st_folium(m_sos, width="100%", height=450, key="map_mon")
        st.markdown('</div>', unsafe_allow_html=True)

        if sos_activos > 0:
            st.subheader("📝 PROTOCOLO DE CIERRE")
            inf_neu = st.text_area("INFORME DE NEUTRALIZACIÓN")
            if st.button("FINALIZAR OPERATIVO"):
                if inf_neu.strip():
                    fila = df_emergencias[df_emergencias['ESTADO'].astype(str).str.upper() == 'PENDIENTE'].index[-1] + 2
                    actualizar_celda("ALERTAS", fila, "D", "RESUELTO")
                    actualizar_celda("ALERTAS", fila, "F", inf_neu)
                    st.rerun()

# C. JEFE DE OPERACIONES
elif st.session_state.rol_sel == "JEFE DE OPERACIONES":
    st.subheader("📋 COMANDO DE OPERACIONES TÁCTICAS")
    df_actas = leer_matriz_nube("ACTAS_FLOTAS")
    if not df_actas.empty: st.dataframe(df_actas.tail(20), use_container_width=True)

# D. GERENCIA
elif st.session_state.rol_sel == "GERENCIA":
    st.header("📈 DASHBOARD ESTRATÉGICO")
    df_al = leer_matriz_nube("ALERTAS")
    if not df_al.empty: st.write(df_al['ESTADO'].value_counts())

# E. ADMINISTRADOR
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
