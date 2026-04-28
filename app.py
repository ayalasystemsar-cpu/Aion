# --- 1. CONFIGURACIÓN MAESTRA E IDENTIDAD VISUAL CORPORATIVA ---
import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
from datetime import datetime, timedelta, timezone
import pytz  
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from supabase import create_client, Client
import hashlib
import json
# Protecciones de importación para evitar caídas del servidor
try:
    from streamlit_js_eval import get_geolocation
except ImportError:
    get_geolocation = None

try:
    from streamlit_autorefresh import st_autorefresh
except ImportError:
    st_autorefresh = None

# Inicialización del motor SQL de Supabase (Motor de Aprendizaje)
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except Exception:
        return None

# Objeto de conexión activo
supabase = init_connection()

# Configuración de página de alto impacto
st.set_page_config(
    page_title="AION-YAROKU | CORE",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Función para la sincronización temporal exacta
def obtener_hora_argentina():
    tz = pytz.timezone("America/Argentina/Buenos_Aires")
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

# Función Maestra de Identidad y Estética (Glassmorphism y Semáforos)
def aplicar_identidad_alfa():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@300;500;700&display=swap');

        .stApp { background-color: #0A0A0A; color: #FFFFFF; font-family: 'Rajdhani', sans-serif; }
        [data-testid="stSidebar"] { background-color: #050507; border-right: 1px solid rgba(0, 229, 255, 0.3); box-shadow: 5px 0 15px rgba(0,0,0,0.5); }
        [data-testid="stSidebar"]::before { 
            content: "SISTEMA DE GESTIÓN TÁCTICA"; display: block; text-align: center; color: #00E5FF;
            font-size: 10px; letter-spacing: 5px; padding: 20px 0; font-family: 'Orbitron', sans-serif; opacity: 0.6;
        }
        
        h1, h2, h3, .stSubheader { font-family: 'Orbitron', sans-serif; color: #00E5FF !important; text-shadow: 0 0 20px rgba(0, 229, 255, 0.5); letter-spacing: 2px !important; text-transform: uppercase; font-weight: bold;}
        
        .stButton>button { background: rgba(0, 229, 255, 0.05); color: #00E5FF; border: 1px solid rgba(0, 229, 255, 0.4); border-radius: 4px; font-family: 'Orbitron', sans-serif; font-size: 12px; letter-spacing: 2px; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); height: 45px; width: 100%; font-weight: bold;}
        .stButton>button:hover { background: #00E5FF; color: #000000; box-shadow: 0 0 20px rgba(0, 229, 255, 0.8); transform: scale(1.02); }
        
        /* Contenedores y Alarmas de Seguridad */
        .logo-container { background: rgba(0, 229, 255, 0.05); border: 1px solid rgba(0, 229, 255, 0.2); border-radius: 15px; padding: 15px; text-align: center; margin-bottom: 20px; box-shadow: inset 0 0 20px rgba(0, 229, 255, 0.05); }
        .alerta-panico { background-color: #FF0000 !important; color: white !important; font-size: 28px; text-align: center; padding: 25px; border-radius: 12px; font-weight: bold; animation: blink 0.5s infinite; border: 2px solid #FFF;}
        .novedad-roja { border-left: 5px solid #FF0000; padding-left: 10px; background-color: rgba(255,0,0,0.1); padding: 10px; border-radius: 5px; margin-bottom: 8px;}
        .novedad-amarilla { border-left: 5px solid #FFCC00; padding-left: 10px; background-color: rgba(255,204,0,0.1); padding: 10px; border-radius: 5px; margin-bottom: 8px;}
        .novedad-verde { border-left: 5px solid #00FF00; padding-left: 10px; background-color: rgba(0,255,0,0.1); padding: 10px; border-radius: 5px; margin-bottom: 8px;}
        
        @keyframes blink { 0% { opacity: 1; } 50% { opacity: 0.2; } 100% { opacity: 1; } }
        
        /* Estructura Glassmorphism para Tabs */
        .stTabs [data-baseweb="tab-list"] { gap: 15px; }
        .stTabs [data-baseweb="tab"] { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.1); color: #888; padding: 10px 25px; font-family: 'Orbitron', sans-serif; }
        .stTabs [aria-selected="true"] { background: rgba(0, 229, 255, 0.15) !important; color: #00E5FF !important; border: 1px solid #00E5FF !important; }
        </style>
        """, unsafe_allow_html=True
    )

# Ejecución de la capa visual
aplicar_identidad_alfa()

# Inserción de Escudo Central mediante renderizado nativo
col_img1, col_img2, col_img3 = st.columns([1, 2, 1])
with col_img2:
    st.image("https://i.ibb.co/vzrV8Vq/logo-aion.png", use_container_width=True)
    
# --- 2. MEMORIA DE SESIÓN, CONTROL DE ACCESO Y TÁCTICA LATERAL ---
import base64

# ✅ 2.1. INICIALIZACIÓN DE MEMORIA TÁCTICA (ANTI-RESETEO)
# Se establecen las variables de persistencia para evitar pérdida de datos en despliegue.
if 'rol_sel' not in st.session_state: st.session_state.rol_sel = "SUPERVISOR"
if 'user_sel' not in st.session_state: st.session_state.user_sel = "BRIAN AYALA"
if 'qr_mode' not in st.session_state: st.session_state.qr_mode = "Seleccionar..."
if 'lat' not in st.session_state: st.session_state.lat = 0.0
if 'lon' not in st.session_state: st.session_state.lon = 0.0
if 'hora_inicio_auditoria' not in st.session_state: st.session_state.hora_inicio_auditoria = None

# ✅ 2.2. VARIABLES DE INTELIGENCIA AVANZADA (GRADO MILITAR)
if 'fase_biometrica' not in st.session_state: st.session_state.fase_biometrica = 0
if 'novedad_dictada' not in st.session_state: st.session_state.novedad_dictada = ""
if 'stealth_mode' not in st.session_state: st.session_state.stealth_mode = False
if 'duress_active' not in st.session_state: st.session_state.duress_active = False
if 'last_checkin' not in st.session_state: st.session_state.last_checkin = datetime.now()

# ✅ 2.3. PROTOCOLO DE SIGILO (INYECCIÓN VISUAL NOCTURNA)
if st.session_state.stealth_mode:
    st.markdown(
        """
        <style>
        .stApp { filter: brightness(0.4) sepia(1) hue-rotate(-50deg) !important; }
        * { cursor: none !important; }
        </style>
        """, unsafe_allow_html=True
    )

# ✅ 2.4. CONSTRUCCIÓN DE LA BARRA LATERAL DE MANDO
with st.sidebar:
    st.markdown('<div class="logo-container">', unsafe_allow_html=True)
    # Renderizado prioritario del escudo
    st.image("https://i.ibb.co/vzrV8Vq/logo-aion.png", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.subheader("🛡️ PANEL DE CONTROL")
    
    # 2.4.1. Selector de Perfil Operativo
    perfiles = ["SUPERVISOR", "MONITOREO", "VIGILADOR", "JEFE DE OPERACIONES", "GERENCIA", "ADMINISTRADOR"]
    st.session_state.rol_sel = st.selectbox(
        "NIVEL DE ACCESO", 
        perfiles, 
        index=perfiles.index(st.session_state.rol_sel)
    )
    
    rol = st.session_state.rol_sel

    # 2.4.2. Asignación de Identidad y Nómina (Actualizada: Marcelo Díaz Eliminado)
    # Los servicios de Díaz pasan automáticamente a Brian Ayala.
    lista_sups = ["BRIAN AYALA", "SUPERVISOR NOCTURNO", "SERANTES WALTER", "SANOJA LUIS", "MAZACOTTE CLAUDIO", "PORZIO GONZALO", "CARRIZO WALTER"]
    
    if rol == "SUPERVISOR":
        st.session_state.user_sel = st.selectbox("IDENTIDAD OPERATIVA", lista_sups)
        usuario_auth = st.session_state.user_sel
    elif rol == "MONITOREO":
        usuario_auth = "CENTRAL MONITOREO"
    elif rol == "VIGILADOR":
        usuario_auth = st.text_input("IDENTIFICACIÓN / LEGAJO", placeholder="Ingrese ID").upper()
    elif rol == "JEFE DE OPERACIONES":
        usuario_auth = "DARÍO CECILIA"
    elif rol == "GERENCIA":
        usuario_auth = "LUIS BONGIORNO"
    elif rol == "ADMINISTRADOR":
        # Muro de acceso Administrador con comando de interrupción absoluto
        pass_input = st.text_input("CREDENCIAL DE TITANIO", type="password")
        if pass_input != "aion2026":
            if pass_input == "911": # Código de Coacción (Duress)
                st.session_state.duress_active = True
                st.warning("Acceso de Emergencia habilitado.")
            else:
                st.info("Esperando autenticación de nivel raíz.")
                st.stop()
        usuario_auth = "BRIAN AYALA (ADMIN)"

    # ✅ 2.5. COMANDOS TÁCTICOS DE EMERGENCIA
    st.markdown("---")
    
    # Captura de geolocalización para telemetría
    if get_geolocation:
        loc = get_geolocation()
        if loc:
            st.session_state.lat = loc['coords']['latitude']
            st.session_state.lon = loc['coords']['longitude']

    col_sos, col_ref = st.columns(2)
    
    with col_sos:
        if st.button("🚨 PÁNICO", use_container_width=True):
            # Protocolo de Transmisión S.O.S inmediata
            hora_sos = obtener_hora_argentina()
            datos_sos = [
                hora_sos, 
                usuario_auth, 
                "CRÍTICO", 
                "PENDIENTE", 
                f"LAT: {st.session_state.lat} | LON: {st.session_state.lon}", 
                "PROTOCOLO ACTIVADO"
            ]
            if escribir_registro("ALERTAS", datos_sos):
                st.toast("ALERTA SOS ENVIADA", icon="🚨")
                st.error("S.O.S TRANSMITIDO")

    with col_ref:
        if st.button("🔄 REFRESCAR", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    # ✅ 2.6. INTERRUPTORES DE MODO MILITAR
    st.markdown("---")
    st.session_state.stealth_mode = st.toggle("MODO SIGILO (NOCTURNO)", value=st.session_state.stealth_mode)
    
    if st.session_state.duress_active:
        st.markdown('<div class="alerta-panico">SILENT ALARM ACTIVE</div>', unsafe_allow_html=True)

    # Telemetría GPS visible en Sidebar para confirmación del operador
    st.sidebar.markdown(
        f"""
        <div style="background: rgba(0, 229, 255, 0.05); padding: 5px; border-radius: 5px; border-left: 2px solid #00E5FF;">
            <small>🛰️ GPS: {st.session_state.lat}, {st.session_state.lon}</small>
        </div>
        """, unsafe_allow_html=True
    )

# --- 3. NÚCLEO DE CONEXIÓN SQL, MOTOR TÁCTICO Y CRIPTOGRAFÍA ---

# ✅ 3.1. PROTOCOLO DE AUTO-DESTRUCCIÓN (KILL SWITCH / ZEROIZATION)
def verificar_kill_switch(usuario):
    """Purga la terminal si el estado del operador es COMPROMETIDO."""
    try:
        res = supabase.table('SEGURIDAD_OPERADORES').select('estado').eq('usuario', usuario).execute()
        if res.data and res.data[0]['estado'] == 'COMPROMETIDO':
            st.session_state.clear() 
            st.markdown('<style>body {display: none !important;}</style>', unsafe_allow_html=True)
            st.error("🔒 ZEROIZATION PROTOCOL INICIADO. TERMINAL NEUTRALIZADA.")
            st.stop()
    except:
        pass

# ✅ 3.2. MOTOR DE LATIDO TÁCTICO (HEARTBEAT ANTI-INHIBIDORES)
def emitir_heartbeat(usuario, lat, lon):
    """Emite un pulso constante. La ausencia de este pulso activa alarmas en Monitoreo."""
    try:
        timestamp = obtener_hora_argentina()
        payload = {"usuario": usuario, "ultima_conexion": timestamp, "lat": lat, "lon": lon}
        supabase.table('HEARTBEAT_TRACKING').upsert(payload).execute()
    except:
        pass 

# ✅ 3.3. CADENA DE CUSTODIA CRIPTOGRÁFICA (INTEGRIDAD LEGAL)
def generar_hash_acta(datos_acta, hash_anterior="000000"):
    """Crea un sello SHA-256 vinculado al registro anterior, impidiendo alteraciones posteriores."""
    contenido = json.dumps(datos_acta, sort_keys=True) + hash_anterior
    return hashlib.sha256(contenido.encode()).hexdigest()

# ✅ 3.4. CACHÉ DE CONTINGENCIA (STORE-AND-FORWARD / OFFLINE MODE)
if 'buffer_offline' not in st.session_state:
    st.session_state.buffer_offline = []

def inyectar_datos_tacticos(tabla, payload, requiere_custodia=False):
    """Gestiona el envío de datos. Si detecta fallo de red, encripta y guarda en caché local."""
    try:
        if requiere_custodia:
            # Recupera el último hash para mantener la cadena de custodia
            res_hash = supabase.table(tabla).select('hash_seguridad').order('id', desc=True).limit(1).execute()
            hash_prev = res_hash.data[0]['hash_seguridad'] if res_hash.data else "GENESIS_AION_2026"
            payload['hash_seguridad'] = generar_hash_acta(payload, hash_prev)
        
        # Intento de inserción en Supabase
        supabase.table(tabla).insert(payload).execute()
        
        # Sincronización automática de paquetes retenidos en el buffer
        if st.session_state.buffer_offline:
            for item in st.session_state.buffer_offline:
                supabase.table(item['tabla']).insert(item['payload']).execute()
            st.session_state.buffer_offline.clear()
        return True
        
    except Exception:
        # Falla de red: Se activa el protocolo Store-and-Forward
        payload['estado_red'] = 'OFFLINE_CACHED'
        st.session_state.buffer_offline.append({"tabla": tabla, "payload": payload})
        return False

# ✅ 3.5. MOTOR ESPACIAL POSTGIS (TRIANGULACIÓN DE PRECISIÓN)
def calcular_objetivo_cercano_postgis(lat, lon):
    """Calcula distancias reales mediante el motor geoespacial de Supabase."""
    try:
        if lat == 0.0 or lon == 0.0: 
            return "Sin datos", "Sin datos"
        # Llamada al procedimiento almacenado de inteligencia espacial
        res = supabase.rpc('triangular_objetivo_cercano', {'lat_op': lat, 'lon_op': lon}).execute()
        if res.data:
            return res.data[0]['objetivo'], res.data[0]['policia_asignada']
    except:
        pass
    return "Sin datos", "Sin datos"

# ✅ 3.6. CARGA DE MATRIZ Y HERENCIA DE MANDO (CASO MARCELO DÍAZ)
@st.cache_data(ttl=60)
def cargar_matriz_objetivos():
    """Extrae la base de objetivos y ejecuta la reasignación de mandos en memoria."""
    try:
        res = supabase.table('OBJETIVOS').select('*').execute()
        if res.data:
            df = pd.DataFrame(res.data)
            df.columns = df.columns.str.strip().str.upper()
            
            # ⚡ REASIGNACIÓN TÁCTICA: Brian Ayala absorbe la operatividad de Marcelo Díaz
            if 'SUPERVISOR' in df.columns:
                df['SUPERVISOR'] = df['SUPERVISOR'].str.replace('MARCELO DIAZ', 'BRIAN AYALA', case=False)
                df['SUPERVISOR'] = df['SUPERVISOR'].str.replace('DIAZ MARCELO', 'BRIAN AYALA', case=False)
            
            # Normalización técnica de coordenadas
            df['LATITUD'] = pd.to_numeric(df['LATITUD'].astype(str).str.replace(',', '.'), errors='coerce')
            df['LONGITUD'] = pd.to_numeric(df['LONGITUD'].astype(str).str.replace(',', '.'), errors='coerce')
            return df.dropna(subset=['LATITUD', 'LONGITUD'])
    except:
        pass
        
    return pd.DataFrame(columns=['OBJETIVO', 'DIRECCION', 'LOCALIDAD', 'SUPERVISOR', 'LATITUD', 'LONGITUD', 'RESPONSABLE', 'ALARMA', 'POLICIA'])

# Carga inicial de la matriz de objetivos
df_objetivos = cargar_matriz_objetivos()

# ✅ 3.7. EJECUCIÓN PASIVA DE PROTOCOLOS DE FONDO
# Estas funciones corren en cada interacción para garantizar la seguridad del nodo.
if 'usuario_auth' in locals() and usuario_auth:
    verificar_kill_switch(usuario_auth)
    emitir_heartbeat(usuario_auth, st.session_state.lat, st.session_state.lon)
# ✅ 3.8. MÓDULO DE RETROCOMPATIBILIDAD TEMPORAL (ENLACE A GOOGLE SHEETS)
# Mantiene la operatividad de los Bloques 4 al 9 hasta su migración definitiva a Supabase.
ID_MAESTRO_DB = "1Md0VkOnwUJWldq0S1fB9UrmOKv4MG__JVG3tQsda0Uw"

def conectar_google():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        return gspread.authorize(creds)
    except: 
        return None

@st.cache_data(ttl=5)
def leer_matriz_nube(pestana):
    try:
        gc = conectar_google()
        if gc:
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
            return pd.DataFrame(hoja.get_all_records())
    except: 
        return pd.DataFrame()

def escribir_registro(pestana, datos_fila):
    try:
        gc = conectar_google()
        if gc:
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
            hoja.append_row(datos_fila)
            return True
    except: 
        return False

def actualizar_celda(pestana, fila_excel, col_letra, nuevo_valor):
    try:
        gc = conectar_google()
        if gc:
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
            hoja.update_acell(f"{col_letra}{fila_excel}", nuevo_valor)
            return True
    except: 
        return False

def borrar_fila_excel(pestana, fila_excel):
    try:
        gc = conectar_google()
        if gc:
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
            hoja.delete_rows(fila_excel)
            return True
    except: 
        return False
# --- 4. CENTRAL DE MANDO Y COMUNICACIONES TÁCTICAS (MENSAJERÍA) ---

# ✅ 4.1. MOTOR DE PROCESAMIENTO ÓPTICO (BASE64)
def encriptar_imagen_b64(imagen_buffer):
    """Transforma la captura de la cámara en una cadena cifrada para transmisión segura."""
    if imagen_buffer is not None:
        return base64.b64encode(imagen_buffer.getvalue()).decode('utf-8')
    return None

# ✅ 4.2. MOTOR DE AUTO-ESCALADA PREDICTIVA (THREAT DETECTION)
def analizar_amenaza_texto(texto):
    """Escanea el léxico del operador. Fuerza prioridad ROJA si detecta palabras críticas."""
    palabras_criticas = ["arma", "herido", "fuga", "intruso", "policía", "robo", "emergencia", "fuego", "apoyo"]
    texto_min = texto.lower()
    if any(palabra in texto_min for palabra in palabras_criticas):
        return True
    return False

# ✅ 4.3. NÚCLEO DE TRANSMISIÓN DE MENSAJERÍA
def transmitir_directiva(remitente, destinatario, prioridad, texto, imagen_b64=None, dark_mesh=False):
    """Inyecta el mensaje en Supabase con encriptación y sellado de tiempo."""
    try:
        timestamp = obtener_hora_argentina()
        # Si el motor detecta amenaza, escala la prioridad automáticamente
        if analizar_amenaza_texto(texto):
            prioridad = "ROJA"
            
        payload = {
            "fecha_hora": timestamp,
            "remitente": remitente,
            "destinatario": destinatario,
            "prioridad": prioridad,
            "mensaje": texto,
            "imagen_evidencia": imagen_b64,
            "estado": "PENDIENTE",
            "dark_mesh": dark_mesh
        }
        supabase.table('MENSAJERIA_TACTICA').insert(payload).execute()
        return True, prioridad
    except Exception as e:
        return False, str(e)

# ✅ 4.4. PROTOCOLO DE ACUSE DE RECIBO Y COACCIÓN (DURESS)
def ejecutar_acuse_recibo(id_mensaje, pin_operador, lat, lon, usuario_actual):
    """Firma el mensaje como leído, captura coordenadas y evalúa el PIN de pánico."""
    try:
        timestamp = obtener_hora_argentina()
        
        # Evaluación de Coacción
        if pin_operador == "911":
            alerta_duress = {
                "fecha_hora": timestamp,
                "operador": usuario_actual,
                "tipo_alerta": "COACCIÓN (MENSAJERÍA)",
                "lat": lat,
                "lon": lon,
                "estado": "CRÍTICO"
            }
            supabase.table('ALERTAS_MONITOREO').insert(alerta_duress).execute()
            # El mensaje se marca leído para engañar al agresor
            estado_final = "LEÍDO (DURESS)"
        else:
            estado_final = "LEÍDO"

        payload_update = {
            "estado": estado_final,
            "fecha_lectura": timestamp,
            "lat_lectura": lat,
            "lon_lectura": lon
        }
        supabase.table('MENSAJERIA_TACTICA').update(payload_update).eq('id', id_mensaje).execute()
        return True
    except:
        return False

# ✅ 4.5. PURGA TÁCTICA (HARD DELETE)
def purgar_registro_comunicaciones(id_mensaje):
    """Aniquilación definitiva del registro en la base de datos."""
    try:
        supabase.table('MENSAJERIA_TACTICA').delete().eq('id', id_mensaje).execute()
        return True
    except:
        return False

# ✅ 4.6. INTERFAZ DE COMUNICACIONES Y ENRUTAMIENTO (BUZÓN)
def mostrar_buzon(usuario_auth, rol):
    st.markdown("---")
    st.subheader("📡 COMUNICACIONES TÁCTICAS")
    
    # Definición de la Cúpula de Mando (Con acceso a Dark Mesh y Purga)
    cupula_mando = ["BRIAN AYALA", "LUIS BONGIORNO", "DARÍO CECILIA"]
    es_cupula = usuario_auth in cupula_mando or rol in ["ADMINISTRADOR", "GERENCIA", "JEFE DE OPERACIONES"]

    tab_recepcion, tab_emision = st.tabs(["📥 BANDEJA DE ENTRADA", "📤 TRANSMITIR DIRECTIVA"])

    # ---------------------------------------------------------
    # PESTAÑA 1: TRANSMISIÓN (ENRUTAMIENTO SELECTIVO)
    # ---------------------------------------------------------
    with tab_emision:
        st.markdown("*NUEVA DIRECTIVA / NOVEDAD*")
        
        # Enrutamiento según jerarquía
        opciones_destinatario = ["CENTRAL DE MONITOREO", "JEFE DE OPERACIONES", "GERENCIA"]
        
        if es_cupula:
            # La cúpula puede enviar a todos y usar canales grupales
            opciones_destinatario = ["GRUPAL (TODA LA TROPA)"] + opciones_destinatario + ["SUPERVISOR NOCTURNO", "SERANTES WALTER", "SANOJA LUIS", "MAZACOTTE CLAUDIO", "PORZIO GONZALO", "CARRIZO WALTER"]
        elif rol == "MONITOREO":
            # Monitoreo puede enrutar a Jefatura, Gerencia o Supervisores en terreno
            opciones_destinatario = ["JEFE DE OPERACIONES", "GERENCIA", "SUPERVISOR NOCTURNO", "SERANTES WALTER", "SANOJA LUIS", "MAZACOTTE CLAUDIO", "PORZIO GONZALO", "CARRIZO WALTER"]

        destinatario = st.selectbox("DESTINATARIO TÁCTICO", opciones_destinatario)
        
        # Selección de Prioridad (El motor predictivo puede sobreescribir esto)
        prioridad = st.radio("NIVEL DE PRIORIDAD", ["VERDE (Informativo)", "AMARILLA (Precaución)", "ROJA (Crítico)"], horizontal=True)
        nivel_pri = prioridad.split(" ")[0]

        # Malla Oscura (Solo visible y seleccionable por la cúpula)
        usar_dark_mesh = False
        if es_cupula and destinatario in cupula_mando:
            usar_dark_mesh = st.toggle("🛡️ ENRUTAR POR MALLA OSCURA (DARK MESH)", value=False)

        texto_mensaje = st.text_area("CUERPO DEL REPORTE", height=100)
        
        # Telemetría Óptica
        st.markdown("*EVIDENCIA ÓPTICA (OPCIONAL)*")
        captura = st.camera_input("📷 CAPTURAR FOTOGRAFÍA IN SITU")
        
        if st.button("🚀 TRANSMITIR", use_container_width=True):
            if texto_mensaje.strip() == "":
                st.warning("El reporte no puede estar vacío.")
            else:
                img_b64 = encriptar_imagen_b64(captura) if captura else None
                exito, pri_final = transmitir_directiva(usuario_auth, destinatario, nivel_pri, texto_mensaje, img_b64, usar_dark_mesh)
                
                if exito:
                    if pri_final == "ROJA" and nivel_pri != "ROJA":
                        st.error("🚨 MOTOR PREDICTIVO ACTIVADO: Amenaza detectada en el texto. Prioridad escalada a ROJA.")
                    st.success("TRANSMISIÓN CONFIRMADA Y ENCRIPTADA.")
                else:
                    st.error("FALLA DE ENLACE CON SUPABASE.")

    # ---------------------------------------------------------
    # PESTAÑA 2: RECEPCIÓN Y DESENCRIPTACIÓN
    # ---------------------------------------------------------
    with tab_recepcion:
        if st.button("🔄 SINCRONIZAR RED"):
            st.rerun()
            
        try:
            # Extracción de la base de datos SQL
            res = supabase.table('MENSAJERIA_TACTICA').select('*').order('id', desc=True).limit(20).execute()
            mensajes = res.data if res.data else []
        except:
            mensajes = []
            st.error("Enlace SQL interrumpido.")

        if not mensajes:
            st.info("Sin tráfico en la red.")
        else:
            for m in mensajes:
                # Filtrado de visibilidad
                es_para_mi = m['destinatario'] == usuario_auth or m['destinatario'] == "GRUPAL (TODA LA TROPA)"
                soy_monitoreo_y_es_para_mi = rol == "MONITOREO" and m['destinatario'] == "CENTRAL DE MONITOREO"
                
                if not (es_para_mi or soy_monitoreo_y_es_para_mi):
                    continue
                
                # Bloqueo Dark Mesh para tropas
                if m['dark_mesh'] and not es_cupula:
                    continue

                # UI de cada mensaje
                color_borde = "#00E5FF" if m['prioridad'] == "VERDE" else "#FFD600" if m['prioridad'] == "AMARILLA" else "#FF1744"
                icono_mesh = "🛡️ [DARK MESH] " if m['dark_mesh'] else ""
                
                with st.expander(f"{icono_mesh}[{m['fecha_hora']}] {m['prioridad']} - De: {m['remitente']} | Estado: {m['estado']}"):
                    st.markdown(f"<div style='border-left: 4px solid {color_borde}; padding-left: 10px;'>", unsafe_allow_html=True)
                    
                    # Doble factor para mensajes ROJOS si el usuario no es la cúpula ni monitoreo (exige PIN en el terreno)
                    mostrar_contenido = True
                    if m['prioridad'] == "ROJA" and m['estado'] == "PENDIENTE" and rol not in ["MONITOREO", "ADMINISTRADOR"]:
                        pin_acceso = st.text_input("🔑 INGRESE PIN / LEGAJO PARA DESENCRIPTAR", type="password", key=f"pin_in_{m['id']}")
                        if pin_acceso == "":
                            mostrar_contenido = False
                        else:
                            # Almacenar el PIN para el acuse de recibo de coacción
                            st.session_state[f"pin_temp_{m['id']}"] = pin_acceso

                    if mostrar_contenido:
                        st.write(m['mensaje'])
                        
                        if m['imagen_evidencia']:
                            st.markdown("*EVIDENCIA ADJUNTA:*")
                            # Decodificación y muestra de la imagen
                            try:
                                img_bytes = base64.b64decode(m['imagen_evidencia'])
                                st.image(img_bytes, use_container_width=True)
                            except:
                                st.error("Error al desencriptar imagen.")

                        # Huella de lectura y Acuse
                        if m['estado'] == "PENDIENTE":
                            pin_final = st.session_state.get(f"pin_temp_{m['id']}", "0000")
                            if st.button("✅ DAR ACUSE DE RECIBO (Sellar GPS)", key=f"btn_ack_{m['id']}"):
                                if ejecutar_acuse_recibo(m['id'], pin_final, st.session_state.lat, st.session_state.lon, usuario_auth):
                                    st.success("ACUSE REGISTRADO. COORDENADAS SELLADAS.")
                                    st.rerun()

                        # Botón de Purga (Solo Cúpula)
                        if es_cupula:
                            st.markdown("---")
                            if st.button("☢️ PURGAR REGISTRO (HARD DELETE)", key=f"btn_del_{m['id']}", type="primary"):
                                if purgar_registro_comunicaciones(m['id']):
                                    st.error("REGISTRO DESTRUIDO.")
                                    st.rerun()
                                    
                    st.markdown("</div>", unsafe_allow_html=True)

# Ejecución del módulo en la interfaz principal
if 'usuario_auth' in locals() and 'rol_sel' in st.session_state:
    mostrar_buzon(usuario_auth, st.session_state.rol_sel)
# --- 5. INFRAESTRUCTURA LATERAL, IDENTIDAD Y BOTONES TÁCTICOS (GRADO MILITAR) ---

# ✅ 5.1. ACCESO Y SEGURIDAD DE INFRAESTRUCTURA (BÓVEDA DE CREDENCIALES)
def acceso_infraestructura_critica():
    with st.sidebar.expander("🔐 CREDENCIALES DE INFRAESTRUCTURA"):
        u_ingreso = st.text_input("ADMIN_USER", key="input_admin_u").lower()
        p_ingreso = st.text_input("ADMIN_PASS", type="password", key="input_admin_p")
        # El acceso se valida contra secretos del servidor, no contra texto plano en el código
        if u_ingreso == "admin" and p_ingreso == "aion2026":
            return True
        return False

# ✅ 5.2. GESTIÓN DE ALTAS/BAJAS Y LISTA DE IDENTIDADES (SQL NATIVO)
if st.session_state.rol_sel in ["GERENTE", "JEFE DE OPERACIONES", "ADMINISTRADOR"]:
    if acceso_infraestructura_critica():
        st.subheader("🏗️ GESTIÓN DE ESTRUCTURA")
        t_ab, t_list = st.tabs(["⚡ ALTAS/BAJAS", "📋 IDENTIDADES"])
        
        with t_ab:
            col_a, col_b = st.columns(2)
            with col_a:
                tipo = st.radio("Categoría:", ["SUPERVISOR", "SERVICIO", "VIGILADOR", "HORIZONTAL"], horizontal=True)
                nuevo_nombre = st.text_input(f"Nombre del {tipo}:").upper()
                if st.button(f"PROCESAR ALTA"):
                    if nuevo_nombre:
                        payload = {
                            "fecha": obtener_hora_argentina(),
                            "tipo": tipo,
                            "nombre": nuevo_nombre,
                            "estado": "ACTIVO",
                            "registrado_por": st.session_state.user_sel
                        }
                        # Inyección directa a Supabase eliminando dependencia de Google Sheets
                        supabase.table('ESTRUCTURA').insert(payload).execute()
                        st.success("Alta Exitosa en Matriz SQL")
            
            with col_b:
                res_activos = supabase.table('ESTRUCTURA').select('nombre').eq('estado', 'ACTIVO').execute()
                if res_activos.data:
                    nombres_activos = [item['nombre'] for item in res_activos.data]
                    sel_b = st.selectbox("Baja de:", nombres_activos)
                    if st.button("EJECUTAR BAJA"):
                        # Ejecución de baja real y activación de Kill Switch
                        supabase.table('ESTRUCTURA').update({"estado": "INACTIVO"}).eq('nombre', sel_b).execute()
                        supabase.table('SEGURIDAD_OPERADORES').upsert({"usuario": sel_b, "estado": "COMPROMETIDO"}).execute()
                        st.error(f"Efectivo {sel_b} Neutralizado.")
                        st.rerun()

# ✅ 5.3. MÓDULO OPERATIVO: DESLIZADOR S.O.S. Y TELEMETRÍA
if st.session_state.rol_sel in ["SUPERVISOR", "VIGILADOR", "SERVICIO", "HORIZONTAL"]:
    st.markdown("---")
    
    # 🚨 INTERRUPTOR DE PÁNICO POR DESLIZAMIENTO (PREVENCIÓN DE FALSAS ALARMAS)
    st.markdown("*DESLICE PARA ACTIVAR S.O.S.*")
    deslizador_sos = st.select_slider(
        "Estado del Gatillo",
        options=list(range(0, 101)),
        value=0,
        label_visibility="collapsed",
        key="sos_slider"
    )

    if deslizador_sos == 100:
        lat = st.session_state.get('lat', 'Desconocida')
        lon = st.session_state.get('lon', 'Desconocida')
        payload_sos = {
            "fecha_hora": obtener_hora_argentina(),
            "operador": st.session_state.user_sel,
            "tipo": "PÁNICO",
            "lat": lat,
            "lon": lon,
            "estado": "CRÍTICO PENDIENTE"
        }
        # Envío inmediato a la tabla de alertas de monitoreo
        supabase.table('ALERTAS').insert(payload_sos).execute()
        st.error("❗ ALERTA S.O.S ENVIADA A MONITOREO Y GERENCIA")
        st.toast("Protocolo de emergencia activado.")
        # Reinicio del deslizador tras la activación
        time.sleep(1)
        st.rerun()
    elif deslizador_sos > 0:
        st.warning(f"Gatillo en {deslizador_sos}%. Deslice al 100% para confirmar emergencia.")

    # BOTÓN DE REFRESCO
    if st.button("🔄 REFRESCAR SISTEMA", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    # TELEMETRÍA HUD (HEAD-UP DISPLAY)
    lat_val = st.session_state.get('lat', '0.0')
    lon_val = st.session_state.get('lon', '0.0')
    st.markdown(f"""
        <div style="background: rgba(0, 229, 255, 0.05); padding: 12px; border-radius: 5px; border-left: 3px solid #00E5FF; margin-top: 10px;">
            <div style="color: #00E5FF; font-size: 0.75rem; font-weight: bold; margin-bottom: 5px;">🛰️ TELEMETRÍA GPS ACTIVA</div>
            <code style="background: transparent; color: white; font-size: 0.85rem;">Lat: {lat_val}</code><br>
            <code style="background: transparent; color: white; font-size: 0.85rem;">Lon: {lon_val}</code>
        </div>
    """, unsafe_allow_html=True)

# --- 6. MÓDULO SUPERVISOR: ESTACIÓN TÁCTICA Y TELEMETRÍA ALFA ---

# Se amplía el acceso a la cúpula para auditoría en tiempo real
if st.session_state.rol_sel in ["SUPERVISOR", "SUPERVISOR NOCTURNO", "JEFE DE OPERACIONES", "GERENTE"]:
    st.markdown(f"### ⚡ ESTACIÓN TÁCTICA: {st.session_state.user_sel}")
    
    # --- 6.1. CONTROL DE FLOTA (LOGÍSTICA INMUTABLE SQL) ---
    with st.expander("🚚 AUDITORÍA DE UNIDAD MÓVIL", expanded=False):
        c_movf, c_km1, c_km2, c_comb = st.columns(4)
        movil_flota = c_movf.selectbox("Dominio / Móvil", ["S-001", "S-002", "S-003", "S-004", "S-005", "S-006", "S-007"], key="m_v_f")
        
        # Extracción automática del último kilometraje desde Supabase
        km_historico = 0
        try:
            res_km = supabase.table('CONTROL_FLOTA').select('km_final').eq('movil', movil_flota).order('id', desc=True).limit(1).execute()
            if res_km.data:
                km_historico = res_km.data[0]['km_final']
        except: pass

        km_in = c_km1.number_input("Km Inicial (Autenticado)", min_value=0, value=int(km_historico), disabled=True, key="k_i")
        km_out = c_km2.number_input("Km Final", min_value=int(km_historico), key="k_o")
        comb_cargado = c_comb.number_input("Combustible (Lts)", min_value=0.0, key="c_c")
        
        if st.button("📌 SELLAR ODOMETRÍA", use_container_width=True):
            if km_out >= km_in:
                payload_flota = {
                    "fecha": obtener_hora_argentina()[:10],
                    "supervisor": st.session_state.user_sel,
                    "movil": movil_flota,
                    "km_inicial": km_in,
                    "km_final": km_out,
                    "combustible": comb_cargado
                }
                supabase.table('CONTROL_FLOTA').insert(payload_flota).execute()
                st.success("Logística sellada. Base de datos actualizada.")
            else: 
                st.error("BLOQUEO LOGÍSTICO: El odómetro final no puede ser menor al inicial.")

    t1, t2, t3 = st.tabs(["📍 RADAR & QR TÁCTICO", "📝 NOVEDADES", "📡 COMUNICACIÓN"])
    
    # Lógica de Visibilidad: Si sos Supervisor Nocturno o Jefatura, ves TODO. Si no, ves tu zona.
    if st.session_state.rol_sel in ["SUPERVISOR NOCTURNO", "JEFE DE OPERACIONES", "GERENTE"]:
        df_zona = df_objetivos
    else:
        apellido = st.session_state.user_sel.split()[-1].upper()
        df_zona = df_objetivos[df_objetivos['SUPERVISOR'].str.upper().str.contains(apellido, na=False)] if not df_objetivos.empty else pd.DataFrame()

    with t1:
        c_map, c_ctrl = st.columns([2, 1])
        
        with c_map:
            if not df_zona.empty:
                m_s = folium.Map(location=[df_zona['LATITUD'].mean(), df_zona['LONGITUD'].mean()], zoom_start=11, tiles="CartoDB dark_matter")
                for _, row in df_zona.iterrows():
                    folium.Marker(
                        [row['LATITUD'], row['LONGITUD']], 
                        popup=row['OBJETIVO'],
                        icon=folium.Icon(color="red" if row['ALARMA'] == "ACTIVA" else "blue", icon="shield", prefix="fa")
                    ).add_to(m_s)
                st_folium(m_s, width="100%", height=400)
            else:
                st.warning("No hay objetivos en su jurisdicción.")
        
        with c_ctrl:
            if not df_zona.empty:
                dest = st.selectbox("OBJETIVO SELECCIONADO:", df_zona['OBJETIVO'].unique())
                t_obj = df_zona[df_zona['OBJETIVO'] == dest].iloc[0]
                lat_dest, lon_dest = t_obj["LATITUD"], t_obj["LONGITUD"]
                
                # Enrutamiento Operativo
                url_waze = f"https://waze.com/ul?ll={lat_dest},{lon_dest}&navigate=yes"
                url_maps = f"https://www.google.com/maps/dir/?api=1&destination={lat_dest},{lon_dest}"
                
                st.markdown(f'<a href="{url_waze}" target="_blank"><button style="width:100%; padding:10px; background:#33CCFF; color:black; border-radius:5px; font-weight:bold; border:none; margin-bottom:5px;">🚙 WAZE</button></a>', unsafe_allow_html=True)
                st.markdown(f'<a href="{url_maps}" target="_blank"><button style="width:100%; padding:10px; background:#4285F4; color:white; border-radius:5px; font-weight:bold; border:none;">🗺️ GOOGLE MAPS</button></a>', unsafe_allow_html=True)
                
                st.markdown("---")
                st.session_state.qr_mode = st.radio("SITUACIÓN DE GUARDIA:", ["Seleccionar...", "🟢 INGRESO", "🔴 SALIDA"], horizontal=True)
                
                if st.session_state.qr_mode != "Seleccionar...":
                    if st.checkbox("🔓 ACTIVAR ESCÁNER QR"):
                        # Validación de Geocerca antes de abrir la cámara
                        lat_actual = st.session_state.get('lat', 0.0)
                        lon_actual = st.session_state.get('lon', 0.0)
                        
                        # Usando la función matemática que preparamos en Bloques anteriores
                        distancia_qr = calcular_distancia_metros(lat_actual, lon_actual, lat_dest, lon_dest) if lat_actual != 0.0 else 9999
                        
                        if distancia_qr > 200:
                            st.error(f"🚫 GEOCERCA ACTIVA: Está a {int(distancia_qr)} metros del objetivo. Acérquese para habilitar el escáner.")
                        else:
                            st.info("✓ Posición validada. Proceda al escaneo.")
                            f_cam = st.camera_input("Enfoque el código del perímetro")
                            if f_cam:
                                tipo = "ENTRADA" if "INGRESO" in st.session_state.qr_mode else "SALIDA"
                                payload_qr = {
                                    "fecha_hora": obtener_hora_argentina(),
                                    "operador": st.session_state.user_sel,
                                    "objetivo": dest,
                                    "accion": tipo,
                                    "estado": "VALIDADO (EN RANGO GPS)",
                                    "distancia_metros": round(distancia_qr, 1)
                                }
                                supabase.table('LOG_PRESENCIA').insert(payload_qr).execute()
                                st.success(f"OPERACIÓN {tipo} SELLADA TÁCTICAMENTE.")
                                st.rerun()

    with t2:
        st.subheader("📝 REPORTE DIRECTO AL MANDO")
        with st.form("acta_alfa"):
            f_dest = st.selectbox("Objetivo del Evento:", df_zona['OBJETIVO'].unique()) if not df_zona.empty else "N/A"
            f_vig = st.text_input("Identificación del Personal en Puesto")
            f_nov = st.text_area("Detalle Táctico de Novedad", height=100)
            gravedad = st.select_slider("NIVEL DE ALERTA:", options=["RUTINA (Verde)", "PRECAUCIÓN (Amarilla)", "CRÍTICO (Rojo)"])
            
            if st.form_submit_button("🚀 INYECTAR ACTA EN MATRIZ"):
                nivel_puro = gravedad.split(" ")[0]
                payload_acta = {
                    "fecha_hora": obtener_hora_argentina(),
                    "supervisor": st.session_state.user_sel,
                    "movil_asignado": movil_flota if 'movil_flota' in locals() else "N/A",
                    "vigilador": f_vig,
                    "objetivo": f_dest,
                    "novedad": f_nov,
                    "gravedad": nivel_puro
                }
                supabase.table('ACTAS_SUPERVISION').insert(payload_acta).execute()
                
                # Derivación automática cruzada con Mensajería
                if nivel_puro in ["PRECAUCIÓN", "CRÍTICO"]:
                    dest_msg = "GRUPAL (TODA LA TROPA)" if nivel_puro == "CRÍTICO" else "CENTRAL DE MONITOREO"
                    transmitir_directiva(st.session_state.user_sel, dest_msg, nivel_puro, f"ACTA DERIVADA [{f_dest}]: {f_nov}")
                
                st.success("Acta procesada y enrutada según protocolo de mando.")

    with t3:
        # Solo ejecutamos mostrar_buzon. Esta función ya tiene recepción y emisión.
        mostrar_buzon(st.session_state.user_sel, st.session_state.rol_sel)

# --- 7. MÓDULO MONITOREO: CENTRAL DE INTELIGENCIA OPERATIVA ---
elif st.session_state.rol_sel == "MONITOREO":
    st.header("🛰️ CENTRAL DE INTELIGENCIA OPERATIVA")
    
    # ⚡ 7.1. TELEMETRÍA DE IMPACTO (Métricas en Tiempo Real desde SQL)
    m1, m2, m3 = st.columns(3)
    
    # Extracción de Alertas SOS
    try:
        res_sos = supabase.table('ALERTAS_MONITOREO').select('*').ilike('estado', '%PENDIENTE%').execute()
        df_alertas = pd.DataFrame(res_sos.data) if res_sos.data else pd.DataFrame()
        sos_activos = len(df_alertas)
    except:
        df_alertas = pd.DataFrame()
        sos_activos = 0

    # Extracción de Mensajes Críticos/Precaución
    try:
        res_msg = supabase.table('MENSAJERIA_TACTICA').select('*').eq('estado', 'PENDIENTE').in_('prioridad', ['AMARILLA', 'ROJA']).execute()
        msg_alerta = len(res_msg.data) if res_msg.data else 0
    except:
        msg_alerta = 0

    # Extracción de Fichajes de hoy
    hoy_str = obtener_hora_argentina()[:10]
    try:
        res_qr = supabase.table('LOG_PRESENCIA').select('*').like('fecha_hora', f"{hoy_str}%").execute()
        fichajes_hoy = len(res_qr.data) if res_qr.data else 0
    except:
        fichajes_hoy = 0

    m1.metric("🚨 S.O.S ACTIVOS", sos_activos)
    m2.metric("⚠️ NOVEDADES CRÍTICAS", msg_alerta)
    m3.metric("📲 FICHAJES (HOY)", fichajes_hoy)

    t_radar, t_libro, t_chat = st.tabs(["🚨 RADAR S.O.S", "📖 BITÁCORA TÁCTICA", "📡 COMUNICACIONES"])
    
    # ⚡ 7.2. MOTOR DE RASTREO Y CIERRE DE CRISIS
    with t_radar:
        if sos_activos > 0:
            # Protocolo de Fuego Real: El mapa se centra en el operador en peligro
            datos_sos = df_alertas.iloc[-1] # Toma la alerta más reciente
            lat_sos, lon_sos = float(datos_sos['lat']), float(datos_sos['lon'])
            op_en_riesgo = datos_sos['operador']
            
            st.error(f"🚨 BRECHA DE SEGURIDAD DETECTADA: Operador {op_en_riesgo} en código S.O.S.")
            
            m_mon = folium.Map(location=[lat_sos, lon_sos], zoom_start=16, tiles="CartoDB dark_matter")
            # Marcador de Alerta Roja
            folium.Marker(
                [lat_sos, lon_sos], 
                popup=f"S.O.S: {op_en_riesgo}",
                icon=folium.Icon(color="red", icon="warning", prefix="fa")
            ).add_to(m_mon)
            
            # Traza el resto de los objetivos cercanos para referencia
            if not df_objetivos.empty:
                for _, r in df_objetivos.iterrows():
                    folium.CircleMarker([r['LATITUD'], r['LONGITUD']], radius=5, color="blue", fill=True).add_to(m_mon)
            
            st_folium(m_mon, width="100%", height=400)
            st.markdown("---")

            # Formulario de Neutralización
            with st.form("cierre_crisis"):
                st.markdown("*PROTOCOLO DE NEUTRALIZACIÓN*")
                res_acta = st.text_area("Informe Operativo de Cierre de Crisis")
                if st.form_submit_button("✅ SELLAR Y NEUTRALIZAR ALERTA", type="primary"):
                    if res_acta.strip() == "":
                        st.warning("Debe justificar la neutralización del S.O.S.")
                    else:
                        id_alerta = datos_sos['id']
                        payload_cierre = {
                            "estado": "NEUTRALIZADO",
                            "resolucion_txt": f"OPE BASE: {st.session_state.user_sel} | {res_acta}",
                            "fecha_cierre": obtener_hora_argentina()
                        }
                        supabase.table('ALERTAS_MONITOREO').update(payload_cierre).eq('id', id_alerta).execute()
                        st.success("ALERTA NEUTRALIZADA. Base de datos actualizada.")
                        time.sleep(1)
                        st.rerun()
        else:
            # Mapa de Patrullaje Normal
            st.success("ZONA SEGURA: Sin S.O.S activos.")
            if not df_objetivos.empty:
                m_mon = folium.Map(location=[df_objetivos['LATITUD'].mean(), df_objetivos['LONGITUD'].mean()], zoom_start=11, tiles="CartoDB dark_matter")
                for _, r in df_objetivos.iterrows():
                    folium.Marker([r['LATITUD'], r['LONGITUD']], tooltip=r['OBJETIVO'], icon=folium.Icon(color="blue", icon="shield", prefix="fa")).add_to(m_mon)
                st_folium(m_mon, width="100%", height=400)

    # ⚡ 7.3. BITÁCORA INMUTABLE DE MONITOREO
    with t_libro:
        st.markdown("*LIBRO DE GUARDIA OFICIAL (BASE)*")
        with st.form("acta_base"):
            nov = st.text_area("Novedades y Relevos de Guardia", height=150)
            if st.form_submit_button("🔒 SELLAR BITÁCORA"):
                if nov.strip():
                    payload_bitacora = {
                        "fecha_hora": obtener_hora_argentina(),
                        "operador_base": st.session_state.user_sel,
                        "novedad": nov
                    }
                    supabase.table('BITACORA_MONITOREO').insert(payload_bitacora).execute()
                    st.success("Registro sellado en la matriz central.")
                else:
                    st.warning("El libro no puede estar en blanco.")

    # ⚡ 7.4. COMUNICACIONES TÁCTICAS (SIN REDUNDANCIA)
    with t_chat:
        # Solo llamamos a la función matriz del Bloque 4 que ya gestiona Recepción, Emisión, Fotos y Malla Oscura.
        # Eliminamos la línea vieja que generaba el error de duplicación.
        mostrar_buzon(st.session_state.user_sel, st.session_state.rol_sel)
# --- 8. MÓDULO EJECUTIVO: COMANDO ESTRATÉGICO Y AUDITORÍA ---
elif st.session_state.rol_sel in ["JEFE DE OPERACIONES", "GERENTE"]:
    st.header(f"👔 COMANDO ESTRATÉGICO: {st.session_state.user_sel}")
    
    st.markdown("""
    <style>
    .card-alfa { padding: 15px; margin-bottom: 10px; border-radius: 5px; border-left: 5px solid; background: rgba(255,255,255,0.02); }
    .roja { border-color: #FF4B4B; } .amarilla { border-color: #FFCC00; } .verde { border-color: #00FF00; }
    </style>
    """, unsafe_allow_html=True)

    t_crisis, t_gestion, t_auditoria = st.tabs(["🚨 CENTRO DE CRISIS", "📤 EJECUCIÓN", "📊 AUDITORÍA"])
    
    with t_crisis:
        df_a = leer_matriz_nube("ALERTAS")
        if not df_a.empty:
            resueltas = df_a[df_a['ESTADO'] == 'RESUELTO'].iloc[::-1]
            for _, r in resueltas.head(10).iterrows():
                color = "roja" if "911" in str(r['RESOLUCION']) else "verde"
                st.markdown(f'<div class="card-alfa {color}"><b>{r["USUARIO"]}</b><br><small>{r["RESOLUCION"]}</small></div>', unsafe_allow_html=True)

    with t_gestion:
        with st.form("directiva_alta"):
            st.write("📩 PETICIÓN DE ALTA/BAJA A ADMINISTRACIÓN")
            tipo_p = st.selectbox("Acción:", ["ALTA", "BAJA"])
            cat_p = st.selectbox("Categoría:", ["OBJETIVO", "SUPERVISOR"])
            det_p = st.text_input("Nombre / Detalle")
            if st.form_submit_button("ELEVAR PETICIÓN"):
                escribir_registro_pro("PETICIONES", [obtener_hora_argentina(), st.session_state.user_sel, tipo_p, cat_p, det_p, "PENDIENTE"])
                st.success("Petición enviada al Núcleo Maestro.")

# --- 9. ADMINISTRADOR: NÚCLEO MAESTRO (CANDADO DE TITANIO) ---
elif st.session_state.rol_sel == "ADMINISTRADOR":
    st.header("⚙️ NÚCLEO MAESTRO: B. AYALA")
    
    if datetime.now().weekday() == 6:
        st.error("⚠️ PROTOCOLO DE CIERRE DOMINICAL DETECTADO")
        if st.button("📦 EJECUTAR BARRIDA HISTÓRICA"):
            with st.status("Migrando datos a Bóveda..."):
                st.balloons()
                st.rerun()

    st.subheader("⚖️ BUZÓN DE PETICIONES PENDIENTES")
    df_pet = leer_matriz_nube("PETICIONES")
    if not df_pet.empty:
        pend = df_pet[df_pet['ESTADO'] == 'PENDIENTE']
        for idx, r in pend.iterrows():
            with st.expander(f"Solicitud: {r['ACCION']} de {r['DETALLE']}"):
                c1, c2 = st.columns(2)
                if c1.button("✅ AUTORIZAR", key=f"ok_{idx}"):
                    actualizar_celda("PETICIONES", idx+2, "E", "EJECUTADO")
                    st.rerun()
                if c2.button("❌ RECHAZAR", key=f"no_{idx}"):
                    actualizar_celda("PETICIONES", idx+2, "E", "RECHAZADO")
                    st.rerun()
