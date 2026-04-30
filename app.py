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

# ✅ LOGO CENTRADO Y EQUILIBRADO (SIN OPACAR PESTAÑAS)
st.markdown(
    """
    <div style="display: flex; justify-content: center; width: 100%; margin-top: -30px; margin-bottom: 0px;">
        <img src="https://i.ibb.co/kMz5rP0/AION-YAROKU-LOGO.png" 
             style="width: 50%; 
                    max-height: 250px; 
                    object-fit: contain; 
                    mask-image: linear-gradient(to bottom, rgba(0,0,0,1) 60%, rgba(0,0,0,0) 100%);
                    -webkit-mask-image: linear-gradient(to bottom, rgba(0,0,0,1) 60%, rgba(0,0,0,0) 100%);">
    </div>
    """, 
    unsafe_allow_html=True
)
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
    # Link actualizado para el escudo de AION-YAROKU
    st.image("https://i.ibb.co/kMz5rP0/AION-YAROKU-LOGO.png", use_container_width=True)
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

        # --- CORRECCIÓN FINAL: KEY EN SELECTBOX ---
        destinatario = st.selectbox(
            "DESTINATARIO TÁCTICO", 
            opciones_destinatario,
            key=f"dest_tactico_{rol}_{usuario_auth.replace(' ', '_')}"
        )
        
        # --- KEY EN RADIO ---
        prioridad = st.radio(
            "NIVEL DE PRIORIDAD", 
            ["VERDE (Informativo)", "AMARILLA (Precaución)", "ROJA (Crítico)"], 
            horizontal=True,
            key=f"radio_prioridad_{rol}_{usuario_auth.replace(' ', '_')}"
        )
        nivel_pri = prioridad.split(" ")[0]

        # --- KEY EN TOGGLE ---
        usar_dark_mesh = False
        if es_cupula and destinatario in cupula_mando:
            usar_dark_mesh = st.toggle(
                "🛡️ ENRUTAR POR MALLA OSCURA (DARK MESH)", 
                value=False,
                key=f"mesh_toggle_{rol}_{usuario_auth.replace(' ', '_')}"
            )

        texto_mensaje = st.text_area("CUERPO DEL REPORTE", height=100, key=f"text_area_{rol}")
        
        # Telemetría Óptica
        st.markdown("*EVIDENCIA ÓPTICA (OPCIONAL)*")
        captura = st.camera_input("📷 CAPTURAR FOTOGRAFÍA IN SITU", key=f"cam_input_{rol}")
        
        if st.button("🚀 TRANSMITIR", use_container_width=True, key=f"btn_transmitir_{rol}"):
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
        if st.button("🔄 SINCRONIZAR RED", key=f"btn_sincronizar_{rol}"):
            st.rerun()
            
        try:
            res = supabase.table('MENSAJERIA_TACTICA').select('*').order('id', desc=True).limit(20).execute()
            mensajes = res.data if res.data else []
        except:
            mensajes = []
            st.error("Enlace SQL interrumpido.")

        if not mensajes:
            st.info("Sin tráfico en la red.")
        else:
            for m in mensajes:
                es_para_mi = m['destinatario'] == usuario_auth or m['destinatario'] == "GRUPAL (TODA LA TROPA)"
                soy_monitoreo_y_es_para_mi = rol == "MONITOREO" and m['destinatario'] == "CENTRAL DE MONITOREO"
                
                if not (es_para_mi or soy_monitoreo_y_es_para_mi):
                    continue
                
                if m['dark_mesh'] and not es_cupula:
                    continue

                color_borde = "#00E5FF" if m['prioridad'] == "VERDE" else "#FFD600" if m['prioridad'] == "AMARILLA" else "#FF1744"
                icono_mesh = "🛡️ [DARK MESH] " if m['dark_mesh'] else ""
                
                with st.expander(f"{icono_mesh}[{m['fecha_hora']}] {m['prioridad']} - De: {m['remitente']} | Estado: {m['estado']}"):
                    st.markdown(f"<div style='border-left: 4px solid {color_borde}; padding-left: 10px;'>", unsafe_allow_html=True)
                    
                    mostrar_contenido = True
                    if m['prioridad'] == "ROJA" and m['estado'] == "PENDIENTE" and rol not in ["MONITOREO", "ADMINISTRADOR"]:
                        pin_acceso = st.text_input("🔑 PIN PARA DESENCRIPTAR", type="password", key=f"pin_in_{m['id']}_{rol}")
                        if pin_acceso == "":
                            mostrar_contenido = False
                        else:
                            st.session_state[f"pin_temp_{m['id']}"] = pin_acceso

                    if mostrar_contenido:
                        st.write(m['mensaje'])
                        
                        if m['imagen_evidencia']:
                            st.markdown("*EVIDENCIA ADJUNTA:*")
                            try:
                                img_bytes = base64.b64decode(m['imagen_evidencia'])
                                st.image(img_bytes, use_container_width=True)
                            except:
                                st.error("Error al desencriptar imagen.")

                        if m['estado'] == "PENDIENTE":
                            pin_final = st.session_state.get(f"pin_temp_{m['id']}", "0000")
                            if st.button("✅ DAR ACUSE DE RECIBO", key=f"btn_ack_{m['id']}_{rol}"):
                                if ejecutar_acuse_recibo(m['id'], pin_final, st.session_state.lat, st.session_state.lon, usuario_auth):
                                    st.success("ACUSE REGISTRADO.")
                                    st.rerun()
if m['estado'] == "PENDIENTE":
                            pin_final = st.session_state.get(f"pin_temp_{m['id']}", "0000")
                            if st.button("✅ DAR ACUSE DE RECIBO", key=f"btn_ack_{m['id']}_{rol}"):
                                if ejecutar_acuse_recibo(m['id'], pin_final, st.session_state.lat, st.session_state.lon, usuario_auth):
                                    st.success("ACUSE REGISTRADO.")
                                    st.rerun()

                        if es_cupula:
                            st.markdown("---")
                            if st.button("☢️ PURGAR", key=f"btn_del_{m['id']}_{rol}", type="primary"):
                                if purgar_registro_comunicaciones(m['id']):
                                    st.error("REGISTRO DESTRUIDO.")
                                    st.rerun()

            # ESTA ES LA LÍNEA 608: Debe estar alineada exactamente con el "for m in mensajes:"
            st.markdown("</div>", unsafe_allow_html=True)
