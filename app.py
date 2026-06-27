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

# 1. ESTADO DE LOGIN
if 'usuario_logueado' not in st.session_state: 
    st.session_state.usuario_logueado = False

# 2. PANTALLA DE LOGIN (Si no estás logueada)
if not st.session_state.usuario_logueado:
    st.set_page_config(page_title="LOGIN AION", page_icon="🛡️")
    st.markdown("### 🔐 ACCESO AION-YAROKU")
    user = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")
    if st.button("ENTRAR"):
        if user == "admin" and password == "1234":
            st.session_state.usuario_logueado = True
            st.rerun()
        else:
            st.error("Credenciales incorrectas")
    st.stop() # <-- ESTO DETIENE TODO LO DE ABAJO HASTA QUE PONGAS LA CLAVE

# 3. SI PASÓ EL LOGIN, CARGA TU CÓDIGO ORIGINAL (INTENTO 1.txt)
# A partir de acá, pegá el resto de tu archivo INTENTO 1.txt (importaciones, funciones, roles...)
# No hace falta que esté dentro de un else, porque el st.stop() arriba ya lo protegió.
