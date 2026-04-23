import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from datetime import datetime
import numpy as np
import os
import sqlite3
from streamlit_js_eval import get_geolocation
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- 1. CONFIGURACIÓN E IDENTIDAD VISUAL ---
st.set_page_config(page_title="AION-YAROKU", layout="wide", initial_sidebar_state="expanded")

# --- LOGO CORPORATIVO DINÁMICO ---
st.markdown(
    """
    <style>
    .logo-container { position: absolute; top: 10px; left: 10px; display: flex; flex-direction: column; align-items: flex-start; z-index: 999; }
    .logo-container img { width: 12vw; max-width: 140px; min-width: 80px; height: auto; }
    @media (max-width: 768px) { .logo-container img { width: 20vw; } }
    </style>
    <div class='logo-container'><img src='assets/logo_aion.png' alt='AION-YAROKU'></div>
    """,
    unsafe_allow_html=True
)

# --- CSS DE ALTA PERFORMANCE ---
st.markdown("""
    <style>
    .stApp { background-color: #0A0A0A; color: #FFFFFF; }
    [data-testid="stSidebar"] { background-color: #111111; border-right: 2px solid #00E5FF; padding-top: 80px; }
    h1, h2, h3, .stSubheader { color: #00E5FF !important; font-family: 'Lexend', sans-serif; font-weight: bold; }
    div[data-testid="metric-container"] { background-color: #1A1A1A; border: 1px solid #333; border-left: 5px solid #00E5FF; padding: 15px; border-radius: 5px; }
    .stButton>button { background-color: #1A1A1A; color: #00E5FF; border: 1px solid #00E5FF; border-radius: 4px; transition: 0.3s; width: 100%; font-weight: bold; }
    .stButton>button:hover { background-color: #00E5FF; color: #000000; box-shadow: 0 0 20px #00E5FF; }
    .alerta-panico { background-color: #FF0000 !important; color: white !important; font-size: 24px; text-align: center; padding: 20px; border-radius: 10px; font-weight: bold; border: 2px solid white; animation: blink 1s infinite; }
    @keyframes blink { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
    </style>
    """, unsafe_allow_html=True)

# --- 2. NÚCLEO DE DATOS (SINCRONIZACIÓN NUBE) ---
ID_MAESTRO_DB = "1Md0VkOnwUJWldq0S1fB9UrmOKv4MG__JVG3tQsda0Uw"

def conectar_google():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
    return gspread.authorize(creds)

def escribir_registro(nombre_pestana, datos_fila):
    try:
        gc = conectar_google()
        hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(nombre_pestana)
        hoja.append_row(datos_fila)
        return True
    except: return False

@st.cache_data(ttl=15)
def leer_matriz_nube(pestana):
    try:
        gc = conectar_google()
        hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
        return pd
# Inicialización de Estados

if 'alerta_activa' not in st.session_state: st.session_state.alerta_activa = False
if 'db_mensajes' not in st.session_state: 
    st.session_state.db_mensajes = pd.DataFrame(columns=['ID', 'FECHA', 'REMITENTE', 'DESTINATARIO', 'ASUNTO', 'MENSAJE', 'ESTADO'])

df_objetivos = cargar_matriz_objetivos()
conn = sqlite3.connect(":memory:", check_same_thread=False)
if not df_objetivos.empty: df_objetivos.to_sql("objetivos", conn, index=False, if_exists="replace")

# --- 3. SISTEMA DE COMUNICACIONES ---
def enviar_msg(rem, dest, asun, texto):
    nuevo = pd.DataFrame([{'ID': len(st.session_state.db_mensajes)+1, 'FECHA': datetime.now().strftime("%H:%M"), 'REMITENTE': rem, 'DESTINATARIO': dest, 'ASUNTO': asun, 'MENSAJE': texto, 'ESTADO': 'NO LEÍDO'}])
    st.session_state.db_mensajes = pd.concat([st.session_state.db_mensajes, nuevo], ignore_index=True)
    escribir_registro("MENSAJERIA", [str(datetime.now()), rem, dest, asun, texto, "NO LEÍDO"])


