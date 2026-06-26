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

# --- 4. LÓGICA PRINCIPAL ---
if not st.session_state.usuario_logueado:
    mostrar_landing()

# ELIMINAMOS EL 'ELSE' AQUÍ para que los 'if/elif' funcionen libremente

if st.session_state.usuario_logueado:
    # 1. CARGA DE DATOS Y SIDEBAR
    df_objetivos = cargar_objetivos()
    df_comisarias = cargar_datos_comisarias()
    LISTA_SUPS_TACTICOS = ["AYALA BRIAN", "SUPERVISOR 1", "SUPERVISOR 2", "SUPERVISOR 3", "SUPERVISOR 4", "SUPERVISOR 5", "SUPERVISOR NOCTURNO"]

    # --- SIDEBAR ---
    with st.sidebar:
        st.markdown('<div class="contenedor-logo-sidebar"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" style="width:180px; border:1px solid #00e5ff; border-radius:4px;"></div>', unsafe_allow_html=True)
        st.subheader("🛡️ PANEL DE CONTROL")
        
        if st.button("🛰️ MONITOREO", use_container_width=True):
            st.session_state.rol_sel = "MONITOREO"; st.session_state.user_sel = "OPERADOR CENTRAL"; st.rerun()
        if st.button("📋 JEFE DE OPERACIONES", use_container_width=True):
            st.session_state.rol_sel = "JEFE DE OPERACIONES"; st.rerun()
        if st.button("🏢 GERENCIA", use_container_width=True):
            st.session_state.rol_sel = "GERENCIA"; st.rerun()
        
        st.write("---")
        st.button("🚪 CERRAR SESIÓN", on_click=lambda: setattr(st.session_state, 'usuario_logueado', False), use_container_width=True)


