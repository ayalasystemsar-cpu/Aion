import streamlit as st
import datetime
from datetime import datetime
import pandas as pd
import pytz
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from streamlit_js_eval import get_geolocation

# --- IMPORTACIONES CRÍTICAS DE MAPAS ---
import folium
from folium.plugins import AntPath
from streamlit_folium import st_folium
import math

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
            data = hoja.get_all_records()
            if not data:
                return pd.DataFrame()
            return pd.DataFrame(data)
        except: return pd.DataFrame()
    return pd.DataFrame()

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

# --- 4. DISEÑO E IDENTIDAD VISUAL ---
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
            color: #00E5FF !important;
            font-size: 24px;
            margin-top: 15px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
            text-shadow: 0 0 15px rgba(0, 229, 255, 0.4);
            letter-spacing: 2px;
            text-transform: uppercase;
        }
        
        .titulo-seccion-admin {
            color: #00E5FF;
            font-family: 'Orbitron', sans-serif;
            font-size: 22px;
            font-weight: bold;
            margin-top: 25px;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
            letter-spacing: 1px;
            text-shadow: 0 0 10px rgba(0, 229, 255, 0.3);
        }

        .stApp div[data-testid="stExpander"] {
            background-color: #1A1C23 !important;
            border: 1px solid #2D313E !important;
            border-radius: 8px !important;
        }
        
        .stApp div[data-testid="stExpander"] summary p {
            color: #E0E0E0 !important;
            font-size: 14px !important;
            font-weight: 600 !important;
            text-transform: uppercase;
        }
        
        .stApp input {
            background-color: #252833 !important;
            color: #FFFFFF !important;
            border: 1px solid #1A1C23 !important;
            border-radius: 6px !important;
        }
        
        .stApp label p {
            color: #A0A5B5 !important;
            font-family: 'Orbitron', sans-serif !important;
            font-size: 11px !important;
            font-weight: bold !important;
            letter-spacing: 0.5px;
            text-transform: uppercase;
        }

        .radar-box { border: 1px solid #1A1A1B; border-radius: 12px; padding: 10px; background: rgba(10, 10, 11, 0.9); }
        .stButton > button[kind="primary"] { 
            background: radial-gradient(circle, #FF0000 0%, #8B0000 100%) !important; 
            color: white !important; border-radius: 50% !important; width: 105px !important; height: 105px !important; 
            border: 3px solid #333 !important; box-shadow: 0 0 25px rgba(255, 0, 0, 0.5) !important; 
            font-family: 'Orbitron', sans-serif; font-size: 11px !important; font-weight: bold;
        }
        
        .chat-container { border: 1px solid #1a1a1b; border-radius: 8px; padding: 15px; margin-top: 10px; background-color: #030305; }
        .message-box { border-left: 3px solid #00e5ff; padding-left: 10px; margin-bottom: 15px; background: rgba(255,255,255,0.02); padding-top: 5px; padding-bottom: 5px; }
        .message-box-red { border-left: 3px solid #ff0000; padding-left: 10px; margin-bottom: 15px; background: rgba(255,255,255,0.02); padding-top: 5px; padding-bottom: 5px; }
        .message-info { color: #00e5ff; font-size: 13px; font-weight: bold; font-family: 'Orbitron', sans-serif; }
        .message-info-red { color: #ff0000; font-size: 13px; font-weight: bold; font-family: 'Orbitron', sans-serif; }
        .message-text { color: #e0e0e0; font-size: 14px; margin-top: 4px; font-family: 'Rajdhani', sans-serif; }
        
        .panel-info { display: flex; justify-content: space-between; margin-bottom: 20px; padding: 10px; border: 1px solid #333; border-radius: 4px; background: rgba(10, 10, 11, 0.9); }
        .panel-novedad { border: 1px solid #333; border-radius: 8px; padding: 15px; margin-top: 20px; background-color: rgba(10, 10, 11, 0.9); }

        .stButton > button.btn-refresh {
            background: #00e5ff !important;
            color: #000 !important;
            font-family: 'Orbitron', sans-serif;
            font-weight: bold;
            border-radius: 4px !important;
            border: 1px solid #00e5ff !important;
            box-shadow: 0 0 10px rgba(0, 229, 255, 0.3) !important;
        }

        .stTabs [data-baseweb="tab-list"] { gap: 10px; background-color: transparent; }
        .stTabs [data-baseweb="tab"] {
            background-color: rgba(26, 28, 35, 0.4) !important;
            border: 1px solid #2D313E !important;
            color: #A0A5B5 !important;
            border-radius: 4px 4px 0px 0px !important;
            padding: 6px 16px !important;
            font-family: 'Orbitron', sans-serif;
            font-size: 11px !important;
            font-weight: bold;
        }
        .stTabs [data-baseweb="tab"]:hover { color: #00E5FF !important; }
        .stTabs [aria-selected="true"] {
            background-color: #1A1C23 !important;
            border-top: 2px solid #00E5FF !important;
            color: #00E5FF !important;
        }

        div[data-testid="stMetric"] {
            background-color: rgba(10, 11, 15, 0.6) !important;
            border: 1px solid #1A1C23 !important;
            border-radius: 6px !important;
            padding: 12px !important;
        }
        div[data-testid="stMetricLabel"] p {
            color: #00E5FF !important;
            font-family: 'Rajdhani', sans-serif !important;
            font-size: 13px !important;
            font-weight: bold !important;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        div[data-testid="stMetricValue"] div {
            color: #FFFFFF !important;
            font-family: 'Orbitron', sans-serif !important;
            font-size: 22px !important;
        }
        </style>
        """, unsafe_allow_html=True
    )

aplicar_identidad_alfa()

# --- 5. SIDEBAR TÁCTICO ---
df_objetivos = cargar_objetivos()

LISTA_SUPS_TACTICOS = [
    "AYALA BRIAN",
    "SUPERVISOR 1", 
    "SUPERVISOR 2", 
    "SUPERVISOR 3", 
    "SUPERVISOR 4", 
    "SUPERVISOR 5", 
    "SUPERVISOR NOCTURNO"
]

if 'rol_sel' not in st.session_state: st.session_state.rol_sel = "MONITOREO"
if 'user_sel' not in st.session_state: st.session_state.user_sel = "OPERADOR CENTRAL"
if 'sup_autenticado' not in st.session_state: st.session_state.sup_autenticado = False

with st.sidebar:
    st.markdown('<div class="contenedor-logo-sidebar"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" style="width:180px; border:1px solid #00e5ff; border-radius:4px;"></div>', unsafe_allow_html=True)
    st.subheader("🛡️ PANEL DE CONTROL")
    st.markdown("<span style='font-size: 11px; color:#A0A5B5; font-family:\"Orbitron\"; font-weight:bold; letter-spacing:0.5px;'>NIVEL DE ACCESO</span>", unsafe_allow_html=True)
    
    if st.button("🛰️ MONITOREO", use_container_width=True): st.session_state.rol_sel = "MONITOREO"; st.rerun()
    if st.button("👤 VIGILADOR", use_container_width=True): st.session_state.rol_sel = "VIGILADOR"; st.rerun()
    if st.button("📋 JEFE DE OPERACIONES", use_container_width=True): st.session_state.rol_sel = "JEFE DE OPERACIONES"; st.rerun()
    if st.button("🏢 GERENCIA", use_container_width=True): st.session_state.rol_sel = "GERENCIA"; st.rerun()

    with st.expander("👤 SUPERVISORES"):
        nom_sup = st.selectbox("RESPONSABLE ACTIVO:", LISTA_SUPS_TACTICOS, key="cambio_supervisor_directo")
        user_sup = st.text_input("USUARIO RECURSO (APELLIDO)", key="auth_user_sup")
        pass_sup = st.text_input("CONTRASEÑA CRÍTICA", type="password", key="auth_pass_sup")
        if st.button("AUTENTICAR E INGRESAR", use_container_width=True):
            st.session_state.rol_sel = "SUPERVISOR"; st.session_state.user_sel = nom_sup; st.session_state.sup_autenticado = True; st.rerun()

    if st.button("⚙️ ADMINISTRADOR", use_container_width=True): st.session_state.rol_sel = "ADMINISTRADOR"; st.rerun()

    # ... (Resto del código de pánico igual) ...

# --- 7. FLUJO POR ROLES ---

# A. ROL: VIGILADOR (NUEVO)
if st.session_state.rol_sel == "VIGILADOR":
    st.markdown('<div class="estacion-titulo">🛡️ PANEL DE VIGILADOR</div>', unsafe_allow_html=True)
    nombre_v = st.text_input("DNI o Apellido:")
    obj_v = st.selectbox("Objetivo Asignado:", df_objetivos['OBJETIVO'].unique() if not df_objetivos.empty else ["CARGANDO..."])
    
    st.subheader("📷 Presentismo Facial")
    foto = st.camera_input("Fichar Entrada")
    if foto:
        escribir_registro_nube("PRESENTISMO", [obtener_hora_argentina(), nombre_v, obj_v, "PRESENTE"])
        st.success("¡Presentismo registrado!")

    st.write("---")
    if st.button("🚨 SOLICITAR CAMBIO DE GUARDIA"):
        info_sup = df_objetivos[df_objetivos['OBJETIVO'].str.upper() == obj_v.upper()]
        if not info_sup.empty:
            sup = info_sup['SUPERVISOR'].iloc[0]
            escribir_registro_nube("NOVEDADES_GUARDIA", [obtener_hora_argentina(), obj_v, nombre_v, "SOLICITUD", sup])
            st.success(f"Solicitud enviada a: {sup}")

# B. ROL: MONITOREO (Original)
elif st.session_state.rol_sel == "MONITOREO":
    # (Toda tu lógica original de monitoreo aquí)
    st.write("Cargando Monitoreo...")

# C. ROL: SUPERVISOR
elif st.session_state.rol_sel == "SUPERVISOR":
    t1, t2 = st.tabs(["Control Táctico", "🚨 BANDEJA NOVEDADES GUARDIA"])
    with t1:
        st.write("Interfaz de control táctico original...")
    with t2:
        st.subheader("🚨 Bandeja de Cambios de Guardia")
        df_ng = leer_matriz_nube("NOVEDADES_GUARDIA")
        if not df_ng.empty:
            df_ng.columns = df_ng.columns.str.strip().str.upper()
            st.dataframe(df_ng[df_ng['SUPERVISOR_ASIGNADO'].str.upper() == st.session_state.user_sel.upper()], use_container_width=True)

# (Continúa con el resto de tus bloques ELIF originales: JEFE, GERENCIA, ADMIN)
# B. ROL: JEFE DE OPERACIONES
elif st.session_state.rol_sel == "JEFE DE OPERACIONES":
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🚨 S.O.S ACTIVOS", "0")
    col2.metric("📡 RED", "OPERATIVA")
    col3.metric("👤 USUARIO", f"{st.session_state.user_sel}")
    col4.metric("🕒 HORA LOCAL", obtener_hora_argentina().split(" ")[1])

    t_crisis, t_ejecucion, t_auditoria = st.tabs(["Centro de Crisis", "Ejecución", "Auditoría"])
    
    with t_crisis:
        st.subheader("📡 RADAR Y LOCALIZACIÓN DE OBJETIVOS")
        st.markdown('<div class="radar-box">', unsafe_allow_html=True)
        df_obj_maps_jefe = df_objetivos.dropna(subset=['LATITUD', 'LONGITUD']) if not df_obj_maps_jefe.empty else pd.DataFrame()
        centro = [df_obj_maps_jefe['LATITUD'].mean(), df_obj_maps_jefe['LONGITUD'].mean()] if not df_obj_maps_jefe.empty else [-34.6, -58.4]
        m_visor = folium.Map(location=centro, zoom_start=12, tiles="CartoDB dark_matter")
        if not df_obj_maps_jefe.empty:
            for _, r in df_obj_maps_jefe.iterrows():
                folium.Marker(
                    [r['LATITUD'], r['LONGITUD']], 
                    tooltip=f"OBJETIVO: {r['OBJETIVO']} | SUPERVISOR: {r.get('SUPERVISOR', 'N/A')}", 
                    icon=folium.Icon(color="blue", icon="shield", prefix="fa")
                ).add_to(m_visor)
        st_folium(m_visor, width="100%", height=500, key=f"map_jefe_operaciones_crisis")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with t_ejecucion:
        st.markdown('<div class="panel-novedad">', unsafe_allow_html=True)
        st.subheader("🚨 PETICIÓN DE ALTA/BAJA")
        
        o_accion = st.selectbox("Acción:", ["ALTA", "BAJA"])
        o_cat = st.selectbox("Categoría:", ["OBJETIVO", "MÓVIL", "RECURSO HUMANO"])
        o_det = st.text_input("Nombre / Detalle:")
        
        if st.button("ELEV AR PETICIÓN"):
            if o_det.strip():
                escribir_registro_nube("PETICIONES", [obtener_hora_argentina(), st.session_state.user_sel, o_accion, o_cat, o_det])
                st.success("✅ Petición Elevada Exitosamente")
            else:
                st.error("⚠️ El campo Nombre / Detalle es obligatorio.")
        st.markdown('</div>', unsafe_allow_html=True)

    st.write("---")
    st.subheader("📋 REPORTE DE MOVIMIENTOS")
    df_novedades = leer_matriz_nube("ACTAS_FLOTAS")
    if not df_novedades.empty:
        st.dataframe(df_novedades.tail(20), use_container_width=True)

# C. ROL: SUPERVISOR (FILTRADO PERIMETRAL EXACTO Y MAPAS CON CENTRO DINÁMICO)
elif st.session_state.rol_sel == "SUPERVISOR":
    if not st.session_state.sup_autenticado:
        st.info("🔒 Estación Bloqueada. Ingrese las credenciales correspondientes en la sección lateral de SUPERVISORES.")
    else:
        # --- FILTRADO DIRECTO 1 A 1 CONTRA EL SIDEBAR ---
        sup_activo_normalizado = st.session_state.user_sel.strip().upper()

        if not df_objetivos.empty and 'SUPERVISOR' in df_objetivos.columns:
            df_objetivos_filtrados = df_objetivos[df_objetivos['SUPERVISOR'].astype(str).str.strip().str.upper() == sup_activo_normalizado]
        else:
            df_objetivos_filtrados = pd.DataFrame()

        st.subheader("Control de Unidad Móvil")
        
        st.markdown('<div class="panel-info">', unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            s_movil = st.selectbox("Móvil:", ["S-001", "M-002", "M-003", "OTRO"], key="sup_movil_select")
        with c2:
            s_km_inicial = st.number_input("Km Inicial:", value=0, step=1, key="sup_km_inicial")
        with c3:
            s_km_final = st.number_input("Km Final:", value=0, step=1, key="sup_km_final")
        with c4:
            s_combustible = st.number_input("Combustible (Lts):", value=0.0, step=0.1, key="sup_combustible")
        st.markdown('</div>', unsafe_allow_html=True)
        
        col_btn1, col_btn2 = st.columns([3, 1])
        with col_btn1:
            st.button("SELLAR ODOMETRÍA Y LOGÍSTICA", key="btn_sellar_logistica", use_container_width=True)
        with col_btn2:
            if st.button("REFRESCAR SISTEMA", key="btn_refrescar_sistema", help="Sincronizar matriz central"):
                st.rerun()

        t_vis_qr, t_car_tac, t_com_sup = st.tabs(["Visita QR", "Carga Táctica", "Comunicación"])
        
        with t_vis_qr:
            if not df_objetivos_filtrados.empty:
                opciones_servicios = df_objetivos_filtrados['OBJETIVO'].unique()
            else:
                opciones_servicios = []

            if len(opciones_servicios) == 0:
                opciones_servicios = ["SIN OBJETIVOS ASIGNADOS"]
            
            st.selectbox("SERVICIO ACTUAL:", opciones_servicios, key="sup_servicio_actual")
            st.radio("ACCIÓN:", ["SELECCIONAR...", "INGRESO", "SALIDA"], index=0, key="sup_radio_accion", horizontal=True)
            
            st.write("---")
            st.subheader("📡 RADAR Y LOCALIZACIÓN DE OBJETIVOS ASIGNADOS")
            st.markdown('<div class="radar-box">', unsafe_allow_html=True)
            
            # --- MOTOR DE RENDERIZADO TÁCTICO DE MAPAS REAC-DINA ---
            if not df_objetivos_filtrados.empty:
                df_mapa_sup = df_objetivos_filtrados.dropna(subset=['LATITUD', 'LONGITUD']).copy()
                
                # Desinfectamos de raíz comas por puntos y barremos espacios invisibles en strings de coordenadas
                df_mapa_sup['LATITUD'] = df_mapa_sup['LATITUD'].astype(str).str.strip().str.replace(',', '.')
                df_mapa_sup['LONGITUD'] = df_mapa_sup['LONGITUD'].astype(str).str.strip().str.replace(',', '.')
                
                df_mapa_sup['LATITUD'] = pd.to_numeric(df_mapa_sup['LATITUD'], errors='coerce')
                df_mapa_sup['LONGITUD'] = pd.to_numeric(df_mapa_sup['LONGITUD'], errors='coerce')
                df_mapa_sup = df_mapa_sup.dropna(subset=['LATITUD', 'LONGITUD'])
            else:
                df_mapa_sup = pd.DataFrame()
            
            if not df_mapa_sup.empty:
                # Centro de masa del vector de los objetivos del supervisor logueado
                centro_coordenadas = [df_mapa_sup['LATITUD'].mean(), df_mapa_sup['LONGITUD'].mean()]
                m_visor = folium.Map(location=centro_coordenadas, zoom_start=12, tiles="CartoDB dark_matter")
                
                for _, r in df_mapa_sup.iterrows():
                    nombre_objetivo = str(r['OBJETIVO']).strip()
                    tooltip_html = f"🎯 <b>OBJETIVO:</b> {nombre_objetivo}<br>👤 <b>RESPONSABLE:</b> {sup_activo_normalizado}"
                    folium.Marker(
                        [r['LATITUD'], r['LONGITUD']], 
                        tooltip=folium.Tooltip(tooltip_html, sticky=True), 
                        icon=folium.Icon(color="blue", icon="shield", prefix="fa")
                    ).add_to(m_visor)
            else:
                m_visor = folium.Map(location=[-34.6037, -58.3816], zoom_start=12, tiles="CartoDB dark_matter")
                st.warning("⚠️ No se detectaron coordenadas válidas en la matriz para estos objetivos.")
                
            st_folium(m_visor, width="100%", height=500, key=f"map_visor_sup_dinamico_{sup_activo_normalizado}")
            st.markdown('</div>', unsafe_allow_html=True)
            
        with t_car_tac:
            st.markdown('<div class="panel-novedad">', unsafe_allow_html=True)
            st.subheader("📋 CARGA DE REGISTROS TÁCTICOS")
            novedad_sup = st.text_area("Novedad / Registro Operativo:", key="texto_novedad_supervisor")
            if st.button("CARGAR REGISTRO", key="btn_cargar_registro_sup"):
                if novedad_sup.strip():
                    escribir_registro_nube("NOVEDADES", [obtener_hora_argentina(), st.session_state.user_sel, novedad_sup])
                    st.success("✅ Registro cargado en la matriz central")
            st.markdown('</div>', unsafe_allow_html=True)
            
        with t_com_sup:
            st.subheader("Bandeja de Novedades del Sector")
            df_chats_sup = leer_matriz_nube("CHATS")
            if not df_chats_sup.empty:
                st.dataframe(df_chats_sup.tail(10), use_container_width=True)

# D. ROL: GERENCIA
elif st.session_state.rol_sel == "GERENCIA":
    st.markdown('<h2 style="color:#00E5FF; font-family:\'Orbitron\', sans-serif; font-size:24px; margin-bottom:5px;">Comando Estratégico: DIRECCIÓN GENERAL</h2>', unsafe_allow_html=True)
    st.markdown('<h3 style="color:#FFFFFF; font-family:\'Rajdhani\', sans-serif; font-size:18px; margin-top:0px; margin-bottom:20px;">Panel de Rentabilidad Operativa</h3>', unsafe_allow_html=True)
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Ahorro de Riesgo (Estimado)", "$ 1.200.000")
    m2.metric("Nivel de Cobertura", "47/93")
    m3.metric("Auditorías Físicas (QRs)", "2")
    m4.metric("Desgaste Flota (Km)", "4954 Km")
    
    st.write("")
    
    t_com_est, t_ejecucion_ger, t_tab_auditoria = st.tabs(["📩 COMUNICACIÓN ESTRATÉGICA", "🎮 EJECUCIÓN", "📍 TABLERO DE AUDITORÍA"])
    
    with t_com_est:
        st.markdown('<div class="panel-novedad">', unsafe_allow_html=True)
        st.subheader("Transmitir Directiva (Push a Celulares)")
        
        g_para = st.selectbox("Para:", ["TODOS"] + LISTA_SUPS_TACTICOS, key="ger_para")
        g_asunto = st.text_input("Asunto:", key="ger_asunto")
        g_orden = st.text_area("Orden:", key="ger_orden")
        g_prioridad = st.selectbox("Prioridad:", ["VERDE", "AMARILLA", "ROJA"], key="ger_prioridad")
        
        if st.button("Ejecutar Directiva", key="btn_ger_directiva"):
            if g_orden.strip():
                escribir_registro_nube("CHATS", [obtener_hora_argentina(), st.session_state.user_sel, g_orden, g_prioridad, g_para, g_asunto])
                st.success("✅ Directiva Transmitida al escalafón operacional")
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
    with t_ejecucion_ger:
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            st.markdown('<div class="panel-novedad">', unsafe_allow_html=True)
            st.subheader("Alta Servicio")
            g_alta_nom = st.text_input("Nombre:", key="ger_alta_nom")
            g_alta_asig = st.selectbox("Asignar a:", LISTA_SUPS_TACTICOS, key="ger_alta_asig")
            
            if st.button("Solicitar Alta a Admin", key="btn_ger_alta"):
                if g_alta_nom.strip():
                    escribir_registro_nube("PETICIONES", [obtener_hora_argentina(), st.session_state.user_sel, "ALTA", "OBJETIVO", f"{g_alta_nom} | ASIG: {g_alta_asig}"])
                    st.success("✅ Petición de Alta enviada al Núcleo Maestro")
            st.markdown('</div>', unsafe_allow_html=True)
            
        with col_g2:
            st.markdown('<div class="panel-novedad">', unsafe_allow_html=True)
            st.subheader("Baja Servicio")
            opciones_baja = df_objetivos['OBJETIVO'].unique() if not df_objetivos.empty else ["ALFAVINIL"]
            g_baja_obj = st.selectbox("Objetivo:", opciones_baja, key="ger_baja_obj")
            if st.button("Solicitar Baja a Admin", key="btn_ger_baja"):
                escribir_registro_nube("PETICIONES", [obtener_hora_argentina(), st.session_state.user_sel, "BAJA", "OBJETIVO", g_baja_obj])
                st.success("✅ Petición de Baja enviada al Núcleo Maestro")
            st.markdown('</div>', unsafe_allow_html=True)

    with t_tab_auditoria:
        st.subheader("📡 LOCALIZACIÓN DE OBJETIVOS ACTIVOS")
        st.markdown('<div class="radar-box">', unsafe_allow_html=True)
        df_ger_maps = df_objetivos.dropna(subset=['LATITUD', 'LONGITUD']) if not df_ger_maps.empty else pd.DataFrame()
        centro = [df_ger_maps['LATITUD'].mean(), df_ger_maps['LONGITUD'].mean()] if not df_ger_maps.empty else [-34.6, -58.4]
        m_visor = folium.Map(location=centro, zoom_start=12, tiles="CartoDB dark_matter")
        if not df_ger_maps.empty:
            for _, r in df_ger_maps.iterrows():
                folium.Marker(
                    [r['LATITUD'], r['LONGITUD']], 
                    tooltip=f"OBJETIVO: {r['OBJETIVO']} | SUPERVISOR: {r.get('SUPERVISOR', 'N/A')}", 
                    icon=folium.Icon(color="blue", icon="shield", prefix="fa")
                ).add_to(m_visor)
        st_folium(m_visor, width="100%", height=450, key=f"map_fiscalizacion_{st.session_state.rol_sel}")
        st.markdown('</div>', unsafe_allow_html=True)

        st.write("---")
        st.subheader("📋 REPORTE HISTÓRICO DE MOVIMIENTOS")
        df_novedades = leer_matriz_nube("ACTAS_FLOTAS")
        if not df_novedades.empty:
            st.dataframe(df_novedades.tail(20), use_container_width=True)

# E. ROL: ADMINISTRADOR
elif st.session_state.rol_sel == "ADMINISTRADOR":
    st.markdown('<div class="titulo-seccion-admin">⚙️ NÚCLEO MAESTRO: AION-YAROKU</div>', unsafe_allow_html=True)
    
    with st.expander("🔐 CREDENCIALES DE INFRAESTRUCTURA", expanded=True):
        u_ing = st.text_input("ADMIN_USER")
        p_ing = st.text_input("ADMIN_PASS", type="password")
        
    st.markdown('<div class="titulo-seccion-admin">⚖️ BUZÓN DE PETICIONES PENDIENTES</div>', unsafe_allow_html=True)
    
    if u_ing == "admin" and p_ing == "aion2026":
        st.write("---")
        tipo = st.radio("Alta:", ["SUPERVISOR", "SERVICIO"], horizontal=True)
        nuevo_nombre = st.text_input("Nombre:").upper()
        if st.button("REGISTRAR"):
            escribir_registro_nube("ESTRUCTURA", [obtener_hora_argentina(), tipo, nuevo_nombre, "ACTIVO", st.session_state.user_sel])
            st.success("Alta Exitosa")
