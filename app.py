import streamlit as st
import datetime
from datetime import datetime
import pandas as pd
import pytz
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from streamlit_js_eval import get_geolocation
import folium
from folium.plugins import AntPath
from streamlit_folium import st_folium
import math

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="AION-YAROKU | CORE", page_icon="🛡️", layout="wide", initial_sidebar_state="expanded")

# --- CONEXIONES ---
ID_MAESTRO_DB = "1Md0VkOnwUJWldq0S1fB9UrmOKv4MG__JVG3tQsda0Uw"

def conectar_google():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        return gspread.authorize(creds)
    except: return None

# --- FUNCIONES DE LÓGICA ---
def obtener_hora_argentina():
    tz = pytz.timezone("America/Argentina/Buenos_Aires")
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

def leer_matriz_nube(pestana):
    gc = conectar_google()
    if gc:
        try:
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
            todas_filas = hoja.get_all_values()
            return pd.DataFrame(todas_filas[1:], columns=[str(h).strip().upper() for h in todas_filas[0]]) if todas_filas else pd.DataFrame()
        except: return pd.DataFrame()
    return pd.DataFrame()

def escribir_registro_nube(pestana, datos_fila):
    try:
        gc = conectar_google()
        hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
        hoja.append_row(datos_fila)
        return True
    except: return False

@st.cache_data(ttl=5)
def cargar_objetivos():
    df = leer_matriz_nube("OBJETIVOS")
    if not df.empty:
        df.columns = df.columns.str.strip().str.upper()
        df['LATITUD'] = pd.to_numeric(df['LATITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        df['LONGITUD'] = pd.to_numeric(df['LONGITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        return df 
    return pd.DataFrame()

@st.cache_data(ttl=60)
def cargar_comisarias():
    df = leer_matriz_nube("COMISARIAS")
    if not df.empty:
        df.columns = df.columns.str.strip().str.upper()
        df['LATITUD'] = pd.to_numeric(df['LATITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        df['LONGITUD'] = pd.to_numeric(df['LONGITUD'].astype(str).str.replace(',', '.'), errors='coerce')
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
        if distancia < distancia_minima: distancia_minima, comisaria_optima = distancia, fila
    return comisaria_optima, distancia_minima

def renderizar_mapa_tactico(df_obj, df_com, objetivo_sel=None):
    m = folium.Map(location=[-34.6, -58.4], zoom_start=12, tiles="CartoDB dark_matter")
    if objetivo_sel:
        fila = df_obj[df_obj['OBJETIVO'] == objetivo_sel]
        if not fila.empty:
            lat_c, lon_c = float(fila['LATITUD'].iloc[0]), float(fila['LONGITUD'].iloc[0])
            com_c, dist = buscar_comisaria_mas_cercana(lat_c, lon_c, df_com)
            folium.Marker([lat_c, lon_c], icon=folium.Icon(color="red", icon="shield")).add_to(m)
            if com_c is not None:
                folium.Marker([com_c['LATITUD'], com_c['LONGITUD']], popup=f"🚔 {com_c['NOMBRE']}", icon=folium.Icon(color="blue")).add_to(m)
                AntPath([[com_c['LATITUD'], com_c['LONGITUD']], [lat_c, lon_c]], color="#FF0000").add_to(m)
    else:
        for _, r in df_obj.dropna(subset=['LATITUD', 'LONGITUD']).iterrows():
            folium.Marker([r['LATITUD'], r['LONGITUD']], tooltip=r['OBJETIVO']).add_to(m)
    st_folium(m, width="100%", height=400)

# --- IDENTIDAD VISUAL ---
st.markdown("""<style>.stApp { background: #030305; color: #E0E0E0; font-family: 'Rajdhani'; }</style>""", unsafe_allow_html=True)

# --- SIDEBAR ---
if 'rol_sel' not in st.session_state: st.session_state.rol_sel = "MONITOREO"
with st.sidebar:
    st.button("🛰️ MONITOREO", on_click=lambda: setattr(st.session_state, 'rol_sel', 'MONITOREO'))
    st.button("📋 JEFE OPERACIONES", on_click=lambda: setattr(st.session_state, 'rol_sel', 'JEFE DE OPERACIONES'))
    st.button("🏢 GERENCIA", on_click=lambda: setattr(st.session_state, 'rol_sel', 'GERENCIA'))
    st.button("👮 VIGILADOR", on_click=lambda: setattr(st.session_state, 'rol_sel', 'VIGILADOR'))

df_objs = cargar_objetivos()
df_coms = cargar_comisarias()

# --- FLUJO DE ROLES ---
if st.session_state.rol_sel == "MONITOREO":
    renderizar_mapa_tactico(df_objs, df_coms)
    st.tabs(["🚨 RADAR", "📖 LIBRO", "💬 CHAT"])

elif st.session_state.rol_sel == "JEFE DE OPERACIONES":
    t1, t2, t3 = st.tabs(["Mapa", "Ejecución", "Auditoría"])
    with t1: renderizar_mapa_tactico(df_objs, df_coms)
    with t2: 
        o_det = st.text_input("Detalle:")
        if st.button("Enviar"): escribir_registro_nube("PETICIONES", [obtener_hora_argentina(), "JEFE_OPS", "ALTA", "OBJ", o_det])

elif st.session_state.rol_sel == "GERENCIA":
    st.subheader("DIRECCIÓN GENERAL")
    t1, t2, t3 = st.tabs(["Directivas", "Gestión", "Auditoría"])
    with t1: 
        g_ord = st.text_area("Orden:")
        if st.button("Ejecutar"): escribir_registro_nube("CHATS", [obtener_hora_argentina(), "GERENCIA", g_ord, "ROJA", "TODOS", ""])
    with t3: renderizar_mapa_tactico(df_objs, df_coms)

elif st.session_state.rol_sel == "VIGILADOR":
    st.subheader("TERMINAL VIGILADOR")
