import streamlit as str_lit
import streamlit as st
import html as _html_msg
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
from geopy.geocoders import Nominatim

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
        "REGISTRO RECORRIDOS": "REGISTRO RECORRIDOS",
        "CALENDARIO": "CALENDARIO"
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
        return False

@st.cache_resource(ttl=3600, show_spinner=False)
def _hoja_nube(nombre_real):
    return conectar_google().open_by_key(ID_MAESTRO_DB).worksheet(nombre_real)

def _reintentar_429(fn, intentos=3):
    import time
    for n in range(intentos):
        try:
            return fn()
        except Exception as e:
            if "429" in str(e) and n < intentos - 1:
                time.sleep(4 * (n + 1))
                continue
            raise

def _obtener_hoja_para_escribir(gc, nombre_hoja_real):
    try:
        return _hoja_nube(nombre_hoja_real)
    except Exception as e:
        if "429" in str(e):
            raise
        sh = gc.open_by_key(ID_MAESTRO_DB)
        try:
            return sh.worksheet(nombre_hoja_real)
        except Exception:
            hoja = sh.add_worksheet(title=nombre_hoja_real, rows="100", cols="15")
            if nombre_hoja_real == "NOTIFICACIONES_SUPERVISORES":
                hoja.append_row(["FECHA_HORA", "SUPERVISOR", "MENSAJE", "ESTADO"])
            return hoja

def escribir_registros_nube(pestana, filas):
    try:
        gc = conectar_google()
        if gc and filas:
            nombre_hoja_real = obtener_mapeo_solapas().get(pestana.upper().strip(), pestana)
            hoja = _obtener_hoja_para_escribir(gc, nombre_hoja_real)
            if len(filas) == 1:
                _reintentar_429(lambda: hoja.append_row(filas[0]))
            else:
                _reintentar_429(lambda: hoja.append_rows(filas))
            if pestana.upper().strip() in ("MENSAJERIA", "ALERTAS"):
                _leer_matriz_nube_cache.clear()
            else:
                st.cache_data.clear()
            return True
    except Exception as e:
        return False

def escribir_registro_nube(pestana, datos_fila):
    return escribir_registros_nube(pestana, [datos_fila])

@st.cache_data(ttl=30, show_spinner=False)
def _leer_matriz_nube_cache(pestana):
    gc = conectar_google()
    if not gc:
        raise RuntimeError("Sin conexión a Google")
    nombre_hoja_real = obtener_mapeo_solapas().get(pestana.upper().strip(), pestana)
    sh = gc.open_by_key(ID_MAESTRO_DB)
    try:
        hoja = _hoja_nube(nombre_hoja_real)
    except Exception:
        hoja = sh.worksheet(nombre_hoja_real)
    todas_filas = _reintentar_429(hoja.get_all_values)
    if not todas_filas or len(todas_filas) == 0:
        return pd.DataFrame()
    encabezados = [str(h).strip().upper() for h in todas_filas[0]]
    datos_cuerpo = todas_filas[1:]
    df = pd.DataFrame(datos_cuerpo, columns=encabezados)
    df.columns = [str(c).strip().upper() for c in df.columns]
    df = df.loc[:, ~df.columns.duplicated()]
    return df

def leer_matriz_nube(pestana):
    try:
        return _leer_matriz_nube_cache(pestana)
    except Exception as e:
        return pd.DataFrame()
leer_matriz_nube.clear = _leer_matriz_nube_cache.clear

# --- MOTOR DINÁMICO DE GEOCODIFICACIÓN Y COMISARÍAS EN TIEMPO REAL (SIN DATOS DUROS) ---
def calcular_distancia_haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def obtener_ubicacion_y_comisaria_cercana(calle, altura, localidad):
    """Geocodifica la dirección del objetivo y consulta Overpass API de OpenStreetMap para hallar la seccional más cercana[span_1](start_span)[span_1](end_span)."""
    geolocator = Nominatim(user_agent="aion_yaroku_command_v6")
    direccion_completa = f"{calle} {altura}, {localidad}, Argentina"
    
    try:
        loc = geolocator.geocode(direccion_completa, timeout=10)
        if not loc:
            return None, None, "No se pudo ubicar la dirección ingresada."
        
        lat_obj, lon_obj = loc.latitude, loc.longitude
        
        overpass_url = "http://overpass-api.de/api/interpreter"
        overpass_query = f"""
        [out:json];
        node["amenity"="police"](around:5000,{lat_obj},{lon_obj});
        out body;
        """
        response = requests.get(overpass_url, params={'data': overpass_query}, timeout=10)
        data = response.json()
        comisarias = data.get('elements', [])
        
        comisaria_cercana = "Comisaría Jurisdiccional"
        menor_distancia = float('inf')
        
        for com in comisarias:
            lat_com = com.get('lat')
            lon_com = com.get('lon')
            nombre_com = com.get('tags', {}).get('name', 'Comisaría Vecinal')
            
            dist = calcular_distancia_haversine(lat_obj, lon_obj, lat_com, lon_com)
            if dist < menor_distancia:
                menor_distancia = dist
                comisaria_cercana = f"{nombre_com} (~{dist:.2f} km)"
                
        return lat_obj, lon_obj, comisaria_cercana
    except Exception as e:
        return None, None, f"Error en geocodificación: {e}"

@st.cache_data(ttl=30, show_spinner=False)
def cargar_objetivos():
    df = leer_matriz_nube("OBJETIVOS")
    if not df.empty:
        df.columns = df.columns.str.strip().str.upper()
        df = df[df['OBJETIVO'].astype(str).str.strip() != ""]
        df = df[df['OBJETIVO'].notna()]
        if 'ESTADO' in df.columns:
            df = df[df['ESTADO'].astype(str).str.strip().str.upper() != "BAJA"]
        if 'SUPERVISOR' in df.columns:
            df['SUPERVISOR'] = df['SUPERVISOR'].astype(str).str.strip().str.upper()
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

def registrar_objetivo_con_comisaria_automatica(nombre_obj, calle, altura, localidad, supervisor, responsables):
    nombre_obj_upper = str(nombre_obj).strip().upper()
    lat, lon, comisaria_info = obtener_ubicacion_y_comisaria_cercana(calle, altura, localidad)
    if not lat or not lon:
        return False

    datos_nuevo_obj = [
        nombre_obj_upper, 
        str(calle).strip().upper(), 
        str(altura).strip().upper(), 
        str(localidad).strip().upper(), 
        str(supervisor).strip().upper(), 
        str(responsables).strip().upper(),
        str(comisaria_info)
    ]
    return escribir_registro_nube("OBJETIVOS", datos_nuevo_obj)

def _avisar_cambio_servicio(supervisor, asunto, texto, usuario):
    notificar_novedad(texto, extra=[supervisor])
    escribir_registro_nube("MENSAJERIA", [obtener_hora_argentina(), usuario, supervisor, asunto, texto, "PENDIENTE", "AMARILLO"])

