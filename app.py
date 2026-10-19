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
import calendar
import re
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
import os, tempfile

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

if 'obj_actual_vig' not in st.session_state and query_params.get("obj"):
    st.session_state.obj_actual_vig = query_params.get("obj")

def sincronizar_url_sesion():
    params = {
        "logueado": "true" if st.session_state.usuario_logueado else "false",
        "rol": st.session_state.rol_sel,
        "user": st.session_state.user_sel,
        "sup_auth": "true" if st.session_state.sup_autenticado else "false",
        "admin_auth": "true" if st.session_state.admin_autenticado else "false"
    }
    if st.session_state.get("obj_actual_vig"):
        params["obj"] = st.session_state.obj_actual_vig
    st.query_params.update(params)

# --- 3. CONEXIONES Y FUNCIONES GLOBALES OPTIMIZADAS ---
ID_MAESTRO_DB = "1Md0VkOnwUJWldq0S1fB9UrmOKv4MG__JVG3tQsda0Uw"

@st.cache_resource(show_spinner=False)
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
        "SOLICITUDES ACCESO": "SOLICITUDES ACCESO",
        "OBJETIVOS": "OBJETIVOS",
        "COMISARIAS": "COMISARIAS",
        "USUARIOS": "USUARIOS",
        "ALERTAS": "ALERTAS",
        "MENSAJERIA": "MENSAJERIA",
        "NOTIFICACIONES_SUPERVISORES": "NOTIFICACIONES_SUPERVISORES",
        "PRESENTISMO": "PRESENTISMO",
        "VIGILADORES": "VIGILADORES",
        "PADRON VIGILADORES": "PADRON VIGILADORES",
        "RECORRIDOS PUNTOS": "RECORRIDOS PUNTOS",
        "REGISTRO RECORRIDOS": "REGISTRO RECORRIDOS"
    }

def actualizar_celda(pestana, fila, columna, valor):
    try:
        gc = conectar_google()
        if gc:
            sh = gc.open_by_key(ID_MAESTRO_DB)
            nombre_hoja_real = obtener_mapeo_solapas().get(pestana.upper().strip(), pestana)
            try:
                hoja = sh.worksheet(nombre_hoja_real)
            except:
                hoja = sh.add_worksheet(title=nombre_hoja_real, rows="100", cols="10")
            hoja.update_acell(f"{columna}{fila}", valor)
            st.cache_data.clear()
            return True
    except Exception as e: 
        print(f"Error actualizando celda en {pestana}: {e}")
        return False

def actualizar_estado_usuario(fila_sheet, nuevo_estado):
    try:
        gc = conectar_google()
        hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet("USUARIOS")
        encabezados = [str(h).strip().upper() for h in hoja.row_values(1)]
        col = encabezados.index("ESTADO") + 1
        hoja.update_cell(fila_sheet, col, nuevo_estado)
        st.cache_data.clear()
        return True
    except Exception as e:
        print(f"Error actualizando estado de usuario: {e}")
        return False

def actualizar_estado_padron(fila_sheet, nuevo_estado):
    try:
        gc = conectar_google()
        hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet("PADRON VIGILADORES")
        encabezados = [str(h).strip().upper() for h in hoja.row_values(1)]
        col = encabezados.index("ESTADO") + 1
        hoja.update_cell(fila_sheet, col, nuevo_estado)
        st.cache_data.clear()
        return True
    except Exception as e:
        print(f"Error actualizando estado en padrón: {e}")
        return False

def escribir_registro_nube(pestana, datos_fila):
    try:
        gc = conectar_google()
        if gc:
            sh = gc.open_by_key(ID_MAESTRO_DB)
            nombre_hoja_real = obtener_mapeo_solapas().get(pestana.upper().strip(), pestana)
            try:
                hoja = sh.worksheet(nombre_hoja_real)
            except:
                hoja = sh.add_worksheet(title=nombre_hoja_real, rows="100", cols="15")
                if nombre_hoja_real == "NOTIFICACIONES_SUPERVISORES":
                    hoja.append_row(["FECHA_HORA", "SUPERVISOR", "MENSAJE", "ESTADO"])
            hoja.append_row(datos_fila)
            st.cache_data.clear() 
            return True
    except Exception as e:
        print(f"Error de nube en {pestana}: {e}")
        st.error(f"⚠️ Error técnico en nube ({pestana}): {e}")
        return False

@st.cache_data(ttl=30, show_spinner=False)
def leer_matriz_nube(pestana):
    gc = conectar_google()
    if gc:
        try:
            sh = gc.open_by_key(ID_MAESTRO_DB)
            nombre_hoja_real = obtener_mapeo_solapas().get(pestana.upper().strip(), pestana)
            try:
                hoja = sh.worksheet(nombre_hoja_real)
            except:
                if pestana.upper().strip() == "NOTIFICACIONES_SUPERVISORES":
                    hoja = sh.add_worksheet(title="NOTIFICACIONES_SUPERVISORES", rows="100", cols="15")
                    hoja.append_row(["FECHA_HORA", "SUPERVISOR", "MENSAJE", "ESTADO"])
                else:
                    return pd.DataFrame()
            
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

@st.cache_data(ttl=60, show_spinner=False)
def cargar_datos_comisarias():
    df_nube = leer_matriz_nube("COMISARIAS")
    if not df_nube.empty and 'COMISARIA' in df_nube.columns:
        df_nube['LATITUD'] = pd.to_numeric(df_nube['LATITUD'].astype(str).str.replace(',', '.'), errors='coerce')
        df_nube['LONGITUD'] = pd.to_numeric(df_nube['LONGITUD'].astype(str).str.replace(',', '.'), errors='coerce')
    else:
        df_nube = pd.DataFrame()
     
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
    df_base = pd.DataFrame(data)
    if df_nube.empty:
        return df_base
    df_total = pd.concat([df_nube, df_base], ignore_index=True)
    df_total['_KEY'] = df_total['COMISARIA'].astype(str).str.strip().str.upper()
    df_total = df_total.drop_duplicates(subset='_KEY', keep='first').drop(columns='_KEY')
    df_total = df_total.dropna(subset=['LATITUD', 'LONGITUD'])
    return df_total.reset_index(drop=True)

@st.cache_data(ttl=30, show_spinner=False)
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

@st.cache_resource(show_spinner=False)
def obtener_grafo_zona(lat, lon):
    try:
        return ox.graph_from_point((lat, lon), dist=5000, network_type='drive')
    except:
        return None

