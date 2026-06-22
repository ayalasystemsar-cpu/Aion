import streamlit as st
import datetime
from datetime import datetime
import pandas as pd
import pytz
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from streamlit_js_eval import get_geolocation
import osmnx as ox
import networkx as nx
import folium
from streamlit_folium import st_folium
import math
import requests
from branca.element import Element

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="AION-YAROKU | CORE", page_icon="🛡️", layout="wide")

ID_MAESTRO_DB = "1Md0VkOnwUJWldq0S1fB9UrmOKv4MG__JVG3tQsda0Uw"

# --- CONEXIONES ---
def conectar_google():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        return gspread.authorize(creds)
    except: return None

# --- LÓGICA DE DATOS ---
def obtener_hora_argentina():
    tz = pytz.timezone("America/Argentina/Buenos_Aires")
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

@st.cache_data(ttl=60)
def leer_matriz_nube(pestana):
    gc = conectar_google()
    if gc:
        try:
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
            todas_filas = hoja.get_all_values()
            if not todas_filas: return pd.DataFrame()
            encabezados = [str(h).strip().upper() for h in todas_filas[0]]
            df = pd.DataFrame(todas_filas[1:], columns=encabezados)
            df.columns = [str(c).strip().upper() for c in df.columns]
            return df.loc[:, ~df.columns.duplicated()]
        except: return pd.DataFrame()
    return pd.DataFrame()

def escribir_registro_nube(pestana, datos_fila):
    gc = conectar_google()
    if gc:
        hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
        hoja.append_row(datos_fila)

# --- IDENTIDAD VISUAL ---
st.markdown("""<style>
    .stApp { background: radial-gradient(circle at top, #0A0F1E 0%, #030305 100%) !important; color: #E0E0E0; font-family: 'Rajdhani', sans-serif; }
    .estacion-titulo { color: #00E5FF !important; font-size: 24px; text-align: center; font-family: 'Orbitron'; }
</style>""", unsafe_allow_html=True)

# --- SIDEBAR TÁCTICO ---
if 'rol_sel' not in st.session_state: st.session_state.rol_sel = "MONITOREO"
with st.sidebar:
    if st.button("🛰️ MONITOREO"): st.session_state.rol_sel = "MONITOREO"; st.rerun()
    if st.button("👤 SUPERVISOR"): st.session_state.rol_sel = "SUPERVISOR"; st.rerun()
    if st.button("👮 VIGILADOR"): st.session_state.rol_sel = "VIGILADOR"; st.rerun()

# --- FLUJO PRINCIPAL ---
if st.session_state.rol_sel == "MONITOREO":
    t_radar, t_chat, t_vig, t_nov = st.tabs(["🚨 RADAR", "💬 CHAT", "👥 PADRÓN", "🔄 NOVEDADES Y FICHAJES"])
    
    with t_nov:
        st.subheader("🔄 HISTORIAL: NOVEDADES Y RELEVOS")
        df_nov = leer_matriz_nube("NOVEDADES_GUARDIA")
        if not df_nov.empty:
            st.dataframe(df_nov.sort_index(ascending=False), use_container_width=True)
        else:
            st.warning("No se encontraron registros en NOVEDADES_GUARDIA.")

elif st.session_state.rol_sel == "SUPERVISOR":
    # Autenticación rápida para ejemplo
    st.session_state.sup_autenticado = True # Simplificado para test
    if st.session_state.sup_autenticado:
        t_qr, t_gps, t_tac, t_chat, t_pres = st.tabs(["QR", "GPS", "Carga", "Chat", "📋 NOVEDADES Y RELEVOS"])
        
        with t_pres:
            st.subheader("📋 NOVEDADES DE MI GRUPO")
            df_v = leer_matriz_nube("NOVEDADES_GUARDIA")
            if not df_v.empty:
                # Filtrado por Supervisor
                sup_act = st.session_state.get("user_sel", "").strip().upper()
                if 'SUPERVISOR_ASIGNADO' in df_v.columns:
                    mask = df_v['SUPERVISOR_ASIGNADO'].astype(str).str.strip().str.upper() == sup_act
                    df_filtrado = df_v[mask]
                    st.dataframe(df_filtrado, use_container_width=True)
                else:
                    st.error("Columna 'SUPERVISOR_ASIGNADO' no encontrada en Sheet.")
            else:
                st.info("No hay datos cargados.")