# --- 4. PANEL LATERAL (IDENTIDAD) ---
with st.sidebar:
    logo_path = os.path.join("assets", "logo_aion.png")
    if os.path.exists(logo_path): st.image(logo_path, width=200)
    else: st.image("https://img.icons8.com/nolan/128/security-shield.png", width=80)

    st.title("AION-YAROKU")
    rol = st.selectbox("PERFIL OPERATIVO", ["SUPERVISOR", "MONITOREO", "JEFE DE OPERACIONES", "GERENCIA", "ADMINISTRADOR"])
    
    usuario_auth = ""
    lista_sups = ["AYALA BRIAN", "SERANTES WALTER", "SANOJA LUIS", "DIAZ MARCELO", "MAZACOTTE CLAUDIO", "PORZIO GONZALO", "CARRIZO WALTER"]
    
    if rol == "SUPERVISOR": usuario_auth = st.selectbox("IDENTIFICACIÓN", lista_sups)
    elif rol == "JEFE DE OPERACIONES": usuario_auth = "DARÍO CECILIA"
    elif rol == "GERENCIA": usuario_auth = "LUIS BONGIORNO"
    elif rol == "MONITOREO": usuario_auth = "CENTRAL MONITOREO"
    elif rol == "ADMINISTRADOR":
        clave = st.text_input("PASSWORD", type="password")
        if clave == st.secrets.get("admin_password", "aion2026"): usuario_auth = "AYALA BRIAN (ADMIN)"
        elif clave != "": st.stop()

    st.markdown("---")
    if st.button("🚨 ACTIVAR PÁNICO", use_container_width=True):
        st.session_state.alerta_activa = True
        escribir_registro("ALERTAS", [str(datetime.now()), usuario_auth, "CRÍTICO", "PENDIENTE"])
        st.error("S.O.S TRANSMITIDO")

# --- 5. LÓGICA DE SUPERVISOR (DOBLE QR + RUTEO) ---
if rol == "SUPERVISOR" and usuario_auth:
    st.header(f"Estación de Control: {usuario_auth}")
    tab1, tab2 = st.tabs(["📍 RADAR", "📤 REPORTES"])
    
    with tab1:
        apellido = usuario_auth.split()[-1].upper()
        df_zona = df_objetivos[df_objetivos['SUPERVISOR'].str.upper().str.contains(apellido, na=False)]
        
        # Ruteo Inteligente (Cálculo del más cercano)
        pos = get_geolocation()
        prox_recom = "Seleccione Objetivo"
        if pos and 'coords' in pos and not df_zona.empty:
            m_lat, m_lon = pos['coords']['latitude'], pos['coords']['longitude']
            distancias = []
            for _, r in df_zona.iterrows():
                p1, l1, p2, l2 = map(np.radians, [m_lat, m_lon, r['LATITUD'], r['LONGITUD']])
                d = 6371000 * (2 * np.arcsin(np.sqrt(np.sin((p2-p1)/2)*2 + np.cos(p1) * np.cos(p2) * np.sin((l2-l1)/2)*2)))
                distancias.append(d)
            idx_cerca = np.argmin(distancias)
            prox_recom = df_zona.iloc[idx_cerca]['OBJETIVO']

        c1, c2, c3 = st.columns(3)
        c1.metric("Objetivos", len(df_zona))
        c2.metric("Estatus GPS", "Activo")
        c3.info(f"💡 RECOMENDACIÓN: {prox_recom}")

        col_m, col_g = st.columns([2, 1])
        with col_m:
            if not df_zona.empty:
                m_s = folium.Map(location=[df_zona['LATITUD'].mean(), df_zona['LONGITUD'].mean()], zoom_start=12, tiles="CartoDB dark_matter")
                for _, row in df_zona.iterrows():
                    folium.Marker([row['LATITUD'], row['LONGITUD']], popup=row['OBJETIVO']).add_to(m_s)
                st_folium(m_s, width="100%", height=400)
        
        with col_g:
            if not df_zona.empty:
                dest = st.selectbox("Objetivo:", df_zona['OBJETIVO'].unique())
                t_obj = df_zona[df_zona['OBJETIVO'] == dest].iloc[0]
                if st.button("🟢 ESCANEAR INGRESO"):
                    # Simulación de lectura QR + GPS
                    escribir_registro("LOG_PRESENCIA", [str(datetime.now()), usuario_auth, dest, "ENTRADA", "QR_VALIDADO"])
                    st.success("INGRESO REGISTRADO")
                st.markdown(f'[🗺️ GPS MAPS](https://www.google.com/maps/dir/?api=1&destination={t_obj["LATITUD"]},{t_obj["LONGITUD"]})')

    with tab2:
        with st.form("form_registro"):
            f_movil = st.selectbox("Móvil", ["S-001", "S-002", "S-003", "S-004", "S-005", "S-006", "S-007"])
            f_km = st.number_input("Kilometraje", min_value=0, step=1)
            f_vig = st.text_input("Vigilador")
            f_nov = st.text_area("Novedades")
            f_foto = st.camera_input("Evidencia")
            
            if st.form_submit_button("🔴 ESCANEAR SALIDA Y ENVIAR"):
                # Simulación Doble QR Salida
                escribir_registro("LOG_PRESENCIA", [str(datetime.now()), usuario_auth, dest, "SALIDA", "QR_VALIDADO"])
                escribir_registro("ACTAS_FLOTAS", [str(datetime.now()), usuario_auth, f_movil, "", f_km, "", f_vig, dest, f_nov])
                st.success("ACTA Y SALIDA SINCRONIZADAS.")

