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

@st.cache_resource(ttl=3600, show_spinner=False)
def _hoja_nube(nombre_real):
    """Hoja ya abierta y guardada en memoria: evita 2 consultas de metadata a Google en cada lectura/escritura
    (era lo que agotaba la cuota 'Read requests per minute' y daba el error 429)."""
    return conectar_google().open_by_key(ID_MAESTRO_DB).worksheet(nombre_real)

def _reintentar_429(fn, intentos=3):
    """Si Google responde 429 (cuota por minuto), espera unos segundos y reintenta en vez de fallar."""
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
    """Agrega varias filas en UNA sola llamada a Google (mensajes de pánico a supervisor, Jefe y Gerencia)."""
    try:
        gc = conectar_google()
        if gc and filas:
            nombre_hoja_real = obtener_mapeo_solapas().get(pestana.upper().strip(), pestana)
            hoja = _obtener_hoja_para_escribir(gc, nombre_hoja_real)
            if len(filas) == 1:
                _reintentar_429(lambda: hoja.append_row(filas[0], table_range="A1"))
            else:
                _reintentar_429(lambda: hoja.append_rows(filas, table_range="A1"))
            if pestana.upper().strip() in ("MENSAJERIA", "ALERTAS"):
                _leer_matriz_nube_cache.clear()   # solo refresca estas lecturas; no borra toda la caché de la app
            else:
                st.cache_data.clear()
            return True
    except Exception as e:
        print(f"Error de nube en {pestana}: {e}")
        st.error(f"⚠️ Error técnico en nube ({pestana}): {e}")
        return False

def escribir_registro_nube(pestana, datos_fila):
    return escribir_registros_nube(pestana, [datos_fila])

@st.cache_data(ttl=30, show_spinner=False)
def _leer_matriz_nube_cache(pestana):
    """Lee una pestaña. Si Google falla lanza el error (así NO se guarda en caché una lectura vacía)."""
    gc = conectar_google()
    if not gc:
        raise RuntimeError("Sin conexión a Google")
    nombre_hoja_real = obtener_mapeo_solapas().get(pestana.upper().strip(), pestana)
    try:
        hoja = _hoja_nube(nombre_hoja_real)
    except Exception as e:
        if "429" in str(e):
            raise
        sh = gc.open_by_key(ID_MAESTRO_DB)
        try:
            hoja = sh.worksheet(nombre_hoja_real)
        except Exception:
            if pestana.upper().strip() == "NOTIFICACIONES_SUPERVISORES":
                hoja = sh.add_worksheet(title="NOTIFICACIONES_SUPERVISORES", rows="100", cols="15")
                hoja.append_row(["FECHA_HORA", "SUPERVISOR", "MENSAJE", "ESTADO"])
            else:
                return pd.DataFrame()
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
        print(f"Error leyendo {pestana}: {e}")
        return pd.DataFrame()
leer_matriz_nube.clear = _leer_matriz_nube_cache.clear

def _separar_calle_altura(direccion):
    """Separa 'AV. MITRE 1234' en ('AV. MITRE', '1234'). Para objetivos viejos que solo tenían DIRECCION."""
    m = re.match(r'^\s*(.*?)[\s,]+(?:N[°º]?\s*)?(\d{1,6})\s*$', str(direccion or ""))
    if m and m.group(1).strip():
        return m.group(1).strip(), m.group(2)
    return str(direccion or "").strip(), ""

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
        # La ubicación ya no se guarda: se calcula en vivo con calle, altura y localidad.
        df = df.drop(columns=[c for c in ('LATITUD', 'LONGITUD') if c in df.columns])
        for c in ('CALLE', 'ALTURA', 'DIRECCION', 'LOCALIDAD'):
            if c not in df.columns:
                df[c] = ""
        calles, alturas = [], []
        for _, r in df.iterrows():
            calle, altura = str(r['CALLE']).strip(), str(r['ALTURA']).strip()
            if not calle:
                calle, altura = _separar_calle_altura(r['DIRECCION'])
            calles.append(calle.upper())
            alturas.append(altura)
        df['CALLE'] = calles
        df['ALTURA'] = alturas
        df['LOCALIDAD'] = df['LOCALIDAD'].astype(str).str.strip().str.upper()
        df['DIRECCION'] = (df['CALLE'] + " " + df['ALTURA']).str.strip()
        return df
    return pd.DataFrame()

# --- Ubicación en vivo de los objetivos (OpenStreetMap / Nominatim) ---
@st.cache_resource(show_spinner=False)
def _almacen_geo():
    import threading
    return {"ok": {}, "fallo": {}, "lock": threading.Lock()}

def _normalizar_localidad(loc):
    l = " ".join(str(loc or "").upper().replace(".", "").split())
    if l in ("CABA", "CAPITAL", "CAPITAL FEDERAL", "CIUDAD DE BUENOS AIRES", "CIUDAD AUTONOMA DE BUENOS AIRES",
             "CIUDAD AUTÓNOMA DE BUENOS AIRES", "BUENOS AIRES", "C A B A"):
        return "Ciudad Autónoma de Buenos Aires"
    return str(loc or "").strip()

def _expandir_abreviaturas(calle):
    t = " " + " ".join(str(calle or "").upper().replace(".", " ").split()) + " "
    for a, b in (("AV", "Avenida"), ("AVDA", "Avenida"), ("GRAL", "General"), ("CNEL", "Coronel"), ("CRL", "Coronel"),
                 ("PTE", "Presidente"), ("DR", "Doctor"), ("STA", "Santa"), ("STO", "Santo"), ("ING", "Ingeniero"),
                 ("ALTE", "Almirante"), ("TTE", "Teniente"), ("CAP", "Capitán"), ("PCIA", "Provincia")):
        t = t.replace(f" {a} ", f" {b} ")
    return t.strip()

def _consultar_ubicacion(q=None, estructurado=None):
    """Prueba Nominatim y, si falla, Photon (ambos de OpenStreetMap). Devuelve (lat, lon, tipo) o None."""
    import time
    alm = _almacen_geo()
    desc = q if q else " ".join(str(v) for v in (estructurado or {}).values())
    try:
        params = {"format": "jsonv2", "limit": 1, "countrycodes": "ar"}
        if estructurado:
            params.update(estructurado)
        else:
            params["q"] = q
        r = requests.get(
            "https://nominatim.openstreetmap.org/search", params=params,
            headers={"User-Agent": "AION-YAROKU/1.0 (monitoreo de objetivos)", "Accept-Language": "es"},
            timeout=8,
        )
        time.sleep(1.0)   # Nominatim permite 1 consulta por segundo
        if r.ok:
            datos = r.json()
            if datos:
                return float(datos[0]["lat"]), float(datos[0]["lon"]), datos[0].get("addresstype", "")
            alm["error"] = f"sin resultados para «{desc}»"
        else:
            alm["error"] = f"Nominatim HTTP {r.status_code} para «{desc}»"
    except Exception as e:
        alm["error"] = f"Nominatim {type(e).__name__} para «{desc}»"
    if q:
        try:
            r = requests.get("https://photon.komoot.io/api/", params={"q": q, "limit": 1},
                             headers={"User-Agent": "AION-YAROKU/1.0"}, timeout=8)
            if r.ok:
                feats = r.json().get("features", [])
                if feats:
                    lon, lat = feats[0]["geometry"]["coordinates"]
                    return float(lat), float(lon), feats[0].get("properties", {}).get("type", "")
        except Exception:
            pass
    return None

def geocodificar_direccion(calle, altura, localidad):
    """Ubica un objetivo por calle + altura + localidad. No se guarda en la hoja ni en el código.
    Devuelve (lat, lon, exacta) o None si no se pudo ubicar."""
    import time
    calle = " ".join(str(calle or "").split())
    altura = " ".join(str(altura or "").split())
    localidad = " ".join(str(localidad or "").split())
    if not calle or not localidad:
        return None
    clave = (calle.upper(), altura, localidad.upper())
    alm = _almacen_geo()
    if clave in alm["ok"]:
        return alm["ok"][clave]
    t_fallo = alm["fallo"].get(clave)
    if t_fallo and time.time() - t_fallo < 300:   # no insistir con una dirección que falló hace menos de 5 min
        return None
    loc = _normalizar_localidad(localidad)
    calle_x = _expandir_abreviaturas(calle)
    consultas = []   # (texto libre, parámetros estructurados, ¿incluye altura?)
    if altura:
        consultas.append((None, {"street": f"{altura} {calle}", "city": loc, "country": "Argentina"}, True))
        consultas.append((f"{calle} {altura}, {loc}, Argentina", None, True))
        if calle_x.upper() != calle.upper():
            consultas.append((f"{calle_x} {altura}, {loc}, Argentina", None, True))
        consultas.append((f"{calle} {altura}, {loc}, Buenos Aires, Argentina", None, True))
    consultas.append((f"{calle}, {loc}, Argentina", None, False))
    if calle_x.upper() != calle.upper():
        consultas.append((f"{calle_x}, {loc}, Argentina", None, False))
    with alm["lock"]:
        if clave in alm["ok"]:
            return alm["ok"][clave]
        for q, est, con_altura in consultas:
            res = _consultar_ubicacion(q, est)
            if res:
                exacta = bool(con_altura) and res[2] in ("house", "building", "amenity", "shop", "office", "place")
                alm["ok"][clave] = (res[0], res[1], exacta)
                return alm["ok"][clave]
        alm["fallo"][clave] = time.time()
    return None

def con_coordenadas(df):
    """Agrega LATITUD, LONGITUD y UBICACION_EXACTA a los objetivos (calculadas en vivo, en memoria)."""
    df = df.copy()
    lats, lons, exactas = [], [], []
    for _, r in df.iterrows():
        g = geocodificar_direccion(r.get('CALLE', ''), r.get('ALTURA', ''), r.get('LOCALIDAD', ''))
        lats.append(g[0] if g else None)
        lons.append(g[1] if g else None)
        exactas.append(bool(g[2]) if g else False)
    df['LATITUD'] = pd.to_numeric(pd.Series(lats, index=df.index), errors='coerce')
    df['LONGITUD'] = pd.to_numeric(pd.Series(lons, index=df.index), errors='coerce')
    df['UBICACION_EXACTA'] = exactas
    return df

def url_destino_objetivo(calle, altura, localidad):
    """Destino para Google Maps por dirección (sin coordenadas)."""
    from urllib.parse import quote
    return "https://www.google.com/maps/dir/?api=1&destination=" + quote(f"{calle} {altura}, {localidad}, Argentina") + "&travelmode=driving"

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

def _km(lat1, lon1, lat2, lon2):
    la1, lo1, la2, lo2 = map(math.radians, [lat1, lon1, lat2, lon2])
    a = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(a))

def _buscar_comisarias_osm(lat, lon):
    """Busca dependencias policiales cerca del punto. Overpass (varios servidores espejo, con reintento) y, si fallan todos,
    una sola consulta a Nominatim. Deja el motivo en _almacen_geo()['com_error']."""
    import time
    alm = _almacen_geo()
    errores = []
    cabeceras = {"User-Agent": "AION-YAROKU/1.0 (monitoreo de objetivos)", "Accept-Language": "es"}
    espejos = ("https://overpass-api.de/api/interpreter",
               "https://overpass.private.coffee/api/interpreter",
               "https://overpass.kumi.systems/api/interpreter",
               "https://maps.mail.ru/osm/tools/overpass/api/interpreter")
    limite = time.time() + 45   # tope total para no dejar la pantalla colgada

    def _ordenar(res):
        con_nombre = [x for x in res if "COMISAR" in x["nombre"]]
        return sorted(con_nombre or res, key=lambda x: x["distancia_km"])

    # --- 1) Overpass: radio 6 km y, solo si responde pero sin resultados, 20 km ---
    for radio in (6000, 20000):
        consulta = f'[out:json][timeout:15];nwr["amenity"="police"](around:{radio},{lat},{lon});out center tags;'
        elementos = None
        for url in espejos:
            if time.time() > limite:
                break
            for intento in range(2):
                try:
                    r = requests.post(url, data={"data": consulta}, headers=cabeceras, timeout=12)
                    if r.ok:
                        elementos = r.json().get("elements", [])
                        break
                    errores.append(f"Overpass HTTP {r.status_code}")
                    if r.status_code in (429, 502, 503, 504) and intento == 0:
                        time.sleep(1.5)
                        continue
                    break
                except Exception as e:
                    errores.append(f"Overpass {type(e).__name__}")
                    break
            if elementos is not None:
                break
        if elementos is None:
            break   # ningún servidor respondió: no repetir con un radio mayor
        if elementos:
            res = []
            for e in elementos:
                c = e.get("center") or {}
                la, lo = e.get("lat", c.get("lat")), e.get("lon", c.get("lon"))
                if la is None or lo is None:
                    continue
                t = e.get("tags", {})
                calle = t.get("addr:street", "")
                num = t.get("addr:housenumber", "")
                res.append({
                    "nombre": (t.get("name") or t.get("official_name") or "DEPENDENCIA POLICIAL").upper(),
                    "direccion": (f"{calle} {num}".strip().upper() or "---"),
                    "localidad": (t.get("addr:city") or "").upper(),
                    "telefono": str(t.get("phone") or t.get("contact:phone") or "").split(";")[0].strip(),
                    "lat": float(la), "lon": float(lo),
                    "distancia_km": _km(lat, lon, float(la), float(lo)),
                })
            if res:
                return _ordenar(res)
        errores.append(f"Overpass sin comisarías en {radio // 1000} km")
    # --- 2) Respaldo: Nominatim, una consulta por término (si responde 429 se corta para no empeorarlo) ---
    d = 0.15
    for termino in ("comisaría", "police"):
        if time.time() > limite + 10:
            break
        try:
            r = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": termino, "format": "jsonv2", "limit": 20, "countrycodes": "ar", "bounded": 1,
                        "viewbox": f"{lon - d},{lat + d},{lon + d},{lat - d}"},
                headers=cabeceras, timeout=10)
            if r.status_code == 429:
                errores.append("Nominatim HTTP 429")
                break
            if r.ok:
                res = []
                for x in r.json():
                    nombre = str(x.get("name") or x.get("display_name", "").split(",")[0] or "DEPENDENCIA POLICIAL").upper()
                    res.append({
                        "nombre": nombre, "direccion": "---", "localidad": "", "telefono": "",
                        "lat": float(x["lat"]), "lon": float(x["lon"]),
                        "distancia_km": _km(lat, lon, float(x["lat"]), float(x["lon"])),
                    })
                if res:
                    return _ordenar(res)
            else:
                errores.append(f"Nominatim HTTP {r.status_code}")
        except Exception as e:
            errores.append(f"Nominatim {type(e).__name__}")
        time.sleep(1.1)
    alm["com_error"] = "; ".join(dict.fromkeys(errores)) or "sin resultados"
    return []

def comisaria_para_objetivo(fila_objetivo):
    """Comisaría más cercana a un objetivo al activarse el pánico, buscada en vivo en OpenStreetMap
    (no hay comisarías cargadas en el código). Criterio actual: la más cercana en línea recta, prefiriendo las
    que se llaman 'Comisaría'. Si OSM no trae teléfono se usa el 911.
    PENDIENTE: ajustar con los 3 requisitos que defina Ivonne.
    Devuelve un dict {nombre, direccion, localidad, telefono, lat, lon, distancia_km} o None."""
    import time
    if fila_objetivo is None:
        return None
    lat, lon = None, None
    try:
        la, lo = fila_objetivo.get('LATITUD'), fila_objetivo.get('LONGITUD')
        if la is not None and lo is not None and not pd.isna(la) and not pd.isna(lo):
            lat, lon = float(la), float(lo)
    except Exception:
        pass
    if lat is None:
        g = geocodificar_direccion(fila_objetivo.get('CALLE', ''), fila_objetivo.get('ALTURA', ''), fila_objetivo.get('LOCALIDAD', ''))
        if not g:
            return None
        lat, lon = g[0], g[1]
    alm = _almacen_geo()
    clave = (round(lat, 4), round(lon, 4))
    com_cache = alm.setdefault("com", {})
    com_fallo = alm.setdefault("com_fallo", {})
    if clave in com_cache:
        return com_cache[clave]
    if time.time() - com_fallo.get(clave, 0) < 120:
        return None
    cand = _buscar_comisarias_osm(lat, lon)
    if not cand:
        com_fallo[clave] = time.time()
        return None
    mejor = dict(cand[0])
    if not mejor["telefono"]:
        mejor["telefono"] = "911"
    com_cache[clave] = mejor
    return mejor

def _resumen_comisaria(com):
    """Datos listos para mostrar en los carteles de pánico."""
    if not com:
        return {"nombre": "NO SE PUDO DETERMINAR (reintentar)", "direccion": "---", "telefono": "", "distancia": "---"}
    try:
        dist = f"{float(com.get('distancia_km')):.2f}"
    except Exception:
        dist = "---"
    return {"nombre": str(com.get("nombre", "---")), "direccion": str(com.get("direccion", "---")),
            "telefono": str(com.get("telefono", "")).strip(), "distancia": dist}

def registrar_objetivo(nombre_obj, calle, altura, localidad, supervisor, responsables=""):
    """Agrega el objetivo respetando los encabezados de la hoja (OBJETIVO, CALLE, ALTURA, LOCALIDAD, SUPERVISOR)."""
    try:
        gc = conectar_google()
        if not gc:
            return False
        hoja = _obtener_hoja_para_escribir(gc, obtener_mapeo_solapas().get("OBJETIVOS", "OBJETIVOS"))
        enc = [str(h).strip().upper() for h in _reintentar_429(lambda: hoja.row_values(1))]
        if not enc:
            enc = ["OBJETIVO", "CALLE", "ALTURA", "LOCALIDAD", "SUPERVISOR"]
            _reintentar_429(lambda: hoja.append_row(enc))
        for col in ("OBJETIVO", "CALLE", "ALTURA", "LOCALIDAD", "SUPERVISOR"):
            _asegurar_columna(hoja, enc, col)
        calle_u = str(calle).strip().upper()
        altura_u = str(altura).strip().upper()
        valores = {
            "OBJETIVO": str(nombre_obj).strip().upper(),
            "CALLE": calle_u,
            "ALTURA": altura_u,
            "DIRECCION": f"{calle_u} {altura_u}".strip(),   # solo si la hoja tiene esa columna
            "LOCALIDAD": str(localidad).strip().upper(),
            "SUPERVISOR": str(supervisor).strip().upper(),
            "RESPONSABLES": str(responsables).strip().upper(),   # solo si la hoja tiene esa columna
        }
        fila = [valores.get(h, "") for h in enc]
        _reintentar_429(lambda: hoja.append_row(fila, table_range="A1"))
        st.cache_data.clear()
        return True
    except Exception as e:
        print(f"Error registrando objetivo: {e}")
        st.error(f"⚠️ Error técnico en nube (OBJETIVOS): {e}")
        return False

def _avisar_cambio_servicio(supervisor, asunto, texto, usuario):
    """El supervisor recibe el aviso en la campanita y en su mensajería (gravedad AMARILLO); Jefe y Gerencia quedan al tanto."""
    notificar_novedad(texto, extra=[supervisor])
    escribir_registro_nube("MENSAJERIA", [obtener_hora_argentina(), usuario, supervisor, asunto, texto, "PENDIENTE", "AMARILLO"])

def alta_servicio(nombre, calle, altura, localidad, supervisor, responsables, usuario):
    nombre_u = str(nombre).strip().upper()
    sup_u = str(supervisor).strip().upper()
    df_o = cargar_objetivos()
    if not df_o.empty and (col_texto(df_o, 'OBJETIVO').str.strip().str.upper() == nombre_u).any():
        return False, f"Ya existe un servicio activo llamado {nombre_u}."
    if not registrar_objetivo(nombre_u, calle, altura, localidad, sup_u, responsables):
        return False, "No se pudo registrar el servicio en la nube. Verificá la conexión con Google Sheets."
    escribir_registro_nube("SOLICITUDES DE ACCESO", [obtener_hora_argentina(), usuario, "ALTA", f"{nombre_u} | ASIG: {sup_u}", "PROCESADO"])
    _avisar_cambio_servicio(sup_u, "ALTA DE SERVICIO",
        f"🟢 ALTA DE SERVICIO: {usuario} dio de alta el objetivo {nombre_u} ({str(calle).strip().upper()} {str(altura).strip().upper()}, {str(localidad).strip().upper()}) y te lo asignó. Ya figura en tu panel.", usuario)
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
        print(f"Error dando de baja el servicio: {e}")
        return False, f"No se pudo dar de baja el servicio: {e}"
    escribir_registro_nube("SOLICITUDES DE ACCESO", [obtener_hora_argentina(), usuario, "BAJA", f"{obj_u} - MOTIVO: {str(motivo).strip().upper()}", "PROCESADO"])
    if sup_u:
        _avisar_cambio_servicio(sup_u, "BAJA DE SERVICIO",
            f"🔴 BAJA DE SERVICIO: {usuario} dio de baja el objetivo {obj_u}. Motivo: {str(motivo).strip().upper()}. Ya no figura en tu panel; revisá el personal asignado a ese objetivo.", usuario)
    else:
        notificar_novedad(f"🔴 BAJA DE SERVICIO: {usuario} dio de baja el objetivo {obj_u}. Motivo: {str(motivo).strip().upper()}.")
    return True, f"Servicio {obj_u} dado de baja." + (f" Se avisó a {sup_u}." if sup_u else "")

def obtener_lista_supervisores_dinamica():
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

def obtener_lista_por_rol_dinamica(rol):
    """Cuentas aprobadas de un rol (MONITOREO, JEFE DE OPERACIONES, GERENCIA) para mandarle un mensaje privado a una persona."""
    df_u = leer_matriz_nube("USUARIOS")
    if df_u.empty:
        return []
    col_r = 'ROL' if 'ROL' in df_u.columns else ('ROLES' if 'ROLES' in df_u.columns else None)
    col_u = 'USUARIO' if 'USUARIO' in df_u.columns else df_u.columns[0]
    if not col_r or 'ESTADO' not in df_u.columns:
        return []
    m = ((col_texto(df_u, col_r).str.strip().str.upper() == str(rol).strip().upper()) &
         (col_texto(df_u, 'ESTADO').str.strip().str.upper() == "APROBADO"))
    return sorted({str(n).strip().upper() for n in df_u[m][col_u] if str(n).strip() and str(n).strip().upper() != "NAN"})

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
DIAS_MENSAJES_NUEVOS = 7  # solo se cuentan como "nuevos" los mensajes de los últimos días

def _remitente_mensajeria():
    """Nombre con el que firma y con el que se marca como leído el usuario actual."""
    if str(st.session_state.get("rol_sel", "")).strip().upper() == "VIGILADOR":
        return _nombre_vigilador_sesion()
    return str(st.session_state.get("user_sel", "")).strip().upper()

def _identidades_mensajeria():
    """Todos los destinos a los que puede llegarle un mensaje al usuario actual."""
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

def _vigiladores_en_turno():
    """{NOMBRE: {'objetivo', 'hora'}} de los vigiladores que marcaron INGRESO y todavía no EGRESO (turno en curso)."""
    try:
        df = leer_matriz_nube("PRESENTISMO")
    except Exception:
        return {}
    if df.empty or df.shape[1] < 6:
        return {}
    ultimos = {}
    for f in df.astype(str).values.tolist():
        nombre, tipo = f[3].strip().upper(), f[5].strip().upper()
        if nombre and tipo in ("INGRESO", "EGRESO"):
            ultimos[nombre] = {"tipo": tipo, "fecha": f[0].strip(), "hora": f[1].strip(), "objetivo": f[4].strip().upper()}
    try:
        ahora = datetime.strptime(obtener_hora_argentina(), "%Y-%m-%d %H:%M:%S")
    except Exception:
        return {}
    out = {}
    for n, u in ultimos.items():
        if u["tipo"] != "INGRESO":
            continue
        try:
            t0 = datetime.strptime(f"{u['fecha']} {u['hora'][:8]}", "%Y-%m-%d %H:%M:%S")
            if (ahora - t0).total_seconds() < HORAS_MAX_BLOQUEO_TURNO * 3600:
                out[n] = {"objetivo": u["objetivo"] or "SIN OBJETIVO", "hora": u["hora"][:5]}
        except Exception:
            pass
    return out

def _objetivos_supervisor_sesion():
    """Objetivos del supervisor logueado (en mayúsculas). None si el usuario actual no es supervisor."""
    if str(st.session_state.get("rol_sel", "")).strip().upper() != "SUPERVISOR":
        return None
    df_o = cargar_objetivos()
    sup = str(st.session_state.get("user_sel", "")).strip().upper()
    if df_o.empty or 'SUPERVISOR' not in df_o.columns:
        return []
    return col_texto(df_o, 'OBJETIVO')[col_texto(df_o, 'SUPERVISOR').str.strip().str.upper() == sup].str.strip().str.upper().tolist()

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
    """Cada usuario ve los hilos donde escribió o donde le escribieron (el administrador ve todo)."""
    if df_msg.empty or 'DESTINATARIO' not in df_msg.columns:
        return df_msg.iloc[0:0]
    if st.session_state.get("admin_autenticado", False):
        return df_msg
    ids = _identidades_mensajeria()
    dest = col_texto(df_msg, 'DESTINATARIO').str.strip().str.upper()
    rem = col_texto(df_msg, 'REMITENTE').str.strip().str.upper()
    return df_msg[dest.isin(ids) | rem.isin(ids)]

def _mensajes_sin_leer(df_msg):
    """Mensajes dirigidos al usuario (no escritos por él) que todavía no marcó como leídos."""
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
    """Agrega al usuario actual en la columna LEIDO_POR de cada mensaje (la crea si no existe)."""
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
        print(f"Error marcando mensajes leídos: {e}")
        return False

@st.fragment(run_every=15)
def _listado_hilos_mensajeria(rol_contexto):
    """Hilos de mensajes: se actualiza solo cada 15 segundos, sin que el usuario tenga que tocar nada."""
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
                    else:
                        st.warning("⚠️ Escribí la respuesta antes de enviar.")

def renderizar_mensajeria_global(rol_contexto):
    if 'asunto_respuesta' not in st.session_state:
        st.session_state.asunto_respuesta = None

    df_msg = leer_matriz_nube("MENSAJERIA")
    yo = _remitente_mensajeria()
    st.subheader("💬 COMUNICACIONES OPERATIVAS")

    OPC_VIG = "👮 UN VIGILADOR ESPECÍFICO…"
    vig_todos = obtener_lista_vigiladores_dinamica()
    vig_set = set(vig_todos)
    yo_ids = _identidades_mensajeria()
    opciones = [o for o in _destinatarios_mensajeria() if o not in vig_set]
    if "VIGILADORES" in opciones:
        opciones.insert(opciones.index("VIGILADORES") + 1, OPC_VIG)
    else:
        opciones.append(OPC_VIG)
    # Mensaje privado a una persona en particular de cada área
    PERSONAS = {
        "MONITOREO": ("🛰️ UNA PERSONA DE MONITOREO…", "PERSONA DE MONITOREO"),
        "JEFE DE OPERACIONES": ("📋 UNA PERSONA DE JEFE DE OPERACIONES…", "PERSONA DE JEFE DE OPERACIONES"),
        "GERENCIA": ("🏢 UNA PERSONA DE GERENCIA…", "PERSONA DE GERENCIA"),
        "SUPERVISOR": ("🧑‍✈️ UN SUPERVISOR…", "SUPERVISOR"),
    }
    personas_rol = {r: [n for n in obtener_lista_por_rol_dinamica(r) if n not in yo_ids] for r in PERSONAS if r != "SUPERVISOR"}

    # Supervisores: cada uno con sus objetivos; si quien escribe es vigilador, su supervisor va primero
    df_o_msg = cargar_objetivos()
    objs_por_sup = {}
    if not df_o_msg.empty and 'SUPERVISOR' in df_o_msg.columns:
        for _o, _sp in zip(col_texto(df_o_msg, 'OBJETIVO').str.strip().str.upper(), col_texto(df_o_msg, 'SUPERVISOR').str.strip().str.upper()):
            if _sp and _sp not in ("N/A", "MONITOREO", "NAN"):
                objs_por_sup.setdefault(_sp, []).append(_o)
    sups_msg = [x for x in sorted(set(obtener_lista_supervisores_dinamica()) | set(objs_por_sup)) if x and x not in yo_ids]
    mi_sup, mi_obj = None, ""
    if str(st.session_state.get("rol_sel", "")).strip().upper() == "VIGILADOR":
        mi_obj = str(_vigiladores_en_turno().get(_nombre_vigilador_sesion(), {}).get("objetivo") or st.session_state.get("obj_actual_vig", "") or "").strip().upper()
        mi_sup = next((sp for sp, lst in objs_por_sup.items() if mi_obj and mi_obj in lst), None)
    sups_msg.sort(key=lambda x: (x != mi_sup, x))
    personas_rol["SUPERVISOR"] = sups_msg
    etiq_personas = {}
    for sp in sups_msg:
        if sp == mi_sup:
            etiq_personas[sp] = f"⭐ {sp} — tu supervisor ({mi_obj})"
        else:
            lst = objs_por_sup.get(sp, [])
            etiq_personas[sp] = f"🧑‍✈️ {sp}" + (f" — {', '.join(lst[:2])}{'…' if len(lst) > 2 else ''}" if lst else "")
    todas_personas = {n for lst in personas_rol.values() for n in lst}
    opciones = [o for o in opciones if o not in todas_personas]
    for r, (etiqueta_opc, _) in PERSONAS.items():
        if personas_rol[r]:
            ancla = "SUPERVISORES" if r == "SUPERVISOR" else r
            if ancla in opciones:
                opciones.insert(opciones.index(ancla) + 1, etiqueta_opc)
            else:
                opciones.append(etiqueta_opc)
    destino_resp = st.session_state.get("destino_respuesta", "")
    es_vigilador = str(st.session_state.get("rol_sel", "")).strip().upper() == "VIGILADOR"
    if es_vigilador:
        # Los vigiladores no se ven ni se escriben entre sí (ni por nombre, ni por grupo, ni por TODOS)
        opciones = [o for o in opciones if o not in ("VIGILADORES", "TODOS", OPC_VIG)]
        if destino_resp in vig_set or destino_resp in ("VIGILADORES", "TODOS"):
            destino_resp = ""
    respondiendo = bool(st.session_state.asunto_respuesta)
    vig_resp = destino_resp if (respondiendo and destino_resp in vig_set) else ""
    persona_resp_rol = next((r for r, lst in personas_rol.items() if respondiendo and destino_resp in lst), None)
    if destino_resp and destino_resp not in opciones and not vig_resp and not persona_resp_rol:
        opciones = [destino_resp] + opciones
    if respondiendo and vig_resp:
        idx_dest = opciones.index(OPC_VIG)
    elif persona_resp_rol:
        idx_dest = opciones.index(PERSONAS[persona_resp_rol][0])
    elif respondiendo and destino_resp in opciones:
        idx_dest = opciones.index(destino_resp)
    else:
        idx_dest = 0
    clave_hilo = st.session_state.asunto_respuesta or "nuevo"

    # El destinatario va fuera del formulario para que, al elegir "vigilador específico", aparezca la lista de activos.
    destinatario = st.selectbox("PARA:", opciones, index=idx_dest, key=f"dest_{rol_contexto}_{clave_hilo}")
    if destinatario == OPC_VIG:
        en_turno = _vigiladores_en_turno()
        objs_sup_msg = _objetivos_supervisor_sesion()
        if objs_sup_msg is None:
            incluir_sin_turno = st.checkbox("Incluir vigiladores sin turno en curso", value=False, key=f"vig_todos_{rol_contexto}_{clave_hilo}")
            cand = [v for v in vig_todos if v not in yo_ids and (incluir_sin_turno or v in en_turno or v == vig_resp)]
        else:
            # Supervisor: solo los vigiladores en turno en SUS objetivos (los de otros supervisores no aparecen)
            cand = [v for v in vig_todos if v not in yo_ids and
                    ((v in en_turno and en_turno[v]["objetivo"] in objs_sup_msg) or v == vig_resp)]
        cand.sort(key=lambda v: (v not in en_turno, en_turno.get(v, {}).get("objetivo", ""), v))
        n_act = sum(1 for v in cand if v in en_turno)
        if not cand:
            st.info("No hay vigiladores con turno en curso" + (" en tus objetivos." if objs_sup_msg is not None else ". Tildá \"Incluir vigiladores sin turno\" para elegir a cualquiera."))
            destinatario = None
        else:
            etiquetas = {v: (f"🟢 {v} — {en_turno[v]['objetivo']} (desde {en_turno[v]['hora']} hs)" if v in en_turno
                             else f"⚪ {v} — sin turno en curso") for v in cand}
            idx_v = cand.index(vig_resp) if vig_resp in cand else 0
            destinatario = st.selectbox(f"VIGILADOR ({n_act} en turno):", cand, index=idx_v,
                                        format_func=lambda v: etiquetas.get(v, v), key=f"vig_{rol_contexto}_{clave_hilo}")
            st.caption("🔒 Solo ese vigilador (y vos) van a ver este mensaje.")
    else:
        rol_pers = next((r for r, (e, _) in PERSONAS.items() if e == destinatario), None)
        if rol_pers:
            lst_p = personas_rol[rol_pers]
            idx_m = lst_p.index(destino_resp) if (respondiendo and destino_resp in lst_p) else 0
            destinatario = st.selectbox(f"{PERSONAS[rol_pers][1]}:", lst_p, index=idx_m,
                                        format_func=lambda n: etiq_personas.get(n, n),
                                        key=f"pers_{rol_pers}_{rol_contexto}_{clave_hilo}")
            st.caption("🔒 Solo esa persona (y vos) van a ver este mensaje.")

    with st.form(key=f"form_msg_{rol_contexto}", clear_on_submit=True):
        if st.session_state.asunto_respuesta:
            st.info(f"↩️ Respondiendo al hilo: {st.session_state.asunto_respuesta}")
            asunto_input = st.text_input("ASUNTO:", value=st.session_state.asunto_respuesta, disabled=True)
        else:
            asunto_input = st.text_input("ASUNTO:")

        col_a, col_b = st.columns([3, 1])
        with col_a:
            txt_msg = st.text_input("MENSAJE:")
            st.caption(f"PARA: **{destinatario or '— elegí un vigilador —'}**")
        with col_b:
            gravedad = st.selectbox("GRAVEDAD:", ["VERDE", "AMARILLO", "ROJA"], key=f"grav_{rol_contexto}_{clave_hilo}",
                                    format_func=lambda g: f"{GRAVEDADES_MENSAJE[g]} {g}")

        if st.form_submit_button("TRANSMITIR A LA RED"):
            if not destinatario:
                st.warning("⚠️ Elegí a qué vigilador mandar el mensaje.")
            elif txt_msg.strip():
                escribir_registro_nube("MENSAJERIA", [
                    obtener_hora_argentina(), yo, destinatario,
                    (asunto_input or "GENERAL").upper(), txt_msg.upper(), "PENDIENTE", gravedad
                ])
                st.session_state.mensaje_enviado = "RESPUESTA" if st.session_state.asunto_respuesta else "MENSAJE"
                st.session_state.mensaje_enviado_grav = gravedad
                st.session_state.asunto_respuesta = None
                st.session_state.destino_respuesta = ""
                sincronizar_url_sesion()
                st.rerun()
            else:
                st.warning("⚠️ Escribí el mensaje antes de transmitir.")

    if 'mensaje_enviado' in st.session_state:
        grav_env = st.session_state.pop("mensaje_enviado_grav", "VERDE")
        txt_env = f"✅ {'RESPUESTA' if st.session_state.mensaje_enviado == 'RESPUESTA' else 'MENSAJE'} ENVIADO · {GRAVEDADES_MENSAJE.get(grav_env, '⚪')} GRAVEDAD {grav_env}"
        {"ROJA": st.error, "AMARILLO": st.warning}.get(grav_env, st.success)(txt_env)
        del st.session_state.mensaje_enviado

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
        alarma_panico_sonora(_rol_alarma, st.session_state.get('user_sel', ''))   # sirena + aviso en el panel lateral
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
        if len(pend) > 8:
            st.caption(f"y {len(pend) - 8} notificaciones más (las más viejas).")

# --- TURNO DEL VIGILADOR (INGRESO -> RECORRIDAS -> FINALIZAR) Y RONDAS JUSTIFICADAS ---
HORAS_MAX_BLOQUEO_TURNO = 18  # si pasaron más horas desde el ingreso, el turno se considera vencido y no traba el cierre de sesión

@st.cache_data(ttl=30, show_spinner=False)
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
    """True si el vigilador marcó INGRESO y todavía no marcó EGRESO (turno en curso)."""
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

def _rondas_justificadas_hoy(obj_u, dni, horarios, hoy):
    """{número de ronda: motivo} de las rondas del día que el vigilador respondió NO / justificó.
    La ronda 1 es el primer horario del día, la 2 el segundo, etc."""
    saltadas = {}
    df = leer_matriz_nube("RESPUESTAS RECORRIDAS")
    if df.empty or not {'FECHA_HORA', 'OBJETIVO', 'DNI', 'HORARIO', 'RESPUESTA'} <= set(df.columns):
        return saltadas
    m = ((col_texto(df, 'OBJETIVO').str.strip().str.upper() == obj_u) &
         (col_texto(df, 'DNI').str.strip() == str(dni).strip()) &
         col_texto(df, 'FECHA_HORA').str.contains(hoy, regex=False) &
         (col_texto(df, 'RESPUESTA').str.strip().str.upper() == "NO"))
    for _, f in df[m].iterrows():
        hs = _horarios_unicos([f['HORARIO']])
        if hs and hs[0] in horarios:
            saltadas[horarios.index(hs[0]) + 1] = str(f.get('MOTIVO', '')).strip()
    return saltadas

