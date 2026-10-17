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
    return df_nube

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

def visor_qr(key):
    return _declarar_visor_qr("v6")(key=key, default=None)

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

def renderizar_alerta_recorrida_js(horarios_previstos):
    if not horarios_previstos:
        return
    h_str_json = str(horarios_previstos).replace("'", '"')
    componentes.html(f"""
    <div style="display:none;"></div>
    <script>
    var horarios = {h_str_json};
    var audioCtx = null;

    function activarAudio() {{
        try {{
            var AC = window.parent.AudioContext || window.parent.webkitAudioContext;
            if (!audioCtx) audioCtx = new AC();
            if (audioCtx.state === "suspended") audioCtx.resume();
        }} catch(e){{}}
    }}
    document.addEventListener("click", activarAudio, {{once: true}});

    function sonarAlarma() {{
        try {{
            activarAudio();
            if(audioCtx) {{
                var o = audioCtx.createOscillator();
                var g = audioCtx.createGain();
                o.type = "square";
                o.frequency.value = 880;
                g.gain.value = 0.5;
                o.connect(g);
                g.connect(audioCtx.destination);
                o.start();
                setTimeout(function(){{ o.stop(); }}, 400);
            }}
            if (navigator.vibrate) navigator.vibrate([300, 100, 300]);
        }} catch(e){{}}
    }}

    setInterval(function() {{
        var d = new Date();
        var hh = String(d.getHours()).padStart(2, '0');
        var mm = String(d.getMinutes()).padStart(2, '0');
        var ss = String(d.getSeconds()).padStart(2, '0');
        var horaActual = hh + ":" + mm;
        
        if (horarios.includes(horaActual) && ss < 5) {{
            sonarAlarma();
            var modalId = "modal_rec_" + horaActual.replace(":", "");
            if (!parent.document.getElementById(modalId)) {{
                var div = parent.document.createElement("div");
                div.id = modalId;
                div.style.cssText = "position:fixed;top:0;left:0;width:100vw;height:100vh;background:rgba(0,0,0,0.85);z-index:99999;display:flex;align-items:center;justify-content:center;";
                div.innerHTML = '<div style="background:#1A1C23;border:3px solid #00E5FF;border-radius:12px;padding:25px;max-width:360px;text-align:center;box-shadow:0 0 30px rgba(0,229,255,0.7);font-family:sans-serif;color:#FFF;">' +
                    '<h2 style="color:#00E5FF;margin-top:0;font-family:Orbitron,sans-serif;">🚨 ¡HORA DE RECORRIDA!</h2>' +
                    '<p style="font-size:16px;margin:15px 0;">Comienza la ronda programada de las <b>' + horaActual + ' HS</b>.</p>' +
                    '<button id="btn_conf_ronda" style="background:#00E5FF;color:#000;border:none;padding:12px 24px;font-weight:bold;font-size:14px;border-radius:6px;cursor:pointer;font-family:Orbitron,sans-serif;margin-top:10px;">¡ENTERADO / INICIAR!</button>' +
                    '</div>';
                parent.document.body.appendChild(div);
                parent.document.getElementById("btn_conf_ronda").onclick = function() {{
                    div.remove();
                }};
            }}
        }}
    }}, 2000);
    </script>
    """, height=0)

