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
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfgen import canvas
import streamlit.components.v1 as components
from streamlit_qrcode_scanner import qrcode_scanner


# --- 1. CLASE PARA NUMERACIÓN DE PÁGINAS EN PDF ---
class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super(NumberedCanvas, self).__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor('#666666'))
        texto_pag = f"Página {self._pageNumber} de {page_count}"
        self.drawRightString(792 - 24, 15, texto_pag)
        self.drawString(24, 15, "AION-YAROKU | SISTEMA TÁCTICO INTEGRAL")
        self.setStrokeColor(colors.HexColor('#CCCCCC'))
        self.setLineWidth(0.5)
        self.line(24, 25, 792 - 24, 25)
        self.restoreState()


# --- 2. CONFIGURACIÓN E INICIALIZACIÓN CON PERSISTENCIA POR URL ---

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


# --- 3. CONEXIONES Y FUNCIONES GLOBALES OPTIMIZADAS ---

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

def determinar_turno_activo(hora_str):
    try:
        if " " in str(hora_str):
            h_parte = hora_str.split(" ")[1]
        else:
            h_parte = str(hora_str)
        dt_h = datetime.strptime(h_parte[:8], "%H:%M:%S").time()
        if datetime.strptime("06:00:00", "%H:%M:%S").time() <= dt_h < datetime.strptime("18:00:00", "%H:%M:%S").time():
            return "DIURNO (06:00 - 18:00)"
        else:
            return "NOCTURNO (18:00 - 06:00)"
    except:
        return "DIURNO (06:00 - 18:00)"

def obtener_mapeo_solapas():
    return {
        "NOVEDADES GUARDIA": "NOVEDADES GUARDIA",
        "REGISTRO QR SUPERVISORES": "REGISTRO QR SUPERVISORES",
        "JORNADA SUPERVISORES": "JORNADA SUPERVISORES",
        "CONTROL DE FLOTA": "CONTROL DE FLOTA",
        "CONTROL FLOTA": "CONTROL DE FLOTA",
        "SOLICITUDES DE ACCESO": "SOLICITUDES ACCESO",
        "OBJETIVOS": "OBJETIVOS",
        "COMISARIAS": "COMISARIAS",
        "USUARIOS": "USUARIOS",
        "ALERTAS": "ALERTAS",
        "MENSAJERIA": "MENSAJERIA",
        "PRESENTISMO": "PRESENTISMO",
        "VIGILADORES": "VIGILADORES"
    }

def actualizar_celda(pestana, fila, columna, valor):
    try:
        gc = conectar_google()
        if gc:
            nombre_hoja_real = obtener_mapeo_solapas().get(pestana.upper().strip(), pestana)
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(nombre_hoja_real)
            hoja.update_acell(f"{columna}{fila}", valor)
            st.cache_data.clear()
            return True
    except Exception as e: 
        print(f"Error actualizando celda en {pestana}: {e}")
        return False

def escribir_registro_nube(pestana, datos_fila):
    try:
        gc = conectar_google()
        if gc:
            nombre_hoja_real = obtener_mapeo_solapas().get(pestana.upper().strip(), pestana)
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(nombre_hoja_real)
            hoja.append_row(datos_fila)
            st.cache_data.clear() 
            return True
    except Exception as e:
        print(f"Error de nube en {pestana}: {e}")
        st.error(f"⚠️ Error técnico en nube ({pestana}): {e}")
        return False

@st.cache_data(ttl=30)
def leer_matriz_nube(pestana):
    gc = conectar_google()
    if gc:
        try:
            nombre_hoja_real = obtener_mapeo_solapas().get(pestana.upper().strip(), pestana)
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(nombre_hoja_real)
            todas_filas = hoja.get_all_values()
            if not todas_filas or len(todas_filas) == 0:
                return pd.DataFrame()
            encabezados = [str(h).strip().upper() for h in todas_filas[0]]
            datos_cuerpo = todas_filas[1:]
            df = pd.DataFrame(datos_cuerpo, columns=encabezados)
            df.columns = [str(c).strip().upper() for c in df.columns]
            df = df.loc[:, ~df.columns.duplicated()]
            return df
        except Exception as e: 
            print(f"Error leyendo {pestana}: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

@st.cache_data(ttl=60)
def cargar_datos_comisarias():
    data = {
        "COMISARIA": ["COMISARÍA SAN MARTÍN 1RA", "COMISARÍA VECINAL 14C", "COMISARÍA AVELLANEDA 1RA", "COMISARÍA CAMPANA 1RA", "COMISARÍA SAN FERNANDO 1RA", "COMISARÍA TIGRE 1RA", "COMISARÍA PILAR 6TA (VILLA ROSA)", "COMISARÍA VECINAL 1B", "COMISARÍA VECINAL 14A", "COMISARÍA LANÚS 2DA", "COMISARÍA VECINAL 13A", "COMISARÍA LA MATANZA 2DA", "COMISARÍA LA MATANZA 3RA", "COMISARÍA VECINAL 2A", "COMISARÍA VECINAL 12A", "COMISARÍA VECINAL 12B", "COMISARÍA VECINAL 6A", "COMISARÍA VECINAL 1D", "COMISARÍA RAMOS MEJÍA 2DA"],
        "DIRECCION": ["Gral. Lavalle 420", "Av. Coronel Díaz 2250", "Gral. Lavalle 150", "Rivadavia 750", "Constitución 720", "Cazón 1250", "Ruta 25 s/n", "Salta 1450", "Av. Cnel. Díaz 2250", "Hipólito Yrigoyen 4300", "Av. Cabildo 2300", "Monseñor Bufano 3200", "Arieta 2500", "Av. Las Heras 2650", "Miller 2750", "Arias 4450", "Av. Díaz Vélez 5150", "Av. San Juan 1050", "Av. de Mayo 350"],
        "LOCALIDAD": ["SAN MARTÍN", "CABA", "AVELLANEDA", "CAMPANA", "SAN FERNANDO", "TIGRE", "PILAR", "CABA", "CABA", "LANÚS", "CABA", "LA MATANZA", "LA MATANZA", "CABA", "CABA", "CABA", "CABA", "CABA", "RAMOS MEJÍA"],
        "TELEFONO": ["011-4754-2321", "011-4821-5544", "011-4201-1122", "03489-422111", "011-4744-0192", "011-4512-9900", "0230-449-0111", "011-4331-1122", "011-4821-5545", "011-4241-0022", "011-4788-9900", "011-4482-1111", "011-4486-2222", "011-4801-3344", "011-4541-1122", "011-4542-3344", "011-4982-5566", "011-4301-7788", "011-4464-1122"],
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

def registrar_objetivo_con_comisaria_automatica(nombre_obj, direccion, localidad, supervisor, lat, lon, responsables):
    distancia_minima = float('inf')
    comisaria_encontrada = "COMISARÍA JURISDICCIONAL"
    direccion_comisaria = "---"
    localidad_comisaria = "---"
    telefono_comisaria = "011-4000-0000"
    
    df_comis = cargar_datos_comisarias()
    
    try:
        lat_f = float(str(lat).replace(',', '.'))
        lon_f = float(str(lon).replace(',', '.'))
        
        for _, com in df_comis.iterrows():
            lon1, lat1, lon2, lat2 = map(math.radians, [lon_f, lat_f, com['LONGITUD'], com['LATITUD']])
            dlon = lon2 - lon1
            dlat = lat2 - lat1
            a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
            c = 2 * math.asin(math.sqrt(a))
            km = 6371 * c
            
            if km < distancia_minima:
                distancia_minima = km
                comisaria_encontrada = com['COMISARIA']
                direccion_comisaria = com['DIRECCION']
                localidad_comisaria = com['LOCALIDAD']
                telefono_comisaria = com.get('TELEFONO', '011-4000-0000')
    except:
        pass

    comisaria_formateada = f"{comisaria_encontrada} - {direccion_comisaria}, {localidad_comisaria} (Tel: {telefono_comisaria}) (~{distancia_minima:.2f} KM)"

    datos_nuevo_obj = [
        str(nombre_obj).strip().upper(), 
        str(direccion).strip().upper(), 
        str(localidad).strip().upper(), 
        str(supervisor).strip().upper(), 
        str(lat), 
        str(lon), 
        str(responsables).strip().upper(),
        comisaria_formateada
    ]
    
    return escribir_registro_nube("OBJETIVOS", datos_nuevo_obj)

def obtener_lista_supervisores_dinamica():
    base = ["AYALA BRIAN", "SUPERVISOR 1", "SUPERVISOR 2", "SUPERVISOR 3", "SUPERVISOR 4", "SUPERVISOR 5", "SUPERVISOR NOCTURNO", "CONTROLADOR NOCTURNO", "TIKI"]
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
            hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet("JORNADA SUPERVISORES")
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
            nombres_posibles = ["REGISTRO QR SUPERVISORES", "REGISTRO-QR-SUPERVISORES"]
            
            for nombre in nombres_posibles:
                try:
                    hoja = sh.worksheet(nombre)
                    break
                except:
                    continue
            
            if hoja is None:
                hoja = sh.add_worksheet(title="REGISTRO QR SUPERVISORES", rows="100", cols="10")
                hoja.append_row(["FECHA_HORA", "OBJETIVO", "ACCION", "SUPERVISOR", "ESTADO"])

            hoja.append_row(datos)
            st.cache_data.clear()
            return True
    except Exception as ex:
        st.error(f"⚠️ Error detallado en nube: {ex}")
    return False

def generar_pdf_reporte(titulo_reporte, df_datos):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), rightMargin=24, leftMargin=24, topMargin=25, bottomMargin=25)
    elementos = []
    styles = getSampleStyleSheet()
    estilo_titulo = ParagraphStyle('TituloTactico', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=14, textColor=colors.HexColor('#000000'), spaceAfter=4, alignment=1)
    estilo_sub = ParagraphStyle('SubTactico', parent=styles['Normal'], fontName='Helvetica', fontSize=9, textColor=colors.HexColor('#333333'), spaceAfter=15, alignment=1)
    
    elementos.append(Paragraph("<b>AION-YAROKU | REPORTE TÁCTICO OFICIAL</b>", estilo_titulo))
    elementos.append(Paragraph(f"<b>{titulo_reporte}</b><br/>Fecha de Emisión: {obtener_hora_argentina()}", estilo_sub))
    elementos.append(Spacer(1, 10))
    
    if not df_datos.empty:
        columnas = list(df_datos.columns)
        datos_tabla = [[str(c) for c in columnas]]
        for _, row in df_datos.iterrows():
            datos_tabla.append([str(row[c]) if pd.notna(row[c]) else "" for c in columnas])
            
        ancho_total_disponible = 744.0
        anchos_lista = [ancho_total_disponible / len(columnas)] * len(columnas)

        t = Table(datos_tabla, colWidths=anchos_lista, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#000000')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8.5),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#FFFFFF')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#666666')),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('TOPPADDING', (0, 1), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
        ]))
        elementos.append(t)
    else:
        elementos.append(Paragraph("No hay registros disponibles para este reporte.", styles['Normal']))
        
    doc.build(elementos, canvasmaker=NumberedCanvas)
    buffer.seek(0)
    return buffer.getvalue()

