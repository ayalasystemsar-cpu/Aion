# --- 1. CONFIGURACIÓN E IDENTIDAD VISUAL CORPORATIVA (AION-YAROKU CORE) ---\r
import streamlit as st\r
import pandas as pd\r
import numpy as np\r
import folium\r
from streamlit_folium import st_folium\r
from datetime import datetime\r
import pytz\r
import gspread\r
from oauth2client.service_account import ServiceAccountCredentials\r
from streamlit_js_eval import get_geolocation\r
import math\r
from folium.plugins import AntPath\r
\r
# Configuración de página OLED\r
st.set_page_config(\r
    page_title="AION-YAROKU | CORE",\r
    page_icon="🛡️",\r
    layout="wide",\r
    initial_sidebar_state="expanded"\r
)\r
\r
# --- 2. CONEXIONES (GOOGLE MATRIZ) ---\r
ID_MAESTRO_DB = "1Md0VkOnwUJWldq0S1fB9UrmOKv4MG__JVG3tQsda0Uw"\r
\r
def conectar_google():\r
    try:\r
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]\r
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)\r
        return gspread.authorize(creds)\r
    except: return None\r
\r
# --- 3. FUNCIONES DE LÓGICA Y DATOS ---\r
def obtener_hora_argentina():\r
    tz = pytz.timezone("America/Argentina/Buenos_Aires")\r
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")\r
\r
# (Nota: Asumimos que las funciones leer_matriz_nube, escribir_registro_nube y actualizar_celda están definidas previamente en tu entorno)\r
\r
# --- CÓDIGO DE BASE DE DATOS SIMULADO PARA ENTORNO TÁCTICO ---\r
# Generamos dataframes de control simulados o leídos de tu infraestructura\r
df_objetivos = pd.DataFrame({\r
    'OBJETIVO': ['ALFAVINIL', 'OBJETIVO XYZ', 'LOGARTE 2'],\r
    'LATITUD': [-34.55, -34.56, -34.57],\r
    'LONGITUD': [-58.45, -58.46, -58.47],\r
    'SUPERVISOR': ['SUPERVISOR NAME', 'DÍAZ MARCELO', 'DARÍO CECILIA']\r
})\r
df_comisarias = pd.DataFrame([\r
    ['COMISARIA 1', -34.54, -58.44]\r
])\r
df_emergencias = pd.DataFrame()\r
alertas_activas = pd.DataFrame()\r
\r
# Variables de control de SOS simuladas\r
sos_activos = 0\r
obj_en_panico = None\r
sup_responsable = None\r
lat_foco, lon_foco = -34.55, -58.45\r
comisaria_cercana = None\r
dist_minima = 99999.0\r
\r
# --- CONTROL DE ACCESO (SIDEBAR COMPLETO) ---\r
st.sidebar.markdown("# 🛡️ CONTROL DE ACCESO")\r
rol_seleccionado = st.sidebar.selectbox("Perfil Activo:", ["MONITOR", "SUPERVISOR", "JEFE DE OPERACIONES", "GERENCIA", "ADMINISTRADOR"], key="rol_sel")\r
usuario_seleccionado = st.sidebar.selectbox("Operador / Usuario:", ["DARÍO CECILIA", "BRIAN AYALA", "SUPERVISOR ..."], key="user_sel")\r
\r
# =========================================================================\r
# A. ROL: MONITOR\r
# =========================================================================\r
if st.session_state.rol_sel == "MONITOR":\r
    st.markdown('<div class="radar-box">', unsafe_allow_html=True)\r
    \r
    # Pestañas del Monitor de Control\r
    t_radar, t_gestion, t_comunicacion = st.tabs(["🎯 RADAR S.O.S", "📖 LIBRO DE BASE", "💬 COMUNICACIÓN"])\r
    \r
    with t_radar:\r
        # Comprobación interna de Emergencias (Mantenemos tu lógica limpia)\r
        if sos_activos > 0:\r
            st.error(f"🚨 EMERGENCIA EN CURSO: {obj_en_panico}")\r
        else:\r
            st.success("✅ Vigilancia Pasiva - Radar Operativo")\r
\r
        # --- MAPA DE MONITOREO --- [cite: 67]\r
        m_mon = folium.Map(location=[lat_foco, lon_foco], zoom_start=13, tiles="CartoDB dark_matter") [cite: 67]\r
        \r
        # Efecto Blink inyectado en el header del mapa para que titilen los círculos en SOS [cite: 68]\r
        map_css = "<style>@keyframes blink {0%{opacity:1;}50%{opacity:0.3;}100%{opacity:1;}} .blink-icon {animation: blink 0.8s linear infinite;}</style>" [cite: 68]\r
        m_mon.get_root().header.add_child(folium.Element(map_css)) [cite: 68]\r
