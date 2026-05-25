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
        df['LATITUD'] = pd.to_numeric(df['LATITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        df['LONGITUD'] = pd.to_numeric(df['LONGITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        return df 
    return pd.DataFrame()

# --- FUNCIONES NUEVAS DE MAPA ---
@st.cache_data(ttl=60)
def cargar_comisarias():
    df = leer_matriz_nube("COMISARIAS")
    if not df.empty:
        df.columns = df.columns.str.strip().str.upper()
        for col in ['LATITUD', 'LONGITUD']:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')
        return df.dropna(subset=['LATITUD', 'LONGITUD'])
    return pd.DataFrame()

def buscar_comisaria_mas_cercana(obj_lat, obj_lon, df_comisarias):
    if df_comisarias.empty: return None, 0.0
    distancia_minima = float('inf')
    comisaria_optima = None
    for _, fila in df_comisarias.iterrows():
        lat2, lon2 = fila['LATITUD'], fila['LONGITUD']
        a = math.sin(math.radians(lat2 - obj_lat)/2)**2 + math.cos(math.radians(obj_lat)) * math.cos(math.radians(lat2)) * math.sin(math.radians(lon2 - obj_lon)/2)**2
        distancia = 6371.0 * 2 * math.asin(math.sqrt(a))
        if distancia < distancia_minima:
            distancia_minima = distancia
            comisaria_optima = fila
    return comisaria_optima, distancia_minima

def renderizar_mapa_tactico(df_obj, df_com, objetivo_sel=None):
    m = folium.Map(location=[-34.6, -58.4], zoom_start=11, tiles="CartoDB dark_matter")
    if objetivo_sel:
        fila = df_obj[df_obj['OBJETIVO'] == objetivo_sel]
        if not fila.empty:
            lat_c, lon_c = float(fila['LATITUD'].iloc[0]), float(fila['LONGITUD'].iloc[0])
            com_c, dist = buscar_comisaria_mas_cercana(lat_c, lon_c, df_com)
            folium.Marker([lat_c, lon_c], icon=folium.Icon(color="red", icon="shield")).add_to(m)
            if com_c is not None:
                folium.Marker([com_c['LATITUD'], com_c['LONGITUD']], popup=f"🚔 {com_c['NOMBRE']}", icon=folium.Icon(color="blue")).add_to(m)
                AntPath([[com_c['LATITUD'], com_c['LONGITUD']], [lat_c, lon_c]], color="#FF0000").add_to(m)
                st.warning(f"🚨 RESPUESTA MÁS CERCANA: {com_c['NOMBRE']} a {dist:.2f} km")
    else:
        for _, r in df_obj.dropna(subset=['LATITUD', 'LONGITUD']).iterrows():
            folium.Marker([r['LATITUD'], r['LONGITUD']], tooltip=r['OBJETIVO']).add_to(m)
    st_folium(m, width="100%", height=400)

# --- 4. IDENTIDAD VISUAL ---
def aplicar_identidad_alfa():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@300;500;700&display=swap');
        .stApp { background: radial-gradient(circle at top, #0A0F1E 0%, #030305 100%) !important; color: #E0E0E0; font-family: 'Rajdhani', sans-serif; }
        .estacion-titulo { font-family: 'Orbitron', sans-serif; color: #00E5FF !important; font-size: 24px; margin-top: 15px; display: flex; align-items: center; justify-content: center; text-shadow: 0 0 15px rgba(0, 229, 255, 0.4); text-transform: uppercase; }
        .logo-phoenix { width: 520px !important; border: 2px solid #00e5ff !important; box-shadow: 0 0 35px rgba(0, 229, 255, 0.5) !important; border-radius: 4px !important; }
        </style>
        """, unsafe_allow_html=True)
aplicar_identidad_alfa()

# --- 5. SIDEBAR TÁCTICO ---
df_objetivos = cargar_objetivos()
df_comisarias = cargar_comisarias()

if 'rol_sel' not in st.session_state: st.session_state.rol_sel = "MONITOREO"
with st.sidebar:
    if st.button("🛰️ MONITOREO"): st.session_state.rol_sel = "MONITOREO"; st.rerun()
    if st.button("📋 JEFE DE OPERACIONES"): st.session_state.rol_sel = "JEFE DE OPERACIONES"; st.rerun()
    if st.button("🏢 GERENCIA"): st.session_state.rol_sel = "GERENCIA"; st.rerun()
    if st.button("👮 VIGILADOR"): st.session_state.rol_sel = "VIGILADOR"; st.rerun()

# --- 6. FLUJO POR ROLES ---
if st.session_state.rol_sel == "MONITOREO":
    renderizar_mapa_tactico(df_objetivos, df_comisarias)
    st.tabs(["🚨 RADAR", "📖 LIBRO", "💬 CHAT"])
elif st.session_state.rol_sel == "JEFE DE OPERACIONES":
    t1, t2 = st.tabs(["Mapa", "Acción"])
    with t1: renderizar_mapa_tactico(df_objetivos, df_comisarias)
    with t2:
        o_det = st.text_input("Detalle:")
        if st.button("Enviar"): escribir_registro_nube("PETICIONES", [obtener_hora_argentina(), "JEFE_OPS", "ALTA", "OBJ", o_det])
elif st.session_state.rol_sel == "GERENCIA":
    t1, t2 = st.tabs(["Directivas", "Auditoría"])
    with t1:
        g_ord = st.text_area("Orden:")
        if st.button("Ejecutar"): escribir_registro_nube("CHATS", [obtener_hora_argentina(), "GERENCIA", g_ord, "ROJA", "TODOS", ""])
    with t2: renderizar_mapa_tactico(df_objetivos, df_comisarias)
elif st.session_state.rol_sel == "VIGILADOR":
    st.subheader("TERMINAL VIGILADOR")
