import streamlit as st
import datetime
from datetime import datetime
import pandas as pd
import pytz
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from streamlit_js_eval import get_geolocation

# --- IMPORTACIONES CRÍTICAS DE MAPAS ---
import folium
from folium.plugins import AntPath
from streamlit_folium import st_folium
import math

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
            data = hoja.get_all_records()
            if not data:
                return pd.DataFrame()
            return pd.DataFrame(data)
        except: return pd.DataFrame()
    return pd.DataFrame()

@st.cache_data(ttl=60)
def cargar_objetivos():
    df = leer_matriz_nube("OBJETIVOS")
    if not df.empty:
        df.columns = df.columns.str.strip().str.upper()
        
        # 1. Filtramos de raíz celdas que visualmente parezcan vacías o tengan puros espacios
        df = df[df['OBJETIVO'].astype(str).str.strip() != ""]
        df = df[df['OBJETIVO'].notna()]
        
        # 2. Sanitización estricta de la columna SUPERVISOR para evitar herencias falsas o espacios extras
        if 'SUPERVISOR' in df.columns:
            df['SUPERVISOR'] = df['SUPERVISOR'].astype(str).str.strip().str.upper()
        
        # Corrección automática de comas por puntos en coordenadas
        df['LATITUD'] = df['LATITUD'].astype(str).str.replace(',', '.')
        df['LONGITUD'] = df['LONGITUD'].astype(str).str.replace(',', '.')
        
        df['LATITUD'] = pd.to_numeric(df['LATITUD'], errors='coerce')
        df['LONGITUD'] = pd.to_numeric(df['LONGITUD'], errors='coerce')
        return df 
    return pd.DataFrame()

