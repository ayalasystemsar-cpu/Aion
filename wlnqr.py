"""
wlnqr - Validación antifraude de marcaciones QR para AION-YAROKU.

Solo contiene LÓGICA (sin st.title, sin st.set_page_config, sin pantallas):
se importa desde la app principal con:  import wlnqr

Reglas, en este orden:
  1. La ronda no puede estar completa ni el punto repetido.
  2. ORDEN: solo se acepta el próximo punto de la lista (no se puede saltear).
  3. HORARIO: ventana asignada en rondas_asignadas (hora argentina).
  4. GPS: la ubicación tomada AL ESCANEAR tiene que estar cerca de ESE punto
     (si escanea fotos de varios QR desde un solo lugar, falla acá).
  5. TIEMPO: mínimo de segundos desde el punto anterior.
"""
import math
from datetime import datetime, time, timezone

import pytz
import requests

TZ_AR = pytz.timezone("America/Argentina/Buenos_Aires")


def distancia_m(lat1, lon1, lat2, lon2):
    """Distancia en metros entre dos coordenadas (haversine)."""
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = p2 - p1
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlam / 2) ** 2
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _rta(valido, tipo=None, mensaje="", fraude=False, **extra):
    d = {"valido": valido, "tipo_error": tipo, "mensaje": mensaje, "fraude": fraude}
    d.update(extra)
    return d


