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

# --- 4. DISEÑO E IDENTIDAD VISUAL ---
def aplicar_identidad_alfa():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@300;500;700&display=swap');
        .stApp { background: radial-gradient(circle at top, #0A0F1E 0%, #030305 100%) !important; color: #E0E0E0; font-family: 'Rajdhani', sans-serif; }
        [data-testid="stSidebar"] { background-color: #050507 !important; border-right: 1px solid rgba(0, 229, 255, 0.3) !important; }
        .contenedor-logo-sidebar { display: flex; justify-content: center; align-items: center; width: 100%; margin-bottom: 20px; padding: 10px; }
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
        h1, h2, h3, .stSubheader { font-family: 'Orbitron', sans-serif; color: #00E5FF !important; text-shadow: 0 0 15px rgba(0, 229, 255, 0.4); }
        
        .estacion-titulo {
            font-family: 'Orbitron', sans-serif;
            color: #00E5FF !important;
            font-size: 24px;
            margin-top: 15px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
        }
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
    
    loc = get_geolocation()
    lat_act = loc['coords']['latitude'] if loc else 0.0
    lon_act = loc['coords'].get('longitude', 0.0) if loc else 0.0

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

# --- 6. FLUJO CENTRAL ---
st.markdown('<div class="contenedor-logo-central"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" class="logo-phoenix"></div>', unsafe_allow_html=True)

df_objetivos = cargar_objetivos()

# --- 7. FLUJO DE INTERFAZ POR ROLES ---

# A. ROL: SUPERVISOR (Captura 531)
if st.session_state.rol_sel == "SUPERVISOR":
    st.markdown(f'<div class="estacion-titulo">📱 Estación de Control: {st.session_state.user_sel}</div>', unsafe_allow_html=True)
    st.markdown('<div style="color:#E0E0E0; font-size:16px; margin-top:20px; text-align:center;">📍 Mi Radar de Servicios y GPS</div>', unsafe_allow_html=True)
    
    t1, t2 = st.tabs(["📍 RADAR GPS", "📝 REPORTE"])
    with t1:
        st.markdown('<div class="radar-box">', unsafe_allow_html=True)
        centro = [lat_act, lon_act] if lat_act != 0 else [-34.6, -58.4]
        m = folium.Map(location=centro, zoom_start=12, tiles="CartoDB dark_matter")
        for _, r in df_objetivos.iterrows():
            folium.Marker([r['LATITUD'], r['LONGITUD']], popup=r['OBJETIVO'], icon=folium.Icon(color="blue", icon="shield", prefix="fa")).add_to(m)
        if lat_act != 0:
            folium.Marker([lat_act, lon_act], icon=folium.Icon(color="red", icon="user", prefix="fa")).add_to(m)
        st_folium(m, width="100%", height=400, key="map_sup")
        st.markdown('</div>', unsafe_allow_html=True)
    with t2:
        with st.form("nov_sup"):
            f_dest = st.selectbox("Objetivo:", df_objetivos['OBJETIVO'].unique()) if not df_objetivos.empty else "N/A"
            f_nov = st.text_area("Informe de Novedad")
            if st.form_submit_button("🚀 TRANSMITIR"):
                escribir_registro_nube("ACTAS_FLOTAS", [obtener_hora_argentina(), st.session_state.user_sel, "", "", "", "", "", f_dest, f_nov, "VERDE"])
                st.success("Reporte enviado.")

# B. ROL: MONITOREO (Lógica Táctica de Alertas)
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
            op_riesgo = datos_sos['USUARIO']
            carga = str(datos_sos.get('CARGA_UTIL', ''))
            
            try:
                lat_m = float(carga.split("|")[0].split(":")[1].strip())
                lon_m = float(carga.split("|")[1].split(":")[1].strip())
                info_sos = {"user": op_riesgo, "lat": lat_m, "lon": lon_m}
                
                # --- LÓGICA TÁCTICA AGREGADA ---
                obj_c, pol, coo_apoyo = calcular_emergencia(lat_m, lon_m, df_objetivos)
                st.error(f"🚨 EMERGENCIA ACTIVA: {op_riesgo} | APOYO CERCANO: {obj_c} | POLICÍA: {pol}")
            except: pass
        else:
            st.success("✅ Vigilancia Pasiva - Radar Operativo")

        st.markdown('<div class="radar-box">', unsafe_allow_html=True)
        m_sos = folium.Map(location=[lat_m, lon_m], zoom_start=13, tiles="CartoDB dark_matter")
        
        # Dibujar Objetivos
        for _, r in df_objetivos.iterrows():
            folium.Marker([r['LATITUD'], r['LONGITUD']], tooltip=r['OBJETIVO'], icon=folium.Icon(color="blue", icon="shield", prefix="fa")).add_to(m_sos)
        
        # Dibujar S.O.S y Ruta de Respuesta
        if info_sos:
            folium.Marker([info_sos["lat"], info_sos["lon"]], tooltip="RIESGO", icon=folium.Icon(color="red", icon="warning")).add_to(m_sos)
            if 'coo_apoyo' in locals() and coo_apoyo:
                # Trazado de ruta táctica neón
                AntPath(locations=[[info_sos["lat"], info_sos["lon"]], [coo_apoyo[0], coo_apoyo[1]]], 
                        color="#FF0000", weight=5, pulse_color="#ffffff").add_to(m_sos)
                
        st_folium(m_sos, width="100%", height=450, key="map_mon_tactico")
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

    with t_gestion:
        if not df_emergencias.empty: st.dataframe(df_emergencias.tail(20), use_container_width=True)

# C. ROL: JEFE DE OPERACIONES
elif st.session_state.rol_sel == "JEFE DE OPERACIONES":
    st.header("📋 COMANDO DE OPERACIONES TÁCTICAS")
    tab_inf, tab_map = st.tabs(["📄 INFORMES", "🌍 MAPA"])
    with tab_inf:
        df_actas = leer_matriz_nube("ACTAS_FLOTAS")
        if not df_actas.empty: st.dataframe(df_actas.tail(20), use_container_width=True)
    with tab_map:
        st.markdown('<div class="radar-box">', unsafe_allow_html=True)
        m_ops = folium.Map(location=[df_objetivos['LATITUD'].mean() if not df_objetivos.empty else -34.6, df_objetivos['LONGITUD'].mean() if not df_objetivos.empty else -58.4], zoom_start=11, tiles="CartoDB dark_matter")
        for _, r in df_objetivos.iterrows():
            folium.Marker([r['LATITUD'], r['LONGITUD']], popup=r['OBJETIVO'], icon=folium.Icon(color="green", icon="dot-circle-o", prefix="fa")).add_to(m_ops)
        st_folium(m_ops, width="100%", height=500, key="mapa_operaciones")
        st.markdown('</div>', unsafe_allow_html=True)

# D. ADMINISTRADOR
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