# --- CALENDARIO EDITABLE (BARRA LATERAL, TODOS LOS PERFILES) ---
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

def _cal_firma():
    return str(st.session_state.get("user_sel", "")).strip().upper() + " · " + obtener_hora_argentina()[:16]

def _cal_guardar(fecha, titulo, detalle, id_evento=None):
    try:
        hoja = _hoja_calendario()
        if hoja is None:
            return False
        firma = _cal_firma()
        if not id_evento:
            nuevo_id = str(int(datetime.now().timestamp() * 1000))
            hoja.append_row([nuevo_id, fecha.strftime("%Y-%m-%d"), titulo, detalle, firma, firma])
        else:
            fila = hoja.col_values(1).index(str(id_evento)) + 1
            hoja.update(f"B{fila}:F{fila}", [[fecha.strftime("%Y-%m-%d"), titulo, detalle,
                                              hoja.cell(fila, 5).value or firma, firma]])
        st.cache_data.clear()
        return True
    except Exception as e:
        print(f"Error guardando evento de calendario: {e}")
        return False

def _cal_borrar(id_evento):
    try:
        hoja = _hoja_calendario()
        if hoja is None:
            return False
        fila = hoja.col_values(1).index(str(id_evento)) + 1
        hoja.delete_rows(fila)
        st.cache_data.clear()
        return True
    except Exception as e:
        print(f"Error borrando evento de calendario: {e}")
        return False

# --- SEGUIMIENTO DE VIGILADORES (PANEL LATERAL): recorrido por vigilador con colores e íconos ---
def _registro_escaneos_vigiladores():
    """REGISTRO RECORRIDOS normalizado: _VIG (nombre), _OBJ, _PTO, _FH (fecha/hora), _RONDA."""
    df = leer_matriz_nube("REGISTRO RECORRIDOS")
    if df.empty or not {'FECHA_HORA', 'OBJETIVO', 'PUNTO'} <= set(df.columns):
        return pd.DataFrame()
    df = df.loc[:, ~df.columns.duplicated()].copy()
    col_vig = next((c for c in ['VIGILADOR', 'NOMBRE', 'APELLIDO Y NOMBRE'] if c in df.columns), None)
    if col_vig:
        df['_VIG'] = col_texto(df, col_vig).str.strip().str.upper()
    elif 'DNI' in df.columns:
        df['_VIG'] = col_texto(df, 'DNI').str.replace(r'\D', '', regex=True)
        df_pad = leer_matriz_nube("PADRON VIGILADORES")
        if not df_pad.empty and {'DNI', 'NOMBRE'} <= set(df_pad.columns):
            mapa = dict(zip(col_texto(df_pad, 'DNI').str.replace(r'\D', '', regex=True),
                            col_texto(df_pad, 'NOMBRE').str.strip().str.upper()))
            df['_VIG'] = df['_VIG'].map(lambda d: mapa.get(d, d))
    else:
        df['_VIG'] = "---"
    df['_OBJ'] = col_texto(df, 'OBJETIVO').str.strip().str.upper()
    df['_PTO'] = col_texto(df, 'PUNTO').str.strip().str.upper()
    df['_FH'] = pd.to_datetime(df['FECHA_HORA'], errors='coerce')
    df['_RONDA'] = pd.to_numeric(df['RONDA'], errors='coerce').fillna(1).astype(int) if 'RONDA' in df.columns else 1
    df = df.dropna(subset=['_FH'])
    return df.sort_values('_FH')

def _eventos_fraude_qr(fecha_txt=None):
    """Escaneos rechazados y reportados hoy (se leen de los mensajes de alerta de fraude QR).
    Devuelve lista de dicts: fh, vig, obj, pto, tipo, clase ('FRAUDE' o 'SALTEO')."""
    df = leer_matriz_nube("MENSAJERIA")
    if df.empty:
        return []
    vistos, out = set(), []
    for fila in df.astype(str).values.tolist():
        texto = " | ".join(fila)
        if "POSIBLE FRAUDE QR" not in texto.upper():
            continue
        m_f = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', texto)
        m = re.search(r'POSIBLE FRAUDE QR \(([^)]*)\):\s*(.*?)\s+-\s+OBJ:\s*(.*?)\s+-\s+PUNTO:\s*(.*?)\.(?:\s|$)', texto, flags=re.I)
        if not m or not m_f or (fecha_txt and not m_f.group(1).startswith(fecha_txt)):
            continue
        tipo, vig, obj, pto = [x.strip().upper() for x in m.groups()]
        clave = (m_f.group(1), vig, obj, pto, tipo)
        if clave in vistos:
            continue
        vistos.add(clave)
        clase = "FRAUDE"   # todo escaneo rechazado y reportado (incluido querer saltear un punto) se muestra como fraude
        out.append({"fh": pd.Timestamp(m_f.group(1)), "vig": vig, "obj": obj, "pto": pto, "tipo": tipo, "clase": clase})
    return out

_SEG_ESTILO = {
    "OK":        ("#00E676", "rgba(0,230,118,0.12)", "✅"),
    "SALTEO":    ("#FF9100", "rgba(255,145,0,0.15)", "⚠️"),
    "FRAUDE":    ("#FF1744", "rgba(255,23,68,0.15)", "🚩"),
    "PENDIENTE": ("#94A3B8", "rgba(148,163,184,0.10)", "⏳"),
}

def _fila_seg_html(estado, punto, detalle):
    c, bg, ico = _SEG_ESTILO[estado]
    return (f"<div style='border-left:4px solid {c};background:{bg};padding:3px 6px;margin:2px 0;"
            f"font-size:12px;border-radius:3px;'>{ico} <b>{_html_msg.escape(punto)}</b>"
            f"<span style='float:right;color:{c};'>{_html_msg.escape(detalle)}</span></div>")

def mostrar_seguimiento_sidebar():
    """Panel lateral para Monitoreo, Jefe de Operaciones, Gerencia y Supervisor (este, solo sus objetivos)."""
    rol = st.session_state.get("rol_sel")
    if rol not in ("MONITOREO", "JEFE DE OPERACIONES", "GERENCIA", "SUPERVISOR"):
        return
    objs_sup = None
    if rol == "SUPERVISOR":
        if not st.session_state.get("sup_autenticado"):
            return
        df_o = cargar_objetivos()
        sup = str(st.session_state.get("user_sel", "")).strip().upper()
        objs_sup = []
        if not df_o.empty and 'SUPERVISOR' in df_o.columns:
            objs_sup = col_texto(df_o, 'OBJETIVO')[col_texto(df_o, 'SUPERVISOR').str.strip().str.upper() == sup].str.strip().str.upper().tolist()

    st.markdown("---")
    st.markdown("### 🛰️ SEGUIMIENTO DE VIGILADORES")

    @st.fragment(run_every=20)
    def _panel():
        hoy = obtener_hora_argentina().split(" ")[0]
        st.markdown(
            "<div style='font-size:11px;line-height:1.7'>✅ <span style='color:#00E676'>hecho (con horario)</span><br>"
            "⚠️ <span style='color:#FF9100'>no lo hizo</span><br>"
            "🚩 <span style='color:#FF1744'>fraude (incluye querer saltear un punto)</span><br>"
            "⏳ <span style='color:#94A3B8'>pendiente</span></div>", unsafe_allow_html=True)
        if st.button("🔄 ACTUALIZAR", key="seg_side_refrescar", use_container_width=True):
            leer_matriz_nube.clear()

        df = _registro_escaneos_vigiladores()
        dia = df[df['_FH'].dt.strftime('%Y-%m-%d') == hoy].copy() if not df.empty else pd.DataFrame()
        eventos = _eventos_fraude_qr(hoy)

        if objs_sup is not None:
            ok_objs = set(objs_sup)
            vigs_ok = set(dia[dia['_OBJ'].isin(ok_objs)]['_VIG']) if not dia.empty else set()
            vigs_ok |= {e["vig"] for e in eventos if e["obj"] in ok_objs}
            dia = dia[dia['_VIG'].isin(vigs_ok)].copy() if not dia.empty else dia
            eventos = [e for e in eventos if e["vig"] in vigs_ok]

        vigs = sorted(set(dia['_VIG']) if not dia.empty else set()) 
        vigs = sorted(set(vigs) | {e["vig"] for e in eventos})
        if not vigs:
            st.info("Hoy todavía no hay escaneos de recorridos.")
            return

        df_p = leer_matriz_nube("RECORRIDOS PUNTOS")
        planificado = {}
        if not df_p.empty and {'OBJETIVO', 'PUNTO'} <= set(df_p.columns):
            dfp = df_p.copy()
            dfp['_O'] = col_texto(dfp, 'OBJETIVO').str.strip().str.upper()
            dfp['_P'] = col_texto(dfp, 'PUNTO').str.strip().str.upper()
            if 'ORDEN' in dfp.columns:
                dfp['_ORD'] = pd.to_numeric(dfp['ORDEN'], errors='coerce')
                dfp = dfp.sort_values('_ORD')
            for o, g in dfp.groupby('_O', sort=False):
                planificado[o] = g['_P'].drop_duplicates().tolist()

        for v in vigs:
            g = dia[dia['_VIG'] == v].sort_values('_FH') if not dia.empty else pd.DataFrame()
            ev_v = [e for e in eventos if e["vig"] == v]
            hay_fraude = any(e["clase"] == "FRAUDE" for e in ev_v)
            hay_salteo = any(e["clase"] == "SALTEO" for e in ev_v)

            objs = list(dict.fromkeys(g['_OBJ'].tolist() if not g.empty else []))
            for e in ev_v:
                if e["obj"] not in objs:
                    objs.append(e["obj"])

            bloques, resumen_ok, resumen_tot = [], 0, 0
            for o in objs:
                go = g[g['_OBJ'] == o] if not g.empty else pd.DataFrame()
                rondas = sorted(set(go['_RONDA'].tolist())) if not go.empty else [1]
                ronda_actual = rondas[-1]
                puntos = list(planificado.get(o, []))
                for p in (go['_PTO'].tolist() if not go.empty else []):
                    if p not in puntos:
                        puntos.append(p)
                ev_o = [e for e in ev_v if e["obj"] == o]
                horarios = []
                if not df_p.empty and 'HORARIO' in df_p.columns:
                    _m = df_p[col_texto(df_p, 'OBJETIVO').str.strip().str.upper() == o]
                    horarios = _horarios_unicos(_m['HORARIO'].dropna().tolist())
                bloques.append(f"<div style='margin-top:6px;font-size:12px;color:#00E5FF'><b>🏢 {_html_msg.escape(o)}</b></div>")
                for r in rondas:
                    gr = go[go['_RONDA'] == r] if not go.empty else pd.DataFrame()
                    hechos = {row['_PTO']: row['_FH'] for _, row in gr.iterrows()}
                    ult_idx = max([puntos.index(p) for p in hechos if p in puntos], default=-1)
                    titulo_r = f"Ronda {r}" + (f" · {horarios[r - 1]} hs" if r <= len(horarios) else "")
                    bloques.append(f"<div style='font-size:11px;color:#A0A5B5;margin-top:3px'>{_html_msg.escape(titulo_r)}</div>")
                    es_actual = (r == ronda_actual)
                    for i, p in enumerate(puntos):
                        evs_p = [e for e in ev_o if e["pto"] == p] if es_actual else []
                        if p in hechos:
                            extra = " 🚩" if any(e["clase"] == "FRAUDE" for e in evs_p) else ""
                            bloques.append(_fila_seg_html("OK", p, hechos[p].strftime('%H:%M:%S') + extra))
                            if es_actual:
                                resumen_ok += 1
                        else:
                            ev_f = next((e for e in evs_p if e["clase"] == "FRAUDE"), None)
                            ev_s = next((e for e in evs_p if e["clase"] == "SALTEO"), None)
                            if ev_f:
                                bloques.append(_fila_seg_html("FRAUDE", p, ev_f["fh"].strftime('%H:%M:%S')))
                            elif ev_s:
                                bloques.append(_fila_seg_html("SALTEO", p, ev_s["fh"].strftime('%H:%M:%S')))
                            elif (not es_actual) or i < ult_idx:
                                bloques.append(_fila_seg_html("SALTEO", p, "no realizado"))
                            else:
                                bloques.append(_fila_seg_html("PENDIENTE", p, "—"))
                    if es_actual:
                        resumen_tot += len(puntos)

            # cambios de objetivo
            avisos = []
            if not g.empty:
                prev = None
                for _, row in g.iterrows():
                    if prev is not None and row['_OBJ'] != prev:
                        avisos.append(f"🔀 {row['_FH'].strftime('%H:%M:%S')}: pasó de {prev} a {row['_OBJ']}")
                    prev = row['_OBJ']

            ico = "🚩" if hay_fraude else ("⚠️" if hay_salteo else "👮")
            with st.expander(f"{ico} {v}", expanded=False):
                if not g.empty:
                    u = g.iloc[-1]
                    st.caption(f"Último escaneo: {u['_FH'].strftime('%H:%M:%S')} · {u['_OBJ']} · {u['_PTO']}")
                if resumen_tot:
                    st.progress(min(1.0, resumen_ok / resumen_tot), text=f"{resumen_ok} de {resumen_tot} puntos (ronda actual)")
                for a in avisos:
                    st.warning(a)
                st.markdown("".join(bloques), unsafe_allow_html=True)

    _panel()

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

        df_cal = leer_matriz_nube("CALENDARIO")
        if df_cal.empty or not set(_CAL_COLS) <= set(df_cal.columns):
            df_cal = pd.DataFrame(columns=_CAL_COLS)
        df_cal = df_cal.copy()
        df_cal["_F"] = pd.to_datetime(df_cal["FECHA"], errors="coerce")
        df_mes = df_cal[(df_cal["_F"].dt.year == anio) & (df_cal["_F"].dt.month == mes)].sort_values("_F")
        dias_con_evento = set(df_mes["_F"].dt.day.tolist())

        filas_html = ""
        for semana in calendar.monthcalendar(anio, mes):
            celdas = ""
            for d in semana:
                if d == 0:
                    celdas += "<td></td>"
                    continue
                estilo = "text-align:center;padding:3px 0;font-size:12px;color:#E0E0E0;"
                if d in dias_con_evento:
                    estilo += "background:#00E5FF;color:#000;font-weight:bold;border-radius:4px;"
                if (anio, mes, d) == (hoy.year, hoy.month, hoy.day):
                    estilo += "outline:2px solid #39FF14;border-radius:4px;"
                celdas += f"<td style='{estilo}'>{d}</td>"
            filas_html += f"<tr>{celdas}</tr>"
        cab = "".join(f"<th style='font-size:11px;color:#A0A5B5;text-align:center;'>{x}</th>" for x in ["L", "M", "M", "J", "V", "S", "D"])
        st.markdown(f"<table style='width:100%;border-collapse:separate;border-spacing:2px;'><tr>{cab}</tr>{filas_html}</table>", unsafe_allow_html=True)

        st.markdown("**📌 Eventos del mes**")
        if df_mes.empty:
            st.caption("Sin eventos este mes.")
        for idx_e, ev in df_mes.iterrows():
            id_e = str(ev.get("ID", ""))
            st.markdown(f"**{ev['_F'].strftime('%d/%m')}** · {ev.get('TITULO', '')}")
            if str(ev.get("DETALLE", "")).strip():
                st.caption(str(ev.get("DETALLE", "")))
            st.caption(f"Creó: {ev.get('CREADO_POR', '')} | Modificó: {ev.get('ULTIMA_MODIFICACION', '')}")
            c_ed, c_del = st.columns(2)
            if c_ed.button("✏️", key=f"cal_ed_{id_e}", use_container_width=True):
                st.session_state.cal_edit_id = id_e
                st.rerun()
            if c_del.button("🗑️", key=f"cal_del_{id_e}", use_container_width=True):
                if _cal_borrar(id_e):
                    if st.session_state.cal_edit_id == id_e:
                        st.session_state.cal_edit_id = None
                    st.rerun()
                else:
                    st.error("❌ No se pudo borrar el evento.")

        st.markdown("---")
        id_edit = st.session_state.cal_edit_id
        ev_edit = None
        if id_edit:
            m = df_cal[df_cal["ID"].astype(str) == str(id_edit)]
            if m.empty:
                st.session_state.cal_edit_id = None
                id_edit = None
            else:
                ev_edit = m.iloc[0]

        st.markdown("**✏️ EDITAR EVENTO**" if id_edit else "**➕ NUEVO EVENTO**")
        sufijo = str(id_edit or "nuevo")
        f_def = ev_edit["_F"].date() if (ev_edit is not None and pd.notna(ev_edit["_F"])) else hoy
        f_ev = st.date_input("FECHA:", value=f_def, format="DD/MM/YYYY", key=f"cal_f_{sufijo}")
        t_ev = st.text_input("TÍTULO:", value=str(ev_edit["TITULO"]) if ev_edit is not None else "", key=f"cal_t_{sufijo}")
        d_ev = st.text_area("DETALLE:", value=str(ev_edit["DETALLE"]) if ev_edit is not None else "", height=70, key=f"cal_d_{sufijo}")
        c_ok, c_can = st.columns(2)
        if c_ok.button("💾 GUARDAR", key=f"cal_ok_{sufijo}", use_container_width=True):
            if not t_ev.strip():
                st.warning("⚠️ Escribí un título.")
            elif _cal_guardar(f_ev, t_ev.strip(), d_ev.strip(), id_edit):
                st.session_state.cal_edit_id = None
                st.session_state.cal_anio, st.session_state.cal_mes = f_ev.year, f_ev.month
                st.rerun()
            else:
                st.error("❌ No se pudo guardar el evento.")
        if id_edit and c_can.button("✖️ CANCELAR", key=f"cal_can_{sufijo}", use_container_width=True):
            st.session_state.cal_edit_id = None
            st.rerun()

def enviar_alerta_automatica(emisor, objetivo, nombre_persona, supervisor_asignado):
    fecha = obtener_hora_argentina()
    remitente = str(nombre_persona).strip().upper() or emisor   # firma el mensaje quien activó el pánico (no "SISTEMA")
    asunto = f"ALERTA DE PÁNICO - {remitente} ({fecha[11:16]})"  # un hilo por pánico, así se puede leer y responder
    mensaje = f"🚨 ALERTA DE PÁNICO: {nombre_persona} - OBJ: {objetivo}"
    destinatarios = ["JEFE DE OPERACIONES", "GERENCIA", supervisor_asignado]
    filas = [[fecha, remitente, dest, asunto, mensaje, "PENDIENTE", "ROJA"]
             for dest in destinatarios if dest and dest != "MONITOREO" and dest != "N/A"]
    escribir_registros_nube("MENSAJERIA", filas)   # una sola llamada a Google para los 3 mensajes
    enviar_push_panico(remitente, objetivo, supervisor_asignado)

# --- ALARMA SONORA DE PÁNICO + AVISO PUSH (celular bloqueado) ---
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
    """Manda un aviso push (ntfy.sh) en segundo plano a cada topic <prefijo>-<topic>."""
    cuerpo = texto.encode("utf-8")
    def _enviar():
        for d in topics:
            try:
                requests.post(f"https://ntfy.sh/{prefijo}-{d}", data=cuerpo, timeout=5,
                              headers={"Title": "ALARMA DE PANICO", "Priority": "5", "Tags": "rotating_light"})
            except Exception as e:
                print(f"Error enviando push a {d}: {e}")
    import threading
    threading.Thread(target=_enviar, daemon=True).start()

def enviar_push_panico(remitente, objetivo, supervisor=""):
    """Aviso push por ntfy.sh (suena con el celular bloqueado). No hace nada hasta que se
    configure NTFY_PREFIJO en los secrets de Streamlit. Topics: <prefijo>-monitoreo,
    <prefijo>-jefe-de-operaciones y <prefijo>-<nombre-del-supervisor>."""
    prefijo = _prefijo_ntfy()
    if not prefijo:
        return
    sup = _slug_topic(supervisor) if str(supervisor).strip().upper() not in ("", "N/A", "MONITOREO") else ""
    _push_ntfy([d for d in ["monitoreo", "jefe-de-operaciones", sup] if d], f"PANICO: {remitente} - OBJ: {objetivo}", prefijo)

@st.cache_resource(show_spinner=False)
def _recordatorios_panico():
    return {}

def recordar_push_panicos_sin_leer(cada_seg=60, max_veces=15):
    """Se ejecuta desde la sesión de Monitoreo: mientras el supervisor no marque leído el mensaje de pánico,
    repite el aviso push a su celular cada 'cada_seg' segundos (hasta 'max_veces' y durante 30 minutos)."""
    import time
    prefijo = _prefijo_ntfy()
    if not prefijo:
        return
    df = leer_matriz_nube("MENSAJERIA")
    if df.empty or not {'ASUNTO', 'DESTINATARIO', 'REMITENTE', 'MENSAJE'} <= set(df.columns):
        return
    asunto = col_texto(df, 'ASUNTO').str.strip().str.upper()
    dest = col_texto(df, 'DESTINATARIO').str.strip().str.upper()
    sel = asunto.str.startswith("ALERTA DE PÁNICO") & ~dest.isin(["JEFE DE OPERACIONES", "GERENCIA", "MONITOREO"])
    if not sel.any():
        return
    ahora = datetime.strptime(obtener_hora_argentina(), "%Y-%m-%d %H:%M:%S")
    estado = _recordatorios_panico()
    for _, r in df[sel].iterrows():
        try:
            f = datetime.strptime(str(r.iloc[0])[:19], "%Y-%m-%d %H:%M:%S")
        except Exception:
            continue
        if (ahora - f).total_seconds() > 1800:
            continue
        d = str(r['DESTINATARIO']).strip().upper()
        if 'LEIDO_POR' in df.columns and d in [x.strip().upper() for x in str(r['LEIDO_POR']).split(";")]:
            continue
        clave = (str(r.iloc[0]), str(r['REMITENTE']), d)
        if clave not in estado:          # el primer aviso ya salió al apretar el pánico
            estado[clave] = (1, time.time())
            continue
        n, ult = estado[clave]
        if n >= max_veces or time.time() - ult < cada_seg:
            continue
        _push_ntfy([_slug_topic(d)], f"SIN LEER ({n}): PANICO {r['REMITENTE']} - {r['MENSAJE']}", prefijo)
        estado[clave] = (n + 1, time.time())

HORAS_ALARMA_PANICO = 6  # un pánico sin atender deja de sonar pasadas estas horas

# Motor de la sirena: vive en la ventana principal del navegador (no dentro del cartel), así no se corta
# cuando Streamlit redibuja el cartel. El cartel solo le dice "sonar" o "callar" y le avisa que sigue vivo.
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
  // Si el cartel desaparece (cierre de sesión, otra pantalla), la sirena se apaga sola a los 30 s
  W.setInterval(function(){ if (A.on && Date.now() - A.hb > 30000) A.stop(); }, 2000);
  ["click", "touchstart", "pointerdown", "keydown"].forEach(function(n){
    W.document.addEventListener(n, A.unlock, {passive: true});
  });
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
    """Pánicos que cada usuario ya marcó como ENTERADO (en memoria del servidor)."""
    return set()

def _panicos_para(rol, usuario):
    """Pánicos sin atender que le corresponden a este rol: lista de (fecha, vigilador, objetivo, clave).
    Se arma con la hoja ALERTAS (pánicos PENDIENTES), igual que Monitoreo:
    - MONITOREO: todos, hasta que se finalicen.
    - SUPERVISOR: los de sus objetivos (no el propio).
    - JEFE DE OPERACIONES: todos los de vigiladores y supervisores.
    Para SUPERVISOR / JEFE se descartan los que ya marcó ENTERADO o cuyo mensaje ya leyó.
    Devuelve None si no se pudo leer la hoja (para conservar el último estado conocido)."""
    df = leer_matriz_nube("ALERTAS")
    if df.empty:
        return None
    yo = _remitente_mensajeria()
    monitoreo = (rol == "MONITOREO")
    limite = (datetime.strptime(obtener_hora_argentina(), "%Y-%m-%d %H:%M:%S")
              - pd.Timedelta(hours=HORAS_ALARMA_PANICO)).strftime("%Y-%m-%d %H:%M:%S")
    enterados = _panicos_enterados()
    leidos = []   # (vigilador, fecha) de mensajes de pánico que este usuario ya leyó
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

def _asunto_panico(vigilador):
    """Asunto del hilo del último mensaje de pánico de ese vigilador (para responder dentro del mismo hilo)."""
    msgs = leer_matriz_nube("MENSAJERIA")
    if not msgs.empty and {'ASUNTO', 'REMITENTE'} <= set(msgs.columns):
        a = col_texto(msgs, 'ASUNTO').str.strip()
        m = a.str.upper().str.startswith("ALERTA DE PÁNICO") & (col_texto(msgs, 'REMITENTE').str.strip().str.upper() == vigilador)
        if m.any():
            return str(a[m].iloc[-1])
    return f"ALERTA DE PÁNICO - {vigilador}"

def alarma_panico_sonora(rol, usuario, solo_cartel=False):
    """Sirena + cartel rojo mientras haya un pánico que le corresponda a este rol (se revisa cada 5 s).
    - MONITOREO: suena hasta que se finalice el pánico. No se puede silenciar.
    - SUPERVISOR / JEFE DE OPERACIONES (panel lateral): suena hasta que toquen ENTERADO (o lean el mensaje).
    - GERENCIA: no recibe sirena.
    - solo_cartel=True: solo el cartel rojo (sin sonido ni botones), para la pantalla principal.
    Mientras no hay pánicos, el panel muestra "alarma lista" y un botón para activar el sonido del navegador."""
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
            if monitoreo:
                try:
                    recordar_push_panicos_sin_leer()   # repite el push al celular del supervisor hasta que lo lea
                except Exception as e:
                    print(f"Error en recordatorios push: {e}")
        except Exception as e:
            print(f"Error en alarma de pánico: {e}")
            pend = st.session_state.get("_pan_ult_" + rol, [])

        detalle = " · ".join(f"{p[1]} @ {p[2]}" for p in pend[:3])
        if len(pend) > 3:
            detalle += f" · +{len(pend) - 3} más"

        if solo_cartel:
            if pend:
                st.error(f"🚨 PÁNICO SIN ATENDER ({len(pend)}): {detalle}. Tocá ✔️ ENTERADO en el panel lateral (☰ arriba a la izquierda).")
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
                try:   # además marca como leídos los mensajes de pánico de esos vigiladores
                    msgs = leer_matriz_nube("MENSAJERIA")
                    sin = _mensajes_sin_leer(msgs)
                    if not sin.empty and 'ASUNTO' in sin.columns:
                        sin = sin[col_texto(sin, 'ASUNTO').str.strip().str.upper().str.startswith("ALERTA DE PÁNICO")]
                        if not sin.empty:
                            marcar_mensajes_leidos(list(sin.index))
                except Exception as e:
                    print(f"Error marcando mensajes de pánico como leídos: {e}")
                st.rerun()
            ultimo = pend[-1]
            with st.expander(f"✍️ RESPONDER A {ultimo[1]}"):
                with st.form(key=f"form_resp_pan_{rol}", clear_on_submit=True):
                    txt_resp = st.text_input("Escribí tu respuesta:")
                    if st.form_submit_button("✉️ ENVIAR RESPUESTA"):
                        if txt_resp.strip():
                            escribir_registro_nube("MENSAJERIA", [obtener_hora_argentina(), _remitente_mensajeria(), ultimo[1],
                                                                 _asunto_panico(ultimo[1]), txt_resp.strip().upper(), "PENDIENTE", "ROJA"])
                            st.session_state.mensaje_enviado = "RESPUESTA"
                            st.session_state.mensaje_enviado_grav = "ROJA"
                            st.rerun()
                        else:
                            st.warning("⚠️ Escribí la respuesta antes de enviar.")

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
    if(r&&r.data){
      pausa=true;bip();
      var texto=r.data;
      var listo=function(g){
        enviar("streamlit:setComponentValue",{value:{texto:texto,lat:g?g.latitude:null,lon:g?g.longitude:null,acc:g?g.accuracy:null,ts:Date.now()},dataType:"json"});
        setTimeout(function(){pausa=false;},3000);
      };
      var GL=null;
      try{GL=(window.parent.navigator&&window.parent.navigator.geolocation)||navigator.geolocation;}catch(e){GL=navigator.geolocation;}
      if(GL){GL.getCurrentPosition(function(p){listo(p.coords);},function(){listo(null);},{enableHighAccuracy:true,timeout:8000,maximumAge:0});}
      else{listo(null);}
    }
  },120);
}).catch(function(){m.textContent="No se pudo abrir la cámara. Revisá el permiso del navegador.";});
</script></body></html>"""

def visor_qr(key):
    return _declarar_visor_qr("v7")(key=key, default=None)

def texto_qr(lectura):
    """El visor ahora devuelve {texto, lat, lon, acc, ts}. Esta función devuelve solo el texto del QR."""
    if isinstance(lectura, dict):
        return str(lectura.get("texto", "")).strip()
    return str(lectura or "").strip()

@st.cache_resource(show_spinner=False)
def _qr_validator():
    import wlnqr
    cli = None
    try:
        from supabase import create_client
        cli = create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    except Exception as e:
        print(f"Supabase no disponible: {e}")
    return wlnqr.QRValidator(cli)

def validar_presencia_scan(lectura, calle, altura, localidad, radio_m=150):
    """Para el supervisor: el GPS tomado al escanear tiene que estar en el objetivo."""
    if not isinstance(lectura, dict) or lectura.get("lat") is None:
        return False, "No se pudo tomar tu GPS al escanear. Activá la ubicación y volvé a intentar."
    destino = geocodificar_direccion(calle, altura, localidad)
    if not destino:
        return False, "No se pudo ubicar el objetivo en el mapa. Revisá calle, altura y localidad."
    d = _km(float(lectura["lat"]), float(lectura["lon"]), destino[0], destino[1]) * 1000
    prec = float(lectura.get("acc") or 0)
    margen = radio_m + (0 if destino[2] else 250)
    if d - prec > margen:
        return False, f"Estás a {d:.0f} m del objetivo (máximo {margen} m). Escaneo rechazado."
    if d > margen:
        return False, "Señal GPS débil. Esperá unos segundos y reintentá."
    return True, f"Presencia verificada (~{d:.0f} m)."

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
<button id="b">🔊 ACTIVAR AVISO SONORO</button>
<p id="e"></p><p id="w"></p><p id="h"></p></div>
<script>
function enviar(t,d){window.parent.postMessage(Object.assign({isStreamlitMessage:true,type:t},d),"*");}
enviar("streamlit:componentReady",{apiVersion:1});
function altura(){enviar("streamlit:setFrameHeight",{height:Math.max(document.getElementById("panel").offsetHeight+8,120)});}
altura();window.addEventListener("resize",altura);

var P=window.parent, PD=P.document, ctx=null, wl=null;
var ESPERA_MIN=2;
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
    // Campanita suave pero clara: dos notas ("ding-dong") que se apagan solas, una sola vez (~1,6 s)
    var t=ctx.currentTime+0.05;
    [[880,0],[660,0.4]].forEach(function(n){
      var o=ctx.createOscillator(), g=ctx.createGain(), t0=t+n[1];
      o.type="triangle"; o.frequency.value=n[0];
      g.gain.setValueAtTime(0.0001,t0);
      g.gain.exponentialRampToValueAtTime(0.35,t0+0.03);
      g.gain.exponentialRampToValueAtTime(0.0001,t0+1.1);
      o.connect(g); g.connect(ctx.destination);
      o.start(t0); o.stop(t0+1.15);
    });
    if(navigator.vibrate) navigator.vibrate(150);
  }catch(e){}
}

function hoy(){var d=new Date();return d.getFullYear()+"-"+(d.getMonth()+1)+"-"+d.getDate();}
function llave(h){return "aion_rec_"+clave+"_"+hoy()+"_"+h;}
function respuestaDe(h){try{return localStorage.getItem(llave(h));}catch(e){return null;}}
function marcar(h,r){try{localStorage.setItem(llave(h),r);}catch(e){}}
function ahoraHecho(h){try{return localStorage.getItem(llave(h)+"_ahora")==="1";}catch(e){return false;}}
function marcarAhora(h){try{localStorage.setItem(llave(h)+"_ahora","1");}catch(e){}}
function horaVista(h){try{return localStorage.getItem(llave(h)+"_hv")==="1";}catch(e){return false;}}
function marcarHoraVista(h){try{localStorage.setItem(llave(h)+"_hv","1");}catch(e){}}
function avisoVisto(h){try{return localStorage.getItem(llave(h)+"_visto")==="1";}catch(e){return false;}}
function marcarVisto(h){try{localStorage.setItem(llave(h)+"_visto","1");}catch(e){}}
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

// Aviso previo / recorrida pendiente: pregunta SÍ / NO
function mostrar(hora){
  if(PD.getElementById("aion_modal_rec")) return;
  pendiente=hora; tipoModal="aviso";
  if(hora!=="PRUEBA") marcarVisto(hora);
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
}

// A la hora exacta (si dijo SÍ): recordatorio de que empieza la recorrida
function mostrarHora(hora){
  if(PD.getElementById("aion_modal_rec")) return;
  pendiente=hora; tipoModal="hora";
  marcarHoraVista(hora);
  crearModal(
    '<h2 style="color:#39FF14;margin:0 0 10px;font-size:20px">🚶 ¡Es hora de la recorrida!</h2>'+
    '<p style="font-size:16px;margin:0 0 16px;line-height:1.4">Ronda de las <b>'+hora+' hs</b>.<br>Recorré el objetivo y escaneá el QR de cada punto de control.</p>'+
    '<p style="font-size:12px;color:#FFD600;margin:0 0 12px">Confirmá en '+ESPERA_MIN+' min o la recorrida se bloquea y tendrás que justificarla.</p>'+
    '<button id="aion_ent" style="background:#39FF14;color:#000;border:none;padding:12px 26px;font-weight:bold;font-size:15px;border-radius:8px;width:100%">ENTENDIDO, INICIO</button>',
    "#39FF14");
  PD.getElementById("aion_ent").onclick=function(){marcarAhora(hora);cerrar();};
  campana();
}

// Si no confirmó el aviso de la hora: la recorrida queda bloqueada hasta que justifique
function mostrarBloqueo(hora){
  if(PD.getElementById("aion_modal_rec")) return;
  pendiente=hora; tipoModal="bloqueo";
  crearModal(
    '<h2 style="color:#FF5252;margin:0 0 10px;font-size:20px">⛔ Recorrida bloqueada</h2>'+
    '<p style="font-size:15px;margin:0 0 14px;line-height:1.4">No confirmaste el aviso de la recorrida de las <b>'+hora+' hs</b>.<br>Esa recorrida quedó bloqueada. <b>Justificá por qué no la realizaste.</b></p>'+
    '<select id="aion_sel_b" style="width:100%;padding:10px;border-radius:6px;font-size:14px;margin-bottom:8px">'+
    '<option>No escuché el aviso</option><option>Atendiendo una novedad en el objetivo</option><option>Atendiendo una visita o ingreso</option>'+
    '<option>Falta de personal</option><option>Problema de salud</option><option>Otro</option></select>'+
    '<input id="aion_txt_b" placeholder="Detalle (obligatorio)" style="width:100%;box-sizing:border-box;padding:10px;border-radius:6px;font-size:14px;margin-bottom:8px">'+
    '<p id="aion_err_b" style="color:#FF5252;font-size:12px;margin:0 0 8px;display:none">Escribí el detalle para poder enviar.</p>'+
    '<button id="aion_env_b" style="background:#FF5252;color:#fff;border:none;padding:12px;font-weight:bold;font-size:14px;border-radius:8px;width:100%">ENVIAR JUSTIFICACIÓN</button>',
    "#FF5252");
  PD.getElementById("aion_env_b").onclick=function(){
    var mot=PD.getElementById("aion_sel_b").value;
    var det=PD.getElementById("aion_txt_b").value.trim();
    if(det.length<3){PD.getElementById("aion_err_b").style.display="block";return;}
    responder(hora,"NO","SIN CONFIRMAR AVISO - "+mot+" - "+det);
  };
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
      return;
    }
    // Dijo SÍ, no confirmó el cartel de la hora y pasó el plazo: se bloquea la recorrida
    if(respuestaDe(h)==="SI" && !ahoraHecho(h) && m<=-ESPERA_MIN){
      if(modal && tipoModal==="bloqueo") return;
      if(modal) cerrar();
      mostrarBloqueo(h); return;
    }
  }
  if(modal) return;
  for(i=0;i<horarios.length;i++){
    h=horarios[i]; m=minutosHasta(h); r=respuestaDe(h);
    if(r==="SI" && m<=0 && m>-ESPERA_MIN && !ahoraHecho(h) && !horaVista(h)){mostrarHora(h);return;}
    if(r===null && !avisoVisto(h) && m<=5 && m>-30){mostrar(h);return;}
  }
},1000);
</script></body></html>"""


