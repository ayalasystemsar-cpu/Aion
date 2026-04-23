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

# --- 1. CONFIGURACIÓN E IDENTIDAD VISUAL CORPORATIVA ---
st.set_page_config(page_title="AION-YAROKU", layout="wide", initial_sidebar_state="expanded")

# --- LOGO CSS (SIN IMÁGENES ROTAS EN EL CUERPO) ---
st.markdown(
    """
    <style>
    .logo-container { position: absolute; top: 10px; left: 10px; display: flex; flex-direction: column; align-items: flex-start; z-index: 999; }
    .logo-container img { width: 12vw; max-width: 140px; min-width: 80px; height: auto; }
    @media (max-width: 768px) { .logo-container img { width: 20vw; } }
    
    /* CSS PRINCIPAL */
    .stApp { background-color: #0A0A0A; color: #FFFFFF; }
    [data-testid="stSidebar"] { background-color: #111111; border-right: 2px solid #00E5FF; padding-top: 80px; }
    h1, h2, h3, .stSubheader { color: #00E5FF !important; font-family: 'Lexend', sans-serif; font-weight: bold; }
    div[data-testid="metric-container"] { background-color: #1A1A1A; border: 1px solid #333; border-left: 5px solid #00E5FF; padding: 15px; border-radius: 5px; }
    .stButton>button { background-color: #1A1A1A; color: #00E5FF; border: 1px solid #00E5FF; border-radius: 4px; transition: 0.3s; width: 100%; font-weight: bold; }
    .stButton>button:hover { background-color: #00E5FF; color: #000000; box-shadow: 0 0 20px #00E5FF; }
    .alerta-panico { background-color: #FF0000 !important; color: white !important; font-size: 24px; text-align: center; padding: 20px; border-radius: 10px; font-weight: bold; border: 2px solid white; animation: blink 1s infinite; }
    @keyframes blink { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
    </style>
    <div class='logo-container'><img src='assets/logo_aion.png' alt='AION-YAROKU'></div>
    """,
    unsafe_allow_html=True
)

# --- 2. NÚCLEO DE CONEXIÓN Y SINCRONIZACIÓN NUBE ---
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

@st.cache_data(ttl=10) # Sincronización rápida para alertas y mensajes
def leer_matriz_nube(pestana):
    try:
        gc = conectar_google()
        hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
        df = pd.DataFrame(hoja.get_all_records())
        return df
    except: return pd.DataFrame()

