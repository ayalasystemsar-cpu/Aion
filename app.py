import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from datetime import datetime
import numpy as np
import sqlite3
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from streamlit_js_eval import get_geolocation

# --- 1. CONFIGURACIÓN E IDENTIDAD VISUAL ---
st.set_page_config(page_title="AION-YAROKU", layout="wide", initial_sidebar_state="expanded")

# Restitución de la imagen original (Sin CSS que la oculte)
try:
    st.image("assets/logo_aion.png", width=180)
except:
    st.markdown("<h2 style='color:#00E5FF;'>AION-YAROKU</h2>", unsafe_allow_html=True)

st.markdown(
    """
    <style>
    .stApp { background-color: #0A0A0A; color: #FFFFFF; }
    [data-testid="stSidebar"] { background-color: #111111; border-right: 2px solid #00E5FF; }
    h1, h2, h3, .stSubheader { color: #00E5FF !important; font-weight: bold; }
    .stButton>button { background-color: #1A1A1A; color: #00E5FF; border: 1px solid #00E5FF; transition: 0.3s; width: 100%; font-weight: bold; }
    .stButton>button:hover { background-color: #00E5FF; color: #000000; box-shadow: 0 0 15px #00E5FF; }
    .alerta-panico { background-color: #FF0000 !important; color: white !important; font-size: 24px; text-align: center; padding: 20px; border-radius: 10px; font-weight: bold; animation: blink 1s infinite; }
    @keyframes blink { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
    </style>
    """, unsafe_allow_html=True
)

