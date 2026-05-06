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

# A. ROL: MONITOREO (RECONSTRUCCIÓN TOTAL - RUTA Y COMISARÍA)
if st.session_state.rol_sel == "MONITOREO":
    from folium.plugins import AntPath
    from streamlit_folium import st_folium
    import folium
    import math

    # Función de limpieza de coordenadas para evitar errores de puntos/comas
    def num_ok(v):
        try: return float(str(v).replace(',', '.').strip())
        except: return None

    # 1. CARGA DE DATOS
    df_emergencias = leer_matriz_nube("ALERTAS")
    df_comisarias = leer_matriz_nube("COMISARIAS")
    
    alertas_activas = df_emergencias[df_emergencias['ESTADO'].astype(str).str.upper() == 'PENDIENTE']
    sos_activos = len(alertas_activas)
    
    # Dashboard superior
    c1, c2, c3 = st.columns(3)
    c1.metric("🚨 S.O.S ACTIVOS", sos_activos)
    c2.metric("📡 RED", "OPERATIVA")
    c3.metric("🕒 HORA LOCAL", obtener_hora_argentina().split(" ")[1])

    t_radar, t_gestion = st.tabs(["🚨 RADAR S.O.S", "📖 LIBRO DE BASE"])
    
    with t_radar:
        lat_foco, lon_foco = -34.6, -58.4 
        obj_en_panico, sup_responsable = "", "N/A"
        comisaria_cercana = None
        dist_minima = float('inf')
        
        if sos_activos > 0:
            try:
                datos_sos = alertas_activas.iloc[-1]
                carga = str(datos_sos.get('CARGA_UTIL', ''))
                
                # Extraer Objetivo y Supervisor de la carga útil
                if "|" in carga:
                    partes = carga.split("|")
                    for p in partes:
                        if "OBJETIVO:" in p.upper(): obj_en_panico = p.split(":")[1].strip().upper()
                        if "SUPERVISOR:" in p.upper(): sup_responsable = p.split(":")[1].strip()
                
                # BUSCAR COORDENADAS DEL OBJETIVO EN PÁNICO (Búsqueda flexible)
                if obj_en_panico:
                    match = df_objetivos[df_objetivos['OBJETIVO'].str.strip().str.upper() == obj_en_panico]
                    if not match.empty:
                        lat_foco = num_ok(match.iloc[0]['LATITUD'])
                        lon_foco = num_ok(match.iloc[0]['LONGITUD'])

                # --- LÓGICA DE COMISARÍA MÁS CERCANA ---
                if not df_comisarias.empty and lat_foco:
                    # Saltamos la primera fila si es el encabezado del Excel
                    df_c_datos = df_comisarias.copy()
                    if "NOMBRE" in str(df_c_datos.iloc[0,0]).upper(): df_c_datos = df_c_datos.iloc[1:]

                    for _, com in df_c_datos.iterrows():
                        try:
                            c_lat, c_lon = num_ok(com.iloc[1]), num_ok(com.iloc[2])
                            if c_lat and c_lon:
                                R = 6371.0
                                phi1, phi2 = math.radians(lat_foco), math.radians(c_lat)
                                dphi, dlambda = math.radians(c_lat-lat_foco), math.radians(c_lon-lon_foco)
                                a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
                                dist = R * (2 * math.atan2(math.sqrt(a), math.sqrt(1-a)))
                                if dist < dist_minima:
                                    dist_minima = dist
                                    comisaria_cercana = {"NOMBRE": str(com.iloc[0]), "LAT": c_lat, "LON": c_lon}
                        except: continue

                if comisaria_cercana:
                    st.error(f"🚨 EMERGENCIA: {obj_en_panico} | COMISARÍA: {comisaria_cercana['NOMBRE']} ({dist_minima:.2f} km)")
                else:
                    st.warning(f"🚨 EMERGENCIA EN CURSO: {obj_en_panico} | Calculando ruta...")
            except: pass
        else:
            st.success("✅ Vigilancia Pasiva - Radar Operativo")

        # --- CONSTRUCCIÓN DEL MAPA ---
        m_mon = folium.Map(location=[lat_foco, lon_foco], zoom_start=14, tiles="CartoDB dark_matter")
        
        # Estilo CSS para que el punto rojo titile con borde blanco
        map_css = """<style>
        @keyframes blink {0%{opacity:1;}50%{opacity:0.3;}100%{opacity:1;}}
        .blink-icon {animation: blink 0.7s linear infinite; border: 2px solid white; border-radius: 50%;}
        </style>"""
        m_mon.get_root().header.add_child(folium.Element(map_css))

        # Dibujar Objetivos
        for _, r in df_objetivos.iterrows():
            r_lat, r_lon = num_ok(r.get('LATITUD')), num_ok(r.get('LONGITUD'))
            if r_lat and r_lon:
                es_sos = (str(r.get('OBJETIVO', '')).strip().upper() == obj_en_panico and obj_en_panico != "")
                folium.CircleMarker(
                    location=[r_lat, r_lon],
                    radius=14 if es_sos else 6,
                    color="red" if es_sos else "#00E5FF",
                    fill=True, fill_opacity=0.9 if es_sos else 0.4,
                    className="blink-icon" if es_sos else "",
                    z_index=1000 if es_sos else 1,
                    tooltip=f"OBJETIVO: {r['OBJETIVO']}"
                ).add_to(m_mon)

        # --- DIBUJAR COMISARÍA Y RUTA ---
        if comisaria_cercana and lat_foco:
            # Icono azul de la comisaría
            folium.Marker(
                [comisaria_cercana['LAT'], comisaria_cercana['LON']], 
                tooltip=f"🚓 {comisaria_cercana['NOMBRE']}",
                icon=folium.Icon(color="blue", icon="shield-halved", prefix="fa")
            ).add_to(m_mon)
            
            # Ruta animada amarilla
            AntPath(
                locations=[[comisaria_cercana['LAT'], comisaria_cercana['LON']], [lat_foco, lon_foco]],
                color='#FFEB3B', weight=8, delay=500, pulse_color='white'
            ).add_to(m_mon)
            
            # Ajustar el mapa para que se vean AMBOS puntos (Comisaría y Objetivo)
            m_mon.fit_bounds([[comisaria_cercana['LAT'], comisaria_cercana['LON']], [lat_foco, lon_foco]])

        st_folium(m_mon, width="100%", height=450, key="mapa_yaroku_final")

        if sos_activos > 0:
            st.markdown("---")
            inf_neu = st.text_area("INFORME DE NEUTRALIZACIÓN")
            if st.button("FINALIZAR OPERATIVO", use_container_width=True):
                if inf_neu.strip():
                    fila_excel = alertas_activas.index[-1] + 2
                    actualizar_celda("ALERTAS", fila_excel, "D", "RESUELTO")
                    actualizar_celda("ALERTAS", fila_excel, "F", inf_neu)
                    st.rerun()

    with t_gestion:
        st.subheader("📖 HISTORIAL OPERATIVO")
        if not df_emergencias.empty:
            st.dataframe(df_emergencias.iloc[::-1], use_container_width=True)
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
