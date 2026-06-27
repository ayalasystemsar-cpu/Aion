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
import qrcode

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="AION-YAROKU | COMMAND", page_icon="🛡️", layout="wide", initial_sidebar_state="expanded")

# --- 2. ESTADO INICIAL ---
if 'usuario_logueado' not in st.session_state: st.session_state.usuario_logueado = False
if 'rol_sel' not in st.session_state: st.session_state.rol_sel = "MONITOREO"
if 'user_sel' not in st.session_state: st.session_state.user_sel = "OPERADOR CENTRAL"
if 'sup_autenticado' not in st.session_state: st.session_state.sup_autenticado = False

ID_MAESTRO_DB = "1Md0VkOnwUJWldq0S1fB9UrmOKv4MG__JVG3tQsda0Uw"

# --- 3. FUNCIONES DE GOOGLE (Mantén tus funciones aquí) ---
def conectar_google():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        return gspread.authorize(creds)
    except: return None

def leer_matriz_nube(pestana):
    gc = conectar_google()
    if not gc: return pd.DataFrame()
    try:
        hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
        rows = hoja.get_all_values()
        if not rows: return pd.DataFrame()
        df = pd.DataFrame(rows[1:], columns=[str(h).strip().upper() for h in rows[0]])
        return df.loc[:, ~df.columns.duplicated()]
    except: return pd.DataFrame()

def escribir_registro_nube(pestana, datos_fila):
    gc = conectar_google()
    if gc:
        hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
        hoja.append_row(datos_fila)

def actualizar_celda(pestana, fila, columna, valor):
    gc = conectar_google()
    if gc:
        hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
        hoja.update_acell(f"{columna}{fila}", valor)

# --- 4. LANDING PAGE ---
def mostrar_landing():
    st.markdown("""<style>.stApp { background: radial-gradient(circle at top, #0A0F1E 0%, #030305 100%) !important; }</style>""", unsafe_allow_html=True)
    st.markdown('<div style="display:flex; justify-content:center;"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" width="400"></div>', unsafe_allow_html=True)
    st.markdown('<h1 style="color:#00E5FF; text-align:center;">AION-YAROKU | COMMAND</h1>', unsafe_allow_html=True)
    
    modo = st.radio("Acceso:", ["Iniciar Sesión", "Crear Cuenta"], horizontal=True)
    
    with st.form("form_unico"):
        user = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        rol = st.selectbox("Rol:", ["VIGILADOR", "MONITOREO", "JEFE DE OPERACIONES", "GERENCIA", "SUPERVISOR", "ADMINISTRADOR"])
        
        if st.form_submit_button("EJECUTAR"):
            if modo == "Iniciar Sesión":
                df = leer_matriz_nube("USUARIOS")
                usr = df[(df['USUARIO']==user) & (df['CONTRASEÑA']==password) & (df['ESTADO']=="APROBADO")]
                if not usr.empty:
                    st.session_state.usuario_logueado = True
                    st.session_state.user_sel = user
                    st.session_state.rol_sel = usr.iloc[0]['ROL']
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas o cuenta PENDIENTE.")
            else:
                escribir_registro_nube("USUARIOS", [user, password, rol, "PENDIENTE"])
                st.success("Solicitud enviada.")

# --- 5. CONTROL DE ACCESO ---
if not st.session_state.usuario_logueado:
    mostrar_landing()
    st.stop()

# --- 6. CORE DEL SISTEMA (Solo se carga si usuario_logueado es True) ---
# Aquí pegas todo tu código de Monitoreo, Mapas, Sidebars, etc.
# ESTE CÓDIGO NO SE DUPLICARÁ PORQUE EL st.stop() ARRIBA LO PROTEGE.
