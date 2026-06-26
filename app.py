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
        .stButton > button { background-color: #0A192F !important; color: #00E5FF !important; border: 1px solid #00E5FF !important; border-radius: 5px !important; font-family: 'Orbitron', sans-serif !important; }
        .stButton > button:hover { background-color: #00E5FF !important; color: #000 !important; }
        </style>
    """, unsafe_allow_html=True)

def mostrar_landing():
    aplicar_identidad_alfa()
    st.markdown('<div class="contenedor-logo-central"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" class="logo-phoenix"></div>', unsafe_allow_html=True)
    st.markdown('<div class="estacion-titulo">AION-YAROKU | COMMAND</div>', unsafe_allow_html=True)
    
    # Selector de Modo
    modo = st.radio("Acceso al Sistema:", ["Iniciar Sesión", "Crear Cuenta"], horizontal=True)
    
    with st.form("form_acceso"):
        user = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        # Nuevo campo para seleccionar el rol
        rol_usuario = st.selectbox("Seleccione su Rol:", 
                                   ["VIGILADOR", "MONITOREO", "JEFE DE OPERACIONES", "GERENCIA", "ADMINISTRADOR"])
        
        btn_texto = "ENTRAR" if modo == "Iniciar Sesión" else "REGISTRARSE"
        
        if st.form_submit_button(btn_texto):
            if modo == "Iniciar Sesión":
                # Lógica de validación (ejemplo simple)
                if user == "admin" and password == "1234":
                    st.session_state.usuario_logueado = True
                    st.session_state.user_sel = user
                    st.session_state.rol_sel = rol_usuario  # <--- GUARDAMOS EL ROL AQUÍ
                    st.rerun()
                else: 
                    st.error("Credenciales incorrectas.")
            else:
                # Aquí guardarías los datos en tu Google Sheet de "USUARIOS"
                st.success(f"Solicitud de registro como {rol_usuario} enviada.")




# --- 4. LÓGICA PRINCIPAL ---
if not st.session_state.usuario_logueado:
    mostrar_landing()
else:
    # 1. CARGA DE DATOS (Solo si está logueado)
    df_objetivos = cargar_objetivos()
    df_comisarias = cargar_datos_comisarias()
    
    # 2. PANEL LATERAL (NO TOCAR, MANTENER TU DISEÑO)
    with st.sidebar:
        st.markdown('<div class="contenedor-logo-sidebar"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" style="width:180px; border:1px solid #00e5ff; border-radius:4px;"></div>', unsafe_allow_html=True)
        st.subheader("🛡️ PANEL DE CONTROL")
        if st.button("🛰️ MONITOREO"): st.session_state.rol_sel = "MONITOREO"; st.rerun()
        if st.button("📋 JEFE DE OPERACIONES"): st.session_state.rol_sel = "JEFE DE OPERACIONES"; st.rerun()
        if st.button("🏢 GERENCIA"): st.session_state.rol_sel = "GERENCIA"; st.rerun()
        st.write("---")
        st.button("🚪 CERRAR SESIÓN", on_click=lambda: setattr(st.session_state, 'usuario_logueado', False), use_container_width=True)

    # 3. LÓGICA DE ROLES (CORREGIDA PARA EVITAR EL ERROR DEL MAPA)
    # APLICAMOS EL BLINDAJE AQUÍ ANTES DE CUALQUIER ROL
    if not df_objetivos.empty and 'LATITUD' in df_objetivos.columns:
        df_objetivos['LATITUD'] = pd.to_numeric(df_objetivos['LATITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        df_objetivos['LONGITUD'] = pd.to_numeric(df_objetivos['LONGITUD'].astype(str).str.replace(',', '.'), errors='coerce')

    # AQUÍ PEGAS TU CÓDIGO DE "CODIGO DE ROLES.txt" DESDE "if st.session_state.rol_sel == "MONITOREO":" HACIA ABAJO
    # (Asegúrate de que todo ese bloque esté indentado dentro de este 'else')


if st.session_state.rol_sel == "MONITOREO":
    col1, col2, col3, col4 = st.columns(4)
    
    # 1. CARGA Y BLINDAJE DE DATOS (PARA ELIMINAR EL ERROR DEL MAPA)
    df_emergencias = leer_matriz_nube("ALERTAS")
    df_objetivos = cargar_objetivos()
    
    if not df_objetivos.empty:
        df_objetivos.columns = df_objetivos.columns.str.strip().str.upper()
        # BLINDAJE: Convertimos todo a número, si hay texto pone NaN
        df_objetivos['LATITUD'] = pd.to_numeric(df_objetivos['LATITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        df_objetivos['LONGITUD'] = pd.to_numeric(df_objetivos['LONGITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        df_mapa_monitoreo = df_objetivos.dropna(subset=['LATITUD', 'LONGITUD']).copy()
    else:
        df_mapa_monitoreo = pd.DataFrame()

    if df_emergencias.empty:
        df_emergencias = pd.DataFrame(columns=['FECHA', 'USUARIO', 'TIPO', 'ESTADO', 'CARGA_UTIL', 'INFORME'])
    else:
        df_emergencias.columns = df_emergencias.columns.str.strip().str.upper()

    # 2. LÓGICA DE PÁNICO
    lista_objetivos_en_panico = []
    if 'ESTADO' in df_emergencias.columns and 'CARGA_UTIL' in df_emergencias.columns:
        pendientes = df_emergencias[df_emergencias['ESTADO'].astype(str).str.upper() == 'PENDIENTE']
        sos_activos = len(pendientes)
        for _, row in pendientes.iterrows():
            carga = str(row['CARGA_UTIL'])
            if "OBJ:" in carga:
                try: 
                    lista_objetivos_en_panico.append(carga.split("OBJ:")[1].split("|")[0].strip().upper())
                except: pass
    else: 
        sos_activos = 0
    
    # 3. CONTADORES Y RELOJ
    with col1.container():
        @st.fragment(run_every=5)
        def contar_panicos_monitoreo():
            df_alertas = leer_matriz_nube("ALERTAS")
            if not df_alertas.empty:
                df_alertas.columns = [str(c).strip().upper() for c in df_alertas.columns]
                total_sos = len(df_alertas[df_alertas['ESTADO'] == "PENDIENTE"])
                st.metric("🚨 S.O.S ACTIVOS", total_sos)
            else: st.metric("🚨 S.O.S ACTIVOS", "0")
        contar_panicos_monitoreo()

    col2.metric("📡 RED", "OPERATIVA")
    col3.metric("👤 OPERADOR", f"{st.session_state.user_sel}")
    
    with col4.container():
        @st.fragment(run_every=1)
        def mostrar_reloj_monitoreo():
            st.metric("🕒 HORA LOCAL", obtener_hora_argentina().split(" ")[1])
        mostrar_reloj_monitoreo() 

    # 4. TABS Y RADAR
    total_nuevos = 0
    df_msg = leer_matriz_nube("MENSAJERIA")
    if not df_msg.empty:
        mask = ((df_msg['DESTINATARIO'] == "TODOS") | (df_msg['DESTINATARIO'] == "MONITOREO") | (df_msg['DESTINATARIO'] == st.session_state.user_sel.upper())) & (df_msg['ESTADO'] == "PENDIENTE")
        total_nuevos = len(df_msg[mask])
    
    label_msg = f"💬 MENSAJERÍA ({total_nuevos})" if total_nuevos > 0 else "💬 MENSAJERÍA"
    t_radar, t_mensajeria, t_vig, t_nov = st.tabs(["🚨 RADAR S.O.S", label_msg, "👥 PADRÓN VIGILADORES", "🔄 NOVEDADES Y FICHAJES"]) 
    
with t_radar:
        st.subheader("📡 RADAR GLOBAL")
        
        # 1. BLINDAJE DE DATOS (Asegura que sean números antes de promediar)
        if not df_mapa_monitoreo.empty:
            df_mapa_monitoreo['LATITUD'] = pd.to_numeric(df_mapa_monitoreo['LATITUD'], errors='coerce')
            df_mapa_monitoreo['LONGITUD'] = pd.to_numeric(df_mapa_monitoreo['LONGITUD'], errors='coerce')
            df_mapa_monitoreo = df_mapa_monitoreo.dropna(subset=['LATITUD', 'LONGITUD'])

        if not df_mapa_monitoreo.empty:
            if obj_seleccionado != "MOSTRAR TODO":
                datos_obj = df_mapa_monitoreo[df_mapa_monitoreo['OBJETIVO'] == obj_seleccionado].iloc[0]
                centro_mapa = [datos_obj['LATITUD'], datos_obj['LONGITUD']]
                zoom_inicial = 13
            else:
                # Ahora este mean() funcionará porque los datos son numéricos
                centro_mapa = [df_mapa_monitoreo['LATITUD'].mean(), df_mapa_monitoreo['LONGITUD'].mean()]
                zoom_inicial = 11

            m_mon = folium.Map(
                location=centro_mapa, 
                zoom_start=zoom_inicial, 
                max_zoom=21,
                tiles="https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}{r}.png",
                attr='© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors © <a href="https://carto.com/attributions">CARTO</a>'
            )

            # Dibujo de marcadores
            for _, r in df_mapa_monitoreo.iterrows():
                es_panico = r['OBJETIVO'] in lista_objetivos_en_panico
                es_el_seleccionado = (r['OBJETIVO'] == obj_seleccionado)
                
                # Tooltip dinámico
                texto_tooltip = f"🎯 {r['OBJETIVO']}"
                if es_panico:
                    alerta_activa = df_emergencias[(df_emergencias['CARGA_UTIL'].str.contains(str(r['OBJETIVO']))) & (df_emergencias['ESTADO'] == 'PENDIENTE')]
                    if not alerta_activa.empty:
                        texto_tooltip = f"🚨 {alerta_activa.iloc[-1]['USUARIO']} | {r['OBJETIVO']}"

                if es_panico or es_el_seleccionado:
                    folium.Marker(
                        location=[r['LATITUD'], r['LONGITUD']],
                        tooltip=texto_tooltip,
                        icon=folium.DivIcon(
                            icon_size=(30, 30), icon_anchor=(15, 15),
                            html='''<div style="background-color: #FF0000; width: 16px; height: 16px; border-radius: 50%; border: 2px solid white; animation: pulse 1s infinite alternate;"></div>'''
                        )
                    ).add_to(m_mon)
                else:
                    folium.CircleMarker(
                        location=[r['LATITUD'], r['LONGITUD']], radius=7, color="#00E5FF", fill=True,
                        tooltip=f"🎯 {r['OBJETIVO']} | 👤 SUP: {r.get('SUPERVISOR', 'N/A')}"
                    ).add_to(m_mon)

            # Capas adicionales
            folium.TileLayer("https://{s}.basemaps.cartocdn.com/dark_only_labels/{z}/{x}/{y}{r}.png", 
                             attr='© <a href="https://carto.com/attributions">CARTO</a>',
                             name="Etiquetas", overlay=True, control=False).add_to(m_mon)
            
            st_folium(m_mon, width="100%", height=550, key="mapa_monitoreo_radar_tactico")
        else:
            st.warning("No hay objetivos con coordenadas válidas para mostrar en el radar.")




































































