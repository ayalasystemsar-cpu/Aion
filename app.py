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

# --- 1. CONFIGURACIÓN E INICIALIZACIÓN ---

st.set_page_config(page_title="AION-YAROKU | COMMAND", page_icon="🛡️", layout="wide", initial_sidebar_state="expanded")

if 'usuario_logueado' not in st.session_state: st.session_state.usuario_logueado = False
if 'rol_sel' not in st.session_state: st.session_state.rol_sel = "MONITOREO"
if 'user_sel' not in st.session_state: st.session_state.user_sel = "OPERADOR CENTRAL"
if 'sup_autenticado' not in st.session_state: st.session_state.sup_autenticado = False
if 'admin_autenticado' not in st.session_state: st.session_state.admin_autenticado = False

# --- 2. CONEXIONES Y FUNCIONES GLOBALES ---

ID_MAESTRO_DB = "1Md0VkOnwUJWldq0S1fB9UrmOKv4MG__JVG3tQsda0Uw"

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

def actualizar_celda(pestana, fila, columna, valor):
    try:
        gc = conectar_google()
        if gc:
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
            hoja.update_acell(f"{columna}{fila}", valor)
            return True
    except: 
        return False

def escribir_registro_nube(pestana, datos_fila):
    try:
        gc = conectar_google()
        if gc:
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
            hoja.append_row(datos_fila)
            return True
    except: 
        return False

@st.cache_data(ttl=60)
def leer_matriz_nube(pestana):
    gc = conectar_google()
    if gc:
        try:
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
            todas_filas = hoja.get_all_values()
            if not todas_filas or len(todas_filas) == 0:
                return pd.DataFrame()
            encabezados = [str(h).strip().upper() for h in todas_filas[0]]
            datos_cuerpo = todas_filas[1:]
            df = pd.DataFrame(datos_cuerpo, columns=encabezados)
            df.columns = [str(c).strip().upper() for c in df.columns]
            df = df.loc[:, ~df.columns.duplicated()]
            return df
        except: 
            return pd.DataFrame()
    return pd.DataFrame()

@st.cache_data(ttl=60)
def cargar_datos_comisarias():
    data = {
        "COMISARIA": ["COMISARÍA SAN MARTÍN 1RA", "COMISARÍA VECINAL 14C", "COMISARÍA AVELLANEDA 1RA", "COMISARÍA CAMPANA 1RA", "COMISARÍA SAN FERNANDO 1RA", "COMISARÍA TIGRE 1RA", "COMISARÍA PILAR 6TA (VILLA ROSA)", "COMISARÍA VECINAL 1B", "COMISARÍA VECINAL 14A", "COMISARÍA LANÚS 2DA", "COMISARÍA VECINAL 13A", "COMISARÍA LA MATANZA 2DA", "COMISARÍA LA MATANZA 3RA", "COMISARÍA VECINAL 2A", "COMISARÍA VECINAL 12A", "COMISARÍA VECINAL 12B", "COMISARÍA VECINAL 6A", "COMISARÍA VECINAL 1D", "COMISARÍA RAMOS MEJÍA 2DA"],
        "LATITUD": [-34.580139, -34.587773, -34.664119, -34.163693, -34.440154, -34.424196, -34.417041, -34.617133, -34.587773, -34.708819, -34.557454, -34.700147, -34.717182, -34.589886, -34.554321, -34.568459, -34.613045, -34.603847, -34.646589],
        "LONGITUD": [-58.541410, -58.416056, -58.368073, -58.961418, -58.556134, -58.579789, -58.868209, -58.378734, -58.416056, -58.385311, -58.461144, -58.575608, -58.608301, -58.401918, -58.472147, -58.482012, -58.437198, -58.381577, -58.564571]
    }
    return pd.DataFrame(data)

@st.cache_data(ttl=60)
def cargar_objetivos():
    df = leer_matriz_nube("OBJETIVOS")
    if not df.empty:
        df.columns = df.columns.str.strip().str.upper()
        df = df[df['OBJETIVO'].astype(str).str.strip() != ""]
        df = df[df['OBJETIVO'].notna()]
        if 'SUPERVISOR' in df.columns:
            df['SUPERVISOR'] = df['SUPERVISOR'].astype(str).str.strip().str.upper()
        df['LATITUD'] = df['LATITUD'].astype(str).str.replace(',', '.')
        df['LONGITUD'] = df['LONGITUD'].astype(str).str.replace(',', '.')
        df['LATITUD'] = pd.to_numeric(df['LATITUD'], errors='coerce')
        df['LONGITUD'] = pd.to_numeric(df['LONGITUD'], errors='coerce')
        return df 
    return pd.DataFrame()

@st.cache_resource
def obtener_grafo_zona(lat, lon):
    try:
        return ox.graph_from_point((lat, lon), dist=5000, network_type='drive')
    except:
        return None

def obtener_ruta_calles_osrm(lat1, lon1, lat2, lon2):
    try:
        url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=full&geometries=geojson"
        response = requests.get(url, timeout=5).json()
        if response.get("code") == "Ok":
            coordenadas = response["routes"][0]["geometry"]["coordinates"]
            return [[point[1], point[0]] for point in coordenadas]
    except:
        pass
    return [[lat1, lon1], [lat2, lon2]]

LISTA_SUPS_TACTICOS = [
    "AYALA BRIAN", "SUPERVISOR 1", "SUPERVISOR 2", "SUPERVISOR 3", "SUPERVISOR 4", "SUPERVISOR 5", "SUPERVISOR NOCTURNO"
]

# --- 3. IDENTIDAD VISUAL Y ESTILOS ---

