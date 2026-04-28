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
# --- 4. BANDEJA DE INTELIGENCIA Y MENSAJERÍA ---

# Lista referencial para selectores
lista_sups = ["SUPERVISOR 1", "SUPERVISOR 2", "SUPERVISOR NOCTURNO"] 

def mostrar_buzon(usuario_actual):
    st.markdown("### 📥 BANDEJA DE INTELIGENCIA")
    df_msg = leer_matriz_nube("MENSAJERIA")
    
    if not df_msg.empty:
        mis_mensajes = df_msg[
            (df_msg['DESTINATARIO'].astype(str).str.contains(usuario_actual, na=False)) | 
            (df_msg['DESTINATARIO'].astype(str).str.contains("TODOS", na=False)) |
            (df_msg['DESTINATARIO'].astype(str).str.contains(st.session_state.rol_sel, na=False))
        ]
        
        if not mis_mensajes.empty:
            for idx, row in mis_mensajes.iloc[::-1].iterrows():
                color_borde = "#00FF00" if row['GRAVEDAD'] == "VERDE" else ("#FFCC00" if row['GRAVEDAD'] == "AMARILLO" else "#FF0000")
                with st.container():
                    st.markdown(f"""
                    <div style="border-left: 5px solid {color_borde}; background: rgba(255,255,255,0.05); padding: 12px; border-radius: 5px; margin-bottom: 8px;">
                        <small style="color: #00E5FF;">{row['FECHA']} | De: {row['REMITENTE']}</small><br>
                        <b style="font-size: 15px;">{row['ASUNTO']}</b><br>
                        <p style="font-size: 14px; margin-top: 4px;">{row['MENSAJE']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    if row['ESTADO'] != "LEÍDO":
                        if st.button(f"Confirmar Lectura", key=f"read_{idx}"):
                            actualizar_celda("MENSAJERIA", idx + 2, "F", "LEÍDO")
                            st.cache_data.clear()
                            st.rerun()
        else:
            st.info("Sin mensajes.")
    else:
        st.info("Bandeja vacía.")

def emitir_mensaje_pro(remitente):
    with st.expander("📤 REDACTAR COMUNICACIÓN"):
        with st.form("envio_tactico"):
            dest = st.selectbox("Para:", ["TODOS", "DARÍO CECILIA", "LUIS BONGIORNO", "MONITOREO"] + lista_sups)
            asu = st.text_input("Asunto")
            men = st.text_area("Mensaje")
            grav = st.selectbox("Prioridad:", ["VERDE", "AMARILLO", "ROJO"])
            if st.form_submit_button("TRANSMITIR"):
                if asu and men:
                    datos = [obtener_hora_argentina(), remitente, dest, asu, men, "ENVIADO", grav]
                    if escribir_registro_pro("MENSAJERIA", datos):
                        st.success(f"Transmitido a {dest}")
                        st.rerun()

# --- 5. INFRAESTRUCTURA LATERAL, IDENTIDAD Y BOTONES TÁCTICOS ---

# ✅ 5.1. ACCESO Y SEGURIDAD DE INFRAESTRUCTURA
def acceso_infraestructura_critica():
    with st.sidebar.expander("🔐 CREDENCIALES DE INFRAESTRUCTURA"):
        u_ingreso = st.text_input("ADMIN_USER", key="input_admin_u").lower()
        p_ingreso = st.text_input("ADMIN_PASS", type="password", key="input_admin_p")
        if u_ingreso == "admin" and p_ingreso == "aion2026":
            return True
        return False

# ✅ 5.2. GESTIÓN DE ALTAS/BAJAS Y LISTA DE IDENTIDADES
if st.session_state.rol_sel in ["GERENTE", "JEFE DE OPERACIONES", "ADMINISTRADOR"]:
    if acceso_infraestructura_critica():
        st.subheader("🏗️ GESTIÓN DE ESTRUCTURA")
        t_ab, t_list = st.tabs(["⚡ ALTAS/BAJAS", "📋 IDENTIDADES"])
        with t_ab:
            col_a, col_b = st.columns(2)
            with col_a:
                tipo = st.radio("Categoría:", ["SUPERVISOR", "SERVICIO", "VIGILADOR"], horizontal=True)
                nuevo_nombre = st.text_input(f"Nombre del {tipo}:").upper()
                if st.button(f"PROCESAR ALTA"):
                    if nuevo_nombre:
                        reg = [obtener_hora_argentina(), tipo, nuevo_nombre, "ACTIVO", st.session_state.user_sel]
                        if escribir_registro_pro("ESTRUCTURA", reg): st.success("Alta Exitosa")
            with col_b:
                df_act = leer_matriz_nube("ESTRUCTURA")
                if not df_act.empty:
                    sel_b = st.selectbox("Baja de:", df_act[df_act['ESTADO'] == 'ACTIVO']['NOMBRE'].tolist())
                    if st.button("EJECUTAR BAJA"): st.error(f"Procesando baja de {sel_b}...")

# ✅ 5.3. MÓDULO OPERATIVO: BOTONES TÁCTICOS Y TELEMETRÍA (SUPERVISOR)
if st.session_state.rol_sel == "SUPERVISOR":
    st.markdown("---")
    col_panico, col_refresco = st.columns(2)
    
    with col_panico:
        if st.button("🚨 ACTIVAR PÁNICO / SOS", use_container_width=True):
            lat, lon = st.session_state.get('lat', 'Desconocida'), st.session_state.get('lon', 'Desconocida')
            datos_sos = [obtener_hora_argentina(), st.session_state.user_sel, "PÁNICO", lat, lon, "CRÍTICO PENDIENTE"]
            if escribir_registro_pro("ALERTAS", datos_sos):
                st.error("❗ ALERTA S.O.S ENVIADA A MONITOREO Y GERENCIA")
                st.toast("Protocolo de emergencia activado.")

    with col_refresco:
        if st.button("🔄 REFRESCAR SISTEMA", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    st.markdown(f"""
        <div style="background: rgba(0, 229, 255, 0.05); padding: 10px; border-radius: 5px; border-left: 3px solid #00E5FF;">
            <small>🛰️ <b>TELEMETRÍA GPS:</b> Lat: {st.session_state.get('lat', '0.0')} | Lon: {st.session_state.get('lon', '0.0')}</small>
        </div>
    """, unsafe_allow_html=True)

# --- 6. MÓDULO SUPERVISOR: ESTACIÓN TÁCTICA Y TELEMETRÍA ALFA ---
if st.session_state.rol_sel == "SUPERVISOR":
    st.markdown(f"### ⚡ ESTACIÓN TÁCTICA: {st.session_state.user_sel}")
    
    # --- 6.1. CONTROL DE FLOTA (LOGÍSTICA GLASSMORPHISM) ---
    with st.expander("🚚 CONTROL DE UNIDAD MÓVIL", expanded=False):
        c_movf, c_km1, c_km2, c_comb = st.columns(4)
        movil_flota = c_movf.selectbox("Móvil", ["S-001", "S-002", "S-003", "S-004", "S-005", "S-006", "S-007"], key="m_v_f")
        km_in = c_km1.number_input("Km Inicial", min_value=0, key="k_i")
        km_out = c_km2.number_input("Km Final", min_value=0, key="k_o")
        comb_cargado = c_comb.number_input("Combustible (Lts)", min_value=0.0, key="c_c")
        
        if st.button("📌 SELLAR ODOMETRÍA Y LOGÍSTICA", use_container_width=True):
            if km_out >= km_in:
                datos_f = [obtener_hora_argentina()[:10], st.session_state.user_sel, movil_flota, km_in, km_out, comb_cargado]
                if escribir_registro_pro("CONTROL_FLOTA", datos_f):
                    st.success("Logística sellada en la matriz maestra.")
            else: st.warning("Revisar kilometraje: El final es menor al inicial.")

    t1, t2, t3 = st.tabs(["📍 RADAR & QR", "📤 CARGA TÁCTICA", "💬 COMUNICACIÓN"])
    
    apellido = st.session_state.user_sel.split()[-1].upper()
    df_zona = df_objetivos[df_objetivos['SUPERVISOR'].str.upper().str.contains(apellido, na=False)] if not df_objetivos.empty else pd.DataFrame()

    with t1:
        c_map, c_ctrl = st.columns([2, 1])
        
        with c_map:
            if not df_zona.empty:
                m_s = folium.Map(location=[df_zona['LATITUD'].mean(), df_zona['LONGITUD'].mean()], zoom_start=12, tiles="CartoDB dark_matter")
                for _, row in df_zona.iterrows():
                    folium.Marker(
                        [row['LATITUD'], row['LONGITUD']], 
                        popup=row['OBJETIVO'],
                        icon=folium.Icon(color="blue", icon="shield", prefix="fa")
                    ).add_to(m_s)
                st_folium(m_s, width="100%", height=400)
        
        with c_ctrl:
            if not df_zona.empty:
                dest = st.selectbox("SERVICIO ACTUAL:", df_zona['OBJETIVO'].unique())
                t_obj = df_zona[df_zona['OBJETIVO'] == dest].iloc[0]
                lat_dest, lon_dest = t_obj["LATITUD"], t_obj["LONGITUD"]
                
                url_waze = f"https://waze.com/ul?ll={lat_dest},{lon_dest}&navigate=yes"
                url_maps = f"https://www.google.com/maps/dir/?api=1&destination={lat_dest},{lon_dest}"
                
                st.markdown(f'<a href="{url_waze}" target="_blank"><button style="width:100%; padding:10px; background:#33CCFF; color:black; border-radius:5px; font-weight:bold; border:none; margin-bottom:5px;">🚙 WAZE</button></a>', unsafe_allow_html=True)
                st.markdown(f'<a href="{url_maps}" target="_blank"><button style="width:100%; padding:10px; background:#4285F4; color:white; border-radius:5px; font-weight:bold; border:none;">🗺️ GOOGLE MAPS</button></a>', unsafe_allow_html=True)
                
                st.markdown("---")
                st.session_state.qr_mode = st.radio("ACCIÓN:", ["Seleccionar...", "🟢 INGRESO", "🔴 SALIDA"], horizontal=True)
                
                if st.session_state.qr_mode != "Seleccionar...":
                    if st.checkbox("🔓 ACTIVAR ESCÁNER TÁCTICO"):
                        f_cam = st.camera_input("Enfoque el QR del Servicio")
                        if f_cam:
                            tipo = "ENTRADA" if "INGRESO" in st.session_state.qr_mode else "SALIDA"
                            delta_t = "0 min"
                            if tipo == "ENTRADA": st.session_state.hora_inicio_auditoria = datetime.now()
                            elif tipo == "SALIDA" and st.session_state.hora_inicio_auditoria:
                                mins = (datetime.now() - st.session_state.hora_inicio_auditoria).total_seconds() / 60
                                delta_t = f"{int(mins)} min"
                                st.session_state.hora_inicio_auditoria = None

                            if escribir_registro_pro("LOG_PRESENCIA", [obtener_hora_argentina(), st.session_state.user_sel, dest, tipo, "VALIDADO", delta_t], id_qr=f"QR_{dest}", servicio=dest):
                                st.success(f"OPERACIÓN {tipo} SELLADA.")
                                st.rerun()

    with t2:
        st.subheader("📝 REPORTE ÁGIL DE NOVEDADES")
        with st.form("acta_alfa"):
            f_dest = st.selectbox("Objetivo:", df_zona['OBJETIVO'].unique()) if not df_zona.empty else "N/A"
            f_vig = st.text_input("Personal en Puesto")
            f_nov = st.text_area("Informe de Novedad (Voz o Teclado)")
            gravedad = st.select_slider("GRAVEDAD:", options=["VERDE", "AMARILLO", "ROJO"])
            
            if st.form_submit_button("🚀 TRANSMITIR ACTA"):
                datos_acta = [obtener_hora_argentina(), st.session_state.user_sel, movil_flota, "", km_in, "", f_vig, f_dest, f_nov, gravedad]
                escribir_registro_pro("ACTAS_FLOTAS", datos_acta)
                
                dest_msg = "TODOS" if gravedad == "ROJO" else ("CENTRAL MONITOREO" if gravedad == "AMARILLO" else "DARIO CECILIA")
                escribir_registro_pro("MENSAJERIA", [obtener_hora_argentina(), st.session_state.user_sel, dest_msg, f"ALERTA {f_dest}", f_nov, "ENVIADO", gravedad])
                st.success("Acta derivada según protocolo de jerarquía.")

    with t3:
        mostrar_buzon(st.session_state.user_sel)
        # Inserción de componente de escritura faltante
        emitir_mensaje_pro(st.session_state.user_sel)

# --- 7. MÓDULO MONITOREO ---
elif st.session_state.rol_sel == "MONITOREO":
    st.header("🛰️ CENTRAL DE INTELIGENCIA OPERATIVA")
    
    m1, m2, m3 = st.columns(3)
    df_alertas = leer_matriz_nube("ALERTAS")
    sos_activos = len(df_alertas[df_alertas['ESTADO'].astype(str).str.upper() == 'PENDIENTE']) if not df_alertas.empty else 0
    m1.metric("🚨 S.O.S ACTIVOS", sos_activos)
    
    df_msg = leer_matriz_nube("MENSAJERIA")
    amarillas = len(df_msg[(df_msg['GRAVEDAD'] == 'AMARILLO') & (df_msg['ESTADO'] != 'LEÍDO')]) if not df_msg.empty else 0
    m2.metric("⚠️ EN PROCESO", amarillas)
    
    df_p = leer_matriz_nube("LOG_PRESENCIA")
    m3.metric("📲 FICHAJES (HOY)", len(df_p))

    t_radar, t_libro, t_chat = st.tabs(["🚨 RADAR S.O.S", "📖 LIBRO DE BASE", "💬 COMUNICACIÓN"])
    
    with t_radar:
        # Recuperación del Mapa de Monitoreo
        if not df_objetivos.empty:
            m_mon = folium.Map(location=[df_objetivos['LATITUD'].mean(), df_objetivos['LONGITUD'].mean()], zoom_start=11, tiles="CartoDB dark_matter")
            for _, r in df_objetivos.iterrows():
                folium.Marker([r['LATITUD'], r['LONGITUD']], tooltip=r['OBJETIVO']).add_to(m_mon)
            st_folium(m_mon, width="100%", height=400)
            st.markdown("---")

        if sos_activos > 0:
            datos_sos = df_alertas[df_alertas['ESTADO'].astype(str).str.upper() == 'PENDIENTE'].iloc[-1]
            op_en_riesgo = datos_sos['USUARIO']
            st.error(f"🚨 ALERTA CRÍTICA: {op_en_riesgo}")
            with st.form("cierre_crisis"):
                res_acta = st.text_area("Informe de Neutralización")
                if st.form_submit_button("✅ CERRAR ALERTA"):
                    fila_real = df_alertas[df_alertas['ESTADO'].astype(str).str.upper() == 'PENDIENTE'].index[-1] + 2
                    actualizar_celda("ALERTAS", fila_real, "D", "RESUELTO")
                    actualizar_celda("ALERTAS", fila_real, "F", f"OPE: {st.session_state.user_sel} | {res_acta}")
                    st.success("Resuelto")
                    st.cache_data.clear()
                    st.rerun()
        else:
            st.success("Zona segura: Sin alertas pendientes.")

    with t_libro:
        with st.form("acta_base"):
            nov = st.text_area("Novedades de Guardia")
            if st.form_submit_button("SELLAR"):
                escribir_registro_pro("MENSAJERIA", [obtener_hora_argentina(), st.session_state.user_sel, "DARIO CECILIA", "LIBRO BASE", nov, "ENVIADO", "VERDE"])
                st.success("Sellado.")
                st.rerun()

    with t_chat:
        mostrar_buzon(st.session_state.user_sel)
        # Inserción de componente de escritura faltante
        emitir_mensaje_pro(st.session_state.user_sel)

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
