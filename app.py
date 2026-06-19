import streamlit as st
import datetime
from datetime import datetime
import pandas as pd
import pytz
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from streamlit_js_eval import get_geolocation
import osmnx as ox
import networkx as nx
import folium
from folium.plugins import AntPath
from streamlit_folium import st_folium
import math
import requests
from branca.element import Element

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="AION-YAROKU | CORE", page_icon="🛡️", layout="wide")

ID_MAESTRO_DB = "1Md0VkOnwUJWldq0S1fB9UrmOKv4MG__JVG3tQsda0Uw"

# --- 2. FUNCIONES DE CONEXIÓN Y DATOS ---
def conectar_google():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        return gspread.authorize(creds)
    except: return None

def obtener_hora_argentina():
    tz = pytz.timezone("America/Argentina/Buenos_Aires")
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

def escribir_registro_nube(pestana, datos_fila):
    try:
        gc = conectar_google()
        if gc:
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
            hoja.append_row(datos_fila)
            return True
    except: return False

@st.cache_data(ttl=60) 
def leer_matriz_nube(pestana):
    gc = conectar_google()
    if gc:
        try:
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
            todas = hoja.get_all_values()
            if not todas: return pd.DataFrame()
            return pd.DataFrame(todas[1:], columns=[str(h).strip().upper() for h in todas[0]])
        except: return pd.DataFrame()
    return pd.DataFrame()

@st.cache_data(ttl=60)
def cargar_objetivos():
    df = leer_matriz_nube("OBJETIVOS")
    if not df.empty:
        df.columns = df.columns.str.strip().str.upper()
        df['LATITUD'] = pd.to_numeric(df['LATITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        df['LONGITUD'] = pd.to_numeric(df['LONGITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        return df 
    return pd.DataFrame()

# --- 3. DISEÑO E IDENTIDAD ---
def aplicar_identidad():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@300;500;700&display=swap');
        .stApp { background: radial-gradient(circle at top, #0A0F1E 0%, #030305 100%) !important; color: #E0E0E0; font-family: 'Rajdhani', sans-serif; }
        .estacion-titulo { font-family: 'Orbitron', sans-serif; color: #00E5FF !important; font-size: 24px; margin-top: 15px; display: flex; align-items: center; justify-content: center; gap: 12px; text-shadow: 0 0 15px rgba(0, 229, 255, 0.4); letter-spacing: 2px; text-transform: uppercase; }
        .panel-novedad { border: 1px solid #333; border-radius: 8px; padding: 15px; margin-top: 20px; background-color: rgba(10, 10, 11, 0.9); }
        </style>
        """, unsafe_allow_html=True)
aplicar_identidad()

# --- 4. SIDEBAR ---
if 'rol_sel' not in st.session_state: st.session_state.rol_sel = "MONITOREO"
df_objetivos = cargar_objetivos()

with st.sidebar:
    if st.button("🛰️ MONITOREO"): st.session_state.rol_sel = "MONITOREO"; st.rerun()
    if st.button("📋 JEFE DE OPERACIONES"): st.session_state.rol_sel = "JEFE DE OPERACIONES"; st.rerun()
    if st.button("🏢 GERENCIA"): st.session_state.rol_sel = "GERENCIA"; st.rerun()

# --- 5. LÓGICA POR ROL ---
if st.session_state.rol_sel == "JEFE DE OPERACIONES":
    st.markdown('<div class="estacion-titulo">📋 COMANDO DE OPERACIONES TÁCTICAS</div>', unsafe_allow_html=True)
    
    t_crisis, t_ejecucion, t_auditoria = st.tabs(["Centro de Crisis", "Ejecución", "Auditoría"])
    
    with t_crisis:
        m = folium.Map(location=[-34.6, -58.4], zoom_start=12, tiles="CartoDB dark_matter")
        for _, r in df_objetivos.dropna(subset=['LATITUD', 'LONGITUD']).iterrows():
            folium.Marker([r['LATITUD'], r['LONGITUD']], popup=r['OBJETIVO'], icon=folium.Icon(color="blue", icon="shield")).add_to(m)
        
        mapa = st_folium(m, width="100%", height=400)
        obj_click = mapa.get("last_object_clicked_popup", "").strip().upper() if mapa else None
        
        if obj_click:
            st.markdown(f"### 📊 AUDITORÍA: {obj_click}")
            sup_resp = df_objetivos[df_objetivos['OBJETIVO'] == obj_click]['SUPERVISOR'].iloc[0] if not df_objetivos[df_objetivos['OBJETIVO'] == obj_click].empty else "N/A"
            
            c1, c2 = st.columns([1, 2])
            with c1:
                st.markdown('<div class="panel-novedad">', unsafe_allow_html=True)
                # Corrección aplicada aquí
                st.markdown(f"**👤 SUPERVISOR:**<br><span style=\"color:#00E5FF; font-family:'Orbitron'; font-size:16px;\">{sup_resp}</span>", unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            with c2:
                st.markdown('<div class="panel-novedad">', unsafe_allow_html=True)
                st.markdown("**🔄 NOVEDADES:**", unsafe_allow_html=True)
                df_nov = leer_matriz_nube("NOVEDADES_GUARDIA")
                if not df_nov.empty:
                    df_nov.columns = df_nov.columns.str.strip().str.upper()
                    st.dataframe(df_nov[df_nov['OBJETIVO'] == obj_click].tail(5), use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)

    with t_ejecucion:
        st.markdown('<div class="panel-novedad">', unsafe_allow_html=True)
        if st.button("ELEVAR PETICIÓN"): escribir_registro_nube("PETICIONES", [obtener_hora_argentina(), "JEFE", "PETICION", "GENERAL", "NUEVA"])
        st.markdown('</div>', unsafe_allow_html=True)

    with t_auditoria:
        st.dataframe(leer_matriz_nube("ACTAS_FLOTAS").tail(20), use_container_width=True)

elif st.session_state.rol_sel == "GERENCIA":
    st.markdown('<div class="estacion-titulo">🏢 DIRECCIÓN ESTRATÉGICA</div>', unsafe_allow_html=True)
    # Lógica de Gerencia simplificada para mantener alineación
    if st.button("TRANSMITIR DIRECTIVA"): escribir_registro_nube("CHATS", [obtener_hora_argentina(), "GERENCIA", "ORDEN GLOBAL", "ROJA", "TODOS", "ASUNTO"])

elif st.session_state.rol_sel == "ADMINISTRADOR":
    u_ing = st.text_input("ADMIN_USER")
    p_ing = st.text_input("ADMIN_PASS", type="password")
    if u_ing == "admin" and p_ing == "aion2026": st.success("Acceso Concedido")
