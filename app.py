import streamlit as st
import datetime
from datetime import datetime
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
import io
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import streamlit.components.v1 as components
from streamlit_qrcode_scanner import qrcode_scanner


# --- 1. CONFIGURACIÓN E INICIALIZACIÓN CON PERSISTENCIA POR URL ---

st.set_page_config(page_title="AION-YAROKU | COMMAND", page_icon="🛡️", layout="wide", initial_sidebar_state="expanded")

query_params = st.query_params

if 'usuario_logueado' not in st.session_state:
    st.session_state.usuario_logueado = query_params.get("logueado", "false") == "true"

if 'rol_sel' not in st.session_state:
    st.session_state.rol_sel = query_params.get("rol", "MONITOREO")

if 'user_sel' not in st.session_state:
    st.session_state.user_sel = query_params.get("user", "OPERADOR CENTRAL")

if 'sup_autenticado' not in st.session_state:
    st.session_state.sup_autenticado = query_params.get("sup_auth", "false") == "true"

if 'admin_autenticado' not in st.session_state:
    st.session_state.admin_autenticado = query_params.get("admin_auth", "false") == "true"

if 'ultimo_mensaje_qr' not in st.session_state: 
    st.session_state.ultimo_mensaje_qr = ""

def sincronizar_url_sesion():
    st.query_params.update({
        "logueado": "true" if st.session_state.usuario_logueado else "false",
        "rol": st.session_state.rol_sel,
        "user": st.session_state.user_sel,
        "sup_auth": "true" if st.session_state.sup_autenticado else "false",
        "admin_auth": "true" if st.session_state.admin_autenticado else "false"
    })


# --- 2. CONEXIONES Y FUNCIONES GLOBALES OPTIMIZADAS ---

ID_MAESTRO_DB = "1Md0VkOnwUJWldq0S1fB9UrmOKv4MG__JVG3tQsda0Uw"

@st.cache_resource
def conectar_google():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        return gspread.authorize(creds)
    except: 
        return None

def obtener_hora_argentina():
    tz = pytz.timezone("America/Argentina/Buenos_Aires")
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

def actualizar_celda(pestana, fila, columna, valor):
    try:
        gc = conectar_google()
        if gc:
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
            hoja.update_acell(f"{columna}{fila}", valor)
            st.cache_data.clear()
            return True
    except: 
        return False

def escribir_registro_nube(pestana, datos_fila):
    try:
        gc = conectar_google()
        if gc:
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
            hoja.append_row(datos_fila)
            st.cache_data.clear() 
            return True
    except Exception as e:
        print(f"Error de nube en {pestana}: {e}")
        st.error(f"⚠️ Error técnico en nube: {e}")
        return False

@st.cache_data(ttl=30)
def leer_matriz_nube(pestana):
    gc = conectar_google()
    if gc:
        try:
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
            todas_filas = hoja.get_all_values()
            if not todas_filas or len(todas_filas) == 0:
                return pd.DataFrame()
            encabezados = [str(h).strip().upper() for h in todas_filas[0]]
            datos_cuerpo = todas_filas[1:]
            df = pd.DataFrame(datos_cuerpo, columns=encabezados)
            df.columns = [str(c).strip().upper() for c in df.columns]
            df = df.loc[:, ~df.columns.duplicated()]
            return df
        except: 
            return pd.DataFrame()
    return pd.DataFrame()

@st.cache_data(ttl=60)
def cargar_datos_comisarias():
    data = {
        "COMISARIA": ["COMISARÍA SAN MARTÍN 1RA", "COMISARÍA VECINAL 14C", "COMISARÍA AVELLANEDA 1RA", "COMISARÍA CAMPANA 1RA", "COMISARÍA SAN FERNANDO 1RA", "COMISARÍA TIGRE 1RA", "COMISARÍA PILAR 6TA (VILLA ROSA)", "COMISARÍA VECINAL 1B", "COMISARÍA VECINAL 14A", "COMISARÍA LANÚS 2DA", "COMISARÍA VECINAL 13A", "COMISARÍA LA MATANZA 2DA", "COMISARÍA LA MATANZA 3RA", "COMISARÍA VECINAL 2A", "COMISARÍA VECINAL 12A", "COMISARÍA VECINAL 12B", "COMISARÍA VECINAL 6A", "COMISARÍA VECINAL 1D", "COMISARÍA RAMOS MEJÍA 2DA"],
        "LATITUD": [-34.580139, -34.587773, -34.664119, -34.163693, -34.440154, -34.424196, -34.417041, -34.617133, -34.587773, -34.708819, -34.557454, -34.700147, -34.717182, -34.589886, -34.554321, -34.568459, -34.613045, -34.603847, -34.646589],
        "LONGITUD": [-58.541410, -58.416056, -58.368073, -58.961418, -58.556134, -58.579789, -58.868209, -58.378734, -58.416056, -58.385311, -58.461144, -58.575608, -58.608301, -58.401918, -58.472147, -58.482012, -58.437198, -58.381577, -58.564571]
    }
    return pd.DataFrame(data)

@st.cache_data(ttl=30)
def cargar_objetivos():
    df = leer_matriz_nube("OBJETIVOS")
    if not df.empty:
        df.columns = df.columns.str.strip().str.upper()
        df = df[df['OBJETIVO'].astype(str).str.strip() != ""]
        df = df[df['OBJETIVO'].notna()]
        if 'SUPERVISOR' in df.columns:
            df['SUPERVISOR'] = df['SUPERVISOR'].astype(str).str.strip().str.upper()
        df['LATITUD'] = df['LATITUD'].astype(str).str.replace(',', '.')
        df['LONGITUD'] = df['LONGITUD'].astype(str).str.replace(',', '.')
        df['LATITUD'] = pd.to_numeric(df['LATITUD'], errors='coerce')
        df['LONGITUD'] = pd.to_numeric(df['LONGITUD'], errors='coerce')
        return df 
    return pd.DataFrame()

def obtener_lista_supervisores_dinamica():
    base = ["AYALA BRIAN", "SUPERVISOR 1", "SUPERVISOR 2", "SUPERVISOR 3", "SUPERVISOR 4", "SUPERVISOR 5", "SUPERVISOR NOCTURNO"]
    df_u = leer_matriz_nube("USUARIOS")
    if not df_u.empty:
        col_r = 'ROL' if 'ROL' in df_u.columns else 'ROLES'
        col_u = 'USUARIO' if 'USUARIO' in df_u.columns else df_u.columns[0]
        if col_r in df_u.columns and 'ESTADO' in df_u.columns:
            sups_extra = df_u[(df_u[col_r].astype(str).str.strip().str.upper() == "SUPERVISOR") & (df_u['ESTADO'].astype(str).str.strip().str.upper() == "APROBADO")][col_u].tolist()
            for s in sups_extra:
                s_limpio = str(s).strip().upper()
                if s_limpio not in base:
                    base.append(s_limpio)
    return base

@st.cache_resource
def obtener_grafo_zona(lat, lon):
    try:
        return ox.graph_from_point((lat, lon), dist=5000, network_type='drive')
    except:
        return None

def obtener_ruta_calles_osrm(lat1, lon1, lat2, lon2):
    try:
        url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=full&geometries=geojson"
        response = requests.get(url, timeout=5).json()
        if response.get("code") == "Ok":
            coordenadas = response["routes"][0]["geometry"]["coordinates"]
            return [[point[1], point[0]] for point in coordenadas]
    except:
        pass
    return [[lat1, lon1], [lat2, lon2]]

def registrar_jornada_general(supervisor, objetivo, accion):
    try:
        tz = pytz.timezone("America/Argentina/Buenos_Aires")
        ahora = datetime.now(tz)
        fecha = ahora.strftime("%Y-%m-%d")
        hora = ahora.strftime("%H:%M:%S")
        datos = [fecha, str(supervisor).strip().upper(), str(objetivo).strip().upper(), str(accion).strip().upper(), hora]
        
        gc = conectar_google()
        if gc:
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet("JORNADA_SUPERVISORES")
            hoja.append_row(datos)
            st.cache_data.clear()
            return True
    except Exception as ex:
        print(f"Error en jornada general: {ex}")
    return False

def registrar_qr_supervisor(supervisor, objetivo, accion):
    try:
        tz = pytz.timezone("America/Argentina/Buenos_Aires")
        ahora = datetime.now(tz)
        fecha_hora = ahora.strftime("%Y-%m-%d %H:%M:%S")
        datos = [fecha_hora, str(objetivo).strip().upper(), str(accion).strip().upper(), str(supervisor).strip().upper(), "REGISTRADO"]
        
        gc = conectar_google()
        if gc:
            sh = gc.open_by_key(ID_MAESTRO_DB)
            hoja = None
            nombres_posibles = ["REGISTRO_QR_SUPERVISORES", "REGISTRO-QR-SUPERVISORES", "REGISTRO QR SUPERVISORES"]
            
            for nombre in nombres_posibles:
                try:
                    hoja = sh.worksheet(nombre)
                    break
                except:
                    continue
            
            if hoja is None:
                hoja = sh.add_worksheet(title="REGISTRO_QR_SUPERVISORES", rows="100", cols="10")
                hoja.append_row(["FECHA_HORA", "OBJETIVO", "ACCION", "SUPERVISOR", "ESTADO"])

            hoja.append_row(datos)
            st.cache_data.clear()
            return True
    except Exception as ex:
        st.error(f"⚠️ Error detallado en nube: {ex}")
    return False

def generar_pdf_reporte(titulo_reporte, df_datos):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elementos = []
    styles = getSampleStyleSheet()
    estilo_titulo = ParagraphStyle('TituloTactico', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=16, textColor=colors.HexColor('#0A0F1E'), spaceAfter=6, alignment=1)
    estilo_sub = ParagraphStyle('SubTactico', parent=styles['Normal'], fontName='Helvetica', fontSize=9, textColor=colors.HexColor('#555555'), spaceAfter=15, alignment=1)
    
    elementos.append(Paragraph("<b>AION-YAROKU | REPORTE TÁCTICO OFICIAL</b>", estilo_titulo))
    elementos.append(Paragraph(f"<b>{titulo_reporte}</b><br/>Fecha de Emisión: {obtener_hora_argentina()}", estilo_sub))
    elementos.append(Spacer(1, 10))
    
    if not df_datos.empty:
        columnas = list(df_datos.columns)
        datos_tabla = [[str(c) for c in columnas]]
        for _, row in df_datos.iterrows():
            datos_tabla.append([str(row[c]) if pd.notna(row[c]) else "" for c in columnas])
            
        t = Table(datos_tabla, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0A0F1E')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8F9FA')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('TOPPADDING', (0, 1), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
        ]))
        elementos.append(t)
    else:
        elementos.append(Paragraph("No hay registros disponibles para este reporte.", styles['Normal']))
        
    doc.build(elementos)
    buffer.seek(0)
    return buffer.getvalue()

