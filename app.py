# --- 1. CONFIGURACIÓN E IDENTIDAD VISUAL CORPORATIVA (AION-YAROKU CORE) ---
import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
from datetime import datetime
import pytz
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from streamlit_js_eval import get_geolocation
import math
from folium.plugins import AntPath

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
    except: return None

# --- 3. FUNCIONES DE LÓGICA Y DATOS ---
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
    except: return False

def escribir_registro_nube(pestana, datos_fila):
    try:
        gc = conectar_google()
        if gc:
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
            hoja.append_row(datos_fila)
            return True
    except: return False

@st.cache_data(ttl=15)
def leer_matriz_nube(pestana):
    gc = conectar_google()
    if gc:
        try:
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
            return pd.DataFrame(hoja.get_all_records())
        except: return pd.DataFrame()
    return pd.DataFrame()

@st.cache_data(ttl=60)
def cargar_objetivos():
    df = leer_matriz_nube("OBJETIVOS")
    if not df.empty:
        df.columns = df.columns.str.strip().str.upper()
        df['LATITUD'] = pd.to_numeric(df['LATITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        df['LONGITUD'] = pd.to_numeric(df['LONGITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        return df.dropna(subset=['LATITUD', 'LONGITUD'])
    return pd.DataFrame()

# --- 4. DISEÑO E IDENTIDAD VISUAL ---
def aplicar_identidad_alfa():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@300;500;700&display=swap');
        .stApp { background: radial-gradient(circle at top, #0A0F1E 0%, #030305 100%) !important; color: #E0E0E0; font-family: 'Rajdhani', sans-serif; }
        .contenedor-logo-central { display: flex; justify-content: center; align-items: center; width: 100%; margin-bottom: 5px; margin-top: 10px; }
        .logo-phoenix { width: 520px !important; border: 2px solid #00e5ff !important; box-shadow: 0 0 35px rgba(0, 229, 255, 0.5) !important; border-radius: 4px !important; background-color: #000 !important; }
        .estacion-titulo { font-family: 'Orbitron', sans-serif; color: #00E5FF !important; font-size: 24px; margin-top: 15px; display: flex; align-items: center; justify-content: center; gap: 12px; text-shadow: 0 0 15px rgba(0, 229, 255, 0.4); letter-spacing: 2px; text-transform: uppercase; }
        .radar-box { border: 1px solid #1A1A1B; border-radius: 12px; padding: 10px; background: rgba(10, 10, 11, 0.9); }
        .stButton > button[kind="primary"] { background: radial-gradient(circle, #FF0000 0%, #8B0000 100%) !important; color: white !important; border-radius: 50% !important; width: 105px !important; height: 105px !important; border: 3px solid #333 !important; box-shadow: 0 0 25px rgba(255, 0, 0, 0.5) !important; font-family: 'Orbitron', sans-serif; font-size: 11px !important; font-weight: bold; }
        
        /* Estilos para la Bandeja de Inteligencia (imagen 0) */
        .chat-container {
            border: 1px solid #00e5ff;
            border-radius: 8px;
            padding: 15px;
            margin-top: 20px;
            background-color: #05050a;
        }
        .message-box {
            border: 1px solid #333;
            border-radius: 4px;
            padding: 10px;
            margin-bottom: 10px;
        }
        .message-info {
            color: #00e5ff;
            font-size: 14px;
            margin-bottom: 5px;
        }
        .message-text {
            color: #ccc;
            font-size: 14px;
        }

        /* Estilos para formularios (imagen 1, 2, 3) */
        .panel-novedad {
            border: 1px solid #333;
            border-radius: 8px;
            padding: 15px;
            margin-top: 20px;
            background-color: rgba(10, 10, 11, 0.9);
        }
        .panel-info {
            display: flex;
            justify-content: space-between;
            margin-bottom: 20px;
            padding: 10px;
            border: 1px solid #333;
            border-radius: 4px;
        }
        .info-item {
            text-align: center;
        }
        
        /* Estilos para Administrador (imagen 4) */
        .peticiones-container {
            border: 1px solid #00e5ff;
            border-radius: 8px;
            padding: 15px;
            margin-top: 20px;
            background-color: #05050a;
        }
        </style>
        """, unsafe_allow_html=True
    )

aplicar_identidad_alfa()

# --- 5. SIDEBAR TÁCTICO (ACTUALIZADO) ---
df_objetivos = cargar_objetivos()

if 'rol_sel' not in st.session_state: st.session_state.rol_sel = "MONITOREO"
if 'user_sel' not in st.session_state: st.session_state.user_sel = "BRIAN AYALA"

with st.sidebar:
    st.markdown('<div class="contenedor-logo-sidebar"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" style="width:180px; border:1px solid #00e5ff; border-radius:4px;"></div>', unsafe_allow_html=True)
    st.subheader("🛡️ PANEL DE CONTROL")
    
    # El selector de roles sigue activo
    st.session_state.rol_sel = st.selectbox("NIVEL DE ACCESO", ["SUPERVISOR", "MONITOREO", "JEFE DE OPERACIONES", "GERENCIA", "ADMINISTRADOR"], index=["SUPERVISOR", "MONITOREO", "JEFE DE OPERACIONES", "GERENCIA", "ADMINISTRADOR"].index(st.session_state.rol_sel))
    
    # LISTA DE IDENTIDAD OPERATIVA
    usuarios_por_rol = {
        "MONITOREO": ["BRIAN AYALA", "SANOJA LUIS", "DARÍO CECILIA"],
        "SUPERVISOR": ["SUPERVISOR LUNA", "SERANTES WALTER", "MAZACOTTE CLAUDIO"],
        "JEFE DE OPERACIONES": ["DARÍO CECILIA"],
        "GERENCIA": ["LUIS BONGIORNO"],
        "ADMINISTRADOR": ["NÚCLEO MAESTRO"]
    }
    
    usuarios = usuarios_por_rol.get(st.session_state.rol_sel, ["BRIAN AYALA"])
    
    if st.session_state.user_sel not in usuarios:
        st.session_state.user_sel = usuarios[0]
        
    st.session_state.user_sel = st.selectbox("IDENTIDAD OPERATIVA", usuarios, index=usuarios.index(st.session_state.user_sel))
    
    # --- EMERGENCIA (SOLO PARA MONITOREO Y SUPERVISOR) ---
    if st.session_state.rol_sel in ["MONITOREO"]: # Se quitó SUPERVISOR de la emergencia del sidebar
        st.write("---")
        st.markdown("**🚨 CONFIGURACIÓN DE EMERGENCIA**")
        
        # Objetivo en pánico
        opciones_objetivo = df_objetivos['OBJETIVO'].unique() if not df_objetivos.empty else ["N/A"]
        obj_panico = st.selectbox("🎯 SELECCIONAR OBJETIVO", opciones_objetivo)
        
        # Supervisor de zona
        sup_panico = st.selectbox("👤 SUPERVISOR DE ZONA", ["BRIAN AYALA", "GONZALO PORZIO", "SUPERVISOR NOCTURNO", "OTRO"])
        
        loc = get_geolocation()
        lat_envio = loc['coords']['latitude'] if loc else 0.0
        lon_envio = loc['coords'].get('longitude', 0.0) if loc else 0.0

        if st.button("ACTIVAR\nPÁNICO", type="primary"):
            # Registro en la nube
            carga_sos = f"LAT:{lat_envio}|LON:{lon_envio}|OBJ:{obj_panico}|SUP:{sup_panico}"
            # Nota: Asegurar que la columna D en Excel sea ESTADO y E sea CARGA_UTIL
            escribir_registro_nube("ALERTAS", [obtener_hora_argentina(), st.session_state.user_sel, "PÁNICO", "PENDIENTE", carga_sos])
            st.error(f"🚨 S.O.S ENVIADO: {obj_panico}")

# --- 6. CABECERA CENTRAL ---
st.markdown('<div class="contenedor-logo-central"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" class="logo-phoenix"></div>', unsafe_allow_html=True)

# Títulos por Rol con Estilo Glow
titulos = {
    "MONITOREO": "🛰️ CENTRAL DE INTELIGENCIA OPERATIVA",
    "SUPERVISOR": f"📱 ESTACIÓN OPERATIVA | {st.session_state.user_sel}", # Modificado para Supervisor (imagen 3)
    "JEFE DE OPERACIONES": f"👤 COMANDO ESTRATÉGICO: {st.session_state.user_sel}", # Modificado (imagen 1)
    "GERENCIA": f"👤 Comando Estratégico: {st.session_state.user_sel}", # Modificado (imagen 2)
    "ADMINISTRADOR": f"⚙️ NÚCLEO MAESTRO: {st.session_state.user_sel}" # Modificado (imagen 4)
}
# Agrega icono de candado para Administrador (imagen 4)
prefix_admin = ""
if st.session_state.rol_sel == "ADMINISTRADOR":
    prefix_admin = '<span style="color:#f1c40f; margin-right:10px;">🔑</span>'

st.markdown(f'<div class="estacion-titulo">{prefix_admin}{titulos.get(st.session_state.rol_sel, "SISTEMA TÁCTICO DE COMANDO")}</div>', unsafe_allow_html=True)

# --- 7. FLUJO POR ROLES ---

# A. ROL: MONITOREO
if st.session_state.rol_sel == "MONITOREO":
    
    # Indicadores superiores (de tu código original)
    df_emergencias = leer_matriz_nube("ALERTAS")
    alertas_activas = df_emergencias[df_emergencias['ESTADO'].astype(str).str.upper() == 'PENDIENTE']
    sos_activos = len(alertas_activas)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("🚨 S.O.S ACTIVOS", sos_activos)
    c2.metric("📡 RED", "OPERATIVA")
    c3.metric("🕒 HORA LOCAL", obtener_hora_argentina().split(" ")[1])

    # 1. PESTAÑAS (Modificadas según imagen 0)
    # Se cambian los nombres de las pestañas
    t_radar, t_comunicacion, t_gestion = st.tabs(["🚨 RADAR S.O.S", "💬 COMUNICACIÓN", "📖 LIBRO DE BASE"])
    
    with t_radar:
        # --- (Mismo código del mapa que ya tenías) ---
        lat_foco, lon_foco = -34.6, -58.4
        obj_en_panico, sup_responsable = "", ""
        
        df_comisarias = leer_matriz_nube("COMISARIAS")
        comisaria_cercana = None
        dist_minima = float('inf')
        
        if sos_activos > 0:
            datos_sos = alertas_activas.iloc[-1]
            try:
                # Extraer Objetivo y Supervisor
                partes = datos_sos.get('CARGA_UTIL', '').split("|")
                obj_en_panico = partes[2].split(":")[1].strip()
                sup_responsable = partes[3].split(":")[1].strip()
                
                # Ubicación del Objetivo en pánico (Limpieza de comas)
                target_data = df_objetivos[df_objetivos['OBJETIVO'] == obj_en_panico].iloc[0]
                lat_foco = float(str(target_data['LATITUD']).replace(',','.'))
                lon_foco = float(str(target_data['LONGITUD']).replace(',','.'))

                # Buscar Comisaría (Usando posiciones de columna)
                if not df_comisarias.empty:
                    for _, com in df_comisarias.iterrows():
                        try:
                            # Posición 0: Nombre, 1: Lat, 2: Lon (según Captura 565)
                            c_lat = float(str(com.iloc[1]).replace(',','.'))
                            c_lon = float(str(com.iloc[2]).replace(',','.'))
                            
                            # Haversine formula
                            R = 6371.0
                            phi1, phi2 = math.radians(lat_foco), math.radians(c_lat)
                            dphi, dlambda = math.radians(c_lat-lat_foco), math.radians(c_lon-lon_foco)
                            a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
                            d = R * (2 * math.atan2(math.sqrt(a), math.sqrt(1-a)))
                            
                            if d < dist_minima:
                                dist_minima = d
                                comisaria_cercana = {"NOMBRE": com.iloc[0], "LAT": c_lat, "LON": c_lon}
                        except: continue
                
                st.error(f"🚨 EMERGENCIA EN CURSO: {obj_en_panico}")
            except: pass
        else:
            st.success("✅ Vigilancia Pasiva - Radar Operativo")

        # --- MAPA ---
        # Se genera el objeto folium.Map
        m_mon = folium.Map(location=[lat_foco, lon_foco], zoom_start=13, tiles="CartoDB dark_matter")
        
        # Efecto Blink para el objetivo en SOS
        map_css = "<style>@keyframes blink {0%{opacity:1;}50%{opacity:0.3;}100%{opacity:1;}} .blink-icon {animation: blink 0.8s linear infinite;}</style>"
        m_mon.get_root().header.add_child(folium.Element(map_css))

        # Dibujar todos los puntos
        for _, r in df_objetivos.iterrows():
            try:
                r_lat, r_lon = float(str(r['LATITUD']).replace(',','.')), float(str(r['LONGITUD']).replace(',','.'))
                es_sos = (r['OBJETIVO'] == obj_en_panico)
                
                color_nodo = "red" if es_sos else "#00E5FF"
                
                # Tooltip (iconos y datos)
                sup_display = sup_responsable if es_sos else r.get('SUPERVISOR', 'N/A')
                tooltip_html = f"🚨 <b>OBJ:</b> {r['OBJETIVO']}<br>👤 <b>SUP:</b> {sup_display}"

                folium.CircleMarker(
                    location=[r_lat, r_lon], radius=8 if es_sos else 6,
                    color=color_nodo, fill=es_sos, fill_color=color_nodo, weight=3,
                    tooltip=folium.Tooltip(tooltip_html, sticky=True),
                    className="blink-icon" if es_sos else ""
                ).add_to(m_mon)
            except: continue

        # --- DIBUJAR RUTA Y COMISARÍA (SI HAY SOS) ---
        if sos_activos > 0 and comisaria_cercana:
            try:
                folium.Marker(
                    [comisaria_cercana['LAT'], comisaria_cercana['LON']], 
                    tooltip=f"🚓 {comisaria_cercana['NOMBRE']}", 
                    icon=folium.Icon(color="blue", icon="shield-halved", prefix="fa")
                ).add_to(m_mon)
                
                AntPath(
                    locations=[[comisaria_cercana['LAT'], comisaria_cercana['LON']], [lat_foco, lon_foco]], 
                    color='#FFEB3B', weight=6, delay=600
                ).add_to(m_mon)
            except: pass

        # Representación en Streamlit
        st_folium(m_mon, width="100%", height=450, key="mapa_final_monitoreo")

        # --- BOTÓN DE CIERRE (DEBAJO DEL MAPA) ---
        if sos_activos > 0:
            st.markdown("---")
            st.subheader("📝 PROTOCOLO DE CIERRE")
            inf_neu = st.text_area("INFORME DE NEUTRALIZACIÓN")
            if st.button("FINALIZAR OPERATIVO", use_container_width=True):
                if inf_neu.strip():
                    # Obtener la fila en Excel (índice DataFrame + 2)
                    fila_excel = alertas_activas.index[-1] + 2
                    # Columna D: ESTADO, F: INFORME
                    actualizar_celda("ALERTAS", fila_excel, "D", "RESUELTO")
                    actualizar_celda("ALERTAS", fila_excel, "F", inf_neu)
                    st.success("✅ Operativo Finalizado")
                    st.rerun()
                else:
                    st.warning("⚠️ El informe es obligatorio para cerrar.")

    # 2. PESTAÑA DE COMUNICACIÓN (Incorporación de imagen 0)
    with t_comunicacion:
        st.subheader("Bandeja de Inteligencia") # Titulo similar a imagen 0

        # Cargar chats (usando leer_matriz_nube - requiere pestaña "CHATS" en Excel)
        df_chats = leer_matriz_nube("CHATS")
        
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)
        
        if not df_chats.empty:
            # Mostrar últimos 10 mensajes, ordenados del más nuevo al más viejo
            mensajes = df_chats.tail(10).iloc[::-1]
            for _, msg in mensajes.iterrows():
                # Nota: Ajustar nombres de columnas según tu Excel ("HORA", "USUARIO", "TEXTO")
                hora_m = msg.get('HORA', obtener_hora_argentina())
                user_m = msg.get('USUARIO', 'DESCONOCIDO')
                texto_m = msg.get('TEXTO', '')
                
                # Caja de mensaje estilo chat (imagen 0)
                st.markdown(
                    f'<div class="message-box">'
                    f'<div class="message-info">{hora_m} De: {user_m}</div>'
                    f'<div class="message-text">{texto_m}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )
        else:
            st.info("Sin mensajes en la bandeja.")
        
        st.markdown('</div>', unsafe_allow_html=True) # Cierre chat-container

        # Área de envío de mensajes (Redactar comunicación - imagen 0)
        with st.expander("Redactar Comunicación", expanded=True):
            user_dest = st.selectbox("Para:", usuarios) # Mismo usuario activo por ahora (imagen 0)
            st.text_input("Asunto:", value="TODOS") # Valor predeterminado (imagen 0)
            nuevo_msg = st.text_area("Mensaje:", height=100)
            
            prio = st.selectbox("Prioridad:", ["VERDE", "AMARILLA", "ROJA"]) # Selectbox prioridad (imagen 0)
            
            if st.button("TRANSMITIR", key="send_chat_mon"):
                if nuevo_msg.strip():
                    # Registro en nube ("CHATS")
                    escribir_registro_nube("CHATS", [obtener_hora_argentina(), st.session_state.user_sel, nuevo_msg, prio, user_dest])
                    st.success("✅ Mensaje Transmitido")
                    st.rerun()
                else:
                    st.warning("⚠️ El mensaje no puede estar vacío.")

    # 3. LIBRO DE BASE (fuera del radar)
    with t_gestion:
        st.subheader("📖 HISTORIAL DE OPERATIVOS")
        if not df_emergencias.empty:
            st.dataframe(df_emergencias.iloc[::-1], use_container_width=True)
        else:
            st.info("No hay registros en el historial.")

# B. ROL: JEFE DE OPERACIONES (Incorporación imagen 1)
elif st.session_state.rol_sel == "JEFE DE OPERACIONES":
    st.subheader("Unidad Móvil")

    # Tabs (imagen 1)
    t_crisis, t_ejecucion, t_auditoria = st.tabs(["Centro de Crisis", "Ejecución", "Auditoría"])

    with t_ejecucion:
        st.markdown('<div class="panel-novedad">', unsafe_allow_html=True)
        st.subheader("🚨 PETICIÓN DE ALTA/BAJA")
        
        accion = st.selectbox("Acción:", ["ALTA", "BAJA"])
        cat = st.selectbox("Categoría:", ["OBJETIVO", "MÓVIL", "RECURSO HUMANO"])
        nom_det = st.text_input("Nombre / Detalle:")
        
        if st.button("ELEV AR PETICIÓN"):
            if nom_det.strip():
                # Registro en la nube (Requiere pestaña "PETICIONES")
                escribir_registro_nube("PETICIONES", [obtener_hora_argentina(), st.session_state.user_sel, accion, cat, nom_det])
                st.success("✅ Petición Elevada")
            else:
                st.warning("⚠️ El nombre/detalle es obligatorio.")
        
        st.markdown('</div>', unsafe_allow_html=True) # Cierre panel-novedad

# C. ROL: GERENCIA (Incorporación imagen 2)
elif st.session_state.rol_sel == "GERENCIA":
    
    st.subheader("👤 PANEL DE RENTABILIDAD OPERATIVA")
    
    st.markdown('<div class="panel-info">', unsafe_allow_html=True)
    # Valores de ejemplo (imagen 2)
    st.markdown('<div class="info-item"><span style="color:#2ecc71;">$ 1.200.000</span><br>Ahorro Riesgo</div>', unsafe_allow_html=True)
    st.markdown('<div class="info-item"><span style="color:#3498db;">47/93</span><br>Nivel Cobertura</div>', unsafe_allow_html=True)
    st.markdown('<div class="info-item"><span style="color:#f1c40f;">2</span><br>Auditorias</div>', unsafe_allow_html=True)
    st.markdown('<div class="info-item"><span style="color:#e74c3c;">4954 Km</span><br>Desgaste</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Botón sidebar (imagen 2)
    st.sidebar.button("FORZAR REFREZCO MATRIZ", key="force_ger")

    # Tabs (imagen 2)
    t_directiva, t_peticion, t_tabla = st.tabs(["Dirección", "Petición", "Tabla Resumen"])

    with t_directiva:
        st.markdown('<div class="panel-novedad">', unsafe_allow_html=True)
        st.subheader("Transmisión de Directiva")
        st.text_input("Asunto (Push a Celulares):", value="DIRECTIVA GENERAL")
        directiva = st.text_area("Directiva:", height=100)
        prio_gen = st.selectbox("Prioridad:", ["VERDE", "AMARILLA", "ROJA"], key="prio_ger")
        
        if st.button("EJECUTAR DIRECTIVA"):
            if directiva.strip():
                # Registro nube ("CHATS")
                escribir_registro_nube("CHATS", [obtener_hora_argentina(), st.session_state.user_sel, directiva, prio_gen, "TODOS"])
                st.success("✅ Directiva Transmitida")
            else:
                st.warning("⚠️ La directiva no puede estar vacía.")
        
        st.markdown('</div>', unsafe_allow_html=True)

# D. ROL: SUPERVISOR (Incorporación imagen 3 - Todo salvo mapa y pánico sidebar)
elif st.session_state.rol_sel == "SUPERVISOR":
    
    # --- PANEL UNIDAD MÓVIL (imagen 3) ---
    st.subheader("Control de Unidad Móvil")
    
    with st.container():
        st.markdown('<div class="panel-info">', unsafe_allow_html=True)
        
        # Selectores (imagen 3)
        c_mov, c_km_i, c_km_f, c_comb = st.columns([2,2,2,2])
        with c_mov: st.selectbox("Móvil:", ["S-001", "M-002"], key="sup_mov")
        with c_km_i: st.number_input("Km Inicial:", value=0)
        with c_km_f: st.number_input("Km Final:", value=0)
        with c_comb: st.number_input("Combustible (Lts):", value=0.0)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Botón sello logístico (imagen 3)
        st.button("SELLAR ODOMETRÍA Y LOGÍSTICA")

    # Tabs (imagen 3)
    t_visita, t_carga, t_com_sup = st.tabs(["Visita QR", "Carga Táctica", "Comunicación"])

    with t_visita:
        # Servicio actual (imagen 3)
        servicios_disponibles = df_objetivos['OBJETIVO'].unique() if not df_objetivos.empty else ["ALFAVINIL"]
        st.selectbox("SERVICIO ACTUAL:", servicios_disponibles, key="sup_serv")
        
        # Acción radio (imagen 3)
        st.radio("ACCIÓN:", ["SELECCIONAR...", "INGRESO", "SALIDA"], index=0, key="sup_accion", horizontal=True)

    with t_carga:
        # Carga Táctica (imagen 3 - similar al botón de directiva de Gerencia pero local)
        st.markdown('<div class="panel-novedad">', unsafe_allow_html=True)
        st.subheader("Carga Táctica")
        novedad = st.text_area("Novedad / Registro:", height=100)
        
        if st.button("CARGAR REGISTRO TÁCTICO"):
            if novedad.strip():
                # Registro nube (Pestaña "NOVEDADES" - ajustar según Excel)
                escribir_registro_nube("NOVEDADES", [obtener_hora_argentina(), st.session_state.user_sel, novelty])
                st.success("✅ Registro Cargado")
            else:
                st.warning("⚠️ El registro no puede estar vacío.")
        st.markdown('</div>', unsafe_allow_html=True)

    # --- MAPA FISCALIZADOR (De tu código original, se mantiene) ---
    st.write("---")
    st.subheader("📡 LOCALIZACIÓN DE OBJETIVOS")
    st.markdown('<div class="radar-box">', unsafe_allow_html=True)
    centro = [df_objetivos['LATITUD'].mean(), df_objetivos['LONGITUD'].mean()] if not df_objetivos.empty else [-34.6, -58.4]
    m_isor = folium.Map(location=centro, zoom_start=12, tiles="CartoDB dark_matter")
    for _, r in df_objetivos.iterrows():
        folium.Marker(
            [r['LATITUD'], r['LONGITUD']], 
            tooltip=f"OBJETIVO: {r['OBJETIVO']} | SUPERVISOR: {r.get('SUPERVISOR', 'N/A')}", 
            icon=folium.Icon(color="blue", icon="shield", prefix="fa")
        ).add_to(m_visor)
    st_folium(m_visora, width="100%", height=400, key="map_supervisor")
    st.markdown('</div>', unsafe_allow_html=True)

# E. ROL: ADMINISTRADOR (Incorporación imagen 4)
elif st.session_state.rol_sel == "ADMINISTRADOR":
    
    st.subheader("Panel de Peticiones Pendientes")
    
    # Peticiones (imagen 4)
    df_peticiones = leer_matriz_nube("PETICIONES")
    
    st.markdown('<div class="peticiones-container">', unsafe_allow_html=True)
    
    if not df_peticiones.empty:
        # Mostrar peticiones ordenadas del más nuevo al más viejo
        pets = df_peticiones.tail(5).iloc[::-1]
        for _, pet in pets.iterrows():
            hora_p = pet.get('HORA', obtener_hora_argentina())
            user_p = pet.get('USUARIO', 'DESCONOCIDO')
            cat_p = pet.get('CATEGORIA', 'DESCONOCIDO')
            nom_p = pet.get('NOMBRE', '')
            accion_p = pet.get('ACCION', '')
            
            # Caja estilo chat (similar a Bandeja de Inteligencia de imagen 0)
            st.markdown(
                f'<div class="message-box">'
                f'<div class="message-info">{hora_p} Solicitante: {user_p} ({cat_p})</div>'
                f'<div class="message-text">Petición de {accion_p} para: {nom_p}</div>'
                f'</div>',
                unsafe_allow_html=True
            )
    else:
        st.info("Sin peticiones pendientes.")
    
    st.markdown('</div>', unsafe_allow_html=True) # Cierre peticiones-container
    
    # Credenciales Infraestructura (imagen 4)
    with st.expander("Credenciales Infraestructura", expanded=True):
        st.text_input("ADMIN_USER:")
        st.text_input("ADMIN_PASS:", type="password")