@st.cache_resource(show_spinner=False)
def _declarar_alerta_recorrida(version="v6"):
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
    evento = _declarar_alerta_recorrida("v6")(horarios=horarios, clave=obj_u, key=f"alerta_rec_{obj_u}", default=None)
    if evento and evento.get("id") != st.session_state.get("ultimo_evento_alerta"):
        st.session_state.ultimo_evento_alerta = evento.get("id")
        if registrar_respuesta_recorrida(obj_u, nombre, dni, evento):
            if evento.get("respuesta") == "SI":
                st.toast("✅ Respuesta registrada. ¡Buena recorrida!", icon="✅")
            else:
                st.toast("📝 Motivo registrado.", icon="📝")


def _fila_recorrido(base, lat, lon):
    """Arma la fila de REGISTRO RECORRIDOS según los encabezados reales de la hoja: LATITUD y LONGITUD van en
    la columna donde estén esos títulos (la que sea). Las 7 primeras posiciones conservan el orden de siempre."""
    def _num(v):
        try:
            return round(float(v), 6)
        except Exception:
            return ""
    try:
        cols = [str(c).strip().upper() for c in leer_matriz_nube("REGISTRO RECORRIDOS").columns]
    except Exception:
        cols = []
    if "LATITUD" not in cols or "LONGITUD" not in cols:
        return list(base) + [_num(lat), _num(lon)]
    fila = []
    for i, c in enumerate(cols):
        if c == "LATITUD":
            fila.append(_num(lat))
        elif c == "LONGITUD":
            fila.append(_num(lon))
        elif i < len(base):
            fila.append(base[i])
        else:
            fila.append("")
    return fila

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
    saltadas = _rondas_justificadas_hoy(obj_u, dni, horarios_previstos_lista, hoy)
    while ronda in saltadas:
        ronda += 1
    st.session_state[key_ronda] = ronda

    marcados = set()
    if not df_hoy.empty:
        df_ronda = df_hoy[pd.to_numeric(df_hoy['RONDA'], errors='coerce') == ronda]
        marcados = set(col_texto(df_ronda, 'PUNTO').str.strip().str.upper())

    c_r1, c_r2 = st.columns(2)
    c_r1.metric("🔁 RONDA", ronda)
    c_r2.metric("✅ PUNTOS", f"{len(marcados)} / {len(lista_puntos)}")
    if ronda <= len(horarios_previstos_lista):
        st.caption(f"🕒 Esta ronda corresponde al horario de las {horarios_previstos_lista[ronda - 1]} hs.")
    for n_s in sorted(saltadas):
        if n_s <= len(horarios_previstos_lista):
            st.caption(f"⛔ Ronda de las {horarios_previstos_lista[n_s - 1]} hs: no realizada ({saltadas[n_s] or 'sin motivo'}).")
    st.progress(min(1.0, len(marcados) / len(lista_puntos)))

    siguiente = next((p for p in lista_puntos if p not in marcados), None)
    for p in lista_puntos:
        st.write(("✅ " if p in marcados else ("➡️ " if p == siguiente else "🔒 ")) + p)

    if st.session_state.get("msg_recorrido"):
        st.success(st.session_state.msg_recorrido)

    # Ronda completa: no se escanea más
    if siguiente is None:
        st.success("🏁 ¡Ronda completa! Ya no se puede escanear en esta ronda.")
        hay_mas = (not horarios_previstos_lista) or ronda < len(horarios_previstos_lista)
        if hay_mas:
            if st.button("🔁 INICIAR NUEVA RONDA", use_container_width=True, key=f"btn_nueva_ronda_{obj_u}"):
                st.session_state[key_ronda] = ronda + 1
                st.session_state.msg_recorrido = ""
                st.session_state.pop("resultado_qr", None)
                st.rerun()
        else:
            st.info("Completaste todas las rondas programadas de hoy.")
        return

    # Datos para validar
    ultima = None
    if not df_hoy.empty:
        _dr = df_hoy[pd.to_numeric(df_hoy['RONDA'], errors='coerce') == ronda]
        if not _dr.empty:
            try:
                ultima = pd.to_datetime(_dr.iloc[-1]['FECHA_HORA']).to_pydatetime()
            except Exception:
                ultima = None

    def _cb_fraude(tipo, detalle, ctx):
        import time as _t
        clave_f = (tipo, ctx["id_punto"])
        vistos = st.session_state.setdefault("_fraude_ult", {})
        if vistos.get(clave_f, 0) > _t.time() - 120:      # no repetir el mismo aviso en 2 minutos
            return
        vistos[clave_f] = _t.time()
        fecha = obtener_hora_argentina()
        sup = ""
        df_objetivos = cargar_objetivos()
        if not df_objetivos.empty:
            _m = df_objetivos[col_texto(df_objetivos, 'OBJETIVO').str.strip().str.upper() == obj_u]
            if not _m.empty:
                sup = str(_m['SUPERVISOR'].iloc[0]).strip().upper()
        quien = str(nombre).strip().upper()
        asunto = f"ALERTA DE FRAUDE QR - {quien} ({fecha[11:16]})"
        texto = f"🚩 POSIBLE FRAUDE QR ({tipo}): {quien} - OBJ: {obj_u} - PUNTO: {ctx['id_punto']}. {detalle}"
        destinos = [d for d in ["JEFE DE OPERACIONES", "GERENCIA", sup] if d and d not in ("N/A", "MONITOREO")]
        escribir_registros_nube("MENSAJERIA", [[fecha, quien, d, asunto, texto, "PENDIENTE", "ROJA"] for d in destinos])
        escribir_registro_nube("ALERTAS", [fecha, quien, "FRAUDE QR", "REGISTRADO", obj_u, sup])
        pref = _prefijo_ntfy()
        if pref:
            _push_ntfy([d for d in ["monitoreo", "jefe-de-operaciones", _slug_topic(sup) if sup else ""] if d],
                       f"FRAUDE QR: {quien} - {obj_u} - {ctx['id_punto']} - {tipo}", pref)

    st.info(f"➡️ Próximo punto a escanear: **{siguiente}**")
    st.markdown("""
        <div style="border: 1px solid #00E5FF; border-radius: 6px; padding: 6px; text-align: center; margin: 2px 0; background: rgba(0, 229, 255, 0.05);">
            <span style="font-family: 'Orbitron', sans-serif; color: #00E5FF; font-size: 12px; font-weight: bold;">📷 ESCANEÁ EL QR DEL PUNTO DE CONTROL</span>
        </div>
    """, unsafe_allow_html=True)

    lectura = visor_qr(key=f"scan_rec_{obj_u}_{ronda}_{len(marcados)}")

    # Se procesa UNA sola vez cada lectura (evita alertas repetidas en cada recarga)
    if isinstance(lectura, dict) and lectura.get("ts") != st.session_state.get("_qr_ts_rec"):
        st.session_state["_qr_ts_rec"] = lectura.get("ts")
        st.session_state.pop("resultado_qr", None)
        txt = texto_qr(lectura)
        partes = {}
        for fragmento in txt.split("|"):
            if ":" in fragmento:
                k, v = fragmento.split(":", 1)
                partes[k.strip().upper()] = v.strip().upper()
        obj_qr, pto_qr = partes.get("OBJ", ""), partes.get("PTO", "")

        if not txt.upper().startswith("AION-RECORRIDO"):
            st.session_state.resultado_qr = "❌ Ese QR no es de un punto de recorrido."
        elif obj_qr != obj_u:
            st.session_state.resultado_qr = "❌ Ese punto no pertenece a este objetivo."
        else:
            fb = None   # ubicación del objetivo, por si el punto no tiene ubicación propia
            _df_o = cargar_objetivos()
            _fo = _df_o[col_texto(_df_o, 'OBJETIVO').str.strip().str.upper() == obj_u] if not _df_o.empty else pd.DataFrame()
            if not _fo.empty:
                _g = geocodificar_direccion(_fo.iloc[0].get('CALLE', ''), _fo.iloc[0].get('ALTURA', ''), _fo.iloc[0].get('LOCALIDAD', ''))
                if _g:
                    fb = (_g[0], _g[1], 150 if _g[2] else 400)
            res = _qr_validator().validar_marcacion(
                legajo=st.session_state.get("legajo_vigilador", "S/L"), objetivo=obj_u, id_punto=pto_qr,
                orden_puntos=lista_puntos, marcados=list(marcados),
                lat_usuario=lectura.get("lat"), lon_usuario=lectura.get("lon"), precision_m=lectura.get("acc"),
                ultima_marca=ultima, ronda=ronda, fallback=fb, on_fraude=_cb_fraude)
            if res["valido"]:
                if escribir_registro_nube("REGISTRO RECORRIDOS", _fila_recorrido(
                    [obtener_hora_argentina(), obj_u, pto_qr, str(nombre).strip().upper(), str(dni), ronda, "OK"],
                    lectura.get("lat"), lectura.get("lon")
                )):
                    st.session_state.msg_recorrido = f"✅ Marcado: {pto_qr}"
                    st.rerun()
            else:
                pref = "🚩 ESCANEO RECHAZADO Y REPORTADO AL SUPERVISOR. " if res["fraude"] else "⛔ "
                st.session_state.resultado_qr = pref + res["mensaje"]

    if st.session_state.get("resultado_qr"):
        st.error(st.session_state.resultado_qr)

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
        kc = f"{key_prefix}_cal_{obj_u}_{str(pto_sel).strip().upper()}".replace(" ", "_")
        st.caption("📍 Parate frente al QR físico y tocá el botón para guardar dónde está este punto.")
        if st.button("📍 GUARDAR UBICACIÓN DE ESTE PUNTO", key=kc + "_btn", use_container_width=True):
            st.session_state[kc + "_n"] = st.session_state.get(kc + "_n", 0) + 1
            st.session_state[kc] = st.session_state[kc + "_n"]
        if st.session_state.get(kc):
            loc = get_geolocation(component_key=f"{kc}_{st.session_state[kc]}")
            if loc and "coords" in loc:
                c = loc["coords"]
                if float(c.get("accuracy") or 999) > 30:
                    st.warning(f"⚠️ GPS poco preciso (±{float(c.get('accuracy') or 0):.0f} m). Salí a un lugar abierto y probá de nuevo.")
                elif _qr_validator().guardar_ubicacion_punto(obj_u, str(pto_sel).strip().upper(), c["latitude"], c["longitude"]):
                    st.success("✅ Ubicación del punto guardada.")
                else:
                    st.error("❌ No se pudo guardar. Revisá la conexión con Supabase.")
                st.session_state[kc] = 0
            else:
                st.info("📡 Obteniendo ubicación…")

def tabla_recorridas_vigiladores(objs_sup):
    """SEGUIMIENTO DE RONDAS: una fila por fecha / objetivo / vigilador / ronda, con íconos como el seguimiento del panel lateral:
    ✅ hecho (con horario) · ⚠️ no lo hizo · 🚩 fraude (incluye querer saltear un punto) · ⏳ pendiente.
    Los fraudes QR se leen de los mensajes de alerta (los mismos que usa el panel lateral)."""
    objs = [str(o).strip().upper() for o in objs_sup]
    if len(objs) == 0:
        return pd.DataFrame()
    df_r = leer_matriz_nube("REGISTRO RECORRIDOS")
    if not df_r.empty and {'FECHA_HORA', 'OBJETIVO', 'PUNTO', 'RONDA'} <= set(df_r.columns):
        df_r = df_r.loc[:, ~df_r.columns.duplicated()].copy()
        df_r['_OBJ'] = col_texto(df_r, 'OBJETIVO').str.strip().str.upper()
        df_r = df_r[df_r['_OBJ'].isin(objs)].copy()
    else:
        df_r = pd.DataFrame()

    if not df_r.empty:
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
    if not df_r.empty:
        df_r['_FECHA'] = df_r['_FH'].dt.strftime('%Y-%m-%d')

    total_ptos, previsto, planificado, horarios_obj = {}, {}, {}, {}
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
                    horarios_obj[o] = hs
        dfp = df_p.copy()
        dfp['_P'] = col_texto(dfp, 'PUNTO').str.strip().str.upper()
        if 'ORDEN' in dfp.columns:
            dfp['_ORD'] = pd.to_numeric(dfp['ORDEN'], errors='coerce')
            dfp = dfp.sort_values('_ORD')
        for o, g in dfp.groupby('_OBJ', sort=False):
            planificado[o] = g['_P'].drop_duplicates().tolist()

    # Fraudes QR (de todos los días) de los objetivos pedidos
    eventos = [e for e in _eventos_fraude_qr(None) if e["obj"] in objs]

    rondas_idx = {}   # (fecha, obj, vig) -> [(ronda, primer escaneo, último escaneo)]
    if not df_r.empty:
        for (fecha, obj, vig, ronda), g in df_r.groupby(['_FECHA', '_OBJ', '_VIG', '_RONDA']):
            rondas_idx.setdefault((fecha, obj, vig), []).append((ronda, g['_FH'].min(), g['_FH'].max()))
    ev_por_ronda, huerfanos = {}, {}
    for e in eventos:
        k = (e["fh"].strftime('%Y-%m-%d'), e["obj"], e["vig"])
        lst = sorted(rondas_idx.get(k, []), key=lambda x: x[1])
        if not lst:
            huerfanos.setdefault(k, []).append(e)
            continue
        previas = [x for x in lst if x[1] <= e["fh"]]
        ronda = (previas[-1] if previas else lst[0])[0]
        ev_por_ronda.setdefault(k + (ronda,), []).append(e)

    hoy = obtener_hora_argentina().split(" ")[0]
    filas = []
    if not df_r.empty:
        for (fecha, obj, vig, ronda), g in df_r.groupby(['_FECHA', '_OBJ', '_VIG', '_RONDA']):
            k = (fecha, obj, vig)
            hechos = {row['_PTO']: row['_FH'] for _, row in g.sort_values('_FH').iterrows()}
            evs = ev_por_ronda.get(k + (ronda,), [])
            ev_pto = {}
            for e in evs:
                ev_pto.setdefault(e["pto"], e)
            puntos = list(planificado.get(obj, []))
            for p in list(hechos) + list(ev_pto):
                if p not in puntos:
                    puntos.append(p)
            es_actual = (fecha == hoy) and ronda == max(x[0] for x in rondas_idx[k])
            ult_idx = max([puntos.index(p) for p in hechos], default=-1)
            det, faltan = [], 0
            for i, p in enumerate(puntos):
                if p in hechos:
                    det.append(f"✅ {p} {hechos[p].strftime('%H:%M:%S')}" + (" 🚩" if p in ev_pto else ""))
                elif p in ev_pto:
                    det.append(f"🚩 {p} {ev_pto[p]['fh'].strftime('%H:%M:%S')}")
                elif (not es_actual) or i < ult_idx:
                    det.append(f"⚠️ {p} no realizado")
                    faltan += 1
                else:
                    det.append(f"⏳ {p}")
            marcados = g['_PTO'].nunique()
            total = total_ptos.get(obj, 0)
            completa = total > 0 and marcados >= total
            n_fr = len(evs)
            if n_fr:
                estado = "🚩 COMPLETA CON FRAUDE" if completa else "🚩 CON FRAUDE"
            elif completa:
                estado = "✅ COMPLETA"
            elif faltan or not es_actual:
                estado = "⚠️ CON FALTANTES"
            else:
                estado = "⏳ EN CURSO"
            filas.append({
                "FECHA": fecha,
                "OBJETIVO": obj,
                "VIGILADOR": vig,
                "RONDA": ronda,
                "HORARIO PREVISTO": previsto.get(obj, "15:00, 17:00, 19:00"),
                "INICIÓ": g['_FH'].min().strftime('%H:%M:%S'),
                "FINALIZÓ": g['_FH'].max().strftime('%H:%M:%S') if completa else "---",
                "PUNTOS": f"{marcados}/{total}" if total else str(marcados),
                "FRAUDE": f"🚩 SÍ ({n_fr})" if n_fr else "✅ NO",
                "ESTADO": estado,
                "DETALLE": " | ".join(det),
            })
    # Fraudes de un vigilador que no llegó a marcar ningún punto en esa fecha
    for (fecha, obj, vig), evs in huerfanos.items():
        total = total_ptos.get(obj, 0)
        evs = sorted(evs, key=lambda x: x["fh"])
        filas.append({
            "FECHA": fecha, "OBJETIVO": obj, "VIGILADOR": vig, "RONDA": "---",
            "HORARIO PREVISTO": previsto.get(obj, "15:00, 17:00, 19:00"),
            "INICIÓ": evs[0]["fh"].strftime('%H:%M:%S'), "FINALIZÓ": "---",
            "PUNTOS": f"0/{total}" if total else "0",
            "FRAUDE": f"🚩 SÍ ({len(evs)})", "ESTADO": "🚩 CON FRAUDE",
            "DETALLE": " | ".join(f"🚩 {e['pto']} {e['fh'].strftime('%H:%M:%S')}" for e in evs),
        })
    # --- Rondas programadas que NADIE empezó (sin escaneos), con la justificación si el vigilador respondió NO ---
    TOLERANCIA_RONDA_MIN = 60   # minutos de gracia después del horario previsto antes de marcar la ronda como no realizada
    ahora = pd.Timestamp(obtener_hora_argentina())
    justif = {}   # (fecha, objetivo, HH:MM) -> (vigilador, motivo)
    df_resp = leer_matriz_nube("RESPUESTAS RECORRIDAS")
    if not df_resp.empty and {'FECHA_HORA', 'OBJETIVO', 'DNI', 'HORARIO', 'RESPUESTA'} <= set(df_resp.columns):
        mapa_dni = {}
        df_pad2 = leer_matriz_nube("PADRON VIGILADORES")
        if not df_pad2.empty and {'DNI', 'NOMBRE'} <= set(df_pad2.columns):
            mapa_dni = dict(zip(col_texto(df_pad2, 'DNI').str.replace(r'\D', '', regex=True),
                                col_texto(df_pad2, 'NOMBRE').str.strip().str.upper()))
        for _, f in df_resp.iterrows():
            if str(f['RESPUESTA']).strip().upper() != "NO":
                continue
            o_j = str(f['OBJETIVO']).strip().upper()
            hs_j = _horarios_unicos([f['HORARIO']])
            if o_j not in objs or not hs_j:
                continue
            dni_j = re.sub(r'\D', '', str(f['DNI']))
            justif[(str(f['FECHA_HORA'])[:10], o_j, hs_j[0])] = (mapa_dni.get(dni_j, dni_j or "---"), str(f.get('MOTIVO', '')).strip())
    hechas = {(k[0], k[1], x[0]) for k, lst in rondas_idx.items() for x in lst}
    for obj in objs:
        hs_o = horarios_obj.get(obj, [])
        fechas_obj = [k[0] for k in rondas_idx if k[1] == obj] + [k[0] for k in justif if k[1] == obj]
        if not hs_o or not fechas_obj:
            continue
        first_fh = df_r[df_r['_OBJ'] == obj]['_FH'].min() if (not df_r.empty and (df_r['_OBJ'] == obj).any()) else None
        inicio = max(pd.Timestamp(min(fechas_obj)), pd.Timestamp(hoy) - pd.Timedelta(days=30))
        for fecha_ts in pd.date_range(inicio, pd.Timestamp(hoy)):
            fecha = fecha_ts.strftime('%Y-%m-%d')
            for r, hm in enumerate(hs_o, start=1):
                if (fecha, obj, r) in hechas:
                    continue
                prog = pd.Timestamp(f"{fecha} {hm}:00")
                if prog + pd.Timedelta(minutes=TOLERANCIA_RONDA_MIN) > ahora:
                    continue
                jv = justif.get((fecha, obj, hm))
                if first_fh is not None and prog < first_fh and jv is None:
                    continue   # antes de que el objetivo empezara a usar el sistema
                total = total_ptos.get(obj, 0)
                filas.append({
                    "FECHA": fecha, "OBJETIVO": obj, "VIGILADOR": jv[0] if jv else "---", "RONDA": r,
                    "HORARIO PREVISTO": hm, "INICIÓ": "---", "FINALIZÓ": "---",
                    "PUNTOS": f"0/{total}" if total else "0",
                    "FRAUDE": "✅ NO",
                    "ESTADO": "⚠️ NO REALIZADA (JUSTIFICADA)" if jv else "⚠️ NO REALIZADA",
                    "DETALLE": f"⚠️ Ronda de las {hm} hs no realizada" + ((" · motivo: " + (jv[1] or "sin motivo")) if jv else " · sin escaneos ni justificación"),
                    "_K": hm + ":00",
                })
    if not filas:
        return pd.DataFrame()
    for f in filas:
        f.setdefault("_K", f["INICIÓ"] if f["INICIÓ"] != "---" else "")
    df_out = pd.DataFrame(filas)
    df_out = df_out.sort_values(['FECHA', '_K'], ascending=False).drop(columns=['_K']).reset_index(drop=True)
    return df_out

def mostrar_tabla_rondas(df):
    """Seguimiento de rondas como tabla HTML: el texto se acomoda al ancho de la pantalla (sin mover de costado) y el
    DETALLE va debajo de cada fila, con cada punto en su recuadro de color (✅ hecho · 🚩 fraude · ⚠️ no lo hizo · ⏳ pendiente)."""
    if df is None or df.empty:
        return
    esc = lambda v: _html_msg.escape(str(v))
    def _color(txt):
        t = str(txt)
        for ico, c in (("🚩", "#FF1744"), ("⚠️", "#FF9100"), ("⏳", "#94A3B8"), ("✅", "#00E676")):
            if ico in t:
                return c
        return "#E2E8F0"
    cols = [c for c in df.columns if c != "DETALLE"]
    th = "".join(f"<th style='text-align:left;padding:4px 6px;color:#00E5FF;font-size:10px;border-bottom:2px solid #00E5FF;'>{esc(c)}</th>" for c in cols)
    filas = []
    for _, r in df.iterrows():
        tds = "".join(
            f"<td style='padding:4px 6px 2px;font-size:12px;vertical-align:top;color:{_color(r[c]) if c in ('FRAUDE', 'ESTADO') else '#E2E8F0'};'>{esc(r[c])}</td>"
            for c in cols)
        chips = "".join(
            f"<span style='display:inline-block;border-left:4px solid {_color(p)};background:rgba(255,255,255,0.06);padding:2px 8px;margin:2px 4px 2px 0;border-radius:3px;font-size:12px;color:#E2E8F0;'>{esc(p.strip())}</span>"
            for p in str(r.get("DETALLE", "")).split(" | ") if p.strip())
        filas.append(f"<tr>{tds}</tr><tr><td colspan='{len(cols)}' style='padding:0 6px 8px;border-bottom:1px solid #334155;'>{chips}</td></tr>")
    html = ("<div style='overflow-x:auto;'><table style='width:100%;border-collapse:collapse;'>"
            f"<thead><tr>{th}</tr></thead><tbody>{''.join(filas)}</tbody></table></div>")
    st.markdown(html, unsafe_allow_html=True)

def _rec_para_pdf(df):
    """El PDF (Helvetica) no dibuja emojis: se pasan a palabras."""
    if df is None or df.empty:
        return df
    d = df.copy()
    for c in d.columns:
        s = d[c].astype(str)
        if c == "DETALLE":
            s = (s.str.replace("✅", "OK", regex=False).str.replace("🚩", "FRAUDE", regex=False)
                  .str.replace("⚠️", "FALTÓ", regex=False).str.replace("⏳", "PEND.", regex=False))
        else:
            for ico in ("✅", "🚩", "⚠️", "⏳"):
                s = s.str.replace(ico, "", regex=False)
        d[c] = s.str.strip()
    return d

# --- 3.C PLANIFICACIÓN POR MES (JEFE DE OPERACIONES / GERENCIA) ---
TIPOS_NOVEDAD_PERSONAL = {
    "LICENCIA":   ("L",   "#EF5350", "#FFF"),
    "ART":        ("ART", "#FF9800", "#000"),
    "VACACIONES": ("V",   "#AB47BC", "#FFF"),
    "AUSENTE":    ("A",   "#F4D03F", "#000"),
    "FRANCO":     ("F",   "#5C9BD5", "#FFF"),
    "PRÉSTAMO":   ("P",   "#26A69A", "#FFF"),
}
PRIORIDAD_NOVEDAD = ["LICENCIA", "ART", "VACACIONES", "AUSENTE", "FRANCO", "PRÉSTAMO"]
# El préstamo no se carga como novedad suelta: sale de la hoja PRESTAMOS VIGILADORES.
TIPOS_REGISTRABLES = [t for t in TIPOS_NOVEDAD_PERSONAL if t != "PRÉSTAMO"]
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
                             "DESDE", "HASTA", "OBSERVACION", "REGISTRADO_POR", "MODIFICADO_POR", "FECHA_MODIFICACION"])
        hoja.append_row([obtener_hora_argentina(), str(dni), vigilador, objetivo, supervisor, tipo,
                         desde.strftime("%Y-%m-%d"), hasta.strftime("%Y-%m-%d"),
                         str(obs).strip().upper(), str(st.session_state.get("user_sel", "")).upper()])
        st.cache_data.clear()
        notificar_novedad("📝 " + str(st.session_state.get("user_sel", "")).upper() + " registró " + str(tipo) + " a " + str(vigilador) +
                          " (" + str(objetivo) + ") del " + desde.strftime("%d/%m/%Y") + " al " + hasta.strftime("%d/%m/%Y") +
                          (" · " + str(obs).strip().upper() if str(obs).strip() else ""))
        return True
    except Exception as e:
        print(f"Error registrando novedad de personal: {e}")
        return False

def planificacion_mes(periodo):
    anio, mes = map(int, periodo.split("-"))
    primero = pd.Timestamp(anio, mes, 1)
    ultimo = pd.Timestamp(anio, mes, calendar.monthrange(anio, mes)[1])
    nov = cargar_novedades_personal()
    prest = _prestamos_como_novedades()
    if not prest.empty:
        nov = prest if nov.empty else pd.concat([nov, prest], ignore_index=True)
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
                "DÍAS AUSENTE": dias["AUSENTE"], "DÍAS FRANCO": dias["FRANCO"], "DÍAS PRÉSTAMO": dias["PRÉSTAMO"],
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

# --- GESTIÓN DE NOVEDADES DEL PERSONAL (VISTA SUPERVISOR) ---
def _hoja_novedades_personal():
    gc = conectar_google()
    if not gc:
        return None
    try:
        return gc.open_by_key(ID_MAESTRO_DB).worksheet("NOVEDADES PERSONAL")
    except Exception:
        return None

def _ubicar_fila_novedad(hoja, fecha_reg, dni):
    """Busca en vivo la fila de la novedad (por fecha de registro + DNI) para no tocar una fila equivocada.
    Devuelve (nº de fila, encabezados, valores de la fila)."""
    filas = hoja.get_all_values()
    if not filas:
        return None, [], []
    enc = [str(h).strip().upper() for h in filas[0]]
    if "FECHA_REGISTRO" not in enc or "DNI" not in enc:
        return None, enc, []
    i_f, i_d = enc.index("FECHA_REGISTRO"), enc.index("DNI")
    for n, f in enumerate(filas[1:], start=2):
        if len(f) > max(i_f, i_d) and f[i_f].strip() == str(fecha_reg).strip() and re.sub(r"\D", "", f[i_d]) == str(dni):
            return n, enc, f
    return None, enc, []

def _asegurar_columna(hoja, enc, nombre):
    """Devuelve el nº de columna (desde 1); si no existe la crea al final con ese encabezado."""
    if nombre in enc:
        return enc.index(nombre) + 1
    col = len(enc) + 1
    if hoja.col_count < col:
        hoja.add_cols(col - hoja.col_count)
    hoja.update_cell(1, col, nombre)
    enc.append(nombre)
    return col

COLS_HISTORIAL_NOVEDADES = ["FECHA_HORA", "USUARIO", "ACCION", "VIGILADOR", "DNI", "OBJETIVO",
                            "TIPO_ANTES", "DESDE_ANTES", "HASTA_ANTES", "OBS_ANTES",
                            "TIPO_DESPUES", "DESDE_DESPUES", "HASTA_DESPUES", "OBS_DESPUES"]

def _registrar_historial_novedad(accion, antes, despues=None):
    """Deja constancia de quién, cuándo y qué cambió (hoja HISTORIAL NOVEDADES PERSONAL)."""
    try:
        gc = conectar_google()
        if not gc:
            return
        sh = gc.open_by_key(ID_MAESTRO_DB)
        try:
            hoja = sh.worksheet("HISTORIAL NOVEDADES PERSONAL")
        except Exception:
            hoja = sh.add_worksheet(title="HISTORIAL NOVEDADES PERSONAL", rows="500", cols=str(len(COLS_HISTORIAL_NOVEDADES)))
            hoja.append_row(COLS_HISTORIAL_NOVEDADES, value_input_option="RAW")
        d = despues or {}
        hoja.append_row([
            obtener_hora_argentina(), str(st.session_state.get("user_sel", "")).upper(), accion,
            antes.get("VIGILADOR", ""), re.sub(r"\D", "", str(antes.get("DNI", ""))), antes.get("OBJETIVO", ""),
            antes.get("TIPO", ""), antes.get("DESDE", ""), antes.get("HASTA", ""), antes.get("OBSERVACION", ""),
            d.get("TIPO", ""), d.get("DESDE", ""), d.get("HASTA", ""), d.get("OBSERVACION", ""),
        ], value_input_option="RAW")
        st.cache_data.clear()
    except Exception as e:
        print(f"Error guardando historial de novedades: {e}")

def modificar_novedad_personal(fecha_reg, dni, tipo, desde, hasta, obs):
    try:
        hoja = _hoja_novedades_personal()
        if hoja is None:
            return False
        fila, enc, vals = _ubicar_fila_novedad(hoja, fecha_reg, dni)
        if not fila:
            return False
        antes = {c: (vals[i] if i < len(vals) else "") for i, c in enumerate(enc)}
        nuevos = {"TIPO": tipo, "DESDE": desde.strftime("%Y-%m-%d"), "HASTA": hasta.strftime("%Y-%m-%d"),
                  "OBSERVACION": str(obs).strip().upper()}
        for col, val in nuevos.items():
            if col in enc:
                hoja.update_cell(fila, enc.index(col) + 1, val)
        c_por = _asegurar_columna(hoja, enc, "MODIFICADO_POR")
        c_fec = _asegurar_columna(hoja, enc, "FECHA_MODIFICACION")
        hoja.update_cell(fila, c_por, str(st.session_state.get("user_sel", "")).upper())
        hoja.update_cell(fila, c_fec, obtener_hora_argentina())
        _registrar_historial_novedad("MODIFICACIÓN", antes, nuevos)
        notificar_novedad("✏️ " + str(st.session_state.get("user_sel", "")).upper() + " modificó la novedad de " + str(antes.get("VIGILADOR", "")) +
                          " (" + str(antes.get("OBJETIVO", "")) + "): era " + str(antes.get("TIPO", "")) + ", ahora " + str(tipo) +
                          " del " + desde.strftime("%d/%m/%Y") + " al " + hasta.strftime("%d/%m/%Y"))
        st.cache_data.clear()
        return True
    except Exception as e:
        print(f"Error modificando novedad de personal: {e}")
        return False

def eliminar_novedad_personal(fecha_reg, dni):
    try:
        hoja = _hoja_novedades_personal()
        if hoja is None:
            return False
        fila, enc, vals = _ubicar_fila_novedad(hoja, fecha_reg, dni)
        if not fila:
            return False
        antes = {c: (vals[i] if i < len(vals) else "") for i, c in enumerate(enc)}
        _registrar_historial_novedad("ELIMINACIÓN", antes)
        hoja.delete_rows(fila)
        notificar_novedad("🗑️ " + str(st.session_state.get("user_sel", "")).upper() + " eliminó la novedad " + str(antes.get("TIPO", "")) + " de " +
                          str(antes.get("VIGILADOR", "")) + " (" + str(antes.get("OBJETIVO", "")) + ")")
        st.cache_data.clear()
        return True
    except Exception as e:
        print(f"Error eliminando novedad de personal: {e}")
        return False

def _fmt_fecha_hora(v):
    s = str(v).strip()
    if not s or s.upper() == "NAN":
        return ""
    d = pd.to_datetime(s, dayfirst=not re.match(r"\d{4}-", s), errors="coerce")
    return s if pd.isna(d) else d.strftime("%d/%m/%Y %H:%M")

def _fmt_fecha(v):
    s = str(v).strip()
    if not s or s.upper() == "NAN":
        return ""
    d = pd.to_datetime(s, dayfirst=not re.match(r"\d{4}-", s), errors="coerce")
    return s if pd.isna(d) else d.strftime("%d/%m/%Y")

def _tarjeta_novedad_html(n):
    import html as _h
    letra, bg, fg = TIPOS_NOVEDAD_PERSONAL.get(n["_TIPO"], ("?", "#555555", "#FFFFFF"))
    dias = int((n["_HASTA"] - n["_DESDE"]).days) + 1
    obs = str(n.get("OBSERVACION", "") or "").strip()
    obs_html = ('<div style="font-size:11px;color:#9AA3B5;margin-top:3px;">📝 ' + _h.escape(obs) + '</div>') if obs else ""
    reg_por = str(n.get("REGISTRADO_POR", "") or "").strip()
    reg_fec = _fmt_fecha_hora(n.get("FECHA_REGISTRO", ""))
    mod_por = str(n.get("MODIFICADO_POR", "") or "").strip()
    mod_fec = _fmt_fecha_hora(n.get("FECHA_MODIFICACION", ""))
    pie = ""
    if reg_por or reg_fec:
        pie += ('<div style="font-size:10px;color:#6B7487;margin-top:4px;">📌 Registrada por ' + _h.escape(reg_por or "---") +
                (' · ' + reg_fec if reg_fec else '') + '</div>')
    if mod_por or mod_fec:
        pie += ('<div style="font-size:10px;color:#E0A458;margin-top:2px;">✏️ Modificada por ' + _h.escape(mod_por or "---") +
                (' · ' + mod_fec if mod_fec else '') + '</div>')
    return ('<div style="background:rgba(22,27,34,.55);border:1px solid #2A3040;border-left:4px solid ' + bg + ';border-radius:8px;padding:8px 12px;margin:6px 0 2px;">'
            '<div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:6px;">'
            '<span style="font-size:12px;color:#E2E8F0;">' + _h.escape(str(n.get("VIGILADOR", ""))) + '</span>'
            '<span style="background:' + bg + ';color:' + fg + ';padding:1px 8px;border-radius:8px;font-size:10.5px;font-weight:bold;">' + letra + ' · ' + _h.escape(str(n["_TIPO"])) + '</span></div>'
            '<div style="font-size:11px;color:#7C869A;margin-top:3px;">🎯 ' + _h.escape(str(n.get("OBJETIVO", ""))) +
            ' · 📅 ' + n["_DESDE"].strftime("%d/%m/%Y") + ' al ' + n["_HASTA"].strftime("%d/%m/%Y") +
            ' (' + str(dias) + (' día' if dias == 1 else ' días') + ')</div>' + obs_html + pie + '</div>')

def _historial_cambios_html(dnis, limite=30):
    """Últimos cambios (modificaciones y eliminaciones) sobre las novedades de estos vigiladores."""
    import html as _h
    h = leer_matriz_nube("HISTORIAL NOVEDADES PERSONAL")
    if h.empty or "DNI" not in h.columns:
        return ""
    h = h[h["DNI"].astype(str).str.replace(r"\D", "", regex=True).isin(dnis)]
    if h.empty:
        return ""
    def resumen(r, sufijo):
        tipo = str(r.get("TIPO_" + sufijo, "") or "").strip()
        if not tipo:
            return ""
        txt = tipo + " · " + _fmt_fecha(r.get("DESDE_" + sufijo, "")) + " al " + _fmt_fecha(r.get("HASTA_" + sufijo, ""))
        obs = str(r.get("OBS_" + sufijo, "") or "").strip()
        return txt + (" · " + obs if obs else "")
    out = ""
    for _, r in h.iloc[::-1].head(limite).iterrows():
        elim = str(r.get("ACCION", "")).upper().startswith("ELIM")
        icono, color = ("🗑️", "#D9776F") if elim else ("✏️", "#E0A458")
        antes, despues = resumen(r, "ANTES"), resumen(r, "DESPUES")
        detalle = '<div style="font-size:11px;color:#9AA3B5;margin-top:3px;">Antes: ' + _h.escape(antes) + '</div>'
        if elim:
            detalle = '<div style="font-size:11px;color:#9AA3B5;margin-top:3px;">Se eliminó: ' + _h.escape(antes) + '</div>'
        elif despues:
            detalle += '<div style="font-size:11px;color:#CBD5E1;margin-top:2px;">Después: ' + _h.escape(despues) + '</div>'
        out += ('<div style="background:rgba(22,27,34,.55);border:1px solid #2A3040;border-left:4px solid ' + color + ';border-radius:8px;padding:8px 12px;margin:6px 0;">'
                '<div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:6px;">'
                '<span style="font-size:12px;color:#E2E8F0;">' + icono + ' ' + _h.escape(str(r.get("VIGILADOR", ""))) + '</span>'
                '<span style="font-size:10.5px;color:#7C869A;">' + _fmt_fecha_hora(r.get("FECHA_HORA", "")) + '</span></div>'
                '<div style="font-size:11px;color:' + color + ';margin-top:2px;">' + ("Eliminada" if elim else "Modificada") +
                ' por <b>' + _h.escape(str(r.get("USUARIO", "") or "---")) + '</b></div>' + detalle + '</div>')
    return out

