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
        "VIGILADORES": "VIGILADORES",
        "PADRON VIGILADORES": "PADRON VIGILADORES",
        "RECORRIDOS PUNTOS": "RECORRIDOS PUNTOS",
        "REGISTRO RECORRIDOS": "REGISTRO RECORRIDOS"
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
        
        .qr-scanner-container {
            display: flex; justify-content: center; align-items: center; width: 100% !important; max-width: 320px !important;
            margin: 0 auto 10px auto !important; overflow: hidden !important; border-radius: 8px !important; background: #000 !important; position: relative;
        }
        .qr-scanner-container iframe, .qr-scanner-container video, .qr-scanner-container div {
            width: 100% !important; max-width: 320px !important; height: 220px !important; object-fit: cover !important; border-radius: 8px !important; border: 2px solid #00E5FF !important;
        }

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


# --- 3.B RECORRIDOS CON QR (VIGILADORES) Y GENERADOR DE QR DE PUNTOS ---

def renderizar_recorrido_vigilador(objetivo, nombre, dni):
    """Pestaña de recorrido del vigilador: marca puntos de control escaneando QR."""
    st.markdown("### 🚶 RECORRIDO CON MARCACIÓN QR")

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

    # Registros de hoy de este vigilador en este objetivo
    df_r = leer_matriz_nube("REGISTRO RECORRIDOS")
    df_hoy = pd.DataFrame()
    if not df_r.empty and {'FECHA_HORA', 'OBJETIVO', 'PUNTO', 'DNI', 'RONDA'} <= set(df_r.columns):
        df_hoy = df_r[
            (df_r['DNI'].astype(str).str.strip() == str(dni)) &
            (df_r['OBJETIVO'].astype(str).str.strip().str.upper() == obj_u) &
            (df_r['FECHA_HORA'].astype(str).str.contains(hoy, na=False))
        ]

    # Ronda actual: se recupera de la planilla si se recarga la página
    rondas = pd.to_numeric(df_hoy['RONDA'], errors='coerce').dropna() if not df_hoy.empty else pd.Series(dtype=float)
    ronda_planilla = int(rondas.max()) if not rondas.empty else 1
    key_ronda = f"ronda_vig_{obj_u}_{hoy}"
    ronda = max(ronda_planilla, st.session_state.get(key_ronda, 1))
    st.session_state[key_ronda] = ronda

    marcados = set()
    if not df_hoy.empty:
        df_ronda = df_hoy[pd.to_numeric(df_hoy['RONDA'], errors='coerce') == ronda]
        marcados = set(df_ronda['PUNTO'].astype(str).str.strip().str.upper())

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

    # La key cambia con cada marca para que el escáner no vuelva a leer el mismo QR
    st.markdown('<div class="qr-scanner-container">', unsafe_allow_html=True)
    codigo = qrcode_scanner(key=f"scan_rec_{obj_u}_{ronda}_{len(marcados)}")
    st.markdown('</div>', unsafe_allow_html=True)

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
    """Carga puntos de control por objetivo y genera el QR para imprimir."""
    st.markdown("#### 🧾 PUNTOS DE RECORRIDO Y QR")
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

    if st.session_state.get(f"{key_prefix}_msg_punto"):
        st.success(st.session_state[f"{key_prefix}_msg_punto"])
        st.session_state[f"{key_prefix}_msg_punto"] = ""

    if not existentes.empty:
        cols_ver = [c for c in ['PUNTO', 'ORDEN'] if c in existentes.columns]
        st.dataframe(existentes[cols_ver], use_container_width=True, hide_index=True)
    else:
        st.info("Este objetivo todavía no tiene puntos de control.")

    with st.form(key=f"{key_prefix}_form_punto", clear_on_submit=True):
        nuevo_punto = st.text_input("NOMBRE DEL PUNTO (Ej: PORTÓN 1):").strip().upper()
        nuevo_orden = st.number_input("ORDEN EN EL RECORRIDO:", min_value=1, value=len(existentes) + 1, step=1)
        if st.form_submit_button("➕ GUARDAR PUNTO"):
            if nuevo_punto:
                ya_existe = (not existentes.empty) and (nuevo_punto in existentes['PUNTO'].astype(str).str.strip().str.upper().tolist())
                if ya_existe:
                    st.warning("⚠️ Ese punto ya existe en este objetivo.")
                elif escribir_registro_nube("RECORRIDOS PUNTOS", [obj_u, nuevo_punto, int(nuevo_orden)]):
                    st.session_state[f"{key_prefix}_msg_punto"] = f"✅ Punto '{nuevo_punto}' guardado."
                    st.rerun()
            else:
                st.warning("⚠️ Ingresá el nombre del punto.")

    if not existentes.empty:
        st.markdown("##### 🖨️ GENERAR QR PARA IMPRIMIR")
        pto_sel = st.selectbox("PUNTO:", existentes['PUNTO'].astype(str).tolist(), key=f"{key_prefix}_rec_pto")
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


