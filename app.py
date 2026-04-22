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

st.markdown("""
    <style>
    .stApp { background-color: #0A0A0A; color: #FFFFFF; }
    [data-testid="stSidebar"] { background-color: #111111; border-right: 2px solid #00E5FF; }
    h1, h2, h3, .stSubheader { color: #00E5FF !important; font-family: 'Lexend', sans-serif; font-weight: bold; }
    div[data-testid="metric-container"] {
        background-color: #1A1A1A; border: 1px solid #333; border-left: 5px solid #00E5FF; padding: 15px; border-radius: 5px;
    }
    .stButton>button {
        background-color: #1A1A1A; color: #00E5FF; border: 1px solid #00E5FF; border-radius: 4px; transition: 0.3s; width: 100%; font-weight: bold;
    }
    .stButton>button:hover { background-color: #00E5FF; color: #000000; box-shadow: 0 0 20px #00E5FF; }
    .alerta-panico { background-color: #FF0000 !important; color: white !important; font-size: 24px; text-align: center; padding: 20px; border-radius: 10px; font-weight: bold; border: 2px solid white; animation: blink 1s infinite; }
    @keyframes blink { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
    </style>
    """, unsafe_allow_html=True)

# --- 2. NÚCLEO DE CONEXIÓN (GOOGLE CLOUD + MAESTRO DB) ---
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
    except Exception as e:
        st.error(f"Falla de enlace: {e}")
        return False

