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
from folium.plugins import AntPath
from streamlit_folium import st_folium
import math
import requests
from branca.element import Element
import qrcode

# --- 1. CONFIGURACIÓN E INICIALIZACIÓN ---
st.set_page_config(page_title="AION-YAROKU | COMMAND", page_icon="🛡️", layout="wide", initial_sidebar_state="expanded")

if 'usuario_logueado' not in st.session_state: st.session_state.usuario_logueado = False
if 'rol_sel' not in st.session_state: st.session_state.rol_sel = "MONITOREO"
if 'user_sel' not in st.session_state: st.session_state.user_sel = "OPERADOR CENTRAL"
if 'sup_autenticado' not in st.session_state: st.session_state.sup_autenticado = False
if 'admin_autenticado' not in st.session_state: st.session_state.admin_autenticado = False

# --- 2. FUNCIONES DE LÓGICA Y GOOGLE ---
ID_MAESTRO_DB = "1Md0VkOnwUJWldq0S1fB9UrmOKv4MG__JVG3tQsda0Uw"

def conectar_google():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        return gspread.authorize(creds)
    except: return None

def escribir_registro_nube(pestana, datos_fila):
    try:
        gc = conectar_google()
        if gc:
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
            hoja.append_row(datos_fila)
            return True
    except: return False

def actualizar_celda(pestana, fila, columna, valor):
    try:
        gc = conectar_google()
        if gc:
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
            hoja.update_acell(f"{columna}{fila}", valor)
            return True
    except: return False

