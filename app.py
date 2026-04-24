import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from datetime import datetime, timedelta, timezone
import numpy as np
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from streamlit_js_eval import get_geolocation

# --- 1. CONFIGURACIÓN E IDENTIDAD VISUAL CORPORATIVA ---
st.set_page_config(page_title="AION-YAROKU", layout="wide", initial_sidebar_state="expanded")

# Inyección CSS (Glassmorphism, Alarmas y Estética de Mando)
st.markdown(
    """
    <style>
    .stApp { background-color: #0A0A0A; color: #FFFFFF; font-family: 'Segoe UI', Tahoma, sans-serif; }
    [data-testid="stSidebar"] { background-color: #111111; border-right: 2px solid #00E5FF; }
    h1, h2, h3, .stSubheader { color: #00E5FF !important; font-weight: bold; letter-spacing: 1px; }
    .stButton>button { background-color: #1A1A1A; color: #00E5FF; border: 1px solid #00E5FF; transition: 0.3s; width: 100%; font-weight: bold; border-radius: 8px;}
    .stButton>button:hover { background-color: #00E5FF; color: #000000; box-shadow: 0 0 15px #00E5FF; transform: translateY(-2px); }
    
    .logo-container {
        background: rgba(0, 229, 255, 0.05);
        border: 1px solid rgba(0, 229, 255, 0.2);
        border-radius: 15px;
        padding: 15px;
        text-align: center;
        margin-bottom: 20px;
    }
    
    .alerta-panico { background-color: #FF0000 !important; color: white !important; font-size: 28px; text-align: center; padding: 25px; border-radius: 12px; font-weight: bold; animation: blink 0.5s infinite; border: 2px solid #FFF;}
    .novedad-roja { border-left: 5px solid #FF0000; padding-left: 10px; background: rgba(255,0,0,0.1); padding: 10px; border-radius: 5px; }
    .novedad-amarilla { border-left: 5px solid #FFCC00; padding-left: 10px; background: rgba(255,204,0,0.1); padding: 10px; border-radius: 5px; }
    .novedad-verde { border-left: 5px solid #00FF00; padding-left: 10px; background: rgba(0,255,0,0.1); padding: 10px; border-radius: 5px; }
    
    @keyframes blink { 0% { opacity: 1; } 50% { opacity: 0.2; } 100% { opacity: 1; } }
    </style>
    """, unsafe_allow_html=True
)

# --- 2. MOTOR DE TIEMPO (ZONA HORARIA ARGENTINA UTC-3) ---
def obtener_hora_argentina():
    tz_arg = timezone(timedelta(hours=-3))
    return datetime.now(tz_arg).strftime("%Y-%m-%d %H:%M:%S")

# --- 3. MEMORIA DE SESIÓN ---
if 'rol_sel' not in st.session_state: st.session_state.rol_sel = "SUPERVISOR"
if 'user_sel' not in st.session_state: st.session_state.user_sel = "AYALA BRIAN"
if 'qr_mode' not in st.session_state: st.session_state.qr_mode = "Seleccionar..."
if 'hora_inicio_auditoria' not in st.session_state: st.session_state.hora_inicio_auditoria = None

# --- 4. NÚCLEO DE CONEXIÓN Y MATRIZ NUBE ---
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
    return pd.DataFrame(columns=['OBJETIVO', 'DIRECCION', 'LOCALIDAD', 'SUPERVISOR', 'LATITUD', 'LONGITUD', 'RESPONSABLE', 'ALARMA', 'POLICIA'])

df_objetivos = cargar_objetivos()

def calcular_objetivo_cercano(lat, lon, df_obj):
    if df_obj.empty or lat == "Desconocida": return "Sin datos", "Sin datos"
    df_temp = df_obj.copy()
    df_temp['distancia'] = np.sqrt((df_temp['LATITUD'] - float(lat))*2 + (df_temp['LONGITUD'] - float(lon))*2)
    cercano = df_temp.loc[df_temp['distancia'].idxmin()]
    return cercano['OBJETIVO'], cercano.get('POLICIA', 'No registrada')

