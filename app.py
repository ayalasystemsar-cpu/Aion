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

@st.cache_data(ttl=5) # 5 segundos de TTL para actualización táctica veloz
def leer_matriz_nube(pestana):
    gc = conectar_google()
    if gc:
        try:
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
            todas_filas = hoja.get_all_values()
            
            if not todas_filas or len(todas_filas) == 0:
                return pd.DataFrame()
                
            encabezados = [str(h).strip().upper() for h in todas_filas[0]]
            datos_cuerpo = todas_filas[1:]
            
            if len(datos_cuerpo) == 0:
                return pd.DataFrame(columns=encabezados)
                
            df = pd.DataFrame(datos_cuerpo, columns=encabezados)
            return df
        except Exception as e: 
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
        
        div[data-testid="stMetric"] { background-color: rgba(10, 11, 15, 0.6) !important; border: 1px solid #1A1C23 !important; border-radius: 6px !important; padding: 12px !important; }
        div[data-testid="stMetricLabel"] p { color: #00E5FF !important; font-family: 'Rajdhani', sans-serif !important; font-size: 13px !important; font-weight: bold !important; text-transform: uppercase; letter-spacing: 0.5px; }
        div[data-testid="stMetricValue"] div { color: #FFFFFF !important; font-family: 'Orbitron', sans-serif !important; font-size: 22px !important; }
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
        st.session_state.user_sel = "JEFE DE OPERACIONES"
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
    lat_envio, lon_envio = 0.0, 0.0
    try:
        loc = get_geolocation()
        if loc and isinstance(loc, dict) and 'coords' in loc:
            lat_envio = loc['coords'].get('latitude', 0.0)
            lon_envio = loc['coords'].get('longitude', 0.0)
    except Exception:
        pass

    if st.button("ACTIVAR\nPÁNICO", type="primary"):
        if st.session_state.rol_sel == "SUPERVISOR" and 'sup_servicio_actual' in st.session_state:
            obj_alerta = st.session_state.sup_servicio_actual
        else: obj_alerta = "CENTRAL BASE"
            
        carga_sos = f"LAT:{lat_envio}|LON:{lon_envio}|OBJ:{obj_alerta}|SUP:{st.session_state.user_sel}"
        escribir_registro_nube("ALERTAS", [obtener_hora_argentina(), st.session_state.user_sel, "PÁNICO", "PENDIENTE", carga_sos])
        st.error(f"🚨 S.O.S ENVIADO DESDE {obj_alerta}")



# --- 6. CABECERA CENTRAL ---

# --- ADICIÓN DE SOPORTE POLICIAL COMISARÍAS (COLOCAR ANTES DE CABECERA CENTRAL) ---
@st.cache_data(ttl=60)
def cargar_comisarias():
    df = leer_matriz_nube("COMISARIAS")
    if not df.empty:
        df.columns = df.columns.str.strip().str.upper()
        if 'NOMBRE' in df.columns:
            df = df[df['NOMBRE'].astype(str).str.strip() != ""]
            df = df[df['NOMBRE'].notna()]
        for col in ['LATITUD', 'LONGITUD']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(',', '.').str.strip()
                df[col] = pd.to_numeric(df[col], errors='coerce')
        return df.dropna(subset=['LATITUD', 'LONGITUD'])
    return pd.DataFrame()

def buscar_comisaria_mas_cercana(obj_lat, obj_lon, df_comisarias):
    if df_comisarias.empty: return None, 0.0
    radio_tierra = 6371.0
    comisaria_optima = None
    distancia_minima = float('inf')
    for _, fila in df_comisarias.iterrows():
        lat2, lon2 = fila['LATITUD'], fila['LONGITUD']
        phi1, phi2 = math.radians(obj_lat), math.radians(lat2)
        d_phi = math.radians(lat2 - obj_lat)
        d_lam = math.radians(lon2 - lon1) if 'lon1' in locals() else math.radians(lon2 - obj_lon)
        a = math.sin(d_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lam/2)**2
        c = 2 * math.asin(math.sqrt(a))
        distancia = radio_tierra * c
        if distancia < distancia_minima:
            distancia_minima = distancia
            comisaria_optima = fila
    return comisaria_optima, distancia_minima

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
# A. ROL: MONITOREO
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
    else:
        sos_activos = 0
    
    c1, c2, c3 = st.columns(3)
    c1.metric("🚨 S.O.S ACTIVOS", sos_activos)
    c2.metric("📡 RED", "OPERATIVA")
    c3.metric("🕒 HORA LOCAL", obtener_hora_argentina().split(" ")[1])

    # 1. Declaración limpia de las pestañas tácticas de Monitoreo
    pestanas_mon = st.tabs([
        "🚨 RADAR S.O.S", "📖 LIBRO DE BASE", "💬 CHAT OPERATIVO", "📋 PRESENTISMO GENERAL", "👥 PADRÓN VIGILADORES", "🔄 NOVEDADES GUARDIA"
    ])
    
    # 2. Inyección directa del Mapa y el Formulario en la primera pestaña sin usar "with"
    df_comisarias = cargar_comisarias()
    
    # Extraer de forma segura el listado de pánicos activos desde Google Sheets
    lista_objetivos_en_panico = []
    if not df_emergencias.empty and 'ESTADO' in df_emergencias.columns and 'CARGA_UTIL' in df_emergencias.columns:
        pendientes = df_emergencias[df_emergencias['ESTADO'].astype(str).str.upper() == 'PENDIENTE']
        sos_activos = len(pendientes)
        for _, row in pendientes.iterrows():
            carga = str(row['CARGA_UTIL'])
            if "OBJ:" in carga:
                try:
                    parte_obj = carga.split("OBJ:")
                    objetivo_extraido = parte_obj[1].split("|")[0].strip().upper()
                    lista_objetivos_en_panico.append(objetivo_extraido)
                except Exception:
                    pass
    else:
        sos_activos = 0

    if sos_activos > 0:
        pestanas_mon[0].markdown('<div class="panel-novedad" style="border: 1px solid #FF0000;">', unsafe_allow_html=True)
        df_pendientes_form = df_emergencias[df_emergencias['ESTADO'] == 'PENDIENTE']
        with pestanas_mon[0].form(key="form_finalizar_panico", clear_on_submit=True):
            opciones_alertas = {f"{r['FECHA']} - {r['USUARIO']}": idx for idx, r in df_pendientes_form.iterrows()}
            alerta_seleccionada = st.selectbox("SELECCIONE EVENTO A FINALIZAR:", list(opciones_alertas.keys()))
            txt_informe_cierre = st.text_area("INFORME OPERATIVO DE CIERRE:", placeholder="Describa la resolución...")
            if st.form_submit_button("🚨 FINALIZAR PÁNICO Y NORMALIZAR") and txt_informe_cierre.strip():
                idx_df = opciones_alertas[alerta_seleccionada]
                actualizar_celda("ALERTAS", idx_df + 2, "D", "FINALIZADO")
                actualizar_celda("ALERTAS", idx_df + 2, "F", txt_informe_cierre.strip().upper())
                st.success("✅ Normalizado")
                st.rerun()
        pestanas_mon[0].markdown('</div>', unsafe_allow_html=True)

    pestanas_mon[0].markdown('<div class="radar-box">', unsafe_allow_html=True)
    df_ger_maps = df_objetivos.dropna(subset=['LATITUD', 'LONGITUD']).copy()
    
    if not df_ger_maps.empty:
        df_ger_maps['LATITUD'] = df_ger_maps['LATITUD'].apply(lambda x: -abs(x))
        df_ger_maps['LONGITUD'] = df_ger_maps['LONGITUD'].apply(lambda x: -abs(x))
        centro = [df_ger_maps['LATITUD'].mean(), df_ger_maps['LONGITUD'].mean()]
    else:
        centro = [-34.65, -58.42]
        
    m_visor = folium.Map(location=centro, zoom_start=11, tiles="CartoDB dark_matter")
    
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
    m_visor.get_root().header.add_child(folium.Element(estilo_pulsar_html))

    if not df_ger_maps.empty:
        for _, r in df_ger_maps.iterrows():
            es_panico = r['OBJETIVO'].strip().upper() in lista_objetivos_en_panico
            info_hover = f"🎯 OBJETIVO: {r['OBJETIVO']} | 👤 SUPERVISOR: {r.get('SUPERVISOR', 'NO ASIGNADO')}"
            
            folium.CircleMarker(
                location=[r['LATITUD'], r['LONGITUD']], radius=7,
                color="#FF0000" if es_panico else "#00E5FF",
                fill=True, fill_color="#FF0000" if es_panico else "#00E5FF",
                tooltip=folium.Tooltip(info_hover, sticky=True),
                class_name="marker-panic-pulsing" if es_panico else None
            ).add_to(m_visor)
            
            if es_panico and not df_comisarias.empty:
                comisaria_cerca, dist_km = buscar_comisaria_mas_cercana(r['LATITUD'], r['LONGITUD'], df_comisarias)
                if comisaria_cerca is not None:
                    c_lat = float(comisaria_cerca['LATITUD'])
                    c_lon = float(comisaria_cerca['LONGITUD'])
                    c_nom = comisaria_cerca['NOMBRE']
                    
                    folium.Marker(
                        location=[c_lat, c_lon],
                        popup=f"🚔 SECTOR: {c_nom} ({dist_km:.2f} km)",
                        icon=folium.Icon(color="blue", icon="shield", prefix="fa")
                    ).add_to(m_visor)
                    
                    AntPath(
                        locations=[[c_lat, c_lon], [r['LATITUD'], r['LONGITUD']]],
                        color="#FF0000", pulse_color="#FFFFFF", weight=5, opacity=0.9, delay=600
                    ).add_to(m_visor)
                    
    with pestanas_mon[0]:
        st_folium(m_visor, width="100%", height=550, key="mapa_monitoreo_radar_tactico")
    pestanas_mon[0].markdown('</div>', unsafe_allow_html=True)

    # 3. Resto de las pestañas hijas alineadas usando el formato de lista plano
    with pestanas_mon[1]:
        st.subheader("📖 HISTORIAL DE OPERATIVOS")
        if not df_emergencias.empty: 
            st.dataframe(df_emergencias.iloc[::-1], use_container_width=True)

    with pestanas_mon[2]:
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

    with pestanas_mon[3]:
        st.subheader("📋 TABLA MASTER: PRESENTISMO")
        df_pres = leer_matriz_nube("PRESENTISMO")
        if df_pres is not None and not df_pres.empty:
            df_pres.columns = df_pres.columns.str.strip().str.upper()
            columnas_maestras = ["FECHA", "HORA", "DNI", "NOMBRE Y APE OBJETIVO", "ESTADO", "TIPO DE MARCACION"]
            columnas_validas = [c for c in columnas_maestras if c in df_pres.columns]
            st.dataframe(df_pres[columnas_validas].iloc[::-1], use_container_width=True)
        else:
            st.info("No hay datos de presentismo registrados.")

    with pestanas_mon[4]:
        st.subheader("👥 TABLA MASTER: RELEVOS VIGILADORES")
        df_padrero = leer_matriz_nube("VIGILADORES")
        if df_padrero is not None and not df_padrero.empty:
            df_padrero.columns = df_padrero.columns.str.strip().str.upper()
            columnas_relevos = ["FECHA", "HORA", "OBJETIVO", "VIGILADOR_SALIENTE", "VIGILADOR_ENTRANTE", "SUPERVISOR_ASIGNADO", "ESTADO"]
            columnas_validas_rel = [c for c in columnas_relevos if c in df_padrero.columns]
            st.dataframe(df_padrero[columnas_validas_rel].iloc[::-1], use_container_width=True)
        else:
            st.info("No hay datos en la pestaña de relevos (Vigiladores).")

    with pestanas_mon[5]:
        st.subheader("🔄 TABLA MASTER: NOVEDADES_GUARDIA")
        df_nov_g = leer_matriz_nube("NOVEDADES_GUARDIA")
        if not df_nov_g.empty: 
            df_nov_g.columns = df_nov_g.columns.str.strip().str.upper()
            st.dataframe(df_nov_g.sort_values(by="FECHA", ascending=False), use_container_width=True)


# --- C. ROL: VIGILADOR ---
elif st.session_state.rol_sel == "VIGILADOR":
    st.markdown('<div class="panel-novedad">', unsafe_allow_html=True)
    opciones_globales_obj = df_objetivos['OBJETIVO'].unique() if not df_objetivos.empty else ["ALFAVINIL", "BARRIO EL CAMPO"]
    
    tab_presentismo, tab_relevo = st.tabs([
        "📋 FICHAJE INDIVIDUAL (PRESENTISMO)", 
        "🔄 SANCIONAR RELEVO (CAMBIO DE GUARDIA)"
    ])
    
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
                    
                    # Separación límpida obligatoria de Fecha y Hora
                    fecha_hora_arg = obtener_hora_argentina()
                    fecha_hoy = fecha_hora_arg.split(" ")[0]
                    hora_hoy = fecha_hora_arg.split(" ")[1]
                    
                    # Estructura EXACTA según Captura 1 (Pestaña PRESENTISMO):
                    # FECHA (A) | HORA (B) | DNI (C) | NOMBRE Y APE OBJETIVO (D) | VACIO (E) | ESTADO (F) | TIPO DE MARCACION (G)
                    datos_presentismo = [
                        fecha_hoy,
                        hora_hoy,
                        v_dni,
                        f"{v_apellido} - {v_obj}",
                        "",  # Columna E libre requerida
                        "OK_SISTEMA",
                        v_tipo_marcacion
                    ]
                    
                    exito_pres = escribir_registro_nube("PRESENTISMO", datos_presentismo)
                    
                    # Espejo de auditoría unificado y alineado en NOVEDADES_GUARDIA:
                    # FECHA | OBJETIVO | DNI | TIPO | NOVEDAD | SUPERVISOR
                    escribir_registro_nube("NOVEDADES_GUARDIA", [
                        fecha_hora_arg, v_obj, v_dni, f"FACIAL_{v_tipo_marcacion}", f"OPERARIO: {v_apellido}", sup_responsable
                    ])
                    
                    if exito_pres:
                        st.success(f"🔒 BIOMETRÍA REGISTRADA: Marcación de {v_tipo_marcacion} guardada correctamente.")
                    else:
                        st.error("❌ ERROR DE RED: No se pudo impactar en la planilla de Presentismo.")
                else:
                    st.error("❌ ERROR: Complete todos los campos y la captura facial.")
                    
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
                    
                    # Separación límpida obligatoria de Fecha y Hora
                    fecha_hora_arg = obtener_hora_argentina()
                    fecha_hoy = fecha_hora_arg.split(" ")[0]
                    hora_hoy = fecha_hora_arg.split(" ")[1]
                    
                    # Estructura EXACTA según Captura 2 (Pestaña VIGILADORES):
                    # FECHA (A) | HORA (B) | OBJETIVO (C) | VIGILADOR_SALIENTE (D) | VIGILADOR_ENTRANTE (E) | SUPERVISOR_ASSIGNADO (F) | ESTADO (G)
                    datos_relevo = [
                        fecha_hoy,
                        hora_hoy,
                        v_obj_relevo,
                        vig_saliente,
                        vig_entrante,
                        sup_responsable,
                        "RELEVO_EFECTUADO"
                    ]
                    
                    exito_relevo = escribir_registro_nube("VIGILADORES", datos_relevo)
                    
                    # Espejo unificado y alineado en NOVEDADES_GUARDIA para que no se corran las celdas:
                    # FECHA | OBJETIVO | DNI (O IDENTIFICADOR) | TIPO | NOVEDAD | SUPERVISOR
                    escribir_registro_nube("NOVEDADES_GUARDIA", [
                        fecha_hora_arg, v_obj_relevo, "RELEVO_S/D", "CAMBIO_GUARDIA", f"SALE: {vig_saliente} | ENTRA: {vig_entrante}", sup_responsable
                    ])
                    
                    if exito_relevo:
                        st.success(f"⚡ RELEVO SANCIONADO: Registro guardado en la pestaña Vigiladores.")
                    else:
                        st.error("❌ ERROR DE RED: No se pudo impactar el relevo.")
                else:
                    st.error("❌ ERROR: Complete los campos de personal saliente y entrante.")
    st.markdown('</div>', unsafe_allow_html=True)

# --- D. JEFE DE OPERACIONES ---
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
        df_obj_maps_jefe = df_objetivos.dropna(subset=['LATITUD', 'LONGITUD'])
        centro = [df_obj_maps_jefe['LATITUD'].mean(), df_obj_maps_jefe['LONGITUD'].mean()] if not df_obj_maps_jefe.empty else [-34.6, -58.4]
        m_visor = folium.Map(location=centro, zoom_start=12, tiles="CartoDB dark_matter")
        if not df_obj_maps_jefe.empty:
            for _, r in df_obj_maps_jefe.iterrows():
                folium.Marker([r['LATITUD'], r['LONGITUD']], tooltip=r['OBJETIVO'], icon=folium.Icon(color="blue", icon="shield", prefix="fa")).add_to(m_visor)
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
        st.markdown('</div>', unsafe_allow_html=True)

    with t_auditoria:
        st.subheader("📋 REPORTE DE MOVIMIENTOS")
        df_novedades = leer_matriz_nube("ACTAS_FLOTAS")
        if not df_novedades.empty: st.dataframe(df_novedades.tail(20), use_container_width=True)

# --- E. GERENCIA ---
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

# H. ROL: ADMINISTRADOR
elif st.session_state.rol_sel == "ADMINISTRADOR":
    u_ing = st.text_input("ADMIN_USER")
    p_ing = st.text_input("ADMIN_PASS", type="password")
    if u_ing == "admin" and p_ing == "aion2026": st.success("Núcleo Maestro desbloqueado.")
