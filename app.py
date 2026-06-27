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

# 1. INICIALIZACIÓN DE SESIÓN (OBLIGATORIO)
if 'usuario_logueado' not in st.session_state:
    st.session_state.usuario_logueado = False

# --- AQUÍ VA TU PANTALLA DE LOGIN ---
if not st.session_state.usuario_logueado:
    st.set_page_config(page_title="LOGIN AION", page_icon="🔒")
    st.markdown("### 🔐 ACCESO RESTRINGIDO AION-YAROKU")
    user = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")
    if st.button("INGRESAR"):
        if user == "admin" and password == "1234":
            st.session_state.usuario_logueado = True
            st.rerun()
        else:
            st.error("Credenciales incorrectas")
    st.stop() # Esto detiene el resto del código hasta que se loguee

# --- SI LLEGA HASTA ACÁ, ES PORQUE EL LOGIN FUE EXITOSO ---
# AHORA PEGÁS TODO TU CÓDIGO ORIGINAL DESDE EL "set_page_config" HASTA EL FINAL
# (Como ya se ejecutó el set_page_config arriba, no pongas otro aquí)

st.set_page_config(page_title="AION-YAROKU | COMMAND", page_icon="🛡️", layout="wide", initial_sidebar_state="expanded")

# ... (PEGÁ AQUÍ TODO TU CÓDIGO TÁCTICO DE INTENTO 1.TXT) ...
# ... (DESDE LAS FUNCIONES, LOS MAPAS, HASTA EL FINAL) ...
