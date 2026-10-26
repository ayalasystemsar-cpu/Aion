"""
rastro_gps - Rastro GPS del vigilador durante la ronda (AION-YAROKU).

Qué hace:
  1. Mientras el vigilador tiene abierta la pantalla de recorrido, el celular manda su ubicación cada ~30 s
     y se guarda en la tabla `rastro_gps` de Supabase.
  2. Al escanear un QR, se mira si el celular SE MOVIÓ desde el escaneo anterior.
     Si no se movió y el punto es otro, es la misma persona fotografiando QR desde un solo lugar.
  3. Funciones para ver el rastro (mapa / resumen) en los paneles de supervisión.

Se importa desde la app principal con:  import rastro_gps
"""
import math
from datetime import datetime, timezone, timedelta

import pytz
import streamlit as st
import streamlit.components.v1 as components
import tempfile, os

TZ_AR = pytz.timezone("America/Argentina/Buenos_Aires")

MOV_MIN_M = 10          # si en todo el tramo entre dos escaneos el celular se movió menos que esto -> sospechoso
PRECISION_OK_M = 50     # se ignoran lecturas peores que esto
MIN_PUNTOS = 2          # con menos lecturas que esto no se acusa (falta de señal, no fraude)

SQL_TABLA = """
create table if not exists public.rastro_gps (
  id bigint generated always as identity primary key,
  legajo text not null,
  objetivo text not null,
  ronda int,
  latitud double precision not null,
  longitud double precision not null,
  precision_m double precision,
  momento timestamptz not null
);
create index if not exists rastro_gps_legajo_momento on public.rastro_gps (legajo, momento);
"""

# --------------------------------------------------------------------------- geometría
def distancia_m(lat1, lon1, lat2, lon2):
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def desplazamiento_m(puntos):
    """Mayor distancia entre cualquier par de lecturas buenas. puntos: lista de (lat, lon, precision)."""
    buenos = [(la, lo) for la, lo, ac in puntos if ac is None or ac <= PRECISION_OK_M]
    if len(buenos) < MIN_PUNTOS:
        return None
    return max(distancia_m(a[0], a[1], b[0], b[1]) for i, a in enumerate(buenos) for b in buenos[i + 1:])


def evaluar_movimiento(puntos):
    """Devuelve ('SIN_DATOS'|'SIN_MOVIMIENTO'|'OK', desplazamiento_m)."""
    d = desplazamiento_m(puntos)
    if d is None:
        return "SIN_DATOS", None
    return ("SIN_MOVIMIENTO" if d < MOV_MIN_M else "OK"), d


# --------------------------------------------------------------------------- base de datos
def _a_utc(dt_naive_ar):
    return TZ_AR.localize(dt_naive_ar).astimezone(timezone.utc)


def guardar_lecturas(cli, legajo, objetivo, ronda, lecturas):
    """lecturas: [{lat, lon, acc, ts(ms)}]. Devuelve True/False (nunca corta la app)."""
    if cli is None or not lecturas:
        return False
    try:
        filas = [{
            "legajo": str(legajo), "objetivo": str(objetivo).strip().upper(), "ronda": int(ronda),
            "latitud": float(x["lat"]), "longitud": float(x["lon"]),
            "precision_m": None if x.get("acc") is None else float(x["acc"]),
            "momento": datetime.fromtimestamp(float(x["ts"]) / 1000.0, tz=timezone.utc).isoformat(),
        } for x in lecturas if x.get("lat") is not None and x.get("lon") is not None]
        if filas:
            cli.table("rastro_gps").insert(filas).execute()
        return True
    except Exception as e:
        print(f"[rastro_gps] Error guardando rastro: {e}")
        return False


def movimiento_desde(cli, legajo, desde_naive_ar, hasta_naive_ar=None):
    """Mira el rastro del legajo entre el escaneo anterior y ahora. Devuelve (estado, desplazamiento_m, n_lecturas)."""
    if cli is None or desde_naive_ar is None:
        return "SIN_DATOS", None, 0
    try:
        q = (cli.table("rastro_gps").select("latitud, longitud, precision_m")
             .eq("legajo", str(legajo)).gte("momento", _a_utc(desde_naive_ar).isoformat()))
        if hasta_naive_ar is not None:
            q = q.lte("momento", _a_utc(hasta_naive_ar).isoformat())
        data = q.limit(2000).execute().data or []
    except Exception as e:
        print(f"[rastro_gps] Error leyendo rastro: {e}")
        return "SIN_DATOS", None, 0
    pts = [(r["latitud"], r["longitud"], r.get("precision_m")) for r in data]
    estado, d = evaluar_movimiento(pts)
    return estado, d, len(pts)