def leer_matriz_nube(pestana):
    gc = conectar_google()
    if gc:
        try:
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
            todas_filas = hoja.get_all_values()
            
            if not todas_filas: 
                return pd.DataFrame()
                
            encabezados = [str(h).strip().upper() for h in todas_filas[0]]
            df = pd.DataFrame(todas_filas[1:], columns=encabezados)
            df.columns = [str(c).strip().upper() for c in df.columns]
            return df.loc[:, ~df.columns.duplicated()]
        except: 
            return pd.DataFrame()
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
        df['LATITUD'] = pd.to_numeric(df['LATITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        df['LONGITUD'] = pd.to_numeric(df['LONGITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        return df 
    return pd.DataFrame()

@st.cache_data(ttl=60)
def cargar_datos_comisarias():
    data = {
        "COMISARIA": ["COMISARÍA SAN MARTÍN 1RA", "COMISARÍA VECINAL 14C", "COMISARÍA AVELLANEDA 1RA", "COMISARÍA CAMPANA 1RA", "COMISARÍA SAN FERNANDO 1RA", "COMISARÍA TIGRE 1RA", "COMISARÍA PILAR 6TA (VILLA ROSA)", "COMISARÍA VECINAL 1B", "COMISARÍA VECINAL 14A", "COMISARÍA LANÚS 2DA", "COMISARÍA VECINAL 13A", "COMISARÍA LA MATANZA 2DA", "COMISARÍA LA MATANZA 3RA", "COMISARÍA VECINAL 2A", "COMISARÍA VECINAL 12A", "COMISARÍA VECINAL 12B", "COMISARÍA VECINAL 6A", "COMISARÍA VECINAL 1D", "COMISARÍA RAMOS MEJÍA 2DA"],
        "LATITUD": [-34.580139, -34.587773, -34.664119, -34.163693, -34.440154, -34.424196, -34.417041, -34.617133, -34.587773, -34.708819, -34.557454, -34.700147, -34.717182, -34.589886, -34.554321, -34.568459, -34.613045, -34.603847, -34.646589],
        "LONGITUD": [-58.541410, -58.416056, -58.368073, -58.961418, -58.556134, -58.579789, -58.868209, -58.378734, -58.416056, -58.385311, -58.461144, -58.575608, -58.608301, -58.401918, -58.472147, -58.482012, -58.437198, -58.381577, -58.564571]
    }
    return pd.DataFrame(data)

def obtener_hora_argentina():
    tz = pytz.timezone("America/Argentina/Buenos_Aires")
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

def obtener_ruta_calles_osrm(lat1, lon1, lat2, lon2):
    try:
        url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=full&geometries=geojson"
        response = requests.get(url, timeout=5).json()
        if response.get("code") == "Ok":
            coordenadas = response["routes"][0]["geometry"]["coordinates"]
            return [[point[1], point[0]] for point in coordenadas]
    except: pass
    return [[lat1, lon1], [lat2, lon2]]

# --- 3. IDENTIDAD Y ESTILOS ---
def aplicar_identidad_alfa():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@300;500;700&display=swap');
        .stApp { background: radial-gradient(circle at top, #0A0F1E 0%, #030305 100%) !important; color: #E0E0E0; font-family: 'Rajdhani', sans-serif; }
        .contenedor-logo-central { display: flex; justify-content: center; align-items: center; width: 100%; margin: 15px 0; }
        .logo-phoenix { width: 420px !important; border: 2px solid #00e5ff !important; box-shadow: 0 0 35px rgba(0, 229, 255, 0.5) !important; border-radius: 4px !important; background-color: #000 !important; }
        .estacion-titulo { font-family: 'Orbitron', sans-serif; color: #00E5FF !important; font-size: 26px; text-align: center; text-shadow: 0 0 15px rgba(0, 229, 255, 0.4); margin-bottom: 20px; }
        .stButton > button { background-color: #0A192F !important; color: #00E5FF !important; border: 1px solid #00E5FF !important; border-radius: 5px !important; font-family: 'Orbitron', sans-serif !important; }
        .stButton > button:hover { background-color: #00E5FF !important; color: #000 !important; }
        .panel-novedad { border: 1px solid #333; border-radius: 8px; padding: 15px; margin-top: 15px; background-color: rgba(10, 10, 11, 0.9); }
        div[data-testid="stMetric"] { background-color: rgba(10, 11, 15, 0.6) !important; border: 1px solid #1A1C23 !important; border-radius: 6px !important; padding: 12px !important; }
        div[data-testid="stMetricLabel"] p { color: #00E5FF !important; font-family: 'Rajdhani', sans-serif !important; font-size: 13px !important; font-weight: bold !important; text-transform: uppercase; }
        div[data-testid="stMetricValue"] div { color: #FFFFFF !important; font-family: 'Orbitron', sans-serif !important; font-size: 20px !important; }
        </style>
    """, unsafe_allow_html=True)

aplicar_identidad_alfa()

# --- 4. LANDING / AUTENTICACIÓN ---
def mostrar_landing():
    st.markdown('<div class="contenedor-logo-central"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" class="logo-phoenix"></div>', unsafe_allow_html=True)
    st.markdown('<div class="estacion-titulo">AION-YAROKU | COMMAND SYSTEM</div>', unsafe_allow_html=True)
    
    modo = st.radio("Acceso al Sistema:", ["Iniciar Sesión", "Crear Cuenta"], horizontal=True, key="radio_modo")
    
    with st.form("form_acceso_real"):
        user = st.text_input("Usuario", key="u")
        password = st.text_input("Contraseña", type="password", key="p")
        roles_registro = ["VIGILADOR", "MONITOREO", "JEFE DE OPERACIONES", "GERENCIA", "SUPERVISOR"]
        rol_usuario = st.selectbox("Seleccione su Rol:", roles_registro, key="r")
        btn_texto = "ENTRAR" if modo == "Iniciar Sesión" else "REGISTRARSE"
        
        if st.form_submit_button(btn_texto):
            if modo == "Iniciar Sesión" and user.strip() == "admin" and password.strip() == "aion2026":
                st.session_state.usuario_logueado = True
                st.session_state.user_sel = "ADMIN CENTRAL"
                st.session_state.rol_sel = "ADMINISTRADOR"
                st.session_state.admin_autenticado = True
                st.rerun()
            elif modo == "Iniciar Sesión":
                df_usuarios = leer_matriz_nube("USUARIOS")
                if not df_usuarios.empty:
                    usuario_ok = df_usuarios[(df_usuarios['USUARIO'].str.strip() == user.strip()) & (df_usuarios['CONTRASEÑA'].str.strip() == password.strip())]
                    if not usuario_ok.empty:
                        if usuario_ok.iloc[0]['ESTADO'].strip() == "APROBADO":
                            st.session_state.usuario_logueado = True
                            st.session_state.user_sel = user.upper()
                            st.session_state.rol_sel = usuario_ok.iloc[0]['ROL'].strip()
                            st.rerun()
                        else:
                            st.warning("⚠️ Tu cuenta existe pero está PENDIENTE de aprobación por el Administrador.")
                    else:
                        st.error("❌ Credenciales inválidas.")
                else:
                    st.error("⚠️ Error al conectar con la base de usuarios.")
            else:
                escribir_registro_nube("USUARIOS", [user.upper(), password, rol_usuario, "PENDIENTE"])
                st.success("✅ Solicitud enviada. Quedamos a la espera de autorización del Administrador.")

if not st.session_state.usuario_logueado:
    mostrar_landing()
    st.stop()

# --- 5. SIDEBAR TÁCTICO ---
df_objetivos = cargar_objetivos()
df_comisarias = cargar_datos_comisarias()
LISTA_SUPS_TACTICOS = ["AYALA BRIAN", "SUPERVISOR 1", "SUPERVISOR 2", "SUPERVISOR 3", "SUPERVISOR 4", "SUPERVISOR 5", "SUPERVISOR NOCTURNO"]

with st.sidebar:
    st.markdown('<div style="text-align:center;"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" style="width:160px; border:1px solid #00e5ff; border-radius:4px;"></div>', unsafe_allow_html=True)
    st.subheader("🛡️ PANEL DE CONTROL")
    
    if st.button("🛰️ MONITOREO", use_container_width=True):
        st.session_state.rol_sel = "MONITOREO"
        st.session_state.user_sel = "OPERADOR CENTRAL"
        st.rerun()
        
    if st.button("📋 JEFE DE OPERACIONES", use_container_width=True):
        st.session_state.rol_sel = "JEFE DE OPERACIONES"
        st.session_state.user_sel = "JEFE DE OPERACIONES"
        st.rerun()
        
    if st.button("🏢 GERENCIA", use_container_width=True):
        st.session_state.rol_sel = "GERENCIA"
        st.session_state.user_sel = "DIRECCIÓN GENERAL"
        st.rerun()

    with st.expander("👤 SUPERVISORES", expanded=(st.session_state.rol_sel == "SUPERVISOR")):
        nom_sup = st.selectbox("RESPONSABLE ACTIVO:", LISTA_SUPS_TACTICOS, key="cambio_supervisor_directo")
        user_sup = st.text_input("USUARIO RECURSO", key="auth_user_sup")
        pass_sup = st.text_input("CONTRASEÑA", type="password", key="auth_pass_sup")
        
        if st.button("AUTENTICAR SUPERVISOR", use_container_width=True):
            usuario_esperado = "ayala" if "AYALA" in nom_sup else (nom_sup.split(" ")[1].lower() if len(nom_sup.split(" ")) > 1 else "sup")
            if user_sup.strip().lower() == usuario_esperado and pass_sup == "1234":
                st.session_state.rol_sel = "SUPERVISOR"
                st.session_state.user_sel = nom_sup
                st.session_state.sup_autenticado = True
                st.success(f"🔓 ACCESO CONCEDIDO: {nom_sup}")
                st.rerun()
            else:
                st.error("❌ Credenciales de supervisor incorrectas.")

    if st.button("👮 VIGILADOR (PUESTO)", use_container_width=True):
        st.session_state.rol_sel = "VIGILADOR"
        st.session_state.user_sel = "VIGILADOR EN PUESTO"
        st.rerun()

    st.markdown("---")
    if st.button("⚙️ NÚCLEO MAESTRO (ADMIN)", use_container_width=True):
        st.session_state.rol_sel = "ADMINISTRADOR"
        st.session_state.user_sel = "ADMIN CENTRAL"
        st.session_state.admin_autenticado = True
        st.rerun()

    st.markdown("---")
    if st.button("🚪 CERRAR SESIÓN", use_container_width=True):
        st.session_state.usuario_logueado = False
        st.session_state.admin_autenticado = False
        st.session_state.sup_autenticado = False
        st.rerun()

# --- 6. MÓDULO DE MENSAJERÍA GLOBAL ---
def renderizar_mensajeria_global(rol_contexto):
    if 'asunto_respuesta' not in st.session_state: st.session_state.asunto_respuesta = None
    df_msg = leer_matriz_nube("MENSAJERIA")
    st.subheader("💬 COMUNICACIONES OPERATIVAS")

    with st.form(key=f"form_msg_{rol_contexto}", clear_on_submit=True):
        asunto_input = st.text_input("ASUNTO:", value=st.session_state.asunto_respuesta if st.session_state.asunto_respuesta else "", disabled=bool(st.session_state.asunto_respuesta))
        col_a, col_b = st.columns([3, 1])
        with col_a: txt_msg = st.text_input("MENSAJE:")
        with col_b:
            destinatarios_posibles = ["TODOS", "MONITOREO", "JEFE DE OPERACIONES", "GERENCIA", "SUPERVISORES"] + LISTA_SUPS_TACTICOS
            destinatario = st.selectbox("PARA:", destinatarios_posibles)
            gravedad = st.selectbox("GRAVEDAD:", ["VERDE", "ROJA"])

        if st.form_submit_button("TRANSMITIR A LA RED"):
            if txt_msg.strip():
                escribir_registro_nube("MENSAJERIA", [obtener_hora_argentina(), st.session_state.user_sel, destinatario, (asunto_input or "GENERAL").upper(), txt_msg.upper(), "PENDIENTE", gravedad])
                st.session_state.asunto_respuesta = None
                st.success("✅ MENSAJE TRANSMITIDO")
                st.rerun()

    if not df_msg.empty and 'ASUNTO' in df_msg.columns:
        for asunto, grupo in df_msg.groupby('ASUNTO'):
            with st.expander(f"💬 Hilo: {asunto}"):
                for _, msg in grupo.iterrows():
                    st.markdown(f"**{msg.get('REMITENTE', 'ANÓNIMO')}:** {msg.get('MENSAJE', '')}")
                if st.button(f"Responder hilo", key=f"btn_hilo_{asunto}_{rol_contexto}"):
                    st.session_state.asunto_respuesta = asunto
                    st.rerun()

# --- 7. EJECUCIÓN POR ROLES ---

# --- ROL: SUPERVISOR ---
if st.session_state.rol_sel == "SUPERVISOR":
    if st.session_state.sup_autenticado:
        sup_activo_normalizado = st.session_state.user_sel.strip().upper()
        df_objetivos_filtrados = df_objetivos[df_objetivos['SUPERVISOR'] == sup_activo_normalizado] if not df_objetivos.empty else pd.DataFrame()
        
        # MEJORA 1: Métrica y conteo de objetivos del supervisor
        total_objs_sup = len(df_objetivos_filtrados)
        st.markdown(f"### 👤 SUPERVISOR ACTIVO: {sup_activo_normalizado}")
        
        c_m1, c_m2, c_m3 = st.columns(3)
        c_m1.metric("🎯 OBJETIVOS A CARGO", total_objs_sup)
        c_m2.metric("📡 ESTADO DE RED", "ACTIVO")
        c_m3.metric("🕒 HORA LOCAL", obtener_hora_argentina().split(" ")[1])

        st.write("---")
        obj_actual = st.session_state.get("obj_qr_tactico", "SIN OBJETIVO")

        t_vis_qr, t_checklist, t_ruta_gmaps, t_car_tac, t_mensajeria_sup = st.tabs([
            "📱 Visita QR & Flota", "✅ Checklist Custodia", "📲 Ruta GPS", "📝 Carga Táctica", "💬 Mensajeria"
        ])

        with t_vis_qr:
            if not df_objetivos_filtrados.empty:
                obj_select = st.selectbox("Seleccione Objetivo Asignado:", df_objetivos_filtrados['OBJETIVO'].unique(), key="obj_qr_tactico")
                datos_sel = df_objetivos_filtrados[df_objetivos_filtrados['OBJETIVO'] == obj_select].iloc[0]
                
                col_q1, col_q2 = st.columns([1, 2])
                with col_q1:
                    qr = qrcode.QRCode(box_size=6, border=1)
                    qr.add_data(f"OBJETIVO:{obj_select}|ID:{datos_sel.get('ID', '0')}")
                    qr.make(fit=True)
                    st.image(qr.make_image(fill_color="#00E5FF", back_color="black").get_image(), width=150)
                with col_q2:
                    st.markdown(f"**Coordenadas:** {datos_sel.get('LATITUD')}, {datos_sel.get('LONGITUD')}")
                    url_nav = f"https://www.google.com/maps/dir/?api=1&destination={datos_sel.get('LATITUD')},{datos_sel.get('LONGITUD')}&travelmode=driving"
                    st.link_button("🗺️ ABRIR NAVEGACIÓN GOOGLE MAPS", url_nav)
            else:
                st.warning("No tiene objetivos asignados en la base de datos maestra.")

            st.markdown("---")
            st.markdown("### ⛽ CONTROL DE FLOTA")
            with st.form("form_flota_sup", clear_on_submit=True):
                c_a, c_b = st.columns(2)
                v_patente = c_a.text_input("PATENTE / MÓVIL:").upper()
                v_km_ini = c_a.number_input("KM INICIAL:", min_value=0)
                v_km_fin = c_b.number_input("KM FINAL:", min_value=0)
                v_comb = c_b.selectbox("COMBUSTIBLE:", ["NO", "SI - MEDIA CARGA", "SI - TANQUE LLENO"])
                if st.form_submit_button("REGISTRAR ACTA DE FLOTA"):
                    escribir_registro_nube("CONTROL_FLOTA", [obtener_hora_argentina(), sup_activo_normalizado, v_patente, v_km_ini, v_km_fin, v_comb])
                    st.success(f"✅ Acta registrada. Distancia recorrida: {v_km_fin - v_km_ini} km")

        with t_checklist:
            st.markdown("### ✅ CHECKLIST OBLIGATORIO DE VISITA Y CUSTODIA")
            with st.form("form_checklist_custodia"):
                chk_1 = st.checkbox("Revisión de perímetro y accesos principales")
                chk_2 = st.checkbox("Control de libro de actas y novedades del puesto")
                chk_3 = st.checkbox("Verificación de elementos de protección / armamento (si aplica)")
                chk_4 = st.checkbox("Prueba de botón de pánico y comunicación con central")
                obs_checklist = st.text_area("Observaciones de la visita:")
                
                if st.form_submit_button("GUARDAR CHECKLIST DE VISITA"):
                    detalle_chk = f"Perímetro: {chk_1}|Actas: {chk_2}|Equipos: {chk_3}|Pánico: {chk_4}|Obs: {obs_checklist}"
                    escribir_registro_nube("NOVEDADES", [obtener_hora_argentina(), sup_activo_normalizado, f"CHECKLIST-{obj_actual}", detalle_chk])
                    st.success("✅ Checklist de custodia guardado correctamente.")

        with t_ruta_gmaps:
            if not df_objetivos_filtrados.empty:
                obj_r = st.selectbox("DESTINO TÁCTICO:", df_objetivos_filtrados['OBJETIVO'].unique(), key="sup_ruta_target")
                datos_r = df_objetivos_filtrados[df_objetivos_filtrados['OBJETIVO'] == obj_r].iloc[0]
                lat, lon = datos_r['LATITUD'], datos_r['LONGITUD']
                
                dist_min, com_name, com_lat, com_lon = float('inf'), "Ninguna", 0.0, 0.0
                for _, com in df_comisarias.iterrows():
                    d = 6371 * 2 * math.asin(math.sqrt(math.sin((math.radians(com['LATITUD'])-math.radians(lat))/2)**2 + math.cos(math.radians(lat))*math.cos(math.radians(com['LATITUD']))*math.sin((math.radians(com['LONGITUD'])-math.radians(lon))/2)**2))
                    if d < dist_min: dist_min, com_name, com_lat, com_lon = d, com['COMISARIA'], com['LATITUD'], com['LONGITUD']
                
                st.info(f"👮 **Comisaría Cercana:** {com_name} ({dist_min:.2f} Km)")
                st.link_button("🗺️ ABRIR RUTA RÁPIDA", f"https://www.google.com/maps/dir/?api=1&destination={lat},{lon}&travelmode=driving")

        with t_car_tac:
            novedad_sup = st.text_area("Registro Operativo / Novedad:")
            if st.button("CARGAR NOVEDAD") and novedad_sup.strip():
                escribir_registro_nube("NOVEDADES"