@st.cache_data(ttl=60)
def cargar_matriz_objetivos():
    try:
        gc = conectar_google()
        hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet("OBJETIVOS")
        df = pd.DataFrame(hoja.get_all_records())
        df['LATITUD'] = pd.to_numeric(df['LATITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        df['LONGITUD'] = pd.to_numeric(df['LONGITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        return df.dropna(subset=['LATITUD', 'LONGITUD'])
    except:
        return pd.DataFrame()

# Inicialización de Estados Dinámicos
if 'alerta_activa' not in st.session_state: st.session_state.alerta_activa = False
if 'db_mensajes' not in st.session_state: 
    st.session_state.db_mensajes = pd.DataFrame(columns=['ID', 'FECHA', 'REMITENTE', 'DESTINATARIO', 'ASUNTO', 'MENSAJE', 'ESTADO'])

df_objetivos = cargar_matriz_objetivos()

# Motor Analítico SQL (Procesamiento en Memoria)
conn = sqlite3.connect(":memory:", check_same_thread=False)
if not df_objetivos.empty:
    df_objetivos.to_sql("objetivos", conn, index=False, if_exists="replace")

# --- 3. SISTEMA DE COMUNICACIONES ---
def enviar_msg(rem, dest, asun, texto):
    nuevo = pd.DataFrame([{'ID': len(st.session_state.db_mensajes)+1, 'FECHA': datetime.now().strftime("%H:%M"), 'REMITENTE': rem, 'DESTINATARIO': dest, 'ASUNTO': asun, 'MENSAJE': texto, 'ESTADO': 'NO LEÍDO'}])
    st.session_state.db_mensajes = pd.concat([st.session_state.db_mensajes, nuevo], ignore_index=True)
    escribir_registro("MENSAJERIA", [str(datetime.now()), rem, dest, asun, texto, "NO LEÍDO"])

def buzon_entrada(usuario):
    msgs = st.session_state.db_mensajes[st.session_state.db_mensajes['DESTINATARIO'].isin([usuario, 'TODOS'])]
    if msgs.empty: st.info("Bandeja vacía.")
    else:
        for idx, r in msgs.sort_values(by='ID', ascending=False).iterrows():
            with st.expander(f"{'🔴' if r['ESTADO'] == 'NO LEÍDO' else '🟢'} [{r['FECHA']}] De: {r['REMITENTE']} | {r['ASUNTO']}"):
                st.write(r['MENSAJE'])
                if r['ESTADO'] == 'NO LEÍDO' and st.button("CORROBORADO", key=f"m_{idx}"):
                    st.session_state.db_mensajes.at[idx, 'ESTADO'] = "LEÍDO"
                    st.rerun()

# --- 4. INTERFAZ DE MANDO ---
with st.sidebar:
    st.title("AION-YAROKU")
    rol = st.selectbox("PERFIL OPERATIVO", ["SUPERVISOR", "MONITOREO", "JEFE DE OPERACIONES", "GERENCIA", "ADMINISTRADOR"])
    
    usuario_auth = ""
    lista_sups = ["AYALA BRIAN", "SERANTES WALTER", "SANOJA LUIS", "DIAZ MARCELO", "MAZACOTTE CLAUDIO", "PORZIO GONZALO", "CARRIZO WALTER"]
    
    if rol == "SUPERVISOR": usuario_auth = st.selectbox("IDENTIFICACIÓN", lista_sups)
    elif rol == "JEFE DE OPERACIONES": usuario_auth = "DARÍO CECILIA"
    elif rol == "GERENCIA": usuario_auth = "LUIS BONGIORNO"
    elif rol == "MONITOREO": usuario_auth = "CENTRAL MONITOREO"
    elif rol == "ADMINISTRADOR":
        clave = st.text_input("PASSWORD DE SISTEMA", type="password")
        if clave == st.secrets.get("admin_password", "aion2026"): usuario_auth = "AYALA BRIAN (ADMIN)"
        elif clave != "": st.stop()

    st.markdown("---")
    if st.button("🚨 ACTIVAR PÁNICO", use_container_width=True):
        st.session_state.alerta_activa = True
        escribir_registro("ALERTAS", [str(datetime.now()), usuario_auth, "CRÍTICO", "PENDIENTE"])
        st.error("S.O.S TRANSMITIDO A CENTRAL")

# --- 5. LÓGICA DE SUPERVISIÓN (TERRENO) ---
if rol == "SUPERVISOR" and usuario_auth:
    st.header(f"Estación de Control: {usuario_auth}")
    tab1, tab2 = st.tabs(["📍 RADAR", "📤 REPORTES"])
    
    with tab1:
        apellido = usuario_auth.split()[-1].upper()
        df_zona = df_objetivos[df_objetivos['SUPERVISOR'].str.upper().str.contains(apellido, na=False)]
        
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
                maps_url = f"https://www.google.com/maps/dir/?api=1&destination={t_obj['LATITUD']},{t_obj['LONGITUD']}"
                st.markdown(f'<a href="{maps_url}" target="_blank"><div style="background-color:#00E5FF; color:black; padding:10px; text-align:center; border-radius:5px; font-weight:bold;">🗺️ GPS MAPS</div></a>', unsafe_allow_html=True)
                
                # Geocerca 150m (Fórmula Haversine)
                pos = get_geolocation()
                bloqueo = True
                if pos and 'coords' in pos:
                    m_lat, m_lon = pos['coords']['latitude'], pos['coords']['longitude']
                    p1, l1, p2, l2 = map(np.radians, [m_lat, m_lon, t_obj['LATITUD'], t_obj['LONGITUD']])
                    d = 6371000 * (2 * np.arcsin(np.sqrt(np.sin((p2-p1)/2)*2 + np.cos(p1) * np.cos(p2) * np.sin((l2-l1)/2)*2)))
                    if d <= 150:
                        st.success(f"🎯 LOCALIZADO ({int(d)}m)")
                        bloqueo = False
                    else: st.warning(f"📡 FUERA DE RANGO ({round(d/1000, 2)}km)")
                else: st.info("Sincronizando GPS...")

    with tab2:
        with st.form("form_registro"):
            st.subheader("Acta de Inspección")
            f_movil = st.selectbox("Móvil", ["S-001", "S-002", "S-003", "S-004", "S-005", "S-006", "S-007"])
            f_km = st.number_input("Kilometraje", min_value=0, step=1)
            f_vig = st.text_input("Vigilador Controlado")
            f_nov = st.text_area("Novedades de la Visita")
            f_foto = st.camera_input("Evidencia")
            
            if st.form_submit_button("IMPACTAR MATRIZ", disabled=bloqueo):
                if escribir_registro("ACTAS_FLOTAS", [str(datetime.now()), usuario_auth, f_movil, "", f_km, "", f_vig, dest, f_nov]):
                    st.success("Acta registrada correctamente.")

# --- 6. MONITOREO Y GERENCIA ---
elif rol == "MONITOREO":
    st.header("Consola Global de Monitoreo")
    if st.session_state.alerta_activa:
        st.markdown('<div class="alerta-panico">🚨 ALERTA ACTIVA 🚨</div>', unsafe_allow_html=True)
        if st.button("Neutralizar y Archivar Alerta"):
            st.session_state.alerta_activa = False
            st.rerun()
    else:
        m_mon = folium.Map(location=[df_objetivos['LATITUD'].mean(), df_objetivos['LONGITUD'].mean()], zoom_start=11, tiles="CartoDB dark_matter")
        for _, row in df_objetivos.iterrows(): folium.Marker([row['LATITUD'], row['LONGITUD']], tooltip=row['OBJETIVO']).add_to(m_mon)
        st_folium(m_mon, width="100%", height=500)

elif rol == "GERENCIA":
    st.header(f"Tablero Ejecutivo: {usuario_auth}")
    st.subheader("Auditoría de Servicios")
    res_sql = pd.read_sql_query("SELECT SUPERVISOR, COUNT(*) as Servicios FROM objetivos GROUP BY SUPERVISOR", conn)
    st.dataframe(res_sql, use_container_width=True)
    st.download_button("Descargar Auditoría", res_sql.to_csv(index=False), "auditoria_yaroku.csv")

# --- 7. ADMINISTRADOR ---
elif rol == "ADMINISTRADOR":
    st.header("⚙️ NÚCLEO AION-YAROKU")
    st.write(f"Conexión con ID: {ID_MAESTRO_DB}")
    if st.button("Forzar Sincronización Real-Time"):
        st.cache_data.clear()
        st.rerun()
    st.dataframe(df_objetivos, use_container_width=True)
