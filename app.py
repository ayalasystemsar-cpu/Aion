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

# --- 1. CONFIGURACIÓN E INICIALIZACIÓN ---
st.set_page_config(page_title="AION-YAROKU | COMMAND", page_icon="🛡️", layout="wide", initial_sidebar_state="expanded")

if 'usuario_logueado' not in st.session_state: st.session_state.usuario_logueado = False
if 'rol_sel' not in st.session_state: st.session_state.rol_sel = "MONITOREO"
if 'user_sel' not in st.session_state: st.session_state.user_sel = "OPERADOR CENTRAL"
if 'sup_autenticado' not in st.session_state: st.session_state.sup_autenticado = False

# --- 2. FUNCIONES DE LÓGICA Y GOOGLE ---
ID_MAESTRO_DB = "1Md0VkOnwUJWldq0S1fB9UrmOKv4MG__JVG3tQsda0Uw"

def conectar_google():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        return gspread.authorize(creds)
    except: return None

def escribir_registro_nube(pestana, datos_fila):
    try:
        gc = conectar_google()
        if gc:
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
            hoja.append_row(datos_fila)
            return True
    except: return False

def leer_matriz_nube(pestana):
    gc = conectar_google()
    if gc:
        try:
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
            todas_filas = hoja.get_all_values()
            if not todas_filas: return pd.DataFrame()
            encabezados = [str(h).strip().upper() for h in todas_filas[0]]
            df = pd.DataFrame(todas_filas[1:], columns=encabezados)
            df.columns = [str(c).strip().upper() for c in df.columns]
            return df.loc[:, ~df.columns.duplicated()]
        except: return pd.DataFrame()
    return pd.DataFrame()

def cargar_objetivos(): return leer_matriz_nube("OBJETIVOS")
def cargar_datos_comisarias(): return leer_matriz_nube("COMISARIAS")
def obtener_hora_argentina():
    tz = pytz.timezone("America/Argentina/Buenos_Aires")
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

# --- 3. IDENTIDAD Y LANDING ---
def aplicar_identidad_alfa():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@300;500;700&display=swap');
        .stApp { background: radial-gradient(circle at top, #0A0F1E 0%, #030305 100%) !important; color: #E0E0E0; font-family: 'Rajdhani', sans-serif; }
        .contenedor-logo-central { display: flex; justify-content: center; align-items: center; width: 100%; margin: 20px 0; }
        .logo-phoenix { width: 400px !important; border: 2px solid #00e5ff !important; box-shadow: 0 0 35px rgba(0, 229, 255, 0.5) !important; border-radius: 4px !important; background-color: #000 !important; }
        .estacion-titulo { font-family: 'Orbitron', sans-serif; color: #00E5FF !important; font-size: 32px; text-align: center; text-shadow: 0 0 15px rgba(0, 229, 255, 0.4); margin-bottom: 30px; }
        </style>
    """, unsafe_allow_html=True)

def mostrar_landing():
    aplicar_identidad_alfa()
    st.markdown('<div class="contenedor-logo-central"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" class="logo-phoenix"></div>', unsafe_allow_html=True)
    st.markdown('<div class="estacion-titulo">AION-YAROKU | COMMAND</div>', unsafe_allow_html=True)
    if st.button("ACCEDER AL COMANDO", type="primary", use_container_width=True):
        st.session_state.usuario_logueado = True
        st.rerun()

# --- 4. LÓGICA PRINCIPAL ---
if not st.session_state.usuario_logueado:
    mostrar_landing()

# ELIMINAMOS EL 'ELSE' AQUÍ para que los 'if/elif' funcionen libremente

if st.session_state.usuario_logueado:
    # 1. CARGA DE DATOS Y SIDEBAR
    df_objetivos = cargar_objetivos()
    df_comisarias = cargar_datos_comisarias()
    LISTA_SUPS_TACTICOS = ["AYALA BRIAN", "SUPERVISOR 1", "SUPERVISOR 2", "SUPERVISOR 3", "SUPERVISOR 4", "SUPERVISOR 5", "SUPERVISOR NOCTURNO"]

    # --- SIDEBAR ---
    with st.sidebar:
        st.markdown('<div class="contenedor-logo-sidebar"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" style="width:180px; border:1px solid #00e5ff; border-radius:4px;"></div>', unsafe_allow_html=True)
        st.subheader("🛡️ PANEL DE CONTROL")
        
        if st.button("🛰️ MONITOREO", use_container_width=True):
            st.session_state.rol_sel = "MONITOREO"; st.session_state.user_sel = "OPERADOR CENTRAL"; st.rerun()
        if st.button("📋 JEFE DE OPERACIONES", use_container_width=True):
            st.session_state.rol_sel = "JEFE DE OPERACIONES"; st.rerun()
        if st.button("🏢 GERENCIA", use_container_width=True):
            st.session_state.rol_sel = "GERENCIA"; st.rerun()
        
        st.write("---")
        st.button("🚪 CERRAR SESIÓN", on_click=lambda: setattr(st.session_state, 'usuario_logueado', False), use_container_width=True)



