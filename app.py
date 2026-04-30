# --- 1. CONFIGURACIÓN E IDENTIDAD VISUAL CORPORATIVA (VERSIÓN ALFA) ---
import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
from datetime import datetime
import pytz
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from supabase import create_client, Client

st.set_page_config(
    page_title="AION-YAROKU | CORE",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_resource
def init_connection():
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except Exception:
        return None

supabase = init_connection()

def aplicar_identidad_alfa():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@300;500;700&display=swap');
        
        .stApp { 
            background: radial-gradient(circle at top, #0A0F1E 0%, #030305 100%);
            color: #E0E0E0;
            font-family: 'Rajdhani', sans-serif;
        }

        /* SIDEBAR SIN MARCOS */
        [data-testid="stSidebar"] { 
            background-color: #050507;
            border-right: 1px solid rgba(0, 229, 255, 0.3);
        }

        [data-testid="stSidebar"]::before { 
            content: "";
            display: block;
            width: 140px;
            height: 140px;
            margin: 30px auto 10px auto;
            background-image: url("https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg");
            background-size: contain;
            background-repeat: no-repeat;
            background-position: center;
        }

        /* ELIMINACIÓN TOTAL DE MARCOS AUTOMÁTICOS */
        div[data-testid="stVerticalBlock"] > div:has(img.escudo-alfa) {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
        }

        .escudo-alfa-container {
            display: flex;
            justify-content: center;
            padding: 20px 0;
            background-color: transparent !important;
        }

        .escudo-alfa {
            width: 450px; 
            border: none !important;
            box-shadow: none !important;
            background: transparent !important;
        }

        h1, h2, h3 { 
            font-family: 'Orbitron', sans-serif;
            color: #00E5FF !important;
        }
        </style>
        """, unsafe_allow_html=True
    )

aplicar_identidad_alfa()

# ✅ RENDERIZADO DIRECTO
st.markdown(
    '<div class="escudo-alfa-container"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" class="escudo-alfa"></div>', 
    unsafe_allow_html=True
)

def obtener_hora_argentina():
    tz = pytz.timezone("America/Argentina/Buenos_Aires")
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

# --- 2. CONTROL DE ACCESO Y MEMORIA DE SESIÓN ---
# (AQUÍ CONTINÚA TU CÓDIGO DE LÓGICA DE ROLES)
# --- 2. CONTROL DE ACCESO Y MEMORIA DE SESIÓN ---
# (El resto del código se mantiene igual a partir de aquí)
if 'rol_sel' not in st.session_state: st.session_state.rol_sel = "SUPERVISOR"
if 'user_sel' not in st.session_state: st.session_state.user_sel = "BRIAN AYALA"
if 'qr_mode' not in st.session_state: st.session_state.qr_mode = "Seleccionar..."

# 🎚️ SELECTORES DE IDENTIDAD TÁCTICA (BARRA LATERAL)
st.sidebar.markdown("### 🎚️ CONTROL DE ACCESO")
perfiles_disponibles = ["SUPERVISOR", "MONITOREO", "JEFE DE OPERACIONES", "GERENCIA", "ADMINISTRADOR"]
st.session_state.rol_sel = st.sidebar.selectbox("Perfil Activo:", perfiles_disponibles, index=perfiles_disponibles.index(st.session_state.rol_sel) if st.session_state.rol_sel in perfiles_disponibles else 0)

# Corrección 1: Lista de operadores para que el sistema sepa quién escribe y a quién filtrar
lista_operadores = ["BRIAN AYALA", "DARÍO CECILIA", "LUIS BONGIORNO", "SUPERVISOR NOCTURNO", "SUPERVISOR 1", "SUPERVISOR 2"]
st.session_state.user_sel = st.sidebar.selectbox("Operador / Usuario:", lista_operadores, index=lista_operadores.index(st.session_state.user_sel) if st.session_state.user_sel in lista_operadores else 0)

# --- 3. CONEXIÓN A MATRIZ NUBE ---
ID_MAESTRO_DB = "1Md0VkOnwUJWldq0S1fB9UrmOKv4MG__JVG3tQsda0Uw"

def conectar_google():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ Error Crítico de Conexión: {e}")
        return None

def actualizar_celda(pestana, fila, columna, valor):
    try:
        gc = conectar_google()
        if gc:
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
            hoja.update_acell(f"{columna}{fila}", valor)
            return True
    except: return False

def escribir_registro_pro(pestana, datos_fila):
    try:
        gc = conectar_google()
        if gc:
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
            hoja.append_row(datos_fila)
            return True
    except: return False

@st.cache_data(ttl=15)
def leer_matriz_nube(pestana):
    gc = conectar_google()
    if gc:
        try:
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
            return pd.DataFrame(hoja.get_all_records())
        except: return pd.DataFrame()
    return pd.DataFrame()

@st.cache_data(ttl=60)
def cargar_objetivos():
    df = leer_matriz_nube("OBJETIVOS")
    if not df.empty:
        df.columns = df.columns.str.strip().str.upper()
        df['LATITUD'] = pd.to_numeric(df['LATITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        df['LONGITUD'] = pd.to_numeric(df['LONGITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        return df.dropna(subset=['LATITUD', 'LONGITUD'])
    return pd.DataFrame()

df_objetivos = cargar_objetivos()

# --- 4. BANDEJA DE INTELIGENCIA Y MENSAJERÍA ---
def mostrar_buzon(usuario_actual):
    st.markdown("### 📥 BANDEJA DE INTELIGENCIA")
    df_msg = leer_matriz_nube("MENSAJERIA")
    
    if not df_msg.empty:
        mis_mensajes = df_msg[
            (df_msg['DESTINATARIO'].astype(str).str.contains(usuario_actual, na=False)) | 
            (df_msg['DESTINATARIO'].astype(str).str.contains("TODOS", na=False)) |
            (df_msg['DESTINATARIO'].astype(str).str.contains(st.session_state.rol_sel, na=False))
        ]
        
        if not mis_mensajes.empty:
            for idx, row in mis_mensajes.iloc[::-1].iterrows():
                color_borde = "#00FF00" if row['GRAVEDAD'] == "VERDE" else ("#FFCC00" if row['GRAVEDAD'] == "AMARILLO" else "#FF0000")
                with st.container():
                    st.markdown(f"""
                    <div style="border-left: 5px solid {color_borde}; background: rgba(255,255,255,0.05); padding: 12px; border-radius: 5px; margin-bottom: 8px;">
                        <small style="color: #00E5FF;">{row['FECHA']} | De: {row['REMITENTE']}</small><br>
                        <b style="font-size: 15px;">{row['ASUNTO']}</b><br>
                        <p style="font-size: 14px; margin-top: 4px;">{row['MENSAJE']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    if row['ESTADO'] != "LEÍDO":
                        if st.button(f"Confirmar Lectura", key=f"read_{idx}"):
                            actualizar_celda("MENSAJERIA", idx + 2, "F", "LEÍDO")
                            st.cache_data.clear()
                            st.rerun()
        else:
            st.info("Sin mensajes.")
    else:
        st.info("Bandeja vacía.")

def emitir_mensaje_pro(remitente):
    with st.expander("📤 REDACTAR COMUNICACIÓN"):
        with st.form("envio_tactico"):
            dest = st.selectbox("Para:", ["TODOS", "DARÍO CECILIA", "LUIS BONGIORNO", "MONITOREO"] + lista_operadores)
            asu = st.text_input("Asunto")
            men = st.text_area("Mensaje")
            grav = st.selectbox("Prioridad:", ["VERDE", "AMARILLO", "ROJO"])
            if st.form_submit_button("TRANSMITIR"):
                if asu and men:
                    datos = [obtener_hora_argentina(), remitente, dest, asu, men, "ENVIADO", grav]
                    if escribir_registro_pro("MENSAJERIA", datos):
                        st.success(f"Transmitido a {dest}")
                        st.rerun()

# --- 5. MÓDULO SUPERVISOR: ESTACIÓN TÁCTICA ---
if st.session_state.rol_sel == "SUPERVISOR":
    st.markdown(f"### ⚡ ESTACIÓN TÁCTICA: {st.session_state.user_sel}")
    
    col_panico, col_refresco = st.columns(2)
    with col_panico:
        if st.button("🚨 ACTIVAR PÁNICO / SOS", use_container_width=True):
            datos_sos = [obtener_hora_argentina(), st.session_state.user_sel, "PÁNICO", "0.0", "0.0", "CRÍTICO PENDIENTE"]
            escribir_registro_pro("ALERTAS", datos_sos)
            st.error("❗ ALERTA S.O.S ENVIADA")
    with col_refresco:
        if st.button("🔄 REFRESCAR SISTEMA", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    with st.expander("🚚 CONTROL DE UNIDAD MÓVIL", expanded=False):
        c_movf, c_km1, c_km2, c_comb = st.columns(4)
        movil_flota = c_movf.selectbox("Móvil", ["S-001", "S-002", "S-003", "S-004", "S-005", "S-006", "S-007"])
        km_in = c_km1.number_input("Km Inicial", min_value=0)
        km_out = c_km2.number_input("Km Final", min_value=0)
        comb_cargado = c_comb.number_input("Combustible (Lts)", min_value=0.0)
        if st.button("📌 SELLAR ODOMETRÍA Y LOGÍSTICA"):
            if km_out >= km_in:
                datos_f = [obtener_hora_argentina()[:10], st.session_state.user_sel, movil_flota, km_in, km_out, comb_cargado]
                escribir_registro_pro("CONTROL_FLOTA", datos_f)
                st.success("Logística sellada.")

    t1, t2, t3 = st.tabs(["📍 RADAR & QR", "📤 CARGA TÁCTICA", "💬 COMUNICACIÓN"])
    
    # Corrección 2: Lógica de filtrado de zona a prueba de fallos
    apellido = st.session_state.user_sel.split()[-1].upper()
    df_zona = df_objetivos[df_objetivos['SUPERVISOR'].str.upper().str.contains(apellido, na=False)] if not df_objetivos.empty else pd.DataFrame()
    
    # Fallback: Si el filtro de zona queda vacío, desplegar la lista completa para no perder operatividad
    if df_zona.empty and not df_objetivos.empty:
        df_zona = df_objetivos

    with t1:
        c_map, c_ctrl = st.columns([2, 1])
        with c_map:
            if not df_zona.empty:
                m_s = folium.Map(location=[df_zona['LATITUD'].mean(), df_zona['LONGITUD'].mean()], zoom_start=12, tiles="CartoDB dark_matter")
                for _, row in df_zona.iterrows():
                    folium.Marker([row['LATITUD'], row['LONGITUD']], popup=row['OBJETIVO'], icon=folium.Icon(color="blue", icon="shield", prefix="fa")).add_to(m_s)
                st_folium(m_s, width="100%", height=400)
        
        with c_ctrl:
            if not df_zona.empty:
                dest = st.selectbox("SERVICIO ACTUAL:", df_zona['OBJETIVO'].unique())
                st.markdown("---")
                st.session_state.qr_mode = st.radio("ACCIÓN:", ["Seleccionar...", "🟢 INGRESO", "🔴 SALIDA"], horizontal=True)
                
                if st.session_state.qr_mode != "Seleccionar...":
                    if st.checkbox("🔓 ACTIVAR ESCÁNER TÁCTICO"):
                        f_cam = st.camera_input("Enfoque QR")
                        if f_cam:
                            tipo = "ENTRADA" if "INGRESO" in st.session_state.qr_mode else "SALIDA"
                            escribir_registro_pro("LOG_PRESENCIA", [obtener_hora_argentina(), st.session_state.user_sel, dest, tipo, "VALIDADO", "0 min"])
                            st.success(f"OPERACIÓN {tipo} SELLADA.")
                            st.rerun()

    with t2:
        st.subheader("📝 REPORTE ÁGIL DE NOVEDADES")
        with st.form("acta_alfa"):
            # Corrección 3: El selectbox ahora se alimenta correctamente de df_zona
            f_dest = st.selectbox("Objetivo:", df_zona['OBJETIVO'].unique()) if not df_zona.empty else "N/A"
            f_vig = st.text_input("Personal en Puesto")
            f_nov = st.text_area("Informe de Novedad")
            gravedad = st.select_slider("GRAVEDAD:", options=["VERDE", "AMARILLO", "ROJO"])
            
            if st.form_submit_button("🚀 TRANSMITIR ACTA"):
                datos_acta = [obtener_hora_argentina(), st.session_state.user_sel, movil_flota, "", km_in, "", f_vig, f_dest, f_nov, gravedad]
                escribir_registro_pro("ACTAS_FLOTAS", datos_acta)
                st.success("Acta derivada.")

    with t3:
        mostrar_buzon(st.session_state.user_sel)
        emitir_mensaje_pro(st.session_state.user_sel)

# --- 6. MÓDULO MONITOREO ---
elif st.session_state.rol_sel == "MONITOREO":
    st.header("🛰️ CENTRAL DE INTELIGENCIA OPERATIVA")
    
    m1, m2, m3 = st.columns(3)
    df_alertas = leer_matriz_nube("ALERTAS")
    sos_activos = len(df_alertas[df_alertas['ESTADO'].astype(str).str.upper() == 'PENDIENTE']) if not df_alertas.empty else 0
    m1.metric("🚨 S.O.S ACTIVOS", sos_activos)
    
    df_msg = leer_matriz_nube("MENSAJERIA")
    amarillas = len(df_msg[(df_msg['GRAVEDAD'] == 'AMARILLO') & (df_msg['ESTADO'] != 'LEÍDO')]) if not df_msg.empty else 0
    m2.metric("⚠️ EN PROCESO", amarillas)
    
    t_radar, t_libro, t_chat = st.tabs(["🚨 RADAR S.O.S", "📖 LIBRO DE BASE", "💬 COMUNICACIÓN"])
    
    with t_radar:
        if not df_objetivos.empty:
            m_mon = folium.Map(location=[df_objetivos['LATITUD'].mean(), df_objetivos['LONGITUD'].mean()], zoom_start=11, tiles="CartoDB dark_matter")
            for _, r in df_objetivos.iterrows():
                folium.Marker([r['LATITUD'], r['LONGITUD']], tooltip=r['OBJETIVO']).add_to(m_mon)
            st_folium(m_mon, width="100%", height=400)

        if sos_activos > 0:
            datos_sos = df_alertas[df_alertas['ESTADO'].astype(str).str.upper() == 'PENDIENTE'].iloc[-1]
            op_en_riesgo = datos_sos['USUARIO']
            st.error(f"🚨 ALERTA CRÍTICA: {op_en_riesgo}")
            with st.form("cierre_crisis"):
                res_acta = st.text_area("Informe de Neutralización")
                if st.form_submit_button("✅ CERRAR ALERTA"):
                    fila_real = df_alertas[df_alertas['ESTADO'].astype(str).str.upper() == 'PENDIENTE'].index[-1] + 2
                    actualizar_celda("ALERTAS", fila_real, "D", "RESUELTO")
                    st.success("Resuelto"); st.cache_data.clear(); st.rerun()

    with t_libro:
        with st.form("acta_base"):
            # Corrección 4: Campo habilitado para Operador de Turno
            op_nombre = st.text_input("Operador de Turno:", value=st.session_state.user_sel)
            nov = st.text_area("Novedades de Guardia")
            if st.form_submit_button("SELLAR"):
                escribir_registro_pro("MENSAJERIA", [obtener_hora_argentina(), op_nombre, "DARÍO CECILIA", "LIBRO BASE", nov, "ENVIADO", "VERDE"])
                st.success("Sellado."); st.rerun()

    with t_chat:
        mostrar_buzon(st.session_state.user_sel)
        emitir_mensaje_pro(st.session_state.user_sel)

# --- 7. MÓDULO EJECUTIVO: COMANDO ESTRATÉGICO ---
elif st.session_state.rol_sel in ["JEFE DE OPERACIONES", "GERENCIA"]:
    # Corrección 5: Cabecera correcta según el usuario seleccionado
    st.header(f"👔 COMANDO ESTRATÉGICO: {st.session_state.user_sel}")
    
    st.markdown("""
    <style>
    .card-alfa { padding: 15px; margin-bottom: 10px; border-radius: 5px; border-left: 5px solid; background: rgba(255,255,255,0.02); }
    .roja { border-color: #FF4B4B; } .amarilla { border-color: #FFCC00; } .verde { border-color: #00FF00; }
    </style>
    """, unsafe_allow_html=True)

    t_crisis, t_gestion, t_auditoria = st.tabs(["🚨 CENTRO DE CRISIS", "📤 EJECUCIÓN", "📊 AUDITORÍA"])
    
    with t_crisis:
        df_a = leer_matriz_nube("ALERTAS")
        if not df_a.empty:
            resueltas = df_a[df_a['ESTADO'] == 'RESUELTO'].iloc[::-1]
            for _, r in resueltas.head(10).iterrows():
                st.markdown(f'<div class="card-alfa verde"><b>{r["USUARIO"]}</b><br><small>{r["RESOLUCION"]}</small></div>', unsafe_allow_html=True)

    with t_gestion:
        with st.form("directiva_alta"):
            st.write("📩 PETICIÓN DE ALTA/BAJA")
            tipo_p = st.selectbox("Acción:", ["ALTA", "BAJA"])
            cat_p = st.selectbox("Categoría:", ["OBJETIVO", "SUPERVISOR"])
            det_p = st.text_input("Nombre / Detalle")
            if st.form_submit_button("ELEVAR PETICIÓN"):
                escribir_registro_pro("PETICIONES", [obtener_hora_argentina(), st.session_state.user_sel, tipo_p, cat_p, det_p, "PENDIENTE"])
                st.success("Enviado.")

# --- 8. ADMINISTRADOR: NÚCLEO MAESTRO ---
elif st.session_state.rol_sel == "ADMINISTRADOR":
    st.header("⚙️ NÚCLEO MAESTRO: B. AYALA")
    
    # Corrección 6: Control de infraestructura reubicado al lugar seguro
    with st.expander("🔐 CREDENCIALES DE INFRAESTRUCTURA"):
        u_ingreso = st.text_input("ADMIN_USER", key="input_admin_u").lower()
        p_ingreso = st.text_input("ADMIN_PASS", type="password", key="input_admin_p")
        if u_ingreso == "admin" and p_ingreso == "aion2026":
            st.subheader("🏗️ GESTIÓN DE ESTRUCTURA")
            col_a, col_b = st.columns(2)
            with col_a:
                tipo = st.radio("Categoría:", ["SUPERVISOR", "SERVICIO"], horizontal=True)
                nuevo_nombre = st.text_input(f"Nombre del {tipo}:").upper()
                if st.button(f"PROCESAR ALTA"):
                    if nuevo_nombre:
                        escribir_registro_pro("ESTRUCTURA", [obtener_hora_argentina(), tipo, nuevo_nombre, "ACTIVO", st.session_state.user_sel])
                        st.success("Alta Exitosa")

    st.subheader("⚖️ BUZÓN DE PETICIONES PENDIENTES")
    df_pet = leer_matriz_nube("PETICIONES")
    if not df_pet.empty:
        pend = df_pet[df_pet['ESTADO'] == 'PENDIENTE']
        for idx, r in pend.iterrows():
            with st.expander(f"Solicitud: {r['ACCION']} de {r['DETALLE']}"):
                c1, c2 = st.columns(2)
                if c1.button("✅ AUTORIZAR", key=f"ok_{idx}"):
                    actualizar_celda("PETICIONES", idx+2, "E", "EJECUTADO")
                    st.rerun()
                if c2.button("❌ RECHAZAR", key=f"no_{idx}"):
                    actualizar_celda("PETICIONES", idx+2, "E", "RECHAZADO")
                    st.rerun()
