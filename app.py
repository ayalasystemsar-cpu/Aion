import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from datetime import datetime
import numpy as np
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from streamlit_js_eval import get_geolocation

# --- 1. CONFIGURACIÓN E IDENTIDAD VISUAL CORPORATIVA ---
st.set_page_config(page_title="AION-YAROKU", layout="wide", initial_sidebar_state="expanded")

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
    # Logo Reestructurado (Escudo Corporativo)
    st.markdown('<div class="logo-container">', unsafe_allow_html=True)
    try:
        st.image("assets/logo_aion.png", use_column_width=True)
    except:
        st.markdown("<h2 style='margin:0;'>AION<br>YAROKU</h2>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

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
    elif rol == "ADMINISTRADOR":
        clave = st.text_input("CREDENCIAL MAESTRA", type="password")
        if clave != st.secrets.get("admin_password", "aion2026"):
            st.error("ACCESO DENEGADO. NÚCLEO BLOQUEADO.")
            st.stop()
        usuario_auth = "AYALA BRIAN (ADMIN)"

    st.markdown("---")