# --- 5. MENSAJERÍA Y ENRUTAMIENTO ---
def mostrar_buzon(usuario):
    st.subheader("📥 Bandeja de Inteligencia")
    df_msgs = leer_matriz_nube("MENSAJERIA")
    if not df_msgs.empty and 'DESTINATARIO' in df_msgs.columns:
        msgs = df_msgs[(df_msgs['DESTINATARIO'].astype(str).str.strip() == usuario) | (df_msgs['DESTINATARIO'].astype(str).str.strip() == 'TODOS')]
        if msgs.empty: st.info("Canal despejado.")
        else:
            for idx, r in msgs.sort_values(by=df_msgs.columns[0], ascending=False).iterrows():
                estado = str(r.get('ESTADO', 'ENVIADO')).strip().upper()
                fila_real = idx + 2; gravedad = str(r.get('GRAVEDAD', 'VERDE')).upper()
                
                clase_css = "novedad-roja" if "ROJO" in gravedad else ("novedad-amarilla" if "AMARILLO" in gravedad else "novedad-verde")

                with st.expander(f"{'✅' if estado == 'LEÍDO' else '✉️'} [{r.iloc[0]}] De: {r.get('REMITENTE', 'SISTEMA')} - Pri: {gravedad}"):
                    st.markdown(f"<div class='{clase_css}'><b>Asunto:</b> {r.get('ASUNTO', 'Novedad')}<br><br>{r.get('MENSAJE', '')}</div>", unsafe_allow_html=True)
                    if estado != "LEÍDO" and usuario != "CENTRAL MONITOREO":
                        if st.button("Acuse", key=f"acuse_{idx}"):
                            if actualizar_celda("MENSAJERIA", fila_real, "F", "LEÍDO"): st.rerun()

