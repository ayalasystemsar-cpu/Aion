# --- 1. CONFIGURACIÓN E IDENTIDAD VISUAL CORPORATIVA (AION-YAROKU CORE) ---
import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
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

@st.cache_data(ttl=60)
def cargar_objetivos():
    df = leer_matriz_nube("OBJETIVOS")
    if not df.empty:
        df.columns = df.columns.str.strip().str.upper()
        df['LATITUD'] = pd.to_numeric(df['LATITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        df['LONGITUD'] = pd.to_numeric(df['LONGITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        return df.dropna(subset=['LATITUD', 'LONGITUD'])
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

# --- 5. SIDEBAR TÁCTICO (ACTUALIZADO CON SUPERVISOR NOCTURNO) ---
df_objetivos = cargar_objetivos()

if 'rol_sel' not in st.session_state: st.session_state.rol_sel = "MONITOREO"
if 'user_sel' not in st.session_state: st.session_state.user_sel = "BRIAN AYALA"

with st.sidebar:
    st.markdown('<div class="contenedor-logo-sidebar"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" style="width:180px; border:1px solid #00e5ff; border-radius:4px;"></div>', unsafe_allow_html=True)
    st.subheader("🛡️ PANEL DE CONTROL")
    st.session_state.rol_sel = st.selectbox("NIVEL DE ACCESO", ["SUPERVISOR", "MONITOREO", "JEFE DE OPERACIONES", "GERENCIA", "ADMINISTRADOR"])
    
    # LISTA DE IDENTIDAD OPERATIVA ACTUALIZADA
    st.session_state.user_sel = st.selectbox("IDENTIDAD OPERATIVA", ["BRIAN AYALA", "SANOJA LUIS", "DARÍO CECILIA", "LUIS BONGIORNO", "SERANTES WALTER", "MAZACOTTE CLAUDIO", "SUPERVISOR NOCTURNO"])
    
    st.write("---")
    st.markdown("**🚨 CONFIGURACIÓN DE EMERGENCIA**")
    obj_panico = st.selectbox("🎯 SELECCIONAR OBJETIVO", df_objetivos['OBJETIVO'].unique() if not df_objetivos.empty else ["N/A"])
    
    # LISTA DE SUPERVISORES DE ZONA (SIN EDGAR VERA)
    sup_panico = st.selectbox("👤 SUPERVISOR DE ZONA", ["BRIAN AYALA", "GONZALO PORZIO", "SUPERVISOR NOCTURNO", "OTRO"])
    
    loc = get_geolocation()
    lat_envio = loc['coords']['latitude'] if loc else 0.0
    lon_envio = loc['coords'].get('longitude', 0.0) if loc else 0.0

    if st.button("ACTIVAR\nPÁNICO", type="primary"):
        carga_sos = f"LAT:{lat_envio}|LON:{lon_envio}|OBJ:{obj_panico}|SUP:{sup_panico}"
        escribir_registro_nube("ALERTAS", [obtener_hora_argentina(), st.session_state.user_sel, "PÁNICO", "PENDIENTE", carga_sos])
        st.error(f"🚨 S.O.S ENVIADO: {obj_panico}")

# --- 6. CABECERA CENTRAL ---
st.markdown('<div class="contenedor-logo-central"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" class="logo-phoenix"></div>', unsafe_allow_html=True)

# Títulos por Rol con Estilo Glow
titulos = {
    "MONITOREO": "🛰️ CENTRAL DE INTELIGENCIA OPERATIVA",
    "SUPERVISOR": f"📱 Estación de Control: {st.session_state.user_sel}",
    "JEFE DE OPERACIONES": "📋 COMANDO DE OPERACIONES TÁCTICAS",
    "GERENCIA": "🏢 DIRECCIÓN Y FISCALIZACIÓN GENERAL",
    "ADMINISTRADOR": "⚙️ NÚCLEO MAESTRO"
}
st.markdown(f'<div class="estacion-titulo">{titulos.get(st.session_state.rol_sel, "SISTEMA TÁCTICO DE COMANDO")}</div>', unsafe_allow_html=True)

# --- 7. FLUJO POR ROLES ---

# A. ROL: MONITOREO (CON INTELIGENCIA DE INTERCEPCIÓN REFORZADA)
if st.session_state.rol_sel == "MONITOREO":
    from folium.plugins import AntPath # IMPORTANTE: Esto dibuja la ruta
    
    # 1. CARGAMOS TODAS LAS BASES NECESARIAS
    df_emergencias = leer_matriz_nube("ALERTAS")
    df_comisarias = leer_matriz_nube("COMISARIAS") # ESTA ES LA CLAVE
    
    sos_activos = len(df_emergencias[df_emergencias['ESTADO'].astype(str).str.upper() == 'PENDIENTE']) if not df_emergencias.empty else 0
    
    c1, c2, c3 = st.columns(3)
    c1.metric("🚨 S.O.S ACTIVOS", sos_activos)
    c2.metric("📡 RED", "OPERATIVA")
    c3.metric("🕒 HORA LOCAL", obtener_hora_argentina().split(" ")[1])

    t_radar, t_gestion = st.tabs(["🚨 RADAR S.O.S", "📖 LIBRO DE BASE"])
    with t_radar:
        lat_foco, lon_foco, obj_en_panico, sup_rep = -34.6, -58.4, "", ""
        comisaria_cercana = None
        dist_minima = float('inf')
        
        if sos_activos > 0:
            datos_sos = df_emergencias[df_emergencias['ESTADO'].astype(str).str.upper() == 'PENDIENTE'].iloc[-1]
            try:
                # Extraemos el objetivo de la carga útil
                partes = datos_sos.get('CARGA_UTIL', '').split("|")
                obj_en_panico = partes[2].split(":")[1]
                
                # Buscamos la ubicación del objetivo
                target_data = df_objetivos[df_objetivos['OBJETIVO'] == obj_en_panico].iloc[0]
                lat_foco = float(str(target_data['LATITUD']).replace(',','.'))
                lon_foco = float(str(target_data['LONGITUD']).replace(',','.'))

                # --- LÓGICA DE INTERCEPCIÓN ---
                if not df_comisarias.empty:
                    import math
                    def calc_dist_pro(la1, lo1, la2, lo2):
                        R = 6371.0
                        la1, lo1, la2, lo2 = map(math.radians, [la1, lo1, la2, lo2])
                        dlat, dlon = la2 - la1, lo2 - lo1
                        a = math.sin(dlat/2)**2 + math.cos(la1)*math.cos(la2)*math.sin(dlon/2)**2
                        return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1-a)))

                    for _, com in df_comisarias.iterrows():
                        try:
                            c_lat = float(str(com['LATITUD']).replace(',','.'))
                            c_lon = float(str(com['LONGITUD']).replace(',','.'))
                            d = calc_dist_pro(lat_foco, lon_foco, c_lat, c_lon)
                            if d < dist_minima:
                                dist_minima = d
                                comisaria_cercana = com
                        except: continue
            except: pass
            
            st.error(f"🚨 EMERGENCIA: {datos_sos['USUARIO']} | 🎯 {obj_en_panico}")
            if comisaria_cercana is not None:
                st.warning(f"🚓 RESPUESTA RECOMENDADA: {comisaria_cercana['NOMBRE']} a {dist_minima:.2f} Km")
        else:
            st.success("✅ Vigilancia Pasiva - Radar Operativo")

        st.markdown('<div class="radar-box">', unsafe_allow_html=True)
        m_mon = folium.Map(location=[lat_foco, lon_foco], zoom_start=14, tiles="CartoDB dark_matter")

        # CSS para el parpadeo (Blink)
        map_css = "<style>@keyframes blink {0%{opacity:1;}50%{opacity:0.1;}100%{opacity:1;}} .blink-icon {animation: blink 0.8s linear infinite;}</style>"
        m_mon.get_root().header.add_child(folium.Element(map_css))

        # Dibujar Objetivos
        for _, r in df_objetivos.iterrows():
            try:
                r_lat = float(str(r['LATITUD']).replace(',','.'))
                r_lon = float(str(r['LONGITUD']).replace(',','.'))
                es_alerta = (r['OBJETIVO'] == obj_en_panico)
                folium.Marker(
                    [r_lat, r_lon], 
                    tooltip=f"OBJ: {r['OBJETIVO']}", 
                    icon=folium.Icon(color="red" if es_alerta else "blue", icon="shield", prefix="fa", extraClasses="blink-icon" if es_alerta else "")
                ).add_to(m_mon)
            except: continue

        # --- DIBUJAR COMISARÍA Y RUTA (ESTO ES LO QUE NO SALÍA) ---
        if sos_activos > 0 and comisaria_cercana is not None:
            try:
                com_lat = float(str(comisaria_cercana['LATITUD']).replace(',','.'))
                com_lon = float(str(comisaria_cercana['LONGITUD']).replace(',','.'))
                
                # Marcador de Comisaría (Azul Oscuro)
                folium.Marker(
                    [com_lat, com_lon],
                    tooltip=f"COMISARÍA: {comisaria_cercana['NOMBRE']}",
                    icon=folium.Icon(color="darkblue", icon="balance-scale", prefix="fa")
                ).add_to(m_mon)
                
                # Trazado de Ruta Animada (Cian)
                AntPath(
                    locations=[[com_lat, com_lon], [lat_foco, lon_foco]],
                    color='#00E5FF', weight=5, opacity=0.9, delay=800
                ).add_to(m_mon)
            except: pass

        st_folium(m_mon, width="100%", height=450, key="map_mon_tactico_final")
        st.markdown('</div>', unsafe_allow_html=True)