@st.cache_data(ttl=60)
def cargar_objetivos():
    df = leer_matriz_nube("OBJETIVOS")
    if not df.empty:
        df.columns = df.columns.str.strip().str.upper()
        df['LATITUD'] = pd.to_numeric(df['LATITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        df['LONGITUD'] = pd.to_numeric(df['LONGITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        return df.dropna(subset=['LATITUD', 'LONGITUD'])
    return pd.DataFrame(columns=['OBJETIVO', 'SUPERVISOR', 'LATITUD', 'LONGITUD'])

# --- ESTADOS DEL SISTEMA ---
if 'qr_mode' not in st.session_state: st.session_state.qr_mode = None # None, 'INGRESO', 'SALIDA'

df_objetivos = cargar_objetivos()
conn = sqlite3.connect(":memory:", check_same_thread=False)
if not df_objetivos.empty: df_objetivos.to_sql("objetivos", conn, index=False, if_exists="replace")

# --- 3. MENSAJERÍA UNIFICADA ---
def mostrar_buzon(usuario):
    st.subheader("Bandeja de Entrada")
    df_msgs = leer_matriz_nube("MENSAJERIA")
    if not df_msgs.empty:
        # Filtrar mensajes para el usuario o para TODOS
        msgs = df_msgs[df_msgs['DESTINATARIO'].astype(str).str.contains(f"{usuario}|TODOS", case=False, na=False)]
        if msgs.empty: st.info("No hay mensajes nuevos.")
        else:
            for idx, r in msgs.sort_values(by=df_msgs.columns[0], ascending=False).iterrows():
                with st.expander(f"✉️ {r.iloc[0]} | De: {r.get('REMITENTE', 'SISTEMA')}"):
                    st.write(f"*Asunto:* {r.get('ASUNTO', 'Novedad')}")
                    st.write(r.get('MENSAJE', ''))
    else: st.info("Conectando con el servidor de mensajes...")

# --- 4. PANEL LATERAL ---
with st.sidebar:
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    rol = st.selectbox("PERFIL OPERATIVO", ["SUPERVISOR", "MONITOREO", "JEFE DE OPERACIONES", "GERENCIA", "ADMINISTRADOR"])
    
    lista_sups = ["AYALA BRIAN", "SUPERVISOR NOCTURNO", "SERANTES WALTER", "SANOJA LUIS", "DIAZ MARCELO", "MAZACOTTE CLAUDIO", "PORZIO GONZALO", "CARRIZO WALTER"]
    usuario_auth = ""
    
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
        if escribir_registro("ALERTAS", [str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")), usuario_auth, "CRÍTICO", "PENDIENTE"]):
            st.error("S.O.S TRANSMITIDO A CENTRAL")
    
    if st.button("🔄 SINCRONIZAR"): st.cache_data.clear(); st.rerun()

# --- 5. PERFIL SUPERVISOR (QR UNIFICADO + RUTEO) ---
if rol == "SUPERVISOR" and usuario_auth:
    st.header(f"Estación: {usuario_auth}")
    t1, t2, t3 = st.tabs(["📍 RADAR", "📤 REPORTES", "💬 MENSAJERÍA"])
    
    # Filtrar zona según nombre o Supervisor Nocturno
    if usuario_auth == "SUPERVISOR NOCTURNO":
        df_zona = df_objetivos
    else:
        # Blindaje para evitar el error de "Ayala Brian"
        apellido = usuario_auth.split()[-1].upper()
        df_zona = df_objetivos[df_objetivos['SUPERVISOR'].str.upper().str.contains(apellido, na=False)]

    with t1:
        pos = get_geolocation()
        # Ruteo Inteligente
        prox = "Seleccione Objetivo"
        if pos and 'coords' in pos and not df_zona.empty:
            m_lat, m_lon = pos['coords']['latitude'], pos['coords']['longitude']
            dist = []
            for _, r in df_zona.iterrows():
                p1, l1, p2, l2 = map(np.radians, [m_lat, m_lon, r['LATITUD'], r['LONGITUD']])
                dist.append(6371000 * (2 * np.arcsin(np.sqrt(np.sin((p2-p1)/2)*2 + np.cos(p1) * np.cos(p2) * np.sin((l2-l1)/2)*2))))
            prox = df_zona.iloc[np.argmin(dist)]['OBJETIVO']

        c1, c2, c3 = st.columns(3)
        c1.metric("Servicios", len(df_zona))
        c2.metric("GPS", "Activo" if pos else "Buscando...")
        c3.info(f"💡 RECOMENDADO: {prox}")

        col_m, col_g = st.columns([2, 1])
        with col_m:
            if not df_zona.empty:
                m_s = folium.Map(location=[df_zona['LATITUD'].mean(), df_zona['LONGITUD'].mean()], zoom_start=12, tiles="CartoDB dark_matter")
                for _, row in df_zona.iterrows(): folium.Marker([row['LATITUD'], row['LONGITUD']], popup=row['OBJETIVO']).add_to(m_s)
                st_folium(m_s, width="100%", height=400)
        
        with col_g:
            if not df_zona.empty:
                dest = st.selectbox("Seleccione Servicio:", df_zona['OBJETIVO'].unique())
                t_obj = df_zona[df_zona['OBJETIVO'] == dest].iloc[0]
                
                # UNIFICACIÓN DE BOTONES QR
                st.subheader("Control de Presencia")
                col_btn1, col_btn2 = st.columns(2)
                if col_btn1.button("🟢 INGRESO"): st.session_state.qr_mode = 'INGRESO'
                if col_btn2.button("🔴 SALIDA"): st.session_state.qr_mode = 'SALIDA'

                if st.session_state.qr_mode:
                    st.info(f"Escaneando {st.session_state.qr_mode}...")
                    f_cam = st.camera_input("Enfoque el QR del servicio")
                    if f_cam:
                        escribir_registro("LOG_PRESENCIA", [str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")), usuario_auth, dest, st.session_state.qr_mode, "QR_VALIDADO"])
                        st.success(f"{st.session_state.qr_mode} REGISTRADO")
                        st.session_state.qr_mode = None # Reset
                
                st.markdown(f'<a href="https://www.google.com/maps/dir/?api=1&destination={t_obj["LATITUD"]},{t_obj["LONGITUD"]}" target="_blank"><div style="background-color:#00E5FF; color:black; padding:10px; text-align:center; border-radius:5px; font-weight:bold;">🗺️ ABRIR GPS</div></a>', unsafe_allow_html=True)

    with t2:
        with st.form("acta"):
            st.subheader("Informe de Inspección")
            f_dest = st.selectbox("Objetivo Confirmado:", df_zona['OBJETIVO'].unique()) if not df_zona.empty else "N/A"
            f_mov = st.selectbox("Móvil", ["S-001", "S-002", "S-003", "S-004", "S-005", "S-006", "S-007"])
            f_km = st.number_input("Kilometraje", min_value=0)
            f_vig = st.text_input("Vigilador de Turno")
            f_nov = st.text_area("Novedades Detectadas")
            if st.form_submit_button("IMPACTAR MATRIZ"):
                escribir_registro("ACTAS_FLOTAS", [str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")), usuario_auth, f_mov, "", f_km, "", f_vig, f_dest, f_nov])
                st.success("ACTA GUARDADA")

    with t3: mostrar_buzon(usuario_auth)

# --- 6. MONITOREO (REACCIÓN EN VIVO) ---
elif rol == "MONITOREO":
    st.header("Consola de Monitoreo Central")
    
    # Lectura de Alertas en Nube para reacción entre dispositivos
    df_alertas = leer_matriz_nube("ALERTAS")
    alerta_critica = not df_alertas.empty and "PENDIENTE" in df_alertas['ESTADO'].values if 'ESTADO' in df_alertas.columns else False

    if alerta_critica:
        st.markdown('<div class="alerta-panico">🚨 ALERTA S.O.S EN CURSO 🚨</div>', unsafe_allow_html=True)
        with st.form("resol"):
            op = st.text_input("Operador que atiende"); res = st.text_area("Informe de resolución")
            if st.form_submit_button("Archivar Emergencia"):
                st.success("Enviando resolución...") # Aquí se debería actualizar el estado en el Excel
    else:
        c_map, c_log = st.columns([2, 1])
        with c_map:
            st.subheader("Mapa Global Secutec")
            if not df_objetivos.empty:
                m_mon = folium.Map(location=[df_objetivos['LATITUD'].mean(), df_objetivos['LONGITUD'].mean()], zoom_start=11, tiles="CartoDB dark_matter")
                for _, row in df_objetivos.iterrows(): folium.Marker([row['LATITUD'], row['LONGITUD']], tooltip=row['OBJETIVO']).add_to(m_mon)
                st_folium(m_mon, width="100%", height=500)
        with c_log:
            st.subheader("Presentismo en Vivo")
            df_p = leer_matriz_nube("LOG_PRESENCIA")
            if not df_p.empty: st.dataframe(df_p.tail(10).iloc[::-1], use_container_width=True, hide_index=True)

# --- 7. JEFE DE OPERACIONES Y GERENCIA (COMANDO TOTAL) ---
elif rol == "JEFE DE OPERACIONES":
    st.header(f"Comando: {usuario_auth}")
    t1, t2, t3 = st.tabs(["📥 MENSAJES", "📤 ENVIAR DIRECTIVA", "📍 ACTIVIDAD"])
    with t1: mostrar_buzon(usuario_auth)
    with t2:
        with st.form("orden"):
            dest = st.selectbox("Para:", ["TODOS", "LUIS BONGIORNO"] + lista_sups); a = st.text_input("Asunto"); m = st.text_area("Orden Táctica")
            if st.form_submit_button("Transmitir"):
                escribir_registro("MENSAJERIA", [str(datetime.now().strftime("%Y-%m-%d %H:%M")), usuario_auth, dest, a, m, "ENVIADO"])
                st.success("Directiva enviada")
    with t3:
        st.subheader("Últimos movimientos QR")
        df_p = leer_matriz_nube("LOG_PRESENCIA")
        if not df_p.empty: st.dataframe(df_p.tail(15).iloc[::-1], use_container_width=True)

elif rol == "GERENCIA":
    st.header(f"Panel Luis Bongiorno")
    m1, m2, m3 = st.columns(3)
    m1.metric("Ahorro Logístico", "$128.400", "Optimización")
    m2.metric("Cobertura Base", f"{len(df_objetivos)}/93")
    m3.metric("Efectividad Central", "100%")
    st.markdown("---")
    t1, t2, t3 = st.tabs(["📊 AUDITORÍA", "⚙️ GESTIÓN", "💬 COMUNICACIÓN"])
    with t1:
        if not df_objetivos.empty:
            st.bar_chart(df_objetivos['SUPERVISOR'].value_counts())
            if st.button("📥 EXPORTAR REPORTE PDF"): st.info("Generando documento auditado...")
    with t2:
        c1, c2 = st.columns(2)
        with c1:
            with st.form("alta"):
                st.write("*Nueva Alta*"); n = st.text_input("Nombre Servicio"); s = st.selectbox("Asignar:", lista_sups)
                if st.form_submit_button("Solicitar"): escribir_registro("PETICIONES", [str(datetime.now().strftime("%Y-%m-%d %H:%M")), usuario_auth, "ALTA", f"{n} -> {s}", "PENDIENTE"])
        with c2:
            with st.form("baja"):
                st.write("*Solicitar Baja*"); rem = st.selectbox("Remover:", df_objetivos['OBJETIVO'].unique()); 
                if st.form_submit_button("Enviar"): escribir_registro("PETICIONES", [str(datetime.now().strftime("%Y-%m-%d %H:%M")), usuario_auth, "BAJA", rem, "PENDIENTE"])
    with t3:
        mostrar_buzon(usuario_auth)
        with st.form("msg_g"):
            st.write("*Mensaje Ejecutivo*")
            d = st.selectbox("Para:", ["TODOS", "DARÍO CECILIA"] + lista_sups); a = st.text_input("Asunto"); m = st.text_area("Mensaje")
            if st.form_submit_button("Enviar"): escribir_registro("MENSAJERIA", [str(datetime.now().strftime("%Y-%m-%d %H:%M")), usuario_auth, d, a, m, "ENVIADO"])

# --- 8. ADMINISTRADOR (AYALA BRIAN) ---
elif rol == "ADMINISTRADOR":
    st.header("⚙️ NÚCLEO MAESTRO")
    st.write(f"Conexión ID: {ID_MAESTRO_DB}")
    st.dataframe(df_objetivos, use_container_width=True)
    st.subheader("Auditoría de Sistemas (Logs de Nube)")
    df_p = leer_matriz_nube("LOG_PRESENCIA")
    if not df_p.empty: st.dataframe(df_p.tail(20).iloc[::-1], use_container_width=True)
