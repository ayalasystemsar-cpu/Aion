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
    except: 
        return None

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
    except: 
        return False

def escribir_registro_nube(pestana, datos_fila):
    try:
        gc = conectar_google()
        if gc:
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
            hoja.append_row(datos_fila)
            return True
    except: 
        return False
        
@st.cache_resource
def obtener_grafo_zona(lat, lon):
    try:
        # Aumentamos el radio a 5000m para asegurar cobertura entre puntos
        return ox.graph_from_point((lat, lon), dist=5000, network_type='drive')
    except:
        return None

def calcular_ruta_real(orig, dest):
    # Intentamos obtener el grafo basado en el punto medio
    mid_lat = (orig[0] + dest[0]) / 2
    mid_lon = (orig[1] + dest[1]) / 2
    G = obtener_grafo_zona(mid_lat, mid_lon)
    
    if G is None: 
        return [orig, dest] # Si falla, devuelve línea recta como seguridad
        
    try:
        orig_node = ox.distance.nearest_nodes(G, X=orig[1], Y=orig[0])
        dest_node = ox.distance.nearest_nodes(G, X=dest[1], Y=dest[0])
        ruta = nx.shortest_path(G, orig_node, dest_node, weight='length')
        return [(G.nodes[n]['y'], G.nodes[n]['x']) for n in ruta]
    except:
        return [orig, dest]

