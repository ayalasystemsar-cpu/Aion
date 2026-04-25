import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from datetime import datetime, timedelta, timezone
import pytz  
import numpy as np
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from streamlit_js_eval import get_geolocation

    
# --- 1. CONFIGURACIÓN E IDENTIDAD VISUAL CORPORATIVA ---
st.set_page_config(page_title="AION-YAROKU", layout="wide", initial_sidebar_state="expanded")

# ✅ Función para hora Argentina (va aquí, después de los imports y configuración)
def obtener_hora_argentina():
    tz = pytz.timezone("America/Argentina/Buenos_Aires")
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
    
# Inyección CSS Avanzada (Glassmorphism, Alarmas y Estética Letal)
st.markdown(
    """
    <style>
    .stApp { background-color: #0A0A0A; color: #FFFFFF; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    [data-testid="stSidebar"] { background-color: #111111; border-right: 2px solid #00E5FF; }
    h1, h2, h3, .stSubheader { color: #00E5FF !important; font-weight: bold; letter-spacing: 1px; }
    .stButton>button { background-color: #1A1A1A; color: #00E5FF; border: 1px solid #00E5FF; transition: 0.3s; width: 100%; font-weight: bold; border-radius: 8px;}
    .stButton>button:hover { background-color: #00E5FF; color: #000000; box-shadow: 0 0 15px #00E5FF; transform: translateY(-2px); }
    
    /* Escudo Institucional en Sidebar */
    .logo-container {
        background: rgba(0, 229, 255, 0.05);
        border: 1px solid rgba(0, 229, 255, 0.2);
        border-radius: 15px;
        padding: 15px;
        text-align: center;
        margin-bottom: 20px;
        box-shadow: inset 0 0 20px rgba(0, 229, 255, 0.05);
    }
    
    /* Alarmas y Semáforos */
    .alerta-panico { background-color: #FF0000 !important; color: white !important; font-size: 28px; text-align: center; padding: 25px; border-radius: 12px; font-weight: bold; animation: blink 0.5s infinite; border: 2px solid #FFF;}
    .novedad-roja { border-left: 5px solid #FF0000; padding-left: 10px; background-color: rgba(255,0,0,0.1); padding: 10px; border-radius: 5px;}
    .novedad-amarilla { border-left: 5px solid #FFCC00; padding-left: 10px; background-color: rgba(255,204,0,0.1); padding: 10px; border-radius: 5px;}
    .novedad-verde { border-left: 5px solid #00FF00; padding-left: 10px; background-color: rgba(0,255,0,0.1); padding: 10px; border-radius: 5px;}
    
    @keyframes blink { 0% { opacity: 1; } 50% { opacity: 0.2; } 100% { opacity: 1; } }
    </style>
    """, unsafe_allow_html=True
)

# --- 2. MEMORIA DE SESIÓN Y TELEMETRÍA (ANTI-RESETEO) ---
if 'rol_sel' not in st.session_state: st.session_state.rol_sel = "SUPERVISOR"
if 'user_sel' not in st.session_state: st.session_state.user_sel = "AYALA BRIAN"
if 'qr_mode' not in st.session_state: st.session_state.qr_mode = "Seleccionar..."
if 'hora_inicio_auditoria' not in st.session_state: st.session_state.hora_inicio_auditoria = None

# --- 3. NÚCLEO DE CONEXIÓN Y MATRIZ NUBE ---
ID_MAESTRO_DB = "1Md0VkOnwUJWldq0S1fB9UrmOKv4MG__JVG3tQsda0Uw"

def conectar_google():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
    return gspread.authorize(creds)

def escribir_registro(pestana, datos_fila):
    try:
        gc = conectar_google()
        hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
        hoja.append_row(datos_fila)
        return True
    except: return False

def actualizar_celda(pestana, fila_excel, col_letra, nuevo_valor):
    try:
        gc = conectar_google()
        hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
        hoja.update_acell(f"{col_letra}{fila_excel}", nuevo_valor)
        return True
    except: return False

def borrar_fila_excel(pestana, fila_excel):
    try:
        gc = conectar_google()
        hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
        hoja.delete_rows(fila_excel)
        return True
    except: return False

@st.cache_data(ttl=5)
def leer_matriz_nube(pestana):
    try:
        gc = conectar_google()
        hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
        return pd.DataFrame(hoja.get_all_records())
    except: return pd.DataFrame()

