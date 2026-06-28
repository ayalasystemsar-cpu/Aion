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
    
    modo = st.radio("Acceso al Sistema:", ["Iniciar Sesión", "Crear Cuenta"], horizontal=True, key="radio_modo")
    
    # UN SOLO FORMULARIO QUE MANEJA TODO
    with st.form("form_acceso_real"):
        user = st.text_input("Usuario", key="u")
        password = st.text_input("Contraseña", type="password", key="p")
            # Rol modificado para eliminar "ADMINISTRADOR" de la lista de registros
        roles_registro = ["VIGILADOR", "MONITOREO", "JEFE DE OPERACIONES", "GERENCIA", "SUPERVISOR"]
        rol_usuario = st.selectbox("Seleccione su Rol:", roles_registro, key="r")

        btn_texto = "ENTRAR" if modo == "Iniciar Sesión" else "REGISTRARSE"
        
        if st.form_submit_button(btn_texto):
            
            # --- NUEVA LÓGICA: ACCESO ADMINISTRADOR SIN APROBACIÓN ---
            if modo == "Iniciar Sesión" and user.strip() == "admin" and password.strip() == "aion2026":
                st.session_state.usuario_logueado = True
                st.session_state.user_sel = "ADMIN CENTRAL"
                st.session_state.rol_sel = "ADMINISTRADOR"
                st.rerun()
            
            # --- LÓGICA NORMAL PARA LOS DEMÁS ---
            elif modo == "Iniciar Sesión":
                df_usuarios = leer_matriz_nube("USUARIOS")
                
                # Buscamos fila donde usuario y pass coincidan
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
                # CREAR CUENTA
                escribir_registro_nube("USUARIOS", [user, password, rol_usuario, "PENDIENTE"])
                st.success("✅ Solicitud enviada. Quedamos a la espera de autorización.")

    # --- 4. LÓGICA PRINCIPAL ---
if not st.session_state.usuario_logueado:
    mostrar_landing()
    st.stop() # <--- ESTA ES LA LLAVE QUE DETIENE TODO SI NO HAY LOGIN

