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
from supabase import create_client, Client

# ✅ CORRECCIÓN GEOLOCALIZACIÓN
try:
    from streamlit_js_eval import get_geolocation
except ImportError:
    get_geolocation = None

# Configuración de página OLED
st.set_page_config(
    page_title="AION-YAROKU | CORE",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CONEXIONES (SUPABASE & GOOGLE MATRIZ) ---
ID_MAESTRO_DB = "1Md0VkOnwUJWldq0S1fB9UrmOKv4MG__JVG3tQsda0Uw"

@st.cache_resource
def init_connection():
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except Exception: return None

supabase = init_connection()

def conectar_google():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        return gspread.authorize(creds)
    except: return None

# --- 3. FUNCIONES DE LÓGICA, DATOS Y COMANDOS ---
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

# ✅ MOTOR DE TRIANGULACIÓN Y LOCALIZACIÓN DE COMISARÍA
def calcular_emergencia(lat, lon, df_obj):
    """Retorna el Objetivo y los datos de la Comisaría/Policía[cite: 3, 4]"""
    if df_obj.empty or lat == 0.0: return "Sin datos", "Sin datos", None
    df_temp = df_obj.copy()
    df_temp['distancia'] = np.sqrt((df_temp['LATITUD'] - lat)**2 + (df_temp['LONGITUD'] - lon)**2)
    cercano = df_temp.loc[df_temp['distancia'].idxmin()]
    
    # Extraemos también la ubicación de la comisaría si estuviera disponible
    # Por ahora devolvemos el Objetivo, el Nombre de la Comisaría y las coordenadas del Objetivo de referencia[cite: 3, 4]
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
    perfiles = ["SUPERVISOR", "MONITOREO", "JEFE DE OPERACIONES", "GERENCIA", "ADMINISTRADOR"]
    st.session_state.rol_sel = st.selectbox("NIVEL DE ACCESO", perfiles)
    lista_sups = ["BRIAN AYALA", "DARÍO CECILIA", "LUIS BONGIORNO", "SUPERVISOR NOCTURNO", "SERANTES WALTER", "SANOJA LUIS", "MAZACOTTE CLAUDIO"]
    st.session_state.user_sel = st.selectbox("IDENTIDAD OPERATIVA", lista_sups)
    st.markdown("---")
    
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

# --- A. ROL: SUPERVISOR ---
if st.session_state.rol_sel == "SUPERVISOR":
    st.subheader(f"📱 Estación: {st.session_state.user_sel}")
    apellido = st.session_state.user_sel.split()[-1].upper()
    df_zona = df_objetivos[df_objetivos['SUPERVISOR'].str.upper().str.contains(apellido, na=False)] if not df_objetivos.empty else pd.DataFrame()
    if df_zona.empty: df_zona = df_objetivos

    t1, t2, t3 = st.tabs(["📍 RADAR & GPS", "📝 NOVEDADES", "💬 COMUNICACIÓN"])
    with t1:
        st.markdown('<div class="radar-box">', unsafe_allow_html=True)
        if not df_zona.empty:
            m = folium.Map(location=[df_zona['LATITUD'].mean(), df_zona['LONGITUD'].mean()], zoom_start=12, tiles="CartoDB dark_matter")
            for _, r in df_zona.iterrows():
                folium.Marker([r['LATITUD'], r['LONGITUD']], popup=r['OBJETIVO'], icon=folium.Icon(color="blue", icon="shield", prefix="fa")).add_to(m)
            st_folium(m, width="100%", height=350)
        st.markdown('</div>', unsafe_allow_html=True)
    with t2:
        st.subheader("📝 REPORTE DE NOVEDADES")
        with st.form("acta_tactica"):
            f_dest = st.selectbox("Objetivo:", df_zona['OBJETIVO'].unique()) if not df_zona.empty else "N/A"
            f_vig = st.text_input("Personal en Puesto")
            f_nov = st.text_area("Informe de Novedad")
            gravedad = st.select_slider("GRAVEDAD:", options=["VERDE", "AMARILLO", "ROJO"])
            if st.form_submit_button("🚀 TRANSMITIR ACTA"):
                datos = [obtener_hora_argentina(), st.session_state.user_sel, "", "", "", "", f_vig, f_dest, f_nov, gravedad]
                if escribir_registro_nube("ACTAS_FLOTAS", datos):
                    st.success("Acta derivada a la matriz.")
    with t3:
        st.info("Bandeja de Mensajería Sincronizada con Matriz Nube")

# --- B. ROL: MONITOREO (MAPA CON RUTA VISUAL A COMISARÍA) ---
elif st.session_state.rol_sel == "MONITOREO":
    st.header("🛰️ CENTRAL DE INTELIGENCIA OPERATIVA")
    df_emergencias = leer_matriz_nube("ALERTAS")
    sos_activos = len(df_emergencias[df_emergencias['ESTADO'].astype(str).str.upper() == 'PENDIENTE']) if not df_emergencias.empty else 0
    m1, m2, m3 = st.columns(3)
    m1.metric("🚨 S.O.S ACTIVOS", sos_activos)
    m2.metric("📡 ESTADO DE RED", "OPERATIVO")
    m3.metric("🕒 HORA LOCAL", obtener_hora_argentina().split(" ")[1])

    t_radar, t_gestion, t_chat = st.tabs(["🚨 RADAR S.O.S", "📖 LIBRO DE BASE", "💬 COMUNICACIÓN"])
    with t_radar:
        if sos_activos > 0:
            datos_sos = df_emergencias[df_emergencias['ESTADO'].astype(str).str.upper() == 'PENDIENTE'].iloc[-1]
            carga = str(datos_sos.get('CARGA_UTIL', ''))
            
            try:
                lat_sos = float(carga.split("|")[0].split(":")[1].strip())
                lon_sos = float(carga.split("|")[1].split(":")[1].strip())
            except: lat_sos, lon_sos = 0.0, 0.0

            # ✅ Triangulación: Supervisor -> Objetivo de referencia -> Comisaría[cite: 3, 4]
            obj_cercano, policia_zona, coords_obj = calcular_emergencia(lat_sos, lon_sos, df_objetivos)
            
            st.markdown(f"""
                <div style="background-color: #FF0000; color: white; padding: 20px; border-radius: 10px; text-align: center; border: 2px solid white;">
                    <h2 style="color: white !important;">🚨 EMERGENCIA DETECTADA 🚨</h2>
                    <h4 style="color: white !important;">Operador: {datos_sos['USUARIO']}</h4>
                    <p style="font-size: 18px;"><b>OBJETIVO CERCANO:</b> {obj_cercano}</p>
                    <p style="font-size: 20px; font-weight: bold; color: #FFFF00;">🚓 COMISARÍA ASIGNADA: {policia_zona}</p>
                </div>
            """, unsafe_allow_html=True)

            # ✅ MAPA CON MARCADORES Y RUTA VISUAL[cite: 3, 4]
            st.markdown('<div class="radar-box">', unsafe_allow_html=True)
            m_sos = folium.Map(location=[lat_sos, lon_sos], zoom_start=14, tiles="CartoDB dark_matter")
            
            # Marcador Supervisor (Rojo)
            folium.Marker([lat_sos, lon_sos], popup=f"SUPERVISOR: {datos_sos['USUARIO']}", icon=folium.Icon(color="red", icon="warning")).add_to(m_sos)
            
            # Marcador Comisaría/Objetivo (Azul)
            if coords_obj:
                folium.Marker([coords_obj[0], coords_obj[1]], popup=f"COMISARÍA/APOYO: {policia_zona}", icon=folium.Icon(color="blue", icon="shield", prefix="fa")).add_to(m_sos)
                # Línea visual de la ruta más corta (Vector táctico)[cite: 3, 4]
                folium.PolyLine([[lat_sos, lon_sos], [coords_obj[0], coords_obj[1]]], color="yellow", weight=5, opacity=0.8, dash_array='10').add_to(m_sos)
            
            st_folium(m_sos, width="100%", height=400, key="mapa_mon_sos")
            st.markdown('</div>', unsafe_allow_html=True)

            # Botón de Navegación Externa[cite: 3, 4]
            url_ruta = f"https://www.google.com/maps/dir/?api=1&origin={lat_sos},{lon_sos}&destination={policia_zona}"
            st.markdown(f'<a href="{url_ruta}" target="_blank"><button style="width:100%; padding:15px; background-color:#4285F4; color:white; border:none; border-radius:8px; font-weight:bold; cursor:pointer; margin-top:10px;">🚓 INICIAR RUTA DE RESPUESTA (GOOGLE MAPS)</button></a>', unsafe_allow_html=True)

            with st.form("cierre_crisis"):
                res_acta = st.text_area("Informe de Neutralización")
                if st.form_submit_button("✅ CERRAR ALERTA"):
                    fila_real = df_emergencias[df_emergencias['ESTADO'].astype(str).str.upper() == 'PENDIENTE'].index[-1] + 2
                    if actualizar_celda("ALERTAS", fila_real, "D", "RESUELTO"):
                        actualizar_celda("ALERTAS", fila_real, "F", res_acta)
                        st.success("Resuelto"); st.cache_data.clear(); st.rerun()
        else:
            st.success("✅ Sistema en Vigilancia Pasiva")
    with t_gestion:
        with st.form("acta_base"):
            op_nombre = st.text_input("Operador:", value=st.session_state.user_sel)
            nov = st.text_area("Novedades")
            if st.form_submit_button("🔒 SELLAR"):
                escribir_registro_nube("MENSAJERIA", [obtener_hora_argentina(), op_nombre, "SISTEMA", "LIBRO BASE", nov, "ENVIADO", "VERDE"])
                st.rerun()
    with t_chat:
        st.subheader("📨 CENTRO DE MENSAJERÍA SINCRONIZADO")
        df_m = leer_matriz_nube("MENSAJERIA")
        if not df_m.empty:
            for _, msg in df_m.tail(10).iloc[::-1].iterrows():
                emisor = msg.get('EMISOR', msg.get('Emisor', 'Desconocido'))
                contenido = msg.get('CONTENIDO', msg.get('Contenido', 'Sin mensaje'))
                with st.chat_message("user"):
                    st.write(f"**{emisor}**: {contenido}")
        else:
            st.info("No hay mensajes registrados.")

# --- C. ROL: JEFE DE OPERACIONES ---
elif st.session_state.rol_sel == "JEFE DE OPERACIONES":
    st.subheader("📋 COMANDO DE OPERACIONES TÁCTICAS")
    df_actas = leer_matriz_nube("ACTAS_FLOTAS")
    c1, c2, c3 = st.columns(3)
    c1.metric("REPORTES", len(df_actas) if not df_actas.empty else 0)
    c2.metric("OBJETIVOS", len(df_objetivos))
    c3.metric("ESTADO", "SINCRO OK")
    t_inf, t_mapa = st.tabs(["📄 INFORMES", "🌍 MAPA"])
    with t_inf:
        if not df_actas.empty: st.dataframe(df_actas.tail(15), use_container_width=True)
    with t_mapa:
        st.markdown('<div class="radar-box">', unsafe_allow_html=True)
        if not df_objetivos.empty:
            m_ops = folium.Map(location=[df_objetivos['LATITUD'].mean(), df_objetivos['LONGITUD'].mean()], zoom_start=11, tiles="CartoDB dark_matter")
            for _, r in df_objetivos.iterrows():
                folium.Marker(location=[r['LATITUD'], r['LONGITUD']], popup=f"OBJETIVO: {r['OBJETIVO']}", icon=folium.Icon(color="blue", icon="shield", prefix="fa")).add_to(m_ops)
            st_folium(m_ops, width="100%", height=400, key="mapa_jefe_ops")
        st.markdown('</div>', unsafe_allow_html=True)

# --- D. ROL: GERENCIA ---
elif st.session_state.rol_sel == "GERENCIA":
    st.header("📈 DASHBOARD ESTRATÉGICO")
    col_a, col_b = st.columns([1, 2])
    with col_a:
        st.subheader("⚠️ Alertas")
        df_al = leer_matriz_nube("ALERTAS")
        if not df_al.empty: st.write(df_al['ESTADO'].value_counts())
    with col_b:
        st.subheader("🏢 Estructura")
        df_est = leer_matriz_nube("ESTRUCTURA")
        if not df_est.empty: st.dataframe(df_est, use_container_width=True)

# --- E. ROL: ADMINISTRADOR ---
elif st.session_state.rol_sel == "ADMINISTRADOR":
    st.header("⚙️ NÚCLEO MAESTRO")
    with st.expander("🔐 CREDENCIALES DE INFRAESTRUCTURA"):
        u_ing = st.text_input("ADMIN_USER").lower()
        p_ing = st.text_input("ADMIN_PASS", type="password")
        if u_ing == "admin" and p_ing == "aion2026":
            st.subheader("🏗️ GESTIÓN DE ESTRUCTURA")
            tipo = st.radio("Categoría:", ["SUPERVISOR", "SERVICIO"], horizontal=True)
            nuevo_nombre = st.text_input(f"Nombre del {tipo}:").upper()
            if st.button(f"PROCESAR ALTA"):
                if nuevo_nombre:
                    escribir_registro_nube("ESTRUCTURA", [obtener_hora_argentina(), tipo, nuevo_nombre, "ACTIVO", st.session_state.user_sel])
                    st.success("Alta Exitosa")