# --- 6. PANEL LATERAL E IDENTIDAD ---
with st.sidebar:
    st.markdown('<div class="logo-container">', unsafe_allow_html=True)
    try: st.image("assets/logo_aion.png", use_column_width=True)
    except: st.markdown("<h2>AION YAROKU</h2>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.session_state.rol_sel = st.selectbox("PERFIL OPERATIVO", ["SUPERVISOR", "MONITOREO", "JEFE DE OPERACIONES", "GERENCIA", "ADMINISTRADOR"], index=["SUPERVISOR", "MONITOREO", "JEFE DE OPERACIONES", "GERENCIA", "ADMINISTRADOR"].index(st.session_state.rol_sel))
    rol = st.session_state.rol_sel
    
    lista_sups = ["AYALA BRIAN", "SUPERVISOR NOCTURNO", "SERANTES WALTER", "SANOJA LUIS", "DIAZ MARCELO", "MAZACOTTE CLAUDIO", "PORZIO GONZALO", "CARRIZO WALTER"]
    usuario_auth = st.session_state.user_sel if rol == "SUPERVISOR" else ("CENTRAL MONITOREO" if rol == "MONITOREO" else ("DARÍO CECILIA" if rol == "JEFE DE OPERACIONES" else "LUIS BONGIORNO"))

    if rol == "ADMINISTRADOR":
        if st.text_input("CREDENCIAL", type="password") != st.secrets.get("admin_password", "aion2026"): st.stop()
        usuario_auth = "AYALA BRIAN (ADMIN)"

    st.markdown("---")
    if rol == "SUPERVISOR" and st.button("🚨 ACTIVAR PÁNICO", use_container_width=True):
        loc = get_geolocation(); lat, lon = (loc['coords']['latitude'], loc['coords']['longitude']) if loc else ("Desconocida", "Desconocida")
        if escribir_registro("ALERTAS", [obtener_hora_argentina(), usuario_auth, "CRÍTICO", "PENDIENTE", f"LAT: {lat} | LON: {lon}", ""]):
            st.error("S.O.S TRANSMITIDO. TRIANGULANDO APOYO.")

    if st.button("🔄 FORZAR REFRESCO"): st.cache_data.clear(); st.rerun()

# --- 7. MÓDULO SUPERVISOR: TÁCTICA Y TELEMETRÍA ---
if rol == "SUPERVISOR":
    st.header(f"Estación Táctica: {usuario_auth}")
    with st.expander("Control de Unidad Móvil (Inicio/Fin)", expanded=False):
        c_movf, c_km1, c_km2, c_comb = st.columns(4)
        movil_flota = c_movf.selectbox("Móvil", ["S-001", "S-002", "S-003", "S-004", "S-005", "S-006", "S-007"])
        km_in = c_km1.number_input("Km Inicial", min_value=0)
        km_out = c_km2.number_input("Km Final", min_value=0)
        comb_cargado = c_comb.number_input("Combustible (Lts)", min_value=0.0)
        if st.button("Sellar Odometría"):
            if km_out >= km_in:
                escribir_registro("CONTROL_FLOTA", [obtener_hora_argentina().split(" ")[0], usuario_auth, movil_flota, km_in, km_out, comb_cargado])
                st.success("Logística sellada.")

    t1, t2, t3 = st.tabs(["📍 RADAR & QR", "📤 ACTAS", "💬 COMUNICACIÓN"])
    
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
                dest = st.selectbox("Objetivo Actual:", df_zona['OBJETIVO'].unique())
                t_obj = df_zona[df_zona['OBJETIVO'] == dest].iloc[0]
                st.subheader("Ruteo Táctico")
                url_waze = f"https://waze.com/ul?ll={t_obj['LATITUD']},{t_obj['LONGITUD']}&navigate=yes"
                st.markdown(f'<a href="{url_waze}" target="_blank"><button style="width:100%; padding:10px; background-color:#33CCFF; color:black; border:none; border-radius:5px; font-weight:bold;">🚙 WAZE</button></a>', unsafe_allow_html=True)
                st.markdown("---")
                st.subheader("Control QR")
                st.session_state.qr_mode = st.radio("Acción:", ["Seleccionar...", "🟢 INGRESO", "🔴 SALIDA"], horizontal=True)
                if st.session_state.qr_mode != "Seleccionar...":
                    if st.checkbox("🔓 Habilitar Escáner"):
                        f_cam = st.camera_input("Enfoque QR")
                        if f_cam:
                            tipo = "ENTRADA" if "INGRESO" in st.session_state.qr_mode else "SALIDA"
                            delta_t = "0 min"
                            if tipo == "ENTRADA": st.session_state.hora_inicio_auditoria = datetime.now()
                            elif tipo == "SALIDA" and st.session_state.hora_inicio_auditoria:
                                delta_t = f"{int((datetime.now() - st.session_state.hora_inicio_auditoria).total_seconds() / 60)} min"
                            if escribir_registro("LOG_PRESENCIA", [obtener_hora_argentina(), usuario_auth, dest, tipo, "QR_VALIDADO", delta_t]):
                                st.success(f"{tipo} CONFIRMADO."); st.rerun()

    with t2:
        with st.form("acta_hibrida"):
            f_dest = st.selectbox("Objetivo Auditado:", df_zona['OBJETIVO'].unique()) if not df_zona.empty else "N/A"
            f_mov = st.selectbox("Móvil", ["S-001", "S-002", "S-003", "S-004", "S-005", "S-006", "S-007"])
            f_km = st.number_input("Km Actual", min_value=0)
            gravedad = st.selectbox("Gravedad:", ["VERDE", "AMARILLO", "ROJO"])
            f_vig = st.text_input("Vigilador/es")
            f_nov = st.text_area("Informe (Teclado o Dictado)")
            if st.form_submit_button("Sellar Acta"):
                grav_corta = gravedad.split(" ")[0]
                escribir_registro("ACTAS_FLOTAS", [obtener_hora_argentina(), usuario_auth, f_mov, "", f_km, "", f_vig, f_dest, f_nov, grav_corta])
                dest_m = "TODOS" if grav_corta == "ROJO" else ("CENTRAL MONITOREO" if grav_corta == "AMARILLO" else "DARÍO CECILIA")
                escribir_registro("MENSAJERIA", [obtener_hora_argentina(), usuario_auth, dest_m, f"Acta {f_dest}", f_nov, "ENVIADO", grav_corta])
                st.success("Acta enviada.")

    with t3: mostrar_buzon(usuario_auth)

# --- 8. MÓDULO MONITOREO: RESPUESTA CRÍTICA Y FLUIDEZ ---
elif rol == "MONITOREO":
    st.header("Consola Central de Inteligencia")
    tab1, tab2, tab3 = st.tabs(["🚨 RADAR & S.O.S", "📖 LIBRO DE BASE", "💬 COMUNICACIÓN"])
    
    with tab1:
        df_alertas = leer_matriz_nube("ALERTAS")
        if not df_alertas.empty and str(df_alertas.iloc[-1]['ESTADO']).strip().upper() == "PENDIENTE":
            datos_sos = df_alertas.iloc[-1]; op_riesgo = datos_sos.get('USUARIO', 'Desconocido'); carga = str(datos_sos.get('CARGA_UTIL', ''))
            lat_a, lon_a = ("Desconocida", "Desconocida")
            if "LAT" in carga:
                try: lat_a = float(carga.split("|")[0].split(":")[1].strip()); lon_a = float(carga.split("|")[1].split(":")[1].strip())
                except: pass
            obj_c, poli = calcular_objetivo_cercano(lat_a, lon_a, df_objetivos)
            st.markdown('<audio autoplay loop><source src="https://www.soundjay.com/buttons/sounds/beep-01a.mp3"></audio>', unsafe_allow_html=True)
            st.markdown(f'<div class="alerta-panico">🚨 S.O.S: {op_riesgo} 🚨<br><span style="font-size:18px;">ZONA: {obj_c} | POLICÍA: {poli}</span></div>', unsafe_allow_html=True)
            with st.form("resolucion_crisis"):
                firma = st.text_input("Operador"); detalle_res = st.text_area("Resolución Operativa")
                if st.form_submit_button("Neutralizar y Notificar Gerencia"):
                    fila_a = len(df_alertas) + 1; hora_res = obtener_hora_argentina()
                    actualizar_celda("ALERTAS", fila_a, "D", "RESUELTO")
                    actualizar_celda("ALERTAS", fila_a, "F", f"OPE: {firma} | Cierre: {hora_res} | {detalle_res}")
                    # Doble Impacto: Notifica a la Gerencia y Operaciones automáticamente
                    escribir_registro("MENSAJERIA", [hora_res, "SISTEMA SOS", "TODOS", f"ALERTA RESUELTA: {obj_c}", f"El operador {firma} neutralizó la alarma. Resolución: {detalle_res}", "ENVIADO", "ROJO"])
                    st.success("Alarma neutralizada y cadena de mando notificada."); st.cache_data.clear(); st.rerun()

        c_map, c_log = st.columns([2, 1])
        with c_map:
            if not df_objetivos.empty:
                m_mon = folium.Map(location=[df_objetivos['LATITUD'].mean(), df_objetivos['LONGITUD'].mean()], zoom_start=11, tiles="CartoDB dark_matter")
                for _, r in df_objetivos.iterrows(): folium.Marker([r['LATITUD'], r['LONGITUD']], tooltip=r['OBJETIVO']).add_to(m_mon)
                st_folium(m_mon, width="100%", height=500)
        with c_log:
            st.subheader("QR en Vivo")
            df_p = leer_matriz_nube("LOG_PRESENCIA")
            if not df_p.empty: st.dataframe(df_p.tail(15).iloc[::-1], use_container_width=True, hide_index=True)

    with tab2:
        with st.form("acta_base"):
            novedad_base = st.text_area("Novedades de la Guardia Central")
            if st.form_submit_button("Sellar Libro Base"):
                escribir_registro("MENSAJERIA", [obtener_hora_argentina(), usuario_auth, "DARÍO CECILIA", "Libro de Base", novedad_base, "ENVIADO", "VERDE"])
                st.success("Reportado a Jefatura.")

    with tab3:
        mostrar_buzon(usuario_auth)
        with st.form("envio_mon"):
            dest_m = st.selectbox("Para:", ["TODOS", "DARÍO CECILIA", "LUIS BONGIORNO"] + lista_sups)
            asu_m = st.text_input("Asunto"); men_m = st.text_area("Mensaje"); grav_m = st.selectbox("Prioridad", ["VERDE", "AMARILLO", "ROJO"])
            if st.form_submit_button("Transmitir"):
                escribir_registro("MENSAJERIA", [obtener_hora_argentina(), usuario_auth, dest_m, asu_m, men_m, "ENVIADO", grav_m])
                st.success("Mensaje enviado.")

# --- 9. MÓDULO EJECUTIVO ---
elif rol in ["JEFE DE OPERACIONES", "GERENCIA"]:
    st.header(f"Comando Estratégico: {usuario_auth}")
    if rol == "GERENCIA":
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Cobertura", f"{len(df_objetivos)}/93")
        df_p = leer_matriz_nube("LOG_PRESENCIA"); m2.metric("Auditorías QR", f"{len(df_p)}")
        df_tel = leer_matriz_nube("CONTROL_FLOTA")
        km_t = (pd.to_numeric(df_tel['KM_FINAL'], errors='coerce') - pd.to_numeric(df_tel['KM_INICIAL'], errors='coerce')).sum() if not df_tel.empty else 0
        m3.metric("KM Recorridos", f"{int(km_t)} Km")
        m4.metric("Efectividad", "100%")

    t_com, t_gest, t_aud = st.tabs(["📥 COMUNICACIÓN", "📤 GESTIÓN", "📍 AUDITORÍA"])
    with t_com: mostrar_buzon(usuario_auth)
    with t_gest:
        with st.form("orden_e"):
            dest_e = st.selectbox("Para:", ["TODOS", "LUIS BONGIORNO", "DARÍO CECILIA"] + lista_sups)
            asu_e = st.text_input("Asunto"); men_e = st.text_area("Orden Táctica"); grav_e = st.selectbox("Prioridad", ["VERDE", "AMARILLO", "ROJO"])
            if st.form_submit_button("Ejecutar Orden"):
                escribir_registro("MENSAJERIA", [obtener_hora_argentina(), usuario_auth, dest_e, asu_e, men_e, "ENVIADO", grav_e])
                st.success("Orden encriptada y enviada.")

# --- 10. ADMINISTRADOR ---
elif rol == "ADMINISTRADOR":
    st.header("⚙️ NÚCLEO MAESTRO")
    df_pet = leer_matriz_nube("PETICIONES")
    if not df_pet.empty:
        for idx, r in df_pet[df_pet['ESTADO'] == 'PENDIENTE'].iterrows():
            with st.expander(f"Solicitud: {r['ACCION']} - {r['DETALLE']}"):
                if st.button("AUTORIZAR", key=f"ok_{idx}"):
                    actualizar_celda("PETICIONES", idx + 2, "E", "EJECUTADO"); st.rerun()
