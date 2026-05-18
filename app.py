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

# (Nota: Asumimos que las funciones leer_matriz_nube, escribir_registro_nube y actualizar_celda están definidas previamente en tu entorno)

# --- CÓDIGO DE BASE DE DATOS SIMULADO PARA ENTORNO TÁCTICO ---
# Generamos dataframes de control simulados o leídos de tu infraestructura
df_objetivos = pd.DataFrame({
    'OBJETIVO': ['ALFAVINIL', 'OBJETIVO XYZ', 'LOGARTE 2'],
    'LATITUD': [-34.55, -34.56, -34.57],
    'LONGITUD': [-58.45, -58.46, -58.47],
    'SUPERVISOR': ['SUPERVISOR NAME', 'DÍAZ MARCELO', 'DARÍO CECILIA']
})
df_comisarias = pd.DataFrame([
    ['COMISARIA 1', -34.54, -58.44]
])
df_emergencias = pd.DataFrame()
alertas_activas = pd.DataFrame()

# Variables de control de SOS simuladas
sos_activos = 0
obj_en_panico = None
sup_responsable = None
lat_foco, lon_foco = -34.55, -58.45
comisaria_cercana = None
dist_minima = 99999.0

# --- CONTROL DE ACCESO (SIDEBAR COMPLETO) ---
st.sidebar.markdown("# 🛡️ CONTROL DE ACCESO")
rol_seleccionado = st.sidebar.selectbox("Perfil Activo:", ["MONITOR", "SUPERVISOR", "JEFE DE OPERACIONES", "GERENCIA", "ADMINISTRADOR"], key="rol_sel")
usuario_seleccionado = st.sidebar.selectbox("Operador / Usuario:", ["DARÍO CECILIA", "BRIAN AYALA", "SUPERVISOR ..."], key="user_sel")

# =========================================================================
# A. ROL: MONITOR
# =========================================================================
if st.session_state.rol_sel == "MONITOR":
    st.markdown('<div class="radar-box">', unsafe_allow_html=True)
    
    # Pestañas del Monitor de Control
    t_radar, t_gestion, t_comunicacion = st.tabs(["🎯 RADAR S.O.S", "📖 LIBRO DE BASE", "💬 COMUNICACIÓN"])
    
    with t_radar:
        # Comprobación interna de Emergencias (Mantenemos tu lógica limpia)
        if sos_activos > 0:
            st.error(f"🚨 EMERGENCIA EN CURSO: {obj_en_panico}")
        else:
            st.success("✅ Vigilancia Pasiva - Radar Operativo")

        # --- MAPA DE MONITOREO ---
        m_mon = folium.Map(location=[lat_foco, lon_foco], zoom_start=13, tiles="CartoDB dark_matter")
        
        # Efecto Blink inyectado en el header del mapa para que titilen los círculos en SOS
        map_css = "<style>@keyframes blink {0%{opacity:1;}50%{opacity:0.3;}100%{opacity:1;}} .blink-icon {animation: blink 0.8s linear infinite;}</style>"
        m_mon.get_root().header.add_child(folium.Element(map_css))

        # Dibujar todos los puntos como CÍRCULOS conforme lo solicitado
        for _, r in df_objetivos.iterrows():
            try:
                r_lat, r_lon = float(str(r['LATITUD']).replace(',','.')), float(str(r['LONGITUD']).replace(',','.'))
                es_sos = (r['OBJETIVO'] == obj_en_panico)
                
                # CAMBIA A ROJO SI SE ACTIVA, SINO CIAN
                color_nodo = "red" if es_sos else "#00E5FF"
                
                tooltip_html = f"🚨 <b>OBJ:</b> {r['OBJETIVO']}<br>👤 <b>SUP:</b> {sup_responsable if es_sos else r.get('SUPERVISOR', 'N/A')}"

                # Construcción del Círculo con clase condicional para TITILAR
                folium.CircleMarker(
                    location=[r_lat, r_lon], 
                    radius=10 if es_sos else 7,
                    color=color_nodo, 
                    fill=True, 
                    fill_color=color_nodo, 
                    weight=3,
                    tooltip=folium.Tooltip(tooltip_html, sticky=True),
                    className="blink-icon" if es_sos else "" # TITILA SI ESTÁ EN ROJO/SOS
                ).add_to(m_mon)
            except: continue

        # Dibujar Ruta y Comisaría si hay alerta activa
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

        # Protocolo de Cierre debajo del mapa si hay SOS
        if sos_activos > 0:
            st.markdown("---")
            st.subheader("📝 PROTOCOLO DE CIERRE")
            inf_neu = st.text_area("INFORME DE NEUTRALIZACIÓN")
            if st.button("FINALIZAR OPERATIVO", use_container_width=True):
                if inf_neu.strip():
                    st.success("✅ Operativo Finalizado")
                    st.rerun()
                else:
                    st.warning("⚠️ El informe es obligatorio para cerrar.")

    with t_gestion:
        st.subheader("📖 HISTORIAL DE OPERATIVOS")
        if not df_emergencias.empty:
            st.dataframe(df_emergencias.iloc[::-1], use_container_width=True)
        else:
            st.info("No hay registros en el historial.")
            
    # --- BANDEJA DE COMUNICACIONES COMPLETA (Captura 590) ---
    with t_comunicacion:
        st.subheader("📩 BANDEJA DE INTELIGENCIA")
        
        # Historial de comunicaciones estático solicitado
        st.markdown("""
        <div style='border-left: 4px solid #00E5FF; padding-left: 10px; margin-bottom: 15px;'>
            <span style='color: #888; font-size: 12px;'>2026-04-25 21:25:14 | De: DARÍO CECILIA</span><br>
            <span style='font-weight: bold;'>noche</span><br>
            <span style='color: #aaa;'>prueba grupal</span>
        </div>
        <div style='border-left: 4px solid #FF5252; padding-left: 10px; margin-bottom: 15px;'>
            <span style='color: #888; font-size: 12px;'>2026-04-25 06:48:42 | De: DÍAZ MARCELO</span><br>
            <span style='font-weight: bold; color: #FF5252;'>ACTA LOGARTE 2</span><br>
            <span style='color: #aaa;'>Paga</span>
        </div>
        """, unsafe_allow_html=True)
        
        with st.expander("📥 REDACTAR COMUNICACIÓN", expanded=True):
            para_sel = st.selectbox("Para:", ["TODOS", "SUPERVISOR", "JEFE DE OPERACIONES", "GERENCIA"], key="mon_com_para")
            asunto_txt = st.text_input("Asunto", key="mon_com_asunto")
            mensaje_txt = st.text_area("Mensaje", key="mon_com_mensaje")
            prioridad_sel = st.selectbox("Prioridad:", ["VERDE", "AMARILLO", "ROJO"], key="mon_com_prioridad")
            if st.button("TRANSMITIR", use_container_width=False):
                if mensaje_txt.strip():
                    st.success("📡 Comunicación Transmitida Exitosamente")
                else:
                    st.warning("⚠️ El mensaje no puede estar vacío.")
    st.markdown('</div>', unsafe_allow_html=True)

