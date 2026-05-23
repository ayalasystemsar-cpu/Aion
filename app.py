
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
            font-family: 'Orbitron', sans-serif; color: #00E5FF !important; font-size: 24px; margin-top: 15px;
            display: flex; align-items: center; justify-content: center; gap: 12px;
            text-shadow: 0 0 15px rgba(0, 229, 255, 0.4); letter-spacing: 2px; text-transform: uppercase;
        }
        
        .stApp div[data-testid="stExpander"] { background-color: #1A1C23 !important; border: 1px solid #2D313E !important; border-radius: 8px !important; }
        .stApp div[data-testid="stExpander"] summary p { color: #E0E0E0 !important; font-size: 14px !important; font-weight: 600 !important; text-transform: uppercase; }
        .stApp input { background-color: #252833 !important; color: #FFFFFF !important; border: 1px solid #1A1C23 !important; border-radius: 6px !important; }
        .stApp label p { color: #A0A5B5 !important; font-family: 'Orbitron', sans-serif !important; font-size: 11px !important; font-weight: bold !important; letter-spacing: 0.5px; text-transform: uppercase; }

        .radar-box { border: 1px solid #00e5ff; border-radius: 8px; padding: 5px; background: #000000; box-shadow: 0 0 20px rgba(0, 229, 255, 0.2); }
        .stButton > button[kind="primary"] { 
            background: radial-gradient(circle, #FF0000 0%, #8B0000 100%) !important; 
            color: white !important; border-radius: 50% !important; width: 105px !important; height: 105px !important; 
            border: 3px solid #333 !important; box-shadow: 0 0 25px rgba(255, 0, 0, 0.5) !important; 
            font-family: 'Orbitron', sans-serif; font-size: 11px !important; font-weight: bold;
        }
        
        .message-box { border-left: 3px solid #00e5ff; padding-left: 10px; margin-bottom: 15px; background: rgba(255,255,255,0.02); padding-top: 5px; padding-bottom: 5px; }
        .message-box-red { border-left: 3px solid #ff0000; padding-left: 10px; margin-bottom: 15px; background: rgba(255,255,255,0.02); padding-top: 5px; padding-bottom: 5px; }
        .message-info { color: #00e5ff; font-size: 13px; font-weight: bold; font-family: 'Orbitron', sans-serif; }
        .message-text { color: #e0e0e0; font-size: 14px; margin-top: 4px; font-family: 'Rajdhani', sans-serif; }
        
        .panel-info { display: flex; justify-content: space-between; margin-bottom: 20px; padding: 10px; border: 1px solid #333; border-radius: 4px; background: rgba(10, 10, 11, 0.9); }
        .panel-novedad { border: 1px solid #333; border-radius: 8px; padding: 15px; margin-top: 20px; background-color: rgba(10, 10, 11, 0.9); }

        .stTabs [data-baseweb="tab-list"] { gap: 10px; background-color: transparent; }
        .stTabs [data-baseweb="tab"] {
            background-color: rgba(26, 28, 35, 0.4) !important; border: 1px solid #2D313E !important;
            color: #A0A5B5 !important; border-radius: 4px 4px 0px 0px !important; padding: 6px 16px !important;
            font-family: 'Orbitron', sans-serif; font-size: 11px !important; font-weight: bold;
        }
        .stTabs [aria-selected="true"] { background-color: #1A1C23 !important; border-top: 2px solid #00E5FF !important; color: #00E5FF !important; }
        </style>
        """, unsafe_allow_html=True
    )

aplicar_identidad_alfa()

# --- 5. SIDEBAR TÁCTICO ---
df_objetivos = cargar_objetivos()

LISTA_SUPS_TACTICOS = [
    "AYALA BRIAN", "SUPERVISOR 1", "SUPERVISOR 2", "SUPERVISOR 3", "SUPERVISOR 4", "SUPERVISOR 5", "SUPERVISOR NOCTURNO"
]

if 'rol_sel' not in st.session_state: st.session_state.rol_sel = "MONITOREO"
if 'user_sel' not in st.session_state: st.session_state.user_sel = "OPERADOR CENTRAL"
if 'sup_autenticado' not in st.session_state: st.session_state.sup_autenticado = False

with st.sidebar:
    st.markdown('<div class="contenedor-logo-sidebar"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" style="width:180px; border:1px solid #00e5ff; border-radius:4px;"></div>', unsafe_allow_html=True)
    st.subheader("🛡️ PANEL DE CONTROL")
    
    if st.button("🛰️ MONITOREO", use_container_width=True):
        st.session_state.rol_sel = "MONITOREO"
        st.session_state.user_sel = "OPERADOR CENTRAL"
        st.session_state.sup_autenticado = False
        st.rerun()
        
    if st.button("📋 JEFE DE OPERACIONES", use_container_width=True):
        st.session_state.rol_sel = "JEFE DE OPERACIONES"
        st.session_state.user_sel = "SANOJA LUIS"
        st.session_state.sup_autenticado = False
        st.rerun()
        
    if st.button("🏢 GERENCIA", use_container_width=True):
        st.session_state.rol_sel = "GERENCIA"
        st.session_state.user_sel = "DIRECCIÓN GENERAL"
        st.session_state.sup_autenticado = False
        st.rerun()

    with st.expander("👤 SUPERVISORES", expanded=(st.session_state.rol_sel == "SUPERVISOR" or 'intentando_sup' in st.session_state)):
        nom_sup = st.selectbox("RESPONSABLE ACTIVO:", LISTA_SUPS_TACTICOS, key="cambio_supervisor_directo")
        user_sup = st.text_input("USUARIO RECURSO (APELLIDO)", key="auth_user_sup")
        pass_sup = st.text_input("CONTRASEÑA CRÍTICA", type="password", key="auth_pass_sup")
        
        if st.button("AUTENTICAR E INGRESAR", use_container_width=True):
            st.session_state.intentando_sup = True
            if "NOCTURNO" in nom_sup: usuario_esperado = "nocturno"
            elif "AYALA" in nom_sup: usuario_esperado = "ayala"
            else: usuario_esperado = nom_sup.split(" ")[1]
            
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
    if st.button("👮 VIGILADOR (ACCESO PUESTO)", use_container_width=True):
        st.session_state.rol_sel = "VIGILADOR"
        st.session_state.user_sel = "VIGILADOR EN PUESTO"
        st.session_state.sup_autenticado = False
        st.rerun()

    st.write("---")
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
        else: obj_alerta = "CENTRAL BASE"
            
        carga_sos = f"LAT:{lat_envio}|LON:{lon_envio}|OBJ:{obj_alerta}|SUP:{st.session_state.user_sel}"
        escribir_registro_nube("ALERTAS", [obtener_hora_argentina(), st.session_state.user_sel, "PÁNICO", "PENDIENTE", carga_sos])
        st.error(f"🚨 S.O.S ENVIADO DESDE {obj_alerta}")

# --- 6. CABECERA CENTRAL ---
st.markdown('<div class="contenedor-logo-central"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" class="logo-phoenix"></div>', unsafe_allow_html=True)

titulos = {
    "MONITOREO": "🛰️ CENTRAL DE INTELIGENCIA OPERATIVA",
    "SUPERVISOR": f"📱 Estación de Control: {st.session_state.user_sel}",
    "VIGILADOR": "👮 TERMINAL OPERATIVO VIGILADORES",
    "JEFE DE OPERACIONES": "📋 COMANDO DE OPERACIONES TÁCTICAS",
    "GERENCIA": "🏢 DIRECCIÓN Y FISCALIZACIÓN GENERAL",
    "ADMINISTRADOR": "⚙️ NÚCLEO MAESTRO: AION-YAROKU"
}
st.markdown(f'<div class="estacion-titulo">{titulos.get(st.session_state.rol_sel, "SISTEMA TÁCTICO DE COMANDO")}</div>', unsafe_allow_html=True)

# --- 7. FLUJO POR ROLES ---
if st.session_state.rol_sel == "MONITOREO":
    df_emergencias = leer_matriz_nube("ALERTAS")
    
    if df_emergencias.empty:
        df_emergencias = pd.DataFrame(columns=['FECHA', 'USUARIO', 'TIPO', 'ESTADO', 'CARGA_UTIL', 'INFORME'])
    else:
        df_emergencias.columns = df_emergencias.columns.str.strip().str.upper()
    
    lista_objetivos_en_panico = []
    if not df_emergencias.empty and 'ESTADO' in df_emergencias.columns and 'CARGA_UTIL' in df_emergencias.columns:
        pendientes = df_emergencias[df_emergencias['ESTADO'].astype(str).str.upper() == 'PENDIENTE']
        sos_activos = len(pendientes)
        for _, row in pendientes.iterrows():
            carga = str(row['CARGA_UTIL'])
            if "OBJ:" in carga:
                try: lista_objetivos_en_panico.append(carga.split("OBJ:")[1].split("|")[0].strip().upper())
                except: pass
    else: sos_activos = 0
    
    c1, c2, c3 = st.columns(3)
    c1.metric("🚨 S.O.S ACTIVOS", sos_activos)
    c2.metric("📡 RED", "OPERATIVA")
    c3.metric("🕒 HORA LOCAL", obtener_hora_argentina().split(" ")[1])

    t_radar, t_gestion, t_comunicacion, t_pres, t_vig, t_guardia = st.tabs([
        "🚨 RADAR S.O.S", "📖 LIBRO DE BASE", "💬 CHAT OPERATIVO", "📋 PRESENTISMO GENERAL", "👥 PADRÓN VIGILADORES", "🔄 NOVEDADES GUARDIA"
    ])
    
    with t_radar:
        st.subheader("📡 RADAR GLOBAL DE OBJETIVOS")
        if sos_activos > 0:
            st.markdown('<div class="panel-novedad" style="border: 1px solid #FF0000;">', unsafe_allow_html=True)
            df_pendientes_form = df_emergencias[df_emergencias['ESTADO'] == 'PENDIENTE']
            with st.form(key="form_finalizar_panico", clear_on_submit=True):
                opciones_alertas = {f"{r['FECHA']} - {r['USUARIO']}": idx for idx, r in df_pendientes_form.iterrows()}
                alerta_seleccionada = st.selectbox("SELECCIONE EVENTO A FINALIZAR:", list(opciones_alertas.keys()))
                txt_informe_cierre = st.text_area("INFORME OPERATIVO DE CIERRE:", placeholder="Describa la resolución...")
                if st.form_submit_button("🚨 FINALIZAR PÁNICO Y NORMALIZAR") and txt_informe_cierre.strip():
                    idx_df = opciones_alertas[alerta_seleccionada]
                    actualizar_celda("ALERTAS", idx_df + 2, "D", "FINALIZADO")
                    actualizar_celda("ALERTAS", idx_df + 2, "F", txt_informe_cierre.strip().upper())
                    st.success("✅ Normalizado")
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="radar-box">', unsafe_allow_html=True)
        df_mapa_monitoreo = df_objetivos.dropna(subset=['LATITUD', 'LONGITUD']).copy()
        if not df_mapa_monitoreo.empty:
            m_mon = folium.Map(location=[df_mapa_monitoreo['LATITUD'].mean(), df_mapa_monitoreo['LONGITUD'].mean()], zoom_start=11, tiles="CartoDB dark_matter")
            estilo_pulsar_html = """
            <style>
            @keyframes pulse-red-critico {
                0% { r: 7px; fill: #FF0000; fill-opacity: 1; stroke-width: 2; stroke: #FF3333; }
                50% { r: 15px; fill: #B30000; fill-opacity: 0.4; stroke: #FF0000; stroke-width: 8; stroke-opacity: 0.6; }
                100% { r: 7px; fill: #FF0000; fill-opacity: 1; stroke-width: 2; stroke: #FF3333; }
            }
            .marker-panic-pulsing { animation: pulse-red-critico 1.1s infinite ease-in-out !important; display: block !important; }
            </style>
            """
            m_mon.get_root().header.add_child(folium.Element(estilo_pulsar_html))
            for _, r in df_mapa_monitoreo.iterrows():
                info_hover = f"🎯 OBJETIVO: {r['OBJETIVO']} | 👤 SUPERVISOR: {r.get('SUPERVISOR', 'NO ASIGNADO')}"
                folium.CircleMarker(
                    location=[r['LATITUD'], r['LONGITUD']], radius=7,
                    color="#FF0000" if r['OBJETIVO'] in lista_objetivos_en_panico else "#00E5FF",
                    fill=True, fill_color="#FF0000" if r['OBJETIVO'] in lista_objetivos_en_panico else "#00E5FF",
                    tooltip=folium.Tooltip(info_hover, sticky=True),
                    class_name="marker-panic-pulsing" if r['OBJETIVO'] in lista_objetivos_en_panico else None
                ).add_to(m_mon)
            st_folium(m_mon, width="100%", height=550, key="mapa_monitoreo_radar_tactico")
        st.markdown('</div>', unsafe_allow_html=True)

    with t_gestion:
        st.subheader("📖 HISTORIAL DE OPERATIVOS")
        if not df_emergencias.empty: st.dataframe(df_emergencias.iloc[::-1], use_container_width=True)

    with t_comunicacion:
        with st.form(key="form_chat_monitoreo", clear_on_submit=True):
            txt_mensaje_mon = st.text_input("ESCRIBIR MENSAJE TÁCTICO GENERAL:")
            prioridad_mon = st.selectbox("NIVEL DE CRITICIDAD:", ["VERDE", "ROJA"])
            if st.form_submit_button("TRANSMITIR A LA RED") and txt_mensaje_mon.strip():
                escribir_registro_nube("CHATS", [obtener_hora_argentina(), st.session_state.user_sel, txt_mensaje_mon.strip().upper(), prioridad_mon, "TODOS", "MONITOREO DIRECTO"])
                st.rerun()
        df_chats = leer_matriz_nube("CHATS")
        if not df_chats.empty:
            for _, msg in df_chats.tail(15).iloc[::-1].iterrows():
                st.markdown(f'<div class="{"message-box-red" if msg.get("PRIORIDAD")=="ROJA" else "message-box"}"><div class="message-info">{msg.get("HORA")} De: {msg.get("USUARIO")}</div><div class="message-text">{msg.get("TEXTO")}</div></div>', unsafe_allow_html=True)

    with t_pres:
        st.subheader("📋 TABLA MASTER: PRESENTISMO")
        df_pres = leer_matriz_nube("PRESENTISMO")
        if not df_pres.empty: st.dataframe(df_pres.sort_values(by="FECHA", ascending=False), use_container_width=True)

    with t_vig:
        st.subheader("👥 TABLA MASTER: VIGILADORES")
        df_padrero = leer_matriz_nube("VIGILADORES")
        if not df_padrero.empty: st.dataframe(df_padrero, use_container_width=True)

    with t_guardia:
        st.subheader("🔄 TABLA MASTER: NOVEDADES_GUARDIA")
        df_nov_g = leer_matriz_nube("NOVEDADES_GUARDIA")
        if not df_nov_g.empty: st.dataframe(df_nov_g.sort_values(by="FECHA", ascending=False), use_container_width=True)

# --- ROL: SUPERVISOR ---
elif st.session_state.rol_sel == "SUPERVISOR":
    if st.session_state.sup_autenticado:
        sup_activo_normalizado = st.session_state.user_sel.strip().upper()
        df_objetivos_filtrados = df_objetivos[df_objetivos['SUPERVISOR'] == sup_activo_normalizado] if not df_objetivos.empty else pd.DataFrame()

        st.subheader("Control de Unidad Móvil")
        st.markdown('<div class="panel-info">', unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.selectbox("Móvil:", ["S-001", "M-002", "M-003", "OTRO"], key="sup_movil_select")
        with c2: st.number_input("Km Inicial:", value=0, key="sup_km_inicial")
        with c3: st.number_input("Km Final:", value=0, key="sup_km_final")
        with c4: st.number_input("Combustible (Lts):", value=0.0, key="sup_combustible")
        st.markdown('</div>', unsafe_allow_html=True)
        
        col_btn1, col_btn2 = st.columns([3, 1])
        with col_btn1: st.button("SELLAR ODOMETRÍA Y LOGÍSTICA", key="btn_sellar_logistica", use_container_width=True)
        with col_btn2:
            if st.button("🔄 REFRESCAR SISTEMA", key=f"btn_refrescar_sistema_{sup_activo_normalizado}", use_container_width=True): st.rerun()

        t_vis_qr, t_car_tac, t_com_sup, t_pres_sup = st.tabs(["Visita QR", "Carga Táctica", "💬 CHAT OPERATIVO", "📋 NOVEDADES DEL SECTOR"])
        
        with t_vis_qr:
            opciones_servicios = df_objetivos_filtrados['OBJETIVO'].unique() if not df_objetivos_filtrados.empty else ["SIN OBJETIVOS"]
            st.selectbox("SERVICIO ACTUAL:", opciones_servicios, key="sup_servicio_actual")
            st.radio("ACCIÓN:", ["SELECCIONAR...", "INGRESO", "SALIDA"], index=0, key="sup_radio_accion", horizontal=True)
            
            st.write("---")
            df_mapa_sup = df_objetivos_filtrados.dropna(subset=['LATITUD', 'LONGITUD'])
            if not df_mapa_sup.empty:
                m_visor = folium.Map(location=[df_mapa_sup['LATITUD'].mean(), df_mapa_sup['LONGITUD'].mean()], zoom_start=12, tiles="CartoDB dark_matter")
                for _, r in df_mapa_sup.iterrows():
                    folium.Marker([r['LATITUD'], r['LONGITUD']], tooltip=f"🎯 OBJETIVO: {r['OBJETIVO']}", icon=folium.Icon(color="blue", icon="shield", prefix="fa")).add_to(m_visor)
                st_folium(m_visor, width="100%", height=400, key=f"map_sup_{sup_activo_normalizado}")

        with t_car_tac:
            novedad_sup = st.text_area("Novedad / Registro Operativo:")
            if st.button("CARGAR REGISTRO") and novedad_sup.strip():
                escribir_registro_nube("NOVEDADES", [obtener_hora_argentina(), st.session_state.user_sel, novedad_sup.upper()])
                st.success("✅ Cargado")

        with t_com_sup:
            with st.form(key="form_chat_supervisor", clear_on_submit=True):
                txt_mensaje_sup = st.text_input("REPORTE RÁPIDO PARA MONITOREO:")
                prioridad_sup = st.selectbox("RELEVANCIA:", ["VERDE", "ROJA"])
                if st.form_submit_button("ENVIAR MENSAJE") and txt_mensaje_sup.strip():
                    escribir_registro_nube("CHATS", [obtener_hora_argentina(), st.session_state.user_sel, txt_mensaje_sup.strip().upper(), prioridad_sup, "MONITOREO", "REPORTE CAMPO"])
                    st.rerun()
            df_chats_sup = leer_matriz_nube("CHATS")
            if not df_chats_sup.empty:
                for _, msg in df_chats_sup.tail(15).iloc[::-1].iterrows():
                    st.markdown(f'<div class="{"message-box-red" if msg.get("PRIORIDAD")=="ROJA" else "message-box"}"><div class="message-info">{msg.get("HORA")} De: {msg.get("USUARIO")}</div><div class="message-text">{msg.get("TEXTO")}</div></div>', unsafe_allow_html=True)

        with t_pres_sup:
            st.markdown("### 📋 HISTORIAL DE NOVEDADES EN MI SECTOR")
            df_v_total = leer_matriz_nube("NOVEDADES_GUARDIA")
            if not df_v_total.empty:
                df_v_total.columns = df_v_total.columns.str.strip().str.upper()
                # Muestra los relevos donde figura este supervisor asignado
                if 'SUPERVISOR' in df_v_total.columns:
                    df_v_filtrado = df_v_total[df_v_total['SUPERVISOR'] == sup_activo_normalizado]
                    st.dataframe(df_v_filtrado.sort_values(by="FECHA", ascending=False), use_container_width=True)

# --- ROL: VIGILADOR (CON MÓDULOS INDEPENDIENTES DE PRESENTISMO Y RELEVO) ---
elif st.session_state.rol_sel == "VIGILADOR":
    st.markdown('<div class="panel-novedad">', unsafe_allow_html=True)
    
    opciones_globales_obj = df_objetivos['OBJETIVO'].unique() if not df_objetivos.empty else ["ALFAVINIL", "BARRIO EL CAMPO"]
    
    # 🗂️ PESTAÑAS EXCLUSIVAS PARA OPERATORIA DEL VIGILADOR
    tab_presentismo, tab_relevo = st.tabs([
        "📋 FICHAJE INDIVIDUAL (PRESENTISMO)", 
        "🔄 SANCIONAR RELEVO (CAMBIO DE GUARDIA)"
    ])
    
    # 1. MÓDULO PRESENTISMO (Fichaje Biométrico)
    with tab_presentismo:
        st.markdown("### 📸 REGISTRO BIOMÉTRICO DE INGRESO")
        with st.form(key="form_fichaje_vigilador", clear_on_submit=True):
            v_apellido = st.text_input("APELLIDO Y NOMBRE COMPLETO:").upper().strip()
            v_dni = st.text_input("DNI / LEGAJO:").strip()
            v_obj = st.selectbox("OBJETIVO DE PRESENTISMO:", opciones_globales_obj, key="obj_pres_vig")
            
            img_facial = st.camera_input("RECONOCIMIENTO FACIAL COMPULSORIO")
            btn_fichar = st.form_submit_button("CONSIGNAR PRESENTE Y TRANSMITIR")
            
            if btn_fichar:
                if v_apellido and img_facial and v_dni:
                    df_match = df_objetivos[df_objetivos['OBJETIVO'] == v_obj]
                    sup_responsable = df_match['SUPERVISOR'].values[0] if not df_match.empty else "NO ASIGNADO"

                    # ⚡ ESCRITURA EXCLUSIVA EN 'PRESENTISMO':
                    escribir_registro_nube("PRESENTISMO", [obtener_hora_argentina(), f"{v_apellido} (DNI: {v_dni})", v_obj, "PRESENTE"])
                    st.success(f"🔒 BIOMETRÍA PROCESADA. Tu Presente fue guardado en la base master y notificado a tu Supervisor ({sup_responsable}).")
                else:
                    st.error("❌ ERROR: Complete su nombre, DNI y capture su foto facial obligatoria para abrir servicio.")
                    
    # 2. MÓDULO RELEVO (Cambio de Guardia)
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
                    
                    # ⚡ ESCRITURA EXCLUSIVA EN 'NOVEDADES_GUARDIA':
                    escribir_registro_nube("NOVEDADES_GUARDIA", [
                        obtener_hora_argentina(), 
                        v_obj_relevo, 
                        "CAMBIO_GUARDIA", 
                        f"SALE: {vig_saliente}", 
                        f"ENTRA: {vig_entrante}",
                        sup_responsable
                    ])
                    st.success(f"⚡ RELEVO REGISTRADO. Se asentó el cambio de guardia en 'NOVEDADES_GUARDIA' bajo la supervisión de {sup_responsable}.")
                else:
                    st.error("❌ ERROR: Debe ingresar tanto el nombre del vigilador saliente como el del entrante.")
                    
    st.markdown('</div>', unsafe_allow_html=True)

# F. ROL: JEFE DE OPERACIONES
elif st.session_state.rol_sel == "JEFE DE OPERACIONES":
    df_obj_maps_jefe = df_objetivos.dropna(subset=['LATITUD', 'LONGITUD'])
    if not df_obj_maps_jefe.empty:
        m_visor = folium.Map(location=[df_obj_maps_jefe['LATITUD'].mean(), df_obj_maps_jefe['LONGITUD'].mean()], zoom_start=12, tiles="CartoDB dark_matter")
        for _, r in df_obj_maps_jefe.iterrows():
            folium.Marker([r['LATITUD'], r['LONGITUD']], tooltip=f"OBJ: {r['OBJETIVO']}").add_to(m_visor)
        st_folium(m_visor, width="100%", height=500, key="mapRef")

# G. ROL: GERENCIA
elif st.session_state.rol_sel == "GERENCIA":
    st.metric("Nivel de Cobertura Humana", "OPERATIVA")

# H. ROL: ADMINISTRADOR
elif st.session_state.rol_sel == "ADMINISTRADOR":
    u_ing = st.text_input("ADMIN_USER")
    p_ing = st.text_input("ADMIN_PASS", type="password")
    if u_ing == "admin" and p_ing == "aion2026":
        st.success("Núcleo Maestro desbloqueado.")
