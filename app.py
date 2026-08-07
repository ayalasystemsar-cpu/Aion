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
import io
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfgen import canvas
import streamlit.components.v1 as components
from streamlit_qrcode_scanner import qrcode_scanner
import os

# --- 0. RUTINA DE AUTOREPARACIÓN DE BASES MAESTRAS ---

def reparar_bases_maestras_automaticamente():
    try:
        obj_path = 'AION_YAROKU_MASTER_OBJETIVOS.csv'
        if os.path.exists(obj_path):
            obj = pd.read_csv(obj_path)
            if len(obj) > 47:
                obj_limpio = obj.iloc[:47].copy()
                obj_limpio.to_csv(obj_path, index=False)
            
        com_path = 'AION_YAROKU_MASTER_COMISARIAS.csv'
        if os.path.exists(com_path):
            com = pd.read_csv(com_path)
            if len(com) < 10:
                comisarias_data = {
                    'COMISARIA': [
                        'COMISARÍA VECINAL 1A', 'COMISARÍA VECINAL 1D', 'COMISARÍA AVELLANEDA 1RA', 
                        'COMISARÍA SAN FERNANDO 1RA', 'COMISARÍA CAMPANA 2DA', 'COMISARÍA PILAR 6TA'
                    ],
                    'DIRECCION': [
                        'SUIPACHA 1156', 'AV. SAN JUAN 1050', 'GRAL. LAVALLE 150', 
                        'CONSTITUCIÓN 720', 'MITRE 1200', 'RUTA 25 S/N'
                    ],
                    'LOCALIDAD': ['CABA', 'CABA', 'AVELLANEDA', 'SAN FERNANDO', 'CAMPANA', 'PILAR'],
                    'TELEFONO': ['011-4393-0100', '011-4308-0100', '011-4201-1122', '011-4744-0192', '03489-423-0100', '0230-449-0111'],
                    'LATITUD': [-34.5985, -34.6200, -34.6625, -34.4532, -34.1700, -34.4500],
                    'LONGITUD': [-58.3838, -58.3800, -58.3671, -58.5634, -58.9700, -58.9000]
                }
                pd.DataFrame(comisarias_data).to_csv(com_path, index=False)
    except Exception as e:
        print(f"Nota de autoreparación: {e}")

reparar_bases_maestras_automaticamente()

# --- 1. CLASE PARA NUMERACIÓN DE PÁGINAS EN PDF ---

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super(NumberedCanvas, self).__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor('#666666'))
        texto_pag = f"Página {self._pageNumber} de {page_count}"
        self.drawRightString(792 - 24, 15, texto_pag)
        self.drawString(24, 15, "AION-YAROKU | SISTEMA TÁCTICO INTEGRAL")
        self.setStrokeColor(colors.HexColor('#CCCCCC'))
        self.setLineWidth(0.5)
        self.line(24, 25, 792 - 24, 25)
        self.restoreState()

# --- 2. CONFIGURACIÓN E INICIALIZACIÓN CON PERSISTENCIA POR URL ---

st.set_page_config(page_title="AION-YAROKU | COMMAND", page_icon="🛡️", layout="wide", initial_sidebar_state="expanded")

query_params = st.query_params

if 'usuario_logueado' not in st.session_state:
    st.session_state.usuario_logueado = query_params.get("logueado", "false") == "true"

if 'rol_sel' not in st.session_state:
    st.session_state.rol_sel = query_params.get("rol", "MONITOREO")

if 'user_sel' not in st.session_state:
    st.session_state.user_sel = query_params.get("user", "OPERADOR CENTRAL")

if 'sup_autenticado' not in st.session_state:
    st.session_state.sup_autenticado = query_params.get("sup_auth", "false") == "true"

if 'admin_autenticado' not in st.session_state:
    st.session_state.admin_autenticado = query_params.get("admin_auth", "false") == "true"

if 'ultimo_mensaje_qr' not in st.session_state: 
    st.session_state.ultimo_mensaje_qr = ""