# --- 2. FLUJO POR ROLES ---
    # Ahora todos estos son 'if' / 'elif' alineados al mismo margen
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

        # 3. TABS Y RADAR
        df_msg = leer_matriz_nube("MENSAJERIA")
        nombre_user = st.session_state.user_sel.upper()
        total_nuevos = 0
        if not df_msg.empty:
            mask = ((df_msg['DESTINATARIO'] == "TODOS") | (df_msg['DESTINATARIO'] == "MONITOREO") | (df_msg['DESTINATARIO'] == nombre_user)) & (df_msg['ESTADO'] == "PENDIENTE")
            total_nuevos = len(df_msg[mask])

        label_msg = f"💬 MENSAJERÍA GLOBAL ({total_nuevos})" if total_nuevos > 0 else "💬 MENSAJERÍA GLOBAL"

        t_radar, t_mensajeria, t_vig, t_nov = st.tabs(["🚨 RADAR S.O.S", label_msg, "👥 PADRÓN VIGILADORES", "🔄 NOVEDADES Y FICHAJES"]) 
        
        with t_radar:
            # ... (Aquí va todo tu código de radar, mapas y comisarias que ya tenías)with t_radar:
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
                    st.info("Seleccione un objetivo.")
            st.markdown('</div>', unsafe_allow_html=True)

            # --- LÓGICA DE FINALIZACIÓN DE PÁNICO ---
            if sos_activos > 0:
                st.markdown('<div class="panel-novedad" style="border: 1px solid #FF0000;">', unsafe_allow_html=True)
                df_pendientes_form = df_emergencias[df_emergencias['ESTADO'] == 'PENDIENTE']
                with st.form(key="form_finalizar_panico", clear_on_submit=True):
                    opciones_alertas = {f"{r['FECHA']} - {r['USUARIO']}": idx for idx, r in df_pendientes_form.iterrows()}
                    alerta_seleccionada = st.selectbox("SELECCIONE EVENTO A FINALIZAR:", list(opciones_alertas.keys()))
                    txt_informe_cierre = st.text_area("INFORME OPERATIVO DE CIERRE:")
                    if st.form_submit_button("🚨 FINALIZAR PÁNICO"):
                        idx_df = opciones_alertas[alerta_seleccionada]
                        actualizar_celda("ALERTAS", idx_df + 2, "D", "FINALIZADO")
                        actualizar_celda("ALERTAS", idx_df + 2, "F", txt_informe_cierre.strip().upper())
                        st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

            # --- MAPA FOLIUM ---
            st.markdown('<div class="radar-box">', unsafe_allow_html=True)
            if not df_mapa_monitoreo.empty:
                centro_mapa = [df_mapa_monitoreo['LATITUD'].mean(), df_mapa_monitoreo['LONGITUD'].mean()] if obj_seleccionado == "MOSTRAR TODO" else [datos_obj['LATITUD'], datos_obj['LONGITUD']]
                
                m_mon = folium.Map(location=centro_mapa, zoom_start=12, tiles="cartodbpositron")
                # (Aquí iría tu lógica de añadir marcadores folium.Marker y folium.CircleMarker...)
                st_folium(m_mon, width="100%", height=550)
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.write("Radar activo") 

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
            # ... (Tu código de novedades)
            # --- CARGA Y PROCESAMIENTO ---
            df_nov_g = leer_matriz_nube("NOVEDADES_GUARDIA")
            
            if not df_nov_g.empty:
                # Limpieza de nombres de columnas
                df_nov_g.columns = [str(c).strip().upper() for c in df_nov_g.columns]
                
                # Eliminar duplicados en columnas por si acaso
                df_nov_g = df_nov_g.loc[:, ~df_nov_g.columns.duplicated()]
                
                # Ordenamiento cronológico si existe la columna FECHA
                if 'FECHA' in df_nov_g.columns:
                    df_nov_g['FECHA_ORDEN'] = pd.to_datetime(df_nov_g['FECHA'], errors='coerce')
                    df_ordenado = df_nov_g.sort_values(by='FECHA_ORDEN', ascending=False).drop(columns=['FECHA_ORDEN'])
                else:
                    df_ordenado = df_nov_g
                
                # Visualización
                st.dataframe(df_ordenado, use_container_width=True, hide_index=True)
            else:
                st.warning("⚠️ No se encontraron datos en 'NOVEDADES_GUARDIA'.")

    elif st.session_state.rol_sel == "SUPERVISOR":
        # ... (Tu código de Supervisor) ...
       # --- 0. GESTIÓN DE JORNADA ---
            st.subheader("⏱️ GESTIÓN DE JORNADA")
            
            sup_activo_normalizado = st.session_state.user_sel.strip().upper()
            df_objs_sup = df_objetivos[df_objetivos['SUPERVISOR'] == sup_activo_normalizado] if not df_objetivos.empty else pd.DataFrame()
            opciones_obj = df_objs_sup['OBJETIVO'].unique() if not df_objs_sup.empty else ["SIN OBJETIVOS ASIGNADOS"]

            obj_seleccionado = st.selectbox("🎯 SELECCIONE OBJETIVO:", opciones_obj, key="obj_jornada_sel")
            
            col_j1, col_j2 = st.columns(2)
            with col_j1:
                if st.button("🚀 INICIO DE JORNADA", use_container_width=True):
                    registrar_movimiento_supervisor(st.session_state.user_sel, obj_seleccionado, "INICIO")
                    st.success(f"Jornada iniciada en {obj_seleccionado}")
            with col_j2:
                if st.button("🏁 CIERRE DE JORNADA", use_container_width=True):
                    registrar_movimiento_supervisor(st.session_state.user_sel, obj_seleccionado, "FIN")
                    st.success(f"Jornada cerrada en {obj_seleccionado}")

            # --- BOTÓN DE PÁNICO ---
            st.markdown("<br>", unsafe_allow_html=True)
            _, col_panico, _ = st.columns([1, 2, 1]) 
            with col_panico:
                if st.button("🚨 ACTIVAR PÁNICO", type="primary", use_container_width=True):
                    obj_alerta = st.session_state.get("obj_jornada_sel", "UBICACIÓN DESCONOCIDA")
                    lat_envio, lon_envio = 0.0, 0.0
                    try:
                        loc = get_geolocation()
                        if loc and isinstance(loc, dict) and 'coords' in loc:
                            lat_envio = loc['coords'].get('latitude', 0.0)
                            lon_envio = loc['coords'].get('longitude', 0.0)
                    except: pass
                    
                    carga_sos = f"LAT:{lat_envio}|LON:{lon_envio}|OBJ:{obj_alerta}|SUP:{st.session_state.user_sel}"
                    escribir_registro_nube("ALERTAS", [obtener_hora_argentina(), st.session_state.user_sel, "PÁNICO", "PENDIENTE", carga_sos])
                    st.error(f"🚨 S.O.S ENVIADO DESDE: {obj_alerta}")

            # --- TABS DE SUPERVISOR ---
            df_objetivos_filtrados = df_objs_sup
            df_msg = leer_matriz_nube("MENSAJERIA")
            nombre_user = st.session_state.user_sel.upper()
            total_nuevos = len(df_msg[((df_msg['DESTINATARIO'] == "TODOS") | (df_msg['DESTINATARIO'] == "SUPERVISORES") | (df_msg['DESTINATARIO'] == nombre_user)) & (df_msg['ESTADO'] == "PENDIENTE")]) if not df_msg.empty else 0
            label_msg = f"💬 MENSAJERÍA GLOBAL ({total_nuevos})" if total_nuevos > 0 else "💬 MENSAJERÍA GLOBAL"

            t_vis_qr, t_ruta_gmaps, t_car_tac, t_mensajeria_sup, t_pres_sup = st.tabs([
                "Visita QR", "📲 RUTA GOOGLE MAPS", "Carga Táctica", label_msg, "📋 NOVEDADES Y RELEVOS"
            ])

            with t_vis_qr:
                st.subheader("📱 ESCANEO TÁCTICO PARA SUPERVISORES")
                if not df_objetivos_filtrados.empty:
                    obj_a_generar = st.selectbox("Seleccione objetivo:", df_objetivos_filtrados['OBJETIVO'].unique())
                    if obj_a_generar:
                        url_final = f"https://tu-app-de-aion.streamlit.app/?obj={obj_a_generar.replace(' ', '%20')}"
                        import qrcode
                        qr = qrcode.QRCode(version=1, box_size=15, border=3)
                        qr.add_data(url_final)
                        qr.make(fit=True)
                        st.image(qr.make_image(fill_color="black", back_color="white").get_image(), width=300)
                
                # --- FLOTA ---
                st.markdown("### 📝 REGISTRO DE ACTA DE FLOTA")
                with st.form(key="form_acta_flota", clear_on_submit=True):
                    col1, col2 = st.columns(2)
                    v_patente = col1.text_input("PATENTE/MÓVIL:").upper()
                    v_km_inicial = col1.number_input("KM INICIAL:", min_value=0)
                    v_km_final = col2.number_input("KM FINAL:", min_value=0)
                    v_combustible = col2.selectbox("CARGA COMBUSTIBLE:", ["NO", "SI - MEDIA CARGA", "SI - TANQUE LLENO"])
                    if st.form_submit_button("REGISTRAR ACTA"):
                        escribir_registro_nube("CONTROL_FLOTA", [obtener_hora_argentina(), st.session_state.user_sel, v_patente, v_km_inicial, v_km_final, v_combustible])
                        st.success("✅ Acta registrada")

            with t_ruta_gmaps:
                # [AQUÍ PEGA TU LÓGICA DE NAVEGACIÓN QUE YA TENÍAS]
                st.markdown("### 🗺️ NAVEGACIÓN TÁCTICA VÍA GOOGLE MAPS")
            opciones_servicios_r = df_objetivos_filtrados['OBJETIVO'].unique() if not df_objetivos_filtrados.empty else []
            
            if len(opciones_servicios_r) > 0:
                obj_ruta_sup = st.selectbox("SELECCIONE OBJETIVO DESTINO:", opciones_servicios_r, key="sup_ruta_gmaps_target")
                
                datos_obj_r = df_objetivos_filtrados[df_objetivos_filtrados['OBJETIVO'] == obj_ruta_sup].iloc[0]
                lat_target = datos_obj_r['LATITUD']
                lon_target = datos_obj_r['LONGITUD']
                
                comisaria_r_name = None
                com_lat_target, com_lon_target = None, None
                dist_min_r = float('inf')
                
                # Cálculo de la comisaría más cercana (Haversine)
                for _, com in df_comisarias.iterrows():
                    ln1, lt1, ln2, lt2 = map(math.radians, [lon_target, lat_target, com['LONGITUD'], com['LATITUD']])
                    dln = ln2 - ln1
                    dlt = lt2 - lt1
                    a = math.sin(dlt/2)**2 + math.cos(lt1) * math.cos(lt2) * math.sin(dln/2)**2
                    c = 2 * math.asin(math.sqrt(a))
                    km = 6371 * c
                    
                    if km < dist_min_r:
                        dist_min_r = km
                        comisaria_r_name = com['COMISARIA']
                        com_lat_target = com['LATITUD']
                        com_lon_target = com['LONGITUD']
                
                if comisaria_r_name:
                    st.info(f"👮 **Comisaría Encontrada:** {comisaria_r_name} (Distancia: {dist_min_r:.2f} Km)")
                    
                    # Generamos el enlace para Google Maps
                    url_gmaps = f"https://www.google.com/maps/dir/?api=1&origin={com_lat_target},{com_lon_target}&destination={lat_target},{lon_target}&travelmode=driving"
                    
                    st.markdown(
                        f'<a href="{url_gmaps}" target="_blank" class="btn-google-maps" style="background-color: #4285F4; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: block; text-align: center;">🗺️ ABRIR ASISTENTE GPS EN GOOGLE MAPS</a>',
                        unsafe_allow_html=True
                    )
                    st.caption("⚠️ Al presionar el botón, se abrirá la aplicación de Google Maps con el trazado listo para iniciar la navegación.")
            else:
                st.warning("No tenés objetivos asignados para trazar rutas de emergencia en este turno.")

    with t_car_tac:
                novedad_sup = st.text_area("Novedad / Registro Operativo:")
                
                if st.button("CARGAR REGISTRO") and novedad_sup.strip():
                    escribir_registro_nube("NOVEDADES", [obtener_hora_argentina(), st.session_state.user_sel, novedad_sup.upper()])
                    st.success("✅ Cargado")

    with t_mensajeria_sup:
                renderizar_mensajeria_global("SUPERVISOR")

    with t_pres_sup:
                st.subheader("📋 NOVEDADES DE MI GRUPO")
 
        
    elif st.session_state.rol_sel == "VIGILADOR":
        # ... (Tu código de Vigilador) ...
        st.markdown('<div class="panel-novedad">', unsafe_allow_html=True)
        opciones_globales_obj = df_objetivos['OBJETIVO'].unique() if not df_objetivos.empty else ["ALFAVINIL"]
        
        # 1. Calculamos el total de mensajes pendientes
        df_msg = leer_matriz_nube("MENSAJERIA")
        nombre_user = st.session_state.user_sel.upper()
        total_nuevos = 0
        if not df_msg.empty:
            mask = ((df_msg['DESTINATARIO'] == "TODOS") | (df_msg['DESTINATARIO'] == "VIGILADOR") | (df_msg['DESTINATARIO'] == nombre_user)) & (df_msg['ESTADO'] == "PENDIENTE")
            total_nuevos = len(df_msg[mask])

        label_msg = f"💬 MENSAJERÍA GLOBAL ({total_nuevos})" if total_nuevos > 0 else "💬 MENSAJERÍA GLOBAL"
        
        # 2. Definimos los tabs
        tab_presentismo, tab_relevo, tab_mensajeria, tab_panico = st.tabs([
            "📋 FICHAJE", "🔄 RELEVO", label_msg, "🚨 PÁNICO"
        ])
      
        # 3. Pestaña Fichaje
        with tab_presentismo:
            st.markdown("### 📸 REGISTRO BIOMÉTRICO")
            with st.form(key="form_fichaje_vigilador", clear_on_submit=True):
                v_nombre_completo = st.text_input("APELLIDO Y NOMBRE:").strip() 
                v_dni = st.text_input("LEGAJO:").strip() 
                v_obj = st.selectbox("OBJETIVO:", opciones_globales_obj)
                v_tipo_marcacion = st.selectbox("TIPO:", ["INGRESO", "EGRESO"])
                img_facial = st.camera_input("RECONOCIMIENTO FACIAL")
                
                if st.form_submit_button("CONSIGNAR Y TRANSMITIR"):
                    if v_nombre_completo and v_dni and img_facial:
                        st.session_state.v_nombre_completo = v_nombre_completo.upper()
                        st.session_state.legajo_vigilador = v_dni
                        
                        fecha_hora_arg = obtener_hora_argentina()
                        sup_responsable = df_objetivos[df_objetivos['OBJETIVO'] == v_obj]['SUPERVISOR'].iloc[0] if not df_objetivos.empty else "N/A"
                        tipo_evento = f"MARCACIÓN_{v_tipo_marcacion}"
                        
                        escribir_registro_nube("PRESENTISMO", [fecha_hora_arg.split(" ")[0], fecha_hora_arg.split(" ")[1], v_dni, f"{v_nombre_completo.upper()} - {v_obj}", "", "OK", v_tipo_marcacion])
                        escribir_registro_nube("NOVEDADES_GUARDIA", [fecha_hora_arg, v_obj, tipo_evento, "---", v_nombre_completo.upper(), v_dni, "PROCESADO", sup_responsable])
                        
                        st.success(f"🔒 {tipo_evento} REGISTRADA PARA {v_nombre_completo.upper()}")
                    else:
                        st.error("⚠️ Por favor, complete todos los campos y capture la foto.")

        # 4. Pestaña de Relevo
        with tab_relevo:
            st.markdown("### 🔄 REGISTRO FORMAL DE CAMBIO")
            with st.form(key="form_relevo_vigilador_directo", clear_on_submit=True):
                v_obj_relevo = st.selectbox("OBJETIVO:", opciones_globales_obj, key="relevo_obj")
                vig_saliente = st.text_input("SALE:").upper().strip()
                vig_entrante = st.text_input("ENTRA:").upper().strip()
                v_dni_relevo = st.text_input("DNI RESPONSABLE:").strip()
                if st.form_submit_button("SANCIONAR CAMBIO"):
                    sup_resp = df_objetivos[df_objetivos['OBJETIVO']==v_obj_relevo]['SUPERVISOR'].iloc[0] if not df_objetivos.empty else "N/A"
                    fecha = obtener_hora_argentina()
                    escribir_registro_nube("NOVEDADES_GUARDIA", [fecha, v_obj_relevo, "RELEVO DE TURNO", vig_saliente, vig_entrante, v_dni_relevo, "PROCESADO", sup_resp])
                    escribir_registro_nube("VIGILADORES", [fecha.split(" ")[0], fecha.split(" ")[1], v_obj_relevo, vig_saliente, vig_entrante, sup_resp, "RELEVO_EFECTUADO"])
                    st.success("🔒 RELEVO REGISTRADO Y EXITOSO")

        # 5. Pestaña Mensajería
        with tab_mensajeria:
            renderizar_mensajeria_global("VIGILADOR")

        # 6. Pestaña Pánico
        with tab_panico:
            st.markdown("### 🛡️ PROTOCOLO DE EMERGENCIA")
            df_jornada = leer_matriz_nube("JORNADA_SUPERVISORES")
            df_jornada['SUPERVISOR_CLEAN'] = df_jornada['SUPERVISOR'].astype(str).str.strip().str.upper()
            nombre_user_clean = st.session_state.user_sel.strip().upper()
            jornada_actual = df_jornada[df_jornada['SUPERVISOR_CLEAN'] == nombre_user_clean].tail(1)
            
            if not jornada_actual.empty:
                obj_detectado = jornada_actual['OBJETIVO'].values[0]
                st.success(f"📍 OBJETIVO DETECTADO: **{obj_detectado}**")
            else:
                obj_detectado = st.selectbox("OBJETIVO:", opciones_globales_obj)
                st.error("⚠️ OBJETIVO NO DETECTADO. SELECCIONE MANUALMENTE.")

            if st.button("🚨 ACTIVAR ALERTA TÁCTICA", type="primary", use_container_width=True):
                nombre_real = st.session_state.get("v_nombre_completo", st.session_state.get("user_sel", "VIGILADOR")).upper()
                sup_asignado = "MONITOREO"
                if not df_objetivos.empty:
                    filtro = df_objetivos[df_objetivos['OBJETIVO'] == obj_detectado]
                    if not filtro.empty:
                        sup_asignado = str(filtro['SUPERVISOR'].iloc[0]).strip()
                
                fecha = obtener_hora_argentina()
                carga_sos = f"VIG:{nombre_real}|OBJ:{obj_detectado}|SUP:{sup_asignado}"
                escribir_registro_nube("ALERTAS", [fecha, nombre_real, "PÁNICO", "PENDIENTE", carga_sos, "PRUEBA"])
                enviar_alerta_automatica("SISTEMA_VIGILADOR", obj_detectado, nombre_real, sup_asignado)
                st.error(f"🚨 ALERTA ENVIADA: {nombre_real} DESDE {obj_detectado}")
        pass

    elif st.session_state.rol_sel == "JEFE DE OPERACIONES":
        # ... (Tu código de Jefe) ...
        # --- CABECERA DINÁMICA ---
        col1, col2, col3, col4 = st.columns(4)
        
        with col1.container():
            @st.fragment(run_every=1)
            def mostrar_sos():
                df_alertas = leer_matriz_nube("ALERTAS")
                total_sos = len(df_alertas[df_alertas['ESTADO'] == "PENDIENTE"]) if not df_alertas.empty else 0
                st.metric("🚨 S.O.S ACTIVOS", total_sos)
            mostrar_sos()

        col2.metric("📡 RED", "OPERATIVA")
        col3.metric("👤 USUARIO", f"{st.session_state.user_sel}")
        
        with col4.container():
            @st.fragment(run_every=1)
            def mostrar_reloj():
                hora_actual = obtener_hora_argentina().split(" ")[1]
                st.metric("🕒 HORA LOCAL", hora_actual)
            mostrar_reloj()

        # --- LÓGICA DE MENSAJERÍA ---
        df_msg = leer_matriz_nube("MENSAJERIA")
        nombre_user = st.session_state.user_sel.upper()
        total_nuevos = len(df_msg[((df_msg['DESTINATARIO'] == "TODOS") | 
                                   (df_msg['DESTINATARIO'] == "JEFE DE OPERACIONES") | 
                                   (df_msg['DESTINATARIO'] == nombre_user)) & 
                                  (df_msg['ESTADO'] == "PENDIENTE")]) if not df_msg.empty else 0
        
        label_msg = f"💬 MENSAJERÍA ({total_nuevos})" if total_nuevos > 0 else "💬 MENSAJERÍA"
        
        st.markdown('<h2 style="color:#00E5FF; font-family:\'Orbitron\'; font-size:24px;">Comando: JEFE DE OPERACIONES</h2>', unsafe_allow_html=True)
        
        # --- TABS ---
        t_mensajeria_jefe, t_ejecucion, t_tab_auditoria = st.tabs([label_msg, "Ejecución", "📍 TABLERO DE AUDITORÍA"])
        
        with t_mensajeria_jefe:
            renderizar_mensajeria_global("JEFE DE OPERACIONES")
            
        with t_ejecucion:
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                st.subheader("ALTA DE RECURSO")
                g_alta_nom = st.text_input("Nombre:", key="jefe_alta_nom")
                g_alta_asig = st.selectbox("Asignar a:", LISTA_SUPS_TACTICOS, key="jefe_alta_asig")
                if st.button("Solicitar Alta"):
                    escribir_registro_nube("PETICIONES", [obtener_hora_argentina(), st.session_state.user_sel, "ALTA", "OBJETIVO", f"{g_alta_nom} | ASIG: {g_alta_asig}"])
                    st.success("✅ Petición enviada")
            with col_g2:
                st.subheader("BAJA DE OBJETIVO")
                g_baja_obj = st.selectbox("Objetivo:", df_objetivos['OBJETIVO'].unique() if not df_objetivos.empty else ["ALFAVINIL"], key="jefe_baja_obj")
                if st.button("Solicitar Baja"):
                    escribir_registro_nube("PETICIONES", [obtener_hora_argentina(), st.session_state.user_sel, "BAJA", "OBJETIVO", g_baja_obj])
                    st.success("✅ Petición enviada")
        
        with t_tab_auditoria:
            # 1. AUDITORÍA DE JORNADA
            st.markdown("### 📋 AUDITORÍA DE SUPERVISIÓN")
            df_jornadas = leer_matriz_nube("JORNADA_SUPERVISORES")
            if not df_jornadas.empty:
                df_jornadas.columns = [str(c).strip().upper() for c in df_jornadas.columns]
                df_jornadas['DATETIME'] = pd.to_datetime(df_jornadas['FECHA'] + ' ' + df_jornadas['HORA'], errors='coerce')
                df_reporte = df_jornadas.groupby(['FECHA', 'SUPERVISOR', 'OBJETIVO']).agg(
                    INGRESO=('HORA', 'first'), EGRESO=('HORA', 'last'),
                    INICIO_DT=('DATETIME', 'first'), FIN_DT=('DATETIME', 'last')
                ).reset_index()
                df_reporte['DURACION_TOTAL'] = ((df_reporte['FIN_DT'] - df_reporte['INICIO_DT']).dt.total_seconds() / 60).round(2)
                st.dataframe(df_reporte[['FECHA', 'SUPERVISOR', 'OBJETIVO', 'INGRESO', 'EGRESO', 'DURACION_TOTAL']], use_container_width=True, hide_index=True)
            
            # 2. HISTÓRICO DE ALERTAS
            st.markdown("---")
            st.markdown("### 🚨 HISTÓRICO DE ALERTAS TÁCTICAS")
            df_alertas = leer_matriz_nube("ALERTAS")
            if not df_alertas.empty:
                df_alertas.columns = [str(c).strip().upper() for c in df_alertas.columns]
                st.dataframe(df_alertas[['FECHA', 'USUARIO', 'CARGA_UTIL', 'ESTADO']], use_container_width=True, hide_index=True)
            
            # 3. AUDITORÍA DE RELEVOS
            st.markdown("---")
            st.markdown("### 🔄 AUDITORÍA DE RELEVOS")
            df_relevos = leer_matriz_nube("NOVEDADES_GUARDIA")
            if not df_relevos.empty:
                df_relevos.columns = [str(c).strip().upper() for c in df_relevos.columns]
                if 'TIPO_EVENTO' in df_relevos.columns:
                    df_filtro = df_relevos[df_relevos['TIPO_EVENTO'] == "RELEVO DE TURNO"].copy()
                    st.dataframe(df_filtro[['FECHA', 'OBJETIVO', 'VIGILADOR_SALE', 'VIGILADOR_ENTRA', 'DNI']], use_container_width=True, hide_index=True)
            
            # 4. AUDITORÍA DE FLOTA
            st.markdown("---")
            st.markdown("### ⛽ AUDITORÍA Y CONTROL DE FLOTA")
            df_flota = leer_matriz_nube("CONTROL_FLOTA")
            if not df_flota.empty:
                df_flota.columns = [str(c).strip().upper() for c in df_flota.columns]
                df_flota['KM_RECORRIDOS'] = pd.to_numeric(df_flota['KM_FINAL'], errors='coerce') - pd.to_numeric(df_flota['KM_INICIAL'], errors='coerce')
                st.dataframe(df_flota[['FECHA', 'SUPERVISOR', 'MOVIL', 'KM_INICIAL', 'KM_FINAL', 'KM_RECORRIDOS', 'COMBUSTIBLE']], use_container_width=True, hide_index=True)

        
    elif st.session_state.rol_sel == "GERENCIA":
        # ... (Tu código de Gerencia) ...
        # 1. Cabecera ejecutiva
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("📊 KPI OPERATIVO", "98%")
        col2.metric("👥 PERSONAL ACTIVO", "12")
        col3.metric("👤 GERENTE", f"{st.session_state.user_sel}")
        
        # 2. Reloj ejecutivo
        with col4.container():
            @st.fragment(run_every=1)
            def mostrar_reloj_gerencia():
                hora_actual = obtener_hora_argentina().split(" ")[1]
                st.metric("🕒 HORA LOCAL", hora_actual)
            mostrar_reloj_gerencia()
            
        st.write("---")

        # 3. Cálculo de mensajes pendientes
        df_msg = leer_matriz_nube("MENSAJERIA")
        nombre_user = st.session_state.user_sel.upper()
        total_nuevos = len(df_msg[((df_msg['DESTINATARIO'] == "TODOS") | 
                                   (df_msg['DESTINATARIO'] == "GERENCIA") | 
                                   (df_msg['DESTINATARIO'] == nombre_user)) & 
                                  (df_msg['ESTADO'] == "PENDIENTE")]) if not df_msg.empty else 0
        
        label_msg = f"💬 MENSAJERÍA ({total_nuevos})" if total_nuevos > 0 else "💬 MENSAJERÍA"

        st.markdown('<h2 style="color:#00E5FF; font-family:\'Orbitron\'; font-size:24px;">Comando: DIRECCIÓN GENERAL</h2>', unsafe_allow_html=True)
        
        # 4. Definición de pestañas
        t_mensajeria_ger, t_ejecucion_ger, t_tab_auditoria = st.tabs(["💬 MENSAJERÍA GLOBAL", "🎮 EJECUCIÓN", "📍 TABLERO DE AUDITORÍA"])
        
        with t_mensajeria_ger:
            renderizar_mensajeria_global("GERENCIA")
            
        with t_ejecucion_ger:
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                st.subheader("ALTA DE RECURSO")
                g_alta_nom = st.text_input("Nombre:", key="ger_alta_nom")
                g_alta_asig = st.selectbox("Asignar a:", LISTA_SUPS_TACTICOS, key="ger_alta_asig")
                if st.button("Solicitar Alta"):
                    escribir_registro_nube("PETICIONES", [obtener_hora_argentina(), st.session_state.user_sel, "ALTA", "OBJETIVO", f"{g_alta_nom} | ASIG: {g_alta_asig}"])
                    st.success("✅ Petición enviada")
            with col_g2:
                st.subheader("BAJA DE OBJETIVO")
                g_baja_obj = st.selectbox("Objetivo:", df_objetivos['OBJETIVO'].unique() if not df_objetivos.empty else ["ALFAVINIL"], key="ger_baja_obj")
                if st.button("Solicitar Baja"):
                    escribir_registro_nube("PETICIONES", [obtener_hora_argentina(), st.session_state.user_sel, "BAJA", "OBJETIVO", g_baja_obj])
                    st.success("✅ Petición enviada")

        with t_tab_auditoria:
            # 1. Auditoría de Jornada
            st.markdown("### 📋 AUDITORÍA DE SUPERVISIÓN")
            df_jornadas = leer_matriz_nube("JORNADA_SUPERVISORES")
            if not df_jornadas.empty:
                df_jornadas.columns = [str(c).strip().upper() for c in df_jornadas.columns]
                df_jornadas['DATETIME'] = pd.to_datetime(df_jornadas['FECHA'] + ' ' + df_jornadas['HORA'], errors='coerce')
                df_reporte = df_jornadas.groupby(['FECHA', 'SUPERVISOR', 'OBJETIVO']).agg(
                    INGRESO=('HORA', 'first'), EGRESO=('HORA', 'last'),
                    INICIO_DT=('DATETIME', 'first'), FIN_DT=('DATETIME', 'last')
                ).reset_index()
                df_reporte['DURACION_TOTAL'] = ((df_reporte['FIN_DT'] - df_reporte['INICIO_DT']).dt.total_seconds() / 60).round(2)
                st.dataframe(df_reporte[['FECHA', 'SUPERVISOR', 'OBJETIVO', 'INGRESO', 'EGRESO', 'DURACION_TOTAL']], use_container_width=True, hide_index=True)

            # 2. Histórico de alertas y otros...
            st.markdown("---")
            st.markdown("### 🚨 HISTÓRICO DE ALERTAS TÁCTICAS")
            df_alertas = leer_matriz_nube("ALERTAS")
            if not df_alertas.empty:
                df_alertas.columns = [str(c).strip().upper() for c in df_alertas.columns]
                st.dataframe(df_alertas[['FECHA', 'USUARIO', 'CARGA_UTIL', 'ESTADO']], use_container_width=True, hide_index=True)

            # 3. Flota
            st.markdown("---")
            st.markdown("### ⛽ AUDITORÍA Y CONTROL DE FLOTA")
            df_flota = leer_matriz_nube("CONTROL_FLOTA")
            if not df_flota.empty:
                df_flota.columns = [str(c).strip().upper() for c in df_flota.columns]
                df_flota['KM_RECORRIDOS'] = pd.to_numeric(df_flota['KM_FINAL'], errors='coerce') - pd.to_numeric(df_flota['KM_INICIAL'], errors='coerce')
                st.dataframe(df_flota[['FECHA', 'SUPERVISOR', 'MOVIL', 'KM_INICIAL', 'KM_FINAL', 'KM_RECORRIDOS', 'COMBUSTIBLE']], use_container_width=True, hide_index=True)
        pass
        
    elif st.session_state.rol_sel == "ADMINISTRADOR":
        # ... (Tu código de Admin) ...
        st.subheader("⚙️ ACCESO AL NÚCLEO MAESTRO")
        
        # Estado de desbloqueo en sesión para no pedir contraseña a cada clic
        if 'admin_desbloqueado' not in st.session_state:
            st.session_state.admin_desbloqueado = False

        if not st.session_state.admin_desbloqueado:
            u_ing = st.text_input("ADMIN_USER")
            p_ing = st.text_input("ADMIN_PASS", type="password")
            if st.button("DESBLOQUEAR NÚCLEO"):
                if u_ing == "admin" and p_ing == "aion2026": 
                    st.session_state.admin_desbloqueado = True
                    st.rerun()
                else:
                    st.error("❌ Credenciales incorrectas.")
        else:
            st.success("✅ Núcleo Maestro desbloqueado.")
            if st.button("🔒 BLOQUEAR NÚCLEO"):
                st.session_state.admin_desbloqueado = False
                st.rerun()
            
            st.markdown("---")
            st.subheader("🛠️ FUNCIONES DE SISTEMA")
            # Aquí puedes agregar botones de mantenimiento, limpieza de caché o gestión de logs
            if st.button("🧹 LIMPIAR CACHÉ DE DATOS"):
                st.cache_data.clear()
                st.success("Caché limpiada.")
            
            # Ejemplo de acceso a configuración global
            st.write("Configuración del sistema AION-YAROKU activa.")
        

