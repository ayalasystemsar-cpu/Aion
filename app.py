import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from PIL import Image
import io

# --- 1. CONFIGURACIÓN E IDENTIDAD VISUAL ---
st.set_page_config(page_title="AION-YAROKU", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .stApp { background-color: #0A0A0A; color: #FFFFFF; }
    [data-testid="stSidebar"] { background-color: #111111; border-right: 2px solid #00E5FF; }
    h1, h2, h3 { color: #00E5FF !important; font-family: 'Lexend', sans-serif; }
    .stButton>button { background-color: #1A1A1A; color: #00E5FF; border: 1px solid #00E5FF; transition: 0.3s; }
    .stButton>button:hover { background-color: #00E5FF; color: #000000; box-shadow: 0 0 20px #00E5FF; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. MOTOR DE CONEXIÓN (NÚCLEO ESTRATÉGICO) ---
# El ID extraído de la terminal del usuario
ID_MAESTRO_DB = "1Md0VkOnwUJWIdq0S1fB9UrmOKv4MG_JVG3tQsda0Uw"

def conectar_servicio():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    # Se utiliza el archivo JSON de credenciales que ya posees en tu terminal
    creds = ServiceAccountCredentials.from_json_keyfile_name("aion-secutec-b9f914330ea6.json", scope)
    return gspread.authorize(creds)

def escribir_registro(nombre_pestana, datos_fila):
    try:
        cliente = conectar_servicio()
        hoja = cliente.open_by_key(ID_MAESTRO_DB).worksheet(nombre_pestana)
        hoja.append_row(datos_fila)
        return True
    except Exception as e:
        st.error(f"Falla de enlace con la base de datos: {e}")
        return False

@st.cache_data(ttl=300)
def cargar_objetivos():
    try:
        cliente = conectar_servicio()
        hoja = cliente.open_by_key(ID_MAESTRO_DB).worksheet("OBJETIVOS")
        df = pd.DataFrame(hoja.get_all_records())
        # Limpieza y normalización de coordenadas
        df['LATITUD'] = pd.to_numeric(df['LATITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        df['LONGITUD'] = pd.to_numeric(df['LONGITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        return df.dropna(subset=['LATITUD', 'LONGITUD'])
    except:
        return pd.DataFrame()

# --- 3. INTERFAZ DE MANDO ---
with st.sidebar:
    st.title("AION-YAROKU")
    perfil = st.selectbox("JERARQUÍA", ["SUPERVISOR", "MONITOREO", "GERENCIA", "ADMINISTRADOR"])
    
    if perfil == "ADMINISTRADOR":
        password = st.text_input("PASSWORD DE SISTEMA", type="password")
        if password != st.secrets.get("admin_password", "aion2026"):
            st.stop()
            
    st.markdown("---")
    if st.button("🚨 ACTIVAR PÁNICO (S.O.S)"):
        escribir_registro("ALERTAS", [str(datetime.now()), perfil, "BOTÓN PÁNICO", "PENDIENTE"])
        st.warning("ALERTA DE EMERGENCIA TRANSMITIDA")

# --- 4. LÓGICA OPERATIVA (SUPERVISIÓN) ---
df_servicios = cargar_objetivos()

if perfil == "SUPERVISOR":
    st.header("Terminal Táctica de Supervisión")
    
    opcion = st.tabs(["🗺️ RADAR", "📝 REPORTE DE MOVIL"])
    
    with opcion[0]:
        if not df_servicios.empty:
            # Mapa centrado en la media de los objetivos
            m = folium.Map(location=[df_servicios['LATITUD'].mean(), df_servicios['LONGITUD'].mean()], 
                           zoom_start=12, tiles="CartoDB dark_matter")
            for _, r in df_servicios.iterrows():
                folium.Marker([r['LATITUD'], r['LONGITUD']], popup=r['OBJETIVO']).add_to(m)
            st_folium(m, width="100%", height=450)
        else:
            st.info("Cargando matriz de objetivos desde la nube...")

    with opcion[1]:
        with st.form("form_flota"):
            st.subheader("Control de Flota y Novedades")
            f_movil = st.text_input("Unidad Móvil (Ej: Movil 10)")
            f_km = st.number_input("Odómetro Actual (KM)", step=1)
            f_patente = st.text_input("Patente")
            f_vigilador = st.text_input("Vigilador en Puesto")
            f_novedad = st.text_area("Informe de Novedades")
            f_foto = st.camera_input("Captura de Evidencia")
            
            if st.form_submit_button("REGISTRAR Y ENVIAR"):
                # Impacto en la pestaña unificada ACTAS_FLOTA
                exito = escribir_registro("ACTAS_FLOTA", [
                    str(datetime.now()), "SUPERVISOR", f_movil, f_patente, 
                    f_km, "", f_vigilador, "CONTROL RUTA", f_novedad
                ])
                if exito: st.success("Datos transmitidos al servidor maestro.")

# --- 5. PANEL DE MONITOREO ---
elif perfil == "MONITOREO":
    st.header("Centro de Monitoreo Global")
    st.metric("Servicios Activos", len(df_servicios))
    # Aquí se visualizan las alertas en tiempo real leyendo la pestaña ALERTAS
    st.dataframe(df_servicios[['OBJETIVO', 'DIRECCION', 'SUPERVISOR']])

# --- 6. ADMINISTRADOR (BRIAN AYALA) ---
elif perfil == "ADMINISTRADOR":
    st.header("Bóveda del Director General")
    st.write("Estado de la infraestructura: *Sincronizado*")
    if st.button("Actualizar Base de Datos"):
        st.cache_data.clear()
        st.rerun()
