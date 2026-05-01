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

# --- 3. FUNCIONES DE LÓGICA Y COMANDOS ---
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

# ✅ MOTOR DE TRIANGULACIÓN Y APOYO TÁCTICO[cite: 3, 4]
def calcular_emergencia(lat, lon, df_obj):
    if df_obj.empty or lat == 0.0: return "Sin datos", "Sin datos", None
    df_temp = df_obj.copy()
    df_temp['distancia'] = np.sqrt((df_temp['LATITUD'] - lat)**2 + (df_temp['LONGITUD'] - lon)**2)
    cercano = df_temp.loc[df_temp['distancia'].idxmin()]
    return cercano['OBJETIVO'], cercano.get('POLICIA', '911 / No asignada'), (cercano['LATITUD'], cercano['LONGITUD'])

# --- 4. DISEÑO E IDENTIDAD VISUAL ---
def aplicar_identidad_alfa():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@300;500;700&display=swap');
        .stApp { background: radial-gradient(circle at top, #0A0F1E 0%, #030305 100%) !important; color: #E0E0E0; font-family: 'Rajdhani', sans-serif; }
        [data-testid="stSidebar"] { background-color: #050507 !important; border-right: 1px solid rgba(0, 229, 255, 0.3) !important; }
        .contenedor-logo-central { display: flex; justify-content: center; align-items: center; width: 100%; margin-top: -10px; margin-bottom: 20px; }
        .logo-phoenix { width: 520px !important; border: 2px solid #00e5ff !important; box-shadow: 0 0 35px rgba(0, 229, 255, 0.5) !important; border-radius: 4px !important; background-color: #000 !important; }
        .panico-container { display: flex !important; justify-content: center !important; align-items: center !important; width: 100% !important; margin: 20px 0 !important; padding: 0 !important; }
        .stButton > button[kind="primary"] { 
            background: radial-gradient(circle, #FF0000 0%, #8B0000 100%) !important; 
            color: white !important; border-radius: 50% !important; width: 105px !important; height: 105px !important; 
            border: 3px solid #333 !important; box-shadow: 0 0 25px rgba(255, 0, 0, 0.5) !important; 
            font-family: 'Orbitron', sans-serif; font-size: 11px !important; font-weight: bold; line-height: 1.1; text-transform: uppercase; margin: 0 auto !important; 
        }
        .radar-box { border: 1px solid #1A1A1B; border-radius: 12px; padding: 20px; background: rgba(10, 10, 11, 0.8); }
        h1, h2, h3, .stSubheader { font-family: 'Orbitron', sans-serif; color: #00E5FF !important; text-shadow: 0 0 15px rgba(0, 229, 255, 0.4); }
        </style>
        """, unsafe_allow_html=True
    )

aplicar_identidad_alfa()
st.markdown('<div class="contenedor-logo-central"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" class="logo-phoenix"></div>', unsafe_allow_html=True)

# --- 5. MEMORIA DE SESIÓN Y SIDEBAR ---
if 'rol_sel' not in st.session_state: st.session_state.rol_sel = "SUPERVISOR"
if 'user_sel' not in st.session_state: st.session_state.user_sel = "BRIAN AYALA"

with st.sidebar:
    st.markdown('<div style="margin-top: 50px;"></div>', unsafe_allow_html=True)
    st.subheader("🛡️ PANEL DE CONTROL")
    st.session_state.rol_sel = st.selectbox("NIVEL DE ACCESO", ["SUPERVISOR", "MONITOREO", "JEFE DE OPERACIONES", "GERENCIA", "ADMINISTRADOR"])
    st.session_state.user_sel = st.selectbox("IDENTIDAD OPERATIVA", ["BRIAN AYALA", "DARÍO CECILIA", "LUIS BONGIORNO", "SERANTES WALTER", "SANOJA LUIS", "MAZACOTTE CLAUDIO"])
    
    loc = get_geolocation()
    lat_act = loc['coords']['latitude'] if loc else 0.0
    lon_act = loc['coords']['longitude'] if loc else 0.0

    st.markdown('<div class="panico-container">', unsafe_allow_html=True)
    if st.button("ACTIVAR\nPÁNICO", type="primary"):
        carga_sos = f"LAT: {lat_act} | LON: {lon_act}"
        if escribir_registro_nube("ALERTAS", [obtener_hora_argentina(), st.session_state.user_sel, "CRÍTICO", "PENDIENTE", carga_sos, ""]):
            st.error("❗ SOS TRANSMITIDO")
    st.markdown('</div>', unsafe_allow_html=True)

# --- 6. FLUJO DE INTERFAZ POR ROLES ---
df_objetivos = cargar_objetivos()

# --- A. ROL: SUPERVISOR (FILTRADO POR ZONA PROPIA) ---
if st.session_state.rol_sel == "SUPERVISOR":
    st.subheader(f"📱 Estación: {st.session_state.user_sel}")
    
    # ✅ FILTRO DE SEGURIDAD: Solo objetivos asignados a este supervisor[cite: 5, 6]
    apellido = st.session_state.user_sel.split()[-1].upper()
    df_propio = df_objetivos[df_objetivos['SUPERVISOR'].astype(str).str.upper().str.contains(apellido, na=False)] if not df_objetivos.empty else pd.DataFrame()
    
    t1, t2, t3 = st.tabs(["📍 MI RADAR", "📝 NOVEDADES", "💬 CHAT"])
    with t1:
        st.markdown('<div class="radar-box">', unsafe_allow_html=True)
        # Centrar mapa en sus objetivos o su posición actual[cite: 3, 4]
        lat_mapa = df_propio['LATITUD'].mean() if not df_propio.empty else (lat_act if lat_act != 0 else -34.6)
        lon_mapa = df_propio['LONGITUD'].mean() if not df_propio.empty else (lon_act if lon_act != 0 else -58.4)
        
        m = folium.Map(location=[lat_mapa, lon_mapa], zoom_start=13, tiles="CartoDB dark_matter")
        
        # Marcador de posición actual del supervisor[cite: 3, 4]
        folium.Marker([lat_act, lon_act], tooltip="MI POSICIÓN", icon=folium.Icon(color="red", icon="user")).add_to(m)
        
        # Solo marcar sus objetivos[cite: 5, 6]
        for _, r in df_propio.iterrows():
            folium.Marker([r['LATITUD'], r['LONGITUD']], popup=r['OBJETIVO'], icon=folium.Icon(color="blue", icon="shield", prefix="fa")).add_to(m)
        
        st_folium(m, width="100%", height=350)
        st.markdown('</div>', unsafe_allow_html=True)
    with t2:
        with st.form("nov_sup"):
            # Solo puede elegir sus objetivos para reportar novedades[cite: 5, 6]
            f_dest = st.selectbox("Objetivo:", df_propio['OBJETIVO'].unique()) if not df_propio.empty else "N/A"
            f_nov = st.text_area("Novedad Operativa")
            if st.form_submit_button("TRANSMITIR"):
                escribir_registro_nube("ACTAS_FLOTAS", [obtener_hora_argentina(), st.session_state.user_sel, "", "", "", "", "", f_dest, f_nov, "VERDE"])
                st.success("Informe transmitido a la matriz.")

# --- B. ROL: MONITOREO (ESTACIÓN DE DESPACHO) ---
elif st.session_state.rol_sel == "MONITOREO":
    st.header("🛰️ CENTRAL DE INTELIGENCIA OPERATIVA")
    df_emergencias = leer_matriz_nube("ALERTAS")
    sos_activos = len(df_emergencias[df_emergencias['ESTADO'].astype(str).str.upper() == 'PENDIENTE']) if not df_emergencias.empty else 0
    
    if sos_activos > 0:
        datos_sos = df_emergencias[df_emergencias['ESTADO'].astype(str).str.upper() == 'PENDIENTE'].iloc[-1]
        carga = str(datos_sos.get('CARGA_UTIL', ''))
        try:
            lat_sos = float(carga.split("|")[0].split(":")[1].strip())
            lon_sos = float(carga.split("|")[1].split(":")[1].strip())
        except: lat_sos, lon_sos = 0.0, 0.0

        obj_cercano, policia_nombre, coords_apoyo = calcular_emergencia(lat_sos, lon_sos, df_objetivos)
        
        st.markdown(f"""
            <div style="background-color: #FF0000; color: white; padding: 20px; border-radius: 10px; text-align: center; border: 2px solid white;">
                <h2 style="color: white !important;">🚨 EMERGENCIA: {datos_sos['USUARIO']} 🚨</h2>
                <p style="font-size: 18px;">UBICADO EN: <b>{obj_cercano}</b></p>
                <p style="font-size: 20px; font-weight: bold; color: #FFFF00;">🚓 COMISARÍA ASIGNADA: {policia_nombre}</p>
            </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="radar-box">', unsafe_allow_html=True)
        m_sos = folium.Map(location=[lat_sos, lon_sos], zoom_start=15, tiles="CartoDB dark_matter")
        folium.Marker([lat_sos, lon_sos], tooltip=f"{datos_sos['USUARIO']} / {obj_cercano}", icon=folium.Icon(color="red", icon="warning")).add_to(m_sos)
        
        if coords_apoyo:
            folium.Marker([coords_apoyo[0], coords_apoyo[1]], tooltip=f"APOYO: {policia_nombre}", icon=folium.Icon(color="blue", icon="shield", prefix="fa")).add_to(m_sos)
            AntPath(locations=[[lat_sos, lon_sos], [coords_apoyo[0], coords_apoyo[1]]], color="#00E5FF", pulse_color="#FFFFFF", weight=5, opacity=0.8).add_to(m_sos)
        
        st_folium(m_sos, width="100%", height=400, key="mapa_mon_sos")
        st.markdown('</div>', unsafe_allow_html=True)
        
        url_maps = f"https://www.google.com/maps/dir/?api=1&origin={lat_sos},{lon_sos}&destination={policia_nombre}"
        st.markdown(f'<a href="{url_maps}" target="_blank"><button style="width:100%; padding:15px; background-color:#4285F4; color:white; border:none; border-radius:8px; font-weight:bold; cursor:pointer; margin-top:10px;">🗺️ VER RECORRIDO EN GOOGLE MAPS</button></a>', unsafe_allow_html=True)

        with st.form("cierre"):
            res = st.text_area("Informe de Resolución")
            if st.form_submit_button("✅ CERRAR ALERTA"):
                fila = df_emergencias[df_emergencias['ESTADO'].astype(str).str.upper() == 'PENDIENTE'].index[-1] + 2
                actualizar_celda("ALERTAS", fila, "D", "RESUELTO")
                actualizar_celda("ALERTAS", fila, "F", res)
                st.rerun()
    else:
        st.success("✅ SISTEMA EN VIGILANCIA PASIVA")

# --- C. ROL: JEFE DE OPERACIONES ---
elif st.session_state.rol_sel == "JEFE DE OPERACIONES":
    st.subheader("📋 COMANDO DE OPERACIONES")
    df_actas = leer_matriz_nube("ACTAS_FLOTAS")
    if not df_actas.empty: st.dataframe(df_actas.tail(15), use_container_width=True)
    if not df_objetivos.empty:
        m_ops = folium.Map(location=[df_objetivos['LATITUD'].mean(), df_objetivos['LONGITUD'].mean()], zoom_start=11, tiles="CartoDB dark_matter")
        for _, r in df_objetivos.iterrows():
            folium.Marker([r['LATITUD'], r['LONGITUD']], popup=r['OBJETIVO'], icon=folium.Icon(color="blue", icon="shield", prefix="fa")).add_to(m_ops)
        st_folium(m_ops, width="100%", height=400)

# --- D. OTROS ROLES ---
elif st.session_state.rol_sel == "GERENCIA":
    st.header("📈 DASHBOARD ESTRATÉGICO")
    df_al = leer_matriz_nube("ALERTAS")
    if not df_al.empty: st.write(df_al['ESTADO'].value_counts())

elif st.session_state.rol_sel == "ADMINISTRADOR":
    st.header("⚙️ NÚCLEO MAESTRO")
    u = st.text_input("USER")
    p = st.text_input("PASS", type="password")
    if u == "admin" and p == "aion2026":
        nombre = st.text_input("NUEVO SERVICIO")
        if st.button("ALTA"):
            escribir_registro_nube("ESTRUCTURA", [obtener_hora_argentina(), "SERVICIO", nombre.upper(), "ACTIVO", st.session_state.user_sel])
            st.success("Ok")