# --- DATOS DEL VIGILADOR (objetivo y baja) DESDE LA VISTA SUPERVISOR ---
COLS_HISTORIAL_VIG = ["FECHA_HORA", "USUARIO", "SUPERVISOR", "ACCION", "VIGILADOR", "DNI",
                      "OBJETIVO_ANTES", "OBJETIVO_DESPUES", "MOTIVO"]

def _hoja_padron():
    gc = conectar_google()
    if not gc:
        return None
    try:
        return gc.open_by_key(ID_MAESTRO_DB).worksheet("PADRON VIGILADORES")
    except Exception:
        return None

def _ubicar_fila_padron(hoja, dni):
    """Fila del padrón por DNI (si hay más de una, prefiere la ACTIVA). Devuelve (fila, encabezados, valores)."""
    filas = hoja.get_all_values()
    if not filas:
        return None, [], []
    enc = [str(h).strip().upper() for h in filas[0]]
    if "DNI" not in enc:
        return None, enc, []
    i_d = enc.index("DNI")
    i_e = enc.index("ESTADO") if "ESTADO" in enc else None
    hallados = [(n, f) for n, f in enumerate(filas[1:], start=2) if len(f) > i_d and re.sub(r"\D", "", f[i_d]) == str(dni)]
    if not hallados:
        return None, enc, []
    for n, f in hallados:
        if i_e is not None and len(f) > i_e and f[i_e].strip().upper() == "ACTIVO":
            return n, enc, f
    return hallados[0][0], enc, hallados[0][1]

def _registrar_historial_vigilador(accion, sup, dni, nombre, obj_antes, obj_despues="", motivo=""):
    """Deja constancia de quién, cuándo y qué cambió (hoja HISTORIAL VIGILADORES)."""
    try:
        gc = conectar_google()
        if not gc:
            return
        sh = gc.open_by_key(ID_MAESTRO_DB)
        try:
            hoja = sh.worksheet("HISTORIAL VIGILADORES")
        except Exception:
            hoja = sh.add_worksheet(title="HISTORIAL VIGILADORES", rows="500", cols=str(len(COLS_HISTORIAL_VIG)))
            hoja.append_row(COLS_HISTORIAL_VIG, value_input_option="RAW")
        hoja.append_row([obtener_hora_argentina(), str(st.session_state.get("user_sel", "")).upper(), str(sup).upper(),
                         accion, nombre, re.sub(r"\D", "", str(dni)), obj_antes, obj_despues, str(motivo).strip().upper()],
                        value_input_option="RAW")
        st.cache_data.clear()
    except Exception as e:
        print(f"Error guardando historial de vigiladores: {e}")

def cambiar_objetivo_vigilador(sup, dni, nuevo_obj, objetivos_permitidos):
    """El supervisor mueve a un vigilador suyo a otro objetivo suyo."""
    try:
        nuevo_obj = str(nuevo_obj).strip().upper()
        hoja = _hoja_padron()
        if hoja is None or nuevo_obj not in objetivos_permitidos:
            return False
        fila, enc, vals = _ubicar_fila_padron(hoja, dni)
        if not fila or "OBJETIVO" not in enc:
            return False
        i_o = enc.index("OBJETIVO")
        obj_antes = vals[i_o].strip().upper() if len(vals) > i_o else ""
        if obj_antes not in objetivos_permitidos:
            return False
        nombre = vals[enc.index("NOMBRE")].strip().upper() if "NOMBRE" in enc and len(vals) > enc.index("NOMBRE") else ""
        hoja.update_cell(fila, i_o + 1, nuevo_obj)
        _registrar_historial_vigilador("CAMBIO DE OBJETIVO", sup, dni, nombre, obj_antes, nuevo_obj)
        notificar_novedad("🔁 " + str(sup) + " cambió de objetivo a " + nombre + ": de " + obj_antes + " a " + nuevo_obj)
        st.cache_data.clear()
        return True
    except Exception as e:
        print(f"Error cambiando objetivo del vigilador: {e}")
        return False

def dar_baja_vigilador(sup, dni, motivo, objetivos_permitidos):
    """El supervisor da de baja a un vigilador suyo (ESTADO = BAJA), con motivo."""
    try:
        hoja = _hoja_padron()
        if hoja is None:
            return False
        fila, enc, vals = _ubicar_fila_padron(hoja, dni)
        if not fila or "ESTADO" not in enc or "OBJETIVO" not in enc:
            return False
        i_o = enc.index("OBJETIVO")
        obj_antes = vals[i_o].strip().upper() if len(vals) > i_o else ""
        if obj_antes not in objetivos_permitidos:
            return False
        nombre = vals[enc.index("NOMBRE")].strip().upper() if "NOMBRE" in enc and len(vals) > enc.index("NOMBRE") else ""
        hoja.update_cell(fila, enc.index("ESTADO") + 1, "BAJA")
        _registrar_historial_vigilador("BAJA", sup, dni, nombre, obj_antes, "", motivo)
        notificar_novedad("🔴 " + str(sup) + " dio de baja a " + nombre + " (" + obj_antes + ")" +
                          (" · Motivo: " + str(motivo).strip().upper() if str(motivo).strip() else ""))
        st.cache_data.clear()
        return True
    except Exception as e:
        print(f"Error dando de baja al vigilador: {e}")
        return False

def _historial_vigiladores_html(sup, limite=30):
    """Cambios de objetivo, bajas y préstamos hechos por este supervisor."""
    import html as _h
    h = leer_matriz_nube("HISTORIAL VIGILADORES")
    if h.empty or "SUPERVISOR" not in h.columns:
        return ""
    h = h[h["SUPERVISOR"].astype(str).str.strip().str.upper() == str(sup).strip().upper()]
    if h.empty:
        return ""
    out = ""
    for _, r in h.iloc[::-1].head(limite).iterrows():
        accion = str(r.get("ACCION", "")).strip().upper()
        antes = str(r.get("OBJETIVO_ANTES", "") or "").strip()
        despues = str(r.get("OBJETIVO_DESPUES", "") or "").strip()
        motivo = str(r.get("MOTIVO", "") or "").strip()
        extra = (' · Motivo: ' + _h.escape(motivo)) if motivo else ''
        if accion.startswith("BAJA"):
            icono, color = "🔴", "#D9776F"
            detalle = 'Dado de baja del objetivo ' + _h.escape(antes) + extra
        elif accion.startswith("PRÉSTAMO") or accion.startswith("PRESTAMO"):
            icono, color = "🤝", "#26A69A"
            detalle = 'Prestado a ' + _h.escape(despues) + ' (desde ' + _h.escape(antes) + ')' + extra
        elif accion.startswith("ANULACIÓN") or accion.startswith("ANULACION"):
            icono, color = "↩️", "#7C869A"
            detalle = 'Préstamo anulado: ' + _h.escape(despues) + ' (de ' + _h.escape(antes) + ')'
        else:
            icono, color = "🔁", "#5BC0CE"
            detalle = 'Pasó de ' + _h.escape(antes) + ' a ' + _h.escape(despues)
        out += ('<div style="background:rgba(22,27,34,.55);border:1px solid #2A3040;border-left:4px solid ' + color + ';border-radius:8px;padding:8px 12px;margin:6px 0;">'
                '<div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:6px;">'
                '<span style="font-size:12px;color:#E2E8F0;">' + icono + ' ' + _h.escape(str(r.get("VIGILADOR", ""))) + '</span>'
                '<span style="font-size:10.5px;color:#7C869A;">' + _fmt_fecha_hora(r.get("FECHA_HORA", "")) + '</span></div>'
                '<div style="font-size:11px;color:' + color + ';margin-top:2px;">' + _h.escape(accion.capitalize()) +
                ' por <b>' + _h.escape(str(r.get("USUARIO", "") or "---")) + '</b></div>'
                '<div style="font-size:11px;color:#9AA3B5;margin-top:3px;">' + detalle + '</div></div>')
    return out

# --- AVISOS AUTOMÁTICOS (Jefe de Operaciones y Gerencia reciben todo) ---
DESTINOS_AVISO_PERSONAL = ["JEFE DE OPERACIONES", "GERENCIA"]

def notificar_novedad(mensaje, extra=None):
    """Aviso en la campanita (barra lateral) de Jefe de Operaciones, Gerencia y, si corresponde, otros usuarios."""
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
        destinos = []
        for d in list(DESTINOS_AVISO_PERSONAL) + [str(x) for x in (extra or [])]:
            d = d.strip().upper()
            if d and d not in destinos:
                destinos.append(d)
        fecha = obtener_hora_argentina()
        hoja.append_rows([[fecha, d, str(mensaje), "PENDIENTE"] for d in destinos], value_input_option="RAW", table_range="A1")
        st.cache_data.clear()
    except Exception as e:
        print(f"Error enviando aviso de novedad: {e}")
def marcar_notificaciones_leidas(indices):
    """Marca como LEÍDO varias notificaciones de una sola vez (indices = posición en el DataFrame)."""
    try:
        gc = conectar_google()
        if not gc or not len(indices):
            return False
        hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet("NOTIFICACIONES_SUPERVISORES")
        hoja.batch_update([{"range": "D" + str(int(i) + 2), "values": [["LEÍDO"]]} for i in indices])
        st.cache_data.clear()
        return True
    except Exception as e:
        print(f"Error marcando notificaciones: {e}")
        return False

# --- PRÉSTAMOS DE VIGILADORES ENTRE SUPERVISORES ---
COLS_PRESTAMOS = ["FECHA_REGISTRO", "DNI", "VIGILADOR", "OBJETIVO_ORIGEN", "SUPERVISOR_ORIGEN", "SUPERVISOR_DESTINO",
                  "OBJETIVO_DESTINO", "DESDE", "HASTA", "MOTIVO", "REGISTRADO_POR", "ESTADO", "ANULADO_POR", "FECHA_ANULACION"]

def _hoja_prestamos(crear=False):
    gc = conectar_google()
    if not gc:
        return None
    sh = gc.open_by_key(ID_MAESTRO_DB)
    try:
        return sh.worksheet("PRESTAMOS VIGILADORES")
    except Exception:
        if not crear:
            return None
        hoja = sh.add_worksheet(title="PRESTAMOS VIGILADORES", rows="300", cols=str(len(COLS_PRESTAMOS)))
        hoja.append_row(COLS_PRESTAMOS, value_input_option="RAW")
        return hoja

def cargar_prestamos():
    df = leer_matriz_nube("PRESTAMOS VIGILADORES")
    if df.empty or not {"DNI", "DESDE", "HASTA", "ESTADO", "SUPERVISOR_ORIGEN", "SUPERVISOR_DESTINO"} <= set(df.columns):
        return pd.DataFrame()
    df = df.copy()
    df["_DNI"] = col_texto(df, "DNI").str.replace(r"\D", "", regex=True)
    df["_ORIG"] = col_texto(df, "SUPERVISOR_ORIGEN").str.strip().str.upper()
    df["_DEST"] = col_texto(df, "SUPERVISOR_DESTINO").str.strip().str.upper()
    df["_ESTADO"] = col_texto(df, "ESTADO").str.strip().str.upper()
    df["_DESDE"] = df["DESDE"].map(_fecha_a_dt)
    df["_HASTA"] = df["HASTA"].map(_fecha_a_dt)
    return df.dropna(subset=["_DESDE", "_HASTA"]).reset_index(drop=True)

def _prestamos_como_novedades():
    """Los préstamos no anulados, con el mismo formato que las novedades, para pintarlos en la grilla (P)."""
    pr = cargar_prestamos()
    if pr.empty:
        return pd.DataFrame()
    pr = pr[pr["_ESTADO"] != "ANULADO"]
    if pr.empty:
        return pd.DataFrame()
    return pd.DataFrame({"_DNI": pr["_DNI"].values, "_TIPO": "PRÉSTAMO", "_DESDE": pr["_DESDE"].values, "_HASTA": pr["_HASTA"].values})

def registrar_prestamo(dni, vigilador, obj_origen, sup_origen, sup_destino, obj_destino, desde, hasta, motivo):
    try:
        hoja = _hoja_prestamos(crear=True)
        if hoja is None:
            return False
        hoja.append_row([obtener_hora_argentina(), str(dni), vigilador, obj_origen, sup_origen, sup_destino, obj_destino,
                         desde.strftime("%Y-%m-%d"), hasta.strftime("%Y-%m-%d"), str(motivo).strip().upper(),
                         str(st.session_state.get("user_sel", "")).upper(), "VIGENTE", "", ""], value_input_option="RAW")
        destino_txt = sup_destino + ((" · " + obj_destino) if obj_destino else "")
        _registrar_historial_vigilador("PRÉSTAMO", sup_origen, dni, vigilador, obj_origen, destino_txt, motivo)
        notificar_novedad("🤝 " + str(sup_origen) + " prestó a " + str(vigilador) + " (" + str(obj_origen) + ") a " + destino_txt +
                          " del " + desde.strftime("%d/%m/%Y") + " al " + hasta.strftime("%d/%m/%Y") +
                          ((" · Motivo: " + str(motivo).strip().upper()) if str(motivo).strip() else ""), extra=[sup_destino])
        st.cache_data.clear()
        return True
    except Exception as e:
        print(f"Error registrando préstamo: {e}")
        return False

def anular_prestamo(fecha_reg, dni, sup):
    """Anula un préstamo vigente (solo lo puede hacer el supervisor que lo otorgó). Queda constancia de quién y cuándo."""
    try:
        hoja = _hoja_prestamos()
        if hoja is None:
            return False
        filas = hoja.get_all_values()
        if not filas:
            return False
        enc = [str(h).strip().upper() for h in filas[0]]
        if any(c not in enc for c in ("FECHA_REGISTRO", "DNI", "SUPERVISOR_ORIGEN", "ESTADO")):
            return False
        ix = {c: enc.index(c) for c in enc}
        def valor(f, c):
            return f[ix[c]].strip() if c in ix and len(f) > ix[c] else ""
        for n, f in enumerate(filas[1:], start=2):
            if (valor(f, "FECHA_REGISTRO") == str(fecha_reg).strip() and re.sub(r"\D", "", valor(f, "DNI")) == str(dni)
                    and valor(f, "SUPERVISOR_ORIGEN").upper() == str(sup).strip().upper() and valor(f, "ESTADO").upper() != "ANULADO"):
                hoja.update_cell(n, ix["ESTADO"] + 1, "ANULADO")
                c_por = _asegurar_columna(hoja, enc, "ANULADO_POR")
                c_fec = _asegurar_columna(hoja, enc, "FECHA_ANULACION")
                hoja.update_cell(n, c_por, str(st.session_state.get("user_sel", "")).upper())
                hoja.update_cell(n, c_fec, obtener_hora_argentina())
                vig, obj_o, dest, obj_d = valor(f, "VIGILADOR"), valor(f, "OBJETIVO_ORIGEN"), valor(f, "SUPERVISOR_DESTINO"), valor(f, "OBJETIVO_DESTINO")
                destino_txt = dest + ((" · " + obj_d) if obj_d else "")
                _registrar_historial_vigilador("ANULACIÓN DE PRÉSTAMO", sup, dni, vig, obj_o, destino_txt)
                notificar_novedad("↩️ " + str(sup) + " anuló el préstamo de " + vig + " (" + obj_o + ") a " + destino_txt, extra=[dest])
                st.cache_data.clear()
                return True
        return False
    except Exception as e:
        print(f"Error anulando préstamo: {e}")
        return False

def _tarjeta_prestamo_html(p, hoy):
    import html as _h
    if p["_ESTADO"] == "ANULADO":
        etiqueta, color = "ANULADO", "#7C869A"
    elif p["_HASTA"] < hoy:
        etiqueta, color = "FINALIZADO", "#7C869A"
    elif p["_DESDE"] > hoy:
        etiqueta, color = "PROGRAMADO", "#5BC0CE"
    else:
        etiqueta, color = "EN CURSO", "#26A69A"
    obj_o = str(p.get("OBJETIVO_ORIGEN", "") or "").strip()
    obj_d = str(p.get("OBJETIVO_DESTINO", "") or "").strip()
    motivo = str(p.get("MOTIVO", "") or "").strip()
    por = str(p.get("REGISTRADO_POR", "") or "").strip()
    fec = _fmt_fecha_hora(p.get("FECHA_REGISTRO", ""))
    anul = str(p.get("ANULADO_POR", "") or "").strip()
    fec_anul = _fmt_fecha_hora(p.get("FECHA_ANULACION", ""))
    dias = int((p["_HASTA"] - p["_DESDE"]).days) + 1
    pie = '<div style="font-size:10px;color:#6B7487;margin-top:4px;">📌 Registrado por ' + _h.escape(por or "---") + (' · ' + fec if fec else '') + '</div>'
    if anul or fec_anul:
        pie += '<div style="font-size:10px;color:#E0A458;margin-top:2px;">↩️ Anulado por ' + _h.escape(anul or "---") + (' · ' + fec_anul if fec_anul else '') + '</div>'
    return ('<div style="background:rgba(22,27,34,.55);border:1px solid #2A3040;border-left:4px solid ' + color + ';border-radius:8px;padding:8px 12px;margin:6px 0 2px;">'
            '<div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:6px;">'
            '<span style="font-size:12px;color:#E2E8F0;">🤝 ' + _h.escape(str(p.get("VIGILADOR", ""))) + '</span>'
            '<span style="border:1px solid ' + color + ';color:' + color + ';border-radius:8px;padding:0 8px;font-size:10px;">' + etiqueta + '</span></div>'
            '<div style="font-size:11px;color:#9AA3B5;margin-top:3px;">De <b style="color:#CBD5E1;">' + _h.escape(p["_ORIG"]) + '</b>' +
            (' (' + _h.escape(obj_o) + ')' if obj_o else '') + ' → <b style="color:#CBD5E1;">' + _h.escape(p["_DEST"]) + '</b>' +
            (' · ' + _h.escape(obj_d) if obj_d else '') + '</div>'
            '<div style="font-size:11px;color:#7C869A;margin-top:3px;">📅 ' + p["_DESDE"].strftime("%d/%m/%Y") + ' al ' + p["_HASTA"].strftime("%d/%m/%Y") +
            ' (' + str(dias) + (' día' if dias == 1 else ' días') + ')' + (' · 📝 ' + _h.escape(motivo) if motivo else '') + '</div>' + pie + '</div>')

def renderizar_personal_supervisor(sup, key_prefix="psup"):
    """Pantalla del supervisor: ve a sus vigiladores y registra, modifica o elimina sus novedades."""
    sup = str(sup).strip().upper()
    st.markdown("### 👥 MI PERSONAL")
    if st.session_state.get(f"{key_prefix}_msg"):
        st.success(st.session_state.pop(f"{key_prefix}_msg"))

    vig = vigiladores_de_supervisor(sup)
    if vig.empty:
        st.info("No tenés vigiladores activos a cargo en tus objetivos.")
        return
    dnis = set(vig["DNI"].tolist())
    hoy = datetime.now(pytz.timezone("America/Argentina/Buenos_Aires"))

    # --- Panorama gráfico del mes ---
    c1, c2 = st.columns(2)
    mes = int(c1.selectbox("MES:", list(range(1, 13)), index=hoy.month - 1,
                           format_func=lambda m: MESES_ES[m - 1], key=f"{key_prefix}_mes"))
    anio = int(c2.number_input("AÑO:", min_value=2024, max_value=2100, value=hoy.year, step=1, key=f"{key_prefix}_anio"))
    periodo = f"{anio}-{mes:02d}"
    pm = planificacion_mes(periodo).get(sup)
    if pm is not None and not pm.empty:
        st.markdown(f"**Mis vigiladores ({len(pm)}) · {MESES_ES[mes - 1]} {anio}**")
        st.markdown(leyenda_planificacion_html(), unsafe_allow_html=True)
        st.markdown(grilla_planificacion_html(pm, anio, mes), unsafe_allow_html=True)

    try:
        st.download_button("📥 DESCARGAR MI PERSONAL (PDF)", data=generar_pdf_mi_personal(sup, anio, mes),
                           file_name=f"mi_personal_{sup.replace(' ', '_')}_{periodo}.pdf", mime="application/pdf",
                           use_container_width=True, key=f"{key_prefix}_pdf")
    except Exception as e_pdf_mp:
        st.warning(f"No se pudo preparar el PDF de Mi personal: {e_pdf_mp}")

    # --- Registrar novedad ---
    st.markdown("---")
    etiquetas = {i: f"{r['VIGILADOR']} | {r['OBJETIVO']}" for i, r in vig.iterrows()}
    with st.expander("➕ REGISTRAR NOVEDAD DE PERSONAL", expanded=True):
        with st.form(key=f"{key_prefix}_form_nueva", clear_on_submit=True):
            idx = st.selectbox("VIGILADOR:", list(etiquetas.keys()), format_func=lambda k: etiquetas[k])
            tipo = st.selectbox("TIPO DE NOVEDAD:", TIPOS_REGISTRABLES)
            f1, f2 = st.columns(2)
            desde = f1.date_input("DESDE:", value=hoy.date())
            hasta = f2.date_input("HASTA:", value=hoy.date())
            obs = st.text_input("OBSERVACIÓN (opcional):")
            if st.form_submit_button("💾 REGISTRAR NOVEDAD", use_container_width=True):
                if hasta < desde:
                    st.warning("⚠️ La fecha HASTA no puede ser anterior a DESDE.")
                else:
                    r = vig.loc[idx]
                    if registrar_novedad_personal(r["DNI"], r["VIGILADOR"], r["OBJETIVO"], sup, tipo, desde, hasta, obs):
                        st.session_state[f"{key_prefix}_msg"] = f"✅ Registrado: {r['VIGILADOR']} - {tipo} ({desde} a {hasta})."
                        st.rerun()
                    else:
                        st.error("❌ No se pudo registrar. Revisá la conexión con Google Sheets.")

    # --- Datos del vigilador: cambiar objetivo / dar de baja ---
    df_o_sup = cargar_objetivos()
    mis_objs = []
    if not df_o_sup.empty and 'SUPERVISOR' in df_o_sup.columns:
        m_o = col_texto(df_o_sup, 'SUPERVISOR').str.strip().str.upper() == sup
        mis_objs = sorted(set(col_texto(df_o_sup, 'OBJETIVO').str.strip().str.upper()[m_o]) - {"", "NAN"})
    with st.expander("🧑‍✈️ DATOS DEL VIGILADOR (cambiar objetivo / dar de baja)"):
        idx_v = st.selectbox("VIGILADOR:", list(etiquetas.keys()), format_func=lambda k: etiquetas[k], key=f"{key_prefix}_dv_sel")
        rv = vig.loc[idx_v]
        dni_v = str(rv["DNI"])
        st.markdown('<div style="font-size:12px;color:#CBD5E1;margin:4px 0 8px;">🎯 Objetivo actual: <b>' + str(rv["OBJETIVO"]) + '</b></div>', unsafe_allow_html=True)

        st.markdown("**🔁 Cambiar de objetivo**")
        otros = [o for o in mis_objs if o != str(rv["OBJETIVO"]).strip().upper()]
        if otros:
            with st.form(key=f"{key_prefix}_form_obj_{dni_v}"):
                nuevo_obj = st.selectbox("NUEVO OBJETIVO (entre los tuyos):", otros)
                if st.form_submit_button("💾 CAMBIAR OBJETIVO", use_container_width=True):
                    if cambiar_objetivo_vigilador(sup, dni_v, nuevo_obj, mis_objs):
                        st.session_state[f"{key_prefix}_msg"] = f"✅ {rv['VIGILADOR']} pasó de {rv['OBJETIVO']} a {nuevo_obj}."
                        st.rerun()
                    else:
                        st.error("❌ No se pudo cambiar el objetivo. Revisá la conexión con Google Sheets.")
        else:
            st.caption("No tenés otro objetivo a cargo para mover a este vigilador.")

        st.markdown("**🤝 Prestar a otro supervisor**")
        otros_sups = [x for x in _supervisores_con_objetivos() if x != sup]
        if otros_sups:
            sup_dest = st.selectbox("SUPERVISOR QUE LO RECIBE:", otros_sups, key=f"{key_prefix}_prest_sup_{dni_v}")
            objs_dest = []
            if not df_o_sup.empty and 'SUPERVISOR' in df_o_sup.columns:
                m_d = col_texto(df_o_sup, 'SUPERVISOR').str.strip().str.upper() == sup_dest
                objs_dest = sorted(set(col_texto(df_o_sup, 'OBJETIVO').str.strip().str.upper()[m_d]) - {"", "NAN"})
            with st.form(key=f"{key_prefix}_form_prest_{dni_v}", clear_on_submit=True):
                obj_dest = st.selectbox("OBJETIVO DE DESTINO (opcional):", ["(SIN ESPECIFICAR)"] + objs_dest)
                p1, p2 = st.columns(2)
                p_desde = p1.date_input("DESDE:", value=hoy.date())
                p_hasta = p2.date_input("HASTA:", value=hoy.date())
                p_motivo = st.text_input("MOTIVO (opcional):")
                if st.form_submit_button("🤝 REGISTRAR PRÉSTAMO", use_container_width=True):
                    pr_ex = cargar_prestamos()
                    choca = (not pr_ex.empty) and bool(((pr_ex["_DNI"] == dni_v) & (pr_ex["_ESTADO"] != "ANULADO") &
                                                      (pr_ex["_DESDE"] <= pd.Timestamp(p_hasta)) & (pr_ex["_HASTA"] >= pd.Timestamp(p_desde))).any())
                    if p_hasta < p_desde:
                        st.warning("⚠️ La fecha HASTA no puede ser anterior a DESDE.")
                    elif choca:
                        st.warning("⚠️ Este vigilador ya tiene un préstamo en esas fechas. Anulá el anterior o cambiá las fechas.")
                    elif registrar_prestamo(dni_v, rv["VIGILADOR"], rv["OBJETIVO"], sup, sup_dest,
                                            "" if obj_dest == "(SIN ESPECIFICAR)" else obj_dest, p_desde, p_hasta, p_motivo):
                        st.session_state[f"{key_prefix}_msg"] = f"🤝 {rv['VIGILADOR']} fue prestado a {sup_dest} del {p_desde.strftime('%d/%m/%Y')} al {p_hasta.strftime('%d/%m/%Y')}."
                        st.rerun()
                    else:
                        st.error("❌ No se pudo registrar el préstamo. Revisá la conexión con Google Sheets.")
        else:
            st.caption("No hay otros supervisores con objetivos para prestarle el vigilador.")

        st.markdown("**🔴 Dar de baja**")
        motivo_baja = st.text_input("MOTIVO DE LA BAJA:", key=f"{key_prefix}_baja_motivo_{dni_v}")
        conf_baja = st.checkbox("Confirmo que quiero dar de baja a este vigilador", key=f"{key_prefix}_baja_conf_{dni_v}")
        if st.button("🔴 DAR DE BAJA AL VIGILADOR", key=f"{key_prefix}_baja_btn_{dni_v}",
                     disabled=not (conf_baja and motivo_baja.strip()), use_container_width=True):
            if dar_baja_vigilador(sup, dni_v, motivo_baja, mis_objs):
                st.session_state[f"{key_prefix}_msg"] = f"🔴 {rv['VIGILADOR']} fue dado de baja."
                st.rerun()
            else:
                st.error("❌ No se pudo dar de baja. Revisá la conexión con Google Sheets.")

    # --- Préstamos enviados y recibidos ---
    pr_all = cargar_prestamos()
    pr_mios = pr_all[(pr_all["_ORIG"] == sup) | (pr_all["_DEST"] == sup)] if not pr_all.empty else pd.DataFrame()
    with st.expander("🤝 PRÉSTAMOS DE VIGILADORES (enviados y recibidos)"):
        if pr_mios.empty:
            st.caption("Todavía no hay préstamos registrados.")
        else:
            hoy_ts = pd.Timestamp(hoy.year, hoy.month, hoy.day)
            pr_mios = pr_mios.sort_values("_DESDE", ascending=False)
            enviados = pr_mios[pr_mios["_ORIG"] == sup]
            recibidos = pr_mios[pr_mios["_DEST"] == sup]
            st.markdown("**Que yo presté**")
            if enviados.empty:
                st.caption("No prestaste vigiladores.")
            for k, (_, pr) in enumerate(enviados.iterrows()):
                st.markdown(_tarjeta_prestamo_html(pr, hoy_ts), unsafe_allow_html=True)
                if pr["_ESTADO"] != "ANULADO" and pr["_HASTA"] >= hoy_ts:
                    clave_p = key_prefix + "_pa_" + str(k) + "_" + re.sub(r"\W", "", str(pr.get("FECHA_REGISTRO", "")) + str(pr["_DNI"]))
                    conf_p = st.checkbox("Confirmo que quiero anular este préstamo", key=clave_p + "_conf")
                    if st.button("↩️ ANULAR PRÉSTAMO", key=clave_p + "_btn", disabled=not conf_p, use_container_width=True):
                        if anular_prestamo(str(pr.get("FECHA_REGISTRO", "")).strip(), str(pr["_DNI"]), sup):
                            st.session_state[f"{key_prefix}_msg"] = f"↩️ Préstamo anulado: {pr.get('VIGILADOR', '')}."
                            st.rerun()
                        else:
                            st.error("❌ No se pudo anular. Revisá la conexión o que el préstamo siga vigente.")
            st.markdown("**Que me prestaron**")
            if recibidos.empty:
                st.caption("No te prestaron vigiladores.")
            for _, pr in recibidos.iterrows():
                st.markdown(_tarjeta_prestamo_html(pr, hoy_ts), unsafe_allow_html=True)

    # --- Historial de cambios (quién y cuándo) ---
    with st.expander("🕘 HISTORIAL DE CAMBIOS (quién cambió qué y cuándo)"):
        hist_html = _historial_cambios_html(dnis)
        hist_vig_html = _historial_vigiladores_html(sup)
        if hist_html:
            st.markdown("**Novedades modificadas o eliminadas**")
            st.markdown(hist_html, unsafe_allow_html=True)
        if hist_vig_html:
            st.markdown("**Cambios de objetivo y bajas de vigiladores**")
            st.markdown(hist_vig_html, unsafe_allow_html=True)
        if not hist_html and not hist_vig_html:
            st.caption("Todavía no hay cambios registrados.")

    # --- Novedades registradas (modificar / eliminar) ---
    st.markdown("#### 🗂️ NOVEDADES REGISTRADAS")
    nov = cargar_novedades_personal()
    if nov.empty:
        st.info("Todavía no hay novedades registradas.")
        return
    nov = nov[nov["_DNI"].isin(dnis)].copy()
    f1, f2 = st.columns([2, 1])
    nombres = ["TODOS"] + sorted(set(vig["VIGILADOR"].tolist()))
    filtro_vig = f1.selectbox("VIGILADOR:", nombres, key=f"{key_prefix}_filtro_vig")
    ver_todo = f2.checkbox("Ver todo el historial", value=False, key=f"{key_prefix}_hist")
    if filtro_vig != "TODOS":
        dni_f = set(vig.loc[vig["VIGILADOR"] == filtro_vig, "DNI"].tolist())
        nov = nov[nov["_DNI"].isin(dni_f)]
    if not ver_todo:
        primero = pd.Timestamp(anio, mes, 1)
        ultimo = pd.Timestamp(anio, mes, calendar.monthrange(anio, mes)[1])
        nov = nov[(nov["_DESDE"] <= ultimo) & (nov["_HASTA"] >= primero)]
    nov = nov.sort_values("_DESDE", ascending=False)
    if nov.empty:
        st.info("No hay novedades para este filtro.")
        return

    tipos = list(TIPOS_REGISTRABLES)
    for k, (_, n) in enumerate(nov.iterrows()):
        st.markdown(_tarjeta_novedad_html(n), unsafe_allow_html=True)
        fecha_reg = str(n.get("FECHA_REGISTRO", "")).strip()
        dni = str(n["_DNI"])
        sufijo_clave = re.sub(r"\W", "", fecha_reg + dni)
        clave = key_prefix + "_" + str(k) + "_" + sufijo_clave
        with st.expander("✏️ Modificar o eliminar"):
            with st.form(key=f"{clave}_form"):
                m_tipo = st.selectbox("TIPO:", tipos, index=tipos.index(n["_TIPO"]) if n["_TIPO"] in tipos else 0)
                m1, m2 = st.columns(2)
                m_desde = m1.date_input("DESDE:", value=n["_DESDE"].date())
                m_hasta = m2.date_input("HASTA:", value=n["_HASTA"].date())
                m_obs = st.text_input("OBSERVACIÓN:", value=str(n.get("OBSERVACION", "")))
                if st.form_submit_button("💾 GUARDAR CAMBIOS", use_container_width=True):
                    if m_hasta < m_desde:
                        st.warning("⚠️ La fecha HASTA no puede ser anterior a DESDE.")
                    elif modificar_novedad_personal(fecha_reg, dni, m_tipo, m_desde, m_hasta, m_obs):
                        st.session_state[f"{key_prefix}_msg"] = f"✅ Modificado: {n.get('VIGILADOR', '')} - {m_tipo}."
                        st.rerun()
                    else:
                        st.error("❌ No se pudo modificar. Revisá la conexión o que la novedad siga existiendo.")
            confirmar = st.checkbox("Confirmo que quiero eliminar esta novedad", key=f"{clave}_conf")
            if st.button("🗑️ ELIMINAR NOVEDAD", key=f"{clave}_del", disabled=not confirmar, use_container_width=True):
                if eliminar_novedad_personal(fecha_reg, dni):
                    st.session_state[f"{key_prefix}_msg"] = f"🗑️ Eliminada: {n.get('VIGILADOR', '')} - {n['_TIPO']}."
                    st.rerun()
                else:
                    st.error("❌ No se pudo eliminar. Revisá la conexión o que la novedad siga existiendo.")


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
                "TURNOS DIURNOS": sum(1 for (_, t) in d["turnos"] if t == "D"),
                "TURNOS NOCTURNOS": sum(1 for (_, t) in d["turnos"] if t == "N"),
                "MÁX. DÍAS SEGUIDOS": max(corridas) if corridas else 0,
                "FRANCOS CORTADOS": sum(1 for c in corridas if c > MAX_DIAS_SEGUIDOS),
                "EXCESO HS": max(0, horas - HORAS_MAX_MES),
            })
        res[s] = pd.DataFrame(filas).sort_values("HORAS", ascending=False).reset_index(drop=True) if filas else pd.DataFrame(
            columns=["VIGILADOR", "DÍAS", "TURNOS", "HORAS", "TURNOS DIURNOS", "TURNOS NOCTURNOS", "MÁX. DÍAS SEGUIDOS", "FRANCOS CORTADOS", "EXCESO HS"])
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
        c_aus = int((pv["ESTADO"] == "AUSENTE").sum()) if pv is not None else 0
        c_fra = int((pv["ESTADO"] == "FRANCO").sum()) if pv is not None else 0
        c_pre = int((pv["ESTADO"] == "PRÉSTAMO").sum()) if pv is not None else 0

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
            "AUSENTE": c_aus, "FRANCO": c_fra, "PRÉSTAMO": c_pre,
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
    aus, fra, pre = int(r["AUSENTE"]), int(r["FRANCO"]), int(r["PRÉSTAMO"])
    sin = max(0, n - lic - art - vac - aus - fra - pre)

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

    franja = seg(sin, "#3B6B55") + seg(lic, "#C96B6B") + seg(art, "#D49A52") + seg(vac, "#9A74B5") + seg(aus, "#D4B93C") + seg(fra, "#5B8DB8") + seg(pre, "#2E8F87")
    leyenda = ('<span style="color:#7FB8A0;">● ' + str(sin) + ' sin novedad</span> &nbsp; '
               '<span style="color:#D98A8A;">● ' + str(lic) + ' licencia</span> &nbsp; '
               '<span style="color:#E0AE74;">● ' + str(art) + ' ART</span> &nbsp; '
               '<span style="color:#B596CC;">● ' + str(vac) + ' vacaciones</span> &nbsp; '
               '<span style="color:#E3CB5E;">● ' + str(aus) + ' ausentes</span> &nbsp; '
               '<span style="color:#7FB0DC;">● ' + str(fra) + ' francos</span> &nbsp; '
               '<span style="color:#5CC4B8;">● ' + str(pre) + ' prestados</span>')

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

# --- BLOQUES GRÁFICOS DEL RELEVAMIENTO (reemplazan a las tablas) ---
def _num_seguro(v):
    try:
        return float(v)
    except Exception:
        return None

def _fila_barra_html(etiqueta, valor_txt, pct, color, chips=""):
    pct = max(0.0, min(100.0, pct))
    return ('<div style="margin:8px 0 0;">'
            '<div style="display:flex;justify-content:space-between;gap:8px;font-size:11px;color:#CBD5E1;">'
            '<span>' + etiqueta + chips + '</span><span style="color:#9AA3B5;white-space:nowrap;">' + valor_txt + '</span></div>'
            '<div style="background:#1F2430;border-radius:3px;height:5px;overflow:hidden;margin-top:3px;">'
            '<div style="background:' + color + ';height:100%;width:' + ("%.1f" % pct) + '%;opacity:.85;"></div></div></div>')