class QRValidator:
    TOLERANCIA_DEFECTO_M = 25     # metros permitidos entre el celular y el punto
    SEG_MIN_DEFECTO = 30          # segundos mínimos desde el punto anterior
    PRECISION_MAX_M = 100         # si el GPS es peor que esto, se pide reintentar (no se acusa)

    def __init__(self, supabase_client=None, ntfy_topic=None, on_fraude=None):
        self.db = supabase_client          # puede ser None: las reglas funcionan igual
        self.ntfy_topic = ntfy_topic
        self.on_fraude = on_fraude

    # ------------------------------------------------------------------ puntos
    def config_punto(self, objetivo, id_punto):
        """Ubicación y límites guardados de un punto (tabla puntos_control)."""
        if self.db is None:
            return {}
        try:
            r = (self.db.table("puntos_control")
                 .select("latitud, longitud, tolerancia_m, seg_min")
                 .eq("objetivo", str(objetivo).strip().upper())
                 .eq("id_punto", str(id_punto).strip().upper())
                 .limit(1).execute())
            return r.data[0] if r.data else {}
        except Exception as e:
            print(f"[wlnqr] Error leyendo puntos_control: {e}")
            return {}

    def guardar_ubicacion_punto(self, objetivo, id_punto, lat, lon, tolerancia_m=None, seg_min=None):
        """El supervisor, parado frente al QR, guarda dónde está ese punto."""
        if self.db is None:
            return False
        try:
            fila = {
                "objetivo": str(objetivo).strip().upper(),
                "id_punto": str(id_punto).strip().upper(),
                "latitud": float(lat),
                "longitud": float(lon),
                "actualizado": datetime.now(TZ_AR).isoformat(),
            }
            if tolerancia_m:
                fila["tolerancia_m"] = int(tolerancia_m)
            if seg_min:
                fila["seg_min"] = int(seg_min)
            self.db.table("puntos_control").upsert(fila, on_conflict="objetivo,id_punto").execute()
            return True
        except Exception as e:
            print(f"[wlnqr] Error guardando ubicación del punto: {e}")
            return False

    # ----------------------------------------------------------------- horario
    def _ventana_horaria(self, legajo, id_punto):
        if self.db is None:
            return {"valido": True}
        try:
            data = (self.db.table("rondas_asignadas")
                    .select("hora_inicio, hora_fin")
                    .eq("legajo", legajo).eq("id_punto", id_punto).eq("activo", True)
                    .execute().data)
        except Exception as e:
            print(f"[wlnqr] Error leyendo rondas_asignadas: {e}")
            return {"valido": True}
        if not data:
            return {"valido": True}
        ahora = datetime.now(TZ_AR).time()          # hora ARGENTINA (antes era UTC)
        for a in data:
            ini, fin = time.fromisoformat(a["hora_inicio"]), time.fromisoformat(a["hora_fin"])
            dentro = (ini <= ahora <= fin) if ini <= fin else (ahora >= ini or ahora <= fin)
            if dentro:
                return {"valido": True}
        return {"valido": False,
                "mensaje": f"Fuera de horario. La marcación del punto {id_punto} no corresponde a la ventana actual."}

    # --------------------------------------------------------------- principal
    def validar_marcacion(self, legajo, objetivo, id_punto, orden_puntos, marcados,
                          lat_usuario, lon_usuario, precision_m=None,
                          ultima_marca=None, ronda=1, fallback=None, on_fraude=None):
        """
        orden_puntos : lista de puntos del objetivo en el orden del recorrido.
        marcados     : puntos ya marcados en ESTA ronda.
        lat/lon_usuario, precision_m : GPS tomado en el instante del escaneo.
        ultima_marca : datetime (hora argentina, sin zona) de la última marca de esta ronda, o None.
        fallback     : (lat, lon, tolerancia_m) del objetivo, si el punto no tiene ubicación propia.
        Devuelve dict: valido, tipo_error, mensaje, fraude (True = se reportó como posible fraude).
        """
        id_punto = str(id_punto).strip().upper()
        orden = [str(p).strip().upper() for p in orden_puntos]
        hechos = {str(p).strip().upper() for p in marcados}
        ctx = {"legajo": legajo, "objetivo": objetivo, "id_punto": id_punto,
               "lat": lat_usuario, "lon": lon_usuario, "precision": precision_m}
        cb = on_fraude or self.on_fraude

        # 1) Ronda / repetidos
        if id_punto not in orden:
            return _rta(False, "PUNTO_DESCONOCIDO", "Ese punto no pertenece a este objetivo.")
        pendientes = [p for p in orden if p not in hechos]
        if not pendientes:
            return _rta(False, "RONDA_COMPLETA", "La ronda ya está completa. No se aceptan más escaneos.")
        if id_punto in hechos:
            return _rta(False, "YA_MARCADO", "Ese punto ya fue marcado en esta ronda.")

        # 2) Orden obligatorio
        siguiente = pendientes[0]
        if id_punto != siguiente:
            self._auditar("FUERA_DE_ORDEN", f"Escaneó {id_punto} y el siguiente era {siguiente}.", ctx)
            return _rta(False, "FUERA_DE_ORDEN", f"No podés saltearte puntos. Te toca: {siguiente}.",
                        siguiente=siguiente)

        # 3) Horario
        h = self._ventana_horaria(legajo, id_punto)
        if not h["valido"]:
            return self._fraude("FRAUDE_HORARIO", h["mensaje"], ctx, cb)

        # 4) GPS en el momento del escaneo
        if lat_usuario is None or lon_usuario is None:
            return _rta(False, "SIN_GPS", "No se pudo tomar tu ubicación al escanear. Activá el GPS y permití la ubicación.")
        cfg = self.config_punto(objetivo, id_punto)
        lat_p, lon_p = cfg.get("latitud"), cfg.get("longitud")
        tol = cfg.get("tolerancia_m") or self.TOLERANCIA_DEFECTO_M
        if lat_p is None or lon_p is None:
            if not fallback:
                return _rta(False, "SIN_UBICACION_PUNTO",
                            "Este punto todavía no tiene ubicación cargada. Avisale a tu supervisor.")
            lat_p, lon_p, tol = fallback          # ubicación del objetivo, con margen mayor
        d = distancia_m(float(lat_usuario), float(lon_usuario), float(lat_p), float(lon_p))
        prec = float(precision_m or 0)
        if prec > self.PRECISION_MAX_M and d > tol:
            return _rta(False, "GPS_IMPRECISO", f"Señal GPS débil (±{prec:.0f} m). Salí a un lugar abierto y reintentá.",
                        distancia=d)
        if d - prec > tol:
            return self._fraude(
                "FRAUDE_GPS",
                f"Escaneó {id_punto} a {d:.0f} m del punto (máx. {tol} m, precisión GPS ±{prec:.0f} m). Posible foto del QR.",
                ctx, cb, distancia=d)
        if d > tol:
            return _rta(False, "GPS_IMPRECISO", "No se pudo confirmar tu posición. Esperá unos segundos y reintentá.",
                        distancia=d)

        # 5) Tiempo mínimo desde el punto anterior
        seg_min = cfg.get("seg_min") or self.SEG_MIN_DEFECTO
        if ultima_marca is not None:
            ahora = datetime.now(TZ_AR).replace(tzinfo=None)
            seg = (ahora - ultima_marca).total_seconds()
            if 0 <= seg < seg_min:
                return self._fraude(
                    "FRAUDE_VELOCIDAD",
                    f"Marcó el punto anterior hace {int(seg)} s (mínimo {seg_min} s). Recorrido imposible.",
                    ctx, cb, segundos=seg)

        self._registrar_exito(legajo, objetivo, id_punto, ronda, lat_usuario, lon_usuario, precision_m)
        return _rta(True, None, "Marcación validada.", False, distancia=d)

    # ---------------------------------------------------------- fraude / logs
    def _fraude(self, tipo, detalle, ctx, cb, **extra):
        self._auditar(tipo, detalle, ctx)
        self._ntfy(f"ALERTA DE FRAUDE QR ({tipo})",
                   f"Vigilador {ctx['legajo']} - {ctx['objetivo']} - punto {ctx['id_punto']}: {detalle}")
        if cb:
            try:
                cb(tipo, detalle, ctx)
            except Exception as e:
                print(f"[wlnqr] Error en callback de fraude: {e}")
        return _rta(False, tipo, detalle, True, **extra)

    def _ntfy(self, titulo, mensaje):
        if not self.ntfy_topic:
            return
        try:   # el título va SIN emojis: los headers HTTP solo admiten latin-1
            requests.post(f"https://ntfy.sh/{self.ntfy_topic}", data=mensaje.encode("utf-8"), timeout=5,
                          headers={"Title": titulo.encode("ascii", "ignore").decode(),
                                   "Priority": "high", "Tags": "rotating_light"})
        except Exception as e:
            print(f"[wlnqr] Error enviando ntfy: {e}")

    def _auditar(self, tipo, detalle, ctx):
        if self.db is None:
            return
        try:
            self.db.table("auditoria_fraudes").insert({
                "legajo": ctx["legajo"], "objetivo": ctx["objetivo"], "id_punto": ctx["id_punto"],
                "tipo_fraude": tipo, "detalle": detalle,
                "latitud": ctx["lat"], "longitud": ctx["lon"], "precision_m": ctx["precision"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }).execute()
        except Exception as e:
            print(f"[wlnqr] Error registrando auditoría: {e}")

    def _registrar_exito(self, legajo, objetivo, id_punto, ronda, lat, lon, precision):
        if self.db is None:
            return
        try:
            self.db.table("historial_marcaciones").insert({
                "legajo": legajo, "objetivo": objetivo, "id_punto": id_punto, "ronda": ronda,
                "estado": "EXITOSO", "latitud": lat, "longitud": lon,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }).execute()
        except Exception as e:
            print(f"[wlnqr] Error registrando marcación: {e}")