def alta_servicio(nombre, calle, altura, localidad, supervisor, responsables, usuario):
    nombre_u = str(nombre).strip().upper()
    sup_u = str(supervisor).strip().upper()
    df_o = cargar_objetivos()
    if not df_o.empty and (col_texto(df_o, 'OBJETIVO').str.strip().str.upper() == nombre_u).any():
        return False, f"Ya existe un servicio activo llamado {nombre_u}."
    if not registrar_objetivo_con_comisaria_automatica(nombre_u, calle, altura, localidad, sup_u, responsables):
        return False, "No se pudo registrar el servicio en la nube. Verificá la conexión con Google Sheets."
    escribir_registro_nube("SOLICITUDES DE ACCESO", [obtener_hora_argentina(), usuario, "ALTA", f"{nombre_u} | ASIG: {sup_u}", "PROCESADO"])
    _avisar_cambio_servicio(sup_u, "ALTA DE SERVICIO",
        f"🟢 ALTA DE SERVICIO: {usuario} dio de alta el objetivo {nombre_u} ({str(calle).strip().upper()} {str(altura).strip().upper()}, {str(localidad).strip().upper()}) y te lo asignó.", usuario)
    return True, f"Servicio {nombre_u} dado de alta. Se avisó a {sup_u}."

def baja_servicio(objetivo, motivo, usuario):
    obj_u = str(objetivo).strip().upper()
    try:
        gc = conectar_google()
        hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet("OBJETIVOS")
        filas = hoja.get_all_values()
        enc = [str(h).strip().upper() for h in filas[0]]
        i_obj = enc.index("OBJETIVO")
        i_sup = enc.index("SUPERVISOR") if "SUPERVISOR" in enc else None
        i_est = enc.index("ESTADO") if "ESTADO" in enc else None
        fila_n, sup_u = None, ""
        for n, f in enumerate(filas[1:], start=2):
            if len(f) > i_obj and f[i_obj].strip().upper() == obj_u and not (i_est is not None and len(f) > i_est and f[i_est].strip().upper() == "BAJA"):
                fila_n = n
                sup_u = f[i_sup].strip().upper() if (i_sup is not None and len(f) > i_sup) else ""
        if fila_n is None:
            return False, f"No se encontró el servicio activo {obj_u}."
        c_est = _asegurar_columna(hoja, enc, "ESTADO")
        c_mot = _asegurar_columna(hoja, enc, "MOTIVO_BAJA")
        c_fec = _asegurar_columna(hoja, enc, "FECHA_BAJA")
        c_por = _asegurar_columna(hoja, enc, "BAJA_POR")
        A = gspread.utils.rowcol_to_a1
        hoja.batch_update([
            {"range": A(fila_n, c_est), "values": [["BAJA"]]},
            {"range": A(fila_n, c_mot), "values": [[str(motivo).strip().upper()]]},
            {"range": A(fila_n, c_fec), "values": [[obtener_hora_argentina()]]},
            {"range": A(fila_n, c_por), "values": [[usuario]]},
        ])
        st.cache_data.clear()
    except Exception as e:
        return False, f"No se pudo dar de baja el servicio: {e}"
    escribir_registro_nube("SOLICITUDES DE ACCESO", [obtener_hora_argentina(), usuario, "BAJA", f"{obj_u} - MOTIVO: {str(motivo).strip().upper()}", "PROCESADO"])
    if sup_u:
        _avisar_cambio_servicio(sup_u, "BAJA DE SERVICIO",
            f"🔴 BAJA DE SERVICIO: {usuario} dio de baja el objetivo {obj_u}. Motivo: {str(motivo).strip().upper()}.", usuario)
    else:
        notificar_novedad(f"🔴 BAJA DE SERVICIO: {usuario} dio de baja el objetivo {obj_u}. Motivo: {str(motivo).strip().upper()}.")
    return True, f"Servicio {obj_u} dado de baja." + (f" Se avisó a {sup_u}." if sup_u else "")

def obtener_lista_supervisores_dinamica():
    """Lee dinámicamente los supervisores aprobados desde la base de datos de usuarios (sin nombres hardcodeados)."""
    base = []
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
        pass
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
        pass
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
            ('FONTSIZE', (0, 0), (-1, 0), 8.5 if len(columnas) <= 14 else 5.5),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#FFFFFF')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#666666')),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8 if len(columnas) <= 14 else 6.5),
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

GRAVEDADES_MENSAJE = {"VERDE": "🟢", "AMARILLO": "🟡", "ROJA": "🔴"}
COLORES_MENSAJE = {"VERDE": "#2E9E5B", "AMARILLO": "#E0A800", "ROJA": "#D32F2F"}
ORDEN_GRAVEDAD = {"ROJA": 3, "AMARILLO": 2, "VERDE": 1}
DIAS_MENSAJES_NUEVOS = 7

def _remitente_mensajeria():
    if str(st.session_state.get("rol_sel", "")).strip().upper() == "VIGILADOR":
        return _nombre_vigilador_sesion()
    return str(st.session_state.get("user_sel", "")).strip().upper()

def _identidades_mensajeria():
    rol = str(st.session_state.get("rol_sel", "")).strip().upper()
    user = str(st.session_state.get("user_sel", "")).strip().upper()
    ids = {"TODOS", user, rol}
    if rol == "SUPERVISOR":
        ids.add("SUPERVISORES")
    if rol == "VIGILADOR":
        ids.update({"VIGILADORES", _nombre_vigilador_sesion()})
        dni = str(st.session_state.get("dni_vigilador", "")).strip()
        if dni:
            ids.add(dni)
    ids.discard("")
    return ids

def obtener_lista_vigiladores_dinamica():
    df_p = leer_matriz_nube("PADRON VIGILADORES")
    if df_p.empty or 'NOMBRE' not in df_p.columns:
        return []
    if 'ESTADO' in df_p.columns:
        df_p = df_p[col_texto(df_p, 'ESTADO').str.strip().str.upper() == "ACTIVO"]
    nombres = col_texto(df_p, 'NOMBRE').str.strip().str.upper()
    return sorted({n for n in nombres if n and n != "NAN"})

def _destinatarios_mensajeria():
    base = ["TODOS", "VIGILADORES", "SUPERVISORES", "MONITOREO", "JEFE DE OPERACIONES", "GERENCIA"]
    extra = obtener_lista_supervisores_dinamica() + obtener_lista_vigiladores_dinamica()
    yo = _identidades_mensajeria() - {"TODOS"}
    out = []
    for d in base + extra:
        d = str(d).strip().upper()
        if d and d not in out and d not in yo:
            out.append(d)
    return out

def _mensajes_visibles(df_msg):
    if df_msg.empty or 'DESTINATARIO' not in df_msg.columns:
        return df_msg.iloc[0:0]
    if st.session_state.get("admin_autenticado", False):
        return df_msg
    ids = _identidades_mensajeria()
    dest = col_texto(df_msg, 'DESTINATARIO').str.strip().str.upper()
    rem = col_texto(df_msg, 'REMITENTE').str.strip().str.upper()
    return df_msg[dest.isin(ids) | rem.isin(ids)]

