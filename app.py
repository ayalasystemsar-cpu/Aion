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
            "COMISARÍA AVELLANEDA 1RA", "COMISARÍA CAMPANA 1RA", "COMISARÍA SAN FERNANDO 1RA", "COMISARÍA TIGRE 1RA", "COMISARÍA PILAR 6TA"
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
            "Gral. Lavalle 150", "Rivadavia 750", "Constitución 720", "Cazón 1250", "Ruta 25 s/n"
        ],
        "LOCALIDAD": [
            "CABA", "CABA", "CABA", "CABA", "CABA", "CABA", "CABA", "CABA", "CABA", "CABA",
            "CABA", "CABA", "CABA", "CABA", "CABA", "CABA", "CABA", "CABA", "CABA", "CABA",
            "CABA", "CABA", "CABA", "CABA", "CABA", "CABA", "CABA", "CABA", "CABA", "CABA",
            "CABA", "CABA", "CABA", "CABA", "CABA", "CABA", "CABA", "CABA", "CABA", "SAN MARTÍN",
            "AVELLANEDA", "CAMPANA", "SAN FERNANDO", "TIGRE", "PILAR"
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
            "011-4201-1122", "03489-422111", "011-4744-0192", "011-4512-9900", "0230-449-0111"
        ],
        "LATITUD": [
            -34.5985, -34.6037, -34.6112, -34.5852, -34.5910, -34.6080, -34.6150, -34.6390, -34.6350, -34.6410,
            -34.6150, -34.6220, -34.6250, -34.6180, -34.6190, -34.6280, -34.6500, -34.6750, -34.6600, -34.6400,
            -34.6450, -34.6500, -34.6200, -34.6150, -34.6100, -34.6000, -34.5950, -34.5543, -34.5684, -34.5600,
            -34.5574, -34.5550, -34.5500, -34.5877, -34.5850, -34.5800, -34.5880, -34.5800, -34.5750, -34.5801,
            -34.6641, -34.1636, -34.4401, -34.4241, -34.4170
        ],
        "LONGITUD": [
            -58.3838, -58.3862, -58.3790, -58.4012, -58.3950, -58.3850, -58.3800, -58.4050, -58.3650, -58.4800,
            -58.4200, -58.3830, -58.4400, -58.4350, -58.3750, -58.4600, -58.4500, -58.4650, -58.4450, -58.5100,
            -58.5050, -58.5200, -58.4900, -58.4600, -58.4750, -58.4950, -58.4700, -58.4721, -58.4820, -58.4600,
            -58.4611, -58.4550, -58.4500, -58.4160, -58.4100, -58.3950, -58.4700, -58.4600, -58.4800, -58.5414,
            -58.3680, -58.9614, -58.5561, -58.5797, -58.8682
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

    # ORDEN EXACTO DE COLUMNAS EN LA NUBE: [OBJETIVO, DIRECCION, LOCALIDAD, SUPERVISOR, LATITUD, LONGITUD, RESPONSABLES, ALARMA]
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
            for nombre in ["REGISTRO QR SUPERVISORES", "REGISTRO-QR-SUPERVISORES"]:
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
        
        .block-container { padding-left: 1rem !important; padding-right: 1rem !important; padding-top: 1rem !important; max-width: 100% !important; }

        .contenedor-logo-central { display: flex; justify-content: center; align-items: center; width: 100%; margin: 10px 0; }
        .logo-phoenix { 
            width: 100% !important; max-width: 320px !important; height: auto !important; object-fit: contain !important;
            border: 2px solid #00e5ff !important; box-shadow: 0 0 35px rgba(0, 229, 255, 0.5) !important; border-radius: 4px !important; background-color: #000 !important; 
        }
        .estacion-titulo {
            font-family: 'Orbitron', sans-serif; color: #00E5FF !important; font-size: 22px; margin-top: 10px;
            display: flex; align-items: center; justify-content: center; gap: 12px;
            text-shadow: 0 0 15px rgba(0, 229, 255, 0.4); letter-spacing: 2px; text-transform: uppercase; text-align: center;
        }

        header { background: transparent !important; background-color: transparent !important; }
        .stApp div[data-testid="stExpander"] { background-color: #1A1C23 !important; border: 1px solid #2D313E !important; border-radius: 8px !important; }
        .stApp div[data-testid="stExpander"] summary p { color: #E0E0E0 !important; font-size: 14px !important; font-weight: 600 !important; text-transform: uppercase; }
        .stApp input { background-color: #252833 !important; color: #FFFFFF !important; border: 1px solid #1A1C23 !important; border-radius: 6px !important; unicode-bidi: plaintext !important; direction: ltr !important; text-align: left !important; }
        .stApp label p { color: #A0A5B5 !important; font-family: 'Orbitron', sans-serif !important; font-size: 11px !important; font-weight: bold !important; letter-spacing: 0.5px; text-transform: uppercase; }
        .radar-box { border: 1px solid #00e5ff; border-radius: 8px; padding: 5px; background: #000000; box-shadow: 0 0 20px rgba(0, 229, 255, 0.2); }
        
        .stButton > button[kind="primary"] { 
            background: radial-gradient(circle, #FF0000 0%, #8B0000 100%) !important; color: white !important; border-radius: 50% !important; width: 110px !important; height: 110px !important; 
            border: 3px solid #333 !important; box-shadow: 0 0 25px rgba(255, 0, 0, 0.6) !important; font-family: 'Orbitron', sans-serif; font-size: 11px !important; font-weight: bold; display: block; margin: 0 auto;
        }
        .panel-novedad { border: 1px solid #333; border-radius: 8px; padding: 15px; margin-top: 15px; background-color: rgba(10, 10, 11, 0.9); }
        
        .stTabs [data-baseweb="tab-list"] { gap: 6px !important; background-color: transparent !important; flex-wrap: nowrap !important; overflow-x: auto !important; white-space: nowrap !important; padding-bottom: 5px !important; }
        .stTabs [data-baseweb="tab"] {
            background-color: rgba(26, 28, 35, 0.6) !important; border: 1px solid #2D313E !important; color: #A0A5B5 !important;
            border-radius: 4px 4px 0px 0px !important; padding: 8px 12px !important; font-family: 'Orbitron', sans-serif; font-size: 11px !important; font-weight: bold; flex-shrink: 0 !important;
        }
        .stTabs [aria-selected="true"] { background-color: #1A1C23 !important; border-top: 2px solid #00E5FF !important; color: #00E5FF !important; }
        div[data-testid="stMetric"] { background-color: rgba(10, 11, 15, 0.6) !important; border: 1px solid #1A1C23 !important; border-radius: 6px !important; padding: 8px !important; }
        div[data-testid="stMetricLabel"] p { color: #00E5FF !important; font-family: 'Rajdhani', sans-serif !important; font-size: 12px !important; font-weight: bold !important; text-transform: uppercase; letter-spacing: 0.5px; }
        div[data-testid="stMetricValue"] div { color: #FFFFFF !important; font-family: 'Orbitron', sans-serif !important; font-size: 18px !important; unicode-bidi: plaintext !important; direction: ltr !important; }
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
                sincronizar_url_sesion()
                st.rerun()

            elif modo == "Iniciar Sesión" and rol_usuario == "MONITOREO" and (user_limpio in ["MONITOREO", "OPERADOR", "OPERADOR CENTRAL"] or pass_limpio == "1234"):
                st.session_state.usuario_logueado = True
                st.session_state.user_sel = "OPERADOR CENTRAL" if user_limpio == "MONITOREO" else user_limpio
                st.session_state.rol_sel = "MONITOREO"
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
                        if rol_encontrado == "SUPERVISOR":
                            st.session_state.sup_autenticado = True
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
df_comisarias = cargar_datos_comisarias()
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
# ROL: MONITOREO
# =========================================================================
if st.session_state.rol_sel == "MONITOREO":
    col1, col2, col3, col4 = st.columns(4)
    
    with col1.container():
        @st.fragment(run_every=5)
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

    t_radar, t_mensajeria = st.tabs(["🚨 RADAR S.O.S", "💬 MENSAJERÍA"])

    with t_radar:
        st.subheader("📡 RADAR GLOBAL DE OBJETIVOS Y PÁNICOS ACTIVOS")
        
        df_alertas_radar = leer_matriz_nube("ALERTAS")
        if not df_alertas_radar.empty:
            df_alertas_radar.columns = [str(c).strip().upper() for c in df_alertas_radar.columns]
            panicos_activos_radar = df_alertas_radar[
                (df_alertas_radar['TIPO'].astype(str).str.upper() == "PÁNICO") & 
                (df_alertas_radar['ESTADO'].astype(str).str.upper() == "PENDIENTE")
            ] if 'TIPO' in df_alertas_radar.columns and 'ESTADO' in df_alertas_radar.columns else pd.DataFrame()
            
            if not panicos_activos_radar.empty:
                st.markdown("#### ⚠️ Pánicos S.O.S Pendientes en la Red")
                for index, row_pan in panicos_activos_radar.iterrows():
                    col_info_pan, col_btn_pan = st.columns([3, 1])
                    with col_info_pan:
                        st.warning(f"🚨 **PÁNICO ACTIVADO** | Fecha: {row_pan.get('FECHA', '---')} | Usuario: {row_pan.get('USUARIO', '---')} | Objetivo: {row_pan.get('OBJETIVO', '---')}")
                    with col_btn_pan:
                        fila_real_excel = index + 2
                        if st.button(f"🏁 Finalizar Pánico", key=f"btn_fin_pan_{index}"):
                            if actualizar_celda("ALERTAS", fila_real_excel, "D", "FINALIZADO"):
                                st.success("✅ Pánico finalizado correctamente.")
                                st.cache_data.clear()
                                st.rerun()
                st.markdown("---")

        if st.button("🔄 ACTUALIZAR RADAR DE CONTROL", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    with t_mensajeria:
        renderizar_mensajeria_global("MONITOREO")


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

        t_vis_qr, t_nuevo_obj = st.tabs(["Visita QR", "➕ CARGAR OBJETIVO"])
        
        with t_vis_qr:
            st.markdown("### 📱 CENTRO TÁCTICO & GENERADOR QR DE OBJETIVOS")
            if not df_objetivos_filtrados.empty:
                obj_select = st.selectbox("Seleccione su Objetivo Asignado:", df_objetivos_filtrados['OBJETIVO'].unique(), key="obj_qr_tactico")
            else:
                st.warning("⚠️ No se encontraron objetivos asignados a su usuario Supervisor.")

        with t_nuevo_obj:
            st.markdown("### ➕ AUTOGESTIÓN Y ALTA DE OBJETIVOS TÁCTICOS")
            with st.form(key="form_crear_objetivo_supervisor", clear_on_submit=False):
                col_no1, col_no2 = st.columns(2)
                nuevo_nombre_obj = col_no1.text_input("NOMBRE DEL OBJETIVO:", value="CARLOS PELLEGRINI").upper().strip()
                nueva_direccion = col_no2.text_input("DIRECCIÓN:", value="1163").upper().strip()
                
                col_loc1, col_loc2 = st.columns(2)
                nueva_localidad = col_loc1.text_input("LOCALIDAD:", value="CABA").upper().strip()
                nueva_lat = col_loc2.text_input("LATITUD (Ej: -34.5985):", value="-34.5985")
                
                col_lon1, col_lon2 = st.columns(2)
                nueva_lon = col_lon1.text_input("LONGITUD (Ej: -58.3838):", value="-58.3838")
                nuevos_responsables = col_lon2.text_input("RESPONSABLES:", value="CENTRO").upper().strip()
                
                supervisor_asignado_actual = st.session_state.user_sel.upper()
                if st.form_submit_button("🚀 DAR DE ALTA OBJETIVO EN LA RED"):
                    if nuevo_nombre_obj and nueva_lat and nueva_lon:
                        exito_alta = registrar_objetivo_con_comisaria_automatica(
                            nuevo_nombre_obj, nueva_direccion, nueva_localidad, supervisor_asignado_actual, nueva_lat, nueva_lon, nuevos_responsables
                        )
                        if exito_alta:
                            st.success(f"✅ ¡Objetivo '{nuevo_nombre_obj}' y comisaría jurisdiccional cargados con éxito en la red!")
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error("❌ Error al registrar en la nube. Verifique la conexión con Google Sheets.")
                    else:
                        st.warning("⚠️ Complete los campos obligatorios (Nombre, Latitud y Longitud).")
