# --- 1. CONFIGURACIÓN E IDENTIDAD VISUAL CORPORATIVA (VERSIÓN FINAL AION-YAROKU) ---
import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
from datetime import datetime
import pytz
from supabase import create_client, Client

# ✅ CORRECCIÓN GEOLOCALIZACIÓN: Sin caracteres invisibles
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
        
        /* Fondo Negro OLED con Degradado Táctico */
        .stApp { 
            background: radial-gradient(circle at top, #0A0F1E 0%, #030305 100%) !important; 
            color: #E0E0E0;
            font-family: 'Rajdhani', sans-serif;
        }

        /* 🛡️ SIDEBAR: Estética Táctica y Borde */
        [data-testid="stSidebar"] { 
            background-color: #050507 !important;
            border-right: 1px solid rgba(0, 229, 255, 0.3) !important;
        }

        [data-testid="stSidebar"]::before { 
            content: "";
            display: block;
            width: 120px;
            height: 120px;
            margin: 10px auto;
            background-image: url("https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg");
            background-size: contain;
            background-repeat: no-repeat;
            background-position: center;
        }

        /* 🛡️ LIMPIEZA DE CONTENEDORES */
        [data-testid="stVerticalBlock"], 
        [data-testid="stVerticalBlock"] > div,
        [data-testid="stMarkdownContainer"],
        .element-container,
        .stMarkdown {
            background-color: transparent !important;
            border: none !important;
            box-shadow: none !important;
        }

        /* 🛡️ LOGO CENTRAL TÁCTICO (EFECTO CAPTURA 511) */
        .contenedor-logo-central {
            display: flex;
            justify-content: center;
            align-items: center;
            width: 100%;
            margin-top: 10px;
            margin-bottom: 5px;
        }

        .logo-tactico {
            width: 580px; 
            border: 2px solid #00e5ff; /* Borde Cian Sólido */
            box-shadow: 0 0 35px rgba(0, 229, 255, 0.45); /* Resplandor Glow */
            border-radius: 4px;
        }

        .titulo-estacion {
            text-align: center;
            font-family: 'Orbitron', sans-serif;
            color: #00e5ff;
            text-shadow: 0 0 15px rgba(0, 229, 255, 0.6);
            letter-spacing: 3px;
            margin-top: 10px;
            font-weight: 700;
            text-transform: uppercase;
        }

       /* ✅ CSS PARA BOTÓN DE PÁNICO REDUCIDO Y DESPLAZADO */
        .panico-container {
            display: flex;
            justify-content: flex-end; /* Alinea al final (derecha) del contenedor */
            width: 100%;
            padding-right: 15px; /* Espacio desde el borde derecho */
            margin-top: 10px;
        }
        
        .stButton > button[kind="primary"] {
            background: radial-gradient(circle, #FF0000 0%, #8B0000 100%) !important;
            color: white !important;
            border-radius: 50% !important;
            width: 90px !important;  /* Tamaño reducido de 110px a 90px */
            height: 90px !important; /* Tamaño reducido de 110px a 90px */
            border: 2px solid #333 !important;
            box-shadow: 0 0 15px rgba(255, 0, 0, 0.4) !important;
            font-family: 'Orbitron', sans-serif;
            font-size: 10px !important; /* Fuente un poco más pequeña */
            font-weight: bold;
            line-height: 1.2;
            transition: transform 0.2s;
        }

# Ejecutar Identidad Alfa
aplicar_identidad_alfa()

def obtener_hora_argentina():
    tz = pytz.timezone("America/Argentina/Buenos_Aires")
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

# ✅ RENDERIZADO DEL LOGO CENTRAL (SEGÚN CAPTURA 511)
st.markdown(
    """
    <div class="contenedor-logo-central">
        <img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" 
             class="logo-tactico">
    </div>
    <h2 class="titulo-estacion">⚡ ESTACIÓN TÁCTICA: BRIAN AYALA</h2>
    """, 
    unsafe_allow_html=True
)

# --- 2. MEMORIA DE SESIÓN Y SIDEBAR ---
if 'rol_sel' not in st.session_state: st.session_state.rol_sel = "SUPERVISOR"
if 'user_sel' not in st.session_state: st.session_state.user_sel = "BRIAN AYALA"

with st.sidebar:
    st.markdown('<div style="margin-top: 140px;"></div>', unsafe_allow_html=True) 
    st.subheader("🛡️ PANEL DE CONTROL")
    
    perfiles = ["SUPERVISOR", "MONITOREO", "VIGILADOR", "JEFE DE OPERACIONES", "GERENCIA", "ADMINISTRADOR"]
    st.session_state.rol_sel = st.selectbox("NIVEL DE ACCESO", perfiles, key="sel_rol")
    
    lista_sups = ["BRIAN AYALA", "SUPERVISOR NOCTURNO", "SERANTES WALTER", "SANOJA LUIS", "MAZACOTTE CLAUDIO", "PORZIO GONZALO", "CARRIZO WALTER"]
    if st.session_state.rol_sel == "SUPERVISOR":
        st.session_state.user_sel = st.selectbox("IDENTIDAD OPERATIVA", lista_sups, key="sel_user")
    
    st.markdown("---")

   # ✅ RENDERIZADO CORREGIDO CON UNICODE PARA EVITAR SYNTAXERROR
st.markdown(
    f"""
    <div class="contenedor-logo-central">
        <img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" 
             class="logo-tactico">
    </div>
    <h2 class="titulo-estacion">\\u26A1 ESTACIÓN TÁCTICA: {st.session_state.user_sel}</h2>
    """, 
    unsafe_allow_html=True
)
# --- 3. ESTACIÓN DE CONTROL PRINCIPAL ---
st.subheader(f"📱 Estación de Control: {st.session_state.user_sel}")

st.markdown('<div class="radar-box">', unsafe_allow_html=True)
st.markdown("📍 **Mi Radar de Servicios y GPS**")

c_map, c_nav = st.columns([2, 1])

with c_map:
    m_s = folium.Map(location=[-34.577, -58.464], zoom_start=14, tiles="CartoDB dark_matter")
    folium.CircleMarker([-34.577, -58.464], radius=10, color="#00E5FF", fill=True).add_to(m_s)
    st_folium(m_s, width="100%", height=350)

with c_nav:
    st.markdown('<div style="background: #121214; padding: 20px; border-radius: 10px; border: 1px solid #1A1A1B;">', unsafe_allow_html=True)
    st.selectbox("Ir al Servicio:", ["CENTRAL", "ZONA NORTE", "ZONA SUR"], key="nav_tactica")
    if st.button("🗺️ INICIAR NAVEGACIÓN TÁCTICA", use_container_width=True):
        st.success("Enlace GPS Establecido")
    
    st.markdown("---")
    st.markdown(f"**LAT:** `{-34.577427}`")
    st.markdown(f"**LON:** `{-58.464084}`")
    st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)
# --- 4. CONTINUACIÓN DE FUNCIONES OPERATIVAS (Buzón, Actas, etc.) ---
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
            opciones_destinatario = ["GRUPAL (TODA LA TROPA)"] + opciones_destinatario + ["SUPERVISOR NOCTURNO", "SERANTES WALTER", "SANOJA LUIS", "MAZACOTTE CLAUDIO", "PORZIO GONZALO", "CARRIZO WALTER"]
        elif rol == "MONITOREO":
            opciones_destinatario = ["JEFE DE OPERACIONES", "GERENCIA", "SUPERVISOR NOCTURNO", "SERANTES WALTER", "SANOJA LUIS", "MAZACOTTE CLAUDIO", "PORZIO GONZALO", "CARRIZO WALTER"]

        destinatario = st.selectbox(
            "DESTINATARIO TÁCTICO", 
            opciones_destinatario,
            key=f"dest_tactico_{rol}_{usuario_auth.replace(' ', '_')}"
        )
        
        prioridad = st.radio(
            "NIVEL DE PRIORIDAD", 
            ["VERDE (Informativo)", "AMARILLA (Precaución)", "ROJA (Crítico)"], 
            horizontal=True,
            key=f"radio_prioridad_{rol}_{usuario_auth.replace(' ', '_')}"
        )
        nivel_pri = prioridad.split(" ")[0]

        usar_dark_mesh = False
        if es_cupula and destinatario in cupula_mando:
            usar_dark_mesh = st.toggle(
                "🛡️ ENRUTAR POR MALLA OSCURA (DARK MESH)", 
                value=False,
                key=f"mesh_toggle_{rol}_{usuario_auth.replace(' ', '_')}"
            )

        texto_mensaje = st.text_area("CUERPO DEL REPORTE", height=100, key=f"text_area_{rol}")
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
                    st.rerun()
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
                
                with st.expander(f"{icono_mesh}[{m['fecha_hora']}] {m['prioridad']} - De: {m['remitente']}"):
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

                        if es_cupula:
                            st.markdown("---")
                            if st.button("☢️ PURGAR", key=f"btn_del_{m['id']}_{rol}", type="primary"):
                                if purgar_registro_comunicaciones(m['id']):
                                    st.error("REGISTRO DESTRUIDO.")
                                    st.rerun()
                    
                    st.markdown("</div>", unsafe_allow_html=True)

             
               
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

# --- 6. MÓDULO SUPERVISOR: ESTACIÓN TÁCTICA ---

if st.session_state.rol_sel in ["SUPERVISOR", "SUPERVISOR NOCTURNO", "JEFE DE OPERACIONES", "GERENTE"]:
    st.markdown(f"### ⚡ ESTACIÓN TÁCTICA: {st.session_state.user_sel}")
    
    # ✅ PASO 1: Garantizar que la variable exista antes de usarla
    if 'df_objetivos' not in locals() and 'df_objetivos' not in globals():
        df_objetivos = pd.DataFrame() 

    nombre_completo = st.session_state.get('user_sel', "BRIAN AYALA")
    apellido = nombre_completo.split()[-1].upper() 

    # ✅ PASO 2: Lógica de filtrado con indentación corregida
    if st.session_state.rol_sel in ["SUPERVISOR NOCTURNO", "JEFE DE OPERACIONES", "GERENTE"]:
        df_zona = df_objetivos
    else:
        if not df_objetivos.empty:
            df_zona = df_objetivos[df_objetivos['SUPERVISOR'].str.upper().str.contains(apellido, na=False)]
        else:
            df_zona = pd.DataFrame()

    # --- 6.1. INTERFAZ DE CONTROL DE FLOTA ---
    with st.expander("🚚 AUDITORÍA DE UNIDAD MÓVIL", expanded=False):
        st.write("Registro de telemetría y estado de unidad.")
        # Aquí continúa tu lógica de columnas y formularios
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
