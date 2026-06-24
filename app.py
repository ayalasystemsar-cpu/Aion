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
import requests # Importante para conectar con el servidor de mapas de calles
from branca.element import Element # Para inyección de z-index nativo seguro

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

# --- 3. FUNCIONES DE LÓGICA E DATOS ---
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
        return ox.graph_from_point((lat, lon), dist=5000, network_type='drive')
    except:
        return None

def calcular_ruta_real(orig, dest):
    mid_lat = (orig[0] + dest[0]) / 2
    mid_lon = (orig[1] + dest[1]) / 2
    G = obtener_grafo_zona(mid_lat, mid_lon)
    
    if G is None: 
        return [orig, dest]
        
    try:
        orig_node = ox.distance.nearest_nodes(G, X=orig[1], Y=orig[0])
        dest_node = ox.distance.nearest_nodes(G, X=dest[1], Y=dest[0])
        ruta = nx.shortest_path(G, orig_node, dest_node, weight='length')
        return [(G.nodes[n]['y'], G.nodes[n]['x']) for n in ruta]
    except:
        return [orig, dest]

# Función dedicada a obtener el trazado exacto calle por calle vía OSRM (Estilo GPS)
def obtener_ruta_calles_osrm(lat1, lon1, lat2, lon2):
    try:
        url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=full&geometries=geojson"
        response = requests.get(url, timeout=5).json()
        if response.get("code") == "Ok":
            coordenadas = response["routes"][0]["geometry"]["coordinates"]
            return [[point[1], point[0]] for point in coordenadas]
    except:
        pass
    return [[lat1, lon1], [lat2, lon2]]

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
            
            df = pd.DataFrame(datos_cuerpo, columns=encabezados)
            
            # --- BLINDAJE CONTRA DUPLICADOS ---
            # 1. Quitar espacios accidentales
            df.columns = [str(c).strip().upper() for c in df.columns]
            # 2. Eliminar columnas duplicadas (mantiene la primera ocurrencia)
            df = df.loc[:, ~df.columns.duplicated()]
            
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
    
