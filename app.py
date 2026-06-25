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
import requests # Importante para conectar con el servidor de mapas de calles
from branca.element import Element # Para inyección de z-index nativo seguro

# Configuración de página OLED
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
        st.session_state.rol_sel = "ADMINISTRADOR"
        st.session_state.user_sel = "ADMIN CENTRAL"
        st.session_state.sup_autenticado = False
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

# --- 7. FLUJO POR ROLES ---
if st.session_state.rol_sel == "MONITOREO":
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
    
    c1, c2, c3 = st.columns(3)
    c1.metric("🚨 S.O.S ACTIVOS", sos_activos)
    c2.metric("📡 RED", "OPERATIVA")
    c3.metric("🕒 HORA LOCAL", obtener_hora_argentina().split(" ")[1])

  # 1. Calculamos el total de nuevos ANTES de definir la etiqueta
    df_msg = leer_matriz_nube("MENSAJERIA")
    nombre_user = st.session_state.user_sel.upper()
    
    total_nuevos = 0
    if not df_msg.empty:
        mask = ((df_msg['DESTINATARIO'] == "TODOS") | 
                (df_msg['DESTINATARIO'] == "MONITOREO") | 
                (df_msg['DESTINATARIO'] == nombre_user)) & \
               (df_msg['ESTADO'] == "PENDIENTE")
        total_nuevos = len(df_msg[mask])

    # 2. Creamos la etiqueta dinámica
    label_msg = f"💬 MENSAJERÍA GLOBAL ({total_nuevos})" if total_nuevos > 0 else "💬 MENSAJERÍA GLOBAL"

    # 3. Definimos los tabs usando esa variable
    t_radar, t_mensajeria, t_vig, t_nov = st.tabs([
        "🚨 RADAR S.O.S", label_msg, "👥 PADRÓN VIGILADORES", "🔄 NOVEDADES Y FICHAJES"
    ]) 
    with t_radar:
        st.subheader("📡 RADAR GLOBAL DE OBJETIVOS")
        if st.button("🔄 ACTUALIZAR RADAR DE CONTROL", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        # --- INTERFAZ DE SELECCIÓN Y ANÁLISIS TÁCTICO ---
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
                attr='© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors © <a href="https://carto.com/attributions">CARTO</a>'
            )
            for _, r in df_mapa_monitoreo.iterrows():
                es_panico = r['OBJETIVO'] in lista_objetivos_en_panico
                es_el_seleccionado = (r['OBJETIVO'] == obj_seleccionado)
                
                # --- LÓGICA DE IDENTIFICACIÓN ---
                texto_tooltip = f"🎯 {r['OBJETIVO']}" # Valor por defecto
                
                if es_panico:
                    alerta_activa = df_emergencias[
                        (df_emergencias['CARGA_UTIL'].str.contains(r['OBJETIVO'])) & 
                        (df_emergencias['ESTADO'] == 'PENDIENTE')
                    ]
                    if not alerta_activa.empty:
                        # Obtenemos el nombre real del vigilador de la columna USUARIO
                        nombre_vigilante = alerta_activa.iloc[-1]['USUARIO']
                        # Aquí tienes la combinación exacta: Nombre Vigilador + Objetivo
                        texto_tooltip = f"🚨 {nombre_vigilante} | {r['OBJETIVO']}"

                # DIBUJO DEL MARCADOR
                if es_panico or es_el_seleccionado:
                    folium.Marker(
                        location=[r['LATITUD'], r['LONGITUD']],
                        tooltip=texto_tooltip, # Mostramos la combinación exacta
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
                
                # --- SÁNDWICH DE CONTRASTE TRANSLÚCIDO ---
                folium.PolyLine(
                    locations=coordenadas_ruta,
                    color="#000000",
                    weight=5,
                    opacity=0.4
                ).add_to(m_mon)

                folium.PolyLine(
                    locations=coordenadas_ruta,
                    color="#39FF14",       
                    weight=4,              
                    opacity=0.25           
                ).add_to(m_mon)
            else:
                color_icono = "#0000FF"
                tamano_fuente = "20px"
                sufijo_tooltip = ""

            # Marcador de la comisaría
            folium.Marker(
                location=[c['LATITUD'], c['LONGITUD']],
                tooltip=f"👮 {c['COMISARIA']}{sufijo_tooltip}",
                icon=folium.DivIcon(html=f"""<div style="font-size: {tamano_fuente}; color: {color_icono}; text-shadow: 0 0 10px {color_icono};"><i class="fa fa-shield"></i></div>""")
            ).add_to(m_mon)
        
        capa_etiquetas = folium.TileLayer(
            tiles="https://{s}.basemaps.cartocdn.com/dark_only_labels/{z}/{x}/{y}{r}.png",
            attr='© <a href="https://carto.com/attributions">CARTO</a>',
            name="Etiquetas de Calles",
            max_zoom=21,         
            max_native_zoom=20,  
            overlay=True,
            control=False
        )
        capa_etiquetas.add_to(m_mon)
        
        script_z_index = Element("""
            <style>
                .leaflet-pane.leaflet-overlay-pane { z-index: 400 !important; }
                .leaflet-pane.leaflet-tile-pane { z-index: 200 !important; }
                .leaflet-layer:nth-last-child(1) { z-index: 500 !important; pointer-events: none; }
            </style>
        """)
        m_mon.get_root().header.add_child(script_z_index)
        
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
    

elif st.session_state.rol_sel == "SUPERVISOR":
    if st.session_state.sup_autenticado:
     # --- 0. GESTIÓN DE JORNADA ---
        st.subheader("⏱️ GESTIÓN DE JORNADA")
        
        # 1. Definimos las opciones de objetivos primero
        sup_activo_normalizado = st.session_state.user_sel.strip().upper()
        df_objs_sup = df_objetivos[df_objetivos['SUPERVISOR'] == sup_activo_normalizado] if not df_objetivos.empty else pd.DataFrame()
        opciones_obj = df_objs_sup['OBJETIVO'].unique() if not df_objs_sup.empty else ["SIN OBJETIVOS ASIGNADOS"]

        # 2. Selector de objetivo (DEBE IR ANTES DE LOS BOTONES)
        obj_seleccionado = st.selectbox("🎯 SELECCIONE OBJETIVO:", opciones_obj, key="obj_jornada_sel")
        
        col_j1, col_j2 = st.columns(2)
        with col_j1:
            if st.button("🚀 INICIO DE JORNADA", use_container_width=True):
                # Usamos obj_seleccionado en lugar de "N/A"
                registrar_movimiento_supervisor(st.session_state.user_sel, obj_seleccionado, "INICIO")
                st.success(f"Jornada iniciada en {obj_seleccionado}")
        with col_j2:
            if st.button("🏁 CIERRE DE JORNADA", use_container_width=True):
                # Usamos obj_seleccionado en lugar de "N/A"
                registrar_movimiento_supervisor(st.session_state.user_sel, obj_seleccionado, "FIN")
                st.success(f"Jornada cerrada en {obj_seleccionado}")

      # --- BOTÓN DE PÁNICO (CORREGIDO) ---
        st.markdown("<br>", unsafe_allow_html=True)
        
        # 1. DEFINIMOS LAS COLUMNAS AQUÍ
        _, col_panico, _ = st.columns([1, 2, 1]) 
        
        # 2. LAS USAMOS INMEDIATAMENTE
        with col_panico:
            if st.button("🚨 ACTIVAR PÁNICO", type="primary", use_container_width=True):
                # Usamos el estado del selectbox definido arriba
                obj_alerta = st.session_state.get("obj_jornada_sel", "UBICACIÓN DESCONOCIDA")
                
                lat_envio, lon_envio = 0.0, 0.0
                try:
                    loc = get_geolocation()
                    if loc and isinstance(loc, dict) and 'coords' in loc:
                        lat_envio = loc['coords'].get('latitude', 0.0)
                        lon_envio = loc['coords'].get('longitude', 0.0)
                except: 
                    pass
                
                carga_sos = f"LAT:{lat_envio}|LON:{lon_envio}|OBJ:{obj_alerta}|SUP:{st.session_state.user_sel}"
                escribir_registro_nube("ALERTAS", [obtener_hora_argentina(), st.session_state.user_sel, "PÁNICO", "PENDIENTE", carga_sos])
                st.error(f"🚨 S.O.S ENVIADO DESDE: {obj_alerta}")
     

        # --- 2. REGISTRO DIRECTO ---
        st.markdown("---")
        st.subheader("📍 REGISTRO DIRECTO (SIN QR)")
        sup_activo_normalizado = st.session_state.user_sel.strip().upper()
        df_objetivos_filtrados = df_objetivos[df_objetivos['SUPERVISOR'] == sup_activo_normalizado] if not df_objetivos.empty else pd.DataFrame()
        
        opciones_obj = df_objetivos_filtrados['OBJETIVO'].unique()
        if len(opciones_obj) > 0:
            obj_select = st.selectbox("Seleccione Objetivo:", opciones_obj, key="obj_select_directo")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ ARRIBO DIRECTO", use_container_width=True):
                    registrar_movimiento_supervisor(st.session_state.user_sel, obj_select, "ARRIBO")
                    st.success(f"Arribo en {obj_select}")
            with c2:
                if st.button("🚪 RETIRO DIRECTO", use_container_width=True):
                    registrar_movimiento_supervisor(st.session_state.user_sel, obj_select, "RETIRO")
                    st.success(f"Retiro en {obj_select}")
        else:
            st.warning("No hay objetivos asignados para registro directo.")

        # --- 3. MENSAJERÍA Y TABS ---
        df_msg = leer_matriz_nube("MENSAJERIA")
        nombre_user = st.session_state.user_sel.upper()
        total_nuevos = 0
        if not df_msg.empty:
            mask = ((df_msg['DESTINATARIO'] == "TODOS") | (df_msg['DESTINATARIO'] == "SUPERVISORES") | (df_msg['DESTINATARIO'] == nombre_user)) & (df_msg['ESTADO'] == "PENDIENTE")
            total_nuevos = len(df_msg[mask])
        
        label_msg = f"💬 MENSAJERÍA GLOBAL ({total_nuevos})" if total_nuevos > 0 else "💬 MENSAJERÍA GLOBAL"

        t_vis_qr, t_ruta_gmaps, t_car_tac, t_mensajeria_sup, t_pres_sup = st.tabs([
            "Visita QR", "📲 RUTA GOOGLE MAPS", "Carga Táctica", label_msg, "📋 NOVEDADES Y RELEVOS"
        ])

        # ... (Aquí debajo van tus 'with' de cada pestaña como los tenías antes) ...
      

        with t_vis_qr:
            st.markdown("### 📱 ESCANEO TÁCTICO PARA SUPERVISORES")
            st.subheader("🖨️ GENERADOR DE QR")
            if not df_objetivos_filtrados.empty:
                lista_objs = df_objetivos_filtrados['OBJETIVO'].unique()
                obj_a_generar = st.selectbox("Seleccione objetivo:", lista_objs)
                if obj_a_generar:
                    url_final = f"https://tu-app-de-aion.streamlit.app/?obj={obj_a_generar.replace(' ', '%20')}"
                    import qrcode
                    qr = qrcode.QRCode(version=1, box_size=15, border=3)
                    qr.add_data(url_final)
                    qr.make(fit=True)
                    img = qr.make_image(fill_color="black", back_color="white")
                    st.image(img.get_image(), width=300, caption=f"QR para {obj_a_generar}")
            else:
                st.warning("No hay objetivos asignados.")

        with t_ruta_gmaps:
            st.markdown("### 🗺️ NAVEGACIÓN TÁCTICA VÍA GOOGLE MAPS")
            opciones_servicios_r = df_objetivos_filtrados['OBJETIVO'].unique() if not df_objetivos_filtrados.empty else []
            
            if len(opciones_servicios_r) > 0:
                obj_ruta_sup = st.selectbox("SELECCIONE OBJETIVO DESTINO:", opciones_servicios_r, key="sup_ruta_gmaps_target")
                
                datos_obj_r = df_objetivos_filtrados[df_objetivos_filtrados['OBJETIVO'] == obj_ruta_sup].iloc[0]
                lat_target = datos_obj_r['LATITUD']
                lon_target = datos_obj_r['LONGITUD']
                
                comisaria_r_name = None
                com_lat_target, com_lon_target = None, None
                dist_min_r = float('inf')
                
                for _, com in df_comisarias.iterrows():
                    ln1, lt1, ln2, lt2 = map(math.radians, [lon_target, lat_target, com['LONGITUD'], com['LATITUD']])
                    dln = ln2 - ln1
                    dlt = lt2 - lt1
                    a = math.sin(dlt/2)**2 + math.cos(lt1) * math.cos(lt2) * math.sin(dln/2)**2
                    c = 2 * math.asin(math.sqrt(a))
                    km = 6371 * c
                    
                    if km < dist_min_r:
                        dist_min_r = km
                        comisaria_r_name = com['COMISARIA']
                        com_lat_target = com['LATITUD']
                        com_lon_target = com['LONGITUD']
                
                if comisaria_r_name:
                    st.info(f"👮 **Comisaría Encontrada:** {comisaria_r_name} (Distancia: {dist_min_r:.2f} Km)")
                    
                    # Generamos el enlace para Google Maps
                    url_gmaps = f"https://www.google.com/maps/dir/?api=1&origin={com_lat_target},{com_lon_target}&destination={lat_target},{lon_target}&travelmode=driving"
                    
                    st.markdown(
                        f'<a href="{url_gmaps}" target="_blank" class="btn-google-maps" style="background-color: #4285F4; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: block; text-align: center;">🗺️ ABRIR ASISTENTE GPS EN GOOGLE MAPS</a>',
                        unsafe_allow_html=True
                    )
                    st.caption("⚠️ Al presionar el botón, se abrirá la aplicación de Google Maps en tu dispositivo con el trazado GPS listo para iniciar la navegación.")
            else:
                st.warning("No tenés objetivos asignados para trazar rutas de emergencia en este turno.")

        with t_car_tac:
            novedad_sup = st.text_area("Novedad / Registro Operativo:")
            if st.button("CARGAR REGISTRO") and novedad_sup.strip():
                escribir_registro_nube("NOVEDADES", [obtener_hora_argentina(), st.session_state.user_sel, novedad_sup.upper()])
                st.success("✅ Cargado")

        with t_mensajeria_sup:
            renderizar_mensajeria_global("SUPERVISOR")
       
        with t_pres_sup:
            st.markdown("### 📋 NOVEDADES DE MI GRUPO ASIGNADO")
            # Código cerrado correctamente
                
                
elif st.session_state.rol_sel == "VIGILADOR":
    st.markdown('<div class="panel-novedad">', unsafe_allow_html=True)
    opciones_globales_obj = df_objetivos['OBJETIVO'].unique() if not df_objetivos.empty else ["ALFAVINIL"]
    
    # 1. Calculamos el total de mensajes pendientes
    df_msg = leer_matriz_nube("MENSAJERIA")
    nombre_user = st.session_state.user_sel.upper()
    total_nuevos = 0
    if not df_msg.empty:
        mask = ((df_msg['DESTINATARIO'] == "TODOS") | (df_msg['DESTINATARIO'] == "VIGILADOR") | (df_msg['DESTINATARIO'] == nombre_user)) & (df_msg['ESTADO'] == "PENDIENTE")
        total_nuevos = len(df_msg[mask])

    label_msg = f"💬 MENSAJERÍA GLOBAL ({total_nuevos})" if total_nuevos > 0 else "💬 MENSAJERÍA GLOBAL"
    
    # 2. Definimos los tabs
    tab_presentismo, tab_relevo, tab_mensajeria, tab_panico = st.tabs([
        "📋 FICHAJE", "🔄 RELEVO", label_msg, "🚨 PÁNICO"
    ])
  
    # 3. Pestaña Fichaje
    with tab_presentismo:
        st.markdown("### 📸 REGISTRO BIOMÉTRICO")
        with st.form(key="form_fichaje_vigilador", clear_on_submit=True):
            v_nombre_completo = st.text_input("APELLIDO Y NOMBRE:").strip() 
            v_dni = st.text_input("LEGAJO:").strip() 
            v_obj = st.selectbox("OBJETIVO:", opciones_globales_obj)
            v_tipo_marcacion = st.selectbox("TIPO:", ["INGRESO", "EGRESO"])
            img_facial = st.camera_input("RECONOCIMIENTO FACIAL")
            
            if st.form_submit_button("CONSIGNAR Y TRANSMITIR"):
                if v_nombre_completo and v_dni and img_facial:
                    # 1. GUARDAMOS EL NOMBRE Y LEGAJO EN LA SESIÓN (Para el botón de Pánico)
                    st.session_state.v_nombre_completo = v_nombre_completo.upper()
                    st.session_state.legajo_vigilador = v_dni
                    
                    # 2. PROCESAMOS EL REGISTRO EN LA NUBE
                    fecha_hora_arg = obtener_hora_argentina()
                    sup_responsable = df_objetivos[df_objetivos['OBJETIVO'] == v_obj]['SUPERVISOR'].iloc[0] if not df_objetivos.empty else "N/A"
                    tipo_evento = f"MARCACIÓN_{v_tipo_marcacion}"
                    
                    # Registro en Presentismo
                    escribir_registro_nube("PRESENTISMO", [
                        fecha_hora_arg.split(" ")[0], fecha_hora_arg.split(" ")[1], 
                        v_dni, f"{v_nombre_completo.upper()} - {v_obj}", "", "OK", v_tipo_marcacion
                    ])
                    
                    # Registro en Novedades Guardia
                    escribir_registro_nube("NOVEDADES_GUARDIA", [
                        fecha_hora_arg, v_obj, tipo_evento, "---", 
                        v_nombre_completo.upper(), v_dni, "PROCESADO", sup_responsable
                    ])
                    
                    st.success(f"🔒 {tipo_evento} REGISTRADA PARA {v_nombre_completo.upper()}")
                else:
                    st.error("⚠️ Por favor, complete todos los campos y capture la foto.")
                

    # 4. Pestaña de Relevo (LA QUE QUERÍAS RECUPERAR)
    with tab_relevo:
        st.markdown("### 🔄 REGISTRO FORMAL DE CAMBIO")
        with st.form(key="form_relevo_vigilador_directo", clear_on_submit=True):
            v_obj_relevo = st.selectbox("OBJETIVO:", opciones_globales_obj, key="relevo_obj")
            vig_saliente = st.text_input("SALE:").upper().strip()
            vig_entrante = st.text_input("ENTRA:").upper().strip()
            v_dni_relevo = st.text_input("DNI RESPONSABLE:").strip()
            if st.form_submit_button("SANCIONAR CAMBIO"):
                sup_resp = df_objetivos[df_objetivos['OBJETIVO']==v_obj_relevo]['SUPERVISOR'].iloc[0] if not df_objetivos.empty else "N/A"
                fecha = obtener_hora_argentina()
                escribir_registro_nube("NOVEDADES_GUARDIA", [fecha, v_obj_relevo, "RELEVO DE TURNO", vig_saliente, vig_entrante, v_dni_relevo, "PROCESADO", sup_resp])
                escribir_registro_nube("VIGILADORES", [fecha.split(" ")[0], fecha.split(" ")[1], v_obj_relevo, vig_saliente, vig_entrante, sup_resp, "RELEVO_EFECTUADO"])
                st.success("🔒 RELEVO REGISTRADO Y EXITOSO")

    # 5. Pestaña Mensajería
    with tab_mensajeria:
        renderizar_mensajeria_global("VIGILADOR")

    # 6. Pestaña Pánico (Instantáneo)
    with tab_panico:
        st.markdown("### 🛡️ PROTOCOLO DE EMERGENCIA")
        st.warning("⚠️ AL PRESIONAR EL BOTÓN, SE NOTIFICARÁ A MONITOREO Y A SU SUPERVISOR.")
        
        obj_vigilador = st.selectbox("CONFIRME SU OBJETIVO ACTUAL:", opciones_globales_obj, key="panico_obj")
        
        if st.checkbox("HABILITAR BOTÓN DE ALERTA"):
            if st.button("🚨 ACTIVAR ALERTA TÁCTICA", key="btn_panico_final", type="primary", use_container_width=True):
                
                # --- AQUÍ ESTÁ EL CAMBIO ---
                # Buscamos el nombre que el vigilador puso en el formulario de fichaje
                # Si no existe, al menos intentamos leerlo de la sesión
                nombre_real = st.session_state.get("v_nombre_completo", st.session_state.get("user_sel", "VIGILADOR"))
                
                sup_asignado = "MONITOREO"
                if not df_objetivos.empty:
                    filtro = df_objetivos[df_objetivos['OBJETIVO'] == obj_vigilador]
                    if not filtro.empty:
                        sup_asignado = str(filtro['SUPERVISOR'].iloc[0]).strip()
                
                fecha = obtener_hora_argentina()
                # Registramos el nombre real (nombre_real) en lugar de user_sel
                carga_sos = f"VIG:{nombre_real}|OBJ:{obj_vigilador}|SUP:{sup_asignado}"
                
                # EN LA HOJA ALERTAS, GUARDAMOS EL NOMBRE REAL EN LA COLUMNA USUARIO
                escribir_registro_nube("ALERTAS", [fecha, nombre_real, "PÁNICO", "PENDIENTE", carga_sos, "SIN INFORME"])
                
                st.error(f"🚨 ALERTA ENVIADA: {nombre_real}")
                
elif st.session_state.rol_sel == "JEFE DE OPERACIONES":
    # Cabecera métricas
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🚨 S.O.S ACTIVOS", "0")
    col2.metric("📡 RED", "OPERATIVA")
    col3.metric("👤 USUARIO", f"{st.session_state.user_sel}")
    col4.metric("🕒 HORA LOCAL", obtener_hora_argentina().split(" ")[1])

    # 1. Calculamos el total de nuevos para el JEFE DE OPERACIONES
    df_msg = leer_matriz_nube("MENSAJERIA")
    nombre_user = st.session_state.user_sel.upper()
    
    total_nuevos = 0
    if not df_msg.empty:
        mask = ((df_msg['DESTINATARIO'] == "TODOS") | 
                (df_msg['DESTINATARIO'] == "JEFE DE OPERACIONES") | 
                (df_msg['DESTINATARIO'] == nombre_user)) & \
               (df_msg['ESTADO'] == "PENDIENTE")
        total_nuevos = len(df_msg[mask])

    # 2. Etiqueta dinámica
    label_msg = f"💬 MENSAJERÍA GLOBAL ({total_nuevos})" if total_nuevos > 0 else "💬 MENSAJERÍA GLOBAL"

    # 3. Definición de pestañas (AGREGAMOS T_AUDITORIA)
    t_mensajeria_jefe, t_crisis, t_ejecucion, t_auditoria = st.tabs([label_msg, "Centro de Crisis", "Ejecución", "📋 AUDITORÍA"])

    # Pestaña 1: Mensajería Global
    with t_mensajeria_jefe:
        renderizar_mensajeria_global("JEFE DE OPERACIONES")

    # Pestaña 2: Centro de Crisis
    with t_crisis:
        st.subheader("📡 RADAR Y AUDITORÍA INTERACTIVA DE SERVICIOS")
        st.markdown('<div class="radar-box">', unsafe_allow_html=True)
        
        df_obj_maps_jefe = df_objetivos.dropna(subset=['LATITUD', 'LONGITUD'])
        centro = [df_obj_maps_jefe['LATITUD'].mean(), df_obj_maps_jefe['LONGITUD'].mean()] if not df_obj_maps_jefe.empty else [-34.6, -58.4]
        
        m_visor = folium.Map(location=centro, zoom_start=12, tiles="CartoDB dark_matter")
        if not df_obj_maps_jefe.empty:
            for _, r in df_obj_maps_jefe.iterrows():
                folium.Marker(
                    [r['LATITUD'], r['LONGITUD']], 
                    popup=r['OBJETIVO'],
                    tooltip=f"Clic para auditar: {r['OBJETIVO']}", 
                    icon=folium.Icon(color="cadetblue", icon="shield", prefix="fa")
                ).add_to(m_visor)
        
        mapa_retorno = st_folium(m_visor, width="100%", height=500, key="map_jefe_operaciones_crisis")
        st.markdown('</div>', unsafe_allow_html=True)
        
        objetivo_cliqueado = None
        if mapa_retorno and mapa_retorno.get("last_object_clicked_popup"):
            objetivo_cliqueado = mapa_retorno["last_object_clicked_popup"].strip().upper()
        
        if objetivo_cliqueado:
            st.markdown(f'### 📊 CONSOLA TÁCTICA DE AUDITORÍA: {objetivo_cliqueado}')
            df_match_obj = df_objetivos[df_objetivos['OBJETIVO'] == objetivo_cliqueado]
            sup_resp = df_match_obj['SUPERVISOR'].values[0] if not df_match_obj.empty else "NO ASIGNADO"
            pan1, pan2 = st.columns([1, 2])
            with pan1:
                st.markdown('<div class="panel-novedad" style="margin-top:0px;">', unsafe_allow_html=True)
                st.markdown(f"**👤 SUPERVISOR RESPONSABLE:**<br><span style=\"color:#00E5FF; font-family:'Orbitron'; font-size:16px;\">{sup_resp}</span>", unsafe_allow_html=True)
                st.write("---")
                st.markdown("**🔄 ÚLTIMO RELEVO REGISTRADO:**", unsafe_allow_html=True)
                df_rel = leer_matriz_nube("VIGILADORES")
                if not df_rel.empty:
                    df_rel.columns = df_rel.columns.str.strip().str.upper()
                    df_rel_obj = df_rel[df_rel['OBJETIVO'] == objetivo_cliqueado]
                    if not df_rel_obj.empty:
                        rel = df_rel_obj.iloc[-1]
                        st.write(f"📅 **Fecha:** {rel.get('FECHA', 'N/A')}")
                        st.write(f"🛑 **Sale:** {rel.get('VIGILADOR_SALIENTE', 'N/A')}")
                        st.write(f"🟢 **Entra:** {rel.get('VIGILADOR_ENTRANTE', 'N/A')}")
                st.markdown('</div>', unsafe_allow_html=True)

    # Pestaña 3: Ejecución
    with t_ejecucion:
        st.markdown('<div class="panel-novedad">', unsafe_allow_html=True)
        st.subheader("🚨 PETICIÓN DE ALTA/BAJA")
        o_accion = st.selectbox("Acción:", ["ALTA", "BAJA"])
        o_cat = st.selectbox("Categoría:", ["OBJETIVO", "MÓVIL", "RECURSO HUMANO"])
        o_det = st.text_input("Nombre / Detalle:")
        if st.button("ELEVAR PETICIÓN"):
            if o_det.strip():
                escribir_registro_nube("PETICIONES", [obtener_hora_argentina(), st.session_state.user_sel, o_accion, o_cat, o_det])
                st.success("✅ Petición Elevada Exitosamente")
        st.markdown('</div>', unsafe_allow_html=True)

    # Pestaña 4: Auditoría de Supervisión (NUEVA)
    with t_auditoria:
        st.subheader("📋 AUDITORÍA DE SUPERVISIÓN")
        df_jornadas = leer_matriz_nube("JORNADA_SUPERVISORES")
        
        if not df_jornadas.empty:
            # 1. Limpieza y preparación
            df_jornadas.columns = [str(c).strip().upper() for c in df_jornadas.columns]
            df_jornadas['DATETIME'] = pd.to_datetime(df_jornadas['FECHA'] + ' ' + df_jornadas['HORA'], errors='coerce')
            
            # 2. Agrupamos por Fecha, Supervisor y Objetivo para hallar Inicio y Fin
            df_reporte = df_jornadas.groupby(['FECHA', 'SUPERVISOR', 'OBJETIVO']).agg(
                INGRESO=('HORA', 'first'),
                EGRESO=('HORA', 'last'),
                INICIO_DT=('DATETIME', 'first'),
                FIN_DT=('DATETIME', 'last')
            ).reset_index()

            # 3. Calculamos la duración real de la jornada en minutos
            df_reporte['DURACION_TOTAL'] = (df_reporte['FIN_DT'] - df_reporte['INICIO_DT']).dt.total_seconds() / 60
            df_reporte['DURACION_TOTAL'] = df_reporte['DURACION_TOTAL'].round(2)

            # 4. Mostramos el cuadro limpio
            st.dataframe(
                df_reporte[['FECHA', 'SUPERVISOR', 'OBJETIVO', 'INGRESO', 'EGRESO', 'DURACION_TOTAL']],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "DURACION_TOTAL": st.column_config.NumberColumn("DURACIÓN (MIN)", format="%d min")
                }
            )
        else:
            st.info("No hay registros de jornada disponibles.")