def renderizar_recorrido_vigilador(objetivo, nombre, dni):
    st.markdown("### 🚶 RECORRIDO CON MARCACIÓN QR")

    if not dni:
        dni = "99999999"

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
        horarios_previstos_lista = [str(h).strip() for h in puntos['HORARIO'].dropna().tolist() if str(h).strip() and str(h).strip().lower() != 'nan']
    renderizar_alerta_recorrida_js(horarios_previstos_lista)

    df_r = leer_matriz_nube("REGISTRO RECORRIDOS")
    df_hoy = pd.DataFrame()
    if not df_r.empty and {'FECHA_HORA', 'OBJETIVO', 'PUNTO', 'DNI', 'RONDA'} <= set(df_r.columns):
        df_r = df_r.loc[:, ~df_r.columns.duplicated()].copy()
        m_dni = df_r['DNI'].map(lambda v: str(v).strip() == str(dni))
        m_obj = df_r['OBJETIVO'].map(lambda v: str(v).strip().upper() == obj_u)
        m_fecha = df_r['FECHA_HORA'].map(lambda v: hoy in str(v))
        df_hoy = df_r[m_dni & m_obj & m_fecha]

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
    c_r1.metric("🔁 RONDA ACTUAL", ronda)
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

    if st.session_state.get(f"{key_prefix}_msg_punto"):
        st.success(st.session_state[f"{key_prefix}_msg_punto"])
        st.session_state[f"{key_prefix}_msg_punto"] = ""

    if not existentes.empty:
        cols_ver = [c for c in ['PUNTO', 'ORDEN', 'HORARIO'] if c in existentes.columns]
        st.dataframe(existentes[cols_ver], use_container_width=True, hide_index=True)
        
        st.markdown("##### ⏰ CONFIGURAR HORARIOS Y CANTIDAD DE RONDAS")
        with st.form(key=f"{key_prefix}_form_act_horario", clear_on_submit=True):
            puntos_disponibles = existentes['PUNTO'].astype(str).tolist()
            punto_a_editar = st.selectbox("SELECCIONAR PUNTO A CONFIGURAR:", puntos_disponibles)
            
            st.markdown("Indicá los horarios previstos separados por coma (ej. `15:00, 17:00, 19:00, 21:00`). Cada hora representará una ronda programada.")
            nuevo_horario_edit = st.text_input("HORARIOS DE RONDAS:", value="15:00, 17:00, 19:00, 21:00").strip()
            
            if st.form_submit_button("💾 GUARDAR HORARIOS Y RONDAS"):
                if punto_a_editar:
                    gc = conectar_google()
                    if gc:
                        sh = gc.open_by_key(ID_MAESTRO_DB)
                        hoja_p = sh.worksheet("RECORRIDOS PUNTOS")
                        filas_hoja = hoja_p.get_all_values()
                        
                        fila_encontrada = -1
                        for idx_h, f_val in enumerate(filas_hoja[1:], start=2):
                            if len(f_val) >= 2 and str(f_val[0]).strip().upper() == obj_u and str(f_val[1]).strip().upper() == str(punto_a_editar).strip().upper():
                                fila_encontrada = idx_h
                                break
                        
                        if fila_encontrada != -1:
                            encabezados_h = [str(x).strip().upper() for x in filas_hoja[0]]
                            if "HORARIO" in encabezados_h:
                                col_idx = encabezados_h.index("HORARIO") + 1
                                letra_col = gspread.utils.rowcol_to_a1(1, col_idx)[0]
                                hoja_p.update_acell(f"{letra_col}{fila_encontrada}", nuevo_horario_edit)
                                st.cache_data.clear()
                                st.session_state[f"{key_prefix}_msg_punto"] = f"✅ Horarios y rondas configurados para '{punto_a_editar}'."
                                st.rerun()
                            else:
                                hoja_p.update_cell(fila_encontrada, 4, nuevo_horario_edit)
                                st.cache_data.clear()
                                st.session_state[f"{key_prefix}_msg_punto"] = f"✅ Horarios y rondas configurados para '{punto_a_editar}'."
                                st.rerun()
                        else:
                            st.error("No se encontró el punto en la planilla.")
                else:
                    st.warning("Seleccioná un punto.")
    else:
        st.info("Este objetivo todavía no tiene puntos de recorrido.")

    with st.expander("➕ CREAR NUEVO PUNTO DE RECORRIDO"):
        with st.form(key=f"{key_prefix}_form_punto", clear_on_submit=True):
            nuevo_punto = st.text_input("NOMBRE DEL PUNTO (Ej: PORTÓN 1):").strip().upper()
            nuevo_orden = st.number_input("ORDEN EN EL RECORRIDO:", min_value=1, value=len(existentes) + 1, step=1)
            nuevo_horario = st.text_input("HORARIOS DE RONDAS (Ej: 15:00, 17:00, 19:00):", value="15:00, 17:00").strip()
            
            if st.form_submit_button("➕ GUARDAR NUEVO PUNTO"):
                if nuevo_punto:
                    ya_existe = (not existentes.empty) and (nuevo_punto in existentes['PUNTO'].astype(str).str.strip().str.upper().tolist())
                    if ya_existe:
                        st.warning("⚠️ Ese punto ya existe en este objetivo. Usá la sección de arriba para configurar sus horarios.")
                    elif escribir_registro_nube("RECORRIDOS PUNTOS", [obj_u, nuevo_punto, int(nuevo_orden), nuevo_horario]):
                        st.session_state[f"{key_prefix}_msg_punto"] = f"✅ Punto '{nuevo_punto}' guardado con éxito."
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

# (Continuación del resto del código de la aplicación...)