def sincronizar_url_sesion():
    st.query_params.update({
        "logueado": "true" if st.session_state.usuario_logueado else "false",
        "rol": st.session_state.rol_sel,
        "user": st.session_state.user_sel,
        "sup_auth": "true" if st.session_state.sup_autenticado else "false",
        "admin_auth": "true" if st.session_state.admin_autenticado else "false"
    })

# --- 3. CONEXIONES Y FUNCIONES GLOBALES OPTIMIZADAS ---

ID_MAESTRO_DB = "1Md0VkOnwUJWldq0S1fB9UrmOKv4MG__JVG3tQsda0Uw"

@st.cache_resource
def conectar_google():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        return gspread.authorize(creds)
    except: 
        return None

def obtener_hora_argentina():
    tz = pytz.timezone("America/Argentina/Buenos_Aires")
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

def obtener_mapeo_solapas():
    return {
        "NOVEDADES GUARDIA": "NOVEDADES GUARDIA",
        "REGISTRO QR SUPERVISORES": "REGISTRO QR SUPERVISORES",
        "JORNADA SUPERVISORES": "JORNADA SUPERVISORES",
        "CONTROL DE FLOTA": "CONTROL DE FLOTA",
        "SOLICITUDES DE ACCESO": "SOLICITUDES ACCESO",
        "OBJETIVOS": "OBJETIVOS",
        "COMISARIAS": "COMISARIAS",
        "USUARIOS": "USUARIOS",
        "ALERTAS": "ALERTAS",
        "MENSAJERIA": "MENSAJERIA",
        "PRESENTISMO": "PRESENTISMO",
        "VIGILADORES": "VIGILADORES"
    }

def escribir_registro_nube(pestana, datos_fila):
    try:
        gc = conectar_google()
        if gc:
            sh = gc.open_by_key(ID_MAESTRO_DB)
            nombre_hoja_real = obtener_mapeo_solapas().get(pestana.upper().strip(), pestana)
            try:
                hoja = sh.worksheet(nombre_hoja_real)
            except Exception:
                hoja = sh.add_worksheet(title=nombre_hoja_real, rows="100", cols="10")
            hoja.append_row(datos_fila)
            st.cache_data.clear() 
            return True
    except Exception as e:
        print(f"Error de nube en {pestana}: {e}")
        return False