# --- A PARTIR DE AQUÍ COMIENZA TU CÓDIGO ORIGINAL ---
# (Tal cual lo tenías: sidebar, roles, mapas, etc.)
# Al no haber un 'else', este código corre igual que siempre.# Configuración de página OLED
st.set_page_config(
    page_title="AION-YAROKU | CORE",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CONEXIONES (GOOGLE MATRIZ) ---
ID_MAESTRO_DB = "1Md0VkOnwUJWldq0S1fB9UrmOKv4MG__JVG3tQsda0Uw"

def conectar_google():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        return gspread.authorize(creds)
    except: 
        return None

# --- 3. FUNCIONES DE LÓGICA E DATOS ---
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
        
@st.cache_resource
def obtener_grafo_zona(lat, lon):
    try:
        return ox.graph_from_point((lat, lon), dist=5000, network_type='drive')
    except:
        return None

def calcular_ruta_real(orig, dest):
    mid_lat = (orig[0] + dest[0]) / 2
    mid_lon = (orig[1] + dest[1]) / 2
    G = obtener_grafo_zona(mid_lat, mid_lon)
    
    if G is None: 
        return [orig, dest]
        
    try:
        orig_node = ox.distance.nearest_nodes(G, X=orig[1], Y=orig[0])
        dest_node = ox.distance.nearest_nodes(G, X=dest[1], Y=dest[0])
        ruta = nx.shortest_path(G, orig_node, dest_node, weight='length')
        return [(G.nodes[n]['y'], G.nodes[n]['x']) for n in ruta]
    except:
        return [orig, dest]

# Función dedicada a obtener el trazado exacto calle por calle vía OSRM (Estilo GPS)
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
            
            # --- BLINDAJE CONTRA DUPLICADOS ---
            # 1. Quitar espacios accidentales
            df.columns = [str(c).strip().upper() for c in df.columns]
            # 2. Eliminar columnas duplicadas (mantiene la primera ocurrencia)
            df = df.loc[:, ~df.columns.duplicated()]
            
            return df
        except Exception as e: 
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

def renderizar_mensajeria_global(rol_contexto):
    # 1. ESTADO DE RESPUESTA
    if 'asunto_respuesta' not in st.session_state:
        st.session_state.asunto_respuesta = None

    # 2. LECTURA DE DATOS
    df_msg = leer_matriz_nube("MENSAJERIA")
    
    st.subheader("💬 COMUNICACIONES OPERATIVAS")

    # 3. FORMULARIO DE ENVÍO
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

        # DENTRO DEL BOTÓN DE TRANSMITIR
        if st.form_submit_button("TRANSMITIR A LA RED"):
            if txt_msg.strip():
                escribir_registro_nube("MENSAJERIA", [
                    obtener_hora_argentina(), st.session_state.user_sel, destinatario, 
                    (asunto_input or "GENERAL").upper(), txt_msg.upper(), "PENDIENTE", gravedad
                ])
                
                # GUARDAMOS EL ESTADO PARA MOSTRAR EL CARTEL
                st.session_state.mensaje_enviado = "RESPUESTA" if st.session_state.asunto_respuesta else "MENSAJE"
                st.session_state.asunto_respuesta = None
                st.rerun()

    # ESTO DEBE IR JUSTO DESPUÉS DEL FORMULARIO PARA QUE SE VEA BIEN
    if 'mensaje_enviado' in st.session_state:
        if st.session_state.mensaje_enviado == "RESPUESTA":
            st.success("✅ RESPUESTA ENVIADA")
        else:
            st.success("✅ MENSAJE ENVIADO")
        
        # BORRAMOS LA VARIABLE PARA QUE EL CARTEL SE VAYA AL RECARGAR
        del st.session_state.mensaje_enviado

    # 4. VISUALIZACIÓN POR HILOS
    if not df_msg.empty:
        # Agrupamos por ASUNTO para ver las conversaciones
        # Aseguramos que la columna ASUNTO exista
        if 'ASUNTO' in df_msg.columns:
            for asunto, grupo in df_msg.groupby('ASUNTO'):
                with st.expander(f"💬 Hilo: {asunto}"):
                    for _, msg in grupo.iterrows():
                        st.markdown(f"**{msg.get('REMITENTE', 'ANÓNIMO')}:** {msg.get('MENSAJE', '')}")
                    
                    if st.button(f"Responder a este hilo", key=f"btn_{asunto}_{rol_contexto}"):
                        st.session_state.asunto_respuesta = asunto
                        st.rerun()
        else:
            st.warning("La base de datos no tiene una columna 'ASUNTO'. Verifica tu Google Sheet.")
            
def obtener_etiqueta_mensajeria(rol_contexto):
    df_msg = leer_matriz_nube("MENSAJERIA")
    if df_msg.empty:
        return "💬 MENSAJERÍA"
    
    nombre_user = st.session_state.user_sel.upper()
    mask = ((df_msg['DESTINATARIO'] == "TODOS") | 
            (df_msg['DESTINATARIO'] == rol_contexto.upper()) | 
            (df_msg['DESTINATARIO'] == nombre_user)) & \
           (df_msg['ESTADO'] == "PENDIENTE")
    
    total_nuevos = len(df_msg[mask])
    return f"💬 MENSAJERÍA ({total_nuevos})" if total_nuevos > 0 else "💬 MENSAJERÍA"

def registrar_movimiento_supervisor(supervisor, objetivo, accion):
    fecha_hora_arg = obtener_hora_argentina()
    fecha = fecha_hora_arg.split(" ")[0]
    hora = fecha_hora_arg.split(" ")[1]
    
    # Esta lista debe coincidir exactamente con el orden de las columnas de tu hoja
    datos = [fecha, supervisor, objetivo, accion, hora]
    
    exito = escribir_registro_nube("JORNADA_SUPERVISORES", datos)
    return exito

def enviar_alerta_automatica(emisor, objetivo, nombre_persona, supervisor_asignado):
    fecha = obtener_hora_argentina()
    mensaje = f"🚨 ALERTA DE PÁNICO: {nombre_persona} - OBJ: {objetivo}"
    
    # Destinatarios fijos
    destinatarios = ["JEFE DE OPERACIONES", "GERENCIA", supervisor_asignado]
    
    for dest in destinatarios:
        if dest and dest != "MONITOREO" and dest != "N/A":
            # [FECHA, EMISOR, DESTINATARIO, MENSAJE, ESTADO]
            escribir_registro_nube("MENSAJERIA", [fecha, emisor, dest, mensaje, "PENDIENTE"])

def aplicar_identidad_alfa():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@300;500;700&display=swap');
        .stApp { background: radial-gradient(circle at top, #0A0F1E 0%, #030305 100%) !important; color: #E0E0E0; font-family: 'Rajdhani', sans-serif; }
        .contenedor-logo-central { display: flex; justify-content: center; align-items: center; width: 100%; margin-bottom: 5px; margin-top: 10px; }
        .logo-phoenix { width: 520px !important; border: 2px solid #00e5ff !important; box-shadow: 0 0 35px rgba(0, 229, 255, 0.5) !important; border-radius: 4px !important; background-color: #000 !important; }
        
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
        .stButton > button[kind="primary"] { 
            background: radial-gradient(circle, #FF0000 0%, #8B0000 100%) !important;
            color: white !important; border-radius: 50% !important; width: 105px !important; height: 105px !important; 
            border: 3px solid #333 !important; box-shadow: 0 0 25px rgba(255, 0, 0, 0.5) !important; 
            font-family: 'Orbitron', sans-serif; font-size: 11px !important; font-weight: bold;
        }
        
        .message-box { border-left: 3px solid #00e5ff; padding-left: 10px; margin-bottom: 15px; background: rgba(255,255,255,0.02); padding-top: 5px; padding-bottom: 5px; }
        .message-box-red { border-left: 3px solid #ff0000; padding-left: 10px; margin-bottom: 15px; background: rgba(255,255,255,0.02); padding-top: 5px; padding-bottom: 5px; }
        .message-info { color: #00e5ff; font-size: 13px; font-weight: bold; font-family: 'Orbitron', sans-serif; }
        .message-text { color: #e0e0e0; font-size: 14px; margin-top: 4px; font-family: 'Rajdhani', sans-serif; }
        
        .panel-info { display: flex; justify-content: space-between; margin-bottom: 20px; padding: 10px; border: 1px solid #333; border-radius: 4px; background: rgba(10, 10, 11, 0.9); }
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

        /* NUEVO: Botón Pánico Fino */
        div.stButton > button[kind="secondary"].panico-fino { 
            border: 1px solid #FF4B4B !important;
            background: transparent !important;
            color: #FF4B4B !important;
            font-family: 'Orbitron', sans-serif !important;
            letter-spacing: 2px !important;
            width: 100% !important;
            transition: all 0.3s ease !important;
        }
        div.stButton > button[kind="secondary"].panico-fino:hover { background: rgba(255, 75, 75, 0.1) !important; }
        </style>
        """, unsafe_allow_html=True
    )

# --- SCRIPT PARA RELOJ EN TIEMPO REAL (SIN RERUNS NI ERRORES) ---
st.markdown("""
<script>
    function updateClock() {
        var now = new Date();
        var timeString = now.toLocaleTimeString('es-AR', {hour12: false});
        var reloj = document.getElementById('mi-reloj');
        if (reloj) {
            reloj.innerText = timeString;
        }
    }
    setInterval(updateClock, 1000);
</script>
""", unsafe_allow_html=True)

aplicar_identidad_alfa()

# --- 5. SIDEBAR TÁCTICO ---
df_objetivos = cargar_objetivos()
df_comisarias = cargar_datos_comisarias()
LISTA_SUPS_TACTICOS = [
    "AYALA BRIAN", "SUPERVISOR 1", "SUPERVISOR 2", "SUPERVISOR 3", "SUPERVISOR 4", "SUPERVISOR 5", "SUPERVISOR NOCTURNO"
]

if 'rol_sel' not in st.session_state: st.session_state.rol_sel = "MONITOREO"
if 'user_sel' not in st.session_state: st.session_state.user_sel = "OPERADOR CENTRAL"
if 'sup_autenticado' not in st.session_state: st.session_state.sup_autenticado = False

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
            else: usuario_esperado = nom_sup.split(" ")[1]
            
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
        st.session_state.usuario_logueado = True # <--- ESTO ES LO QUE TE FALTABA
        st.session_state.rol_sel = "ADMINISTRADOR"
        st.session_state.user_sel = "ADMIN CENTRAL"
        st.session_state.sup_autenticado = False
        st.rerun()

    st.markdown("---")
    if st.button("🚪 CERRAR SESIÓN", use_container_width=True):
        st.session_state.usuario_logueado = False
        st.rerun()

    

    st.write("---")
    

# --- 6. CABECERA CENTRAL ---
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


# --- 7. FLUJO POR ROLES INTEGRADO Y BLINDADO ---

if st.session_state.rol_sel == "MONITOREO":
    col1, col2, col3, col4 = st.columns(4)
    df_emergencias = leer_matriz_nube("ALERTAS")
    df_objetivos = cargar_objetivos()
    
    if df_emergencias.empty:
        df_emergencias = pd.DataFrame(columns=['FECHA', 'USUARIO', 'TIPO', 'ESTADO', 'CARGA_UTIL', 'INFORME'])
    else:
        df_emergencias.columns = df_emergencias.columns.str.strip().str.upper()

    df_mapa_monitoreo = df_objetivos.dropna(subset=['LATITUD', 'LONGITUD']).copy() if not df_objetivos.empty else pd.DataFrame()
    lista_objetivos_en_panico = [carga.split("OBJ:")[1].split("|")[0].strip().upper() 
                                 for _, row in df_emergencias[df_emergencias['ESTADO'] == 'PENDIENTE'].iterrows() 
                                 if "OBJ:" in str(row['CARGA_UTIL'])]

    with col1.container():
        @st.fragment(run_every=5)
        def contar_panicos():
            df_a = leer_matriz_nube("ALERTAS")
            total = len(df_a[df_a['ESTADO'] == "PENDIENTE"]) if not df_a.empty else 0
            st.metric("🚨 S.O.S ACTIVOS", total)
        contar_panicos()

    col2.metric("📡 RED", "OPERATIVA")
    col3.metric("👤 OPERADOR", f"{st.session_state.user_sel}")
    
    with col4.container():
        @st.fragment(run_every=1)
        def mostrar_reloj():
            st.metric("🕒 HORA LOCAL", obtener_hora_argentina().split(" ")[1])
        mostrar_reloj()

    label_msg = obtener_etiqueta_mensajeria("MONITOREO")
    t_radar, t_mensajeria, t_vig, t_nov = st.tabs(["🚨 RADAR S.O.S", label_msg, "👥 PADRÓN VIGILADORES", "🔄 NOVEDADES Y FICHAJES"]) 
    
    with t_radar:
        st.subheader("📡 RADAR GLOBAL DE OBJETIVOS")
        if st.button("🔄 ACTUALIZAR RADAR DE CONTROL", key="btn_radar_mon_final", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        opciones = ["MOSTRAR TODO"] + list(df_mapa_monitoreo['OBJETIVO'].unique()) if not df_mapa_monitoreo.empty else ["MOSTRAR TODO"]
        obj_sel = st.selectbox("🎯 ENFOCAR OBJETIVO:", opciones, key="radar_focus_final")
        
        m_mon = folium.Map(location=[-34.6, -58.4], zoom_start=11, tiles="cartodbdark_matter")
        for _, r in df_mapa_monitoreo.iterrows():
            if r['OBJETIVO'] == obj_sel:
                folium.Marker([r['LATITUD'], r['LONGITUD']], tooltip=f"🚨 {r['OBJETIVO']}", icon=folium.Icon(color="red")).add_to(m_mon)
            else:
                folium.CircleMarker([r['LATITUD'], r['LONGITUD']], radius=7, color="#00E5FF", fill=True, tooltip=r['OBJETIVO']).add_to(m_mon)
        
        for _, c in cargar_datos_comisarias().iterrows():
            folium.Marker([c['LATITUD'], c['LONGITUD']], tooltip=f"👮 {c['COMISARIA']}", icon=folium.Icon(color="blue", icon="shield")).add_to(m_mon)
        
        st_folium(m_mon, width="100%", height=550, key="mapa_monitoreo_radar_final")

    with t_mensajeria: renderizar_mensajeria_global("MONITOREO")
    with t_vig: st.dataframe(leer_matriz_nube("VIGILADORES"), use_container_width=True)
    with t_nov: st.dataframe(leer_matriz_nube("NOVEDADES_GUARDIA"), use_container_width=True)

elif st.session_state.rol_sel == "SUPERVISOR":
    st.subheader("📱 PANEL DE CONTROL SUPERVISOR")
    if st.session_state.sup_autenticado:
        tab1, tab2, tab3 = st.tabs(["🚀 JORNADA Y QR", "🗺️ NAVEGACIÓN", "💬 MENSAJERÍA"])
        with tab1:
            if st.button("🚀 INICIO DE JORNADA", key="sup_inicio", use_container_width=True):
                registrar_movimiento_supervisor(st.session_state.user_sel, "GENERAL", "INICIO")
            if st.button("🏁 CIERRE DE JORNADA", key="sup_cierre", use_container_width=True):
                registrar_movimiento_supervisor(st.session_state.user_sel, "GENERAL", "FIN")
        with tab2: st.info("Módulo de navegación activado.")
        with tab3: renderizar_mensajeria_global("SUPERVISOR")

elif st.session_state.rol_sel == "VIGILADOR":
    st.subheader("👮 TERMINAL VIGILADOR")
    tab1, tab2 = st.tabs(["📋 FICHAJE", "🚨 PÁNICO"])
    with tab1: st.write("Sistema de marcación activo.")
    with tab2: 
        if st.button("🚨 ACTIVAR PÁNICO TÁCTICO", key="panico_vig_final", type="primary"):
            st.error("Alerta enviada.")

elif st.session_state.rol_sel == "JEFE DE OPERACIONES":
    st.subheader("📋 COMANDO TÁCTICO")
    renderizar_mensajeria_global("JEFE DE OPERACIONES")

elif st.session_state.rol_sel == "GERENCIA":
    st.subheader("🏢 DIRECCIÓN GENERAL")
    renderizar_mensajeria_global("GERENCIA")

elif st.session_state.rol_sel == "ADMINISTRADOR":
    st.subheader("⚙️ NÚCLEO MAESTRO: PANEL DE CONTROL")
    if st.session_state.user_sel == "ADMIN CENTRAL":
        st.session_state.admin_autenticado = True
    if st.session_state.get("admin_autenticado"):
        st.success("✅ Núcleo Maestro desbloqueado.")
        df_usuarios = leer_matriz_nube("USUARIOS")
        if not df_usuarios.empty:
            df_usuarios['ESTADO'] = df_usuarios['ESTADO'].astype(str).str.strip()
            pendientes = df_usuarios[df_usuarios['ESTADO'] == "PENDIENTE"]
            if not pendientes.empty:
                st.warning(f"⚠️ Hay {len(pendientes)} solicitudes pendientes.")
                st.dataframe(pendientes, use_container_width=True)
                usuario_a_aprobar = st.selectbox("Seleccionar usuario:", pendientes['USUARIO'].tolist(), key="admin_sel_user")
                if st.button("✅ DAR ACCESO Y APROBAR", key="admin_btn_aprobar"):
                    idx = df_usuarios[df_usuarios['USUARIO'] == usuario_a_aprobar].index[0]
                    if actualizar_celda("USUARIOS", idx + 2, "D", "APROBADO"):
                        st.success("Usuario aprobado.")
                        st.rerun()
            else: st.info("No hay solicitudes pendientes.")
    else:
        st.error("⚠️ Acceso restringido.")



    
 