elif st.session_state.rol_sel == "VIGILADOR":
    tab1, tab2 = st.tabs(["📋 FICHAJE (PRESENTISMO)", "🔄 RELEVO"])
    # [Resto de lógica de vigilancia...]

    # Asegúrate de que esta línea esté a 4 espacios
    with tab_presentismo:
        st.markdown("### 📸 REGISTRO BIOMÉTRICO DE INGRESO")
        with st.form(key="form_fichaje_vigilador", clear_on_submit=True):
            v_apellido = st.text_input("APELLIDO Y NOMBRE COMPLETO:").upper().strip()
            v_dni = st.text_input("DNI / LEGAJO:").strip()
            v_obj = st.selectbox("OBJETIVO DE PRESENTISMO:", opciones_globales_obj, key="obj_pres_vig")
            v_tipo_marcacion = st.selectbox("TIPO DE MARCACIÓN:", ["INGRESO", "EGRESO"], key="tipo_marc_vig")
            img_facial = st.camera_input("RECONOCIMIENTO FACIAL COMPULSORIO")
            btn_fichar = st.form_submit_button("CONSIGNAR PRESENTE Y TRANSMITIR")
            
            if btn_fichar:
                if v_apellido and img_facial and v_dni:
                    df_match = df_objetivos[df_objetivos['OBJETIVO'] == v_obj]
                    sup_responsable = df_match['SUPERVISOR'].values[0] if not df_match.empty else "NO ASIGNADO"
                    
                    fecha_hora_arg = obtener_hora_argentina()
                    fecha_hoy = fecha_hora_arg.split(" ")[0]
                    hora_hoy = fecha_hora_arg.split(" ")[1]
                    
                    # 1. Registro en PRESENTISMO
                    datos_presentismo = [fecha_hoy, hora_hoy, v_dni, f"{v_apellido} - {v_obj}", "", "OK_SISTEMA", v_tipo_marcacion]
                    exito_pres = escribir_registro_nube("PRESENTISMO", datos_presentismo)
                    
                    # 2. Registro en NOVEDADES_GUARDIA (Alineado a 8 columnas)
                    datos_novedad_fichaje = [
                       fecha_hora_arg,           # A: FECHA
                       v_obj,                    # B: OBJETIVO
                        f"FACIAL_{v_tipo_marcacion}", # C: TIPO_EVENTO
                        v_apellido,               # D: VIGILADOR_SALE
                        "N/A",                    # E: VIGILADOR_ENTRA
                        v_dni,                    # F: DNI/LEGAJO
                        "PROCESADO",              # G: ESTADO
                        sup_responsable           # H: SUPERVISOR_ASIGNADO
                    ]
                    escribir_registro_nube("NOVEDADES_GUARDIA", datos_novedad_fichaje)
                    
                    if exito_pres: 
                        st.success(f"🔒 BIOMETRÍA REGISTRADA.")
                    else: 
                        st.error("❌ ERROR DE RED")
                else: 
                    st.error("❌ ERROR: Complete todos los campos.")
    with tab_relevo:
        st.markdown("### 🔄 REGISTRO FORMAL DE CAMBIO DE GUARDIA")
        with st.form(key="form_relevo_vigilador_directo", clear_on_submit=True):
            v_obj_relevo = st.selectbox("OBJETIVO DEL RELEVO:", opciones_globales_obj, key="obj_relevo_vig")
            vig_saliente = st.text_input("VIGILADOR QUE ENTREGA (SALE):").upper().strip()
            vig_entrante = st.text_input("VIGILADOR QUE RECIBE (ENTRA):").upper().strip()
            btn_relevo = st.form_submit_button("SANCIONAR CAMBIO DE GUARDIA")
            
            if btn_relevo:
                if vig_saliente and vig_entrante:
                    df_match = df_objetivos[df_objetivos['OBJETIVO'] == v_obj_relevo]
                    sup_responsable = df_match['SUPERVISOR'].values[0] if not df_match.empty else "NO ASIGNADO"
                    
                    fecha_hora_arg = obtener_hora_argentina()
                  #  --- CORRECCIÓN AQUÍ: Definimos la variable antes de usarla ---
                    tipo_evento_relevo = "CAMBIO_GUARDIA"
                    datos_novedad = [
                        fecha_hora_arg,           # A: FECHA
                        v_obj,                    # B: OBJETIVO
                        tipo_evento_relevo,       # C: TIPO_EVENTO
                        v_apellido,               # D: VIGILADOR_SALE (quien reporta)
                        "N/A",                    # E: VIGILADOR_ENTRA
                        v_dni,                    # F: DNI/LEGAJO
                        "PROCESADO",              # G: ESTADO
                        sup_responsable           # H: SUPERVISOR_ASIGNADO
                    ]
                    
                    escribir_registro_nube("NOVEDADES_GUARDIA", datos_novedad)
                    
                    fecha_hoy = fecha_hora_arg.split(" ")[0]
                    hora_hoy = fecha_hora_arg.split(" ")[1]
                    datos_relevo = [fecha_hoy, hora_hoy, v_obj_relevo, vig_saliente, vig_entrante, sup_responsable, "RELEVO_EFECTUADO"]
                    exito_relevo = escribir_registro_nube("VIGILADORES", datos_relevo)
                    
                    if exito_relevo: 
                        st.success("🔒 RELEVO REGISTRADO Y SANEADO")
                    else: 
                        st.error("❌ ERROR DE RED AL REGISTRAR")
                else:
                    st.error("❌ Por favor, completa los nombres de los vigiladores")
    st.markdown('</div>', unsafe_allow_html=True)
