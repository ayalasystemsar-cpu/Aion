import streamlit as st
import datetime
from datetime import datetime, time
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
if 'ultimo_escaneo_tiempo' not in st.session_state: st.session_state.ultimo_escaneo_tiempo = 0


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
            doc = gc.open_by_key(ID_MAESTRO_DB)
            try:
                hoja = doc.worksheet(pestana)
            except:
                hoja = doc.add_worksheet(title=pestana, rows="200", cols="10")
                if pestana == "REGISTRO_QR_SUPERVISORES":
                    hoja.append_row(["FECHA_HORA", "OBJETIVO", "TIPO_ACCION", "SUPERVISOR", "ESTADO"])
                elif pestana == "ALERTAS":
                    hoja.append_row(["FECHA", "USUARIO", "TIPO", "ESTADO", "CARGA_UTIL", "INFORME"])
                elif pestana == "MENSAJERIA":
                    hoja.append_row(["FECHA", "REMITENTE", "DESTINATARIO", "ASUNTO", "MENSAJE", "ESTADO", "GRAVEDAD"])
            
            hoja.append_row(datos_fila)
            return True
    except Exception as e:
        print(f"Error escribiendo en nube: {e}")
        return False

def leer_matriz_nube(pestana):
    gc = conectar_google()
    if gc:
        try:
            doc = gc.open_by_key(ID_MAESTRO_DB)
            try:
                hoja = doc.worksheet(pestana)
            except:
                hoja = doc.add_worksheet(title=pestana, rows="200", cols="10")
                if pestana == "REGISTRO_QR_SUPERVISORES":
                    hoja.append_row(["FECHA_HORA", "OBJETIVO", "TIPO_ACCION", "SUPERVISOR", "ESTADO"])
            
            todas_filas = hoja.get_all_values()
            if not todas_filas or len(todas_filas) <= 1: return pd.DataFrame()
            encabezados = [str(h).strip().upper() for h in todas_filas[0]]
            df = pd.DataFrame(todas_filas[1:], columns=encabezados)
            df.columns = [str(c).strip().upper() for c in df.columns]
            return df.loc[:, ~df.columns.duplicated()]
        except: return pd.DataFrame()
    return pd.DataFrame()

def cargar_objetivos():
    df = leer_matriz_nube("OBJETIVOS")
    if not df.empty:
        df.columns = df.columns.str.strip().str.upper()
        df = df[df['OBJETIVO'].astype(str).str.strip() != ""]
        df = df[df['OBJETIVO'].notna()]
        if 'SUPERVISOR' in df.columns:
            df['SUPERVISOR'] = df['SUPERVISOR'].astype(str).str.strip().str.upper()
        return df
    return pd.DataFrame()

def cargar_datos_comisarias(): return leer_matriz_nube("COMISARIAS")

def obtener_hora_argentina():
    tz = pytz.timezone("America/Argentina/Buenos_Aires")
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

def renderizar_mensajeria_global(rol_contexto):
    if 'asunto_respuesta' not in st.session_state:
        st.session_state.asunto_respuesta = None

    df_msg = leer_matriz_nube("MENSAJERIA")
    st.subheader("💬 COMUNICACIONES OPERATIVAS")

    with st.form(key=f"form_msg_{rol_contexto}", clear_on_submit=True):
        if st.session_state.asunto_respuesta:
            st.info(f"↩️ Respondiendo al hilo: {st.session_state.asunto_respuesta}")
            asunto_input = st.text_input("ASUNTO:", value=st.session_state.asunto_respuesta, disabled=True)
        else:
            asunto_input = st.text_input("ASUNTO:")

        col_a, col_b = st.columns([3, 1])
        with col_a:
            txt_msg = st.text_input("MENSAJE:")
        with col_b:
            destinatarios_posibles = ["TODOS", "MONITOREO", "JEFE DE OPERACIONES", "GERENCIA", "SUPERVISORES", "VIGILADOR"] + LISTA_SUPS_TACTICOS
            destinatario = st.selectbox("PARA:", destinatarios_posibles)
            gravedad = st.selectbox("GRAVEDAD:", ["VERDE", "ROJA"])

        if st.form_submit_button("TRANSMITIR A LA RED"):
            if txt_msg.strip():
                escribir_registro_nube("MENSAJERIA", [
                    obtener_hora_argentina(), st.session_state.user_sel, destinatario, 
                    (asunto_input or "GENERAL").upper(), txt_msg.upper(), "PENDIENTE", gravedad
                ])
                st.session_state.mensaje_enviado = "RESPUESTA" if st.session_state.asunto_respuesta else "MENSAJE"
                st.session_state.asunto_respuesta = None
                st.rerun()

    if 'mensaje_enviado' in st.session_state:
        if st.session_state.mensaje_enviado == "RESPUESTA":
            st.success("✅ RESPUESTA ENVIADA")
        else:
            st.success("✅ MENSAJE ENVIADO")
        del st.session_state.mensaje_enviado

    if not df_msg.empty and 'ASUNTO' in df_msg.columns:
        for asunto, grupo in df_msg.groupby('ASUNTO'):
            with st.expander(f"💬 Hilo: {asunto}"):
                for _, msg in grupo.iterrows():
                    st.markdown(f"**{msg.get('REMITENTE', 'ANÓNIMO')}:** {msg.get('MENSAJE', '')}")
                if st.button(f"Responder a este hilo", key=f"btn_{asunto}_{rol_contexto}"):
                    st.session_state.asunto_respuesta = asunto
                    st.rerun()


