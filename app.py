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

# --- 3. FUNCIONES DE LÓGICA TÁCTICA Y DATOS ---
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

# CÁLCULO DE DISTANCIA (Fórmula Haversine)
def calcular_distancia(lat1, lon1, lat2, lon2):
    rad = math.pi / 180
    dlat = (lat2 - lat1) * rad
    dlon = (lon2 - lon1) * rad
    a = math.sin(dlat/2)**2 + math.cos(lat1*rad) * math.cos(lat2*rad) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return 6371 * c # Resultado en Km

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
        .radar-box { border: 1px solid #1A1A1B; border-radius: 12px; padding: 10px; background: rgba(10, 10, 11, 0.9); }
        .stButton > button[kind="primary"] { 
            background: radial-gradient(circle, #FF0000 0%, #8B0000 100%) !important; 
            color: white !important; border-radius: 50% !important; width: 105px !important; height: 105px !important; 
            border: 3px solid #333 !important; box-shadow: 0 0 25px rgba(255, 0, 0, 0.5) !important; 
            font-family: 'Orbitron', sans-serif; font-size: 11px !important; font-weight: bold;
        }
        </style>
        """, unsafe_allow_html=True
    )

aplicar_identidad_alfa()

# --- 5. CARGA DE BASES OPERATIVAS ---
df_objetivos = leer_matriz_nube("OBJETIVOS")
if not df_objetivos.empty:
    df_objetivos.columns = df_objetivos.columns.str.strip().str.upper()
    df_objetivos['LATITUD'] = pd.to_numeric(df_objetivos['LATITUD'].astype(str).str.replace(',', '.'), errors='coerce')
    df_objetivos['LONGITUD'] = pd.to_numeric(df_objetivos['LONGITUD'].astype(str).str.replace(',', '.'), errors='coerce')

# Base de Comisarías (Asegurate que la pestaña se llame 'COMISARIAS')
df_comisarias = leer_matriz_nube("COMISARIAS")
if not df_comisarias.empty:
    df_comisarias.columns = df_comisarias.columns.str.strip().str.upper()
    df_comisarias['LATITUD'] = pd.to_numeric(df_comisarias['LATITUD'].astype(str).str.replace(',', '.'), errors='coerce')
    df_comisarias['LONGITUD'] = pd.to_numeric(df_comisarias['LONGITUD'].astype(str).str.replace(',', '.'), errors='coerce')

# --- 6. SIDEBAR TÁCTICO ---
if 'rol_sel' not in st.session_state: st.session_state.rol_sel = "MONITOREO"
if 'user_sel' not in st.session_state: st.session_state.user_sel = "BRIAN AYALA"

with st.sidebar:
    st.markdown('<div class="contenedor-logo-sidebar"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" style="width:180px; border:1px solid #00e5ff; border-radius:4px;"></div>', unsafe_allow_html=True)
    st.subheader("🛡️ PANEL DE CONTROL")
    st.session_state.rol_sel = st.selectbox("NIVEL DE ACCESO", ["SUPERVISOR", "MONITOREO", "JEFE DE OPERACIONES", "GERENCIA", "ADMINISTRADOR"])
    st.session_state.user_sel = st.selectbox("IDENTIDAD OPERATIVA", ["BRIAN AYALA", "SANOJA LUIS", "DARÍO CECILIA", "LUIS BONGIORNO", "SERANTES WALTER", "MAZACOTTE CLAUDIO", "SUPERVISOR NOCTURNO"])
    
    st.write("---")
    st.markdown("**🚨 CONFIGURACIÓN DE EMERGENCIA**")
    obj_panico = st.selectbox("🎯 SELECCIONAR OBJETIVO", df_objetivos['OBJETIVO'].unique() if not df_objetivos.empty else ["N/A"])
    sup_panico = st.selectbox("👤 SUPERVISOR DE ZONA", ["BRIAN AYALA", "GONZALO PORZIO", "SUPERVISOR NOCTURNO", "OTRO"])
    
    loc = get_geolocation()
    lat_envio = loc['coords']['latitude'] if loc else 0.0
    lon_envio = loc['coords'].get('longitude', 0.0) if loc else 0.0

    if st.button("ACTIVAR\nPÁNICO", type="primary"):
        carga_sos = f"LAT:{lat_envio}|LON:{lon_envio}|OBJ:{obj_panico}|SUP:{sup_panico}"
        escribir_registro_nube("ALERTAS", [obtener_hora_argentina(), st.session_state.user_sel, "PÁNICO", "PENDIENTE", carga_sos])
        st.error(f"🚨 S.O.S ENVIADO: {obj_panico}")

# --- 7. CABECERA CENTRAL ---
st.markdown('<div class="contenedor-logo-central"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" class="logo-phoenix"></div>', unsafe_allow_html=True)

titulos = {
    "MONITOREO": "🛰️ CENTRAL DE INTELIGENCIA OPERATIVA",
    "SUPERVISOR": f"📱 Estación de Control: {st.session_state.user_sel}",
    "JEFE DE OPERACIONES": "📋 COMANDO DE OPERACIONES TÁCTICAS",
    "GERENCIA": "🏢 DIRECCIÓN Y FISCALIZACIÓN GENERAL",
    "ADMINISTRADOR": "⚙️ NÚCLEO MAESTRO"
}
st.markdown(f'<div class="estacion-titulo">{titulos.get(st.session_state.rol_sel, "SISTEMA TÁCTICO DE COMANDO")}</div>', unsafe_allow_html=True)

# --- 8. FLUJO POR ROLES ---

# A. ROL: MONITOREO (CON INTELIGENCIA DE RUTA)
if st.session_state.rol_sel == "MONITOREO":
    df_emergencias = leer_matriz_nube("ALERTAS")
    sos_activos = len(df_emergencias[df_emergencias['ESTADO'].astype(str).str.upper() == 'PENDIENTE']) if not df_emergencias.empty else 0
    
    c1, c2, c3 = st.columns(3)
    c1.metric("🚨 S.O.S ACTIVOS", sos_activos)
    c2.metric("📡 RED", "OPERATIVA")
    c3.metric("🕒 HORA LOCAL", obtener_hora_argentina().split(" ")[1])

    t_radar, t_gestion = st.tabs(["🚨 RADAR S.O.S", "📖 LIBRO DE BASE"])
    with t_radar:
        lat_foco, lon_foco, obj_en_panico, sup_rep = -34.6, -58.4, "", ""
        comisaria_cercana = None
        
        if sos_activos > 0:
            datos_sos = df_emergencias[df_emergencias['ESTADO'].astype(str).str.upper() == 'PENDIENTE'].iloc[-1]
            try:
                partes = datos_sos.get('CARGA_UTIL', '').split("|")
                obj_en_panico = partes[2].split(":")[1]
                sup_rep = partes[3].split(":")[1]
                
                # Coordenadas del Objetivo en pánico
                target_data = df_objetivos[df_objetivos['OBJETIVO'] == obj_en_panico].iloc[0]
                lat_foco, lon_foco = target_data['LATITUD'], target_data['LONGITUD']
                
                # LÓGICA DE COMISARÍA MÁS CERCANA
                dist_min = float('inf')
                if not df_comisarias.empty:
                    for _, com in df_comisarias.iterrows():
                        d = calcular_distancia(lat_foco, lon_foco, com['LATITUD'], com['LONGITUD'])
                        if d < dist_min:
                            dist_min = d
                            comisaria_cercana = com
                
                st.error(f"🚨 EMERGENCIA: {datos_sos['USUARIO']} | 🎯 {obj_en_panico} | 👤 SUP: {sup_rep}")
                if comisaria_cercana is not None:
                    st.warning(f"🚓 SOPORTE: {comisaria_cercana['NOMBRE']} a {dist_min:.2f} Km")
            except: pass
        else:
            st.success("✅ Vigilancia Pasiva - Radar Operativo")

        st.markdown('<div class="radar-box">', unsafe_allow_html=True)
        m_mon = folium.Map(location=[lat_foco, lon_foco], zoom_start=14, tiles="CartoDB dark_matter")
        
        for _, r in df_objetivos.iterrows():
            es_alerta = (r['OBJETIVO'] == obj_en_panico)
            color_m = "red" if es_alerta else "blue"
            folium.Marker(
                [r['LATITUD'], r['LONGITUD']], 
                tooltip=f"OBJETIVO: {r['OBJETIVO']} | SUPERVISOR: {sup_rep if es_alerta else r.get('SUPERVISOR', 'N/A')}", 
                icon=folium.Icon(color=color_m, icon="shield", prefix="fa")
            ).add_to(m_mon)
            
        # TRAZADO DE RUTA TÁCTICA
        if sos_activos > 0 and comisaria_cercana is not None:
            # Marcador de Comisaría
            folium.Marker(
                [comisaria_cercana['LATITUD'], comisaria_cercana['LONGITUD']],
                tooltip=f"COMISARÍA: {comisaria_cercana['NOMBRE']}",
                icon=folium.Icon(color="darkblue", icon="balance-scale", prefix="fa")
            ).add_to(m_mon)
            
            # Línea de ruta animada
            AntPath(
                locations=[[comisaria_cercana['LATITUD'], comisaria_cercana['LONGITUD']], [lat_foco, lon_foco]],
                color='#00E5FF', weight=5, opacity=0.8, delay=1000
            ).add_to(m_mon)

        st_folium(m_mon, width="100%", height=450, key="map_mon_intel")
        st.markdown('</div>', unsafe_allow_html=True)

        if sos_activos > 0:
            st.subheader("📝 PROTOCOLO DE CIERRE")
            inf_neu = st.text_area("INFORME DE NEUTRALIZACIÓN")
            if st.button("FINALIZAR OPERATIVO", use_container_width=True):
                if inf_neu.strip():
                    fila = df_emergencias[df_emergencias['ESTADO'].astype(str).str.upper() == 'PENDIENTE'].index[-1] + 2
                    actualizar_celda("ALERTAS", fila, "D", "RESUELTO")
                    actualizar_celda("ALERTAS", fila, "F", inf_neu)
                    st.rerun()

    with t_gestion:
        if not df_emergencias.empty: st.dataframe(df_emergencias.iloc[::-1], use_container_width=True)

# B. ROL: SUPERVISOR, JEFE DE OPERACIONES Y GERENCIA
elif st.session_state.rol_sel in ["SUPERVISOR", "JEFE DE OPERACIONES", "GERENCIA"]:
    st.markdown('<div class="radar-box">', unsafe_allow_html=True)
    m_visor = folium.Map(location=[-34.6, -58.4], zoom_start=12, tiles="CartoDB dark_matter")
    for _, r in df_objetivos.iterrows():
        folium.Marker([r['LATITUD'], r['LONGITUD']], tooltip=r['OBJETIVO'], icon=folium.Icon(color="blue", icon="shield", prefix="fa")).add_to(m_visor)
    st_folium(m_visor, width="100%", height=500, key=f"map_fiscal_{st.session_state.rol_sel}")
    st.markdown('</div>', unsafe_allow_html=True)
