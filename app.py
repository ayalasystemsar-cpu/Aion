import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import qrcode
import io
import datetime
import pytz
import math
import json
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfgen import canvas

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="AION-YAROKU | COMMAND",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- INICIALIZACIÓN DE ESTADOS ---
if 'usuario_logueado' not in st.session_state:
    st.session_state.usuario_logueado = False
if 'rol_sel' not in st.session_state:
    st.session_state.rol_sel = "VIGILADOR"
if 'user_sel' not in st.session_state:
    st.session_state.user_sel = "INVITADO"
if 'admin_autenticado' not in st.session_state:
    st.session_state.admin_autenticado = False
if 'sup_autenticado' not in st.session_state:
    st.session_state.sup_autenticado = False
if 'ultimo_mensaje_qr' not in st.session_state:
    st.session_state.ultimo_mensaje_qr = ""

# --- CAPTURA DE PARÁMETROS URL ---
query_params = st.query_params
if "v" in query_params and not st.session_state.usuario_logueado:
    st.session_state.usuario_logueado = True
    st.session_state.user_sel = query_params.get("u", "USUARIO")
    st.session_state.rol_sel = query_params.get("r", "VIGILADOR")

def sincronizar_url_sesion():
    if st.session_state.usuario_logueado:
        st.query_params.clear()
        st.query_params["v"] = "1"
        st.query_params["u"] = st.session_state.user_sel
        st.query_params["r"] = st.session_state.rol_sel