@st.cache_data(ttl=10) # TTL corto para ver mensajes en tiempo real
def contar_mensajes_nuevos(rol_usuario):
    df = leer_matriz_nube("MENSAJERIA")
    if df.empty:
        return 0
    
    # Filtramos: Destino coincide con el rol Y el estado es PENDIENTE
    # (Asegúrate de que 'PENDIENTE' esté escrito tal cual en tu Excel)
    pendientes = df[
        (df['DESTINATARIO'].str.strip().str.upper() == rol_usuario.upper()) & 
        (df['ESTADO'].str.strip().str.upper() == "PENDIENTE")
    ]
    return len(pendientes)
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
        
        /* Estilo para botón de Google Maps */
        .btn-google-maps {
            display: inline-flex; align-items: center; justify-content: center;
            background-color: #ffffff !important; color: #1a73e8 !important;
            font-family: 'Orbitron', sans-serif; font-weight: bold; font-size: 14px;
            padding: 12px 24px; border-radius: 6px; border: 2px solid #1a73e8;
            text-decoration: none !important; box-shadow: 0 4px 15px rgba(26, 115, 232, 0.3);
            width: 100%; text-align: center; margin-top: 10px; transition: 0.3s;
        }
        .btn-google-maps:hover { background-color: #1a73e8 !important; color: white !important; }
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

    # --- PASO 3: Pestaña Dinámica ---
    
    total_nuevos = contar_mensajes_nuevos(st.session_state.rol_sel)
    label_mensajeria = f"💬 CHAT ({total_nuevos})" if total_nuevos > 0 else "💬 CHAT"

    # Ahora usamos la variable label_mensajeria en lugar del nombre fijo
    t_radar, t_comunicacion, t_vig, t_nov = st.tabs([
        "🚨 RADAR S.O.S", label_mensajeria, "👥 PADRÓN VIGILADORES", "🔄 NOVEDADES Y FICHAJES"
    ])
# --- INTERFAZ DE SELECCIÓN Y ANÁLISIS TÁCTICO ---
st.markdown('<div class="panel-novedad">', unsafe_allow_html=True)
col_sel1, col_sel2 = st.columns([2, 1])

if "filtro_radar_valor" not in st.session_state:
    st.session_state["filtro_radar_valor"] = "MOSTRAR TODO"
with col_sel1:
            try:
                idx_defecto = opciones_busqueda.index(st.session_state["filtro_radar_valor"])
            except:
                idx_defecto = 0
            
            # --- SELECCIONADOR LIMPIO ---
            obj_seleccionado = st.selectbox(
                "🎯 ENFOCAR OBJETIVO EN RADAR / BUSCADOR:", 
                opciones_busqueda, 
                index=idx_defecto,
                key="buscador_radar_master"
            )
st.session_state["filtro_radar_valor"] = obj_seleccionado

            # --- ESTAS LÍNEAS DEBEN TENER EXACTAMENTE 8 ESPACIOS ---
            comisaria_cercana_name = None
            distancia_minima = float('inf')
            com_lat_m, com_lon_m = None, None
            
            # El siguiente IF debe estar al mismo nivel que las líneas anteriores
            if obj_seleccionado != "MOSTRAR TODO" and not df_mapa_monitoreo.empty:
                datos_obj = df_mapa_monitoreo[df_mapa_monitoreo['OBJETIVO'] == obj_seleccionado].iloc[0]
                lat_obj = datos_obj['LATITUD']
                lon_obj = datos_obj['LONGITUD']
                
                # Este FOR debe tener 12 espacios (4 más que el IF)
                for _, com in df_comisarias.iterrows():
                    # ... (el resto de tu código de cálculo)
                lon1, lat1, lon2, lat2 = map(math.radians, [lon_obj, lat_obj, com['LONGITUD'], com['LATITUD']])
                dlon = lon2 - lon1
                dlat = lat2 - lat1
                a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
                c = 2 * math.asin(math.sqrt(a))
                km = 6371 * c
                
                if km < distancia_minima:
                    distancia_minima = km
                    comisaria_cercana_name = com['COMISARIA']
                    com_lat_m = com['LATITUD']
                    com_lon_m = com['LONGITUD']
            
            with col_sel2:
                st.metric(label="👮 COMISARÍA MÁS CERCANA", value=comisaria_cercana_name if comisaria_cercana_name else "N/A")
                st.caption(f"Distancia estimada: {distancia_minima:.2f} Km")
                
                if comisaria_cercana_name:
                    url_gmaps_monitoreo = f"https://www.google.com/maps/dir/?api=1&origin={com_lat_m},{com_lon_m}&destination={lat_obj},{lon_obj}&travelmode=driving"
                    st.markdown(
                        f'<a href="{url_gmaps_monitoreo}" target="_blank" class="btn-google-maps" style="font-size:11px; padding:6px 12px; margin-top:5px;">🗺️ ASISTENTE GPS COMPARTIDO</a>',
                        unsafe_allow_html=True
                    )
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
                    
                    st.session_state["filtro_radar_valor"] = "MOSTRAR TODO"
                    st.success("✅ Normalizado")
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
   
        st.markdown('<div class="radar-box">', unsafe_allow_html=True)
        if not df_mapa_monitoreo.empty:
            if obj_seleccionado != "MOSTRAR TODO":
                datos_obj = df_mapa_monitoreo[df_mapa_monitoreo['OBJETIVO'] == obj_seleccionado].iloc[0]
                centro_mapa = [datos_obj['LATITUD'], datos_obj['LONGITUD']]
                zoom_inicial = 13
            else:
                centro_mapa = [df_mapa_monitoreo['LATITUD'].mean(), df_mapa_monitoreo['LONGITUD'].mean()]
                zoom_inicial = 11

            m_mon = folium.Map(
                location=centro_mapa, 
                zoom_start=zoom_inicial, 
                max_zoom=21,
                tiles="https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}{r}.png",
                attr='© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors © <a href="https://carto.com/attributions">CARTO</a>'
            )
            
            for _, r in df_mapa_monitoreo.iterrows():
                es_panico = r['OBJETIVO'] in lista_objetivos_en_panico
                es_el_seleccionado = (r['OBJETIVO'] == obj_seleccionado)
                
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
                    folium.CircleMarker(
                        location=[r['LATITUD'], r['LONGITUD']], 
                        radius=7,
                        color="#00E5FF",
                        fill=True, 
                        fill_color="#00E5FF",
                        tooltip=f"🎯 {r['OBJETIVO']} | 👤 SUP: {r.get('SUPERVISOR', 'N/A')}"
                    ).add_to(m_mon)
            
        df_com = cargar_datos_comisarias()
        for _, c in df_com.iterrows():
            es_la_mas_cercana = (c['COMISARIA'] == comisaria_cercana_name)
            
            if es_la_mas_cercana and obj_seleccionado != "MOSTRAR TODO":
                color_icono = "#FF9800"
                tamano_fuente = "26px"
                sufijo_tooltip = " 🌟 [MÁS CERCANA AL OBJETIVO]"
                
                com_lat, com_lon = c['LATITUD'], c['LONGITUD']
                coordenadas_ruta = obtener_ruta_calles_osrm(lat_obj, lon_obj, com_lat, com_lon)
                
                # --- SÁNDWICH DE CONTRASTE TRANSLÚCIDO ---
                folium.PolyLine(
                    locations=coordenadas_ruta,
                    color="#000000",
                    weight=5,
                    opacity=0.4
                ).add_to(m_mon)

                folium.PolyLine(
                    locations=coordenadas_ruta,
                    color="#39FF14",       
                    weight=4,              
                    opacity=0.25           
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
        
        capa_etiquetas = folium.TileLayer(
            tiles="https://{s}.basemaps.cartocdn.com/dark_only_labels/{z}/{x}/{y}{r}.png",
            attr='© <a href="https://carto.com/attributions">CARTO</a>',
            name="Etiquetas de Calles",
            max_zoom=21,         
            max_native_zoom=20,  
            overlay=True,
            control=False
        )
        capa_etiquetas.add_to(m_mon)
        
        script_z_index = Element("""
            <style>
                .leaflet-pane.leaflet-overlay-pane { z-index: 400 !important; }
                .leaflet-pane.leaflet-tile-pane { z-index: 200 !important; }
                .leaflet-layer:nth-last-child(1) { z-index: 500 !important; pointer-events: none; }
            </style>
        """)
        m_mon.get_root().header.add_child(script_z_index)
        
        st_folium(m_mon, width="100%", height=550, key="mapa_monitoreo_radar_tactico"
    with t_comunicacion:
        st.subheader("💬 CENTRO DE MENSAJES")
        
        # 1. Selector de destinatario
        destinatarios = ["TODOS", "JEFE DE OPERACIONES", "MONITOREO", "SUPERVISORES", "VIGILADORES"]
        destino_sel = st.selectbox("ENVIAR MENSAJE A:", destinatarios)
        
        with st.form(key="form_chat_mensajeria", clear_on_submit=True):
            txt_mensaje = st.text_input("ESCRIBIR MENSAJE:")
            prioridad = st.selectbox("CRITICIDAD:", ["VERDE", "ROJA"])
            
            if st.form_submit_button("TRANSMITIR"):
                if txt_mensaje.strip():
                    # Aquí escribimos en la pestaña "MENSAJERIA" de tu Excel
                    # La estructura debe coincidir con tus columnas: 
                    # [FECHA, REMITENTE, DESTINATARIO, ASUNTO, MENSAJE, ESTADO, GRAVEDAD]
                    escribir_registro_nube("MENSAJERIA", [
                        obtener_hora_argentina(), 
                        st.session_state.user_sel, 
                        destino_sel, 
                        "GENERAL", 
                        txt_mensaje.strip().upper(), 
                        "PENDIENTE", # <--- ESTO ACTIVA TU CONTADOR
                        prioridad
                    ])
                    st.rerun()
        
        # 2. Visualización
        df_mensajes = leer_matriz_nube("MENSAJERIA")
        if not df_mensajes.empty:
            # Filtro para ver solo lo que le corresponde al rol actual o lo que es para TODOS
            df_filtrado = df_mensajes[
                (df_mensajes['DESTINATARIO'].str.upper() == "TODOS") | 
                (df_mensajes['DESTINATARIO'].str.upper() == st.session_state.rol_sel)
            ]
            
            for _, msg in df_filtrado.tail(15).iloc[::-1].iterrows():
                st.markdown(f'''
                    <div class="{"message-box-red" if msg.get("GRAVEDAD")=="ROJA" else "message-box"}">
                        <div class="message-info">{msg.get("FECHA")} | Para: {msg.get("DESTINATARIO")}</div>
                        <div class="message-text"><b>{msg.get("REMITENTE")}:</b> {msg.get("MENSAJE")}</div>
                    </div>
                ''', unsafe_allow_html=True)
    with t_vig:
        st.subheader("👥 PADRÓN VIGILADORES")
        df_padrero = leer_matriz_nube("VIGILADORES")
        if not df_padrero.empty:
            df_padrero.columns = df_padrero.columns.str.strip().str.upper()
            st.dataframe(df_padrero.iloc[::-1], use_container_width=True)
        else:
            st.info("No hay datos en la pestaña de relevos (Vigiladores).")
            
    with t_nov:
        st.subheader("🔄 HISTORIAL: NOVEDADES, FICHAJES Y RELEVOS")
        df_nov_g = leer_matriz_nube("NOVEDADES_GUARDIA")
        
        if not df_nov_g.empty:
            df_nov_g.columns = [str(c).strip().upper() for c in df_nov_g.columns]
            df_nov_g = df_nov_g.loc[:, ~df_nov_g.columns.duplicated()]
            
            if 'FECHA' in df_nov_g.columns:
                df_nov_g['FECHA_ORDEN'] = pd.to_datetime(df_nov_g['FECHA'], errors='coerce')
                df_ordenado = df_nov_g.sort_values(by='FECHA_ORDEN', ascending=False).drop(columns=['FECHA_ORDEN'])
            else:
                df_ordenado = df_nov_g
            
            st.dataframe(df_ordenado, use_container_width=True, hide_index=True)
        else:
            st.warning("⚠️ No se encontraron datos en 'NOVEDADES_GUARDIA'.")
    


# --- 8. BLOQUE FINAL DE LÓGICA DE ROL Y AUDITORÍA ---
elif st.session_state.rol_sel == "SUPERVISOR":
    if st.session_state.sup_autenticado:
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

        t_vis_qr, t_ruta_gmaps, t_car_tac, t_com_sup, t_pres_sup = st.tabs([
            "Visita QR", "📲 RUTA GOOGLE MAPS", "Carga Táctica", "💬 CHAT OPERATIVO", "📋 NOVEDADES Y RELEVOS"
        ])
        
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

        with t_ruta_gmaps:
            st.markdown("### 🗺️ NAVEGACIÓN TÁCTICA VÍA GOOGLE MAPS")
            opciones_servicios_r = df_objetivos_filtrados['OBJETIVO'].unique() if not df_objetivos_filtrados.empty else []
            if len(opciones_servicios_r) > 0:
                obj_ruta_sup = st.selectbox("SELECCIONE OBJETIVO DESTINO:", opciones_servicios_r, key="sup_ruta_gmaps_target")
                datos_obj_r = df_objetivos_filtrados[df_objetivos_filtrados['OBJETIVO'] == obj_ruta_sup].iloc[0]
                lat_target, lon_target = datos_obj_r['LATITUD'], datos_obj_r['LONGITUD']
                
                comisaria_r_name = None
                com_lat_target, com_lon_target = None, None
                dist_min_r = float('inf')
                
                for _, com in df_comisarias.iterrows():
                    ln1, lt1, ln2, lt2 = map(math.radians, [lon_target, lat_target, com['LONGITUD'], com['LATITUD']])
                    dln, dlt = ln2 - ln1, lt2 - lt1
                    a = math.sin(dlt/2)**2 + math.cos(lt1) * math.cos(lt2) * math.sin(dln/2)**2
                    km = 6371 * (2 * math.asin(math.sqrt(a)))
                    if km < dist_min_r:
                        dist_min_r, comisaria_r_name = km, com['COMISARIA']
                        com_lat_target, com_lon_target = com['LATITUD'], com['LONGITUD']
                
                if comisaria_r_name:
                    st.info(f"👮 **Comisaría Encontrada:** {comisaria_r_name} (Distancia: {dist_min_r:.2f} Km)")
                    url_gmaps = f"https://www.google.com/maps/dir/?api=1&origin={com_lat_target},{com_lon_target}&destination={lat_target},{lon_target}&travelmode=driving"
                    st.markdown(f'<a href="{url_gmaps}" target="_blank" class="btn-google-maps">🗺️ ABRIR ASISTENTE GPS</a>', unsafe_allow_html=True)
            else:
                st.warning("No tenés objetivos asignados.")

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
            st.markdown("### 📋 NOVEDADES DE MI GRUPO")
            df_v_total = leer_matriz_nube("NOVEDADES_GUARDIA")
            if not df_v_total.empty:
                df_v_total.columns = df_v_total.columns.str.strip().str.upper()
                mask_sup = df_v_total.apply(lambda r: any(str(val).strip().upper() == sup_activo_normalizado for val in r.values), axis=1)
                st.dataframe(df_v_total[mask_sup].sort_values(by="FECHA", ascending=False), use_container_width=True)

elif st.session_state.rol_sel == "VIGILADOR":
    # ... (Mantiene tu lógica actual de vigilador)
    st.markdown('<div class="panel-novedad">', unsafe_allow_html=True)
    opciones_globales_obj = df_objetivos['OBJETIVO'].unique() if not df_objetivos.empty else ["ALFAVINIL"]
    
    tab_presentismo, tab_relevo = st.tabs(["📋 FICHAJE (PRESENTISMO)", "🔄 SANCIONAR RELEVO"])
    
    with tab_presentismo:
        st.markdown("### 📸 REGISTRO BIOMÉTRICO")
        with st.form(key="form_fichaje_vigilador", clear_on_submit=True):
            v_apellido = st.text_input("NOMBRE COMPLETO:").upper().strip()
            v_dni = st.text_input("DNI / LEGAJO:").strip()
            v_obj = st.selectbox("OBJETIVO:", opciones_globales_obj)
            v_tipo_marcacion = st.selectbox("TIPO:", ["INGRESO", "EGRESO"])
            img_facial = st.camera_input("RECONOCIMIENTO FACIAL")
            btn_fichar = st.form_submit_button("CONSIGNAR Y TRANSMITIR")
            
            if btn_fichar and v_apellido and img_facial and v_dni:
                sup_responsable = df_objetivos[df_objetivos['OBJETIVO']==v_obj]['SUPERVISOR'].iloc[0] if not df_objetivos.empty else "N/A"
                fecha_hora_arg = obtener_hora_argentina()
                
                # LÓGICA DE BITÁCORA TÁCTICA
                tipo_evento = f"MARCACIÓN_{v_tipo_marcacion}"
                vig_sale = v_apellido if v_tipo_marcacion == "EGRESO" else "---"
                vig_entra = v_apellido if v_tipo_marcacion == "INGRESO" else "---"
                
                escribir_registro_nube("PRESENTISMO", [fecha_hora_arg.split(" ")[0], fecha_hora_arg.split(" ")[1], v_dni, f"{v_apellido} - {v_obj}", "", "OK", v_tipo_marcacion])
                escribir_registro_nube("NOVEDADES_GUARDIA", [fecha_hora_arg, v_obj, tipo_evento, vig_sale, vig_entra, v_dni, "PROCESADO", sup_responsable])
                st.success(f"🔒 {tipo_evento} REGISTRADA.")

    with tab_relevo:
        st.markdown("### 🔄 REGISTRO FORMAL DE CAMBIO")
        with st.form(key="form_relevo_vigilador_directo", clear_on_submit=True):
            v_obj_relevo = st.selectbox("OBJETIVO:", opciones_globales_obj)
            vig_saliente = st.text_input("SALE:").upper().strip()
            vig_entrante = st.text_input("ENTRA:").upper().strip()
            v_dni_relevo = st.text_input("DNI RESPONSABLE:").strip()
            btn_relevo = st.form_submit_button("SANCIONAR CAMBIO")
            
            if btn_relevo and vig_saliente and vig_entrante and v_dni_relevo:
                sup_resp = df_objetivos[df_objetivos['OBJETIVO']==v_obj_relevo]['SUPERVISOR'].iloc[0] if not df_objetivos.empty else "N/A"
                fecha = obtener_hora_argentina()
                escribir_registro_nube("NOVEDADES_GUARDIA", [fecha, v_obj_relevo, "RELEVO DE TURNO", vig_saliente, vig_entrante, v_dni_relevo, "PROCESADO", sup_resp])
                escribir_registro_nube("VIGILADORES", [fecha.split(" ")[0], fecha.split(" ")[1], v_obj_relevo, vig_saliente, vig_entrante, sup_resp, "RELEVO_EFECTUADO"])
                st.success("🔒 RELEVO REGISTRADO Y SANEADO")
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
