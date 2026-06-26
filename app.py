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


# --- 2. FLUJO POR ROLES ---
    if st.session_state.rol_sel == "MONITOREO":
        # ... (Tu código de Monitoreo que ya teníamos) ...
        col1, col2, col3, col4 = st.columns(4)
        
        # --- CARGA DE DATOS ---
        df_emergencias = leer_matriz_nube("ALERTAS")
        df_objetivos = cargar_objetivos()
        
        # --- LIMPIEZA DE DATOS ---
        if not df_emergencias.empty:
            df_emergencias.columns = df_emergencias.columns.str.strip().str.upper()
        else:
            df_emergencias = pd.DataFrame(columns=['FECHA', 'USUARIO', 'TIPO', 'ESTADO', 'CARGA_UTIL', 'INFORME'])

        # --- MAPA Y CORRECCIÓN DE NUMÉRICOS ---
        df_mapa_monitoreo = pd.DataFrame()
        if not df_objetivos.empty:
            df_objetivos.columns = df_objetivos.columns.str.strip().str.upper()
            if 'LATITUD' in df_objetivos.columns and 'LONGITUD' in df_objetivos.columns:
                df_mapa_monitoreo = df_objetivos.dropna(subset=['LATITUD', 'LONGITUD']).copy()
                df_mapa_monitoreo['LATITUD'] = pd.to_numeric(df_mapa_monitoreo['LATITUD'], errors='coerce')
                df_mapa_monitoreo['LONGITUD'] = pd.to_numeric(df_mapa_monitoreo['LONGITUD'], errors='coerce')
                df_mapa_monitoreo = df_mapa_monitoreo.dropna(subset=['LATITUD', 'LONGITUD'])

        # --- LÓGICA DE PÁNICOS ---
        sos_activos = 0
        if 'ESTADO' in df_emergencias.columns:
            sos_activos = len(df_emergencias[df_emergencias['ESTADO'].astype(str).str.upper() == 'PENDIENTE'])

        # --- 1. CABECERA Y MÉTRICAS ---
        with col1.container():
            @st.fragment(run_every=5)
            def contar_panicos():
                df = leer_matriz_nube("ALERTAS")
                total = len(df[df['ESTADO'].astype(str).str.upper() == "PENDIENTE"]) if not df.empty else 0
                st.metric("🚨 S.O.S ACTIVOS", total)
            contar_panicos()

        col2.metric("📡 RED", "OPERATIVA")
        col3.metric("👤 OPERADOR", f"{st.session_state.user_sel}")
        with col4.container():
            @st.fragment(run_every=1)
            def reloj():
                st.metric("🕒 HORA LOCAL", obtener_hora_argentina().split(" ")[1])
            reloj()

        # --- 2. TABS Y RADAR ---
        label_msg = "💬 MENSAJERÍA GLOBAL"
        t_radar, t_mensajeria, t_vig, t_nov = st.tabs(["🚨 RADAR S.O.S", label_msg, "👥 PADRÓN VIGILADORES", "🔄 NOVEDADES Y FICHAJES"]) 
        
        with t_radar:
            st.subheader("📡 RADAR GLOBAL DE OBJETIVOS")
            if st.button("🔄 ACTUALIZAR"): st.rerun()
            st.markdown('<div class="panel-novedad">', unsafe_allow_html=True)
            st.info("Radar operativo. Seleccione un objetivo para analizar.")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with t_mensajeria:
            renderizar_mensajeria_global("MONITOREO")
            
        with t_vig:
            st.subheader("👥 PADRÓN VIGILADORES")
            df_p = leer_matriz_nube("VIGILADORES")
            if not df_p.empty: st.dataframe(df_p.iloc[::-1], use_container_width=True)
            
        with t_nov:
            st.subheader("🔄 HISTORIAL")
            df_n = leer_matriz_nube("NOVEDADES_GUARDIA")
            if not df_n.empty: st.dataframe(df_n, use_container_width=True)
        
        st.write("Panel de Monitoreo cargado.")
        
    elif st.session_state.rol_sel == "SUPERVISOR":
        # Código de Supervisor
        if st.session_state.sup_autenticado:
            st.subheader("⏱️ GESTIÓN DE JORNADA")
            # ... (Tu código de Supervisor) ...
        else:
            st.warning("⚠️ Autenticación de Supervisor requerida.")

    elif st.session_state.rol_sel == "VIGILADOR":
        # ... (Tu código de Vigilador) ...
        st.write("Panel de Vigilador cargado.")

    elif st.session_state.rol_sel == "JEFE DE OPERACIONES":
        # ... (Tu código de Jefe) ...
        st.write("Panel de Jefe cargado.")

    elif st.session_state.rol_sel == "GERENCIA":
        # ... (Tu código de Gerencia) ...
        st.write("Panel de Gerencia cargado.")

    elif st.session_state.rol_sel == "ADMINISTRADOR":
        # ... (Tu código de Admin) ...
        st.subheader("⚙️ ACCESO AL NÚCLEO MAESTRO")
        if 'admin_desbloqueado' not in st.session_state: st.session_state.admin_desbloqueado = False
        
        if not st.session_state.admin_desbloqueado:
            u_ing = st.text_input("ADMIN_USER")
            p_ing = st.text_input("ADMIN_PASS", type="password")
            if st.button("DESBLOQUEAR NÚCLEO"):
                if u_ing == "admin" and p_ing == "aion2026": 
                    st.session_state.admin_desbloqueado = True
                    st.rerun()
                else: st.error("❌ Credenciales incorrectas.")
        else:
            st.success("✅ Núcleo Maestro desbloqueado.")
            if st.button("🔒 BLOQUEAR NÚCLEO"):
                st.session_state.admin_desbloqueado = False
                st.rerun()
