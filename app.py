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

# --- 1. CONFIGURACIÓN E INICIALIZACIÓN ---
st.set_page_config(page_title="AION-YAROKU | COMMAND", page_icon="🛡️", layout="wide", initial_sidebar_state="expanded")

if 'usuario_logueado' not in st.session_state: st.session_state.usuario_logueado = False
if 'rol_sel' not in st.session_state: st.session_state.rol_sel = "MONITOREO"
if 'user_sel' not in st.session_state: st.session_state.user_sel = "OPERADOR CENTRAL"
if 'sup_autenticado' not in st.session_state: st.session_state.sup_autenticado = False

# --- 2. FLUJO PRINCIPAL ---
if not st.session_state.usuario_logueado:
    # AQUI VA TU LANDING (mostrar_landing)
    if st.button("ACCEDER AL COMANDO"):
        st.session_state.usuario_logueado = True
        st.rerun()

if st.session_state.usuario_logueado:
    # SIDEBAR
    with st.sidebar:
        if st.button("🛰️ MONITOREO"): st.session_state.rol_sel = "MONITOREO"; st.rerun()
        if st.button("📋 JEFE DE OPERACIONES"): st.session_state.rol_sel = "JEFE DE OPERACIONES"; st.rerun()
        if st.button("🏢 GERENCIA"): st.session_state.rol_sel = "GERENCIA"; st.rerun()
        if st.button("👤 VIGILADOR"): st.session_state.rol_sel = "VIGILADOR"; st.rerun()
        if st.button("⚙️ ADMINISTRADOR"): st.session_state.rol_sel = "ADMINISTRADOR"; st.rerun()

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
