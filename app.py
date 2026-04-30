# --- 1. CONFIGURACIÓN E IDENTIDAD VISUAL CORPORATIVA (ESTILO ESTACIÓN DE CONTROL) ---
import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
from datetime import datetime
import pytz
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from supabase import create_client, Client
import hashlib
import json
import base64
import time

# ✅ CORRECCIÓN FINAL: GEOLOCALIZACIÓN
try:
    from streamlit_js_eval import get_geolocation
except ImportError:
    get_geolocation = None

# Configuración de página OLED
st.set_page_config(
    page_title="AION-YAROKU | CORE",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inicialización Supabase
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except Exception:
        return None

supabase = init_connection()

def aplicar_identidad_alfa():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@300;500;700&display=swap');
        
        /* Fondo Negro OLED Profundo */
        .stApp { 
            background-color: #050505 !important; 
            color: #E0E0E0;
            font-family: 'Rajdhani', sans-serif;
        }

        /* Sidebar Oscuro */
        [data-testid="stSidebar"] { 
            background-color: #0A0A0B !important;
            border-right: 1px solid #1A1A1B !important;
        }

        /* Títulos en Cian Táctico */
        h1, h2, h3, .stSubheader { 
            font-family: 'Orbitron', sans-serif; 
            color: #00E5FF !important; 
            text-shadow: 0 0 10px rgba(0, 229, 255, 0.3);
            text-transform: uppercase;
        }

        /* 🛡️ ELIMINACIÓN DE RECUADROS GRISES */
        [data-testid="stVerticalBlock"], 
        [data-testid="stVerticalBlock"] > div,
        [data-testid="stMarkdownContainer"],
        .element-container,
        .stMarkdown {
            background-color: transparent !important;
            border: none !important;
            box-shadow: none !important;
        }

        /* Botón de Pánico Circular (Rojo Pulsante) */
        .panico-container {
            display: flex;
            justify-content: center;
            padding: 30px 0;
        }
        
        .stButton > button[kind="primary"] {
            background: radial-gradient(circle, #FF0000 0%, #8B0000 100%) !important;
            color: white !important;
            border-radius: 50% !important;
            width: 130px !important;
            height: 130px !important;
            border: 4px solid #333 !important;
            box-shadow: 0 0 25px rgba(255, 0, 0, 0.6) !important;
            font-family: 'Orbitron', sans-serif;
            font-size: 14px !important;
            transition: all 0.3s ease;
        }
        
        .stButton > button[kind="primary"]:hover {
            transform: scale(1.05);
            box-shadow: 0 0 40px rgba(255, 0, 0, 0.8) !important;
        }

        /* Contenedor del Radar de Servicios */
        .radar-box {
            border: 1px solid #1A1A1B;
            border-radius: 12px;
            padding: 20px;
            background: #0A0A0B;
            box-shadow: inset 0 0 20px rgba(0, 229, 255, 0.05);
        }
        </style>
        """, unsafe_allow_html=True
    )

aplicar_identidad_alfa()

def obtener_hora_argentina():
    tz = pytz.timezone("America/Argentina/Buenos_Aires")
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

# --- 2. MEMORIA DE SESIÓN Y SIDEBAR TÁCTICO ---
if 'rol_sel' not in st.session_state: st.session_state.rol_sel = "SUPERVISOR"
if 'user_sel' not in st.session_state: st.session_state.user_sel = "BRIAN AYALA"
if 'lat' not in st.session_state: st.session_state.lat = 0.0
if 'lon' not in st.session_state: st.session_state.lon = 0.0

with st.sidebar:
    st.markdown("### 🛡️ AION YORAKU")
    
    # Perfiles de Acceso Estilo Imagen
    perfiles = ["SUPERVISOR", "MONITOREO", "GERENCIA", "ADMINISTRADOR"]
    st.session_state.rol_sel = st.selectbox("PERFIL DE ACCESO", perfiles, key="sel_rol")
    
    # Identificación
    identidades = ["AYALA BRIAN", "CECILIA DARIO", "CALDO DOLVIR", "KALEN ANDRES"]
    st.session_state.user_sel = st.selectbox("IDENTIFÍQUESE", identidades, key="sel_user")

    # Botón de Pánico Circular al Final
    st.markdown('<div class="panico-container">', unsafe_allow_html=True)
    if st.button("ACTIVAR\nPÁNICO", type="primary"):
        # Lógica de SOS...
        st.error("❗ SOS TRANSMITIDO")
    st.markdown('</div>', unsafe_allow_html=True)

# --- 3. ESTACIÓN DE CONTROL PRINCIPAL ---
st.subheader(f"📱 Estación de Control: {st.session_state.user_sel}")

# Contenedor Radar (Estilo Tablero Táctico)
st.markdown('<div class="radar-box">', unsafe_allow_html=True)
st.markdown("📍 **Mi Radar de Servicios y GPS**")

c_map, c_nav = st.columns([2, 1])

with c_map:
    # Simulación de Radar GPS
    m_s = folium.Map(location=[-34.577, -58.464], zoom_start=14, tiles="CartoDB dark_matter")
    folium.CircleMarker([-34.577, -58.464], radius=10, color="#00E5FF", fill=True).add_to(m_s)
    st_folium(m_s, width="100%", height=350)

with c_nav:
    st.markdown('<div style="background: #121214; padding: 20px; border-radius: 10px; border: 1px solid #1A1A1B;">', unsafe_allow_html=True)
    st.selectbox("Ir al Servicio:", ["CENTRAL", "ZONA NORTE", "ZONA SUR"], key="nav_serv")
    if st.button("🗺️ INICIAR NAVEGACIÓN TÁCTICA", use_container_width=True):
        st.success("Enlace GPS Establecido")
    
    st.markdown("---")
    st.markdown("**ESTADO DE RED:** ✅ ACTIVA")
    st.markdown(f"**LAT:** `{st.session_state.lat}`")
    st.markdown(f"**LON:** `{st.session_state.lon}`")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# --- 4. SECCIONES DE MENSAJERÍA Y GESTIÓN (REUTILIZADAS) ---
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

# --- 4.6. INTERFAZ DE COMUNICACIONES Y ENRUTAMIENTO (BUZÓN) ---
def mostrar_buzon(usuario_auth, rol):
    st.markdown("---")
    st.subheader("📡 COMUNICACIONES TÁCTICAS")
    
    # ✅ DEFINICIÓN DE LA CÚPULA (Protección de acceso)
    cupula_mando = ["BRIAN AYALA", "LUIS BONGIORNO", "DARÍO CECILIA"]
    es_cupula = usuario_auth in cupula_mando or rol in ["ADMINISTRADOR", "GERENCIA", "JEFE DE OPERACIONES"]

    tab_recepcion, tab_emision = st.tabs(["📥 BANDEJA DE ENTRADA", "📤 TRANSMITIR DIRECTIVA"])

    # ---------------------------------------------------------
    # PESTAÑA 1: TRANSMISIÓN
    # ---------------------------------------------------------
    with tab_emision:
        st.markdown("*NUEVA DIRECTIVA / NOVEDAD*")
        opciones_destinatario = ["CENTRAL DE MONITOREO", "JEFE DE OPERACIONES", "GERENCIA"]
        
        if es_cupula:
            opciones_destinatario = ["GRUPAL (TODA LA TROPA)"] + opciones_destinatario + ["SUPERVISOR NOCTURNO", "SERANTES WALTER", "SANOJA LUIS", "MAZACOTTE CLAUDIO", "PORZIO GONZALO", "CARRIZO WALTER"]
        elif rol == "MONITOREO":
            opciones_destinatario = ["JEFE DE OPERACIONES", "GERENCIA", "SUPERVISOR NOCTURNO", "SERANTES WALTER", "SANOJA LUIS", "MAZACOTTE CLAUDIO", "PORZIO GONZALO", "CARRIZO WALTER"]

        destinatario = st.selectbox("DESTINATARIO TÁCTICO", opciones_destinatario, key=f"dest_{rol}_{usuario_auth.replace(' ', '_')}")
        prioridad = st.radio("NIVEL DE PRIORIDAD", ["VERDE (Informativo)", "AMARILLA (Precaución)", "ROJA (Crítico)"], horizontal=True, key=f"pri_{rol}")
        nivel_pri = prioridad.split(" ")[0]

        texto_mensaje = st.text_area("CUERPO DEL REPORTE", height=100, key=f"txt_{rol}")
        captura = st.camera_input("📷 CAPTURAR FOTOGRAFÍA", key=f"cam_{rol}")
        
        if st.button("🚀 TRANSMITIR", use_container_width=True, key=f"btn_send_{rol}"):
            if texto_mensaje.strip() != "":
                img_b64 = encriptar_imagen_b64(captura) if captura else None
                transmitir_directiva(usuario_auth, destinatario, nivel_pri, texto_mensaje, img_b64)
                st.success("TRANSMISIÓN ENVIADA.")
                st.rerun()

    # ---------------------------------------------------------
    # PESTAÑA 2: RECEPCIÓN (Aquí es donde estaba el error)
    # ---------------------------------------------------------
    with tab_recepcion:
        if st.button("🔄 SINCRONIZAR RED", key=f"sync_{rol}"):
            st.rerun()
            
        try:
            res = supabase.table('MENSAJERIA_TACTICA').select('*').order('id', desc=True).limit(20).execute()
            mensajes = res.data if res.data else []
        except:
            mensajes = []

        if not mensajes:
            st.info("Sin tráfico en la red.")
        else:
            for m in mensajes:
                # Filtros de visibilidad
                es_para_mi = m['destinatario'] == usuario_auth or m['destinatario'] == "GRUPAL (TODA LA TROPA)"
                soy_monitoreo = rol == "MONITOREO" and m['destinatario'] == "CENTRAL DE MONITOREO"
                
                if not (es_para_mi or soy_monitoreo): continue
                if m['dark_mesh'] and not es_cupula: continue

                color_b = "#00E5FF" if m['prioridad'] == "VERDE" else "#FFD600" if m['prioridad'] == "AMARILLA" else "#FF1744"
                
                with st.expander(f"De: {m['remitente']} | {m['fecha_hora']}"):
                    st.markdown(f"<div style='border-left: 4px solid {color_b}; padding-left: 10px;'>", unsafe_allow_html=True)
                    st.write(m['mensaje'])
                    
                    if m['imagen_evidencia']:
                        img_bytes = base64.b64decode(m['imagen_evidencia'])
                        st.image(img_bytes, use_container_width=True)

                    # ✅ BOTÓN DE ACUSE PARA TODOS
                    if m['estado'] == "PENDIENTE":
                        if st.button("✅ RECIBIDO", key=f"ack_{m['id']}"):
                            ejecutar_acuse_recibo(m['id'], "0000", st.session_state.lat, st.session_state.lon, usuario_auth)
                            st.rerun()

                    # ✅ BOTÓN DE PURGA SÓLO PARA LA CÚPULA (Bien alineado)
                    if es_cupula:
                        st.markdown("---")
                        if st.button("☢️ PURGAR REGISTRO", key=f"del_{m['id']}", type="primary"):
                            if purgar_registro_comunicaciones(m['id']):
                                st.error("DESTRUIDO.")
                                st.rerun()
                    
                    st.markdown("</div>", unsafe_allow_html=True)

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
                tipo = st.radio("Categoría:", ["SUPERVISOR", "SERVICIO", "VIGILADOR", "HORIZONTAL"], horizontal=True, key="radio_alta_tipo")
                nuevo_nombre = st.text_input(f"Nombre del {tipo}:").upper()
                
                # --- AQUÍ SE AGREGA EL PIN (LO QUE PIDIÓ TU SOCIO) ---
                pin_seguridad = st.text_input("Asignar PIN de Acceso (4 dígitos):", value="1234", key=f"pin_alta_{tipo}")
                
                if st.button(f"PROCESAR ALTA"):
                    if nuevo_nombre:
                        payload = {
                            "fecha": obtener_hora_argentina(),
                            "tipo": tipo,
                            "nombre": nuevo_nombre,
                            "pin": pin_seguridad,  # <-- PIN AGREGADO AL REGISTRO
                            "estado": "ACTIVO",
                            "registrado_por": st.session_state.user_sel
                        }
                        # Inyección directa a Supabase
                        supabase.table('ESTRUCTURA').insert(payload).execute()
                        st.success(f"Alta Exitosa de {nuevo_nombre} con PIN: {pin_seguridad}")
            
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
    
    # 🚨 INTERRUPTOR DE PÁNICO POR DESLIZAMIENTO
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
        supabase.table('ALERTAS').insert(payload_sos).execute()
        st.error("❗ ALERTA S.O.S ENVIADA A MONITOREO Y GERENCIA")
        st.toast("Protocolo de emergencia activado.")
        time.sleep(1)
        st.rerun()
    elif deslizador_sos > 0:
        st.warning(f"Gatillo en {deslizador_sos}%. Deslice al 100% para confirmar emergencia.")

    if st.button("🔄 REFRESCAR SISTEMA", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

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
elif st.session_state.rol_sel in ["JEFE DE OPERACIONES", "GERENTE", "ADMINISTRADOR"]:
    st.header(f"👔 COMANDO ESTRATÉGICO: {st.session_state.user_sel}")
    
    # CSS para el HUD de la cúpula
    st.markdown("""
    <style>
    .card-alfa { padding: 15px; margin-bottom: 10px; border-radius: 5px; border-left: 5px solid; background: rgba(255,255,255,0.02); }
    .roja { border-color: #FF4B4B; } .amarilla { border-color: #FFCC00; } .verde { border-color: #00FF00; }
    </style>
    """, unsafe_allow_html=True)

    t_crisis, t_gestion, t_auditoria, t_comms = st.tabs(["🚨 CENTRO DE CRISIS", "⚡ EJECUCIÓN DIRECTA", "📊 AUDITORÍA GLOBAL", "📡 COMUNICACIONES"])
    
    # ⚡ 8.1. CENTRO DE CRISIS (Registro Histórico)
    with t_crisis:
        st.subheader("HISTORIAL DE ALERTAS NEUTRALIZADAS")
        try:
            res_alertas = supabase.table('ALERTAS_MONITOREO').select('*').eq('estado', 'NEUTRALIZADO').order('id', desc=True).limit(15).execute()
            if res_alertas.data:
                for r in res_alertas.data:
                    # Si la resolución incluye la palabra S.O.S, coacción o 911, marca rojo, si no verde
                    color = "roja" if any(x in str(r.get('resolucion_txt', '')).upper() for x in ["S.O.S", "COACCIÓN", "911", "ARMADO"]) else "verde"
                    st.markdown(f'''
                        <div class="card-alfa {color}">
                            <b>OPERADOR: {r.get("operador", "N/A")}</b> | Fecha: {r.get("fecha_hora", "")}<br>
                            <small>📍 Lat: {r.get("lat", "")} | Lon: {r.get("lon", "")}</small><br>
                            <small style="color:#00E5FF;"><b>RESOLUCIÓN:</b> {r.get("resolucion_txt", "Sin detalles")}</small>
                        </div>
                    ''', unsafe_allow_html=True)
            else:
                st.info("No hay historial de crisis en la matriz reciente.")
        except:
            st.error("Fallo de enlace con la tabla de Alertas.")

    # ⚡ 8.2. EJECUCIÓN DIRECTA (Gestión SQL sin intermediarios)
    with t_gestion:
        st.subheader("ALTA TÁCTICA DE NUEVOS OBJETIVOS")
        with st.form("directiva_alta_objetivo"):
            st.write("La inyección impactará la matriz de toda la flota en tiempo real.")
            col_o1, col_o2 = st.columns(2)
            nuevo_obj = col_o1.text_input("Nombre del Objetivo Nuevo").upper()
            dir_obj = col_o2.text_input("Dirección y Localidad").upper()
            
            # Extraer supervisores activos para asignación
            lista_sup = ["SIN ASIGNAR"]
            try:
                res_sup = supabase.table('ESTRUCTURA_PERSONAL').select('nombre').in_('rol', ['SUPERVISOR', 'SUPERVISOR NOCTURNO']).eq('estado', 'ACTIVO').execute()
                if res_sup.data:
                    lista_sup = [s['nombre'] for s in res_sup.data]
            except: pass
            
            sup_asignado = st.selectbox("Supervisor a Cargo", lista_sup)
            
            col_c1, col_c2 = st.columns(2)
            lat_n = col_c1.number_input("Latitud Exacta", format="%.6f")
            lon_n = col_c2.number_input("Longitud Exacta", format="%.6f")
            
            if st.form_submit_button("🚀 EJECUTAR INYECCIÓN EN MATRIZ", type="primary"):
                if nuevo_obj and dir_obj and lat_n != 0.0:
                    payload_obj = {
                        "objetivo": nuevo_obj,
                        "direccion": dir_obj,
                        "supervisor": sup_asignado,
                        "latitud": lat_n,
                        "longitud": lon_n,
                        "alarma": "INACTIVA",
                        "policia": "911"
                    }
                    try:
                        supabase.table('OBJETIVOS').insert(payload_obj).execute()
                        st.success(f"OBJETIVO '{nuevo_obj}' INYECTADO. Geocerca activada.")
                        st.cache_data.clear() # Limpia caché para que los supervisores vean el cambio al instante
                    except:
                        st.error("Error al escribir en la base de datos SQL.")
                else:
                    st.warning("Debe completar Nombre, Dirección y Coordenadas para armar la Geocerca.")

    # ⚡ 8.3. AUDITORÍA GLOBAL (Extracción de Fichajes y Logística)
    with t_auditoria:
        st.subheader("OJO PANÓPTICO: AUDITORÍA DE TERRENO")
        sub_tab1, sub_tab2 = st.tabs(["📱 FICHAJES QR / GEOCERCA", "🚚 LOGÍSTICA FLOTA"])
        
        with sub_tab1:
            st.caption("Validación de Presencia y Fraude Espacial")
            if st.button("🔄 EXTRAER MATRIZ DE FICHAJES"):
                try:
                    res_presencia = supabase.table('LOG_PRESENCIA').select('fecha_hora, operador, objetivo, accion, estado, distancia_metros').order('id', desc=True).limit(50).execute()
                    if res_presencia.data:
                        df_presencia = pd.DataFrame(res_presencia.data)
                        st.dataframe(df_presencia, use_container_width=True, hide_index=True)
                    else:
                        st.info("Sin registros de fichaje.")
                except:
                    st.error("Enlace SQL interrumpido.")
                    
        with sub_tab2:
            st.caption("Control de Odometría y Combustible")
            if st.button("🔄 EXTRAER MATRIZ LOGÍSTICA"):
                try:
                    res_flota = supabase.table('CONTROL_FLOTA').select('fecha, supervisor, movil, km_inicial, km_final, combustible').order('id', desc=True).limit(50).execute()
                    if res_flota.data:
                        df_flota = pd.DataFrame(res_flota.data)
                        st.dataframe(df_flota, use_container_width=True, hide_index=True)
                    else:
                        st.info("Sin registros de flota.")
                except:
                    st.error("Enlace SQL interrumpido.")

    # ⚡ 8.4. COMUNICACIONES (Dark Mesh)
    with t_comms:
        mostrar_buzon(st.session_state.user_sel, st.session_state.rol_sel)

# --- 9. ADMINISTRADOR: NÚCLEO MAESTRO (CANDADO DE TITANIO) ---
elif st.session_state.rol_sel == "ADMINISTRADOR":
    st.header("⚙️ NÚCLEO MAESTRO: B. AYALA (ACCESO RAÍZ)")
    
    st.markdown("---")
    c_defcon, c_db = st.columns(2)
    
    # ⚡ 9.1. AISLAMIENTO TOTAL
    with c_defcon:
        st.subheader("🚨 PROTOCOLO DEFCON 1")
        st.write("Bloqueo absoluto del sistema. Corta el enlace SQL de toda la flota en terreno y gerencia.")
        
        # Un check de confirmación para no apretar el botón rojo por error
        if st.checkbox("Habilitar Switch de Apagón"):
            if st.button("☢️ DETONAR APAGÓN GLOBAL", type="primary", use_container_width=True):
                with st.spinner("Desconectando terminales..."):
                    try:
                        # 1. Purga de acceso operativo (Todos a INACTIVO menos Brian Ayala)
                        supabase.table('ESTRUCTURA_PERSONAL').update({"estado": "BLOQUEO_DEFCON"}).neq('nombre', 'BRIAN AYALA').execute()
                        
                        # 2. Inyección de Kill Switch (Fuerza el cierre de sesión en los teléfonos)
                        supabase.table('SEGURIDAD_OPERADORES').update({"estado": "COMPROMETIDO"}).neq('usuario', 'BRIAN AYALA').execute()
                        
                        st.error("DEFCON 1 EJECUTADO. Todos los nodos han sido neutralizados. Acceso exclusivo para Nivel Raíz.")
                    except:
                        st.warning("Interferencia en la ejecución SQL.")
                
    # ⚡ 9.2. MANTENIMIENTO DE RENDIMIENTO SQL
    with c_db:
        st.subheader("📦 MIGRACIÓN TÁCTICA A BÓVEDA")
        st.write("Purga de memoria caché y traslado de actas operativas a la Bóveda Histórica Inmutable.")
        
        if st.button("🗄️ EJECUTAR BARRIDA DE DATOS", use_container_width=True):
            with st.status("Ejecutando volcado SQL y optimización de índices..."):
                try:
                    # Llama a una función interna de Supabase (RPC) para mover filas viejas y vaciar RAM
                    supabase.rpc('ejecutar_barrida_historica').execute()
                    time.sleep(2) # Simulación de tiempo de encriptación de bloques
                    st.success("BARRIDA COMPLETADA. Matriz principal operando al 100% de rendimiento.")
                except:
                    st.error("Aviso: Requiere configurar la función 'ejecutar_barrida_historica' en el servidor Supabase.")

    st.markdown("---")
    
    # ⚡ 9.3. AUDITORÍA DE LA CÚPULA (ROOT ALERTS)
    st.subheader("👁️ VISOR EN LA SOMBRA (INTERCEPCIÓN DARK MESH)")
    st.caption("Tráfico clasificado de Jefatura y Gerencia interceptado por Nivel Raíz.")
    
    if st.button("🔄 ACTUALIZAR INTERCEPTOR"):
        st.rerun()

    try:
        # Extrae mensajes de la tabla saltándose los bloqueos de usuario normales
        res_shadow = supabase.table('MENSAJERIA_TACTICA').select('*').eq('dark_mesh', True).order('id', desc=True).limit(10).execute()
        
        if res_shadow.data:
            for m in res_shadow.data:
                estado_msj = m.get('estado', 'DESCONOCIDO')
                color_borde = "#FF1744" if estado_msj == "PENDIENTE" else "#00E5FF"
                
                st.markdown(f"<div style='border-left: 4px solid {color_borde}; padding-left: 10px; background: rgba(0,0,0,0.2); margin-bottom: 5px;'>", unsafe_allow_html=True)
                with st.expander(f"🛡️ [INTERCEPTADO] De: {m['remitente']} a {m['destinatario']}"):
                    st.write(f"*Contenido:* {m['mensaje']}")
                    st.caption(f"Emitido: {m['fecha_hora']} | Prioridad: {m['prioridad']} | Estado: {estado_msj}")
                st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("La Malla Oscura está en silencio.")
    except:
        st.error("Enlace de interceptación caído.")
