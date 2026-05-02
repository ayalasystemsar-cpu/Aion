# --- 1. CONFIGURACIÓN E IDENTIDAD VISUAL CORPORATIVA (AION-YAROKU CORE) ---
import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
from folium.plugins import AntPath  # DIBUJA LA RUTA ANIMADA
from datetime import datetime
import pytz
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from streamlit_js_eval import get_geolocation
import math # PARA CÁLCULO DE DISTANCIAS

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

def calcular_distancia(lat1, lon1, lat2, lon2):
    try:
        rad = math.pi / 180
        l1, n1 = float(str(lat1).replace(',','.')), float(str(lon1).replace(',','.'))
        l2, n2 = float(str(lat2).replace(',','.')), float(str(lon2).replace(',','.'))
        dlat, dlon = (l2 - l1) * rad, (n2 - n1) * rad
        a = math.sin(dlat/2)**2 + math.cos(l1*rad) * math.cos(l2*rad) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return 6371 * c # Retorna Km
    except: return 999.0

def escribir_registro_nube(pestana, datos_fila):
    try:
        gc = conectar_google()
        if gc:
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
            hoja.append_row(datos_fila)
            return True
    except: return False

def actualizar_celda(pestana, fila, columna, valor):
    try:
        gc = conectar_google()
        if gc:
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
            hoja.update_acell(f"{columna}{fila}", valor)
            return True
    except: return False

@st.cache_data(ttl=10) # Reducido para mayor frescura
def leer_matriz_nube(pestana):
    gc = conectar_google()
    if gc:
        try:
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
            df = pd.DataFrame(hoja.get_all_records())
            df.columns = df.columns.str.strip().str.upper()
            return df
        except: return pd.DataFrame()
    return pd.DataFrame()