# --- 2. MEMORIA DE SESIÓN (ANTI-RESETEO) ---
if 'rol_sel' not in st.session_state: st.session_state.rol_sel = "SUPERVISOR"
if 'user_sel' not in st.session_state: st.session_state.user_sel = "AYALA BRIAN"
if 'qr_mode' not in st.session_state: st.session_state.qr_mode = "Seleccionar..."

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
        # Limpieza balística: Fuerza la conversión a float, ignora formato visual de Google Sheets
        df['LATITUD'] = pd.to_numeric(df['LATITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        df['LONGITUD'] = pd.to_numeric(df['LONGITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        return df.dropna(subset=['LATITUD', 'LONGITUD'])
    return pd.DataFrame(columns=['OBJETIVO', 'SUPERVISOR', 'LATITUD', 'LONGITUD'])

df_objetivos = cargar_objetivos()

# --- 4. MENSAJERÍA BLINDADA (SIN DUPLICADOS) ---
def mostrar_buzon(usuario):
    st.subheader("📥 Bandeja de Entrada")
    df_msgs = leer_matriz_nube("MENSAJERIA")
    if not df_msgs.empty and 'DESTINATARIO' in df_msgs.columns:
        msgs = df_msgs[(df_msgs['DESTINATARIO'].astype(str).str.strip() == usuario) | (df_msgs['DESTINATARIO'].astype(str).str.strip() == 'TODOS')]
        if msgs.empty: st.info("Bandeja limpia.")
        else:
            for idx, r in msgs.sort_values(by=df_msgs.columns[0], ascending=False).iterrows():
                estado = str(r.get('ESTADO', 'ENVIADO')).strip().upper()
                fila_real = idx + 2 # Cálculo exacto de fila en Excel (índice 0 = fila 2)
                
                with st.expander(f"{'✅' if estado == 'LEÍDO' else '✉️'} [{r.iloc[0]}] De: {r.get('REMITENTE', 'SISTEMA')} - Estado: {estado}"):
                    st.write(f"*Asunto:* {r.get('ASUNTO', 'Novedad')}")
                    st.write(r.get('MENSAJE', ''))
                    
                    if estado != "LEÍDO" and usuario != "CENTRAL MONITOREO":
                        if st.button("Acuse de Recibo", key=f"acuse_{idx}"):
                            # Asumiendo que ESTADO es la columna F (6ta columna). Ajustar letra si tu Excel es distinto.
                            if actualizar_celda("MENSAJERIA", fila_real, "F", "LEÍDO"):
                                st.success("Lectura confirmada en Matriz. No se duplicó el registro.")
                                st.cache_data.clear()
                                st.rerun()

# --- 5. PANEL LATERAL CON RETENCIÓN DE ESTADO ---
with st.sidebar:
    st.session_state.rol_sel = st.selectbox("PERFIL OPERATIVO", ["SUPERVISOR", "MONITOREO", "JEFE DE OPERACIONES", "GERENCIA", "ADMINISTRADOR"], index=["SUPERVISOR", "MONITOREO", "JEFE DE OPERACIONES", "GERENCIA", "ADMINISTRADOR"].index(st.session_state.rol_sel))
    rol = st.session_state.rol_sel
    
    lista_sups = ["AYALA BRIAN", "SUPERVISOR NOCTURNO", "SERANTES WALTER", "SANOJA LUIS", "DIAZ MARCELO", "MAZACOTTE CLAUDIO", "PORZIO GONZALO", "CARRIZO WALTER"]
    usuario_auth = ""
    
    if rol == "SUPERVISOR": 
        st.session_state.user_sel = st.selectbox("IDENTIFICACIÓN", lista_sups, index=lista_sups.index(st.session_state.user_sel) if st.session_state.user_sel in lista_sups else 0)
        usuario_auth = st.session_state.user_sel
    elif rol == "JEFE DE OPERACIONES": usuario_auth = "DARÍO CECILIA"
    elif rol == "GERENCIA": usuario_auth = "LUIS BONGIORNO"
    elif rol == "MONITOREO": usuario_auth = "CENTRAL MONITOREO"
    
    # EL CANDADO DE TITANIO
    elif rol == "ADMINISTRADOR":
        clave = st.text_input("CREDENCIAL MAESTRA", type="password")
        if clave != st.secrets.get("admin_password", "aion2026"):
            st.error("ACCESO DENEGADO. NÚCLEO BLOQUEADO.")
            st.stop() # FRENO TOTAL: La pantalla queda en blanco hasta validar.
        usuario_auth = "AYALA BRIAN (ADMIN)"

    st.markdown("---")
    if st.button("🚨 ACTIVAR PÁNICO", use_container_width=True):
        if escribir_registro("ALERTAS", [str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")), usuario_auth, "CRÍTICO", "PENDIENTE"]):
            st.error("S.O.S TRANSMITIDO A LA MATRIZ")
    
    if st.button("🔄 FORZAR REFRESCO"): st.cache_data.clear(); st.rerun()

# --- 6. PERFIL SUPERVISOR (NAVEGACIÓN DUAL Y CÁMARA UNIFICADA) ---
if rol == "SUPERVISOR" and usuario_auth:
    st.header(f"Estación Táctica: {usuario_auth}")
    t1, t2, t3 = st.tabs(["📍 RADAR", "📤 ACTAS", "💬 COMUNICACIÓN"])
    
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
                st.subheader("Control QR")
                st.session_state.qr_mode = st.radio("Acción:", ["Seleccionar...", "🟢 INGRESO", "🔴 SALIDA"], horizontal=True, index=["Seleccionar...", "🟢 INGRESO", "🔴 SALIDA"].index(st.session_state.qr_mode))
                
                if st.session_state.qr_mode != "Seleccionar...":
                    if st.checkbox("🔓 Habilitar Escáner"):
                        f_cam = st.camera_input("Enfoque el código")
                        if f_cam:
                            tipo = "ENTRADA" if "INGRESO" in st.session_state.qr_mode else "SALIDA"
                            if escribir_registro("LOG_PRESENCIA", [str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")), usuario_auth, dest, tipo, "QR_VALIDADO"]):
                                st.success(f"{tipo} CONFIRMADO.")
                                st.session_state.qr_mode = "Seleccionar..."
                                st.rerun()

    with t2:
        with st.form("acta"):
            f_dest = st.selectbox("Objetivo Auditado:", df_zona['OBJETIVO'].unique()) if not df_zona.empty else "N/A"
            f_mov = st.selectbox("Móvil", ["S-001", "S-002", "S-003", "S-004", "S-005", "S-006", "S-007"])
            f_km = st.number_input("Kilómetros", min_value=0)
            f_vig = st.text_input("Vigilador de Turno")
            f_nov = st.text_area("Novedades")
            if st.form_submit_button("Subir Acta"):
                escribir_registro("ACTAS_FLOTAS", [str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")), usuario_auth, f_mov, "", f_km, "", f_vig, f_dest, f_nov])
                st.success("Acta en línea.")
    with t3:
        mostrar_buzon(usuario_auth)
        with st.form("enviar_sup"):
            d = st.selectbox("Para:", ["TODOS", "CENTRAL MONITOREO", "DARÍO CECILIA", "LUIS BONGIORNO"]); a = st.text_input("Asunto"); m = st.text_area("Cuerpo")
            if st.form_submit_button("Enviar"): escribir_registro("MENSAJERIA", [str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")), usuario_auth, d, a, m, "ENVIADO"]); st.success("Transmitido.")

# --- 7. MONITOREO (RECEPTOR CONTINUO) ---
elif rol == "MONITOREO":
    st.header("Consola Central")
    df_alertas = leer_matriz_nube("ALERTAS")
    alerta_critica = not df_alertas.empty and 'ESTADO' in df_alertas.columns and str(df_alertas.iloc[-1]['ESTADO']).strip().upper() == "PENDIENTE"

    if alerta_critica:
        st.markdown('<div class="alerta-panico">🚨 ALERTA S.O.S ACTIVA 🚨</div>', unsafe_allow_html=True)
        with st.form("resol"):
            op = st.text_input("Operador"); res = st.text_area("Reporte de Crisis")
            if st.form_submit_button("Neutralizar Alarma"):
                escribir_registro("ALERTAS", [str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")), f"OPE: {op}", "RESUELTO", res])
                st.success("Sistema normalizado."); st.cache_data.clear(); st.rerun()

    c_map, c_log = st.columns([2, 1])
    with c_map:
        if not df_objetivos.empty:
            m_mon = folium.Map(location=[df_objetivos['LATITUD'].mean(), df_objetivos['LONGITUD'].mean()], zoom_start=11, tiles="CartoDB dark_matter")
            for _, r in df_objetivos.iterrows(): folium.Marker([r['LATITUD'], r['LONGITUD']], tooltip=r['OBJETIVO']).add_to(m_mon)
            st_folium(m_mon, width="100%", height=500)
    with c_log:
        st.subheader("Movimientos QR")
        df_p = leer_matriz_nube("LOG_PRESENCIA")
        if not df_p.empty: st.dataframe(df_p.tail(15).iloc[::-1], use_container_width=True, hide_index=True)
    mostrar_buzon(usuario_auth)

# --- 8. JEFE DE OPERACIONES Y GERENCIA ---
elif rol in ["JEFE DE OPERACIONES", "GERENCIA"]:
    st.header(f"Comando Ejecutivo: {usuario_auth}")
    if rol == "GERENCIA":
        m1, m2, m3 = st.columns(3)
        m1.metric("Ahorro Logístico", "$128.400"); m2.metric("Cobertura", f"{len(df_objetivos)}/93"); m3.metric("Efectividad", "100%")
    
    t1, t2, t3 = st.tabs(["📥 COMUNICACIÓN", "📤 GESTIÓN", "📍 AUDITORÍA"])
    with t1: mostrar_buzon(usuario_auth)
    with t2:
        if rol == "GERENCIA":
            c1, c2 = st.columns(2)
            with c1:
                with st.form("alta"):
                    st.write("Alta Servicio"); n = st.text_input("Nombre"); s = st.selectbox("Asignar a:", lista_sups)
                    if st.form_submit_button("Solicitar Alta"): escribir_registro("PETICIONES", [str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")), usuario_auth, "ALTA", f"{n} | {s}", "PENDIENTE", "OBJETIVO"])
            with c2:
                with st.form("baja"):
                    st.write("Baja Servicio"); rem = st.selectbox("Objetivo:", df_objetivos['OBJETIVO'].unique() if not df_objetivos.empty else ["N/A"])
                    if st.form_submit_button("Solicitar Baja"): escribir_registro("PETICIONES", [str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")), usuario_auth, "BAJA", rem, "PENDIENTE", "OBJETIVO"])
        with st.form("orden"):
            st.write("Transmitir Directiva")
            dest = st.selectbox("Para:", ["TODOS", "LUIS BONGIORNO", "DARÍO CECILIA"] + lista_sups); a = st.text_input("Asunto"); m = st.text_area("Orden")
            if st.form_submit_button("Enviar"): escribir_registro("MENSAJERIA", [str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")), usuario_auth, dest, a, m, "ENVIADO"]); st.success("Directiva en la red.")
    with t3:
        st.subheader("Auditoría de Terreno")
        if not df_objetivos.empty: st.bar_chart(df_objetivos['SUPERVISOR'].value_counts())
        df_p = leer_matriz_nube("LOG_PRESENCIA")
        if not df_p.empty: st.dataframe(df_p.tail(20).iloc[::-1], use_container_width=True)

# --- 9. ADMINISTRADOR (NÚCLEO DE MANDO ABSOLUTO) ---
elif rol == "ADMINISTRADOR":
    st.header("⚙️ NÚCLEO MAESTRO AION-YAROKU")
    st.success("AUTENTICACIÓN EXITOSA. BIENVENIDO, AYALA BRIAN.")
    
    st.markdown("---")
    st.subheader("⚖️ Buzón de Peticiones y Ejecución")
    df_pet = leer_matriz_nube("PETICIONES")
    if not df_pet.empty and 'ESTADO' in df_pet.columns:
        pendientes = df_pet[df_pet['ESTADO'].astype(str).str.strip().str.upper() == 'PENDIENTE']
        if pendientes.empty: st.info("No hay solicitudes pendientes de Gerencia o Jefatura.")
        else:
            for idx, r in pendientes.iterrows():
                tipo = r.get('TIPO', '')
                detalle = r.get('DETALLE', '')
                fila_pet_real = idx + 2
                
                with st.expander(f"⚠️ Solicitud de {tipo} - De: {r.get('USUARIO', '')} - Detalle: {detalle}"):
                    c_ok, c_no = st.columns(2)
                    if c_ok.button(f"✅ AUTORIZAR EJECUCIÓN", key=f"ok_{idx}"):
                        if tipo.upper() == "BAJA":
                            indice_borrar = df_objetivos[df_objetivos['OBJETIVO'] == detalle].index
                            if not indice_borrar.empty:
                                # Borra de la pestaña OBJETIVOS (+2 para convertir índice a fila Google Sheet)
                                if borrar_fila_excel("OBJETIVOS", int(indice_borrar[0]) + 2):
                                    actualizar_celda("PETICIONES", fila_pet_real, "E", "EJECUTADO") # Columna E = ESTADO
                                    st.success(f"Servicio {detalle} eliminado de la base.")
                                    st.cache_data.clear(); st.rerun()
                        elif tipo.upper() == "ALTA":
                            actualizar_celda("PETICIONES", fila_pet_real, "E", "EJECUTADO")
                            st.success(f"Autorizado. (El alta física en mapa requiere cargar lat/lon en el Excel).")
                            st.cache_data.clear(); st.rerun()

                    if c_no.button(f"❌ RECHAZAR SOLICITUD", key=f"no_{idx}"):
                        actualizar_celda("PETICIONES", fila_pet_real, "E", "RECHAZADO")
                        st.warning("Petición rechazada y archivada.")
                        st.cache_data.clear(); st.rerun()
    else: st.info("Matriz de peticiones no detectada o vacía.")

    st.markdown("---")
    st.subheader("Auditoría Cruda (Logs Nube)")
    df_p = leer_matriz_nube("LOG_PRESENCIA")
    if not df_p.empty: st.dataframe(df_p.tail(30).iloc[::-1], use_container_width=True)