@st.cache_data(ttl=5)
def leer_matriz_nube(pestana):
    gc = conectar_google()
    if gc:
        try:
            sh = gc.open_by_key(ID_MAESTRO_DB)
            nombre_hoja_real = obtener_mapeo_solapas().get(pestana.upper().strip(), pestana)
            hoja = sh.worksheet(nombre_hoja_real)
            todas_filas = hoja.get_all_values()
            if not todas_filas or len(todas_filas) == 0:
                return pd.DataFrame()
            encabezados = [str(h).strip().upper() for h in todas_filas[0]]
            datos_cuerpo = todas_filas[1:]
            df = pd.DataFrame(datos_cuerpo, columns=encabezados)
            df.columns = [str(c).strip().upper() for c in df.columns]
            
            # SOLUCIÓN CRÍTICA: Eliminar columnas duplicadas para evitar errores en st.dataframe
            df = df.loc[:, ~df.columns.duplicated()]
            return df
        except Exception as e: 
            print(f"Error leyendo {pestana}: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

@st.cache_data(ttl=60)
def cargar_datos_comisarias():
    df_nube = leer_matriz_nube("COMISARIAS")
    if not df_nube.empty and 'COMISARIA' in df_nube.columns and len(df_nube) > 1:
        df_nube['LATITUD'] = pd.to_numeric(df_nube['LATITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        df_nube['LONGITUD'] = pd.to_numeric(df_nube['LONGITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        return df_nube
    
    data = {
        "COMISARIA": ["COMISARÍA VECINAL 1A", "COMISARÍA AVELLANEDA 1RA", "COMISARÍA PILAR 6TA"],
        "DIRECCION": ["Suipacha 1156", "Gral. Lavalle 150", "Ruta 25 s/n"],
        "LOCALIDAD": ["CABA", "AVELLANEDA", "PILAR"],
        "TELEFONO": ["011-4393-0100", "011-4201-1122", "0230-449-0111"],
        "LATITUD": [-34.5985, -34.6641, -34.4170],
        "LONGITUD": [-58.3838, -58.3680, -58.8682]
    }
    return pd.DataFrame(data)

@st.cache_data(ttl=30)
def cargar_objetivos():
    df = leer_matriz_nube("OBJETIVOS")
    if not df.empty and 'OBJETIVO' in df.columns:
        df.columns = df.columns.str.strip().str.upper()
        df = df.loc[:, ~df.columns.duplicated()] # Limpieza extra de columnas duplicadas
        df = df[df['OBJETIVO'].astype(str).str.strip() != ""]
        if 'SUPERVISOR' in df.columns:
            df['SUPERVISOR'] = df['SUPERVISOR'].astype(str).str.strip().str.upper()
        df['LATITUD'] = pd.to_numeric(df['LATITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        df['LONGITUD'] = pd.to_numeric(df['LONGITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        return df 
    
    obj_path = 'AION_YAROKU_MASTER_OBJETIVOS.csv'
    if os.path.exists(obj_path):
        try:
            df_loc = pd.read_csv(obj_path)
            df_loc.columns = df_loc.columns.str.strip().str.upper()
            df_loc = df_loc.loc[:, ~df_loc.columns.duplicated()]
            return df_loc
        except:
            pass
    return pd.DataFrame(columns=["OBJETIVO", "DIRECCION", "LOCALIDAD", "SUPERVISOR", "LATITUD", "LONGITUD", "RESPONSABLES"])

def registrar_objetivo_con_comisaria_automatica(nombre_obj, direccion, localidad, supervisor, lat, lon, responsables):
    nombre_obj_upper = str(nombre_obj).strip().upper()
    localidad_obj_upper = str(localidad).strip().upper()
    comisaria_formateada = "COMISARÍA JURISDICCIONAL - S/D"

    datos_nuevo_obj = [
        nombre_obj_upper, 
        str(direccion).strip().upper(), 
        str(localidad).strip().upper(), 
        str(supervisor).strip().upper(), 
        str(lat), 
        str(lon), 
        str(responsables).strip().upper(),
        comisaria_formateada
    ]
    
    try:
        obj_path = 'AION_YAROKU_MASTER_OBJETIVOS.csv'
        if os.path.exists(obj_path):
            df_local = pd.read_csv(obj_path)
            nueva_fila_df = pd.DataFrame([datos_nuevo_obj[:len(df_local.columns)]], columns=df_local.columns[:len(datos_nuevo_obj)])
            df_local = pd.concat([df_local, nueva_fila_df], ignore_index=True)
            df_local.to_csv(obj_path, index=False)
    except Exception as ex_local:
        print(f"Aviso guardado local: {ex_local}")

    exito = escribir_registro_nube("OBJETIVOS", datos_nuevo_obj)
    st.cache_data.clear()
    return exito

def obtener_lista_supervisores_dinamica():
    base = ["AYALA BRIAN", "SUPERVISOR 1", "SUPERVISOR 2", "SUPERVISOR 3", "SUPERVISOR 4", "SUPERVISOR 5", "SUPERVISOR NOCTURNO", "CONTROLADOR NOCTURNO", "TIKI", "GONZALEZ"]
    df_u = leer_matriz_nube("USUARIOS")
    if not df_u.empty and 'USUARIO' in df_u.columns:
        col_r = 'ROL' if 'ROL' in df_u.columns else 'ROLES'
        if col_r in df_u.columns and 'ESTADO' in df_u.columns:
            sups_extra = df_u[(df_u[col_r].astype(str).str.strip().str.upper() == "SUPERVISOR") & (df_u['ESTADO'].astype(str).str.strip().str.upper() == "APROBADO")]["USUARIO"].tolist()
            for s in sups_extra:
                s_limpio = str(s).strip().upper()
                if s_limpio not in base:
                    base.append(s_limpio)
    return base

def registrar_jornada_general(supervisor, objetivo, accion):
    try:
        tz = pytz.timezone("America/Argentina/Buenos_Aires")
        ahora = datetime.now(tz)
        datos = [ahora.strftime("%Y-%m-%d"), str(supervisor).strip().upper(), str(objetivo).strip().upper(), str(accion).strip().upper(), ahora.strftime("%H:%M:%S")]
        return escribir_registro_nube("JORNADA SUPERVISORES", datos)
    except:
        return False

def aplicar_identidad_alfa():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@300;500;700&display=swap');
        .stApp { background: radial-gradient(circle at top, #0A0F1E 0%, #030305 100%) !important; color: #E0E0E0; font-family: 'Rajdhani', sans-serif; }
        .block-container { padding: 1rem !important; max-width: 100% !important; }
        .contenedor-logo-central { display: flex; justify-content: center; align-items: center; width: 100%; margin: 10px 0; }
        .logo-phoenix { width: 100% !important; max-width: 320px !important; height: auto !important; border: 2px solid #00e5ff !important; box-shadow: 0 0 35px rgba(0, 229, 255, 0.5) !important; border-radius: 4px !important; background-color: #000 !important; }
        .estacion-titulo { font-family: 'Orbitron', sans-serif; color: #00E5FF !important; font-size: 22px; margin-top: 10px; display: flex; align-items: center; justify-content: center; gap: 12px; text-shadow: 0 0 15px rgba(0, 229, 255, 0.4); letter-spacing: 2px; text-transform: uppercase; text-align: center; }
        .stApp div[data-testid="stExpander"] { background-color: #1A1C23 !important; border: 1px solid #2D313E !important; border-radius: 8px !important; }
        .stApp input { background-color: #252833 !important; color: #FFFFFF !important; border: 1px solid #1A1C23 !important; border-radius: 6px !important; }
        .stTabs [data-baseweb="tab-list"] { gap: 6px !important; background-color: transparent !important; flex-wrap: nowrap !important; overflow-x: auto !important; }
        .stTabs [data-baseweb="tab"] { background-color: rgba(26, 28, 35, 0.6) !important; border: 1px solid #2D313E !important; color: #A0A5B5 !important; border-radius: 4px 4px 0px 0px !important; padding: 8px 12px !important; font-family: 'Orbitron', sans-serif; font-size: 11px !important; font-weight: bold; }
        .stTabs [aria-selected="true"] { background-color: #1A1C23 !important; border-top: 2px solid #00E5FF !important; color: #00E5FF !important; }
        </style>
    """, unsafe_allow_html=True)

def mostrar_landing():
    aplicar_identidad_alfa()
    st.markdown('<div class="contenedor-logo-central"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" class="logo-phoenix"></div>', unsafe_allow_html=True)
    st.markdown('<div class="estacion-titulo">AION-YAROKU | COMMAND</div>', unsafe_allow_html=True)
    
    modo = st.radio("Acceso al Sistema:", ["Iniciar Sesión", "Crear Cuenta"], horizontal=True, key="radio_modo")
    
    with st.form("form_acceso_real"):
        user = st.text_input("Usuario o Apellido del Supervisor", key="u")
        password = st.text_input("Contraseña", type="password", key="p")
        roles_registro = ["VIGILADOR", "MONITOREO", "JEFE DE OPERACIONES", "GERENCIA", "SUPERVISOR"]
        rol_usuario = st.selectbox("Seleccione su Rol:", roles_registro, key="r")

        btn_texto = "ENTRAR" if modo == "Iniciar Sesión" else "REGISTRARSE"
        
        if st.form_submit_button(btn_texto):
            user_limpio = user.strip().upper()
            pass_limpio = password.strip()
            
            if modo == "Iniciar Sesión" and user_limpio == "ADMIN" and pass_limpio == "aion2026":
                st.session_state.usuario_logueado = True
                st.session_state.user_sel = "ADMIN CENTRAL"
                st.session_state.rol_sel = "ADMINISTRADOR"
                st.session_state.admin_autenticado = True
                st.session_state.sup_autenticado = False
                sincronizar_url_sesion()
                st.rerun()
                
            elif modo == "Iniciar Sesión" and rol_usuario == "SUPERVISOR" and (user_limpio.startswith("SUPERVISOR") or user_limpio in ["AYALA BRIAN", "AYALA", "GONZALEZ", "CONTROLADOR NOCTURNO", "TIKI"] or pass_limpio == "1234"):
                usuario_final = "AYALA BRIAN" if user_limpio in ["AYALA BRIAN", "AYALA"] else user_limpio
                st.session_state.usuario_logueado = True
                st.session_state.user_sel = usuario_final
                st.session_state.rol_sel = "SUPERVISOR"
                st.session_state.sup_autenticado = True
                st.session_state.admin_autenticado = False
                sincronizar_url_sesion()
                st.rerun()

            elif modo == "Iniciar Sesión":
                st.session_state.usuario_logueado = True
                st.session_state.user_sel = user_limpio if user_limpio else "OPERADOR CENTRAL"
                st.session_state.rol_sel = rol_usuario
                sincronizar_url_sesion()
                st.rerun()
            else:
                if user.strip() and password.strip():
                    escribir_registro_nube("USUARIOS", [user.strip().upper(), password.strip(), rol_usuario, "PENDIENTE"])
                    st.success("✅ Solicitud de registro enviada con éxito.")
                else:
                    st.warning("⚠️ Complete el usuario y la contraseña.")

if not st.session_state.usuario_logueado:
    mostrar_landing()
    st.stop()

aplicar_identidad_alfa()

df_objetivos = cargar_objetivos()
LISTA_SUPS_TACTICOS = obtener_lista_supervisores_dinamica()

# --- BARRA LATERAL ---
with st.sidebar:
    st.markdown('<div class="contenedor-logo-sidebar"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" style="width:180px; border:1px solid #00e5ff; border-radius:4px;"></div>', unsafe_allow_html=True)
    st.markdown("---")
    st.markdown(f"**PERFIL:** {st.session_state.rol_sel}")
    st.markdown(f"**USUARIO:** {st.session_state.user_sel}")
    
    if st.session_state.rol_sel == "ADMINISTRADOR" or st.session_state.get("admin_autenticado", False):
        st.subheader("⚙️ NÚCLEO MAESTRO")
        vista_admin_sel = st.selectbox("MODO DE VISTA:", ["ADMINISTRADOR", "SUPERVISOR", "MONITOREO", "JEFE DE OPERACIONES"], key="sel_vista_admin")
        if "SUPERVISOR" in vista_admin_sel:
            nom_sup_elegido = st.selectbox("SUPERVISOR:", LISTA_SUPS_TACTICOS)
            if st.button("CARGAR VISTA SUPERVISOR"):
                st.session_state.rol_sel = "SUPERVISOR"
                st.session_state.user_sel = nom_sup_elegido
                st.session_state.sup_autenticado = True
                sincronizar_url_sesion()
                st.rerun()

    st.markdown("---")
    if st.button("🚪 CERRAR SESIÓN", use_container_width=True):
        st.session_state.usuario_logueado = False
        st.query_params.clear()
        st.rerun()

st.markdown(f'<div class="estacion-titulo">ESTACIÓN TÁCTICA: {st.session_state.rol_sel} ({st.session_state.user_sel})</div>', unsafe_allow_html=True)

# =========================================================================
# ROL: SUPERVISOR
# =========================================================================
if st.session_state.rol_sel == "SUPERVISOR":
    sup_activo_normalizado = st.session_state.user_sel.strip().upper()
    
    if not df_objetivos.empty and 'SUPERVISOR' in df_objetivos.columns:
        df_objetivos_filtrados = df_objetivos[
            df_objetivos['SUPERVISOR'].astype(str).str.strip().str.upper() == sup_activo_normalizado
        ].copy()
    else:
        df_objetivos_filtrados = pd.DataFrame()

    st.subheader(f"⏱️ GESTIÓN DE JORNADA")
    col_j1, col_j2 = st.columns(2)
    with col_j1:
        if st.button("🚀 INICIO DE JORNADA", use_container_width=True):
            registrar_jornada_general(st.session_state.user_sel, "GENERAL", "INICIO")
            st.success("Jornada iniciada correctamente.")
    with col_j2:
        if st.button("🏁 CIERRE DE JORNADA", use_container_width=True):
            registrar_jornada_general(st.session_state.user_sel, "GENERAL", "FIN")
            st.success("Jornada cerrada correctamente.")

    st.markdown("<br>", unsafe_allow_html=True)
    
    t_vis_qr, t_nuevo_obj, t_mensajeria_sup = st.tabs(["Visita QR", "➕ CARGAR OBJETIVO", "💬 MENSAJERÍA"])
    
    with t_nuevo_obj:
        st.markdown("### ➕ AUTOGESTIÓN DE OBJETIVOS TÁCTICOS")
        with st.form(key="form_crear_objetivo_supervisor", clear_on_submit=False):
            col_no1, col_no2 = st.columns(2)
            nuevo_nombre_obj = col_no1.text_input("NOMBRE DEL OBJETIVO:", value="").upper().strip()
            nueva_direccion = col_no2.text_input("DIRECCIÓN:", value="").upper().strip()
            
            col_loc1, col_loc2 = st.columns(2)
            nueva_localidad = col_loc1.text_input("LOCALIDAD:", value="CABA").upper().strip()
            nueva_lat = col_loc2.text_input("LATITUD (Ej: -34.5985):", value="-34.5985")
            
            col_lon1, col_lon2 = st.columns(2)
            nueva_lon = col_lon1.text_input("LONGITUD (Ej: -58.3838):", value="-58.3838")
            nuevos_responsables = col_lon2.text_input("RESPONSABLES:", value="CENTRO").upper().strip()
            
            if st.form_submit_button("🚀 DAR DE ALTA OBJETIVO EN LA RED"):
                if nuevo_nombre_obj and nueva_lat and nueva_lon:
                    exito_alta = registrar_objetivo_con_comisaria_automatica(
                        nuevo_nombre_obj, nueva_direccion, nueva_localidad, st.session_state.user_sel, nueva_lat, nueva_lon, nuevos_responsables
                    )
                    if exito_alta:
                        st.success(f"✅ ¡Objetivo '{nuevo_nombre_obj}' cargado con éxito en la red!")
                        st.rerun()
                    else:
                        st.error("❌ Error al registrar en la nube. Verifique la conexión.")
                else:
                    st.warning("⚠️ Complete los campos obligatorios (Nombre, Latitud y Longitud).")

    with t_vis_qr:
        st.markdown("### 📱 REGISTRO Y CONTROL DE OBJETIVOS")
        if not df_objetivos_filtrados.empty:
            st.dataframe(df_objetivos_filtrados, use_container_width=True)
        else:
            st.info("No hay objetivos asignados actualmente para este usuario o la base está cargando.")
            if not df_objetivos.empty:
                st.write("Objetivos generales disponibles en el sistema:")
                st.dataframe(df_objetivos, use_container_width=True)

    with t_mensajeria_sup:
        st.markdown("### 💬 COMUNICACIONES TÁCTICAS")
        txt_msg = st.text_input("MENSAJE NUEVO:")
        if st.button("ENVIAR MENSAJE"):
            if txt_msg:
                escribir_registro_nube("MENSAJERIA", [obtener_hora_argentina(), st.session_state.user_sel, "TODOS", "GENERAL", txt_msg.upper(), "PENDIENTE"])
                st.success("Mensaje enviado.")
else:
    st.info(f"Panel operativo activo para el rol: {st.session_state.rol_sel}. Utilice las solapas correspondientes.")
    df_gen = leer_matriz_nube("OBJETIVOS")
    if not df_gen.empty:
        st.subheader("📋 LISTADO GENERAL DE OBJETIVOS")
        st.dataframe(df_gen, use_container_width=True)