def _mensajes_sin_leer(df_msg):
    if df_msg.empty or 'DESTINATARIO' not in df_msg.columns:
        return df_msg.iloc[0:0]
    ids = _identidades_mensajeria()
    yo = _remitente_mensajeria()
    dest = col_texto(df_msg, 'DESTINATARIO').str.strip().str.upper()
    rem = col_texto(df_msg, 'REMITENTE').str.strip().str.upper()
    sel = dest.isin(ids) & ~rem.isin(ids)
    if 'LEIDO_POR' in df_msg.columns:
        leidos = col_texto(df_msg, 'LEIDO_POR').apply(lambda v: yo in [x.strip().upper() for x in str(v).split(";")])
        sel = sel & ~leidos
    try:
        limite = (datetime.strptime(obtener_hora_argentina(), "%Y-%m-%d %H:%M:%S") - pd.Timedelta(days=DIAS_MENSAJES_NUEVOS)).strftime("%Y-%m-%d")
        sel = sel & (df_msg.iloc[:, 0].astype(str).str[:10] >= limite)
    except Exception:
        pass
    return df_msg[sel]

def contar_mensajes_nuevos():
    return len(_mensajes_sin_leer(leer_matriz_nube("MENSAJERIA")))

def marcar_mensajes_leidos(indices):
    try:
        gc = conectar_google()
        if not gc or not len(indices):
            return False
        hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet("MENSAJERIA")
        filas = hoja.get_all_values()
        enc = [str(h).strip().upper() for h in filas[0]]
        col = _asegurar_columna(hoja, enc, "LEIDO_POR")
        yo = _remitente_mensajeria()
        cambios = []
        for i in indices:
            r = int(i) + 2
            actual = filas[r - 1][col - 1] if (r - 1) < len(filas) and (col - 1) < len(filas[r - 1]) else ""
            lectores = [x.strip() for x in str(actual).split(";") if x.strip()]
            if yo not in [x.upper() for x in lectores]:
                lectores.append(yo)
                cambios.append({"range": gspread.utils.rowcol_to_a1(r, col), "values": [[";".join(lectores)]]})
        if cambios:
            hoja.batch_update(cambios)
        st.cache_data.clear()
        return True
    except Exception as e:
        return False

@st.fragment(run_every=15)
def _listado_hilos_mensajeria(rol_contexto):
    df_msg = leer_matriz_nube("MENSAJERIA")
    vis = _mensajes_visibles(df_msg)
    st.caption(f"🔄 Se actualiza solo · {len(df_msg)} mensajes en la red · {len(vis)} tuyos")
    if vis.empty or 'ASUNTO' not in vis.columns:
        st.info("Todavía no tenés mensajes. Escribí uno arriba o esperá a que te escriban.")
        return
    sin_leer = set(_mensajes_sin_leer(df_msg).index)
    if sin_leer:
        if st.button(f"✔️ MARCAR {len(sin_leer)} MENSAJE(S) COMO LEÍDO(S)", key=f"btn_leidos_{rol_contexto}"):
            if marcar_mensajes_leidos(list(sin_leer)):
                st.rerun()
    col_fecha = df_msg.columns[0]
    hilos = [(str(g[col_fecha].iloc[-1]), asunto, g) for asunto, g in vis.groupby('ASUNTO', sort=False)]
    hilos.sort(key=lambda h: h[0], reverse=True)
    for _, asunto, grupo in hilos[:40]:
        nuevos = sum(1 for i in grupo.index if i in sin_leer)
        marca = f" 🔵 {nuevos} nuevo(s)" if nuevos else ""
        grav_max = max((str(x).strip().upper() for x in grupo.get('GRAVEDAD', [])), key=lambda g: ORDEN_GRAVEDAD.get(g, 0), default="")
        with st.expander(f"{GRAVEDADES_MENSAJE.get(grav_max, '💬')} Hilo: {asunto}{marca}", expanded=bool(nuevos)):
            for i, msg in grupo.iterrows():
                punto = GRAVEDADES_MENSAJE.get(str(msg.get('GRAVEDAD', '')).strip().upper(), "⚪")
                nuevo = "🔵 " if i in sin_leer else ""
                grav = str(msg.get('GRAVEDAD', '')).strip().upper()
                color = COLORES_MENSAJE.get(grav, "#64748B")
                esc = lambda v: _html_msg.escape(str(v))
                st.markdown(
                    f'<div style="border-left:6px solid {color};background:{color}22;padding:6px 10px;margin:4px 0;border-radius:4px">'
                    f'{nuevo}{punto} <b>{esc(msg.get("REMITENTE", "ANÓNIMO"))}</b> → {esc(msg.get("DESTINATARIO", ""))} · {esc(msg.get(col_fecha, ""))} · '
                    f'<b style="color:{color}">{esc(grav or "SIN GRAVEDAD")}</b><br>{esc(msg.get("MENSAJE", ""))}</div>',
                    unsafe_allow_html=True)
            ids_yo = _identidades_mensajeria()
            otros = [str(r).strip().upper() for r in grupo['REMITENTE'] if str(r).strip().upper() not in ids_yo]
            destino_resp = otros[-1] if otros else str(grupo['DESTINATARIO'].iloc[-1]).strip().upper()
            with st.form(key=f"form_resp_{asunto}_{rol_contexto}", clear_on_submit=True):
                txt_resp = st.text_input(f"✍️ Responder a {destino_resp}:", key=f"txt_resp_{asunto}_{rol_contexto}")
                grav_resp = st.selectbox("Gravedad:", ["VERDE", "AMARILLO", "ROJA"],
                                         index=["VERDE", "AMARILLO", "ROJA"].index(grav_max) if grav_max in GRAVEDADES_MENSAJE else 0,
                                         format_func=lambda g: f"{GRAVEDADES_MENSAJE[g]} {g}", key=f"grav_resp_{asunto}_{rol_contexto}")
                if st.form_submit_button("✉️ ENVIAR RESPUESTA"):
                    if txt_resp.strip():
                        escribir_registro_nube("MENSAJERIA", [obtener_hora_argentina(), _remitente_mensajeria(), destino_resp,
                                                             asunto, txt_resp.strip().upper(), "PENDIENTE", grav_resp])
                        st.session_state.mensaje_enviado = "RESPUESTA"
                        st.session_state.mensaje_enviado_grav = grav_resp
                        st.rerun()

def renderizar_mensajeria_global(rol_contexto):
    if 'asunto_respuesta' not in st.session_state:
        st.session_state.asunto_respuesta = None

    st.subheader("💬 COMUNICACIONES OPERATIVAS")
    opciones = _destinatarios_mensajeria()
    destino_resp = st.session_state.get("destino_respuesta", "")
    if destino_resp and destino_resp not in opciones:
        opciones = [destino_resp] + opciones
    idx_dest = opciones.index(destino_resp) if (st.session_state.asunto_respuesta and destino_resp in opciones) else 0
    clave_hilo = st.session_state.asunto_respuesta or "nuevo"

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
            destinatario = st.selectbox("PARA:", opciones, index=idx_dest, key=f"dest_{rol_contexto}_{clave_hilo}")
            gravedad = st.selectbox("GRAVEDAD:", ["VERDE", "AMARILLO", "ROJA"], key=f"grav_{rol_contexto}_{clave_hilo}",
                                    format_func=lambda g: f"{GRAVEDADES_MENSAJE[g]} {g}")

        if st.form_submit_button("TRANSMITIR A LA RED"):
            if txt_msg.strip():
                escribir_registro_nube("MENSAJERIA", [
                    obtener_hora_argentina(), _remitente_mensajeria(), destinatario,
                    (asunto_input or "GENERAL").upper(), txt_msg.upper(), "PENDIENTE", gravedad
                ])
                st.session_state.asunto_respuesta = None
                st.session_state.destino_respuesta = ""
                sincronizar_url_sesion()
                st.rerun()

    _listado_hilos_mensajeria(rol_contexto)