def aplicar_identidad_alfa():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@300;500;700&display=swap');
        .stApp { background: radial-gradient(circle at top, #0A0F1E 0%, #030305 100%) !important; color: #E0E0E0; font-family: 'Rajdhani', sans-serif; unicode-bidi: plaintext !important; }
        
        .block-container {
            padding-left: 1rem !important;
            padding-right: 1rem !important;
            padding-top: 1rem !important;
            max-width: 100% !important;
        }

        .contenedor-logo-central { display: flex; justify-content: center; align-items: center; width: 100%; margin: 10px 0; }
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
            color: #00E5FF !important; font-size: 22px; margin-top: 10px;
            display: flex; align-items: center; justify-content: center; gap: 12px;
            text-shadow: 0 0 15px rgba(0, 229, 255, 0.4); letter-spacing: 2px; text-transform: uppercase;
            text-align: center;
        }

        header {
            background: transparent !important;
            background-color: transparent !important;
        }

        .stApp div[data-testid="stExpander"] { background-color: #1A1C23 !important; border: 1px solid #2D313E !important; border-radius: 8px !important; }
        .stApp div[data-testid="stExpander"] summary p { color: #E0E0E0 !important; font-size: 14px !important; font-weight: 600 !important; text-transform: uppercase; }
        .stApp input { background-color: #252833 !important; color: #FFFFFF !important; border: 1px solid #1A1C23 !important; border-radius: 6px !important; unicode-bidi: plaintext !important; direction: ltr !important; text-align: left !important; }
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
            width: 100% !important;
            max-width: 320px !important;
            margin: 0 auto 10px auto !important;
            overflow: hidden !important;
            border-radius: 8px !important;
            background: #000 !important;
            position: relative;
        }
        .qr-scanner-container iframe, .qr-scanner-container video, .qr-scanner-container div {
            width: 100% !important;
            max-width: 320px !important;
            height: 220px !important;
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
        div[data-testid="stMetricValue"] div { color: #FFFFFF !important; font-family: 'Orbitron', sans-serif !important; font-size: 18px !important; unicode-bidi: plaintext !important; direction: ltr !important; }
        
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

# --- REEMPLAZO NATIVO DEL RELOJ EN VIVO USANDO FRAGMENT DE STREAMLIT ---
@st.fragment(run_every=1)
def renderizar_reloj_fluido():
    tz = pytz.timezone("America/Argentina/Buenos_Aires")
    hora_actual = datetime.now(tz).strftime("%H:%M:%S")
    st.metric(label="HORA LOCAL", value=hora_actual)

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
            nombre_hoja_real = obtener_mapeo_solapas().get(nombre_hoja.upper().strip(), nombre_hoja)
            worksheet = gc.open_by_key(ID_MAESTRO_DB).worksheet(nombre_hoja_real)
            worksheet.delete_rows(2, worksheet.row_count)
            st.cache_data.clear()
            return True
    except: return False

def ejecutar_cierre_táctico():
    matrices = ["JORNADA SUPERVISORES", "REGISTRO QR SUPERVISORES", "ALERTAS", "NOVEDADES GUARDIA", "CONTROL DE FLOTA"]
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
            user_limpio = user.strip().upper()
            pass_limpio = password.strip()
            
            if modo == "Iniciar Sesión" and user_limpio == "ADMIN" and pass_limpio == "aion2026":
                st.session_state.usuario_logueado = True
                st.session_state.user_sel = "ADMIN CENTRAL"
                st.session_state.rol_sel = "ADMINISTRADOR"
                st.session_state.admin_autenticado = True
                st.session_state.sup_autenticado = False
                sincronizar_url_sesion()
                st.rerun()
                
            elif modo == "Iniciar Sesión" and rol_usuario == "SUPERVISOR" and (user_limpio.startswith("SUPERVISOR") or user_limpio in ["AYALA BRIAN", "AYALA", "GONZALEZ", "CONTROLADOR NOCTURNO", "TIKI"] or pass_limpio == "1234"):
                usuario_final = "AYALA BRIAN" if user_limpio in ["AYALA BRIAN", "AYALA"] else user_limpio
                st.session_state.usuario_logueado = True
                st.session_state.user_sel = usuario_final
                st.session_state.rol_sel = "SUPERVISOR"
                st.session_state.sup_autenticado = True
                st.session_state.admin_autenticado = False
                sincronizar_url_sesion()
                st.rerun()

            elif modo == "Iniciar Sesión" and rol_usuario == "MONITOREO" and (user_limpio in ["MONITOREO", "OPERADOR", "OPERADOR CENTRAL"] or pass_limpio == "1234"):
                st.session_state.usuario_logueado = True
                st.session_state.user_sel = "OPERADOR CENTRAL" if user_limpio == "MONITOREO" else user_limpio
                st.session_state.rol_sel = "MONITOREO"
                st.session_state.sup_autenticado = False
                st.session_state.admin_autenticado = False
                sincronizar_url_sesion()
                st.rerun()

            elif modo == "Iniciar Sesión" and rol_usuario == "JEFE DE OPERACIONES" and (user_limpio in ["JEFE", "JEFE DE OPERACIONES"] or pass_limpio == "1234"):
                st.session_state.usuario_logueado = True
                st.session_state.user_sel = "JEFE DE OPERACIONES"
                st.session_state.rol_sel = "JEFE DE OPERACIONES"
                st.session_state.sup_autenticado = False
                st.session_state.admin_autenticado = False
                sincronizar_url_sesion()
                st.rerun()

            elif modo == "Iniciar Sesión" and rol_usuario == "GERENCIA" and (user_limpio in ["GERENCIA", "DIRECTOR", "DIRECCIÓN GENERAL"] or pass_limpio == "1234"):
                st.session_state.usuario_logueado = True
                st.session_state.user_sel = "DIRECCIÓN GENERAL"
                st.session_state.rol_sel = "GERENCIA"
                st.session_state.sup_autenticado = False
                st.session_state.admin_autenticado = False
                sincronizar_url_sesion()
                st.rerun()

            elif modo == "Iniciar Sesión" and rol_usuario == "VIGILADOR" and (user_limpio in ["VIGILADOR", "AGENTE", "CUSTODIO"] or pass_limpio == "1234"):
                st.session_state.usuario_logueado = True
                st.session_state.user_sel = "VIGILADOR EN PUESTO" if user_limpio == "VIGILADOR" else user_limpio
                st.session_state.rol_sel = "VIGILADOR"
                st.session_state.sup_autenticado = False
                st.session_state.admin_autenticado = False
                sincronizar_url_sesion()
                st.rerun()
                
            elif modo == "Iniciar Sesión":
                df_usuarios = leer_matriz_nube("USUARIOS")
                usuario_ok = pd.DataFrame()
                if not df_usuarios.empty and 'USUARIO' in df_usuarios.columns and 'CONTRASEÑA' in df_usuarios.columns:
                    usuario_ok = df_usuarios[
                        (df_usuarios['USUARIO'].str.strip().str.upper() == user_limpio) & 
                        (df_usuarios['CONTRASEÑA'].str.strip() == pass_limpio)
                    ]
                if not usuario_ok.empty:
                    estado = str(usuario_ok.iloc[0].get('ESTADO', 'PENDIENTE')).strip().upper()
                    if estado == "APROBADO":
                        rol_encontrado = str(usuario_ok.iloc[0]['ROL']).strip().upper()
                        st.session_state.usuario_logueado = True
                        st.session_state.user_sel = user_limpio
                        st.session_state.rol_sel = rol_encontrado
                        
                        if rol_encontrado == "SUPERVISOR":
                            st.session_state.sup_autenticado = True
                            st.session_state.admin_autenticado = False
                        elif rol_encontrado == "ADMINISTRADOR":
                            st.session_state.admin_autenticado = True
                            st.session_state.sup_autenticado = False
                        else:
                            st.session_state.sup_autenticado = False
                            st.session_state.admin_autenticado = False

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

# --- LÓGICA DE BARRA LATERAL DIFERENCIADA Y SELECTOR DE VISTAS ADMIN ---
if st.session_state.rol_sel == "ADMINISTRADOR" or st.session_state.get("admin_autenticado", False):
    with st.sidebar:
        st.markdown('<div class="contenedor-logo-sidebar"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" style="width:180px; border:1px solid #00e5ff; border-radius:4px;"></div>', unsafe_allow_html=True)
        st.subheader("⚙️ NÚCLEO MAESTRO")
        
        vista_admin_sel = st.selectbox(
            "MODO DE VISTA ACTIVO:", 
            ["ADMINISTRADOR (NÚCLEO)", "MONITOREO", "JEFE DE OPERACIONES", "GERENCIA", "SUPERVISOR", "VIGILADOR"],
            key="selector_vista_admin"
        )
        
        if "ADMINISTRADOR" in vista_admin_sel:
            st.session_state.rol_sel = "ADMINISTRADOR"
            st.session_state.user_sel = "ADMIN CENTRAL"
            st.session_state.sup_autenticado = False
        elif "MONITOREO" in vista_admin_sel:
            st.session_state.rol_sel = "MONITOREO"
            st.session_state.user_sel = "OPERADOR CENTRAL"
            st.session_state.sup_autenticado = False
        elif "JEFE DE OPERACIONES" in vista_admin_sel:
            st.session_state.rol_sel = "JEFE DE OPERACIONES"
            st.session_state.user_sel = "JEFE DE OPERACIONES"
            st.session_state.sup_autenticado = False
        elif "GERENCIA" in vista_admin_sel:
            st.session_state.rol_sel = "GERENCIA"
            st.session_state.user_sel = "DIRECCIÓN GENERAL"
            st.session_state.sup_autenticado = False
        elif "VIGILADOR" in vista_admin_sel:
            st.session_state.rol_sel = "VIGILADOR"
            st.session_state.user_sel = "VIGILADOR EN PUESTO"
            st.session_state.sup_autenticado = False
        elif "SUPERVISOR" in vista_admin_sel:
            st.session_state.rol_sel = "SUPERVISOR"
            
        if "SUPERVISOR" in vista_admin_sel or st.session_state.rol_sel == "SUPERVISOR":
            st.markdown("---")
            st.markdown("### 👤 SELECCIONAR SUPERVISOR")
            nom_sup_elegido = st.selectbox("ELEGIR RESPONSABLE:", LISTA_SUPS_TACTICOS, key="selector_directo_supervisor_admin")
            
            if st.button("🚀 ACCEDER A ESTA VISTA", use_container_width=True):
                st.session_state.rol_sel = "SUPERVISOR"
                st.session_state.user_sel = nom_sup_elegido.strip().upper()
                st.session_state.sup_autenticado = True
                sincronizar_url_sesion()
                st.rerun()

        st.markdown("---")
        if st.button("🚪 CERRAR SESIÓN", use_container_width=True):
            st.session_state.usuario_logueado = False
            st.query_params.clear()
            st.rerun()
else:
    with st.sidebar:
        st.markdown('<div class="contenedor-logo-sidebar"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" style="width:180px; border:1px solid #00e5ff; border-radius:4px;"></div>', unsafe_allow_html=True)
        st.markdown("---")
        st.markdown(f"**PERFIL:** {st.session_state.rol_sel}")
        st.markdown(f"**USUARIO:** {st.session_state.user_sel}")
        st.markdown("---")
        if st.button("🚪 CERRAR SESIÓN", use_container_width=True):
            st.session_state.usuario_logueado = False
            st.query_params.clear()
            st.rerun()

st.markdown('<div class="contenedor-logo-central"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" class="logo-phoenix"></div>', unsafe_allow_html=True)

st.markdown(f"""
    <div style="background: rgba(30, 41, 59, 0.4); border: 1px solid rgba(148, 163, 184, 0.3); border-radius: 8px; padding: 15px; text-align: center; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);">
        <span style="font-family: 'Orbitron', sans-serif; color: #94A3B8; font-size: 16px; font-weight: bold; text-transform: uppercase; letter-spacing: 1px;">⚡ ESTACIÓN TÁCTICA AION-YAROKU ⚡</span><br>
        <span style="font-family: 'Rajdhani', sans-serif; color: #CBD5E1; font-size: 13px; letter-spacing: 0.5px;">MODO DE ACCESO AUTORIZADO: <b>{st.session_state.rol_sel}</b> ({st.session_state.user_sel})</span>
    </div>
""", unsafe_allow_html=True)

titulos = {
    "MONITOREO": "🛰️ CENTRAL DE INTELIGENCIA OPERATIVA",
    "SUPERVISOR": f"📱 Estación de Control: {st.session_state.user_sel}",
    "VIGILADOR": "👮 TERMINAL OPERATIVO VIGILADORES",
    "JEFE DE OPERACIONES": "📋 COMANDO DE OPERACIONES TÁCTICAS",
    "GERENCIA": "🏢 DIRECCIÓN Y FISCALIZACIÓN GENERAL",
    "ADMINISTRADOR": "⚙️ NÚCLEO MAESTRO: AION-YAROKU"
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
        df_emergencias = pd.DataFrame(columns=['FECHA', 'USUARIO', 'TIPO', 'ESTADO', 'OBJETIVO', 'SUPERVISOR'])
    else:
        df_emergencias.columns = df_emergencias.columns.str.strip().str.upper()

    df_mapa_monitoreo = pd.DataFrame()
    if not df_objetivos.empty:
        df_objetivos.columns = df_objetivos.columns.str.strip().str.upper()
        if 'LATITUD' in df_objetivos.columns and 'LONGITUD' in df_objetivos.columns:
            df_mapa_monitoreo = df_objetivos.dropna(subset=['LATITUD', 'LONGITUD']).copy()

    lista_objetivos_en_panico = []
    if not df_emergencias.empty and 'ESTADO' in df_emergencias.columns and 'TIPO' in df_emergencias.columns:
        pendientes_sos = df_emergencias[
            (df_emergencias['ESTADO'].astype(str).str.upper() == 'PENDIENTE') & 
            (df_emergencias['TIPO'].astype(str).str.upper() == 'PÁNICO')
        ]
        sos_activos = len(pendientes_sos)
        for _, row in pendientes_sos.iterrows():
            obj_val = str(row.get('OBJETIVO', '')).strip().upper()
            if obj_val and obj_val != "NAN":
                lista_objetivos_en_panico.append(obj_val)
    else: 
        sos_activos = 0
    
    with col1.container():
        @st.fragment(run_every=10)
        def contar_panicos_monitoreo():
            df_alertas = leer_matriz_nube("ALERTAS")
            if not df_alertas.empty:
                df_alertas.columns = [str(c).strip().upper() for c in df_alertas.columns]
                df_pan_vig = df_alertas[
                    (df_alertas['TIPO'].astype(str).str.upper() == "PÁNICO") & 
                    (df_alertas['ESTADO'].astype(str).str.upper() == "PENDIENTE")
                ] if 'TIPO' in df_alertas.columns else pd.DataFrame()
                total_sos = len(df_pan_vig)
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

    t_radar, t_mensajeria, t_nov = st.tabs([
        "🚨 RADAR S.O.S", label_msg, "Auditoría y registro de monitoreo por supervisor"
    ]) 

    with t_radar:
        st.subheader("📡 RADAR GLOBAL DE OBJETIVOS Y PÁNICOS ACTIVOS")
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

        if sup_filtro_mono != "TODOS LOS SUPERVISORES" and not df_mapa_filtrado_sup.empty:
            df_jornadas_mon = leer_matriz_nube("REGISTRO QR SUPERVISORES")
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
                obj_nombre = str(r['OBJETIVO']).strip().upper()
                es_panico = obj_nombre in lista_objetivos_en_panico
                es_el_seleccionado = (obj_nombre == str(obj_seleccionado).strip().upper())
                
                texto_tooltip = f"🎯 {obj_nombre}"
                if es_panico:
                    alerta_activa = df_emergencias[
                        ((df_emergencias['OBJETIVO'].astype(str).str.strip().str.upper() == obj_nombre)) & 
                        (df_emergencias['ESTADO'].astype(str).str.strip().str.upper() == 'PENDIENTE') & 
                        (df_emergencias['TIPO'].astype(str).str.strip().str.upper() == 'PÁNICO')
                    ] if 'OBJETIVO' in df_emergencias.columns else pd.DataFrame()
                    if not alerta_activa.empty:
                        nombre_persona = alerta_activa.iloc[-1].get('USUARIO', 'AGENTE')
                        texto_tooltip = f"🚨 PÁNICO: {nombre_persona} | OBJ: {obj_nombre}"

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
                        tooltip=f"🎯 {obj_nombre} | 👤 SUP: {r.get('SUPERVISOR', 'N/A')}"
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
            
    with t_nov:
        st.subheader("🔄 AUDITORÍA Y REGISTROS DE MONITOREO")
        
        df_qr_m_base = leer_matriz_nube("REGISTRO QR SUPERVISORES")
        df_jor_m_base = leer_matriz_nube("JORNADA SUPERVISORES")
        df_flota_m_base = leer_matriz_nube("CONTROL DE FLOTA")
        df_vig_rel_m_base = leer_matriz_nube("VIGILADORES")
        df_nov_m_base = leer_matriz_nube("NOVEDADES GUARDIA")
        df_alt_m_base = leer_matriz_nube("ALERTAS")

        sups_dinamicos_set = set()
        
        if not df_qr_m_base.empty:
            df_qr_m_base.columns = [str(c).strip().upper() for c in df_qr_m_base.columns]
            col_sup_qm = 'SUPERVISOR' if 'SUPERVISOR' in df_qr_m_base.columns else df_qr_m_base.columns[3]
            if col_sup_qm in df_qr_m_base.columns:
                for s in df_qr_m_base[col_sup_qm].dropna().astype(str).str.strip().str.upper():
                    if s and s != "NAN": sups_dinamicos_set.add(s)

        if not df_jor_m_base.empty:
            df_jor_m_base.columns = [str(c).strip().upper() for c in df_jor_m_base.columns]
            col_sup_jm = 'SUPERVISOR' if 'SUPERVISOR' in df_jor_m_base.columns else df_jor_m_base.columns[1]
            if col_sup_jm in df_jor_m_base.columns:
                for s in df_jor_m_base[col_sup_jm].dropna().astype(str).str.strip().str.upper():
                    if s and s != "NAN": sups_dinamicos_set.add(s)

        if not df_flota_m_base.empty:
            df_flota_m_base.columns = [str(c).strip().upper() for c in df_flota_m_base.columns]
            col_sup_fm = 'SUPERVISOR' if 'SUPERVISOR' in df_flota_m_base.columns else df_flota_m_base.columns[1]
            if col_sup_fm in df_flota_m_base.columns:
                for s in df_flota_m_base[col_sup_fm].dropna().astype(str).str.strip().str.upper():
                    if s and s != "NAN": sups_dinamicos_set.add(s)

        sups_dinamicos_lista = sorted(list(sups_dinamicos_set))

        if len(sups_dinamicos_lista) > 0:
            pestanas_sups = st.tabs(sups_dinamicos_lista)
            
            for idx_p, sup_seleccionado_mono in enumerate(sups_dinamicos_lista):
                with pestanas_sups[idx_p]:
                    st.markdown(f"### 🛡️ PANEL DE CONTROL: {sup_seleccionado_mono}")
                    
                    st.markdown("#### 📱 Fichajes QR")
                    if not df_qr_m_base.empty:
                        col_sup_qm = 'SUPERVISOR' if 'SUPERVISOR' in df_qr_m_base.columns else df_qr_m_base.columns[3]
                        df_sup_qrs_m = df_qr_m_base[df_qr_m_base[col_sup_qm].astype(str).str.strip().str.upper() == str(sup_seleccionado_mono).strip().upper()]
                        if not df_sup_qrs_m.empty:
                            st.dataframe(df_sup_qrs_m.iloc[::-1], use_container_width=True, hide_index=True)
                        else:
                            st.info("Sin registros QR para este supervisor.")
                    else:
                        st.info("No hay datos de fichajes QR.")

                    st.markdown("---")
                    st.markdown("#### 📋 Fichaje de Vigiladores")
                    if not df_nov_m_base.empty:
                        df_nov_m_base.columns = [str(c).strip().upper() for c in df_nov_m_base.columns]
                        objs_del_sup = [o.strip().upper() for o in df_objetivos[df_objetivos['SUPERVISOR'].astype(str).str.strip().str.upper() == str(sup_seleccionado_mono).strip().upper()]['OBJETIVO'].tolist()] if not df_objetivos.empty else []
                        
                        if len(objs_del_sup) > 0 and 'OBJETIVO' in df_nov_m_base.columns:
                            df_nov_m_base['OBJETIVO_CLEAN'] = df_nov_m_base['OBJETIVO'].astype(str).str.strip().str.upper()
                            
                            col_evento_real = None
                            for posible_col in ['TIPO_EVENTO', 'TIPO EVENTO', 'EVENTO', 'TIPO']:
                                if posible_col in df_nov_m_base.columns:
                                    col_evento_real = posible_col
                                    break
                            if col_evento_real is None and len(df_nov_m_base.columns) > 2:
                                col_evento_real = df_nov_m_base.columns[2]

                            if col_evento_real:
                                mask_fich = df_nov_m_base['OBJETIVO_CLEAN'].isin(objs_del_sup) & \
                                            df_nov_m_base[col_evento_real].astype(str).str.strip().str.upper().str.contains("MARCACIÓN|FICHAJE|INGRESO|EGRESO", regex=True)
                                df_fichajes_sup_filtrado = df_nov_m_base[mask_fich].copy()
                            else:
                                df_fichajes_sup_filtrado = pd.DataFrame()
                            
                            if not df_fichajes_sup_filtrado.empty:
                                st.dataframe(df_fichajes_sup_filtrado.iloc[::-1], use_container_width=True, hide_index=True)
                            else:
                                st.info("No hay fichajes de vigiladores registrados para los objetivos de este supervisor.")
                        else:
                            st.info("Este supervisor no tiene objetivos asignados en la red.")
                    else:
                        st.info("No hay novedades de guardia registradas.")

                    st.markdown("---")
                    st.markdown("#### 🔄 Relevos de vigiladores")
                    if not df_vig_rel_m_base.empty:
                        df_vig_rel_m_base.columns = [str(c).strip().upper() for c in df_vig_rel_m_base.columns]
                        objs_del_sup = df_objetivos[df_objetivos['SUPERVISOR'].astype(str).str.strip().str.upper() == sup_seleccionado_mono]['OBJETIVO'].tolist() if not df_objetivos.empty else []
                        
                        if len(objs_del_sup) > 0:
                            col_obj_v = 'OBJETIVO' if 'OBJETIVO' in df_vig_rel_m_base.columns else df_vig_rel_m_base.columns[2]
                            df_rel_sup_filtrado = df_vig_rel_m_base[df_vig_rel_m_base[col_obj_v].astype(str).str.strip().str.upper().isin([o.upper() for o in objs_del_sup])]
                            
                            if not df_rel_sup_filtrado.empty:
                                st.dataframe(df_rel_sup_filtrado.iloc[::-1], use_container_width=True, hide_index=True)
                            else:
                                st.info("No hay relevos de vigiladores registrados para los objetivos de este supervisor.")
                        else:
                            st.info("Este supervisor no tiene objetivos asignados.")
                    else:
                        st.info("No hay relevos de vigiladores registrados.")

                    st.markdown("---")
                    st.markdown("#### 🚨 Pánico S.O.S de Supervisor")
                    if not df_alt_m_base.empty:
                        df_alt_m_base.columns = [str(c).strip().upper() for c in df_alt_m_base.columns]
                        df_panicos_op = df_alt_m_base[df_alt_m_base['TIPO'].astype(str).str.strip().str.upper() == "PÁNICO"].copy() if 'TIPO' in df_alt_m_base.columns else pd.DataFrame()
                        
                        if not df_panicos_op.empty:
                            mask_solo_supervisor = (df_panicos_op['USUARIO'].astype(str).str.strip().str.upper() == str(sup_seleccionado_mono).strip().upper())
                            df_pan_sup_filtrado = df_panicos_op[mask_solo_supervisor]
                        else:
                            df_pan_sup_filtrado = pd.DataFrame()
                        
                        if not df_pan_sup_filtrado.empty:
                            st.dataframe(df_pan_sup_filtrado.iloc[::-1], use_container_width=True, hide_index=True)
                        else:
                            st.info("No hay pánicos S.O.S de supervisor registrados.")
                    else:
                        st.info("Sin pánicos S.O.S registrados.")

                    st.markdown("---")
                    st.markdown("#### 🚨 Pánico S.O.S Vigilador")
                    if not df_alt_m_base.empty:
                        df_alt_m_base.columns = [str(c).strip().upper() for c in df_alt_m_base.columns]
                        df_panicos_op = df_alt_m_base[df_alt_m_base['TIPO'].astype(str).str.strip().str.upper() == "PÁNICO"].copy() if 'TIPO' in df_alt_m_base.columns else pd.DataFrame()
                        objs_del_sup = [o.strip().upper() for o in df_objetivos[df_objetivos['SUPERVISOR'].astype(str).str.strip().str.upper() == str(sup_seleccionado_mono).strip().upper()]['OBJETIVO'].tolist()] if not df_objetivos.empty else []
                        
                        if not df_panicos_op.empty:
                            mask_obj_del_sup = df_panicos_op['OBJETIVO'].astype(str).str.strip().str.upper().isin([o.upper() for o in objs_del_sup])
                            mask_no_es_supervisor = ~(df_panicos_op['USUARIO'].astype(str).str.strip().str.upper() == str(sup_seleccionado_mono).strip().upper())
                            df_pan_vig_filtrado = df_panicos_op[mask_obj_del_sup & mask_no_es_supervisor]
                        else:
                            df_pan_vig_filtrado = pd.DataFrame()
                        
                        if not df_pan_vig_filtrado.empty:
                            df_pan_vig_c_turno_m = df_pan_vig_filtrado.copy()
                            turnos_vig_list_m = []
                            for _, f_row_m in df_pan_vig_c_turno_m.iterrows():
                                fh_val_pm = str(f_row_m.get('FECHA', ''))
                                turnos_vig_list_m.append(determinar_turno_activo(fh_val_pm))
                            df_pan_vig_c_turno_m['TURNO VIGILADOR'] = turnos_vig_list_m
                            st.dataframe(df_pan_vig_c_turno_m.iloc[::-1], use_container_width=True, hide_index=True)
                        else:
                            st.info("No hay pánicos S.O.S de vigiladores registrados en los objetivos de este supervisor.")
                    else:
                        st.info("Sin pánicos S.O.S de vigiladores registrados.")

                    st.markdown("---")
                    st.markdown("#### ⚠️ Alertas Operativas")
                    if not df_alt_m_base.empty:
                        df_alt_m_base.columns = [str(c).strip().upper() for c in df_alt_m_base.columns]
                        
                        df_panicos_op_total = df_alt_m_base[df_alt_m_base['TIPO'].astype(str).str.strip().str.upper() == "PÁNICO"].copy() if 'TIPO' in df_alt_m_base.columns else pd.DataFrame()
                        
                        mask_solo_sup_cnt = (df_panicos_op_total['USUARIO'].astype(str).str.strip().str.upper() == str(sup_seleccionado_mono).strip().upper()) if not df_panicos_op_total.empty else pd.Series([False])
                        total_alertas_supervisor = len(df_panicos_op_total[mask_solo_sup_cnt]) if not df_panicos_op_total.empty else 0
                        
                        objs_del_sup_cnt = [o.strip().upper() for o in df_objetivos[df_objetivos['SUPERVISOR'].astype(str).str.strip().str.upper() == str(sup_seleccionado_mono).strip().upper()]['OBJETIVO'].tolist()] if not df_objetivos.empty else []
                        mask_obj_sup_cnt = df_panicos_op_total['OBJETIVO'].astype(str).str.strip().str.upper().isin([o.upper() for o in objs_del_sup_cnt]) if not df_panicos_op_total.empty and 'OBJETIVO' in df_panicos_op_total.columns else pd.Series([False])
                        mask_no_sup_cnt = ~mask_solo_sup_cnt if not df_panicos_op_total.empty else pd.Series([False])
                        total_alertas_vigilador = len(df_panicos_op_total[mask_obj_sup_cnt & mask_no_sup_cnt]) if not df_panicos_op_total.empty else 0

                        df_alertas_op = df_alt_m_base[df_alt_m_base['TIPO'].astype(str).str.strip().str.upper() != "PÁNICO"].copy() if 'TIPO' in df_alt_m_base.columns else df_alt_m_base.copy()
                        
                        if not df_alertas_op.empty:
                            mask_alt = pd.Series([False]*len(df_alertas_op))
                            if 'OBJETIVO' in df_alertas_op.columns:
                                mask_alt = mask_alt | df_alertas_op['OBJETIVO'].astype(str).str.strip().str.upper().isin([o.upper() for o in objs_del_sup])
                            if 'SUPERVISOR' in df_alertas_op.columns:
                                mask_alt = mask_alt | (df_alertas_op['SUPERVISOR'].astype(str).str.strip().str.upper() == str(sup_seleccionado_mono).strip().upper())
                            df_alt_sup_filtrado = df_alertas_op[mask_alt]
                        else:
                            df_alt_sup_filtrado = pd.DataFrame()
                        
                        if total_alertas_supervisor > 0 or total_alertas_vigilador > 0 or not df_alt_sup_filtrado.empty:
                            if total_alertas_supervisor > 0:
                                st.markdown(f"• TOTAL ALERTAS DE SUPERVISOR: **{total_alertas_supervisor}**")
                            if total_alertas_vigilador > 0:
                                st.markdown(f"• TOTAL ALERTAS DE VIGILADOR: **{total_alertas_vigilador}**")
                            
                            if not df_alt_sup_filtrado.empty:
                                st.dataframe(df_alt_sup_filtrado.iloc[::-1], use_container_width=True, hide_index=True)
                        else:
                            st.info("No hay alertas operativas adicionales registradas para los objetivos de este supervisor.")
                    else:
                        st.info("Sin alertas operativas registradas.")
        else:
            st.info("No hay supervisores con registros activos en el sistema todavía.")


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

        st.subheader(f"⏱️ GESTIÓN DE JORNADA")
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
            st.markdown(f"""
                <div style="background: rgba(25, 35, 30, 0.45); border: 1px solid rgba(60, 90, 75, 0.3); border-radius: 6px; padding: 10px; margin-bottom: 12px; font-family: 'Rajdhani', sans-serif; text-align: center;">
                    <span style="color: #92B9A4; font-size: 13px; font-weight: 500; letter-spacing: 0.5px;">📍 OBJETO DETECTADO PARA PÁNICO: <b>{obj_actual}</b></span>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.warning("⚠️ Selecciona tu objetivo en 'Visita QR' para activar el pánico correctamente.")

        col_p1, col_p2, col_p3 = st.columns([1, 1, 1])
        with col_p2:
            if st.button("S.O.S\nPÁNICO", type="primary"):
                exito = escribir_registro_nube("ALERTAS", [
                    obtener_hora_argentina(), st.session_state.user_sel, "PÁNICO", "PENDIENTE", obj_actual, st.session_state.user_sel
                ])
                if exito:
                    st.error(f"🚨 ALERTA ENVIADA DESDE {obj_actual}")

                    # --- CÁLCULO DE LA COMISARÍA MÁS CERCANA PARA LLAMADA DIRECTA ---
                    lat_obj_s, lon_obj_s = 0.0, 0.0
                    if not df_objetivos.empty:
                        filtro_sup_obj = df_objetivos[df_objetivos['OBJETIVO'] == obj_actual]
                        if not filtro_sup_obj.empty:
                            lat_obj_s = float(str(filtro_sup_obj['LATITUD'].iloc[0]).replace(',', '.'))
                            lon_obj_s = float(str(filtro_sup_obj['LONGITUD'].iloc[0]).replace(',', '.'))

                    com_nombre_s = "COMISARÍA JURISDICCIONAL"
                    com_tel_s = "011-4000-0000"
                    dist_s = float('inf')

                    for _, com in df_comisarias.iterrows():
                        try:
                            lon1, lat1, lon2, lat2 = map(math.radians, [lon_obj_s, lat_obj_s, com['LONGITUD'], com['LATITUD']])
                            d = 6371 * 2 * math.asin(math.sqrt(math.sin((lat2-lat1)/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2-lon1)/2)**2))
                            if d < dist_s:
                                dist_s = d
                                com_nombre_s = com['COMISARIA']
                                com_tel_s = com.get('TELEFONO', '011-4000-0000')
                        except: pass

                    st.session_state.alerta_activa_supervisor = {
                        "comisaria": com_nombre_s,
                        "telefono": com_tel_s,
                        "distancia": f"{dist_s:.2f}"
                    }

        if 'alerta_activa_supervisor' in st.session_state:
            datos_s = st.session_state.alerta_activa_supervisor
            st.markdown(f"""
                <div style="background: rgba(22, 27, 34, 0.6); border: 1px solid rgba(100, 116, 139, 0.3); border-radius: 8px; padding: 15px; margin-top: 12px; text-align: center; font-family: 'Rajdhani', sans-serif;">
                    <div style="font-family: 'Orbitron', sans-serif; color: #94A3B8; font-size: 13px; font-weight: 500; letter-spacing: 1px;">
                        🚨 EMERGENCIA ACTIVA - COMISARÍA JURISDICCIONAL
                    </div>
                    <div style="color: #CBD5E1; font-size: 13px; margin-top: 6px;">
                        <b>{datos_s['comisaria']}</b> (~{datos_s['distancia']} KM)
                    </div>
                    <div style="margin-top: 12px;">
                        <a href="tel:{datos_s['telefono']}" style="background-color: #1E293B; color: #94A3B8; padding: 10px 22px; border-radius: 6px; border: 1px solid #475569; font-family: 'Orbitron', sans-serif; font-weight: 500; font-size: 11px; text-decoration: none; display: inline-block; text-transform: uppercase; letter-spacing: 0.5px; direction: ltr !important; unicode-bidi: bidi-override !important; text-align: center;">
                            📞 LLAMAR DIRECTAMENTE AHORA ({datos_s['telefono']})
                        </a>
                    </div>
                </div>
            """, unsafe_allow_html=True)

        t_vis_qr, t_nuevo_obj, t_ruta_gmaps, t_car_tac, t_mensajeria_sup, t_pres_sup = st.tabs([
            "Visita QR", "➕ CARGAR OBJETIVO", "📲 RUTA GOOGLE MAPS", "Carga Táctica", "💬 MENSAJERÍA", "📋 NOVEDADES Y RELEVOS"
        ])
        
        with t_vis_qr:
            fecha_hoy_str = datetime.now(pytz.timezone('America/Argentina/Buenos_Aires')).strftime('%Y-%m-%d')
            st.markdown(f"### 📊 ESTADO DE MIS OBJETIVOS ASIGNADOS ({fecha_hoy_str})")

            if not df_objetivos_filtrados.empty:
                lista_tabla_objs = []
                df_jornadas_act = leer_matriz_nube("REGISTRO QR SUPERVISORES")
                
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
                st.info("Sin objetivos asignados actualmente.")

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
                                    escribir_registro_nube("NOVEDADES GUARDIA", [obtener_hora_argentina(), obj_select, f"SUPERVISIÓN QR VALIDADA ({accion_str})", "---", st.session_state.user_sel, "---", "PROCESADO", st.session_state.user_sel])
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
                    
                    v_km_ini_str = c_a.text_input("KM INICIAL:", value="0")
                    v_km_fin_str = c_b.text_input("KM FINAL:", value="0")
                    
                    v_combustible = c_a.selectbox("TIPO DE COMBUSTIBLE:", ["NAFTA SÚPER", "NAFTA PREMIUM", "GASOIL", "OTRO"])
                    v_monto_str = c_b.text_input("MONTO CARGADO ($):", value="0,00")
                    v_vig = st.text_input("SUPERVISOR RESPONSABLE:", value=st.session_state.user_sel).upper()
                    
                    if st.form_submit_button("REGISTRAR ACTA DE FLOTA"):
                        def parsear_numero(val_str):
                            if not val_str:
                                return 0.0
                            s = str(val_str).strip().replace('$', '').replace(' ', '')
                            s = s.replace('.', '').replace(',', '.')
                            try:
                                return float(s)
                            except:
                                return 0.0

                        v_km_ini = parsear_numero(v_km_ini_str)
                        v_km_fin = parsear_numero(v_km_fin_str)
                        v_monto = parsear_numero(v_monto_str)
                        
                        km_recorridos = max(0.0, v_km_fin - v_km_ini)
                        costo_km = round(v_monto / km_recorridos, 2) if km_recorridos > 0 else 0.0
                        estado_auditoria = "⚠️ REVISAR" if costo_km > 300 or costo_km == 0 else "✅ ACORDE"

                        fecha_reg = obtener_hora_argentina()
                        
                        km_rec_fmt = f"{km_recorridos:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                        monto_fmt = f"{v_monto:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                        km_ini_fmt = f"{v_km_ini:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                        km_fin_fmt = f"{v_km_fin:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                        costo_km_fmt = f"{costo_km:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

                        escribir_registro_nube("CONTROL DE FLOTA", [
                            fecha_reg, v_vig, v_patente, km_ini_fmt, km_fin_fmt, km_rec_fmt, v_combustible, monto_fmt, costo_km_fmt, estado_auditoria
                        ])
                        st.success(f"✅ Acta registrada. Distancia recorrida: {km_rec_fmt} km | Gasto: ${monto_fmt}")
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
                            exito_alta = registrar_objetivo_con_comisaria_automatica(
                                nuevo_nombre_obj, nueva_direccion, nueva_localidad, supervisor_asignado_actual, nueva_lat, nueva_lon, nuevos_responsables
                            )
                            if exito_alta:
                                st.success(f"✅ ¡Objetivo '{nuevo_nombre_obj}' creado con éxito!")
                                st.rerun()

            with tab_baja_sup:
                if not df_objetivos_filtrados.empty:
                    with st.form(key="form_baja_objetivo_supervisor", clear_on_submit=True):
                        obj_a_baja = st.selectbox("SELECCIONE OBJETIVO A DAR DE BAJA:", df_objetivos_filtrados['OBJETIVO'].unique())
                        motivo_baja = st.text_input("MOTIVO DE LA BAJA:")
                        if st.form_submit_button("🗑️ SOLICITAR BAJA DE OBJETIVO"):
                            escribir_registro_nube("SOLICITUDES DE ACCESO", [obtener_hora_argentina(), st.session_state.user_sel, "BAJA", f"{obj_a_baja} - MOTIVO: {motivo_baja}", "PENDIENTE"])
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
                escribir_registro_nube("NOVEDADES GUARDIA", [obtener_hora_argentina(), obj_actual, "NOVEDAD OPERATIVA", novedad_sup.strip().upper(), st.session_state.user_sel, "---", "PROCESADO", st.session_state.user_sel])
                st.success("✅ Cargado correctamente")

        with t_mensajeria_sup:
            renderizar_mensajeria_global("SUPERVISOR")
        
        with t_pres_sup:
            st.markdown(f"#### 📱 MIS ESCANEOS QR REGISTRADOS EN CAMPO")
            df_qr_sup_base = leer_matriz_nube("REGISTRO QR SUPERVISORES")
            if not df_qr_sup_base.empty:
                df_qr_sup_base.columns = [str(c).strip().upper() for c in df_qr_sup_base.columns]
                col_sup_q = 'SUPERVISOR' if 'SUPERVISOR' in df_qr_sup_base.columns else df_qr_sup_base.columns[3]
                df_qr_sup_propio = df_qr_sup_base[df_qr_sup_base[col_sup_q].astype(str).str.strip().str.upper() == sup_activo_normalizado]
                if not df_qr_sup_propio.empty:
                    st.dataframe(df_qr_sup_propio.iloc[::-1], use_container_width=True, hide_index=True)
                else:
                    st.info("No tienes escaneos QR registrados en este turno.")
            else:
                st.info("Sin registros QR en el sistema.")
    else:
        st.warning("⚠️ Autentíquese con sus credenciales de supervisor en la barra lateral.")


# =========================================================================
# ROL: VIGILADOR
# =========================================================================
elif st.session_state.rol_sel == "VIGILADOR":
    st.markdown('<div class="panel-novedad">', unsafe_allow_html=True)
    opciones_globales_obj = df_objetivos['OBJETIVO'].unique() if not df_objetivos.empty else ["ALFAVINIL"]
    
    if 'obj_actual_vig' not in st.session_state or not st.session_state.obj_actual_vig:
        if len(opciones_globales_obj) > 0:
            st.session_state.obj_actual_vig = opciones_globales_obj[0]
        else:
            st.session_state.obj_actual_vig = "ALFAVINIL"

    df_msg = leer_matriz_nube("MENSAJERIA")
    nombre_user = st.session_state.user_sel.upper()
    total_nuevos = 0
    if not df_msg.empty:
        mask = ((df_msg['DESTINATARIO'] == "TODOS") | (df_msg['DESTINATARIO'] == "VIGILADOR") | (df_msg['DESTINATARIO'] == nombre_user)) & (df_msg['ESTADO'] == "PENDIENTE")
        total_nuevos = len(df_msg[mask])

    label_msg = f"💬 MENSAJERÍA GLOBAL ({total_nuevos})" if total_nuevos > 0 else "💬 MENSAJERÍA GLOBAL"
    
    st.markdown(f"### 🛡️ PROTOCOLO DE EMERGENCIA")
    obj_detectado = st.session_state.get("obj_actual_vig", None)

    if obj_detectado:
        st.markdown(f"""
            <div style="background: rgba(25, 35, 30, 0.45); border: 1px solid rgba(60, 90, 75, 0.3); border-radius: 6px; padding: 10px; margin-bottom: 12px; font-family: 'Rajdhani', sans-serif; text-align: center;">
                <span style="color: #92B9A4; font-size: 13px; font-weight: 500; letter-spacing: 0.5px;">📍 OBJETO DETECTADO PARA PÁNICO: <b>{obj_detectado}</b></span>
            </div>
        """, unsafe_allow_html=True)
        col_pv1, col_pv2, col_pv3 = st.columns([1, 1, 1])
        with col_pv2:
            if st.button("S.O.S\nPÁNICO", type="primary"):
                nombre_real = st.session_state.get("v_nombre_completo", st.session_state.user_sel).upper()
                sup_asignado = "MONITOREO"
                lat_obj_vig, lon_obj_vig = 0.0, 0.0
                if not df_objetivos.empty:
                    filtro = df_objetivos[df_objetivos['OBJETIVO'] == obj_detectado]
                    if not filtro.empty:
                        sup_asignado = str(filtro['SUPERVISOR'].iloc[0]).strip()
                        lat_obj_vig = float(str(filtro['LATITUD'].iloc[0]).replace(',', '.'))
                        lon_obj_vig = float(str(filtro['LONGITUD'].iloc[0]).replace(',', '.'))
                
                com_cercana_nombre = "COMISARÍA JURISDICCIONAL"
                com_cercana_dir = "---"
                com_cercana_tel = "---"
                dist_min_com = float('inf')
                
                for _, com in df_comisarias.iterrows():
                    try:
                        lon1, lat1, lon2, lat2 = map(math.radians, [lon_obj_vig, lat_obj_vig, com['LONGITUD'], com['LATITUD']])
                        dlon = lon2 - lon1
                        dlat = lat2 - lat1
                        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
                        c = 2 * math.asin(math.sqrt(a))
                        km = 6371 * c
                        if km < dist_min_com:
                            dist_min_com = km
                            com_cercana_nombre = com['COMISARIA']
                            com_cercana_dir = com['DIRECCION']
                            com_cercana_tel = com.get('TELEFONO', '011-4000-0000')
                    except: pass

                st.session_state.alerta_activa_vigilador = {
                    "nombre": nombre_real,
                    "obj": obj_detectado,
                    "comisaria": com_cercana_nombre,
                    "direccion": com_cercana_dir,
                    "telefono": com_cercana_tel,
                    "distancia": f"{dist_min_com:.2f}"
                }

                fecha = obtener_hora_argentina()
                escribir_registro_nube("ALERTAS", [fecha, nombre_real, "PÁNICO", "PENDIENTE", obj_detectado, sup_asignado])
                enviar_alerta_automatica("SISTEMA_VIGILADOR", obj_detectado, nombre_real, sup_asignado)
                st.error(f"🚨 ALERTA ENVIADA: {nombre_real} DESDE {obj_detectado}")

        if 'alerta_activa_vigilador' in st.session_state:
            datos_pan = st.session_state.alerta_activa_vigilador
            st.markdown(f"""
                <div style="background: rgba(22, 27, 34, 0.6); border: 1px solid rgba(100, 116, 139, 0.3); border-radius: 8px; padding: 15px; margin-top: 12px; font-family: 'Rajdhani', sans-serif;">
                    <div style="color: #94A3B8; font-family: 'Orbitron', sans-serif; font-size: 13px; font-weight: 500; letter-spacing: 1px; display: flex; align-items: center; justify-content: center; gap: 6px;">
                        🚨 ALERTA ENVIADA: DESDE {datos_pan['obj']}
                    </div>
                    <div style="color: #CBD5E1; font-size: 13px; margin-top: 8px; text-align: center;">
                        👮 <b>COMISARÍA:</b> {datos_pan['comisaria']}<br>
                        <b>Dirección:</b> {datos_pan['direccion']} (~{datos_pan['distancia']} KM)
                    </div>
                    <div style="margin-top: 12px; text-align: center;">
                        <a href="tel:{datos_pan['telefono']}" style="background-color: #1E293B; color: #94A3B8; padding: 12px 24px; border-radius: 6px; border: 1px solid #475569; font-family: 'Orbitron', sans-serif; font-weight: 500; font-size: 11px; text-decoration: none; display: inline-block; text-transform: uppercase; letter-spacing: 0.5px; direction: ltr !important; unicode-bidi: bidi-override !important; text-align: center;">
                            📞 LLAMAR A LA COMISARÍA ({datos_pan['telefono']})
                        </a>
                    </div>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.warning("⚠️ Debes realizar el Fichaje o Relevo primero para activar el sistema de pánico.")
    
    st.markdown("---")
    
    tab_presentismo, tab_relevo, t_mensajeria = st.tabs(["📋 FICHAJE", "🔄 RELEVO", label_msg])
  
    with tab_presentismo:
        st.markdown("### 📸 REGISTRO BIOMÉTRICO")
        with st.form(key="form_fichaje_vigilador", clear_on_submit=True):
            v_nombre_completo = st.text_input("APELLIDO Y NOMBRE:", value="VIGILADOR DE PRUEBA" if st.session_state.user_sel != "VIGILADOR EN PUESTO" else "").strip() 
            v_legajo = st.text_input("LEGAJO:", value="12345" if st.session_state.user_sel != "VIGILADOR EN PUESTO" else "").strip() 
            v_obj = st.selectbox("OBJETIVO:", opciones_globales_obj)
            v_tipo_marcacion = st.selectbox("TIPO:", ["INGRESO", "EGRESO"])
            img_facial = st.camera_input("RECONOCIMIENTO FACIAL")
            
            if st.form_submit_button("CONSIGNAR Y TRANSMITIR"):
                if v_nombre_completo and v_legajo:
                    st.session_state.v_nombre_completo = v_nombre_completo.upper()
                    st.session_state.legajo_vigilador = v_legajo
                    st.session_state.obj_actual_vig = v_obj
                    
                    fecha_hora_arg = obtener_hora_argentina()
                    fecha_hoy = fecha_hora_arg.split(" ")[0]
                    hora_actual = fecha_hora_arg.split(" ")[1]
                    sup_responsable = df_objetivos[df_objetivos['OBJETIVO'] == v_obj]['SUPERVISOR'].iloc[0] if not df_objetivos.empty else "N/A"
                    tipo_evento = f"MARCACIÓN_{v_tipo_marcacion}"
                    
                    escribir_registro_nube("PRESENTISMO", [fecha_hoy, hora_actual, v_legajo, v_nombre_completo.upper(), v_obj, v_tipo_marcacion, "OK"])
                    escribir_registro_nube("NOVEDADES GUARDIA", [fecha_hora_arg, v_obj, tipo_evento, "---", v_nombre_completo.upper(), v_legajo, "PROCESADO", sup_responsable])
                    st.success(f"🔒 {tipo_evento} REGISTRADA PARA {v_nombre_completo.upper()}")
                else:
                    st.error("⚠️ Por favor, complete el apellido, nombre y legajo.")

    with tab_relevo:
        st.markdown("### 🔄 REGISTRO FORMAL DE CAMBIO")
        with st.form(key="form_relevo_vigilador_directo", clear_on_submit=True):
            v_obj_relevo = st.selectbox("OBJETIVO:", opciones_globales_obj, key="relevo_obj")
            vig_saliente = st.text_input("SALE (EGRESA):", value="AGENTE SALIENTE").upper().strip()
            vig_entrante = st.text_input("ENTRA (INGRESA):", value="AGENTE ENTRANTE").upper().strip()
            v_dni_relevo = st.text_input("DNI DE QUIEN INGRESA:", value="12345678").strip()
            
            if st.form_submit_button("SANCIONAR CAMBIO"):
                st.session_state.obj_actual_vig = v_obj_relevo
                sup_resp = df_objetivos[df_objetivos['OBJETIVO']==v_obj_relevo]['SUPERVISOR'].iloc[0] if not df_objetivos.empty else "N/A"
                fecha_hora_arg = obtener_hora_argentina()
                fecha_hoy = fecha_hora_arg.split(" ")[0]
                hora_actual = fecha_hora_arg.split(" ")[1]
                
                escribir_registro_nube("NOVEDADES GUARDIA", [fecha_hora_arg, v_obj_relevo, "RELEVO DE TURNO", vig_saliente, vig_entrante, v_dni_relevo, "PROCESADO", sup_resp])
                escribir_registro_nube("VIGILADORES", [fecha_hoy, hora_actual, v_obj_relevo, vig_saliente, vig_entrante, v_dni_relevo, sup_resp, "RELEVO_EFECTUADO"])
                
                st.success("🔒 RELEVO REGISTRADO Y EXITOSO")

    with t_mensajeria:
        renderizar_mensajeria_global("VIGILADOR")
    st.markdown('</div>', unsafe_allow_html=True)


# =========================================================================
# ROL: JEFE DE OPERACIONES / GERENCIA (TABLERO COMPARTIDO DE AUDITORÍA)
# =========================================================================
if st.session_state.rol_sel in ["JEFE DE OPERACIONES", "GERENCIA"]:
    col1, col2, col3, col4 = st.columns(4)
    
    with col1.container():
        @st.fragment(run_every=5)
        def mostrar_sos():
            df_alertas = leer_matriz_nube("ALERTAS")
            df_pan_vig_jefe = df_alertas[
                (df_alertas['TIPO'].astype(str).str.upper() == "PÁNICO") & 
                (df_alertas['ESTADO'].astype(str).str.upper() == "PENDIENTE")
            ] if not df_alertas.empty and 'TIPO' in df_alertas.columns else pd.DataFrame()
            total_sos = len(df_pan_vig_jefe)
            st.metric("🚨 S.O.S ACTIVOS", total_sos)
        mostrar_sos()

    col2.metric("📡 RED", "OPERATIVA")
    col3.metric("👤 USUARIO", f"{st.session_state.user_sel}")
    
    with col4.container():
        renderizar_reloj_fluido()

    df_msg = leer_matriz_nube("MENSAJERIA")
    nombre_user = st.session_state.user_sel.upper()
    total_nuevos = len(df_msg[((df_msg['DESTINATARIO'] == "TODOS") | 
                            (df_msg['DESTINATARIO'] == st.session_state.rol_sel) | 
                            (df_msg['DESTINATARIO'] == nombre_user)) & 
                           (df_msg['ESTADO'] == "PENDIENTE")]) if not df_msg.empty and 'ESTADO' in df_msg.columns else 0
    
    label_msg = f"💬 MENSAJERÍA ({total_nuevos})" if total_nuevos > 0 else "💬 MENSAJERÍA"
    
    st.markdown(f'<h2 style="color:#00E5FF; font-family:\'Orbitron\'; font-size:24px;">Comando: {st.session_state.rol_sel}</h2>', unsafe_allow_html=True)
    
    t_mensajeria_jefe, t_ejecucion, t_tab_auditoria = st.tabs([label_msg, "Ejecución", "📍 TABLERO DE AUDITORÍA"])
    
    with t_mensajeria_jefe:
        renderizar_mensajeria_global(st.session_state.rol_sel)
        
    with t_ejecucion:
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.subheader("ALTA DE RECURSO / OBJETIVO")
            g_alta_nom = st.text_input("Nombre:", key="jefe_alta_nom")
            g_alta_asig = st.selectbox("Asignar a:", LISTA_SUPS_TACTICOS, key="jefe_alta_asig")
            if st.button("Solicitar Alta"):
                escribir_registro_nube("SOLICITUDES DE ACCESO", [obtener_hora_argentina(), st.session_state.user_sel, "ALTA", f"{g_alta_nom} | ASIG: {g_alta_asig}", "PENDIENTE"])
                st.success("✅ Petición enviada")
        with col_g2:
            st.subheader("BAJA DE OBJETIVO")
            g_baja_obj = st.selectbox("Objetivo:", df_objetivos['OBJETIVO'].unique() if not df_objetivos.empty else ["ALFAVINIL"], key="jefe_baja_obj")
            if st.button("Solicitar Baja"):
                escribir_registro_nube("SOLICITUDES DE ACCESO", [obtener_hora_argentina(), st.session_state.user_sel, "BAJA", g_baja_obj, "PENDIENTE"])
                st.success("✅ Petición enviada")
    
    with t_tab_auditoria:
        st.markdown(f"### ⏱️ AUDITORÍA DE TIEMPOS, OBJETIVOS Y FLOTA POR SUPERVISOR")
        df_jornada_aud = leer_matriz_nube("JORNADA SUPERVISORES")
        df_qr_aud = leer_matriz_nube("REGISTRO QR SUPERVISORES")
        df_flota_aud = leer_matriz_nube("CONTROL DE FLOTA")
        df_alertas_aud = leer_matriz_nube("ALERTAS")
        df_vig_rel_aud = leer_matriz_nube("VIGILADORES")
        df_nov_aud = leer_matriz_nube("NOVEDADES GUARDIA")

        supervisores_en_qr_set = set()
        if not df_qr_aud.empty:
            df_qr_aud.columns = [str(c).strip().upper() for c in df_qr_aud.columns]
            col_sup_q = 'SUPERVISOR' if 'SUPERVISOR' in df_qr_aud.columns else df_qr_aud.columns[3]
            if col_sup_q in df_qr_aud.columns:
                for s in df_qr_aud[col_sup_q].dropna().astype(str).str.strip().str.upper():
                    if s and s != "NAN": supervisores_en_qr_set.add(s)

        if not df_jornada_aud.empty:
            df_jornada_aud.columns = [str(c).strip().upper() for c in df_jornada_aud.columns]
            col_sup_j = 'SUPERVISOR' if 'SUPERVISOR' in df_jornada_aud.columns else df_jornada_aud.columns[1]
            if col_sup_j in df_jornada_aud.columns:
                for s in df_jornada_aud[col_sup_j].dropna().astype(str).str.strip().str.upper():
                    if s and s != "NAN": supervisores_en_qr_set.add(s)

        if not df_flota_aud.empty:
            df_flota_aud.columns = [str(c).strip().upper() for c in df_flota_aud.columns]
            col_sup_f = 'SUPERVISOR' if 'SUPERVISOR' in df_flota_aud.columns else df_flota_aud.columns[1]
            if col_sup_f in df_flota_aud.columns:
                for s in df_flota_aud[col_sup_f].dropna().astype(str).str.strip().str.upper():
                    if s and s != "NAN": supervisores_en_qr_set.add(s)

        supervisores_en_qr = sorted(list(supervisores_en_qr_set))

        if len(supervisores_en_qr) > 0:
            pestanas_jefe = st.tabs(supervisores_en_qr)
            
            for idx_pj, sup_seleccionado_jefe in enumerate(supervisores_en_qr):
                with pestanas_jefe[idx_pj]:
                    st.markdown(f"### 🛡️ REPORTE TÁCTICO INTEGRAL: **{sup_seleccionado_jefe}**")
                    
                    inicio_jornada_gen = "---"
                    fin_jornada_gen = "---"
                    total_horas_trabajadas = "---"
                    
                    if not df_jornada_aud.empty:
                        df_jornada_aud.columns = [str(c).strip().upper() for c in df_jornada_aud.columns]
                        col_s_j = df_jornada_aud.columns[1]
                        col_a_j = df_jornada_aud.columns[3]
                        col_h_j = df_jornada_aud.columns[4]
                        
                        df_sup_jor = df_jornada_aud[df_jornada_aud[col_s_j].astype(str).str.strip().str.upper() == str(sup_seleccionado_jefe).strip().upper()]
                        if not df_sup_jor.empty:
                            inicios_jor = df_sup_jor[df_sup_jor[col_a_j].astype(str).str.strip().str.upper() == 'INICIO']
                            fines_jor = df_sup_jor[df_sup_jor[col_a_j].astype(str).str.strip().str.upper() == 'FIN']
                            
                            dt_ini_j = None
                            dt_fin_j = None
                            
                            if not inicios_jor.empty:
                                inicio_jornada_gen = str(inicios_jor.iloc[-1][col_h_j])
                                try:
                                    dt_ini_j = datetime.strptime(inicio_jornada_gen, "%H:%M:%S")
                                except: pass
                            if not fines_jor.empty:
                                fin_jornada_gen = str(fines_jor.iloc[-1][col_h_j])
                                try:
                                    dt_fin_j = datetime.strptime(fin_jornada_gen, "%H:%M:%S")
                                except: pass
                                
                            if dt_ini_j and dt_fin_j and dt_fin_j >= dt_ini_j:
                                dif_j = dt_fin_j - dt_ini_j
                                m_tot_j = int(dif_j.total_seconds() // 60)
                                h_j = m_tot_j // 60
                                mi_j = m_tot_j % 60
                                total_horas_trabajadas = f"{h_j}h {mi_j}m" if h_j > 0 else f"{mi_j} min"

                    c_jor1, c_jor2, c_jor3 = st.columns(3)
                    c_jor1.metric("🚀 INICIO DE JORNADA", inicio_jornada_gen)
                    c_jor2.metric("🏁 CIERRE DE JORNADA", fin_jornada_gen)
                    c_jor3.metric("⏳ TOTAL HORAS TRABAJADAS", total_horas_trabajadas)

                    df_sup_qrs = df_qr_aud[df_qr_aud[col_sup_q].astype(str).str.strip().str.upper() == str(sup_seleccionado_jefe).strip().upper()] if not df_qr_aud.empty and col_sup_q in df_qr_aud.columns else pd.DataFrame()
                    
                    df_tabla_permanencia = pd.DataFrame()
                    if not df_sup_qrs.empty:
                        df_sup_qrs.columns = [str(c).strip().upper() for c in df_sup_qrs.columns]
                        col_fh_qr = df_sup_qrs.columns[0]
                        col_obj_qr = df_sup_qrs.columns[1]
                        col_acc_qr = df_sup_qrs.columns[2]
                        
                        lista_resumen_permanencia = []
                        objetivos_visitados_set = df_sup_qrs[col_obj_qr].dropna().astype(str).str.strip().str.upper().unique()
                        
                        for obj_v in objetivos_visitados_set:
                            df_obj_reg = df_sup_qrs[df_sup_qrs[col_obj_qr].astype(str).str.strip().str.upper() == obj_v]
                            inicios_obj = df_obj_reg[df_obj_reg[col_acc_qr].astype(str).str.strip().str.upper() == 'INICIO']
                            fines_obj = df_obj_reg[df_obj_reg[col_acc_qr].astype(str).str.strip().str.upper() == 'FIN']
                            
                            ingreso_str = "---"
                            egreso_str = "---"
                            permanencia_calc = "---"
                            dt_ing, dt_egr = None, None
                            
                            if not inicios_obj.empty:
                                fh_ing_raw = str(inicios_obj.iloc[-1][col_fh_qr])
                                ingreso_str = fh_ing_raw.split(" ")[1] if " " in fh_ing_raw else fh_ing_raw
                                try: dt_ing = datetime.strptime(ingreso_str, "%H:%M:%S")
                                except: pass
                                
                            if not fines_obj.empty:
                                fh_egr_raw = str(fines_obj.iloc[-1][col_fh_qr])
                                egreso_str = fh_egr_raw.split(" ")[1] if " " in fh_egr_raw else fh_egr_raw
                                try: dt_egr = datetime.strptime(egreso_str, "%H:%M:%S")
                                except: pass
                                
                            if dt_ing and dt_egr and dt_egr >= dt_ing:
                                dif_p = dt_egr - dt_ing
                                m_tot_p = int(dif_p.total_seconds() // 60)
                                hp, mp = m_tot_p // 60, m_tot_p % 60
                                permanencia_calc = f"{hp}h {mp}m" if hp > 0 else f"{mp} min"
                                
                            lista_resumen_permanencia.append({
                                "OBJETIVO": obj_v,
                                "HORARIO INGRESO": ingreso_str,
                                "HORARIO EGRESO": egreso_str,
                                "TIEMPO DE PERMANENCIA": permanencia_calc
                            })
                            
                        df_tabla_permanencia = pd.DataFrame(lista_resumen_permanencia)
                        st.markdown("##### 📍 Detalle de Permanencia por Objetivo (Escaneos QR)")
                        st.dataframe(df_tabla_permanencia, use_container_width=True, hide_index=True)
                    else:
                        st.info("No hay registros de escaneos QR para este supervisor.")

                    st.markdown("---")
                    
                    objs_del_sup = [o.strip().upper() for o in df_objetivos[df_objetivos['SUPERVISOR'].astype(str).str.strip().str.upper() == str(sup_seleccionado_jefe).strip().upper()]['OBJETIVO'].tolist()] if not df_objetivos.empty else []
                    
                    df_fich_filtrado = pd.DataFrame()
                    if not df_nov_aud.empty and len(objs_del_sup) > 0:
                        df_nov_aud.columns = [str(c).strip().upper() for c in df_nov_aud.columns]
                        df_nov_aud['OBJETIVO_CLEAN'] = df_nov_aud['OBJETIVO'].astype(str).str.strip().str.upper() if 'OBJETIVO' in df_nov_aud.columns else ""
                        col_ev = next((p for p in ['TIPO_EVENTO', 'TIPO EVENTO', 'EVENTO', 'TIPO'] if p in df_nov_aud.columns), df_nov_aud.columns[2] if len(df_nov_aud.columns) > 2 else None)
                        if col_ev:
                            mask_f = df_nov_aud['OBJETIVO_CLEAN'].isin(objs_del_sup) & df_nov_aud[col_ev].astype(str).str.upper().str.contains("MARCACIÓN|FICHAJE|INGRESO|EGRESO", regex=True)
                            df_fich_raw = df_nov_aud[mask_f].copy()
                            if not df_fich_raw.empty:
                                filas_fich_limpias = []
                                for _, r in df_fich_raw.iterrows():
                                    fh_val = str(r.iloc[0])
                                    obj_val = str(r.iloc[1])
                                    ev_val = str(r.iloc[2])
                                    nombre_vig = str(r.iloc[4])
                                    leg_val = str(r.iloc[5])
                                    est_val = str(r.iloc[6]) if len(r) > 6 else "PROCESADO"
                                    
                                    ingreso_col = nombre_vig if "INGRESO" in ev_val.upper() or "MARCACIÓN_INGRESO" in ev_val.upper() else "---"
                                    egreso_col = nombre_vig if "EGRESO" in ev_val.upper() or "MARCACIÓN_EGRESO" in ev_val.upper() else "---"
                                    
                                    filas_fich_limpias.append({
                                        "FECHA": fh_val,
                                        "OBJETIVO": obj_val,
                                        "EVENTO": ev_val,
                                        "INGRESO": ingreso_col,
                                        "EGRESO": egreso_col,
                                        "LEGAJO": leg_val,
                                        "ESTADO": est_val
                                    })
                                df_fich_filtrado = pd.DataFrame(filas_fich_limpias)

                    df_rel_filtrado = pd.DataFrame()
                    if not df_vig_rel_aud.empty and len(objs_del_sup) > 0:
                        df_vig_rel_aud.columns = [str(c).strip().upper() for c in df_vig_rel_aud.columns]
                        col_ov = 'OBJETIVO' if 'OBJETIVO' in df_vig_rel_aud.columns else df_vig_rel_aud.columns[2]
                        df_rel_filtrado = df_vig_rel_aud[df_vig_rel_aud[col_ov].astype(str).str.strip().str.upper().isin([o.upper() for o in objs_del_sup])]

                    df_pan_sup_filtrado = pd.DataFrame()
                    if not df_alertas_aud.empty and 'TIPO' in df_alertas_aud.columns:
                        df_pan_op = df_alertas_aud[df_alertas_aud['TIPO'].astype(str).str.strip().str.upper() == "PÁNICO"]
                        mask_s_pan = (df_pan_op['USUARIO'].astype(str).str.strip().str.upper() == sup_seleccionado_jefe)
                        df_pan_sup_filtrado = df_pan_op[mask_s_pan]

                    df_pan_vig_filtrado = pd.DataFrame()
                    if not df_alertas_aud.empty and 'TIPO' in df_alertas_aud.columns:
                        df_pan_op = df_alertas_aud[df_alertas_aud['TIPO'].astype(str).str.strip().str.upper() == "PÁNICO"]
                        mask_v_pan = df_pan_op['OBJETIVO'].astype(str).str.strip().str.upper().isin([o.upper() for o in objs_del_sup])
                        mask_no_sup = ~(df_pan_op['USUARIO'].astype(str).str.strip().str.upper() == sup_seleccionado_jefe)
                        df_pan_vig_filtrado = df_pan_op[mask_v_pan & mask_no_sup]

                    df_alt_sup_filtrado = pd.DataFrame()
                    if not df_alertas_aud.empty:
                        df_alertas_aud.columns = [str(c).strip().upper() for c in df_alertas_aud.columns]
                        df_alt_op = df_alertas_aud[df_alertas_aud['TIPO'].astype(str).str.strip().str.upper() != "PÁNICO"] if 'TIPO' in df_alertas_aud.columns else df_alertas_aud
                        mask_alt = (df_alt_op['OBJETIVO'].astype(str).str.strip().str.upper().isin([o.upper() for o in objs_del_sup]) if 'OBJETIVO' in df_alt_op.columns else False) | \
                                   (df_alt_op['SUPERVISOR'].astype(str).str.strip().str.upper() == sup_seleccionado_jefe if 'SUPERVISOR' in df_alt_op.columns else False)
                        df_alt_sup_filtrado = df_alt_op[mask_alt]

                    df_flota_sup_filtro = pd.DataFrame()
                    if not df_flota_aud.empty:
                        df_flota_aud.columns = [str(c).strip().upper() for c in df_flota_aud.columns]
                        col_sf = 'SUPERVISOR' if 'SUPERVISOR' in df_flota_aud.columns else (df_flota_aud.columns[1] if len(df_flota_aud.columns) > 1 else None)
                        if col_sf:
                            df_flota_sup_filtro = df_flota_aud[df_flota_aud[col_sf].astype(str).str.strip().str.upper() == str(sup_seleccionado_jefe).strip().upper()].copy()

                    st.markdown("---")
                    
                    with st.expander(f"👁️ VISTA PREVIA DEL REPORTE TÁCTICO: {sup_seleccionado_jefe}", expanded=True):
                        st.markdown(f"**Supervisor:** {sup_seleccionado_jefe} | **Emisión:** {obtener_hora_argentina()}")
                        
                        st.markdown("##### ⏱️ Control de Jornada y Horas Trabajadas")
                        df_resumen_jor_prev = pd.DataFrame({
                            "INICIO DE JORNADA": [inicio_jornada_gen],
                            "CIERRE DE JORNADA": [fin_jornada_gen],
                            "TOTAL HORAS TRABAJADAS": [total_horas_trabajadas]
                        })
                        st.dataframe(df_resumen_jor_prev, use_container_width=True, hide_index=True)
                        
                        st.markdown("##### 📍 Detalle de Escaneos QR y Permanencia")
                        if not df_tabla_permanencia.empty:
                            st.dataframe(df_tabla_permanencia, use_container_width=True, hide_index=True)
                        else:
                            st.info("Sin registros QR en este periodo.")
                            
                        st.markdown("##### 📋 Fichaje de Vigiladores")
                        if not df_fich_filtrado.empty:
                            st.dataframe(df_fich_filtrado, use_container_width=True, hide_index=True)
                        else:
                            st.info("Sin fichajes registrados.")

                        st.markdown("##### 🔄 Relevos de Vigiladores")
                        if not df_rel_filtrado.empty:
                            st.dataframe(df_rel_filtrado, use_container_width=True, hide_index=True)
                        else:
                            st.info("Sin relevos registrados.")

                        st.markdown("##### 🚨 Pánicos S.O.S de Supervisor")
                        if not df_pan_sup_filtrado.empty:
                            st.dataframe(df_pan_sup_filtrado.iloc[::-1], use_container_width=True, hide_index=True)
                        else:
                            st.info("Sin pánicos de supervisor.")

                        st.markdown("##### 🚨 Pánicos S.O.S de Vigiladores")
                        if not df_pan_vig_filtrado.empty:
                            df_pan_vig_c_turno = df_pan_vig_filtrado.copy()
                            turnos_vig_list = []
                            for _, f_row in df_pan_vig_c_turno.iterrows():
                                fh_val_p = str(f_row.get('FECHA', ''))
                                turnos_vig_list.append(determinar_turno_activo(fh_val_p))
                            df_pan_vig_c_turno['TURNO VIGILADOR'] = turnos_vig_list
                            st.dataframe(df_pan_vig_c_turno.iloc[::-1], use_container_width=True, hide_index=True)
                        else:
                            st.info("Sin pánicos de vigiladores.")

                        total_alertas_supervisor_j = len(df_pan_sup_filtrado) if not df_pan_sup_filtrado.empty else 0
                        total_alertas_vigilador_j = len(df_pan_vig_filtrado) if not df_pan_vig_filtrado.empty else 0

                        if total_alertas_supervisor_j > 0 or total_alertas_vigilador_j > 0 or not df_alt_sup_filtrado.empty:
                            st.markdown("##### ⚠️ Alertas Operativas")
                            if total_alertas_supervisor_j > 0:
                                st.markdown(f"• TOTAL ALERTAS DE SUPERVISOR: **{total_alertas_supervisor_j}**")
                            if total_alertas_vigilador_j > 0:
                                st.markdown(f"• TOTAL ALERTAS DE VIGILADOR: **{total_alertas_vigilador_j}**")
                            if not df_alt_sup_filtrado.empty:
                                st.dataframe(df_alt_sup_filtrado, use_container_width=True, hide_index=True)

                        st.markdown("##### 🚗 Control de Flota")
                        if not df_flota_sup_filtro.empty:
                            st.dataframe(df_flota_sup_filtro, use_container_width=True, hide_index=True)
                        else:
                            st.info("Sin registros de flota.")

                    st.markdown("---")

                    def generar_pdf_integral_completo(sup_nombre, j_ini, j_fin, j_tot, d_perm, d_fich, d_rel, d_alt, d_psup, d_pvig, d_flota, tot_s_cnt, tot_v_cnt):
                        buffer = io.BytesIO()
                        doc = SimpleDocTemplate(
                            buffer, 
                            pagesize=landscape(letter), 
                            rightMargin=24, 
                            leftMargin=24, 
                            topMargin=24, 
                            bottomMargin=35
                        )
                        elementos = []
                        styles = getSampleStyleSheet()
                        
                        estilo_titulo = ParagraphStyle('T1', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=13, leading=15, textColor=colors.HexColor('#000000'), spaceAfter=2, alignment=1)
                        estilo_sub = ParagraphStyle('T2', parent=styles['Normal'], fontName='Helvetica', fontSize=8.5, leading=10, textColor=colors.HexColor('#333333'), spaceAfter=10, alignment=1)
                        estilo_seccion = ParagraphStyle('T3', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=9.5, leading=11, textColor=colors.HexColor('#000000'), spaceBefore=8, spaceAfter=4)
                        estilo_texto = ParagraphStyle('T4', parent=styles['Normal'], fontName='Helvetica', fontSize=8, leading=10, textColor=colors.HexColor('#333333'))

                        elementos.append(Paragraph("<b>AION-YAROKU | REPORTE TÁCTICO INTEGRAL DE SUPERVISOR</b>", estilo_titulo))
                        elementos.append(Paragraph(f"<b>Supervisor: {sup_nombre}</b> | Emisión: {obtener_hora_argentina()}", estilo_sub))
                        
                        elementos.append(Paragraph("<b>Control de Jornada y Horas Trabajadas:</b>", estilo_seccion))
                        datos_jornada_resumen = [
                            ["INICIO DE JORNADA", "CIERRE DE JORNADA", "TOTAL HORAS TRABAJADAS"],
                            [j_ini, j_fin, j_tot]
                        ]
                        t_jor = Table(datos_jornada_resumen, colWidths=[248, 248, 248])
                        t_jor.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#000000')),
                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                            ('FONTSIZE', (0, 0), (-1, 0), 8),
                            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#FFFFFF')),
                            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#666666')),
                            ('TOPPADDING', (0, 0), (-1, -1), 4),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                        ]))
                        elementos.append(t_jor)
                        elementos.append(Spacer(1, 6))

                        def agregar_tabla_pdf(titulo_sec, df_in, anchos_personalizados=None):
                            elementos.append(Paragraph(f"<b>{titulo_sec}</b>", estilo_seccion))
                            if not df_in.empty:
                                cols = list(df_in.columns)
                                num_cols = len(cols)
                                ancho_total_disponible = 744.0
                                
                                if anchos_personalizados and len(anchos_personalizados) == num_cols:
                                    anchos_lista = anchos_personalizados
                                else:
                                    anchos_lista = [ancho_total_disponible / num_cols] * num_cols

                                estilo_cab = ParagraphStyle('EC', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=7, leading=9, textColor=colors.white, alignment=1)
                                estilo_cel = ParagraphStyle('ECL', parent=styles['Normal'], fontName='Helvetica', fontSize=6.5, leading=8.5, textColor=colors.HexColor('#333333'), alignment=1)

                                datos = []
                                fila_encabezados = [Paragraph(str(c), estilo_cab) for c in cols]
                                datos.append(fila_encabezados)

                                for _, row in df_in.iterrows():
                                    fila_parrafos = []
                                    for c in cols:
                                        val = str(row[c]) if pd.notna(row[c]) else ""
                                        fila_parrafos.append(Paragraph(val, estilo_cel))
                                    datos.append(fila_parrafos)

                                t = Table(datos, colWidths=anchos_lista, repeatRows=1)
                                t.setStyle(TableStyle([
                                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#000000')),
                                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#666666')),
                                    ('TOPPADDING', (0, 1), (-1, -1), 3),
                                    ('BOTTOMPADDING', (0, 1), (-1, -1), 3),
                                    ('LEFTPADDING', (0, 0), (-1, -1), 2),
                                    ('RIGHTPADDING', (0, 0), (-1, -1), 2),
                                ]))
                                elementos.append(t)
                            else:
                                elementos.append(Paragraph("Sin registros en este periodo.", estilo_texto))
                            elementos.append(Spacer(1, 6))

                        agregar_tabla_pdf("Detalle de Escaneos QR y Permanencia por Objetivo:", d_perm, [180, 180, 180, 204])
                        agregar_tabla_pdf("Fichaje de Vigiladores:", d_fich, [80, 110, 100, 90, 90, 90, 184])
                        agregar_tabla_pdf("Relevos de Vigiladores:", d_rel, [60, 100, 120, 120, 70, 90, 184])
                        agregar_tabla_pdf("Pánicos S.O.S de Supervisor:", d_psup)
                        
                        df_pvig_pdf = d_pvig.copy()
                        if not df_pvig_pdf.empty:
                            turnos_vig_pdf_list = []
                            for _, p_row in df_pvig_pdf.iterrows():
                                f_val_p = str(p_row.get('FECHA', ''))
                                turnos_vig_pdf_list.append(determinar_turno_activo(f_val_p))
                            df_pvig_pdf['TURNO VIGILADOR'] = turnos_vig_pdf_list
                        agregar_tabla_pdf("Pánicos S.O.S de Vigiladores:", df_pvig_pdf)
                        
                        if tot_s_cnt > 0 or tot_v_cnt > 0 or not d_alt.empty:
                            elementos.append(Paragraph("<b>Alertas Operativas</b>", estilo_seccion))
                            if tot_s_cnt > 0:
                                elementos.append(Paragraph(f"• TOTAL ALERTAS DE SUPERVISOR: <b>{tot_s_cnt}</b>", estilo_texto))
                            if tot_v_cnt > 0:
                                element = Paragraph(f"• TOTAL ALERTAS DE VIGILADOR: <b>{tot_v_cnt}</b>", estilo_texto)
                                elementos.append(element)
                            elementos.append(Spacer(1, 4))

                            if not d_alt.empty:
                                agregar_tabla_pdf("Detalle de Alertas Operativas:", d_alt)

                        agregar_tabla_pdf("Control de Flota:", d_flota, [75, 70, 70, 60, 100, 90, 90, 189])

                        doc.build(elementos, canvasmaker=NumberedCanvas)
                        buffer.seek(0)
                        return buffer.getvalue()

                    pdf_bytes_integral = generar_pdf_integral_completo(
                        sup_seleccionado_jefe, inicio_jornada_gen, fin_jornada_gen, total_horas_trabajadas,
                        df_tabla_permanencia, df_fich_filtrado, df_rel_filtrado, 
                        df_alt_sup_filtrado, df_pan_sup_filtrado, df_pan_vig_filtrado, df_flota_sup_filtro,
                        total_alertas_supervisor_j, total_alertas_vigilador_j
                    )

                    st.download_button(
                        label=f"📥 DESCARGAR REPORTE TÁCTICO INTEGRAL (PDF COMPLETO) - {sup_seleccionado_jefe}",
                        data=pdf_bytes_integral,
                        file_name=f"reporte_tactico_integral_{sup_seleccionado_jefe.replace(' ', '_')}.pdf",
                        mime="application/pdf",
                        key=f"btn_pdf_integral_jefe_{sup_seleccionado_jefe}_{idx_pj}",
                        use_container_width=True
                    )
        else:
            st.info("No hay registros activos de supervisores en el sistema todavía.")

        if st.session_state.rol_sel == "GERENCIA":
            st.markdown("---")
            st.markdown("### 🔒 PROTOCOLO DE CIERRE TÁCTICO MENSUAL")
            st.info("ℹ️ Esta acción archivará y limpiará las tablas operativas actuales para iniciar un nuevo ciclo.")
            if st.button("EJECUTAR CIERRE TÁCTICO MENSUAL"):
                if ejecutar_cierre_táctico():
                    st.success("✅ ¡Cierre táctico ejecutado con éxito! Ciclo reiniciado.")
                    st.rerun()


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
        df_pan_vig_adm = df_alt_m[
            (df_alt_m['TIPO'].astype(str).str.upper() == "PÁNICO") & 
            (df_alt_m['ESTADO'].astype(str).str.upper() == "PENDIENTE")
        ] if not df_alt_m.empty and 'TIPO' in df_alt_m.columns else pd.DataFrame()
        pend_sos = len(df_pan_vig_adm)

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
            st.markdown("#### 🛡️ RESPALDO Y CAJA FUERTE DIGITAL")
            if not df_obj_m.empty:
                pdf_respaldo_objs = generar_pdf_reporte("RESPALDO GENERAL DE OBJETIVOS ACTIVOS", df_obj_m[['OBJETIVO', 'DIRECCION', 'LOCALIDAD', 'SUPERVISOR']])
                st.download_button("📥 DESCARGAR RESPALDO DE OBJETIVOS (PDF)", data=pdf_respaldo_objs, file_name=f"respaldo_objetivos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf", mime="application/pdf", use_container_width=True, key="dl_pdf_mantenimiento_objetivos")

        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.error("⚠️ Acceso restringido.")
