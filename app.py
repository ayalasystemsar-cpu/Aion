import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from datetime import datetime
import numpy as np
from streamlit_js_eval import get_geolocation

# --- 1. ESTÉTICA TÁCTICA AION-YORAKU ---
st.set_page_config(page_title="AION-YORAKU v5.0", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .stApp { background-color: #121212; color: #E0E0E0; }
    [data-testid="stSidebar"] { background-color: #1A1A1A; border-right: 2px solid #00E5FF; }
    h1, h2, h3, .stSubheader { color: #00E5FF !important; font-family: 'Courier New', monospace; font-weight: bold; }
    div[data-testid="metric-container"] {
        background-color: #1E1E1E; border: 1px solid #333; border-left: 5px solid #00E5FF; padding: 15px; border-radius: 5px;
    }
    .stButton>button {
        background-color: #1E1E1E; color: #00E5FF; border: 1px solid #00E5FF; border-radius: 4px; transition: 0.3s; width: 100%;
    }
    .stButton>button:hover { background-color: #00E5FF; color: #121212; box-shadow: 0 0 15px #00E5FF; }
    .alerta-panico { background-color: #FF0000 !important; color: white !important; font-size: 24px; text-align: center; padding: 20px; border-radius: 10px; font-weight: bold; animation: blinker 1s linear infinite; }
    @keyframes blinker { 50% { opacity: 0; } }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZACIÓN DE BASES DE DATOS EN MEMORIA (Para despliegue inmediato) ---
if 'db_objetivos' not in st.session_state:
    st.session_state.db_objetivos = pd.DataFrame({
        'OBJETIVO': ['Mercedes 3575', 'RUTA 4 KM 3.5'],
        'SUPERVISOR': ['MAZACOTTE CLAUDIO', 'AYALA BRIAN'],
        'LATITUD': [-34.55, -34.45],
        'LONGITUD': [-58.53, -58.56]
    })
if 'db_mensajes' not in st.session_state:
    st.session_state.db_mensajes = pd.DataFrame(columns=['ID', 'FECHA', 'REMITENTE', 'DESTINATARIO', 'ASUNTO', 'MENSAJE', 'ESTADO'])
if 'alerta_activa' not in st.session_state:
    st.session_state.alerta_activa = False
if 'detalles_alerta' not in st.session_state:
    st.session_state.detalles_alerta = ""

df = st.session_state.db_objetivos
mensajes = st.session_state.db_mensajes

# --- 2. PANEL LATERAL: JERARQUÍA ---
with st.sidebar:
    st.title("AION-YORAKU")
    st.image("https://img.icons8.com/nolan/128/security-shield.png", width=100)

    rol = st.selectbox("PERFIL DE ACCESO", ["SUPERVISOR", "MONITOREO", "JEFE DE OPERACIONES", "GERENCIA"])
    
    usuario_auth = "ADMIN"
    if rol == "SUPERVISOR":
        lista_sup = ["SERANTES WALTER", "SANOJA LUIS", "DIAZ MARCELO", "MAZACOTTE CLAUDIO", "PORZIO GONZALO", "AYALA BRIAN", "CARRIZO WALTER"]
        usuario_auth = st.selectbox("IDENTIFÍQUESE", lista_sup)
    elif rol == "JEFE DE OPERACIONES":
        usuario_auth = "DARÍO CECILIA"
    elif rol == "GERENCIA":
        usuario_auth = "LUIS BONGIORNO"
    elif rol == "MONITOREO":
        usuario_auth = "CENTRAL MONITOREO"
    
    st.markdown("---")
    
    # PÁNICO BLINDADO
    if st.button("🔴 ACTIVAR PÁNICO (S.O.S)", use_container_width=True):
        st.session_state.alerta_activa = True
        st.session_state.detalles_alerta = f"ALERTA CRÍTICA INICIADA POR {usuario_auth} A LAS {datetime.now().strftime('%H:%M:%S')}"
        st.error("ALERTA ENVIADA A MONITOREO. MANTENGA LA POSICIÓN.")

# --- MÓDULO EXCLUSIVO BRIAN AYALA ---
if usuario_auth == "AYALA BRIAN" and rol == "SUPERVISOR":
    with st.expander("🐺 MÓDULO TÁCTICO B.A. (ACCESO RESTRINGIDO)", expanded=True):
        st.markdown("### ⚙️ Herramientas de Terreno y Proyección")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("*Inventario de Despliegue*")
            st.checkbox("Hoja Principal (Yarará / ESEE)")
            st.checkbox("Kit de Primeros Auxilios")
            st.checkbox("Linterna y baterías extra")
        with c2:
            st.markdown("*Radar de Objetivos a Largo Plazo*")
            st.metric("Destino Operativo", "Los Zapallos, Sta. Fe")
            st.metric("Estatus Académico", "Data Analytics - Activo")
        
        if st.button("🎵 Sintonizar Frecuencia Base"):
            st.success("📡 Interceptando señal de Santa Fe... Frecuencia melódica asegurada (L.M. / U.L.). Terreno despejado.")

st.markdown("---")

# --- FUNCIONES AUXILIARES DE MENSAJERÍA ---
def enviar_mensaje(remitente, destinatario, asunto, texto):
    nuevo_msg = pd.DataFrame([{
        'ID': len(st.session_state.db_mensajes) + 1,
        'FECHA': datetime.now().strftime("%Y-%m-%d %H:%M"),
        'REMITENTE': remitente,
        'DESTINATARIO': destinatario,
        'ASUNTO': asunto,
        'MENSAJE': texto,
        'ESTADO': 'NO LEÍDO'
    }])
    st.session_state.db_mensajes = pd.concat([st.session_state.db_mensajes, nuevo_msg], ignore_index=True)

def mostrar_buzon(usuario):
    st.subheader("📥 Bandeja de Entrada")
    mis_mensajes = st.session_state.db_mensajes[st.session_state.db_mensajes['DESTINATARIO'].isin([usuario, 'TODOS'])]
    
    if mis_mensajes.empty:
        st.info("No hay comunicaciones entrantes.")
    else:
        for idx, row in mis_mensajes.iterrows():
            with st.expander(f"{'🔴' if row['ESTADO'] == 'NO LEÍDO' else '🟢'} {row['FECHA']} - De: {row['REMITENTE']} | Asunto: {row['ASUNTO']}"):
                st.write(row['MENSAJE'])
                if row['ESTADO'] == 'NO LEÍDO':
                    if st.button(f"Acusar Recibo (ID: {row['ID']})", key=f"btn_{row['ID']}"):
                        st.session_state.db_mensajes.at[idx, 'ESTADO'] = f"LEÍDO POR {usuario}"
                        st.success("Notificación de lectura enviada.")
                        st.rerun()

# --- 3. PERFIL SUPERVISOR ---
if rol == "SUPERVISOR":
    st.header(f"Estación de Control: {usuario_auth}")
    mostrar_buzon(usuario_auth)
    
    apellido = usuario_auth.split()[-1].upper()
    df_zona = df[df['SUPERVISOR'].str.upper().str.contains(apellido, na=False)]

    if not df_zona.empty:
        st.subheader("📍 Navegación y Geovalla")
        col_map, col_gps = st.columns([2, 1])
        with col_map:
            m = folium.Map(location=[df_zona['LATITUD'].mean(), df_zona['LONGITUD'].mean()], zoom_start=12, tiles="CartoDB dark_matter")
            for _, row in df_zona.iterrows():
                folium.Marker([row['LATITUD'], row['LONGITUD']], popup=row['OBJETIVO']).add_to(m)
            st_folium(m, width="100%", height=300, key="map_sup")
        
        with col_gps:
            destino = st.selectbox("Seleccionar Objetivo:", df_zona['OBJETIVO'].unique())
            target = df_zona[df_zona['OBJETIVO'] == destino].iloc[0]
            maps_url = f"https://www.google.com/maps/dir/?api=1&destination={target['LATITUD']},{target['LONGITUD']}"
            st.markdown(f"""<a href="{maps_url}" target="_blank"><div style="background-color:#00E5FF; color:black; padding:10px; text-align:center; border-radius:5px; font-weight:bold;">🗺️ INICIAR RUTA GPS</div></a>""", unsafe_allow_html=True)

        st.markdown("### 📋 Registro de Ronda")
        with st.form("form_visita"):
            novedad = st.text_area("Novedades del Servicio")
            if st.form_submit_button("IMPACTAR REPORTE"):
                st.success("✅ Reporte enviado al servidor maestro.")

    st.subheader("📤 Enviar Reporte a Mando")
    with st.form("msg_sup"):
        dest = st.selectbox("Destinatario", ["DARÍO CECILIA", "LUIS BONGIORNO"])
        asunto_sup = st.text_input("Asunto")
        msg_sup = st.text_area("Mensaje")
        if st.form_submit_button("Transmitir"):
            enviar_mensaje(usuario_auth, dest, asunto_sup, msg_sup)
            st.success("Transmisión exitosa.")

# --- 4. PERFIL MONITOREO ---
elif rol == "MONITOREO":
    st.header("🖥️ Central de Monitoreo Global")
    
    if st.session_state.alerta_activa:
        st.markdown(f'<div class="alerta-panico">{st.session_state.detalles_alerta}</div>', unsafe_allow_html=True)
        with st.form("cierre_panico"):
            st.write("Debe registrar la resolución para levantar el bloqueo.")
            resolucion = st.text_area("Procedimiento ejecutado")
            if st.form_submit_button("CERRAR INCIDENTE CRÍTICO"):
                st.session_state.alerta_activa = False
                st.success("Incidente neutralizado.")
                st.rerun()
    else:
        st.success("🟢 Sistema Estable. Sin alertas en curso.")
        m_mon = folium.Map(location=[df['LATITUD'].mean(), df['LONGITUD'].mean()], zoom_start=11, tiles="CartoDB dark_matter")
        for _, row in df.iterrows():
            folium.Marker([row['LATITUD'], row['LONGITUD']], popup=row['OBJETIVO']).add_to(m_mon)
        st_folium(m_mon, width="100%", height=500, key="map_mon")

# --- 5. PERFIL JEFE DE OPERACIONES ---
elif rol == "JEFE DE OPERACIONES":
    st.header(f"🗃️ Comando Operativo: {usuario_auth}")
    t1, t2 = st.tabs(["COMUNICACIONES", "ESTADO DE RED"])
    
    with t1:
        mostrar_buzon(usuario_auth)
        st.markdown("---")
        st.subheader("📤 Emitir Directiva")
        with st.form("msg_jefe"):
            dest_jefe = st.selectbox("Destinatario", ["TODOS", "LUIS BONGIORNO"] + df['SUPERVISOR'].unique().tolist())
            asunto_jefe = st.text_input("Asunto")
            msg_jefe = st.text_area("Directiva")
            if st.form_submit_button("Transmitir"):
                enviar_mensaje(usuario_auth, dest_jefe, asunto_jefe, msg_jefe)
                st.success("Directiva en red.")
                
    with t2:
        m_jefe = folium.Map(location=[df['LATITUD'].mean(), df['LONGITUD'].mean()], zoom_start=11, tiles="CartoDB dark_matter")
        for _, row in df.iterrows():
            folium.Marker([row['LATITUD'], row['LONGITUD']], popup=f"{row['OBJETIVO']} ({row['SUPERVISOR']})").add_to(m_jefe)
        st_folium(m_jefe, width="100%", height=400, key="map_jefe")

# --- 6. PERFIL GERENCIA (CONTROL TOTAL) ---
elif rol == "GERENCIA":
    st.header(f"📊 Tablero Ejecutivo: {usuario_auth}")
    t1, t2, t3 = st.tabs(["COMUNICACIONES", "GESTIÓN DE ACTIVOS", "AUDITORÍA"])
    
    with t1:
        mostrar_buzon(usuario_auth)
        st.markdown("---")
        st.subheader("📤 Circular Ejecutiva")
        with st.form("msg_gerencia"):
            dest_ger = st.selectbox("Destinatario", ["TODOS", "DARÍO CECILIA"] + df['SUPERVISOR'].unique().tolist())
            asunto_ger = st.text_input("Asunto")
            msg_ger = st.text_area("Contenido")
            if st.form_submit_button("Difundir"):
                enviar_mensaje(usuario_auth, dest_ger, asunto_ger, msg_ger)
                st.success("Circular distribuida.")
                
    with t2:
        st.subheader("➕ Alta de Nuevo Servicio")
        with st.form("alta_servicio"):
            n_obj = st.text_input("Nombre del Objetivo")
            n_sup = st.selectbox("Supervisor Asignado", ["SERANTES WALTER", "SANOJA LUIS", "DIAZ MARCELO", "MAZACOTTE CLAUDIO", "PORZIO GONZALO", "AYALA BRIAN", "CARRIZO WALTER"])
            n_lat = st.number_input("Latitud", format="%.6f")
            n_lon = st.number_input("Longitud", format="%.6f")
            if st.form_submit_button("Registrar en Base de Datos"):
                nuevo_obj = pd.DataFrame({'OBJETIVO': [n_obj], 'SUPERVISOR': [n_sup], 'LATITUD': [n_lat], 'LONGITUD': [n_lon]})
                st.session_state.db_objetivos = pd.concat([st.session_state.db_objetivos, nuevo_obj], ignore_index=True)
                st.success("Objetivo impactado en la red táctica.")
                st.rerun()

    with t3:
        st.subheader("Base de Datos Activa")
        st.dataframe(st.session_state.db_objetivos, use_container_width=True)
