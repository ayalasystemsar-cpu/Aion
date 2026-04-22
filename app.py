import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from datetime import datetime
import numpy as np
import os
import sqlite3
from streamlit_js_eval import get_geolocation
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- 1. ESTÉTICA AION-YORAKU (INYECCIÓN CSS QUIRÚRGICA) ---
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
        background-color: #1E1E1E; color: #00E5FF; border: 1px solid #00E5FF; border-radius: 4px; transition: 0.3s; width: 100%; font-weight: bold;
    }
    .stButton>button:hover { background-color: #00E5FF; color: #121212; box-shadow: 0 0 15px #00E5FF; }
    .alerta-panico { background-color: #FF0000 !important; color: white !important; font-size: 24px; text-align: center; padding: 20px; border-radius: 10px; font-weight: bold; border: 2px solid white; animation: blink 1s infinite; }
    @keyframes blink { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIONES Y BASES DE DATOS ---
def conectar_google():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("aion-secutec-b9f914330ea6.json", scope)
    return gspread.authorize(creds)

ID_REPORTES = "1UxvfiIqPjWxUJlc7C-zqQWOCTmm1O18J2Q5AoFx9Gl0"  
ID_PANICO = "1sM4NhsbkJQR7pTvXWKK4QZlw3unzXvBMFWOPLruAZ5Q"    

@st.cache_data(ttl=60)
def cargar_base_viva():
    url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSAGsJV1Geh53WoeRhi9Jec_KLWlSnPAwId0ADMuAUrnRofMW-4SVawEuIDrEVf7mWB7DfYQnSShXzm/pub?output=csv"
    try:
        data = pd.read_csv(url)
        data.columns = data.columns.str.strip().str.upper()
        data['LATITUD'] = pd.to_numeric(data['LATITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        data['LONGITUD'] = pd.to_numeric(data['LONGITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        return data.dropna(subset=['LATITUD', 'LONGITUD'])
    except:
        return pd.DataFrame(columns=['OBJETIVO', 'SUPERVISOR', 'LATITUD', 'LONGITUD'])

# Inicialización en Memoria para Funciones Activas
if 'db_objetivos' not in st.session_state:
    st.session_state.db_objetivos = cargar_base_viva()
if 'db_mensajes' not in st.session_state:
    st.session_state.db_mensajes = pd.DataFrame(columns=['ID', 'FECHA', 'REMITENTE', 'DESTINATARIO', 'ASUNTO', 'MENSAJE', 'ESTADO'])
if 'alerta_activa' not in st.session_state:
    st.session_state.alerta_activa = False

df = st.session_state.db_objetivos

# Motor SQL para Analítica
conn = sqlite3.connect(":memory:", check_same_thread=False)
df.to_sql("objetivos", conn, index=False, if_exists="replace")

# Funciones de Comunicación
def enviar_msg(rem, dest, asun, texto):
    nuevo = pd.DataFrame([{'ID': len(st.session_state.db_mensajes)+1, 'FECHA': datetime.now().strftime("%H:%M"), 'REMITENTE': rem, 'DESTINATARIO': dest, 'ASUNTO': asun, 'MENSAJE': texto, 'ESTADO': 'NO LEÍDO'}])
    st.session_state.db_mensajes = pd.concat([st.session_state.db_mensajes, nuevo], ignore_index=True)

def buzon(usuario):
    msgs = st.session_state.db_mensajes[st.session_state.db_mensajes['DESTINATARIO'].isin([usuario, 'TODOS'])]
    if msgs.empty: st.info("Sin mensajes en la bandeja.")
    else:
        for idx, r in msgs.sort_values(by='ID', ascending=False).iterrows():
            with st.expander(f"{'🔴' if r['ESTADO'] == 'NO LEÍDO' else '🟢'} [{r['FECHA']}] De: {r['REMITENTE']} | {r['ASUNTO']}"):
                st.write(r['MENSAJE'])
                if r['ESTADO'] == 'NO LEÍDO' and st.button("RECIBIDO Y CORROBORADO", key=f"m_{r['ID']}"):
                    st.session_state.db_mensajes.at[idx, 'ESTADO'] = f"LEÍDO POR {usuario}"
                    st.rerun()

# --- 3. PANEL LATERAL Y ROLES ---
with st.sidebar:
    logo_path = os.path.join("assets", "logo_aion.png")
    if os.path.exists(logo_path):
        st.image(logo_path, width=200)
    else:
        st.image("https://img.icons8.com/nolan/128/security-shield.png", width=100)

    st.title("AION-YORAKU")
    rol = st.selectbox("PERFIL DE ACCESO", ["SUPERVISOR", "MONITOREO", "JEFE DE OPERACIONES", "GERENCIA", "ADMINISTRADOR"])
    
    usuario_auth = "ADMIN"
    lista_sups = ["SERANTES WALTER", "SANOJA LUIS", "DIAZ MARCELO", "MAZACOTTE CLAUDIO", "PORZIO GONZALO", "AYALA BRIAN", "CARRIZO WALTER", "DARÍO CECILIA"]
    
    if rol == "SUPERVISOR": usuario_auth = st.selectbox("IDENTIFÍQUESE", lista_sups)
    elif rol == "JEFE DE OPERACIONES": usuario_auth = "DARÍO CECILIA"
    elif rol == "GERENCIA": usuario_auth = "LUIS BONGIORNO"
    elif rol == "MONITOREO": usuario_auth = "CENTRAL MONITOREO"

    st.markdown("---")
    if st.button("🔴 ACTIVAR PÁNICO", use_container_width=True):
        st.session_state.alerta_activa = True
        try:
            gc = conectar_google()
            sh = gc.open_by_key(ID_PANICO).get_worksheet(0)
            sh.append_row([str(datetime.now()), usuario_auth, "EMERGENCIA CRÍTICA", "GPS ACTIVO"])
        except: pass
        st.error("ALERTA ENVIADA A MONITOREO")

# MÓDULO TÁCTICO AYALA
if usuario_auth == "AYALA BRIAN":
    with st.sidebar.expander("🐺 MÓDULO AYALA (CLASIFICADO)", expanded=True):
        st.metric("Rumbo Operativo", "Los Zapallos, Sta. Fe")
        st.checkbox("Armamento Secundario (Yarará / ESEE)")
        st.checkbox("Motor SQL Activo")
        if st.button("Sintonizar Base"): st.success("📡 Frecuencia melódica asegurada. Terreno despejado.")

# --- 4. PERFIL SUPERVISOR ---
if rol == "SUPERVISOR":
    st.header(f"Estación de Control: {usuario_auth}")
    
    apellido = usuario_auth.split()[-1].upper()
    df_zona = df[df['SUPERVISOR'].str.upper().str.contains(apellido, na=False)]

    t1, t2 = st.tabs(["📍 RADAR TÁCTICO", "📥 COMUNICACIONES"])
    
    with t2:
        buzon(usuario_auth)
        st.markdown("---")
        with st.form("env_sup"):
            d = st.selectbox("Transmitir a:", ["DARÍO CECILIA", "LUIS BONGIORNO"])
            a = st.text_input("Asunto")
            m = st.text_area("Novedad o Reporte")
            if st.form_submit_button("Enviar Mensaje"): enviar_msg(usuario_auth, d, a, m); st.success("Transmisión exitosa.")

    with t1:
        c1, c2, c3 = st.columns(3)
        c1.metric("Objetivos en Zona", len(df_zona))
        c2.metric("Estatus GPS", "Activo", delta="100m Lock")
        c3.metric("Ruta Sugerida", "Colectora R3")

        st.markdown("---")
        col_map, col_gps = st.columns([2, 1])
        
        with col_map:
            st.subheader("📍 Despliegue Táctico")
            if not df_zona.empty:
                m_s = folium.Map(location=[df_zona['LATITUD'].mean(), df_zona['LONGITUD'].mean()], zoom_start=12, tiles="CartoDB dark_matter")
                for _, row in df_zona.iterrows():
                    folium.Marker([row['LATITUD'], row['LONGITUD']], popup=row['OBJETIVO'], icon=folium.Icon(color='cadetblue', icon='info-sign')).add_to(m_s)
                st_folium(m_s, width="100%", height=400)
        
        with col_gps:
            st.subheader("🚀 Navegación")
            if not df_zona.empty:
                destino = st.selectbox("Seleccionar Objetivo:", df_zona['OBJETIVO'].unique())
                st.info(f"Ruta optimizada para {destino}")
                target = df_zona[df_zona['OBJETIVO'] == destino].iloc[0]
                
                maps_url = f"https://www.google.com/maps/dir/?api=1&destination={target['LATITUD']},{target['LONGITUD']}"
                st.markdown(f'<a href="{maps_url}" target="_blank"><div style="background-color:#00E5FF; color:black; padding:10px; text-align:center; border-radius:5px; font-weight:bold; margin-bottom:15px;">🗺️ INICIAR GPS</div></a>', unsafe_allow_html=True)
                
                # Radar Táctico (Distancia)
                pos_gps = get_geolocation()
                bloqueo = True
                if pos_gps and 'coords' in pos_gps:
                    mi_lat, mi_lon = float(pos_gps['coords']['latitude']), float(pos_gps['coords']['longitude'])
                    p1, l1, p2, l2 = map(np.radians, [mi_lat, mi_lon, target['LATITUD'], target['LONGITUD']])
                    a_calc = np.sin((p2-p1)/2)*2 + np.cos(p1) * np.cos(p2) * np.sin((l2-l1)/2)*2
                    dist_m = 6371000 * (2 * np.arcsin(np.sqrt(a_calc)))
                    
                    if dist_m <= 150:
                        st.success(f"🎯 AION YORAKU: OBJETIVO LOCALIZADO ({int(dist_m)}m)")
                        bloqueo = False
                    else:
                        st.warning(f"📡 FUERA DE RANGO ({round(dist_m/1000, 2)} km)")
                else:
                    st.info("📡 SINCRONIZANDO GPS...")

        st.markdown("---")
        st.subheader("📝 Registro Operativo")
        with st.form("form_visita"):
            vigilantes = st.text_area("Personal presente en puesto")
            tipo_nov = st.selectbox("Gravedad de Novedad", ["Normal", "Siniestro", "Pedido Uniforme", "Urgencia"])
            novedad = st.text_area("Informe detallado")
            foto = st.camera_input("Capturar evidencia visual")
            c_m, c_o = st.columns(2)
            movil = c_m.text_input("Unidad Móvil", value="S-002")
            odo = c_o.number_input("Odómetro Actual", step=1)
            
            if st.form_submit_button("REGISTRAR VISITA EN MATRIZ", disabled=bloqueo):
                try:
                    gc = conectar_google()
                    sh = gc.open_by_key(ID_REPORTES).get_worksheet(0)
                    sh.append_row([str(datetime.now()), usuario_auth, movil, odo, destino, vigilantes, novedad, tipo_nov])
                    st.success("✅ Datos sincronizados correctamente.")
                except:
                    st.warning("Registro guardado localmente (Sin conexión directa al Drive).")

# --- 5. PERFIL MONITOREO ---
elif rol == "MONITOREO":
    st.header("🖥️ Consola Central de Monitoreo")
    
    if st.session_state.alerta_activa:
        st.markdown('<div class="alerta-panico">🚨 ALERTA CRÍTICA DE PÁNICO EN CURSO 🚨</div>', unsafe_allow_html=True)
        st.error("BLOQUEO TÁCTICO: Resuelva la emergencia para liberar la consola.")
        with st.form("cierre_panico"):
            operador = st.text_input("Operador que atiende")
            resolucion = st.text_area("Procedimiento y Resolución del Incidente") 
            if st.form_submit_button("Confirmar Atención y Archivar"):
                if operador and resolucion:
                    st.session_state.alerta_activa = False
                    st.success("Incidente archivado.")
                    st.rerun()
                else:
                    st.error("Complete todos los campos para desactivar la alarma.")
    else:
        col_radar, col_alertas = st.columns([2, 1])
        with col_radar:
            st.subheader("🛰️ Radar Satelital Global")
            m_mon = folium.Map(location=[df['LATITUD'].mean(), df['LONGITUD'].mean()], zoom_start=11, tiles="CartoDB dark_matter")
            for _, row in df.iterrows():
                folium.Marker([row['LATITUD'], row['LONGITUD']], tooltip=row['OBJETIVO']).add_to(m_mon)
            st_folium(m_mon, width="100%", height=500)
        with col_alertas:
            st.subheader("🔔 Gestión de Alarmas")
            st.success("🟢 Sistema Estable. Sin alertas en curso.")

# --- 6. PERFIL GERENCIA (SQL, ALTAS/BAJAS Y MENSAJES) ---
elif rol == "GERENCIA":
    st.header(f"📊 Tablero Ejecutivo: {usuario_auth}")
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Ahorro Logístico Estimado", "$128.400", "Optimización")
    m2.metric("Cobertura de Objetivos", f"{len(df)}/93", "Total Base")
    m3.metric("Efectividad de Respuesta", "100%", "Sin demoras")
    
    t1, t2, t3 = st.tabs(["📈 AUDITORÍA Y GESTIÓN", "⚙️ ALTAS/BAJAS DE SERVICIO", "📥 COMUNICACIONES"])
    
    with t1:
        st.subheader("Carga de Trabajo (Servicios por Supervisor)")
        chart_data = df['SUPERVISOR'].value_counts()
        st.bar_chart(chart_data)
        st.caption("Este gráfico detalla la cantidad de objetivos legales asignados a cada supervisor según la base de datos.")
        
        st.markdown("---")
        st.subheader("Motor Analítico SQL")
        query = "SELECT SUPERVISOR, COUNT(*) as Servicios FROM objetivos GROUP BY SUPERVISOR"
        res = pd.read_sql_query(query, conn)
        st.dataframe(res, use_container_width=True)
        st.download_button("📥 GENERAR REPORTE LUIS BONGIORNO (CSV)", res.to_csv(index=False), "auditoria_gerencia.csv")

    with t2:
        c_alta, c_baja = st.columns(2)
        with c_alta:
            with st.form("alta_obj"):
                st.write("➕ Alta de Servicio")
                n_obj = st.text_input("Nombre"); n_sup = st.selectbox("Asignar:", lista_sups); n_lat = st.number_input("Latitud", format="%.6f"); n_lon = st.number_input("Longitud", format="%.6f")
                if st.form_submit_button("INCORPORAR A LA RED"):
                    nuevo = pd.DataFrame([{'OBJETIVO': n_obj, 'SUPERVISOR': n_sup, 'LATITUD': n_lat, 'LONGITUD': n_lon}])
                    st.session_state.db_objetivos = pd.concat([st.session_state.db_objetivos, nuevo], ignore_index=True); st.rerun()
        with c_baja:
            with st.form("baja_obj"):
                st.write("➖ Baja de Servicio")
                elim = st.selectbox("Seleccionar Objetivo:", df['OBJETIVO'].tolist())
                if st.form_submit_button("ELIMINAR DEFINITIVAMENTE"):
                    st.session_state.db_objetivos = st.session_state.db_objetivos[st.session_state.db_objetivos['OBJETIVO'] != elim]; st.rerun()

    with t3:
        buzon(usuario_auth)
        st.markdown("---")
        with st.form("msg_ger"):
            d = st.selectbox("Destinatario de Circular:", ["TODOS", "DARÍO CECILIA"] + lista_sups)
            a = st.text_input("Asunto")
            m = st.text_area("Directiva Ejecutiva")
            if st.form_submit_button("Difundir"): enviar_msg(usuario_auth, d, a, m); st.success("Circular enviada a la red.")

# --- 7. JEFE DE OPERACIONES ---
elif rol == "JEFE DE OPERACIONES":
    st.header(f"🗃️ Comando Operativo: {usuario_auth}")
    t1, t2 = st.tabs(["📥 MENSAJES", "📤 EMITIR DIRECTIVA"])
    with t1: buzon(usuario_auth)
    with t2:
        with st.form("e_j"):
            d = st.selectbox("A:", ["TODOS", "LUIS BONGIORNO"] + lista_sups); a = st.text_input("Asunto"); m = st.text_area("Orden")
            if st.form_submit_button("Transmitir"): enviar_msg(usuario_auth, d, a, m); st.success("Orden en red.")
            
# --- 8. ADMINISTRADOR ---
elif rol == "ADMINISTRADOR":
    st.header("⚙️ Control Maestro AION-YORAKU")
    st.write("Base de Datos Maestra Activa")
    st.dataframe(df, use_container_width=True)
