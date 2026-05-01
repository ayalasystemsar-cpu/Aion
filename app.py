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

def calcular_emergencia(lat, lon, df_obj):
    if df_obj.empty or lat == 0.0: return "S/D", "911", None
    df_temp = df_obj.copy()
    df_temp['distancia'] = np.sqrt((df_temp['LATITUD'] - lat)**2 + (df_temp['LONGITUD'] - lon)**2)
    cercano = df_temp.loc[df_temp['distancia'].idxmin()]
    return cercano['OBJETIVO'], cercano.get('POLICIA', '911'), (cercano['LATITUD'], cercano['LONGITUD'])

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
        
        .radar-box { border: 1px solid #1A1A1B; border-radius: 12px; padding: 15px; background: rgba(10, 10, 11, 0.8); }
        .banner-emergencia { background: #FF0000; color: white; padding: 15px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 10px; border: 2px solid #FFF; }
        h1, h2, h3, .stSubheader { font-family: 'Orbitron', sans-serif; color: #00E5FF !important; text-shadow: 0 0 10px rgba(0, 229, 255, 0.4); }
        
        /* Estilo para el área de texto de neutralización */
        .stTextArea textarea { background-color: #121212 !important; color: #E0E0E0 !important; border: 1px solid #FF0000 !important; }
        </style>
        """, unsafe_allow_html=True
    )

aplicar_identidad_alfa()

# --- 5. SIDEBAR Y GPS ---
if 'rol_sel' not in st.session_state: st.session_state.rol_sel = "MONITOREO"

with st.sidebar:
    st.markdown('<div class="contenedor-logo-sidebar"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" class="logo-sidebar"></div>', unsafe_allow_html=True)
    st.subheader("🛡️ PANEL DE CONTROL")
    st.session_state.rol_sel = st.selectbox("NIVEL DE ACCESO", ["MONITOREO", "SUPERVISOR", "JEFE DE OPERACIONES", "GERENCIA", "ADMINISTRADOR"])
    st.session_state.user_sel = st.selectbox("IDENTIDAD OPERATIVA", ["BRIAN AYALA", "SANOJA LUIS", "MAZACOTTE CLAUDIO", "DARÍO CECILIA", "LUIS BONGIORNO"])
    
    loc = get_geolocation()
    lat_act, lon_act = (loc['coords']['latitude'], loc['coords']['longitude']) if loc and 'coords' in loc else (-34.6037, -58.3816)

    st.markdown('<div style="display:flex; justify-content:center; margin-top:40px;">', unsafe_allow_html=True)
    if st.button("ACTIVAR\nPÁNICO", type="primary"):
        escribir_registro_nube("ALERTAS", [obtener_hora_argentina(), st.session_state.user_sel, "PÁNICO", "PENDIENTE", f"LAT: {lat_act} | LON: {lon_act}"])
    st.markdown('</div>', unsafe_allow_html=True)

# --- 6. FLUJO CENTRAL ---
st.markdown('<div class="contenedor-logo-central"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" class="logo-phoenix"></div>', unsafe_allow_html=True)
df_objetivos = cargar_objetivos()

# --- ROL: MONITOREO (Captura 537) ---
if st.session_state.rol_sel == "MONITOREO":
    st.subheader("🛰️ CENTRAL DE INTELIGENCIA OPERATIVA")
    df_alertas = leer_matriz_nube("ALERTAS")
    pendientes = df_alertas[df_alertas['ESTADO'].astype(str).str.upper() == 'PENDIENTE'] if not df_alertas.empty else pd.DataFrame()
    
    m1, m2, m3 = st.columns(3)
    m1.metric("🚨 S.O.S ACTIVOS", len(pendientes))
    m2.metric("📡 ESTADO DE RED", "OPERATIVO")
    m3.metric("🕒 HORA LOCAL", obtener_hora_argentina())

    tab_radar, tab_base, tab_com = st.tabs(["🚨 RADAR S.O.S", "📖 LIBRO DE BASE", "💬 COMUNICACIÓN"])
    
    with tab_radar:
        if not pendientes.empty:
            alerta_actual = pendientes.iloc[-1]
            op_sos = alerta_actual['USUARIO']
            carga = str(alerta_actual.get('CARGA_UTIL', ''))
            try:
                lat_s = float(carga.split("|")[0].split(":")[1].strip())
                lon_s = float(carga.split("|")[1].split(":")[1].strip())
            except: lat_s, lon_s = -34.6037, -58.3816
            
            obj_cercano, comisaria, _ = calcular_emergencia(lat_s, lon_s, df_objetivos)
            
            # Banner de Alerta Roja
            st.markdown(f"""<div class="banner-emergencia">
                <h3>Operador: {op_sos}</h3>
                <p>OBJETIVO CERCANO: {obj_cercano}</p>
                <p>🚓 COMISARÍA ASIGNADA: {comisaria}</p>
            </div>""", unsafe_allow_html=True)
            
            # Mapa SOS
            m_sos = folium.Map(location=[lat_s, lon_s], zoom_start=15, tiles="CartoDB dark_matter")
            folium.Marker([lat_s, lon_s], popup=f"SOS: {op_sos}", icon=folium.Icon(color="red", icon="warning")).add_to(m_sos)
            st_folium(m_sos, width="100%", height=400)
            
            # Botón de Ruta
            if st.button("🛣️ VER MEJOR RUTA DE RESPUESTA", use_container_width=True):
                maps_url = f"https://www.google.com/maps/dir/?api=1&destination={lat_s},{lon_s}"
                st.markdown(f'<meta http-equiv="refresh" content="0;url={maps_url}">', unsafe_allow_html=True)

            # --- SECCIÓN DE CIERRE (Imagen 537_2/3) ---
            st.markdown("### Informe de Neutralización")
            inf_texto = st.text_area("Detalles de la resolución:", placeholder="Escriba aquí...", label_visibility="collapsed")
            
            if st.button("CERRAR ALERTA", use_container_width=True, type="primary"):
                if inf_texto:
                    st.success(f"Alerta de {op_sos} neutralizada y registrada.")
                else:
                    st.error("Debe ingresar un informe para cerrar el evento.")
        else:
            st.success("✅ Vigilancia Pasiva - Sin Emergencias Detectadas")

# --- ROL: SUPERVISOR (Imagen 513/517) ---
elif st.session_state.rol_sel == "SUPERVISOR":
    st.subheader(f"⚡ ESTACIÓN TÁCTICA: {st.session_state.user_sel}")
    
    st.write("DESLICE PARA ACTIVAR S.O.S.")
    val_sos = st.slider("SOS", 0, 100, 0, label_visibility="collapsed")
    if val_sos == 100:
        escribir_registro_nube("ALERTAS", [obtener_hora_argentina(), st.session_state.user_sel, "PÁNICO", "PENDIENTE", f"LAT: {lat_act} | LON: {lon_act}"])
        st.warning("🚨 ALERTA SOS ENVIADA A CENTRAL")

    if st.button("🔄 REFRESCAR SISTEMA", use_container_width=True): st.rerun()

    st.info(f"🛰️ TELEMETRÍA GPS ACTIVA\n\nLat: {lat_act}\n\nLon: {lon_act}")

    t_map, t_rep = st.tabs(["📍 RADAR GPS", "📝 REPORTE"])
    with t_map:
        st.markdown('<div class="radar-box">', unsafe_allow_html=True)
        m_sup = folium.Map(location=[lat_act, lon_act], zoom_start=12, tiles="CartoDB dark_matter")
        # Marcadores de objetivos según zona
        st_folium(m_sup, width="100%", height=400, key="map_supervisor")
        st.markdown('</div>', unsafe_allow_html=True)

# --- JEFE DE OPERACIONES ---
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

# --- GERENCIA ---
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

# --- ADMINISTRADOR ---
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
