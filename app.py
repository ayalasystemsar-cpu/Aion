import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from datetime import datetime
import numpy as np
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from streamlit_js_eval import get_geolocation

# --- 1. CONFIGURACIÓN E IDENTIDAD VISUAL CORPORATIVA (AION-YAROKU CORE) ---
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
    import pytz
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
        df.columns = df.columns.str.replace('DIRECCIÓN', 'DIRECCION')
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

        .gerencia-tarjeta-peticion {
            border: 1px solid #1a1a1b;
            border-radius: 6px;
            padding: 15px;
            margin-top: 10px;
            margin-bottom: 5px;
            background: rgba(5, 5, 8, 0.95);
        }
        .gerencia-txt-titulo {
            color: #00e5ff;
            font-family: 'Orbitron', sans-serif;
            font-size: 14px;
            font-weight: bold;
            letter-spacing: 1px;
        }
        .gerencia-txt-detalle {
            color: #dcdcdc;
            font-family: 'Rajdhani', sans-serif;
            font-size: 14px;
            margin-top: 4px;
        }
        </style>
        """, unsafe_allow_html=True
    )

aplicar_identidad_alfa()

# --- 5. SIDEBAR TÁCTICO ---
df_objetivos = cargar_objetivos()

if 'rol_sel' not in st.session_state: st.session_state.rol_sel = "MONITOREO"
if 'user_sel' not in st.session_state: st.session_state.user_sel = "BRIAN AYALA"

with st.sidebar:
    st.markdown('<div class="contenedor-logo-sidebar"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" style="width:180px; border:1px solid #00e5ff; border-radius:4px;"></div>', unsafe_allow_html=True)
    st.subheader("🛡️ PANEL DE CONTROL")
    st.session_state.rol_sel = st.selectbox("NIVEL DE ACCESO", ["SUPERVISOR", "MONITOREO", "JEFE DE OPERACIONES", "GERENCIA", "ADMINISTRADOR"], index=["SUPERVISOR", "MONITOREO", "JEFE DE OPERACIONES", "GERENCIA", "ADMINISTRADOR"].index(st.session_state.rol_sel))
    st.session_state.user_sel = st.selectbox("IDENTIDAD OPERATIVA", ["BRIAN AYALA", "SANOJA LUIS", "DARÍO CECILIA", "LUIS BONGIORNO", "SERANTES WALTER", "MAZACOTTE CLAUDIO", "SUPERVISOR NOCTURNO"])
    
    st.write("---")
    st.markdown("**🚨 CONFIGURACIÓN DE EMERGENCIA**")
    obj_panico = st.selectbox("🎯 SELECCIONAR OBJETIVO", df_objetivos['OBJETIVO'].unique() if not df_objetivos.empty else ["N/A"])
    sup_panico = st.selectbox("👤 SUPERVISOR DE ZONA", ["BRIAN AYALA", "GONZALO PORZIO", "SUPERVISOR NOCTURNO", "OTRO"])
    
    loc = get_geolocation()
    lat_envio = loc['coords']['latitude'] if loc else 0.0
    lon_envio = loc['coords'].get('longitude', 0.0) if loc else 0.0

    if st.button("ACTIVAR\nPÁNICO", type="primary"):
        carga_sos = f"LAT:{lat_envio}|LON:{lon_envio}|OBJ:{obj_panico}|SUP:{sup_panico}"
        escribir_registro_nube("ALERTAS", [obtener_hora_argentina(), st.session_state.user_sel, "PÁNICO", "PENDIENTE", carga_sos])
        st.error(f"🚨 S.O.S ENVIADO: {obj_panico}")

# --- 6. CABECERA CENTRAL ---
st.markdown('<div class="contenedor-logo-central"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" class="logo-phoenix"></div>', unsafe_allow_html=True)

titulos = {
    "MONITOREO": "🛰️ CENTRAL DE INTELIGENCIA OPERATIVA",
    "SUPERVISOR": f"📱 Estación de Control: {st.session_state.user_sel}",
    "JEFE DE OPERACIONES": "📋 COMANDO DE OPERACIONES TÁCTICAS",
    "GERENCIA": "🏢 DIRECCIÓN Y FISCALIZACIÓN GENERAL",
    "ADMINISTRADOR": "⚙️ NÚCLEO MAESTRO"
}
st.markdown(f'<div class="estacion-titulo">{titulos.get(st.session_state.rol_sel, "SISTEMA TÁCTICO DE COMANDO")}</div>', unsafe_allow_html=True)

# --- 7. FLUJO POR ROLES ---

# A. ROL: MONITOREO
if st.session_state.rol_sel == "MONITOREO":
    from folium.plugins import AntPath
    import math

    df_emergencias = leer_matriz_nube("ALERTAS")
    df_comisarias = leer_matriz_nube("COMISARIAS")
    alertas_activas = df_emergencias[df_emergencias['ESTADO'].astype(str).str.upper() == 'PENDIENTE']
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
        
        if sos_activos > 0:
            datos_sos = alertas_activas.iloc[-1]
            try:
                partes = datos_sos.get('CARGA_UTIL', '').split("|")
                obj_en_panico = partes[2].split(":")[1].strip()
                sup_responsable = partes[3].split(":")[1].strip()
                target_data = df_objetivos[df_objetivos['OBJETIVO'] == obj_en_panico].iloc[0]
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

        for _, r in df_objetivos.iterrows():
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

    with t_comunicacion:
        st.subheader("📥 BANDEJA DE INTELIGENCIA")
        df_chats = leer_matriz_nube("CHATS")
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)
        if not df_chats.empty:
            for _, msg in df_chats.tail(10).iloc[::-1].iterrows():
                es_rojo = msg.get("PRIORIDAD", "VERDE") == "ROJA"
                clase_info = "message-info-red" if es_rojo else "message-info"
                clase_box = "message-box-red" if es_rojo else "message-box"
                st.markdown(f'<div class="{clase_box}"><div class="{clase_info}">{msg.get("HORA")} De: {msg.get("USUARIO")}</div><div class="message-text">{msg.get("TEXTO")}</div></div>', unsafe_allow_html=True)
        st.sidebar.markdown('</div>', unsafe_allow_html=True)
        
        with st.expander("📩 REDACTAR COMUNICACIÓN", expanded=True):
            c_para = st.selectbox("Para:", ["TODOS", "BRIAN AYALA", "SANOJA LUIS", "DARÍO CECILIA", "LUIS BONGIORNO", "SUPERVISOR NOCTURNO"])
            c_asunto = st.text_input("Asunto:")
            c_mensaje = st.text_area("Mensaje:")
            c_prioridad = st.selectbox("Prioridad:", ["VERDE", "AMARILLA", "ROJA"])
            if st.button("TRANSMITIR", key="btn_transmitir_mon"):
                if c_mensaje.strip():
                    escribir_registro_nube("CHATS", [obtener_hora_argentina(), st.session_state.user_sel, c_mensaje, c_prioridad, c_para, c_asunto])
                    st.success("✅ Comunicación Transmitida")
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
        st.subheader("📡 RADAR Y LOCALIZACIÓN DE OBJETIVOS")
        st.markdown('<div class="radar-box">', unsafe_allow_html=True)
        centro = [df_objetivos['LATITUD'].mean(), df_objetivos['LONGITUD'].mean()] if not df_objetivos.empty else [-34.6, -58.4]
        m_visor = folium.Map(location=centro, zoom_start=12, tiles="CartoDB dark_matter")
        for _, r in df_objetivos.iterrows():
            folium.Marker([r['LATITUD'], r['LONGITUD']], tooltip=f"OBJETIVO: {r['OBJETIVO']}").add_to(m_visor)
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
                st.success("✅ Petición Elevada")
        st.markdown('</div>', unsafe_allow_html=True)

    st.write("---")
    st.subheader("📋 REPORTE DE MOVIMIENTOS")
    df_novedades = leer_matriz_nube("ACTAS_FLOTAS")
    if not df_novedades.empty:
        st.dataframe(df_novedades.tail(20), use_container_width=True)

# C. ROL: SUPERVISOR
elif st.session_state.rol_sel == "SUPERVISOR":
    st.subheader("Control de Unidad Móvil")
    st.markdown('<div class="panel-info">', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    with c1: s_movil = st.selectbox("Móvil:", ["S-001", "M-002", "M-003", "OTRO"])
    with c2: s_km_inicial = st.number_input("Km Inicial:", value=0, step=1)
    with c3: s_km_final = st.number_input("Km Final:", value=0, step=1)
    with c4: s_combustible = st.number_input("Combustible (Lts):", value=0.0, step=0.1)
    st.markdown('</div>', unsafe_allow_html=True)
    
    col_btn1, col_btn2 = st.columns([3, 1])
    with col_btn1: st.button("SELLAR ODOMETRÍA Y LOGÍSTICA", use_container_width=True)
    with col_btn2:
        if st.button("REFRESCR SISTEMA"): st.rerun()

    t_visita_qr, t_carga_tactica, t_comunicacion_sup = st.tabs(["Visita QR", "Carga Táctica", "Comunicación"])
    with t_visita_qr:
        opciones_servicios = df_objetivos['OBJETIVO'].unique() if not df_objetivos.empty else ["ALFAVINIL"]
        st.selectbox("SERVICIO ACTUAL:", opciones_servicios)
        st.radio("ACCIÓN:", ["SELECCIONAR...", "INGRESO", "SALIDA"], index=0, horizontal=True)
        st.write("---")
        st.markdown('<div class="radar-box">', unsafe_allow_html=True)
        centro = [df_objetivos['LATITUD'].mean(), df_objetivos['LONGITUD'].mean()] if not df_objetivos.empty else [-34.6, -58.4]
        m_visor = folium.Map(location=centro, zoom_start=12, tiles="CartoDB dark_matter")
        for _, r in df_objetivos.iterrows():
            folium.Marker([r['LATITUD'], r['LONGITUD']], tooltip=f"OBJETIVO: {r['OBJETIVO']}").add_to(m_visor)
        st_folium(m_visor, width="100%", height=500, key=f"map_supervisor_exclusivo_visita_qr")
        st.markdown('</div>', unsafe_allow_html=True)
        
    with t_carga_tactica:
        st.markdown('<div class="panel-novedad">', unsafe_allow_html=True)
        novedad_sup = st.text_area("Novedad / Registro Operativo:")
        if st.button("CARGAR REGISTRO"):
            if novedad_sup.strip():
                escribir_registro_nube("NOVEDADES", [obtener_hora_argentina(), st.session_state.user_sel, novedad_sup])
                st.success("✅ Registro cargado")
        st.markdown('</div>', unsafe_allow_html=True)
        
    with t_comunicacion_sup:
        df_chats_sup = leer_matriz_nube("CHATS")
        if not df_chats_sup.empty: st.dataframe(df_chats_sup.tail(10), use_container_width=True)

# D. ROL: GERENCIA (DISEÑO MODIFICADO DE MANERA EXACTA E IDÉNTICA A LA CAPTURA 594)
elif st.session_state.rol_sel == "GERENCIA":
    with st.container():
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("💰 AHORRO RIESGO", "$ 1.200.000")
        m2.metric("📊 NIVEL COBERTURA", "47/93")
        m3.metric("📋 AUDITORIAS", "2")
        m4.metric("🚗 DESGASTE", "4954 Km")

    st.write("---")

    t_com_est, t_ejecucion, t_auditoria = st.tabs(["Comunicación Estratégica", "Ejecución", "Tablero de Auditoría"])
    
    with t_com_est:
        st.markdown('<div class="panel-novedad">', unsafe_allow_html=True)
        st.subheader("📢 EMISIÓN DE DIRECTIVAS GENERALES")
        g_asunto = st.text_input("Asunto de la Directiva:", key="ger_asunto_core")
        g_directiva = st.text_area("Cuerpo de la instrucción corporativa:", key="ger_dir_core")
        if st.button("TRANSMITIR DIRECTIVA", key="ger_btn_trans_core"):
            if g_directiva.strip():
                escribir_registro_nube("CHATS", [obtener_hora_argentina(), st.session_state.user_sel, g_directiva, "ROJA", "TODOS", g_asunto])
                st.success("✅ Directiva Transmitida con Éxito")
        st.markdown('</div>', unsafe_allow_html=True)
        
    with t_ejecucion:
        # Pestaña Ejecución Oficial: Formularios nativos de Alta/Baja y Directivas unificadas (Imagen 594)
        c1, c2 = st.columns(2)
        with c1:
            with st.form("alta_gerencia"):
                st.write("Alta Servicio")
                n = st.text_input("Nombre")
                s = st.selectbox("Asignar a:", lista_sups)
                if st.form_submit_button("Solicitar Alta a Admin"): 
                    escribir_registro_nube("PETICIONES", [str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")), usuario_auth, "ALTA", f"{n} | {s}", "PENDIENTE", "OBJETIVO"])
                    st.success("Solicitud de Alta registrada.")
        with c2:
            with st.form("baja_gerencia"):
                st.write("Baja Servicio")
                rem = st.selectbox("Objetivo:", df_objetivos['OBJETIVO'].unique() if not df_objetivos.empty else ["N/A"])
                if st.form_submit_button("Solicitar Baja a Admin"): 
                    escribir_registro_nube("PETICIONES", [str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")), usuario_auth, "BAJA", rem, "PENDIENTE", "OBJETIVO"])
                    st.success("Solicitud de Baja registrada.")
                    
        with st.form("orden_gerencia"):
            st.write("Transmitir Directiva (Push a Celulares)")
            dest_dir = st.selectbox("Para:", ["TODOS", "LUIS BONGIORNO", "DARÍO CECILIA"] + lista_sups)
            asunto_dir = st.text_input("Asunto")
            msg_dir = st.text_area("Orden")
            prioridad_dir = st.selectbox("Prioridad", ["VERDE", "AMARILLO", "ROJO"])
            if st.form_submit_button("Ejecutar Directiva"): 
                escribir_registro_nube("MENSAJERIA", [str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")), usuario_auth, dest_dir, asunto_dir, msg_dir, "ENVIADO", prioridad_dir])
                st.success("Directiva inyectada en la red con éxito.")

    with t_auditoria:
        st.subheader("📋 TABLERO DE AUDITORÍA DE OBJETIVOS")
        if not df_objetivos.empty:
            df_display = df_objetivos[['OBJETIVO', 'DIRECCION', 'SUPERVISOR']]
            st.dataframe(df_display, use_container_width=True)

# E. ROL: ADMINISTRADOR
elif st.session_state.rol_sel == "ADMINISTRADOR":
    st.header("⚙️ NÚCLEO MAESTRO")
    u_ing = st.text_input("ADMIN_USER")
    p_ing = st.text_input("ADMIN_PASS", type="password")
    if u_ing == "admin" and p_ing == "aion2026":
        t_infra, t_estruc = st.tabs(["Infraestructura", "Estructura Base"])
        with t_infra:
            st.text_input("GOOGLE SHEET ID MASTER:", value=ID_MAESTRO_DB, disabled=True)
            st.success("📡 Sincronización en la nube con Google Drive API: ACTIVA")
        with t_estruc:
            tipo = st.radio("Alta:", ["SUPERVISOR", "SERVICIO"], horizontal=True)
            nuevo_nombre = st.text_input("Nombre:").upper()
            if st.button("REGISTRAR"):
                escribir_registro_nube("ESTRUCTURA", [obtener_hora_argentina(), tipo, nuevo_nombre, "ACTIVO", st.session_state.user_sel])
                st.success("Alta Exitosa")
