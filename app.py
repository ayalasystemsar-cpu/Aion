import streamlit as st
import datetime
from datetime import datetime
import pandas as pd
import pytz
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from streamlit_js_eval import get_geolocation
import folium
from folium.plugins import AntPath
from streamlit_folium import st_folium
import math

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="AION-YAROKU | CORE", page_icon="🛡️", layout="wide", initial_sidebar_state="expanded")

# --- 2. CONEXIONES Y FUNCIONES ---
ID_MAESTRO_DB = "1Md0VkOnwUJWldq0S1fB9UrmOKv4MG__JVG3tQsda0Uw"

def conectar_google():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        return gspread.authorize(creds)
    except: return None

def obtener_hora_argentina():
    tz = pytz.timezone("America/Argentina/Buenos_Aires")
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

def leer_matriz_nube(pestana):
    gc = conectar_google()
    try:
        hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
        data = hoja.get_all_records()
        return pd.DataFrame(data) if data else pd.DataFrame()
    except: return pd.DataFrame()

def escribir_registro_nube(pestana, datos_fila):
    gc = conectar_google()
    if gc:
        hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
        hoja.append_row(datos_fila)

def cargar_objetivos():
    df = leer_matriz_nube("OBJETIVOS")
    if not df.empty:
        df.columns = df.columns.str.strip().str.upper()
        df['LATITUD'] = pd.to_numeric(df['LATITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        df['LONGITUD'] = pd.to_numeric(df['LONGITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        return df
    return pd.DataFrame()

# [AQUÍ MANTIENES TU IDENTIDAD VISUAL (APLICAR_IDENTIDAD_ALFA) Y SIDEBAR QUE YA TENÍAS]
# (Como no quería borrar tu CSS, asegúrate de mantener esa parte arriba)

# --- 7. FLUJO POR ROLES (CORREGIDO Y COMPLETO) ---
df_objetivos = cargar_objetivos()

# A. ROL: MONITOREO
if st.session_state.rol_sel == "MONITOREO":
    st.markdown('<div class="estacion-titulo">🛰️ CENTRAL DE INTELIGENCIA OPERATIVA</div>', unsafe_allow_html=True)
    df_emergencias = leer_matriz_nube("ALERTAS")
    sos_pendientes = df_emergencias[df_emergencias['ESTADO'].astype(str).str.upper() == 'PENDIENTE'] if not df_emergencias.empty else pd.DataFrame()
    
    t_radar, t_gestion, t_com, t_pres = st.tabs(["🚨 RADAR S.O.S", "📖 LIBRO", "💬 COMUNICACIÓN", "📋 PRESENTISMO"])
    
    with t_radar:
        m = folium.Map(location=[-34.6, -58.4], zoom_start=13, tiles="CartoDB dark_matter")
        for _, r in df_objetivos.iterrows():
            # Lógica: circulito rojo si hay pánico pendiente, azul si está normal
            es_panico = not sos_pendientes.empty and any(sos_pendientes['CARGA_UTIL'].str.contains(str(r['OBJETIVO'])))
            folium.CircleMarker(
                [r['LATITUD'], r['LONGITUD']],
                radius=10 if es_panico else 7,
                color="red" if es_panico else "#00E5FF",
                fill=True,
                popup=r['OBJETIVO']
            ).add_to(m)
        st_folium(m, width="100%", height=450)

    with t_gestion:
        st.dataframe(df_emergencias.iloc[::-1] if not df_emergencias.empty else pd.DataFrame(), use_container_width=True)

# B. ROL: JEFE DE OPERACIONES
elif st.session_state.rol_sel == "JEFE DE OPERACIONES":
    st.markdown('<div class="estacion-titulo">📋 COMANDO DE OPERACIONES TÁCTICAS</div>', unsafe_allow_html=True)
    # [PEGA AQUÍ EL RESTO DE TU CÓDIGO ORIGINAL DE JEFE]

# C. ROL: SUPERVISOR
elif st.session_state.rol_sel == "SUPERVISOR":
    if st.session_state.sup_autenticado:
        st.markdown(f'<div class="estacion-titulo">📱 Control: {st.session_state.user_sel}</div>', unsafe_allow_html=True)
        # [PEGA AQUÍ TODO TU CÓDIGO ORIGINAL DE SUPERVISOR]

# D. ROL: GERENCIA
elif st.session_state.rol_sel == "GERENCIA":
    st.markdown('<div class="estacion-titulo">🏢 DIRECCIÓN GENERAL</div>', unsafe_allow_html=True)
    # [PEGA AQUÍ TU CÓDIGO ORIGINAL DE GERENCIA]

# E. ROL: ADMINISTRADOR
elif st.session_state.rol_sel == "ADMINISTRADOR":
    st.markdown('<div class="titulo-seccion-admin">⚙️ NÚCLEO MAESTRO</div>', unsafe_allow_html=True)
    # [PEGA AQUÍ TU CÓDIGO ORIGINAL DE ADMIN]