# --- NUEVA SECCIÓN DE AUDITORÍA DE PÁNICOS ---
        st.markdown("---")
        st.subheader("🚨 HISTÓRICO DE ALERTAS TÁCTICAS")
        df_alertas = leer_matriz_nube("ALERTAS")
        
        if not df_alertas.empty:
            df_alertas.columns = [str(c).strip().upper() for c in df_alertas.columns]
            
            # Filtramos para mostrar lo que pediste:
            # Seleccionamos solo las columnas relevantes para la Auditoría
            if {'FECHA', 'USUARIO', 'CARGA_UTIL', 'ESTADO'}.issubset(df_alertas.columns):
                df_historial = df_alertas[['FECHA', 'USUARIO', 'CARGA_UTIL', 'ESTADO']]
                
                # Mostramos la tabla
                st.dataframe(
                    df_historial, 
                    use_container_width=True, 
                    hide_index=True,
                    column_config={
                        "USUARIO": "EMISOR ALERTA",
                        "CARGA_UTIL": "DETALLE (VIG | OBJ | SUP)",
                        "ESTADO": st.column_config.TextColumn("RESOLUCIÓN")
                    }
                )
            else:
                st.warning("La hoja 'ALERTAS' no contiene las columnas necesarias.")
        else:
            st.info("No se registran eventos de pánico.")