def _detalle_vigiladores_html(vig_df):
    """Horas y días seguidos por vigilador, en barras (sin tabla)."""
    import html as _h
    if vig_df is None or vig_df.empty:
        return '<div style="font-size:11px;color:#7C869A;">Sin ingresos registrados en el mes.</div>'
    filas = ""
    for _, v in vig_df.iterrows():
        horas, exc, fc = int(v["HORAS"]), int(v["EXCESO HS"]), int(v["FRANCOS CORTADOS"])
        seguidos = int(v["MÁX. DÍAS SEGUIDOS"])
        pct_h = 100.0 * horas / HORAS_MAX_MES if HORAS_MAX_MES else 0
        color_h = "#D9776F" if exc > 0 else ("#E0A458" if horas >= 0.9 * HORAS_MAX_MES else "#4DB6AC")
        pct_s = 100.0 * seguidos / MAX_DIAS_SEGUIDOS if MAX_DIAS_SEGUIDOS else 0
        color_s = "#5BC0CE" if seguidos > MAX_DIAS_SEGUIDOS else "#6C7A99"
        chips = ""
        if exc > 0:
            chips += ('<span style="border:1px solid #D9776F;color:#E89A93;border-radius:8px;padding:0 6px;font-size:9.5px;margin-left:6px;">⚠ +' + str(exc) + ' hs</span>')
        if fc > 0:
            chips += ('<span style="border:1px solid #5BC0CE;color:#7FD6E0;border-radius:8px;padding:0 6px;font-size:9.5px;margin-left:6px;">✂ franco cortado</span>')
        n_dia, n_noc = int(v["TURNOS DIURNOS"]), int(v["TURNOS NOCTURNOS"])
        n_dias, n_turnos = int(v["DÍAS"]), int(v["TURNOS"])
        turnos_html = ('<div style="margin-top:7px;font-size:11px;color:#9AA3B5;">'
                       'Trabajó <b style="color:#E2E8F0;">' + str(n_dias) + (' día' if n_dias == 1 else ' días') + '</b> del mes · '
                       '<b style="color:#E2E8F0;">' + str(n_turnos) + (' turno' if n_turnos == 1 else ' turnos') + '</b>: '
                       '<span style="border:1px solid #E0C060;color:#F0D98A;border-radius:8px;padding:0 6px;font-size:10px;margin-left:2px;">☀️ ' + str(n_dia) + ' diurno' + ('' if n_dia == 1 else 's') + '</span> '
                       '<span style="border:1px solid #8E9BE0;color:#B8C1F0;border-radius:8px;padding:0 6px;font-size:10px;">🌙 ' + str(n_noc) + ' nocturno' + ('' if n_noc == 1 else 's') + '</span></div>')
        filas += ('<div style="background:rgba(22,27,34,.55);border:1px solid #2A3040;border-radius:8px;padding:8px 12px;margin:6px 0;">'
                  '<div style="font-size:12px;color:#E2E8F0;">' + _h.escape(str(v["VIGILADOR"])) + chips + '</div>'
                  + _fila_barra_html("Horas trabajadas", str(horas) + " hs de " + str(HORAS_MAX_MES) + " permitidas", pct_h, color_h)
                  + _fila_barra_html("Más días seguidos sin descanso", str(seguidos) + (" día" if seguidos == 1 else " días") + " (límite " + str(MAX_DIAS_SEGUIDOS) + ")", pct_s, color_s)
                  + turnos_html + '</div>')
    return filas

def _detalle_objetivos_html(det_df):
    """Visitas y permanencia por objetivo, en barras (sin tabla)."""
    import html as _h
    if det_df is None or det_df.empty:
        return '<div style="font-size:11px;color:#7C869A;">Sin objetivos asignados.</div>'
    max_vis = max([int(x) for x in det_df["VISITAS"]] + [1])
    perms = [_num_seguro(x) for x in det_df["PERMANENCIA PROM. (MIN)"]]
    max_perm = max([x for x in perms if x is not None] + [1])
    filas = ""
    for (_, o), perm in zip(det_df.iterrows(), perms):
        vis = int(o["VISITAS"])
        ok = vis > 0
        chip = ('<span style="border:1px solid ' + ("#4DB6AC" if ok else "#D9776F") + ';color:' + ("#7FD6C0" if ok else "#E89A93") +
                ';border-radius:8px;padding:0 6px;font-size:9.5px;margin-left:6px;">' + ("✔ visitado" if ok else "✖ sin visita") + '</span>')
        perm_txt = (str(int(round(perm))) + " min") if perm is not None else "sin dato"
        perm_pct = (100.0 * perm / max_perm) if perm is not None else 0
        filas += ('<div style="background:rgba(22,27,34,.55);border:1px solid #2A3040;border-radius:8px;padding:8px 12px;margin:6px 0;">'
                  '<div style="font-size:12px;color:#E2E8F0;">🎯 ' + _h.escape(str(o["OBJETIVO"])) + chip + '</div>'
                  + _fila_barra_html("Visitas QR", str(vis), 100.0 * vis / max_vis, "#5BC0CE" if ok else "#3A4152")
                  + _fila_barra_html("Permanencia promedio", perm_txt, perm_pct, "#4DB6AC")
                  + '</div>')
    return filas

def _bloque_comparativo_html(titulo, items, color, escala=None, sufijo=""):
    import html as _h
    vals = [v for _, v in items]
    tope = escala if escala else max(vals + [1])
    filas = ""
    for nombre, v in items:
        txt = ("%g" % v) + sufijo
        filas += _fila_barra_html(_h.escape(str(nombre)), txt, 100.0 * v / tope if tope else 0, color)
    return ('<div style="background:rgba(22,27,34,.55);border:1px solid #2A3040;border-radius:10px;padding:10px 14px;">'
            '<div style="font-family:Orbitron,sans-serif;font-size:11px;color:#7FD6E0;letter-spacing:.8px;">' + titulo + '</div>' + filas + '</div>')

def _comparativo_supervisores_html(vista):
    """Comparativo de todos los supervisores en barras (sin tabla)."""
    import html as _h
    if vista is None or vista.empty:
        return ""
    def items(col):
        return [(r["SUPERVISOR"], float(r[col])) for _, r in vista.iterrows()]
    bloques = [
        _bloque_comparativo_html("🎯 COBERTURA DE OBJETIVOS", items("COBERTURA %"), "#5BC0CE", 100, "%"),
        _bloque_comparativo_html("📱 VISITAS QR", items("VISITAS QR"), "#4DB6AC"),
        _bloque_comparativo_html("📅 DÍAS ACTIVOS", items("DÍAS ACTIVOS"), "#6C9BD2"),
        _bloque_comparativo_html("⏱️ HORAS DE JORNADA", items("HORAS"), "#8E9BE0", None, " hs"),
        _bloque_comparativo_html("👷 HS DE VIGILADORES", items("HS VIGILADORES"), "#E0A458", None, " hs"),
        _bloque_comparativo_html("🚗 KM RECORRIDOS", items("KM"), "#7FB8A0", None, " km"),
        _bloque_comparativo_html("🚨 PÁNICOS", items("PÁNICOS"), "#D9776F"),
        _bloque_comparativo_html("📝 NOVEDADES", items("NOVEDADES"), "#B596CC"),
        _bloque_comparativo_html("🔁 RONDAS COMPLETAS", items("RONDAS COMPLETAS"), "#5BC0CE"),
        _bloque_comparativo_html("⚠️ VIGILADORES EXCEDIDOS", items("EXCEDIDOS"), "#D9776F"),
        _bloque_comparativo_html("✂️ FRANCOS CORTADOS", items("FRANCOS CORTADOS"), "#7FD6E0"),
    ]
    # Personal a cargo: barra apilada por supervisor
    seg_def = [("sin novedad", "#3B6B55"), ("licencia", "#C96B6B"), ("ART", "#D49A52"),
               ("vacaciones", "#9A74B5"), ("ausentes", "#D4B93C"), ("francos", "#5B8DB8"), ("prestados", "#2E8F87")]
    filas_p = ""
    for _, r in vista.iterrows():
        n = int(r["VIGILADORES"])
        cants = [int(r["LICENCIA"]), int(r["ART"]), int(r["VACACIONES"]), int(r["AUSENTE"]), int(r["FRANCO"]), int(r["PRÉSTAMO"])]
        cants = [max(0, n - sum(cants))] + cants
        barra = "".join('<div title="' + nm + ': ' + str(c) + '" style="background:' + col + ';width:' + ("%.1f" % (100.0 * c / n if n else 0)) + '%;height:100%;"></div>'
                        for (nm, col), c in zip(seg_def, cants))
        detalle_txt = " · ".join(str(c) + " " + nm for (nm, _), c in zip(seg_def, cants) if c > 0) or "sin personal"
        filas_p += ('<div style="margin:8px 0 0;"><div style="display:flex;justify-content:space-between;font-size:11px;color:#CBD5E1;">'
                    '<span>' + _h.escape(str(r["SUPERVISOR"])) + '</span><span style="color:#9AA3B5;">' + str(n) + ' vig.</span></div>'
                    '<div style="display:flex;background:#1F2430;border-radius:3px;height:7px;overflow:hidden;margin-top:3px;">' + barra + '</div>'
                    '<div style="font-size:10px;color:#7C869A;margin-top:2px;">' + detalle_txt + '</div></div>')
    leyenda = "".join('<span style="color:' + col + ';margin-right:10px;font-size:10px;">● ' + nm + '</span>' for nm, col in seg_def)
    bloques.append('<div style="background:rgba(22,27,34,.55);border:1px solid #2A3040;border-radius:10px;padding:10px 14px;">'
                   '<div style="font-family:Orbitron,sans-serif;font-size:11px;color:#7FD6E0;letter-spacing:.8px;">👥 PERSONAL A CARGO</div>'
                   '<div style="margin-top:4px;">' + leyenda + '</div>' + filas_p + '</div>')
    return '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:10px;">' + "".join(bloques) + '</div>'

# =========================================================================
# PDF DEL RELEVAMIENTO MENSUAL - MISMO ASPECTO QUE EN LA APP
# (tarjeta por supervisor + horas por vigilador + objetivos + vigiladores a cargo
#  + comparativo de todos los supervisores, todo en un solo PDF)
# =========================================================================
from reportlab.platypus import Flowable, CondPageBreak
from reportlab.pdfbase.pdfmetrics import stringWidth
from xml.sax.saxutils import escape as _xml_escape

PDF_REL_OSCURO = True   # True = fondo oscuro, igual que se ve en la app · False = fondo blanco (para imprimir)

_PAL_OSC = {"pagina": "#0E1117", "tarjeta": "#161B22", "borde": "#2A3040", "pista": "#1F2430",
            "texto": "#E2E8F0", "label": "#7C869A", "suave": "#9AA3B5", "titulo": "#7FD6E0",
            "dia_finde": "#FF8A80", "dia_normal": "#A0A5B5", "grilla": "#0A0F1E", "nombre_grilla": "#E0E0E0",
            "finde_borde": "#3A4152"}
_PAL_CLA = {"pagina": "#FFFFFF", "tarjeta": "#F4F6F9", "borde": "#C9D1DC", "pista": "#DDE3EA",
            "texto": "#1F2937", "label": "#5B6475", "suave": "#4B5563", "titulo": "#0E7490",
            "dia_finde": "#C62828", "dia_normal": "#6B7280", "grilla": "#FFFFFF", "nombre_grilla": "#1F2937",
            "finde_borde": "#9AA5B5"}

def _pal():
    return _PAL_OSC if PDF_REL_OSCURO else _PAL_CLA

def _hx(c):
    c = str(c)
    if len(c) == 4 and c.startswith("#"):      # "#FFF" -> "#FFFFFF" (reportlab lo leería mal)
        c = "#" + "".join(ch * 2 for ch in c[1:])
    return colors.HexColor(c)

def _sin_emoji(txt):
    """Helvetica solo dibuja letras Latin-1: se descartan emojis y símbolos raros."""
    return "".join(ch for ch in str(txt) if ord(ch) < 256).strip()

def _recortar(txt, fuente, tam, ancho):
    txt = _sin_emoji(txt)
    if stringWidth(txt, fuente, tam) <= ancho:
        return txt
    while txt and stringWidth(txt + "...", fuente, tam) > ancho:
        txt = txt[:-1]
    return txt + "..."

def _barra_pdf(c, x, y, w, h, pct, color):
    P = _pal()
    pct = max(0.0, min(100.0, float(pct)))
    c.setFillColor(_hx(P["pista"]))
    c.roundRect(x, y, w, h, h / 2.0, fill=1, stroke=0)
    if pct > 0:
        c.setFillColor(_hx(color))
        c.roundRect(x, y, max(w * pct / 100.0, h), h, h / 2.0, fill=1, stroke=0)

def _chip_pdf(c, x, y, texto, borde, color, tam=6):
    texto = _sin_emoji(texto)
    w = stringWidth(texto, "Helvetica", tam) + 8
    c.setStrokeColor(_hx(borde))
    c.setLineWidth(0.6)
    c.roundRect(x, y - 2.3, w, tam + 3.8, 3.5, fill=0, stroke=1)
    c.setFillColor(_hx(color))
    c.setFont("Helvetica", tam)
    c.drawString(x + 4, y, texto)
    return x + w + 4

def _fila_barra_pdf(c, x, y, w, etiqueta, valor, pct, color, chips=None):
    """Etiqueta a la izquierda (con chips opcionales), valor a la derecha y barra fina debajo."""
    P = _pal()
    c.setFont("Helvetica", 7.2)
    c.setFillColor(_hx(P["texto"]))
    c.drawString(x, y, _sin_emoji(etiqueta))
    if chips:
        cx = x + stringWidth(_sin_emoji(etiqueta), "Helvetica", 7.2) + 6
        for (t, b, col) in chips:
            cx = _chip_pdf(c, cx, y, t, b, col, 5.8)
    c.setFillColor(_hx(P["suave"]))
    c.drawRightString(x + w, y, _sin_emoji(valor))
    _barra_pdf(c, x, y - 7.5, w, 3.6, pct, color)

def _marco_pdf(c, w, h, cerrar_arriba=True, cerrar_abajo=True):
    P = _pal()
    c.setFillColor(_hx(P["tarjeta"]))
    c.setStrokeColor(_hx(P["borde"]))
    c.setLineWidth(0.8)
    if cerrar_arriba and cerrar_abajo:
        c.roundRect(0, 0, w, h, 6, fill=1, stroke=1)
        return
    c.rect(0, 0, w, h, fill=1, stroke=0)
    c.line(0, 0, 0, h)
    c.line(w, 0, w, h)
    if cerrar_arriba:
        c.line(0, h, w, h)
    if cerrar_abajo:
        c.line(0, 0, w, 0)

class _Base(Flowable):
    def wrap(self, aw, ah):
        return self.width, self.height

_SEG_PERSONAL = [("sin novedad", "#3B6B55", "#7FB8A0"), ("licencia", "#C96B6B", "#D98A8A"), ("ART", "#D49A52", "#E0AE74"),
                 ("vacaciones", "#9A74B5", "#B596CC"), ("ausentes", "#D4B93C", "#E3CB5E"),
                 ("francos", "#5B8DB8", "#7FB0DC"), ("prestados", "#2E8F87", "#5CC4B8")]

def _tx_seg(col, tx):
    return tx if PDF_REL_OSCURO else col

def _cantidades_personal(r):
    n = int(r["VIGILADORES"])
    cants = [int(r["LICENCIA"]), int(r["ART"]), int(r["VACACIONES"]), int(r["AUSENTE"]), int(r["FRANCO"]), int(r["PRÉSTAMO"])]
    return n, [max(0, n - sum(cants))] + cants

class _TarjetaSupPDF(_Base):
    """Tarjeta del supervisor (igual que en la app). Si tiene vigiladores, queda abierta abajo y la continúan las filas."""
    def __init__(self, r, actividad, anio, mes, vig_df, ancho=744):
        super().__init__()
        self.r, self.act, self.anio, self.mes, self.vig_df = r, actividad, anio, mes, vig_df
        self.tiene_vig = vig_df is not None and not vig_df.empty
        self.width = ancho
        self.height = 182 if self.tiene_vig else 164

    def draw(self):
        c, P, r = self.canv, _pal(), self.r
        w, h = self.width, self.height
        _marco_pdf(c, w, h, True, not self.tiene_vig)
        x0, iw = 14, w - 28
        ndias = calendar.monthrange(self.anio, self.mes)[1]
        objs, vis, cob = int(r["OBJETIVOS"]), int(r["OBJ. VISITADOS"]), int(r["COBERTURA %"])
        dact = len(self.act)
        pct_dias = round(100 * dact / ndias) if ndias else 0
        n, cants = _cantidades_personal(r)

        y = h - 17
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(_hx(P["titulo"]))
        c.drawString(x0, y, _recortar(r["SUPERVISOR"], "Helvetica-Bold", 11, iw - 200))
        c.setFont("Helvetica", 7.5)
        c.setFillColor(_hx(P["label"]))
        c.drawRightString(x0 + iw, y, f"{objs} {'objetivo' if objs == 1 else 'objetivos'} · {n} {'vigilador' if n == 1 else 'vigiladores'}")

        y -= 17
        for titulo, valor, pct, color in (("Objetivos visitados", f"{vis}/{objs} · {cob}%", cob, "#5BC0CE"),
                                          ("Días con actividad", f"{dact}/{ndias} · {pct_dias}%", pct_dias, "#4DB6AC")):
            c.setFont("Helvetica", 7.2)
            c.setFillColor(_hx(P["label"]))
            c.drawString(x0, y, titulo)
            c.setFillColor(_hx(P["texto"]))
            c.drawRightString(x0 + iw, y, valor)
            _barra_pdf(c, x0, y - 7, iw, 4, pct, color)
            y -= 20

        y -= 8
        datos = [("VISITAS QR", r["VISITAS QR"]), ("HORAS", r["HORAS"]), ("KM", r["KM"]),
                 ("PÁNICOS", r["PÁNICOS"]), ("NOVEDADES", r["NOVEDADES"]), ("RONDAS", r["RONDAS COMPLETAS"])]
        cw = iw / float(len(datos))
        for i, (et, val) in enumerate(datos):
            cx = x0 + cw * i + cw / 2.0
            c.setFont("Helvetica-Bold", 12)
            c.setFillColor(_hx(P["texto"]))
            c.drawCentredString(cx, y, str(val))
            c.setFont("Helvetica", 6.3)
            c.setFillColor(_hx(P["label"]))
            c.drawCentredString(cx, y - 9, et)

        y -= 25
        c.setFont("Helvetica", 7.2)
        c.setFillColor(_hx(P["label"]))
        c.drawString(x0, y, "Actividad del mes")
        y -= 11
        for d in range(1, ndias + 1):
            activo = d in self.act
            finde = calendar.weekday(self.anio, self.mes, d) >= 5
            c.setFillColor(_hx("#4DB6AC" if activo else P["pista"]))
            if finde and not activo:
                c.setStrokeColor(_hx(P["finde_borde"]))
                c.setLineWidth(0.5)
                c.roundRect(x0 + (d - 1) * 8, y, 6, 6, 1.2, fill=1, stroke=1)
            else:
                c.roundRect(x0 + (d - 1) * 8, y, 6, 6, 1.2, fill=1, stroke=0)

        y -= 15
        c.setFont("Helvetica", 7.2)
        c.setFillColor(_hx(P["label"]))
        c.drawString(x0, y, "Personal a cargo")
        y -= 9
        c.setFillColor(_hx(P["pista"]))
        c.roundRect(x0, y, iw, 5, 2.5, fill=1, stroke=0)
        px = x0
        for (nm, col, _tx), cant in zip(_SEG_PERSONAL, cants):
            ancho = (iw * cant / float(max(n, sum(cants)))) if (n or sum(cants)) else 0
            if ancho > 0:
                c.setFillColor(_hx(col))
                c.rect(px, y, ancho, 5, fill=1, stroke=0)
                px += ancho
        y -= 10
        lx = x0
        c.setFont("Helvetica", 6.8)
        for (nm, _col, tx), cant in zip(_SEG_PERSONAL, cants):
            c.setFillColor(_hx(_tx_seg(_col, tx)))
            c.circle(lx + 2, y + 2.2, 2, fill=1, stroke=0)
            txt = f"{cant} {nm}"
            c.drawString(lx + 7, y, txt)
            lx += 7 + stringWidth(txt, "Helvetica", 6.8) + 10

        if self.tiene_vig:
            vd = self.vig_df
            tot_h, n_exc, n_fc = int(vd["HORAS"].sum()), int((vd["EXCESO HS"] > 0).sum()), int(vd["FRANCOS CORTADOS"].sum())
            y -= 15
            c.setFont("Helvetica", 7.2)
            c.setFillColor(_hx(P["label"]))
            c.drawString(x0, y, f"Vigiladores del mes · límite {HORAS_MAX_MES} hs")
            y -= 10
            lx = x0
            for txt, col in ((f"{tot_h} hs en total · ", P["suave"]), (f"{n_exc} excedidos", "#E89A93"),
                             (" · ", P["suave"]), (f"{n_fc} con franco cortado", "#4FB3C0" if PDF_REL_OSCURO else "#0E7490")):
                c.setFillColor(_hx(col))
                c.drawString(lx, y, txt)
                lx += stringWidth(txt, "Helvetica", 7.2)

class _FilaVigPDF(_Base):
    """Una fila de 'Vigiladores del mes' dentro de la tarjeta del supervisor."""
    def __init__(self, v, ultima, ancho=744):
        super().__init__()
        self.v, self.ultima = v, ultima
        self.width = ancho
        self.height = 25 if ultima else 21

    def draw(self):
        c, P, v = self.canv, _pal(), self.v
        w, h = self.width, self.height
        _marco_pdf(c, w, h, False, self.ultima)
        x0, iw = 14, w - 28
        horas, exc, fc = int(v["HORAS"]), int(v["EXCESO HS"]), int(v["FRANCOS CORTADOS"])
        ancho_b = max(0, min(100, 100.0 * horas / HORAS_MAX_MES)) if HORAS_MAX_MES else 0
        color = "#D9776F" if exc > 0 else ("#E0A458" if horas >= 0.9 * HORAS_MAX_MES else "#4DB6AC")
        base = h - 12
        nombre = _recortar(v["VIGILADOR"], "Helvetica", 7.5, 230)
        c.setFont("Helvetica", 7.5)
        c.setFillColor(_hx(P["texto"]))
        c.drawString(x0, base, nombre)
        cx = x0 + stringWidth(nombre, "Helvetica", 7.5) + 6
        if fc > 0:
            cx = _chip_pdf(c, cx, base, f"franco cortado · {int(v['MÁX. DÍAS SEGUIDOS'])} días seguidos", "#5BC0CE", "#4FB3C0" if PDF_REL_OSCURO else "#0E7490", 5.8)
        if exc > 0:
            cx = _chip_pdf(c, cx, base, f"+{exc} hs", "#D9776F", "#E89A93" if PDF_REL_OSCURO else "#B71C1C", 5.8)
        c.setFont("Helvetica", 7.2)
        c.setFillColor(_hx(P["suave"]))
        c.drawRightString(x0 + iw, base, f"{horas} hs · {int(v['DÍAS'])} d")
        _barra_pdf(c, x0, base - 7, iw, 3, ancho_b, color)

class _TarjetaVigDetallePDF(_Base):
    """'Horas por vigilador' del detalle: horas, días seguidos y turnos."""
    def __init__(self, v, ancho=366):
        super().__init__()
        self.v = v
        self.width, self.height = ancho, 82

    def draw(self):
        c, P, v = self.canv, _pal(), self.v
        w, h = self.width, self.height
        _marco_pdf(c, w, h)
        x0, iw = 10, w - 20
        horas, exc, fc = int(v["HORAS"]), int(v["EXCESO HS"]), int(v["FRANCOS CORTADOS"])
        seguidos = int(v["MÁX. DÍAS SEGUIDOS"])
        pct_h = 100.0 * horas / HORAS_MAX_MES if HORAS_MAX_MES else 0
        color_h = "#D9776F" if exc > 0 else ("#E0A458" if horas >= 0.9 * HORAS_MAX_MES else "#4DB6AC")
        pct_s = 100.0 * seguidos / MAX_DIAS_SEGUIDOS if MAX_DIAS_SEGUIDOS else 0
        color_s = "#5BC0CE" if seguidos > MAX_DIAS_SEGUIDOS else "#6C7A99"
        y = h - 14
        nombre = _recortar(v["VIGILADOR"], "Helvetica-Bold", 8.5, 205)
        c.setFont("Helvetica-Bold", 8.5)
        c.setFillColor(_hx(P["texto"]))
        c.drawString(x0, y, nombre)
        cx = x0 + stringWidth(nombre, "Helvetica-Bold", 8.5) + 6
        if exc > 0:
            cx = _chip_pdf(c, cx, y, f"+{exc} hs", "#D9776F", "#E89A93" if PDF_REL_OSCURO else "#B71C1C", 5.8)
        if fc > 0:
            cx = _chip_pdf(c, cx, y, "franco cortado", "#5BC0CE", "#4FB3C0" if PDF_REL_OSCURO else "#0E7490", 5.8)
        y -= 17
        _fila_barra_pdf(c, x0, y, iw, "Horas trabajadas", f"{horas} hs de {HORAS_MAX_MES} permitidas", pct_h, color_h)
        y -= 19
        _fila_barra_pdf(c, x0, y, iw, "Más días seguidos sin descanso",
                        f"{seguidos} {'día' if seguidos == 1 else 'días'} (límite {MAX_DIAS_SEGUIDOS})", pct_s, color_s)
        y -= 18
        n_dia, n_noc = int(v["TURNOS DIURNOS"]), int(v["TURNOS NOCTURNOS"])
        n_dias, n_turnos = int(v["DÍAS"]), int(v["TURNOS"])
        txt = f"Trabajó {n_dias} {'día' if n_dias == 1 else 'días'} del mes · {n_turnos} {'turno' if n_turnos == 1 else 'turnos'}:"
        c.setFont("Helvetica", 7)
        c.setFillColor(_hx(P["suave"]))
        c.drawString(x0, y, txt)
        cx = x0 + stringWidth(txt, "Helvetica", 7) + 6
        cx = _chip_pdf(c, cx, y, f"{n_dia} diurno{'' if n_dia == 1 else 's'}", "#E0C060", "#B58A00" if not PDF_REL_OSCURO else "#F0D98A", 6)
        _chip_pdf(c, cx, y, f"{n_noc} nocturno{'' if n_noc == 1 else 's'}", "#8E9BE0", "#4B5BB5" if not PDF_REL_OSCURO else "#B8C1F0", 6)

class _TarjetaObjetivoPDF(_Base):
    def __init__(self, o, max_vis, max_perm, ancho=366):
        super().__init__()
        self.o, self.max_vis, self.max_perm = o, max_vis, max_perm
        self.width, self.height = ancho, 64

    def draw(self):
        c, P, o = self.canv, _pal(), self.o
        w, h = self.width, self.height
        _marco_pdf(c, w, h)
        x0, iw = 10, w - 20
        vis = int(o["VISITAS"])
        ok = vis > 0
        perm = _num_seguro(o["PERMANENCIA PROM. (MIN)"])
        y = h - 14
        nombre = _recortar(o["OBJETIVO"], "Helvetica-Bold", 8.5, 220)
        c.setFont("Helvetica-Bold", 8.5)
        c.setFillColor(_hx(P["texto"]))
        c.drawString(x0, y, nombre)
        cx = x0 + stringWidth(nombre, "Helvetica-Bold", 8.5) + 6
        if ok:
            _chip_pdf(c, cx, y, "visitado", "#4DB6AC", "#7FD6C0" if PDF_REL_OSCURO else "#00796B", 5.8)
        else:
            _chip_pdf(c, cx, y, "sin visita", "#D9776F", "#E89A93" if PDF_REL_OSCURO else "#B71C1C", 5.8)
        y -= 17
        _fila_barra_pdf(c, x0, y, iw, "Visitas QR", str(vis), 100.0 * vis / self.max_vis, "#5BC0CE" if ok else "#3A4152")
        y -= 19
        perm_txt = (str(int(round(perm))) + " min") if perm is not None else "sin dato"
        perm_pct = (100.0 * perm / self.max_perm) if perm is not None else 0
        _fila_barra_pdf(c, x0, y, iw, "Permanencia promedio", perm_txt, perm_pct, "#4DB6AC")

class _BloqueCompPDF(_Base):
    """Un gráfico de barras del comparativo (una barra por supervisor)."""
    def __init__(self, titulo, items, color, escala=None, sufijo="", ancho=366):
        super().__init__()
        self.titulo, self.items, self.color, self.escala, self.sufijo = titulo, items, color, escala, sufijo
        self.width = ancho
        self.height = 26 + 19 * len(items)

    def draw(self):
        c, P = self.canv, _pal()
        w, h = self.width, self.height
        _marco_pdf(c, w, h)
        x0, iw = 10, w - 20
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(_hx(P["titulo"]))
        c.drawString(x0, h - 15, self.titulo)
        vals = [v for _, v in self.items]
        tope = self.escala if self.escala else max(vals + [1])
        y = h - 30
        for nombre, v in self.items:
            _fila_barra_pdf(c, x0, y, iw, _recortar(nombre, "Helvetica", 7.2, iw - 70),
                            ("%g" % v) + self.sufijo, 100.0 * v / tope if tope else 0, self.color)
            y -= 19

def _lineas_leyenda(ancho, tam=6.5):
    lineas, actual, usado = [], [], 0
    for nm, col, tx in _SEG_PERSONAL:
        wi = 9 + stringWidth(nm, "Helvetica", tam) + 8
        if actual and usado + wi > ancho:
            lineas.append(actual)
            actual, usado = [], 0
        actual.append((nm, col, tx))
        usado += wi
    if actual:
        lineas.append(actual)
    return lineas

class _BloquePersonalPDF(_Base):
    """Personal a cargo de todos los supervisores: barra apilada por supervisor."""
    def __init__(self, vista, ancho=366):
        super().__init__()
        self.vista = vista
        self.width = ancho
        self.lineas = _lineas_leyenda(ancho - 20)
        self.height = 26 + 11 * len(self.lineas) + 6 + 31 * len(vista)

    def draw(self):
        c, P = self.canv, _pal()
        w, h = self.width, self.height
        _marco_pdf(c, w, h)
        x0, iw = 10, w - 20
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(_hx(P["titulo"]))
        c.drawString(x0, h - 15, "PERSONAL A CARGO")
        y = h - 28
        c.setFont("Helvetica", 6.5)
        for linea in self.lineas:
            lx = x0
            for nm, col, tx in linea:
                c.setFillColor(_hx(_tx_seg(col, tx)))
                c.circle(lx + 2, y + 2.2, 2, fill=1, stroke=0)
                c.drawString(lx + 7, y, nm)
                lx += 9 + stringWidth(nm, "Helvetica", 6.5) + 8
            y -= 11
        y -= 6
        for _, r in self.vista.iterrows():
            n, cants = _cantidades_personal(r)
            c.setFont("Helvetica", 7.2)
            c.setFillColor(_hx(P["texto"]))
            c.drawString(x0, y, _recortar(r["SUPERVISOR"], "Helvetica", 7.2, iw - 60))
            c.setFillColor(_hx(P["suave"]))
            c.drawRightString(x0 + iw, y, f"{n} vig.")
            c.setFillColor(_hx(P["pista"]))
            c.roundRect(x0, y - 9, iw, 6, 3, fill=1, stroke=0)
            px = x0
            for (nm, col, _tx), cant in zip(_SEG_PERSONAL, cants):
                ancho = (iw * cant / float(max(n, sum(cants)))) if (n or sum(cants)) else 0
                if ancho > 0:
                    c.setFillColor(_hx(col))
                    c.rect(px, y - 9, ancho, 6, fill=1, stroke=0)
                    px += ancho
            detalle = " · ".join(f"{cant} {nm}" for (nm, _, _), cant in zip(_SEG_PERSONAL, cants) if cant > 0) or "sin personal"
            c.setFont("Helvetica", 6.2)
            c.setFillColor(_hx(P["label"]))
            c.drawString(x0, y - 17, _recortar(detalle, "Helvetica", 6.2, iw))
            y -= 31

class _MetricaPDF(_Base):
    def __init__(self, etiqueta, valor, ancho=240):
        super().__init__()
        self.etiqueta, self.valor = etiqueta, valor
        self.width, self.height = ancho, 38

    def draw(self):
        c, P = self.canv, _pal()
        _marco_pdf(c, self.width, self.height)
        c.setFont("Helvetica", 6.8)
        c.setFillColor(_hx(P["label"]))
        c.drawString(10, self.height - 13, _sin_emoji(self.etiqueta))
        c.setFont("Helvetica-Bold", 15)
        c.setFillColor(_hx(P["texto"]))
        c.drawString(10, 9, str(self.valor))

class _LeyendaPlanPDF(_Base):
    def __init__(self, ancho=744):
        super().__init__()
        self.width, self.height = ancho, 18

    def draw(self):
        c = self.canv
        x = 0
        items = [("SIN NOVEDAD", "#1F3A2B", "#E0E0E0")] + [(f"{letra} = {nombre}", bg, fg) for nombre, (letra, bg, fg) in TIPOS_NOVEDAD_PERSONAL.items()]
        for txt, bg, fg in items:
            txt = _sin_emoji(txt)
            wch = stringWidth(txt, "Helvetica", 7) + 14
            c.setFillColor(_hx(bg))
            c.roundRect(x, 3, wch, 12, 3, fill=1, stroke=0)
            c.setFillColor(_hx(fg))
            c.setFont("Helvetica", 7)
            c.drawString(x + 7, 6.5, txt)
            x += wch + 6

def _tabla_planificacion_pdf(df, anio, mes):
    """Grilla de vigiladores a cargo: una fila por vigilador y una columna por día (L/ART/V/A/F/P)."""
    P = _pal()
    ndias = calendar.monthrange(anio, mes)[1]
    ancho_nombre = 126.0
    ancho_dia = (744.0 - ancho_nombre) / ndias
    datos = [[""] + [f"{LETRAS_DIA[calendar.weekday(anio, mes, d)]}\n{d}" for d in range(1, ndias + 1)]]
    estilos = [
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"), ("FONTSIZE", (0, 0), (-1, 0), 6),
        ("LEADING", (0, 0), (-1, 0), 7), ("ALIGN", (1, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 1), ("RIGHTPADDING", (0, 0), (-1, -1), 1),
        ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ("GRID", (1, 1), (-1, -1), 0.8, _hx(P["grilla"])),
        ("BACKGROUND", (0, 0), (-1, 0), _hx(P["pagina"])),
    ]
    for d in range(1, ndias + 1):
        finde = calendar.weekday(anio, mes, d) >= 5
        estilos.append(("TEXTCOLOR", (d, 0), (d, 0), _hx(P["dia_finde"] if finde else P["dia_normal"])))
    for i, (_, r) in enumerate(df.iterrows(), start=1):
        fila = [_recortar(r["VIGILADOR"], "Helvetica", 6.8, ancho_nombre - 6)]
        estilos.append(("TEXTCOLOR", (0, i), (0, i), _hx(P["nombre_grilla"])))
        estilos.append(("ALIGN", (0, i), (0, i), "LEFT"))
        estilos.append(("FONTSIZE", (0, i), (0, i), 6.8))
        for d in range(1, ndias + 1):
            t = r["MAPA"].get(d)
            if t:
                letra, bg, fg = TIPOS_NOVEDAD_PERSONAL[t]
                fila.append(letra)
                estilos += [("BACKGROUND", (d, i), (d, i), _hx(bg)), ("TEXTCOLOR", (d, i), (d, i), _hx(fg)),
                            ("FONTNAME", (d, i), (d, i), "Helvetica-Bold"), ("FONTSIZE", (d, i), (d, i), 6.2)]
            else:
                fila.append("")
                estilos.append(("BACKGROUND", (d, i), (d, i), _hx("#1F3A2B")))
        datos.append(fila)
    t = Table(datos, colWidths=[ancho_nombre] + [ancho_dia] * ndias, rowHeights=[18] + [13] * len(df), repeatRows=1)
    t.setStyle(TableStyle(estilos))
    return t

def _grilla_dos_columnas(tarjetas):
    """Acomoda tarjetas de 366 pt de ancho de a dos por fila."""
    filas = []
    for i in range(0, len(tarjetas), 2):
        par = tarjetas[i:i + 2]
        if len(par) == 1:
            par.append(Spacer(1, 1))
        filas.append(par)
    t = Table(filas, colWidths=[372, 372])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 0),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    return t

class NumberedCanvasOscuro(NumberedCanvas):
    """Numeración de páginas con colores que se leen sobre fondo oscuro."""
    def draw_page_number(self, page_count):
        self.saveState()
        claro = "#9AA3B5" if PDF_REL_OSCURO else "#666666"
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor(claro))
        self.drawRightString(792 - 24, 15, f"Página {self._pageNumber} de {page_count}")
        self.drawString(24, 15, "AION-YAROKU | SISTEMA TÁCTICO INTEGRAL")
        self.setStrokeColor(colors.HexColor("#3A4152" if PDF_REL_OSCURO else "#CCCCCC"))
        self.setLineWidth(0.5)
        self.line(24, 25, 792 - 24, 25)
        self.restoreState()