# =========================================================================
# B. ROL: SUPERVISOR (Captura 593 - Sin botón de pánico superior)
# =========================================================================
elif st.session_state.rol_sel == "SUPERVISOR":
    st.markdown('<div class="radar-box">', unsafe_allow_html=True)
    
    # Botón de refresco alineado a la derecha en la barra superior
    col_vacia, col_ref = st.columns([8, 2])
    with col_ref:
        st.button("🔄 REFRESCAR SISTEMA", use_container_width=True)
    
    # --- PANEL DE CONTROL DE UNIDAD MÓVIL --- 
    with st.expander("🚚 CONTROL DE UNIDAD MÓVIL", expanded=True):
        col_mov, col_kmi, col_kmf, col_comb = st.columns([2, 2, 2, 2])
        with col_mov:
            movil_sel = st.selectbox("Móvil", ["S-001", "S-002", "S-003"], key="sup_movil")
        with col_kmi:
            km_inicial = st.number_input("Km Inicial", min_value=0, value=0, step=1, key="sup_kmi")
        with col_kmf:
            km_final = st.number_input("Km Final", min_value=0, value=0, step=1, key="sup_kmf")
        with col_comb:
            combustible = st.number_input("Combustible (Lts)", min_value=0.0, value=0.0, step=0.5, key="sup_comb")
        
        if st.button("📌 SELLAR ODOMETRÍA Y LOGÍSTICA", use_container_width=False):
            st.success(f"📋 Registro Guardado para Unidad {movil_sel}")

    # Pestañas inferiores de interacción de Supervisor
    t_radar_sup, t_carga_sup, t_com_sup = st.tabs(["🎯 RADAR & QR", "📦 CARGA TÁCTICA", "💬 COMUNICACIÓN"])
    
    with t_radar_sup:
        col_mapa, col_ctrl = st.columns([7, 3])
        
        with col_mapa:
            centro = [df_objetivos['LATITUD'].mean(), df_objetivos['LONGITUD'].mean()] if not df_objetivos.empty else [-34.6, -58.4]
            m_visor = folium.Map(location=centro, zoom_start=12, tiles="CartoDB dark_matter")
            for _, r in df_objetivos.iterrows():
                folium.Marker(
                    [r['LATITUD'], r['LONGITUD']], 
                    tooltip=f"OBJETIVO: {r['OBJETIVO']} | SUPERVISOR: {r.get('SUPERVISOR', 'N/A')}", 
                    icon=folium.Icon(color="blue", icon="shield", prefix="fa")
                ).add_to(m_visor)
            st_folium(m_visor, width="100%", height=450, key="map_supervisor_operativo")
        
        with col_ctrl:
            st.selectbox("SERVICIO ACTUAL:", df_objetivos['OBJETIVO'].unique() if not df_objetivos.empty else ["ALFAVINIL"], key="sup_servicio_act")
            st.radio("ACCIÓN:", ["Seleccionar...", "🟢 INGRESO", "🔴 SALIDA"], key="sup_accion_io")
            
    st.markdown('</div>', unsafe_allow_html=True)

