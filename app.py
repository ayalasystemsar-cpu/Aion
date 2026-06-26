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

# --- 1. CONFIGURACIÓN E INICIALIZACIÓN ---
st.set_page_config(page_title="AION-YAROKU | COMMAND", page_icon="🛡️", layout="wide", initial_sidebar_state="expanded")

if 'usuario_logueado' not in st.session_state: st.session_state.usuario_logueado = False
if 'rol_sel' not in st.session_state: st.session_state.rol_sel = "MONITOREO"
if 'user_sel' not in st.session_state: st.session_state.user_sel = "OPERADOR CENTRAL"
if 'sup_autenticado' not in st.session_state: st.session_state.sup_autenticado = False

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

def cargar_objetivos(): return leer_matriz_nube("OBJETIVOS")
def cargar_datos_comisarias(): return leer_matriz_nube("COMISARIAS")
def obtener_hora_argentina():
    tz = pytz.timezone("America/Argentina/Buenos_Aires")
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

# --- 3. IDENTIDAD Y LANDING ---
def aplicar_identidad_alfa():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@300;500;700&display=swap');
        .stApp { background: radial-gradient(circle at top, #0A0F1E 0%, #030305 100%) !important; color: #E0E0E0; font-family: 'Rajdhani', sans-serif; }
        .contenedor-logo-central { display: flex; justify-content: center; align-items: center; width: 100%; margin: 20px 0; }
        .logo-phoenix { width: 400px !important; border: 2px solid #00e5ff !important; box-shadow: 0 0 35px rgba(0, 229, 255, 0.5) !important; border-radius: 4px !important; background-color: #000 !important; }
        .estacion-titulo { font-family: 'Orbitron', sans-serif; color: #00E5FF !important; font-size: 32px; text-align: center; text-shadow: 0 0 15px rgba(0, 229, 255, 0.4); margin-bottom: 30px; }
        </style>
    """, unsafe_allow_html=True)

def mostrar_landing():
    aplicar_identidad_alfa()
    st.markdown('<div class="contenedor-logo-central"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" class="logo-phoenix"></div>', unsafe_allow_html=True)
    st.markdown('<div class="estacion-titulo">AION-YAROKU | COMMAND</div>', unsafe_allow_html=True)
    if st.button("ACCEDER AL COMANDO", type="primary", use_container_width=True):
        st.session_state.usuario_logueado = True
        st.rerun()


# ... (Todo tu código anterior hasta el 'else:') ...
# --- 4. LÓGICA PRINCIPAL ---
if not st.session_state.usuario_logueado:
    mostrar_landing()
else:
    # 1. Carga de datos base (Se hace una sola vez al entrar)
    df_objetivos = cargar_objetivos()
    df_comisarias = cargar_datos_comisarias()
    
    # 2. Sidebar (Solo se muestra una vez logueado)
    with st.sidebar:
        st.markdown('<div class="contenedor-logo-sidebar"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" style="width:180px; border:1px solid #00e5ff; border-radius:4px;"></div>', unsafe_allow_html=True)
        st.subheader("🛡️ PANEL DE CONTROL")
        
        if st.button("🛰️ MONITOREO", use_container_width=True):
            st.session_state.rol_sel = "MONITOREO"; st.session_state.user_sel = "OPERADOR CENTRAL"; st.rerun()
        if st.button("📋 JEFE DE OPERACIONES", use_container_width=True):
            st.session_state.rol_sel = "JEFE DE OPERACIONES"; st.rerun()
        if st.button("🏢 GERENCIA", use_container_width=True):
            st.session_state.rol_sel = "GERENCIA"; st.rerun()

    # --- 7. FLUJO POR ROLES ---
    # ESTA ESTRUCTURA ES LA ÚNICA QUE FUNCIONA:
    
    if st.session_state.rol_sel == "MONITOREO":
        # Todo el código de MONITOREO aquí
if st.session_state.rol_sel == "MONITOREO":
        col1, col2, col3, col4 = st.columns(4)
        
        # --- CARGA DE DATOS ---
        df_emergencias = leer_matriz_nube("ALERTAS")
        df_objetivos = cargar_objetivos()
        
        # --- LIMPIEZA DE DATOS ---
        if not df_emergencias.empty:
            df_emergencias.columns = df_emergencias.columns.str.strip().str.upper()
        else:
            df_emergencias = pd.DataFrame(columns=['FECHA', 'USUARIO', 'TIPO', 'ESTADO', 'CARGA_UTIL', 'INFORME'])

        # --- MAPA Y CORRECCIÓN DE NUMÉRICOS ---
        df_mapa_monitoreo = pd.DataFrame()
        if not df_objetivos.empty:
            df_objetivos.columns = df_objetivos.columns.str.strip().str.upper()
            if 'LATITUD' in df_objetivos.columns and 'LONGITUD' in df_objetivos.columns:
                df_mapa_monitoreo = df_objetivos.dropna(subset=['LATITUD', 'LONGITUD']).copy()
                df_mapa_monitoreo['LATITUD'] = pd.to_numeric(df_mapa_monitoreo['LATITUD'], errors='coerce')
                df_mapa_monitoreo['LONGITUD'] = pd.to_numeric(df_mapa_monitoreo['LONGITUD'], errors='coerce')
            # Eliminamos filas que no pudieron convertirse a número
            df_mapa_monitoreo = df_mapa_monitoreo.dropna(subset=['LATITUD', 'LONGITUD'])

    # Lógica de Pánicos
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

# 1. CONTADOR DE PANICOS
with col1.container():
    @st.fragment(run_every=5)
    def contar_panicos_monitoreo():
        df_alertas = leer_matriz_nube("ALERTAS")
        if not df_alertas.empty:
            df_alertas.columns = [str(c).strip().upper() for c in df_alertas.columns]
            total_sos = len(df_alertas[df_alertas['ESTADO'] == "PENDIENTE"])
            st.metric("🚨 S.O.S ACTIVOS", total_sos)
        else:
            st.metric("🚨 S.O.S ACTIVOS", "0")
    contar_panicos_monitoreo()

col2.metric("📡 RED", "OPERATIVA")
col3.metric("👤 OPERADOR", f"{st.session_state.user_sel}")

# 2. RELOJ DINAMICO
with col4.container():
    @st.fragment(run_every=1)
    def mostrar_reloj_monitoreo():
        hora_actual = obtener_hora_argentina().split(" ")[1]
        st.metric("🕒 HORA LOCAL", hora_actual)
    mostrar_reloj_monitoreo() 

# 3. TABS Y RADAR (Continúa con el resto de tu código original aquí)
# ... (El resto de tu lógica de tabs, radar y folium va aquí abajo)rite("---")

    # 1. Calculamos el total de nuevos ANTES de definir la etiqueta
df_msg = leer_matriz_nube("MENSAJERIA")
nombre_user = st.session_state.user_sel.upper()

total_nuevos = 0
if not df_msg.empty:
    mask = ((df_msg['DESTINATARIO'] == "TODOS") | 
            (df_msg['DESTINATARIO'] == "MONITOREO") | 
            (df_msg['DESTINATARIO'] == nombre_user)) & \
           (df_msg['ESTADO'] == "PENDIENTE")
    total_nuevos = len(df_msg[mask])

# 2. Creamos la etiqueta dinámica
label_msg = f"💬 MENSAJERÍA GLOBAL ({total_nuevos})" if total_nuevos > 0 else "💬 MENSAJERÍA GLOBAL"

# 3. Definimos los tabs usando esa variable
t_radar, t_mensajeria, t_vig, t_nov = st.tabs([
    "🚨 RADAR S.O.S", label_msg, "👥 PADRÓN VIGILADORES", "🔄 NOVEDADES Y FICHAJES"
]) 
with t_radar:
    st.subheader("📡 RADAR GLOBAL DE OBJETIVOS")
    if st.button("🔄 ACTUALIZAR RADAR DE CONTROL", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    # --- INTERFAZ DE SELECCIÓN Y ANÁLISIS TÁCTICO ---
    st.markdown('<div class="panel-novedad">', unsafe_allow_html=True)
    col_sel1, col_sel2 = st.columns([2, 1])
    
    if "filtro_radar_valor" not in st.session_state:
        st.session_state["filtro_radar_valor"] = "MOSTRAR TODO"

    with col_sel1:
        opciones_busqueda = ["MOSTRAR TODO"] + list(df_mapa_monitoreo['OBJETIVO'].unique()) if not df_mapa_monitoreo.empty else ["MOSTRAR TODO"]
        
        try:
            idx_defecto = opciones_busqueda.index(st.session_state["filtro_radar_valor"])
        except:
            idx_defecto = 0
            
        obj_seleccionado = st.selectbox(
            "🎯 ENFOCAR OBJETIVO EN RADAR / BUSCADOR:", 
            opciones_busqueda, 
            index=idx_defecto,
            key="buscador_radar_master"
        )
        st.session_state["filtro_radar_valor"] = obj_seleccionado
    
    comisaria_cercana_name = None
    distancia_minima = float('inf')
    com_lat_m, com_lon_m = None, None
    
    if obj_seleccionado != "MOSTRAR TODO" and not df_mapa_monitoreo.empty:
        datos_obj = df_mapa_monitoreo[df_mapa_monitoreo['OBJETIVO'] == obj_seleccionado].iloc[0]
        lat_obj = datos_obj['LATITUD']
        lon_obj = datos_obj['LONGITUD']
        
        for _, com in df_comisarias.iterrows():
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
            
            # --- LÓGICA DE IDENTIFICACIÓN ---
            texto_tooltip = f"🎯 {r['OBJETIVO']}" # Valor por defecto
            
            if es_panico:
                alerta_activa = df_emergencias[
                    (df_emergencias['CARGA_UTIL'].str.contains(r['OBJETIVO'])) & 
                    (df_emergencias['ESTADO'] == 'PENDIENTE')
                ]
                if not alerta_activa.empty:
                    # Obtenemos el nombre real del vigilador de la columna USUARIO
                    nombre_vigilante = alerta_activa.iloc[-1]['USUARIO']
                    # Aquí tienes la combinación exacta: Nombre Vigilador + Objetivo
                    texto_tooltip = f"🚨 {nombre_vigilante} | {r['OBJETIVO']}"

            # DIBUJO DEL MARCADOR
            if es_panico or es_el_seleccionado:
                folium.Marker(
                    location=[r['LATITUD'], r['LONGITUD']],
                    tooltip=texto_tooltip, # Mostramos la combinación exacta
                    icon=folium.DivIcon(
                        icon_size=(30, 30),
                        icon_anchor=(15, 15),
                        html='''<div style="background-color: #FF0000; width: 16px; height: 16px; border-radius: 50%; border: 2px solid white; animation: pulse 1s infinite alternate;"></div>'''
                    )
                ).add_to(m_mon)
            else:
                folium.CircleMarker(
                    location=[r['LATITUD'], r['LONGITUD']], radius=7, color="#00E5FF", fill=True,
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
    
    st_folium(m_mon, width="100%", height=550, key="mapa_monitoreo_radar_tactico")
with t_mensajeria:
    renderizar_mensajeria_global("MONITOREO")
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

        
    elif st.session_state.rol_sel == "SUPERVISOR":
        # Todo el código de SUPERVISOR aquí
        pass # <-- Borra este pass y pega aquí tu código de SUPERVISOR
        
    elif st.session_state.rol_sel == "VIGILADOR":
        # Todo el código de VIGILADOR aquí
        pass # <-- Borra este pass y pega aquí tu código de VIGILADOR

    elif st.session_state.rol_sel == "JEFE DE OPERACIONES":
        # Todo el código de JEFE aquí
        pass # <-- Borra este pass y pega aquí tu código de JEFE

    elif st.session_state.rol_sel == "GERENCIA":
        # Todo el código de GERENCIA aquí
        pass # <-- Borra este pass y pega aquí tu código de GERENCIA
        
    elif st.session_state.rol_sel == "ADMINISTRADOR":
        # Todo el código de ADMIN aquí
        pass # <-- Borra este pass y pega aquí tu código de ADMIN