# B. ROL: SUPERVISOR, JEFE DE OPERACIONES Y GERENCIA (MAPA FISCALIZADOR)
elif st.session_state.rol_sel in ["SUPERVISOR", "JEFE DE OPERACIONES", "GERENCIA"]:
    st.markdown('<div class="radar-box">', unsafe_allow_html=True)
    centro = [df_objetivos['LATITUD'].mean(), df_objetivos['LONGITUD'].mean()] if not df_objetivos.empty else [-34.6, -58.4]
    m_visor = folium.Map(location=centro, zoom_start=12, tiles="CartoDB dark_matter")
    for _, r in df_objetivos.iterrows():
        folium.Marker(
            [r['LATITUD'], r['LONGITUD']], 
            tooltip=f"OBJETIVO: {r['OBJETIVO']} | SUPERVISOR: {r.get('SUPERVISOR', 'N/A')}", 
            icon=folium.Icon(color="blue", icon="shield", prefix="fa")
        ).add_to(m_visor)
    st_folium(m_visor, width="100%", height=500, key=f"map_fiscalizacion_{st.session_state.rol_sel}")
    st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.rol_sel in ["JEFE DE OPERACIONES", "GERENCIA"]:
        st.subheader("📋 REPORTE DE MOVIMIENTOS")
        df_novedades = leer_matriz_nube("ACTAS_FLOTAS")
        if not df_novedades.empty:
            st.dataframe(df_novedades.tail(20), use_container_width=True)

# C. ROL: ADMINISTRADOR
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