@st.cache_resource(show_spinner=False)
def _declarar_visor_qr(version="v6"):
    carpeta = tempfile.mkdtemp(prefix=f"aion_qr_{version}_")
    js = ""
    for url in [
        "https://cdn.jsdelivr.net/npm/jsQR@1.4.0/dist/jsQR.js",
        "https://cdnjs.cloudflare.com/ajax/libs/jsQR/1.4.0/jsQR.min.js",
        "https://unpkg.com/jsqr@1.4.0/dist/jsQR.js",
    ]:
        try:
            r = requests.get(url, timeout=10)
            if r.ok and len(r.text) > 20000:
                js = r.text
                break
        except Exception:
            continue
    if js:
        with open(os.path.join(carpeta, "jsQR.js"), "w", encoding="utf-8") as f:
            f.write(js)
        tag = '<script src="jsQR.js"></script>'
    else:
        tag = '<script src="https://cdn.jsdelivr.net/npm/jsQR@1.4.0/dist/jsQR.js"></script>'
    html = _QR_HTML.replace("<!--JSQR_SCRIPT-->", tag)
    with open(os.path.join(carpeta, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    return components.declare_component(f"aion_visor_qr_{version}", path=carpeta)

def verificar_e_insertar_comisaria_automatica(com_n, com_d, com_l, com_t, lat, lon):
    try:
        gc = conectar_google()
        if gc:
            sh = gc.open_by_key(ID_MAESTRO_DB)
            try:
                hoja_comis = sh.worksheet("COMISARIAS")
            except:
                hoja_comis = sh.add_worksheet(title="COMISARIAS", rows="100", cols="10")
                hoja_comis.append_row(["COMISARIA", "DIRECCION", "LOCALIDAD", "TELEFONO", "LATITUD", "LONGITUD"])

            registros_existentes = hoja_comis.get_all_values()
            encontrada = False
            for fila_c in registros_existentes[1:]:
                if len(fila_c) > 0 and str(fila_c[0]).strip().upper() == str(com_n).strip().upper():
                    encontrada = True
                    break
             
            if not encontrada and str(com_n).strip() != "" and str(com_n).strip() != "---":
                hoja_comis.append_row([
                    str(com_n).strip().upper(), 
                    str(com_d).strip().upper(), 
                    str(com_l).strip().upper(), 
                    str(com_t).strip(), 
                    str(lat), 
                    str(lon)
                ])
                st.cache_data.clear()
    except Exception as e:
        print(f"Error gestionando solapa comisarías: {e}")

def registrar_objetivo_con_comisaria_automatica(nombre_obj, direccion, localidad, supervisor, lat, lon, responsables):
    nombre_obj_upper = str(nombre_obj).strip().upper()
    localidad_obj_upper = str(localidad).strip().upper()
     
    distancia_minima = float('inf')
    com_n, com_d, com_l, com_t = "COMISARÍA JURISDICCIONAL", "---", "---", "011-4000-0000"
    com_lat_calc, com_lon_calc = lat, lon
     
    df_comis = cargar_datos_comisarias()
    try:
        lat_f = float(str(lat).replace(',', '.'))
        lon_f = float(str(lon).replace(',', '.'))
         
        if not df_comis.empty and 'LOCALIDAD' in df_comis.columns:
            df_comis_filtrada = df_comis[df_comis['LOCALIDAD'].astype(str).str.strip().str.upper() == localidad_obj_upper]
            if df_comis_filtrada.empty:
                df_comis_filtrada = df_comis
        else:
            df_comis_filtrada = df_comis

        for _, com in df_comis_filtrada.iterrows():
            lon1, lat1, lon2, lat2 = map(math.radians, [lon_f, lat_f, com['LONGITUD'], com['LATITUD']])
            dlon = lon2 - lon1
            dlat = lat2 - lat1
            a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
            c = 2 * math.asin(math.sqrt(a))
            km = 6371 * c
            if km < distancia_minima:
                distancia_minima = km
                com_n = com['COMISARIA']
                com_d = com['DIRECCION']
                com_l = com['LOCALIDAD']
                com_t = com.get('TELEFONO', '011-4000-0000')
                com_lat_calc = com.get('LATITUD', lat)
                com_lon_calc = com.get('LONGITUD', lon)
    except Exception as e:
        print(f"Error calculando comisaría cercana: {e}")

    comisaria_formateada = f"{com_n} - {com_d}, {com_l} (Tel: {com_t}) (~{distancia_minima:.2f} KM)"

    datos_nuevo_obj = [
        nombre_obj_upper, 
        str(direccion).strip().upper(), 
        str(localidad).strip().upper(), 
        str(supervisor).strip().upper(), 
        str(lat), 
        str(lon), 
        str(responsables).strip().upper(),
        comisaria_formateada
    ]
     
    exito = escribir_registro_nube("OBJETIVOS", datos_nuevo_obj)
    verificar_e_insertar_comisaria_automatica(com_n, com_d, com_l, com_t, com_lat_calc, com_lon_calc)
    return exito

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

        .btn-google-maps {
            display: inline-flex; align-items: center; justify-content: center;
            background-color: #ffffff !important; color: #1a73e8 !important;
            font-family: 'Orbitron', sans-serif; font-weight: bold; font-size: 13px;
            padding: 10px 18px; border-radius: 6px; border: 2px solid #1a73e8;
            text-decoration: none !important; box-shadow: 0 4px 15px rgba(26, 115, 232, 0.3);
            width: 100%; text-align: center; margin-top: 10px; transition: 0.3s;
        }
        .btn-google-maps:hover { background-color: #1a73e8 !important; color: white !important; }
        [data-testid="stStatusWidget"] { display: none !important; }
        </style>
    """, unsafe_allow_html=True)

@st.fragment(run_every=1)
def renderizar_reloj_fluido():
    tz = pytz.timezone("America/Argentina/Buenos_Aires")
    hora_actual = datetime.now(tz).strftime("%H:%M:%S")
    st.metric(label="HORA LOCAL", value=hora_actual)

def col_texto(df, col):
    if df.empty or col not in df.columns:
        return pd.Series(dtype=str)
    s = df[col]
    if isinstance(s, pd.DataFrame):
        s = s.iloc[:, 0]
    return s.astype(str)

def comisaria_mas_cercana(lat, lon, localidad, df_com):
    df_f = df_com
    if localidad and 'LOCALIDAD' in df_com.columns:
        sub = df_com[col_texto(df_com, 'LOCALIDAD').str.strip().str.upper() == localidad]
        if not sub.empty:
            df_f = sub
    mejor, dmin = None, float('inf')
    for _, c in df_f.iterrows():
        la1, lo1, la2, lo2 = map(math.radians, [lat, lon, c['LATITUD'], c['LONGITUD']])
        a = math.sin((la2-la1)/2)**2 + math.cos(la1)*math.cos(la2)*math.sin((lo2-lo1)/2)**2
        d = 6371 * 2 * math.asin(math.sqrt(a))
        if d < dmin:
            dmin, mejor = d, c
    return mejor

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
            destinatarios_posibles = ["TODOS", "MONITOREO", "JEFE DE OPERACIONES", "GERENCIA", "SUPERVISORES"] + obtener_lista_supervisores_dinamica()
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

    if not df_msg.empty and 'ASUNTO' in df_msg.columns:
        for asunto, grupo in df_msg.groupby('ASUNTO'):
            with st.expander(f"💬 Hilo: {asunto}"):
                for _, msg in grupo.iterrows():
                    st.markdown(f"**{msg.get('REMITENTE', 'ANÓNIMO')}:** {msg.get('MENSAJE', '')}")
                if st.button(f"Responder a este hilo", key=f"btn_{asunto}_{rol_contexto}"):
                    st.session_state.asunto_respuesta = asunto
                    sincronizar_url_sesion()
                    st.rerun()

def mostrar_notificaciones_sidebar():
    usuario_actual = str(st.session_state.get('user_sel', '')).strip().upper()
    
    df_notif = leer_matriz_nube("NOTIFICACIONES_SUPERVISORES")
    if df_notif.empty or not {'SUPERVISOR', 'MENSAJE', 'ESTADO'} <= set(df_notif.columns):
        return

    pend = df_notif[
        (col_texto(df_notif, 'SUPERVISOR').str.strip().str.upper() == usuario_actual) &
        (col_texto(df_notif, 'ESTADO').str.strip().str.upper() == "PENDIENTE")
    ]

    if not pend.empty:
        st.markdown("---")
        st.markdown(f"### 🔔 NOTIFICACIONES DE ALTA ({len(pend)})")
        for idx_n, fila_n in pend.iterrows():
            st.warning(f"{fila_n.get('MENSAJE', '')}")
            if st.button("✔️ LEÍDO / OK", key=f"btn_notif_{idx_n}", use_container_width=True):
                if actualizar_celda("NOTIFICACIONES_SUPERVISORES", idx_n + 2, "D", "LEÍDO"):
                    st.rerun()

def enviar_alerta_automatica(emisor, objetivo, nombre_persona, supervisor_asignado):
    fecha = obtener_hora_argentina()
    mensaje = f"🚨 ALERTA DE PÁNICO: {nombre_persona} - OBJ: {objetivo}"
    destinatarios = ["JEFE DE OPERACIONES", "GERENCIA", supervisor_asignado]
    for dest in destinatarios:
        if dest and dest != "MONITOREO" and dest != "N/A":
            escribir_registro_nube("MENSAJERIA", [fecha, emisor, dest, "ALERTA DE PÁNICO", mensaje, "PENDIENTE", "ROJA"])

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

# --- COMPONENTE PERSONALIZADO VISOR QR CON v6 Y AUDIO DESBLOQUEADO ---
_QR_HTML = r"""<!DOCTYPE html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
html,body{margin:0;padding:0;background:transparent;overflow:hidden}
#caja{position:relative;box-sizing:border-box;width:min(100%,340px);aspect-ratio:1/1;margin:6px auto;
border:2px solid #00E5FF;border-radius:14px;overflow:hidden;background:#000;box-shadow:0 0 15px rgba(0,229,255,.3)}
video{width:100%;height:100%;object-fit:cover;display:block}
#msg{position:absolute;left:0;right:0;bottom:0;padding:6px;color:#fff;background:rgba(0,0,0,.55);
font:12px sans-serif;text-align:center;pointer-events:none}
</style></head><body>
<div id="caja"><video id="v" playsinline muted autoplay></video><div id="msg"></div></div>
<canvas id="c" style="display:none"></canvas>
<!--JSQR_SCRIPT-->
<script>
function enviar(t,d){window.parent.postMessage(Object.assign({isStreamlitMessage:true,type:t},d),"*");}
function altura(){var w=Math.min(document.documentElement.clientWidth||window.innerWidth,340);
enviar("streamlit:setFrameHeight",{height:w+16});}
enviar("streamlit:componentReady",{apiVersion:1});altura();window.addEventListener("resize",altura);

var v=document.getElementById("v"),c=document.getElementById("c"),m=document.getElementById("msg");
var ctx=c.getContext("2d",{willReadFrequently:true}),pausa=false,audioCtx=null;

function desbloquear(){
  try{
    var AC=window.AudioContext||window.webkitAudioContext;
    if(!audioCtx)audioCtx=new AC();
    if(audioCtx.state==="suspended")audioCtx.resume();
    m.textContent="";
  }catch(e){}
}
["touchstart","click","pointerdown"].forEach(function(ev){
  document.addEventListener(ev,desbloquear,{passive:true});
});
m.textContent="Tocá el visor una vez para activar el sonido";

function bip(){
  try{
    desbloquear();
    var o=audioCtx.createOscillator(),g=audioCtx.createGain();
    o.type="sine";o.frequency.value=1300;g.gain.value=0.4;
    o.connect(g);g.connect(audioCtx.destination);
    o.start();
    setTimeout(function(){o.stop();},170);
  }catch(e){}
  try{if(navigator.vibrate)navigator.vibrate(120);}catch(e){}
}

navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:"environment"},width:{ideal:1280},height:{ideal:720}},audio:false})
.then(function(s){
  v.srcObject=s;v.play();
  window.addEventListener("pagehide",function(){s.getTracks().forEach(function(t){t.stop();});});
  setInterval(function(){
    if(pausa||v.readyState<2||!v.videoWidth)return;
    if(typeof jsQR==="undefined"){m.textContent="No cargó el lector QR. Revisá la conexión.";return;}
    var e=Math.min(1,640/Math.max(v.videoWidth,v.videoHeight));
    c.width=Math.round(v.videoWidth*e);c.height=Math.round(v.videoHeight*e);
    ctx.drawImage(v,0,0,c.width,c.height);
    var im=ctx.getImageData(0,0,c.width,c.height);
    var r=jsQR(im.data,im.width,im.height,{inversionAttempts:"attemptBoth"});
    if(r&&r.data){pausa=true;bip();enviar("streamlit:setComponentValue",{value:r.data,dataType:"json"});
      setTimeout(function(){pausa=false;},3000);}
  },120);
}).catch(function(){m.textContent="No se pudo abrir la cámara. Revisá el permiso del navegador.";});
</script></body></html>"""

def visor_qr(key):
    return _declarar_visor_qr("v6")(key=key, default=None)

# --- 3.B RECORRIDOS CON QR (VIGILADORES) Y ALERTA SONORA DE HORARIOS MEJORADA ---
def _horarios_unicos(valores):
    """Extrae horarios HH:MM únicos y ordenados de celdas como '19:23', '15:00, 17:00' o '19:23:00'."""
    vistos = []
    for v in valores:
        for h, m in re.findall(r'(\d{1,2}):(\d{2})', str(v)):
            if int(h) < 24 and int(m) < 60:
                hm = f"{int(h):02d}:{m}"
                if hm not in vistos:
                    vistos.append(hm)
    return sorted(vistos)


def aplicar_horarios_objetivo(obj_u, texto_horarios):
    """Escribe los mismos horarios en TODOS los puntos del objetivo."""
    try:
        gc = conectar_google()
        if not gc:
            return False
        hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet("RECORRIDOS PUNTOS")
        filas = hoja.get_all_values()
        if not filas:
            return False
        enc = [str(x).strip().upper() for x in filas[0]]
        col_idx = enc.index("HORARIO") + 1 if "HORARIO" in enc else 4
        letra = re.sub(r'\d', '', gspread.utils.rowcol_to_a1(1, col_idx))
        datos = []
        for i, f in enumerate(filas[1:], start=2):
            if len(f) >= 1 and str(f[0]).strip().upper() == obj_u:
                datos.append({"range": f"{letra}{i}", "values": [[texto_horarios]]})
        if not datos:
            return False
        hoja.batch_update(datos, value_input_option="RAW")
        st.cache_data.clear()
        return True
    except Exception as ex:
        print(f"Error aplicando horarios al objetivo: {ex}")
        return False


_ALERTA_HTML = r"""<!DOCTYPE html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
html,body{margin:0;padding:0;background:transparent;font-family:sans-serif}
#panel{box-sizing:border-box;background:#1A1C23;border:1px solid #00E5FF;border-radius:10px;padding:10px;text-align:center}
#t{color:#00E5FF;font-weight:bold;font-size:13px;margin:0 0 8px}
button{background:#00E5FF;color:#000;border:none;padding:9px 14px;font-weight:bold;font-size:13px;border-radius:6px;cursor:pointer;margin:2px}
button.ok{background:#39FF14}
button.sec{background:#2D313E;color:#E0E0E0}
#e{color:#39FF14;font-size:12px;margin:8px 0 0;line-height:1.3}
#w{color:#39FF14;font-size:11px;margin:4px 0 0;line-height:1.3}
#h{color:#A0A5B5;font-size:11px;margin:4px 0 0;line-height:1.3}
</style></head><body>
<div id="panel"><p id="t">🔔 AVISO DE RECORRIDAS</p>
<button id="b">🔊 ACTIVAR AVISO SONORO</button><button id="p" class="sec">🔔 PROBAR</button>
<p id="e"></p><p id="w"></p><p id="h"></p></div>
<script>
function enviar(t,d){window.parent.postMessage(Object.assign({isStreamlitMessage:true,type:t},d),"*");}
enviar("streamlit:componentReady",{apiVersion:1});
function altura(){enviar("streamlit:setFrameHeight",{height:Math.max(document.getElementById("panel").offsetHeight+8,120)});}
altura();window.addEventListener("resize",altura);

var P=window.parent, PD=P.document, ctx=null, wl=null;
var horarios=[], clave="", pendiente=null, tipoModal=null, repeticiones=0, timerRepeat=null, avisadoAhora={};

window.addEventListener("message",function(ev){
  if(ev.data && ev.data.type==="streamlit:render"){
    var a=ev.data.args||{};
    clave=String(a.clave||"");
    horarios=(a.horarios||[]).map(function(h){
      var p=String(h).trim().split(":");
      return p.length>=2 ? ("0"+p[0]).slice(-2)+":"+("0"+p[1]).slice(-2) : "";
    }).filter(Boolean);
    document.getElementById("h").textContent=horarios.length
      ? "Rondas: "+horarios.join(" · ")+" (aviso 5 min antes y a la hora)"
      : "Este objetivo no tiene horarios cargados.";
    ui(); altura();
  }
});

function ui(){
  var ok=ctx&&ctx.state==="running";
  var b=document.getElementById("b"), e=document.getElementById("e"), w=document.getElementById("w");
  if(ok){b.className="ok";b.textContent="🔊 SONIDO ACTIVO";e.style.color="#39FF14";e.textContent="✅ Sonido activo. Vas a recibir el aviso 5 minutos antes y a la hora de cada recorrida.";}
  else{b.className="";b.textContent="🔊 ACTIVAR AVISO SONORO";e.style.color="#FFD600";e.textContent="⚠️ Tocá el botón para activar el sonido. El cartel aparece igual.";}
  w.textContent=wl?"📱 La pantalla se mantiene encendida mientras esta pantalla esté abierta. Si bloqueás el celular, el aviso no suena.":"";
  altura();
}

function audio(){
  try{
    var AC=window.AudioContext||window.webkitAudioContext;
    if(!ctx){ctx=new AC();ctx.onstatechange=ui;}
    if(ctx.state!=="running"&&ctx.resume){ctx.resume().then(ui).catch(ui);}
    ui();
  }catch(e){document.getElementById("e").textContent="No se pudo iniciar el audio en este navegador.";}
}

// Mantiene la pantalla encendida (si el navegador lo permite) para que el aviso pueda sonar
function pantalla(){
  try{
    if(!P.navigator.wakeLock||wl) return;
    P.navigator.wakeLock.request("screen").then(function(l){
      wl=l; l.addEventListener("release",function(){wl=null;ui();}); ui();
    }).catch(function(){});
  }catch(e){}
}
PD.addEventListener("visibilitychange",function(){
  if(PD.visibilityState==="visible"){ if(!wl) pantalla(); if(ctx&&ctx.state!=="running") audio(); }
});

["touchstart","click","pointerdown"].forEach(function(n){
  PD.addEventListener(n,function(){ if(!ctx||ctx.state!=="running") audio(); if(!wl) pantalla(); },{passive:true});
});
document.getElementById("b").onclick=function(){audio();pantalla();setTimeout(campana,150);};
document.getElementById("p").onclick=function(){audio();pantalla();setTimeout(function(){mostrar("PRUEBA");},150);};

function nota(t0,f,dur){
  var o=ctx.createOscillator(), g=ctx.createGain();
  o.type="sine"; o.frequency.value=f;
  g.gain.setValueAtTime(0.0001,t0);
  g.gain.exponentialRampToValueAtTime(0.15,t0+0.03);
  g.gain.exponentialRampToValueAtTime(0.0001,t0+dur);
  o.connect(g); g.connect(ctx.destination);
  o.start(t0); o.stop(t0+dur+0.05);
}
function campana(){
  try{
    if(!ctx) audio();
    if(ctx.state==="suspended") ctx.resume();
    var t=ctx.currentTime+0.05;
    [523.25,659.25,783.99,1046.5].forEach(function(f,i){nota(t+i*0.28,f,0.9);});
    if(navigator.vibrate) navigator.vibrate([200,120,200]);
  }catch(e){}
}

function hoy(){var d=new Date();return d.getFullYear()+"-"+(d.getMonth()+1)+"-"+d.getDate();}
function llave(h){return "aion_rec_"+clave+"_"+hoy()+"_"+h;}
function respuestaDe(h){try{return localStorage.getItem(llave(h));}catch(e){return null;}}
function marcar(h,r){try{localStorage.setItem(llave(h),r);}catch(e){}}
function ahoraHecho(h){try{return localStorage.getItem(llave(h)+"_ahora")==="1";}catch(e){return false;}}
function marcarAhora(h){try{localStorage.setItem(llave(h)+"_ahora","1");}catch(e){}}
function minutosHasta(h){
  var p=h.split(":"), t=new Date();
  t.setHours(parseInt(p[0],10),parseInt(p[1],10),0,0);
  return (t.getTime()-Date.now())/60000;
}

function cerrar(){
  var m=PD.getElementById("aion_modal_rec"); if(m) m.remove();
  pendiente=null; tipoModal=null; repeticiones=0;
  if(timerRepeat){clearInterval(timerRepeat); timerRepeat=null;}
}
function responder(hora,resp,motivo){
  if(hora!=="PRUEBA"){
    marcar(hora,resp);
    enviar("streamlit:setComponentValue",{
      value:{id:hora+"_"+Date.now(),hora:hora,respuesta:resp,motivo:motivo||""},
      dataType:"json"
    });
  }
  cerrar();
}

function textoAviso(h){
  if(h==="PRUEBA") return 'Esto es una <b>prueba</b> del aviso.<br><b>¿Realizás la recorrida?</b>';
  var m=minutosHasta(h), cuando;
  if(m>0) cuando='es en <b>'+Math.ceil(m)+' min</b>.';
  else if(m>-1) cuando='es <b>ahora</b>.';
  else cuando='era hace <b>'+Math.round(-m)+' min</b>.';
  return 'Tu recorrida de las <b>'+h+' hs</b> '+cuando+'<br><b>¿Realizás la recorrida?</b>';
}

function crearModal(html,borde){
  var d=PD.createElement("div");
  d.id="aion_modal_rec";
  d.style.cssText="position:fixed;inset:0;background:rgba(0,0,0,.85);z-index:999999;display:flex;align-items:center;justify-content:center;padding:20px;box-sizing:border-box;font-family:sans-serif";
  d.innerHTML='<div style="background:#1A1C23;border:2px solid '+borde+';border-radius:14px;padding:24px;max-width:380px;width:100%;text-align:center;color:#FFF;box-shadow:0 0 30px rgba(0,229,255,.5)">'+html+'</div>';
  PD.body.appendChild(d);
}

function repetir(ms,max){
  repeticiones=0;
  timerRepeat=setInterval(function(){
    if(pendiente && repeticiones<max){repeticiones++; campana();}
    else if(timerRepeat){clearInterval(timerRepeat); timerRepeat=null;}
  },ms);
}

// Aviso previo / recorrida pendiente: pregunta SÍ / NO
function mostrar(hora){
  if(PD.getElementById("aion_modal_rec")) return;
  pendiente=hora; tipoModal="aviso";
  crearModal(
    '<h2 style="color:#00E5FF;margin:0 0 10px;font-size:20px">🔔 Aviso de recorrida</h2>'+
    '<p id="aion_txt_p" style="font-size:16px;margin:0 0 16px;line-height:1.4">'+textoAviso(hora)+'</p>'+
    '<div id="aion_botones"><button id="aion_si" style="background:#39FF14;color:#000;border:none;padding:12px 26px;font-weight:bold;font-size:15px;border-radius:8px;margin:4px">SÍ</button>'+
    '<button id="aion_no" style="background:#FF5252;color:#fff;border:none;padding:12px 26px;font-weight:bold;font-size:15px;border-radius:8px;margin:4px">NO</button></div>'+
    '<div id="aion_motivo" style="display:none;margin-top:10px">'+
    '<select id="aion_sel" style="width:100%;padding:10px;border-radius:6px;font-size:14px;margin-bottom:8px">'+
    '<option>Atendiendo una novedad en el objetivo</option><option>Atendiendo una visita o ingreso</option>'+
    '<option>Falta de personal</option><option>Problema de salud</option><option>Otro</option></select>'+
    '<input id="aion_txt" placeholder="Detalle (opcional)" style="width:100%;box-sizing:border-box;padding:10px;border-radius:6px;font-size:14px;margin-bottom:8px">'+
    '<button id="aion_env" style="background:#00E5FF;color:#000;border:none;padding:12px;font-weight:bold;font-size:14px;border-radius:8px;width:100%">ENVIAR MOTIVO</button></div>',
    "#00E5FF");
  PD.getElementById("aion_si").onclick=function(){responder(hora,"SI","");};
  PD.getElementById("aion_no").onclick=function(){
    PD.getElementById("aion_botones").style.display="none";
    PD.getElementById("aion_motivo").style.display="block";
  };
  PD.getElementById("aion_env").onclick=function(){
    var mot=PD.getElementById("aion_sel").value;
    var det=PD.getElementById("aion_txt").value.trim();
    responder(hora,"NO",det?mot+" - "+det:mot);
  };
  campana();
  repetir(60000,2);
}

// A la hora exacta (si dijo SÍ): recordatorio de que empieza la recorrida
function mostrarHora(hora){
  if(PD.getElementById("aion_modal_rec")) return;
  pendiente=hora; tipoModal="hora";
  crearModal(
    '<h2 style="color:#39FF14;margin:0 0 10px;font-size:20px">🚶 ¡Es hora de la recorrida!</h2>'+
    '<p style="font-size:16px;margin:0 0 16px;line-height:1.4">Ronda de las <b>'+hora+' hs</b>.<br>Recorré el objetivo y escaneá el QR de cada punto de control.</p>'+
    '<button id="aion_ent" style="background:#39FF14;color:#000;border:none;padding:12px 26px;font-weight:bold;font-size:15px;border-radius:8px;width:100%">ENTENDIDO, INICIO</button>',
    "#39FF14");
  PD.getElementById("aion_ent").onclick=function(){marcarAhora(hora);cerrar();};
  campana();
  repetir(45000,3);
}

setInterval(function(){
  var modal=PD.getElementById("aion_modal_rec");
  var i,h,m,r;
  // Si el aviso previo sigue sin responder cuando llega la hora, se actualiza el texto y suena de nuevo
  for(i=0;i<horarios.length;i++){
    h=horarios[i]; m=minutosHasta(h);
    if(modal && tipoModal==="aviso" && pendiente===h && m<=0 && !avisadoAhora[h]){
      avisadoAhora[h]=true;
      var tp=PD.getElementById("aion_txt_p"); if(tp) tp.innerHTML=textoAviso(h);
      campana();
      return;
    }
  }
  if(modal) return;
  for(i=0;i<horarios.length;i++){
    h=horarios[i]; m=minutosHasta(h); r=respuestaDe(h);
    if(r==="SI" && m<=0 && m>-5 && !ahoraHecho(h)){mostrarHora(h);return;}
    if(r===null && m<=5 && m>-30){mostrar(h);return;}
  }
},1000);
</script></body></html>"""


@st.cache_resource(show_spinner=False)
def _declarar_alerta_recorrida(version="v3"):
    carpeta = tempfile.mkdtemp(prefix=f"aion_alerta_{version}_")
    with open(os.path.join(carpeta, "index.html"), "w", encoding="utf-8") as f:
        f.write(_ALERTA_HTML)
    return components.declare_component(f"aion_alerta_rec_{version}", path=carpeta)


def registrar_respuesta_recorrida(obj, nombre, dni, evento):
    try:
        gc = conectar_google()
        if not gc:
            return False
        sh = gc.open_by_key(ID_MAESTRO_DB)
        try:
            hoja = sh.worksheet("RESPUESTAS RECORRIDAS")
        except Exception:
            hoja = sh.add_worksheet(title="RESPUESTAS RECORRIDAS", rows="100", cols="10")
            hoja.append_row(["FECHA_HORA", "OBJETIVO", "VIGILADOR", "DNI", "HORARIO", "RESPUESTA", "MOTIVO"])
        hoja.append_row([
            obtener_hora_argentina(), obj, str(nombre).upper(), str(dni),
            evento.get("hora", ""), evento.get("respuesta", ""), str(evento.get("motivo", "")).upper()
        ])
        st.cache_data.clear()
        return True
    except Exception as ex:
        print(f"Error guardando respuesta de recorrida: {ex}")
        return False


def renderizar_alerta_recorrida_js(horarios_previstos, obj_u, nombre, dni):
    horarios = _horarios_unicos(horarios_previstos)
    evento = _declarar_alerta_recorrida("v3")(horarios=horarios, clave=obj_u, key=f"alerta_rec_{obj_u}", default=None)
    if evento and evento.get("id") != st.session_state.get("ultimo_evento_alerta"):
        st.session_state.ultimo_evento_alerta = evento.get("id")
        if registrar_respuesta_recorrida(obj_u, nombre, dni, evento):
            if evento.get("respuesta") == "SI":
                st.toast("✅ Respuesta registrada. ¡Buena recorrida!", icon="✅")
            else:
                st.toast("📝 Motivo registrado.", icon="📝")


def renderizar_recorrido_vigilador(objetivo, nombre, dni):
    st.markdown("### 🚶 RECORRIDO CON MARCACIÓN QR")

    if not dni and (st.session_state.get('rol_sel') == "ADMINISTRADOR" or st.session_state.get('admin_autenticado')):
        dni = "99999999"

    if not dni:
        st.warning("⚠️ Para registrar recorridos debés ingresar con tu DNI.")
        return

    obj_u = str(objetivo).strip().upper()
    hoy = obtener_hora_argentina().split(" ")[0]
    st.caption(f"📍 Objetivo: {obj_u}")

    df_p = leer_matriz_nube("RECORRIDOS PUNTOS")
    if df_p.empty or not {'OBJETIVO', 'PUNTO'} <= set(df_p.columns):
        st.info("No hay puntos de control cargados.")
        return

    puntos = df_p[df_p['OBJETIVO'].astype(str).str.strip().str.upper() == obj_u].copy()
    if puntos.empty:
        st.info(f"El objetivo {obj_u} no tiene puntos de recorrido cargados.")
        return

    if 'ORDEN' in puntos.columns:
        puntos['_ORD'] = pd.to_numeric(puntos['ORDEN'], errors='coerce')
        puntos = puntos.sort_values('_ORD')
    lista_puntos = [str(p).strip().upper() for p in puntos['PUNTO']]

    horarios_previstos_lista = []
    if 'HORARIO' in puntos.columns:
        horarios_previstos_lista = _horarios_unicos(puntos['HORARIO'].dropna().tolist())

    renderizar_alerta_recorrida_js(horarios_previstos_lista, obj_u, nombre, dni)

    df_r = leer_matriz_nube("REGISTRO RECORRIDOS")
    df_hoy = pd.DataFrame()
    if not df_r.empty and {'FECHA_HORA', 'OBJETIVO', 'PUNTO', 'DNI', 'RONDA'} <= set(df_r.columns):
        df_r = df_r.loc[:, ~df_r.columns.duplicated()].copy()
        m_dni = df_r['DNI'].map(lambda v: str(v).strip() == str(dni))
        m_obj = df_r['OBJETIVO'].map(lambda v: str(v).strip().upper() == obj_u)
        m_fecha = col_texto(df_r, 'FECHA_HORA').map(lambda v: hoy in str(v))
        df_hoy = df_r[m_dni & m_obj & m_fecha]

    rondas = pd.to_numeric(df_hoy['RONDA'], errors='coerce').dropna() if not df_hoy.empty else pd.Series(dtype=float)
    ronda_planilla = int(rondas.max()) if not rondas.empty else 1
    key_ronda = f"ronda_vig_{obj_u}_{hoy}"
    ronda = max(ronda_planilla, st.session_state.get(key_ronda, 1))
    st.session_state[key_ronda] = ronda

    marcados = set()
    if not df_hoy.empty:
        df_ronda = df_hoy[pd.to_numeric(df_hoy['RONDA'], errors='coerce') == ronda]
        marcados = set(col_texto(df_ronda, 'PUNTO').str.strip().str.upper())

    c_r1, c_r2 = st.columns(2)
    c_r1.metric("🔁 RONDA", ronda)
    c_r2.metric("✅ PUNTOS", f"{len(marcados)} / {len(lista_puntos)}")
    st.progress(min(1.0, len(marcados) / len(lista_puntos)))

    for p in lista_puntos:
        st.write(("✅ " if p in marcados else "⏳ ") + p)

    if st.session_state.get("msg_recorrido"):
        st.success(st.session_state.msg_recorrido)

    if len(marcados) >= len(lista_puntos):
        st.success("🏁 ¡Ronda completa!")
        if st.button("🔁 INICIAR NUEVA RONDA", use_container_width=True, key=f"btn_nueva_ronda_{obj_u}"):
            st.session_state[key_ronda] = ronda + 1
            st.session_state.msg_recorrido = ""
            st.rerun()
        return

    st.markdown("""
        <div style="border: 1px solid #00E5FF; border-radius: 6px; padding: 6px; text-align: center; margin: 2px 0; background: rgba(0, 229, 255, 0.05);">
            <span style="font-family: 'Orbitron', sans-serif; color: #00E5FF; font-size: 12px; font-weight: bold;">📷 ESCANEÁ EL QR DEL PUNTO DE CONTROL</span>
        </div>
    """, unsafe_allow_html=True)

    codigo = visor_qr(key=f"scan_rec_{obj_u}_{ronda}_{len(marcados)}")

    if codigo:
        txt = str(codigo).strip()
        partes = {}
        for fragmento in txt.split("|"):
            if ":" in fragmento:
                k, v = fragmento.split(":", 1)
                partes[k.strip().upper()] = v.strip().upper()
        obj_qr = partes.get("OBJ", "")
        pto_qr = partes.get("PTO", "")

        if not txt.upper().startswith("AION-RECORRIDO"):
            st.error("❌ Ese QR no es de un punto de recorrido.")
        elif obj_qr != obj_u or pto_qr not in lista_puntos:
            st.error("❌ Ese punto no pertenece a este objetivo.")
        elif pto_qr in marcados:
            st.warning("⚠️ Ese punto ya fue marcado en esta ronda.")
        else:
            ok = escribir_registro_nube("REGISTRO RECORRIDOS", [
                obtener_hora_argentina(), obj_u, pto_qr, str(nombre).strip().upper(), str(dni), ronda, "OK"
            ])
            if ok:
                st.session_state.msg_recorrido = f"✅ Marcado: {pto_qr}"
                st.rerun()

def renderizar_generador_qr_recorrido(lista_objetivos, key_prefix):
    st.markdown("#### 🧾 CONFIGURACIÓN DE RONDAS Y HORARIOS ESPECÍFICOS")
    lista_objetivos = list(lista_objetivos)
    if len(lista_objetivos) == 0:
        st.info("No hay objetivos disponibles.")
        return

    obj = st.selectbox("OBJETIVO:", lista_objetivos, key=f"{key_prefix}_rec_obj")
    obj_u = str(obj).strip().upper()

    df_p = leer_matriz_nube("RECORRIDOS PUNTOS")
    existentes = pd.DataFrame()
    if not df_p.empty and {'OBJETIVO', 'PUNTO'} <= set(df_p.columns):
        existentes = df_p[df_p['OBJETIVO'].astype(str).str.strip().str.upper() == obj_u].copy()
        if 'ORDEN' in existentes.columns:
            existentes['_ORD'] = pd.to_numeric(existentes['ORDEN'], errors='coerce')
            existentes = existentes.sort_values('_ORD')

    horarios_actuales = _horarios_unicos(existentes['HORARIO'].tolist()) if (not existentes.empty and 'HORARIO' in existentes.columns) else []

    if st.session_state.get(f"{key_prefix}_msg_punto"):
        st.success(st.session_state[f"{key_prefix}_msg_punto"])
        st.session_state[f"{key_prefix}_msg_punto"] = ""

    if not existentes.empty:
        cols_ver = [c for c in ['PUNTO', 'ORDEN', 'HORARIO'] if c in existentes.columns]
        st.dataframe(existentes[cols_ver], use_container_width=True, hide_index=True)
        
        st.markdown("##### ⏰ HORARIOS DE RONDAS PARA TODO EL OBJETIVO")
        with st.form(key=f"{key_prefix}_form_act_horario_{obj_u}", clear_on_submit=False):
            st.markdown("Indicá los horarios separados por coma (ej. `15:00, 17:00, 19:00, 21:00`). Se aplican a **todos los puntos** del objetivo. Cada hora es una ronda y el vigilador recibe el aviso 5 minutos antes.")
            nuevo_horario_edit = st.text_input("HORARIOS DE RONDAS:", value=", ".join(horarios_actuales) or "15:00, 17:00, 19:00, 21:00").strip()
            if st.form_submit_button("💾 GUARDAR HORARIOS PARA TODO EL OBJETIVO"):
                nuevos_h = _horarios_unicos([nuevo_horario_edit])
                if not nuevos_h:
                    st.warning("⚠️ Ingresá al menos un horario válido (ej. 15:00).")
                elif aplicar_horarios_objetivo(obj_u, ", ".join(nuevos_h)):
                    st.session_state[f"{key_prefix}_msg_punto"] = f"✅ Horarios {', '.join(nuevos_h)} aplicados a todos los puntos de '{obj_u}'."
                    st.rerun()
                else:
                    st.error("❌ No se pudieron guardar los horarios. Revisá la hoja RECORRIDOS PUNTOS.")
    else:
        st.info("Este objetivo todavía no tiene puntos de recorrido.")

    with st.expander("➕ CREAR NUEVO PUNTO DE RECORRIDO"):
        with st.form(key=f"{key_prefix}_form_punto", clear_on_submit=True):
            nuevo_punto = st.text_input("NOMBRE DEL PUNTO (Ej: PORTÓN 1):").strip().upper()
            nuevo_orden = st.number_input("ORDEN EN EL RECORRIDO:", min_value=1, value=len(existentes) + 1, step=1)
            nuevo_horario = st.text_input("HORARIOS DE RONDAS (Ej: 15:00, 17:00, 19:00):", value=", ".join(horarios_actuales) or "15:00, 17:00").strip()
            
            if st.form_submit_button("➕ GUARDAR NUEVO PUNTO"):
                if nuevo_punto:
                    ya_existe = (not existentes.empty) and (nuevo_punto in col_texto(existentes, 'PUNTO').str.strip().str.upper().tolist())
                    if ya_existe:
                        st.warning("⚠️ Ese punto ya existe en este objetivo. Usá la sección de arriba para configurar sus horarios.")
                    elif escribir_registro_nube("RECORRIDOS PUNTOS", [obj_u, nuevo_punto, int(nuevo_orden), nuevo_horario]):
                        st.session_state[f"{key_prefix}_msg_punto"] = f"✅ Punto '{nuevo_punto}' guardado con éxito."
                        st.rerun()
                else:
                    st.warning("⚠️ Ingresá el nombre del punto.")

    if not existentes.empty:
        st.markdown("##### 🖨️ GENERAR QR PARA IMPRIMIR")
        pto_sel = st.selectbox("PUNTO:", col_texto(existentes, 'PUNTO').tolist(), key=f"{key_prefix}_rec_pto")
        texto_qr = f"AION-RECORRIDO|OBJ:{obj_u}|PTO:{str(pto_sel).strip().upper()}"
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=3)
        qr.add_data(texto_qr)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#000000", back_color="#FFFFFF")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        st.image(buf.getvalue(), width=220, caption=f"{obj_u} | {str(pto_sel).strip().upper()}")
        st.download_button(
            "📥 DESCARGAR QR (PNG)",
            data=buf.getvalue(),
            file_name=f"qr_{obj_u}_{str(pto_sel).strip().upper()}.png".replace(" ", "_"),
            mime="image/png",
            key=f"{key_prefix}_dl_qr_{obj_u}_{pto_sel}"
        )

def tabla_recorridas_vigiladores(objs_sup):
    df_r = leer_matriz_nube("REGISTRO RECORRIDOS")
    if df_r.empty or len(objs_sup) == 0 or not {'FECHA_HORA', 'OBJETIVO', 'PUNTO', 'RONDA'} <= set(df_r.columns):
        return pd.DataFrame()
    df_r = df_r.loc[:, ~df_r.columns.duplicated()].copy()
    objs = [str(o).strip().upper() for o in objs_sup]
    df_r['_OBJ'] = col_texto(df_r, 'OBJETIVO').str.strip().str.upper()
    df_r = df_r[df_r['_OBJ'].isin(objs)].copy()
    if df_r.empty:
        return pd.DataFrame()

    col_vig = next((c for c in ['VIGILADOR', 'NOMBRE', 'APELLIDO Y NOMBRE'] if c in df_r.columns), None)
    if col_vig:
        df_r['_VIG'] = col_texto(df_r, col_vig).str.strip().str.upper()
    elif 'DNI' in df_r.columns:
        df_r['_VIG'] = col_texto(df_r, 'DNI').str.replace(r'\D', '', regex=True)
        df_pad = leer_matriz_nube("PADRON VIGILADORES")
        if not df_pad.empty and {'DNI', 'NOMBRE'} <= set(df_pad.columns):
            mapa = dict(zip(
                col_texto(df_pad, 'DNI').str.replace(r'\D', '', regex=True),
                col_texto(df_pad, 'NOMBRE').str.strip().str.upper()
            ))
            df_r['_VIG'] = df_r['_VIG'].map(lambda d: mapa.get(d, d))
    else:
        df_r['_VIG'] = "---"

    df_r['_PTO'] = col_texto(df_r, 'PUNTO').str.strip().str.upper()
    df_r['_FH'] = pd.to_datetime(df_r['FECHA_HORA'], errors='coerce')
    df_r['_RONDA'] = pd.to_numeric(df_r['RONDA'], errors='coerce').fillna(1).astype(int)
    df_r = df_r.dropna(subset=['_FH'])
    if df_r.empty:
        return pd.DataFrame()
    df_r['_FECHA'] = df_r['_FH'].dt.strftime('%Y-%m-%d')

    total_ptos, previsto = {}, {}
    df_p = leer_matriz_nube("RECORRIDOS PUNTOS")
    if not df_p.empty and {'OBJETIVO', 'PUNTO'} <= set(df_p.columns):
        df_p = df_p.loc[:, ~df_p.columns.duplicated()].copy()
        df_p['_OBJ'] = col_texto(df_p, 'OBJETIVO').str.strip().str.upper()
        total_ptos = df_p.groupby('_OBJ')['PUNTO'].nunique().to_dict()
        if 'HORARIO' in df_p.columns:
            for o, g in df_p.groupby('_OBJ'):
                hs = _horarios_unicos(col_texto(g, 'HORARIO').tolist())
                if hs:
                    previsto[o] = ", ".join(hs)

    filas = []
    for (fecha, obj, vig, ronda), g in df_r.groupby(['_FECHA', '_OBJ', '_VIG', '_RONDA']):
        marcados = g['_PTO'].nunique()
        total = total_ptos.get(obj, 0)
        completa = total > 0 and marcados >= total
        filas.append({
            "FECHA": fecha,
            "OBJETIVO": obj,
            "VIGILADOR": vig,
            "RONDA": ronda,
            "HORARIO PREVISTO": previsto.get(obj, "15:00, 17:00, 19:00"),
            "INICIÓ": g['_FH'].min().strftime('%H:%M:%S'),
            "FINALIZÓ": g['_FH'].max().strftime('%H:%M:%S') if completa else "---",
            "PUNTOS": f"{marcados}/{total}" if total else str(marcados),
            "ESTADO": "✅ COMPLETA" if completa else "⏳ EN CURSO"
        })
    df_out = pd.DataFrame(filas)
    return df_out.sort_values(['FECHA', 'INICIÓ'], ascending=False).reset_index(drop=True)

# --- 3.C PLANIFICACIÓN POR MES (JEFE DE OPERACIONES / GERENCIA) ---
TIPOS_NOVEDAD_PERSONAL = {
    "LICENCIA":   ("L",   "#EF5350", "#FFF"),
    "ART":        ("ART", "#FF9800", "#000"),
    "VACACIONES": ("V",   "#AB47BC", "#FFF"),
}
PRIORIDAD_NOVEDAD = ["LICENCIA", "ART", "VACACIONES"]
MESES_ES = ["ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO", "JULIO",
            "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"]
LETRAS_DIA = ["L", "M", "M", "J", "V", "S", "D"]

def _fecha_a_dt(v):
    s = str(v).strip()
    if not s:
        return pd.NaT
    d = pd.to_datetime(s, format="%Y-%m-%d", errors="coerce")
    if pd.isna(d):
        d = pd.to_datetime(s, dayfirst=True, errors="coerce")
    return d

def _supervisores_con_objetivos():
    df_o = cargar_objetivos()
    if df_o.empty or 'SUPERVISOR' not in df_o.columns:
        return []
    return sorted(set(col_texto(df_o, 'SUPERVISOR').str.strip().str.upper()) - {"", "NAN"})

def vigiladores_de_supervisor(sup):
    vacio = pd.DataFrame(columns=["OBJETIVO", "VIGILADOR", "DNI"])
    df_o = cargar_objetivos()
    df_p = leer_matriz_nube("PADRON VIGILADORES")
    if df_o.empty or df_p.empty or 'SUPERVISOR' not in df_o.columns or not {'DNI', 'NOMBRE', 'OBJETIVO'} <= set(df_p.columns):
        return vacio
    m_sup = col_texto(df_o, 'SUPERVISOR').str.strip().str.upper() == str(sup).strip().upper()
    objs = col_texto(df_o, 'OBJETIVO').str.strip().str.upper()[m_sup].tolist()
    df_p = df_p.copy()
    df_p['_OBJ'] = col_texto(df_p, 'OBJETIVO').str.strip().str.upper()
    if 'ESTADO' in df_p.columns:
        df_p = df_p[col_texto(df_p, 'ESTADO').str.strip().str.upper() == "ACTIVO"]
    df_p = df_p[df_p['_OBJ'].isin(objs)]
    if df_p.empty:
        return vacio
    return pd.DataFrame({
        "OBJETIVO": df_p['_OBJ'].values,
        "VIGILADOR": col_texto(df_p, 'NOMBRE').str.strip().str.upper().values,
        "DNI": col_texto(df_p, 'DNI').str.replace(r'\D', '', regex=True).values,
    }).sort_values(["OBJETIVO", "VIGILADOR"]).reset_index(drop=True)

def cargar_novedades_personal():
    df = leer_matriz_nube("NOVEDADES PERSONAL")
    if df.empty or not {'DNI', 'TIPO', 'DESDE', 'HASTA'} <= set(df.columns):
        return pd.DataFrame()
    df = df.copy()
    df['_DNI'] = col_texto(df, 'DNI').str.replace(r'\D', '', regex=True)
    df['_TIPO'] = col_texto(df, 'TIPO').str.strip().str.upper()
    df['_DESDE'] = df['DESDE'].map(_fecha_a_dt)
    df['_HASTA'] = df['HASTA'].map(_fecha_a_dt)
    return df.dropna(subset=['_DESDE', '_HASTA'])

def registrar_novedad_personal(dni, vigilador, objetivo, supervisor, tipo, desde, hasta, obs):
    try:
        gc = conectar_google()
        if not gc:
            return False
        sh = gc.open_by_key(ID_MAESTRO_DB)
        try:
            hoja = sh.worksheet("NOVEDADES PERSONAL")
        except Exception:
            hoja = sh.add_worksheet(title="NOVEDADES PERSONAL", rows="200", cols="12")
            hoja.append_row(["FECHA_REGISTRO", "DNI", "VIGILADOR", "OBJETIVO", "SUPERVISOR", "TIPO",
                             "DESDE", "HASTA", "OBSERVACION", "REGISTRADO_POR"])
        hoja.append_row([obtener_hora_argentina(), str(dni), vigilador, objetivo, supervisor, tipo,
                         desde.strftime("%Y-%m-%d"), hasta.strftime("%Y-%m-%d"),
                         str(obs).strip().upper(), str(st.session_state.get("user_sel", "")).upper()])
        st.cache_data.clear()
        return True
    except Exception as e:
        print(f"Error registrando novedad de personal: {e}")
        return False

def planificacion_mes(periodo):
    anio, mes = map(int, periodo.split("-"))
    primero = pd.Timestamp(anio, mes, 1)
    ultimo = pd.Timestamp(anio, mes, calendar.monthrange(anio, mes)[1])
    nov = cargar_novedades_personal()
    resultado = {}
    for s in _supervisores_con_objetivos():
        vig = vigiladores_de_supervisor(s)
        if vig.empty:
            continue
        filas = []
        for _, v in vig.iterrows():
            mapa = {}
            if not nov.empty:
                for _, n in nov[nov['_DNI'] == v['DNI']].iterrows():
                    t = n['_TIPO']
                    if t not in PRIORIDAD_NOVEDAD:
                        continue
                    ini, fin = max(n['_DESDE'], primero), min(n['_HASTA'], ultimo)
                    if ini > fin:
                        continue
                    for d in range(ini.day, fin.day + 1):
                        previo = mapa.get(d)
                        if previo is None or PRIORIDAD_NOVEDAD.index(t) < PRIORIDAD_NOVEDAD.index(previo):
                            mapa[d] = t
            dias = {t: list(mapa.values()).count(t) for t in PRIORIDAD_NOVEDAD}
            estado = next((t for t in PRIORIDAD_NOVEDAD if dias[t] > 0), "SIN NOVEDAD")
            filas.append({
                "OBJETIVO": v["OBJETIVO"], "VIGILADOR": v["VIGILADOR"], "DNI": v["DNI"],
                "ESTADO": estado, "DÍAS LICENCIA": dias["LICENCIA"],
                "DÍAS ART": dias["ART"], "DÍAS VACACIONES": dias["VACACIONES"],
                "MAPA": mapa,
            })
        resultado[s] = pd.DataFrame(filas)
    return resultado

def grilla_planificacion_html(df, anio, mes):
    import html as _h
    ndias = calendar.monthrange(anio, mes)[1]
    cab = "".join(
        f'<th style="padding:2px 4px;font-size:10px;color:{"#FF8A80" if calendar.weekday(anio, mes, d) >= 5 else "#A0A5B5"};">'
        f'{LETRAS_DIA[calendar.weekday(anio, mes, d)]}<br>{d}</th>' for d in range(1, ndias + 1))
    filas = ""
    for _, r in df.iterrows():
        celdas = ""
        for d in range(1, ndias + 1):
            t = r["MAPA"].get(d)
            if t:
                letra, bg, fg = TIPOS_NOVEDAD_PERSONAL[t]
                celdas += f'<td style="background:{bg};color:{fg};text-align:center;font-size:10px;font-weight:bold;padding:3px 2px;border:1px solid #0A0F1E;">{letra}</td>'
            else:
                celdas += '<td style="background:#1F3A2B;border:1px solid #0A0F1E;"></td>'
        filas += (f'<tr><td style="padding:3px 8px;font-size:11px;white-space:nowrap;color:#E0E0E0;position:sticky;left:0;background:#0A0F1E;">'
                  f'{_h.escape(str(r["VIGILADOR"]))}</td>{celdas}</tr>')
    return f'<div style="overflow-x:auto;"><table style="border-collapse:collapse;"><tr><th></th>{cab}</tr>{filas}</table></div>'

def leyenda_planificacion_html():
    chips = '<span style="background:#1F3A2B;color:#E0E0E0;padding:2px 8px;border-radius:4px;font-size:11px;margin-right:6px;display:inline-block;margin-bottom:4px;">■ SIN NOVEDAD</span>'
    for nombre, (letra, bg, fg) in TIPOS_NOVEDAD_PERSONAL.items():
        chips += f'<span style="background:{bg};color:{fg};padding:2px 8px;border-radius:4px;font-size:11px;margin-right:6px;display:inline-block;margin-bottom:4px;">{letra} = {nombre}</span>'
    return f'<div style="margin-bottom:8px;">{chips}</div>'

def formulario_novedad_personal(key_prefix):
    frames = []
    for s in _supervisores_con_objetivos():
        v = vigiladores_de_supervisor(s)
        if not v.empty:
            frames.append(v.assign(SUPERVISOR=s))
    if not frames:
        st.info("No hay vigiladores activos para registrar novedades.")
        return
    todos = pd.concat(frames, ignore_index=True)
    etiquetas = {i: f"{r['VIGILADOR']} | {r['OBJETIVO']} | SUP: {r['SUPERVISOR']}" for i, r in todos.iterrows()}
    hoy = datetime.now(pytz.timezone("America/Argentina/Buenos_Aires")).date()
    with st.form(key=f"{key_prefix}_form_novedad", clear_on_submit=True):
        idx = st.selectbox("VIGILADOR:", list(etiquetas.keys()), format_func=lambda k: etiquetas[k])
        tipo = st.selectbox("TIPO DE NOVEDAD:", list(TIPOS_NOVEDAD_PERSONAL.keys()))
        c1, c2 = st.columns(2)
        desde = c1.date_input("DESDE:", value=hoy)
        hasta = c2.date_input("HASTA:", value=hoy)
        obs = st.text_input("OBSERVACIÓN (opcional):")
        if st.form_submit_button("💾 REGISTRAR NOVEDAD", use_container_width=True):
            if hasta < desde:
                st.warning("⚠️ La fecha HASTA no puede ser anterior a DESDE.")
            else:
                r = todos.loc[idx]
                if registrar_novedad_personal(r["DNI"], r["VIGILADOR"], r["OBJETIVO"], r["SUPERVISOR"], tipo, desde, hasta, obs):
                    st.session_state[f"{key_prefix}_msg"] = f"✅ Registrado: {r['VIGILADOR']} - {tipo} ({desde} a {hasta})."
                    st.rerun()
                else:
                    st.error("❌ No se pudo registrar. Revisá la conexión con Google Sheets.")


def _hora_a_min(s):
    try:
        t = datetime.strptime(str(s).strip().split(" ")[-1][:8], "%H:%M:%S")
        return t.hour * 60 + t.minute + t.second / 60.0
    except Exception:
        return None

def _num_ar(v):
    s = str(v).replace("$", "").replace(" ", "").strip().replace(".", "").replace(",", ".")
    try:
        return float(s)
    except Exception:
        return 0.0

def _leer_mes(pestana, periodo, min_cols):
    """Hoja viva + hoja archivada del cierre mensual (NOMBRE_MM), filtradas por el período.
    Devuelve columnas numeradas 0..min_cols-1 (se trabaja por posición)."""
    mes = int(periodo.split("-")[1])
    partes = []
    for nombre in (pestana, f"{pestana}_{mes:02d}"):
        d = leer_matriz_nube(nombre)
        if not d.empty and d.shape[1] >= min_cols:
            d = d.iloc[:, :min_cols].copy()
            d.columns = range(min_cols)
            partes.append(d.astype(str).apply(lambda c: c.str.strip()))
    if not partes:
        return pd.DataFrame()
    df = pd.concat(partes, ignore_index=True).drop_duplicates()
    return df[df[0].str.startswith(periodo)].reset_index(drop=True)

HORAS_TURNO = 12        # horas que se cuentan por cada turno de ingreso
HORAS_MAX_MES = 200     # límite mensual de horas por vigilador (ajustar según convenio)
MAX_DIAS_SEGUIDOS = 6   # más de estos días seguidos sin descanso = franco cortado

def estadistica_vigiladores(periodo, pres, obj_a_sup, personal):
    """Por supervisor y vigilador: turnos, horas, días seguidos, francos cortados y exceso de horas.
    Sale de los INGRESOS que cada vigilador marca en la app (hoja PRESENTISMO)."""
    reg = {}
    if not pres.empty:
        ing = pres[pres[5].str.upper() == "INGRESO"]
        for _, f in ing.iterrows():
            sup = obj_a_sup.get(f[4].upper())
            if not sup:
                continue
            try:
                dia = int(f[0][8:10])
            except Exception:
                continue
            minutos = _hora_a_min(f[1])
            turno = "D" if (minutos is not None and 360 <= minutos < 1080) else "N"
            d = reg.setdefault((sup, f[3].upper()), {"dias": set(), "turnos": set()})
            d["dias"].add(dia)
            d["turnos"].add((dia, turno))
    res = {}
    for s in set([k[0] for k in reg] + list(personal.keys())):
        nombres = set(n for (sp, n) in reg if sp == s)
        if s in personal:
            nombres |= set(personal[s]["VIGILADOR"].tolist())
        filas = []
        for n in sorted(nombres):
            d = reg.get((s, n), {"dias": set(), "turnos": set()})
            dias = sorted(d["dias"])
            corridas, largo, previo = [], 0, None
            for x in dias:
                largo = largo + 1 if previo is not None and x == previo + 1 else 1
                if previo is not None and x != previo + 1:
                    corridas.append(largo_ant)
                largo_ant = largo
                previo = x
            if dias:
                corridas.append(largo_ant)
            horas = len(d["turnos"]) * HORAS_TURNO
            filas.append({
                "VIGILADOR": n, "DÍAS": len(dias), "TURNOS": len(d["turnos"]), "HORAS": horas,
                "MÁX. DÍAS SEGUIDOS": max(corridas) if corridas else 0,
                "FRANCOS CORTADOS": sum(1 for c in corridas if c > MAX_DIAS_SEGUIDOS),
                "EXCESO HS": max(0, horas - HORAS_MAX_MES),
            })
        res[s] = pd.DataFrame(filas).sort_values("HORAS", ascending=False).reset_index(drop=True) if filas else pd.DataFrame(
            columns=["VIGILADOR", "DÍAS", "TURNOS", "HORAS", "MÁX. DÍAS SEGUIDOS", "FRANCOS CORTADOS", "EXCESO HS"])
    return res

def relevamiento_mes(periodo):
    anio, mes = map(int, periodo.split("-"))
    df_o = cargar_objetivos()
    jor = _leer_mes("JORNADA SUPERVISORES", periodo, 5)
    qr = _leer_mes("REGISTRO QR SUPERVISORES", periodo, 4)
    flo = _leer_mes("CONTROL DE FLOTA", periodo, 10)
    ale = _leer_mes("ALERTAS", periodo, 6)
    nov = _leer_mes("NOVEDADES GUARDIA", periodo, 5)
    pres = _leer_mes("PRESENTISMO", periodo, 6)
    personal = planificacion_mes(periodo)
    obj_a_sup = dict(zip(col_texto(df_o, 'OBJETIVO').str.strip().str.upper(), col_texto(df_o, 'SUPERVISOR').str.strip().str.upper())) if not df_o.empty else {}
    vigs = estadistica_vigiladores(periodo, pres, obj_a_sup, personal)
    filas, detalle, actividad = [], {}, {}

    for s in _supervisores_con_objetivos():
        m_sup = col_texto(df_o, 'SUPERVISOR').str.strip().str.upper() == s
        objs = col_texto(df_o, 'OBJETIVO').str.strip().str.upper()[m_sup].unique().tolist()
        dias_act = set()

        # Jornada (inicio / cierre)
        dias_j, horas_j = 0, 0.0
        sj = jor[jor[1].str.upper() == s] if not jor.empty else pd.DataFrame()
        if not sj.empty:
            for fecha, g in sj.groupby(sj[0].str[:10]):
                ini = [m for m in g[g[3].str.upper() == "INICIO"][4].map(_hora_a_min) if m is not None]
                fin = [m for m in g[g[3].str.upper() == "FIN"][4].map(_hora_a_min) if m is not None]
                if ini:
                    dias_j += 1
                    try:
                        dias_act.add(int(str(fecha)[8:10]))
                    except Exception:
                        pass
                if ini and fin and max(fin) >= min(ini):
                    horas_j += (max(fin) - min(ini)) / 60.0

        # Visitas por QR y permanencia en cada objetivo
        sq = pd.DataFrame()
        if not qr.empty:
            sq = qr[qr[3].str.upper() == s].copy()
        if not sq.empty:
            sq["_F"], sq["_O"], sq["_A"] = sq[0].str[:10], sq[1].str.upper(), sq[2].str.upper()
            sq["_M"] = sq[0].map(_hora_a_min)
            for f in sq[sq["_A"] == "INICIO"]["_F"]:
                try:
                    dias_act.add(int(str(f)[8:10]))
                except Exception:
                    pass
        det, visitas, visitados, perms_all = [], 0, 0, []
        for o in objs:
            n_vis, perms = 0, []
            if not sq.empty:
                so = sq[sq["_O"] == o]
                n_vis = int((so["_A"] == "INICIO").sum())
                for _, g in so.groupby("_F"):
                    ini = g[g["_A"] == "INICIO"]["_M"].dropna().tolist()
                    fin = g[g["_A"] == "FIN"]["_M"].dropna().tolist()
                    if ini and fin and max(fin) >= min(ini):
                        perms.append(max(fin) - min(ini))
            visitas += n_vis
            visitados += 1 if n_vis > 0 else 0
            perms_all += perms
            det.append({
                "OBJETIVO": o, "VISITAS": n_vis,
                "PERMANENCIA PROM. (MIN)": round(sum(perms) / len(perms)) if perms else "---",
                "ESTADO": "✅ VISITADO" if n_vis > 0 else "❌ SIN VISITA",
            })
        detalle[s] = pd.DataFrame(det)
        actividad[s] = dias_act

        # Flota (con suma en Python: una tabla vacía no debe romper el cálculo)
        km, monto, actas, revisar = 0.0, 0.0, 0, 0
        if not flo.empty:
            sf = flo[flo[1].str.upper() == s]
            actas = len(sf)
            km = sum(_num_ar(v) for v in sf[5])
            monto = sum(_num_ar(v) for v in sf[7])
            revisar = sum(1 for v in sf[9] if "REVISAR" in str(v).upper())

        # Pánicos (propios y de vigiladores de sus objetivos)
        panicos = 0
        if not ale.empty:
            m = (ale[2].str.upper() == "PÁNICO") & ((ale[5].str.upper() == s) | (ale[4].str.upper().isin(objs)) | (ale[1].str.upper() == s))
            panicos = int(m.sum())

        # Novedades operativas cargadas por el supervisor
        novs = 0
        if not nov.empty:
            novs = int(((nov[2].str.upper() == "NOVEDAD OPERATIVA") & (nov[4].str.upper() == s)).sum())

        # Rondas completas de sus vigiladores
        rondas = 0
        try:
            tr = tabla_recorridas_vigiladores(objs)
            if not tr.empty:
                rondas = int((tr["FECHA"].astype(str).str.startswith(periodo) & tr["ESTADO"].astype(str).str.contains("COMPLETA")).sum())
        except Exception:
            pass

        pv = personal.get(s)
        n_vig = len(pv) if pv is not None else 0
        c_lic = int((pv["ESTADO"] == "LICENCIA").sum()) if pv is not None else 0
        c_art = int((pv["ESTADO"] == "ART").sum()) if pv is not None else 0
        c_vac = int((pv["ESTADO"] == "VACACIONES").sum()) if pv is not None else 0

        vd = vigs.get(s)
        hs_vig = int(vd["HORAS"].sum()) if vd is not None and not vd.empty else 0
        n_exc = int((vd["EXCESO HS"] > 0).sum()) if vd is not None and not vd.empty else 0
        n_fc = int(vd["FRANCOS CORTADOS"].sum()) if vd is not None and not vd.empty else 0
        filas.append({
            "SUPERVISOR": s, "OBJETIVOS": len(objs), "VIGILADORES": n_vig,
            "HS VIGILADORES": hs_vig, "EXCEDIDOS": n_exc, "FRANCOS CORTADOS": n_fc,
            "DÍAS ACTIVOS": len(dias_act), "DÍAS JORNADA": dias_j, "HORAS": round(horas_j, 1),
            "VISITAS QR": visitas, "OBJ. VISITADOS": visitados,
            "COBERTURA %": round(100 * visitados / len(objs)) if objs else 0,
            "PERMANENCIA PROM. (MIN)": round(sum(perms_all) / len(perms_all)) if perms_all else 0,
            "KM": round(km, 1), "COMBUSTIBLE ($)": round(monto), "ACTAS FLOTA": actas, "ACTAS A REVISAR": revisar,
            "PÁNICOS": panicos, "NOVEDADES": novs, "RONDAS COMPLETAS": rondas,
            "LICENCIA": c_lic, "ART": c_art, "VACACIONES": c_vac,
        })
    return pd.DataFrame(filas), detalle, personal, actividad, vigs

def _tarjeta_supervisor_html(r, actividad, anio, mes, vig_df=None):
    """Tarjeta delicada por supervisor: barras finas, datos clave, tira de actividad del mes y personal a cargo."""
    import html as _h
    ndias = calendar.monthrange(anio, mes)[1]
    objs, vis, cob = int(r["OBJETIVOS"]), int(r["OBJ. VISITADOS"]), int(r["COBERTURA %"])
    dact = len(actividad)
    pct_dias = round(100 * dact / ndias) if ndias else 0
    n = int(r["VIGILADORES"])
    lic, art, vac = int(r["LICENCIA"]), int(r["ART"]), int(r["VACACIONES"])
    sin = max(0, n - lic - art - vac)

    def barra(titulo, valor, pct, color):
        pct = max(0, min(100, pct))
        return ('<div style="margin:9px 0 3px;display:flex;justify-content:space-between;font-size:11px;color:#8B95A8;letter-spacing:.4px;">'
                '<span>' + titulo + '</span><span style="color:#CBD5E1;">' + valor + '</span></div>'
                '<div style="background:#1F2430;border-radius:3px;height:4px;overflow:hidden;">'
                '<div style="background:' + color + ';height:100%;width:' + str(pct) + '%;opacity:.85;"></div></div>')

    def dato(etiqueta, valor):
        return ('<div style="flex:1;min-width:56px;text-align:center;">'
                '<div style="font-size:15px;color:#E2E8F0;font-family:Orbitron,sans-serif;">' + str(valor) + '</div>'
                '<div style="font-size:9.5px;color:#7C869A;letter-spacing:.5px;text-transform:uppercase;">' + etiqueta + '</div></div>')

    celdas = ""
    for d in range(1, ndias + 1):
        activo = d in actividad
        finde = calendar.weekday(anio, mes, d) >= 5
        fondo = "#4DB6AC" if activo else "#1F2430"
        borde = "1px solid #3A4152" if (finde and not activo) else "1px solid transparent"
        celdas += ('<span title="Día ' + str(d) + '" style="display:inline-block;width:9px;height:9px;margin:1px;'
                   'border-radius:2px;background:' + fondo + ';border:' + borde + ';"></span>')

    def seg(cant, color):
        ancho = (100.0 * cant / n) if n else 0
        return '<div style="background:' + color + ';width:' + ("%.1f" % ancho) + '%;height:100%;"></div>'

    franja = seg(sin, "#3B6B55") + seg(lic, "#C96B6B") + seg(art, "#D49A52") + seg(vac, "#9A74B5")
    leyenda = ('<span style="color:#7FB8A0;">● ' + str(sin) + ' sin novedad</span> &nbsp; '
               '<span style="color:#D98A8A;">● ' + str(lic) + ' licencia</span> &nbsp; '
               '<span style="color:#E0AE74;">● ' + str(art) + ' ART</span> &nbsp; '
               '<span style="color:#B596CC;">● ' + str(vac) + ' vacaciones</span>')

    datos = (dato("Visitas QR", r["VISITAS QR"]) + dato("Horas", r["HORAS"]) + dato("Km", r["KM"]) +
             dato("Pánicos", r["PÁNICOS"]) + dato("Novedades", r["NOVEDADES"]) + dato("Rondas", r["RONDAS COMPLETAS"]))


    # Vigiladores del mes: horas, exceso y francos cortados
    vig_html = ""
    if vig_df is not None and not vig_df.empty:
        filas_v = ""
        for _, v in vig_df.iterrows():
            horas, exc, fc = int(v["HORAS"]), int(v["EXCESO HS"]), int(v["FRANCOS CORTADOS"])
            ancho = max(0, min(100, 100.0 * horas / HORAS_MAX_MES)) if HORAS_MAX_MES else 0
            color = "#D9776F" if exc > 0 else ("#E0A458" if horas >= 0.9 * HORAS_MAX_MES else "#4DB6AC")
            chips = ""
            if fc > 0:
                chips += ('<span style="border:1px solid #5BC0CE;color:#7FD6E0;border-radius:8px;padding:0 6px;font-size:9.5px;margin-left:6px;">'
                          '✂ franco cortado · ' + str(int(v["MÁX. DÍAS SEGUIDOS"])) + ' días seguidos</span>')
            if exc > 0:
                chips += ('<span style="border:1px solid #D9776F;color:#E89A93;border-radius:8px;padding:0 6px;font-size:9.5px;margin-left:6px;">'
                          '⚠ +' + str(exc) + ' hs</span>')
            filas_v += ('<div style="margin:7px 0 0;">'
                        '<div style="display:flex;justify-content:space-between;font-size:11px;color:#CBD5E1;">'
                        '<span>' + _h.escape(str(v["VIGILADOR"])) + chips + '</span>'
                        '<span style="color:#9AA3B5;">' + str(horas) + ' hs · ' + str(int(v["DÍAS"])) + ' d</span></div>'
                        '<div style="background:#1F2430;border-radius:3px;height:3px;overflow:hidden;margin-top:3px;">'
                        '<div style="background:' + color + ';height:100%;width:' + ("%.1f" % ancho) + '%;opacity:.85;"></div></div></div>')
        tot_h, n_exc, n_fc = int(vig_df["HORAS"].sum()), int((vig_df["EXCESO HS"] > 0).sum()), int(vig_df["FRANCOS CORTADOS"].sum())
        vig_html = ('<div style="font-size:11px;color:#7C869A;margin:14px 0 2px;">Vigiladores del mes · límite ' + str(HORAS_MAX_MES) + ' hs</div>'
                    '<div style="font-size:11px;color:#9AA3B5;">' + str(tot_h) + ' hs en total · '
                    '<span style="color:#E89A93;">' + str(n_exc) + ' excedidos</span> · '
                    '<span style="color:#7FD6E0;">' + str(n_fc) + ' con franco cortado</span></div>' + filas_v)

    return ('<div style="background:rgba(22,27,34,.55);border:1px solid #2A3040;border-radius:10px;padding:12px 14px;margin:10px 0 4px;">'
            '<div style="display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;">'
            '<span style="font-family:Orbitron,sans-serif;font-size:13px;color:#7FD6E0;letter-spacing:1px;">🛡️ ' + _h.escape(str(r["SUPERVISOR"])) + '</span>'
            '<span style="font-size:11px;color:#7C869A;">' + str(objs) + (' objetivo' if objs == 1 else ' objetivos') + ' · ' + str(n) + (' vigilador' if n == 1 else ' vigiladores') + '</span></div>'
            + barra("Objetivos visitados", str(vis) + "/" + str(objs) + " · " + str(cob) + "%", cob, "#5BC0CE")
            + barra("Días con actividad", str(dact) + "/" + str(ndias) + " · " + str(pct_dias) + "%", pct_dias, "#4DB6AC")
            + '<div style="display:flex;flex-wrap:wrap;gap:4px;margin:14px 0 6px;">' + datos + '</div>'
            '<div style="font-size:11px;color:#7C869A;margin:8px 0 2px;">Actividad del mes</div>'
            '<div style="line-height:0;">' + celdas + '</div>'
            '<div style="font-size:11px;color:#7C869A;margin:12px 0 4px;">Personal a cargo</div>'
            '<div style="display:flex;height:5px;border-radius:3px;overflow:hidden;background:#1F2430;">' + franja + '</div>'
            '<div style="font-size:10.5px;margin-top:5px;">' + leyenda + '</div>'
            + vig_html + '</div>')

def renderizar_relevamiento_mensual(key_prefix="rel"):
    st.markdown("### 📊 RELEVAMIENTO MENSUAL DE SUPERVISORES")
    hoy = datetime.now(pytz.timezone("America/Argentina/Buenos_Aires"))
    c1, c2 = st.columns(2)
    mes = int(c1.selectbox("MES:", list(range(1, 13)), index=hoy.month - 1,
                           format_func=lambda m: MESES_ES[m - 1], key=f"{key_prefix}_mes"))
    anio = int(c2.number_input("AÑO:", min_value=2024, max_value=2100, value=hoy.year, step=1, key=f"{key_prefix}_anio"))
    periodo = f"{anio}-{mes:02d}"

    if st.session_state.get(f"{key_prefix}_msg"):
        st.success(st.session_state.pop(f"{key_prefix}_msg"))

    comp, detalle, personal, actividad, vigs = relevamiento_mes(periodo)
    if comp.empty:
        st.info("No hay supervisores con objetivos asignados para mostrar.")
    else:
        sup_sel = st.selectbox("SUPERVISOR:", ["TODOS"] + comp["SUPERVISOR"].tolist(), key=f"{key_prefix}_sup")
        vista = comp if sup_sel == "TODOS" else comp[comp["SUPERVISOR"] == sup_sel]

        a1, a2, a3 = st.columns(3)
        a1.metric("🛡️ SUPERVISORES", len(vista))
        a2.metric("📱 VISITAS QR", int(vista["VISITAS QR"].sum()))
        a3.metric("🎯 COBERTURA PROM.", f"{int(round(vista['COBERTURA %'].mean()))}%")

        b1, b2, b3 = st.columns(3)
        b1.metric("⏱️ HS VIGILADORES", int(vista["HS VIGILADORES"].sum()))
        b2.metric("⚠️ EXCEDIDOS", int(vista["EXCEDIDOS"].sum()))
        b3.metric("✂️ FRANCOS CORTADOS", int(vista["FRANCOS CORTADOS"].sum()))

        st.markdown("##### 🛡️ POR SUPERVISOR")
        for _, r in vista.iterrows():
            s = r["SUPERVISOR"]
            st.markdown(_tarjeta_supervisor_html(r, actividad.get(s, set()), anio, mes, vigs.get(s)), unsafe_allow_html=True)
            with st.expander("Ver detalle de objetivos y personal"):
                if s in vigs and not vigs[s].empty:
                    st.markdown("**Horas por vigilador**")
                    st.dataframe(vigs[s], use_container_width=True, hide_index=True)
                st.markdown("**Objetivos**")
                st.dataframe(detalle[s], use_container_width=True, hide_index=True)
                if s in personal:
                    st.markdown(f"**Vigiladores a cargo ({r['VIGILADORES']})**")
                    st.markdown(leyenda_planificacion_html(), unsafe_allow_html=True)
                    st.markdown(grilla_planificacion_html(personal[s], anio, mes), unsafe_allow_html=True)

        with st.expander("📋 COMPARATIVO DE TODOS LOS SUPERVISORES"):
            st.dataframe(vista, use_container_width=True, hide_index=True)
        cols_pdf = ["SUPERVISOR", "OBJETIVOS", "VIGILADORES", "DÍAS ACTIVOS", "HORAS", "VISITAS QR", "COBERTURA %",
                    "HS VIGILADORES", "EXCEDIDOS", "FRANCOS CORTADOS", "KM", "PÁNICOS", "NOVEDADES", "LICENCIA", "ART", "VACACIONES"]
        try:
            pdf_rel = generar_pdf_reporte(f"RELEVAMIENTO MENSUAL DE SUPERVISORES - {MESES_ES[mes - 1]} {anio}", vista[cols_pdf])
            st.download_button("📥 DESCARGAR RELEVAMIENTO (PDF)", data=pdf_rel,
                               file_name=f"relevamiento_supervisores_{periodo}.pdf", mime="application/pdf",
                               use_container_width=True, key=f"{key_prefix}_pdf")
        except Exception as e:
            print(f"Error generando PDF de relevamiento: {e}")

    with st.expander("➕ REGISTRAR NOVEDAD DE PERSONAL (licencia, ART, vacaciones)"):
        formulario_novedad_personal(key_prefix)

def mostrar_boton_planificacion():
    if st.session_state.get("rol_sel") not in ["JEFE DE OPERACIONES", "GERENCIA"]:
        return
    st.markdown("---")
    en_rel = st.session_state.get("ver_planificacion", False)
    if st.button("⬅️ VOLVER AL COMANDO" if en_rel else "📊 RELEVAMIENTO MENSUAL",
                 use_container_width=True, key="btn_planificacion_sidebar"):
        st.session_state.ver_planificacion = not en_rel
        st.rerun()

def mostrar_landing():
    aplicar_identidad_alfa()
    st.markdown('<div class="contenedor-logo-central"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" class="logo-phoenix"></div>', unsafe_allow_html=True)
    st.markdown('<div class="estacion-titulo">AION-YAROKU | COMMAND</div>', unsafe_a
