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
    vistos = []
    for v in valores:
        for h, m in re.findall(r'(\d{1,2}):(\d{2})', str(v)):
            if int(h) < 24 and int(m) < 60:
                hm = f"{int(h):02d}:{m}"
                if hm not in vistos:
                    vistos.append(hm)
    return sorted(vistos)


def aplicar_horarios_objetivo(obj_u, texto_horarios):
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

def relevamiento_mes(periodo):
    df_o = cargar_objetivos()
    jor = _leer_mes("JORNADA SUPERVISORES", periodo, 5)
    qr = _leer_mes("REGISTRO QR SUPERVISORES", periodo, 4)
    flo = _leer_mes("CONTROL DE FLOTA", periodo, 10)
    ale = _leer_mes("ALERTAS", periodo, 6)
    nov = _leer_mes("NOVEDADES GUARDIA", periodo, 5)
    personal = planificacion_mes(periodo)
    filas, detalle = [], {}

    for s in _supervisores_con_objetivos():
        m_sup = col_texto(df_o, 'SUPERVISOR').str.strip().str.upper() == s
        objs = col_texto(df_o, 'OBJETIVO').str.strip().str.upper()[m_sup].unique().tolist()

        dias_j, horas_j = 0, 0.0
        if not jor.empty:
            sj = jor[jor[1].str.upper() == s]
            for _, g in sj.groupby(sj[0].str[:10]):
                ini = [m for m in g[g[3].str.upper() == "INICIO"][4].map(_hora_a_min) if m is not None]
                fin = [m for m in g[g[3].str.upper() == "FIN"][4].map(_hora_a_min) if m is not None]
                if ini:
                    dias_j += 1
                if ini and fin and max(fin) >= min(ini):
                    horas_j += (max(fin) - min(ini)) / 60.0

        sq = pd.DataFrame()
        if not qr.empty:
            sq = qr[qr[3].str.upper() == s].copy()
            sq["_F"], sq["_O"], sq["_A"] = sq[0].str[:10], sq[1].str.upper(), sq[2].str.upper()
            sq["_M"] = sq[0].map(_hora_a_min)
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

        km, monto, actas, revisar = 0.0, 0.0, 0, 0
        if not flo.empty:
            sf = flo[flo[1].str.upper() == s]
            actas = len(sf)
            km = float(sf[5].map(_num_ar).sum())
            monto = float(sf[7].map(_num_ar).sum())
            revisar = int(sf[9].str.upper().str.contains("REVISAR").sum())

        panicos = 0
        if not ale.empty:
            m = (ale[2].str.upper() == "PÁNICO") & ((ale[5].str.upper() == s) | (ale[4].str.upper().isin(objs)) | (ale[1].str.upper() == s))
            panicos = int(m.sum())

        novs = 0
        if not nov.empty:
            novs = int(((nov[2].str.upper() == "NOVEDAD OPERATIVA") & (nov[4].str.upper() == s)).sum())

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

        # --- EVALUACIÓN NORMATIVA CCT DE SEGURIDAD PRIVADA ---
        # Jornada estándar de 8h/12h con topes y francos correspondientes
        horas_estimadas_mes = n_vig * 200 # Promedio estándar operativo de horas mensuales por agente
        estado_franco = "✅ CORTADO (ÓPTIMO)" if c_lic == 0 and c_art == 0 else "⚠️ REQUIERE FRANCO COMPENSATORIO"

        filas.append({
            "SUPERVISOR": s, "OBJETIVOS": len(objs), "VIGILADORES": n_vig,
            "DÍAS JORNADA": dias_j, "HORAS": round(horas_j, 1),
            "VISITAS QR": visitas, "OBJ. VISITADOS": visitados,
            "COBERTURA %": round(100 * visitados / len(objs)) if objs else 0,
            "PERMANENCIA PROM. (MIN)": round(sum(perms_all) / len(perms_all)) if perms_all else 0,
            "KM": round(km, 1), "COMBUSTIBLE ($)": round(monto), "ACTAS FLOTA": actas, "ACTAS A REVISAR": revisar,
            "PÁNICOS": panicos, "NOVEDADES": novs, "RONDAS COMPLETAS": rondas,
            "LICENCIA": c_lic, "ART": c_art, "VACACIONES": c_vac,
            "¿SE LE PUDO CORTAR EL FRANCO?": estado_franco
        })
    return pd.DataFrame(filas), detalle, personal

