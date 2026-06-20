import streamlit as st
import datetime
from datetime import datetime
import pandas as pd
import pytz
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from streamlit_js_eval import get_geolocation
import osmnx as ox
import networkx as nx
import folium
from folium.plugins import AntPath
from streamlit_folium import st_folium
import math
import requests
from branca.element import Element

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
        
def obtener_ruta_calles_osrm(lat1, lon1, lat2, lon2):
    try:
        url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=full&geometries=geojson"
        response = requests.get(url, timeout=5).json()
        if response.get("code") == "Ok":
            coordenadas = response["routes"][0]["geometry"]["coordinates"]
            return [[point[1], point[0]] for point in coordenadas]
    except: pass
    return [[lat1, lon1], [lat2, lon2]]

@st.cache_data(ttl=60) 
def leer_matriz_nube(pestana):
    gc = conectar_google()
    if gc:
        try:
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
            todas_filas = hoja.get_all_values()
            if not todas_filas: return pd.DataFrame()
            encabezados = [str(h).strip().upper() for h in todas_filas[0]]
            datos_cuerpo = todas_filas[1:]
            return pd.DataFrame(datos_cuerpo, columns=encabezados) if datos_cuerpo else pd.DataFrame(columns=encabezados)
        except: return pd.DataFrame()
    return pd.DataFrame()

