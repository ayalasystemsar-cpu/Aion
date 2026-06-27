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
from streamlit_folium import st_folium
import math
import requests
from branca.element import Element

# 1. CONFIGURACIÓN ÚNICA
st.set_page_config(page_title="AION-YAROKU | COMMAND", page_icon="🛡️", layout="wide", initial_sidebar_state="expanded")

# 2. INICIALIZACIÓN
if 'usuario_logueado' not in st.session_state: st.session_state.usuario_logueado = False

# 3. PANTALLA DE LOGIN (CON EL DISEÑO QUE PEDISTE)
if not st.session_state.usuario_logueado:
    # Aplicamos el estilo oscuro de tu captura
    st.markdown("""
        <style>
        .stApp { background: radial-gradient(circle at top, #0A0F1E 0%, #030305 100%) !important; }
        .logo-login { display: block; margin-left: auto; margin-right: auto; width: 400px; border: 2px solid #00e5ff; }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<br><br>', unsafe_allow_html=True)
    st.image("https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg", use_container_width=False)
    st.markdown('<h1 style="text-align:center; color:#00E5FF; font-family:Orbitron;">AION-YAROKU | COMMAND</h1>', unsafe_allow_html=True)
    
    with st.form("form_acceso"):
        user = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        rol_usuario = st.selectbox("Seleccione su Rol:", ["VIGILADOR", "MONITOREO", "JEFE DE OPERACIONES", "GERENCIA", "ADMINISTRADOR"])
        if st.form_submit_button("ENTRAR"):
            if user == "admin" and password == "1234":
                st.session_state.usuario_logueado = True
                st.session_state.rol_sel = rol_usuario
                st.rerun()
            else: st.error("Credenciales incorrectas")
    st.stop() 

# 4. A PARTIR DE ACÁ, EL CÓDIGO OPERATIVO (INTENTO 1.txt)
# Solo se carga si usuario_logueado es True.
# [PEGÁ AQUÍ TODO TU CÓDIGO ORIGINAL DESDE LAS FUNCIONES HASTA EL FINAL]