def renderizar_relevamiento_mensual(key_prefix="rel"):
    st.markdown("### 📊 RELEVAMIENTO MENSUAL DE SUPERVISORES & CCT")
    hoy = datetime.now(pytz.timezone("America/Argentina/Buenos_Aires"))
    c1, c2 = st.columns(2)
    mes = int(c1.selectbox("MES:", list(range(1, 13)), index=hoy.month - 1,
                           format_func=lambda m: MESES_ES[m - 1], key=f"{key_prefix}_mes"))
    anio = int(c2.number_input("AÑO:", min_value=2024, max_value=2100, value=hoy.year, step=1, key=f"{key_prefix}_anio"))
    periodo = f"{anio}-{mes:02d}"

    if st.session_state.get(f"{key_prefix}_msg"):
        st.success(st.session_state.pop(f"{key_prefix}_msg"))

    comp, detalle, personal = relevamiento_mes(periodo)
    if comp.empty:
        st.info("No hay supervisores con objetivos asignados para mostrar.")
    else:
        a1, a2, a3 = st.columns(3)
        a1.metric("🛡️ SUPERVISORES", len(comp))
        a2.metric("📱 VISITAS QR", int(comp["VISITAS QR"].sum()))
        a3.metric("🎯 COBERTURA PROM.", f"{int(round(comp['COBERTURA %'].mean()))}%")
        b1, b2, b3 = st.columns(3)
        b1.metric("⏱️ HORAS JORNADA", round(float(comp["HORAS"].sum()), 1))
        b2.metric("🚗 KM RECORRIDOS", round(float(comp["KM"].sum()), 1))
        b3.metric("🚨 PÁNICOS", int(comp["PÁNICOS"].sum()))

        st.markdown("##### 📋 COMPARATIVO DE SUPERVISORES Y CUMPLIMIENTO CCT")
        st.dataframe(comp, use_container_width=True, hide_index=True)
        cols_pdf = ["SUPERVISOR", "OBJETIVOS", "VIGILADORES", "DÍAS JORNADA", "HORAS", "VISITAS QR", "COBERTURA %",
                    "KM", "PÁNICOS", "NOVEDADES", "LICENCIA", "ART", "VACACIONES", "¿SE LE PUDO CORTAR EL FRANCO?"]
        try:
            pdf_rel = generar_pdf_reporte(f"RELEVAMIENTO MENSUAL CCT - {MESES_ES[mes - 1]} {anio}", comp[cols_pdf])
            st.download_button("📥 DESCARGAR RELEVAMIENTO & CCT (PDF)", data=pdf_rel,
                               file_name=f"relevamiento_cct_supervisores_{periodo}.pdf", mime="application/pdf",
                               use_container_width=True, key=f"{key_prefix}_pdf")
        except Exception as e:
            print(f"Error generando PDF de relevamiento: {e}")

        st.markdown("##### 🎯 COBERTURA DE OBJETIVOS VISITADOS (%)")
        st.bar_chart(comp.set_index("SUPERVISOR")["COBERTURA %"])
        st.markdown("##### ⏱️ HORAS DE JORNADA")
        st.bar_chart(comp.set_index("SUPERVISOR")["HORAS"])
        st.markdown("##### 📱 VISITAS QR A OBJETIVOS")
        st.bar_chart(comp.set_index("SUPERVISOR")["VISITAS QR"])
        st.markdown("##### 🚗 KILÓMETROS RECORRIDOS")
        st.bar_chart(comp.set_index("SUPERVISOR")["KM"])

        st.markdown("##### 👥 PERSONAL A CARGO: LICENCIA, ART Y VACACIONES")
        pers = pd.DataFrame([
            {"SUPERVISOR": s, "SIN NOVEDAD": int((d["ESTADO"] == "SIN NOVEDAD").sum()),
             "LICENCIA": int((d["ESTADO"] == "LICENCIA").sum()),
             "ART": int((d["ESTADO"] == "ART").sum()),
             "VACACIONES": int((d["ESTADO"] == "VACACIONES").sum())}
            for s, d in personal.items()
        ])
        if not pers.empty:
            st.bar_chart(pers.set_index("SUPERVISOR"), color=["#2E7D32", "#EF5350", "#FF9800", "#AB47BC"])

        st.markdown("##### 🛡️ DETALLE POR SUPERVISOR")
        for _, r in comp.iterrows():
            s = r["SUPERVISOR"]
            with st.expander(f"🛡️ {s} · cobertura {r['COBERTURA %']}% · {r['VISITAS QR']} visitas"):
                st.caption(
                    f"⏱️ {r['DÍAS JORNADA']} días de jornada ({r['HORAS']} hs) · 🚗 {r['KM']} km · 🚨 {r['PÁNICOS']} pánicos · "
                    f"📝 {r['NOVEDADES']} novedades · 🚶 {r['RONDAS COMPLETAS']} rondas completas de vigiladores")
                st.markdown("**Objetivos**")
                st.dataframe(detalle[s], use_container_width=True, hide_index=True)
                if s in personal:
                    st.markdown(f"**Vigiladores a cargo ({r['VIGILADORES']})** · 🟥 {r['LICENCIA']} licencia · 🟧 {r['ART']} ART · 🟪 {r['VACACIONES']} vacaciones")
                    st.markdown(leyenda_planificacion_html(), unsafe_allow_html=True)
                    st.markdown(grilla_planificacion_html(personal[s], anio, mes), unsafe_allow_html=True)

    with st.expander("➕ REGISTRAR NOVEDAD DE PERSONAL (licencia, ART, vacaciones)"):
        formulario_novedad_personal(key_prefix)

