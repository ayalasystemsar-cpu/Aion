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
        df = df[df['OBJETIVO'].astype(str).str.strip() != ""]
        df = df[df['OBJETIVO'].notna()]
        if 'SUPERVISOR' in df.columns:
            df['SUPERVISOR'] = df['SUPERVISOR'].astype(str).str.strip().str.upper()
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
        st.session_state.rol_sel = "MONITOREO"; st.session_state.user_sel = "OPERADOR CENTRAL"; st.session_state.sup_autenticado = False; st.rerun()
    
    # 2. VIGILADOR (NUEVO)
    if st.button("👤 VIGILADOR", use_container_width=True):
        st.session_state.rol_sel = "VIGILADOR"; st.session_state.user_sel = "VIGILADOR"; st.session_state.sup_autenticado = False; st.rerun()
        
    # 3. JEFE DE OPERACIONES
    if st.button("📋 JEFE DE OPERACIONES", use_container_width=True):
        st.session_state.rol_sel = "JEFE DE OPERACIONES"; st.session_state.user_sel = "SANOJA LUIS"; st.session_state.sup_autenticado = False; st.rerun()
        
    # 4. GERENCIA
    if st.button("🏢 GERENCIA", use_container_width=True):
        st.session_state.rol_sel = "GERENCIA"; st.session_state.user_sel = "DIRECCIÓN GENERAL"; st.session_state.sup_autenticado = False; st.rerun()

    # 5. SUPERVISORES
    with st.expander("👤 SUPERVISORES", expanded=(st.session_state.rol_sel == "SUPERVISOR" or 'intentando_sup' in st.session_state)):
        nom_sup = st.selectbox("RESPONSABLE ACTIVO:", LISTA_SUPS_TACTICOS, key="cambio_supervisor_directo")
        user_sup = st.text_input("USUARIO RECURSO (APELLIDO)", key="auth_user_sup")
        pass_sup = st.text_input("CONTRASEÑA CRÍTICA", type="password", key="auth_pass_sup")
        if st.button("AUTENTICAR E INGRESAR", use_container_width=True):
            st.session_state.rol_sel = "SUPERVISOR"; st.session_state.user_sel = nom_sup; st.session_state.sup_autenticado = True; st.rerun()

    # 6. ADMINISTRADOR
    st.markdown("**⚙️ ADMINISTRADOR**")
    if st.button("ACCEDER AL NÚCLEO MAESTRO", use_container_width=True):
        st.session_state.rol_sel = "ADMINISTRADOR"; st.session_state.user_sel = "ADMIN CENTRAL"; st.session_state.sup_autenticado = False; st.rerun()

    st.write("---")
    loc = get_geolocation()
    if st.button("ACTIVAR\nPÁNICO", type="primary"):
        obj_alerta = st.session_state.sup_servicio_actual if st.session_state.rol_sel == "SUPERVISOR" else "CENTRAL BASE"
        escribir_registro_nube("ALERTAS", [obtener_hora_argentina(), st.session_state.user_sel, "PÁNICO", "PENDIENTE", obj_alerta])
        st.error(f"🚨 S.O.S ENVIADO DESDE {obj_alerta}")

# --- 6. CABECERA CENTRAL ---
st.markdown('<div class="contenedor-logo-central"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" class="logo-phoenix"></div>', unsafe_allow_html=True)

# --- 7. FLUJO POR ROLES ---

# A. ROL: VIGILADOR
if st.session_state.rol_sel == "VIGILADOR":
    st.markdown('<div class="estacion-titulo">🛡️ PANEL DE VIGILADOR</div>', unsafe_allow_html=True)
    nombre_v = st.text_input("DNI o Apellido:")
    obj_v = st.selectbox("Objetivo Asignado:", df_objetivos['OBJETIVO'].unique() if not df_objetivos.empty else ["CARGANDO..."])
    st.subheader("📷 Presentismo Facial")
    foto = st.camera_input("Fichar Entrada")
    if foto:
        escribir_registro_nube("PRESENTISMO", [obtener_hora_argentina(), nombre_v, obj_v, "PRESENTE"])
        st.success("¡Presentismo registrado!")
    if st.button("🚨 SOLICITAR CAMBIO DE GUARDIA"):
        sup = df_objetivos[df_objetivos['OBJETIVO'] == obj_v]['SUPERVISOR'].iloc[0] if not df_objetivos.empty else "N/A"
        escribir_registro_nube("NOVEDADES_GUARDIA", [obtener_hora_argentina(), obj_v, nombre_v, "SOLICITUD", sup])
        st.success(f"Solicitud enviada a: {sup}")

# B. ROL: MONITOREO
elif st.session_state.rol_sel == "MONITOREO":
    df_emergencias = leer_matriz_nube("ALERTAS")
    df_comisarias = leer_matriz_nube("COMISARIAS")
    sos_activos = len(df_emergencias[df_emergencias['ESTADO'] == 'PENDIENTE']) if not df_emergencias.empty else 0
    c1, c2, c3 = st.columns(3)
    c1.metric("🚨 S.O.S ACTIVOS", sos_activos)
    c2.metric("📡 RED", "OPERATIVA")
    c3.metric("🕒 HORA LOCAL", obtener_hora_argentina().split(" ")[1])
    # Aquí iría tu lógica original de monitoreo...

# C. ROL: JEFE DE OPERACIONES
elif st.session_state.rol_sel == "JEFE DE OPERACIONES":
    df_obj_maps_jefe = df_objetivos.dropna(subset=['LATITUD', 'LONGITUD'])
    st.markdown('<div class="estacion-titulo">📋 JEFE DE OPERACIONES</div>', unsafe_allow_html=True)
    # Aquí tu lógica de jefe...

# D. ROL: SUPERVISOR
elif st.session_state.rol_sel == "SUPERVISOR":
    t1, t2 = st.tabs(["Control Táctico", "🚨 BANDEJA NOVEDADES GUARDIA"])
    with t2:
        df_ng = leer_matriz_nube("NOVEDADES_GUARDIA")
        if not df_ng.empty:
            df_ng.columns = df_ng.columns.str.strip().str.upper()
            st.dataframe(df_ng[df_ng['SUPERVISOR_ASIGNADO'].str.upper() == st.session_state.user_sel.upper()], use_container_width=True)

# E. ROL: ADMINISTRADOR
elif st.session_state.rol_sel == "ADMINISTRADOR":
    st.markdown('<div class="titulo-seccion-admin">⚙️ NÚCLEO MAESTRO: AION-YAROKU</div>', unsafe_allow_html=True)
    
    with st.expander("🔐 CREDENCIALES DE INFRAESTRUCTURA", expanded=True):
        u_ing = st.text_input("ADMIN_USER")
        p_ing = st.text_input("ADMIN_PASS", type="password")
        
    st.markdown('<div class="titulo-seccion-admin">⚖️ BUZÓN DE PETICIONES PENDIENTES</div>', unsafe_allow_html=True)
    
    if u_ing == "admin" and p_ing == "aion2026":
        st.write("---")
        tipo = st.radio("Alta:", ["SUPERVISOR", "SERVICIO"], horizontal=True)
        nuevo_nombre = st.text_input("Nombre:").upper()
        if st.button("REGISTRAR"):
            escribir_registro_nube("ESTRUCTURA", [obtener_hora_argentina(), tipo, nuevo_nombre, "ACTIVO", st.session_state.user_sel])
            st.success("Alta Exitosa")
