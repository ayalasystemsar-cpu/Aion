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
        # Limpieza de coordenadas sin eliminar filas vacías
        df['LATITUD'] = pd.to_numeric(df['LATITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        df['LONGITUD'] = pd.to_numeric(df['LONGITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        return df # FIX CRÍTICO: Retorna la lista completa de objetivos sin descartar nada
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

# --- 5. SIDEBAR TÁCTICO (CONTROL CON LOGIN REFORZADO POR ESQUEMA ROBUSTO) ---
df_objetivos = cargar_objetivos()

LISTA_SUPS_TACTICOS = [
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
    
    # 1. MONITOREO
    if st.button("🛰️ MONITOREO", use_container_width=True):
        st.session_state.rol_sel = "MONITOREO"
        st.session_state.user_sel = "OPERADOR CENTRAL"
        st.session_state.sup_autenticado = False
        st.rerun()
        
    # 2. JEFE DE OPERACIONES
    if st.button("📋 JEFE DE OPERACIONES", use_container_width=True):
        st.session_state.rol_sel = "JEFE DE OPERACIONES"
        st.session_state.user_sel = "SANOJA LUIS"
        st.session_state.sup_autenticado = False
        st.rerun()
        
    # 3. GERENCIA
    if st.button("🏢 GERENCIA", use_container_width=True):
        st.session_state.rol_sel = "GERENCIA"
        st.session_state.user_sel = "DIRECCIÓN GENERAL"
        st.session_state.sup_autenticado = False
        st.rerun()

    # 4. SUPERVISORES
    with st.expander("👤 SUPERVISORES", expanded=(st.session_state.rol_sel == "SUPERVISOR" or 'intentando_sup' in st.session_state)):
        nom_sup = st.selectbox(
            "RESPONSABLE ACTIVO:", 
            LISTA_SUPS_TACTICOS,
            key="cambio_supervisor_directo"
        )
        
        user_sup = st.text_input("USUARIO RECURSO (APELLIDO)", key="auth_user_sup")
        pass_sup = st.text_input("CONTRASEÑA CRÍTICA", type="password", key="auth_pass_sup")
        
        if st.button("AUTENTICAR E INGRESAR", use_container_width=True):
            st.session_state.intentando_sup = True
            
            if "NOCTURNO" in nom_sup:
                usuario_esperado = "nocturno"
            else:
                usuario_esperado = nom_sup.split(" ")[1]
            
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
    
    # 5. ADMINISTRADOR
    st.markdown("**⚙️ ADMINISTRADOR**")
    if st.button("ACCEDER AL NÚCLEO MAESTRO", use_container_width=True):
        st.session_state.rol_sel = "ADMINISTRADOR"
        st.session_state.user_sel = "ADMIN CENTRAL"
        st.session_state.sup_autenticado = False
        st.rerun()

    st.write("---")
    
    loc = get_geolocation()
    lat_envio = loc['coords']['latitude'] if loc else 0.0
    lon_envio = loc['coords'].get('longitude', 0.0) if loc else 0.0

    if st.button("ACTIVAR\nPÁNICO", type="primary"):
        if st.session_state.rol_sel == "SUPERVISOR" and 'sup_servicio_actual' in st.session_state:
            obj_alerta = st.session_state.sup_servicio_actual
        else:
            obj_alerta = "CENTRAL BASE"
            
        carga_sos = f"LAT:{lat_envio}|LON:{lon_envio}|OBJ:{obj_alerta}|SUP:{st.session_state.user_sel}"
        escribir_registro_nube("ALERTAS", [obtener_hora_argentina(), st.session_state.user_sel, "PÁNICO", "PENDIENTE", carga_sos])
        st.error(f"🚨 S.O.S ENVIADO DESDE {obj_alerta}")

# --- 6. CABECERA CENTRAL ---
st.markdown('<div class="contenedor-logo-central"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" class="logo-phoenix"></div>', unsafe_allow_html=True)

if st.session_state.rol_sel == "SUPERVISOR" and not st.session_state.sup_autenticado:
    st.markdown('<div class="estacion-titulo">🔒 ESTACIÓN BLOQUEADA - REQUIERE AUTENTICACIÓN EN SIDEBAR</div>', unsafe_allow_html=True)
else:
    titulos = {
        "MONITOREO": "🛰️ CENTRAL DE INTELIGENCIA OPERATIVA",
        "SUPERVISOR": f"📱 Estación de Control: {st.session_state.user_sel}",
        "JEFE DE OPERACIONES": "📋 COMANDO DE OPERACIONES TÁCTICAS",
        "GERENCIA": "🏢 DIRECCIÓN Y FISCALIZACIÓN GENERAL",
        "ADMINISTRADOR": "⚙️ NÚCLEO MAESTRO: AION-YAROKU"
    }
    st.markdown(f'<div class="estacion-titulo">{titulos.get(st.session_state.rol_sel, "SISTEMA TÁCTICO DE COMANDO")}</div>', unsafe_allow_html=True)

# --- 7. FLUJO POR ROLES ---

# A. ROL: MONITOREO
if st.session_state.rol_sel == "MONITOREO":
    df_emergencias = leer_matriz_nube("ALERTAS")
    df_comisarias = leer_matriz_nube("COMISARIAS")
    
    if df_emergencias.empty:
        df_emergencias = pd.DataFrame(columns=['FECHA', 'USUARIO', 'TIPO', 'ESTADO', 'CARGA_UTIL', 'INFORME'])
    else:
        df_emergencias.columns = df_emergencias.columns.str.strip().str.upper()
    
    if 'ESTADO' in df_emergencias.columns:
        alertas_activas = df_emergencias[df_emergencias['ESTADO'].astype(str).str.upper() == 'PENDIENTE']
    else:
        alertas_activas = pd.DataFrame(columns=df_emergencias.columns)
        
    sos_activos = len(alertas_activas)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("🚨 S.O.S ACTIVOS", sos_activos)
    c2.metric("📡 RED", "OPERATIVA")
    c3.metric("🕒 HORA LOCAL", obtener_hora_argentina().split(" ")[1])

    t_radar, t_gestion, t_comunicacion = st.tabs(["🚨 RADAR S.O.S", "📖 LIBRO DE BASE", "💬 COMUNICACIÓN"])
    
    with t_radar:
        lat_foco, lon_foco = -34.6, -58.4
        obj_en_panico, sup_responsable = "", ""
        comisaria_cercana = None
        dist_minima = float('inf')
        
        # Filtro de objetivos con coordenadas válidas para evitar roturas de mapa en monitoreo
        df_objetivos_mapa = df_objetivos.dropna(subset=['LATITUD', 'LONGITUD']) if not df_objetivos.empty else pd.DataFrame()
        
        if sos_activos > 0 and not df_objetivos_mapa.empty:
            datos_sos = alertas_activas.iloc[-1]
            try:
                carga_util_col = 'CARGA_UTIL' if 'CARGA_UTIL' in alertas_activas.columns else alertas_activas.columns[4]
                partes = datos_sos.get(carga_util_col, '').split("|")
                obj_en_panico = partes[2].split(":")[1].strip()
                sup_responsable = partes[3].split(":")[1].strip()
                
                target_data = df_objetivos_mapa[df_objetivos_mapa['OBJETIVO'] == obj_en_panico].iloc[0]
                lat_foco = float(str(target_data['LATITUD']).replace(',','.'))
                lon_foco = float(str(target_data['LONGITUD']).replace(',','.'))

                if not df_comisarias.empty:
                    for _, com in df_comisarias.iterrows():
                        try:
                            c_lat = float(str(com.iloc[1]).replace(',','.'))
                            c_lon = float(str(com.iloc[2]).replace(',','.'))
                            
                            R = 6371.0
                            phi1, phi2 = math.radians(lat_foco), math.radians(c_lat)
                            dphi, dlambda = math.radians(c_lat-lat_foco), math.radians(c_lon-lon_foco)
                            a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
                            d = R * (2 * math.atan2(math.sqrt(a), math.sqrt(1-a)))
                            
                            if d < dist_minima:
                                dist_minima = d
                                comisaria_cercana = {"NOMBRE": com.iloc[0], "LAT": c_lat, "LON": c_lon}
                        except: continue
                
                st.error(f"🚨 EMERGENCY EN CURSO: {obj_en_panico}")
            except: pass
        else:
            st.success("✅ Vigilancia Pasiva - Radar Operativo")

        m_mon = folium.Map(location=[lat_foco, lon_foco], zoom_start=13, tiles="CartoDB dark_matter")
        map_css = "<style>@keyframes blink {0%{opacity:1;}50%{opacity:0.3;}100%{opacity:1;}} .blink-icon {animation: blink 0.8s linear infinite;}</style>"
        m_mon.get_root().header.add_child(folium.Element(map_css))

        if not df_objetivos_mapa.empty:
            for _, r in df_objetivos_mapa.iterrows():
                try:
                    r_lat, r_lon = float(str(r['LATITUD']).replace(',','.')), float(str(r['LONGITUD']).replace(',','.'))
                    es_sos = (r['OBJETIVO'] == obj_en_panico)
                    color_nodo = "red" if es_sos else "#00E5FF"
                    
                    sup_display = sup_responsable if es_sos else r.get('SUPERVISOR', 'N/A')
                    tooltip_html = f"🚨 <b>OBJ:</b> {r['OBJETIVO']}<br>👤 <b>SUP:</b> {sup_display}"

                    folium.CircleMarker(
                        location=[r_lat, r_lon], radius=8 if es_sos else 6,
                        color=color_nodo, fill=es_sos, fill_color=color_nodo, weight=3,
                        tooltip=folium.Tooltip(tooltip_html, sticky=True),
                        className="blink-icon" if es_sos else ""
                    ).add_to(m_mon)
                except: continue

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

        st.sidebar.markdown("---")
        st_folium(m_mon, width="100%", height=450, key="mapa_final_corregido_v30")

        if sos_activos > 0:
            st.markdown("---")
            st.subheader("📝 PROTOCOLO DE CIERRE")
            inf_neu = st.text_area("INFORME DE NEUTRALIZACIÓN")
            if st.button("FINALIZAR OPERATIVO", use_container_width=True):
                if inf_neu.strip():
                    fila_excel = alertas_activas.index[-1] + 2
                    actualizar_celda("ALERTAS", fila_excel, "D", "RESUELTO")
                    actualizar_celda("ALERTAS", fila_excel, "F", inf_neu)
                    st.success("✅ Operativo Finalizado")
                    st.rerun()

    with t_gestion:
        st.subheader("📖 HISTORIAL DE OPERATIVOS")
        if not df_emergencias.empty:
            st.dataframe(df_emergencias.iloc[::-1], use_container_width=True)
        else:
            st.info("No hay registros en el historial.")

    with t_comunicacion:
        st.markdown('<h3>📥 BANDEJA DE INTELIGENCIA</h3>', unsafe_allow_html=True)
        df_chats = leer_matriz_nube("CHATS")
        
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)
        if not df_chats.empty:
            for _, msg in df_chats.tail(10).iloc[::-1].iterrows():
                es_rojo = msg.get("PRIORIDAD", "VERDE") == "ROJA"
                clase_info = "message-info-red" if es_rojo else "message-info"
                clase_box = "message-box-red" if es_rojo else "message-box"
                
                msg_hora = msg.get("HORA")
                msg_usuario = msg.get("USUARIO")
                msg_texto = msg.get("TEXTO")
                
                html_msg = (
                    f'<div class="{clase_box}">'
                    f'<div class="{clase_info}">{msg_hora} De: {msg_usuario}</div>'
                    f'<div class="message-text">{msg_texto}</div>'
                    f'</div>'
                )
                st.markdown(html_msg, unsafe_allow_html=True)
        else:
            st.info("Sin comunicaciones registradas en la bandeja.")
        st.markdown('</div>', unsafe_allow_html=True)
        
        with st.expander("📩 REDACTAR COMUNICACIÓN", expanded=True):
            c_para = st.selectbox("Para:", ["TODOS"] + LISTA_SUPS_TACTICOS)
            c_asunto = st.text_input("Asunto:")
            c_mensaje = st.text_area("Mensaje:")
            c_prioridad = st.selectbox("Prioridad:", ["VERDE", "AMARILLA", "ROJA"])
            
            if st.button("TRANSMITIR", key="btn_transmitir_mon"):
                if c_mensaje.strip():
                    escribir_registro_nube("CHATS", [obtener_hora_argentina(), st.session_state.user_sel, c_mensaje, c_prioridad, c_para, c_asunto])
                    st.success("✅ Comunicación Transmitida con Éxito")
                    st.rerun()

# B. ROL: JEFE DE OPERACIONES
elif st.session_state.rol_sel == "JEFE DE OPERACIONES":
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🚨 S.O.S ACTIVOS", "0")
    col2.metric("📡 RED", "OPERATIVA")
    col3.metric("👤 USUARIO", f"{st.session_state.user_sel}")
    col4.metric("🕒 HORA LOCAL", obtener_hora_argentina().split(" ")[1])

    t_crisis, t_ejecucion, t_auditoria = st.tabs(["Centro de Crisis", "Ejecución", "Auditoría"])
    
    with t_crisis:
        st.subheader("📡 RADAR Y LOCALIZACIÓN DE
