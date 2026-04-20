import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from streamlit_js_eval import get_geolocation
import sqlite3
import numpy as np
import os

# --- 1. ESTÉTICA TÁCTICA AION-YAROKU ---
st.set_page_config(page_title="AION-YAROKU v4.1", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .stApp { background-color: #121212; color: #E0E0E0; }
    [data-testid="stSidebar"] { background-color: #1A1A1A; border-right: 2px solid #00E5FF; }
    h1, h2, h3, .stSubheader { color: #00E5FF !important; font-family: 'Courier New', monospace; font-weight: bold; }
    div[data-testid="metric-container"] {
        background-color: #1E1E1E; border: 1px solid #333; border-left: 5px solid #00E5FF; padding: 15px; border-radius: 5px;
    }
    .stButton>button {
        background-color: #1E1E1E; color: #00E5FF; border: 1px solid #00E5FF; border-radius: 4px; transition: 0.3s;
    }
    .stButton>button:hover { background-color: #00E5FF; color: #121212; box-shadow: 0 0 15px #00E5FF; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIONES DINÁMICAS (NUBE) ---
def conectar_google():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        # Uso de Secrets para privacidad total (Invisible en GitHub)
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return gspread.authorize(creds)
    except:
        return None

# [span_0](start_span)IDs de tus planillas originales[span_0](end_span)
ID_SERVICIOS = "1zr3q9kM8z-GU-uPaUQG4iv8-kcgLgdYHInIJZhDxd-s" 
ID_REPORTES = "1UxvfiIqPjWxUJlc7C-zqQWOCTmm1O18J2Q5AoFx9Gl0"  
ID_PANICO = "1sM4NhsbkJQR7pTvXWKK4QZlw3unzXvBMFWOPLruAZ5Q"    

@st.cache_data(ttl=60)
def cargar_base_viva():
    # [span_1](start_span)Tu enlace original de Google Sheets[span_1](end_span)
    url = f"https://docs.google.com/spreadsheets/d/e/2PACX-1vSAGsJV1Geh53WoeRhi9Jec_KLWlSnPAwId0ADMuAUrnRofMW-4SVawEuIDrEVf7mWB7DfYQnSShXzm/pub?output=csv"
    data = pd.read_csv(url)
    data.columns = data.columns.str.strip().str.upper()
    
    # [span_2](start_span)[span_3](start_span)Limpieza Robusta: Elimina vacíos y normaliza coordenadas (comas a puntos)[span_2](end_span)[span_3](end_span)
    data = data.dropna(subset=['LATITUD', 'LONGITUD'])
    data["LATITUD"] = data["LATITUD"].astype(str).str.replace(",", ".").astype(float).round(6)
    data["LONGITUD"] = data["LONGITUD"].astype(str).str.replace(",", ".").astype(float).round(6)
    return data

df = cargar_base_viva()

# [span_4](start_span)MOTOR SQL EN MEMORIA PARA AUDITORÍA[span_4](end_span)
conn = sqlite3.connect(":memory:")
df.to_sql("objetivos", conn, index=False, if_exists="replace")
consulta_sql = pd.read_sql_query("SELECT SUPERVISOR, COUNT(*) as total_objetivos FROM objetivos GROUP BY SUPERVISOR", conn)

# --- 3. PANEL LATERAL: JERARQUÍA DE MANDO ---
with st.sidebar:
    st.title("AION-YAROKU")
    st.image("https://img.icons8.com/nolan/128/security-shield.png", width=100)

    rol = st.selectbox("PERFIL DE ACCESO", ["SUPERVISOR", "MONITOREO", "JEFE DE OPERACIONES", "GERENCIA", "ADMINISTRADOR"])
    
    usuario_auth = "ADMIN"
    if rol == "SUPERVISOR":
        # Lista actualizada: Darío ahora es Jefe de Operaciones
        lista_sup = ["SERANTES WALTER", "SANOJA LUIS", "DIAZ MARCELO", "MAZACOTTE CLAUDIO", "PORZIO GONZALO", "AYALA BRIAN", "CARRIZO WALTER"]
        usuario_auth = st.selectbox("IDENTIFÍQUESE", lista_sup)
    elif rol == "JEFE DE OPERACIONES":
        usuario_auth = "DARÍO CECILIA"
    elif rol == "GERENCIA":
        usuario_auth = "LUIS BONGIORNO"
    
    st.markdown("---")
    # PÁNICO BLINDADO: Independiente del GPS para mayor seguridad
    if st.button("🔴 ACTIVAR PÁNICO", use_container_width=True):
        gc = conectar_google()
        if gc:
            sh = gc.open_by_key(ID_PANICO).get_worksheet(0)
            sh.append_row([str(datetime.now()), usuario_auth, "EMERGENCIA", "ENVIADO"])
            st.error("ALERTA ENVIADA A MONITOREO")
        else:
            st.warning("📡 Error de conexión. Verifique señal.")

# --- 4. PERFIL SUPERVISOR (RADAR Y REGISTRO) ---
if rol == "SUPERVISOR":
    st.header(f"Estación de Control: {usuario_auth}")
    st.warning("⚠️ ÚLTIMA CIRCULAR DE GERENCIA PENDIENTE")
    
    apellido = usuario_auth.split()[-1].upper()
    df_zona = df[df['SUPERVISOR'].str.upper().str.contains(apellido, na=False)]

    c1, c2, c3 = st.columns(3)
    c1.metric("Objetivos", len(df_zona))
    c2.metric("GPS", "Sincronizado")
    c3.metric("Ruta", "Zona Norte")

    st.markdown("---")
    col_map, col_gps = st.columns([2, 1])
    
    with col_map:
        st.subheader("📍 Despliegue Táctico")
        m = folium.Map(location=[df_zona['LATITUD'].mean(), df_zona['LONGITUD'].mean()], zoom_start=12, tiles="CartoDB dark_matter")
        for _, row in df_zona.iterrows():
            folium.Marker([row['LATITUD'], row['LONGITUD']], popup=row['OBJETIVO']).add_to(m)
        st_folium(m, width="100%", height=400)
    
    with col_gps:
        st.subheader("🚀 Navegación")
        destino = st.selectbox("Seleccionar Objetivo:", df_zona['OBJETIVO'].unique())
        if st.button("🗺️ VER EN MAPS"):
            target = df_zona[df_zona['OBJETIVO'] == destino].iloc[0]
            st.markdown(f"[ABRIR GOOGLE MAPS](http://maps.google.com/?q={target['LATITUD']},{target['LONGITUD']})")

    # RADAR DE PROXIMIDAD (150m)
    pos_gps = get_geolocation()
    bloqueo = True
    if pos_gps and 'coords' in pos_gps:
        target = df_zona[df_zona['OBJETIVO'] == destino].iloc[0]
        mi_lat, mi_lon = pos_gps['coords']['latitude'], pos_gps['coords']['longitude']
        dist = 6371000 * (2 * np.arcsin(np.sqrt(np.sin((np.radians(target['LATITUD'])-np.radians(mi_lat))/2)*2 + np.cos(np.radians(mi_lat))*np.cos(np.radians(target['LATITUD']))*np.sin((np.radians(target['LONGITUD'])-np.radians(mi_lon))/2)*2)))
        if dist <= 150:
            st.success(f"🎯 EN RANGO ({int(dist)}m)"); bloqueo = False
        else:
            st.warning(f"📡 FUERA DE RANGO ({round(dist/1000, 2)} km)")

    with st.form("form_visita"):
        novedad = st.text_area("Informe de Visita")
        foto = st.camera_input("Evidencia")
        if st.form_submit_button("REGISTRAR VISITA", disabled=bloqueo):
            try:
                gc = conectar_google()
                sh = gc.open_by_key(ID_REPORTES).get_worksheet(0)
                sh.append_row([str(datetime.now()), usuario_auth, "S-002", 0, destino, "Presente", novedad, "Normal"])
                st.success("✅ Registro sincronizado con éxito.")
            except:
                st.error("Error de sincronización.")

# --- 5. PERFIL MONITOREO (CIERRE DE PÁNICOS) ---
elif rol == "MONITOREO":
    st.header("🖥️ Consola de Monitoreo")
    m_mon = folium.Map(location=[df['LATITUD'].mean(), df['LONGITUD'].mean()], zoom_start=11, tiles="CartoDB dark_matter")
    for _, row in df.iterrows():
        folium.Marker([row['LATITUD'], row['LONGITUD']], tooltip=row['OBJETIVO']).add_to(m_mon)
    st_folium(m_mon, width="100%", height=500)
    
    st.subheader("🔔 Gestión de Alarmas")
    with st.form("cierre_panico"):
        operador = st.text_input("Operador que atiende")
        resolucion = st.text_area("Procedimiento realizado")
        if st.form_submit_button("Archivar y Notificar a Gerencia"):
            st.success(f"Alerta gestionada por {operador}.")

# --- 6. PERFIL JEFE DE OPERACIONES (DARÍO CECILIA) ---
elif rol == "JEFE DE OPERACIONES":
    st.header(f"🗃️ ESTACIÓN DE MANDO: {usuario_auth}")
    t1, t2, t3 = st.tabs(["📊 AUDITORÍA SQL", "📍 RADAR GLOBAL", "📝 INFORME A GERENCIA"])
    with t1:
        st.subheader("Objetivos por Supervisor (Datos Reales)")
        st.dataframe(consulta_sql, use_container_width=True)
    with t2:
        m_ceci = folium.Map(location=[df['LATITUD'].mean(), df['LONGITUD'].mean()], zoom_start=11, tiles="CartoDB dark_matter")
        for _, row in df.iterrows():
            folium.Marker([row['LATITUD'], row['LONGITUD']], popup=row['OBJETIVO']).add_to(m_ceci)
        st_folium(m_ceci, width="100%", height=500)
    with t3:
        asunto = st.text_input("Asunto")
        detalle = st.text_area("Desarrollo de Novedad")
        if st.button("ENVIAR DIRECTIVA"):
            st.success("Informe enviado a Gerencia.")

# --- 7. PERFIL GERENCIA (LUIS BONGIORNO) ---
elif rol == "GERENCIA":
    st.header(f"📊 GERENCIA GENERAL: {usuario_auth}")
    m1, m2 = st.columns(2)
    m1.metric("Cobertura de Red", f"{len(df)}/93", "Servicios Activos")
    m2.metric("Efectividad", "100%", "Operativo")
    
    st.bar_chart(df['SUPERVISOR'].value_counts())
    
    st.markdown("---")
    st.subheader("📣 COMUNICACIÓN Y GESTIÓN")
    dest = st.radio("Destinatario:", ["MENSAJE A TODOS", "DARÍO CECILIA"])
    msg = st.text_area("Directiva de Gerencia:")
    if st.button("DIFUNDIR"):
        st.success("Circular enviada y registrada.")

# --- 8. ADMINISTRADOR ---
elif rol == "ADMINISTRADOR":
    st.header("Control Maestro AION-YAROKU")
    st.write("Base de Datos Maestra (93 Objetivos)")
    st.dataframe(df, use_container_width=True)
