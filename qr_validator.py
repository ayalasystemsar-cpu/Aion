import math
from datetime import datetime, timezone, time
import requests

class QRValidator:
    def __init__(self, supabase_client, ntfy_topic: str = None):
        """
        Librería táctica para validación de códigos QR, geofencing, anti-teletransporte 
        y control de ventanas horarias en Aion Yaroku.
        
        :param supabase_client: Instancia cliente de Supabase conectada.
        :param ntfy_topic: Tópico de ntfy.sh para alertas instantáneas push a supervisores.
        """
        self.supabase = supabase_client
        self.ntfy_topic = ntfy_topic

    def calcular_distancia(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calcula la distancia métrica exacta entre dos puntos GPS usando la fórmula de Haversine.
        Retorna la distancia en metros.
        """
        R = 6371000  # Radio de la Tierra en metros
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon1 - lon2)
        a = (math.sin(dlat / 2) ** 2 +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dlon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    def enviar_alerta_ntfy(self, titulo: str, mensaje: str, prioridad: str = "high"):
        """Envía una notificación push instantánea a los supervisores vía ntfy.sh."""
        if not self.ntfy_topic:
            return
        try:
            requests.post(
                f"https://ntfy.sh/{self.ntfy_topic}",
                data=mensaje.encode("utf-8"),
                headers={
                    "Title": titulo,
                    "Priority": prioridad,
                    "Tags": "rotating_light,police_car"
                }
            )
        except Exception as e:
            print(f"Error al enviar alerta ntfy: {e}")

    def validar_ventana_horaria(self, legajo: str, id_punto: str) -> dict:
        """
        Verifica si la hora actual se encuentra dentro del rango horario 
        autorizado para la ronda o punto en curso según la planificación en Supabase.
        """
        try:
            response = self.supabase.table("rondas_asignadas") \
                .select("hora_inicio, hora_fin, activo") \
                .eq("legajo", legajo) \
                .eq("id_punto", id_punto) \
                .eq("activo", True) \
                .execute()
            
            data = response.data
            if not data:
                return {"valido": True}

            hora_actual = datetime.now(timezone.utc).time()
            
            for asignacion in data:
                h_inicio = time.fromisoformat(asignacion["hora_inicio"])
                h_fin = time.fromisoformat(asignacion["hora_fin"])
                
                if h_inicio <= hora_actual <= h_fin:
                    return {"valido": True}
            
            return {
                "valido": False,
                "mensaje": f"Fuera de horario operativo. La marcación para el punto {id_punto} no corresponde a la ventana horaria actual."
            }
        except Exception as e:
            print(f"Error validando horario en DB: {e}")
            return {"valido": True}

    def validar_marcacion(
        self, 
        legajo_vigilador: str, 
        id_punto: str, 
        lat_objetivo: float, 
        lon_objetivo: float, 
        lat_usuario: float, 
        lon_usuario: float, 
        tolerancia_metros: float = 15.0,
        tiempo_minimo_segundos: int = 30
    ) -> dict:
        """
        Ejecuta todas las capas de validación táctica en secuencia estricta:
        1. Ventana Horaria.
        2. Geolocalización GPS (Geofencing / Anti-Foto desde garita).
        3. Control de Velocidad (Anti-Teletransporte entre puntos).
        """
        
        # --- CAPA 1: VALIDACIÓN HORARIA ---
        check_horario = self.validar_ventana_horaria(legajo_vigilador, id_punto)
        if not check_horario["valido"]:
            motivo = check_horario["mensaje"]
            self._registrar_fraude(legajo_vigilador, id_punto, "FRAUDE_HORARIO", motivo, lat_usuario, lon_usuario)
            self.enviar_alerta_ntfy(
                "⏰ ALERTA: Marcación Fuera de Horario", 
                f"Vigilador {legajo_vigilador} intentó marcar el punto {id_punto} fuera de su ventana asignada."
            )
            return {"valido": False, "tipo_error": "FUERA_DE_HORARIO", "mensaje": motivo}

        # --- CAPA 2: VALIDACIÓN GPS (GEOFENCING / ANTI-FOTO) ---
        distancia_real = self.calcular_distancia(lat_usuario, lon_usuario, lat_objetivo, lon_objetivo)
        
        if distancia_real > tolerancia_metros:
            motivo = f"Fuera de rango geográfico. Distancia real: {round(distancia_real, 2)}m (Máx permitido: {tolerancia_metros}m)."
            self._registrar_fraude(legajo_vigilador, id_punto, "FRAUDE_GPS", motivo, lat_usuario, lon_usuario)
            self.enviar_alerta_ntfy(
                "🚨 ALERTA DE FRAUDE: QR Escaneado a Distancia", 
                f"Vigilador {legajo_vigilador} intentó marcar el punto {id_punto} a {round(distancia_real, 2)} metros de distancia (Posible foto)."
            )
            return {
                "valido": False, 
                "tipo_error": "GPS_FUERA_DE_RANGO", 
                "mensaje": motivo,
                "distancia": distancia_real
            }

        # --- CAPA 3: CONTROL DE VELOCIDAD (ANTI-TELETRANSPORTE) ---
        ultimo_registro = self._obtener_ultimo_registro(legajo_vigilador)
        
        if ultimo_registro:
            ultimo_punto = ultimo_registro.get("id_punto")
            ultimo_tiempo_str = ultimo_registro.get("timestamp")
            
            ultimo_tiempo = datetime.fromisoformat(ultimo_tiempo_str.replace("Z", "+00:00"))
            tiempo_actual = datetime.now(timezone.utc)
            diferencia_segundos = (tiempo_actual - ultimo_tiempo).total_seconds()
            
            if id_punto != ultimo_punto and diferencia_segundos < tiempo_minimo_segundos:
                motivo = f"Velocidad anómala. Marcó el punto anterior hace solo {int(diferencia_segundos)} segundos."
                self._registrar_fraude(legajo_vigilador, id_punto, "FRAUDE_VELOCIDAD", motivo, lat_usuario, lon_usuario)
                self.enviar_alerta_ntfy(
                    "⚡ ALERTA: Patrullaje Imposible (Teletransporte)", 
                    f"Vigilador {legajo_vigilador} cambió de punto demasiado rápido ({int(diferencia_segundos)}s)."
                )
                return {
                    "valido": False, 
                    "tipo_error": "VELOCIDAD_ANOMALA", 
                    "mensaje": motivo,
                    "tiempo_transcurrido": diferencia_segundos
                }

        # --- ÉXITO TOTAL: REGISTRO VÁLIDO ---
        self._registrar_exito(legajo_vigilador, id_punto, lat_usuario, lon_usuario)
        return {
            "valido": True,
            "mensaje": "Marcación validada y registrada correctamente."
        }

    def _obtener_ultimo_registro(self, legajo: str):
        """Consulta en Supabase el último punto marcado exitosamente por el vigilador."""
        try:
            response = self.supabase.table("historial_marcaciones") \
                .select("id_punto, timestamp") \
                .eq("legajo", legajo) \
                .eq("estado", "EXITOSO") \
                .order("timestamp", desc=True) \
                .limit(1) \
                .execute()
            
            data = response.data
            return data[0] if data else None
        except Exception as e:
            print(f"Error consultando DB: {e}")
            return None

    def _registrar_fraude(self, legajo: str, id_punto: str, tipo_fraude: str, detalle: str, lat: float, lon: float):
        """Registra el intento de fraude en la tabla de auditoría de Supabase."""
        try:
            self.supabase.table("auditoria_fraudes").insert({
                "legajo": legajo,
                "id_punto": id_punto,
                "tipo_fraude": tipo_fraude,
                "detalle": detalle,
                "latitud": lat,
                "longitud": lon,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }).execute()
        except Exception as e:
            print(f"Error registrando fraude en DB: {e}")

    def _registrar_exito(self, legajo: str, id_punto: str, lat: float, lon: float):
        """Guarda la marcación exitosa en la tabla de historial de Supabase."""
        try:
            self.supabase.table("historial_marcaciones").insert({
                "legajo": legajo,
                "id_punto": id_punto,
                "estado": "EXITOSO",
                "latitud": lat,
                "longitud": lon,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }).execute()
        except Exception as e:
            print(f"Error registrando éxito en DB: {e}")
      