def rastro_del_dia(cli, legajo, fecha_txt):
    """Lecturas del legajo en un día (YYYY-MM-DD, hora argentina). Devuelve lista de dicts ordenada."""
    if cli is None:
        return []
    try:
        ini = TZ_AR.localize(datetime.strptime(fecha_txt, "%Y-%m-%d")).astimezone(timezone.utc)
        fin = ini + timedelta(days=1)
        return (cli.table("rastro_gps").select("latitud, longitud, precision_m, momento, objetivo, ronda")
                .eq("legajo", str(legajo)).gte("momento", ini.isoformat()).lt("momento", fin.isoformat())
                .order("momento").limit(5000).execute().data or [])
    except Exception as e:
        print(f"[rastro_gps] Error leyendo rastro del día: {e}")
        return []


def resumen_rastro(filas):
    """Metros caminados (suma de tramos con GPS bueno), cantidad de lecturas y última lectura."""
    buenas = [r for r in filas if (r.get("precision_m") is None or r["precision_m"] <= PRECISION_OK_M)]
    total = sum(distancia_m(a["latitud"], a["longitud"], b["latitud"], b["longitud"])
                for a, b in zip(buenas, buenas[1:]))
    return {"lecturas": len(filas), "metros": total, "ultima": filas[-1]["momento"] if filas else None}


# --------------------------------------------------------------------------- componente (celular)
_HTML = r"""<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<style>html,body{margin:0;padding:0;background:transparent;font-family:sans-serif}#m{font-size:12px;color:#00E5FF;padding:6px;text-align:center}</style></head><body>
<div id="m">📡 Rastro GPS: iniciando…</div>
<script>
function enviar(t,d){window.parent.postMessage(Object.assign({isStreamlitMessage:true,type:t},d),"*");}
enviar("streamlit:componentReady",{apiVersion:1});
enviar("streamlit:setFrameHeight",{height:34});
var m=document.getElementById("m"), buf=[], iniciado=false, ultimo=0, err="";
window.addEventListener("message",function(ev){
  if(ev.data && ev.data.type==="streamlit:render" && !iniciado){
    iniciado=true; var a=ev.data.args||{}; arrancar(Number(a.cada)||30);
  }
});
function arrancar(cada){
  var GL=null;
  try{GL=(window.parent.navigator&&window.parent.navigator.geolocation)||navigator.geolocation;}catch(e){GL=navigator.geolocation;}
  if(!GL){m.textContent="⚠️ Este dispositivo no tiene GPS";return;}
  // Mantener la pantalla encendida mientras el recorrido está abierto (si el navegador lo permite)
  var lock=null;
  function pedirLock(){
    try{
      var W=(window.parent.navigator&&window.parent.navigator.wakeLock)||navigator.wakeLock;
      if(W&&W.request){W.request("screen").then(function(l){lock=l;}).catch(function(){});}
    }catch(e){}
  }
  pedirLock();
  document.addEventListener("visibilitychange",function(){ if(document.visibilityState==="visible") pedirLock(); });
  try{window.parent.document.addEventListener("visibilitychange",function(){ if(window.parent.document.visibilityState==="visible") pedirLock(); });}catch(e){}
  GL.watchPosition(function(p){
    var ahora=Date.now(); err="";
    if(ahora-ultimo>=10000){ ultimo=ahora; buf.push({lat:p.coords.latitude,lon:p.coords.longitude,acc:p.coords.accuracy,ts:ahora}); }
    m.textContent="📡 Rastro GPS activo ±"+Math.round(p.coords.accuracy)+" m";
  },function(e){
    err=(e&&e.code===1)?"permiso":"sin_senal";
    m.textContent=(err==="permiso")?"⚠️ Activá el permiso de ubicación":"⚠️ Sin señal GPS";
  },{enableHighAccuracy:true,maximumAge:0,timeout:20000});
  setInterval(function(){
    if(buf.length){ var out=buf.splice(0); enviar("streamlit:setComponentValue",{value:{puntos:out,error:err,ts:Date.now()},dataType:"json"}); }
  },cada*1000);
}
</script></body></html>"""


@st.cache_resource(show_spinner=False)
def _declarar_rastro(version="v2"):
    carpeta = tempfile.mkdtemp(prefix=f"aion_rastro_{version}_")
    with open(os.path.join(carpeta, "index.html"), "w", encoding="utf-8") as f:
        f.write(_HTML)
    return components.declare_component(f"aion_rastro_{version}", path=carpeta)


def activar_rastro(cli, legajo, objetivo, ronda, cada_seg=30):
    """Llamar dentro de la pantalla de recorrido del vigilador. Corre en su propio fragmento
    (no recarga toda la app cada vez que llegan lecturas)."""
    @st.fragment
    def _frag():
        val = _declarar_rastro("v2")(cada=cada_seg, key=f"rastro_gps_{legajo}", default=None)
        if isinstance(val, dict) and val.get("ts") != st.session_state.get("_rastro_ts"):
            st.session_state["_rastro_ts"] = val.get("ts")
            guardar_lecturas(cli, legajo, objetivo, ronda, val.get("puntos") or [])
    _frag()