@st.cache_data(ttl=10)
def cargar_objetivos():
    df = leer_matriz_nube("OBJETIVOS")
    if not df.empty:
        df.columns = df.columns.str.strip().str.upper()
        df['LATITUD'] = pd.to_numeric(df['LATITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        df['LONGITUD'] = pd.to_numeric(df['LONGITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        return df.dropna(subset=['LATITUD', 'LONGITUD'])
    # Estructura 9 columnas pactada
    return pd.DataFrame(columns=['OBJETIVO', 'DIRECCION', 'LOCALIDAD', 'SUPERVISOR', 'LATITUD', 'LONGITUD', 'RESPONSABLE', 'ALARMA', 'POLICIA'])

df_objetivos = cargar_objetivos()
def calcular_objetivo_cercano(lat, lon, df_obj):


    # Triangulación euclidiana rápida para módulo SOS
    if df_obj.empty or lat == "Desconocida": return "Sin datos", "Sin datos"
    df_temp = df_obj.copy()
    df_temp['distancia'] = np.sqrt((df_temp['LATITUD'] - lat)*2 + (df_temp['LONGITUD'] - lon)*2)
    cercano = df_temp.loc[df_temp['distancia'].idxmin()]
    return cercano['OBJETIVO'], cercano.get('POLICIA', 'No registrada')


# --- 4. MENSAJERÍA Y ENRUTAMIENTO INTELIGENTE (7 COLUMNAS) ---
def mostrar_buzon(usuario):
    st.subheader("📥 Bandeja de Inteligencia (Comunicaciones)")
    df_msgs = leer_matriz_nube("MENSAJERIA")
    if not df_msgs.empty and 'DESTINATARIO' in df_msgs.columns:
        msgs = df_msgs[(df_msgs['DESTINATARIO'].astype(str).str.strip() == usuario) | (df_msgs['DESTINATARIO'].astype(str).str.strip() == 'TODOS')]
        if msgs.empty: st.info("Canal despejado. Sin novedades.")
        else:
            for idx, r in msgs.sort_values(by=df_msgs.columns[0], ascending=False).iterrows():
                estado = str(r.get('ESTADO', 'ENVIADO')).strip().upper()
                fila_real = idx + 2 
                gravedad = str(r.get('GRAVEDAD', 'VERDE')).upper()
                
                clase_css = ""
                if "ROJO" in gravedad: clase_css = "novedad-roja"
                elif "AMARILLO" in gravedad: clase_css = "novedad-amarilla"
                elif "VERDE" in gravedad: clase_css = "novedad-verde"

                with st.expander(f"{'✅' if estado == 'LEÍDO' else '✉️'} [{r.iloc[0]}] De: {r.get('REMITENTE', 'SISTEMA')} - Pri: {gravedad}"):
                    st.markdown(f"<div class='{clase_css}'><b>Asunto:</b> {r.get('ASUNTO', 'Novedad')}<br><br>{r.get('MENSAJE', '')}</div>", unsafe_allow_html=True)
                    
                    if estado != "LEÍDO" and usuario != "CENTRAL MONITOREO":
                        if st.button("Acuse de Recibo", key=f"acuse_{idx}"):
                            # Apunta a la Columna F (ESTADO)
                            if actualizar_celda("MENSAJERIA", fila_real, "F", "LEÍDO"): 
                                st.success("Lectura confirmada. Registro auditado.")
                                st.cache_data.clear()
                                st.rerun()

# --- 5. ESTRUCTURA LATERAL E IDENTIDAD ---
with st.sidebar:
    st.markdown('<div class="logo-container">', unsafe_allow_html=True)
    try: 
        st.image("assets/logo_aion.png", use_column_width=True)
    except: 
        st.markdown("<h2>AION YAROKU</h2>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # 1. ASIGNACIÓN DE IDENTIDAD (Secuencia obligatoria para evitar el NameError)
    st.session_state.rol_sel = st.selectbox("PERFIL OPERATIVO", ["SUPERVISOR", "MONITOREO", "JEFE DE OPERACIONES", "GERENCIA", "ADMINISTRADOR"], index=["SUPERVISOR", "MONITOREO", "JEFE DE OPERACIONES", "GERENCIA", "ADMINISTRADOR"].index(st.session_state.rol_sel))
    rol = st.session_state.rol_sel
    
    lista_sups = ["AYALA BRIAN", "SUPERVISOR NOCTURNO", "SERANTES WALTER", "SANOJA LUIS", "DIAZ MARCELO", "MAZACOTTE CLAUDIO", "PORZIO GONZALO", "CARRIZO WALTER"]
    
    if rol == "SUPERVISOR":
        usuario_auth = st.session_state.user_sel
    elif rol == "MONITOREO":
        usuario_auth = "CENTRAL MONITOREO"
    elif rol == "JEFE DE OPERACIONES":
        usuario_auth = "DARÍO CECILIA"
    elif rol == "GERENCIA":
        usuario_auth = "LUIS BONGIORNO"
    elif rol == "ADMINISTRADOR":
        if st.text_input("CREDENCIAL", type="password") != st.secrets.get("admin_password", "aion2026"): 
            st.stop()
        usuario_auth = "AYALA BRIAN (ADMIN)"

    # 2. BOTONES TÁCTICOS (Ejecución post-identidad)
    st.markdown("---")
    if rol == "SUPERVISOR":
        if st.button("🚨 ACTIVAR PÁNICO", use_container_width=True):
            loc = get_geolocation()
            lat, lon = (loc['coords']['latitude'], loc['coords']['longitude']) if loc else ("Desconocida", "Desconocida")
            
            if escribir_registro("ALERTAS", [obtener_hora_argentina(), usuario_auth, "CRÍTICO", "PENDIENTE", f"LAT: {lat} | LON: {lon}", ""]):
                st.error("S.O.S TRANSMITIDO. TRIANGULANDO APOYO.")

    if st.button("🔄 FORZAR REFRESCO"): 
        st.cache_data.clear()
        st.rerun()

# --- 6. MÓDULO SUPERVISOR: TÁCTICA Y TELEMETRÍA ---
if rol == "SUPERVISOR" and usuario_auth:
    st.header(f"Estación Táctica: {usuario_auth}")
    
    # Telemetría Logística a tabla CONTROL_FLOTA (6 columnas)
    with st.expander("Control de Unidad Móvil (Inicio/Fin de Turno)", expanded=False):
        c_movf, c_km1, c_km2, c_comb = st.columns(4)
        movil_flota = c_movf.selectbox("Dominio/Móvil", ["S-001", "S-002", "S-003", "S-004", "S-005", "S-006", "S-007"], key="mov_flota")
        km_in = c_km1.number_input("Km Inicial", min_value=0)
        km_out = c_km2.number_input("Km Final", min_value=0)
        comb_cargado = c_comb.number_input("Combustible (Lts)", min_value=0.0)
        
        if st.button("Sellar Odometría"):
            # Escribe 6 columnas exactas: Fecha, Supervisor, Movil, Km_Inicial, Km_Final, Combustible
            if km_out >= km_in:
                escribir_registro("CONTROL_FLOTA", [str(datetime.now().strftime("%Y-%m-%d")), usuario_auth, movil_flota, km_in, km_out, comb_cargado])
                st.success(f"Logística de flota sellada en la matriz.")
            else: st.warning("El kilometraje final no puede ser menor al inicial.")

    t1, t2, t3 = st.tabs(["📍 RADAR & QR", "📤 CARGA TÁCTICA", "💬 COMUNICACIÓN"])
    
    if usuario_auth == "SUPERVISOR NOCTURNO": df_zona = df_objetivos
    else:
        apellido = usuario_auth.split()[-1].upper()
        df_zona = df_objetivos[df_objetivos['SUPERVISOR'].str.upper().str.contains(apellido, na=False)] if not df_objetivos.empty else pd.DataFrame()

    with t1:
        c_map, c_ctrl = st.columns([2, 1])
        with c_map:
            if not df_zona.empty:
                m_s = folium.Map(location=[df_zona['LATITUD'].mean(), df_zona['LONGITUD'].mean()], zoom_start=12, tiles="CartoDB dark_matter")
                for _, row in df_zona.iterrows(): folium.Marker([row['LATITUD'], row['LONGITUD']], popup=row['OBJETIVO']).add_to(m_s)
                st_folium(m_s, width="100%", height=450)
        
        with c_ctrl:
            if not df_zona.empty:
                dest = st.selectbox("Servicio Actual:", df_zona['OBJETIVO'].unique())
                t_obj = df_zona[df_zona['OBJETIVO'] == dest].iloc[0]
                lat_dest, lon_dest = t_obj["LATITUD"], t_obj["LONGITUD"]
                
                st.markdown("---")
                st.subheader("Ruteo Táctico")
                url_waze = f"https://waze.com/ul?ll={lat_dest},{lon_dest}&navigate=yes"
                url_maps = f"https://www.google.com/maps/dir/?api=1&destination={lat_dest},{lon_dest}"
                
                c_btn1, c_btn2 = st.columns(2)
                c_btn1.markdown(f'<a href="{url_waze}" target="_blank"><button style="width:100%; padding:10px; background-color:#33CCFF; color:black; border:none; border-radius:5px; font-weight:bold;">🚙 WAZE</button></a>', unsafe_allow_html=True)
                c_btn2.markdown(f'<a href="{url_maps}" target="_blank"><button style="width:100%; padding:10px; background-color:#4285F4; color:white; border:none; border-radius:5px; font-weight:bold;">🗺️ MAPS</button></a>', unsafe_allow_html=True)
                
                st.markdown("---")
                st.subheader("Control de Mando QR (Blindado)")
                st.session_state.qr_mode = st.radio("Acción:", ["Seleccionar...", "🟢 INGRESO", "🔴 SALIDA"], horizontal=True, index=["Seleccionar...", "🟢 INGRESO", "🔴 SALIDA"].index(st.session_state.qr_mode))
                
                if st.session_state.qr_mode != "Seleccionar...":
                    if st.checkbox("🔓 Habilitar Escáner"):
                        f_cam = st.camera_input("Enfoque el código del Servicio")
                        if f_cam:
                            tipo = "ENTRADA" if "INGRESO" in st.session_state.qr_mode else "SALIDA"
                            hora_actual = str(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                            
                            # Telemetría de Tiempos Invisible a LOG_PRESENCIA (6 columnas)
                            delta_t = "0 min"
                            if tipo == "ENTRADA": st.session_state.hora_inicio_auditoria = datetime.now()
                            elif tipo == "SALIDA" and st.session_state.hora_inicio_auditoria:
                                mins = (datetime.now() - st.session_state.hora_inicio_auditoria).total_seconds() / 60
                                delta_t = f"{int(mins)} min"
                                st.session_state.hora_inicio_auditoria = None

                            # Escribe 6 columnas exactas: Fecha, Supervisor, Objetivo, Tipo, Estado, Tiempo_Invertido
                            if escribir_registro("LOG_PRESENCIA", [hora_actual, usuario_auth, dest, tipo, "QR_VALIDADO", delta_t]):
                                st.success(f"✅ OPERACIÓN {tipo} CONFIRMADA EN MATRIZ.")
                                st.session_state.qr_mode = "Seleccionar..."
                                st.rerun()

    with t2:
        st.subheader("Reporte Ágil de Novedades (Híbrido)")
        with st.form("acta_hibrida"):
            f_dest = st.selectbox("Objetivo Auditado:", df_zona['OBJETIVO'].unique()) if not df_zona.empty else "N/A"
            
            c_mov, c_km = st.columns(2)
            f_mov = c_mov.selectbox("Móvil Asignado", ["S-001", "S-002", "S-003", "S-004", "S-005", "S-006", "S-007"])
            f_km = c_km.number_input("Kilometraje Actual", min_value=0)
            
            c_sem1, c_sem2 = st.columns([1, 2])
            gravedad = c_sem1.selectbox("Gravedad (Semáforo):", ["VERDE", "AMARILLO", "ROJO"])
            f_vig = c_sem2.text_input("Vigilador/es Presente/s")
            
            f_nov = st.text_area("Carga de Acta (Use Teclado o Micrófono del móvil)")
            
            if st.form_submit_button("Sellar y Transmitir Acta"):
                grav_corta = gravedad.split(" ")[0] 
                
                # Escritura EXACTA a ACTAS_FLOTAS (10 columnas)
                escribir_registro("ACTAS_FLOTAS", [
                    str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")), # 1. Fecha
                    usuario_auth,                                      # 2. Supervisor
                    f_mov,                                             # 3. Móvil
                    "",                                                # 4. Patente
                    f_km,                                              # 5. Km
                    "",                                                # 6. Rendimiento
                    f_vig,                                             # 7. Vigilador
                    f_dest,                                            # 8. Objetivo
                    f_nov,                                             # 9. Informe
                    grav_corta                                         # 10. Gravedad
                ])
                
                # Enrutamiento Inteligente a MENSAJERIA (7 columnas)
                if grav_corta == "ROJO": dest_msg = "TODOS"
                elif grav_corta == "AMARILLO": dest_msg = "CENTRAL MONITOREO"
                else: dest_msg = "DARÍO CECILIA" 
                
                escribir_registro("MENSAJERIA", [
                    str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")), # 1. Fecha
                    usuario_auth,                                      # 2. Remitente
                    dest_msg,                                          # 3. Destinatario
                    f"Acta {f_dest}",                                  # 4. Asunto
                    f_nov,                                             # 5. Mensaje
                    "ENVIADO",                                         # 6. Estado
                    grav_corta                                         # 7. Gravedad
                ])
                st.success("Acta encriptada y derivada según protocolo jerárquico.")

    with t3:
        mostrar_buzon(usuario_auth)

# --- 7. MÓDULO MONITOREO: RESPUESTA CRÍTICA Y GESTIÓN CONTINUA ---
elif rol == "MONITOREO":
    st.header("Consola Central de Inteligencia")
    
    # Telemetría Frontal
    st.markdown("### Estado de Red en Tiempo Real")
    m1, m2, m3 = st.columns(3)
    df_alertas = leer_matriz_nube("ALERTAS")
    sos_activos = len(df_alertas[df_alertas['ESTADO'].astype(str).str.strip().str.upper() == 'PENDIENTE']) if not df_alertas.empty and 'ESTADO' in df_alertas.columns else 0
    m1.metric("🚨 S.O.S Activos", sos_activos)
    
    df_msg = leer_matriz_nube("MENSAJERIA")
    amarillas = len(df_msg[(df_msg['GRAVEDAD'].astype(str).str.upper() == 'AMARILLO') & (df_msg['ESTADO'].astype(str).str.upper() != 'LEÍDO')]) if not df_msg.empty and 'GRAVEDAD' in df_msg.columns else 0
    m2.metric("⚠️ Novedades en Proceso", amarillas)
    
    df_p = leer_matriz_nube("LOG_PRESENCIA")
    fecha_hoy = obtener_hora_argentina().split(" ")[0]
    qrs_hoy = len(df_p[df_p['FECHA'].astype(str).str.contains(fecha_hoy)]) if not df_p.empty and 'FECHA' in df_p.columns else 0
    m3.metric("📲 Fichajes QR (Hoy)", qrs_hoy)
    st.markdown("---")

    tab_radar, tab_libro, tab_com = st.tabs(["🚨 RADAR & S.O.S", "📖 LIBRO DE BASE", "💬 COMUNICACIÓN"])
    
    with tab_radar:
        if sos_activos > 0:
            datos_sos = df_alertas[df_alertas['ESTADO'].astype(str).str.strip().str.upper() == 'PENDIENTE'].iloc[-1]
            op_en_riesgo = datos_sos.get('USUARIO', 'Desconocido')
            carga_util = str(datos_sos.get('CARGA_UTIL', ''))
            
            lat_alerta, lon_alerta = "Desconocida", "Desconocida"
            if "LAT" in carga_util:
                try:
                    partes = carga_util.split("|")
                    lat_alerta = float(partes[0].split(":")[1].strip())
                    lon_alerta = float(partes[1].split(":")[1].strip())
                except: pass
            
            obj_cercano, policia_zona = calcular_objetivo_cercano(lat_alerta, lon_alerta, df_objetivos)
            
            st.markdown("""<audio autoplay loop><source src="https://www.soundjay.com/buttons/sounds/beep-01a.mp3" type="audio/mpeg"></audio>""", unsafe_allow_html=True)
            st.markdown(f'''
                <div class="alerta-panico">
                    🚨 BRECHA DE SEGURIDAD DETECTADA 🚨<br>
                    <span style="font-size:20px;">Unidad: {op_en_riesgo} | {carga_util}</span><br>
                    <span style="font-size:22px; color: #FFFF00;">OBJETIVO POSIBLE: {obj_cercano}</span><br>
                    <span style="font-size:24px; font-weight: 900;">POLICÍA ASIGNADA: {policia_zona}</span>
                </div>
            ''', unsafe_allow_html=True)

            with st.form("resolucion_crisis"):
                st.write("Resolución Operativa y Clasificación")
                op = st.text_input("Firma del Monitorista")
                
                # Menú estricto de semáforos tácticos
                opciones_semaforo = [
                    "🔴 911 - Comando Policial", 
                    "🔴 Robo en Proceso", 
                    "🔴 Gendarmería Nacional",
                    "🟡 107 - SAME / Ambulancia", 
                    "🟡 100 - Bomberos",
                    "🟢 Intervención Interna (Secutec)", 
                    "🟢 Falsa Alarma / Error de Operador", 
                    "🟢 Simulacro / Prueba de Sistema"
                ]
                derivacion = st.selectbox("Clasificación de Derivación (Semáforo):", opciones_semaforo)
                res = st.text_area("Detalle del acta")
                
                if st.form_submit_button("Neutralizar y Clasificar"):
                    hora_cierre = obtener_hora_argentina()
                    fila_alerta = df_alertas[df_alertas['ESTADO'].astype(str).str.strip().str.upper() == 'PENDIENTE'].index[-1] + 2 
                    
                    actualizar_celda("ALERTAS", fila_alerta, "D", "RESUELTO") 
                    actualizar_celda("ALERTAS", fila_alerta, "F", f"OPE: {op} | Cierre: {hora_cierre} | Entidad: {derivacion} | Acta: {res}")
                    st.success("S.O.S Neutralizado y clasificado en la matriz.")
                    st.cache_data.clear()
                    st.rerun()

        c_map, c_log = st.columns([2, 1])
        with c_map:
            if not df_objetivos.empty:
                m_mon = folium.Map(location=[df_objetivos['LATITUD'].mean(), df_objetivos['LONGITUD'].mean()], zoom_start=11, tiles="CartoDB dark_matter")
                for _, r in df_objetivos.iterrows(): folium.Marker([r['LATITUD'], r['LONGITUD']], tooltip=r['OBJETIVO']).add_to(m_mon)
                st_folium(m_mon, width="100%", height=500)
        with c_log:
            st.subheader("Auditoría QR en Vivo")
            if not df_p.empty: st.dataframe(df_p.tail(15).iloc[::-1], use_container_width=True, hide_index=True)

    with tab_libro:
        with st.form("acta_rutina"):
            novedades_base = st.text_area("Novedades de la guardia / Relevos")
            if st.form_submit_button("Sellar Acta"):
                escribir_registro("MENSAJERIA", [obtener_hora_argentina(), usuario_auth, "DARÍO CECILIA", "Libro de Base", novedades_base, "ENVIADO", "VERDE"])
                st.success("Acta sellada.")

    with tab_com:
        mostrar_buzon(usuario_auth)
        with st.form("emision_monitoreo"):
            dest_m = st.selectbox("Para:", ["TODOS", "DARÍO CECILIA", "LUIS BONGIORNO"] + lista_sups)
            asu_m = st.text_input("Asunto"); men_m = st.text_area("Mensaje"); grav_m = st.selectbox("Prioridad", ["VERDE", "AMARILLO", "ROJO"])
            if st.form_submit_button("Transmitir"):
                escribir_registro("MENSAJERIA", [obtener_hora_argentina(), usuario_auth, dest_m, asu_m, men_m, "ENVIADO", grav_m])
                st.success("Transmitido.")

# --- 8. MÓDULO EJECUTIVO (JEFATURA Y GERENCIA) ---
elif rol in ["JEFE DE OPERACIONES", "GERENCIA"]:
    st.header(f"Comando Estratégico: {usuario_auth}")
    
    # CSS dinámico para las tarjetas semáforo
    st.markdown("""
    <style>
    .card-roja { background: linear-gradient(145deg, #1a0000, #330000); border-left: 6px solid #FF0000; padding: 15px; margin-bottom: 15px; border-radius: 5px; box-shadow: 0 2px 10px rgba(255,0,0,0.2); }
    .card-amarilla { background: linear-gradient(145deg, #1a1a00, #333300); border-left: 6px solid #FFCC00; padding: 15px; margin-bottom: 15px; border-radius: 5px; box-shadow: 0 2px 10px rgba(255,204,0,0.2); }
    .card-verde { background: linear-gradient(145deg, #001a00, #003300); border-left: 6px solid #00FF00; padding: 15px; margin-bottom: 15px; border-radius: 5px; box-shadow: 0 2px 10px rgba(0,255,0,0.2); }
    .titulo-card { font-size: 14px; color: #00E5FF; font-weight: bold; text-transform: uppercase; margin-bottom: 8px;}
    .texto-card { font-size: 14px; color: #FFFFFF; font-family: monospace; }
    </style>
    """, unsafe_allow_html=True)

    t_crisis, t_com, t_gest, t_aud = st.tabs(["🚨 CENTRO DE CRISIS", "📥 COMUNICACIONES", "📤 EJECUCIÓN ESTRATÉGICA", "📍 TABLERO DE AUDITORÍA"])
    
    with t_crisis:
        st.markdown("### Historial de S.O.S (Clasificación por Gravedad)")
        df_alertas = leer_matriz_nube("ALERTAS")
        
        if not df_alertas.empty and 'ESTADO' in df_alertas.columns:
            resueltas = df_alertas[df_alertas['ESTADO'].astype(str).str.strip().str.upper() == 'RESUELTO']
            
            # Contadores lógicos
            c_rojas = c_amarillas = c_verdes = 0
            tarjetas_html = ""
            
            for idx, row in resueltas.iloc[::-1].iterrows():
                hora = row.get('FECHA_HORA', 'Sin datos')
                usuario_r = row.get('USUARIO', 'Desconocido')
                resolucion_raw = str(row.get('RESOLUCION', ''))
                
                op_mon = "Desconocido"; entidad = "N/A"; acta = resolucion_raw
                try:
                    if " | " in resolucion_raw:
                        partes = resolucion_raw.split(" | ")
                        for p in partes:
                            if p.startswith("OPE:"): op_mon = p.replace("OPE:", "").strip()
                            elif p.startswith("Entidad:"): entidad = p.replace("Entidad:", "").strip()
                            elif p.startswith("Acta:"): acta = p.replace("Acta:", "").strip()
                except: pass

                # Clasificación automática por presencia del emoji
                clase_css = "card-verde"
                if "🔴" in entidad:
                    clase_css = "card-roja"; c_rojas += 1
                elif "🟡" in entidad:
                    clase_css = "card-amarilla"; c_amarillas += 1
                elif "🟢" in entidad:
                    clase_css = "card-verde"; c_verdes += 1
                else:
                    c_verdes += 1 

                tarjetas_html += f"""
                <div class="{clase_css}">
                    <div class="titulo-card">{entidad}</div>
                    <div class="texto-card">
                        <b>Detonó:</b> {usuario_r} a las {hora}<br>
                        <b>Neutralizó:</b> {op_mon}<br>
                        <b>Acta Operativa:</b> {acta}
                    </div>
                </div>
                """

            # Panel frontal de contadores
            col1, col2, col3 = st.columns(3)
            col1.metric("🔴 CRÍTICAS", c_rojas)
            col2.metric("🟡 ASISTENCIALES", c_amarillas)
            col3.metric("🟢 PRUEBAS/INTERNAS", c_verdes)
            st.markdown("---")
            
            if resueltas.empty:
                st.info("No hay eventos registrados en la matriz.")
            else:
                st.markdown(tarjetas_html, unsafe_allow_html=True)
        else:
            st.warning("Sin conexión a la matriz de alertas.")

    with t_com: 
        mostrar_buzon(usuario_auth)
    
    with t_gest:
        st.subheader("Emisión de Directivas")
        with st.form("orden_e"):
            dest_e = st.selectbox("Destinatario:", ["TODOS", "LUIS BONGIORNO", "DARÍO CECILIA"] + lista_sups)
            asu_e = st.text_input("Asunto")
            men_e = st.text_area("Cuerpo de la orden")
            grav_e = st.selectbox("Nivel de Prioridad", ["VERDE", "AMARILLO", "ROJO"])
            if st.form_submit_button("Ejecutar Orden"):
                escribir_registro("MENSAJERIA", [obtener_hora_argentina(), usuario_auth, dest_e, asu_e, men_e, "ENVIADO", grav_e])
                st.success("Directiva inyectada a la red.")
                
    with t_aud: 
        st.write("Panel de control de kilómetros y fichajes en desarrollo estratégico.")

# --- 9. ADMINISTRADOR (CANDADO DE TITANIO MANTENIDO Y PLENAMENTE OPERATIVO) ---
elif rol == "ADMINISTRADOR":
    st.header("⚙️ NÚCLEO MAESTRO AION-YAROKU")
    st.success("AUTENTICACIÓN EXITOSA. BIENVENIDO AL SISTEMA, AYALA BRIAN.")
    
    st.markdown("---")
    # --- SISTEMA DE MANTENIMIENTO Y BÓVEDA HISTÓRICA ---
    # 1. DETECTOR DE PROTOCOLO DOMINICAL (6 = Domingo)
    es_domingo = datetime.now(timezone(timedelta(hours=-3))).weekday() == 6
    
    if es_domingo:
        st.markdown('''
            <div style="background-color: #FF0000; color: white; padding: 20px; border-radius: 10px; text-align: center; border: 2px solid white; animation: blink 1s infinite;">
                ⚠️ PROTOCOLO DE CIERRE DOMINICAL ACTIVO ⚠️<br>
                <span style="font-size: 14px;">Ejecute el archivado para liberar carga de la matriz y resguardar el historial semanal.</span>
            </div>
        ''', unsafe_allow_html=True)
        st.write("")

    # 2. ACCIÓN DE ARCHIVADO QUIRÚRGICO
    if st.button("📦 EJECUTAR BARRIDA Y ARCHIVADO HISTÓRICO", use_container_width=True):
        with st.status("Iniciando migración a Bóvedas Históricas...", expanded=True) as status:
            
            st.write("Analizando matriz de ALERTAS...")
            df_a = leer_matriz_nube("ALERTAS")
            if not df_a.empty:
                a_mover = df_a[df_a['ESTADO'].astype(str).str.strip().str.upper() == 'RESUELTO']
                a_quedar = df_a[df_a['ESTADO'].astype(str).str.strip().str.upper() != 'RESUELTO']
                
                if not a_mover.empty:
                    for _, fila in a_mover.iterrows():
                        escribir_registro("HISTORICO_ALERTAS", fila.tolist())
                    
                    sh = conectar_google_sheets()
                    ws_a = sh.worksheet("ALERTAS")
                    ws_a.clear()
                    ws_a.append_row(df_a.columns.tolist())
                    if not a_quedar.empty:
                        ws_a.append_rows(a_quedar.values.tolist())
                    st.write(f"✅ {len(a_mover)} Alertas resguardadas en Bóveda.")

            st.write("Analizando matriz de MENSAJERÍA...")
            df_m = leer_matriz_nube("MENSAJERIA")
            if not df_m.empty:
                m_mover = df_m[df_m['ESTADO'].astype(str).str.strip().str.upper() == 'LEÍDO']
                m_quedar = df_m[df_m['ESTADO'].astype(str).str.strip().str.upper() != 'LEÍDO']
                
                if not m_mover.empty:
                    for _, fila in m_mover.iterrows():
                        escribir_registro("HISTORICO", fila.tolist())
                    
                    ws_m = sh.worksheet("MENSAJERIA")
                    ws_m.clear()
                    ws_m.append_row(df_m.columns.tolist())
                    if not m_quedar.empty:
                        ws_m.append_rows(m_quedar.values.tolist())
                    st.write(f"✅ {len(m_mover)} Mensajes archivados con éxito.")

            status.update(label="Mantenimiento Finalizado. Matriz Optimizada.", state="complete", expanded=False)
            st.balloons()
            st.cache_data.clear()
            st.rerun()
    st.markdown("---")
    # --- FIN DEL SISTEMA DE MANTENIMIENTO ---
    st.subheader("⚖️ Buzón de Peticiones y Ejecución (Gestión de Base)")
    df_pet = leer_matriz_nube("PETICIONES")
    if not df_pet.empty and 'ESTADO' in df_pet.columns:
        pendientes = df_pet[df_pet['ESTADO'].astype(str).str.strip().str.upper() == 'PENDIENTE']
        if pendientes.empty: st.info("No hay solicitudes pendientes de Gerencia o Jefatura.")
        else:
            for idx, r in pendientes.iterrows():
                tipo = str(r.get('ACCIÓN', r.get('ACCION', '')))
                detalle = str(r.get('DETALLE', ''))
                categoria = str(r.get('CATEGORIA', 'OBJETIVO'))
                fila_pet_real = idx + 2
                
                with st.expander(f"⚠️ Solicitud de {tipo} - De: {r.get('GERENTE', r.get('USUARIO', ''))} - Detalle: {detalle} ({categoria})"):
                    c_ok, c_no = st.columns(2)
                    if c_ok.button(f"✅ AUTORIZAR EJECUCIÓN", key=f"ok_{idx}"):
                        if tipo.upper() == "BAJA" and categoria.upper() == "OBJETIVO":
                            indice_borrar = df_objetivos[df_objetivos['OBJETIVO'] == detalle].index
                            if not indice_borrar.empty:
                                # Borra de la pestaña OBJETIVOS (+2 para convertir índice a fila Google Sheet)
                                if borrar_fila_excel("OBJETIVOS", int(indice_borrar[0]) + 2):
                                    actualizar_celda("PETICIONES", fila_pet_real, "E", "EJECUTADO") # Columna E = ESTADO
                                    st.success(f"Servicio {detalle} eliminado de la base.")
                                    st.cache_data.clear(); st.rerun()
                        elif tipo.upper() == "ALTA" and categoria.upper() == "OBJETIVO":
                            actualizar_celda("PETICIONES", fila_pet_real, "E", "EJECUTADO")
                            st.success(f"Autorizado. (El alta física en mapa requiere cargar lat/lon en el Excel).")
                            st.cache_data.clear(); st.rerun()

                    if c_no.button(f"❌ RECHAZAR SOLICITUD", key=f"no_{idx}"):
                        actualizar_celda("PETICIONES", fila_pet_real, "E", "RECHAZADO")
                        st.warning("Petición rechazada y archivada.")
                        st.cache_data.clear(); st.rerun()
    else: st.info("Matriz de peticiones no detectada o vacía.")

    st.markdown("---")
    st.subheader("Auditoría Cruda de Terreno (Logs Nube)")
    df_p = leer_matriz_nube("LOG_PRESENCIA")
    if not df_p.empty: st.dataframe(df_p.tail(30).iloc[::-1], use_container_width=True)