# --- 4. DISEÑO E IDENTIDAD VISUAL ---
def aplicar_identidad_alfa():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@300;500;700&display=swap');
        .stApp { background: radial-gradient(circle at top, #0A0F1E 0%, #030305 100%) !important; color: #E0E0E0; font-family: 'Rajdhani', sans-serif; }
        .contenedor-logo-central { display: flex; justify-content: center; align-items: center; width: 100%; margin-bottom: 5px; margin-top: 10px; }
        .logo-phoenix { width: 520px !important; border: 2px solid #00e5ff !important; box-shadow: 0 0 35px rgba(0, 229, 255, 0.5) !important; border-radius: 4px !important; }
        .estacion-titulo { font-family: 'Orbitron', sans-serif; color: #00E5FF !important; font-size: 24px; text-align: center; text-shadow: 0 0 15px rgba(0, 229, 255, 0.4); text-transform: uppercase; margin-top: 15px; }
        
        /* EFECTO TITILANTE PARA ALERTA */
        @keyframes blinker { 50% { opacity: 0; } }
        .emergency-active { color: #FF0000; font-weight: bold; animation: blinker 1s linear infinite; }
        
        .radar-box { border: 1px solid #1A1A1B; border-radius: 12px; padding: 10px; background: rgba(10, 10, 11, 0.9); }
        .stButton > button[kind="primary"] { 
            background: radial-gradient(circle, #FF0000 0%, #8B0000 100%) !important; 
            color: white !important; border-radius: 50% !important; width: 105px !important; height: 105px !important; 
            border: 3px solid #333 !important; box-shadow: 0 0 25px rgba(255, 0, 0, 0.5) !important; font-family: 'Orbitron', sans-serif;
        }
        </style>
        """, unsafe_allow_html=True
    )

aplicar_identidad_alfa()

# --- 5. CARGA DE DATOS ---
df_objetivos = leer_matriz_nube("OBJETIVOS")
df_comisarias = leer_matriz_nube("COMISARIAS")

# --- 6. SIDEBAR TÁCTICO ---
if 'rol_sel' not in st.session_state: st.session_state.rol_sel = "MONITOREO"
if 'user_sel' not in st.session_state: st.session_state.user_sel = "BRIAN AYALA"

with st.sidebar:
    st.markdown('<img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" style="width:180px; border:1px solid #00e5ff; border-radius:4px;">', unsafe_allow_html=True)
    st.session_state.rol_sel = st.selectbox("NIVEL DE ACCESO", ["MONITOREO", "SUPERVISOR", "JEFE DE OPERACIONES", "GERENCIA", "ADMINISTRADOR"])
    st.session_state.user_sel = st.selectbox("IDENTIDAD OPERATIVA", ["BRIAN AYALA", "SANOJA LUIS", "DARÍO CECILIA", "LUIS BONGIORNO", "SERANTES WALTER", "MAZACOTTE CLAUDIO", "SUPERVISOR NOCTURNO"])
    st.write("---")
    
    if not df_objetivos.empty:
        obj_panico = st.selectbox("🎯 OBJETIVO", df_objetivos['OBJETIVO'].unique())
        sup_panico = st.selectbox("👤 SUPERVISOR", ["BRIAN AYALA", "GONZALO PORZIO", "SUPERVISOR NOCTURNO", "OTRO"])
        
        loc = get_geolocation()
        lat_envio = loc['coords']['latitude'] if loc else 0.0
        lon_envio = loc['coords'].get('longitude', 0.0) if loc else 0.0

        if st.button("ACTIVAR\nPÁNICO", type="primary"):
            carga_sos = f"LAT:{lat_envio}|LON:{lon_envio}|OBJ:{obj_panico}|SUP:{sup_panico}"
            # REGISTRO ÚNICO
            escribir_registro_nube("ALERTAS", [obtener_hora_argentina(), st.session_state.user_sel, "PÁNICO", "PENDIENTE", carga_sos])
            st.rerun() # LIMPIA EL BUFFER PARA EVITAR DUPLICADOS

# --- 7. CABECERA ---
st.markdown('<div class="contenedor-logo-central"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" class="logo-phoenix"></div>', unsafe_allow_html=True)

# --- 8. FLUJO POR ROLES ---

if st.session_state.rol_sel == "MONITOREO":
    df_emergencias = leer_matriz_nube("ALERTAS")
    # FILTRO ESTRICTO PARA EVITAR MÚLTIPLES ALERTAS VISUALES
    pendientes = df_emergencias[df_emergencias['ESTADO'].astype(str).str.upper() == 'PENDIENTE']
    sos_activos = len(pendientes)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("🚨 S.O.S ACTIVOS", sos_activos)
    c2.metric("📡 RED", "OPERATIVA")
    c3.metric("🕒 HORA LOCAL", obtener_hora_argentina().split(" ")[1])

    t_radar, t_gestion = st.tabs(["🚨 RADAR S.O.S", "📖 LIBRO DE BASE"])
    with t_radar:
        lat_foco, lon_foco, obj_en_panico, sup_rep = -34.6, -58.4, "", ""
        comisaria_cercana = None
        
        if sos_activos > 0:
            # TOMAMOS SOLO LA ÚLTIMA ALERTA ACTIVA
            datos_sos = pendientes.iloc[-1]
            try:
                partes = datos_sos.get('CARGA_UTIL', '').split("|")
                obj_en_panico = partes[2].split(":")[1]
                sup_rep = partes[3].split(":")[1]
                
                target_data = df_objetivos[df_objetivos['OBJETIVO'] == obj_en_panico].iloc[0]
                lat_foco = float(str(target_data['LATITUD']).replace(',','.'))
                lon_foco = float(str(target_data['LONGITUD']).replace(',','.'))
                
                # CÁLCULO DE RESPUESTA POLICIAL
                if not df_comisarias.empty:
                    dist_min = 999.0
                    for _, com in df_comisarias.iterrows():
                        d = calcular_distancia(lat_foco, lon_foco, com['LATITUD'], com['LONGITUD'])
                        if d < dist_min:
                            dist_min = d
                            comisaria_cercana = com
                
                st.markdown(f'<div class="emergency-active">🚨 EMERGENCIA: {datos_sos["USUARIO"]} | 🎯 {obj_en_panico}</div>', unsafe_allow_html=True)
                if comisaria_cercana is not None:
                    st.warning(f"🚓 APOYO MÁS CERCANO: {comisaria_cercana['NOMBRE']} ({dist_min:.2f} Km)")
            except: pass
        else:
            st.success("✅ Vigilancia Pasiva - Radar Operativo")

        st.markdown('<div class="radar-box">', unsafe_allow_html=True)
        m_mon = folium.Map(location=[lat_foco, lon_foco], zoom_start=14, tiles="CartoDB dark_matter")
        
        # DIBUJAR TODOS LOS OBJETIVOS
        for _, r in df_objetivos.iterrows():
            es_sos = (r['OBJETIVO'] == obj_en_panico)
            color_m = "red" if es_sos else "blue"
            # SI ES SOS, EL ICONO TIENE UN Tooltip especial
            folium.Marker(
                [float(str(r['LATITUD']).replace(',','.')), float(str(r['LONGITUD']).replace(',','.'))], 
                tooltip=f"OBJ: {r['OBJETIVO']}", 
                icon=folium.Icon(color=color_m, icon="shield", prefix="fa")
            ).add_to(m_mon)
            
        # DIBUJAR COMISARÍA Y RUTA (ANT-PATH)
        if sos_activos > 0 and comisaria_cercana is not None:
            c_lat = float(str(comisaria_cercana['LATITUD']).replace(',','.'))
            c_lon = float(str(comisaria_cercana['LONGITUD']).replace(',','.'))
            
            folium.Marker(
                [c_lat, c_lon],
                tooltip=f"COMISARÍA: {comisaria_cercana['NOMBRE']}",
                icon=folium.Icon(color="darkblue", icon="balance-scale", prefix="fa")
            ).add_to(m_mon)
            
            # RUTA ANIMADA CIAN
            AntPath(
                locations=[[c_lat, c_lon], [lat_foco, lon_foco]],
                color='#00E5FF', weight=5, opacity=0.8, delay=1000
            ).add_to(m_mon)

        st_folium(m_mon, width="100%", height=450, key="map_mon_intel")
        st.markdown('</div>', unsafe_allow_html=True)

        if sos_activos > 0:
            inf_neu = st.text_area("INFORME DE NEUTRALIZACIÓN")
            if st.button("FINALIZAR OPERATIVO", use_container_width=True):
                if inf_neu.strip():
                    fila = pendientes.index[-1] + 2
                    actualizar_celda("ALERTAS", fila, "D", "RESUELTO")
                    actualizar_celda("ALERTAS", fila, "F", inf_neu)
                    st.rerun()

    with t_gestion:
        if not df_emergencias.empty: st.dataframe(df_emergencias.iloc[::-1], use_container_width=True)

# OTROS ROLES (MAPA FISCALIZADOR)
elif st.session_state.rol_sel in ["SUPERVISOR", "JEFE DE OPERACIONES", "GERENCIA"]:
    st.markdown('<div class="radar-box">', unsafe_allow_html=True)
    m_visor = folium.Map(location=[-34.6, -58.4], zoom_start=12, tiles="CartoDB dark_matter")
    for _, r in df_objetivos.iterrows():
        folium.Marker([float(str(r['LATITUD']).replace(',','.')), float(str(r['LONGITUD']).replace(',','.'))], 
                      tooltip=r['OBJETIVO'], icon=folium.Icon(color="blue", icon="shield", prefix="fa")).add_to(m_visor)
    st_folium(m_visor, width="100%", height=500, key=f"map_fiscal_{st.session_state.rol_sel}")
    st.markdown('</div>', unsafe_allow_html=True)

# ROL: ADMINISTRADOR
elif st.session_state.rol_sel == "ADMINISTRADOR":
    st.header("⚙️ NÚCLEO MAESTRO")
    u_ing = st.text_input("ADMIN_USER")
    p_ing = st.text_input("ADMIN_PASS", type="password")
    if u_ing == "admin" and p_ing == "aion2026":
        tipo = st.radio("Alta:", ["SUPERVISOR", "SERVICIO"], horizontal=True)
        nuevo_nombre = st.text_input("Nombre:").upper()
        if st.button("REGISTRAR"):
            escribir_registro_nube("ESTRUCTURA", [obtener_hora_argentina(), tipo, nuevo_nombre, "ACTIVO", st.session_state.user_sel])
            st.success("Alta Exitosa")
            