# --- SE REMOVIÓ EL TTL=5 QUE HACÍA QUE LA PÁGINA SE ACTUALIZARA SOLA TODO EL TIEMPO ---
@st.cache_data(ttl=60) 
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
def cargar_datos_comisarias():
    data = {
        "COMISARIA": ["COMISARÍA SAN MARTÍN 1RA", "COMISARÍA VECINAL 14C", "COMISARÍA AVELLANEDA 1RA", "COMISARÍA CAMPANA 1RA", "COMISARÍA SAN FERNANDO 1RA", "COMISARÍA TIGRE 1RA", "COMISARÍA PILAR 6TA (VILLA ROSA)", "COMISARÍA VECINAL 1B", "COMISARÍA VECINAL 14A", "COMISARÍA LANÚS 2DA", "COMISARÍA VECINAL 13A", "COMISARÍA LA MATANZA 2DA", "COMISARÍA LA MATANZA 3RA", "COMISARÍA VECINAL 2A", "COMISARÍA VECINAL 12A", "COMISARÍA VECINAL 12B", "COMISARÍA VECINAL 6A", "COMISARÍA VECINAL 1D", "COMISARÍA RAMOS MEJÍA 2DA"],
        "LATITUD": [-34.580139, -34.587773, -34.664119, -34.163693, -34.440154, -34.424196, -34.417041, -34.617133, -34.587773, -34.708819, -34.557454, -34.700147, -34.717182, -34.589886, -34.554321, -34.568459, -34.613045, -34.603847, -34.646589],
        "LONGITUD": [-58.541410, -58.416056, -58.368073, -58.961418, -58.556134, -58.579789, -58.868209, -58.378734, -58.416056, -58.385311, -58.461144, -58.575608, -58.608301, -58.401918, -58.472147, -58.482012, -58.437198, -58.381577, -58.564571]
    }
    return pd.DataFrame(data)

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
            color: #00E5FF !important; font-size: 24px; margin-top: 15px;
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
        
        /* --- ESTILO DE PARPADEO MEJORADO PARA EL RADAR --- */
        @keyframes parpadeo-radar {
            0% { transform: scale(0.9); opacity: 1; box-shadow: 0 0 0 0 rgba(255, 0, 0, 0.7); }
            70% { transform: scale(1.1); opacity: 0.8; box-shadow: 0 0 0 15px rgba(255, 0, 0, 0); }
            100% { transform: scale(0.9); opacity: 1; box-shadow: 0 0 0 0 rgba(255, 0, 0, 0); }
        }
        .marcador-panico {
            background-color: #FF0000;
            width: 14px; height: 14px;
            border-radius: 50%;
            border: 2px solid white;
            animation: parpadeo-radar 1s infinite;
            display: inline-block;
        }
        </style>
        """, unsafe_allow_html=True
    )

aplicar_identidad_alfa()

# --- 5. SIDEBAR TÁCTICO ---
df_objetivos = cargar_objetivos()
df_comisarias = cargar_datos_comisarias()
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
# A. ROL: MONITOREO
if st.session_state.rol_sel == "MONITOREO":
    df_emergencias = leer_matriz_nube("ALERTAS")
    df_objetivos = cargar_objetivos()
    
    if df_emergencias.empty:
        df_emergencias = pd.DataFrame(columns=['FECHA', 'USUARIO', 'TIPO', 'ESTADO', 'CARGA_UTIL', 'INFORME'])
    else:
        df_emergencias.columns = df_emergencias.columns.str.strip().str.upper()

    df_mapa_monitoreo = pd.DataFrame()
    if not df_objetivos.empty:
        df_objetivos.columns = df_objetivos.columns.str.strip().str.upper()
        if 'LATITUD' in df_objetivos.columns and 'LONGITUD' in df_objetivos.columns:
            df_mapa_monitoreo = df_objetivos.dropna(subset=['LATITUD', 'LONGITUD']).copy()

    lista_objetivos_en_panico = []
    if 'ESTADO' in df_emergencias.columns and 'CARGA_UTIL' in df_emergencias.columns:
        pendientes = df_emergencias[df_emergencias['ESTADO'].astype(str).str.upper() == 'PENDIENTE']
        sos_activos = len(pendientes)
        for _, row in pendientes.iterrows():
            carga = str(row['CARGA_UTIL'])
            if "OBJ:" in carga:
                try: 
                    lista_objetivos_en_panico.append(carga.split("OBJ:")[1].split("|")[0].strip().upper())
                except: pass
    else: 
        sos_activos = 0
    
    c1, c2, c3 = st.columns(3)
    c1.metric("🚨 S.O.S ACTIVOS", sos_activos)
    c2.metric("📡 RED", "OPERATIVA")
    c3.metric("🕒 HORA LOCAL", obtener_hora_argentina().split(" ")[1])

    t_radar, t_gestion, t_comunicacion, t_pres, t_vig, t_guardia = st.tabs([
        "🚨 RADAR S.O.S", "📖 LIBRO DE BASE", "💬 CHAT OPERATIVO", "📋 PRESENTISMO GENERAL", "👥 PADRÓN VIGILADORES", "🔄 NOVEDADES GUARDIA"
    ])

    with t_radar:
        st.subheader("📡 RADAR GLOBAL DE OBJETIVOS")
        
        # Botón manual de refresco estratégico para control del operador sin interrupciones arbitrarias
        if st.button("🔄 ACTUALIZAR RADAR DE CONTROL", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        # --- INTERFAZ DE SELECCIÓN Y ANÁLISIS TÁCTICO ---
        st.markdown('<div class="panel-novedad">', unsafe_allow_html=True)
        col_sel1, col_sel2 = st.columns([2, 1])
        
        with col_sel1:
            opciones_busqueda = ["MOSTRAR TODO"] + list(df_mapa_monitoreo['OBJETIVO'].unique()) if not df_mapa_monitoreo.empty else ["MOSTRAR TODO"]
            obj_seleccionado = st.selectbox("🎯 ENFOCAR OBJETIVO EN RADAR / BUSCADOR:", opciones_busqueda)
        
        # Lógica para encontrar la comisaría más cercana mediante Haversine
        comisaria_cercana_name = None
        distancia_minima = float('inf')
        
        if obj_seleccionado != "MOSTRAR TODO" and not df_mapa_monitoreo.empty:
            datos_obj = df_mapa_monitoreo[df_mapa_monitoreo['OBJETIVO'] == obj_seleccionado].iloc[0]
            lat_obj = datos_obj['LATITUD']
            lon_obj = datos_obj['LONGITUD']
            
            # Buscar la más cercana entre las comisarías cargadas
            for _, com in df_comisarias.iterrows():
                # Fórmula de Haversine para cálculo de distancia en Km
                lon1, lat1, lon2, lat2 = map(math.radians, [lon_obj, lat_obj, com['LONGITUD'], com['LATITUD']])
                dlon = lon2 - lon1
                dlat = lat2 - lat1
                a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
                c = 2 * math.asin(math.sqrt(a))
                km = 6371 * c
                
                if km < distancia_minima:
                    distancia_minima = km
                    comisaria_cercana_name = com['COMISARIA']
            
            with col_sel2:
                st.metric(label="👮 COMISARÍA MÁS CERCANA", value=comisaria_cercana_name if comisaria_cercana_name else "N/A")
                st.caption(f"Distancia estimada: {distancia_minima:.2f} Km")
        else:
            with col_sel2:
                st.info("Seleccione un objetivo específico para calcular la comisaría más cercana.")
        st.markdown('</div>', unsafe_allow_html=True)

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
        if not df_mapa_monitoreo.empty:
            # Si hay un objetivo seleccionado, centramos el mapa directamente ahí
            if obj_seleccionado != "MOSTRAR TODO":
                datos_obj = df_mapa_monitoreo[df_mapa_monitoreo['OBJETIVO'] == obj_seleccionado].iloc[0]
                centro_mapa = [datos_obj['LATITUD'], datos_obj['LONGITUD']]
                zoom_inicial = 14 # Hacemos zoom táctico sobre el objetivo
            else:
                centro_mapa = [df_mapa_monitoreo['LATITUD'].mean(), df_mapa_monitoreo['LONGITUD'].mean()]
                zoom_inicial = 11

            m_mon = folium.Map(location=centro_mapa, zoom_start=zoom_inicial, tiles="CartoDB dark_matter")
            
            for _, r in df_mapa_monitoreo.iterrows():
                es_panico = r['OBJETIVO'] in lista_objetivos_en_panico
                es_el_seleccionado = (r['OBJETIVO'] == obj_seleccionado)
                
                # REGLA VISUAL: Si está en pánico O es el seleccionado en el buscador -> ROJO TITILANDO CON REGLA CSS INJECT
                if es_panico or es_el_seleccionado:
                    folium.Marker(
                        location=[r['LATITUD'], r['LONGITUD']],
                        tooltip=f"🚨 {'[EN ENFOQUE TÁCTICO]' if es_el_seleccionado else '¡ALERTA PÁNICO!'} | {r['OBJETIVO']} | 👤 SUP: {r.get('SUPERVISOR', 'N/A')}",
                        icon=folium.DivIcon(
                            icon_size=(30, 30),
                            icon_anchor=(15, 15),
                            html='''
                            <div style="
                                background-color: #FF0000;
                                width: 16px;
                                height: 16px;
                                border-radius: 50%;
                                border: 2px solid white;
                                box-shadow: 0 0 10px #FF0000;
                                animation: pulse 1s infinite alternate;
                            "></div>
                            <style>
                                @keyframes pulse {
                                    0% { transform: scale(0.8); box-shadow: 0 0 0 0 rgba(255, 0, 0, 0.7); }
                                    100% { transform: scale(1.2); box-shadow: 0 0 0 12px rgba(255, 0, 0, 0); }
                                }
                            </style>
                            '''
                        )
                    ).add_to(m_mon)
                else:
                    # Tus círculos celestes normales de siempre
                    folium.CircleMarker(
                        location=[r['LATITUD'], r['LONGITUD']], 
                        radius=7,
                        color="#00E5FF",
                        fill=True, 
                        fill_color="#00E5FF",
                        tooltip=f"🎯 {r['OBJETIVO']} | 👤 SUP: {r.get('SUPERVISOR', 'N/A')}"
                    ).add_to(m_mon)
                    
# Asegúrate de que este if esté alineado con el código anterior
        if obj_seleccionado != "MOSTRAR TODO": 
            # El for debe estar un nivel a la derecha
            df_com = cargar_datos_comisarias()
            for _, c in df_com.iterrows():
                es_la_mas_cercana = (c['COMISARIA'] == comisaria_cercana_name)
                
                if es_la_mas_cercana:
                    color_icono = "#FF9800"
                    tamano_fuente = "26px"
                    sufijo_tooltip = " 🌟 [MÁS CERCANA AL OBJETIVO]"
                    
                    # Cálculo de la ruta
                    coordenadas_ruta = calcular_ruta_real([lat_obj, lon_obj], [c['LATITUD'], c['LONGITUD']])
                    
                    folium.PolyLine(
                        locations=coordenadas_ruta,
                        color="#7CFC00",  # Verde cálido
                        weight=5,
                        opacity=0.7
                    ).add_to(m_mon)
                else:
                    color_icono = "#0000FF"
                    tamano_fuente = "20px"
                    sufijo_tooltip = ""

                # Marcador de la comisaría
                folium.Marker(
                    location=[c['LATITUD'], c['LONGITUD']],
                    tooltip=f"👮 {c['COMISARIA']}{sufijo_tooltip}",
                    icon=folium.DivIcon(html=f"""<div style="font-size: {tamano_fuente}; color: {color_icono}; text-shadow: 0 0 10px {color_icono};"><i class="fa fa-shield"></i></div>""")
                ).add_to(m_mon)
            
            # st_folium debe estar al mismo nivel que el for
            st_folium(m_mon, width="100%", height=550, key="mapa_monitoreo_radar_tactico")
    with t_gestion:
        st.subheader("📖 HISTORIAL DE OPERATIVOS")
        if not df_emergencias.empty:
            st.dataframe(df_emergencias.iloc[::-1], use_container_width=True)

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
        if df_pres is not None and not df_pres.empty:
            df_pres.columns = df_pres.columns.str.strip().str.upper()
            columnas_maestras = ["FECHA", "HORA", "DNI", "NOMBRE Y APE OBJETIVO", "ESTADO", "TIPO DE MARCACION"]
            columnas_validas = [c for c in columnas_maestras if c in df_pres.columns]
            st.dataframe(df_pres[columnas_validas].iloc[::-1], use_container_width=True)
        else:
            st.info("No hay datos de presentismo registrados.")

    with t_vig:
        st.subheader("👥 TABLA MASTER: RELEVOS VIGILADORES")
        df_padrero = leer_matriz_nube("VIGILADORES")
        if df_padrero is not None and not df_padrero.empty:
            df_padrero.columns = df_padrero.columns.str.strip().str.upper()
            columnas_relevos = ["FECHA", "HORA", "OBJETIVO", "VIGILADOR_SALIENTE", "VIGILADOR_ENTRANTE", "SUPERVISOR_ASIGNADO", "ESTADO"]
            columnas_validas_rel = [c for c in columnas_relevos if c in df_padrero.columns]
            st.dataframe(df_padrero[columnas_validas_rel].iloc[::-1], use_container_width=True)
        else:
            st.info("No hay datos en la pestaña de relevos (Vigiladores).")

    with t_guardia:
        st.subheader("🔄 TABLA MASTER: NOVEDADES_GUARDIA")
        df_nov_g = leer_matriz_nube("NOVEDADES_GUARDIA")
        if not df_nov_g.empty: 
            df_nov_g.columns = df_nov_g.columns.str.strip().str.upper()
            st.dataframe(df_nov_g.sort_values(by="FECHA", ascending=False), use_container_width=True)

# Resto de los roles mapeados de forma regular para mantener la integridad exacta del sistema...

elif st.session_state.rol_sel == "SUPERVISOR":
    if st.session_state.sup_autenticado:
        
        # --- BOTÓN DE PÁNICO IDENTICO AL SIDEBAR ---
        col_p1, col_p2, col_p3 = st.columns([1, 1, 1])
        with col_p2:
            if st.button("ACTIVAR\nPÁNICO", type="primary", use_container_width=True):
                lat_envio, lon_envio = 0.0, 0.0
                try:
                    loc = get_geolocation()
                    if loc and isinstance(loc, dict) and 'coords' in loc:
                        lat_envio = loc['coords'].get('latitude', 0.0)
                        lon_envio = loc['coords'].get('longitude', 0.0)
                except: pass
                
                obj_alerta = st.session_state.sup_servicio_actual if 'sup_servicio_actual' in st.session_state else "SUPERVISOR"
                carga_sos = f"LAT:{lat_envio}|LON:{lon_envio}|OBJ:{obj_alerta}|SUP:{st.session_state.user_sel}"
                escribir_registro_nube("ALERTAS", [obtener_hora_argentina(), st.session_state.user_sel, "PÁNICO", "PENDIENTE", carga_sos])
                st.error(f"🚨 S.O.S ENVIADO DESDE {obj_alerta}")

        # --- LÓGICA DE CONTROL ---
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

        t_vis_qr, t_car_tac, t_com_sup, t_pres_sup = st.tabs(["Visita QR", "Carga Táctica", "💬 CHAT OPERATIVO", "📋 NOVEDADES Y RELEVOS"])
        
        with t_vis_qr:
            opciones_servicios = df_objetivos_filtrados['OBJETIVO'].unique() if not df_objetivos_filtrados.empty else ["SIN OBJETIVOS"]
            obj_seleccionado_sup = st.selectbox("SERVICIO ACTUAL:", opciones_servicios, key="sup_servicio_actual")
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
            st.markdown("### 📋 NOVEDADES DE MI GRUPO ASIGNADO")
            df_v_total = leer_matriz_nube("NOVEDADES_GUARDIA")
            if not df_v_total.empty:
                df_v_total.columns = df_v_total.columns.str.strip().str.upper()
                
                def fila_pertenece_a_supervisor(row, sup_name):
                    for cell_val in row.values:
                        if str(cell_val).strip().upper() == sup_name: return True
                    return False
                
                mask_sup = df_v_total.apply(lambda r: fila_pertenece_a_supervisor(r, sup_activo_normalizado), axis=1)
                df_v_filtrado = df_v_total[mask_sup]
                if not df_v_filtrado.empty:
                    st.dataframe(df_v_filtrado.sort_values(by="FECHA", ascending=False), use_container_width=True)
                else:
                    st.info(f"Sin registros asignados para {sup_activo_normalizado} en este turno.")
            else:
                st.info("No hay datos registrados en Novedades Guardia.")

elif st.session_state.rol_sel == "VIGILADOR":
    st.markdown('<div class="panel-novedad">', unsafe_allow_html=True)
    opciones_globales_obj = df_objetivos['OBJETIVO'].unique() if not df_objetivos.empty else ["ALFAVINIL", "BARRIO EL CAMPO"]
    
    tab_presentismo, tab_relevo = st.tabs(["📋 FICHAJE INDIVIDUAL (PRESENTISMO)", "🔄 SANCIONAR RELEVO (CAMBIO DE GUARDIA)"])
    
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
                    
                    datos_presentismo = [fecha_hoy, hora_hoy, v_dni, f"{v_apellido} - {v_obj}", "", "OK_SISTEMA", v_tipo_marcacion]
                    exito_pres = escribir_registro_nube("PRESENTISMO", datos_presentismo)
                    
                    escribir_registro_nube("NOVEDADES_GUARDIA", [fecha_hora_arg, v_obj, v_dni, f"FACIAL_{v_tipo_marcacion}", f"OPERARIO: {v_apellido}", sup_responsable])
                    if exito_pres: st.success(f"🔒 BIOMETRÍA REGISTRADA.")
                    else: st.error("❌ ERROR DE RED")
                else: st.error("❌ ERROR: Complete todos los campos.")
                    
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
                    fecha_hoy = fecha_hora_arg.split(" ")[0]
                    hora_hoy = fecha_hora_arg.split(" ")[1]
                    
                    datos_relevo = [fecha_hoy, hora_hoy, v_obj_relevo, vig_saliente, vig_entrante, sup_responsable, "RELEVO_EFECTUADO"]
                    exito_relevo = escribir_registro_nube("VIGILADORES", datos_relevo)
                    
                    escribir_registro_nube("NOVEDADES_GUARDIA", [fecha_hora_arg, v_obj_relevo, "RELEVO_S/D", "CAMBIO_GUARDIA", f"SALE: {vig_saliente} | ENTRA: {vig_entrante}", sup_responsable])
                    if exito_relevo: st.success(f"⚡ RELEVO SANCIONADO.")
                    else: st.error("❌ ERROR DE RED")
    st.markdown('</div>', unsafe_allow_html=True)

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
    if u_ing == "admin" and p_ing == "aion2026": st.success("Núcleo Maestro desbloqueado.")