# --- AUDITORÍA DE RELEVOS: REGLA ESTRICTA (MENOS CUARTO) ---
        st.markdown("---")
        st.subheader("🔄 AUDITORÍA DE RELEVOS (REGLA: MENOS CUARTO)")
        df_relevos = leer_matriz_nube("NOVEDADES_GUARDIA")
        
        if not df_relevos.empty:
            df_relevos.columns = [str(c).strip().upper() for c in df_relevos.columns]
            
            # Filtramos los relevos
            df_filtro = df_relevos[df_relevos['TIPO_NOVEDAD'] == "RELEVO DE TURNO"].copy()
            
            if not df_filtro.empty:
                # 1. Convertimos la FECHA a formato datetime
                df_filtro['DT'] = pd.to_datetime(df_filtro['FECHA'], errors='coerce')
                df_filtro['MINUTO'] = df_filtro['DT'].dt.minute
                
                # 2. Lógica de cumplimiento estricto
                # El relevo debe ser a los 45 minutos. 
                # Damos 1 minuto de margen (44 a 46). Si es menor a 44 o mayor a 46, está fuera de regla.
                df_filtro['CUMPLIMIENTO'] = df_filtro['MINUTO'].apply(
                    lambda x: "✅ EN HORARIO" if 44 <= x <= 46 else f"⚠️ FUERA DE REGLA (Min:{x})"
                )

                # 3. Mostramos tabla
                df_reporte = df_filtro[['FECHA', 'OBJETIVO', 'VIG_SALIENTE', 'VIG_ENTRANTE', 'LEGAJO', 'CUMPLIMIENTO']]
                
                st.dataframe(
                    df_reporte,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "CUMPLIMIENTO": st.column_config.TextColumn("ESTADO REGLA"),
                        "FECHA": "HORARIO REAL"
                    }
                )
            else:
                st.info("No hay registros de relevos actualmente.")
            
