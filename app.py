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

@st.cache_data(ttl=5)
def leer_matriz_nube(pestana):
    gc = conectar_google()
    if gc:
        try:
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
            todas_filas = hoja.get_all_values()
            if not todas_filas or len(todas_filas) == 0: return pd.DataFrame()
            encabezados = [str(h).strip().upper() for h in todas_filas[0]]
            datos_cuerpo = todas_filas[1:]
            if len(datos_cuerpo) == 0: return pd.DataFrame(columns=encabezados)
            return pd.DataFrame(datos_cuerpo, columns=encabezados)
        except Exception as e: return pd.DataFrame()
    return pd.DataFrame()

@st.cache_data(ttl=5)
def cargar_objetivos():
    df = leer_matriz_nube("OBJETIVOS")
    if not df.empty:
        df.columns = df.columns.str.strip().str.upper()
        df = df[df['OBJETIVO'].astype(str).str.strip() != ""]
        df = df[df['OBJETIVO'].notna()]
        if 'SUPERVISOR' in df.columns: df['SUPERVISOR'] = df['SUPERVISOR'].astype(str).str.strip().str.upper()
        df['LATITUD'] = df['LATITUD'].astype(str).str.replace(',', '.')
        df['LONGITUD'] = df['LONGITUD'].astype(str).str.replace(',', '.')
        df['LATITUD'] = pd.to_numeric(df['LATITUD'], errors='coerce')
        df['LONGITUD'] = pd.to_numeric(df['LONGITUD'], errors='coerce')
        df['LATITUD'] = df['LATITUD'].apply(lambda x: -abs(x) if pd.notna(x) else x)
        df['LONGITUD'] = df['LONGITUD'].apply(lambda x: -abs(x) if pd.notna(x) else x)
        return df 
    return pd.DataFrame()

@st.cache_data(ttl=60)
def cargar_comisarias():
    df = leer_matriz_nube("COMISARIAS")
    if not df.empty:
        df.columns = df.columns.str.strip().str.upper()
        if 'NOMBRE' in df.columns:
            df = df[df['NOMBRE'].astype(str).str.strip() != ""]
            df = df[df['NOMBRE'].notna()]
        for col in ['LATITUD', 'LONGITUD']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(',', '.').str.strip()
                df[col] = pd.to_numeric(df[col], errors='coerce')
        if 'LATITUD' in df.columns and 'LONGITUD' in df.columns:
            df['LATITUD'] = df['LATITUD'].apply(lambda x: -abs(x) if pd.notna(x) else x)
            df['LONGITUD'] = df['LONGITUD'].apply(lambda x: -abs(x) if pd.notna(x) else x)
        return df.dropna(subset=['LATITUD', 'LONGITUD'])
    return pd.DataFrame()

def buscar_comisaria_mas_cercana(obj_lat, obj_lon, df_comisarias):
    if df_comisarias.empty: return None, 0.0
    radio_tierra = 6371.0
    comisaria_optima = None
    distancia_minima = float('inf')
    for _, fila in df_comisarias.iterrows():
        lat2, lon2 = fila['LATITUD'], fila['LONGITUD']
        phi1, phi2 = math.radians(obj_lat), math.radians(lat2)
        d_phi = math.radians(lat2 - obj_lat)
        d_lam = math.radians(lon2 - obj_lon)
        a = math.sin(d_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lam/2)**2
        distancia = radio_tierra * 2 * math.asin(math.sqrt(a))
        if distancia < distancia_minima:
            distancia_minima = distancia
            comisaria_optima = fila
    return comisaria_optima, distancia_minima