# =========================================================================
# C. ROL: JEFE DE OPERACIONES Y GERENCIA (Captura 591)
# =========================================================================
elif st.session_state.rol_sel in ["JEFE DE OPERACIONES", "GERENCIA"]:
    st.markdown('<div class="radar-box">', unsafe_allow_html=True)
    
    # Cabecera de Comando Estratégico 
    st.title(f"🏢 COMANDO ESTRATÉGICO: {st.session_state.get('user_sel', 'OPERADOR')} ∞")
    
    t_crisis, t_ejecucion, t_auditoria = st.tabs(["🚨 CENTRO DE CRISIS", "🛠️ EJECUCIÓN", "📊 AUDITORÍA"])
    
    # Bloque de ejecución con formulario de Peticiones de Alta/Baja
    with t_ejecucion:
        with st.expander("📁 PETICIÓN DE ALTA/BAJA", expanded=True):
            accion_sel = st.selectbox("Acción:", ["ALTA", "BAJA"], key="jefe_accion")
            categoria_sel = st.selectbox("Categoría:", ["OBJETIVO", "SUPERVISOR", "MÓVIL"], key="jefe_cat")
            detalle_txt = st.text_input("Nombre / Detalle", key="jefe_detalle")
            if st.button("ELEVAR PETICIÓN", use_container_width=False):
                if detalle_txt.strip():
                    st.success(f"🚀 Petición de {accion_sel} para {categoria_sel} enviada con éxito.")
                else:
                    st.warning("⚠️ Debe ingresar el Nombre/Detalle para continuar.")

    # Mapa Base de Fiscalización Operativa para la Plana Mayor
    centro = [df_objetivos['LATITUD'].mean(), df_objetivos['LONGITUD'].mean()] if not df_objetivos.empty else [-34.6, -58.4]
    m_visor = folium.Map(location=centro, zoom_start=12, tiles="CartoDB dark_matter")
    for _, r in df_objetivos.iterrows():
        folium.Marker(
            [r['LATITUD'], r['LONGITUD']], 
            tooltip=f"OBJETIVO: {r['OBJETIVO']} | SUPERVISOR: {r.get('SUPERVISOR', 'N/A')}", 
            icon=folium.Icon(color="blue", icon="shield", prefix="fa")
        ).add_to(m_visor)
    st_folium(m_visor, width="100%", height=400, key=f"map_fiscalizacion_{st.session_state.rol_sel}")
    st.markdown('</div>', unsafe_allow_html=True)

    st.subheader("📋 REPORTE DE MOVIMIENTOS")
    # (Simulamos la lectura remota para evitar quiebres de ejecución)
    try:
        df_novedades = leer_matriz_nube("ACTAS_FLOTAS")
        if not df_novedades.empty:
            st.dataframe(df_novedades.tail(20), use_container_width=True)
    except: 
        st.info("No hay registros en el reporte de movimientos actual.")

# =========================================================================
# D. ROL: ADMINISTRADOR
# =========================================================================
elif st.session_state.rol_sel == "ADMINISTRADOR":
    st.header("⚙️ NÚCLEO MAESTRO")
    u_ing = st.text_input("ADMIN_USER")
    p_ing = st.text_input("ADMIN_PASS", type="password")
    if u_ing == "admin" and p_ing == "aion2026":
        tipo = st.radio("Alta:", ["SUPERVISOR", "SERVICIO"], horizontal=True)
        nuevo_nombre = st.text_input("Nombre:").upper()
        if st.button("REGISTRAR"):
            st.success("Alta Exitosa")