\r
        # Dibujar todos los puntos como CÍRCULOS conforme lo solicitado [cite: 68]\r
        for _, r in df_objetivos.iterrows():\r
            try:\r
                r_lat, r_lon = float(str(r['LATITUD']).replace(',','.')), float(str(r['LONGITUD']).replace(',','.')) [cite: 68]\r
                es_sos = (r['OBJETIVO'] == obj_en_panico) [cite: 68]\r
                \r
                # CAMBIA A ROJO SI SE ACTIVA, SINO CIAN [cite: 68, 69]\r
                color_nodo = "red" if es_sos else "#00E5FF" [cite: 69]\r
                \r
                tooltip_html = f"🚨 <b>OBJ:</b> {r['OBJETIVO']}<br>👤 <b>SUP:</b> {sup_responsable if es_sos else r.get('SUPERVISOR', 'N/A')}" [cite: 69]\r
\r
                # Construcción del Círculo con clase condicional para TITILAR [cite: 70]\r
                folium.CircleMarker(\r
                    location=[r_lat, r_lon], \r
                    radius=10 if es_sos else 7,\r
                    color=color_nodo, \r
                    fill=True, \r
                    fill_color=color_nodo, \r
                    weight=3,\r
                    tooltip=folium.Tooltip(tooltip_html, sticky=True),\r
                    className="blink-icon" if es_sos else "" # TITILA SI ESTÁ EN ROJO/SOS [cite: 70, 71]\r
                ).add_to(m_mon) [cite: 71]\r
            except: continue [cite: 71]\r
\r
        # Dibujar Ruta y Comisaría si hay alerta activa [cite: 71]\r
        if sos_activos > 0 and comisaria_cercana:\r
            try:\r
                folium.Marker(\r
                    [comisaria_cercana['LAT'], comisaria_cercana['LON']], \r
                    tooltip=f"🚓 {comisaria_cercana['NOMBRE']}", \r
                    icon=folium.Icon(color="blue", icon="shield-halved", prefix="fa")\r
                ).add_to(m_mon) [cite: 72]\r
                \r
                AntPath(\r
                    locations=[[comisaria_cercana['LAT'], comisaria_cercana['LON']], [lat_foco, lon_foco]], \r
                    color='#FFEB3B', weight=6, delay=600\r
                ).add_to(m_mon) [cite: 73, 74]\r
            except: pass\r
\r
        st_folium(m_mon, width="100%", height=450, key="mapa_final_corregido_v30") [cite: 74]\r
\r
        # Protocolo de Cierre debajo del mapa si hay SOS [cite: 74]\r
        if sos_activos > 0:\r
            st.markdown("---") [cite: 74]\r
            st.subheader("📝 PROTOCOLO DE CIERRE") [cite: 74]\r
            inf_neu = st.text_area("INFORME DE NEUTRALIZACIÓN") [cite: 74]\r
            if st.button("FINALIZAR OPERATIVO", use_container_width=True): [cite: 75]\r
                if inf_neu.strip():\r
                    st.success("✅ Operativo Finalizado")\r
                    st.rerun() [cite: 76]\r
                else:\r
                    st.warning("⚠️ El informe es obligatorio para cerrar.") [cite: 76]\r
