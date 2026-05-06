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
    
    # LISTA DE SUPERVISORES DE ZONA 
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
# ==========================================
# A. ROL: MONITOREO - INTERFAZ "AION YAROKU TACTICAL"
# ==========================================
if st.session_state.rol_sel == "MONITOREO":
    from folium.plugins import AntPath
    from streamlit_folium import st_folium
    import folium
    import math

    def n_ok(v):
        try: return float(str(v).replace(',', '.').strip())
        except: return None

    # 1. CARGA DE DATOS
    df_emergencias = leer_matriz_nube("ALERTAS")
    df_comisarias = leer_matriz_nube("COMISARIAS")
    alertas_activas = df_emergencias[df_emergencias['ESTADO'].astype(str).str.upper() == 'PENDIENTE']
    sos_activos = len(alertas_activas)

    # Estilo de Fondo y Títulos (CSS)
    st.markdown("""
        <style>
        [data-testid="stMetricValue"] { font-size: 28px; color: #00E5FF; }
        .emergency-box { background-color: rgba(255, 0, 0, 0.2); padding: 10px; border-radius: 10px; border: 1px solid red; }
        </style>
    """, unsafe_allow_html=True)

    # --- ESTRUCTURA TÁCTICA DE 3 COLUMNAS ---
    col_izq, col_centro, col_der = st.columns([1.2, 3.5, 1.5])

    with col_izq:
        st.markdown("### 📡 INDICADORES")
        st.metric("S.O.S ACTIVOS", sos_activos, delta="CRÍTICO" if sos_activos > 0 else "NORMAL", delta_color="inverse")
        st.write("---")
        st.write("🔴 **ESTADO:** RADAR ACTIVO")
        st.write("🟢 **SISTEMA:** ONLINE")
        st.write("🚓 **UNIDADES:**", len(df_comisarias))
        st.write("📍 **NODOS:**", len(df_objetivos))
        
        if sos_activos > 0:
            st.markdown("<div class='emergency-box'>🚨 <b>PROTOCOLO ACTIVADO</b><br>Desplegando ruta de interceptación...</div>", unsafe_allow_html=True)

    with col_centro:
        lat_foco, lon_foco = -34.6037, -58.3816
        obj_en_panico, sup_responsable = "", "N/A"
        comisaria_cercana = None
        dist_minima = float('inf')

        if sos_activos > 0:
            datos_sos = alertas_activas.iloc[-1]
            carga = str(datos_sos.get('CARGA_UTIL', ''))
            if "OBJETIVO:" in carga.upper():
                obj_en_panico = carga.split("OBJETIVO:")[1].split("|")[0].strip().upper()
                sup_responsable = carga.split("SUPERVISOR:")[1].strip() if "SUPERVISOR:" in carga.upper() else "N/A"
            
            match = df_objetivos[df_objetivos['OBJETIVO'].str.strip().str.upper() == obj_en_panico]
            if not match.empty:
                lat_foco, lon_foco = n_ok(match.iloc[0]['LATITUD']), n_ok(match.iloc[0]['LONGITUD'])

            # Cálculo de Comisaría más cercana
            if not df_comisarias.empty and lat_foco:
                df_c_datos = df_comisarias.copy()
                if "NOMBRE" in str(df_c_datos.iloc[0,0]).upper(): df_c_datos = df_c_datos.iloc[1:]
                for _, com in df_c_datos.iterrows():
                    try:
                        c_lat, c_lon = n_ok(com.iloc[1]), n_ok(com.iloc[2])
                        R = 6371.0
                        dphi, dlambda = math.radians(c_lat-lat_foco), math.radians(c_lon-lon_foco)
                        a = math.sin(dphi/2)**2 + math.cos(math.radians(lat_foco))*math.cos(math.radians(c_lat))*math.sin(dlambda/2)**2
                        dist = R * (2 * math.atan2(math.sqrt(a), math.sqrt(1-a)))
                        if dist < dist_minima:
                            dist_minima = dist
                            comisaria_cercana = {"NOMBRE": str(com.iloc[0]), "LAT": c_lat, "LON": c_lon}
                    except: continue

        # --- MAPA TÁCTICO CON EFECTO RADAR (ASÍ COMO LA IMAGEN) ---
        m_mon = folium.Map(location=[lat_foco, lon_foco], zoom_start=15, 
                           tiles="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", attr='CartoDB')

        # CSS PARA ONDAS DE CHOQUE ROJAS (TITILE EXPANSIVO)
        radar_css = """
        <style>
        @keyframes pulse { 0% { transform: scale(0.5); opacity: 1; } 100% { transform: scale(4); opacity: 0; } }
        .radar-wave { background: rgba(255, 0, 0, 0.4); border-radius: 50%; animation: pulse 2s infinite; border: 2px solid red; }
        </style>
        """
        m_mon.get_root().header.add_child(folium.Element(radar_css))

        # Dibujar todos los puntos
        for _, r in df_objetivos.iterrows():
            r_lat, r_lon = n_ok(r.get('LATITUD')), n_ok(r.get('LONGITUD'))
            if r_lat and r_lon:
                es_sos = (str(r.get('OBJETIVO', '')).strip().upper() == obj_en_panico and obj_en_panico != "")
                if es_sos:
                    # Onda de Radar (Doble capa para que se vea más fuerte)
                    folium.Marker([r_lat, r_lon], icon=folium.DivIcon(html='<div class="radar-wave" style="width:40px; height:40px;"></div>')).add_to(m_mon)
                    folium.CircleMarker([r_lat, r_lon], radius=15, color="red", fill=True, fill_color="red", fill_opacity=0.9, z_index=1000).add_to(m_mon)
                else:
                    folium.CircleMarker([r_lat, r_lon], radius=5, color="#00E5FF", fill=True, fill_opacity=0.2).add_to(m_mon)

        # Ruta de Respuesta Amarilla
        if comisaria_cercana and lat_foco:
            folium.Marker([comisaria_cercana['LAT'], comisaria_cercana['LON']], 
                          icon=folium.Icon(color="blue", icon="shield", prefix="fa")).add_to(m_mon)
            AntPath(locations=[[comisaria_cercana['LAT'], comisaria_cercana['LON']], [lat_foco, lon_foco]], 
                    color='#FFEB3B', weight=8, delay=400, pulse_color='white').add_to(m_mon)
            m_mon.fit_bounds([[comisaria_cercana['LAT'], comisaria_cercana['LON']], [lat_foco, lon_foco]])

        st_folium(m_mon, width="100%", height=550, key="mapa_tactico_final")

    with col_der:
        st.markdown("### 📖 NOVEDADES")
        if not df_emergencias.empty:
            # Vista compacta del historial
            st.dataframe(df_emergencias[['HORA', 'ESTADO']].iloc[::-1], height=300, use_container_width=True)
        
        if sos_activos > 0:
            st.error(f"OBJ: {obj_en_panico}")
            st.info(f"SUP: {sup_responsable}")
            inf = st.text_area("INFORME DE CIERRE", placeholder="Escriba aquí...")
            if st.button("FINALIZAR", use_container_width=True):
                if inf.strip():
                    actualizar_celda("ALERTAS", alertas_activas.index[-1]+2, "D", "RESUELTO")
                    actualizar_celda("ALERTAS", alertas_activas.index[-1]+2, "F", inf)
                    st.rerun()
                    
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