def mostrar_boton_planificacion():
    if st.session_state.get("rol_sel") not in ["JEFE DE OPERACIONES", "GERENCIA"]:
        return
    st.markdown("---")
    en_rel = st.session_state.get("ver_planificacion", False)
    if st.button("⬅️ VOLVER AL COMANDO" if en_rel else "📊 RELEVAMIENTO MENSUAL & CCT",
                 use_container_width=True, key="btn_planificacion_sidebar"):
        st.session_state.ver_planificacion = not en_rel
        st.rerun()

def mostrar_landing():
    aplicar_identidad_alfa()
    st.markdown('<div class="contenedor-logo-central"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" class="logo-phoenix"></div>', unsafe_allow_html=True)
    st.markdown('<div class="estacion-titulo">AION-YAROKU | COMMAND</div>', unsafe_allow_html=True)
     
    modo = st.radio("Acceso al Sistema:", ["Iniciar Sesión", "Crear Cuenta"], horizontal=True, key="radio_modo")
     
    nombre_vig_reg = ""
    obj_vig_reg = ""
    legajo_vig_reg = ""

    roles_registro = ["VIGILADOR", "MONITOREO", "JEFE DE OPERACIONES", "GERENCIA", "SUPERVISOR"]
    rol_usuario = st.selectbox("Selección del Rol", roles_registro, key="r")

    with st.form("form_acceso_real"):
        user = st.text_input("Usuario", key="u")
        password = st.text_input("Contraseña", type="password", key="p")

        if modo == "Crear Cuenta":
            nombre_vig_reg = st.text_input("Apellido y Nombre", key="nv_reg")
            legajo_vig_reg = st.text_input("Número de Legajo", key="leg_reg")

            _df_obj_login = cargar_objetivos()
            _lista_obj_login = sorted(_df_obj_login['OBJETIVO'].astype(str).str.strip().str.upper().unique().tolist()) if not _df_obj_login.empty else []
            if rol_usuario == "VIGILADOR":
                if _lista_obj_login:
                    obj_vig_reg = st.selectbox("Objetivo", _lista_obj_login, key="ov_reg")
            else:
                st.selectbox("Objetivo", ["NO APLICA PARA ESTE ROL"], key="ov_reg_off", disabled=True)

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

            elif modo == "Iniciar Sesión" and rol_usuario == "VIGILADOR":
                dni_ingresado = "".join(ch for ch in user_limpio if ch.isdigit())
                df_pad = leer_matriz_nube("PADRON VIGILADORES")
                fila_vig = pd.DataFrame()
                if dni_ingresado and pass_limpio == dni_ingresado and not df_pad.empty and 'DNI' in df_pad.columns:
                    fila_vig = df_pad[col_texto(df_pad, 'DNI').str.replace(r'\D', '', regex=True) == dni_ingresado]
                if not fila_vig.empty and str(fila_vig.iloc[0].get('ESTADO', '')).strip().upper() == "ACTIVO":
                    nombre_vig = str(fila_vig.iloc[0].get('NOMBRE', dni_ingresado)).strip().upper()
                    st.session_state.usuario_logueado = True
                    st.session_state.user_sel = nombre_vig
                    st.session_state.rol_sel = "VIGILADOR"
                    st.session_state.dni_vigilador = dni_ingresado
                    st.session_state.v_nombre_completo = nombre_vig
                    st.session_state.legajo_vigilador = str(fila_vig.iloc[0].get('LEGAJO', '')).strip()
                    st.session_state.sup_autenticado = False
                    st.session_state.admin_autenticado = False
                    sincronizar_url_sesion()
                    st.rerun()
                else:
                    st.error("❌ DNI no habilitado o contraseña incorrecta.")
                 
            elif modo == "Iniciar Sesión":
                df_usuarios = leer_matriz_nube("USUARIOS")
                usuario_ok = pd.DataFrame()
                if not df_usuarios.empty and 'USUARIO' in df_usuarios.columns and 'CONTRASEÑA' in df_usuarios.columns:
                    usuario_ok = df_usuarios[
                        (col_texto(df_usuarios, 'USUARIO').str.strip().str.upper() == user_limpio) & 
                        (col_texto(df_usuarios, 'CONTRASEÑA').str.strip() == pass_limpio)
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
            elif modo == "Crear Cuenta" and rol_usuario == "VIGILADOR":
                dni_reg = "".join(ch for ch in user_limpio if ch.isdigit())
                pass_reg = "".join(ch for ch in pass_limpio if ch.isdigit())
                nombre_reg = nombre_vig_reg.strip().upper()
                legajo_reg = legajo_vig_reg.strip().upper()
                if not dni_reg or not nombre_reg or not obj_vig_reg:
                    st.warning("⚠️ Complete DNI, apellido y nombre, y seleccione su objetivo.")
                elif pass_reg != dni_reg:
                    st.warning("⚠️ La contraseña debe coincidir con su DNI.")
                else:
                    st.cache_data.clear()
                    df_pad_reg = leer_matriz_nube("PADRON VIGILADORES")
                    ya_reg = (not df_pad_reg.empty) and ('DNI' in df_pad_reg.columns) and \
                             (dni_reg in col_texto(df_pad_reg, 'DNI').str.replace(r'\D', '', regex=True).tolist())
                    if ya_reg:
                        st.warning("⚠️ Este DNI ya se encuentra registrado. Si ya fue dado de alta, inicie sesión.")
                    elif escribir_registro_nube("PADRON VIGILADORES", [dni_reg, nombre_reg, legajo_reg, "PENDIENTE", obj_vig_reg]):
                        st.success("✅ Solicitud registrada con legajo. Quedará pendiente de aprobación por la Administración.")
            else:
                nombre_reg2 = nombre_vig_reg.strip().upper()
                legajo_reg2 = legajo_vig_reg.strip().upper()
                if not user.strip() or not password.strip() or not nombre_reg2 or not legajo_reg2:
                    st.warning("⚠️ Complete usuario, contraseña, apellido y nombre, y número de legajo.")
                else:
                    exito_reg = escribir_registro_nube("USUARIOS", [
                        user.strip().upper(), password.strip(), nombre_reg2,
                        legajo_reg2, rol_usuario, "PENDIENTE"
                    ])
                    if exito_reg:
                        st.success("✅ Solicitud de registro enviada con éxito. Inicie sesión una vez que el Administrador apruebe su cuenta.")
                    else:
                        st.error("❌ Error al registrar la cuenta en la nube.")

if not st.session_state.usuario_logueado:
    mostrar_landing()
    st.stop()

aplicar_identidad_alfa()

df_objetivos = cargar_objetivos()
df_comisarias = cargar_datos_comisarias()
LISTA_SUPS_TACTICOS = obtener_lista_supervisores_dinamica()

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

        mostrar_notificaciones_sidebar()
        mostrar_boton_planificacion()

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
        
        mostrar_notificaciones_sidebar()
        mostrar_boton_planificacion()
            
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

if st.session_state.rol_sel in ["JEFE DE OPERACIONES", "GERENCIA"] and st.session_state.get("ver_planificacion", False):
    renderizar_relevamiento_mensual(key_prefix="rel")
    st.stop()

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
    if not df_msg.empty and 'DESTINATARIO' in df_msg.columns and 'ESTADO' in df_msg.columns:
        mask = ((df_msg['DESTINATARIO'].str.strip().str.upper() == "TODOS") | 
                (df_msg['DESTINATARIO'].str.strip().str.upper() == "MONITOREO") | 
                (df_msg['DESTINATARIO'].str.strip().str.upper() == nombre_user)) & \
               (df_msg['ESTADO'].str.strip().str.upper() == "PENDIENTE")
        total_nuevos = len(df_msg[mask])

    label_msg = f"💬 MENSAJERÍA GLOBAL ({total_nuevos})" if total_nuevos > 0 else "💬 MENSAJERÍA GLOBAL"

    t_radar, t_mensajeria, t_nov = st.tabs([
        "🚨 RADAR S.O.S", label_msg, "Auditoría y registro de monitoreo por supervisor"
    ]) 

    with t_radar:
        st.subheader("📡 RADAR GLOBAL DE OBJETIVOS Y PÁNICOS ACTIVOS")
         
        df_alertas_radar = leer_matriz_nube("ALERTAS")
        if not df_alertas_radar.empty:
            df_alertas_radar.columns = [str(c).strip().upper() for c in df_alertas_radar.columns]
            panicos_pendientes_globales = df_alertas_radar[
                (df_alertas_radar['TIPO'].astype(str).str.upper() == "PÁNICO") & 
                (df_alertas_radar['ESTADO'].astype(str).str.upper() == "PENDIENTE")
            ] if 'TIPO' in df_alertas_radar.columns and 'ESTADO' in df_alertas_radar.columns else pd.DataFrame()
             
            if not panicos_pendientes_globales.empty:
                st.error("🚨 ¡HAY PÁNICOS S.O.S ACTIVOS EN LA RED!")
                for idx_gp, row_gp in panicos_pendientes_globales.iterrows():
                    col_p1, col_p2 = st.columns([3, 1])
                    col_p1.markdown(f"**Usuario:** {row_gp.get('USUARIO','')} | **Objetivo:** {row_gp.get('OBJETIVO','')} | **Fecha:** {row_gp.get('FECHA','')}")
                     
                    key_btn_radar = f"fin_pan_radar_{idx_gp}_{row_gp.get('USUARIO','')}_{row_gp.get('OBJETIVO','')}_{row_gp.get('FECHA','')}".replace(" ", "_")
                    if col_p2.button(f"✅ Finalizar Pánico", key=key_btn_radar):
                        gc_rg = conectar_google()
                        if gc_rg:
                            hoja_alt_rg = gc_rg.open_by_key(ID_MAESTRO_DB).worksheet("ALERTAS")
                            todas_a_rg = hoja_alt_rg.get_all_values()
                            for i_rg, fila_rg in enumerate(todas_a_rg[1:], start=2):
                                if len(fila_rg) > 5 and fila_rg[1].strip().upper() == str(row_gp.get('USUARIO','')).strip().upper() and fila_rg[4].strip().upper() == str(row_gp.get('OBJETIVO','')).strip().upper() and fila_rg[3].strip().upper() == "PENDIENTE":
                                    hoja_alt_rg.update_acell(f"D{i_rg}", "FINALIZADO")
                                    st.success("✅ Pánico finalizado correctamente desde el Radar.")
                                    st.cache_data.clear()
                                    st.rerun()
                st.markdown("---")

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
                df_mapa_filtrado_sup = df_mapa_filtrado_sup[col_texto(df_mapa_filtrado_sup, 'SUPERVISOR').str.strip().str.upper() == sup_filtro_mono]

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
                    (col_texto(df_jornadas_mon, col_sup_h).str.strip().str.upper() == sup_filtro_mono) & 
                    (col_texto(df_jornadas_mon, col_fec_h).str.contains(fecha_hoy_str, na=False)) &
                    (col_texto(df_jornadas_mon, col_acc_h).str.strip().str.upper() == 'INICIO')
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
            localidad_obj_val = str(datos_obj.get('LOCALIDAD', '')).strip().upper()
             
            df_comis_filtro_mono = df_comisarias
            if localidad_obj_val and 'LOCALIDAD' in df_comisarias.columns:
                df_sub_c = df_comisarias[col_texto(df_comisarias, 'LOCALIDAD').str.strip().str.upper() == localidad_obj_val]
                if not df_sub_c.empty:
                    df_comis_filtro_mono = df_sub_c

            for _, com in df_comis_filtro_mono.iterrows():
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
                max_zoom=19,
                tiles="OpenStreetMap"
            )

            m_mon.get_root().header.add_child(Element("""
            <style>
            .leaflet-container { background: #262626 !important; }
            .leaflet-tile-pane {
                filter: invert(100%) hue-rotate(180deg) grayscale(100%) brightness(0.8) contrast(1.25);
            }
            @keyframes pulse {
                from { transform: scale(1); opacity: 1; box-shadow: 0 0 0 0 rgba(255,0,0,.8); }
                to   { transform: scale(1.7); opacity: .35; box-shadow: 0 0 18px 8px rgba(255,0,0,.6); }
            }
            </style>
            """))

            df_com = cargar_datos_comisarias()
            comisarias_en_panico = set()

            for _, r in df_mapa_filtrado_sup.iterrows():
                obj_nombre = str(r['OBJETIVO']).strip().upper()
                es_panico = obj_nombre in lista_objetivos_en_panico
                es_el_seleccionado = (obj_nombre == str(obj_seleccionado).strip().upper())

                if es_panico:
                    texto_tooltip = f"🚨 PÁNICO | OBJ: {obj_nombre}"
                    if 'OBJETIVO' in df_emergencias.columns:
                        alerta_activa = df_emergencias[
                            (col_texto(df_emergencias, 'OBJETIVO').str.strip().str.upper() == obj_nombre) &
                            (col_texto(df_emergencias, 'ESTADO').str.strip().str.upper() == 'PENDIENTE') &
                            (col_texto(df_emergencias, 'TIPO').str.strip().str.upper() == 'PÁNICO')
                        ]
                        if not alerta_activa.empty:
                            texto_tooltip = f"🚨 PÁNICO: {alerta_activa.iloc[-1].get('USUARIO', 'AGENTE')} | OBJ: {obj_nombre}"

                    folium.Marker(
                        location=[r['LATITUD'], r['LONGITUD']],
                        tooltip=texto_tooltip,
                        icon=folium.DivIcon(
                            icon_size=(30, 30), icon_anchor=(15, 15),
                            html='<div style="background-color:#FF0000;width:16px;height:16px;border-radius:50%;border:2px solid white;animation:pulse 0.8s infinite alternate;"></div>'
                        )
                    ).add_to(m_mon)

                    com = comisaria_mas_cercana(r['LATITUD'], r['LONGITUD'], str(r.get('LOCALIDAD', '')).strip().upper(), df_com)
                    if com is not None:
                        comisarias_en_panico.add(com['COMISARIA'])
                        ruta = obtener_ruta_calles_osrm(r['LATITUD'], r['LONGITUD'], com['LATITUD'], com['LONGITUD'])
                        folium.PolyLine(locations=ruta, color="#000000", weight=5, opacity=0.4).add_to(m_mon)
                        folium.PolyLine(locations=ruta, color="#39FF14", weight=4, opacity=0.8).add_to(m_mon)

                elif es_el_seleccionado:
                    folium.CircleMarker(
                        location=[r['LATITUD'], r['LONGITUD']], radius=10, color="#FFFFFF",
                        fill=True, fill_color="#00E5FF", fill_opacity=0.9,
                        tooltip=f"🎯 {obj_nombre} | 👤 SUP: {r.get('SUPERVISOR', 'N/A')}"
                    ).add_to(m_mon)
                else:
                    folium.CircleMarker(
                        location=[r['LATITUD'], r['LONGITUD']], radius=7, color="#00E5FF", fill=True,
                        tooltip=f"🎯 {obj_nombre} | 👤 SUP: {r.get('SUPERVISOR', 'N/A')}"
                    ).add_to(m_mon)

            for _, c in df_com.iterrows():
                en_panico = c['COMISARIA'] in comisarias_en_panico
                color_icono = "#FFD600" if en_panico else "#0000FF"
                tamano_fuente = "26px" if en_panico else "20px"
                sufijo = " 🌟 [MÁS CERCANA AL PÁNICO]" if en_panico else ""
                folium.Marker(
                    location=[c['LATITUD'], c['LONGITUD']],
                    tooltip=f"👮 {c['COMISARIA']}{sufijo}",
                    icon=folium.DivIcon(html=f"""<div style="font-size:{tamano_fuente};color:{color_icono};text-shadow:0 0 10px {color_icono};"><i class="fa fa-shield"></i></div>""")
                ).add_to(m_mon)

            st_folium(m_mon, use_container_width=True, height=500, key="mapa_monitoreo_radar_tactico", returned_objects=[])
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
                for s in col_texto(df_qr_m_base, col_sup_qm).dropna().str.strip().str.upper():
                    if s and s != "NAN": sups_dinamicos_set.add(s)

        if not df_jor_m_base.empty:
            df_jor_m_base.columns = [str(c).strip().upper() for c in df_jor_m_base.columns]
            col_sup_jm = 'SUPERVISOR' if 'SUPERVISOR' in df_jor_m_base.columns else df_jor_m_base.columns[1]
            if col_sup_jm in df_jor_m_base.columns:
                for s in col_texto(df_jor_m_base, col_sup_jm).dropna().str.strip().str.upper():
                    if s and s != "NAN": sups_dinamicos_set.add(s)

        if not df_flota_m_base.empty:
            df_flota_m_base.columns = [str(c).strip().upper() for c in df_flota_m_base.columns]
            col_sup_fm = 'SUPERVISOR' if 'SUPERVISOR' in df_flota_m_base.columns else df_flota_m_base.columns[1]
            if col_sup_fm in df_flota_m_base.columns:
                for s in col_texto(df_flota_m_base, col_sup_fm).dropna().str.strip().str.upper():
                    if s and s != "NAN": sups_dinamicos_set.add(s)

        sups_dinamicos_lista = sorted(list(sups_dinamicos_set))

        opciones_filtro_monitoreo = ["VER TODOS LOS SUPERVISORES"] + sups_dinamicos_lista
        sup_elegido_monitoreo_tab = st.selectbox("🔍 FILTRAR AUDITORÍA POR SUPERVISOR O VER TODOS:", opciones_filtro_monitoreo, key="filtro_auditoria_monitoreo_gral")

        lista_sups_a_mostrar = sups_dinamicos_lista if sup_elegido_monitoreo_tab == "VER TODOS LOS SUPERVISORES" else [sup_elegido_monitoreo_tab]

        if len(lista_sups_a_mostrar) > 0:
            pestanas_sups = st.tabs(lista_sups_a_mostrar)
             
            for idx_p, sup_seleccionado_mono in enumerate(lista_sups_a_mostrar):
                with pestanas_sups[idx_p]:
                    st.markdown(f"### 🛡️ PANEL DE CONTROL: {sup_seleccionado_mono}")
                     
                    st.markdown("#### 📱 Fichajes QR")
                    if not df_qr_m_base.empty:
                        col_sup_qm = 'SUPERVISOR' if 'SUPERVISOR' in df_qr_m_base.columns else df_qr_m_base.columns[3]
                        df_sup_qrs_m = df_qr_m_base[col_texto(df_qr_m_base, col_sup_qm).str.strip().str.upper() == str(sup_seleccionado_mono).strip().upper()]
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
                        objs_del_sup = [o.strip().upper() for o in df_objetivos[col_texto(df_objetivos, 'SUPERVISOR').str.strip().str.upper() == str(sup_seleccionado_mono).strip().upper()]['OBJETIVO'].tolist()] if not df_objetivos.empty else []
                         
                        if len(objs_del_sup) > 0 and 'OBJETIVO' in df_nov_m_base.columns:
                            df_nov_m_base['OBJETIVO_CLEAN'] = col_texto(df_nov_m_base, 'OBJETIVO').str.strip().str.upper()
                             
                            col_evento_real = None
                            for posible_col in ['TIPO_EVENTO', 'TIPO EVENTO', 'EVENTO', 'TIPO']:
                                if posible_col in df_nov_m_base.columns:
                                    col_evento_real = posible_col
                                    break
                            if col_evento_real is None and len(df_nov_m_base.columns) > 2:
                                col_evento_real = df_nov_m_base.columns[2]

                            if col_evento_real:
                                mask_fich = df_nov_m_base['OBJETIVO_CLEAN'].isin(objs_del_sup) & \
                                            col_texto(df_nov_m_base, col_evento_real).str.strip().str.upper().str.contains("MARCACIÓN|FICHAJE|INGRESO|EGRESO", regex=True)
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
                        objs_del_sup = df_objetivos[col_texto(df_objetivos, 'SUPERVISOR').str.strip().str.upper() == sup_seleccionado_mono]['OBJETIVO'].tolist() if not df_objetivos.empty else []
                         
                        if len(objs_del_sup) > 0:
                            col_obj_v = 'OBJETIVO' if 'OBJETIVO' in df_vig_rel_m_base.columns else df_vig_rel_m_base.columns[2]
                            df_rel_sup_filtrado = df_vig_rel_m_base[col_texto(df_vig_rel_m_base, col_obj_v).str.strip().str.upper().isin([o.upper() for o in objs_del_sup])]
                             
                            if not df_rel_sup_filtrado.empty:
                                st.dataframe(df_rel_sup_filtrado.iloc[::-1], use_container_width=True, hide_index=True)
                            else:
                                st.info("No hay relevos de vigiladores registrados para los objetivos de este supervisor.")
                        else:
                            st.info("Este supervisor no tiene objetivos asignados.")
                    else:
                        st.info("No hay relevos de vigiladores registrados.")

                    st.markdown("---")
                    st.markdown("#### 🚶 Recorridas de Vigiladores")
                    objs_rec_m = df_objetivos[col_texto(df_objetivos, 'SUPERVISOR').str.strip().str.upper() == str(sup_seleccionado_mono).strip().upper()]['OBJETIVO'].tolist() if not df_objetivos.empty else []
                    df_rec_m = tabla_recorridas_vigiladores(objs_rec_m)
                    if not df_rec_m.empty:
                        st.dataframe(df_rec_m, use_container_width=True, hide_index=True)
                    else:
                        st.info("Sin recorridas registradas para los objetivos de este supervisor.")

                    st.markdown("---")
                    st.markdown("#### 🚨 Pánico S.O.S de Supervisor")
                    if not df_alt_m_base.empty:
                        df_alt_m_base.columns = [str(c).strip().upper() for c in df_alt_m_base.columns]
                        df_panicos_op = df_alt_m_base[col_texto(df_alt_m_base, 'TIPO').str.strip().str.upper() == "PÁNICO"].copy() if 'TIPO' in df_alt_m_base.columns else pd.DataFrame()
                         
                        if not df_panicos_op.empty:
                            mask_solo_supervisor = (col_texto(df_panicos_op, 'USUARIO').str.strip().str.upper() == str(sup_seleccionado_mono).strip().upper())
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
                        df_panicos_op = df_alt_m_base[col_texto(df_alt_m_base, 'TIPO').str.strip().str.upper() == "PÁNICO"].copy() if 'TIPO' in df_alt_m_base.columns else pd.DataFrame()
                        objs_del_sup = [o.strip().upper() for o in df_objetivos[col_texto(df_objetivos, 'SUPERVISOR').str.strip().str.upper() == str(sup_seleccionado_mono).strip().upper()]['OBJETIVO'].tolist()] if not df_objetivos.empty else []
                         
                        if not df_panicos_op.empty:
                            mask_obj_del_sup = col_texto(df_panicos_op, 'OBJETIVO').str.strip().str.upper().isin([o.upper() for o in objs_del_sup])
                            mask_no_es_supervisor = ~(col_texto(df_panicos_op, 'USUARIO').str.strip().str.upper() == str(sup_seleccionado_mono).strip().upper())
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
