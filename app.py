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

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="AION-YAROKU | CORE", page_icon="🛡️", layout="wide", initial_sidebar_state="expanded")

# --- 2. CONEXIONES ---
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
        df = df[df['OBJETIVO'].astype(str).str.strip() != ""]
        df['LATITUD'] = pd.to_numeric(df['LATITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        df['LONGITUD'] = pd.to_numeric(df['LONGITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        df['LATITUD'] = df['LATITUD'].apply(lambda x: -abs(x) if pd.notna(x) else x)
        df['LONGITUD'] = df['LONGITUD'].apply(lambda x: -abs(x) if pd.notna(x) else x)
        return df 
    return pd.DataFrame()

@st.cache_data(ttl=60)
def cargar_comisarias():
    df = leer_matriz_nube("COMISARIAS")
    if not df.empty:
        df.columns = df.columns.str.strip().str.upper()
        for col in ['LATITUD', 'LONGITUD']:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')
        df['LATITUD'] = df['LATITUD'].apply(lambda x: -abs(x) if pd.notna(x) else x)
        df['LONGITUD'] = df['LONGITUD'].apply(lambda x: -abs(x) if pd.notna(x) else x)
        return df.dropna(subset=['LATITUD', 'LONGITUD'])
    return pd.DataFrame()

def buscar_comisaria_mas_cercana(obj_lat, obj_lon, df_comisarias):
    if df_comisarias.empty: return None, 0.0
    distancia_minima, comisaria_optima = float('inf'), None
    for _, fila in df_comisarias.iterrows():
        lat2, lon2 = fila['LATITUD'], fila['LONGITUD']
        a = math.sin(math.radians(lat2 - obj_lat)/2)**2 + math.cos(math.radians(obj_lat)) * math.cos(math.radians(lat2)) * math.sin(math.radians(lon2 - obj_lon)/2)**2
        distancia = 6371.0 * 2 * math.asin(math.sqrt(a))
        if distancia < distancia_minima: distancia_minima, comisaria_optima = distancia, fila
    return comisaria_optima, distancia_minima

# --- 4. IDENTIDAD VISUAL ---
def aplicar_identidad_alfa():
    st.markdown("""
        <style>
        .stApp { background: #030305; color: #E0E0E0; font-family: 'Rajdhani', sans-serif; }
        .estacion-titulo { font-family: 'Orbitron', sans-serif; color: #00E5FF; font-size: 24px; text-align: center; margin-bottom: 20px; }
        .radar-box { border: 1px solid #00e5ff; padding: 10px; background: #000; }
        .message-box-red { border-left: 3px solid #ff0000; padding: 10px; background: rgba(255,0,0,0.1); margin: 10px 0; }
        .panel-novedad { border: 1px solid #333; padding: 15px; border-radius: 8px; background: rgba(10, 10, 11, 0.9); }
        </style>
        """, unsafe_allow_html=True)

aplicar_identidad_alfa()

# --- 5. RENDERIZADO MAPA MONITOREO ---
def renderizar_mapa_monitoreo(df_obj, df_com):
    st.markdown('<div class="estacion-titulo">🛡️ ESTACIÓN CENTRAL DE MONITOREO 🚨</div>', unsafe_allow_html=True)
    obj_critico = st.sidebar.selectbox("SELECCIONAR OBJETIVO", df_obj['OBJETIVO'].tolist() if not df_obj.empty else ["SIN OBJETIVOS"])
    fila = df_obj[df_obj['OBJETIVO'] == obj_critico]
    if not fila.empty:
        lat_c, lon_c = float(fila['LATITUD'].iloc[0]), float(fila['LONGITUD'].iloc[0])
        com_c, dist = buscar_comisaria_mas_cercana(lat_c, lon_c, df_com)
        m = folium.Map(location=[lat_c, lon_c], zoom_start=14, tiles="CartoDB dark_matter")
        folium.Marker([lat_c, lon_c], icon=folium.Icon(color="red", icon="exclamation-triangle")).add_to(m)
        if com_c is not None:
            folium.Marker([com_c['LATITUD'], com_c['LONGITUD']], popup=f"🚔 {com_c['NOMBRE']}", icon=folium.Icon(color="blue")).add_to(m)
            AntPath([[com_c['LATITUD'], com_c['LONGITUD']], [lat_c, lon_c]], color="#FF0000").add_to(m)
            st.markdown(f'<div class="message-box-red">🚨 ALERTA: <b>{obj_critico}</b> | Dep: <b>{com_c["NOMBRE"]}</b> ({dist:.2f} km)</div>', unsafe_allow_html=True)
        st_folium(m, width="100%", height=400)

# --- 6. FLUJO PRINCIPAL ---
LISTA_SUPS_TACTICOS = ["AYALA BRIAN", "SUPERVISOR 1", "SUPERVISOR 2"]
if 'rol_sel' not in st.session_state: st.session_state.rol_sel = "MONITOREO"
if 'user_sel' not in st.session_state: st.session_state.user_sel = "OPERADOR CENTRAL"

df_objetivos = cargar_objetivos()
df_comisarias = cargar_comisarias()

if st.session_state.rol_sel == "MONITOREO":
    renderizar_mapa_monitoreo(df_objetivos, df_comisarias)

elif st.session_state.rol_sel == "JEFE DE OPERACIONES":
    t_crisis, t_ejecucion, t_auditoria = st.tabs(["Centro de Crisis", "Ejecución", "Auditoría"])
    with t_crisis: renderizar_mapa_monitoreo(df_objetivos, df_comisarias)
    with t_ejecucion:
        st.markdown('<div class="panel-novedad">', unsafe_allow_html=True)
        o_accion = st.selectbox("Acción:", ["ALTA", "BAJA"])
        o_cat = st.selectbox("Categoría:", ["OBJETIVO", "MÓVIL"])
        o_det = st.text_input("Detalle:")
        if st.button("ELEV AR PETICIÓN") and o_det.strip():
            escribir_registro_nube("PETICIONES", [obtener_hora_argentina(), st.session_state.user_sel, o_accion, o_cat, o_det])
            st.success("✅ Petición Elevada")
        st.markdown('</div>', unsafe_allow_html=True)
    with t_auditoria:
        st.subheader("📋 REPORTE DE MOVIMIENTOS")
        df_n = leer_matriz_nube("ACTAS_FLOTAS")
        if not df_n.empty: st.dataframe(df_n.tail(20), use_container_width=True)

elif st.session_state.rol_sel == "GERENCIA":
    st.markdown('<h2 style="color:#00E5FF;">Comando Estratégico: DIRECCIÓN GENERAL</h2>', unsafe_allow_html=True)
    t_com_est, t_ejecucion_ger, t_tab_auditoria = st.tabs(["📩 COMUNICACIÓN ESTRATÉGICA", "🎮 EJECUCIÓN", "📍 TABLERO DE AUDITORÍA"])
    with t_com_est:
        st.markdown('<div class="panel-novedad">', unsafe_allow_html=True)
        g_para = st.selectbox("Para:", ["TODOS"] + LISTA_SUPS_TACTICOS)
        g_asunto = st.text_input("Asunto:")
        g_orden = st.text_area("Orden:")
        g_prioridad = st.selectbox("Prioridad:", ["VERDE", "AMARILLA", "ROJA"])
        if st.button("Ejecutar Directiva"):
            escribir_registro_nube("CHATS", [obtener_hora_argentina(), st.session_state.user_sel, g_orden, g_prioridad, g_para, g_asunto])
            st.success("✅ Directiva Transmitida")
        st.markdown('</div>', unsafe_allow_html=True)
    with t_ejecucion_ger:
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.markdown('<div class="panel-novedad">', unsafe_allow_html=True)
            g_alta_nom = st.text_input("Nombre:")
            g_alta_asig = st.selectbox("Asignar a:", LISTA_SUPS_TACTICOS)
            if st.button("Solicitar Alta"):
                escribir_registro_nube("PETICIONES", [obtener_hora_argentina(), st.session_state.user_sel, "ALTA", "OBJETIVO", f"{g_alta_nom} | ASIG: {g_alta_asig}"])
                st.success("✅ Petición enviada")
            st.markdown('</div>', unsafe_allow_html=True)
        with col_g2:
            st.markdown('<div class="panel-novedad">', unsafe_allow_html=True)
            opciones_baja = df_objetivos['OBJETIVO'].unique() if not df_objetivos.empty else ["ALFAVINIL"]
            g_baja_obj = st.selectbox("Objetivo:", opciones_baja)
            if st.button("Solicitar Baja"):
                escribir_registro_nube("PETICIONES", [obtener_hora_argentina(), st.session_state.user_sel, "BAJA", "OBJETIVO", g_baja_obj])
                st.success("✅ Petición enviada")
            st.markdown('</div>', unsafe_allow_html=True)
    with t_tab_auditoria:
        m_v = folium.Map(location=[-34.6, -58.4], zoom_start=11, tiles="CartoDB dark_matter")
        for _, r in df_objetivos.dropna(subset=['LATITUD', 'LONGITUD']).iterrows():
            folium.Marker([r['LATITUD'], r['LONGITUD']], tooltip=r['OBJETIVO']).add_to(m_v)
        st_folium(m_v, width="100%", height=450)

elif st.session_state.rol_sel == "ADMINISTRADOR":
    if st.text_input("ADMIN_USER") == "admin" and st.text_input("ADMIN_PASS", type="password") == "aion2026":
        st.success("Núcleo Maestro desbloqueado.")