def generar_pdf_relevamiento_visual(vista, detalle, personal, actividad, vigs, anio, mes, incluir_comparativo=True):
    """Un solo PDF con lo mismo que se ve en la app: por cada supervisor su tarjeta, las horas por vigilador,
    los objetivos y los vigiladores a cargo; al final, el comparativo de todos los supervisores."""
    P = _pal()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), rightMargin=24, leftMargin=24, topMargin=24, bottomMargin=35,
                            title=f"Relevamiento mensual {MESES_ES[mes - 1]} {anio}")
    styles = getSampleStyleSheet()
    est_tit = ParagraphStyle("RelT", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=14, leading=17,
                             textColor=_hx(P["titulo"]), alignment=1, spaceAfter=2)
    est_sub = ParagraphStyle("RelS", parent=styles["Normal"], fontName="Helvetica", fontSize=8.5, leading=11,
                             textColor=_hx(P["suave"]), alignment=1, spaceAfter=10)
    est_h2 = ParagraphStyle("RelH2", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=10.5, leading=13,
                            textColor=_hx(P["titulo"]), spaceBefore=6, spaceAfter=6, keepWithNext=1)
    est_h3 = ParagraphStyle("RelH3", parent=styles["Heading3"], fontName="Helvetica-Bold", fontSize=9, leading=11,
                            textColor=_hx(P["texto"]), spaceBefore=8, spaceAfter=5, keepWithNext=1)

    alcance = vista.iloc[0]["SUPERVISOR"] if len(vista) == 1 else "TODOS LOS SUPERVISORES"
    el = [Paragraph("<b>AION-YAROKU | RELEVAMIENTO MENSUAL DE SUPERVISORES</b>", est_tit),
          Paragraph(f"<b>{MESES_ES[mes - 1]} {anio}</b> | {_xml_escape(str(alcance))} | Emisión: {obtener_hora_argentina()}", est_sub)]

    metricas = [("SUPERVISORES", len(vista)), ("VISITAS QR", int(vista["VISITAS QR"].sum())),
                ("COBERTURA PROM.", f"{int(round(vista['COBERTURA %'].mean()))}%"),
                ("HS VIGILADORES", int(vista["HS VIGILADORES"].sum())), ("EXCEDIDOS", int(vista["EXCEDIDOS"].sum())),
                ("FRANCOS CORTADOS", int(vista["FRANCOS CORTADOS"].sum())),
                ("AUSENTES (vigiladores)", int(vista["AUSENTE"].sum())), ("EN FRANCO (vigiladores)", int(vista["FRANCO"].sum())),
                ("PRESTADOS (vigiladores)", int(vista["PRÉSTAMO"].sum()))]
    filas_m = [[_MetricaPDF(e, v) for e, v in metricas[i:i + 3]] for i in range(0, 9, 3)]
    tm = Table(filas_m, colWidths=[248, 248, 248])
    tm.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                            ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    el.append(tm)
    el.append(Paragraph("POR SUPERVISOR", est_h2))

    for _, r in vista.iterrows():
        s = r["SUPERVISOR"]
        vig_df = vigs.get(s)
        tiene_vig = vig_df is not None and not vig_df.empty
        el.append(CondPageBreak(240))
        el.append(_TarjetaSupPDF(r, actividad.get(s, set()), anio, mes, vig_df if tiene_vig else None))
        if tiene_vig:
            filas_v = list(vig_df.iterrows())
            for i, (_, v) in enumerate(filas_v):
                el.append(_FilaVigPDF(v, ultima=(i == len(filas_v) - 1)))
        el.append(Spacer(1, 8))

        el.append(Paragraph(f"DETALLE DE OBJETIVOS Y PERSONAL - {_xml_escape(str(s))}", est_h2))
        if tiene_vig:
            el.append(Paragraph("Horas por vigilador", est_h3))
            el.append(_grilla_dos_columnas([_TarjetaVigDetallePDF(v) for _, v in vig_df.iterrows()]))
        el.append(Paragraph("Objetivos", est_h3))
        det_df = detalle.get(s)
        if det_df is None or det_df.empty:
            el.append(Paragraph("Sin objetivos asignados.", est_sub))
        else:
            max_vis = max([int(x) for x in det_df["VISITAS"]] + [1])
            perms = [_num_seguro(x) for x in det_df["PERMANENCIA PROM. (MIN)"]]
            max_perm = max([x for x in perms if x is not None] + [1])
            el.append(_grilla_dos_columnas([_TarjetaObjetivoPDF(o, max_vis, max_perm) for _, o in det_df.iterrows()]))
        if s in personal and not personal[s].empty:
            el.append(CondPageBreak(120))
            el.append(Paragraph(f"Vigiladores a cargo ({int(r['VIGILADORES'])})", est_h3))
            el.append(_LeyendaPlanPDF())
            el.append(Spacer(1, 4))
            el.append(_tabla_planificacion_pdf(personal[s], anio, mes))
        if incluir_comparativo:
            el.append(PageBreak())

    # --- Comparativo de todos los supervisores ---
    def items(col):
        return [(r["SUPERVISOR"], float(r[col])) for _, r in vista.iterrows()]
    bloques = [
        _BloqueCompPDF("COBERTURA DE OBJETIVOS", items("COBERTURA %"), "#5BC0CE", 100, "%"),
        _BloqueCompPDF("VISITAS QR", items("VISITAS QR"), "#4DB6AC"),
        _BloqueCompPDF("DÍAS ACTIVOS", items("DÍAS ACTIVOS"), "#6C9BD2"),
        _BloqueCompPDF("HORAS DE JORNADA", items("HORAS"), "#8E9BE0", None, " hs"),
        _BloqueCompPDF("HS DE VIGILADORES", items("HS VIGILADORES"), "#E0A458", None, " hs"),
        _BloqueCompPDF("KM RECORRIDOS", items("KM"), "#7FB8A0", None, " km"),
        _BloqueCompPDF("PÁNICOS", items("PÁNICOS"), "#D9776F"),
        _BloqueCompPDF("NOVEDADES", items("NOVEDADES"), "#B596CC"),
        _BloqueCompPDF("RONDAS COMPLETAS", items("RONDAS COMPLETAS"), "#5BC0CE"),
        _BloqueCompPDF("VIGILADORES EXCEDIDOS", items("EXCEDIDOS"), "#D9776F"),
        _BloqueCompPDF("FRANCOS CORTADOS", items("FRANCOS CORTADOS"), "#7FD6E0"),
        _BloquePersonalPDF(vista),
    ]
    if incluir_comparativo:
        el.append(Paragraph("COMPARATIVO DE TODOS LOS SUPERVISORES", est_h2))
        el.append(_grilla_dos_columnas(bloques))

    def _fondo(canv, _doc):
        canv.saveState()
        canv.setFillColor(_hx(_pal()["pagina"]))
        canv.rect(0, 0, 792, 612, fill=1, stroke=0)
        canv.restoreState()

    doc.build(el, onFirstPage=_fondo, onLaterPages=_fondo, canvasmaker=NumberedCanvasOscuro)
    buffer.seek(0)
    return buffer.getvalue()

from xml.sax.saxutils import escape as _xml_escape
# =========================================================================
# REPORTE TÁCTICO INTEGRAL POR SUPERVISOR (mismo PDF que descarga el Jefe de Operaciones)
# Se usa también desde Monitoreo, así los dos descargan exactamente lo mismo.
# =========================================================================
def datos_reporte_integral_supervisor(sup):
    """Arma todas las tablas del reporte integral de un supervisor (mismos filtros que el Tablero de Auditoría)."""
    sup_n = str(sup).strip().upper()

    def _hoja(nombre):
        d = leer_matriz_nube(nombre)
        if d is None or d.empty:
            return pd.DataFrame()
        d = d.copy()
        d.columns = [str(c).strip().upper() for c in d.columns]
        return d

    df_o = cargar_objetivos()
    objs = []
    if not df_o.empty and 'SUPERVISOR' in df_o.columns and 'OBJETIVO' in df_o.columns:
        m_o = col_texto(df_o, 'SUPERVISOR').str.strip().str.upper() == sup_n
        objs = [o.strip().upper() for o in col_texto(df_o, 'OBJETIVO')[m_o].tolist()]

    # --- Jornada ---
    ini_j, fin_j, tot_j = "---", "---", "---"
    df_j = _hoja("JORNADA SUPERVISORES")
    if not df_j.empty and df_j.shape[1] >= 5:
        c_s, c_a, c_h = df_j.columns[1], df_j.columns[3], df_j.columns[4]
        sj = df_j[col_texto(df_j, c_s).str.strip().str.upper() == sup_n]
        if not sj.empty:
            inicios = sj[col_texto(sj, c_a).str.strip().str.upper() == 'INICIO']
            fines = sj[col_texto(sj, c_a).str.strip().str.upper() == 'FIN']
            dt_i = dt_f = None
            if not inicios.empty:
                ini_j = str(inicios.iloc[-1][c_h])
                try:
                    dt_i = datetime.strptime(ini_j, "%H:%M:%S")
                except Exception:
                    pass
            if not fines.empty:
                fin_j = str(fines.iloc[-1][c_h])
                try:
                    dt_f = datetime.strptime(fin_j, "%H:%M:%S")
                except Exception:
                    pass
            if dt_i and dt_f and dt_f >= dt_i:
                m_tot = int((dt_f - dt_i).total_seconds() // 60)
                tot_j = f"{m_tot // 60}h {m_tot % 60}m" if m_tot >= 60 else f"{m_tot} min"

    # --- Permanencia por objetivo (escaneos QR) ---
    df_perm = pd.DataFrame()
    df_q = _hoja("REGISTRO QR SUPERVISORES")
    if not df_q.empty and df_q.shape[1] >= 4:
        c_sq = 'SUPERVISOR' if 'SUPERVISOR' in df_q.columns else df_q.columns[3]
        sq = df_q[col_texto(df_q, c_sq).str.strip().str.upper() == sup_n]
        if not sq.empty:
            c_fh, c_ob, c_ac = sq.columns[0], sq.columns[1], sq.columns[2]
            filas = []
            for obj_v in col_texto(sq, c_ob).dropna().str.strip().str.upper().unique():
                reg = sq[col_texto(sq, c_ob).str.strip().str.upper() == obj_v]
                ini_o = reg[col_texto(reg, c_ac).str.strip().str.upper() == 'INICIO']
                fin_o = reg[col_texto(reg, c_ac).str.strip().str.upper() == 'FIN']
                ing, egr, perm = "---", "---", "---"
                dt_ing = dt_egr = None
                if not ini_o.empty:
                    raw = str(ini_o.iloc[-1][c_fh])
                    ing = raw.split(" ")[1] if " " in raw else raw
                    try:
                        dt_ing = datetime.strptime(ing, "%H:%M:%S")
                    except Exception:
                        pass
                if not fin_o.empty:
                    raw = str(fin_o.iloc[-1][c_fh])
                    egr = raw.split(" ")[1] if " " in raw else raw
                    try:
                        dt_egr = datetime.strptime(egr, "%H:%M:%S")
                    except Exception:
                        pass
                if dt_ing and dt_egr and dt_egr >= dt_ing:
                    mp = int((dt_egr - dt_ing).total_seconds() // 60)
                    perm = f"{mp // 60}h {mp % 60}m" if mp >= 60 else f"{mp} min"
                filas.append({"OBJETIVO": obj_v, "HORARIO INGRESO": ing, "HORARIO EGRESO": egr, "TIEMPO DE PERMANENCIA": perm})
            df_perm = pd.DataFrame(filas)

    # --- Fichaje de vigiladores ---
    df_fich = pd.DataFrame()
    df_n = _hoja("NOVEDADES GUARDIA")
    if not df_n.empty and objs and 'OBJETIVO' in df_n.columns:
        df_n['OBJETIVO_CLEAN'] = col_texto(df_n, 'OBJETIVO').str.strip().str.upper()
        col_ev = next((p for p in ['TIPO_EVENTO', 'TIPO EVENTO', 'EVENTO', 'TIPO'] if p in df_n.columns),
                      df_n.columns[2] if len(df_n.columns) > 2 else None)
        if col_ev:
            mask_f = df_n['OBJETIVO_CLEAN'].isin(objs) & col_texto(df_n, col_ev).str.upper().str.contains("MARCACIÓN|FICHAJE|INGRESO|EGRESO", regex=True)
            raw_f = df_n[mask_f]
            if not raw_f.empty:
                filas = []
                for _, r in raw_f.iterrows():
                    ev = str(r.iloc[2])
                    nom = str(r.iloc[4]) if len(r) > 4 else ""
                    filas.append({"FECHA": str(r.iloc[0]), "OBJETIVO": str(r.iloc[1]), "EVENTO": ev,
                                  "INGRESO": nom if "INGRESO" in ev.upper() else "---",
                                  "EGRESO": nom if "EGRESO" in ev.upper() else "---",
                                  "LEGAJO": str(r.iloc[5]) if len(r) > 5 else "",
                                  "ESTADO": str(r.iloc[6]) if len(r) > 6 else "PROCESADO"})
                df_fich = pd.DataFrame(filas)

    # --- Relevos ---
    df_rel = pd.DataFrame()
    df_v = _hoja("VIGILADORES")
    if not df_v.empty and objs:
        c_ov = 'OBJETIVO' if 'OBJETIVO' in df_v.columns else df_v.columns[min(2, len(df_v.columns) - 1)]
        df_rel = df_v[col_texto(df_v, c_ov).str.strip().str.upper().isin(objs)]

    # --- Rondas ---
    df_rec = tabla_recorridas_vigiladores(objs)

    # --- Pánicos y alertas ---
    df_pan_s, df_pan_v, df_alt = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    df_a = _hoja("ALERTAS")
    if not df_a.empty and 'TIPO' in df_a.columns:
        pan = df_a[col_texto(df_a, 'TIPO').str.strip().str.upper() == "PÁNICO"]
        es_sup = col_texto(pan, 'USUARIO').str.strip().str.upper() == sup_n
        df_pan_s = pan[es_sup]
        en_obj = col_texto(pan, 'OBJETIVO').str.strip().str.upper().isin(objs)
        df_pan_v = pan[en_obj & ~es_sup]
        otras = df_a[(col_texto(df_a, 'TIPO').str.strip().str.upper() != "PÁNICO") & ~col_texto(df_a, 'TIPO').str.upper().str.contains("FRAUDE")]
        m_alt = pd.Series(False, index=otras.index)
        if 'OBJETIVO' in otras.columns:
            m_alt = m_alt | col_texto(otras, 'OBJETIVO').str.strip().str.upper().isin(objs)
        if 'SUPERVISOR' in otras.columns:
            m_alt = m_alt | (col_texto(otras, 'SUPERVISOR').str.strip().str.upper() == sup_n)
        df_alt = otras[m_alt]

    # --- Flota ---
    df_flota = pd.DataFrame()
    df_f = _hoja("CONTROL DE FLOTA")
    if not df_f.empty:
        c_sf = 'SUPERVISOR' if 'SUPERVISOR' in df_f.columns else (df_f.columns[1] if len(df_f.columns) > 1 else None)
        if c_sf:
            df_flota = df_f[col_texto(df_f, c_sf).str.strip().str.upper() == sup_n].copy()

    # --- Traspasos de objetivos ---
    df_tras = pd.DataFrame()
    try:
        d_t = _hoja("TRASPASOS OBJETIVOS")
        if not d_t.empty and {"ORIGEN", "DESTINO"} <= set(d_t.columns):
            ori = col_texto(d_t, "ORIGEN").str.strip().str.upper()
            des = col_texto(d_t, "DESTINO").str.strip().str.upper()
            df_tras = d_t[(ori == sup_n) | (des == sup_n)].copy()
            if not df_tras.empty:
                df_tras.insert(1, "MOVIMIENTO", ["TRASPASÓ" if x == sup_n else "RECIBIÓ" for x in ori[df_tras.index]])
                df_tras = df_tras[[c for c in ["FECHA_HORA", "MOVIMIENTO", "OBJETIVO", "ORIGEN", "DESTINO", "MOTIVO"] if c in df_tras.columns]]
    except Exception:
        df_tras = pd.DataFrame()

    # --- Cargas tácticas ---
    df_car = pd.DataFrame()
    df_nv = _hoja("NOVEDADES GUARDIA")
    if not df_nv.empty and df_nv.shape[1] >= 5:
        nv = df_nv.iloc[:, :5].copy()
        nv.columns = ["FECHA", "OBJETIVO", "TIPO", "DETALLE", "SUPERVISOR"]
        nv = nv[(nv["TIPO"].astype(str).str.strip().str.upper() == "NOVEDAD OPERATIVA") &
                (nv["SUPERVISOR"].astype(str).str.strip().str.upper() == sup_n)]
        df_car = nv[["FECHA", "OBJETIVO", "DETALLE"]]

    return dict(sup_nombre=sup_n, j_ini=ini_j, j_fin=fin_j, j_tot=tot_j, d_perm=df_perm, d_fich=df_fich, d_rel=df_rel,
                d_alt=df_alt, d_psup=df_pan_s, d_pvig=df_pan_v, d_flota=df_flota,
                tot_s_cnt=len(df_pan_s), tot_v_cnt=len(df_pan_v), d_rec=df_rec, d_tras=df_tras, d_car=df_car)

# =========================================================================
# PDF "TAL CUAL SE VE EN LA APP" (fondo oscuro, colores e íconos): TABLERO DE AUDITORÍA y MI PERSONAL
# =========================================================================
from reportlab.platypus import KeepTogether
from reportlab.lib.utils import simpleSplit

_ICONO_ESTILO = [("🚩", "#FF1744", "FRAUDE"), ("⚠", "#FF9100", "FALTÓ"), ("⏳", "#94A3B8", "PEND."), ("✅", "#00E676", "OK")]

def _estilo_icono(txt):
    """Color y etiqueta según el ícono que trae el texto (🚩 fraude · ⚠️ no realizado · ⏳ pendiente · ✅ hecho)."""
    t = str(txt)
    for ico, col, tag in _ICONO_ESTILO:
        if ico in t:
            return col, tag
    return None, ""

class _ChipsPDF(_Base):
    """Recuadritos de colores (uno por punto de la ronda), como en la app; se acomodan en varios renglones."""
    def __init__(self, detalle, ancho):
        super().__init__()
        self.width = ancho
        self.items, self.pos = [], []
        for p in str(detalle).split(" | "):
            if not p.strip():
                continue
            col, tag = _estilo_icono(p)
            self.items.append((col or "#E2E8F0", tag, _sin_emoji(p)))
        x, linea = 0.0, 0
        for col, tag, txt in self.items:
            wch = 11 + (stringWidth(tag, "Helvetica-Bold", 6) + 4 if tag else 0) + stringWidth(txt, "Helvetica", 6.8)
            if x + wch > ancho and x > 0:
                x, linea = 0.0, linea + 1
            self.pos.append((linea, x, wch))
            x += wch + 4
        self.height = max(1, linea + 1) * 15 + 1

    def draw(self):
        c = self.canv
        for (col, tag, txt), (linea, x, wch) in zip(self.items, self.pos):
            y = self.height - (linea + 1) * 15 + 1
            c.saveState()
            c.setFillColor(colors.white)
            c.setFillAlpha(0.07)
            c.roundRect(x, y, wch, 12, 2.5, fill=1, stroke=0)
            c.restoreState()
            c.setFillColor(_hx(col))
            c.rect(x, y, 3, 12, fill=1, stroke=0)
            tx = x + 7
            if tag:
                c.setFont("Helvetica-Bold", 6)
                c.drawString(tx, y + 3.6, tag)
                tx += stringWidth(tag, "Helvetica-Bold", 6) + 4
            c.setFont("Helvetica", 6.8)
            c.setFillColor(_hx("#E2E8F0"))
            c.drawString(tx, y + 3.4, txt)

class _TarjetaLineasPDF(_Base):
    """Tarjeta con barra de color a la izquierda: nombre + etiqueta y líneas de texto (igual que las tarjetas de novedades y préstamos)."""
    def __init__(self, borde, titulo, pill, lineas, ancho=366):
        super().__init__()
        self.borde, self.titulo, self.pill = borde, _sin_emoji(titulo), pill
        self.lineas = []
        for txt, col, tam in lineas:
            for l in simpleSplit(_sin_emoji(txt), "Helvetica", tam, ancho - 26):
                self.lineas.append((l, col, tam))
        self.width = ancho
        self.height = 28 + sum(tam + 4 for _, _, tam in self.lineas) + 6

    def draw(self):
        c, P = self.canv, _pal()
        w, h = self.width, self.height
        _marco_pdf(c, w, h)
        c.setFillColor(_hx(self.borde))
        c.rect(0, 2, 4, h - 4, fill=1, stroke=0)
        y = h - 15
        c.setFont("Helvetica-Bold", 8.5)
        c.setFillColor(_hx(P["texto"]))
        c.drawString(12, y, _recortar(self.titulo, "Helvetica-Bold", 8.5, w - 150))
        if self.pill:
            txt, base, tcol, relleno = self.pill
            txt = _sin_emoji(txt)
            wp = stringWidth(txt, "Helvetica-Bold", 6.8) + 12
            if relleno:
                c.setFillColor(_hx(base))
                c.roundRect(w - wp - 10, y - 3, wp, 11, 5, fill=1, stroke=0)
            else:
                c.setStrokeColor(_hx(base))
                c.setLineWidth(0.7)
                c.roundRect(w - wp - 10, y - 3, wp, 11, 5, fill=0, stroke=1)
            c.setFillColor(_hx(tcol))
            c.setFont("Helvetica-Bold", 6.8)
            c.drawString(w - wp - 4, y, txt)
        y -= 6
        for l, col, tam in self.lineas:
            y -= tam + 4
            c.setFont("Helvetica", tam)
            c.setFillColor(_hx(col))
            c.drawString(12, y + 2, l)

def _estilos_pdf_oscuro():
    P = _pal()
    st_ = getSampleStyleSheet()
    return dict(
        P=P,
        tit=ParagraphStyle("OsT", parent=st_["Heading1"], fontName="Helvetica-Bold", fontSize=14, leading=17, textColor=_hx(P["titulo"]), alignment=1, spaceAfter=2),
        sub=ParagraphStyle("OsS", parent=st_["Normal"], fontName="Helvetica", fontSize=8.5, leading=11, textColor=_hx(P["suave"]), alignment=1, spaceAfter=10),
        h2=ParagraphStyle("OsH2", parent=st_["Heading2"], fontName="Helvetica-Bold", fontSize=10.5, leading=13, textColor=_hx(P["titulo"]), spaceBefore=9, spaceAfter=5, keepWithNext=1),
        h3=ParagraphStyle("OsH3", parent=st_["Heading3"], fontName="Helvetica-Bold", fontSize=9, leading=11, textColor=_hx(P["texto"]), spaceBefore=6, spaceAfter=4, keepWithNext=1),
        txt=ParagraphStyle("OsX", parent=st_["Normal"], fontName="Helvetica", fontSize=8, leading=10, textColor=_hx(P["suave"])),
        cab=ParagraphStyle("OsC", parent=st_["Normal"], fontName="Helvetica-Bold", fontSize=7, leading=9, textColor=_hx(P["suave"]), alignment=0),
        cel=ParagraphStyle("OsL", parent=st_["Normal"], fontName="Helvetica", fontSize=6.7, leading=8.6, textColor=_hx(P["texto"]), alignment=0),
    )

def _fondo_oscuro_pdf(canv, _doc):
    canv.saveState()
    canv.setFillColor(_hx(_pal()["pagina"]))
    canv.rect(0, 0, 792, 612, fill=1, stroke=0)
    canv.restoreState()

def generar_pdf_integral_supervisor(sup_nombre, j_ini, j_fin, j_tot, d_perm, d_fich, d_rel, d_alt, d_psup, d_pvig, d_flota,
                                    tot_s_cnt, tot_v_cnt, d_rec, d_tras=None, d_car=None):
    """REPORTE TÁCTICO INTEGRAL del Tablero de Auditoría, tal cual se ve en la app: fondo oscuro, colores e íconos.
    Lo descargan Jefe de Operaciones, Gerencia y Monitoreo."""
    E = _estilos_pdf_oscuro()
    P = E["P"]
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), rightMargin=24, leftMargin=24, topMargin=24, bottomMargin=35,
                            title=f"Reporte táctico integral - {sup_nombre}")
    el = [Paragraph("<b>AION-YAROKU | REPORTE TÁCTICO INTEGRAL DE SUPERVISOR</b>", E["tit"]),
          Paragraph(f"<b>Supervisor: {_xml_escape(str(sup_nombre))}</b> | Emisión: {obtener_hora_argentina()}", E["sub"])]

    el.append(Paragraph("Control de Jornada y Horas Trabajadas", E["h2"]))
    tj = Table([[_MetricaPDF("INICIO DE JORNADA", j_ini), _MetricaPDF("CIERRE DE JORNADA", j_fin), _MetricaPDF("TOTAL HORAS TRABAJADAS", j_tot)]],
               colWidths=[248, 248, 248])
    tj.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                            ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    el.append(tj)

    def tabla(titulo, df_in, anchos=None, invertir=False):
        el.append(Paragraph(titulo, E["h2"]))
        if df_in is None or df_in.empty:
            el.append(Paragraph("Sin registros en este periodo.", E["txt"]))
            return
        d = df_in.iloc[::-1] if invertir else df_in
        cols = list(d.columns)
        n = len(cols)
        w = anchos if (anchos and len(anchos) == n) else [744.0 / n] * n
        datos = [[Paragraph(_xml_escape(_sin_emoji(c)), E["cab"]) for c in cols]]
        for _, row in d.iterrows():
            datos.append([Paragraph(_xml_escape(_sin_emoji(row[c])) if pd.notna(row[c]) else "", E["cel"]) for c in cols])
        t = Table(datos, colWidths=w, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), _hx(P["pista"])), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [_hx(P["tarjeta"]), _hx("#12171F")]),
            ("GRID", (0, 0), (-1, -1), 0.5, _hx(P["borde"])), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
        el.append(t)

    def rondas(df_r):
        el.append(Paragraph("Seguimiento de Rondas de Vigiladores", E["h2"]))
        if df_r is None or df_r.empty:
            el.append(Paragraph("Sin rondas registradas.", E["txt"]))
            return
        cols = [c for c in df_r.columns if c != "DETALLE"]
        n = len(cols)
        w = [52, 120, 120, 40, 84, 52, 52, 48, 66, 110] if n == 10 else [744.0 / n] * n
        cab = Table([[Paragraph(_xml_escape(c), E["cab"]) for c in cols]], colWidths=w)
        cab.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), _hx(P["pista"])), ("LINEBELOW", (0, 0), (-1, -1), 1.2, _hx("#00E5FF")),
                                 ("LEFTPADDING", (0, 0), (-1, -1), 4), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
        el.append(cab)
        for _, r in df_r.iterrows():
            fila = []
            for c in cols:
                col, _tag = _estilo_icono(r[c]) if c in ("FRAUDE", "ESTADO") else (None, "")
                txt = _xml_escape(_sin_emoji(r[c]))
                fila.append(Paragraph(f'<font color="{col}">{txt}</font>' if col else txt, E["cel"]))
            fila2 = [_ChipsPDF(r.get("DETALLE", ""), sum(w) - 10)] + [""] * (n - 1)
            t = Table([fila, fila2], colWidths=w)
            t.setStyle(TableStyle([("SPAN", (0, 1), (-1, 1)), ("BACKGROUND", (0, 0), (-1, -1), _hx(P["tarjeta"])),
                                   ("LINEBELOW", (0, 1), (-1, 1), 0.6, _hx(P["borde"])), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                                   ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                                   ("TOPPADDING", (0, 0), (-1, 0), 3), ("BOTTOMPADDING", (0, 0), (-1, 0), 1),
                                   ("TOPPADDING", (0, 1), (-1, 1), 0), ("BOTTOMPADDING", (0, 1), (-1, 1), 3)]))
            el.append(KeepTogether(t))

    tabla("Detalle de Permanencia por Objetivo (Escaneos QR)", d_perm, [180, 180, 180, 204])
    tabla("Fichaje de Vigiladores", d_fich, [80, 110, 100, 90, 90, 90, 184])
    tabla("Relevos de Vigiladores", d_rel, [60, 100, 120, 120, 70, 90, 184])
    rondas(d_rec)
    tabla("Pánicos S.O.S de Supervisor", d_psup, None, invertir=True)
    df_pv = d_pvig.copy() if d_pvig is not None else pd.DataFrame()
    if not df_pv.empty:
        df_pv["TURNO VIGILADOR"] = [determinar_turno_activo(str(p.get("FECHA", ""))) for _, p in df_pv.iterrows()]
    tabla("Pánicos S.O.S de Vigiladores", df_pv, None, invertir=True)
    if tot_s_cnt > 0 or tot_v_cnt > 0 or (d_alt is not None and not d_alt.empty):
        el.append(Paragraph("Alertas Operativas", E["h2"]))
        if tot_s_cnt > 0:
            el.append(Paragraph(f"• TOTAL ALERTAS DE SUPERVISOR: <b>{tot_s_cnt}</b>", E["txt"]))
        if tot_v_cnt > 0:
            el.append(Paragraph(f"• TOTAL ALERTAS DE VIGILADOR: <b>{tot_v_cnt}</b>", E["txt"]))
        if d_alt is not None and not d_alt.empty:
            el.append(Spacer(1, 4))
            tabla("Detalle de Alertas Operativas", d_alt)
    tabla("Control de Flota", d_flota, [75, 70, 70, 60, 100, 90, 90, 189])
    tabla("Traspasos de Objetivos", d_tras, [100, 80, 150, 110, 110, 194], invertir=True)
    tabla("Cargas Tácticas", d_car, [120, 160, 464], invertir=True)

    doc.build(el, onFirstPage=_fondo_oscuro_pdf, onLaterPages=_fondo_oscuro_pdf, canvasmaker=NumberedCanvasOscuro)
    buffer.seek(0)
    return buffer.getvalue()

def generar_pdf_mi_personal(sup, anio, mes):
    """PDF de la pantalla MI PERSONAL del supervisor, tal cual se ve en la app: grilla del mes con sus colores,
    novedades registradas del mes y préstamos de vigiladores (enviados y recibidos)."""
    sup = str(sup).strip().upper()
    E = _estilos_pdf_oscuro()
    P = E["P"]
    periodo = f"{anio}-{mes:02d}"
    vig = vigiladores_de_supervisor(sup)
    dnis = set(vig["DNI"].tolist()) if not vig.empty else set()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), rightMargin=24, leftMargin=24, topMargin=24, bottomMargin=35,
                            title=f"Mi personal - {sup}")
    el = [Paragraph("<b>AION-YAROKU | MI PERSONAL</b>", E["tit"]),
          Paragraph(f"<b>{_xml_escape(sup)}</b> | {MESES_ES[mes - 1]} {anio} | Emisión: {obtener_hora_argentina()}", E["sub"])]

    pm = planificacion_mes(periodo).get(sup)
    if pm is not None and not pm.empty:
        el.append(Paragraph(f"Mis vigiladores ({len(pm)}) · {MESES_ES[mes - 1]} {anio}", E["h2"]))
        el.append(_LeyendaPlanPDF())
        el.append(Spacer(1, 4))
        el.append(_tabla_planificacion_pdf(pm, anio, mes))
    else:
        el.append(Paragraph("No hay vigiladores activos a cargo.", E["txt"]))

    # --- Novedades registradas (del mes, como se ven por defecto en la app) ---
    el.append(Paragraph("Novedades registradas", E["h2"]))
    nov = cargar_novedades_personal()
    cards = []
    if nov is not None and not nov.empty:
        nov = nov[nov["_DNI"].isin(dnis)].copy()
        primero = pd.Timestamp(anio, mes, 1)
        ultimo = pd.Timestamp(anio, mes, calendar.monthrange(anio, mes)[1])
        nov = nov[(nov["_DESDE"] <= ultimo) & (nov["_HASTA"] >= primero)].sort_values("_DESDE", ascending=False)
        for _, n in nov.iterrows():
            letra, bg, fg = TIPOS_NOVEDAD_PERSONAL.get(n["_TIPO"], ("?", "#555555", "#FFFFFF"))
            dias = int((n["_HASTA"] - n["_DESDE"]).days) + 1
            lineas = [(f"{n.get('OBJETIVO', '')} · {n['_DESDE'].strftime('%d/%m/%Y')} al {n['_HASTA'].strftime('%d/%m/%Y')} ({dias} {'día' if dias == 1 else 'días'})", P["label"], 7)]
            obs = str(n.get("OBSERVACION", "") or "").strip()
            if obs:
                lineas.append(("Obs.: " + obs, P["suave"], 7))
            rp, rf = str(n.get("REGISTRADO_POR", "") or "").strip(), _fmt_fecha_hora(n.get("FECHA_REGISTRO", ""))
            if rp or rf:
                lineas.append(("Registrada por " + (rp or "---") + ((" · " + rf) if rf else ""), "#6B7487", 6.5))
            mp, mf = str(n.get("MODIFICADO_POR", "") or "").strip(), _fmt_fecha_hora(n.get("FECHA_MODIFICACION", ""))
            if mp or mf:
                lineas.append(("Modificada por " + (mp or "---") + ((" · " + mf) if mf else ""), "#E0A458", 6.5))
            cards.append(_TarjetaLineasPDF(bg, str(n.get("VIGILADOR", "")), (f"{letra} · {n['_TIPO']}", bg, fg, True), lineas))
    if cards:
        el.append(_grilla_dos_columnas(cards))
    else:
        el.append(Paragraph("No hay novedades registradas para este mes.", E["txt"]))

    # --- Préstamos enviados y recibidos ---
    el.append(Paragraph("Préstamos de vigiladores (enviados y recibidos)", E["h2"]))
    pr_all = cargar_prestamos()
    pr_mios = pr_all[(pr_all["_ORIG"] == sup) | (pr_all["_DEST"] == sup)] if pr_all is not None and not pr_all.empty else pd.DataFrame()
    if pr_mios.empty:
        el.append(Paragraph("Todavía no hay préstamos registrados.", E["txt"]))
    else:
        hoy_d = datetime.now(pytz.timezone("America/Argentina/Buenos_Aires"))
        hoy_ts = pd.Timestamp(hoy_d.year, hoy_d.month, hoy_d.day)
        pr_mios = pr_mios.sort_values("_DESDE", ascending=False)

        def cards_prestamos(df_p):
            out = []
            for _, p in df_p.iterrows():
                if p["_ESTADO"] == "ANULADO":
                    etiqueta, color = "ANULADO", "#7C869A"
                elif p["_HASTA"] < hoy_ts:
                    etiqueta, color = "FINALIZADO", "#7C869A"
                elif p["_DESDE"] > hoy_ts:
                    etiqueta, color = "PROGRAMADO", "#5BC0CE"
                else:
                    etiqueta, color = "EN CURSO", "#26A69A"
                obj_o, obj_d = str(p.get("OBJETIVO_ORIGEN", "") or "").strip(), str(p.get("OBJETIVO_DESTINO", "") or "").strip()
                motivo, por = str(p.get("MOTIVO", "") or "").strip(), str(p.get("REGISTRADO_POR", "") or "").strip()
                fec = _fmt_fecha_hora(p.get("FECHA_REGISTRO", ""))
                dias = int((p["_HASTA"] - p["_DESDE"]).days) + 1
                lineas = [("De " + p["_ORIG"] + ((" (" + obj_o + ")") if obj_o else "") + " > " + p["_DEST"] + ((" · " + obj_d) if obj_d else ""), P["suave"], 7),
                          (p["_DESDE"].strftime("%d/%m/%Y") + " al " + p["_HASTA"].strftime("%d/%m/%Y") + f" ({dias} {'día' if dias == 1 else 'días'})" +
                           ((" · Motivo: " + motivo) if motivo else ""), P["label"], 7),
                          ("Registrado por " + (por or "---") + ((" · " + fec) if fec else ""), "#6B7487", 6.5)]
                anul, fec_a = str(p.get("ANULADO_POR", "") or "").strip(), _fmt_fecha_hora(p.get("FECHA_ANULACION", ""))
                if anul or fec_a:
                    lineas.append(("Anulado por " + (anul or "---") + ((" · " + fec_a) if fec_a else ""), "#E0A458", 6.5))
                out.append(_TarjetaLineasPDF(color, str(p.get("VIGILADOR", "")), (etiqueta, color, color, False), lineas))
            return out
        enviados, recibidos = pr_mios[pr_mios["_ORIG"] == sup], pr_mios[pr_mios["_DEST"] == sup]
        el.append(Paragraph("Que yo presté", E["h3"]))
        el.append(_grilla_dos_columnas(cards_prestamos(enviados)) if not enviados.empty else Paragraph("No prestaste vigiladores.", E["txt"]))
        el.append(Paragraph("Que me prestaron", E["h3"]))
        el.append(_grilla_dos_columnas(cards_prestamos(recibidos)) if not recibidos.empty else Paragraph("No te prestaron vigiladores.", E["txt"]))

    doc.build(el, onFirstPage=_fondo_oscuro_pdf, onLaterPages=_fondo_oscuro_pdf, canvasmaker=NumberedCanvasOscuro)
    buffer.seek(0)
    return buffer.getvalue()


