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
        .stButton > button { background-color: #0A192F !important; color: #00E5FF !important; border: 1px solid #00E5FF !important; border-radius: 5px !important; font-family: 'Orbitron', sans-serif !important; }
        .stButton > button:hover { background-color: #00E5FF !important; color: #000 !important; }
        </style>
    """, unsafe_allow_html=True)

def mostrar_landing():
    aplicar_identidad_alfa()
    st.markdown('<div class="contenedor-logo-central"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" class="logo-phoenix"></div>', unsafe_allow_html=True)
    st.markdown('<div class="estacion-titulo">AION-YAROKU | COMMAND</div>', unsafe_allow_html=True)
    
    # Selector de Modo
    modo = st.radio("Acceso al Sistema:", ["Iniciar Sesión", "Crear Cuenta"], horizontal=True)
    
    with st.form("form_acceso"):
        user = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        # Nuevo campo para seleccionar el rol
        rol_usuario = st.selectbox("Seleccione su Rol:", 
                                   ["VIGILADOR", "MONITOREO", "JEFE DE OPERACIONES", "GERENCIA", "ADMINISTRADOR"])
        
        btn_texto = "ENTRAR" if modo == "Iniciar Sesión" else "REGISTRARSE"
        
        if st.form_submit_button(btn_texto):
            if modo == "Iniciar Sesión":
                # Lógica de validación (ejemplo simple)
                if user == "admin" and password == "1234":
                    st.session_state.usuario_logueado = True
                    st.session_state.user_sel = user
                    st.session_state.rol_sel = rol_usuario  # <--- GUARDAMOS EL ROL AQUÍ
                    st.rerun()
                else: 
                    st.error("Credenciales incorrectas.")
            else:
                # Aquí guardarías los datos en tu Google Sheet de "USUARIOS"
                st.success(f"Solicitud de registro como {rol_usuario} enviada.")
#--------------------------------------------------------------------------------------------------------------------------------#

# --- 4. LÓGICA PRINCIPAL ---
if not st.session_state.usuario_logueado:
    mostrar_landing()
else:
    # 1. CARGA DE DATOS (Carga los datos una sola vez aquí)
    df_objetivos = cargar_objetivos()
    df_comisarias = cargar_datos_comisarias()
  #---------------------------------------------------------------------------------------------------------------------------------------#  
    # 2. EL BLINDAJE QUE QUERÍAS AGREGAR (Va justo aquí)
    if not df_objetivos.empty and 'LATITUD' in df_objetivos.columns:
        df_objetivos['LATITUD'] = pd.to_numeric(df_objetivos['LATITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        df_objetivos['LONGITUD'] = pd.to_numeric(df_objetivos['LONGITUD'].astype(str).str.replace(',', '.'), errors='coerce')
    #---------------------------------------------------------------------------------------------------------------------------------------#
# 2. PANEL LATERAL (NO TOCAR, MANTENER TU DISEÑO)
    
    with st.sidebar:
        st.markdown('<div class="contenedor-logo-sidebar"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" style="width:180px; border:1px solid #00e5ff; border-radius:4px;"></div>', unsafe_allow_html=True)
        st.subheader("🛡️ PANEL DE CONTROL")
        
        # Botones de navegación
        if st.button("🛰️ MONITOREO"): st.session_state.rol_sel = "MONITOREO"; st.rerun()
        if st.button("👤 SUPERVISOR"): st.session_state.rol_sel = "SUPERVISOR"; st.rerun()
        if st.button("📋 JEFE DE OPERACIONES"): st.session_state.rol_sel = "JEFE DE OPERACIONES"; st.rerun()
        if st.button("🏢 GERENCIA"): st.session_state.rol_sel = "GERENCIA"; st.rerun()
        if st.button("👮 VIGILADOR"): st.session_state.rol_sel = "VIGILADOR"; st.rerun()
        
        st.write("---")
        st.button("🚪 CERRAR SESIÓN", on_click=lambda: setattr(st.session_state, 'usuario_logueado', False), use_container_width=True)
      #----------------------------------------------------------------------------------------------------------------------------------------------------------------------------#  
# 3. FLUJO POR ROLES (Estructura IF/ELIF impecable)
    if st.session_state.rol_sel == "MONITOREO":
        # ... (Tu código de MONITOREO que ya funciona) ...
        # (Asegúrate de mantenerlo dentro de este bloque)
        col1, col2, col3, col4 = st.columns(4)
        
        # Carga de datos
        df_emergencias = leer_matriz_nube("ALERTAS")
        df_objetivos = cargar_objetivos()
        
        # --- BLINDAJE: Conversión a números antes de cualquier cálculo ---
        if not df_objetivos.empty:
            df_objetivos.columns = df_objetivos.columns.str.strip().str.upper()
            df_objetivos['LATITUD'] = pd.to_numeric(df_objetivos['LATITUD'].astype(str).str.replace(',', '.'), errors='coerce')
            df_objetivos['LONGITUD'] = pd.to_numeric(df_objetivos['LONGITUD'].astype(str).str.replace(',', '.'), errors='coerce')
            df_mapa_monitoreo = df_objetivos.dropna(subset=['LATITUD', 'LONGITUD']).copy()
        else:
            df_mapa_monitoreo = pd.DataFrame()
    
        # (Aquí va el resto de tu lógica de contadore# 2. LÓGICA DE PÁNICO
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
        
        # 3. CONTADORES Y RELOJ
        with col1.container():
            @st.fragment(run_every=5)
            def contar_panicos_monitoreo():
                df_alertas = leer_matriz_nube("ALERTAS")
                if not df_alertas.empty:
                    df_alertas.columns = [str(c).strip().upper() for c in df_alertas.columns]
                    total_sos = len(df_alertas[df_alertas['ESTADO'] == "PENDIENTE"])
                    st.metric("🚨 S.O.S ACTIVOS", total_sos)
                else: st.metric("🚨 S.O.S ACTIVOS", "0")
            contar_panicos_monitoreo()
    
        col2.metric("📡 RED", "OPERATIVA")
        col3.metric("👤 OPERADOR", f"{st.session_state.user_sel}")
        
        with col4.container():
            @st.fragment(run_every=1)
            def mostrar_reloj_monitoreo():
                st.metric("🕒 HORA LOCAL", obtener_hora_argentina().split(" ")[1])
        
        # ... mostrar_reloj_monitoreo() s igual que la tenías...)
        
        
        # --- TABS Y RADAR ---
        t_radar, t_mensajeria, t_vig, t_nov = st.tabs(["🚨 RADAR S.O.S", "💬 MENSAJERÍA", "👥 PADRÓN", "🔄 NOVEDADES"]) 
        
        with t_radar:
            st.subheader("📡 RADAR GLOBAL")
            
            # --- AQUÍ ESTÁ EL MAPA BIEN UBICADO ---
            if not df_mapa_monitoreo.empty:
                # Ahora el mean() no fallará porque los datos son números
                centro_mapa = [df_mapa_monitoreo['LATITUD'].mean(), df_mapa_monitoreo['LONGITUD'].mean()]
                
                m_mon = folium.Map(location=centro_mapa, zoom_start=11)
                
                for _, r in df_mapa_monitoreo.iterrows():
                    folium.CircleMarker(
                        location=[r['LATITUD'], r['LONGITUD']], 
                        radius=7, color="#00E5FF", fill=True
                    ).add_to(m_mon)
                
                st_folium(m_mon, width="100%", height=550)
            else:
                st.warning("No hay objetivos válidos.")
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------#
        

    elif st.session_state.rol_sel == "SUPERVISOR":
        # --- Código de SUPERVISOR que extrajimos antes ---
        if st.session_state.sup_autenticado:
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

            # --- 2. REGISTRO DIRECTO ---
            st.markdown("---")
            st.subheader("📍 REGISTRO DIRECTO (SIN QR)")
            df_objetivos_filtrados = df_objetivos[df_objetivos['SUPERVISOR'] == sup_activo_normalizado] if not df_objetivos.empty else pd.DataFrame()
            
            opciones_obj_dir = df_objetivos_filtrados['OBJETIVO'].unique()
            if len(opciones_obj_dir) > 0:
                obj_select = st.selectbox("Seleccione Objetivo:", opciones_obj_dir, key="obj_select_directo")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("✅ ARRIBO DIRECTO", use_container_width=True):
                        registrar_movimiento_supervisor(st.session_state.user_sel, obj_select, "ARRIBO")
                        st.success(f"Arribo en {obj_select}")
                with c2:
                    if st.button("🚪 RETIRO DIRECTO", use_container_width=True):
                        registrar_movimiento_supervisor(st.session_state.user_sel, obj_select, "RETIRO")
                        st.success(f"Retiro en {obj_select}")
            else:
                st.warning("No hay objetivos asignados para registro directo.")

            # --- 3. TABS Y FUNCIONES ---
            df_msg = leer_matriz_nube("MENSAJERIA")
            nombre_user = st.session_state.user_sel.upper()
            total_nuevos = len(df_msg[((df_msg['DESTINATARIO'] == "TODOS") | (df_msg['DESTINATARIO'] == "SUPERVISORES") | (df_msg['DESTINATARIO'] == nombre_user)) & (df_msg['ESTADO'] == "PENDIENTE")]) if not df_msg.empty else 0
            label_msg = f"💬 MENSAJERÍA GLOBAL ({total_nuevos})" if total_nuevos > 0 else "💬 MENSAJERÍA GLOBAL"

            t_vis_qr, t_ruta_gmaps, t_car_tac, t_mensajeria_sup, t_pres_sup = st.tabs([
                "Visita QR", "📲 RUTA GOOGLE MAPS", "Carga Táctica", label_msg, "📋 NOVEDADES Y RELEVOS"
            ])

            with t_vis_qr:
                st.markdown("### 📱 ESCANEO TÁCTICO")
                if not df_objetivos_filtrados.empty:
                    obj_a_generar = st.selectbox("Seleccione objetivo:", df_objetivos_filtrados['OBJETIVO'].unique())
                    if obj_a_generar:
                        url_final = f"https://tu-app-de-aion.streamlit.app/?obj={obj_a_generar.replace(' ', '%20')}"
                        qr = qrcode.QRCode(version=1, box_size=10, border=3)
                        qr.add_data(url_final)
                        qr.make(fit=True)
                        st.image(qr.make_image(fill_color="black", back_color="white").get_image(), width=250)
                
                st.markdown("---") 
                st.markdown("### 📝 REGISTRO DE ACTA DE FLOTA")
                with st.form(key="form_acta_flota", clear_on_submit=True):
                    col1, col2 = st.columns(2)
                    v_patente = col1.text_input("PATENTE/MÓVIL:").upper()
                    v_km_ini = col1.number_input("KM INICIAL:", min_value=0)
                    v_km_fin = col2.number_input("KM FINAL:", min_value=0)
                    v_comb = col2.selectbox("COMBUSTIBLE:", ["NO", "SI - MEDIA CARGA", "SI - TANQUE LLENO"])
                    
                    if st.form_submit_button("REGISTRAR ACTA"):
                        escribir_registro_nube("CONTROL_FLOTA", [obtener_hora_argentina(), st.session_state.user_sel, v_patente, v_km_ini, v_km_fin, v_comb])
                        st.success("✅ Acta registrada.")

            with t_ruta_gmaps:
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
                        st.caption("⚠️ Al presionar el botón, se abrirá la aplicación de Google Maps en tu dispositivo.")
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
                st.markdown("### 📋 NOVEDADES DE MI GRUPO")
        else:
            st.warning("Supervisor no autenticado.")
#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------#

    elif st.session_state.rol_sel == "JEFE DE OPERACIONES":
        # --- Código de JEFE DE OPERACIONES ---
        col1, col2, col3, col4 = st.columns(4)
        # ... (tu lógica de métricas y pestañas de Jefe) ...

    elif st.session_state.rol_sel == "GERENCIA":
        # --- Código de GERENCIA ---
        col1, col2, col3, col4 = st.columns(4)
        # ... (tu lógica de métricas y pestañas de Gerencia) ...

    elif st.session_state.rol_sel == "VIGILADOR":
        # --- Código de VIGILADOR ---
        st.markdown('<div class="panel-novedad">', unsafe_allow_html=True)
        # ... (tu lógica de fichaje, relevo y pánico) ...

    elif st.session_state.rol_sel == "ADMINISTRADOR":
        # --- Código de ADMINISTRADOR ---
        u_ing = st.text_input("ADMIN_USER")
        p_ing = st.text_input("ADMIN_PASS", type="password")
        if u_ing == "admin" and p_ing == "aion2026": 
            st.success("Núcleo Maestro desbloqueado.")
            # Aquí puedes agregar las herramientas de admin
        else:
            if u_ing or p_ing: st.error("Acceso denegado.")
            
    else:
        st.info("Seleccione una función en el panel lateral para comenzar.")


    
   
