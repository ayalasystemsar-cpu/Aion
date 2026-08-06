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
    df_nube = leer_matriz_nube("COMISARIAS")
    if not df_nube.empty and 'COMISARIA' in df_nube.columns and len(df_nube) > 1:
        df_nube['LATITUD'] = pd.to_numeric(df_nube['LATITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        df_nube['LONGITUD'] = pd.to_numeric(df_nube['LONGITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        return df_nube
    
    data = {
        "COMISARIA": [
            "COMISARÍA VECINAL 1A", "COMISARÍA VECINAL 1B", "COMISARÍA VECINAL 1C", "COMISARÍA VECINAL 2A", "COMISARÍA VECINAL 2B",
            "COMISARÍA VECINAL 3A", "COMISARÍA VECINAL 3B", "COMISARÍA VECINAL 4A", "COMISARÍA VECINAL 4B", "COMISARÍA VECINAL 4C",
            "COMISARÍA VECINAL 5A", "COMISARÍA VECINAL 5B", "COMISARÍA VECINAL 6A", "COMISARÍA VECINAL 6B", "COMISARÍA VECINAL 7A",
            "COMISARÍA VECINAL 7B", "COMISARÍA VECINAL 8A", "COMISARÍA VECINAL 8B", "COMISARÍA VECINAL 8C", "COMISARÍA VECINAL 9A",
            "COMISARÍA VECINAL 9B", "COMISARÍA VECINAL 9C", "COMISARÍA VECINAL 10A", "COMISARÍA VECINAL 10B", "COMISARÍA VECINAL 10C",
            "COMISARÍA VECINAL 11A", "COMISARÍA VECINAL 11B", "COMISARÍA VECINAL 12A", "COMISARÍA VECINAL 12B", "COMISARÍA VECINAL 12C",
            "COMISARÍA VECINAL 13A", "COMISARÍA VECINAL 13B", "COMISARÍA VECINAL 13C", "COMISARÍA VECINAL 14A", "COMISARÍA VECINAL 14B",
            "COMISARÍA VECINAL 14C", "COMISARÍA VECINAL 15A", "COMISARÍA VECINAL 15B", "COMISARÍA VECINAL 15C", "COMISARÍA SAN MARTÍN 1RA",
            "COMISARÍA AVELLANEDA 1RA", "COMISARÍA CAMPANA 1RA", "COMISARÍA SAN FERNANDO 1RA", "COMISARÍA TIGRE 1RA", "COMISARÍA PILAR 6TA",
            "COMISARÍA ESCOBAR 3RA", "COMISARÍA VICENTE LÓPEZ 2DA", "COMISARÍA SAN ISIDRO 1RA", "COMISARÍA LANÚS 1RA", "COMISARÍA LOMAS DE ZAMORA 1RA",
            "COMISARÍA MORÓN 1RA", "COMISARÍA LA MATANZA 1RA", "COMISARÍA TRES DE FEBRERO 1RA", "COMISARÍA QUILMES 1RA", "COMISARÍA VARELA 1RA",
            "COMISARÍA BERAZATEGUI 1RA", "COMISARÍA TIGRE 2DA (PACHECO)", "COMISARÍA ESCOBAR 1RA (BELÉN)", "COMISARÍA PILAR 1RA", "COMISARÍA ZÁRATE 1RA",
            "COMISARÍA CAMPANA 2DA", "COMISARÍA EXALTACIÓN DE LA CRUZ (CARDALES)", "COMISARÍA LUJÁN 1RA", "COMISARÍA MERCEDES 1RA", "COMISARÍA SAN ANDRÉS DE GILES",
            "COMISARÍA GENERAL SAN MARTÍN 2DA", "COMISARÍA VICENTE LÓPEZ 1RA", "COMISARÍA SAN ISIDRO 4TA (MARTÍNEZ)", "COMISARÍA SAN FERNANDO 2DA (VIRREYES)", "COMISARÍA TIGRE 3RA (DON TORCUATO)",
            "COMISARÍA MALVINAS ARGENTINAS 1RA", "COMISARÍA J. C. PAZ 1RA", "COMISARÍA SAN MIGUEL 1RA", "COMISARÍA MORENO 1RA", "COMISARÍA MERLO 1RA"
        ],
        "DIRECCION": [
            "Suipacha 1156", "Uruguay 350", "Tacuarí 770", "General Las Heras 2650", "Paraguay 1122",
            "Lavalle 2625", "San Juan 1767", "Zavaleta 425", "Av. Regimiento de Patricios 1150", "Benito Juárez 1445",
            "Maza 1250", "Av. Independencia 2250", "Av. La Plata 550", "Rivadavia 4701", "Piedras 1450",
            "Av. Directorio 1500", "Dellepiane 6900", "Av. General Paz 14500", "Av. Cruz 4500", "Av. Juan B. Alberdi 6752",
            "Coronel Cárdenas 2850", "Toneleroro 6400", "Segurola 1550", "Av. Gaona 3850", "Alejandro Magariños Cervantes 4525",
            "Av. Nazca 4550", "Cuenca 3250", "Miller 2750", "Arias 4450", "Manuela Pedraza 2340",
            "Av. Cabildo 2300", "Amenábar 2320", "Av. Cramer 3250", "Cnel. Díaz 2250", "Av. Coronel Díaz 2550",
            "Av. Santa Fe 3200", "Guzmán 346", "Av. Forest 1450", "Av. Triunvirato 4550", "Gral. Lavalle 420",
            "Gral. Lavalle 150", "Rivadavia 750", "Constitución 720", "Cazón 1250", "Ruta 25 s/n",
            "Belgrano 1150", "Av. San Martín 2450", "25 de Mayo 450", "Yrigoyen 300", "Chacabuco 500",
            "San Martín 750", "Arieta 2500", "Belgrano 3400", "Rivadavia 400", "San Martín 800",
            "Mitre 600", "Av. Constituyentes 450", "Asborno 750", "San Martín 950", "Justa Lima 450",
            "Mitre 1200", "Belgrano 600", "San Martín 500", "Calle 24 Nro 650", "Mitre 400",
            "Mitre 1500", "Maipú 2500", "Alvear 500", "Av. Avellaneda 1200", "Alvear 800",
            "Perón 1200", "Hipólito Yrigoyen 500", "Perón 800", "Alcorta 400", "Suipacha 300"
        ],
        "LOCALIDAD": [
            "CABA", "CABA", "CABA", "CABA", "CABA", "CABA", "CABA", "CABA", "CABA", "CABA",
            "CABA", "CABA", "CABA", "CABA", "CABA", "CABA", "CABA", "CABA", "CABA", "CABA",
            "CABA", "CABA", "CABA", "CABA", "CABA", "CABA", "CABA", "CABA", "CABA", "CABA",
            "CABA", "CABA", "CABA", "CABA", "CABA", "CABA", "CABA", "CABA", "CABA", "SAN MARTÍN",
            "AVELLANEDA", "CAMPANA", "SAN FERNANDO", "TIGRE", "PILAR", "GARÍN", "FLORIDA", "SAN ISIDRO", "LANÚS", "LOMAS DE ZAMORA",
            "MORÓN", "LA MATANZA", "TRES DE FEBRERO", "QUILMES", "VARELA", "BERAZATEGUI", "PACHECO", "ESCÓBAR", "PILAR", "ZÁRATE",
            "CAMPANA", "CARDALES", "LUJÁN", "MERCEDES", "GILES", "SAN MARTÍN", "VICENTE LÓPEZ", "MARTÍNEZ", "VIRREYES", "DON TORCUATO",
            "MALVINAS ARGENTINAS", "J. C. PAZ", "SAN MIGUEL", "MORENO", "MERLO"
        ],
        "TELEFONO": [
            "011-4393-0100", "011-4371-0100", "011-4331-0100", "011-4803-0100", "011-4811-0100",
            "011-4381-0100", "011-4952-0100", "011-4301-0100", "011-4361-0100", "011-4683-0100",
            "011-4931-0100", "011-4304-0100", "011-4923-0100", "011-4982-0100", "011-4342-0100",
            "011-4631-0100", "011-4637-0100", "011-4696-0100", "011-4919-0100", "011-4641-0100",
            "011-4682-0100", "011-4642-0100", "011-4567-0100", "011-4581-0100", "011-4585-0100",
            "011-4501-0100", "011-4571-0100", "011-4541-1122", "011-4542-3344", "011-4572-0100",
            "011-4788-9900", "011-4781-0100", "011-4552-0100", "011-4821-5544", "011-4822-0100",
            "011-4813-0100", "011-4554-0100", "011-4555-0100", "011-4521-0100", "011-4754-2321",
            "011-4201-1122", "03489-422111", "011-4744-0192", "011-4512-9900", "0230-449-0111",
            "03327-442000", "011-4791-0000", "011-4743-0100", "011-4241-0100", "011-4243-0100",
            "011-4483-0100", "011-4482-0100", "011-4751-0100", "011-4253-0100", "011-4255-0100",
            "011-4256-0100", "011-4740-0100", "0348-442-0100", "0230-442-0100", "03487-422-0100",
            "03489-423-0100", "02322-490-100", "02323-420-100", "02324-420-100", "02326-452-100",
            "011-4752-0100", "011-4797-0100", "011-4792-0100", "011-4745-0100", "011-4717-0100",
            "02320-482-100", "02320-432-100", "02323-442-100", "0237-482-0100", "0220-482-0100"
        ],
        "LATITUD": [
            -34.5985, -34.6037, -34.6112, -34.5852, -34.5910, -34.6080, -34.6150, -34.6390, -34.6350, -34.6410,
            -34.6150, -34.6220, -34.6250, -34.6180, -34.6190, -34.6280, -34.6500, -34.6750, -34.6600, -34.6400,
            -34.6450, -34.6500, -34.6200, -34.6150, -34.6100, -34.6000, -34.5950, -34.5543, -34.5684, -34.5600,
            -34.5574, -34.5550, -34.5500, -34.5877, -34.5850, -34.5800, -34.5880, -34.5800, -34.5750, -34.5801,
            -34.6641, -34.1636, -34.4401, -34.4241, -34.4170, -34.4273, -34.5453, -34.4720, -34.7000, -34.7600,
            -34.6500, -34.6700, -34.5800, -34.7200, -34.8100, -34.7600, -34.4600, -34.3400, -34.4500, -34.0900,
            -34.1700, -34.2900, -34.5700, -34.6500, -34.2500, -34.5800, -34.5100, -34.4900, -34.4500, -34.4700,
            -34.4800, -34.5100, -34.5300, -34.6500, -34.6700
        ],
        "LONGITUD": [
            -58.3838, -58.3862, -58.3790, -58.4012, -58.3950, -58.3850, -58.3800, -58.4050, -58.3650, -58.4800,
            -58.4200, -58.3830, -58.4400, -58.4350, -58.3750, -58.4600, -58.4500, -58.4650, -58.4450, -58.5100,
            -58.5050, -58.5200, -58.4900, -58.4600, -58.4750, -58.4950, -58.4700, -58.4721, -58.4820, -58.4600,
            -58.4611, -58.4550, -58.4500, -58.4160, -58.4100, -58.3950, -58.4700, -58.4600, -58.4800, -58.5414,
            -58.3680, -58.9614, -58.5561, -58.5797, -58.8682, -58.7205, -58.4937, -58.5100, -58.3700, -58.4000,
            -58.6200, -58.5600, -58.5400, -58.2700, -58.2800, -58.2100, -58.6300, -58.7900, -58.9000, -58.8500,
            -58.9700, -58.9100, -59.5400, -59.4300, -59.7100, -58.5500, -58.4800, -58.5200, -58.5400, -58.6000,
            -58.7000, -58.7100, -58.7200, -58.9000, -58.7100
        ]
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
    base = ["AYALA BRIAN", "SUPERVISOR 1", "SUPERVISOR 2", "SUPERVISOR 3", "SUPERVISOR 4", "SUPERVISOR 5", "SUPERVISOR NOCTURNO", "CONTROLADOR NOCTURNO", "TIKI", "GONZALEZ"]
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

        header { background: transparent !important; background-color: transparent !important; }

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
        
        .stTabs [data-baseweb="tab-list"] {
            gap: 6px !important; background-color: transparent !important; flex-wrap: nowrap !important; overflow-x: auto !important; white-space: nowrap !important; padding-bottom: 5px !important;
        }
        .stTabs [data-baseweb="tab"] {
            background-color: rgba(26, 28, 35, 0.6) !important; border: 1px solid #2D313E !important; color: #A0A5B5 !important;
            border-radius: 4px 4px 0px 0px !important; padding: 8px 12px !important; font-family: 'Orbitron', sans-serif; font-size: 11px !important; font-weight: bold; flex-shrink: 0 !important;
        }
        .stTabs [aria-selected="true"] { background-color: #1A1C23 !important; border-top: 2px solid #00E5FF !important; color: #00E5FF !important; }
        
        div[data-testid="stMetric"] { background-color: rgba(10, 11, 15, 0.6) !important; border: 1px solid #1A1C23 !important; border-radius: 6px !important; padding: 8px !important; }
        div[data-testid="stMetricLabel"] p { color: #00E5FF !important; font-family: 'Rajdhani', sans-serif !important; font-size: 12px !important; font-weight: bold !important; text-transform: uppercase; letter-spacing: 0.5px; }
        div[data-testid="stMetricValue"] div { color: #FFFFFF !important; font-family: 'Orbitron', sans-serif !important; font-size: 18px !important; unicode-bidi: plaintext !important; direction: ltr !important; }
        
        div[data-testid="stDataFrame"] { width: 100% !important; overflow-x: auto !important; }
        </style>
    """, unsafe_allow_html=True)

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

            else:
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
                        sincronizar_url_sesion()
                        st.rerun()
                    else:
                        st.warning("⚠️ Tu cuenta existe pero está PENDIENTE de aprobación.")
                else:
                    st.error("❌ Credenciales inválidas.")

if not st.session_state.usuario_logueado:
    mostrar_landing()
    st.stop()

aplicar_identidad_alfa()

df_objetivos = cargar_objetivos()
LISTA_SUPS_TACTICOS = obtener_lista_supervisores_dinamica()

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

# =========================================================================
# ROL: JEFE DE OPERACIONES / GERENCIA ( CON LOS CUADROS DE PÁNICOS Y FLOTA EXACTOS )
# =========================================================================
if st.session_state.rol_sel in ["JEFE DE OPERACIONES", "GERENCIA", "MONITOREO"]:
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

    st.markdown(f'<h2 style="color:#00E5FF; font-family:\'Orbitron\'; font-size:24px;">Comando: {st.session_state.rol_sel}</h2>', unsafe_allow_html=True)
    
    t_mensajeria_jefe, t_ejecucion, t_tab_auditoria = st.tabs(["💬 MENSAJERÍA", "Ejecución", "📍 TABLERO DE AUDITORÍA"])
    
    with t_mensajeria_jefe:
        renderizar_mensajeria_global(st.session_state.rol_sel)
        
    with t_ejecucion:
        st.markdown("### 🚨 Pánicos S.O.S de Supervisor")
        df_alertas_jefe = leer_matriz_nube("ALERTAS")
        if not df_alertas_jefe.empty:
            df_alertas_jefe.columns = [str(c).strip().upper() for c in df_alertas_jefe.columns]
            panicos_pendientes_jefe = df_alertas_jefe[
                (df_alertas_jefe['TIPO'].astype(str).str.upper() == "PÁNICO") & 
                (df_alertas_jefe['ESTADO'].astype(str).str.upper() == "PENDIENTE")
            ] if 'TIPO' in df_alertas_jefe.columns and 'ESTADO' in df_alertas_jefe.columns else pd.DataFrame()
            
            if not panicos_pendientes_jefe.empty:
                st.dataframe(panicos_pendientes_jefe[['FECHA', 'USUARIO', 'TIPO', 'ESTADO', 'OBJETIVO', 'SUPERVISOR']], use_container_width=True, hide_index=True)
            else:
                st.info("No hay pánicos de supervisor pendientes.")

            st.markdown("### 🚨 Pánicos S.O.S de Vigiladores")
            df_pan_vigiladores = panicos_pendientes_jefe[panicos_pendientes_jefe['USUARIO'].astype(str).str.strip().str.upper() != panicos_pendientes_jefe['SUPERVISOR'].astype(str).str.strip().str.upper()] if not panicos_pendientes_jefe.empty else pd.DataFrame()
            if not df_pan_vigiladores.empty:
                st.dataframe(df_pan_vigiladores[['FECHA', 'USUARIO', 'TIPO', 'ESTADO', 'OBJETIVO', 'SUPERVISOR']], use_container_width=True, hide_index=True)
            else:
                st.info("No hay pánicos de vigiladores activos.")

            st.markdown("### ⚠️ Alertas Operativas")
            tot_sup_alert = len(panicos_pendientes_jefe)
            tot_vig_alert = len(df_pan_vigiladores)
            st.markdown(f"- **Total alertas de supervisor:** {tot_sup_alert}")
            st.markdown(f"- **Total alertas de vigilador:** {tot_vig_alert}")
        else:
            st.info("Sin registros de alertas.")

        st.markdown("---")
        st.markdown("### 🚗 Control de Flota")
        df_flota_jefe_sec = leer_matriz_nube("CONTROL DE FLOTA")
        if not df_flota_jefe_sec.empty:
            st.dataframe(df_flota_jefe_sec, use_container_width=True, hide_index=True)
        else:
            st.info("No hay registros de control de flota.")
    
    with t_tab_auditoria:
        st.markdown(f"### ⏱️ AUDITORÍA DE TIEMPOS, OBJETIVOS Y FLOTA POR SUPERVISOR")
        df_jornada_aud = leer_matriz_nube("JORNADA SUPERVISORES")
        df_qr_aud = leer_matriz_nube("REGISTRO QR SUPERVISORES")
        df_flota_aud = leer_matriz_nube("CONTROL DE FLOTA")
        df_alertas_aud = leer_matriz_nube("ALERTAS")
        df_vig_rel_aud = leer_matriz_nube("VIGILADORES")
        df_nov_aud = leer_matriz_nube("NOVEDADES GUARDIA")

        supervisores_en_qr_set = set()
        for df_tmp in [df_qr_aud, df_jornada_aud, df_flota_aud]:
            if not df_tmp.empty:
                col_s = next((c for c in ['SUPERVISOR'] if c in df_tmp.columns), df_tmp.columns[1] if len(df_tmp.columns) > 1 else None)
                if col_s:
                    for s in df_tmp[col_s].dropna().astype(str).str.strip().str.upper():
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
                            
                            dt_ini_j, dt_fin_j = None, None
                            if not inicios_jor.empty:
                                inicio_jornada_gen = str(inicios_jor.iloc[-1][col_h_j])
                                try: dt_ini_j = datetime.strptime(inicio_jornada_gen, "%H:%M:%S")
                                except: pass
                            if not fines_jor.empty:
                                fin_jornada_gen = str(fines_jor.iloc[-1][col_h_j])
                                try: dt_fin_j = datetime.strptime(fin_jornada_gen, "%H:%M:%S")
                                except: pass
                                
                            if dt_ini_j and dt_fin_j and dt_fin_j >= dt_ini_j:
                                dif_j = dt_fin_j - dt_ini_j
                                m_tot_j = int(dif_j.total_seconds() // 60)
                                h_j, mi_j = m_tot_j // 60, m_tot_j % 60
                                total_horas_trabajadas = f"{h_j}h {mi_j}m" if h_j > 0 else f"{mi_j} min"

                    c_jor1, c_jor2, c_jor3 = st.columns(3)
                    c_jor1.metric("🚀 INICIO DE JORNADA", inicio_jornada_gen)
                    c_jor2.metric("🏁 CIERRE DE JORNADA", fin_jornada_gen)
                    c_jor3.metric("⏳ TOTAL HORAS TRABAJADAS", total_horas_trabajadas)

                    # --- DETALLE DE PERMANENCIA QR ---
                    df_sup_qrs = df_qr_aud[df_qr_aud['SUPERVISOR'].astype(str).str.strip().str.upper() == str(sup_seleccionado_jefe).strip().upper()] if not df_qr_aud.empty and 'SUPERVISOR' in df_qr_aud.columns else pd.DataFrame()
                    df_tabla_permanencia = pd.DataFrame()
                    if not df_sup_qrs.empty:
                        df_sup_qrs.columns = [str(c).strip().upper() for c in df_sup_qrs.columns]
                        col_fh_qr, col_obj_qr, col_acc_qr = df_sup_qrs.columns[0], df_sup_qrs.columns[1], df_sup_qrs.columns[2]
                        
                        lista_resumen_permanencia = []
                        for obj_v in df_sup_qrs[col_obj_qr].dropna().astype(str).str.strip().str.upper().unique():
                            df_obj_reg = df_sup_qrs[df_sup_qrs[col_obj_qr].astype(str).str.strip().str.upper() == obj_v]
                            inicios_obj = df_obj_reg[df_obj_reg[col_acc_qr].astype(str).str.strip().str.upper() == 'INICIO']
                            fines_obj = df_obj_reg[df_obj_reg[col_acc_qr].astype(str).str.strip().str.upper() == 'FIN']
                            
                            ingreso_str, egreso_str, permanencia_calc = "---", "---", "---"
                            dt_ing, dt_egr = None, None
                            if not inicios_obj.empty:
                                ingreso_str = str(inicios_obj.iloc[-1][col_fh_qr]).split(" ")[-1]
                                try: dt_ing = datetime.strptime(ingreso_str, "%H:%M:%S")
                                except: pass
                            if not fines_obj.empty:
                                egreso_str = str(fines_obj.iloc[-1][col_fh_qr]).split(" ")[-1]
                                try: dt_egr = datetime.strptime(egreso_str, "%H:%M:%S")
                                except: pass
                            if dt_ing and dt_egr and dt_egr >= dt_ing:
                                m_tot_p = int((dt_egr - dt_ing).total_seconds() // 60)
                                permanencia_calc = f"{m_tot_p // 60}h {m_tot_p % 60}m" if m_tot_p >= 60 else f"{m_tot_p} min"
                                
                            lista_resumen_permanencia.append({"OBJETIVO": obj_v, "HORARIO INGRESO": ingreso_str, "HORARIO EGRESO": egreso_str, "TIEMPO DE PERMANENCIA": permanencia_calc})
                        df_tabla_permanencia = pd.DataFrame(lista_resumen_permanencia)

                    # --- FICHES Y RELEVOS ---
                    objs_del_sup = [o.strip().upper() for o in df_objetivos[df_objetivos['SUPERVISOR'].astype(str).str.strip().str.upper() == str(sup_seleccionado_jefe).strip().upper()]['OBJETIVO'].tolist()] if not df_objetivos.empty else []
                    
                    df_fich_filtrado = pd.DataFrame()
                    if not df_nov_aud.empty and len(objs_del_sup) > 0:
                        df_nov_aud.columns = [str(c).strip().upper() for c in df_nov_aud.columns]
                        df_nov_aud['OBJETIVO_CLEAN'] = df_nov_aud['OBJETIVO'].astype(str).str.strip().str.upper() if 'OBJETIVO' in df_nov_aud.columns else ""
                        mask_f = df_nov_aud['OBJETIVO_CLEAN'].isin(objs_del_sup) & df_nov_aud.iloc[:, 2].astype(str).str.upper().str.contains("MARCACIÓN|FICHAJE|INGRESO|EGRESO", regex=True)
                        df_fich_raw = df_nov_aud[mask_f].copy()
                        if not df_fich_raw.empty:
                            filas_f = []
                            for _, r in df_fich_raw.iterrows():
                                filas_f.append({
                                    "FECHA": str(r.iloc[0]), "OBJETIVO": str(r.iloc[1]), "EVENTO": str(r.iloc[2]),
                                    "INGRESO": str(r.iloc[4]) if "INGRESO" in str(r.iloc[2]).upper() else "---",
                                    "EGRESO": str(r.iloc[4]) if "EGRESO" in str(r.iloc[2]).upper() else "---",
                                    "LEGAJO": str(r.iloc[5]), "ESTADO": str(r.iloc[6]) if len(r) > 6 else "PROCESADO"
                                })
                            df_fich_filtrado = pd.DataFrame(filas_f)

                    df_rel_filtrado = pd.DataFrame()
                    if not df_vig_rel_aud.empty and len(objs_del_sup) > 0:
                        df_vig_rel_aud.columns = [str(c).strip().upper() for c in df_vig_rel_aud.columns]
                        df_rel_filtrado = df_vig_rel_aud[df_vig_rel_aud['OBJETIVO'].astype(str).str.strip().str.upper().isin([o.upper() for o in objs_del_sup])]

                    df_flota_sup_filtro = df_flota_aud[df_flota_aud['SUPERVISOR'].astype(str).str.strip().str.upper() == str(sup_seleccionado_jefe).strip().upper()].copy() if not df_flota_aud.empty and 'SUPERVISOR' in df_flota_aud.columns else pd.DataFrame()

                    # --- FILTROS DE PÁNICOS Y ALERTAS ESPECÍFICOS PARA ESTE SUPERVISOR ---
                    df_alertas_sup_filtro = df_alertas_aud[df_alertas_aud['SUPERVISOR'].astype(str).str.strip().str.upper() == str(sup_seleccionado_jefe).strip().upper()] if not df_alertas_aud.empty and 'SUPERVISOR' in df_alertas_aud.columns else pd.DataFrame()
                    
                    df_pan_sup_reporte = df_alertas_sup_filtro[
                        (df_alertas_sup_filtro['TIPO'].astype(str).str.upper() == "PÁNICO") & 
                        (df_alertas_sup_filtro['USUARIO'].astype(str).str.strip().str.upper() == str(sup_seleccionado_jefe).strip().upper())
                    ] if not df_alertas_sup_filtro.empty else pd.DataFrame()

                    df_pan_vig_reporte = df_alertas_sup_filtro[
                        (df_alertas_sup_filtro['TIPO'].astype(str).str.upper() == "PÁNICO") & 
                        (df_alertas_sup_filtro['USUARIO'].astype(str).str.strip().str.upper() != str(sup_seleccionado_jefe).strip().upper())
                    ] if not df_alertas_sup_filtro.empty else pd.DataFrame()

                    tot_alert_s = len(df_pan_sup_reporte)
                    tot_alert_v = len(df_pan_vig_reporte)

                    st.markdown("---")
                    
                    # --- VISTA PREVIA IDÉNTICA A LA SEGUNDA CAPTURA ---
                    with st.expander(f"👁️ VISTA PREVIA DEL REPORTE TÁCTICO: {sup_seleccionado_jefe}", expanded=True):
                        st.markdown(f"**Supervisor:** {sup_seleccionado_jefe} | **Emisión:** {obtener_hora_argentina()}")
                        
                        st.markdown("##### ⏱️ Control de Jornada y Horas Trabajadas")
                        st.dataframe(pd.DataFrame({
                            "INICIO DE JORNADA": [inicio_jornada_gen],
                            "CIERRE DE JORNADA": [fin_jornada_gen],
                            "TOTAL HORAS TRABAJADAS": [total_horas_trabajadas]
                        }), use_container_width=True, hide_index=True)
                        
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

                        # === AQUÍ ESTABAN LOS CUADROS QUE FALTABAN EN LA FOTO 1 ===
                        st.markdown("##### 🚨 Pánicos S.O.S de Supervisor")
                        if not df_pan_sup_reporte.empty:
                            st.dataframe(df_pan_sup_reporte[['FECHA', 'USUARIO', 'TIPO', 'ESTADO', 'OBJETIVO', 'SUPERVISOR']], use_container_width=True, hide_index=True)
                        else:
                            st.info("Sin pánicos de supervisor registrados.")

                        st.markdown("##### 🚨 Pánicos S.O.S de Vigiladores")
                        if not df_pan_vig_reporte.empty:
                            st.dataframe(df_pan_vig_reporte[['FECHA', 'USUARIO', 'TIPO', 'ESTADO', 'OBJETIVO', 'SUPERVISOR']], use_container_width=True, hide_index=True)
                        else:
                            st.info("Sin pánicos de vigiladores registrados.")

                        st.markdown("##### ⚠️ Alertas Operativas")
                        st.markdown(f"- **Total alertas de supervisor:** {tot_alert_s}")
                        st.markdown(f"- **Total alertas de vigilador:** {tot_alert_v}")
                        # ========================================================

                        st.markdown("##### 🚗 Control de Flota")
                        if not df_flota_sup_filtro.empty:
                            st.dataframe(df_flota_sup_filtro, use_container_width=True, hide_index=True)
                        else:
                            st.info("Sin registros de flota.")