elif st.session_state.rol_sel == "GERENCIA":
    # 1. Calculamos el total de mensajes pendientes para GERENCIA
    df_msg = leer_matriz_nube("MENSAJERIA")
    nombre_user = st.session_state.user_sel.upper()
    
    total_nuevos = 0
    if not df_msg.empty:
        mask = ((df_msg['DESTINATARIO'] == "TODOS") | 
                (df_msg['DESTINATARIO'] == "GERENCIA") | 
                (df_msg['DESTINATARIO'] == nombre_user)) & \
               (df_msg['ESTADO'] == "PENDIENTE")
        total_nuevos = len(df_msg[mask])

    # 2. Creamos la etiqueta dinámica
    label_msg = f"💬 MENSAJERÍA GLOBAL ({total_nuevos})" if total_nuevos > 0 else "💬 MENSAJERÍA GLOBAL"

    st.markdown('<h2 style="color:#00E5FF; font-family:\'Orbitron\', sans-serif; font-size:24px; margin-bottom:5px;">Comando Estratégico: DIRECCIÓN GENERAL</h2>', unsafe_allow_html=True)
    
    # 3. Definición de pestañas con el label dinámico
    t_mensajeria_ger, t_ejecucion_ger, t_tab_auditoria = st.tabs([label_msg, "🎮 EJECUCIÓN", "📍 TABLERO DE AUDITORÍA"])
    
    # 4. Pestaña de Mensajería Global
    with t_mensajeria_ger:
        renderizar_mensajeria_global("GERENCIA")
    # 3. Pestaña de EJECUCIÓN (Restaurada)
    with t_ejecucion_ger:
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.markdown('<div class="panel-novedad">', unsafe_allow_html=True)
            st.subheader("ALTA DE RECURSO")
            g_alta_nom = st.text_input("Nombre:", key="ger_alta_nom")
            g_alta_asig = st.selectbox("Asignar a:", LISTA_SUPS_TACTICOS, key="ger_alta_asig")
            if st.button("Solicitar Alta"):
                escribir_registro_nube("PETICIONES", [obtener_hora_argentina(), st.session_state.user_sel, "ALTA", "OBJETIVO", f"{g_alta_nom} | ASIG: {g_alta_asig}"])
                st.success("✅ Petición enviada")
            st.markdown('</div>', unsafe_allow_html=True)
        with col_g2:
            st.markdown('<div class="panel-novedad">', unsafe_allow_html=True)
            st.subheader("BAJA DE OBJETIVO")
            opciones_baja = df_objetivos['OBJETIVO'].unique() if not df_objetivos.empty else ["ALFAVINIL"]
            g_baja_obj = st.selectbox("Objetivo:", opciones_baja, key="ger_baja_obj")
            if st.button("Solicitar Baja"):
                escribir_registro_nube("PETICIONES", [obtener_hora_argentina(), st.session_state.user_sel, "BAJA", "OBJETIVO", g_baja_obj])
                st.success("✅ Petición enviada")
            st.markdown('</div>', unsafe_allow_html=True)

    # 4. Pestaña de Tablero
    with t_tab_auditoria:
        df_ger_maps = df_objetivos.dropna(subset=['LATITUD', 'LONGITUD'])
        centro = [df_ger_maps['LATITUD'].mean(), df_ger_maps['LONGITUD'].mean()] if not df_ger_maps.empty else [-34.6, -58.4]
        m_visor = folium.Map(location=centro, zoom_start=12, tiles="CartoDB dark_matter")
        for _, r in df_ger_maps.iterrows():
            folium.Marker([r['LATITUD'], r['LONGITUD']], tooltip=r['OBJETIVO'], icon=folium.Icon(color="blue", icon="shield", prefix="fa")).add_to(m_visor)
        st_folium(m_visor, width="100%", height=450, key="map_gerencia")
   
elif st.session_state.rol_sel == "ADMINISTRADOR":
    u_ing = st.text_input("ADMIN_USER")
    p_ing = st.text_input("ADMIN_PASS", type="password")
    if u_ing == "admin" and p_ing == "aion2026": 
        st.success("Núcleo Maestro desbloqueado.")