# B. ROL: JEFE DE OPERACIONES (MÓDULO INTERACTIVO DE AUDITORÍA DE OBJETIVOS)
elif st.session_state.rol_sel == "JEFE DE OPERACIONES":
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🚨 S.O.S ACTIVOS", "0")
    col2.metric("📡 RED", "OPERATIVA")
    col3.metric("👤 USUARIO", f"{st.session_state.user_sel}")
    col4.metric("🕒 HORA LOCAL", obtener_hora_argentina().split(" ")[1])

    t_crisis, t_ejecucion = st.tabs(["Centro de Crisis", "Ejecución"])
    with t_crisis:
        st.subheader("📡 RADAR Y AUDITORÍA INTERACTIVA DE SERVICIOS")
        st.markdown('<div class="radar-box">', unsafe_allow_html=True)
        
        df_obj_maps_jefe = df_objetivos.dropna(subset=['LATITUD', 'LONGITUD'])
        centro = [df_obj_maps_jefe['LATITUD'].mean(), df_obj_maps_jefe['LONGITUD'].mean()] if not df_obj_maps_jefe.empty else [-34.6, -58.4]
        
        m_visor = folium.Map(location=centro, zoom_start=12, tiles="CartoDB dark_matter")
        if not df_obj_maps_jefe.empty:
            for _, r in df_obj_maps_jefe.iterrows():
                folium.Marker(
                    [r['LATITUD'], r['LONGITUD']], 
                    popup=r['OBJETIVO'], # Importante: El popup define el 'last_object_clicked' en st_folium
                    tooltip=f"Clic para auditar: {r['OBJETIVO']}", 
                    icon=folium.Icon(color="cadetblue", icon="shield", prefix="fa")
                ).add_to(m_visor)
        
        # Captura de datos interactiva del mapa
        mapa_retorno = st_folium(m_visor, width="100%", height=500, key="map_jefe_operaciones_crisis")
        st.markdown('</div>', unsafe_allow_html=True)
        
        # --- LÓGICA DE DETECCIÓN DE CLIC EN OBJETIVO ---
        objetivo_cliqueado = None
        if mapa_retorno and mapa_retorno.get("last_object_clicked_popup"):
            objetivo_cliqueado = mapa_retorno["last_object_clicked_popup"].strip().upper()
        
        if objetivo_cliqueado:
            st.markdown(f'### 📊 CONSOLA TÁCTICA DE AUDITORÍA: {objetivo_cliqueado}')
            
            # 1. Buscar supervisor asignado en la base de objetivos
            df_match_obj = df_objetivos[df_objetivos['OBJETIVO'] == objetivo_cliqueado]
            sup_resp = df_match_obj['SUPERVISOR'].values[0] if not df_match_obj.empty else "NO ASIGNADO"
            
            pan1, pan2 = st.columns([1, 2])
            
            with pan1:
                st.markdown('<div class="panel-novedad" style="margin-top:0px;">', unsafe_allow_html=True)
                st.markdown(f"**👤 SUPERVISOR RESPONSABLE:**<br><span style=\"color:#00E5FF; font-family:'Orbitron'; font-size:16px;\">{sup_resp}</span>", unsafe_allow_html=True)
                st.write("---")
                
                st.markdown("**🔄 ÚLTIMO RELEVO REGISTRADO:**", unsafe_allow_html=True)
                df_rel = leer_matriz_nube("VIGILADORES")
                
                if not df_rel.empty:
                    df_rel.columns = df_rel.columns.str.strip().str.upper()
                    df_rel_obj = df_rel[df_rel['OBJETIVO'] == objetivo_cliqueado]
                    
                    if not df_rel_obj.empty:
                        rel = df_rel_obj.iloc[-1]
                        hora_relevo = rel.get('HORA', 'N/A')
                        
                        # Mostramos los datos con la hora integrada
                        st.write(f"📅 **Fecha:** {rel.get('FECHA', 'N/A')}")
                        st.write(f"🛑 **Sale:** {rel.get('VIGILADOR_SALIENTE', 'N/A')} ({hora_relevo})")
                        st.write(f"🟢 **Entra:** {rel.get('VIGILADOR_ENTRANTE', 'N/A')} ({hora_relevo})")
                        st.write(f"📊 **Estado:** {rel.get('ESTADO', 'N/A')}")
                        
                        # Lógica Antipánico (Sí/No)
                        df_alt = leer_matriz_nube("ALERTAS")
                        if not df_alt.empty:
                            df_alt.columns = df_alt.columns.str.strip().str.upper()
                            hay_panico = df_alt[df_alt['CARGA_UTIL'].str.contains(objetivo_cliqueado, na=False) & (df_alt['ESTADO'] == 'PENDIENTE')]
                            
                            if not hay_panico.empty:
                                st.error("🚨 **ANTIPÁNICO:** SÍ (ACTIVADO)")
                            else:
                                st.success("✅ **ANTIPÁNICO:** NO")
                    else:
                        st.info("Sin registros de relevo en este objetivo.")
                st.markdown('</div>', unsafe_allow_html=True)
                
    with pan2:
               
            st.info("🎯 Seleccione o haga clic en el marcador de cualquier objetivo dentro del mapa táctico superior para desplegar su estado de relevos, supervisor y novedades.")
    
    with t_ejecucion:
        st.markdown('<div class="panel-novedad">', unsafe_allow_html=True)
        st.subheader("🚨 PETICIÓN DE ALTA/BAJA")
        o_accion = st.selectbox("Acción:", ["ALTA", "BAJA"])
        o_cat = st.selectbox("Categoría:", ["OBJETIVO", "MÓVIL", "RECURSO HUMANO"])
        o_det = st.text_input("Nombre / Detalle:")
        if st.button("ELEVAR PETICIÓN"):
            if o_det.strip():
                escribir_registro_nube("PETICIONES", [obtener_hora_argentina(), st.session_state.user_sel, o_accion, o_cat, o_det])
                st.success("✅ Petición Elevada Exitosamente")
        st.markdown('</div>', unsafe_allow_html=True)

    with t_auditoria:
        st.subheader("📋 REPORTE DE MOVIMIENTOS")
        df_novedades = leer_matriz_nube("ACTAS_FLOTAS")
        if not df_novedades.empty: st.dataframe(df_novedades.tail(20), use_container_width=True)

