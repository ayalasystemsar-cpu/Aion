import streamlit as st
import datetime
from datetime import datetime
import pandas as pd
import pytz
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from streamlit_js_eval import get_geolocation
import folium
from folium.plugins import AntPath
from streamlit_folium import st_folium
import math

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="AION-YAROKU | CORE",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CONEXIONES ---
ID_MAESTRO_DB = "1Md0VkOnwUJWldq0S1fB9UrmOKv4MG__JVG3tQsda0Uw"

def conectar_google():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        return gspread.authorize(creds)
    except: return None

# --- 3. LÓGICA Y DATOS ---
def obtener_hora_argentina():
    tz = pytz.timezone("America/Argentina/Buenos_Aires")
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

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
            return pd.DataFrame(data) if data else pd.DataFrame()
        except: return pd.DataFrame()
    return pd.DataFrame()

@st.cache_data(ttl=60)
def cargar_objetivos():
    df = leer_matriz_nube("OBJETIVOS")
    if not df.empty:
        df.columns = df.columns.str.strip().str.upper()
        df = df[df['OBJETIVO'].astype(str).str.strip() != ""]
        if 'SUPERVISOR' in df.columns:
            df['SUPERVISOR'] = df['SUPERVISOR'].astype(str).str.strip().str.upper()
        df['LATITUD'] = pd.to_numeric(df['LATITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        df['LONGITUD'] = pd.to_numeric(df['LONGITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        return df
    return pd.DataFrame()

# --- 4. IDENTIDAD VISUAL ---
def aplicar_identidad_alfa():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@300;500;700&display=swap');
        .stApp { background: radial-gradient(circle at top, #0A0F1E 0%, #030305 100%) !important; color: #E0E0E0; font-family: 'Rajdhani', sans-serif; }
        .estacion-titulo { font-family: 'Orbitron', sans-serif; color: #00E5FF !important; font-size: 24px; text-align: center; margin-top: 15px; }
        .panel-novedad { border: 1px solid #333; border-radius: 8px; padding: 15px; margin-top: 20px; background-color: rgba(10, 10, 11, 0.9); }
        .titulo-seccion-admin { color: #00E5FF; font-family: 'Orbitron', sans-serif; font-size: 22px; font-weight: bold; margin: 25px 0 15px; }
        </style>
    """, unsafe_allow_html=True)

aplicar_identidad_alfa()
df_objetivos = cargar_objetivos()

# --- 5. SIDEBAR ---
if 'rol_sel' not in st.session_state: st.session_state.rol_sel = "MONITOREO"
if 'user_sel' not in st.session_state: st.session_state.user_sel = "OPERADOR CENTRAL"
if 'sup_autenticado' not in st.session_state: st.session_state.sup_autenticado = False

with st.sidebar:
    st.markdown("### PANEL DE CONTROL")
    if st.button("🛰️ MONITOREO"): st.session_state.rol_sel = "MONITOREO"; st.rerun()
    if st.button("📋 JEFE DE OPERACIONES"): st.session_state.rol_sel = "JEFE DE OPERACIONES"; st.rerun()
    if st.button("🏢 GERENCIA"): st.session_state.rol_sel = "GERENCIA"; st.rerun()
    if st.button("👤 SUPERVISOR"): st.session_state.rol_sel = "SUPERVISOR"; st.rerun()
    if st.button("🛡️ VIGILADOR"): st.session_state.rol_sel = "VIGILADOR"; st.rerun()
    if st.button("⚙️ ADMINISTRADOR"): st.session_state.rol_sel = "ADMINISTRADOR"; st.rerun()

# --- 6. FLUJO POR ROLES ---
if st.session_state.rol_sel == "MONITOREO":
    st.markdown('<div class="estacion-titulo">🛰️ CENTRAL DE INTELIGENCIA OPERATIVA</div>', unsafe_allow_html=True)
    # A. ROL: MONITOREO
if st.session_state.rol_sel == "MONITOREO":
    df_emergencias = leer_matriz_nube("ALERTAS")
    df_comisarias = leer_matriz_nube("COMISARIAS")
    
    if df_emergencias.empty:
        df_emergencias = pd.DataFrame(columns=['FECHA', 'USUARIO', 'TIPO', 'ESTADO', 'CARGA_UTIL', 'INFORME'])
    else:
        df_emergencias.columns = df_emergencias.columns.str.strip().str.upper()
    
    sos_activos = len(df_emergencias[df_emergencias['ESTADO'].astype(str).str.upper() == 'PENDIENTE']) if 'ESTADO' in df_emergencias.columns else 0
    
    c1, c2, c3 = st.columns(3)
    c1.metric("🚨 S.O.S ACTIVOS", sos_activos)
    c2.metric("📡 RED", "OPERATIVA")
    c3.metric("🕒 HORA LOCAL", obtener_hora_argentina().split(" ")[1])

    # Definición de las pestañas
    t_radar, t_gestion, t_comunicacion, t_pres = st.tabs(["🚨 RADAR S.O.S", "📖 LIBRO DE BASE", "💬 COMUNICACIÓN", "📋 PRESENTISMO"])
    
    with t_radar:
        st.subheader("📡 RADAR GLOBAL DE OBJETIVOS")
        
        # 1. Preparación del mapa: Limpieza de coordenadas nulas
        df_mapa = df_objetivos.dropna(subset=['LATITUD', 'LONGITUD']).copy()
        
        if not df_mapa.empty:
            # Centro del mapa basado en el promedio de coordenadas
            centro_mapa = [df_mapa['LATITUD'].mean(), df_mapa['LONGITUD'].mean()]
            m_mon = folium.Map(location=centro_mapa, zoom_start=11, tiles="CartoDB dark_matter")
            
            # 2. Iteración para dibujar cada objetivo
            for _, r in df_mapa.iterrows():
                info_hover = f"OBJETIVO: {r['OBJETIVO']} | SUP: {r.get('SUPERVISOR', 'N/A')}"
                folium.CircleMarker(
                    location=[r['LATITUD'], r['LONGITUD']], 
                    radius=8,
                    color="#00E5FF", 
                    fill=True, 
                    fill_color="#00E5FF",
                    tooltip=folium.Tooltip(info_hover, sticky=True)
                ).add_to(m_mon)
            
            # 3. Renderizado en Streamlit
            st_folium(m_mon, width="100%", height=550, key="mapa_radar_operativo")
        else:
            st.warning("⚠️ No hay objetivos con coordenadas válidas para desplegar en el radar.")

    with t_gestion:
        st.subheader("📖 HISTORIAL DE OPERATIVOS")
        if not df_emergencias.empty: 
            st.dataframe(df_emergencias.iloc[::-1], use_container_width=True)
        else: 
            st.info("No hay registros en el historial.")

    with t_comunicacion:
        st.markdown('<h3>📥 BANDEJA DE INTELIGENCIA</h3>', unsafe_allow_html=True)
        df_chats = leer_matriz_nube("CHATS")
        if not df_chats.empty:
            for _, msg in df_chats.tail(10).iloc[::-1].iterrows():
                es_rojo = msg.get("PRIORIDAD", "VERDE") == "ROJA"
                st.markdown(f'<div class="{"message-box-red" if es_rojo else "message-box"}"><div class="{"message-info-red" if es_rojo else "message-info"}">{msg.get("HORA")} De: {msg.get("USUARIO")}</div><div class="message-text">{msg.get("TEXTO")}</div></div>', unsafe_allow_html=True)
        else:
            st.info("Sin comunicaciones.")

    with t_pres:
        st.subheader("📋 REGISTRO DE PRESENTISMO (TOTAL)")
        df_pres = leer_matriz_nube("PRESENTISMO")
        if not df_pres.empty:
            st.dataframe(df_pres.sort_values(by="FECHA", ascending=False), use_container_width=True)
        else:
            st.info("No hay registros de presentismo.")

elif st.session_state.rol_sel == "JEFE DE OPERACIONES":
    st.markdown('<div class="estacion-titulo">📋 COMANDO DE OPERACIONES TÁCTICAS</div>', unsafe_allow_html=True)
# C. ROL: JEFE DE OPERACIONES
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
        
        # 1. Definir el DataFrame primero
        df_obj_maps_jefe = df_objetivos.dropna(subset=['LATITUD', 'LONGITUD'])
        
        # 2. Calcular centro solo si el DataFrame tiene datos
        if not df_obj_maps_jefe.empty:
            centro = [df_obj_maps_jefe['LATITUD'].mean(), df_obj_maps_jefe['LONGITUD'].mean()]
        else:
            centro = [-34.6, -58.4]
            
        m_visor = folium.Map(location=centro, zoom_start=12, tiles="CartoDB dark_matter")
        
        # 3. Dibujar marcadores si el DataFrame no está vacío
        if not df_obj_maps_jefe.empty:
            for _, r in df_obj_maps_jefe.iterrows():
                folium.Marker(
                    [r['LATITUD'], r['LONGITUD']], 
                    tooltip=f"OBJETIVO: {r['OBJETIVO']} | SUPERVISOR: {r.get('SUPERVISOR', 'N/A')}", 
                    icon=folium.Icon(color="blue", icon="shield", prefix="fa")
                ).add_to(m_visor)
        
        st_folium(m_visor, width="100%", height=500, key="map_jefe_operaciones_crisis")
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

elif st.session_state.rol_sel == "SUPERVISOR":
    st.markdown('<div class="estacion-titulo">📱 ESTACIÓN DE CONTROL</div>', unsafe_allow_html=True)
    # D. ROL: SUPERVISOR (FILTRADO PERIMETRAL EXACTO Y MAPAS CON CENTRO DINÁMICO)
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

        # AQUÍ AGREGUÉ LA PESTAÑA DE PRESENTISMO
        t_vis_qr, t_car_tac, t_com_sup, t_pres_sup = st.tabs(["Visita QR", "Carga Táctica", "Comunicación", "📋 PRESENTISMO"])
        
        with t_vis_qr:
            if not df_objetivos_filtrados.empty:
                opciones_servicios = df_objetivos_filtrados['OBJETIVO'].unique()
            else:
                opciones_servicios = ["SIN OBJETIVOS ASIGNADOS"]
            
            st.selectbox("SERVICIO ACTUAL:", opciones_servicios, key="sup_servicio_actual")
            st.radio("ACCIÓN:", ["SELECCIONAR...", "INGRESO", "SALIDA"], index=0, key="sup_radio_accion", horizontal=True)
            
            st.write("---")
            st.subheader("📡 RADAR Y LOCALIZACIÓN DE OBJETIVOS ASIGNADOS")
            st.markdown('<div class="radar-box">', unsafe_allow_html=True)
            
            # Limpieza y renderizado táctico
            df_mapa_sup = df_objetivos_filtrados.dropna(subset=['LATITUD', 'LONGITUD']).copy()
            df_mapa_sup['LATITUD'] = pd.to_numeric(df_mapa_sup['LATITUD'].astype(str).str.replace(',', '.'), errors='coerce')
            df_mapa_sup['LONGITUD'] = pd.to_numeric(df_mapa_sup['LONGITUD'].astype(str).str.replace(',', '.'), errors='coerce')
            df_mapa_sup = df_mapa_sup.dropna(subset=['LATITUD', 'LONGITUD'])
            
            if not df_mapa_sup.empty:
                centro_coordenadas = [df_mapa_sup['LATITUD'].mean(), df_mapa_sup['LONGITUD'].mean()]
                m_visor = folium.Map(location=centro_coordenadas, zoom_start=12, tiles="CartoDB dark_matter")
                for _, r in df_mapa_sup.iterrows():
                    folium.Marker([r['LATITUD'], r['LONGITUD']], tooltip=r['OBJETIVO'], icon=folium.Icon(color="blue", icon="shield", prefix="fa")).add_to(m_visor)
            else:
                m_visor = folium.Map(location=[-34.6037, -58.3816], zoom_start=12, tiles="CartoDB dark_matter")
            
            st_folium(m_visor, width="100%", height=500, key=f"map_visor_sup_dinamico_{sup_activo_normalizado}")
            st.markdown('</div>', unsafe_allow_html=True)
            
        with t_car_tac:
            st.markdown('<div class="panel-novedad">', unsafe_allow_html=True)
            st.subheader("📋 CARGA DE REGISTROS TÁCTICOS")
            novedad_sup = st.text_area("Novedad / Registro Operativo:", key="texto_novedad_supervisor")
            if st.button("CARGAR REGISTRO", key="btn_cargar_registro_sup"):
                if novedad_sup.strip():
                    escribir_registro_nube("NOVEDADES", [obtener_hora_argentina(), st.session_state.user_sel, novedad_sup])
                    st.success("✅ Registro cargado")
            st.markdown('</div>', unsafe_allow_html=True)
            
        with t_com_sup:
            st.subheader("Bandeja de Novedades del Sector")
            df_chats_sup = leer_matriz_nube("CHATS")
            if not df_chats_sup.empty:
                st.dataframe(df_chats_sup.tail(10), use_container_width=True)

        # NUEVA PESTAÑA PRESENTISMO PARA SUPERVISOR
        with t_pres_sup:
            st.subheader(f"📋 PRESENTISMO: {st.session_state.user_sel}")
            df_p = leer_matriz_nube("PRESENTISMO")
            if not df_p.empty:
                st.dataframe(df_p.sort_values(by="FECHA", ascending=False), use_container_width=True)
            else:
                st.info("Sin registros.")

# --- C. ROL: VIGILADOR (INTEGRADO) ---
elif st.session_state.rol_sel == "VIGILADOR":
    st.markdown('<div class="panel-novedad">', unsafe_allow_html=True)
    st.header("🛡️ TERMINAL OPERATIVO: VIGILADOR")
    opciones_globales_obj = df_objetivos['OBJETIVO'].unique() if not df_objetivos.empty else ["ALFAVINIL", "BARRIO EL CAMPO"]
    
    tab_pres, tab_rev = st.tabs(["📍 FICHAJE BIOMÉTRICO", "🔄 CAMBIO DE GUARDIA"])
    
    with tab_pres:
        with st.form(key="form_fichaje_vigilador", clear_on_submit=True):
            v_ape = st.text_input("APELLIDO Y NOMBRE:").upper().strip()
            v_dni = st.text_input("DNI / LEGAJO:").strip()
            v_obj = st.selectbox("OBJETIVO:", opciones_globales_obj)
            v_tipo = st.selectbox("TIPO:", ["INGRESO", "EGRESO"])
            img = st.camera_input("RECONOCIMIENTO FACIAL")
            
            if st.form_submit_button("CONSIGNAR PRESENTE"):
                if v_ape and img and v_dni:
                    df_match = df_objetivos[df_objetivos['OBJETIVO'] == v_obj]
                    sup_resp = df_match['SUPERVISOR'].values[0] if not df_match.empty else "NO ASIGNADO"
                    fh = obtener_hora_argentina()
                    if escribir_registro_nube("PRESENTISMO", [fh.split(" ")[0], fh.split(" ")[1], v_dni, f"{v_ape} - {v_obj}", "", "OK", v_tipo]):
                        escribir_registro_nube("NOVEDADES_GUARDIA", [fh, v_obj, v_dni, f"FACIAL_{v_tipo}", f"OP: {v_ape}", sup_resp])
                        st.success("✅ REGISTRADO")
                else: st.warning("⚠️ Faltan datos o captura facial.")

    with tab_rev:
        with st.form(key="form_relevo", clear_on_submit=True):
            v_obj_rel = st.selectbox("OBJETIVO RELEVO:", opciones_globales_obj)
            v_sal = st.text_input("SALE:").upper().strip()
            v_ent = st.text_input("ENTRA:").upper().strip()
            
            if st.form_submit_button("SANCIONAR RELEVO"):
                if v_sal and v_ent:
                    fh = obtener_hora_argentina()
                    sup_resp = df_objetivos[df_objetivos['OBJETIVO'] == v_obj_rel]['SUPERVISOR'].iloc[0] if not df_objetivos[df_objetivos['OBJETIVO'] == v_obj_rel].empty else "NO ASIGNADO"
                    if escribir_registro_nube("VIGILADORES", [fh.split(" ")[0], fh.split(" ")[1], v_obj_rel, v_sal, v_ent, sup_resp, "RELEVO"]):
                        escribir_registro_nube("NOVEDADES_GUARDIA", [fh, v_obj_rel, "RELEVO", "CAMBIO_GUARDIA", f"S:{v_sal}|E:{v_ent}", sup_resp])
                        st.success("🔄 RELEVO SANCIONADO")
    st.markdown('</div>', unsafe_allow_html=True)

elif st.session_state.rol_sel == "GERENCIA":
    # E. ROL: GERENCIA
elif st.session_state.rol_sel == "GERENCIA":
    st.markdown('<h2 style="color:#00E5FF; font-family:\'Orbitron\', sans-serif; font-size:24px; margin-bottom:5px;">Comando Estratégico: DIRECCIÓN GENERAL</h2>', unsafe_allow_html=True)
    st.markdown('<h3 style="color:#FFFFFF; font-family:\'Rajdhani\', sans-serif; font-size:18px; margin-top:0px; margin-bottom:20px;">Panel de Rentabilidad Operativa</h3>', unsafe_allow_html=True)
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Ahorro de Riesgo (Estimado)", "$ 1.200.000")
    m2.metric("Nivel de Cobertura", "47/93")
    m3.metric("Auditorías Físicas (QRs)", "2")
    m4.metric("Desgaste Flota (Km)", "4954 Km")
    
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
                st.success("✅ Directiva Transmitida")
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
    with t_ejecucion_ger:
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.markdown('<div class="panel-novedad">', unsafe_allow_html=True)
            st.subheader("Alta Servicio")
            g_alta_nom = st.text_input("Nombre:", key="ger_alta_nom")
            g_alta_asig = st.selectbox("Asignar a:", LISTA_SUPS_TACTICOS, key="ger_alta_asig")
            if st.button("Solicitar Alta", key="btn_ger_alta"):
                escribir_registro_nube("PETICIONES", [obtener_hora_argentina(), st.session_state.user_sel, "ALTA", "OBJETIVO", f"{g_alta_nom} | ASIG: {g_alta_asig}"])
                st.success("✅ Petición enviada")
            st.markdown('</div>', unsafe_allow_html=True)
        with col_g2:
            st.markdown('<div class="panel-novedad">', unsafe_allow_html=True)
            st.subheader("Baja Servicio")
            opciones_baja = df_objetivos['OBJETIVO'].unique() if not df_objetivos.empty else ["ALFAVINIL"]
            g_baja_obj = st.selectbox("Objetivo:", opciones_baja, key="ger_baja_obj")
            if st.button("Solicitar Baja", key="btn_ger_baja"):
                escribir_registro_nube("PETICIONES", [obtener_hora_argentina(), st.session_state.user_sel, "BAJA", "OBJETIVO", g_baja_obj])
                st.success("✅ Petición enviada")
            st.markdown('</div>', unsafe_allow_html=True)

    with t_tab_auditoria:
        st.subheader("📡 LOCALIZACIÓN DE OBJETIVOS ACTIVOS")
        # 1. Definición sin validación recursiva
        df_ger_maps = df_objetivos.dropna(subset=['LATITUD', 'LONGITUD'])
        
        # 2. Lógica de centro separada
        centro = [df_ger_maps['LATITUD'].mean(), df_ger_maps['LONGITUD'].mean()] if not df_ger_maps.empty else [-34.6, -58.4]
        m_visor = folium.Map(location=centro, zoom_start=12, tiles="CartoDB dark_matter")
        
        # 3. Marcadores
        for _, r in df_ger_maps.iterrows():
            folium.Marker([r['LATITUD'], r['LONGITUD']], tooltip=r['OBJETIVO'], icon=folium.Icon(color="blue", icon="shield", prefix="fa")).add_to(m_visor)
            
        st_folium(m_visor, width="100%", height=450, key="map_gerencia")
        
        st.write("---")
        st.subheader("📋 REPORTE HISTÓRICO DE MOVIMIENTOS")
        df_novedades = leer_matriz_nube("ACTAS_FLOTAS")
        if not df_novedades.empty:
            st.dataframe(df_novedades.tail(20), use_container_width=True)

elif st.session_state.rol_sel == "ADMINISTRADOR":
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