# --- 4. DISEÑO E IDENTIDAD VISUAL ---
def aplicar_identidad_alfa():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@300;500;700&display=swap');
        .stApp { background: radial-gradient(circle at top, #0A0F1E 0%, #030305 100%) !important; color: #E0E0E0; font-family: 'Rajdhani', sans-serif; }
        .contenedor-logo-central { display: flex; justify-content: center; align-items: center; width: 100%; margin-bottom: 5px; margin-top: 10px; }
        .logo-phoenix { width: 520px !important; border: 2px solid #00e5ff !important; box-shadow: 0 0 35px rgba(0, 229, 255, 0.5) !important; border-radius: 4px !important; background-color: #000 !important; }
        .estacion-titulo { font-family: 'Orbitron', sans-serif; color: #00E5FF !important; font-size: 24px; margin-top: 15px; display: flex; align-items: center; justify-content: center; gap: 12px; text-shadow: 0 0 15px rgba(0, 229, 255, 0.4); letter-spacing: 2px; text-transform: uppercase; }
        .radar-box { border: 1px solid #00e5ff; border-radius: 8px; padding: 5px; background: #000000; box-shadow: 0 0 20px rgba(0, 229, 255, 0.2); }
        .stButton > button[kind="primary"] { background: radial-gradient(circle, #FF0000 0%, #8B0000 100%) !important; color: white !important; border-radius: 50% !important; width: 105px !important; height: 105px !important; border: 3px solid #333 !important; box-shadow: 0 0 25px rgba(255, 0, 0, 0.5) !important; font-family: 'Orbitron', sans-serif; font-size: 11px !important; font-weight: bold; }
        .message-box { border-left: 3px solid #00e5ff; padding-left: 10px; margin-bottom: 15px; background: rgba(255,255,255,0.02); padding-top: 5px; padding-bottom: 5px; }
        .message-box-red { border-left: 3px solid #ff0000; padding-left: 10px; margin-bottom: 15px; background: rgba(255,0,0,0.1); padding-top: 5px; padding-bottom: 5px; }
        .message-info { color: #00e5ff; font-size: 13px; font-weight: bold; font-family: 'Orbitron', sans-serif; }
        .message-text { color: #e0e0e0; font-size: 14px; margin-top: 4px; font-family: 'Rajdhani', sans-serif; }
        .panel-novedad { border: 1px solid #333; border-radius: 8px; padding: 15px; margin-top: 20px; background-color: rgba(10, 10, 11, 0.9); }
        </style>
        """, unsafe_allow_html=True
    )
aplicar_identidad_alfa()

# --- NUEVO GENERADOR DE MAPA ---
def renderizar_mapa_monitoreo(df_obj, df_com):
    st.markdown('<div class="estacion-titulo">🛡️ RADAR TÁCTICO DE RESPUESTA</div>', unsafe_allow_html=True)
    st.markdown("""<style>
        @keyframes pulso-emergencia { 0% { transform: scale(0.9); opacity: 0.6; } 50% { transform: scale(1.3); opacity: 1; } 100% { transform: scale(0.9); opacity: 0.6; } }
        .antipanico-pulso { background-color: #ff0000; border: 2px solid #ffffff; border-radius: 50%; animation: pulso-emergencia 1.2s infinite ease-in-out; }
    </style>""", unsafe_allow_html=True)
    
    lista_nombres_obj = df_obj['OBJETIVO'].tolist() if not df_obj.empty else ["SIN OBJETIVOS"]
    objetivo_critico = st.sidebar.selectbox("SELECCIONAR OBJETIVO EN ALERTA", lista_nombres_obj)
    
    fila_critica = df_obj[df_obj['OBJETIVO'] == objetivo_critico]
    if not fila_critica.empty:
        lat_c, lon_c = float(fila_critica['LATITUD'].values[0]), float(fila_critica['LONGITUD'].values[0])
        com_c, dist = buscar_comisaria_mas_cercana(lat_c, lon_c, df_com)
        m = folium.Map(location=[lat_c, lon_c], zoom_start=14, tiles="CartoDB dark_matter")
        folium.Marker([lat_c, lon_c], icon=folium.DivIcon(html='<div class="antipanico-pulso" style="width:22px; height:22px;"></div>')).add_to(m)
        if com_c is not None:
            folium.Marker([com_c['LATITUD'], com_c['LONGITUD']], popup=f"🚔 {com_c['NOMBRE']}", icon=folium.Icon(color="blue", icon="shield", prefix="fa")).add_to(m)
            AntPath([[com_c['LATITUD'], com_c['LONGITUD']], [lat_c, lon_c]], color="#FF0000", pulse_color="#FFFFFF", weight=6).add_to(m)
            st.markdown(f'<div class="message-box-red"><div class="message-info">🚨 ANTIPÁNICO: {objetivo_critico}</div><div class="message-text">Dependencia: <b>{com_c["NOMBRE"]}</b> a <b>{dist:.2f} km</b>.</div></div>', unsafe_allow_html=True)
        st_folium(m, width="100%", height=500)

# --- 5. SIDEBAR TÁCTICO (EL ORIGINAL) ---
df_objetivos = cargar_objetivos()
df_comisarias = cargar_comisarias()

LISTA_SUPS_TACTICOS = ["AYALA BRIAN", "SUPERVISOR 1", "SUPERVISOR 2", "SUPERVISOR 3", "SUPERVISOR 4", "SUPERVISOR 5", "SUPERVISOR NOCTURNO"]

if 'rol_sel' not in st.session_state: st.session_state.rol_sel = "MONITOREO"
with st.sidebar:
    if st.button("🛰️ MONITOREO"): st.session_state.rol_sel = "MONITOREO"; st.rerun()
    if st.button("📋 JEFE DE OPERACIONES"): st.session_state.rol_sel = "JEFE DE OPERACIONES"; st.rerun()
    if st.button("🏢 GERENCIA"): st.session_state.rol_sel = "GERENCIA"; st.rerun()
    if st.button("👮 VIGILADOR"): st.session_state.rol_sel = "VIGILADOR"; st.rerun()
    if st.button("⚙️ ADMINISTRADOR"): st.session_state.rol_sel = "ADMINISTRADOR"; st.rerun()

# --- 7. FLUJO POR ROLES (MANTIENE TU ESTRUCTURA ORIGINAL) ---
if st.session_state.rol_sel == "MONITOREO":
    renderizar_mapa_monitoreo(df_objetivos, df_comisarias)
    st.tabs(["🚨 RADAR S.O.S", "📖 LIBRO DE BASE", "💬 CHAT OPERATIVO", "📋 PRESENTISMO GENERAL", "👥 PADRÓN VIGILADORES", "🔄 NOVEDADES GUARDIA"])

elif st.session_state.rol_sel == "JEFE DE OPERACIONES":
    t_crisis, t_ejecucion, t_auditoria = st.tabs(["Centro de Crisis", "Ejecución", "Auditoría"])
    with t_crisis: renderizar_mapa_monitoreo(df_objetivos, df_comisarias)
    with t_ejecucion:
        o_det = st.text_input("Nombre / Detalle:")
        if st.button("ELEV AR PETICIÓN"): escribir_registro_nube("PETICIONES", [obtener_hora_argentina(), "JEFE_OPS", "ALTA", "OBJ", o_det]); st.success("✅ Petición Elevada")
    with t_auditoria: st.dataframe(leer_matriz_nube("ACTAS_FLOTAS").tail(20))

elif st.session_state.rol_sel == "GERENCIA":
    t_com_est, t_ejecucion_ger, t_tab_auditoria = st.tabs(["📩 COMUNICACIÓN ESTRATÉGICA", "🎮 EJECUCIÓN", "📍 TABLERO DE AUDITORÍA"])
    with t_com_est:
        g_ord = st.text_area("Orden:")
        if st.button("Ejecutar Directiva"): escribir_registro_nube("CHATS", [obtener_hora_argentina(), "GERENCIA", g_ord, "ROJA", "TODOS", ""])
    with t_tab_auditoria: renderizar_mapa_monitoreo(df_objetivos, df_comisarias)

elif st.session_state.rol_sel == "VIGILADOR":
    st.subheader("📋 FICHAJE Y RELEVO")

elif st.session_state.rol_sel == "ADMINISTRADOR":
    if st.text_input("ADMIN_USER") == "admin" and st.text_input("ADMIN_PASS", type="password") == "aion2026": st.success("Núcleo Maestro desbloqueado.")