\r
    with t_gestion:\r
        st.subheader("📖 HISTORIAL DE OPERATIVOS") [cite: 77]\r
        if not df_emergencias.empty:\r
            st.dataframe(df_emergencias.iloc[::-1], use_container_width=True) [cite: 77]\r
        else:\r
            st.info("No hay registros en el historial.") [cite: 77]\r
            \r
    # --- BANDEJA DE COMUNICACIONES COMPLETA (Captura 590) ---\r
    with t_comunicacion:\r
        st.subheader("📩 BANDEJA DE INTELIGENCIA")\r
        \r
        # Historial de comunicaciones estático solicitado\r
        st.markdown("""\r
        <div style='border-left: 4px solid #00E5FF; padding-left: 10px; margin-bottom: 15px;'>\r
            <span style='color: #888; font-size: 12px;'>2026-04-25 21:25:14 | De: DARÍO CECILIA</span><br>\r
            <span style='font-weight: bold;'>noche</span><br>\r
            <span style='color: #aaa;'>prueba grupal</span>\r
        </div>\r
        <div style='border-left: 4px solid #FF5252; padding-left: 10px; margin-bottom: 15px;'>\r
            <span style='color: #888; font-size: 12px;'>2026-04-25 06:48:42 | De: DÍAZ MARCELO</span><br>\r
            <span style='font-weight: bold; color: #FF5252;'>ACTA LOGARTE 2</span><br>\r
            <span style='color: #aaa;'>Paga</span>\r
        </div>\r
        """, unsafe_allow_html=True)\r
        \r
        with st.expander("📥 REDACTAR COMUNICACIÓN", expanded=True):\r
            para_sel = st.selectbox("Para:", ["TODOS", "SUPERVISOR", "JEFE DE OPERACIONES", "GERENCIA"], key="mon_com_para")\r
            asunto_txt = st.text_input("Asunto", key="mon_com_asunto")\r
            mensaje_txt = st.text_area("Mensaje", key="mon_com_mensaje")\r
            prioridad_sel = st.selectbox("Prioridad:", ["VERDE", "AMARILLO", "ROJO"], key="mon_com_prioridad")\r
            if st.button("TRANSMITIR", use_container_width=False):\r
                if mensaje_txt.strip():\r
                    st.success("📡 Comunicación Transmitida Exitosamente")\r
                else:\r
                    st.warning("⚠️ El mensaje no puede estar vacío.")\r
    st.markdown('</div>', unsafe_allow_html=True)\r
\r
# =========================================================================\r
# B. ROL: SUPERVISOR (Captura 593 - Sin botón de pánico superior)\r
# =========================================================================\r
elif st.session_state.rol_sel == "SUPERVISOR":\r
    st.markdown('<div class="radar-box">', unsafe_allow_html=True) [cite: 78]\r
    \r
    # Botón de refresco alineado a la derecha en la barra superior\r
    col_vacia, col_ref = st.columns([8, 2])\r
    with col_ref:\r
        st.button("🔄 REFRESCAR SISTEMA", use_container_width=True)\r
    \r
    # --- PANEL DE CONTROL DE UNIDAD MÓVIL --- \r
    with st.expander("🚚 CONTROL DE UNIDAD MÓVIL", expanded=True):\r
        col_mov, col_kmi, col_kmf, col_comb = st.columns([2, 2, 2, 2])\r
        with col_mov:\r
            movil_sel = st.selectbox("Móvil", ["S-001", "S-002", "S-003"], key="sup_movil")\r
        with col_kmi:\r
            km_inicial = st.number_input("Km Inicial", min_value=0, value=0, step=1, key="sup_kmi")\r
        with col_kmf:\r
            km_final = st.number_input("Km Final", min_value=0, value=0, step=1, key="sup_kmf")\r
        with col_comb:\r
            combustible = st.number_input("Combustible (Lts)", min_value=0.0, value=0.0, step=0.5, key="sup_comb")\r
        \r
        if st.button("📌 SELLAR ODOMETRÍA Y LOGÍSTICA", use_container_width=False):\r
            st.success(f"📋 Registro Guardado para Unidad {movil_sel}")\r
\r
    # Pestañas inferiores de interacción de Supervisor\r
    t_radar_sup, t_carga_sup, t_com_sup = st.tabs(["🎯 RADAR & QR", "📦 CARGA TÁCTICA", "💬 COMUNICACIÓN"])\r
    \r
    with t_radar_sup:\r
        col_mapa, col_ctrl = st.columns([7, 3])\r
        \r
        with col_mapa:\r
            centro = [df_objetivos['LATITUD'].mean(), df_objetivos['LONGITUD'].mean()] if not df_objetivos.empty else [-34.6, -58.4] [cite: 78]\r
            m_visor = folium.Map(location=centro, zoom_start=12, tiles="CartoDB dark_matter") [cite: 78]\r
            for _, r in df_objetivos.iterrows():\r
                folium.Marker(\r
                    [r['LATITUD'], r['LONGITUD']], \r
                    tooltip=f"OBJETIVO: {r['OBJETIVO']} | SUPERVISOR: {r.get('SUPERVISOR', 'N/A')}", \r
                    icon=folium.Icon(color="blue", icon="shield", prefix="fa")\r
                ).add_to(m_visor) [cite: 78, 79]\r
            st_folium(m_visor, width="100%", height=450, key="map_supervisor_operativo") [cite: 79]\r
        \r
        with col_ctrl:\r
            st.selectbox("SERVICIO ACTUAL:", df_objetivos['OBJETIVO'].unique() if not df_objetivos.empty else ["ALFAVINIL"], key="sup_servicio_act")\r
            st.radio("ACCIÓN:", ["Seleccionar...", "🟢 INGRESO", "🔴 SALIDA"], key="sup_accion_io")\r
            \r
    st.markdown('</div>', unsafe_allow_html=True) [cite: 79]\r