# --- 3. IDENTIDAD Y LANDING ---

def aplicar_identidad_alfa():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@300;500;700&display=swap');
        .stApp { background: radial-gradient(circle at top, #0A0F1E 0%, #030305 100%) !important; color: #E0E0E0; font-family: 'Rajdhani', sans-serif; }
        .contenedor-logo-central { display: flex; justify-content: center; align-items: center; width: 100%; margin: 20px 0; }
        .logo-phoenix { width: 400px !important; border: 2px solid #00e5ff !important; box-shadow: 0 0 35px rgba(0, 229, 255, 0.5) !important; border-radius: 4px !important; background-color: #000 !important; }
        .estacion-titulo { font-family: 'Orbitron', sans-serif; color: #00E5FF !important; font-size: 32px; text-align: center; text-shadow: 0 0 15px rgba(0, 229, 255, 0.4); margin-bottom: 30px; }
        .stButton > button { background-color: #0A192F !important; color: #00E5FF !important; border: 1px solid #00e5ff !important; border-radius: 5px !important; font-family: 'Orbitron', sans-serif !important; }
        .stButton > button:hover { background-color: #00E5FF !important; color: #000 !important; }
        </style>
    """, unsafe_allow_html=True)

def mostrar_landing():
    aplicar_identidad_alfa()
    st.markdown('<div class="contenedor-logo-central"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" class="logo-phoenix"></div>', unsafe_allow_html=True)
    st.markdown('<div class="estacion-titulo">AION-YAROKU | COMMAND</div>', unsafe_allow_html=True)
    
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
                st.rerun()
            elif modo == "Iniciar Sesión":
                df_usuarios = leer_matriz_nube("USUARIOS")
                if not df_usuarios.empty and 'USUARIO' in df_usuarios.columns:
                    usuario_ok = df_usuarios[
                        (df_usuarios['USUARIO'].str.strip() == user.strip()) & 
                        (df_usuarios['CONTRASEÑA'].str.strip() == password.strip())
                    ]
                    if not usuario_ok.empty:
                        estado = usuario_ok.iloc[0]['ESTADO']
                        if estado == "APROBADO":
                            st.session_state.usuario_logueado = True
                            st.session_state.user_sel = user
                            st.session_state.rol_sel = usuario_ok.iloc[0]['ROL']
                            st.rerun()
                        else:
                            st.warning("⚠️ Tu cuenta existe pero está PENDIENTE de aprobación.")
                    else:
                        st.error("❌ Credenciales inválidas.")
                else:
                    st.error("❌ No se pudieron leer los usuarios de la base de datos.")
            else:
                escribir_registro_nube("USUARIOS", [user, password, rol_usuario, "PENDIENTE"])
                st.success("✅ Solicitud enviada. Quedamos a la espera de autorización.")

if not st.session_state.usuario_logueado:
    mostrar_landing()
    st.stop()


# --- FUNCIONES ADICIONALES ---

def actualizar_celda(pestana, fila, columna, valor):
    try:
        gc = conectar_google()
        if gc:
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
            hoja.update_acell(f"{columna}{fila}", valor)
            return True
    except: 
        return False

def registrar_movimiento_supervisor(supervisor, objetivo, accion):
    fecha_hora_arg = obtener_hora_argentina()
    fecha = fecha_hora_arg.split(" ")[0]
    hora = fecha_hora_arg.split(" ")[1]
    datos = [fecha, supervisor, objetivo, accion, hora]
    exito = escribir_registro_nube("JORNADA_SUPERVISORES", datos)
    return exito


aplicar_identidad_alfa()

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
        st.session_state.usuario_logueado = True
        st.session_state.rol_sel = "ADMINISTRADOR"
        st.session_state.user_sel = "ADMIN CENTRAL"
        st.session_state.sup_autenticado = False
        st.rerun()

    st.markdown("---")
    if st.button("🚪 CERRAR SESIÓN", use_container_width=True):
        st.session_state.usuario_logueado = False
        st.rerun()


# --- CABECERA CENTRAL ---

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


# --- ROL SUPERVISOR ---

if st.session_state.rol_sel == "SUPERVISOR":
    if st.session_state.sup_autenticado:
        sup_activo_normalizado = st.session_state.user_sel.strip().upper()
        
        if df_objetivos.empty:
            df_objetivos = cargar_objetivos()

        if not df_objetivos.empty and 'SUPERVISOR' in df_objetivos.columns:
            df_objetivos_filtrados = df_objetivos[df_objetivos['SUPERVISOR'].astype(str).str.strip().str.upper() == sup_activo_normalizado]
            if df_objetivos_filtrados.empty:
                df_objetivos_filtrados = df_objetivos
        else:
            df_objetivos_filtrados = df_objetivos
        
        obj_actual = st.session_state.get("obj_qr_tactico", "SIN OBJETIVO")

        st.subheader("⏱️ GESTIÓN DE JORNADA")
        _, col_j1, col_j2, _ = st.columns([2, 3, 3, 2]) 
        with col_j1:
            if st.button("🚀 INICIO DE JORNADA", use_container_width=True):
                registrar_movimiento_supervisor(st.session_state.user_sel, obj_actual, "INICIO")
                st.success("Jornada iniciada")
        with col_j2:
            if st.button("🏁 CIERRE DE JORNADA", use_container_width=True):
                registrar_movimiento_supervisor(st.session_state.user_sel, obj_actual, "FIN")
                st.success("Jornada cerrada")

        st.markdown("<br>", unsafe_allow_html=True)
        
        fecha_hoy_str = obtener_hora_argentina().split(" ")[0]
        total_asignados = len(df_objetivos_filtrados) if not df_objetivos_filtrados.empty else 0
        
        df_qr_sup_check = leer_matriz_nube("REGISTRO_QR_SUPERVISORES")
        
        ingresos_hoy = {}
        egresos_hoy = {}
        
        if not df_qr_sup_check.empty:
            df_qr_sup_check.columns = [str(c).strip().upper() for c in df_qr_sup_check.columns]
            
            df_qr_hoy = df_qr_sup_check[
                df_qr_sup_check['SUPERVISOR'].astype(str).str.upper().str.contains(sup_activo_normalizado, na=False) &
                df_qr_sup_check['FECHA_HORA'].astype(str).str.contains(fecha_hoy_str, na=False)
            ]
            
            for _, row in df_qr_hoy.iterrows():
                obj_name = str(row['OBJETIVO']).strip().upper()
                timestamp_completo = str(row['FECHA_HORA'])
                tipo_acc = str(row['TIPO_ACCION']).upper()
                
                if "EGRESO" in tipo_acc or "SALIDA" in tipo_acc:
                    egresos_hoy[obj_name] = timestamp_completo
                elif "INGRESO" in tipo_acc or "ENTRADA" in tipo_acc:
                    if obj_name not in ingresos_hoy:
                        ingresos_hoy[obj_name] = timestamp_completo

        total_visitados = len(ingresos_hoy)
        total_restantes = max(0, total_asignados - total_visitados)
        
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("📌 OBJETIVOS ASIGNADOS", total_asignados)
        col_m2.metric("✅ OBJETIVOS VISITADOS HOY", total_visitados)
        col_m3.metric("⏳ OBJETIVOS RESTANTES", total_restantes)
        
        st.markdown("---")
        st.markdown(f"### 📊 ESTADO DE MIS OBJETIVOS ASIGNADOS ({fecha_hoy_str})")
        if not df_objetivos_filtrados.empty:
            lista_estado_objs = []
            for _, r in df_objetivos_filtrados.iterrows():
                nombre_o = str(r['OBJETIVO']).strip().upper()
                
                f_ingreso = ingresos_hoy.get(nombre_o, "---")
                f_egreso = egresos_hoy.get(nombre_o, "---")
                
                tiempo_permanencia = "---"
                if f_ingreso != "---" and f_egreso != "---":
                    try:
                        dt_in = datetime.strptime(f_ingreso.split(".")[0], "%Y-%m-%d %H:%M:%S")
                        dt_out = datetime.strptime(f_egreso.split(".")[0], "%Y-%m-%d %H:%M:%S")
                        diff = dt_out - dt_in
                        minutos_totales = int(diff.total_seconds() // 60)
                        horas = minutos_totales // 60
                        mins = minutos_totales % 60
                        tiempo_permanencia = f"{horas}h {mins}m" if horas > 0 else f"{mins} mins"
                    except:
                        tiempo_permanencia = "Calculado"

                if f_ingreso != "---" and f_egreso == "---":
                    estado_visita = "🟡 EN OBJETIVO (PRESENTE)"
                elif f_ingreso != "---" and f_egreso != "---":
                    estado_visita = "✅ FINALIZADO / RETIRADO"
                else:
                    estado_visita = "⏳ PENDIENTE DE VISITA"

                lista_estado_objs.append({
                    "OBJETIVO": nombre_o,
                    "ESTADO": estado_visita,
                    "INGRESO": f_ingreso,
                    "EGRESO": f_egreso,
                    "PERMANENCIA": tiempo_permanencia
                })
            
            df_estado_final = pd.DataFrame(lista_estado_objs)
            st.dataframe(df_estado_final, use_container_width=True, hide_index=True)
        else:
            st.warning("⚠️ No se encontraron objetivos cargados en la base para este usuario.")

        st.markdown("---")
        
        t_vis_qr, t_ruta_gmaps, t_car_tac, t_mensajeria_sup, t_pres_sup = st.tabs([
            "Visita QR", "📲 RUTA GOOGLE MAPS", "Carga Táctica", "💬 MENSAJERÍA", "📋 NOVEDADES Y RELEVOS"
        ])

        with t_vis_qr:
            st.markdown("### 📱 CENTRO TÁCTICO & CÁMARA QR")
            if not df_objetivos_filtrados.empty:
                lista_objs = df_objetivos_filtrados['OBJETIVO'].unique()
                if "obj_qr_tactico_sel" not in st.session_state:
                    st.session_state.obj_qr_tactico_sel = lista_objs[0]

                obj_select = st.selectbox(
                    "Seleccione Objetivo:", 
                    lista_objs, 
                    index=list(lista_objs).index(st.session_state.obj_qr_tactico_sel) if st.session_state.obj_qr_tactico_sel in lista_objs else 0,
                    key="obj_qr_tactico_sel"
                )
                
                datos_sel = df_objetivos_filtrados[df_objetivos_filtrados['OBJETIVO'] == obj_select].iloc[0]
                c1, c2 = st.columns([1, 2])
                with c1:
                    qr = qrcode.QRCode(box_size=6, border=1)
                    qr.add_data(f"OBJETIVO:{obj_select}|ID:{datos_sel.get('ID', '0')}")
                    qr.make(fit=True)
                    st.image(qr.make_image(fill_color="#00E5FF", back_color="black").get_image(), width=150)
                    st.caption(f"QR: {obj_select}")

                with c2:
                    st.markdown("<br>", unsafe_allow_html=True)
                    lat = datos_sel.get('LATITUD', 0)
                    lon = datos_sel.get('LONGITUD', 0)
                    nombre_obj = obj_select
                    url_navegacion = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lon}&destination_place_name={nombre_obj}&travelmode=driving"
                    st.markdown(f'''
                        <a href="{url_navegacion}" target="_blank" 
                        style="display: inline-block; width: 100%; padding: 10px; border: 1px solid #00E5FF; 
                        color: #00E5FF; text-decoration: none; border-radius: 4px; font-family: sans-serif; 
                        font-size: 14px; text-align: center; transition: 0.3s; margin-bottom: 10px;">
                        📍 IR A {nombre_obj}
                        </a>
                    ''', unsafe_allow_html=True)

                    tipo_accion_qr = st.radio("SELECCIONE EL TIPO DE ESCANEO:", ["ENTRADA (INGRESO)", "SALIDA (EGRESO)"], horizontal=True, key="radio_accion_qr")

                    st.markdown("### 📷 CÁMARA QR ESTABLE & ANTIRREBOTE")
                    
                    modo_lente = st.selectbox("ELEGIR LENTE:", ["Cámara Trasera (Environment)", "Cámara Frontal (User)"], key="selector_lente_manual")
                    
                    if "Trasera" in modo_lente:
                        st.markdown("""
                            <script>
                                const inputs = window.parent.document.querySelectorAll('input[type="file"]');
                                inputs.forEach(input => {
                                    input.setAttribute('capture', 'environment');
                                });
                            </script>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown("""
                            <script>
                                const inputs = window.parent.document.querySelectorAll('input[type="file"]');
                                inputs.forEach(input => {
                                    input.removeAttribute('capture');
                                });
                            </script>
                        """, unsafe_allow_html=True)

                    cam_key = f"camara_qr_{tipo_accion_qr}_{obj_select}"
                    img_qr_cam = st.camera_input("Capturar Código QR", key=cam_key)

                    tiempo_actual_epoch = datetime.now().timestamp()
                    if img_qr_cam is not None and (tiempo_actual_epoch - st.session_state.get('ultimo_escaneo_tiempo', 0)) > 5:
                        st.session_state.ultimo_escaneo_tiempo = tiempo_actual_epoch
                        nombre_limpio_obj = str(obj_select).strip().upper()
                        fecha_hora_arg = obtener_hora_argentina()
                        
                        etiqueta_evento = "INGRESO QR" if "ENTRADA" in tipo_accion_qr else "EGRESO QR"
                        
                        exito_escaneo = escribir_registro_nube("REGISTRO_QR_SUPERVISORES", [
                            fecha_hora_arg, 
                            nombre_limpio_obj, 
                            etiqueta_evento, 
                            sup_activo_normalizado,
                            "PROCESADO"
                        ])
                        if exito_escaneo:
                            st.success(f"✅ ¡Registro de {etiqueta_evento} guardado con éxito para {nombre_limpio_obj}!")
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error("Error al registrar el escaneo en la base.")

        with t_ruta_gmaps:
            st.markdown("### 🗺️ NAVEGACIÓN TÁCTICA")
            opciones_r = df_objetivos_filtrados['OBJETIVO'].unique() if not df_objetivos_filtrados.empty else []
            if len(opciones_r) > 0:
                obj_r = st.selectbox("DESTINO:", opciones_r, key="sup_ruta_gmaps_target")
                datos_r = df_objetivos_filtrados[df_objetivos_filtrados['OBJETIVO'] == obj_r].iloc[0]
                lat, lon = datos_r['LATITUD'], datos_r['LONGITUD']
                dist_min, com_name, com_lat, com_lon = float('inf'), "Ninguna", 0.0, 0.0
                for _, com in df_comisarias.iterrows():
                    d = 6371 * 2 * math.asin(math.sqrt(math.sin((math.radians(com['LATITUD'])-math.radians(lat))/2)**2 + math.cos(math.radians(lat))*math.cos(math.radians(com['LATITUD']))*math.sin((math.radians(com['LONGITUD'])-math.radians(lon))/2)**2))
                    if d < dist_min: dist_min, com_name, com_lat, com_lon = d, com['COMISARIA'], com['LATITUD'], com['LONGITUD']
                st.info(f"👮 **Comisaría Encontrada:** {com_name} ({dist_min:.2f} Km)")
                st.link_button("🗺️ ABRIR ASISTENTE GPS", f"https://www.google.com/maps/dir/?api=1&origin={com_lat},{com_lon}&destination={lat},{lon}&travelmode=driving", use_container_width=True)

        with t_car_tac:
            novedad_sup = st.text_area("Novedad / Registro Operativo:")
            if st.button("CARGAR REGISTRO") and novedad_sup.strip():
                escribir_registro_nube("NOVEDADES", [obtener_hora_argentina(), st.session_state.user_sel, novedad_sup.upper()])
                st.success("✅ Cargado")

        with t_mensajeria_sup:
            renderizar_mensajeria_global("SUPERVISOR")
       
        with t_pres_sup:
            st.markdown("#### 🔄 RELEVOS DE GUARDIA")
            df_nov_sup = leer_matriz_nube("NOVEDADES_GUARDIA")
            if not df_nov_sup.empty:
                df_nov_sup.columns = [str(c).strip().upper() for c in df_nov_sup.columns]
                if 'SUPERVISOR' in df_nov_sup.columns:
                    df_nov_sup = df_nov_sup[df_nov_sup['SUPERVISOR'].str.upper() == sup_activo_normalizado]
                    df_nov_sup = df_nov_sup.drop(columns=['SUPERVISOR'])
                st.dataframe(df_nov_sup.iloc[::-1], use_container_width=True, hide_index=True)
            else:
                st.info("Sin relevos registrados.")
