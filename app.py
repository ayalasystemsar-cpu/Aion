import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- 1. CONFIGURACIÓN E IDENTIDAD CORPORATIVA ---
st.set_page_config(page_title="AION-YAROKU", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .stApp { background-color: #0A0A0A; color: #FFFFFF; }
    [data-testid="stSidebar"] { background-color: #111111; border-right: 2px solid #00E5FF; }
    h1, h2, h3 { color: #00E5FF !important; font-family: 'Courier New', monospace; }
    .stButton>button { background-color: #1A1A1A; color: #00E5FF; border: 1px solid #00E5FF; transition: 0.3s; font-weight: bold; width: 100%; }
    .stButton>button:hover { background-color: #00E5FF; color: #000000; box-shadow: 0 0 15px #00E5FF; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. MOTOR DE BASE DE DATOS (NÚCLEO CENTRAL) ---
ID_MAESTRO_DB = "1Md0VkOnwUJWIdq0S1fB9UrmOKv4MG_JVG3tQsda0Uw"

def conectar_servicio():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("aion-secutec-b9f914330ea6.json", scope)
    return gspread.authorize(creds)

def escribir_registro(nombre_pestana, datos_fila):
    try:
        cliente = conectar_servicio()
        hoja = cliente.open_by_key(ID_MAESTRO_DB).worksheet(nombre_pestana)
        hoja.append_row(datos_fila)
        return True
    except Exception as e:
        st.error(f"Falla de enlace de transmisión: {e}")
        return False

@st.cache_data(ttl=120)
def cargar_objetivos():
    try:
        cliente = conectar_servicio()
        hoja = cliente.open_by_key(ID_MAESTRO_DB).worksheet("OBJETIVOS")
        df = pd.DataFrame(hoja.get_all_records())
        df['LATITUD'] = pd.to_numeric(df['LATITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        df['LONGITUD'] = pd.to_numeric(df['LONGITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        return df.dropna(subset=['LATITUD', 'LONGITUD'])
    except:
        return pd.DataFrame()

df_servicios = cargar_objetivos()

# --- 3. GESTIÓN DE ACCESO Y JERARQUÍAS ---
with st.sidebar:
    st.title("AION-YAROKU")
    perfil = st.selectbox("JERARQUÍA OPERATIVA", ["SUPERVISOR", "MONITOREO", "GERENCIA", "ADMINISTRADOR"])
    
    usuario_activo = ""
    if perfil == "SUPERVISOR":
        lista_sups = ["AYALA BRIAN", "SERANTES WALTER", "SANOJA LUIS", "DIAZ MARCELO", "MAZACOTTE CLAUDIO", "PORZIO GONZALO", "CARRIZO WALTER"]
        usuario_activo = st.selectbox("IDENTIFICACIÓN", lista_sups)
    elif perfil == "ADMINISTRADOR":
        password = st.text_input("CLAVE DE SISTEMA", type="password")
        if password == st.secrets.get("admin_password", "aion2026"):
            usuario_activo = "AYALA BRIAN (SysAdmin)"
            st.success("Acceso Nivel Bóveda Autorizado")
        elif password != "":
            st.error("Credencial Denegada")
            st.stop()
        else:
            st.stop()
    else:
        usuario_activo = perfil
            
    st.markdown("---")
    if st.button("🚨 ACTIVAR PÁNICO (S.O.S)"):
        escribir_registro("ALERTAS", [str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")), usuario_activo, "BOTÓN PÁNICO", "CRÍTICO"])
        st.error("SEÑAL DE EMERGENCIA TRANSMITIDA A CENTRAL")

# --- 4. TERMINAL TÁCTICA: SUPERVISORES ---
if perfil == "SUPERVISOR" and usuario_activo:
    st.header(f"Unidad de Mando: {usuario_activo}")
    
    pestanas = st.tabs(["🗺️ RADAR DE ZONA", "📋 ACTA DE FLOTA"])
    
    with pestanas[0]:
        if not df_servicios.empty:
            m = folium.Map(location=[df_servicios['LATITUD'].mean(), df_servicios['LONGITUD'].mean()], 
                           zoom_start=11, tiles="CartoDB dark_matter")
            for _, r in df_servicios.iterrows():
                folium.Marker(
                    [r['LATITUD'], r['LONGITUD']], 
                    popup=f"{r['OBJETIVO']} - {r['DIRECCION']}",
                    tooltip=r['OBJETIVO']
                ).add_to(m)
            st_folium(m, width="100%", height=500)
        else:
            st.warning("Matriz de coordenadas offline. Verifique conexión a base de datos.")

    with pestanas[1]:
        with st.form("registro_acta"):
            st.subheader("Auditoría de Puesto y Unidad")
            
            # Directivas ejecutadas: Flota predeterminada, KM numérico, Vigilador libre
            f_movil = st.selectbox("Asignación de Unidad Móvil", ["S-001", "S-002", "S-003", "S-004", "S-005", "S-006", "S-007"])
            f_km = st.number_input("Odómetro Actual (KM)", min_value=0, step=1)
            
            f_objetivo = st.selectbox("Objetivo Inspeccionado", df_servicios['OBJETIVO'].unique() if not df_servicios.empty else ["Sin conexión"])
            f_vigilador = st.text_input("Nombre y Apellido del Personal en Puesto")
            f_novedad = st.text_area("Desarrollo de la Inspección / Novedades")
            
            if st.form_submit_button("SELLAR Y TRANSMITIR ACTA"):
                if f_vigilador == "" or f_novedad == "":
                    st.error("Rechazado. Los campos de personal y novedades son obligatorios.")
                else:
                    # Columnas destino: FECHA, SUPERVISOR, MOVIL, PATENTE, KM, RENDIMIENTO, VIGILADOR_NOMBRE, OBJETIVO, INFORME
                    # Dejamos Patente y Rendimiento en blanco por ahora para ser procesados luego.
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    datos = [timestamp, usuario_activo, f_movil, "", f_km, "", f_vigilador, f_objetivo, f_novedad]
                    
                    if escribir_registro("ACTAS_FLOTA", datos):
                        st.success("Acta registrada con éxito. Información enrutada a la base central.")

# --- 5. TERMINAL: CENTRAL DE MONITOREO ---
elif perfil == "MONITOREO":
    st.header("Centro de Control Global")
    col1, col2 = st.columns(2)
    col1.metric("Servicios Activos en Matriz", len(df_servicios))
    col2.metric("Estado de Red", "EN LÍNEA", delta="Latencia Óptima")
    st.info("Operador de monitoreo: El radar maestro está en la consola secundaria.")

# --- 6. BÓVEDA DEL DIRECTOR GENERAL (CEO) ---
elif perfil == "ADMINISTRADOR":
    st.header("Centro de Mando General")
    st.write("Métricas y Auditoría de Datos.")
    
    if st.button("Forzar Sincronización de Nube"):
        st.cache_data.clear()
        st.success("Caché purgado. La base de datos está leyendo en tiempo real.")
        
    st.subheader("Auditoría de Despliegue")
    st.dataframe(df_servicios)