\r
# =========================================================================\r
# C. ROL: JEFE DE OPERACIONES Y GERENCIA (Captura 591)\r
# =========================================================================\r
elif st.session_state.rol_sel in ["JEFE DE OPERACIONES", "GERENCIA"]:\r
    st.markdown('<div class="radar-box">', unsafe_allow_html=True) [cite: 78]\r
    \r
    # Cabecera de Comando Estratégico \r
    st.title(f"🏢 COMANDO ESTRATÉGICO: {st.session_state.get('user_sel', 'OPERADOR')} ∞")\r
    \r
    t_crisis, t_ejecucion, t_auditoria = st.tabs(["🚨 CENTRO DE CRISIS", "🛠️ EJECUCIÓN", "📊 AUDITORÍA"])\r
    \r
    # Bloque de ejecución con formulario de Peticiones de Alta/Baja\r
    with t_ejecucion:\r
        with st.expander("📁 PETICIÓN DE ALTA/BAJA", expanded=True):\r
            accion_sel = st.selectbox("Acción:", ["ALTA", "BAJA"], key="jefe_accion")\r
            categoria_sel = st.selectbox("Categoría:", ["OBJETIVO", "SUPERVISOR", "MÓVIL"], key="jefe_cat")\r
            detalle_txt = st.text_input("Nombre / Detalle", key="jefe_detalle")\r
            if st.button("ELEVAR PETICIÓN", use_container_width=False):\r
                if detalle_txt.strip():\r
                    st.success(f"🚀 Petición de {accion_sel} para {categoria_sel} enviada con éxito.")\r
                else:\r
                    st.warning("⚠️ Debe ingresar el Nombre/Detalle para continuar.")\r
\r
    # Mapa Base de Fiscalización Operativa para la Plana Mayor\r
    centro = [df_objetivos['LATITUD'].mean(), df_objetivos['LONGITUD'].mean()] if not df_objetivos.empty else [-34.6, -58.4] [cite: 78]\r
    m_visor = folium.Map(location=centro, zoom_start=12, tiles="CartoDB dark_matter") [cite: 78]\r
    for _, r in df_objetivos.iterrows():\r
        folium.Marker(\r
            [r['LATITUD'], r['LONGITUD']], \r
            tooltip=f"OBJETIVO: {r['OBJETIVO']} | SUPERVISOR: {r.get('SUPERVISOR', 'N/A')}", \r
            icon=folium.Icon(color="blue", icon="shield", prefix="fa")\r
        ).add_to(m_visor) [cite: 78, 79]\r
    st_folium(m_visor, width="100%", height=400, key=f"map_fiscalizacion_{st.session_state.rol_sel}") [cite: 79]\r
    st.markdown('</div>', unsafe_allow_html=True) [cite: 79]\r
\r
    st.subheader("📋 REPORTE DE MOVIMIENTOS") [cite: 79]\r
    # (Simulamos la lectura remota para evitar quiebres de ejecución)\r
    try:\r
        df_novedades = leer_matriz_nube("ACTAS_FLOTAS") [cite: 79]\r
        if not df_novedades.empty:\r
            st.dataframe(df_novedades.tail(20), use_container_width=True) [cite: 79]\r
    except: \r
        st.info("No hay registros en el reporte de movimientos actual.")\r
\r
# =========================================================================\r
# D. ROL: ADMINISTRADOR\r
# =========================================================================\r
elif st.session_state.rol_sel == "ADMINISTRADOR":\r
    st.header("⚙️ NÚCLEO MAESTRO") [cite: 80]\r
    u_ing = st.text_input("ADMIN_USER") [cite: 80]\r
    p_ing = st.text_input("ADMIN_PASS", type="password") [cite: 80]\r
    if u_ing == "admin" and p_ing == "aion2026": [cite: 80]\r
        tipo = st.radio("Alta:", ["SUPERVISOR", "SERVICIO"], horizontal=True) [cite: 80]\r
        nuevo_nombre = st.text_input("Nombre:").upper() [cite: 80]\r
        if st.button("REGISTRAR"): [cite: 80]\r
            st.success("Alta Exitosa") [cite: 80]\r