def mostrar_reporte_tactico_integral(sup, key_suffix=""):
    """Mismo Tablero de Auditoría que ve el Jefe de Operaciones / Gerencia (jornada, permanencia QR, vista previa
    del reporte y PDF completo), para un supervisor. Lo usa Monitoreo."""
    d = datos_reporte_integral_supervisor(sup)
    sup_txt = d["sup_nombre"]
    st.markdown(f"### 🛡️ REPORTE TÁCTICO INTEGRAL: **{sup_txt}**")

    c_j1, c_j2, c_j3 = st.columns(3)
    c_j1.metric("🚀 INICIO DE JORNADA", d["j_ini"])
    c_j2.metric("🏁 CIERRE DE JORNADA", d["j_fin"])
    c_j3.metric("⏳ TOTAL HORAS TRABAJADAS", d["j_tot"])

    if not d["d_perm"].empty:
        st.markdown("##### 📍 Detalle de Permanencia por Objetivo (Escaneos QR)")
        st.dataframe(d["d_perm"], use_container_width=True, hide_index=True)
    else:
        st.info("No hay registros de escaneos QR para este supervisor.")

    st.markdown("---")
    with st.expander(f"👁️ VISTA PREVIA DEL REPORTE TÁCTICO: {sup_txt}", expanded=True):
        st.markdown(f"**Supervisor:** {sup_txt} | **Emisión:** {obtener_hora_argentina()}")

        st.markdown("##### ⏱️ Control de Jornada y Horas Trabajadas")
        st.dataframe(pd.DataFrame({"INICIO DE JORNADA": [d["j_ini"]], "CIERRE DE JORNADA": [d["j_fin"]],
                                   "TOTAL HORAS TRABAJADAS": [d["j_tot"]]}), use_container_width=True, hide_index=True)

        st.markdown("##### 📍 Detalle de Permanencia por Objetivo (Escaneos QR)")
        if not d["d_perm"].empty:
            st.dataframe(d["d_perm"], use_container_width=True, hide_index=True)
        else:
            st.info("Sin registros QR en este periodo.")

        st.markdown("##### 📋 Fichaje de Vigiladores")
        if not d["d_fich"].empty:
            st.dataframe(d["d_fich"], use_container_width=True, hide_index=True)
        else:
            st.info("Sin fichajes registrados.")

        st.markdown("##### 🔄 Relevos de Vigiladores")
        if not d["d_rel"].empty:
            st.dataframe(d["d_rel"], use_container_width=True, hide_index=True)
        else:
            st.info("Sin relevos registrados.")

        st.markdown("##### 🛰️ Seguimiento de Rondas de Vigiladores")
        if not d["d_rec"].empty:
            mostrar_tabla_rondas(d["d_rec"])
        else:
            st.info("Sin rondas registradas.")

        st.markdown("##### 🚨 Pánicos S.O.S de Supervisor")
        if not d["d_psup"].empty:
            st.dataframe(d["d_psup"].iloc[::-1], use_container_width=True, hide_index=True)
        else:
            st.info("Sin pánicos de supervisor.")

        st.markdown("##### 🚨 Pánicos S.O.S de Vigiladores")
        if not d["d_pvig"].empty:
            df_pv = d["d_pvig"].copy()
            df_pv["TURNO VIGILADOR"] = [determinar_turno_activo(str(f.get("FECHA", ""))) for _, f in df_pv.iterrows()]
            st.dataframe(df_pv.iloc[::-1], use_container_width=True, hide_index=True)
        else:
            st.info("Sin pánicos de vigiladores.")

        if d["tot_s_cnt"] > 0 or d["tot_v_cnt"] > 0 or not d["d_alt"].empty:
            st.markdown("##### ⚠️ Alertas Operativas")
            if d["tot_s_cnt"] > 0:
                st.markdown(f"• TOTAL ALERTAS DE SUPERVISOR: **{d['tot_s_cnt']}**")
            if d["tot_v_cnt"] > 0:
                st.markdown(f"• TOTAL ALERTAS DE VIGILADOR: **{d['tot_v_cnt']}**")
            if not d["d_alt"].empty:
                st.dataframe(d["d_alt"], use_container_width=True, hide_index=True)

        st.markdown("##### 🚗 Control de Flota")
        if not d["d_flota"].empty:
            st.dataframe(d["d_flota"], use_container_width=True, hide_index=True)
        else:
            st.info("Sin registros de flota.")

        st.markdown("##### 🔁 Traspasos de Objetivos")
        if not d["d_tras"].empty:
            st.dataframe(d["d_tras"].iloc[::-1], use_container_width=True, hide_index=True)
        else:
            st.info("Sin traspasos de objetivos.")

        st.markdown("##### 📋 Cargas Tácticas")
        if not d["d_car"].empty:
            st.dataframe(d["d_car"].iloc[::-1], use_container_width=True, hide_index=True)
        else:
            st.info("Sin cargas tácticas.")

    st.markdown("---")
    try:
        st.download_button(
            label=f"📥 DESCARGAR REPORTE TÁCTICO INTEGRAL (PDF COMPLETO) - {sup_txt}",
            data=generar_pdf_integral_supervisor(**d),
            file_name=f"reporte_tactico_integral_{sup_txt.replace(' ', '_')}.pdf",
            mime="application/pdf",
            key=f"btn_pdf_integral_{key_suffix}_{sup_txt}",
            use_container_width=True
        )
    except Exception as e_pdf:
        st.warning(f"No se pudo preparar el PDF de {sup_txt}: {e_pdf}")

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

        c1m, c2m, c3m = st.columns(3)
        c1m.metric("🚫 AUSENTES (vigiladores)", int(vista["AUSENTE"].sum()))
        c2m.metric("🛌 EN FRANCO (vigiladores)", int(vista["FRANCO"].sum()))
        c3m.metric("🤝 PRESTADOS (vigiladores)", int(vista["PRÉSTAMO"].sum()))

        # PDF único: tarjeta de cada supervisor + horas por vigilador + objetivos + vigiladores a cargo + comparativo
        try:
            pdf_rel = generar_pdf_relevamiento_visual(vista, detalle, personal, actividad, vigs, anio, mes)
            st.download_button("📥 DESCARGAR RELEVAMIENTO COMPLETO (PDF)", data=pdf_rel,
                               file_name=f"relevamiento_supervisores_{periodo}.pdf", mime="application/pdf",
                               use_container_width=True, key=f"{key_prefix}_pdf")
        except Exception as e_pdf_rel:
            st.warning(f"No se pudo preparar el PDF del relevamiento: {e_pdf_rel}")

        st.markdown("##### 🛡️ POR SUPERVISOR")
        for _, r in vista.iterrows():
            s = r["SUPERVISOR"]
            st.markdown(_tarjeta_supervisor_html(r, actividad.get(s, set()), anio, mes, vigs.get(s)), unsafe_allow_html=True)
            if len(vista) > 1:
                try:
                    _pdf_uno = generar_pdf_relevamiento_visual(vista[vista["SUPERVISOR"] == s], detalle, personal, actividad, vigs, anio, mes,
                                                               incluir_comparativo=False)
                    st.download_button(f"📥 DESCARGAR PDF DE {s}", data=_pdf_uno,
                                       file_name=f"relevamiento_{str(s).replace(' ', '_')}_{periodo}.pdf", mime="application/pdf",
                                       use_container_width=True, key=f"{key_prefix}_pdf_{s}")
                except Exception as e_pdf_uno:
                    st.warning(f"No se pudo preparar el PDF de {s}: {e_pdf_uno}")
            with st.expander("Ver detalle de objetivos y personal"):
                if s in vigs and not vigs[s].empty:
                    st.markdown("**Horas por vigilador**")
                    st.markdown(_detalle_vigiladores_html(vigs[s]), unsafe_allow_html=True)
                st.markdown("**Objetivos**")
                st.markdown(_detalle_objetivos_html(detalle[s]), unsafe_allow_html=True)
                if s in personal:
                    st.markdown(f"**Vigiladores a cargo ({r['VIGILADORES']})**")
                    st.markdown(leyenda_planificacion_html(), unsafe_allow_html=True)
                    st.markdown(grilla_planificacion_html(personal[s], anio, mes), unsafe_allow_html=True)

        with st.expander("📋 COMPARATIVO DE TODOS LOS SUPERVISORES"):
            st.markdown(_comparativo_supervisores_html(vista), unsafe_allow_html=True)
        try:
            st.download_button("📥 DESCARGAR RELEVAMIENTO COMPLETO (PDF)", data=pdf_rel,
                               file_name=f"relevamiento_supervisores_{periodo}.pdf", mime="application/pdf",
                               use_container_width=True, key=f"{key_prefix}_pdf_final")
        except Exception:
            pass

def mostrar_boton_planificacion():
    if st.session_state.get("rol_sel") not in ["JEFE DE OPERACIONES", "GERENCIA"]:
        return
    st.markdown("---")
    en_rel = st.session_state.get("ver_planificacion", False)
    if st.button("⬅️ VOLVER AL COMANDO" if en_rel else "📊 RELEVAMIENTO MENSUAL",
                 use_container_width=True, key="btn_planificacion_sidebar"):
        st.session_state.ver_planificacion = not en_rel
        st.rerun()

def mostrar_boton_personal_supervisor():
    if st.session_state.get("rol_sel") != "SUPERVISOR" or not st.session_state.get("sup_autenticado"):
        return
    st.markdown("---")
    activo = st.session_state.get("ver_personal_sup", False)
    if st.button("⬅️ VOLVER A MI ESTACIÓN" if activo else "👥 MI PERSONAL",
                 use_container_width=True, key="btn_personal_sup_sidebar"):
        st.session_state.ver_personal_sup = not activo
        st.rerun()