# --- 4. DISEÑO E IDENTIDAD VISUAL ---
def aplicar_identidad_alfa():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@300;500;700&display=swap');
        .stApp { background: radial-gradient(circle at top, #0A0F1E 0%, #030305 100%) !important; color: #E0E0E0; font-family: 'Rajdhani', sans-serif; }
        .contenedor-logo-central { display: flex; justify-content: center; align-items: center; width: 100%; margin-bottom: 5px; margin-top: 10px; }
        .logo-phoenix { width: 520px !important; border: 2px solid #00e5ff !important; box-shadow: 0 0 35px rgba(0, 229, 255, 0.5) !important; border-radius: 4px !important; background-color: #000 !important; }
        
        .estacion-titulo {
            font-family: 'Orbitron', sans-serif;
            color: #00E5FF !important;
            font-size: 24px;
            margin-top: 15px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
            text-shadow: 0 0 15px rgba(0, 229, 255, 0.4);
            letter-spacing: 2px;
            text-transform: uppercase;
        }
        
        .titulo-seccion-admin {
            color: #00E5FF;
            font-family: 'Orbitron', sans-serif;
            font-size: 22px;
            font-weight: bold;
            margin-top: 25px;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
            letter-spacing: 1px;
            text-shadow: 0 0 10px rgba(0, 229, 255, 0.3);
        }

        .stApp div[data-testid="stExpander"] {
            background-color: #1A1C23 !important;
            border: 1px solid #2D313E !important;
            border-radius: 8px !important;
        }
        
        .stApp div[data-testid="stExpander"] summary p {
            color: #E0E0E0 !important;
            font-size: 14px !important;
            font-weight: 600 !important;
            text-transform: uppercase;
        }
        
        .stApp input {
            background-color: #252833 !important;
            color: #FFFFFF !important;
            border: 1px solid #1A1C23 !important;
            border-radius: 6px !important;
        }
        
        .stApp label p {
            color: #A0A5B5 !important;
            font-family: 'Orbitron', sans-serif !important;
            font-size: 11px !important;
            font-weight: bold !important;
            letter-spacing: 0.5px;
            text-transform: uppercase;
        }

        .radar-box { border: 1px solid #1A1A1B; border-radius: 12px; padding: 10px; background: rgba(10, 10, 11, 0.9); }
        .stButton > button[kind="primary"] { 
            background: radial-gradient(circle, #FF0000 0%, #8B0000 100%) !important; 
            color: white !important; border-radius: 50% !important; width: 105px !important; height: 105px !important; 
            border: 3px solid #333 !important; box-shadow: 0 0 25px rgba(255, 0, 0, 0.5) !important; 
            font-family: 'Orbitron', sans-serif; font-size: 11px !important; font-weight: bold;
        }
        
        .chat-container { border: 1px solid #1a1a1b; border-radius: 8px; padding: 15px; margin-top: 10px; background-color: #030305; }
        .message-box { border-left: 3px solid #00e5ff; padding-left: 10px; margin-bottom: 15px; background: rgba(255,255,255,0.02); padding-top: 5px; padding-bottom: 5px; }
        .message-box-red { border-left: 3px solid #ff0000; padding-left: 10px; margin-bottom: 15px; background: rgba(255,255,255,0.02); padding-top: 5px; padding-bottom: 5px; }
        .message-info { color: #00e5ff; font-size: 13px; font-weight: bold; font-family: 'Orbitron', sans-serif; }
        .message-info-red { color: #ff0000; font-size: 13px; font-weight: bold; font-family: 'Orbitron', sans-serif; }
        .message-text { color: #e0e0e0; font-size: 14px; margin-top: 4px; font-family: 'Rajdhani', sans-serif; }
        
        .panel-info { display: flex; justify-content: space-between; margin-bottom: 20px; padding: 10px; border: 1px solid #333; border-radius: 4px; background: rgba(10, 10, 11, 0.9); }
        .panel-novedad { border: 1px solid #333; border-radius: 8px; padding: 15px; margin-top: 20px; background-color: rgba(10, 10, 11, 0.9); }

        .stButton > button.btn-refresh {
            background: #00e5ff !important;
            color: #000 !important;
            font-family: 'Orbitron', sans-serif;
            font-weight: bold;
            border-radius: 4px !important;
            border: 1px solid #00e5ff !important;
            box-shadow: 0 0 10px rgba(0, 229, 255, 0.3) !important;
        }

        .stTabs [data-baseweb="tab-list"] { gap: 10px; background-color: transparent; }
        .stTabs [data-baseweb="tab"] {
            background-color: rgba(26, 28, 35, 0.4) !important;
            border: 1px solid #2D313E !important;
            color: #A0A5B5 !important;
            border-radius: 4px 4px 0px 0px !important;
            padding: 6px 16px !important;
            font-family: 'Orbitron', sans-serif;
            font-size: 11px !important;
            font-weight: bold;
        }
        .stTabs [data-baseweb="tab"]:hover { color: #00E5FF !important; }
        .stTabs [aria-selected="true"] {
            background-color: #1A1C23 !important;
            border-top: 2px solid #00E5FF !important;
            color: #00E5FF !important;
        }

        div[data-testid="stMetric"] {
            background-color: rgba(10, 11, 15, 0.6) !important;
            border: 1px solid #1A1C23 !important;
            border-radius: 6px !important;
            padding: 12px !important;
        }
        div[data-testid="stMetricLabel"] p {
            color: #00E5FF !important;
            font-family: 'Rajdhani', sans-serif !important;
            font-size: 13px !important;
            font-weight: bold !important;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        div[data-testid="stMetricValue"] div {
            color: #FFFFFF !important;
            font-family: 'Orbitron', sans-serif !important;
            font-size: 22px !important;
        }
        </style>
        """, unsafe_allow_html=True
    )

aplicar_identidad_alfa()

# --- 5. SIDEBAR TÁCTICO ---
df_objetivos = cargar_objetivos()

LISTA_SUPS_TACTICOS = [
    "AYALA BRIAN",
    "SUPERVISOR 1", 
    "SUPERVISOR 2", 
    "SUPERVISOR 3", 
    "SUPERVISOR 4", 
    "SUPERVISOR 5", 
    "SUPERVISOR NOCTURNO"
]

if 'rol_sel' not in st.session_state: st.session_state.rol_sel = "MONITOREO"
if 'user_sel' not in st.session_state: st.session_state.user_sel = "OPERADOR CENTRAL"
if 'sup_autenticado' not in st.session_state: st.session_state.sup_autenticado = False

with st.sidebar:
    st.markdown('<div class="contenedor-logo-sidebar"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" style="width:180px; border:1px solid #00e5ff; border-radius:4px;"></div>', unsafe_allow_html=True)
    st.subheader("🛡️ PANEL DE CONTROL")
    st.markdown("<span style='font-size: 11px; color:#A0A5B5; font-family:\"Orbitron\"; font-weight:bold; letter-spacing:0.5px;'>NIVEL DE ACCESO</span>", unsafe_allow_html=True)
    
    # 1. MONITOREO
    if st.button("🛰️ MONITOREO", use_container_width=True):
        st.session_state.rol_sel = "MONITOREO"
        st.session_state.user_sel = "OPERADOR CENTRAL"
        st.session_state.sup_autenticado = False
        st.rerun()
        
    # 2. JEFE DE OPERACIONES
    if st.button("📋 JEFE DE OPERACIONES", use_container_width=True):
        st.session_state.rol_sel = "JEFE DE OPERACIONES"
        st.session_state.user_sel = "SANOJA LUIS"
        st.session_state.sup_autenticado = False
        st.rerun()
        
    # 3. GERENCIA
    if st.button("🏢 GERENCIA", use_container_width=True):
        st.session_state.rol_sel = "GERENCIA"
        st.session_state.user_sel = "DIRECCIÓN GENERAL"
        st.session_state.sup_autenticado = False
        st.rerun()

    # 4. SUPERVISORES
    with st.expander("👤 SUPERVISORES", expanded=(st.session_state.rol_sel == "SUPERVISOR" or 'intentando_sup' in st.session_state)):
        nom_sup = st.selectbox(
            "RESPONSABLE ACTIVO:", 
            LISTA_SUPS_TACTICOS,
            key="cambio_supervisor_directo"
        )
        
        user_sup = st.text_input("USUARIO RECURSO (APELLIDO)", key="auth_user_sup")
        pass_sup = st.text_input("CONTRASEÑA CRÍTICA", type="password", key="auth_pass_sup")
        
        if st.button("AUTENTICAR E INGRESAR", use_container_width=True):
            st.session_state.intentando_sup = True
            
            if "NOCTURNO" in nom_sup:
                usuario_esperado = "nocturno"
            elif "AYALA" in nom_sup:
                usuario_esperado = "ayala"
            else:
                usuario_esperado = nom_sup.split(" ")[1]
            
            if user_sup.strip().lower() == usuario_esperado and pass_sup == "1234":
                st.session_state.rol_sel = "SUPERVISOR"
                st.session_state.user_sel = nom_sup
                st.session_state.sup_autenticado = True
                if 'intentando_sup' in st.session_state: del st.session_state.intentando_sup
                st.success(f"🔓 ACCESO CONCEDIDO: {nom_sup}")
                st.rerun()
            else:
                st.session_state.sup_autenticado = False
                st.error("❌ CREDENCIALES INVÁLIDAS EN BASE")

    st.write("---")
    
    # 5. ADMINISTRADOR
    st.markdown("**⚙️ ADMINISTRADOR**")
    if st.button("ACCEDER AL NÚCLEO MAESTRO", use_container_width=True):
        st.session_state.rol_sel = "ADMINISTRADOR"
        st.session_state.user_sel = "ADMIN CENTRAL"
        st.session_state.sup_autenticado = False
        st.rerun()

    st.write("---")
    
    loc = get_geolocation()
    lat_envio = loc['coords']['latitude'] if loc else 0.0
    lon_envio = loc['coords'].get('longitude', 0.0) if loc else 0.0

    if st.button("ACTIVAR\nPÁNICO", type="primary"):
        if st.session_state.rol_sel == "SUPERVISOR" and 'sup_servicio_actual' in st.session_state:
            obj_alerta = st.session_state.sup_servicio_actual
        else:
            obj_alerta = "CENTRAL BASE"
            
        carga_sos = f"LAT:{lat_envio}|LON:{lon_envio}|OBJ:{obj_alerta}|SUP:{st.session_state.user_sel}"
        escribir_registro_nube("ALERTAS", [obtener_hora_argentina(), st.session_state.user_sel, "PÁNICO", "PENDIENTE", carga_sos])
        st.error(f"🚨 S.O.S ENVIADO DESDE {obj_alerta}")

# --- 6. CABECERA CENTRAL ---
st.markdown('<div class="contenedor-logo-central"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" class="logo-phoenix"></div>', unsafe_allow_html=True)

if st.session_state.rol_sel == "SUPERVISOR" and not st.session_state.sup_autenticado:
    st.markdown('<div class="estacion-titulo">🔒 ESTACIÓN BLOQUEADA - REQUIERE AUTENTICACIÓN EN SIDEBAR</div>', unsafe_allow_html=True)
else:
    titulos = {
        "MONITOREO": "🛰️ CENTRAL DE INTELIGENCIA OPERATIVA",
        "SUPERVISOR": f"📱 Estación de Control: {st.session_state.user_sel}",
        "JEFE DE OPERACIONES": "📋 COMANDO DE OPERACIONES TÁCTICAS",
        "GERENCIA": "🏢 DIRECCIÓN Y FISCALIZACIÓN GENERAL",
        "ADMINISTRADOR": "⚙️ NÚCLEO MAESTRO: AION-YAROKU"
    }
    st.markdown(f'<div class="estacion-titulo">{titulos.get(st.session_state.rol_sel, "SISTEMA TÁCTICO DE COMANDO")}</div>', unsafe_allow_html=True)
# --- FUNCIÓN UNIFICADA DE COMUNICACIONES ---
def renderizar_comunicaciones():
    st.markdown('<h3>📥 BANDEJA DE INTELIGENCIA</h3>', unsafe_allow_html=True)
    df_chats = leer_matriz_nube("CHATS")
    if not df_chats.empty:
        for _, msg in df_chats.tail(10).iloc[::-1].iterrows():
            es_rojo = msg.get("PRIORIDAD", "VERDE") == "ROJA"
            st.markdown(
                f'<div class="{"message-box-red" if es_rojo else "message-box"}">'
                f'<div class="{"message-info-red" if es_rojo else "message-info"}">'
                f'{msg.get("HORA")} De: {msg.get("USUARIO")}</div>'
                f'<div class="message-text">{msg.get("TEXTO")}</div></div>', 
                unsafe_allow_html=True
            )
    else:
        st.info("Sin comunicaciones.")

# --- 7. FLUJO POR ROLES ---
# A. ROL:MONITOREO
if st.session_state.rol_sel == "MONITOREO":
    # 1. Definición de pestañas
    t_radar, t_gestion, t_comunicacion, t_pres = st.tabs(["🚨 RADAR S.O.S", "📖 LIBRO DE BASE", "💬 COMUNICACIÓN", "📋 PRESENTISMO"])
    
    # 2. Contenido de pestañas
    with t_radar:
        st.info("📡 Módulo de Radar S.O.S activo")
    
    with t_gestion:
        st.subheader("📖 HISTORIAL DE OPERATIVOS")
        if not df_emergencias.empty: 
            st.dataframe(df_emergencias.iloc[::-1], use_container_width=True)
        else:
            st.info("No hay registros en el historial.")
            
    with t_comunicacion:
        renderizar_comunicaciones()
        
    with t_pres:
        st.subheader("📋 REGISTRO DE PRESENTISMO (TOTAL)")
        df_pres = leer_matriz_nube("PRESENTISMO")
        if not df_pres.empty:
            st.dataframe(df_pres.sort_values(by="FECHA", ascending=False), use_container_width=True)
        else:
            st.info("No hay registros de presentismo.")
# B. ROL: JEFE DE OPERACIONES
elif st.session_state.rol_sel == "JEFE DE OPERACIONES":
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🚨 S.O.S ACTIVOS", "0")
    col2.metric("📡 RED", "OPERATIVA")
    col3.metric("👤 USUARIO", f"{st.session_state.user_sel}")
    col4.metric("🕒 HORA LOCAL", obtener_hora_argentina().split(" ")[1])

    t_crisis, t_ejecucion, t_auditoria = st.tabs(["Centro de Crisis", "Ejecución", "Auditoría"])
    
    with t_crisis:
        st.subheader("📡 RADAR Y LOCALIZACIÓN DE OBJETIVOS")
        df_obj_maps_jefe = df_objetivos.dropna(subset=['LATITUD', 'LONGITUD'])
        centro = [df_obj_maps_jefe['LATITUD'].mean(), df_obj_maps_jefe['LONGITUD'].mean()] if not df_obj_maps_jefe.empty else [-34.6, -58.4]
        m_visor = folium.Map(location=centro, zoom_start=12, tiles="CartoDB dark_matter")
        if not df_obj_maps_jefe.empty:
            for _, r in df_obj_maps_jefe.iterrows():
                folium.Marker([r['LATITUD'], r['LONGITUD']], tooltip=f"OBJETIVO: {r['OBJETIVO']}", icon=folium.Icon(color="blue", icon="shield", prefix="fa")).add_to(m_visor)
        st_folium(m_visor, width="100%", height=500, key="map_jefe_crisis")

    with t_ejecucion:
        st.subheader("🚨 PETICIÓN DE ALTA/BAJA")
        o_accion = st.selectbox("Acción:", ["ALTA", "BAJA"])
        o_cat = st.selectbox("Categoría:", ["OBJETIVO", "MÓVIL", "RECURSO HUMANO"])
        o_det = st.text_input("Nombre / Detalle:")
        if st.button("ELEV AR PETICIÓN"):
            if o_det.strip():
                escribir_registro_nube("PETICIONES", [obtener_hora_argentina(), st.session_state.user_sel, o_accion, o_cat, o_det])
                st.success("✅ Petición Elevada")

    with t_auditoria:
        st.subheader("📋 REPORTE DE MOVIMIENTOS")
        df_novedades = leer_matriz_nube("ACTAS_FLOTAS")
        if not df_novedades.empty:
            st.dataframe(df_novedades.tail(20), use_container_width=True)
  # C. ROL: GERENCIA 
elif st.session_state.rol_sel == "GERENCIA":
    st.markdown('<h2 style="color:#00E5FF;">Comando Estratégico: DIRECCIÓN GENERAL</h2>', unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Ahorro de Riesgo", "$ 1.200.000")
    
    t_com_est, t_ejecucion_ger, t_tab_auditoria = st.tabs(["📩 COMUNICACIÓN ESTRATÉGICA", "🎮 EJECUCIÓN", "📍 TABLERO DE AUDITORÍA"])
    
    with t_com_est:
        st.subheader("Transmitir Directiva")
        g_para = st.selectbox("Para:", ["TODOS"] + LISTA_SUPS_TACTICOS)
        g_orden = st.text_area("Orden:")
        g_prioridad = st.selectbox("Prioridad:", ["VERDE", "AMARILLA", "ROJA"])
        if st.button("Ejecutar Directiva"):
            escribir_registro_nube("CHATS", [obtener_hora_argentina(), st.session_state.user_sel, g_orden, g_prioridad, g_para, "DIRECTIVA"])
            st.success("✅ Transmitido")

    with t_ejecucion_ger:
        st.subheader("Alta/Baja Servicios")
        # (Tu lógica de alta/baja)

    with t_tab_auditoria:
        st.subheader("📡 LOCALIZACIÓN DE OBJETIVOS")
        # (Tu lógica de mapas para gerencia)

elif st.session_state.rol_sel == "ADMINISTRADOR":
    st.markdown('<div class="titulo-seccion-admin">⚙️ NÚCLEO MAESTRO: AION-YAROKU</div>', unsafe_allow_html=True)
    with st.expander("🔐 CREDENCIALES DE INFRAESTRUCTURA", expanded=True):
        u_ing = st.text_input("ADMIN_USER")
        p_ing = st.text_input("ADMIN_PASS", type="password")
    
    st.markdown('<div class="titulo-seccion-admin">⚖️ BUZÓN DE PETICIONES PENDIENTES</div>', unsafe_allow_html=True)
    if u_ing == "admin" and p_ing == "aion2026":
        tipo = st.radio("Alta:", ["SUPERVISOR", "SERVICIO"], horizontal=True)
        nuevo_nombre = st.text_input("Nombre:").upper()
        if st.button("REGISTRAR"):
            escribir_registro_nube("ESTRUCTURA", [obtener_hora_argentina(), tipo, nuevo_nombre, "ACTIVO", st.session_state.user_sel])
            st.success("Alta Exitosa")