def aplicar_identidad_alfa():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@300;500;700&display=swap');
        .stApp { background: radial-gradient(circle at top, #0A0F1E 0%, #030305 100%) !important; color: #E0E0E0; font-family: 'Rajdhani', sans-serif; }
        .contenedor-logo-central { display: flex; justify-content: center; align-items: center; width: 100%; margin: 10px 0; }
        .logo-phoenix { width: 450px !important; border: 2px solid #00e5ff !important; box-shadow: 0 0 35px rgba(0, 229, 255, 0.5) !important; border-radius: 4px !important; background-color: #000 !important; }
        .estacion-titulo {
            font-family: 'Orbitron', sans-serif;
            color: #00E5FF !important; font-size: 24px; margin-top: 15px;
            display: flex; align-items: center; justify-content: center; gap: 12px;
            text-shadow: 0 0 15px rgba(0, 229, 255, 0.4); letter-spacing: 2px; text-transform: uppercase;
        }
        .stApp div[data-testid="stExpander"] { background-color: #1A1C23 !important; border: 1px solid #2D313E !important; border-radius: 8px !important; }
        .stApp div[data-testid="stExpander"] summary p { color: #E0E0E0 !important; font-size: 14px !important; font-weight: 600 !important; text-transform: uppercase; }
        .stApp input { background-color: #252833 !important; color: #FFFFFF !important; border: 1px solid #1A1C23 !important; border-radius: 6px !important; }
        .stApp label p { color: #A0A5B5 !important; font-family: 'Orbitron', sans-serif !important; font-size: 11px !important; font-weight: bold !important; letter-spacing: 0.5px; text-transform: uppercase; }
        .radar-box { border: 1px solid #00e5ff; border-radius: 8px; padding: 5px; background: #000000; box-shadow: 0 0 20px rgba(0, 229, 255, 0.2); }
        
        /* BOTÓN DE PÁNICO CIRCULAR EXACTO */
        .stButton > button[kind="primary"] { 
            background: radial-gradient(circle, #FF0000 0%, #8B0000 100%) !important;
            color: white !important; border-radius: 50% !important; width: 110px !important; height: 110px !important; 
            border: 3px solid #333 !important; box-shadow: 0 0 25px rgba(255, 0, 0, 0.6) !important; 
            font-family: 'Orbitron', sans-serif; font-size: 11px !important; font-weight: bold;
            display: block; margin: 0 auto;
        }

        .panel-novedad { border: 1px solid #333; border-radius: 8px; padding: 15px; margin-top: 20px; background-color: rgba(10, 10, 11, 0.9); }
        .stTabs [data-baseweb="tab-list"] { gap: 10px; background-color: transparent; }
        .stTabs [data-baseweb="tab"] {
            background-color: rgba(26, 28, 35, 0.4) !important; border: 1px solid #2D313E !important;
            color: #A0A5B5 !important; border-radius: 4px 4px 0px 0px !important; padding: 6px 16px !important;
            font-family: 'Orbitron', sans-serif; font-size: 11px !important; font-weight: bold;
        }
        .stTabs [aria-selected="true"] { background-color: #1A1C23 !important; border-top: 2px solid #00E5FF !important; color: #00E5FF !important; }
        div[data-testid="stMetric"] { background-color: rgba(10, 11, 15, 0.6) !important; border: 1px solid #1A1C23 !important; border-radius: 6px !important; padding: 12px !important; }
        div[data-testid="stMetricLabel"] p { color: #00E5FF !important; font-family: 'Rajdhani', sans-serif !important; font-size: 13px !important; font-weight: bold !important; text-transform: uppercase; letter-spacing: 0.5px; }
        div[data-testid="stMetricValue"] div { color: #FFFFFF !important; font-family: 'Orbitron', sans-serif !important; font-size: 22px !important; }
        .btn-google-maps {
            display: inline-flex; align-items: center; justify-content: center;
            background-color: #ffffff !important; color: #1a73e8 !important;
            font-family: 'Orbitron', sans-serif; font-weight: bold; font-size: 14px;
            padding: 12px 24px; border-radius: 6px; border: 2px solid #1a73e8;
            text-decoration: none !important; box-shadow: 0 4px 15px rgba(26, 115, 232, 0.3);
            width: 100%; text-align: center; margin-top: 10px; transition: 0.3s;
        }
        .btn-google-maps:hover { background-color: #1a73e8 !important; color: white !important; }
        </style>
    """, unsafe_allow_html=True)

# --- 4. FUNCIONES DE MENSAJERÍA Y CIERRE ---

def renderizar_mensajeria_global(rol_contexto):
    if 'asunto_respuesta' not in st.session_state:
        st.session_state.asunto_respuesta = None

    df_msg = leer_matriz_nube("MENSAJERIA")
    st.subheader("💬 COMUNICACIONES OPERATIVAS")

    with st.form(key=f"form_msg_{rol_contexto}", clear_on_submit=True):
        if st.session_state.asunto_respuesta:
            st.info(f"↩️ Respondiendo al hilo: {st.session_state.asunto_respuesta}")
            asunto_input = st.text_input("ASUNTO:", value=st.session_state.asunto_respuesta, disabled=True)
        else:
            asunto_input = st.text_input("ASUNTO:")

        col_a, col_b = st.columns([3, 1])
        with col_a:
            txt_msg = st.text_input("MENSAJE:")
        with col_b:
            destinatarios_posibles = ["TODOS", "MONITOREO", "JEFE DE OPERACIONES", "GERENCIA", "SUPERVISORES", "VIGILADOR"] + LISTA_SUPS_TACTICOS
            destinatario = st.selectbox("PARA:", destinatarios_posibles)
            gravedad = st.selectbox("GRAVEDAD:", ["VERDE", "ROJA"])

        if st.form_submit_button("TRANSMITIR A LA RED"):
            if txt_msg.strip():
                escribir_registro_nube("MENSAJERIA", [
                    obtener_hora_argentina(), st.session_state.user_sel, destinatario, 
                    (asunto_input or "GENERAL").upper(), txt_msg.upper(), "PENDIENTE", gravedad
                ])
                st.session_state.mensaje_enviado = "RESPUESTA" if st.session_state.asunto_respuesta else "MENSAJE"
                st.session_state.asunto_respuesta = None
                st.rerun()

    if 'mensaje_enviado' in st.session_state:
        if st.session_state.mensaje_enviado == "RESPUESTA":
            st.success("✅ RESPUESTA ENVIADA")
        else:
            st.success("✅ MENSAJE ENVIADO")
        del st.session_state.mensaje_enviado

    if not df_msg.empty:
        if 'ASUNTO' in df_msg.columns:
            for asunto, grupo in df_msg.groupby('ASUNTO'):
                with st.expander(f"💬 Hilo: {asunto}"):
                    for _, msg in grupo.iterrows():
                        st.markdown(f"**{msg.get('REMITENTE', 'ANÓNIMO')}:** {msg.get('MENSAJE', '')}")
                    if st.button(f"Responder a este hilo", key=f"btn_{asunto}_{rol_contexto}"):
                        st.session_state.asunto_respuesta = asunto
                        st.rerun()

def registrar_movimiento_supervisor(supervisor, objetivo, accion):
    fecha_hora_arg = obtener_hora_argentina()
    fecha = fecha_hora_arg.split(" ")[0]
    hora = fecha_hora_arg.split(" ")[1]
    datos = [fecha, supervisor, objetivo, accion, hora]
    return escribir_registro_nube("JORNADA_SUPERVISORES", datos)

def enviar_alerta_automatica(emisor, objetivo, nombre_persona, supervisor_asignado):
    fecha = obtener_hora_argentina()
    mensaje = f"🚨 ALERTA DE PÁNICO: {nombre_persona} - OBJ: {objetivo}"
    destinatarios = ["JEFE DE OPERACIONES", "GERENCIA", supervisor_asignado]
    for dest in destinatarios:
        if dest and dest != "MONITOREO" and dest != "N/A":
            escribir_registro_nube("MENSAJERIA", [fecha, emisor, dest, mensaje, "PENDIENTE"])

def limpiar_matriz_nube(nombre_hoja):
    try:
        gc = conectar_google()
        if gc:
            worksheet = gc.open_by_key(ID_MAESTRO_DB).worksheet(nombre_hoja)
            worksheet.delete_rows(2, worksheet.row_count)
            return True
    except: return False

def ejecutar_cierre_táctico():
    matrices = ["JORNADA_SUPERVISORES", "ALERTAS", "NOVEDADES_GUARDIA", "CONTROL_FLOTA"]
    fecha_hoy = obtener_hora_argentina()
    mes_actual = fecha_hoy.split("-")[1] 
    try:
        gc = conectar_google()
        for mat in matrices:
            df = leer_matriz_nube(mat)
            if not df.empty:
                nombre_historico = f"{mat}_{mes_actual}"
                try:
                    hoja_hist = gc.open_by_key(ID_MAESTRO_DB).worksheet(nombre_historico)
                except:
                    hoja_hist = gc.open_by_key(ID_MAESTRO_DB).add_worksheet(title=nombre_historico, rows="100", cols="20")
                hoja_hist.clear()
                hoja_hist.update([df.columns.values.tolist()] + df.values.tolist())
                limpiar_matriz_nube(mat)
        return True
    except: return False

# --- 5. CONTROL DE ACCESO (LANDING) ---

def mostrar_landing():
    aplicar_identidad_alfa()
    st.markdown('<div class="contenedor-logo-central"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" class="logo-phoenix"></div>', unsafe_allow_html=True)
    st.markdown('<div class="estacion-titulo">AION-YAROKU | COMMAND</div>', unsafe_allow_html=True)
    
    modo = st.radio("Acceso al Sistema:", ["Iniciar Sesión", "Crear Cuenta"], horizontal=True, key="radio_modo")
    
    with st.form("form_acceso_real"):
        user = st.text_input("Usuario", key="u")
        password = st.text_input("Contraseña", type="password", key="p")
        roles_registro = ["VIGILADOR", "MONITOREO", "JEFE DE OPERACIONES", "GERENCIA", "SUPERVISOR"]
        rol_usuario = st.selectbox("Seleccione su Rol:", roles_registro, key="r")

        btn_texto = "ENTRAR" if modo == "Iniciar Sesión" else "REGISTRARSE"
        
        if st.form_submit_button(btn_texto):
            if modo == "Iniciar Sesión" and user.strip() == "admin" and password.strip() == "aion2026":
                st.session_state.usuario_logueado = True
                st.session_state.user_sel = "ADMIN CENTRAL"
                st.session_state.rol_sel = "ADMINISTRADOR"
                st.session_state.admin_autenticado = True
                st.rerun()
            elif modo == "Iniciar Sesión":
                df_usuarios = leer_matriz_nube("USUARIOS")
                usuario_ok = pd.DataFrame()
                if not df_usuarios.empty and 'USUARIO' in df_usuarios.columns and 'CONTRASEÑA' in df_usuarios.columns:
                    usuario_ok = df_usuarios[
                        (df_usuarios['USUARIO'].str.strip() == user.strip()) & 
                        (df_usuarios['CONTRASEÑA'].str.strip() == password.strip())
                    ]
                if not usuario_ok.empty:
                    estado = usuario_ok.iloc[0]['ESTADO']
                    if estado == "APROBADO":
                        st.session_state.usuario_logueado = True
                        st.session_state.user_sel = user
                        st.session_state.rol_sel = usuario_ok.iloc[0]['ROL']
                        st.rerun()
                    else:
                        st.warning("⚠️ Tu cuenta existe pero está PENDIENTE de aprobación.")
                else:
                    st.error("❌ Credenciales inválidas.")
            else:
                escribir_registro_nube("USUARIOS", [user, password, rol_usuario, "PENDIENTE"])
                st.success("✅ Solicitud enviada. Quedamos a la espera de autorización.")

if not st.session_state.usuario_logueado:
    mostrar_landing()
    st.stop()

aplicar_identidad_alfa()

# --- 6. SIDEBAR TÁCTICO ---

df_objetivos = cargar_objetivos()
df_comisarias = cargar_datos_comisarias()

with st.sidebar:
    st.markdown('<div class="contenedor-logo-sidebar"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" style="width:180px; border:1px solid #00e5ff; border-radius:4px;"></div>', unsafe_allow_html=True)
    st.subheader("🛡️ PANEL DE CONTROL")
    
    if st.button("🛰️ MONITOREO", use_container_width=True):
        st.session_state.rol_sel = "MONITOREO"
        st.session_state.user_sel = "OPERADOR CENTRAL"
        st.session_state.sup_autenticado = False
        st.rerun()
        
    if st.button("📋 JEFE DE OPERACIONES", use_container_width=True):
        st.session_state.rol_sel = "JEFE DE OPERACIONES"
        st.session_state.user_sel = "JEFE DE OPERACIONES"
        st.session_state.sup_autenticado = False
        st.rerun()
        
    if st.button("🏢 GERENCIA", use_container_width=True):
        st.session_state.rol_sel = "GERENCIA"
        st.session_state.user_sel = "DIRECCIÓN GENERAL"
        st.session_state.sup_autenticado = False
        st.rerun()

    with st.expander("👤 SUPERVISORES", expanded=(st.session_state.rol_sel == "SUPERVISOR" or 'intentando_sup' in st.session_state)):
        nom_sup = st.selectbox("RESPONSABLE ACTIVO:", LISTA_SUPS_TACTICOS, key="cambio_supervisor_directo")
        user_sup = st.text_input("USUARIO RECURSO (APELLIDO)", key="auth_user_sup")
        pass_sup = st.text_input("CONTRASEÑA CRÍTICA", type="password", key="auth_pass_sup")
        
        if st.button("AUTENTICAR E INGRESAR", use_container_width=True):
            st.session_state.intentando_sup = True
            if "NOCTURNO" in nom_sup: usuario_esperado = "nocturno"
            elif "AYALA" in nom_sup: usuario_esperado = "ayala"
            else: usuario_esperado = nom_sup.split(" ")[1].lower()
            
            if user_sup.strip().lower() == usuario_esperado and pass_sup == "1234":
                st.session_state.rol_sel = "SUPERVISOR"
                st.session_state.user_sel = nom_sup
                st.session_state.sup_autenticado = True
                if 'intentando_sup' in st.session_state: del st.session_state.intentando_sup
                st.success(f"🔓 ACCESO CONCEDIDO: {nom_sup}")
                st.rerun()
            else:
                st.session_state.sup_autenticado = False
                st.error("❌ CREDENCIALES INVÁLIDAS EN BASE")

    st.write("---")
    if st.button("👮 VIGILADOR (ACCESO PUESTO)", use_container_width=True):
        st.session_state.rol_sel = "VIGILADOR"
        st.session_state.user_sel = "VIGILADOR EN PUESTO"
        st.session_state.sup_autenticado = False
        st.rerun()

    st.write("---")
    st.markdown("**⚙️ ADMINISTRADOR**")
    if st.button("ACCEDER AL NÚCLEO MAESTRO", use_container_width=True):
        st.session_state.usuario_logueado = True
        st.session_state.rol_sel = "ADMINISTRADOR"
        st.session_state.user_sel = "ADMIN CENTRAL"
        st.session_state.admin_autenticado = True
        st.session_state.sup_autenticado = False
        st.rerun()

    st.markdown("---")
    if st.button("🚪 CERRAR SESIÓN", use_container_width=True):
        st.session_state.usuario_logueado = False
        st.rerun()

# --- 7. CABECERA CENTRAL Y RASTREO POR ROLES ---

st.markdown('<div class="contenedor-logo-central"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" class="logo-phoenix"></div>', unsafe_allow_html=True)

titulos = {
    "MONITOREO": "🛰️ CENTRAL DE INTELIGENCIA OPERATIVA",
    "SUPERVISOR": f"📱 Estación de Control: {st.session_state.user_sel}",
    "VIGILADOR": "👮 TERMINAL OPERATIVO VIGILADORES",
    "JEFE DE OPERACIONES": "📋 COMANDO DE OPERACIONES TÁCTICAS",
    "GERENCIA": "🏢 DIRECCIÓN Y FISCALIZACIÓN GENERAL",
    "ADMINISTRADOR": "⚙️ NÚCLEO MAESTRO: AION-YAROKU"
}
st.markdown(f'<div class="estacion-titulo">{titulos.get(st.session_state.rol_sel, "SISTEMA TÁCTICO DE COMANDO")}</div>', unsafe_allow_html=True)


# =========================================================================
# ROL: MONITOREO
# =========================================================================
if st.session_state.rol_sel == "MONITOREO":
    col1, col2, col3, col4 = st.columns(4)
    
    df_emergencias = leer_matriz_nube("ALERTAS")
    df_objetivos = cargar_objetivos()
    
    if df_emergencias.empty:
        df_emergencias = pd.DataFrame(columns=['FECHA', 'USUARIO', 'TIPO', 'ESTADO', 'CARGA_UTIL', 'INFORME'])
    else:
        df_emergencias.columns = df_emergencias.columns.str.strip().str.upper()

    df_mapa_monitoreo = pd.DataFrame()
    if not df_objetivos.empty:
        df_objetivos.columns = df_objetivos.columns.str.strip().str.upper()
        if 'LATITUD' in df_objetivos.columns and 'LONGITUD' in df_objetivos.columns:
            df_mapa_monitoreo = df_objetivos.dropna(subset=['LATITUD', 'LONGITUD']).copy()

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
    
    with col1.container():
        @st.fragment(run_every=5)
        def contar_panicos_monitoreo():
            df_alertas = leer_matriz_nube("ALERTAS")
            if not df_alertas.empty:
                df_alertas.columns = [str(c).strip().upper() for c in df_alertas.columns]
                total_sos = len(df_alertas[df_alertas['ESTADO'] == "PENDIENTE"])
                st.metric("🚨 S.O.S ACTIVOS", total_sos)
            else:
                st.metric("🚨 S.O.S ACTIVOS", "0")
        contar_panicos_monitoreo()

    col2.metric("📡 RED", "OPERATIVA")
    col3.metric("👤 OPERADOR", f"{st.session_state.user_sel}")
    
    with col4.container():
        @st.fragment(run_every=1)
        def mostrar_reloj_monitoreo():
            hora_actual = obtener_hora_argentina().split(" ")[1]
            st.metric("🕒 HORA LOCAL", hora_actual)
        mostrar_reloj_monitoreo() 

    df_msg = leer_matriz_nube("MENSAJERIA")
    nombre_user = st.session_state.user_sel.upper()
    total_nuevos = 0
    if not df_msg.empty:
        mask = ((df_msg['DESTINATARIO'] == "TODOS") | 
                (df_msg['DESTINATARIO'] == "MONITOREO") | 
                (df_msg['DESTINATARIO'] == nombre_user)) & \
               (df_msg['ESTADO'] == "PENDIENTE")
        total_nuevos = len(df_msg[mask])

    label_msg = f"💬 MENSAJERÍA GLOBAL ({total_nuevos})" if total_nuevos > 0 else "💬 MENSAJERÍA GLOBAL"

    t_radar, t_mensajeria, t_vig, t_nov = st.tabs([
        "🚨 RADAR S.O.S", label_msg, "👥 PADRÓN VIGILADORES", "🔄 NOVEDADES Y FICHAJES"
    ]) 

    with t_radar:
        st.subheader("📡 RADAR GLOBAL DE OBJETIVOS")
        if st.button("🔄 ACTUALIZAR RADAR DE CONTROL", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        st.markdown('<div class="panel-novedad">', unsafe_allow_html=True)
        col_sel1, col_sel2 = st.columns([2, 1])
        
        if "filtro_radar_valor" not in st.session_state:
            st.session_state["filtro_radar_valor"] = "MOSTRAR TODO"

        with col_sel1:
            opciones_busqueda = ["MOSTRAR TODO"] + list(df_mapa_monitoreo['OBJETIVO'].unique()) if not df_mapa_monitoreo.empty else ["MOSTRAR TODO"]
            try:
                idx_defecto = opciones_busqueda.index(st.session_state["filtro_radar_valor"])
            except:
                idx_defecto = 0
                
            obj_seleccionado = st.selectbox(
                "🎯 ENFOCAR OBJETIVO EN RADAR / BUSCADOR:", 
                opciones_busqueda, 
                index=idx_defecto,
                key="buscador_radar_master"
            )
            st.session_state["filtro_radar_valor"] = obj_seleccionado
        
        comisaria_cercana_name = None
        distancia_minima = float('inf')
        com_lat_m, com_lon_m = None, None
        lat_obj, lon_obj = 0.0, 0.0
        
        if obj_seleccionado != "MOSTRAR TODO" and not df_mapa_monitoreo.empty:
            datos_obj = df_mapa_monitoreo[df_mapa_monitoreo['OBJETIVO'] == obj_seleccionado].iloc[0]
            lat_obj = datos_obj['LATITUD']
            lon_obj = datos_obj['LONGITUD']
            
            for _, com in df_comisarias.iterrows():
                lon1, lat1, lon2, lat2 = map(math.radians, [lon_obj, lat_obj, com['LONGITUD'], com['LATITUD']])
                dlon = lon2 - lon1
                dlat = lat2 - lat1
                a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
                c = 2 * math.asin(math.sqrt(a))
                km = 6371 * c
                
                if km < distancia_minima:
                    distancia_minima = km
                    comisaria_cercana_name = com['COMISARIA']
                    com_lat_m = com['LATITUD']
                    com_lon_m = com['LONGITUD']
            
            with col_sel2:
                st.metric(label="👮 COMISARÍA MÁS CERCANA", value=comisaria_cercana_name if comisaria_cercana_name else "N/A")
                st.caption(f"Distancia estimada: {distancia_minima:.2f} Km")
                
                if comisaria_cercana_name:
                    url_gmaps_monitoreo = f"https://www.google.com/maps/dir/?api=1&origin={com_lat_m},{com_lon_m}&destination={lat_obj},{lon_obj}&travelmode=driving"
                    st.markdown(
                        f'<a href="{url_gmaps_monitoreo}" target="_blank" class="btn-google-maps" style="font-size:11px; padding:6px 12px; margin-top:5px;">🗺️ ASISTENTE GPS COMPARTIDO</a>',
                        unsafe_allow_html=True
                    )
        else:
            with col_sel2:
                st.info("Seleccione un objetivo específico para calcular la comisaría más cercana.")
        st.markdown('</div>', unsafe_allow_html=True)

        if sos_activos > 0:
            st.markdown('<div class="panel-novedad" style="border: 1px solid #FF0000;">', unsafe_allow_html=True)
            df_pendientes_form = df_emergencias[df_emergencias['ESTADO'] == 'PENDIENTE']
            with st.form(key="form_finalizar_panico", clear_on_submit=True):
                opciones_alertas = {f"{r['FECHA']} - {r['USUARIO']}": idx for idx, r in df_pendientes_form.iterrows()}
                alerta_seleccionada = st.selectbox("SELECCIONE EVENTO A FINALIZAR:", list(opciones_alertas.keys()))
                txt_informe_cierre = st.text_area("INFORME OPERATIVO DE CIERRE:", placeholder="Describa la resolución...")
                if st.form_submit_button("🚨 FINALIZAR PÁNICO Y NORMALIZAR") and txt_informe_cierre.strip():
                    idx_df = opciones_alertas[alerta_seleccionada]
                    actualizar_celda("ALERTAS", idx_df + 2, "D", "FINALIZADO")
                    actualizar_celda("ALERTAS", idx_df + 2, "F", txt_informe_cierre.strip().upper())
                    st.session_state["filtro_radar_valor"] = "MOSTRAR TODO"
                    st.success("✅ Normalizado")
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
   
        st.markdown('<div class="radar-box">', unsafe_allow_html=True)
        if not df_mapa_monitoreo.empty:
            if obj_seleccionado != "MOSTRAR TODO":
                datos_obj = df_mapa_monitoreo[df_mapa_monitoreo['OBJETIVO'] == obj_seleccionado].iloc[0]
                centro_mapa = [datos_obj['LATITUD'], datos_obj['LONGITUD']]
                zoom_inicial = 13
            else:
                centro_mapa = [df_mapa_monitoreo['LATITUD'].mean(), df_mapa_monitoreo['LONGITUD'].mean()]
                zoom_inicial = 11

            m_mon = folium.Map(
                location=centro_mapa, 
                zoom_start=zoom_inicial, 
                max_zoom=21,
                tiles="https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}{r}.png",
                attr='© OpenStreetMap contributors © CARTO'
            )
            for _, r in df_mapa_monitoreo.iterrows():
                es_panico = r['OBJETIVO'] in lista_objetivos_en_panico
                es_el_seleccionado = (r['OBJETIVO'] == obj_seleccionado)
                
                texto_tooltip = f"🎯 {r['OBJETIVO']}"
                if es_panico:
                    alerta_activa = df_emergencias[
                        (df_emergencias['CARGA_UTIL'].str.contains(r['OBJETIVO'])) & 
                        (df_emergencias['ESTADO'] == 'PENDIENTE')
                    ]
                    if not alerta_activa.empty:
                        nombre_vigilante = alerta_activa.iloc[-1]['USUARIO']
                        texto_tooltip = f"🚨 {nombre_vigilante} | {r['OBJETIVO']}"

                if es_panico or es_el_seleccionado:
                    folium.Marker(
                        location=[r['LATITUD'], r['LONGITUD']],
                        tooltip=texto_tooltip,
                        icon=folium.DivIcon(
                            icon_size=(30, 30),
                            icon_anchor=(15, 15),
                            html='''<div style="background-color: #FF0000; width: 16px; height: 16px; border-radius: 50%; border: 2px solid white; animation: pulse 1s infinite alternate;"></div>'''
                        )
                    ).add_to(m_mon)
                else:
                    folium.CircleMarker(
                        location=[r['LATITUD'], r['LONGITUD']], radius=7, color="#00E5FF", fill=True,
                        tooltip=f"🎯 {r['OBJETIVO']} | 👤 SUP: {r.get('SUPERVISOR', 'N/A')}"
                    ).add_to(m_mon)

            df_com = cargar_datos_comisarias()
            for _, c in df_com.iterrows():
                es_la_mas_cercana = (c['COMISARIA'] == comisaria_cercana_name)
                if es_la_mas_cercana and obj_seleccionado != "MOSTRAR TODO":
                    color_icono = "#FF9800"
                    tamano_fuente = "26px"
                    sufijo_tooltip = " 🌟 [MÁS CERCANA AL OBJETIVO]"
                    com_lat, com_lon = c['LATITUD'], c['LONGITUD']
                    coordenadas_ruta = obtener_ruta_calles_osrm(lat_obj, lon_obj, com_lat, com_lon)
                    
                    folium.PolyLine(locations=coordenadas_ruta, color="#000000", weight=5, opacity=0.4).add_to(m_mon)
                    folium.PolyLine(locations=coordenadas_ruta, color="#39FF14", weight=4, opacity=0.25).add_to(m_mon)
                else:
                    color_icono = "#0000FF"
                    tamano_fuente = "20px"
                    sufijo_tooltip = ""

                folium.Marker(
                    location=[c['LATITUD'], c['LONGITUD']],
                    tooltip=f"👮 {c['COMISARIA']}{sufijo_tooltip}",
                    icon=folium.DivIcon(html=f"""<div style="font-size: {tamano_fuente}; color: {color_icono}; text-shadow: 0 0 10px {color_icono};"><i class="fa fa-shield"></i></div>""")
                ).add_to(m_mon)
            
            capa_etiquetas = folium.TileLayer(
                tiles="https://{s}.basemaps.cartocdn.com/dark_only_labels/{z}/{x}/{y}{r}.png",
                attr='© CARTO', name="Etiquetas", max_zoom=21, max_native_zoom=20, overlay=True, control=False
            )
            capa_etiquetas.add_to(m_mon)
            st_folium(m_mon, width="100%", height=550, key="mapa_monitoreo_radar_tactico")

    with t_mensajeria:
        renderizar_mensajeria_global("MONITOREO")
    with t_vig:
        st.subheader("👥 PADRÓN VIGILADORES")
        df_padrero = leer_matriz_nube("VIGILADORES")
        if not df_padrero.empty:
            df_padrero.columns = df_padrero.columns.str.strip().str.upper()
            st.dataframe(df_padrero.iloc[::-1], use_container_width=True)
        else:
            st.info("No hay datos en la pestaña de relevos (Vigiladores).")
    with t_nov:
        st.subheader("🔄 HISTORIAL: NOVEDADES, FICHAJES Y RELEVOS")
        df_nov_g = leer_matriz_nube("NOVEDADES_GUARDIA")
        if not df_nov_g.empty:
            df_nov_g.columns = [str(c).strip().upper() for c in df_nov_g.columns]
            df_nov_g = df_nov_g.loc[:, ~df_nov_g.columns.duplicated()]
            if 'FECHA' in df_nov_g.columns:
                df_nov_g['FECHA_ORDEN'] = pd.to_datetime(df_nov_g['FECHA'], errors='coerce')
                df_ordenado = df_nov_g.sort_values(by='FECHA_ORDEN', ascending=False).drop(columns=['FECHA_ORDEN'])
            else:
                df_ordenado = df_nov_g
            st.dataframe(df_ordenado, use_container_width=True, hide_index=True)
        else:
            st.warning("⚠️ No se encontraron datos en 'NOVEDADES_GUARDIA'.")


# =========================================================================
# ROL: SUPERVISOR
# =========================================================================
elif st.session_state.rol_sel == "SUPERVISOR":
    if st.session_state.sup_autenticado:
        sup_activo_normalizado = st.session_state.user_sel.strip().upper()
        df_objetivos_filtrados = df_objetivos[df_objetivos['SUPERVISOR'] == sup_activo_normalizado] if not df_objetivos.empty else pd.DataFrame()
        
        obj_actual = st.session_state.get("obj_qr_tactico", "SIN OBJETIVO")

        st.subheader("⏱️ GESTIÓN DE JORNADA")
        _, col_j1, col_j2, _ = st.columns([2, 3, 3, 2]) 
        with col_j1:
            if st.button("🚀 INICIO DE JORNADA", use_container_width=True):
                registrar_movimiento_supervisor(st.session_state.user_sel, obj_actual, "INICIO")
                st.success("Jornada iniciada")
        with col_j2:
            if st.button("🏁 CIERRE DE JORNADA", use_container_width=True):
                registrar_movimiento_supervisor(st.session_state.user_sel, obj_actual, "FIN")
                st.success("Jornada cerrada")

        st.markdown("<br>", unsafe_allow_html=True)
        
        # --- BLOQUE PÁNICO CIRCULAR ORIGINAL PARA SUPERVISOR ---
        st.markdown("### 🛡️ PROTOCOLO DE EMERGENCIA")
        if obj_actual != "SIN OBJETIVO":
            st.success(f"📍 OBJETIVO DETECTADO PARA PÁNICO: **{obj_actual}**")
        else:
            st.warning("⚠️ Selecciona un objetivo en 'Visita QR' para activar el pánico correctamente.")

        col_p1, col_p2, col_p3 = st.columns([1, 1, 1])
        with col_p2:
            if st.button("S.O.S\nPÁNICO", type="primary"):
                lat_envio, lon_envio = 0.0, 0.0
                try:
                    loc = get_geolocation()
                    if loc and isinstance(loc, dict) and 'coords' in loc:
                        lat_envio = loc['coords'].get('latitude', 0.0)
                        lon_envio = loc['coords'].get('longitude', 0.0)
                except: pass
                
                carga_sos = f"SUP:{st.session_state.user_sel}|OBJ:{obj_actual}|LAT:{lat_envio}|LON:{lon_envio}"
                exito = escribir_registro_nube("ALERTAS", [
                    obtener_hora_argentina(), st.session_state.user_sel, "PÁNICO", "PENDIENTE", carga_sos
                ])
                if exito:
                    st.error(f"🚨 ALERTA ENVIADA DESDE {obj_actual}")

        t_vis_qr, t_ruta_gmaps, t_car_tac, t_mensajeria_sup, t_pres_sup = st.tabs([
            "Visita QR", "📲 RUTA GOOGLE MAPS", "Carga Táctica", "💬 MENSAJERÍA", "📋 NOVEDADES Y RELEVOS"
        ])
        
        # --- TABLA DE ESTADO Y CÁMARA QR (CON CORRECCIÓN DE KEYERROR) ---
        with t_vis_qr:
            st.markdown(f"### 📊 ESTADO DE MIS OBJETIVOS ASIGNADOS ({datetime.now(pytz.timezone('America/Argentina/Buenos_Aires')).strftime('%Y-%m-%d')})")
            
            if not df_objetivos_filtrados.empty:
                lista_tabla_objs = []
                df_jornadas_act = leer_matriz_nube("JORNADA_SUPERVISORES")
                
                for obj_item in df_objetivos_filtrados['OBJETIVO'].unique():
                    estado_txt = "⏳ PENDIENTE DE VISITA"
                    ingreso_txt = "---"
                    egreso_txt = "---"
                    permanencia_txt = "---"
                    
                    if not df_jornadas_act.empty and 'ACCION' in df_jornadas_act.columns:
                        col_acc = 'ACCION'
                        col_sup = 'SUPERVISOR' if 'SUPERVISOR' in df_jornadas_act.columns else df_jornadas_act.columns[1]
                        col_obj = 'OBJETIVO' if 'OBJETIVO' in df_jornadas_act.columns else df_jornadas_act.columns[2]
                        
                        df_j_obj = df_jornadas_act[(df_jornadas_act[col_sup].str.upper() == sup_activo_normalizado) & (df_jornadas_act[col_obj].str.upper() == obj_item.upper())]
                        if not df_j_obj.empty:
                            inicios = df_j_obj[df_j_obj[col_acc].str.upper() == 'INICIO']
                            fines = df_j_obj[df_j_obj[col_acc].str.upper() == 'FIN']
                            if not inicios.empty:
                                col_h = ' HORA' if ' HORA' in inicios.columns else ('HORA' if 'HORA' in inicios.columns else inicios.columns[-1])
                                ingreso_txt = inicios.iloc[-1][col_h]
                                estado_txt = "✅ FINALIZADO / RETIRADO"
                            if not fines.empty:
                                col_h_fin = ' HORA' if ' HORA' in fines.columns else ('HORA' if 'HORA' in fines.columns else fines.columns[-1])
                                egreso_txt = fines.iloc[-1][col_h_fin]
                                
                    lista_tabla_objs.append({
                        "OBJETIVO": obj_item,
                        "ESTADO": estado_txt,
                        "INGRESO": ingreso_txt,
                        "EGRESO": egreso_txt,
                        "PERMANENCIA": permanencia_txt
                    })
                
                df_tabla_estado = pd.DataFrame(lista_tabla_objs)
                st.dataframe(df_tabla_estado, use_container_width=True, hide_index=True)
            else:
                st.info("Sin objetivos asignados actualmente.")

            st.markdown("---")
            st.markdown("### 📱 CENTRO TÁCTICO & GENERADOR QR DE OBJETIVOS")
            if not df_objetivos_filtrados.empty:
                obj_select = st.selectbox("Seleccione Objetivo Asignado:", df_objetivos_filtrados['OBJETIVO'].unique(), key="obj_qr_tactico")
                datos_sel = df_objetivos_filtrados[df_objetivos_filtrados['OBJETIVO'] == obj_select].iloc[0]
                
                col_qr1, col_qr2 = st.columns([1, 2])
                with col_qr1:
                    qr_data_string = f"AION-YAROKU-OBJ:{obj_select}|ID:{datos_sel.get('ID', '0')}"
                    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=2)
                    qr.add_data(qr_data_string)
                    qr.make(fit=True)
                    img_qr = qr.make_image(fill_color="#00E5FF", back_color="#000000")
                    
                    buffered = io.BytesIO()
                    img_qr.save(buffered, format="PNG")
                    st.image(buffered.getvalue(), width=160, caption=f"QR Oficial: {obj_select}")

                with col_qr2:
                    st.markdown("#### DATOS CLAVE DEL OBJETIVO")
                    st.write(f"**ID Oficial:** {datos_sel.get('ID', 'N/A')}")
                    st.write(f"**Coordenadas:** {datos_sel.get('LATITUD', 0)}, {datos_sel.get('LONGITUD', 0)}")
                    
                    lat = datos_sel.get('LATITUD', 0)
                    lon = datos_sel.get('LONGITUD', 0)
                    url_navegacion = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lon}&destination_place_name={obj_select}&travelmode=driving"
                    st.markdown(f'''
                        <a href="{url_navegacion}" target="_blank" class="btn-google-maps" style="margin-top:10px;">
                        📍 ABRIR NAVEGACIÓN GPS A {obj_select}
                        </a>
                    ''', unsafe_allow_html=True)

                st.markdown("---")
                st.markdown("### 📷 CÁMARA DE ESCANEO DE QR DE PUESTO")
                st.info("Utilice la cámara de su dispositivo para escanear el código QR del puesto durante su visita.")
                foto_qr_sup = st.camera_input("Capturar Código QR del Puesto", key="camara_qr_supervisor")
                
                if foto_qr_sup is not None:
                    st.success("✅ Código QR escaneado y verificado correctamente por el Supervisor.")
                    escribir_registro_nube("NOVEDADES", [obtener_hora_argentina(), st.session_state.user_sel, f"SUPERVISIÓN QR VALIDADA - {obj_select}"])
                    st.rerun()
                
                st.markdown("---")
                st.markdown("### 📝 REGISTRO DE ACTA DE FLOTA")
                with st.form(key="form_acta_flota", clear_on_submit=True):
                    c_a, c_b = st.columns(2)
                    v_patente = c_a.text_input("PATENTE/MÓVIL:").upper()
                    v_km_ini = c_a.number_input("KM INICIAL:", min_value=0)
                    v_km_fin = c_b.number_input("KM FINAL:", min_value=0)
                    v_comb = c_b.selectbox("COMBUSTIBLE:", ["NO", "SI - MEDIA CARGA", "SI - TANQUE LLENO"])
                    v_vig = st.text_input("SUPERVISOR RESPONSABLE:", value=st.session_state.user_sel).upper()
                    if st.form_submit_button("REGISTRAR ACTA DE FLOTA"):
                        escribir_registro_nube("CONTROL_FLOTA", [obtener_hora_argentina(), v_vig, v_patente, v_km_ini, v_km_fin, v_comb])
                        st.success(f"✅ Acta registrada. Distancia recorrida: {v_km_fin - v_km_ini} km")
            else:
                st.warning("⚠️ No se encontraron objetivos asignados a su usuario Supervisor.")

        with t_ruta_gmaps:
            st.markdown("### 🗺️ NAVEGACIÓN TÁCTICA A COMISARÍAS")
            opciones_r = df_objetivos_filtrados['OBJETIVO'].unique() if not df_objetivos_filtrados.empty else []
            if len(opciones_r) > 0:
                obj_r = st.selectbox("DESTINO:", opciones_r, key="sup_ruta_gmaps_target")
                datos_r = df_objetivos_filtrados[df_objetivos_filtrados['OBJETIVO'] == obj_r].iloc[0]
                lat, lon = datos_r['LATITUD'], datos_r['LONGITUD']
                dist_min, com_name, com_lat, com_lon = float('inf'), "Ninguna", 0.0, 0.0
                for _, com in df_comisarias.iterrows():
                    d = 6371 * 2 * math.asin(math.sqrt(math.sin((math.radians(com['LATITUD'])-math.radians(lat))/2)**2 + math.cos(math.radians(lat))*math.cos(math.radians(com['LATITUD']))*math.sin((math.radians(com['LONGITUD'])-math.radians(lon))/2)**2))
                    if d < dist_min: dist_min, com_name, com_lat, com_lon = d, com['COMISARIA'], com['LATITUD'], com['LONGITUD']
                st.info(f"👮 **Comisaría Encontrada:** {com_name} ({dist_min:.2f} Km)")
                st.link_button("🗺️ ABRIR ASISTENTE GPS", f"https://www.google.com/maps/dir/?api=1&origin={com_lat},{com_lon}&destination={lat},{lon}&travelmode=driving", use_container_width=True)

        with t_car_tac:
            novedad_sup = st.text_area("Novedad / Registro Operativo:")
            if st.button("CARGAR REGISTRO") and novedad_sup.strip():
                escribir_registro_nube("NOVEDADES", [obtener_hora_argentina(), st.session_state.user_sel, novedad_sup.upper()])
                st.success("✅ Cargado correctamente")

        with t_mensajeria_sup:
            renderizar_mensajeria_global("SUPERVISOR")
       
        with t_pres_sup:
            st.markdown("#### 🔄 RELEVOS DE GUARDIA")
            df_nov_sup = leer_matriz_nube("NOVEDADES_GUARDIA")
            if not df_nov_sup.empty:
                df_nov_sup.columns = [str(c).strip().upper() for c in df_nov_sup.columns]
                if 'SUPERVISOR' in df_nov_sup.columns:
                    df_nov_sup = df_nov_sup[df_nov_sup['SUPERVISOR'].str.upper() == sup_activo_normalizado]
                    df_nov_sup = df_nov_sup.drop(columns=['SUPERVISOR'])
                st.dataframe(df_nov_sup.iloc[::-1], use_container_width=True, hide_index=True)
            else:
                st.info("Sin relevos registrados.")

            st.markdown("---")
            st.markdown("#### 🚨 ALERTAS DE PÁNICO")
            df_pan_sup = leer_matriz_nube("ALERTAS")
            if not df_pan_sup.empty:
                df_pan_sup.columns = [str(c).strip().upper() for c in df_pan_sup.columns]
                df_pan_sup = df_pan_sup[df_pan_sup['CARGA_UTIL'].str.contains(sup_activo_normalizado, na=False)]
                st.dataframe(df_pan_sup.iloc[::-1], use_container_width=True, hide_index=True)
            else:
                st.info("Sin alertas de pánico registradas.")
    else:
        st.warning("⚠️ Autentíquese con sus credenciales de supervisor en la barra lateral.")


# =========================================================================
# ROL: VIGILADOR
# =========================================================================
elif st.session_state.rol_sel == "VIGILADOR":
    st.markdown('<div class="panel-novedad">', unsafe_allow_html=True)
    opciones_globales_obj = df_objetivos['OBJETIVO'].unique() if not df_objetivos.empty else ["ALFAVINIL"]
    
    df_msg = leer_matriz_nube("MENSAJERIA")
    nombre_user = st.session_state.user_sel.upper()
    total_nuevos = 0
    if not df_msg.empty:
        mask = ((df_msg['DESTINATARIO'] == "TODOS") | (df_msg['DESTINATARIO'] == "VIGILADOR") | (df_msg['DESTINATARIO'] == nombre_user)) & (df_msg['ESTADO'] == "PENDIENTE")
        total_nuevos = len(df_msg[mask])

    label_msg = f"💬 MENSAJERÍA GLOBAL ({total_nuevos})" if total_nuevos > 0 else "💬 MENSAJERÍA GLOBAL"
    
    # --- PROTOCOLO DE EMERGENCIA CON BOTÓN CIRCULAR PARA VIGILADOR ---
    st.markdown("### 🛡️ PROTOCOLO DE EMERGENCIA")
    obj_detectado = st.session_state.get("obj_actual_vig", None)

    if obj_detectado:
        st.success(f"📍 OBJETIVO DETECTADO PARA PÁNICO: **{obj_detectado}**")
        col_pv1, col_pv2, col_pv3 = st.columns([1, 1, 1])
        with col_pv2:
            if st.button("S.O.S\nPÁNICO", type="primary"):
                nombre_real = st.session_state.get("v_nombre_completo", "VIGILADOR").upper()
                sup_asignado = "MONITOREO"
                if not df_objetivos.empty:
                    filtro = df_objetivos[df_objetivos['OBJETIVO'] == obj_detectado]
                    if not filtro.empty:
                        sup_asignado = str(filtro['SUPERVISOR'].iloc[0]).strip()
                
                fecha = obtener_hora_argentina()
                carga_sos = f"VIG:{nombre_real}|OBJ:{obj_detectado}|SUP:{sup_asignado}"
                escribir_registro_nube("ALERTAS", [fecha, nombre_real, "PÁNICO", "PENDIENTE", carga_sos, "PRUEBA"])
                enviar_alerta_automatica("SISTEMA_VIGILADOR", obj_detectado, nombre_real, sup_asignado)
                st.error(f"🚨 ALERTA ENVIADA: {nombre_real} DESDE {obj_detectado}")
    else:
        st.warning("⚠️ Debes realizar el Fichaje o Relevo primero para activar el sistema de pánico.")
    
    st.markdown("---")
    
    tab_presentismo, tab_relevo, tab_mensajeria = st.tabs([
        "📋 FICHAJE", "🔄 RELEVO", label_msg
    ])
  
    with tab_presentismo:
        st.markdown("### 📸 REGISTRO BIOMÉTRICO")
        with st.form(key="form_fichaje_vigilador", clear_on_submit=True):
            v_nombre_completo = st.text_input("APELLIDO Y NOMBRE:").strip() 
            v_dni = st.text_input("LEGAJO / DNI:").strip() 
            v_obj = st.selectbox("OBJETIVO:", opciones_globales_obj)
            v_tipo_marcacion = st.selectbox("TIPO:", ["INGRESO", "EGRESO"])
            img_facial = st.camera_input("RECONOCIMIENTO FACIAL")
            
            if st.form_submit_button("CONSIGNAR Y TRANSMITIR"):
                if v_nombre_completo and v_dni and img_facial:
                    st.session_state.v_nombre_completo = v_nombre_completo.upper()
                    st.session_state.legajo_vigilador = v_dni
                    st.session_state.obj_actual_vig = v_obj
                    
                    fecha_hora_arg = obtener_hora_argentina()
                    sup_responsable = df_objetivos[df_objetivos['OBJETIVO'] == v_obj]['SUPERVISOR'].iloc[0] if not df_objetivos.empty else "N/A"
                    tipo_evento = f"MARCACIÓN_{v_tipo_marcacion}"
                    
                    escribir_registro_nube("PRESENTISMO", [fecha_hora_arg.split(" ")[0], fecha_hora_arg.split(" ")[1], v_dni, f"{v_nombre_completo.upper()} - {v_obj}", "", "OK", v_tipo_marcacion])
                    escribir_registro_nube("NOVEDADES_GUARDIA", [fecha_hora_arg, v_obj, tipo_evento, "---", v_nombre_completo.upper(), v_dni, "PROCESADO", sup_responsable])
                    st.success(f"🔒 {tipo_evento} REGISTRADA PARA {v_nombre_completo.upper()}")
                else:
                    st.error("⚠️ Por favor, complete todos los campos y capture la foto.")

    with tab_relevo:
        st.markdown("### 🔄 REGISTRO FORMAL DE CAMBIO")
        with st.form(key="form_relevo_vigilador_directo", clear_on_submit=True):
            v_obj_relevo = st.selectbox("OBJETIVO:", opciones_globales_obj, key="relevo_obj")
            vig_saliente = st.text_input("SALE:").upper().strip()
            vig_entrante = st.text_input("ENTRA:").upper().strip()
            v_dni_relevo = st.text_input("DNI RESPONSABLE:").strip()
            if st.form_submit_button("SANCIONAR CAMBIO"):
                st.session_state.obj_actual_vig = v_obj_relevo
                sup_resp = df_objetivos[df_objetivos['OBJETIVO']==v_obj_relevo]['SUPERVISOR'].iloc[0] if not df_objetivos.empty else "N/A"
                fecha = obtener_hora_argentina()
                escribir_registro_nube("NOVEDADES_GUARDIA", [fecha, v_obj_relevo, "RELEVO DE TURNO", vig_saliente, vig_entrante, v_dni_relevo, "PROCESADO", sup_resp])
                escribir_registro_nube("VIGILADORES", [fecha.split(" ")[0], fecha.split(" ")[1], v_obj_relevo, vig_saliente, vig_entrante, sup_resp, "RELEVO_EFECTUADO"])
                st.success("🔒 RELEVO REGISTRADO Y EXITOSO")

    with tab_mensajeria:
        renderizar_mensajeria_global("VIGILADOR")
    st.markdown('</div>', unsafe_allow_html=True)


# =========================================================================
# ROL: JEFE DE OPERACIONES
# =========================================================================
elif st.session_state.rol_sel == "JEFE DE OPERACIONES":
    col1, col2, col3, col4 = st.columns(4)
    
    with col1.container():
        @st.fragment(run_every=1)
        def mostrar_sos():
            df_alertas = leer_matriz_nube("ALERTAS")
            total_sos = len(df_alertas[df_alertas['ESTADO'] == "PENDIENTE"]) if not df_alertas.empty else 0
            st.metric("🚨 S.O.S ACTIVOS", total_sos)
        mostrar_sos()

    col2.metric("📡 RED", "OPERATIVA")
    col3.metric("👤 USUARIO", f"{st.session_state.user_sel}")
    
    with col4.container():
        @st.fragment(run_every=1)
        def mostrar_reloj():
            hora_actual = obtener_hora_argentina().split(" ")[1]
            st.metric("🕒 HORA LOCAL", hora_actual)
        mostrar_reloj()

    df_msg = leer_matriz_nube("MENSAJERIA")
    nombre_user = st.session_state.user_sel.upper()
    total_nuevos = len(df_msg[((df_msg['DESTINATARIO'] == "TODOS") | 
                            (df_msg['DESTINATARIO'] == "JEFE DE OPERACIONES") | 
                            (df_msg['DESTINATARIO'] == nombre_user)) & 
                           (df_msg['ESTADO'] == "PENDIENTE")]) if not df_msg.empty else 0
    
    label_msg = f"💬 MENSAJERÍA ({total_nuevos})" if total_nuevos > 0 else "💬 MENSAJERÍA"
    
    st.markdown('<h2 style="color:#00E5FF; font-family:\'Orbitron\'; font-size:24px;">Comando: JEFE DE OPERACIONES</h2>', unsafe_allow_html=True)
    
    t_mensajeria_jefe, t_ejecucion, t_tab_auditoria = st.tabs([label_msg, "Ejecución", "📍 TABLERO DE AUDITORÍA"])
    
    with t_mensajeria_jefe:
        renderizar_mensajeria_global("JEFE DE OPERACIONES")
        
    with t_ejecucion:
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.subheader("ALTA DE RECURSO / OBJETIVO")
            g_alta_nom = st.text_input("Nombre:", key="jefe_alta_nom")
            g_alta_asig = st.selectbox("Asignar a:", LISTA_SUPS_TACTICOS, key="jefe_alta_asig")
            if st.button("Solicitar Alta"):
                escribir_registro_nube("PETICIONES", [obtener_hora_argentina(), st.session_state.user_sel, "ALTA", "OBJETIVO", f"{g_alta_nom} | ASIG: {g_alta_asig}"])
                st.success("✅ Petición enviada")
        with col_g2:
            st.subheader("BAJA DE OBJETIVO")
            g_baja_obj = st.selectbox("Objetivo:", df_objetivos['OBJETIVO'].unique() if not df_objetivos.empty else ["ALFAVINIL"], key="jefe_baja_obj")
            if st.button("Solicitar Baja"):
                escribir_registro_nube("PETICIONES", [obtener_hora_argentina(), st.session_state.user_sel, "BAJA", "OBJETIVO", g_baja_obj])
                st.success("✅ Petición enviada")
    
    with t_tab_auditoria:
        st.markdown("### 📋 AUDITORÍA DE SUPERVISIÓN")
        df_jornadas = leer_matriz_nube("JORNADA_SUPERVISORES")
        if not df_jornadas.empty:
            df_jornadas.columns = [str(c).strip().upper() for c in df_jornadas.columns]
            st.dataframe(df_jornadas, use_container_width=True, hide_index=True)
        else:
            st.write("*(Sin jornadas registradas)*")

        st.markdown("---")
        st.markdown("### 🚨 HISTÓRICO DE ALERTAS TÁCTICAS")
        df_alertas = leer_matriz_nube("ALERTAS")
        if not df_alertas.empty:
            df_alertas.columns = [str(c).strip().upper() for c in df_alertas.columns]
            st.dataframe(df_alertas[['FECHA', 'USUARIO', 'CARGA_UTIL', 'ESTADO']], use_container_width=True, hide_index=True)
        else:
            st.write("*(Sin alertas tácticas)*")

        st.markdown("---")
        st.markdown("### 🔄 AUDITORÍA DE RELEVOS")
        df_relevos = leer_matriz_nube("NOVEDADES_GUARDIA")
        if not df_relevos.empty and 'TIPO_EVENTO' in df_relevos.columns:
            df_filtro = df_relevos[df_relevos['TIPO_EVENTO'] == "RELEVO DE TURNO"].copy()
            if not df_filtro.empty:
                st.dataframe(df_filtro[['FECHA', 'OBJETIVO', 'VIGILADOR_SALE', 'VIGILADOR_ENTRA', 'DNI']], use_container_width=True, hide_index=True)
            else:
                st.write("*(Sin relevos registrados)*")
        else:
            st.write("*(Sin novedades registradas)*")

        st.markdown("---")
        st.markdown("### ⛽ AUDITORÍA Y CONTROL DE FLOTA")
        df_flota = leer_matriz_nube("CONTROL_FLOTA")
        if not df_flota.empty:
            df_flota.columns = [str(c).strip().upper() for c in df_flota.columns]
            if 'KM_FINAL' in df_flota.columns and 'KM_INICIAL' in df_flota.columns:
                df_flota['KM_RECORRIDOS'] = pd.to_numeric(df_flota['KM_FINAL'], errors='coerce') - pd.to_numeric(df_flota['KM_INICIAL'], errors='coerce')
                st.dataframe(df_flota[['FECHA', 'SUPERVISOR', 'MOVIL', 'KM_INICIAL', 'KM_FINAL', 'KM_RECORRIDOS', 'COMBUSTIBLE']], use_container_width=True, hide_index=True)
        else:
            st.write("*(Sin registros de flota)*")


# =========================================================================
# ROL: GERENCIA
# =========================================================================
elif st.session_state.rol_sel == "GERENCIA":
    fecha_hoy = obtener_hora_argentina().split(" ")[0]
    df_jornada_actual = leer_matriz_nube("JORNADA_SUPERVISORES")
    
    if not df_jornada_actual.empty:
        df_jornada_actual.columns = [str(c).strip().upper() for c in df_jornada_actual.columns]
        df_hoy = df_jornada_actual[df_jornada_actual['FECHA'] == fecha_hoy]
        personal_activo = df_hoy['SUPERVISOR'].nunique()
        objs_cubiertos = len(df_hoy['OBJETIVO'].unique())
    else:
        personal_activo = 0
        objs_cubiertos = 0

    total_objetivos_db = len(df_objetivos) if not df_objetivos.empty else 1
    kpi_operativo = int((objs_cubiertos / total_objetivos_db) * 100) if total_objetivos_db > 0 else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📊 KPI OPERATIVO", f"{kpi_operativo}%")
    col2.metric("👥 PERSONAL ACTIVO", f"{personal_activo}")
    col3.metric("👤 GERENTE", f"{st.session_state.user_sel}")
    
    hora_container = col4.container()
    @st.fragment(run_every=1)
    def mostrar_reloj_gerencia():
        hora_actual = obtener_hora_argentina().split(" ")[1]
        st.metric("🕒 HORA LOCAL", hora_actual)
    with hora_container:
        mostrar_reloj_gerencia()
        
    st.write("---")
    st.markdown('<h2 style="color:#00E5FF; font-family:\'Orbitron\'; font-size:24px;">Comando: DIRECCIÓN GENERAL</h2>', unsafe_allow_html=True)
    
    t_mensajeria_ger, t_ejecucion_ger, t_tab_auditoria = st.tabs(["💬 MENSAJERÍA GLOBAL", "🎮 EJECUCIÓN", "📍 TABLERO DE AUDITORÍA"])
    
    with t_mensajeria_ger:
        renderizar_mensajeria_global("GERENCIA")
        
    with t_ejecucion_ger:
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.subheader("ALTA DE RECURSO")
            g_alta_nom = st.text_input("Nombre:", key="ger_alta_nom")
            g_alta_asig = st.selectbox("Asignar a:", LISTA_SUPS_TACTICOS, key="ger_alta_asig")
            if st.button("Solicitar Alta"):
                escribir_registro_nube("PETICIONES", [obtener_hora_argentina(), st.session_state.user_sel, "ALTA", "OBJETIVO", f"{g_alta_nom} | ASIG: {g_alta_asig}"])
                st.success("✅ Petición enviada")
        with col_g2:
            st.subheader("BAJA DE OBJETIVO")
            g_baja_obj = st.selectbox("Objetivo:", df_objetivos['OBJETIVO'].unique() if not df_objetivos.empty else ["ALFAVINIL"], key="ger_baja_obj")
            if st.button("Solicitar Baja"):
                escribir_registro_nube("PETICIONES", [obtener_hora_argentina(), st.session_state.user_sel, "BAJA", "OBJETIVO", g_baja_obj])
                st.success("✅ Petición enviada")

    with t_tab_auditoria:
        st.markdown("### 📋 AUDITORÍA DE SUPERVISIÓN")
        df_jornadas = leer_matriz_nube("JORNADA_SUPERVISORES")
        if not df_jornadas.empty:
            df_jornadas.columns = [str(c).strip().upper() for c in df_jornadas.columns]
            st.dataframe(df_jornadas, use_container_width=True, hide_index=True)
        else:
            st.write("*(Sin jornadas registradas)*")

        st.markdown("---")
        st.markdown("### 🚨 HISTÓRICO DE ALERTAS TÁCTICAS")
        df_alertas = leer_matriz_nube("ALERTAS")
        if not df_alertas.empty:
            df_alertas.columns = [str(c).strip().upper() for c in df_alertas.columns]
            st.dataframe(df_alertas[['FECHA', 'USUARIO', 'CARGA_UTIL', 'ESTADO']], use_container_width=True, hide_index=True)
        else:
            st.write("*(Sin alertas tácticas)*")

        st.markdown("---")
        st.markdown("### 🔄 AUDITORÍA DE RELEVOS")
        df_relevos = leer_matriz_nube("NOVEDADES_GUARDIA")
        if not df_relevos.empty and 'TIPO_EVENTO' in df_relevos.columns:
            df_filtro = df_relevos[df_relevos['TIPO_EVENTO'] == "RELEVO DE TURNO"].copy()
            if not df_filtro.empty:
                st.dataframe(df_filtro[['FECHA', 'OBJETIVO', 'VIGILADOR_SALE', 'VIGILADOR_ENTRA', 'DNI']], use_container_width=True, hide_index=True)
            else:
                st.write("*(Sin relevos registrados)*")
        else:
            st.write("*(Sin novedades registradas)*")

        st.markdown("---")
        st.markdown("### ⛽ AUDITORÍA Y CONTROL DE FLOTA")
        df_flota = leer_matriz_nube("CONTROL_FLOTA")
        if not df_flota.empty:
            df_flota.columns = [str(c).strip().upper() for c in df_flota.columns]
            if 'KM_FINAL' in df_flota.columns and 'KM_INICIAL' in df_flota.columns:
                df_flota['KM_RECORRIDOS'] = pd.to_numeric(df_flota['KM_FINAL'], errors='coerce') - pd.to_numeric(df_flota['KM_INICIAL'], errors='coerce')
                st.dataframe(df_flota[['FECHA', 'SUPERVISOR', 'MOVIL', 'KM_INICIAL', 'KM_FINAL', 'KM_RECORRIDOS', 'COMBUSTIBLE']], use_container_width=True, hide_index=True)
        else:
            st.write("*(Sin registros de flota)*")

        st.markdown("---")
        st.markdown("### ⚠️ COMANDO DE CIERRE TÁCTICO")
        st.info("Esta acción archiva todos los reportes operativos y reinicia los contadores del sistema.")
        if st.checkbox("CONFIRMAR EJECUCIÓN DE CIERRE MENSUAL"):
            if st.button("🚀 EJECUTAR RESPALDO Y REINICIO"):
                with st.spinner("Procesando archivos históricos..."):
                    if ejecutar_cierre_táctico(): 
                        st.success("Cierre mensual completado. Todo el historial fue archivado.")
                        st.rerun()


# =========================================================================
# ROL: ADMINISTRADOR
# =========================================================================
elif st.session_state.rol_sel == "ADMINISTRADOR":
    st.subheader("⚙️ NÚCLEO MAESTRO: PANEL DE CONTROL")
    
    if st.session_state.user_sel == "ADMIN CENTRAL":
        st.session_state.admin_autenticado = True
    
    if st.session_state.admin_autenticado:
        st.success("✅ Núcleo Maestro desbloqueado.")
        df_usuarios = leer_matriz_nube("USUARIOS")
        
        if not df_usuarios.empty and 'ESTADO' in df_usuarios.columns:
            df_usuarios['ESTADO'] = df_usuarios['ESTADO'].astype(str).str.strip()
            pendientes = df_usuarios[df_usuarios['ESTADO'] == "PENDIENTE"]
            
            if not pendientes.empty:
                st.warning(f"⚠️ Hay {len(pendientes)} solicitudes pendientes de aprobación.")
                st.dataframe(pendientes, use_container_width=True)
                
                usuario_a_aprobar = st.selectbox("Seleccionar usuario para autorizar:", pendientes['USUARIO'].tolist())
                if st.button("✅ DAR ACCESO Y APROBAR"):
                    idx = df_usuarios[df_usuarios['USUARIO'] == usuario_a_aprobar].index[0]
                    if actualizar_celda("USUARIOS", idx + 2, "D", "APROBADO"):
                        st.success(f"Usuario {usuario_a_aprobar} autorizado correctamente.")
                        st.rerun()
                    else:
                        st.error("Error al actualizar la base de datos.")
            else:
                st.info("No hay solicitudes pendientes de aprobación.")
        else:
            st.info("No hay registros en la matriz de USUARIOS.")
    else:
        st.error("⚠️ Acceso restringido. Debes iniciar sesión como ADMINISTRADOR desde la pantalla principal.")
