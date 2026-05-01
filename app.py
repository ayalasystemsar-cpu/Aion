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

# --- 4. DISEÑO E IDENTIDAD VISUAL (ESTILO TÁCTICO) ---
def aplicar_identidad_alfa():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@300;500;700&display=swap');
        
        .stApp { background: #030305 !important; color: #E0E0E0; font-family: 'Rajdhani', sans-serif; }
        [data-testid="stSidebar"] { background-color: #050507 !important; border-right: 1px solid rgba(0, 229, 255, 0.3) !important; }
        
        /* LOGO SIDEBAR: RECUADRO CIAN NEÓN */
        .contenedor-logo-sidebar { display: flex; justify-content: center; align-items: center; padding: 10px; margin-bottom: 20px; }
        .logo-sidebar { 
            width: 180px !important; 
            border: 2px solid #00e5ff !important; 
            box-shadow: 0 0 20px rgba(0, 229, 255, 0.6) !important; 
            border-radius: 4px; background: #000 !important;
        }

        .stButton > button[kind="primary"] { 
            background: radial-gradient(circle, #FF0000 0%, #8B0000 100%) !important; 
            color: white !important; border-radius: 50% !important; width: 105px !important; height: 105px !important; 
            box-shadow: 0 0 25px rgba(255, 0, 0, 0.7) !important; border: 2px solid #333 !important;
            font-family: 'Orbitron', sans-serif; font-size: 11px !important; font-weight: bold;
        }

        .radar-box { border: 1px solid #1A1A1B; border-radius: 12px; padding: 10px; background: #000; }
        h1, h2, h3, .stSubheader { font-family: 'Orbitron', sans-serif; color: #00E5FF !important; }
        </style>
        """, unsafe_allow_html=True
    )

aplicar_identidad_alfa()

# --- 5. SIDEBAR (GPS SEGURO Y CONTROL) ---
with st.sidebar:
    st.markdown('<div class="contenedor-logo-sidebar"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" class="logo-sidebar"></div>', unsafe_allow_html=True)
    st.subheader("🛡️ PANEL DE CONTROL")
    
    rol_actual = st.selectbox("NIVEL DE ACCESO", ["SUPERVISOR", "MONITOREO", "JEFE DE OPERACIONES", "ADMINISTRADOR"])
    
    identidades = ["SERANTES WALTER", "BRIAN AYALA", "SANOJA LUIS", "DARÍO CECILIA", "LUIS BONGIORNO", "MAZACOTTE CLAUDIO"]
    usuario_actual = st.selectbox("IDENTIDAD OPERATIVA", identidades)
    
    # GPS SEGURO PARA CELULARES
    loc = get_geolocation()
    lat_act = loc['coords'].get('latitude', 0.0) if loc and 'coords' in loc else 0.0
    lon_act = loc['coords'].get('longitude', 0.0) if loc and 'coords' in loc else 0.0

    st.markdown('<div style="display:flex; justify-content:center; margin-top:20px;">', unsafe_allow_html=True)
    if st.button("ACTIVAR\nPÁNICO", type="primary"):
        carga_sos = f"LAT: {lat_act} | LON: {lon_act}"
        exito = escribir_registro_nube("ALERTAS", [obtener_hora_argentina(), usuario_actual, "PÁNICO", "PENDIENTE", carga_sos])
        if exito:
            st.error("🚨 S.O.S ENVIADO")
            st.toast("Señal transmitida", icon="🛡️")
    st.markdown('</div>', unsafe_allow_html=True)

# --- 6. FLUJO CENTRAL ---
df_objetivos = cargar_objetivos()

# A. ROL: SUPERVISOR
if rol_actual == "SUPERVISOR":
    st.subheader(f"📱 Estación: {usuario_actual}")
    t1, t2 = st.tabs(["📍 MI RADAR", "📝 NOVEDADES"])
    with t1:
        st.markdown('<div class="radar-box">', unsafe_allow_html=True)
        centro = [lat_act if lat_act != 0 else -34.6, lon_act if lon_act != 0 else -58.4]
        m = folium.Map(location=centro, zoom_start=12, tiles="CartoDB dark_matter")
        for _, r in df_objetivos.iterrows():
            folium.Marker([r['LATITUD'], r['LONGITUD']], popup=r['OBJETIVO'], icon=folium.Icon(color="blue", icon="shield", prefix="fa")).add_to(m)
        if lat_act != 0:
            folium.Marker([lat_act, lon_act], icon=folium.Icon(color="red", icon="user", prefix="fa")).add_to(m)
        st_folium(m, width="100%", height=400, key="map_sup")
        st.markdown('</div>', unsafe_allow_html=True)

# B. ROL: MONITOREO (Cerebro de la operación)
elif rol_actual == "MONITOREO":
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
                obj_cercano, policia, coords_apoyo = calcular_emergencia(lat_m, lon_m, df_objetivos)
                st.error(f"🚨 EMERGENCIA ACTIVA: {op_riesgo} | OBJETIVO: {obj_cercano} | POLICÍA: {policia}")
            except: pass
        else:
            st.success("✅ Vigilancia Pasiva - Radar Operativo")

        st.markdown('<div class="radar-box">', unsafe_allow_html=True)
        m_sos = folium.Map(location=[lat_m, lon_m], zoom_start=13, tiles="CartoDB dark_matter")
        for _, r in df_objetivos.iterrows():
            folium.Marker([r['LATITUD'], r['LONGITUD']], tooltip=r['OBJETIVO'], icon=folium.Icon(color="blue", icon="shield", prefix="fa")).add_to(m_sos)
        if info_sos:
            folium.Marker([info_sos["lat"], info_sos["lon"]], icon=folium.Icon(color="red", icon="warning")).add_to(m_sos)
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

    with t_gestion:
        if not df_emergencias.empty: st.dataframe(df_emergencias.tail(20), use_container_width=True)

# C. ROL: JEFE DE OPERACIONES
elif rol_actual == "JEFE DE OPERACIONES":
    st.header("📋 COMANDO DE OPERACIONES TÁCTICAS")
    tab_inf, tab_map = st.tabs(["📄 INFORMES", "🌍 MAPA"])
    with tab_inf:
        df_actas = leer_matriz_nube("ACTAS_FLOTAS")
        if not df_actas.empty: st.dataframe(df_actas.tail(20), use_container_width=True)
    with tab_map:
        st.markdown('<div class="radar-box">', unsafe_allow_html=True)
        m_ops = folium.Map(location=[df_objetivos['LATITUD'].mean(), df_objetivos['LONGITUD'].mean()], zoom_start=11, tiles="CartoDB dark_matter")
        for _, r in df_objetivos.iterrows():
            folium.Marker([r['LATITUD'], r['LONGITUD']], popup=r['OBJETIVO'], icon=folium.Icon(color="green", icon="dot-circle-o", prefix="fa")).add_to(m_ops)
        st_folium(m_ops, width="100%", height=500, key="mapa_operaciones")
        st.markdown('</div>', unsafe_allow_html=True)

# D. ROL: ADMINISTRADOR
elif rol_actual == "ADMINISTRADOR":
    st.header("⚙️ NÚCLEO MAESTRO")
    u_ing = st.text_input("ADMIN_USER")
    p_ing = st.text_input("ADMIN_PASS", type="password")
    if u_ing == "admin" and p_ing == "aion2026":
        tipo = st.radio("Categoría:", ["SUPERVISOR", "SERVICIO"], horizontal=True)
        nuevo_nombre = st.text_input(f"Nombre del {tipo}:").upper()
        if st.button("PROCESAR ALTA"):
            escribir_registro_nube("ESTRUCTURA", [obtener_hora_argentina(), tipo, nuevo_nombre, "ACTIVO", usuario_actual])
            st.success("Alta Exitosa")