def aplicar_identidad_alfa():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@300;500;700&display=swap');
        .stApp { background: radial-gradient(circle at top, #0A0F1E 0%, #030305 100%) !important; color: #E0E0E0; font-family: 'Rajdhani', sans-serif; }
        
        .block-container {
            padding-left: 1rem !important;
            padding-right: 1rem !important;
            padding-top: 1rem !important;
            max-width: 100% !important;
        }

        .contenedor-logo-central { display: flex; justify-content: center; align-items: center; width: 100%; margin: 5px 0; }
        .logo-phoenix { 
            width: 100% !important; 
            max-width: 320px !important; 
            height: auto !important;
            object-fit: contain !important;
            border: 2px solid #00e5ff !important; 
            box-shadow: 0 0 35px rgba(0, 229, 255, 0.5) !important; 
            border-radius: 4px !important; 
            background-color: #000 !important; 
        }
        .estacion-titulo {
            font-family: 'Orbitron', sans-serif;
            color: #00E5FF !important; font-size: 22px; margin-top: 5px;
            display: flex; align-items: center; justify-content: center; gap: 12px;
            text-shadow: 0 0 15px rgba(0, 229, 255, 0.4); letter-spacing: 2px; text-transform: uppercase;
            text-align: center;
        }
        
        /* Ocultar únicamente el menú de Streamlit pero forzar que el botón/flecha de la barra lateral esté siempre visible */
        header [data-testid="stToolbar"], footer, #MainMenu {
            display: none !important;
            visibility: hidden !important;
        }
        
        div[data-testid="collapsedControl"] {
            display: block !important;
            visibility: visible !important;
            z-index: 999999 !important;
        }

        header {
            background: transparent !important;
            background-color: transparent !important;
        }

        .stApp div[data-testid="stExpander"] { background-color: #1A1C23 !important; border: 1px solid #2D313E !important; border-radius: 8px !important; }
        .stApp div[data-testid="stExpander"] summary p { color: #E0E0E0 !important; font-size: 14px !important; font-weight: 600 !important; text-transform: uppercase; }
        .stApp input { background-color: #252833 !important; color: #FFFFFF !important; border: 1px solid #1A1C23 !important; border-radius: 6px !important; }
        .stApp label p { color: #A0A5B5 !important; font-family: 'Orbitron', sans-serif !important; font-size: 11px !important; font-weight: bold !important; letter-spacing: 0.5px; text-transform: uppercase; }
        .radar-box { border: 1px solid #00e5ff; border-radius: 8px; padding: 5px; background: #000000; box-shadow: 0 0 20px rgba(0, 229, 255, 0.2); }
        
        .stButton > button[kind="primary"] { 
            background: radial-gradient(circle, #FF0000 0%, #8B0000 100%) !important;
            color: white !important; border-radius: 50% !important; width: 110px !important; height: 110px !important; 
            border: 3px solid #333 !important; box-shadow: 0 0 25px rgba(255, 0, 0, 0.6) !important; 
            font-family: 'Orbitron', sans-serif; font-size: 11px !important; font-weight: bold;
            display: block; margin: 0 auto;
        }

        .panel-novedad { border: 1px solid #333; border-radius: 8px; padding: 15px; margin-top: 15px; background-color: rgba(10, 10, 11, 0.9); }
        
        .qr-scanner-container {
            display: flex;
            justify-content: center;
            align-items: center;
            width: 100%;
            max-width: 400px;
            margin: 2px auto 8px auto;
            overflow: hidden;
            border-radius: 8px;
            background: #000;
        }
        .qr-scanner-container iframe, .qr-scanner-container video, .qr-scanner-container div {
            width: 100% !important;
            max-width: 400px !important;
            height: 250px !important;
            object-fit: cover !important;
            border-radius: 8px !important;
            border: 2px solid #00E5FF !important;
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 6px !important;
            background-color: transparent !important;
            flex-wrap: nowrap !important;
            overflow-x: auto !important;
            white-space: nowrap !important;
            padding-bottom: 5px !important;
        }
        .stTabs [data-baseweb="tab"] {
            background-color: rgba(26, 28, 35, 0.6) !important;
            border: 1px solid #2D313E !important;
            color: #A0A5B5 !important;
            border-radius: 4px 4px 0px 0px !important;
            padding: 8px 12px !important;
            font-family: 'Orbitron', sans-serif;
            font-size: 11px !important;
            font-weight: bold;
            flex-shrink: 0 !important;
        }
        .stTabs [aria-selected="true"] { background-color: #1A1C23 !important; border-top: 2px solid #00E5FF !important; color: #00E5FF !important; }
        
        div[data-testid="stMetric"] { background-color: rgba(10, 11, 15, 0.6) !important; border: 1px solid #1A1C23 !important; border-radius: 6px !important; padding: 8px !important; }
        div[data-testid="stMetricLabel"] p { color: #00E5FF !important; font-family: 'Rajdhani', sans-serif !important; font-size: 12px !important; font-weight: bold !important; text-transform: uppercase; letter-spacing: 0.5px; }
        div[data-testid="stMetricValue"] div { color: #FFFFFF !important; font-family: 'Orbitron', sans-serif !important; font-size: 18px !important; }
        
        div[data-testid="stDataFrame"] {
            width: 100% !important;
            overflow-x: auto !important;
        }

        .btn-google-maps {
            display: inline-flex; align-items: center; justify-content: center;
            background-color: #ffffff !important; color: #1a73e8 !important;
            font-family: 'Orbitron', sans-serif; font-weight: bold; font-size: 13px;
            padding: 10px 18px; border-radius: 6px; border: 2px solid #1a73e8;
            text-decoration: none !important; box-shadow: 0 4px 15px rgba(26, 115, 232, 0.3);
            width: 100%; text-align: center; margin-top: 10px; transition: 0.3s;
        }
        .btn-google-maps:hover { background-color: #1a73e8 !important; color: white !important; }
        </style>
    """, unsafe_allow_html=True)

def renderizar_reloj_fluido():
    reloj_html = """
    <div style="background-color: rgba(10, 11, 15, 0.6); border: 1px solid #1A1C23; border-radius: 6px; padding: 12px; box-sizing: border-box;">
        <div style="color: #00E5FF; font-family: 'Rajdhani', sans-serif; font-size: 13px; font-weight: bold; text-transform: uppercase; letter-spacing: 0.5px;">
            HORA LOCAL
        </div>
        <div id="reloj-digital" style="color: #FFFFFF; font-family: 'Orbitron', sans-serif; font-size: 22px; font-weight: normal; margin-top: 4px;">--:--:--</div>
    </div>
    <script>
    function actualizarReloj() {
        const opciones = { timeZone: 'America/Argentina/Buenos_Aires', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false };
        const horaLocal = new Date().toLocaleTimeString('es-AR', opciones);
        const elemento = document.getElementById('reloj-digital');
        if (elemento) {
            elemento.innerText = horaLocal;
        }
    }
    setInterval(actualizarReloj, 1000);
    actualizarReloj();
    </script>
    """
    components.html(reloj_html, height=75)

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
            destinatarios_posibles = ["TODOS", "MONITOREO", "JEFE DE OPERACIONES", "GERENCIA", "SUPERVISORES", "VIGILADOR"] + obtener_lista_supervisores_dinamica()
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
                sincronizar_url_sesion()
                st.rerun()

    if 'mensaje_enviado' in st.session_state:
        if st.session_state.mensaje_enviado == "RESPUESTA":
            st.success("✅ RESPUESTA ENVIADA")
        else:
            st.success("✅ MENSAJE ENVIADO")
        del st.session_state.mensaje_enviado

    if not df_msg.empty:
        if 'ASUNTO' in df_msg.columns:
            for asunto, grupo in df_msg.groupby('ASUNTO'):
                with st.expander(f"💬 Hilo: {asunto}"):
                    for _, msg in grupo.iterrows():
                        st.markdown(f"**{msg.get('REMITENTE', 'ANÓNIMO')}:** {msg.get('MENSAJE', '')}")
                    if st.button(f"Responder a este hilo", key=f"btn_{asunto}_{rol_contexto}"):
                        st.session_state.asunto_respuesta = asunto
                        sincronizar_url_sesion()
                        st.rerun()

def enviar_alerta_automatica(emisor, objetivo, nombre_persona, supervisor_asignado):
    fecha = obtener_hora_argentina()
    mensaje = f"🚨 ALERTA DE PÁNICO: {nombre_persona} - OBJ: {objetivo}"
    destinatarios = ["JEFE DE OPERACIONES", "GERENCIA", supervisor_asignado]
    for dest in destinatarios:
        if dest and dest != "MONITOREO" and dest != "N/A":
            escribir_registro_nube("MENSAJERIA", [fecha, emisor, dest, mensaje, "PENDIENTE"])

def limpiar_matriz_nube(nombre_hoja):
    try:
        gc = conectar_google()
        if gc:
            worksheet = gc.open_by_key(ID_MAESTRO_DB).worksheet(nombre_hoja)
            worksheet.delete_rows(2, worksheet.row_count)
            st.cache_data.clear()
            return True
    except: return False

def ejecutar_cierre_táctico():
    matrices = ["JORNADA_SUPERVISORES", "REGISTRO_QR_SUPERVISORES", "ALERTAS", "NOVEDADES_GUARDIA", "CONTROL_FLOTA"]
    fecha_hoy = obtener_hora_argentina()
    mes_actual = fecha_hoy.split("-")[1] 
    try:
        gc = conectar_google()
        for mat in matrices:
            df = leer_matriz_nube(mat)
            if not df.empty:
                nombre_historico = f"{mat}_{mes_actual}"
                try:
                    hoja_hist = gc.open_by_key(ID_MAESTRO_DB).worksheet(nombre_historico)
                except:
                    hoja_hist = gc.open_by_key(ID_MAESTRO_DB).add_worksheet(title=nombre_historico, rows="100", cols="20")
                hoja_hist.clear()
                hoja_hist.update([df.columns.values.tolist()] + df.values.tolist())
                limpiar_matriz_nube(mat)
        st.cache_data.clear()
        return True
    except: return False

def mostrar_landing():
    aplicar_identidad_alfa()
    st.markdown('<div class="contenedor-logo-central"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" class="logo-phoenix"></div>', unsafe_allow_html=True)
    st.markdown('<div class="estacion-titulo">AION-YAROKU | COMMAND</div>', unsafe_allow_html=True)
    
    modo = st.radio("Acceso al Sistema:", ["Iniciar Sesión", "Crear Cuenta"], horizontal=True, key="radio_modo")
    
    with st.form("form_acceso_real"):
        user = st.text_input("Usuario o Apellido del Supervisor", key="u")
        password = st.text_input("Contraseña", type="password", key="p")
        roles_registro = ["VIGILADOR", "MONITOREO", "JEFE DE OPERACIONES", "GERENCIA", "SUPERVISOR"]
        rol_usuario = st.selectbox("Seleccione su Rol:", roles_registro, key="r")

        btn_texto = "ENTRAR" if modo == "Iniciar Sesión" else "REGISTRARSE"
        
        if st.form_submit_button(btn_texto):
            if modo == "Iniciar Sesión" and user.strip() == "admin" and password.strip() == "aion2026":
                st.session_state.usuario_logueado = True
                st.session_state.user_sel = "ADMIN CENTRAL"
                st.session_state.rol_sel = "ADMINISTRADOR"
                st.session_state.admin_autenticado = True
                sincronizar_url_sesion()
                st.rerun()
            elif modo == "Iniciar Sesión":
                df_usuarios = leer_matriz_nube("USUARIOS")
                usuario_ok = pd.DataFrame()
                if not df_usuarios.empty and 'USUARIO' in df_usuarios.columns and 'CONTRASEÑA' in df_usuarios.columns:
                    usuario_ok = df_usuarios[
                        (df_usuarios['USUARIO'].str.strip().str.upper() == user.strip().upper()) & 
                        (df_usuarios['CONTRASEÑA'].str.strip() == password.strip())
                    ]
                if not usuario_ok.empty:
                    estado = str(usuario_ok.iloc[0].get('ESTADO', 'PENDIENTE')).strip().upper()
                    if estado == "APROBADO":
                        st.session_state.usuario_logueado = True
                        st.session_state.user_sel = user.strip().upper()
                        st.session_state.rol_sel = usuario_ok.iloc[0]['ROL'].strip().upper()
                        if st.session_state.rol_sel == "SUPERVISOR":
                            st.session_state.sup_autenticado = True
                        sincronizar_url_sesion()
                        st.rerun()
                    else:
                        st.warning("⚠️ Tu cuenta existe pero está PENDIENTE de aprobación por el Administrador.")
                else:
                    st.error("❌ Credenciales inválidas o cuenta aún no aprobada.")
            else:
                if user.strip() and password.strip():
                    exito_reg = escribir_registro_nube("USUARIOS", [user.strip().upper(), password.strip(), rol_usuario, "PENDIENTE"])
                    if exito_reg:
                        st.success("✅ Solicitud de registro enviada con éxito. Inicie sesión una vez que el Administrador apruebe su cuenta.")
                    else:
                        st.error("❌ Error al registrar la cuenta en la nube.")
                else:
                    st.warning("⚠️ Complete el usuario y la contraseña.")

if not st.session_state.usuario_logueado:
    mostrar_landing()
    st.stop()

aplicar_identidad_alfa()

df_objetivos = cargar_objetivos()
df_comisarias = cargar_datos_comisarias()
LISTA_SUPS_TACTICOS = obtener_lista_supervisores_dinamica()

with st.sidebar:
    st.markdown('<div class="contenedor-logo-sidebar"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" style="width:180px; border:1px solid #00e5ff; border-radius:4px;"></div>', unsafe_allow_html=True)
    st.subheader("🛡️ PANEL DE CONTROL")
    
    if st.button("🛰️ MONITOREO", use_container_width=True):
        st.session_state.rol_sel = "MONITOREO"
        st.session_state.user_sel = "OPERADOR CENTRAL"
        st.session_state.sup_autenticado = False
        sincronizar_url_sesion()
        st.rerun()
        
    if st.button("📋 JEFE DE OPERACIONES", use_container_width=True):
        st.session_state.rol_sel = "JEFE DE OPERACIONES"
        st.session_state.user_sel = "JEFE DE OPERACIONES"
        st.session_state.sup_autenticado = False
        sincronizar_url_sesion()
        st.rerun()
        
    if st.button("🏢 GERENCIA", use_container_width=True):
        st.session_state.rol_sel = "GERENCIA"
        st.session_state.user_sel = "DIRECCIÓN GENERAL"
        st.session_state.sup_autenticado = False
        sincronizar_url_sesion()
        st.rerun()

    with st.expander("👤 SUPERVISORES", expanded=(st.session_state.rol_sel == "SUPERVISOR" or 'intentando_sup' in st.session_state)):
        nom_sup = st.selectbox("RESPONSABLE ACTIVO:", LISTA_SUPS_TACTICOS, key="cambio_supervisor_directo")
        user_sup = st.text_input("USUARIO RECURSO (APELLIDO)", key="auth_user_sup")
        pass_sup = st.text_input("CONTRASEÑA CRÍTICA", type="password", key="auth_pass_sup")
        
        if st.button("AUTENTICAR E INGRESAR", use_container_width=True):
            st.session_state.intentando_sup = True
            if "NOCTURNO" in nom_sup: usuario_esperado = "nocturno"
            elif "AYALA" in nom_sup: usuario_esperado = "ayala"
            else: usuario_esperado = nom_sup.split(" ")[-1].lower()
            
            if user_sup.strip().lower() in [usuario_esperado, nom_sup.strip().lower()] or pass_sup == "1234":
                st.session_state.rol_sel = "SUPERVISOR"
                st.session_state.user_sel = nom_sup.strip().upper()
                st.session_state.sup_autenticado = True
                if 'intentando_sup' in st.session_state: del st.session_state.intentando_sup
                sincronizar_url_sesion()
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
        sincronizar_url_sesion()
        st.rerun()

    st.write("---")
    st.markdown("**⚙️ ADMINISTRADOR**")
    if st.button("ACCEDER AL NÚCLEO MAESTRO", use_container_width=True):
        st.session_state.usuario_logueado = True
        st.session_state.rol_sel = "ADMINISTRADOR"
        st.session_state.user_sel = "ADMIN CENTRAL"
        st.session_state.admin_autenticado = True
        st.session_state.sup_autenticado = False
        sincronizar_url_sesion()
        st.rerun()

    st.markdown("---")
    if st.button("🚪 CERRAR SESIÓN", use_container_width=True):
        st.session_state.usuario_logueado = False
        st.query_params.clear()
        st.rerun()

st.markdown('<div class="contenedor-logo-central"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" class="logo-phoenix"></div>', unsafe_allow_html=True)

titulos = {
    "MONITOREO": "🛰️ CENTRAL DE INTELIGENCIA OPERATIVA",
    "SUPERVISOR": f"📱 Estación de Control: {st.session_state.user_sel}",
    "VIGILADOR": "👮 TERMINAL OPERATIVO VIGILADORES",
    "JEFE DE OPERACIONES": "📋 COMANDO DE OPERACIONES TÁCTICAS",
    "GERENCIA": "🏢 DIRECCIÓN Y FISCALIZACIÓN GENERAL",
    "ADMINISTRADOR": "⚙️ NÚCLEO MAESTRO:AION-YAROKU"
}
st.markdown(f'<div class="estacion-titulo">{titulos.get(st.session_state.rol_sel, "SISTEMA TÁCTICO DE COMANDO")}</div>', unsafe_allow_html=True)


# =========================================================================
# ROL: MONITOREO
# =========================================================================
if st.session_state.rol_sel == "MONITOREO":
    col1, col2, col3, col4 = st.columns(4)
    
    df_emergencias = leer_matriz_nube("ALERTAS")
    df_objetivos = cargar_objetivos()
    
    if df_emergencias.empty:
        df_emergencias = pd.DataFrame(columns=['FECHA', 'USUARIO', 'TIPO', 'ESTADO', 'CARGA_UTIL', 'INFORME'])
    else:
        df_emergencias.columns = df_emergencias.columns.str.strip().str.upper()

    df_mapa_monitoreo = pd.DataFrame()
    if not df_objetivos.empty:
        df_objetivos.columns = df_objetivos.columns.str.strip().str.upper()
        if 'LATITUD' in df_objetivos.columns and 'LONGITUD' in df_objetivos.columns:
            df_mapa_monitoreo = df_objetivos.dropna(subset=['LATITUD', 'LONGITUD']).copy()

    lista_objetivos_en_panico = []
    if 'ESTADO' in df_emergencias.columns and 'CARGA_UTIL' in df_emergencias.columns:
        pendientes = df_emergencias[df_emergencias['ESTADO'].astype(str).str.upper() == 'PENDIENTE']
        sos_activos = len(pendientes)
        for _, row in pendientes.iterrows():
            carga = str(row['CARGA_UTIL'])
            if "OBJ:" in carga:
                try: 
                    lista_objetivos_en_panico.append(carga.split("OBJ:")[1].split("|")[0].strip().upper())
                except: pass
    else: 
        sos_activos = 0
    
    with col1.container():
        @st.fragment(run_every=10)
        def contar_panicos_monitoreo():
            df_alertas = leer_matriz_nube("ALERTAS")
            if not df_alertas.empty:
                df_alertas.columns = [str(c).strip().upper() for c in df_alertas.columns]
                total_sos = len(df_alertas[df_alertas['ESTADO'] == "PENDIENTE"])
                st.metric("🚨 S.O.S ACTIVOS", total_sos)
            else:
                st.metric("🚨 S.O.S ACTIVOS", "0")
        contar_panicos_monitoreo()

    col2.metric("📡 RED", "OPERATIVA")
    col3.metric("👤 OPERADOR", f"{st.session_state.user_sel}")
    
    with col4.container():
        renderizar_reloj_fluido()

    df_msg = leer_matriz_nube("MENSAJERIA")
    nombre_user = st.session_state.user_sel.upper()
    total_nuevos = 0
    if not df_msg.empty:
        mask = ((df_msg['DESTINATARIO'] == "TODOS") | 
                (df_msg['DESTINATARIO'] == "MONITOREO") | 
                (df_msg['DESTINATARIO'] == nombre_user)) & \
               (df_msg['ESTADO'] == "PENDIENTE")
        total_nuevos = len(df_msg[mask])

    label_msg = f"💬 MENSAJERÍA GLOBAL ({total_nuevos})" if total_nuevos > 0 else "💬 MENSAJERÍA GLOBAL"

    t_radar, t_mensajeria, t_vig, t_nov = st.tabs([
        "🚨 RADAR S.O.S", label_msg, "👥 PADRÓN VIGILADORES", "🔄 NOVEDADES Y FICHAJES"
    ]) 

    with t_radar:
        st.subheader("📡 RADAR GLOBAL DE OBJETIVOS")
        if st.button("🔄 ACTUALIZAR RADAR DE CONTROL", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        st.markdown('<div class="panel-novedad">', unsafe_allow_html=True)
        
        col_filt1, col_filt2 = st.columns(2)
        
        lista_sups_monitoreo = ["TODOS LOS SUPERVISORES"] + LISTA_SUPS_TACTICOS
        sup_filtro_mono = col_filt1.selectbox("🔍 FILTRAR POR SUPERVISOR:", lista_sups_monitoreo, key="filtro_sup_monitoreo")
        
        df_mapa_filtrado_sup = df_mapa_monitoreo.copy()
        if sup_filtro_mono != "TODOS LOS SUPERVISORES":
            if 'SUPERVISOR' in df_mapa_filtrado_sup.columns:
                df_mapa_filtrado_sup = df_mapa_filtrado_sup[df_mapa_filtrado_sup['SUPERVISOR'].astype(str).str.strip().str.upper() == sup_filtro_mono]
            else:
                st.warning("⚠️ La columna 'SUPERVISOR' no se encuentra en la solapa OBJETIVOS.")

        if sup_filtro_mono != "TODOS LOS SUPERVISORES" and not df_mapa_filtrado_sup.empty:
            df_jornadas_mon = leer_matriz_nube("REGISTRO_QR_SUPERVISORES")
            total_objs_sup = len(df_mapa_filtrado_sup['OBJETIVO'].unique())
            visitados_sup_count = 0
            
            if not df_jornadas_mon.empty:
                df_jornadas_mon.columns = [str(c).strip().upper() for c in df_jornadas_mon.columns]
                fecha_hoy_str = datetime.now(pytz.timezone('America/Argentina/Buenos_Aires')).strftime('%Y-%m-%d')
                
                col_fec_h = df_jornadas_mon.columns[0]
                col_obj_h = df_jornadas_mon.columns[1]
                col_acc_h = df_jornadas_mon.columns[2]
                col_sup_h = df_jornadas_mon.columns[3]
                
                df_j_sup_hoy = df_jornadas_mon[
                    (df_jornadas_mon[col_sup_h].astype(str).str.strip().str.upper() == sup_filtro_mono) & 
                    (df_jornadas_mon[col_fec_h].astype(str).str.contains(fecha_hoy_str)) &
                    (df_jornadas_mon[col_acc_h].astype(str).str.strip().str.upper() == 'INICIO')
                ]
                visitados_sup_count = len(df_j_sup_hoy[col_obj_h].unique())
            
            porcentaje_progreso = int((visitados_sup_count / total_objs_sup) * 100) if total_objs_sup > 0 else 0
            
            col_filt2.markdown(f"""
                <div style="background: rgba(0, 229, 255, 0.05); border: 1px solid rgba(0, 229, 255, 0.2); border-radius: 6px; padding: 8px 12px; margin-top: 5px; font-family: 'Rajdhani', sans-serif;">
                    <div style="display: flex; justify-content: space-between; font-size: 12px; color: #00E5FF; font-weight: bold; text-transform: uppercase;">
                        <span>📊 Cobertura Turno: {sup_filtro_mono}</span>
                        <span>{visitados_sup_count} / {total_objs_sup} Objetivos ({porcentaje_progreso}%)</span>
                    </div>
                    <div style="background: #1A1C23; border-radius: 3px; height: 6px; width: 100%; margin-top: 6px; overflow: hidden;">
                        <div style="background: #00E5FF; height: 100%; width: {porcentaje_progreso}%;"></div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
        else:
            col_filt2.info("Seleccione un supervisor específico para ver su métrica de cobertura.")

        col_sel1, col_sel2 = st.columns([2, 1])
        
        if "filtro_radar_valor" not in st.session_state:
            st.session_state["filtro_radar_valor"] = "MOSTRAR TODO"

        with col_sel1:
            opciones_busqueda = ["MOSTRAR TODO"] + list(df_mapa_filtrado_sup['OBJETIVO'].unique()) if not df_mapa_filtrado_sup.empty else ["MOSTRAR TODO"]
            try:
                idx_defecto = opciones_busqueda.index(st.session_state["filtro_radar_valor"])
            except:
                idx_defecto = 0
                
            obj_seleccionado = st.selectbox(
                "🎯 ENFOCAR OBJETIVO EN RADAR / BUSCADOR:", 
                opciones_busqueda, 
                index=idx_defecto,
                key="buscador_radar_master"
            )
            st.session_state["filtro_radar_valor"] = obj_seleccionado
        
        comisaria_cercana_name = None
        distancia_minima = float('inf')
        com_lat_m, com_lon_m = None, None
        lat_obj, lon_obj = 0.0, 0.0
        
        if obj_seleccionado != "MOSTRAR TODO" and not df_mapa_filtrado_sup.empty:
            datos_obj = df_mapa_filtrado_sup[df_mapa_filtrado_sup['OBJETIVO'] == obj_seleccionado].iloc[0]
            lat_obj = datos_obj['LATITUD']
            lon_obj = datos_obj['LONGITUD']
            
            for _, com in df_comisarias.iterrows():
                lon1, lat1, lon2, lat2 = map(math.radians, [lon_obj, lat_obj, com['LONGITUD'], com['LATITUD']])
                dlon = lon2 - lon1
                dlat = lat2 - lat1
                a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
                c = 2 * math.asin(math.sqrt(a))
                km = 6371 * c
                
                if km < distancia_minima:
                    distancia_minima = km
                    comisaria_cercana_name = com['COMISARIA']
                    com_lat_m = com['LATITUD']
                    com_lon_m = com['LONGITUD']
            
            with col_sel2:
                st.metric(label="👮 COMISARÍA MÁS CERCANA", value=comisaria_cercana_name if comisaria_cercana_name else "N/A")
                st.caption(f"Distancia estimada: {distancia_minima:.2f} Km")
                
                if comisaria_cercana_name:
                    url_gmaps_monitoreo = f"https://www.google.com/maps/dir/?api=1&origin={com_lat_m},{com_lon_m}&destination={lat_obj},{lon_obj}&travelmode=driving"
                    st.markdown(
                        f'<a href="{url_gmaps_monitoreo}" target="_blank" class="btn-google-maps" style="font-size:11px; padding:6px 12px; margin-top:5px;">🗺️ ASISTENTE GPS COMPARTIDO</a>',
                        unsafe_allow_html=True
                    )
        else:
            with col_sel2:
                st.info("Seleccione un objetivo específico para calcular la comisaría más cercana.")
        st.markdown('</div>', unsafe_allow_html=True)

        if sos_activos > 0:
            st.markdown('<div class="panel-novedad" style="border: 1px solid #FF0000;">', unsafe_allow_html=True)
            df_pendientes_form = df_emergencias[df_emergencias['ESTADO'] == 'PENDIENTE']
            with st.form(key="form_finalizar_panico", clear_on_submit=True):
                opciones_alertas = {f"{r['FECHA']} - {r['USUARIO']}": idx for idx, r in df_pendientes_form.iterrows()}
                alerta_seleccionada = st.selectbox("SELECCIONE EVENTO A FINALIZAR:", list(opciones_alertas.keys()))
                txt_informe_cierre = st.text_area("INFORME OPERATIVO DE CIERRE:", placeholder="Describa la resolución...")
                if st.form_submit_button("🚨 FINALIZAR PÁNICO Y NORMALIZAR") and txt_informe_cierre.strip():
                    idx_df = opciones_alertas[alerta_seleccionada]
                    actualizar_celda("ALERTAS", idx_df + 2, "D", "FINALIZADO")
                    actualizar_celda("ALERTAS", idx_df + 2, "F", txt_informe_cierre.strip().upper())
                    st.session_state["filtro_radar_valor"] = "MOSTRAR TODO"
                    st.success("✅ Normalizado")
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
   
        st.markdown('<div class="radar-box">', unsafe_allow_html=True)
        if not df_mapa_filtrado_sup.empty:
            if obj_seleccionado != "MOSTRAR TODO":
                datos_obj = df_mapa_filtrado_sup[df_mapa_filtrado_sup['OBJETIVO'] == obj_seleccionado].iloc[0]
                centro_mapa = [datos_obj['LATITUD'], datos_obj['LONGITUD']]
                zoom_inicial = 13
            else:
                centro_mapa = [df_mapa_filtrado_sup['LATITUD'].mean(), df_mapa_filtrado_sup['LONGITUD'].mean()]
                zoom_inicial = 11

            m_mon = folium.Map(
                location=centro_mapa, 
                zoom_start=zoom_inicial, 
                max_zoom=21,
                tiles="https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}{r}.png",
                attr='© OpenStreetMap contributors © CARTO'
            )
            for _, r in df_mapa_filtrado_sup.iterrows():
                es_panico = r['OBJETIVO'] in lista_objetivos_en_panico
                es_el_seleccionado = (r['OBJETIVO'] == obj_seleccionado)
                
                texto_tooltip = f"🎯 {r['OBJETIVO']}"
                if es_panico:
                    alerta_activa = df_emergencias[
                        (df_emergencias['CARGA_UTIL'].str.contains(r['OBJETIVO'])) & 
                        (df_emergencias['ESTADO'] == 'PENDIENTE')
                    ]
                    if not alerta_activa.empty:
                        nombre_vigilante = alerta_activa.iloc[-1]['USUARIO']
                        texto_tooltip = f"🚨 {nombre_vigilante} | {r['OBJETIVO']}"

                if es_panico or es_el_seleccionado:
                    folium.Marker(
                        location=[r['LATITUD'], r['LONGITUD']],
                        tooltip=texto_tooltip,
                        icon=folium.DivIcon(
                            icon_size=(30, 30),
                            icon_anchor=(15, 15),
                            html='''<div style="background-color: #FF0000; width: 16px; height: 16px; border-radius: 50%; border: 2px solid white; animation: pulse 1s infinite alternate;"></div>'''
                        )
                    ).add_to(m_mon)
                else:
                    folium.CircleMarker(
                        location=[r['LATITUD'], r['LONGITUD']], radius=7, color="#00E5FF", fill=True,
                        tooltip=f"🎯 {r['OBJETIVO']} | 👤 SUP: {r.get('SUPERVISOR', 'N/A')}"
                    ).add_to(m_mon)

            df_com = cargar_datos_comisarias()
            for _, c in df_com.iterrows():
                es_la_mas_cercana = (c['COMISARIA'] == comisaria_cercana_name)
                if es_la_mas_cercana and obj_seleccionado != "MOSTRAR TODO":
                    color_icono = "#FF9800"
                    tamano_fuente = "26px"
                    sufijo_tooltip = " 🌟 [MÁS CERCANA AL OBJETIVO]"
                    com_lat, com_lon = c['LATITUD'], c['LONGITUD']
                    coordenadas_ruta = obtener_ruta_calles_osrm(lat_obj, lon_obj, com_lat, com_lon)
                    
                    if len(coordenadas_ruta) <= 2:
                        coordenadas_ruta = [[lat_obj, lon_obj], [com_lat, com_lon]]

                    folium.PolyLine(locations=coordenadas_ruta, color="#000000", weight=5, opacity=0.4).add_to(m_mon)
                    folium.PolyLine(locations=coordenadas_ruta, color="#39FF14", weight=4, opacity=0.8).add_to(m_mon)
                else:
                    color_icono = "#0000FF"
                    tamano_fuente = "20px"
                    sufijo_tooltip = ""

                folium.Marker(
                    location=[c['LATITUD'], c['LONGITUD']],
                    tooltip=f"👮 {c['COMISARIA']}{sufijo_tooltip}",
                    icon=folium.DivIcon(html=f"""<div style="font-size: {tamano_fuente}; color: {color_icono}; text-shadow: 0 0 10px {color_icono};"><i class="fa fa-shield"></i></div>""")
                ).add_to(m_mon)
            
            capa_etiquetas = folium.TileLayer(
                tiles="https://{s}.basemaps.cartocdn.com/dark_only_labels/{z}/{x}/{y}{r}.png",
                attr='© CARTO', name="Etiquetas", max_zoom=21, max_native_zoom=20, overlay=True, control=False
            )
            capa_etiquetas.add_to(m_mon)
            
            st_folium(m_mon, use_container_width=True, height=500, key="mapa_monitoreo_radar_tactico")
        st.markdown('</div>', unsafe_allow_html=True)

    with t_mensajeria:
        renderizar_mensajeria_global("MONITOREO")
    with t_vig:
        st.subheader("👥 PADRÓN VIGILADORES")
        df_padrero = leer_matriz_nube("VIGILADORES")
        if not df_padrero.empty:
            df_padrero.columns = df_padrero.columns.str.strip().str.upper()
            st.dataframe(df_padrero.iloc[::-1], use_container_width=True)
        else:
            st.info("No hay datos en la pestaña de relevos (Vigiladores).")
            
    with t_nov:
        st.subheader("🔄 CENTRO DE REGISTROS Y NOVEDADES (SEPARADO POR CUADROS)")
        
        sub_c_qr, sub_c_rel, sub_c_pan = st.tabs(["📱 QR Superiores", "🔄 Relevos de Vigiladores", "🚨 Alertas y Pánicos"])
        
        with sub_c_qr:
            st.markdown("#### 📱 Historial de Fichajes y Escaneos QR (Supervisores)")
            df_qr_neto = leer_matriz_nube("REGISTRO_QR_SUPERVISORES")
            if not df_qr_neto.empty:
                df_qr_neto.columns = [str(c).strip().upper() for c in df_qr_neto.columns]
                st.dataframe(df_qr_neto.iloc[::-1], use_container_width=True, hide_index=True)
                pdf_qr_mono = generar_pdf_reporte("REPORTE OPERATIVO - ESCANEOS QR DE SUPERVISORES", df_qr_neto)
                st.download_button("📥 DESCARGAR REPORTE QR (PDF)", data=pdf_qr_mono, file_name="reporte_qr_supervisores.pdf", mime="application/pdf", key="dl_qr_mono")
            else:
                st.info("No hay registros QR de supervisores.")

        with sub_c_rel:
            st.markdown("#### 🔄 Historial de Relevos de Guardia (Vigiladores)")
            df_vig_rel = leer_matriz_nube("VIGILADORES")
            if not df_vig_rel.empty:
                df_vig_rel.columns = [str(c).strip().upper() for c in df_vig_rel.columns]
                st.dataframe(df_vig_rel.iloc[::-1], use_container_width=True, hide_index=True)
                pdf_rel_mono = generar_pdf_reporte("REPORTE OPERATIVO - RELEVOS DE VIGILADORES", df_vig_rel)
                st.download_button("📥 DESCARGAR REPORTE DE RELEVOS (PDF)", data=pdf_rel_mono, file_name="reporte_relevos_vigiladores.pdf", mime="application/pdf", key="dl_rel_mono")
            else:
                st.info("No hay relevos de guardia registrados.")

        with sub_c_pan:
            st.markdown("#### 🚨 Historial de Alertas / Pánicos Activos e Históricos")
            df_alertas_mon = leer_matriz_nube("ALERTAS")
            if not df_alertas_mon.empty:
                df_alertas_mon.columns = [str(c).strip().upper() for c in df_alertas_mon.columns]
                st.dataframe(df_alertas_mon.iloc[::-1], use_container_width=True, hide_index=True)
                pdf_pan_mono = generar_pdf_reporte("REPORTE OPERATIVO - ALERTAS Y PÁNICOS", df_alertas_mon)
                st.download_button("📥 DESCARGAR REPORTE DE PÁNICOS (PDF)", data=pdf_pan_mono, file_name="reporte_panicos.pdf", mime="application/pdf", key="dl_pan_mono")
            else:
                st.info("No hay alertas registradas.")


# =========================================================================
# ROL: SUPERVISOR
# =========================================================================
elif st.session_state.rol_sel == "SUPERVISOR":
    if st.session_state.sup_autenticado:
        sup_activo_normalizado = st.session_state.user_sel.strip().upper()
        
        if not df_objetivos.empty and 'SUPERVISOR' in df_objetivos.columns:
            df_objetivos_filtrados = df_objetivos[
                df_objetivos['SUPERVISOR'].astype(str).str.strip().str.upper() == sup_activo_normalizado
            ].copy()
        else:
            df_objetivos_filtrados = pd.DataFrame()
        
        obj_actual = st.session_state.get("obj_qr_tactico", "SIN OBJETIVO")

        st.subheader("⏱️ GESTIÓN DE JORNADA")
        _, col_j1, col_j2, _ = st.columns([2, 3, 3, 2]) 
        with col_j1:
            if st.button("🚀 INICIO DE JORNADA", use_container_width=True):
                registrar_jornada_general(st.session_state.user_sel, obj_actual, "INICIO")
                st.success("Jornada iniciada")
        with col_j2:
            if st.button("🏁 CIERRE DE JORNADA", use_container_width=True):
                registrar_jornada_general(st.session_state.user_sel, obj_actual, "FIN")
                st.success("Jornada cerrada")

        st.markdown("<br>", unsafe_allow_html=True)
        
        st.markdown("### 🛡️ PROTOCOLO DE EMERGENCIA")
        if obj_actual != "SIN OBJETIVO":
            st.success(f"📍 OBJETIVO DETECTADO PARA PÁNICO: **{obj_actual}**")
        else:
            st.warning("⚠️ Selecciona tu objetivo en 'Visita QR' para activar el pánico correctamente.")

        col_p1, col_p2, col_p3 = st.columns([1, 1, 1])
        with col_p2:
            if st.button("S.O.S\nPÁNICO", type="primary"):
                lat_envio, lon_envio = 0.0, 0.0
                try:
                    loc = get_geolocation()
                    if loc and isinstance(loc, dict) and 'coords' in loc:
                        lat_envio = loc['coords'].get('latitude', 0.0)
                        lon_envio = loc['coords'].get('longitude', 0.0)
                except: pass
                
                carga_sos = f"SUP:{st.session_state.user_sel}|OBJ:{obj_actual}|LAT:{lat_envio}|LON:{lon_envio}"
                exito = escribir_registro_nube("ALERTAS", [
                    obtener_hora_argentina(), st.session_state.user_sel, "PÁNICO", "PENDIENTE", carga_sos
                ])
                if exito:
                    st.error(f"🚨 ALERTA ENVIADA DESDE {obj_actual}")

        t_vis_qr, t_nuevo_obj, t_ruta_gmaps, t_car_tac, t_mensajeria_sup, t_pres_sup = st.tabs([
            "Visita QR", "➕ CARGAR OBJETIVO", "📲 RUTA GOOGLE MAPS", "Carga Táctica", "💬 MENSAJERÍA", "📋 NOVEDADES Y RELEVOS"
        ])
        
        with t_vis_qr:
            fecha_hoy_str = datetime.now(pytz.timezone('America/Argentina/Buenos_Aires')).strftime('%Y-%m-%d')
            st.markdown(f"### 📊 ESTADO DE MIS OBJETIVOS ASIGNADOS ({fecha_hoy_str})")

            if not df_objetivos_filtrados.empty:
                lista_tabla_objs = []
                df_jornadas_act = leer_matriz_nube("REGISTRO_QR_SUPERVISORES")
                
                total_asignados = len(df_objetivos_filtrados['OBJETIVO'].unique())
                visitados_count = 0
                
                for obj_item in df_objetivos_filtrados['OBJETIVO'].unique():
                    estado_txt = "⏳ PENDIENTE DE VISITA"
                    ingreso_txt = "---"
                    egreso_txt = "---"
                    permanencia_txt = "---"
                    
                    if not df_jornadas_act.empty:
                        df_jornadas_act.columns = [str(c).strip().upper() for c in df_jornadas_act.columns]
                        
                        col_fec_hora = df_jornadas_act.columns[0]
                        col_obj = df_jornadas_act.columns[1]
                        col_acc = df_jornadas_act.columns[2]
                        col_sup = df_jornadas_act.columns[3]
                        
                        df_j_obj = df_jornadas_act[
                            (df_jornadas_act[col_sup].astype(str).str.strip().str.upper() == sup_activo_normalizado) & 
                            (df_jornadas_act[col_obj].astype(str).str.strip().str.upper() == obj_item.strip().upper()) &
                            (df_jornadas_act[col_fec_hora].astype(str).str.contains(fecha_hoy_str))
                        ]
                        
                        if not df_j_obj.empty:
                            inicios = df_j_obj[df_j_obj[col_acc].astype(str).str.strip().str.upper() == 'INICIO']
                            fines = df_j_obj[df_j_obj[col_acc].astype(str).str.strip().str.upper() == 'FIN']
                            
                            hora_ingreso_dt = None
                            hora_egreso_dt = None
                            
                            if not inicios.empty:
                                val_fh_ing = str(inicios.iloc[-1][col_fec_hora])
                                ingreso_txt = val_fh_ing.split(" ")[1] if " " in val_fh_ing else val_fh_ing
                                estado_txt = "✅ EN OBJETIVO / VISITADO"
                                visitados_count += 1
                                try:
                                    hora_ingreso_dt = datetime.strptime(ingreso_txt, "%H:%M:%S")
                                except: pass

                            if not fines.empty:
                                val_fh_fin = str(fines.iloc[-1][col_fec_hora])
                                egreso_txt = val_fh_fin.split(" ")[1] if " " in val_fh_fin else val_fh_fin
                                estado_txt = "🏁 EGRESO REGISTRADO"
                                try:
                                    hora_egreso_dt = datetime.strptime(egreso_txt, "%H:%M:%S")
                                except: pass

                            if hora_ingreso_dt and hora_egreso_dt:
                                if hora_egreso_dt >= hora_ingreso_dt:
                                    diff = hora_egreso_dt - hora_ingreso_dt
                                    minutos_totales = int(diff.total_seconds() // 60)
                                    horas = minutos_totales // 60
                                    mins = minutos_totales % 60
                                    permanencia_txt = f"{horas}h {mins}m" if horas > 0 else f"{mins} min"
                                else:
                                    permanencia_txt = "---"
                            
                    lista_tabla_objs.append({
                        "OBJETIVO": obj_item,
                        "ESTADO": estado_txt,
                        "INGRESO": ingreso_txt,
                        "EGRESO": egreso_txt,
                        "PERMANENCIA": permanencia_txt
                    })
                
                pendientes_count = total_asignados - visitados_count
                c_m1, c_m2, c_m3 = st.columns(3)
                c_m1.metric("📌 TOTAL OBJETIVOS", total_asignados)
                c_m2.metric("✅ VISITADOS", visitados_count)
                c_m3.metric("⏳ PENDIENTES", pendientes_count)

                df_tabla_estado = pd.DataFrame(lista_tabla_objs)
                st.dataframe(df_tabla_estado, use_container_width=True, hide_index=True)
            else:
                st.info("Sin objetivos asignados actualmente. Podés dar de alta un objetivo nuevo desde la solapa 'CARGAR OBJETIVO'.")

            st.markdown("---")
            st.markdown("### 📱 CENTRO TÁCTICO & GENERADOR QR DE OBJETIVOS")
            if not df_objetivos_filtrados.empty:
                obj_select = st.selectbox("Seleccione su Objetivo Asignado:", df_objetivos_filtrados['OBJETIVO'].unique(), key="obj_qr_tactico")
                datos_sel = df_objetivos_filtrados[df_objetivos_filtrados['OBJETIVO'] == obj_select].iloc[0]
                
                st.markdown("---")
                
                st.markdown("### 📷 ESCANEO TÁCTICO DE PUESTO (VALIDACIÓN EN TIEMPO REAL)")
                st.info("Alinee el código QR dentro del visor.")
                
                tipo_mov_qr = st.radio("TIPO DE MOVIMIENTO QR:", ["INICIO (INGRESO)", "FIN (EGRESO)"], horizontal=True, key="radio_tipo_mov_qr")
                accion_str = "INICIO" if "INICIO" in tipo_mov_qr else "FIN"

                st.markdown("""
                    <div style="border: 1px solid #00E5FF; border-radius: 6px; padding: 6px; text-align: center; margin: 2px 0; background: rgba(0, 229, 255, 0.05);">
                        <span style="font-family: 'Orbitron', sans-serif; color: #00E5FF; font-size: 12px; font-weight: bold;">🚨 ESCANER TÁCTICO DE ALTA VELOCIDAD</span><br>
                        <span style="font-family: 'Rajdhani', sans-serif; color: #A0A5B5; font-size: 10px;">Acerque el código QR para lectura instantánea.</span>
                    </div>
                """, unsafe_allow_html=True)

                st.markdown('<div class="qr-scanner-container">', unsafe_allow_html=True)
                codigo_qr_leido = qrcode_scanner(key=f"scanner_tactico_{accion_str}")
                st.markdown('</div>', unsafe_allow_html=True)

                if st.session_state.ultimo_mensaje_qr:
                    st.success(st.session_state.ultimo_mensaje_qr)

                if codigo_qr_leido is not None and str(codigo_qr_leido).strip() != "":
                    clave_registro_actual = f"{codigo_qr_leido}_{accion_str}"
                    
                    if st.session_state.get("ultimo_qr_procesado") != clave_registro_actual:
                        st.session_state.ultimo_qr_procesado = clave_registro_actual
                        try:
                            exito_registro = registrar_qr_supervisor(st.session_state.user_sel, obj_select, accion_str)
                            if exito_registro:
                                try:
                                    escribir_registro_nube("NOVEDADES_GUARDIA", [obtener_hora_argentina(), obj_select, f"SUPERVISIÓN QR VALIDADA ({accion_str})", "---", st.session_state.user_sel, "---", "PROCESADO", st.session_state.user_sel])
                                except:
                                    pass
                                
                                if accion_str == "INICIO":
                                    st.session_state.ultimo_mensaje_qr = f"✅ ¡INGRESO (INICIO) REGISTRADO CORRECTAMENTE PARA EL OBJETIVO: {obj_select}!"
                                else:
                                    st.session_state.ultimo_mensaje_qr = f"🏁 ¡EGRESO (FIN) REGISTRADO CORRECTAMENTE PARA EL OBJETIVO: {obj_select}!"
                                
                                sincronizar_url_sesion()
                                st.rerun()
                            else:
                                st.error("❌ Error al registrar en la nube. Intente nuevamente.")
                        except Exception as e:
                            st.warning(f"⚠️ Nota de sistema: {e}")

                st.markdown("---")
                
                col_qr1, col_qr2 = st.columns([1, 2])
                with col_qr1:
                    qr_data_string = f"AION-YAROKU-OBJ:{obj_select}|ID:{datos_sel.get('ID', '0')}"
                    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=2)
                    qr.add_data(qr_data_string)
                    qr.make(fit=True)
                    img_qr = qr.make_image(fill_color="#00E5FF", back_color="#000000")
                    
                    buffered = io.BytesIO()
                    img_qr.save(buffered, format="PNG")
                    st.image(buffered.getvalue(), width=160, caption=f"QR Oficial: {obj_select}")

                with col_qr2:
                    st.markdown("#### DATOS CLAVE DEL OBJETIVO")
                    st.write(f"**Dirección:** {datos_sel.get('DIRECCION', 'N/A')}")
                    st.write(f"**Localidad:** {datos_sel.get('LOCALIDAD', 'N/A')}")
                    st.write(f"**Coordenadas:** {datos_sel.get('LATITUD', 0)}, {datos_sel.get('LONGITUD', 0)}")
                    
                    lat = datos_sel.get('LATITUD', 0)
                    lon = datos_sel.get('LONGITUD', 0)
                    url_navegacion = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lon}&destination_place_name={obj_select}&travelmode=driving"
                    st.markdown(f'''
                        <a href="{url_navegacion}" target="_blank" class="btn-google-maps" style="margin-top:10px;">
                        📍 ABRIR NAVEGACIÓN GPS A {obj_select}
                        </a>
                    ''', unsafe_allow_html=True)
                
                st.markdown("---")
                st.markdown("### 📝 REGISTRO DE ACTA DE FLOTA")
                with st.form(key="form_acta_flota", clear_on_submit=True):
                    c_a, c_b = st.columns(2)
                    v_patente = c_a.text_input("PATENTE/MÓVIL:").upper()
                    v_km_ini = c_a.number_input("KM INICIAL:", min_value=0)
                    v_km_fin = c_b.number_input("KM FINAL:", min_value=0)
                    v_comb = c_b.selectbox("COMBUSTIBLE:", ["NO", "SI - MEDIA CARGA", "SI - TANQUE LLENO"])
                    v_vig = st.text_input("SUPERVISOR RESPONSABLE:", value=st.session_state.user_sel).upper()
                    if st.form_submit_button("REGISTRAR ACTA DE FLOTA"):
                        escribir_registro_nube("CONTROL_FLOTA", [obtener_hora_argentina(), v_vig, v_patente, v_km_ini, v_km_fin, v_comb])
                        st.success(f"✅ Acta registrada. Distancia recorrida: {v_km_fin - v_km_ini} km")
            else:
                st.warning("⚠️ No se encontraron objetivos asignados a su usuario Supervisor.")

        with t_nuevo_obj:
            st.markdown("### ➕ AUTOGESTIÓN Y BAJA DE OBJETIVOS TÁCTICOS")
            tab_alta_sup, tab_baja_sup = st.tabs(["🚀 DAR DE ALTA", "🗑️ SOLICITAR BAJA"])
            
            with tab_alta_sup:
                with st.form(key="form_crear_objetivo_supervisor", clear_on_submit=True):
                    col_no1, col_no2 = st.columns(2)
                    nuevo_nombre_obj = col_no1.text_input("NOMBRE DEL OBJETIVO:").upper().strip()
                    nueva_direccion = col_no2.text_input("DIRECCIÓN:").upper().strip()
                    
                    col_loc1, col_loc2 = st.columns(2)
                    nueva_localidad = col_loc1.text_input("LOCALIDAD:").upper().strip()
                    nueva_lat = col_loc2.text_input("LATITUD (Ej: -34.662580):")
                    
                    col_lon1, col_lon2 = st.columns(2)
                    nueva_lon = col_lon1.text_input("LONGITUD (Ej: -58.367150):")
                    nuevos_responsables = col_lon2.text_input("RESPONSABLES:").upper().strip()
                    
                    supervisor_asignado_actual = st.session_state.user_sel.upper()
                    if st.form_submit_button("🚀 DAR DE ALTA OBJETIVO EN LA RED"):
                        if nuevo_nombre_obj and nueva_lat and nueva_lon:
                            datos_nuevo_obj = [nuevo_nombre_obj, nueva_direccion, nueva_localidad, supervisor_asignado_actual, nueva_lat, nueva_lon, nuevos_responsables]
                            exito_alta = escribir_registro_nube("OBJETIVOS", datos_nuevo_obj)
                            if exito_alta:
                                st.success(f"✅ ¡Objetivo '{nuevo_nombre_obj}' creado con éxito!")
                                st.rerun()
                            else:
                                st.error("❌ Error al escribir en la nube.")

            with tab_baja_sup:
                if not df_objetivos_filtrados.empty:
                    with st.form(key="form_baja_objetivo_supervisor", clear_on_submit=True):
                        obj_a_baja = st.selectbox("SELECCIONE OBJETIVO A DAR DE BAJA:", df_objetivos_filtrados['OBJETIVO'].unique())
                        motivo_baja = st.text_input("MOTIVO DE LA BAJA:")
                        if st.form_submit_button("🗑️ SOLICITAR BAJA DE OBJETIVO"):
                            escribir_registro_nube("PETICIONES", [obtener_hora_argentina(), st.session_state.user_sel, "BAJA", "OBJETIVO", f"{obj_a_baja} - MOTIVO: {motivo_baja}"])
                            st.success(f"✅ Petición de baja enviada para '{obj_a_baja}'.")

        with t_ruta_gmaps:
            st.markdown("### 🗺️ NAVEGACIÓN TÁCTICA A COMISARÍAS")
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
                escribir_registro_nube("NOVEDADES_GUARDIA", [obtener_hora_argentina(), obj_actual, "NOVEDAD OPERATIVA", novedad_sup.strip().upper(), st.session_state.user_sel, "---", "PROCESADO", st.session_state.user_sel])
                st.success("✅ Cargado correctamente")

        with t_mensajeria_sup:
            renderizar_mensajeria_global("SUPERVISOR")
        
        with t_pres_sup:
            st.markdown(f"#### 📱 MIS ESCANEOS QR REGISTRADOS EN CAMPO")
            df_qr_sup_base = leer_matriz_nube("REGISTRO_QR_SUPERVISORES")
            if not df_qr_sup_base.empty:
                df_qr_sup_base.columns = [str(c).strip().upper() for c in df_qr_sup_base.columns]
                col_sup_q = 'SUPERVISOR' if 'SUPERVISOR' in df_qr_sup_base.columns else df_qr_sup_base.columns[3]
                df_qr_sup_propio = df_qr_sup_base[df_qr_sup_base[col_sup_q].astype(str).str.strip().str.upper() == sup_activo_normalizado]
                if not df_qr_sup_propio.empty:
                    st.dataframe(df_qr_sup_propio.iloc[::-1], use_container_width=True, hide_index=True)
                    pdf_qr_sup_dl = generar_pdf_reporte(f"MIS ESCANEOS QR - SUPERVISOR: {sup_activo_normalizado}", df_qr_sup_propio)
                    st.download_button("📥 DESCARGAR MIS ESCANEOS QR (PDF)", data=pdf_qr_sup_dl, file_name=f"mis_escaneos_qr_{sup_activo_normalizado}.pdf", mime="application/pdf", key="dl_qr_sup")
                else:
                    st.info("No tienes escaneos QR registrados en este turno.")
            else:
                st.info("Sin registros QR en el sistema.")

            st.markdown("---")
            st.markdown(f"#### 🔄 RELEVO DE GUARDIA Y ASISTENCIA EN TUS OBJETIVOS")
            lista_objs_supervisor = df_objetivos_filtrados['OBJETIVO'].tolist() if not df_objetivos_filtrados.empty else []

            df_vig_rel_sup = leer_matriz_nube("VIGILADORES")
            if not df_vig_rel_sup.empty and len(lista_objs_supervisor) > 0:
                df_vig_rel_sup.columns = [str(c).strip().upper() for c in df_vig_rel_sup.columns]
                col_obj_v = 'OBJETIVO' if 'OBJETIVO' in df_vig_rel_sup.columns else df_vig_rel_sup.columns[2]
                df_vig_rel_sup_filtrado = df_vig_rel_sup[df_vig_rel_sup[col_obj_v].astype(str).str.strip().str.upper().isin([o.upper() for o in lista_objs_supervisor])]
                
                if not df_vig_rel_sup_filtrado.empty:
                    st.dataframe(df_vig_rel_sup_filtrado.iloc[::-1], use_container_width=True, hide_index=True)
                    pdf_rel_sup_dl = generar_pdf_reporte(f"RELEVOS DE VIGILADORES - {sup_activo_normalizado}", df_vig_rel_sup_filtrado)
                    st.download_button("📥 DESCARGAR RELEVOS DE VIGILADORES (PDF)", data=pdf_rel_sup_dl, file_name=f"relevos_vigiladores_{sup_activo_normalizado}.pdf", mime="application/pdf", key="dl_rel_sup")
                else:
                    st.info("No hay relevos registrados en tus objetivos asignados.")
            else:
                st.info("No tienes objetivos asignados o no hay relevos en la base.")

            st.markdown("---")
            st.markdown("#### 🚨 ALERTAS DE PÁNICO DE TUS OBJETIVOS")
            df_pan_sup = leer_matriz_nube("ALERTAS")
            if not df_pan_sup.empty and len(lista_objs_supervisor) > 0:
                df_pan_sup.columns = [str(c).strip().upper() for c in df_pan_sup.columns]
                mask_objs = df_pan_sup['CARGA_UTIL'].apply(lambda x: any(obj.upper() in str(x).upper() for obj in lista_objs_supervisor))
                df_pan_sup_filtro = df_pan_sup[mask_objs | (df_pan_sup['CARGA_UTIL'].str.contains(sup_activo_normalizado, na=False))]
                
                if not df_pan_sup_filtro.empty:
                    st.dataframe(df_pan_sup_filtro.iloc[::-1], use_container_width=True, hide_index=True)
                    pdf_pan_sup_dl = generar_pdf_reporte(f"ALERTAS DE PÁNICO - {sup_activo_normalizado}", df_pan_sup_filtro)
                    st.download_button("📥 DESCARGAR ALERTAS DE PÁNICO (PDF)", data=pdf_pan_sup_dl, file_name=f"alertas_panico_{sup_activo_normalizado}.pdf", mime="application/pdf", key="dl_pan_sup")
                else:
                    st.info("Sin alertas de pánico en tus objetivos.")
            else:
                st.info("Sin alertas de pánico registradas.")
    else:
        st.warning("⚠️ Autentíquese con sus credenciales de supervisor en la barra lateral.")


# =========================================================================
# ROL: VIGILADOR
# =========================================================================
elif st.session_state.rol_sel == "VIGILADOR":
    st.markdown('<div class="panel-novedad">', unsafe_allow_html=True)
    opciones_globales_obj = df_objetivos['OBJETIVO'].unique() if not df_objetivos.empty else ["ALFAVINIL"]
    
    df_msg = leer_matriz_nube("MENSAJERIA")
    nombre_user = st.session_state.user_sel.upper()
    total_nuevos = 0
    if not df_msg.empty:
        mask = ((df_msg['DESTINATARIO'] == "TODOS") | (df_msg['DESTINATARIO'] == "VIGILADOR") | (df_msg['DESTINATARIO'] == nombre_user)) & (df_msg['ESTADO'] == "PENDIENTE")
        total_nuevos = len(df_msg[mask])

    label_msg = f"💬 MENSAJERÍA GLOBAL ({total_nuevos})" if total_nuevos > 0 else "💬 MENSAJERÍA GLOBAL"
    
    st.markdown("### 🛡️ PROTOCOLO DE EMERGENCIA")
    obj_detectado = st.session_state.get("obj_actual_vig", None)

    if obj_detectado:
        st.success(f"📍 OBJETIVO DETECTADO PARA PÁNICO: **{obj_detectado}**")
        col_pv1, col_pv2, col_pv3 = st.columns([1, 1, 1])
        with col_pv2:
            if st.button("S.O.S\nPÁNICO", type="primary"):
                nombre_real = st.session_state.get("v_nombre_completo", "VIGILADOR").upper()
                sup_asignado = "MONITOREO"
                if not df_objetivos.empty:
                    filtro = df_objetivos[df_objetivos['OBJETIVO'] == obj_detectado]
                    if not filtro.empty:
                        sup_asignado = str(filtro['SUPERVISOR'].iloc[0]).strip()
                
                fecha = obtener_hora_argentina()
                carga_sos = f"VIG:{nombre_real}|OBJ:{obj_detectado}|SUP:{sup_asignado}"
                escribir_registro_nube("ALERTAS", [fecha, nombre_real, "PÁNICO", "PENDIENTE", carga_sos, "PRUEBA"])
                enviar_alerta_automatica("SISTEMA_VIGILADOR", obj_detectado, nombre_real, sup_asignado)
                st.error(f"🚨 ALERTA ENVIADA: {nombre_real} DESDE {obj_detectado}")
    else:
        st.warning("⚠️ Debes realizar el Fichaje o Relevo primero para activar el sistema de pánico.")
    
    st.markdown("---")
    
    tab_presentismo, tab_relevo, tab_mensajeria_vig = st.tabs(["📋 FICHAJE", "🔄 RELEVO", label_msg])
  
    with tab_presentismo:
        st.markdown("### 📸 REGISTRO BIOMÉTRICO")
        with st.form(key="form_fichaje_vigilador", clear_on_submit=True):
            v_nombre_completo = st.text_input("APELLIDO Y NOMBRE:").strip() 
            v_dni = st.text_input("LEGAJO:").strip() 
            v_obj = st.selectbox("OBJETIVO:", opciones_globales_obj)
            v_tipo_marcacion = st.selectbox("TIPO:", ["INGRESO", "EGRESO"])
            img_facial = st.camera_input("RECONOCIMIENTO FACIAL")
            
            if st.form_submit_button("CONSIGNAR Y TRANSMITIR"):
                if v_nombre_completo and v_dni and img_facial:
                    st.session_state.v_nombre_completo = v_nombre_completo.upper()
                    st.session_state.legajo_vigilador = v_dni
                    st.session_state.obj_actual_vig = v_obj
                    
                    fecha_hora_arg = obtener_hora_argentina()
                    sup_responsable = df_objetivos[df_objetivos['OBJETIVO'] == v_obj]['SUPERVISOR'].iloc[0] if not df_objetivos.empty else "N/A"
                    tipo_evento = f"MARCACIÓN_{v_tipo_marcacion}"
                    
                    escribir_registro_nube("PRESENTISMO", [fecha_hora_arg.split(" ")[0], fecha_hora_arg.split(" ")[1], v_dni, f"{v_nombre_completo.upper()} - {v_obj}", "", "OK", v_tipo_marcacion])
                    escribir_registro_nube("NOVEDADES_GUARDIA", [fecha_hora_arg, v_obj, tipo_evento, "---", v_nombre_completo.upper(), v_dni, "PROCESADO", sup_responsable])
                    st.success(f"🔒 {tipo_evento} REGISTRADA PARA {v_nombre_completo.upper()}")
                else:
                    st.error("⚠️ Por favor, complete todos los campos y capture la foto.")

    with tab_relevo:
        st.markdown("### 🔄 REGISTRO FORMAL DE CAMBIO")
        with st.form(key="form_relevo_vigilador_directo", clear_on_submit=True):
            v_obj_relevo = st.selectbox("OBJETIVO:", opciones_globales_obj, key="relevo_obj")
            vig_saliente = st.text_input("SALE:").upper().strip()
            vig_entrante = st.text_input("ENTRA:").upper().strip()
            v_dni_relevo = st.text_input("DNI RESPONSABLE:").strip()
            if st.form_submit_button("SANCIONAR CAMBIO"):
                st.session_state.obj_actual_vig = v_obj_relevo
                sup_resp = df_objetivos[df_objetivos['OBJETIVO']==v_obj_relevo]['SUPERVISOR'].iloc[0] if not df_objetivos.empty else "N/A"
                fecha = obtener_hora_argentina()
                escribir_registro_nube("NOVEDADES_GUARDIA", [fecha, v_obj_relevo, "RELEVO DE TURNO", vig_saliente, vig_entrante, v_dni_relevo, "PROCESADO", sup_resp])
                escribir_registro_nube("VIGILADORES", [fecha.split(" ")[0], fecha.split(" ")[1], v_obj_relevo, vig_saliente, vig_entrante, sup_resp, "RELEVO_EFECTUADO"])
                st.success("🔒 RELEVO REGISTRADO Y EXITOSO")

    with tab_mensajeria_vig:
        renderizar_mensajeria_global("VIGILADOR")
    st.markdown('</div>', unsafe_allow_html=True)


# =========================================================================
# ROL: JEFE DE OPERACIONES
# =========================================================================
elif st.session_state.rol_sel == "JEFE DE OPERACIONES":
    col1, col2, col3, col4 = st.columns(4)
    
    with col1.container():
        @st.fragment(run_every=5)
        def mostrar_sos():
            df_alertas = leer_matriz_nube("ALERTAS")
            total_sos = len(df_alertas[df_alertas['ESTADO'] == "PENDIENTE"]) if not df_alertas.empty else 0
            st.metric("🚨 S.O.S ACTIVOS", total_sos)
        mostrar_sos()

    col2.metric("📡 RED", "OPERATIVA")
    col3.metric("👤 USUARIO", f"{st.session_state.user_sel}")
    
    with col4.container():
        renderizar_reloj_fluido()

    df_msg = leer_matriz_nube("MENSAJERIA")
    nombre_user = st.session_state.user_sel.upper()
    total_nuevos = len(df_msg[((df_msg['DESTINATARIO'] == "TODOS") | 
                            (df_msg['DESTINATARIO'] == "JEFE DE OPERACIONES") | 
                            (df_msg['DESTINATARIO'] == nombre_user)) & 
                           (df_msg['ESTADO'] == "PENDIENTE")]) if not df_msg.empty else 0
    
    label_msg = f"💬 MENSAJERÍA ({total_nuevos})" if total_nuevos > 0 else "💬 MENSAJERÍA"
    
    st.markdown('<h2 style="color:#00E5FF; font-family:\'Orbitron\'; font-size:24px;">Comando: JEFE DE OPERACIONES</h2>', unsafe_allow_html=True)
    
    t_mensajeria_jefe, t_ejecucion, t_tab_auditoria = st.tabs([label_msg, "Ejecución", "📍 TABLERO DE AUDITORÍA"])
    
    with t_mensajeria_jefe:
        renderizar_mensajeria_global("JEFE DE OPERACIONES")
        
    with t_ejecucion:
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.subheader("ALTA DE RECURSO / OBJETIVO")
            g_alta_nom = st.text_input("Nombre:", key="jefe_alta_nom")
            g_alta_asig = st.selectbox("Asignar a:", LISTA_SUPS_TACTICOS, key="jefe_alta_asig")
            if st.button("Solicitar Alta"):
                escribir_registro_nube("PETICIONES", [obtener_hora_argentina(), st.session_state.user_sel, "ALTA", "OBJETIVO", f"{g_alta_nom} | ASIG: {g_alta_asig}"])
                st.success("✅ Petición enviada")
        with col_g2:
            st.subheader("BAJA DE OBJETIVO")
            g_baja_obj = st.selectbox("Objetivo:", df_objetivos['OBJETIVO'].unique() if not df_objetivos.empty else ["ALFAVINIL"], key="jefe_baja_obj")
            if st.button("Solicitar Baja"):
                escribir_registro_nube("PETICIONES", [obtener_hora_argentina(), st.session_state.user_sel, "BAJA", "OBJETIVO", g_baja_obj])
                st.success("✅ Petición enviada")
    
    with t_tab_auditoria:
        st.markdown("### 📋 AUDITORÍA DE SUPERVISIÓN Y DESCARGAS PDF")
        df_jornadas = leer_matriz_nube("JORNADA_SUPERVISORES")
        if not df_jornadas.empty:
            df_jornadas.columns = [str(c).strip().upper() for c in df_jornadas.columns]
            st.dataframe(df_jornadas, use_container_width=True, hide_index=True)
            pdf_jornadas = generar_pdf_reporte("REPORTE DE JORNADAS DE SUPERVISORES", df_jornadas)
            st.download_button("📥 DESCARGAR REPORTE DE JORNADAS (PDF)", data=pdf_jornadas, file_name="reporte_jornadas.pdf", mime="application/pdf", key="dl_jornadas_jefe")
        else:
            st.write("*(Sin jornadas registradas)*")

        st.markdown("---")
        st.markdown("### 📱 AUDITORÍA DE REGISTRO QR")
        df_qr_sup = leer_matriz_nube("REGISTRO_QR_SUPERVISORES")
        if not df_qr_sup.empty:
            df_qr_sup.columns = [str(c).strip().upper() for c in df_qr_sup.columns]
            st.dataframe(df_qr_sup, use_container_width=True, hide_index=True)
            pdf_qr = generar_pdf_reporte("REPORTE DE REGISTRO QR DE SUPERVISORES", df_qr_sup)
            st.download_button("📥 DESCARGAR REPORTE QR (PDF)", data=pdf_qr, file_name="reporte_qr_supervisores.pdf", mime="application/pdf", key="dl_qr_jefe")
        else:
            st.write("*(Sin registros QR)*")

        st.markdown("---")
        st.markdown("### 🚗 AUDITORÍA DE CONTROL DE FLOTA")
        df_flota = leer_matriz_nube("CONTROL_FLOTA")
        if not df_flota.empty:
            df_flota.columns = [str(c).strip().upper() for c in df_flota.columns]
            st.dataframe(df_flota, use_container_width=True, hide_index=True)
            pdf_flota = generar_pdf_reporte("REPORTE DE CONTROL DE FLOTA", df_flota)
            st.download_button("📥 DESCARGAR REPORTE DE FLOTA (PDF)", data=pdf_flota, file_name="reporte_flota.pdf", mime="application/pdf", key="dl_flota_jefe")
        else:
            st.write("*(Sin registros de flota)*")

        st.markdown("---")
        st.markdown("### 🚨 HISTÓRICO DE ALERTAS TÁCTICAS")
        df_alertas = leer_matriz_nube("ALERTAS")
        if not df_alertas.empty:
            df_alertas.columns = [str(c).strip().upper() for c in df_alertas.columns]
            st.dataframe(df_alertas[['FECHA', 'USUARIO', 'CARGA_UTIL', 'ESTADO']], use_container_width=True, hide_index=True)
            pdf_alertas = generar_pdf_reporte("REPORTE DE ALERTAS TÁCTICAS", df_alertas[['FECHA', 'USUARIO', 'CARGA_UTIL', 'ESTADO']])
            st.download_button("📥 DESCARGAR HISTÓRICO DE ALERTAS (PDF)", data=pdf_alertas, file_name="reporte_alertas.pdf", mime="application/pdf", key="dl_alertas_jefe")
        else:
            st.write("*(Sin alertas tácticas)*")


# =========================================================================
# ROL: GERENCIA
# =========================================================================
elif st.session_state.rol_sel == "GERENCIA":
    fecha_hoy = obtener_hora_argentina().split(" ")[0]
    df_jornada_actual = leer_matriz_nube("JORNADA_SUPERVISORES")
    
    if not df_jornada_actual.empty:
        df_jornada_actual.columns = [str(c).strip().upper() for c in df_jornada_actual.columns]
        df_hoy = df_jornada_actual[df_jornada_actual['FECHA'] == fecha_hoy]
        personal_activo = df_hoy['SUPERVISOR'].nunique()
        objs_cubiertos = len(df_hoy['OBJETIVO'].unique())
    else:
        personal_activo = 0
        objs_cubiertos = 0

    total_objetivos_db = len(df_objetivos) if not df_objetivos.empty else 1
    kpi_operativo = int((objs_cubiertos / total_objetivos_db) * 100) if total_objetivos_db > 0 else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📊 KPI OPERATIVO", f"{kpi_operativo}%")
    col2.metric("👥 PERSONAL ACTIVO", f"{personal_activo}")
    col3.metric("👤 GERENTE", f"{st.session_state.user_sel}")
    
    with col4.container():
        renderizar_reloj_fluido()
        
    st.write("---")
    st.markdown('<h2 style="color:#00E5FF; font-family:\'Orbitron\'; font-size:24px;">Comando: DIRECCIÓN GENERAL</h2>', unsafe_allow_html=True)
    
    t_mensajeria_ger, t_ejecucion_ger, t_tab_auditoria = st.tabs(["💬 MENSAJERÍA GLOBAL", "🎮 EJECUCIÓN", "📍 TABLERO DE AUDITORÍA"])
    
    with t_mensajeria_ger:
        renderizar_mensajeria_global("GERENCIA")
        
    with t_ejecucion_ger:
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.subheader("ALTA DE RECURSO")
            g_alta_nom = st.text_input("Nombre:", key="ger_alta_nom")
            g_alta_asig = st.selectbox("Asignar a:", LISTA_SUPS_TACTICOS, key="ger_alta_asig")
            if st.button("Solicitar Alta"):
                escribir_registro_nube("PETICIONES", [obtener_hora_argentina(), st.session_state.user_sel, "ALTA", "OBJETIVO", f"{g_alta_nom} | ASIG: {g_alta_asig}"])
                st.success("✅ Petición enviada")
        with col_g2:
            st.subheader("BAJA DE OBJETIVO")
            g_baja_obj = st.selectbox("Objetivo:", df_objetivos['OBJETIVO'].unique() if not df_objetivos.empty else ["ALFAVINIL"], key="ger_baja_obj")
            if st.button("Solicitar Baja"):
                escribir_registro_nube("PETICIONES", [obtener_hora_argentina(), st.session_state.user_sel, "BAJA", "OBJETIVO", g_baja_obj])
                st.success("✅ Petición enviada")

    with t_tab_auditoria:
        st.markdown("### 📋 TABLERO GERENCIAL Y DESCARGAS PDF")
        
        st.markdown("#### 📋 AUDITORÍA DE SUPERVISIÓN")
        df_jornadas = leer_matriz_nube("JORNADA_SUPERVISORES")
        if not df_jornadas.empty:
            df_jornadas.columns = [str(c).strip().upper() for c in df_jornadas.columns]
            st.dataframe(df_jornadas, use_container_width=True, hide_index=True)
            pdf_jornadas_ger = generar_pdf_reporte("REPORTE GERENCIAL DE JORNADAS", df_jornadas)
            st.download_button("📥 DESCARGAR REPORTE DE JORNADAS (PDF)", data=pdf_jornadas_ger, file_name="reporte_gerencial_jornadas.pdf", mime="application/pdf", key="dl_jornadas_ger")
        else:
            st.write("*(Sin jornadas registradas)*")

        st.markdown("---")
        st.markdown("#### 📱 AUDITORÍA DE REGISTRO CÓDIGO QR")
        df_qr_ger = leer_matriz_nube("REGISTRO_QR_SUPERVISORES")
        if not df_qr_ger.empty:
            df_qr_ger.columns = [str(c).strip().upper() for c in df_qr_ger.columns]
            st.dataframe(df_qr_ger, use_container_width=True, hide_index=True)
            pdf_qr_ger = generar_pdf_reporte("REPORTE GERENCIAL DE REGISTRO QR", df_qr_ger)
            st.download_button("📥 DESCARGAR REPORTE QR (PDF)", data=pdf_qr_ger, file_name="reporte_gerencial_qr.pdf", mime="application/pdf", key="dl_qr_ger")
        else:
            st.write("*(Sin registros QR)*")

        st.markdown("---")
        st.markdown("#### 🚗 AUDITORÍA DE CONTROL DE FLOTA")
        df_flota_ger = leer_matriz_nube("CONTROL_FLOTA")
        if not df_flota_ger.empty:
            df_flota_ger.columns = [str(c).strip().upper() for c in df_flota_ger.columns]
            st.dataframe(df_flota_ger, use_container_width=True, hide_index=True)
            pdf_flota_ger = generar_pdf_reporte("REPORTE GERENCIAL DE FLOTA", df_flota_ger)
            st.download_button("📥 DESCARGAR REPORTE DE FLOTA (PDF)", data=pdf_flota_ger, file_name="reporte_gerencial_flota.pdf", mime="application/pdf", key="dl_flota_ger")
        else:
            st.write("*(Sin registros de flota)*")

        st.markdown("---")
        st.markdown("#### 🚨 AUDITORÍA DE ALERTAS TÁCTICAS")
        df_alt_ger = leer_matriz_nube("ALERTAS")
        if not df_alt_ger.empty:
            df_alt_ger.columns = [str(c).strip().upper() for c in df_alt_ger.columns]
            st.dataframe(df_alt_ger[['FECHA', 'USUARIO', 'CARGA_UTIL', 'ESTADO']], use_container_width=True, hide_index=True)
            pdf_alt_ger = generar_pdf_reporte("REPORTE GERENCIAL DE ALERTAS TÁCTICAS", df_alt_ger[['FECHA', 'USUARIO', 'CARGA_UTIL', 'ESTADO']])
            st.download_button("📥 DESCARGAR HISTÓRICO DE ALERTAS (PDF)", data=pdf_alt_ger, file_name="reporte_gerencial_alertas.pdf", mime="application/pdf", key="dl_altas_ger")
        else:
            st.write("*(Sin alertas tácticas)*")

        st.markdown("---")
        st.markdown("### 🔒 PROTOCOLO DE CIERRE TÁCTICO MENSUAL")
        st.info("ℹ️ Esta acción archivará y limpiará las tablas operativas actuales para iniciar un nuevo ciclo.")
        if st.button("EJECUTAR CIERRE TÁCTICO MENSUAL"):
            if ejecutar_cierre_táctico():
                st.success("✅ ¡Cierre táctico ejecutado con éxito! Ciclo reiniciado.")
                st.rerun()
            else:
                st.error("❌ Error al ejecutar el cierre táctico.")


# =========================================================================
# ROL: ADMINISTRADOR
# =========================================================================
elif st.session_state.rol_sel == "ADMINISTRADOR":
    if st.session_state.user_sel == "ADMIN CENTRAL":
        st.session_state.admin_autenticado = True
    
    if st.session_state.admin_autenticado:
        st.markdown('<div class="panel-novedad">', unsafe_allow_html=True)
        st.markdown("### ⚙️ NÚCLEO MAESTRO: PANEL DE CONTROL DE ADMINISTRACIÓN")
        st.success("✅ Acceso autorizado al Núcleo Maestro Central.")

        df_usr_m = leer_matriz_nube("USUARIOS")
        df_obj_m = cargar_objetivos()
        df_alt_m = leer_matriz_nube("ALERTAS")
        
        total_usrs = len(df_usr_m) if not df_usr_m.empty else 0
        total_objs = len(df_obj_m) if not df_obj_m.empty else 0
        pend_sos = len(df_alt_m[df_alt_m['ESTADO'].astype(str).str.upper() == "PENDIENTE"]) if not df_alt_m.empty and 'ESTADO' in df_alt_m.columns else 0

        c_adm1, c_adm2, c_adm3 = st.columns(3)
        c_adm1.metric("👥 TOTAL USUARIOS", total_usrs)
        c_adm2.metric("🎯 OBJETIVOS ACTIVOS", total_objs)
        c_adm3.metric("🚨 ALERTAS PENDIENTES", pend_sos)

        st.markdown("---")

        t_adm_usr, t_adm_obj, t_adm_mantenimiento = st.tabs([
            "👥 APROBACIÓN DE USUARIOS", "🎯 GESTIÓN DE OBJETIVOS", "🛡️ RESPALDO Y ARCHIVO TÁCTICO"
        ])

        with t_adm_usr:
            st.markdown("#### 👤 SOLICITUDES DE ACCESO Y PADRÓN DE USUARIOS")
            if not df_usr_m.empty:
                st.dataframe(df_usr_m[['USUARIO', 'ROL', 'ESTADO']], use_container_width=True, hide_index=True)
                pdf_usuarios = generar_pdf_reporte("PADRÓN GENERAL DE USUARIOS Y ACCESOS", df_usr_m[['USUARIO', 'ROL', 'ESTADO']])
                st.download_button("📥 DESCARGAR PADRÓN DE USUARIOS (PDF)", data=pdf_usuarios, file_name=f"padron_usuarios_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf", mime="application/pdf", key="dl_pdf_usuarios_admin")
                
                st.markdown("---")
                if 'ESTADO' in df_usr_m.columns:
                    pendientes_u = df_usr_m[df_usr_m['ESTADO'] == "PENDIENTE"]
                    if not pendientes_u.empty:
                        usuario_a_aprobar = st.selectbox("Seleccionar usuario para autorizar:", pendientes_u['USUARIO'].tolist(), key="sel_usr_aprobar")
                        if st.button("✅ DAR ACCESO Y APROBAR USUARIO", use_container_width=True):
                            idx = df_usr_m[df_usr_m['USUARIO'] == usuario_a_aprobar].index[0]
                            if actualizar_celda("USUARIOS", idx + 2, "D", "APROBADO"):
                                st.success(f"✅ ¡Usuario {usuario_a_aprobar} autorizado correctamente!")
                                st.cache_data.clear()
                                st.rerun()

        with t_adm_obj:
            st.markdown("#### 📋 LISTADO GENERAL DE OBJETIVOS EN LA RED")
            if not df_obj_m.empty:
                st.dataframe(df_obj_m[['OBJETIVO', 'DIRECCION', 'LOCALIDAD', 'SUPERVISOR']], use_container_width=True, hide_index=True)
                pdf_objetivos = generar_pdf_reporte("PADRÓN GENERAL DE OBJETIVOS ACTIVOS", df_obj_m[['OBJETIVO', 'DIRECCION', 'LOCALIDAD', 'SUPERVISOR']])
                st.download_button("📥 DESCARGAR PADRÓN DE OBJETIVOS (PDF)", data=pdf_objetivos, file_name=f"padron_objetivos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf", mime="application/pdf", key="dl_pdf_objetivos_admin")

        with t_adm_mantenimiento:
            st.markdown("#### 🛡️ CENTRO DE RESPALDO Y CAJA FUERTE DIGITAL")
            if not df_obj_m.empty:
                pdf_respaldo_objs = generar_pdf_reporte("RESPALDO GENERAL DE OBJETIVOS ACTIVOS", df_obj_m[['OBJETIVO', 'DIRECCION', 'LOCALIDAD', 'SUPERVISOR']])
                st.download_button("📥 DESCARGAR RESPALDO DE OBJETIVOS (PDF)", data=pdf_respaldo_objs, file_name=f"respaldo_objetivos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf", mime="application/pdf", use_container_width=True, key="dl_pdf_mantenimiento_objetivos")

        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.error("⚠️ Acceso restringido.")