elif st.session_state.rol_sel == "GERENCIA":
    st.markdown('<h2 style="color:#00E5FF; font-family:\'Orbitron\', sans-serif; font-size:24px; margin-bottom:5px;">Comando Estratégico: DIRECCIÓN GENERAL</h2>', unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Ahorro de Riesgo (Estimado)", "$ 1.200.000")
    m2.metric("Nivel de Cobertura", "47/93")
    m3.metric("Auditorías Físicas (QRs)", "2")
    m4.metric("Desgaste Flota (Km)", "4954 Km")
    
    t_com_est, t_ejecucion_ger, t_tab_auditoria = st.tabs(["📩 COMUNICACIÓN ESTRATÉGICA", "🎮 EJECUCIÓN", "📍 TABLERO DE AUDITORÍA"])
    with t_com_est:
        st.markdown('<div class="panel-novedad">', unsafe_allow_html=True)
        g_para = st.selectbox("Para:", ["TODOS"] + LISTA_SUPS_TACTICOS, key="ger_para")
        g_asunto = st.text_input("Asunto:", key="ger_asunto")
        g_orden = st.text_area("Orden:", key="ger_orden")
        g_prioridad = st.selectbox("Prioridad:", ["VERDE", "AMARILLA", "ROJA"], key="ger_prioridad")
        if st.button("Ejecutar Directiva"):
            escribir_registro_nube("CHATS", [obtener_hora_argentina(), st.session_state.user_sel, g_orden, g_prioridad, g_para, g_asunto])
            st.success("✅ Directiva Transmitida")
        st.markdown('</div>', unsafe_allow_html=True)
        
    with t_ejecucion_ger:
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.markdown('<div class="panel-novedad">', unsafe_allow_html=True)
            g_alta_nom = st.text_input("Nombre:", key="ger_alta_nom")
            g_alta_asig = st.selectbox("Asignar a:", LISTA_SUPS_TACTICOS, key="ger_alta_asig")
            if st.button("Solicitar Alta"):
                escribir_registro_nube("PETICIONES", [obtener_hora_argentina(), st.session_state.user_sel, "ALTA", "OBJETIVO", f"{g_alta_nom} | ASIG: {g_alta_asig}"])
                st.success("✅ Petición enviada")
            st.markdown('</div>', unsafe_allow_html=True)
        with col_g2:
            st.markdown('<div class="panel-novedad">', unsafe_allow_html=True)
            opciones_baja = df_objetivos['OBJETIVO'].unique() if not df_objetivos.empty else ["ALFAVINIL"]
            g_baja_obj = st.selectbox("Objetivo:", opciones_baja, key="ger_baja_obj")
            if st.button("Solicitar Baja"):
                escribir_registro_nube("PETICIONES", [obtener_hora_argentina(), st.session_state.user_sel, "BAJA", "OBJETIVO", g_baja_obj])
                st.success("✅ Petición enviada")
            st.markdown('</div>', unsafe_allow_html=True)

    with t_tab_auditoria:
        df_ger_maps = df_objetivos.dropna(subset=['LATITUD', 'LONGITUD'])
        centro = [df_ger_maps['LATITUD'].mean(), df_ger_maps['LONGITUD'].mean()] if not df_ger_maps.empty else [-34.6, -58.4]
        m_visor = folium.Map(location=centro, zoom_start=12, tiles="CartoDB dark_matter")
        for _, r in df_ger_maps.iterrows():
            folium.Marker([r['LATITUD'], r['LONGITUD']], tooltip=r['OBJETIVO'], icon=folium.Icon(color="blue", icon="shield", prefix="fa")).add_to(m_visor)
        st_folium(m_visor, width="100%", height=450, key="map_gerencia")

elif st.session_state.rol_sel == "ADMINISTRADOR":
    u_ing = st.text_input("ADMIN_USER")
    p_ing = st.text_input("ADMIN_PASS", type="password")
    if u_ing == "admin" and p_ing == "aion2026": 
        st.success("Núcleo Maestro desbloqueado.")