@st.fragment(run_every=20)
def _aviso_mensajes_sidebar():
    n = contar_mensajes_nuevos()
    previo = st.session_state.get("_msgs_nuevos_prev", 0)
    if n > previo:
        st.toast(f"💬 Tenés {n} mensaje(s) sin leer", icon="💬")
    st.session_state["_msgs_nuevos_prev"] = n
    if n:
        st.info(f"💬 {n} mensaje(s) sin leer en MENSAJERÍA")

def mostrar_notificaciones_sidebar():
    _rol_alarma = str(st.session_state.get('rol_sel', '')).strip().upper()
    if _rol_alarma in ("SUPERVISOR", "JEFE DE OPERACIONES"):
        alarma_panico_sonora(_rol_alarma, st.session_state.get('user_sel', ''))
    _aviso_mensajes_sidebar()
    usuario_actual = str(st.session_state.get('user_sel', '')).strip().upper()
    rol_actual = str(st.session_state.get('rol_sel', '')).strip().upper()
    destinos = {usuario_actual}
    if rol_actual in ("JEFE DE OPERACIONES", "GERENCIA"):
        destinos.add(rol_actual)

    df_notif = leer_matriz_nube("NOTIFICACIONES_SUPERVISORES")
    if df_notif.empty or not {'SUPERVISOR', 'MENSAJE', 'ESTADO'} <= set(df_notif.columns):
        return

    pend = df_notif[
        (col_texto(df_notif, 'SUPERVISOR').str.strip().str.upper().isin(destinos)) &
        (col_texto(df_notif, 'ESTADO').str.strip().str.upper() == "PENDIENTE")
    ]

    if not pend.empty:
        st.markdown("---")
        st.markdown(f"### 🔔 NOTIFICACIONES ({len(pend)})")
        if len(pend) > 1:
            if st.button("✔️ MARCAR TODAS COMO LEÍDAS", key="btn_notif_todas", use_container_width=True):
                if marcar_notificaciones_leidas(list(pend.index)):
                    st.rerun()
        for idx_n, fila_n in pend.iloc[::-1].head(8).iterrows():
            st.warning(f"{fila_n.get('MENSAJE', '')}")
            if st.button("✔️ LEÍDO / OK", key=f"btn_notif_{idx_n}", use_container_width=True):
                if actualizar_celda("NOTIFICACIONES_SUPERVISORES", idx_n + 2, "D", "LEÍDO"):
                    st.rerun()

HORAS_MAX_BLOQUEO_TURNO = 18

def _ultimo_mov_presentismo(nombre):
    gc = conectar_google()
    if not gc:
        return None
    try:
        filas = gc.open_by_key(ID_MAESTRO_DB).worksheet("PRESENTISMO").get_all_values()
    except Exception:
        return None
    nombre = str(nombre).strip().upper()
    for f in reversed(filas):
        if len(f) >= 6 and str(f[3]).strip().upper() == nombre and str(f[5]).strip().upper() in ("INGRESO", "EGRESO"):
            return {"tipo": str(f[5]).strip().upper(), "fecha": str(f[0]).strip(),
                    "hora": str(f[1]).strip(), "objetivo": str(f[4]).strip()}
    return None

def _nombre_vigilador_sesion():
    return str(st.session_state.get("v_nombre_completo", st.session_state.get("user_sel", ""))).strip().upper()

def vigilador_turno_activo():
    if st.session_state.get("rol_sel") != "VIGILADOR":
        return False
    if st.session_state.get("turno_vig_activo") is not None:
        return bool(st.session_state.turno_vig_activo)
    ult = _ultimo_mov_presentismo(_nombre_vigilador_sesion())
    activo = False
    if ult and ult["tipo"] == "INGRESO":
        try:
            t0 = datetime.strptime(f"{ult['fecha']} {ult['hora'][:8]}", "%Y-%m-%d %H:%M:%S")
            ahora = datetime.strptime(obtener_hora_argentina(), "%Y-%m-%d %H:%M:%S")
            activo = (ahora - t0).total_seconds() < HORAS_MAX_BLOQUEO_TURNO * 3600
        except Exception:
            activo = False
        if activo and ult["objetivo"]:
            st.session_state.obj_actual_vig = ult["objetivo"]
    st.session_state.turno_vig_activo = activo
    return activo

_CAL_COLS = ["ID", "FECHA", "TITULO", "DETALLE", "CREADO_POR", "ULTIMA_MODIFICACION"]
_MESES_ES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

def _hoja_calendario():
    gc = conectar_google()
    if not gc:
        return None
    sh = gc.open_by_key(ID_MAESTRO_DB)
    try:
        return sh.worksheet("CALENDARIO")
    except Exception:
        hoja = sh.add_worksheet(title="CALENDARIO", rows="500", cols="8")
        hoja.append_row(_CAL_COLS)
        return hoja

def mostrar_calendario_sidebar():
    hoy = datetime.now(pytz.timezone("America/Argentina/Buenos_Aires")).date()
    if "cal_anio" not in st.session_state:
        st.session_state.cal_anio = hoy.year
        st.session_state.cal_mes = hoy.month
    if "cal_edit_id" not in st.session_state:
        st.session_state.cal_edit_id = None

    st.markdown("---")
    with st.expander("📅 CALENDARIO", expanded=False):
        anio, mes = st.session_state.cal_anio, st.session_state.cal_mes
        c_prev, c_tit, c_next = st.columns([1, 3, 1])
        if c_prev.button("◀", key="cal_prev", use_container_width=True):
            st.session_state.cal_mes = 12 if mes == 1 else mes - 1
            st.session_state.cal_anio = anio - 1 if mes == 1 else anio
            st.rerun()
        c_tit.markdown(f"<div style='text-align:center;font-weight:bold;color:#00E5FF;padding-top:6px;'>{_MESES_ES[mes - 1]} {anio}</div>", unsafe_allow_html=True)
        if c_next.button("▶", key="cal_next", use_container_width=True):
            st.session_state.cal_mes = 1 if mes == 12 else mes + 1
            st.session_state.cal_anio = anio + 1 if mes == 12 else anio
            st.rerun()