@st.cache_data(ttl=60)
def cargar_objetivos():
    df = leer_matriz_nube("OBJETIVOS")
    if not df.empty:
        df.columns = df.columns.str.strip().str.upper()
        df['LATITUD'] = pd.to_numeric(df['LATITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        df['LONGITUD'] = pd.to_numeric(df['LONGITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        return df 
    return pd.DataFrame()

# --- 4. DISEÑO E IDENTIDAD VISUAL ---
def aplicar_identidad_alfa():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@300;500;700&display=swap');
        .stApp { background: radial-gradient(circle at top, #0A0F1E 0%, #030305 100%) !important; color: #E0E0E0; font-family: 'Rajdhani', sans-serif; }
        .estacion-titulo { font-family: 'Orbitron', sans-serif; color: #00E5FF !important; font-size: 24px; margin-top: 15px; display: flex; align-items: center; justify-content: center; gap: 12px; text-shadow: 0 0 15px rgba(0, 229, 255, 0.4); letter-spacing: 2px; text-transform: uppercase; }
        .radar-box { border: 1px solid #00e5ff; border-radius: 8px; padding: 5px; background: #000000; box-shadow: 0 0 20px rgba(0, 229, 255, 0.2); }
        .panel-novedad { border: 1px solid #333; border-radius: 8px; padding: 15px; margin-top: 20px; background-color: rgba(10, 10, 11, 0.9); }
        .btn-google-maps { display: inline-flex; align-items: center; justify-content: center; background-color: #ffffff !important; color: #1a73e8 !important; font-family: 'Orbitron', sans-serif; font-weight: bold; font-size: 14px; padding: 12px 24px; border-radius: 6px; border: 2px solid #1a73e8; text-decoration: none !important; width: 100%; text-align: center; margin-top: 10px; }
        </style>
        """, unsafe_allow_html=True)
aplicar_identidad_alfa()

# --- 5. SIDEBAR Y ESTADO ---
df_objetivos = cargar_objetivos()
if 'rol_sel' not in st.session_state: st.session_state.rol_sel = "MONITOREO"

with st.sidebar:
    st.markdown('<div class="contenedor-logo-sidebar"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" style="width:180px; border:1px solid #00e5ff; border-radius:4px;"></div>', unsafe_allow_html=True)
    if st.button("🛰️ MONITOREO"): st.session_state.rol_sel = "MONITOREO"; st.rerun()
    if st.button("📋 JEFE DE OPERACIONES"): st.session_state.rol_sel = "JEFE DE OPERACIONES"; st.rerun()
    if st.button("🏢 GERENCIA"): st.session_state.rol_sel = "GERENCIA"; st.rerun()

# --- ROL: JEFE DE OPERACIONES (CONSOLA TÁCTICA) ---
if st.session_state.rol_sel == "JEFE DE OPERACIONES":
    st.markdown('<div class="estacion-titulo">📋 COMANDO DE OPERACIONES TÁCTICAS</div>', unsafe_allow_html=True)
    
    t_crisis, t_ejecucion, t_auditoria = st.tabs(["Centro de Crisis", "Ejecución", "Auditoría"])
    
    with t_crisis:
        st.subheader("📡 RADAR Y AUDITORÍA INTERACTIVA DE SERVICIOS")
        m_visor = folium.Map(location=[-34.6, -58.4], zoom_start=12, tiles="CartoDB dark_matter")
        for _, r in df_objetivos.dropna(subset=['LATITUD', 'LONGITUD']).iterrows():
            folium.Marker([r['LATITUD'], r['LONGITUD']], popup=r['OBJETIVO'], tooltip=f"Clic para auditar: {r['OBJETIVO']}", icon=folium.Icon(color="cadetblue", icon="shield", prefix="fa")).add_to(m_visor)
        
        mapa_retorno = st_folium(m_visor, width="100%", height=500, key="map_jefe")
        
        obj_click = mapa_retorno.get("last_object_clicked_popup", "").strip().upper() if mapa_retorno else None
        
        if obj_click:
            st.markdown(f"### 📊 CONSOLA TÁCTICA: {obj_click}")
            sup_resp = df_objetivos[df_objetivos['OBJETIVO'] == obj_click]['SUPERVISOR'].iloc[0] if not df_objetivos[df_objetivos['OBJETIVO'] == obj_click].empty else "N/A"
            
            pan1, pan2 = st.columns([1, 2])
            with pan1:
                st.markdown('<div class="panel-novedad">', unsafe_allow_html=True)
                # CÓDIGO CORREGIDO CON COMILLAS DOBLES \"
                st.markdown(f"**👤 SUPERVISOR RESPONSABLE:**<br><span style=\"color:#00E5FF; font-family:'Orbitron'; font-size:16px;\">{sup_resp}</span>", unsafe_allow_html=True)
                st.write("---")
                df_rel = leer_matriz_nube("VIGILADORES")
                if not df_rel.empty:
                    df_rel.columns = df_rel.columns.str.strip().str.upper()
                    df_rel_obj = df_rel[df_rel['OBJETIVO'] == obj_click]
                    if not df_rel_obj.empty:
                        rel = df_rel_obj.iloc[-1]
                        st.write(f"🛑 Sale: {rel.get('VIGILADOR_SALIENTE')}")
                        st.write(f"🟢 Entra: {rel.get('VIGILADOR_ENTRANTE')}")
                st.markdown('</div>', unsafe_allow_html=True)
            with pan2:
                st.markdown('<div class="panel-novedad">', unsafe_allow_html=True)
                st.markdown("**🔄 HISTORIAL RECIENTE:**", unsafe_allow_html=True)
                df_nov = leer_matriz_nube("NOVEDADES_GUARDIA")
                if not df_nov.empty:
                    df_nov.columns = df_nov.columns.str.strip().str.upper()
                    st.dataframe(df_nov[df_nov['OBJETIVO'] == obj_click].tail(5), use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
    
    with t_ejecucion:
        st.markdown('<div class="panel-novedad">', unsafe_allow_html=True)
        if st.button("ELEVAR PETICIÓN"): escribir_registro_nube("PETICIONES", [obtener_hora_argentina(), "JEFE", "PETICION", "GENERAL", "NUEVA"])
        st.markdown('</div>', unsafe_allow_html=True)

# (Continuación de otros roles omitida por espacio, mantiene la estructura original)
with t_ejecucion_ger:
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.markdown('<div class="panel-novedad">', unsafe_allow_html=True)
            g_alta_nom = st.text_input("Nombre:", key="ger_alta_nom")
            g_alta_asig = st.selectbox("Asignar a:", LISTA_SUPS_TACTICOS, key="ger_alta_asig")
            if st.button("Solicitar Alta"):
                escribir_registro_nube("PETICIONES", [obtener_hora_argentina(), st.session_state.user_sel, "ALTA", "OBJETIVO", f"{g_alta_nom} | ASIG: {g_alta_asig}"])
                st.success("✅ Petición enviada")
            st.markdown('</div>', unsafe_allow_html=True)
        with col_g2:
            st.markdown('<div class="panel-novedad">', unsafe_allow_html=True)
            opciones_baja = df_objetivos['OBJETIVO'].unique() if not df_objetivos.empty else ["ALFAVINIL"]
            g_baja_obj = st.selectbox("Objetivo:", opciones_baja, key="ger_baja_obj")
            if st.button("Solicitar Baja"):
                escribir_registro_nube("PETICIONES", [obtener_hora_argentina(), st.session_state.user_sel, "BAJA", "OBJETIVO", g_baja_obj])
                st.success("✅ Petición enviada")
            st.markdown('</div>', unsafe_allow_html=True)

    with t_tab_auditoria:
        df_ger_maps = df_objetivos.dropna(subset=['LATITUD', 'LONGITUD'])
        centro = [df_ger_maps['LATITUD'].mean(), df_ger_maps['LONGITUD'].mean()] if not df_ger_maps.empty else [-34.6, -58.4]
        m_visor = folium.Map(location=centro, zoom_start=12, tiles="CartoDB dark_matter")
        for _, r in df_ger_maps.iterrows():
            folium.Marker([r['LATITUD'], r['LONGITUD']], tooltip=r['OBJETIVO'], icon=folium.Icon(color="blue", icon="shield", prefix="fa")).add_to(m_visor)
        st_folium(m_visor, width="100%", height=450, key="map_gerencia")

elif st.session_state.rol_sel == "ADMINISTRADOR":
    u_ing = st.text_input("ADMIN_USER")
    p_ing = st.text_input("ADMIN_PASS", type="password")
    if u_ing == "admin" and p_ing == "aion2026": 
        st.success("Núcleo Maestro desbloqueado.")