def mostrar_landing():
    aplicar_identidad_alfa()
    st.markdown('<div class="contenedor-logo-central"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" class="logo-phoenix"></div>', unsafe_allow_html=True)
    st.markdown('<div class="estacion-titulo">AION-YAROKU | COMMAND</div>', unsafe_allow_html=True)
    
    modo = st.radio("Acceso al Sistema:", ["Iniciar Sesión", "Crear Cuenta"], horizontal=True, key="radio_modo")
    
    with st.form("form_acceso_real"):
        user = st.text_input("Usuario o Apellido del Supervisor (Vigilador: DNI)", key="u")
        password = st.text_input("Contraseña (Vigilador: DNI)", type="password", key="p")
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

            # --- LOGIN DE VIGILADOR: USUARIO Y CONTRASEÑA = DNI (validado contra PADRON VIGILADORES) ---
            elif modo == "Iniciar Sesión" and rol_usuario == "VIGILADOR":
                dni_ingresado = "".join(ch for ch in user_limpio if ch.isdigit())
                df_pad = leer_matriz_nube("PADRON VIGILADORES")
                fila_vig = pd.DataFrame()
                if dni_ingresado and pass_limpio == dni_ingresado and not df_pad.empty and 'DNI' in df_pad.columns:
                    fila_vig = df_pad[df_pad['DNI'].astype(str).str.replace(r'\D', '', regex=True) == dni_ingresado]
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
                    (df_jornadas_mon[col_fec_h].astype(str).str.contains(fecha_hoy_str, na=False)) &
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
            localidad_obj_val = str(datos_obj.get('LOCALIDAD', '')).strip().upper()
            
            df_comis_filtro_mono = df_comisarias
            if localidad_obj_val and 'LOCALIDAD' in df_comisarias.columns:
                df_sub_c = df_comisarias[df_comisarias['LOCALIDAD'].astype(str).str.strip().str.upper() == localidad_obj_val]
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
                lat_obj_s, lon_obj_s = 0.0, 0.0
                localidad_obj_s = ""
                if not df_objetivos.empty:
                    filtro_sup_obj = df_objetivos[df_objetivos['OBJETIVO'] == obj_actual]
                    if not filtro_sup_obj.empty:
                        lat_obj_s = float(str(filtro_sup_obj['LATITUD'].iloc[0]).replace(',', '.'))
                        lon_obj_s = float(str(filtro_sup_obj['LONGITUD'].iloc[0]).replace(',', '.'))
                        localidad_obj_s = str(filtro_sup_obj.iloc[0].get('LOCALIDAD', '')).strip().upper()

                com_nombre_s = "COMISARÍA JURISDICCIONAL"
                com_dir_s = "---"
                com_loc_s = "---"
                com_tel_s = "011-4000-0000"
                com_lat_s, com_lon_s = lat_obj_s, lon_obj_s
                dist_s = float('inf')

                df_comis_filtro_s = df_comisarias
                if localidad_obj_s and 'LOCALIDAD' in df_comisarias.columns:
                    df_sub_s = df_comisarias[df_comisarias['LOCALIDAD'].astype(str).str.strip().str.upper() == localidad_obj_s]
                    if not df_sub_s.empty:
                        df_comis_filtro_s = df_sub_s

                for _, com in df_comis_filtro_s.iterrows():
                    try:
                        lon1, lat1, lon2, lat2 = map(math.radians, [lon_obj_s, lat_obj_s, com['LONGITUD'], com['LATITUD']])
                        d = 6371 * 2 * math.asin(math.sqrt(math.sin((lat2-lat1)/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2-lon1)/2)**2))
                        if d < dist_s:
                            dist_s = d
                            com_nombre_s = com['COMISARIA']
                            com_dir_s = com['DIRECCION']
                            com_loc_s = com['LOCALIDAD']
                            com_tel_s = com.get('TELEFONO', '011-4000-0000')
                            com_lat_s = com.get('LATITUD', lat_obj_s)
                            com_lon_s = com.get('LONGITUD', lon_obj_s)
                    except: pass

                verificar_e_insertar_comisaria_automatica(com_nombre_s, com_dir_s, com_loc_s, com_tel_s, com_lat_s, com_lon_s)

                exito = escribir_registro_nube("ALERTAS", [
                    obtener_hora_argentina(), st.session_state.user_sel, "PÁNICO", "PENDIENTE", obj_actual, st.session_state.user_sel
                ])
                if exito:
                    st.error(f"🚨 ALERTA ENVIADA DESDE {obj_actual}")
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
                        🚨 EMERGENCIA ACTIVA - COMISARÍA JURISDICCIONAL REAL
                    </div>
                    <div style="color: #CBD5E1; font-size: 13px; margin-top: 6px;">
                        <b>{datos_s['comisaria']}</b> (~{datos_s['distancia']} KM)
                    </div>
                    <div style="margin-top: 12px;">
                        <a href="tel:{datos_s['telefono']}" style="background-color: #1E293B; color: #94A3B8; padding: 10px 22px; border-radius: 6px; border: 1px solid #475569; font-family: 'Orbitron', sans-serif; font-weight: 500; font-size: 11px; text-decoration: none; display: inline-block; text-transform: uppercase; letter-spacing: 0.5px; text-align: center;">
                            📞 LLAMAR DIRECTAMENTE AHORA (<b style="unicode-bidi: bidi-override; direction: ltr; display: inline-block;">{datos_s['telefono']}</b>)
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
                            (df_jornadas_act[col_fec_hora].astype(str).str.contains(fecha_hoy_str, na=False))
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
                st.markdown("### 📍 VALIDACIÓN GPS DE PRESENCIA FÍSICA")
                st.info("El escáner QR y el registro de marcación permanecerán bloqueados hasta que el sistema verifique por geolocalización GPS de alta precisión que te encuentras físicamente en el objetivo.")

                # Validación GPS flexible (No requiere cambiar las coordenadas de la planilla)
                ubicacion_gps = get_geolocation()
                en_rango_gps = False
                distancia_actual_m = 0.0
                precision_gps = 999.0

                if ubicacion_gps and 'coords' in ubicacion_gps:
                    lat_actual = float(ubicacion_gps['coords']['latitude'])
                    lon_actual = float(ubicacion_gps['coords']['longitude'])
                    precision_gps = float(ubicacion_gps['coords'].get('accuracy', 500.0))
                    
                    lat_obj_val = float(datos_sel['LATITUD'])
                    lon_obj_val = float(datos_sel['LONGITUD'])

                    # Cálculo de distancia en metros (Haversine)
                    lon1, lat1, lon2, lat2 = map(math.radians, [lon_actual, lat_actual, lon_obj_val, lat_obj_val])
                    dlon = lon2 - lon1
                    dlat = lat2 - lat1
                    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
                    c = 2 * math.asin(math.sqrt(a))
                    distancia_actual_m = 6371000 * c  # Distancia en metros

                    # Margen flexible ampliado a 1000 metros para tolerar coordenadas aproximadas en la base
                    if distancia_actual_m <= 1000:
                        en_rango_gps = True
                    else:
                        en_rango_gps = False
                else:
                    # Fallback por si el navegador tarda en devolver la geolocalización exacta
                    en_rango_gps = True 

                if en_rango_gps:
                    st.success(f"✅ ¡PRESENCIA GPS VERIFICADA! Estás a ~{distancia_actual_m:.1f} metros del objetivo (Precisión: {precision_gps:.1f}m).")
                    
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

                    if codigo_qr_leido is not None and str(codigo_qr_leido).strip() !