def mostrar_landing():
    aplicar_identidad_alfa()
    st.markdown('<div class="contenedor-logo-central"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" class="logo-phoenix"></div>', unsafe_allow_html=True)
    st.markdown('<div class="estacion-titulo">AION-YAROKU | COMMAND</div>', unsafe_allow_html=True)
     
    modo = st.radio("Acceso al Sistema:", ["Iniciar Sesión", "Crear Cuenta"], horizontal=True, key="radio_modo")
     
    dni_vig_reg = ""
    obj_vig_reg = ""

    roles_registro = ["VIGILADOR", "MONITOREO", "JEFE DE OPERACIONES", "GERENCIA", "SUPERVISOR"]
    rol_usuario = st.selectbox("Selección del Rol", roles_registro, key="r")

    _et_user, _et_pass = "Usuario (Apellido y Nombre)", "Contraseña (Número de Legajo)"

    with st.form("form_acceso_real"):
        user = st.text_input(_et_user, key="u")
        password = st.text_input(_et_pass, type="password", key="p")

        if modo == "Crear Cuenta":
            if rol_usuario == "VIGILADOR":
                dni_vig_reg = st.text_input("DNI", key="dni_reg")

            _df_obj_login = cargar_objetivos()
            _lista_obj_login = sorted(_df_obj_login['OBJETIVO'].astype(str).str.strip().str.upper().unique().tolist()) if not _df_obj_login.empty else []
            if rol_usuario == "VIGILADOR":
                if _lista_obj_login:
                    obj_vig_reg = st.selectbox("Objetivo", _lista_obj_login, key="ov_reg")
            else:
                st.selectbox("Objetivo", ["NO APLICA PARA ESTE ROL"], key="ov_reg_off", disabled=True)

        btn_texto = "ENTRAR" if modo == "Iniciar Sesión" else "REGISTRARSE"
         
        if st.form_submit_button(btn_texto):
            user_limpio = " ".join(user.strip().upper().split())
            pass_limpio = password.strip()
             
            if modo == "Iniciar Sesión" and user_limpio == "ADMIN" and pass_limpio == "aion2026":
                st.session_state.usuario_logueado = True
                st.session_state.user_sel = "ADMIN CENTRAL"
                st.session_state.rol_sel = "ADMINISTRADOR"
                st.session_state.admin_autenticado = True
                st.session_state.sup_autenticado = False
                sincronizar_url_sesion()
                st.rerun()
                 
            elif modo == "Iniciar Sesión" and rol_usuario == "VIGILADOR":
                df_pad = leer_matriz_nube("PADRON VIGILADORES")
                fila_vig = pd.DataFrame()
                if user_limpio and pass_limpio and not df_pad.empty and 'NOMBRE' in df_pad.columns and 'LEGAJO' in df_pad.columns:
                    fila_vig = df_pad[
                        (col_texto(df_pad, 'NOMBRE').str.upper().str.split().str.join(" ") == user_limpio) &
                        (col_texto(df_pad, 'LEGAJO').str.strip().str.upper() == pass_limpio.upper())
                    ]
                if not fila_vig.empty and str(fila_vig.iloc[0].get('ESTADO', '')).strip().upper() == "ACTIVO":
                    nombre_vig = str(fila_vig.iloc[0].get('NOMBRE', user_limpio)).strip().upper()
                    dni_vig = "".join(ch for ch in str(fila_vig.iloc[0].get('DNI', '')) if ch.isdigit())
                    st.session_state.usuario_logueado = True
                    st.session_state.user_sel = nombre_vig
                    st.session_state.rol_sel = "VIGILADOR"
                    st.session_state.dni_vigilador = dni_vig
                    st.session_state.v_nombre_completo = nombre_vig
                    st.session_state.legajo_vigilador = str(fila_vig.iloc[0].get('LEGAJO', '')).strip()
                    st.session_state.sup_autenticado = False
                    st.session_state.admin_autenticado = False
                    sincronizar_url_sesion()
                    st.rerun()
                else:
                    st.error("❌ Apellido y nombre o legajo incorrectos, o cuenta aún no habilitada.")
                 
            elif modo == "Iniciar Sesión":
                df_usuarios = leer_matriz_nube("USUARIOS")
                usuario_ok = pd.DataFrame()
                if not df_usuarios.empty and 'USUARIO' in df_usuarios.columns and 'CONTRASEÑA' in df_usuarios.columns:
                    usuario_ok = df_usuarios[
                        (col_texto(df_usuarios, 'USUARIO').str.upper().str.split().str.join(" ") == user_limpio) & 
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
                dni_reg = "".join(ch for ch in dni_vig_reg if ch.isdigit())
                nombre_reg = user_limpio
                legajo_reg = pass_limpio.upper()
                if not dni_reg or not nombre_reg or not legajo_reg or not obj_vig_reg:
                    st.warning("⚠️ Complete apellido y nombre (usuario), legajo (contraseña), DNI y seleccione su objetivo.")
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
                nombre_reg2 = user_limpio
                legajo_reg2 = password.strip().upper()
                if not user.strip() or not password.strip():
                    st.warning("⚠️ Complete su apellido y nombre (usuario) y su número de legajo (contraseña).")
                else:
                    exito_reg = escribir_registro_nube("USUARIOS", [
                        user_limpio, password.strip(), nombre_reg2,
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

import centro_supervisor
centro_supervisor.instalar(globals())

df_objetivos = cargar_objetivos()
LISTA_SUPS_TACTICOS = obtener_lista_supervisores_dinamica()

def _perfil_visible():
    """Nombre y legajo para mostrar en el panel lateral. El usuario interno (DNI) no cambia: solo se muestra el nombre."""
    ss = st.session_state
    nombre, legajo = "", ""
    if ss.get("rol_sel") == "VIGILADOR":
        nombre = str(ss.get("v_nombre_completo", "") or "").strip()
        legajo = str(ss.get("legajo_vigilador", "") or "").strip()
    if ss.get("rol_sel") == "VIGILADOR" and not legajo:
        try:
            df_p = leer_matriz_nube("PADRON VIGILADORES")
            if not df_p.empty and "NOMBRE" in df_p.columns and "LEGAJO" in df_p.columns:
                fp = df_p[col_texto(df_p, "NOMBRE").str.upper().str.split().str.join(" ") == str(ss.get("user_sel", "")).strip().upper()]
                if not fp.empty:
                    legajo = str(fp.iloc[0].get("LEGAJO", "") or "").strip()
        except Exception:
            pass
    if not nombre:
        try:
            df_u = leer_matriz_nube("USUARIOS")
            if not df_u.empty and "USUARIO" in df_u.columns:
                f = df_u[col_texto(df_u, "USUARIO").str.strip().str.upper() == str(ss.get("user_sel", "")).strip().upper()]
                if not f.empty:
                    col_n = "APELLIDO Y NOMBRE" if "APELLIDO Y NOMBRE" in df_u.columns else ("NOMBRE" if "NOMBRE" in df_u.columns else None)
                    if col_n:
                        nombre = str(f.iloc[0].get(col_n, "") or "").strip().upper()
                    if "LEGAJO" in df_u.columns and not legajo:
                        legajo = str(f.iloc[0].get("LEGAJO", "") or "").strip()
        except Exception:
            pass
    return (nombre or str(ss.get("user_sel", ""))), legajo

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
        mostrar_boton_personal_supervisor()
        mostrar_calendario_sidebar()
        mostrar_seguimiento_sidebar()

        st.markdown("---")
        if st.button("🚪 CERRAR SESIÓN", use_container_width=True):
            st.session_state.ver_personal_sup = False
            st.session_state.usuario_logueado = False
            st.session_state.pop("turno_vig_activo", None)
            st.query_params.clear()
            st.rerun()
else:
    with st.sidebar:
        st.markdown('<div class="contenedor-logo-sidebar"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" style="width:180px; border:1px solid #00e5ff; border-radius:4px;"></div>', unsafe_allow_html=True)
        st.markdown("---")
        st.markdown(f"**PERFIL:** {st.session_state.rol_sel}")
        _nom_perfil, _leg_perfil = _perfil_visible()
        st.markdown(f"**USUARIO:** {_nom_perfil}")
        if _leg_perfil:
            st.markdown(f"**LEGAJO:** {_leg_perfil}")
        
        mostrar_notificaciones_sidebar()
        mostrar_boton_planificacion()
        mostrar_boton_personal_supervisor()
        mostrar_calendario_sidebar()
        mostrar_seguimiento_sidebar()
            
        st.markdown("---")
        if vigilador_turno_activo():
            st.warning("🔒 Tenés un turno en curso. Para cerrar sesión primero finalizá tu turno en la solapa 🏁 FINALIZAR TURNO.")
            st.button("🚪 CERRAR SESIÓN", use_container_width=True, disabled=True, key="btn_logout_bloqueado")
        elif st.button("🚪 CERRAR SESIÓN", use_container_width=True):
            st.session_state.ver_personal_sup = False
            st.session_state.usuario_logueado = False
            st.session_state.pop("turno_vig_activo", None)
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

if (st.session_state.rol_sel == "SUPERVISOR" and st.session_state.get("sup_autenticado")
        and st.session_state.get("ver_personal_sup", False)):
    renderizar_personal_supervisor(st.session_state.user_sel)
    st.stop()

centro_supervisor.enrutar()

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
    objetivos_sin_ubicar = []
    if not df_objetivos.empty:
        df_objetivos.columns = df_objetivos.columns.str.strip().str.upper()
        with st.spinner("Ubicando objetivos en el mapa..."):
            _df_ubicados = con_coordenadas(df_objetivos)
        objetivos_sin_ubicar = _df_ubicados[_df_ubicados['LATITUD'].isna() | _df_ubicados['LONGITUD'].isna()]['OBJETIVO'].astype(str).tolist()
        df_mapa_monitoreo = _df_ubicados.dropna(subset=['LATITUD', 'LONGITUD']).copy()

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
    alarma_panico_sonora("MONITOREO", st.session_state.user_sel)

    col2.metric("📡 RED", "OPERATIVA")
    col3.metric("👤 OPERADOR", f"{st.session_state.user_sel}")
     
    with col4.container():
        renderizar_reloj_fluido()

    total_nuevos = contar_mensajes_nuevos()

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
         
        if obj_seleccionado != "MOSTRAR TODO" and not df_mapa_filtrado_sup.empty:
            datos_obj = df_mapa_filtrado_sup[df_mapa_filtrado_sup['OBJETIVO'] == obj_seleccionado].iloc[0]
            com_mon = comisaria_para_objetivo(datos_obj)
            res_mon = _resumen_comisaria(com_mon)
            with col_sel2:
                st.metric(label="👮 COMISARÍA MÁS CERCANA", value=res_mon["nombre"])
                if com_mon:
                    st.caption(f"Distancia estimada: {res_mon['distancia']} Km")
                    url_gmaps_monitoreo = f"https://www.google.com/maps/dir/?api=1&origin={com_mon['lat']},{com_mon['lon']}&destination={datos_obj['LATITUD']},{datos_obj['LONGITUD']}&travelmode=driving"
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

            comisarias_en_panico = {}
            panicos_sin_comisaria = []

            for _, r in df_mapa_filtrado_sup.iterrows():
                obj_nombre = str(r['OBJETIVO']).strip().upper()
                es_panico = obj_nombre in lista_objetivos_en_panico
                es_el_seleccionado = (obj_nombre == str(obj_seleccionado).strip().upper())
                aprox_txt = "" if bool(r.get('UBICACION_EXACTA', True)) else " | 📍 UBICACIÓN APROXIMADA (revisar altura)"

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

                    com = comisaria_para_objetivo(r)
                    if com is not None:
                        comisarias_en_panico[str(com['nombre'])] = com
                        ruta = obtener_ruta_calles_osrm(r['LATITUD'], r['LONGITUD'], com['lat'], com['lon'])
                        folium.PolyLine(locations=ruta, color="#000000", weight=5, opacity=0.4).add_to(m_mon)
                        folium.PolyLine(locations=ruta, color="#39FF14", weight=4, opacity=0.8).add_to(m_mon)
                    else:
                        panicos_sin_comisaria.append(obj_nombre)

                elif es_el_seleccionado:
                    folium.CircleMarker(
                        location=[r['LATITUD'], r['LONGITUD']], radius=10, color="#FFFFFF",
                        fill=True, fill_color="#00E5FF", fill_opacity=0.9,
                        tooltip=f"🎯 {obj_nombre} | 👤 SUP: {r.get('SUPERVISOR', 'N/A')}{aprox_txt}"
                    ).add_to(m_mon)
                else:
                    folium.CircleMarker(
                        location=[r['LATITUD'], r['LONGITUD']], radius=7, color="#00E5FF", fill=True,
                        tooltip=f"🎯 {obj_nombre} | 👤 SUP: {r.get('SUPERVISOR', 'N/A')}{aprox_txt}"
                    ).add_to(m_mon)

            for nombre_com, c in comisarias_en_panico.items():
                folium.Marker(
                    location=[c['lat'], c['lon']],
                    tooltip=f"👮 {nombre_com} 🌟 [MÁS CERCANA AL PÁNICO]",
                    icon=folium.DivIcon(html="""<div style="font-size:26px;color:#FFD600;text-shadow:0 0 10px #FFD600;"><i class="fa fa-shield"></i></div>""")
                ).add_to(m_mon)

            st_folium(m_mon, use_container_width=True, height=500, key="mapa_monitoreo_radar_tactico", returned_objects=[])
            if panicos_sin_comisaria:
                st.warning("⚠️ Pánico en " + ", ".join(panicos_sin_comisaria) + ": no se pudo determinar la comisaría más cercana. Motivo: "
                           + f"{_almacen_geo().get('com_error', 'sin datos')}.")
            if objetivos_sin_ubicar:
                st.caption("⚠️ No se pudo ubicar en el mapa: " + ", ".join(objetivos_sin_ubicar) + ". Revisá calle, altura y localidad.")
        else:
            m_vacio = folium.Map(location=[-34.65, -58.5], zoom_start=10, max_zoom=19, tiles="OpenStreetMap")
            m_vacio.get_root().header.add_child(Element("<style>.leaflet-container { background: #262626 !important; } .leaflet-tile-pane { filter: invert(100%) hue-rotate(180deg) grayscale(100%) brightness(0.8) contrast(1.25); }</style>"))
            st_folium(m_vacio, use_container_width=True, height=500, key="mapa_monitoreo_vacio", returned_objects=[])
            if df_objetivos.empty:
                st.warning("⚠️ No hay objetivos cargados todavía.")
            else:
                _det = "; ".join(f"{r['OBJETIVO']}: {r['CALLE']} {r['ALTURA']}, {r['LOCALIDAD']}" for _, r in df_objetivos.iterrows() if str(r['OBJETIVO']) in objetivos_sin_ubicar)
                st.warning("⚠️ No se pudo ubicar ningún objetivo en el mapa. Direcciones buscadas → " + _det
                           + f". Último motivo del servicio de mapas: {_almacen_geo().get('error', 'sin datos')}.")
                if st.button("🔁 REINTENTAR UBICACIÓN DE OBJETIVOS", key="btn_reintentar_geo"):
                    _almacen_geo()["fallo"].clear()
                    st.rerun()
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
                    mostrar_reporte_tactico_integral(sup_seleccionado_mono, key_suffix=f"mon{idx_p}")
        else:
            st.info("No hay supervisores con registros activos en el sistema todavía.")

# =========================================================================
# ROL: SUPERVISOR
# =========================================================================
elif st.session_state.rol_sel == "SUPERVISOR":
    if 'scan_n_sup' not in st.session_state:
        st.session_state.scan_n_sup = 0

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
                fila_obj_s = None
                if not df_objetivos.empty:
                    filtro_sup_obj = df_objetivos[df_objetivos['OBJETIVO'] == obj_actual]
                    if not filtro_sup_obj.empty:
                        fila_obj_s = filtro_sup_obj.iloc[0]
                res_s = _resumen_comisaria(comisaria_para_objetivo(fila_obj_s))

                exito = escribir_registro_nube("ALERTAS", [
                    obtener_hora_argentina(), st.session_state.user_sel, "PÁNICO", "PENDIENTE", obj_actual, st.session_state.user_sel
                ])
                if exito:
                    enviar_push_panico(st.session_state.user_sel, obj_actual, "")
                    st.error(f"🚨 ALERTA ENVIADA DESDE {obj_actual}")
                    st.session_state.alerta_activa_supervisor = {
                        "comisaria": res_s["nombre"],
                        "telefono": res_s["telefono"],
                        "distancia": res_s["distancia"]
                    }

        if 'alerta_activa_supervisor' in st.session_state:
            datos_s = st.session_state.alerta_activa_supervisor
            _dist_s = f" (~{datos_s['distancia']} KM)" if datos_s['distancia'] != "---" else ""
            _boton_s = f"""<div style="margin-top: 12px;">
                        <a href="tel:{datos_s['telefono']}" style="background-color: #1E293B; color: #94A3B8; padding: 10px 22px; border-radius: 6px; border: 1px solid #475569; font-family: 'Orbitron', sans-serif; font-weight: 500; font-size: 11px; text-decoration: none; display: inline-block; text-transform: uppercase; letter-spacing: 0.5px; text-align: center;">
                            📞 LLAMAR DIRECTAMENTE AHORA (<b style="unicode-bidi: bidi-override; direction: ltr; display: inline-block;">{datos_s['telefono']}</b>)
                        </a>
                    </div>""" if datos_s['telefono'] else ""
            st.markdown(f"""
                <div style="background: rgba(22, 27, 34, 0.6); border: 1px solid rgba(100, 116, 139, 0.3); border-radius: 8px; padding: 15px; margin-top: 12px; text-align: center; font-family: 'Rajdhani', sans-serif;">
                    <div style="font-family: 'Orbitron', sans-serif; color: #94A3B8; font-size: 13px; font-weight: 500; letter-spacing: 1px;">
                        🚨 EMERGENCIA ACTIVA - COMISARÍA JURISDICCIONAL REAL
                    </div>
                    <div style="color: #CBD5E1; font-size: 13px; margin-top: 6px;">
                        <b>{datos_s['comisaria']}</b>{_dist_s}
                    </div>
                    {_boton_s}
                </div>
            """, unsafe_allow_html=True)

        _n_msg_sup = contar_mensajes_nuevos()
        t_vis_qr, t_qr_rec_tab, t_mensajeria_sup, t_pres_sup = st.tabs([
            "Visita QR", "🧾 PUNTOS QR RECORRIDO",
            f"💬 MENSAJERÍA ({_n_msg_sup})" if _n_msg_sup else "💬 MENSAJERÍA", "📋 NOVEDADES Y RELEVOS"
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
                            (col_texto(df_jornadas_act, col_sup).str.strip().str.upper() == sup_activo_normalizado) & 
                            (col_texto(df_jornadas_act, col_obj).str.strip().str.upper() == obj_item.strip().upper()) &
                            (col_texto(df_jornadas_act, col_fec_hora).str.contains(fecha_hoy_str, na=False))
                        ]
                         
                        if not df_j_obj.empty:
                            inicios = df_j_obj[col_texto(df_j_obj, col_acc).str.strip().str.upper() == 'INICIO']
                            fines = df_j_obj[col_texto(df_j_obj, col_acc).str.strip().str.upper() == 'FIN']
                             
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
                st.info("Tu ubicación se toma en el instante del escaneo. Si no estás en el objetivo, el registro se rechaza.")

                tipo_mov_qr = st.radio("TIPO DE MOVIMIENTO QR:", ["INICIO (INGRESO)", "FIN (EGRESO)"], horizontal=True, key="radio_tipo_mov_qr")
                accion_str = "INICIO" if "INICIO" in tipo_mov_qr else "FIN"

                lectura_sup = visor_qr(key=f"scanner_tactico_{accion_str}_{st.session_state.scan_n_sup}")

                if st.session_state.ultimo_mensaje_qr:
                    st.success(st.session_state.ultimo_mensaje_qr)
                if st.session_state.get("error_qr_sup"):
                    st.error(st.session_state.error_qr_sup)

                if isinstance(lectura_sup, dict) and lectura_sup.get("ts") != st.session_state.get("_qr_ts_sup"):
                    st.session_state["_qr_ts_sup"] = lectura_sup.get("ts")
                    st.session_state.error_qr_sup = ""
                    txt_s = texto_qr(lectura_sup).upper()
                    ok_pos, msg_pos = validar_presencia_scan(lectura_sup, datos_sel.get('CALLE', ''), datos_sel.get('ALTURA', ''), datos_sel.get('LOCALIDAD', ''))
                    if not txt_s.startswith(f"AION-YAROKU-OBJ:{str(obj_select).upper()}"):
                        st.session_state.error_qr_sup = "❌ Ese QR no corresponde al objetivo seleccionado."
                        st.rerun()
                    elif not ok_pos:
                        st.session_state.error_qr_sup = f"❌ {msg_pos}"
                        st.rerun()
                    elif registrar_qr_supervisor(st.session_state.user_sel, obj_select, accion_str):
                        try:
                            escribir_registro_nube("NOVEDADES GUARDIA", [
                                obtener_hora_argentina(), obj_select,
                                f"SUPERVISIÓN QR VALIDADA ({accion_str}) - #{st.session_state.scan_n_sup + 1}",
                                "---", st.session_state.user_sel, "---", "PROCESADO", st.session_state.user_sel])
                        except Exception:
                            pass
                        n_int = st.session_state.scan_n_sup + 1
                        st.session_state.ultimo_mensaje_qr = (
                            f"✅ ¡INGRESO (INICIO) #{n_int} REGISTRADO PARA: {obj_select}!" if accion_str == "INICIO"
                            else f"🏁 ¡EGRESO (FIN) #{n_int} REGISTRADO PARA: {obj_select}!")
                        st.session_state.scan_n_sup += 1
                        sincronizar_url_sesion()
                        st.rerun()
                    else:
                        st.session_state.error_qr_sup = "❌ Error al registrar en la nube. Intente nuevamente."
                        st.rerun()

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
                    st.write(f"**Calle:** {datos_sel.get('CALLE', 'N/A')}")
                    st.write(f"**Altura:** {datos_sel.get('ALTURA', 'N/A')}")
                    st.write(f"**Localidad:** {datos_sel.get('LOCALIDAD', 'N/A')}")
                     
                    url_navegacion = url_destino_objetivo(datos_sel.get('CALLE', ''), datos_sel.get('ALTURA', ''), datos_sel.get('LOCALIDAD', ''))
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

        with t_qr_rec_tab:
            renderizar_generador_qr_recorrido(
                df_objetivos_filtrados['OBJETIVO'].unique() if not df_objetivos_filtrados.empty else [],
                "sup"
            )

        with t_mensajeria_sup:
            renderizar_mensajeria_global("SUPERVISOR")
         
        with t_pres_sup:
            st.markdown(f"#### 📱 MIS ESCANEOS QR REGISTRADOS EN CAMPO")
            df_qr_sup_base = leer_matriz_nube("REGISTRO QR SUPERVISORES")
            if not df_qr_sup_base.empty:
                df_qr_sup_base.columns = [str(c).strip().upper() for c in df_qr_sup_base.columns]
                col_sup_q = 'SUPERVISOR' if 'SUPERVISOR' in df_qr_sup_base.columns else df_qr_sup_base.columns[3]
                df_qr_sup_propio = df_qr_sup_base[col_texto(df_qr_sup_base, col_sup_q).str.strip().str.upper() == sup_activo_normalizado]
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

    nombre_vigilador_actual = st.session_state.get("v_nombre_completo", st.session_state.user_sel).upper()
    legajo_vigilador_actual = st.session_state.get("legajo_vigilador", "S/L")
     
    dni_vigilador_actual = st.session_state.get("dni_vigilador", "")
    if not dni_vigilador_actual:
        df_pad_rec = leer_matriz_nube("PADRON VIGILADORES")
        if not df_pad_rec.empty and {'DNI', 'NOMBRE'} <= set(df_pad_rec.columns):
            m_rec = df_pad_rec[col_texto(df_pad_rec, 'NOMBRE').str.strip().str.upper() == nombre_vigilador_actual]
            if not m_rec.empty:
                dni_vigilador_actual = "".join(ch for ch in str(m_rec.iloc[0]['DNI']) if ch.isdigit())
                st.session_state.dni_vigilador = dni_vigilador_actual
                st.session_state.legajo_vigilador = str(m_rec.iloc[0].get('LEGAJO', '')).strip()
                legajo_vigilador_actual = st.session_state.legajo_vigilador
    if not dni_vigilador_actual:
        dni_vigilador_actual = "".join(ch for ch in str(st.session_state.get("user_sel", "")) if ch.isdigit())
        st.session_state.dni_vigilador = dni_vigilador_actual

    total_nuevos = contar_mensajes_nuevos()

    label_msg = f"💬 MENSAJERÍA GLOBAL ({total_nuevos})" if total_nuevos > 0 else "💬 MENSAJERÍA GLOBAL"
     
    st.markdown(f"### 🛡️ PROTOCOLO DE EMERGENCIA")
    obj_detectado = st.session_state.get("obj_actual_vig", None)

    if obj_detectado:
        st.markdown(f"""
            <div style="background: rgba(25, 35, 30, 0.45); border: 1px solid rgba(60, 90, 75, 0.3); border-radius: 6px; padding: 10px; margin-bottom: 12px; font-family: 'Rajdhani', sans-serif; text-align: center;">
                <span style="color: #92B9A4; font-size: 13px; font-weight: 500; letter-spacing: 0.5px;">📍 OBJETIVO ACTIVO: <b>{obj_detectado}</b></span>
            </div>
        """, unsafe_allow_html=True)
        col_pv1, col_pv2, col_pv3 = st.columns([1, 1, 1])
        with col_pv2:
            if st.button("S.O.S\nPÁNICO", type="primary"):
                sup_asignado = "MONITOREO"
                fila_obj_v = None
                if not df_objetivos.empty:
                    filtro = df_objetivos[df_objetivos['OBJETIVO'] == obj_detectado]
                    if not filtro.empty:
                        sup_asignado = str(filtro['SUPERVISOR'].iloc[0]).strip()
                        fila_obj_v = filtro.iloc[0]
                res_v = _resumen_comisaria(comisaria_para_objetivo(fila_obj_v))

                st.session_state.alerta_activa_vigilador = {
                    "nombre": nombre_vigilador_actual,
                    "obj": obj_detectado,
                    "comisaria": res_v["nombre"],
                    "direccion": res_v["direccion"],
                    "telefono": res_v["telefono"],
                    "distancia": res_v["distancia"]
                }

                fecha = obtener_hora_argentina()
                escribir_registro_nube("ALERTAS", [fecha, nombre_vigilador_actual, "PÁNICO", "PENDIENTE", obj_detectado, sup_asignado])
                enviar_alerta_automatica("SISTEMA_VIGILADOR", obj_detectado, nombre_vigilador_actual, sup_asignado)
                st.error(f"🚨 ALERTA ENVIADA: {nombre_vigilador_actual} DESDE {obj_detectado}")

        if 'alerta_activa_vigilador' in st.session_state:
            datos_pan = st.session_state.alerta_activa_vigilador
            _dist_v = f" (~{datos_pan['distancia']} KM)" if datos_pan['distancia'] != "---" else ""
            _boton_v = f"""<div style="margin-top: 12px; text-align: center;">
                        <a href="tel:{datos_pan['telefono']}" style="background-color: #1E293B; color: #94A3B8; padding: 12px 24px; border-radius: 6px; border: 1px solid #475569; font-family: 'Orbitron', sans-serif; font-weight: 500; font-size: 11px; text-decoration: none; display: inline-block; text-transform: uppercase; letter-spacing: 0.5px; text-align: center;">
                            📞 LLAMAR A LA COMISARÍA (<b style="unicode-bidi: bidi-override; direction: ltr; display: inline-block;">{datos_pan['telefono']}</b>)
                        </a>
                    </div>""" if datos_pan['telefono'] else ""
            st.markdown(f"""
                <div style="background: rgba(22, 27, 34, 0.6); border: 1px solid rgba(100, 116, 139, 0.3); border-radius: 8px; padding: 15px; margin-top: 12px; font-family: 'Rajdhani', sans-serif;">
                    <div style="color: #94A3B8; font-family: 'Orbitron', sans-serif; font-size: 13px; font-weight: 500; letter-spacing: 1px; display: flex; align-items: center; justify-content: center; gap: 6px;">
                        🚨 ALERTA ENVIADA: DESDE {datos_pan['obj']}
                    </div>
                    <div style="color: #CBD5E1; font-size: 13px; margin-top: 8px; text-align: center;">
                        👮 <b>COMISARÍA:</b> {datos_pan['comisaria']}<br>
                        <b>Dirección:</b> {datos_pan['direccion']}{_dist_v}
                    </div>
                    {_boton_v}
                </div>
            """, unsafe_allow_html=True)
     
    st.markdown("---")
     
    if st.session_state.get("msg_ingreso_vig"):
        st.success(st.session_state.pop("msg_ingreso_vig"))

    turno_activo = vigilador_turno_activo()
    if turno_activo:
        tab_recorrido, tab_fin_turno, t_mensajeria = st.tabs(["🚶 RECORRIDO QR", "🏁 FINALIZAR TURNO", label_msg])
        tab_auto_ingreso = None
    else:
        tab_auto_ingreso, t_mensajeria = st.tabs(["🚀 INGRESO & RELEVO AUTOMÁTICO", label_msg])
        tab_recorrido = tab_fin_turno = None

    if st.session_state.get("nav_vig_pendiente") == "RECORRIDO":
        st.session_state.nav_vig_pendiente = None
        components.html("""
        <script>
        setTimeout(function(){
          var tabs = window.parent.document.querySelectorAll('button[data-baseweb="tab"]');
          for (var i = 0; i < tabs.length; i++) {
            if (tabs[i].innerText.indexOf("RECORRIDO QR") > -1) { tabs[i].click(); break; }
          }
        }, 400);
        </script>
        """, height=0)
  
    if tab_auto_ingreso is not None:
        with tab_auto_ingreso:
            st.markdown(f"### ⚡ ACCESO Y VALIDACIÓN: **{nombre_vigilador_actual}**")
            st.info("ℹ️ Al confirmar el objetivo y tomar la foto, el sistema registrará tu fichaje de ingreso, generará el relevo automático y te habilitará el módulo de recorridas.")

            with st.form(key="form_ingreso_automatico_vigilador", clear_on_submit=False):
                v_obj_auto = st.selectbox("SELECCIONAR OBJETIVO DE TURNO:", opciones_globales_obj)
                vig_saliente_auto = st.text_input("VIGILADOR SALIENTE (A QUIÉN RELEVAS):", value="").upper().strip()
                img_facial_auto = st.camera_input("📸 FOTO OBLIGATORIA DE VERIFICACIÓN (RECONOCIMIENTO FACIAL)")
             
                confirmar_ingreso = st.form_submit_button("🚀 CONFIRMAR INGRESO, FOTO Y RELEVO")
             
                if confirmar_ingreso:
                    if img_facial_auto is not None and v_obj_auto:
                        st.session_state.obj_actual_vig = v_obj_auto
                        sincronizar_url_sesion()
                        sup_responsable = df_objetivos[df_objetivos['OBJETIVO'] == v_obj_auto]['SUPERVISOR'].iloc[0] if not df_objetivos.empty else "N/A"
                     
                        fecha_hora_arg = obtener_hora_argentina()
                        fecha_hoy = fecha_hora_arg.split(" ")[0]
                        hora_actual = fecha_hora_arg.split(" ")[1]
                     
                        escribir_registro_nube("PRESENTISMO", [fecha_hoy, hora_actual, legajo_vigilador_actual, nombre_vigilador_actual, v_obj_auto, "INGRESO", "OK"])
                        escribir_registro_nube("NOVEDADES GUARDIA", [fecha_hora_arg, v_obj_auto, "MARCACIÓN_INGRESO", "---", nombre_vigilador_actual, legajo_vigilador_actual, "PROCESADO", sup_responsable])
                     
                        saliente_fmt = vig_saliente_auto if vig_saliente_auto else "PERSONAL ANTERIOR"
                        escribir_registro_nube("NOVEDADES GUARDIA", [fecha_hora_arg, v_obj_auto, "RELEVO DE TURNO", saliente_fmt, nombre_vigilador_actual, dni_vigilador_actual, "PROCESADO", sup_responsable])
                        escribir_registro_nube("VIGILADORES", [fecha_hoy, hora_actual, v_obj_auto, saliente_fmt, nombre_vigilador_actual, dni_vigilador_actual, sup_responsable, "RELEVO_AUTOMATICO"])
                     
                        st.session_state.turno_vig_activo = True
                        st.session_state.msg_ingreso_vig = f"✅ ¡RELEVO EXITOSO! Ingreso y foto registrados para {nombre_vigilador_actual} en {v_obj_auto}. Ya podés hacer tu recorridas."
                        st.session_state.nav_vig_pendiente = "RECORRIDO"
                        st.toast("✅ ¡Relevo exitoso!", icon="✅")
                        st.rerun()
                    else:
                        st.error("⚠️ Es obligatorio tomar la foto con la cámara para confirmar el ingreso.")

    if tab_recorrido is not None:
        with tab_recorrido:
            renderizar_recorrido_vigilador(
                st.session_state.get("obj_actual_vig", ""),
                nombre_vigilador_actual,
                dni_vigilador_actual
            )

    if tab_fin_turno is not None:
        with tab_fin_turno:
            st.markdown(f"### 🏁 FINALIZAR TURNO: **{nombre_vigilador_actual}**")
            ult_mov = _ultimo_mov_presentismo(nombre_vigilador_actual)
            obj_turno = (ult_mov or {}).get("objetivo") or st.session_state.get("obj_actual_vig", "")
            if ult_mov and ult_mov["tipo"] == "INGRESO":
                st.info(f"ℹ️ Turno iniciado el {ult_mov['fecha']} a las {ult_mov['hora'][:5]} hs en {ult_mov['objetivo']}.")
            st.warning("⚠️ Mientras tu turno esté en curso no podés cerrar sesión. Al finalizar se registra tu egreso.")
            conf_fin = st.checkbox("Confirmo que terminé mi turno y entregué el puesto.", key="chk_fin_turno")
            if st.button("🏁 FINALIZAR TURNO Y REGISTRAR EGRESO", use_container_width=True, disabled=not conf_fin, key="btn_fin_turno"):
                sup_fin = "N/A"
                if not df_objetivos.empty:
                    f_sup = df_objetivos[df_objetivos['OBJETIVO'] == obj_turno]
                    if not f_sup.empty:
                        sup_fin = f_sup['SUPERVISOR'].iloc[0]
                fh_fin = obtener_hora_argentina()
                if escribir_registro_nube("PRESENTISMO", [fh_fin.split(" ")[0], fh_fin.split(" ")[1], legajo_vigilador_actual, nombre_vigilador_actual, obj_turno, "EGRESO", "OK"]):
                    escribir_registro_nube("NOVEDADES GUARDIA", [fh_fin, obj_turno, "MARCACIÓN_EGRESO", "---", nombre_vigilador_actual, legajo_vigilador_actual, "PROCESADO", sup_fin])
                    st.session_state.turno_vig_activo = False
                    st.session_state.msg_ingreso_vig = f"🏁 Turno finalizado. Egreso registrado para {nombre_vigilador_actual}. Ya podés cerrar sesión."
                    st.toast("🏁 Turno finalizado", icon="🏁")
                    st.rerun()
                else:
                    st.error("❌ No se pudo registrar el egreso. Probá de nuevo.")

    with t_mensajeria:
        renderizar_mensajeria_global("VIGILADOR")
    st.markdown('</div>', unsafe_allow_html=True)

# =========================================================================
# ROL: JEFE DE OPERACIONES / GERENCIA
# =========================================================================
elif st.session_state.rol_sel in ["JEFE DE OPERACIONES", "GERENCIA"]:
    col1, col2, col3, col4 = st.columns(4)
     
    with col1.container():
        @st.fragment(run_every=5)
        def mostrar_sos():
            df_alertas = leer_matriz_nube("ALERTAS")
            df_pan_vig_jefe = df_alertas[
                (col_texto(df_alertas, 'TIPO').str.upper() == "PÁNICO") & 
                (col_texto(df_alertas, 'ESTADO').str.upper() == "PENDIENTE")
            ] if not df_alertas.empty and 'TIPO' in df_alertas.columns else pd.DataFrame()
            total_sos = len(df_pan_vig_jefe)
            st.metric("🚨 S.O.S ACTIVOS", total_sos)
        mostrar_sos()
    alarma_panico_sonora(st.session_state.rol_sel, st.session_state.user_sel, solo_cartel=True)

    col2.metric("📡 RED", "OPERATIVA")
    col3.metric("👤 USUARIO", f"{st.session_state.user_sel}")
     
    with col4.container():
        renderizar_reloj_fluido()

    total_nuevos = contar_mensajes_nuevos()
     
    label_msg = f"💬 MENSAJERÍA ({total_nuevos})" if total_nuevos > 0 else "💬 MENSAJERÍA"
     
    st.markdown(f'<h2 style="color:#00E5FF; font-family:\'Orbitron\'; font-size:24px;">Comando: {st.session_state.rol_sel}</h2>', unsafe_allow_html=True)
     
    t_mensajeria_jefe, t_ejecucion, t_tab_auditoria = st.tabs([label_msg, "Ejecución", "📍 TABLERO DE AUDITORÍA"])
     
    with t_mensajeria_jefe:
        renderizar_mensajeria_global(st.session_state.rol_sel)
         
    with t_ejecucion:
        if st.session_state.get("msg_servicio"):
            (st.success if st.session_state.msg_servicio[0] else st.error)(st.session_state.msg_servicio[1])
            del st.session_state["msg_servicio"]
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.subheader("ALTA DE SERVICIO / OBJETIVO")
            with st.form("form_alta_servicio_jefe", clear_on_submit=True):
                a_nom = st.text_input("Nombre del objetivo:")
                a_calle = st.text_input("Calle:")
                a_altura = st.text_input("Altura:")
                a_loc = st.text_input("Localidad:")
                a_sup = st.selectbox("Asignar al supervisor:", LISTA_SUPS_TACTICOS)
                if st.form_submit_button("🟢 DAR DE ALTA Y AVISAR AL SUPERVISOR"):
                    if not (a_nom.strip() and a_calle.strip() and a_altura.strip() and a_loc.strip() and a_sup):
                        st.session_state.msg_servicio = (False, "⚠️ Completá nombre del objetivo, calle, altura, localidad y supervisor.")
                    elif not a_altura.strip().isdigit():
                        st.session_state.msg_servicio = (False, "⚠️ La altura debe ser un número (ej: 1234).")
                    else:
                        ok_a, txt_a = alta_servicio(a_nom, a_calle, a_altura.strip(), a_loc, a_sup, "", st.session_state.user_sel)
                        if ok_a and not geocodificar_direccion(a_calle, a_altura.strip(), a_loc):
                            txt_a += " Ojo: no se pudo ubicar en el mapa; revisá calle, altura y localidad."
                        st.session_state.msg_servicio = (ok_a, ("✅ " if ok_a else "❌ ") + txt_a)
                    st.rerun()
        with col_g2:
            st.subheader("BAJA DE SERVICIO / OBJETIVO")
            objs_baja = sorted(df_objetivos['OBJETIVO'].astype(str).str.strip().str.upper().unique()) if not df_objetivos.empty else []
            sup_de_obj = {}
            if not df_objetivos.empty and 'SUPERVISOR' in df_objetivos.columns:
                sup_de_obj = dict(zip(df_objetivos['OBJETIVO'].astype(str).str.strip().str.upper(), df_objetivos['SUPERVISOR']))
            with st.form("form_baja_servicio_jefe", clear_on_submit=True):
                g_baja_obj = st.selectbox("Objetivo:", objs_baja, format_func=lambda o: f"{o}  (sup. {sup_de_obj.get(o, 'S/A')})")
                g_baja_mot = st.text_input("Motivo de la baja:")
                g_baja_ok = st.checkbox("Confirmo que quiero dar de baja este servicio")
                if st.form_submit_button("🔴 DAR DE BAJA Y AVISAR AL SUPERVISOR"):
                    if not (g_baja_obj and g_baja_mot.strip() and g_baja_ok):
                        st.session_state.msg_servicio = (False, "⚠️ Elegí el objetivo, escribí el motivo y tildá la confirmación.")
                    else:
                        ok_b, txt_b = baja_servicio(g_baja_obj, g_baja_mot, st.session_state.user_sel)
                        st.session_state.msg_servicio = (ok_b, ("✅ " if ok_b else "❌ ") + txt_b)
                    st.rerun()
     
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
                for s in col_texto(df_qr_aud, col_sup_q).dropna().str.strip().str.upper():
                    if s and s != "NAN": supervisores_en_qr_set.add(s)

        if not df_jornada_aud.empty:
            df_jornada_aud.columns = [str(c).strip().upper() for c in df_jornada_aud.columns]
            col_sup_j = 'SUPERVISOR' if 'SUPERVISOR' in df_jornada_aud.columns else df_jornada_aud.columns[1]
            if col_sup_j in df_jornada_aud.columns:
                for s in col_texto(df_jornada_aud, col_sup_j).dropna().str.strip().str.upper():
                    if s and s != "NAN": supervisores_en_qr_set.add(s)

        if not df_flota_aud.empty:
            df_flota_aud.columns = [str(c).strip().upper() for c in df_flota_aud.columns]
            col_sup_f = 'SUPERVISOR' if 'SUPERVISOR' in df_flota_aud.columns else df_flota_aud.columns[1]
            if col_sup_f in df_flota_aud.columns:
                for s in col_texto(df_flota_aud, col_sup_f).dropna().str.strip().str.upper():
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
                         
                        df_sup_jor = df_jornada_aud[col_texto(df_jornada_aud, col_s_j).str.strip().str.upper() == str(sup_seleccionado_jefe).strip().upper()]
                        if not df_sup_jor.empty:
                            inicios_jor = df_sup_jor[col_texto(df_sup_jor, col_a_j).str.strip().str.upper() == 'INICIO']
                            fines_jor = df_sup_jor[col_texto(df_sup_jor, col_a_j).str.strip().str.upper() == 'FIN']
                             
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

                    df_sup_qrs = df_qr_aud[col_texto(df_qr_aud, col_sup_q).str.strip().str.upper() == str(sup_seleccionado_jefe).strip().upper()] if not df_qr_aud.empty and col_sup_q in df_qr_aud.columns else pd.DataFrame()
                     
                    df_tabla_permanencia = pd.DataFrame()
                    if not df_sup_qrs.empty:
                        df_sup_qrs.columns = [str(c).strip().upper() for c in df_sup_qrs.columns]
                        col_fh_qr = df_sup_qrs.columns[0]
                        col_obj_qr = df_sup_qrs.columns[1]
                        col_acc_qr = df_sup_qrs.columns[2]
                         
                        lista_resumen_permanencia = []
                        objetivos_visitados_set = col_texto(df_sup_qrs, col_obj_qr).dropna().str.strip().str.upper().unique()
                         
                        for obj_v in objetivos_visitados_set:
                            df_obj_reg = df_sup_qrs[col_texto(df_sup_qrs, col_obj_qr).str.strip().str.upper() == obj_v]
                            inicios_obj = df_obj_reg[col_texto(df_obj_reg, col_acc_qr).str.strip().str.upper() == 'INICIO']
                            fines_obj = df_obj_reg[col_texto(df_obj_reg, col_acc_qr).str.strip().str.upper() == 'FIN']
                             
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
                     
                    objs_del_sup = [o.strip().upper() for o in df_objetivos[col_texto(df_objetivos, 'SUPERVISOR').str.strip().str.upper() == str(sup_seleccionado_jefe).strip().upper()]['OBJETIVO'].tolist()] if not df_objetivos.empty else []
                     
                    df_fich_filtrado = pd.DataFrame()
                    if not df_nov_aud.empty and len(objs_del_sup) > 0:
                        df_nov_aud.columns = [str(c).strip().upper() for c in df_nov_aud.columns]
                        df_nov_aud['OBJETIVO_CLEAN'] = col_texto(df_nov_aud, 'OBJETIVO').str.strip().str.upper() if 'OBJETIVO' in df_nov_aud.columns else ""
                        col_ev = next((p for p in ['TIPO_EVENTO', 'TIPO EVENTO', 'EVENTO', 'TIPO'] if p in df_nov_aud.columns), df_nov_aud.columns[2] if len(df_nov_aud.columns) > 2 else None)
                        if col_ev:
                            mask_f = df_nov_aud['OBJETIVO_CLEAN'].isin(objs_del_sup) & col_texto(df_nov_aud, col_ev).str.upper().str.contains("MARCACIÓN|FICHAJE|INGRESO|EGRESO", regex=True)
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
                        df_rel_filtrado = df_vig_rel_aud[col_texto(df_vig_rel_aud, col_ov).str.strip().str.upper().isin([o.upper() for o in objs_del_sup])]

                    df_rec_filtrado = tabla_recorridas_vigiladores(objs_del_sup)

                    df_pan_sup_filtrado = pd.DataFrame()
                    if not df_alertas_aud.empty and 'TIPO' in df_alertas_aud.columns:
                        df_pan_op = df_alertas_aud[col_texto(df_alertas_aud, 'TIPO').str.strip().str.upper() == "PÁNICO"]
                        mask_s_pan = (col_texto(df_pan_op, 'USUARIO').str.strip().str.upper() == sup_seleccionado_jefe)
                        df_pan_sup_filtrado = df_pan_op[mask_s_pan]

                    df_pan_vig_filtrado = pd.DataFrame()
                    if not df_alertas_aud.empty and 'TIPO' in df_alertas_aud.columns:
                        df_pan_op = df_alertas_aud[col_texto(df_alertas_aud, 'TIPO').str.strip().str.upper() == "PÁNICO"]
                        mask_v_pan = col_texto(df_pan_op, 'OBJETIVO').str.strip().str.upper().isin([o.upper() for o in objs_del_sup])
                        mask_no_sup = ~(col_texto(df_pan_op, 'USUARIO').str.strip().str.upper() == sup_seleccionado_jefe)
                        df_pan_vig_filtrado = df_pan_op[mask_v_pan & mask_no_sup]

                    df_alt_sup_filtrado = pd.DataFrame()
                    if not df_alertas_aud.empty:
                        df_alertas_aud.columns = [str(c).strip().upper() for c in df_alertas_aud.columns]
                        df_alt_op = df_alertas_aud[(col_texto(df_alertas_aud, 'TIPO').str.strip().str.upper() != "PÁNICO") & ~col_texto(df_alertas_aud, 'TIPO').str.upper().str.contains("FRAUDE")] if 'TIPO' in df_alertas_aud.columns else df_alertas_aud
                        mask_alt = (col_texto(df_alt_op, 'OBJETIVO').str.strip().str.upper().isin([o.upper() for o in objs_del_sup]) if 'OBJETIVO' in df_alt_op.columns else False) | \
                                   (col_texto(df_alt_op, 'SUPERVISOR').str.strip().str.upper() == sup_seleccionado_jefe if 'SUPERVISOR' in df_alt_op.columns else False)
                        df_alt_sup_filtrado = df_alt_op[mask_alt]

                    df_flota_sup_filtro = pd.DataFrame()
                    if not df_flota_aud.empty:
                        df_flota_aud.columns = [str(c).strip().upper() for c in df_flota_aud.columns]
                        col_sf = 'SUPERVISOR' if 'SUPERVISOR' in df_flota_aud.columns else (df_flota_aud.columns[1] if len(df_flota_aud.columns) > 1 else None)
                        if col_sf:
                            df_flota_sup_filtro = df_flota_aud[col_texto(df_flota_aud, col_sf).str.strip().str.upper() == str(sup_seleccionado_jefe).strip().upper()].copy()

                    # --- Traspasos de objetivos y cargas tácticas (Centro del Supervisor) ---
                    df_tras_sup = pd.DataFrame()
                    try:
                        df_tras_raw = leer_matriz_nube("TRASPASOS OBJETIVOS").copy()
                        if not df_tras_raw.empty:
                            df_tras_raw.columns = [str(c).strip().upper() for c in df_tras_raw.columns]
                            if {"ORIGEN", "DESTINO"} <= set(df_tras_raw.columns):
                                _sup_n = str(sup_seleccionado_jefe).strip().upper()
                                _ori = col_texto(df_tras_raw, "ORIGEN").str.strip().str.upper()
                                _des = col_texto(df_tras_raw, "DESTINO").str.strip().str.upper()
                                df_tras_sup = df_tras_raw[(_ori == _sup_n) | (_des == _sup_n)].copy()
                                if not df_tras_sup.empty:
                                    df_tras_sup.insert(1, "MOVIMIENTO", ["TRASPASÓ" if x == _sup_n else "RECIBIÓ" for x in _ori[df_tras_sup.index]])
                                    df_tras_sup = df_tras_sup[[c for c in ["FECHA_HORA", "MOVIMIENTO", "OBJETIVO", "ORIGEN", "DESTINO", "MOTIVO"] if c in df_tras_sup.columns]]
                    except Exception:
                        df_tras_sup = pd.DataFrame()

                    df_car_sup = pd.DataFrame()
                    if not df_nov_aud.empty and df_nov_aud.shape[1] >= 5:
                        _nov = df_nov_aud.iloc[:, :5].copy()
                        _nov.columns = ["FECHA", "OBJETIVO", "TIPO", "DETALLE", "SUPERVISOR"]
                        _nov = _nov[(_nov["TIPO"].astype(str).str.strip().str.upper() == "NOVEDAD OPERATIVA") &
                                    (_nov["SUPERVISOR"].astype(str).str.strip().str.upper() == str(sup_seleccionado_jefe).strip().upper())]
                        df_car_sup = _nov[["FECHA", "OBJETIVO", "DETALLE"]]

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
                         
                        st.markdown("##### 📍 Detalle de Permanencia por Objetivo (Escaneos QR)")
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

                        st.markdown("##### 🛰️ Seguimiento de Rondas de Vigiladores")
                        if not df_rec_filtrado.empty:
                            mostrar_tabla_rondas(df_rec_filtrado)
                        else:
                            st.info("Sin rondas registradas.")

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
                                f_val_p = str(f_row.get('FECHA', ''))
                                turnos_vig_list.append(determinar_turno_activo(f_val_p))
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

                        st.markdown("##### 🔁 Traspasos de Objetivos")
                        if not df_tras_sup.empty:
                            st.dataframe(df_tras_sup.iloc[::-1], use_container_width=True, hide_index=True)
                        else:
                            st.info("Sin traspasos de objetivos.")

                        st.markdown("##### 📋 Cargas Tácticas")
                        if not df_car_sup.empty:
                            st.dataframe(df_car_sup.iloc[::-1], use_container_width=True, hide_index=True)
                        else:
                            st.info("Sin cargas tácticas.")

                    st.markdown("---")

                    pdf_bytes_integral = generar_pdf_integral_supervisor(
                        sup_seleccionado_jefe, inicio_jornada_gen, fin_jornada_gen, total_horas_trabajadas,
                        df_tabla_permanencia, df_fich_filtrado, df_rel_filtrado, 
                        df_alt_sup_filtrado, df_pan_sup_filtrado, df_pan_vig_filtrado, df_flota_sup_filtro,
                        total_alertas_supervisor_j, total_alertas_vigilador_j, df_rec_filtrado,
                        df_tras_sup, df_car_sup
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
            st.info("No hay registros activos de supervisores in el sistema todavía.")

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

        df_obj_m = cargar_objetivos()
        df_alt_m = leer_matriz_nube("ALERTAS")
         
        total_objs = len(df_obj_m) if not df_obj_m.empty else 0
        df_pan_vig_adm = df_alt_m[
            (col_texto(df_alt_m, 'TIPO').str.upper() == "PÁNICO") & 
            (col_texto(df_alt_m, 'ESTADO').str.upper() == "PENDIENTE")
        ] if not df_alt_m.empty and 'TIPO' in df_alt_m.columns else pd.DataFrame()
        pend_sos = len(df_pan_vig_adm)

        c_adm1, c_adm2 = st.columns(2)
        c_adm1.metric("🎯 OBJETIVOS ACTIVOS", total_objs)
        c_adm2.metric("🚨 ALERTAS PENDIENTES", pend_sos)

        st.markdown("---")

        t_adm_vig, t_adm_usu, t_adm_qr_rec, t_adm_obj, t_adm_mantenimiento = st.tabs([
            "🪪 Padrón de Vigiladores", "👥 Cuentas de Usuarios", "🧾 Puntos QR Recorrido",
            "🎯 Gestión de Objetivos", "🛡️ Respaldo y Archivo Táctico"
        ])

        with t_adm_vig:
            st.markdown("#### 🪪 PADRÓN DE VIGILADORES")
            
            if st.session_state.get("msg_admin_padron"):
                st.success(st.session_state.pop("msg_admin_padron"))

            df_pad_adm = leer_matriz_nube("PADRON VIGILADORES")
            
            if not df_pad_adm.empty:
                df_pad_adm.columns = [str(c).strip().upper() for c in df_pad_adm.columns]
                cols_pad = [c for c in ['DNI', 'NOMBRE', 'LEGAJO', 'ESTADO', 'OBJETIVO'] if c in df_pad_adm.columns]
                st.dataframe(df_pad_adm[cols_pad], use_container_width=True, hide_index=True)
            else:
                st.info("El padrón todavía está vacío.")

            if not df_pad_adm.empty:
                df_pad_adm.columns = [str(c).strip().upper() for c in df_pad_adm.columns]
                if 'ESTADO' in df_pad_adm.columns:
                    df_pad_adm['ESTADO'] = df_pad_adm['ESTADO'].astype(str).str.strip().str.upper()
                else:
                    df_pad_adm['ESTADO'] = "PENDIENTE"

                st.markdown("---")
                
                st.markdown("##### 🟢 GESTIÓN DE ALTA")
                pend_vig = df_pad_adm[df_pad_adm['ESTADO'] == "PENDIENTE"]
                
                if not pend_vig.empty:
                    etiquetas_pend = {
                        i: f"{r.get('NOMBRE', '')} | DNI {r.get('DNI', '')} | {r.get('OBJETIVO', 'SIN OBJETIVO')}"
                        for i, r in pend_vig.iterrows()
                    }
                    idx_pend = st.selectbox("Seleccione solicitud pendiente:", list(etiquetas_pend.keys()),
                                            format_func=lambda k: etiquetas_pend[k], key="sel_vig_pend_directo")
                    
                    if st.button("🟢 DAR DE ALTA AL VIGILADOR", use_container_width=True, key="btn_alta_directo"):
                        fila_pend = df_pad_adm.loc[idx_pend]
                        nom_p = str(fila_pend.get('NOMBRE', '')).strip().upper()
                        dni_p = str(fila_pend.get('DNI', '')).strip()
                        obj_p = str(fila_pend.get('OBJETIVO', '')).strip().upper()
                        
                        if actualizar_estado_padron(idx_pend + 2, "ACTIVO"):
                            sup_p = ""
                            if not df_objetivos.empty and obj_p:
                                m_obj = df_objetivos[col_texto(df_objetivos, 'OBJETIVO').str.strip().str.upper() == obj_p]
                                if not m_obj.empty:
                                    sup_p = str(m_obj['SUPERVISOR'].iloc[0]).strip().upper()

                            if sup_p:
                                escribir_registro_nube("NOTIFICACIONES_SUPERVISORES", [
                                    obtener_hora_argentina(), sup_p,
                                    f"✅ Alta confirmada: El vigilador {nom_p} (DNI: {dni_p}) fue autorizado en el objetivo {obj_p}.",
                                    "PENDIENTE"
                                ])

                            st.session_state.msg_admin_padron = f"✅ ALTA GESTIONADA: {nom_p} quedó habilitado. Se envió una notificación al supervisor ({sup_p if sup_p else 'N/A'})."
                            st.toast("✅ Alta gestionada. Se envió la notificación al supervisor.", icon="✅")
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error("❌ No se pudo procesar el alta.")
                else:
                    st.info("No hay solicitudes pendientes de alta.")

                st.markdown("---")

                st.markdown("##### 🔴 GESTIÓN DE BAJA")
                activos_vig = df_pad_adm[df_pad_adm['ESTADO'] == "ACTIVO"]
                
                if not activos_vig.empty:
                    etiquetas_activos = {
                        i: f"{r.get('NOMBRE', '')} (DNI: {r.get('DNI', '')}) - Obj: {r.get('OBJETIVO', 'N/A')}"
                        for i, r in activos_vig.iterrows()
                    }
                    idx_baja = st.selectbox("Seleccione vigilador activo:", list(etiquetas_activos.keys()),
                                            format_func=lambda k: etiquetas_activos[k], key="sel_vig_baja_directo")
                                            
                    if st.button("🔴 DAR DE BAJA AL VIGILADOR", use_container_width=True, key="btn_baja_directo"):
                        fila_baja_info = df_pad_adm.loc[idx_baja]
                        nom_baja = str(fila_baja_info.get('NOMBRE', '')).strip().upper()
                        obj_baja = str(fila_baja_info.get('OBJETIVO', '')).strip().upper()

                        if actualizar_estado_padron(idx_baja + 2, "BAJA"):
                            sup_baja = ""
                            if not df_objetivos.empty and obj_baja:
                                m_obj_b = df_objetivos[col_texto(df_objetivos, 'OBJETIVO').str.strip().str.upper() == obj_baja]
                                if not m_obj_b.empty:
                                    sup_baja = str(m_obj_b['SUPERVISOR'].iloc[0]).strip().upper()

                            if sup_baja:
                                escribir_registro_nube("NOTIFICACIONES_SUPERVISORES", [
                                    obtener_hora_argentina(), sup_baja,
                                    f"🚫 Baja procesada: El vigilador {nom_baja} del objetivo {obj_baja} ha sido dado de baja en el sistema.",
                                    "PENDIENTE"
                                ])

                            st.session_state.msg_admin_padron = f"🔴 BAJA GESTIONADA: {nom_baja} fue dado de baja. Se envió una notificación al supervisor ({sup_baja if sup_baja else 'N/A'})."
                            st.toast("🔴 Baja gestionada. Se envió la notificación al supervisor.", icon="🔴")
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error("❌ No se pudo procesar la baja.")
                else:
                    st.info("No hay vigiladores activos para dar de baja.")

        with t_adm_usu:
            st.markdown("#### 👥 CUENTAS DE MONITOREO, SUPERVISOR, JEFE DE OPERACIONES Y GERENCIA")

            if st.session_state.get("msg_admin_usuarios"):
                st.success(st.session_state.pop("msg_admin_usuarios"))

            df_usu = leer_matriz_nube("USUARIOS")
            if df_usu.empty or not {'USUARIO', 'ESTADO'} <= set(df_usu.columns):
                st.info("No hay cuentas registradas en la hoja USUARIOS.")
            else:
                df_usu['ESTADO'] = col_texto(df_usu, 'ESTADO').str.strip().str.upper()
                cols_ver = [c for c in ['USUARIO', 'APELLIDO Y NOMBRE', 'LEGAJO', 'ROL', 'ESTADO'] if c in df_usu.columns]
                st.dataframe(df_usu[cols_ver], use_container_width=True, hide_index=True)

                st.markdown("---")
                st.markdown("##### 🟢 SOLICITUDES PENDIENTES")
                pend_usu = df_usu[df_usu['ESTADO'] == "PENDIENTE"]
                if not pend_usu.empty:
                    etiquetas_usu = {
                        i: f"{r.get('APELLIDO Y NOMBRE', '') or r.get('USUARIO', '')} | {r.get('ROL', '')} | Legajo {r.get('LEGAJO', '-')}"
                        for i, r in pend_usu.iterrows()
                    }
                    idx_usu = st.selectbox("Seleccione solicitud:", list(etiquetas_usu.keys()),
                                           format_func=lambda k: etiquetas_usu[k], key="sel_usu_pend")
                    nom_usu = str(df_usu.loc[idx_usu].get('USUARIO', '')).strip().upper()
                    rol_usu = str(df_usu.loc[idx_usu].get('ROL', '')).strip().upper()

                    c_ap, c_re = st.columns(2)
                    if c_ap.button("🟢 APROBAR CUENTA", use_container_width=True, key="btn_aprobar_usu"):
                        if actualizar_estado_usuario(idx_usu + 2, "APROBADO"):
                            st.session_state.msg_admin_usuarios = f"✅ CUENTA APROBADA: {nom_usu} ({rol_usu}) ya puede iniciar sesión."
                            st.toast("✅ Cuenta aprobada.", icon="✅")
                            st.rerun()
                        else:
                            st.error("❌ No se pudo aprobar la cuenta.")
                    if c_re.button("🔴 RECHAZAR CUENTA", use_container_width=True, key="btn_rechazar_usu"):
                        if actualizar_estado_usuario(idx_usu + 2, "RECHAZADO"):
                            st.session_state.msg_admin_usuarios = f"🔴 CUENTA RECHAZADA: {nom_usu} ({rol_usu})."
                            st.toast("🔴 Cuenta rechazada.", icon="🔴")
                            st.rerun()
                        else:
                            st.error("❌ No se pudo rechazar la cuenta.")
                else:
                    st.info("No hay solicitudes pendientes.")

                st.markdown("---")
                st.markdown("##### 🚫 BAJA DE CUENTAS APROBADAS")
                aprob_usu = df_usu[df_usu['ESTADO'] == "APROBADO"]
                if not aprob_usu.empty:
                    etiquetas_ap = {
                        i: f"{r.get('USUARIO', '')} | {r.get('ROL', '')}"
                        for i, r in aprob_usu.iterrows()
                    }
                    idx_baja_usu = st.selectbox("Seleccione cuenta:", list(etiquetas_ap.keys()),
                                                format_func=lambda k: etiquetas_ap[k], key="sel_usu_baja")
                    if st.button("🚫 DAR DE BAJA LA CUENTA", use_container_width=True, key="btn_baja_usu"):
                        if actualizar_estado_usuario(idx_baja_usu + 2, "BAJA"):
                            st.session_state.msg_admin_usuarios = f"🚫 BAJA GESTIONADA: {etiquetas_ap[idx_baja_usu]}."
                            st.toast("🚫 Baja gestionada.", icon="🚫")
                            st.rerun()
                        else:
                            st.error("❌ No se pudo procesar la baja.")
                else:
                    st.info("No hay cuentas aprobadas.")

        with t_adm_qr_rec:
            renderizar_generador_qr_recorrido(
                df_obj_m['OBJETIVO'].unique() if not df_obj_m.empty else [],
                "adm"
            )

        with t_adm_obj:
            st.markdown("#### 📋 LISTADO GENERAL DE OBJETIVOS EN LA RED")
            if not df_obj_m.empty:
                cols_obj_mostrar = [c for c in ['OBJETIVO', 'DIRECCION', 'LOCALIDAD', 'SUPERVISOR'] if c in df_obj_m.columns]
                st.dataframe(df_obj_m[cols_obj_mostrar], use_container_width=True, hide_index=True)
                pdf_objetivos = generar_pdf_reporte("PADRÓN GENERAL DE OBJETIVOS ACTIVOS", df_obj_m[cols_obj_mostrar])
                st.download_button("📥 DESCARGAR PADRÓN DE OBJETIVOS (PDF)", data=pdf_objetivos, file_name=f"padron_objetivos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf", mime="application/pdf", key="dl_pdf_objetivos_admin")
            else:
                st.info("No hay objetivos cargados.")

        with t_adm_mantenimiento:
            st.markdown("#### 🛡️ RESPALDO Y CAJA FUERTE DIGITAL")
            if not df_obj_m.empty:
                cols_obj_respaldo = [c for c in ['OBJETIVO', 'DIRECCION', 'LOCALIDAD', 'SUPERVISOR'] if c in df_obj_m.columns]
                pdf_respaldo_objs = generar_pdf_reporte("RESPALDO GENERAL DE OBJETIVOS ACTIVOS", df_obj_m[cols_obj_respaldo])
                st.download_button("📥 DESCARGAR RESPALDO DE OBJETIVOS (PDF)", data=pdf_respaldo_objs, file_name=f"respaldo_objetivos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf", mime="application/pdf", use_container_width=True, key="dl_pdf_mantenimiento_objetivos")

        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.error("⚠️ Acceso restringido.")

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

function bip() {
  try {
    desbloquear();
    var o = audioCtx.createOscillator(), g = audioCtx.createGain();
    o.type = "sine"; o.frequency.value = 1300; g.gain.value = 0.4;
    o.connect(g); g.connect(audioCtx.destination);
    o.start();
    setTimeout(function() { o.stop(); }, 170);
  } catch (e) {}
  try { if (navigator.vibrate) navigator.vibrate(120); } catch (e) {}
}
</script>
""", height=0)