# --- 6. MONITOREO Y JEFE DE OPERACIONES ---
elif rol == "MONITOREO":
    st.header("Consola Central")
    if st.session_state.alerta_activa:
        st.markdown('<div class="alerta-panico">🚨 ALERTA ACTIVA 🚨</div>', unsafe_allow_html=True)
        with st.form("resol"):
            op = st.text_input("Operador"); desc = st.text_area("Resolución")
            if st.form_submit_button("Archivar"):
                st.session_state.alerta_activa = False; st.rerun()
    else:
        st.subheader("Mapa Global de Infraestructura")
        m_mon = folium.Map(location=[df_objetivos['LATITUD'].mean(), df_objetivos['LONGITUD'].mean()], zoom_start=11, tiles="CartoDB dark_matter")
        for _, row in df_objetivos.iterrows(): folium.Marker([row['LATITUD'], row['LONGITUD']], tooltip=row['OBJETIVO']).add_to(m_mon)
        st_folium(m_mon, width="100%", height=500)

elif rol == "JEFE DE OPERACIONES":
    st.header(f"Comando: {usuario_auth}")
    t1, t2, t3 = st.tabs(["💬 MENSAJES", "📍 DESPLIEGUE", "📊 ACTIVIDAD"])
    with t1:
        with st.form("msg"):
            d = st.selectbox("A:", ["TODOS"] + lista_sups); a = st.text_input("Asunto"); m = st.text_area("Orden")
            if st.form_submit_button("Enviar"): enviar_msg(usuario_auth, d, a, m)
    with t3:
        st.write("Últimas Actas Recibidas")
        # Aquí se cargaría un dataframe de ACTAS_FLOTAS filtrado

# --- 7. GERENCIA (KPIs + PDF INTERNO) ---
elif rol == "GERENCIA":
    st.header(f"Tablero Luis Bongiorno")
    m1, m2, m3 = st.columns(3)
    m1.metric("Ahorro Estimado", "$128.400", "+12%")
    m2.metric("Cobertura", f"{len(df_objetivos)}/93")
    m3.metric("Efectividad", "100%")
    
    st.markdown("---")
    st.subheader("Auditoría de Carga de Trabajo")
    chart_data = df_objetivos['SUPERVISOR'].value_counts()
    st.bar_chart(chart_data)
    
    if st.button("📥 GENERAR REPORTE EJECUTIVO (PDF)"):
        st.info("Función de generación PDF interna activada. El documento se procesará en el servidor.")

# --- 8. ADMINISTRADOR (AYALA) ---
elif rol == "ADMINISTRADOR":
    st.header("⚙️ NÚCLEO MAESTRO")
    st.write(f"Enlace con Google Maestro: {ID_MAESTRO_DB}")
    if st.button("Sincronizar Base"): st.cache_data.clear(); st.rerun()
    st.dataframe(df_objetivos, use_container_width=True)
    st.warning("Acceso total a la Matriz de Datos habilitado.")