# --- ESTILOS VISUALES ALFA ---
def aplicar_identidad_alfa():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;800&family=Rajdhani:wght@500;700&display=swap');
    
    .stApp {
        background-color: #0D0E12;
        color: #F8FAFC;
        font-family: 'Rajdhani', sans-serif;
    }
    .estacion-titulo {
        font-family: 'Orbitron', sans-serif;
        color: #00E5FF;
        font-size: 26px;
        font-weight: 800;
        text-align: center;
        margin-bottom: 15px;
        text-shadow: 0 0 15px rgba(0,229,255,0.4);
    }
    .panel-novedad {
        background: #14161F;
        border: 1px solid rgba(0, 229, 255, 0.25);
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.5);
    }
    .logo-phoenix {
        width: 140px;
        height: 140px;
        border-radius: 50%;
        border: 3px solid #00E5FF;
        box-shadow: 0 0 25px rgba(0,229,255,0.6);
        object-fit: cover;
    }
    .contenedor-logo-central {
        display: flex;
        justify-content: center;
        align-items: center;
        margin-bottom: 10px;
    }
    .contenedor-logo-sidebar {
        display: flex;
        justify-content: center;
        align-items: center;
        margin-bottom: 15px;
    }
    .btn-google-maps {
        background-color: #00E5FF;
        color: #000000;
        padding: 10px 20px;
        border-radius: 6px;
        font-family: 'Orbitron', sans-serif;
        font-weight: bold;
        font-size: 12px;
        text-decoration: none;
        display: block;
        text-align: center;
        box-shadow: 0 0 12px rgba(0,229,255,0.5);
        margin-top: 10px;
    }
    .btn-google-maps:hover {
        background-color: #39FF14;
        color: #000;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CONFIGURACIÓN DE GOOGLE SHEETS ---
ID_MAESTRO_DB = "1r4XbT_X2x_5m07m4lBv5xY9W0x_z61xYv45b6n7m8k9"

def conectar_google():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        else:
            creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
        return gspread.authorize(creds)
    except Exception:
        return None

@st.cache_data(ttl=10)
def leer_matriz_nube(nombre_hoja):
    try:
        gc = conectar_google()
        if gc:
            sh = gc.open_by_key(ID_MAESTRO_DB)
            try:
                worksheet = sh.worksheet(nombre_hoja)
            except:
                worksheet = sh.add_worksheet(title=nombre_hoja, rows="100", cols="20")
            data = worksheet.get_all_values()
            if len(data) > 0:
                headers = [str(h).strip().upper() for h in data[0]]
                df = pd.DataFrame(data[1:], columns=headers) if len(data) > 1 else pd.DataFrame(columns=headers)
                return df
        return pd.DataFrame()
    except:
        return pd.DataFrame()

def escribir_registro_nube(nombre_hoja, fila_datos):
    try:
        gc = conectar_google()
        if gc:
            sh = gc.open_by_key(ID_MAESTRO_DB)
            try:
                worksheet = sh.worksheet(nombre_hoja)
            except:
                worksheet = sh.add_worksheet(title=nombre_hoja, rows="100", cols="20")
            worksheet.append_row(fila_datos)
            st.cache_data.clear()
            return True
    except:
        return False

def col_texto(df, nombre_col):
    if nombre_col in df.columns:
        return df[nombre_col].astype(str).str.strip()
    return pd.Series([""] * len(df))

def obtener_hora_argentina():
    tz_arg = pytz.timezone('America/Argentina/Buenos_Aires')
    return datetime.now(tz_arg).strftime('%Y-%m-%d %H:%M:%S')

def determinar_turno_activo(fecha_hora_str):
    try:
        dt = datetime.strptime(fecha_hora_str.split(".")[0], "%Y-%m-%d %H:%M:%S")
        hora = dt.hour
        return "TURNO NOCHE (22:00 A 06:00)" if (hora >= 22 or hora < 6) else "TURNO DÍA (06:00 A 22:00)"
    except:
        return "TURNO DÍA (06:00 A 22:00)"

def cargar_objetivos():
    df = leer_matriz_nube("OBJETIVOS")
    if df.empty or 'OBJETIVO' not in df.columns:
        return pd.DataFrame([
            {"ID": "1", "OBJETIVO": "ALFAVINIL", "DIRECCION": "AV. CORRIENTES 1234", "LOCALIDAD": "CAPITAL FEDERAL", "SUPERVISOR": "AYALA BRIAN", "LATITUD": "-34.6037", "LONGITUD": "-58.3816"}
        ])
    return df

def cargar_datos_comisarias():
    df = leer_matriz_nube("COMISARIAS")
    if df.empty or 'COMISARIA' not in df.columns:
        return pd.DataFrame([
            {"COMISARIA": "COMISARIA VECINAL 1A", "DIRECCION": "DIAGONAL NORTE 500", "LOCALIDAD": "CAPITAL FEDERAL", "LATITUD": "-34.6030", "LONGITUD": "-58.3800", "TELEFONO": "011-4382-0101"}
        ])
    return df

def obtener_lista_supervisores_dinamica():
    sups = ["AYALA BRIAN", "GONZALEZ", "CONTROLADOR NOCTURNO", "TIKI"]
    df_obj = cargar_objetivos()
    if not df_obj.empty and 'SUPERVISOR' in df_obj.columns:
        for s in col_texto(df_obj, 'SUPERVISOR').dropna().unique():
            sups.append(str(s).strip().upper())
    return sorted(list(set(sups)))

def comisaria_mas_cercana(lat_obj, lon_obj, localidad_obj, df_comisarias):
    dist_min = float('inf')
    comisaria_elegida = None
    
    df_sub = df_comisarias
    if localidad_obj and 'LOCALIDAD' in df_comisarias.columns:
        df_sub_loc = df_comisarias[col_texto(df_comisarias, 'LOCALIDAD').str.strip().str.upper() == localidad_obj]
        if not df_sub_loc.empty:
            df_sub = df_sub_loc

    for _, com in df_sub.iterrows():
        try:
            lat_c = float(str(com['LATITUD']).replace(',', '.'))
            lon_c = float(str(com['LONGITUD']).replace(',', '.'))
            
            lon1, lat1, lon2, lat2 = map(math.radians, [float(lon_obj), float(lat_obj), lon_c, lat_c])
            dlon = lon2 - lon1
            dlat = lat2 - lat1
            a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
            c = 2 * math.asin(math.sqrt(a))
            km = 6371 * c
            
            if km < dist_min:
                dist_min = km
                comisaria_elegida = com
        except:
            continue
            
    return comisaria_elegida

def verificar_e_insertar_comisaria_automatica(nombre_com, dir_com, loc_com, tel_com, lat_com, lon_com):
    try:
        df_c = leer_matriz_nube("COMISARIAS")
        existe = False
        if not df_c.empty and 'COMISARIA' in df_c.columns:
            nombres_existentes = col_texto(df_c, 'COMISARIA').str.upper().tolist()
            if nombre_com.upper() in nombres_existentes:
                existe = True
        if not existe:
            escribir_registro_nube("COMISARIAS", [nombre_com, dir_com, loc_com, str(lat_com), str(lon_com), tel_com])
    except:
        pass

def registrar_jornada_general(usuario, objetivo, accion):
    fecha_hora = obtener_hora_argentina()
    return escribir_registro_nube("JORNADA SUPERVISORES", [fecha_hora, objetivo, accion, usuario])

def registrar_qr_supervisor(usuario, objetivo, accion):
    fecha_hora = obtener_hora_argentina()
    return escribir_registro_nube("REGISTRO QR SUPERVISORES", [fecha_hora, objetivo, accion, usuario])

def actualizar_estado_padron(fila_idx, nuevo_estado):
    try:
        gc = conectar_google()
        if gc:
            worksheet = gc.open_by_key(ID_MAESTRO_DB).worksheet("PADRON VIGILADORES")
            encabezados = [str(x).strip().upper() for x in worksheet.row_values(1)]
            if "ESTADO" in encabezados:
                col_idx = encabezados.index("ESTADO") + 1
                worksheet.update_cell(fila_idx, col_idx, nuevo_estado)
                st.cache_data.clear()
                return True
    except:
        return False
    return False

def actualizar_estado_usuario(fila_idx, nuevo_estado):
    try:
        gc = conectar_google()
        if gc:
            worksheet = gc.open_by_key(ID_MAESTRO_DB).worksheet("USUARIOS")
            encabezados = [str(x).strip().upper() for x in worksheet.row_values(1)]
            if "ESTADO" in encabezados:
                col_idx = encabezados.index("ESTADO") + 1
                worksheet.update_cell(fila_idx, col_idx, nuevo_estado)
                st.cache_data.clear()
                return True
    except:
        return False
    return False

def mostrar_notificaciones_sidebar():
    try:
        df_n = leer_matriz_nube("NOTIFICACIONES_SUPERVISORES")
        if not df_n.empty and 'SUPERVISOR' in df_n.columns and 'ESTADO' in df_n.columns:
            sup_act = st.session_state.user_sel.strip().upper()
            pendientes = df_n[
                (col_texto(df_n, 'SUPERVISOR').str.upper() == sup_act) & 
                (col_texto(df_n, 'ESTADO').str.upper() == "PENDIENTE")
            ]
            if not pendientes.empty:
                st.sidebar.markdown("---")
                st.sidebar.markdown("### 🔔 NOTIFICACIONES")
                for idx, r in pendientes.iterrows():
                    st.sidebar.info(r.get('MENSAJE', ''))
                    if st.sidebar.button("Marcar leída", key=f"leida_not_{idx}"):
                        gc = conectar_google()
                        if gc:
                            w = gc.open_by_key(ID_MAESTRO_DB).worksheet("NOTIFICACIONES_SUPERVISORES")
                            w.update_cell(idx + 2, 4, "LEIDA")
                            st.cache_data.clear()
                            st.rerun()
    except:
        pass

def renderizar_reloj_fluido():
    components.html("""
    <div style="font-family: 'Orbitron', sans-serif; color: #00E5FF; font-size: 16px; font-weight: bold; text-align: center; background: rgba(0,229,255,0.05); padding: 8px; border-radius: 6px; border: 1px solid rgba(0,229,255,0.2);">
        <span id="reloj_vivo">--:--:--</span>
    </div>
    <script>
    function actualizarReloj() {
        var d = new Date();
        var hora = String(d.getHours()).padStart(2, '0');
        var min = String(d.getMinutes()).padStart(2, '0');
        var sec = String(d.getSeconds()).padStart(2, '0');
        var el = document.getElementById("reloj_vivo");
        if(el) el.textContent = hora + ":" + min + ":" + sec;
    }
    setInterval(actualizarReloj, 1000);
    actualizarReloj();
    </script>
    """, height=45)

def renderizar_mensajeria_global(rol_usuario_actual):
    st.markdown("### 💬 CENTRO DE MENSAJERÍA TÁCTICA GLOBAL")
    
    with st.form("form_enviar_mensaje_global", clear_on_submit=True):
        destinatario = st.selectbox("DESTINATARIO:", ["TODOS", "MONITOREO", "SUPERVISOR", "JEFE DE OPERACIONES", "GERENCIA"])
        mensaje_txt = st.text_area("MENSAJE:")
        if st.form_submit_button("ENVIAR MENSAJE A LA RED"):
            if mensaje_txt.strip():
                escribir_registro_nube("MENSAJERIA", [
                    obtener_hora_argentina(), st.session_state.user_sel, destinatario, "MENSAJE TÁCTICO", mensaje_txt.strip().upper(), "PENDIENTE", "NORMAL"
                ])
                st.success("✅ Mensaje enviado correctamente a la red.")
                st.rerun()
            else:
                st.warning("Escriba un mensaje.")

    st.markdown("---")
    df_m = leer_matriz_nube("MENSAJERIA")
    if not df_m.empty and 'DESTINATARIO' in df_m.columns:
        st.markdown("#### 📥 BANDEJA DE ENTRADA")
        nombre_actual = st.session_state.user_sel.upper()
        rol_actual = rol_usuario_actual.upper()
        
        mis_mensajes = df_m[
            (col_texto(df_m, 'DESTINATARIO').str.upper() == "TODOS") | 
            (col_texto(df_m, 'DESTINATARIO').str.upper() == rol_actual) | 
            (col_texto(df_m, 'DESTINATARIO').str.upper() == nombre_actual)
        ]
        
        if not mis_mensajes.empty:
            for idx_m, row_m in mis_mensajes.iloc[::-1].iterrows():
                estado_m = str(row_m.get('ESTADO', 'PENDIENTE')).upper()
                color_borde = "#39FF14" if estado_m == "PENDIENTE" else "#555"
                st.markdown(f"""
                <div style="background: #14161F; border-left: 4px solid {color_borde}; border-radius: 6px; padding: 10px; margin-bottom: 8px;">
                    <b>De:</b> {row_m.get('EMISOR', 'SISTEMA')} | <b>Fecha:</b> {row_m.get('FECHA', '')}<br>
                    <b>Mensaje:</b> {row_m.get('MENSAJE', '')}
                </div>
                """, unsafe_allow_html=True)
                
                if estado_m == "PENDIENTE":
                    if st.button("Marcar como leído / Atendido", key=f"btn_leer_msg_{idx_m}"):
                        gc = conectar_google()
                        if gc:
                            w = gc.open_by_key(ID_MAESTRO_DB).worksheet("MENSAJERIA")
                            w.update_cell(idx_m + 2, 6, "ATENDIDO")
                            st.cache_data.clear()
                            st.rerun()
        else:
            st.info("No hay mensajes en su bandeja.")

def enviar_alerta_automatica(emisor, objetivo_actual, nombre_persona, supervisor_asignado):
    fecha = obtener_hora_argentina()
    mensaje = f"S.O.S PÁNICO: {nombre_persona} - OBJ: {objetivo_actual}"
    destinatarios = ["JEFE DE OPERACIONES", "GERENCIA", supervisor_asignado]
    for dest in destinatarios:
        if dest and dest != "MONITOREO" and dest != "N/A":
            escribir_registro_nube("MENSAJERIA", [fecha, emisor, dest, "ALERTA DE PÁNICO", mensaje, "PENDIENTE", "ROJA"])

# --- COMPONENTE VISOR QR ---
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
<script src="https://cdn.jsdelivr.net/npm/jsqr@1.4.0/dist/jsQR.min.js"></script>
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
    o.type="sine";o.frequency.value=800;g.gain.value=0.15;
    o.connect(g);g.connect(audioCtx.destination);
    o.start();
    setTimeout(function(){o.stop();},120);
  }catch(e){}
  try{if(navigator.vibrate)navigator.vibrate(80);}catch(e){}
}

navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:"environment"},width:{ideal:1280},height:{ideal:720}},audio:false})
.then(function(s){
  v.srcObject=s;v.play();
  window.addEventListener("pagehide",function(){s.getTracks().forEach(function(t){t.stop();});});
  setInterval(function(){
    if(pausa||v.readyState<2||!v.videoWidth)return;
    if(typeof jsQR==="undefined"){m.textContent="No cargó el lector QR.";return;}
    var e=Math.min(1,640/Math.max(v.videoWidth,v.videoHeight));
    c.width=Math.round(v.videoWidth*e);c.height=Math.round(v.videoHeight*e);
    ctx.drawImage(v,0,0,c.width,c.height);
    var im=ctx.getImageData(0,0,c.width,c.height);
    var r=jsQR(im.data,im.width,im.height,{inversionAttempts:"attemptBoth"});
    if(r&&r.data){pausa=true;bip();enviar("streamlit:setComponentValue",{value:r.data,dataType:"json"});
      setTimeout(function(){pausa=false;},3000);}
  },120);
}).catch(function(){m.textContent="No se pudo abrir la cámara.";});
</script></body></html>"""

def _declarar_visor_qr(name):
    return components.declare_component(name, data=_QR_HTML)

def visor_qr(key):
    return _declarar_visor_qr("v6")(key=key, default=None)

# --- RECORRIDOS CON QR Y ALERTA SUAVE (5 MIN ANTES) CON JUSTIFICACIÓN ---
def renderizar_alerta_recorrida_js(horarios_previstos, objetivo_actual, vigilador_actual):
    if not horarios_previstos:
        return
    
    horarios_alerta = []
    for h in horarios_previstos:
        try:
            partes = h.split(":")
            dt_base = datetime.strptime(f"{partes[0]}:{partes[1]}", "%H:%M")
            dt_menos_5 = dt_base - timedelta(minutes=5)
            horarios_alerta.append(dt_menos_5.strftime("%H:%M"))
        except:
            horarios_alerta.append(h)

    h_str_json = str(horarios_alerta).replace("'", '"')
    h_originales_json = str(horarios_previstos).replace("'", '"')
    
    components.html(f"""
    <div style="background:#1A1C23;border:2px solid #00E5FF;border-radius:10px;padding:12px;text-align:center;font-family:sans-serif;margin-bottom:10px;box-shadow:0 0 15px rgba(0,229,255,0.3);">
        <p style="color:#00E5FF;font-weight:bold;font-size:13px;margin:0 0 8px 0;">🛡️ SISTEMA DE ALARMAS Y HORARIOS PROGRAMADOS</p>
        <button id="btn_activar_alerta" style="background:#00E5FF;color:#000;border:none;padding:10px 20px;font-weight:bold;font-size:13px;border-radius:6px;cursor:pointer;box-shadow:0 0 10px rgba(0,229,255,0.8);">🔊 ACTIVAR AVISOS DE RECORRIDA</button>
        <p id="estado_audio" style="color:#39FF14;font-size:11px;margin:6px 0 0 0;font-weight:bold;"></p>
    </div>
    <script>
    var horariosAlerta = {h_str_json};
    var horariosOriginales = {h_originales_json};
    var objetivo = "{objetivo_actual}";
    var vigilador = "{vigilador_actual}";
    var audioCtx = null;
    var activado = false;
    var intervaloAlarma = null;

    function desbloquearAudioCompleto() {{
        try {{
            var AC = window.parent.AudioContext || window.parent.webkitAudioContext;
            if (!audioCtx) audioCtx = new AC();
            if (audioCtx.state === "suspended") audioCtx.resume();
            
            var o = audioCtx.createOscillator();
            var g = audioCtx.createGain();
            o.type = "sine"; o.frequency.value = 800; g.gain.value = 0.1;
            o.connect(g); g.connect(audioCtx.destination);
            o.start(); setTimeout(function(){{ o.stop(); }}, 60);

            activado = true;
            var st = document.getElementById("estado_audio");
            if(st) st.textContent = "✅ Sistema activado (Aviso preventivo 5 min antes)";
            var btn = document.getElementById("btn_activar_alerta");
            if(btn) {{
                btn.style.background = "#39FF14";
                btn.textContent = "🔊 AVISOS DE RECORRIDA ACTIVOS";
            }}
        }} catch(e){{}}
    }}

    document.getElementById("btn_activar_alerta").onclick = desbloquearAudioCompleto;
    ["touchstart", "click", "pointerdown"].forEach(function(ev) {{
        parent.document.addEventListener(ev, function() {{
            if(!activado) desbloquearAudioCompleto();
        }}, {{once: true}});
    }});

    function sonarBipSuave() {{
        try {{
            desbloquearAudioCompleto();
            if(audioCtx) {{
                // Tono dual suave y amigable (tipo campanita digital)
                [0, 150].forEach(function(delay, index) {{
                    setTimeout(function() {{
                        var o = audioCtx.createOscillator();
                        var g = audioCtx.createGain();
                        o.type = "sine";
                        o.frequency.value = index === 0 ? 880 : 1046.5; // Notas LA y DO (amigables)
                        g.gain.value = 0.15;
                        o.connect(g);
                        g.connect(audioCtx.destination);
                        o.start();
                        setTimeout(function(){{ o.stop(); }}, 100);
                    }}, delay);
                }});
            }}
            if (navigator.vibrate) navigator.vibrate(100);
        }} catch(e){{}}
    }}

    function iniciarBucleSuave() {{
        if (intervaloAlarma) return;
        sonarBipSuave();
        intervaloAlarma = setInterval(sonarBipSuave, 4000); // Cada 4 segundos un toque suave
    }}

    function detenerAlarma() {{
        if (intervaloAlarma) {{
            clearInterval(intervaloAlarma);
            intervaloAlarma = null;
        }}
    }}

    setInterval(function() {{
        var d = new Date();
        var hh = String(d.getHours()).padStart(2, '0');
        var mm = String(d.getMinutes()).padStart(2, '0');
        var ss = String(d.getSeconds()).padStart(2, '0');
        var horaActual = hh + ":" + mm;
        
        var indexAlerta = horariosAlerta.indexOf(horaActual);
        if (indexAlerta !== -1 && ss < 5) {{
            var horaOficialRonda = horariosOriginales[indexAlerta];
            iniciarBucleSuave();
            var modalId = "modal_rec_" + horaActual.replace(":", "");
            if (!parent.document.getElementById(modalId)) {{
                var div = parent.document.createElement("div");
                div.id = modalId;
                div.style.cssText = "position:fixed;top:0;left:0;width:100vw;height:100vh;background:rgba(0,0,0,0.95);z-index:999999;display:flex;align-items:center;justify-content:center;padding:20px;box-sizing:border-box;";
                div.innerHTML = '<div style="background:#1A1C23;border:4px solid #00E5FF;border-radius:14px;padding:25px;max-width:420px;width:100%;text-align:center;box-shadow:0 0 40px rgba(0,229,255,0.4);font-family:sans-serif;color:#FFF;">' +
                    '<h1 style="color:#00E5FF;margin-top:0;font-family:Orbitron,sans-serif;font-size:20px;">🚨 AVISO PREVENTIVO DE RECORRIDA</h1>' +
                    '<p style="font-size:15px;margin:15px 0;line-height:1.4;">Faltan 5 minutos para la ronda programada de las <b>' + horaOficialRonda + ' HS</b>.<br>¿Desea realizar la recorrida en dicho horario?</p>' +
                    
                    '<div id="contenedor_botones" style="display:flex;flex-direction:column;gap:10px;margin-top:15px;">' +
                    '<button id="btn_si_ronda" style="background:#00E5FF;color:#000;border:none;padding:12px;font-weight:bold;font-size:15px;border-radius:8px;cursor:pointer;font-family:Orbitron,sans-serif;box-shadow:0 0 15px rgba(0,229,255,0.7);width:100%;">✅ SÍ, REALIZARÉ LA RECORRIDA</button>' +
                    '<button id="btn_no_ronda" style="background:#FF3333;color:#FFF;border:none;padding:12px;font-weight:bold;font-size:15px;border-radius:8px;cursor:pointer;font-family:Orbitron,sans-serif;box-shadow:0 0 15px rgba(255,51,51,0.7);width:100%;">❌ NO REALIZARÉ LA RECORRIDA</button>' +
                    '</div>' +

                    '<div id="formulario_motivo" style="display:none;margin-top:15px;text-align:left;">' +
                    '<label style="font-size:12px;color:#FF9999;font-weight:bold;display:block;margin-bottom:5px;">INDIQUE EL MOTIVO OBLIGATORIO DE LA NO REALIZACIÓN:</label>' +
                    '<textarea id="txt_motivo_no" rows="3" style="width:100%;background:#0D0E12;color:#FFF;border:1px solid #FF3333;border-radius:6px;padding:8px;box-sizing:border-box;font-size:13px;"></textarea>' +
                    '<button id="btn_enviar_motivo" style="background:#FF3333;color:#FFF;border:none;padding:10px;font-weight:bold;font-size:13px;border-radius:6px;cursor:pointer;width:100%;margin-top:10px;">ENVIAR JUSTIFICACIÓN Y CERRAR</button>' +
                    '</div>' +

                    '</div>';
                
                parent.document.body.appendChild(div);

                parent.document.getElementById("btn_si_ronda").onclick = function() {{
                    detenerAlarma();
                    div.remove();
                }};

                parent.document.getElementById("btn_no_ronda").onclick = function() {{
                    parent.document.getElementById("contenedor_botones").style.display = "none";
                    parent.document.getElementById("formulario_motivo").style.display = "block";
                }};

                parent.document.getElementById("btn_enviar_motivo").onclick = function() {{
                    var motivoTxt = parent.document.getElementById("txt_motivo_no").value.trim();
                    if (!motivoTxt) {{
                        alert("Por favor, escriba el motivo por el cual no se realizará la recorrida.");
                        return;
                    }}
                    detenerAlarma();
                    fetch("?motivo_no_ronda=" + encodeURIComponent(motivoTxt) + "&obj=" + encodeURIComponent(objetivo) + "&vig=" + encodeURIComponent(vigilador) + "&hora=" + encodeURIComponent(horaOficialRonda));
                    div.remove();
                    alert("Justificación de no realización enviada correctamente a la central.");
                }};
            }}
        }}
    }}, 1000);
    </script>
    """, height=120)

def renderizar_recorrido_vigilador(objetivo, nombre, dni):
    st.markdown("### 🚶 RECORRIDO CON MARCACIÓN QR")

    if not dni and st.session_state.get('rol_sel') == "ADMINISTRADOR":
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
        for h_val in puntos['HORARIO'].dropna().tolist():
            s_h = str(h_val).strip()
            if s_h and s_h.lower() != 'nan':
                for sub_h in s_h.split(','):
                    sh_limpio = sub_h.strip()
                    if sh_limpio:
                        horarios_previstos_lista.append(sh_limpio)
    
    renderizar_alerta_recorrida_js(horarios_previstos_lista, obj_u, nombre)

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
        df_ronda = df_hoy[pd.to_numeric(df_hoy['RONDA'], errors='coerce'] == ronda]
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

    if st.session_state.get(f"{key_prefix}_msg_punto"):
        st.success(st.session_state[f"{key_prefix}_msg_punto"])
        st.session_state[f"{key_prefix}_msg_punto"] = ""

    if not existentes.empty:
        cols_ver = [c for c in ['PUNTO', 'ORDEN', 'HORARIO'] if c in existentes.columns]
        st.dataframe(existentes[cols_ver], use_container_width=True, hide_index=True)
        
        st.markdown("##### ⏰ CONFIGURAR HORARIOS Y RONDAS")
        with st.form(key=f"{key_prefix}_form_act_horario", clear_on_submit=True):
            puntos_disponibles = col_texto(existentes, 'PUNTO').tolist()
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