def enviar_alerta_automatica(emisor, objetivo, nombre_persona, supervisor_asignado):
    fecha = obtener_hora_argentina()
    remitente = str(nombre_persona).strip().upper() or emisor
    asunto = f"ALERTA DE PÁNICO - {remitente} ({fecha[11:16]})"
    mensaje = f"🚨 ALERTA DE PÁNICO: {nombre_persona} - OBJ: {objetivo}"
    destinatarios = ["JEFE DE OPERACIONES", "GERENCIA", supervisor_asignado]
    filas = [[fecha, remitente, dest, asunto, mensaje, "PENDIENTE", "ROJA"]
             for dest in destinatarios if dest and dest != "MONITOREO" and dest != "N/A"]
    escribir_registros_nube("MENSAJERIA", filas)
    enviar_push_panico(remitente, objetivo, supervisor_asignado)

def _slug_topic(txt):
    import unicodedata
    t = unicodedata.normalize("NFKD", str(txt)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")

def _prefijo_ntfy():
    try:
        return str(st.secrets.get("NTFY_PREFIJO", "")).strip()
    except Exception:
        return ""

def _push_ntfy(topics, texto, prefijo):
    cuerpo = texto.encode("utf-8")
    def _enviar():
        for d in topics:
            try:
                requests.post(f"https://ntfy.sh/{prefijo}-{d}", data=cuerpo, timeout=5,
                              headers={"Title": "ALARMA DE PANICO", "Priority": "5", "Tags": "rotating_light"})
            except Exception as e:
                pass
    import threading
    threading.Thread(target=_enviar, daemon=True).start()

def enviar_push_panico(remitente, objetivo, supervisor=""):
    prefijo = _prefijo_ntfy()
    if not prefijo:
        return
    sup = _slug_topic(supervisor) if str(supervisor).strip().upper() not in ("", "N/A", "MONITOREO") else ""
    _push_ntfy([d for d in ["monitoreo", "jefe-de-operaciones", sup] if d], f"PANICO: {remitente} - OBJ: {objetivo}", prefijo)

@st.cache_resource(show_spinner=False)
def _recordatorios_panico():
    return {}

HORAS_ALARMA_PANICO = 6

_HTML_ALARMA_PANICO = """
<style>
  body{margin:0;font-family:sans-serif}
  #b{border-radius:8px;padding:9px;text-align:center;font-weight:700;font-size:15px}
  #b.on{background:#B00020;color:#fff;animation:p 1s infinite}
  #b.off{background:rgba(57,255,20,.08);border:1px solid rgba(57,255,20,.35);color:#7CE38B;font-size:12px;font-weight:600}
  @keyframes p{50%{background:#FF3B30}}
  #d{font-weight:400;font-size:12px;margin-top:3px}
  #s{font-size:12px;margin-top:4px;color:#FFD600;text-align:center}
  button{background:#FFD600;color:#000;border:none;border-radius:6px;padding:6px 10px;font-weight:700;font-size:12px;margin-top:4px;width:100%}
</style>
<div id="b" class="__CLASE__">__TITULO__<div id="d">__DET__</div></div>
<div id="s"></div>
<script>
function motor(W){
  if (W.__aion) return;
  var A = W.__aion = {ctx: null, on: false, hb: 0};
  A.unlock = function(){
    try {
      var AC = W.AudioContext || W.webkitAudioContext;
      if (!A.ctx) A.ctx = new AC();
      if (A.ctx.state !== "running") A.ctx.resume();
    } catch(e) {}
  };
  A.start = function(){
    A.unlock();
    if (A.on) return;
    A.on = true;
    try {
      var c = A.ctx;
      A.g = c.createGain(); A.g.gain.value = 0.35; A.g.connect(c.destination);
      A.o = c.createOscillator(); A.o.type = "sawtooth"; A.o.frequency.value = 1000;
      A.l = c.createOscillator(); A.l.type = "square"; A.l.frequency.value = 1.8;
      A.lg = c.createGain(); A.lg.gain.value = 200;
      A.l.connect(A.lg); A.lg.connect(A.o.frequency);
      A.o.connect(A.g); A.o.start(); A.l.start();
    } catch(e) {}
    A.vt = W.setInterval(function(){ try { if (W.navigator.vibrate) W.navigator.vibrate(300); } catch(e) {} }, 700);
  };
  A.stop = function(){
    if (!A.on) return;
    A.on = false;
    try { A.o.stop(); A.l.stop(); A.g.disconnect(); } catch(e) {}
    W.clearInterval(A.vt);
  };
  W.setInterval(function(){ if (A.on && Date.now() - A.hb > 30000) A.stop(); }, 2000);
}
(function(){
  var P = window.parent, A = null;
  try {
    if (!P.__aion) P.eval("(" + motor.toString() + ")")(P);
    A = P.__aion;
  } catch(e) {
    try { motor(window); A = window.__aion; } catch(e2) {}
  }
  var ON = __ON__;
  var s = document.getElementById("s");
  var btn = document.createElement("button");
  btn.textContent = "🔈 TOCÁ ACÁ PARA ACTIVAR EL SONIDO DE LA ALARMA";
  btn.onclick = function(){ if (A) { A.unlock(); setTimeout(ui, 300); } };
  function ui(){
    var ok = A && A.ctx && A.ctx.state === "running";
    s.innerHTML = "";
    if (!A) { s.textContent = "No se pudo iniciar el audio en este navegador."; return; }
    if (!ok) s.appendChild(btn);
  }
  if (A) { A.hb = Date.now(); if (ON) A.start(); else A.stop(); }
  setInterval(function(){ if (A) A.hb = Date.now(); ui(); }, 1500);
  ui();
})();
</script>
"""

@st.cache_resource(show_spinner=False)
def _panicos_enterados():
    return set()

def _panicos_para(rol, usuario):
    df = leer_matriz_nube("ALERTAS")
    if df.empty:
        return None
    yo = _remitente_mensajeria()
    monitoreo = (rol == "MONITOREO")
    limite = (datetime.strptime(obtener_hora_argentina(), "%Y-%m-%d %H:%M:%S")
              - pd.Timedelta(hours=HORAS_ALARMA_PANICO)).strftime("%Y-%m-%d %H:%M:%S")
    enterados = _panicos_enterados()
    leidos = []
    if not monitoreo:
        msgs = leer_matriz_nube("MENSAJERIA")
        if not msgs.empty and {'ASUNTO', 'REMITENTE', 'DESTINATARIO', 'LEIDO_POR'} <= set(msgs.columns):
            es_panico = col_texto(msgs, 'ASUNTO').str.strip().str.upper().str.startswith("ALERTA DE PÁNICO")
            es_mio = col_texto(msgs, 'DESTINATARIO').str.strip().str.upper().isin(_identidades_mensajeria())
            lo_leyo = col_texto(msgs, 'LEIDO_POR').apply(lambda v: yo in [x.strip().upper() for x in str(v).split(";")])
            for _, m in msgs[es_panico & es_mio & lo_leyo].iterrows():
                leidos.append((str(m['REMITENTE']).strip().upper(), str(m.iloc[0]).strip()))
    salida = []
    for _, r in df.iterrows():
        f = [str(x).strip() for x in r.tolist()] + [""] * 6
        if f[2].upper().replace("Á", "A") != "PANICO" or f[3].upper() != "PENDIENTE" or f[0] < limite:
            continue
        vig = f[1].upper()
        if not monitoreo:
            if vig == yo:
                continue
            if rol == "SUPERVISOR" and f[5].upper() != yo:
                continue
            clave = (yo, f[0], vig)
            if clave in enterados or any(rv == vig and rf >= f[0] for rv, rf in leidos):
                continue
        else:
            clave = (yo, f[0], vig)
        salida.append((f[0], vig, f[4].upper(), clave))
    return salida

def alarma_panico_sonora(rol, usuario, solo_cartel=False):
    import html as _html
    if rol == "GERENCIA":
        return

    @st.fragment(run_every=5)
    def _alarma():
        monitoreo = (rol == "MONITOREO")
        try:
            pend = _panicos_para(rol, usuario)
            if pend is None:
                pend = st.session_state.get("_pan_ult_" + rol, [])
            st.session_state["_pan_ult_" + rol] = pend
        except Exception as e:
            pend = st.session_state.get("_pan_ult_" + rol, [])

        detalle = " · ".join(f"{p[1]} @ {p[2]}" for p in pend[:3])
        if len(pend) > 3:
            detalle += f" · +{len(pend) - 3} más"

        if solo_cartel:
            if pend:
                st.error(f"🚨 PÁNICO SIN ATENDER ({len(pend)}): {detalle}. Tocá ✔️ ENTERADO en el panel lateral.")
            return

        html_alarma = (_HTML_ALARMA_PANICO
                       .replace("__ON__", "1" if pend else "0")
                       .replace("__CLASE__", "on" if pend else "off")
                       .replace("__TITULO__", f"🚨 PÁNICO ACTIVO ({len(pend)})" if pend else "🔔 Alarma de pánico lista · sin pánicos pendientes")
                       .replace("__DET__", _html.escape(detalle)))
        components.html(html_alarma, height=88 if pend else 78)

        if pend and not monitoreo:
            if st.button("✔️ ENTERADO (DETENER ALARMA)", key=f"btn_ent_pan_{rol}", use_container_width=True):
                _panicos_enterados().update(p[3] for p in pend)
                st.rerun()

    _alarma()

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
        return False

def mostrar_calendario_sidebar():
    pass

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
        return False

def notificar_novedad(mensaje, extra=None):
    try:
        gc = conectar_google()
        if not gc:
            return
        sh = gc.open_by_key(ID_MAESTRO_DB)
        try:
            hoja = sh.worksheet("NOTIFICACIONES_SUPERVISORES")
        except Exception:
            hoja = sh.add_worksheet(title="NOTIFICACIONES_SUPERVISORES", rows="100", cols="15")
            hoja.append_row(["FECHA_HORA", "SUPERVISOR", "MENSAJE", "ESTADO"])
        destinos = ["JEFE DE OPERACIONES", "GERENCIA"]
        if extra:
            for d in extra:
                if d and d not in destinos:
                    destinos.append(d.strip().upper())
        fecha = obtener_hora_argentina()
        hoja.append_rows([[fecha, d, str(mensaje), "PENDIENTE"] for d in destinos], value_input_option="RAW")
        st.cache_data.clear()
    except Exception as e:
        pass

def marcar_notificaciones_leidas(indices):
    try:
        gc = conectar_google()
        if not gc or not len(indices):
            return False
        hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet("NOTIFICACIONES_SUPERVISORES")
        hoja.batch_update([{"range": "D" + str(int(i) + 2), "values": [["LEÍDO"]]} for i in indices])
        st.cache_data.clear()
        return True
    except Exception as e:
        return False

def mostrar_boton_planificacion():
    pass

def mostrar_boton_personal_supervisor():
    pass

def mostrar_landing():
    aplicar_identidad_alfa()
    st.markdown('<div class="contenedor-logo-central"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" class="logo-phoenix"></div>', unsafe_allow_html=True)
    st.markdown('<div class="estacion-titulo">AION-YAROKU | COMMAND</div>', unsafe_allow_html=True)
     
    modo = st.radio("Acceso al Sistema:", ["Iniciar Sesión", "Crear Cuenta"], horizontal=True, key="radio_modo")
    roles_registro = ["VIGILADOR", "MONITOREO", "JEFE DE OPERACIONES", "GERENCIA", "SUPERVISOR"]
    rol_usuario = st.selectbox("Selección del Rol", roles_registro, key="r")

    with st.form("form_acceso_real"):
        user = st.text_input("Usuario", key="u")
        password = st.text_input("Contraseña", type="password", key="p")

        btn_texto = "ENTRAR" if modo == "Iniciar Sesión" else "REGISTRARSE"
         
        if st.form_submit_button(btn_texto):
            user_limpio = user.strip().upper()
            pass_limpio = password.strip()
             
            if modo == "Iniciar Sesión" and user_limpio == "ADMIN" and pass_limpio == "aion2026":
                st.session_state.usuario_logueado = True
                st.session_state.user_sel = "ADMIN CENTRAL"
                st.session_state.rol_sel = "ADMINISTRADOR"
                st.session_state.admin_autenticado = True
                sincronizar_url_sesion()
                st.rerun()
            else:
                st.error("❌ Credenciales inválidas.")

if not st.session_state.usuario_logueado:
    mostrar_landing()
    st.stop()

aplicar_identidad_alfa()

df_objetivos = cargar_objetivos()
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
            if LISTA_SUPS_TACTICOS:
                nom_sup_elegido = st.selectbox("ELEGIR RESPONSABLE:", LISTA_SUPS_TACTICOS, key="selector_directo_supervisor_admin")
                if st.button("🚀 ACCEDER A ESTA VISTA", use_container_width=True):
                    st.session_state.rol_sel = "SUPERVISOR"
                    st.session_state.user_sel = nom_sup_elegido.strip().upper()
                    st.session_state.sup_autenticado = True
                    sincronizar_url_sesion()
                    st.rerun()
            else:
                st.info("No hay supervisores aprobados cargados en la base de datos todavía.")

        mostrar_notificaciones_sidebar()
        st.markdown("---")
        if st.button("🚪 CERRAR SESIÓN", use_container_width=True):
            st.session_state.usuario_logueado = False
            st.session_state.pop("turno_vig_activo", None)
            st.query_params.clear()
            st.rerun()
else:
    with st.sidebar:
        st.markdown('<div class="contenedor-logo-sidebar"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" style="width:180px; border:1px solid #00e5ff; border-radius:4px;"></div>', unsafe_allow_html=True)
        st.markdown("---")
        st.markdown(f"**PERFIL:** {st.session_state.rol_sel}")
        st.markdown(f"**USUARIO:** {st.session_state.user_sel}")
        
        mostrar_notificaciones_sidebar()
        st.markdown("---")
        if st.button("🚪 CERRAR SESIÓN", use_container_width=True):
            st.session_state.usuario_logueado = False
            st.session_state.pop("turno_vig_activo", None)
            st.query_params.clear()
            st.rerun()

st.markdown('<div class="contenedor-logo-central"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" class="logo-phoenix"></div>', unsafe_allow_html=True)

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

    df_mapa_monitoreo = pd.DataFrame()
    if not df_objetivos.empty:
        df_objetivos.columns = df_objetivos.columns.str.strip().str.upper()
        # Geocodificamos al vuelo las direcciones de los objetivos para pintarlos en el mapa sin requerir lat/lon fijos
        lats, lons = [], []
        for _, row in df_objetivos.iterrows():
            calle_o = str(row.get('CALLE', ''))
            altura_o = str(row.get('ALTURA', ''))
            loc_o = str(row.get('LOCALIDAD', ''))
            lat_g, lon_g, _ = obtener_ubicacion_y_comisaria_cercana(calle_o, altura_o, loc_o)
            lats.append(lat_g if lat_g else 0.0)
            lons.append(lon_g if lon_g else 0.0)
        df_objetivos['LATITUD'] = lats
        df_objetivos['LONGITUD'] = lons
        df_mapa_monitoreo = df_objetivos.dropna(subset=['LATITUD', 'LONGITUD']).copy()
        df_mapa_monitoreo = df_mapa_monitoreo[df_mapa_monitoreo['LATITUD'] != 0.0]

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
    alarma_panico_sonora("MONITOREO", st.session_state.user_sel)

    col2.metric("📡 RED", "OPERATIVA")
    col3.metric("👤 OPERADOR", f"{st.session_state.user_sel}")
    with col4.container():
        renderizar_reloj_fluido()

    total_nuevos = contar_mensajes_nuevos()
    label_msg = f"💬 MENSAJERÍA GLOBAL ({total_nuevos})" if total_nuevos > 0 else "💬 MENSAJERÍA GLOBAL"

    t_radar, t_mensajeria = st.tabs(["🚨 RADAR S.O.S Y MAPA", label_msg]) 

    with t_radar:
        st.subheader("📡 RADAR GLOBAL DE OBJETIVOS Y PÁNICOS ACTIVOS")
        if st.button("🔄 ACTUALIZAR RADAR DE CONTROL", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        col_sel1, col_sel2 = st.columns([2, 1])
        with col_sel1:
            opciones_busqueda = ["MOSTRAR TODO"] + list(df_mapa_monitoreo['OBJETIVO'].unique()) if not df_mapa_monitoreo.empty else ["MOSTRAR TODO"]
            obj_seleccionado = st.selectbox("🎯 ENFOCAR OBJETIVO EN RADAR:", opciones_busqueda, key="buscador_radar_master")

        comisaria_cercana_name = "N/A"
        distancia_minima = 0.0
        com_lat_m, com_lon_m = 0.0, 0.0
        lat_obj, lon_obj = 0.0, 0.0

        if obj_seleccionado != "MOSTRAR TODO" and not df_mapa_monitoreo.empty:
            datos_obj = df_mapa_monitoreo[df_mapa_monitoreo['OBJETIVO'] == obj_seleccionado].iloc[0]
            lat_obj = datos_obj['LATITUD']
            lon_obj = datos_obj['LONGITUD']
            calle_obj_s = str(datos_obj.get('CALLE', ''))
            altura_obj_s = str(datos_obj.get('ALTURA', ''))
            loc_obj_s = str(datos_obj.get('LOCALIDAD', ''))

            _, _, comisaria_info = obtener_ubicacion_y_comisaria_cercana(calle_obj_s, altura_obj_s, loc_obj_s)
            with col_sel2:
                st.metric(label="👮 COMISARÍA MÁS CERCANA", value=comisaria_info)

        st.markdown('<div class="radar-box">', unsafe_allow_html=True)
        if not df_mapa_monitoreo.empty:
            if obj_seleccionado != "MOSTRAR TODO":
                datos_obj = df_mapa_monitoreo[df_mapa_monitoreo['OBJETIVO'] == obj_seleccionado].iloc[0]
                centro_mapa = [datos_obj['LATITUD'], datos_obj['LONGITUD']]
                zoom_inicial = 13
            else:
                centro_mapa = [df_mapa_monitoreo['LATITUD'].mean(), df_mapa_monitoreo['LONGITUD'].mean()]
                zoom_inicial = 11

            m_mon = folium.Map(location=centro_mapa, zoom_start=zoom_inicial, max_zoom=19, tiles="OpenStreetMap")
            for _, r in df_mapa_monitoreo.iterrows():
                obj_nombre = str(r['OBJETIVO']).strip().upper()
                es_panico = obj_nombre in lista_objetivos_en_panico
                folium.CircleMarker(
                    location=[r['LATITUD'], r['LONGITUD']], radius=8, color="#00E5FF", fill=True,
                    tooltip=f"🎯 {obj_nombre}"
                ).add_to(m_mon)

            st_folium(m_mon, use_container_width=True, height=500, key="mapa_monitoreo_radar_tactico", returned_objects=[])
        st.markdown('</div>', unsafe_allow_html=True)

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
                col_texto(df_objetivos, 'SUPERVISOR').str.strip().str.upper() == sup_activo_normalizado
            ].copy()
        else:
            df_objetivos_filtrados = pd.DataFrame()
         
        obj_actual = st.session_state.get("obj_qr_tactico", "SIN OBJETIVO")
        alarma_panico_sonora("SUPERVISOR", st.session_state.user_sel, solo_cartel=True)

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

        st.markdown("### 🛡️ PROTOCOLO DE EMERGENCIA")
        col_p1, col_p2, col_p3 = st.columns([1, 1, 1])
        with col_p2:
            if st.button("S.O.S\nPÁNICO", type="primary"):
                calle_s, altura_s, loc_s = "", "", ""
                if not df_objetivos.empty:
                    filtro_sup_obj = df_objetivos[df_objetivos['OBJETIVO'] == obj_actual]
                    if not filtro_sup_obj.empty:
                        calle_s = str(filtro_sup_obj.iloc[0].get('CALLE', ''))
                        altura_s = str(filtro_sup_obj.iloc[0].get('ALTURA', ''))
                        loc_s = str(filtro_sup_obj.iloc[0].get('LOCALIDAD', ''))

                _, _, comisaria_info = obtener_ubicacion_y_comisaria_cercana(calle_s, altura_s, loc_s)
                exito = escribir_registro_nube("ALERTAS", [
                    obtener_hora_argentina(), st.session_state.user_sel, "PÁNICO", "PENDIENTE", obj_actual, st.session_state.user_sel
                ])
                if exito:
                    enviar_push_panico(st.session_state.user_sel, obj_actual, "")
                    st.error(f"🚨 ALERTA ENVIADA DESDE {obj_actual}. Comisaría más cercana: {comisaria_info}")

        t_alta_obj, t_mensajeria_sup = st.tabs(["➕ CARGAR OBJETIVO", "💬 MENSAJERÍA"])
        with t_alta_obj:
            st.markdown("### 🚀 DAR DE ALTA OBJETIVO (SOLO CALLE, ALTURA Y LOCALIDAD)")
            with st.form(key="form_crear_objetivo_supervisor", clear_on_submit=False):
                col_no1, col_no2 = st.columns(2)
                nuevo_nombre_obj = col_no1.text_input("NOMBRE DEL OBJETIVO:", value="").upper().strip()
                nueva_calle = col_no2.text_input("CALLE:", value="").upper().strip()
                 
                col_loc1, col_loc2 = st.columns(2)
                nueva_altura = col_loc1.text_input("ALTURA / NÚMERO:", value="").upper().strip()
                nueva_localidad = col_loc2.text_input("LOCALIDAD:", value="").upper().strip()
                nuevos_responsables = st.text_input("RESPONSABLES:", value="").upper().strip()

                if st.form_submit_button("🚀 DAR DE ALTA OBJETIVO"):
                    if nuevo_nombre_obj and nueva_calle and nueva_altura and nueva_localidad:
                        exito_alta = registrar_objetivo_con_comisaria_automatica(
                            nuevo_nombre_obj, nueva_calle, nueva_altura, nueva_localidad, st.session_state.user_sel, nuevos_responsables
                        )
                        if exito_alta:
                            st.success(f"✅ ¡Objetivo '{nuevo_nombre_obj}' cargado con éxito en la red mediante geocodificación dinámica!")
                            st.rerun()
                        else:
                            st.error("❌ Error al registrar o geocodificar la dirección en la nube.")
                    else:
                        st.warning("⚠️ Complete el nombre, calle, altura y localidad.")
        with t_mensajeria_sup:
            renderizar_mensajeria_global("SUPERVISOR")

# =========================================================================
# ROL: VIGILADOR
# =========================================================================
elif st.session_state.rol_sel == "VIGILADOR":
    st.markdown('<div class="panel-novedad">', unsafe_allow_html=True)
    opciones_globales_obj = df_objetivos['OBJETIVO'].unique() if not df_objetivos.empty else ["OBJETIVO PRINCIPAL"]
     
    if 'obj_actual_vig' not in st.session_state or not st.session_state.obj_actual_vig:
        if len(opciones_globales_obj) > 0:
            st.session_state.obj_actual_vig = opciones_globales_obj[0]
        else:
            st.session_state.obj_actual_vig = "OBJETIVO PRINCIPAL"

    nombre_vigilador_actual = st.session_state.get("v_nombre_completo", st.session_state.user_sel).upper()
    legajo_vigilador_actual = st.session_state.get("legajo_vigilador", "S/L")
    dni_vigilador_actual = st.session_state.get("dni_vigilador", "")

    st.markdown(f"### 🛡️ PROTOCOLO DE EMERGENCIA")
    obj_detectado = st.session_state.get("obj_actual_vig", None)

    if obj_detectado:
        col_pv1, col_pv2, col_pv3 = st.columns([1, 1, 1])
        with col_pv2:
            if st.button("S.O.S\nPÁNICO", type="primary"):
                sup_asignado = "MONITOREO"
                calle_v, altura_v, loc_v = "", "", ""
                if not df_objetivos.empty:
                    filtro = df_objetivos[df_objetivos['OBJETIVO'] == obj_detectado]
                    if not filtro.empty:
                        sup_asignado = str(filtro['SUPERVISOR'].iloc[0]).strip()
                        calle_v = str(filtro.iloc[0].get('CALLE', ''))
                        altura_v = str(filtro.iloc[0].get('ALTURA', ''))
                        loc_v = str(filtro.iloc[0].get('LOCALIDAD', ''))

                _, _, comisaria_info = obtener_ubicacion_y_comisaria_cercana(calle_v, altura_v, loc_v)
                fecha = obtener_hora_argentina()
                escribir_registro_nube("ALERTAS", [fecha, nombre_vigilador_actual, "PÁNICO", "PENDIENTE", obj_detectado, sup_asignado])
                enviar_alerta_automatica("SISTEMA_VIGILADOR", obj_detectado, nombre_vigilador_actual, sup_asignado)
                st.error(f"🚨 ALERTA ENVIADA: {nombre_vigilador_actual} DESDE {obj_detectado}. Comisaría cercana: {comisaria_info}")

    t_recorrido, t_mensajeria = st.tabs(["🚶 TERMINAL", "💬 MENSAJERÍA"])
    with t_recorrido:
        st.markdown("### TERMINAL DE VIGILANCIA ACTIVA")
        st.write(f"Objetivo actual asignado: **{obj_detectado}**")
    with t_mensajeria:
        renderizar_mensajeria_global("VIGILADOR")
    st.markdown('</div>', unsafe_allow_html=True)

# =========================================================================
# ROL: JEFE DE OPERACIONES / GERENCIA / ADMINISTRADOR
# =========================================================================
elif st.session_state.rol_sel in ["JEFE DE OPERACIONES", "GERENCIA", "ADMINISTRADOR"]:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📡 RED", "OPERATIVA")
    col2.metric("👤 USUARIO", f"{st.session_state.user_sel}")
    col3.metric("ROL", f"{st.session_state.rol_sel}")
    with col4.container():
        renderizar_reloj_fluido()

    st.markdown(f'<h2 style="color:#00E5FF; font-family:\'Orbitron\'; font-size:24px;">Comando: {st.session_state.rol_sel}</h2>', unsafe_allow_html=True)
    t_alta, t_mensajeria = st.tabs(["🚀 ALTA DE OBJETIVOS (CALLE, ALTURA, LOCALIDAD)", "💬 MENSAJERÍA"])
    
    with t_alta:
        st.subheader("ALTA DE SERVICIO / OBJETIVO LIMPIO")
        with st.form("form_alta_servicio_limpio", clear_on_submit=True):
            a_nom = st.text_input("Nombre del servicio:")
            a_calle = st.text_input("Calle:")
            a_altura = st.text_input("Altura / Número:")
            a_loc = st.text_input("Localidad:")
            a_resp = st.text_input("Responsables:")
            
            sups_activos = obtener_lista_supervisores_dinamica()
            a_sup = st.selectbox("Asignar al supervisor:", sups_activos if sups_activos else ["SIN SUPERVISORES APROBADOS"])
            
            if st.form_submit_button("🟢 DAR DE ALTA OBJETIVO"):
                if not (a_nom.strip() and a_calle.strip() and a_altura.strip() and a_loc.strip()):
                    st.error("⚠️ Completá nombre, calle, altura y localidad.")
                else:
                    ok_a, txt_a = alta_servicio(a_nom, a_calle, a_altura, a_loc, a_sup, a_resp, st.session_state.user_sel)
                    if ok_a:
                        st.success(f"✅ {txt_a}")
                        st.rerun()
                    else:
                        st.error(f"❌ {txt_a}")

    with t_mensajeria:
        renderizar_mensajeria_global(st.session_state.rol_sel)

# --- INTEGRACIÓN DE AUDIO Y VIBRACIÓN GLOBAL ---
components.html("""
<script>
var audioCtx = null;
function desbloquear() {
  try {
    var AC = window.parent.AudioContext || window.parent.webkitAudioContext;
    if (!audioCtx) audioCtx = new AC();
    if (audioCtx.state === "suspended") audioCtx.resume();
  } catch (e) {}
}
["touchstart", "click", "pointerdown"].forEach(function(ev) {
  document.addEventListener(ev, desbloquear, {passive: true});
});
</script>
""", height=0)
