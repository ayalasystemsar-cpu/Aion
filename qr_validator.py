import math
from datetime import datetime, timezone, time
import requests
import streamlit as st
from supabase import create_client, Client

# --- 1. CLASE DE VALIDACIÓN TÁCTICA (LIBRERÍA QR) ---
class QRValidator:
    def __init__(self, supabase_client, ntfy_topic: str = None):
        self.supabase = supabase_client
        self.ntfy_topic = ntfy_topic

    def calcular_distancia(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        R = 6371000  # Radio de la Tierra en metros
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon1 - lon2)
        a = (math.sin(dlat / 2) ** 2 +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dlon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    def enviar_alerta_ntfy(self, titulo: str, mensaje: str, prioridad: str = "high"):
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


# --- 2. CONFIGURACIÓN DE SUPABASE Y STREAMLIT ---
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]

@st.cache_resource
def init_connection():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase_client = init_connection()

# Instanciamos el validador (puedes configurar tu tópico de ntfy si deseas push reales)
validator = QRValidator(supabase_client=supabase_client, ntfy_topic="aion_yaroku_alertas")

# --- 3. INTERFAZ GRÁFICA (UI) ---
st.set_page_config(
    page_title="Aion Yaroku - Control Operativo",
    page_icon="🛡️",
    layout="centered"
)

st.title("🛡️ Aion Yaroku: Validación Táctica de Recorridos")
st.markdown("Sistema antifraude con geofencing, control horario y anti-teletransporte.")

st.sidebar.header("⚙️ Configuración de Prueba")
# Coordenadas de referencia simuladas (Ej: Coordenadas fijas del Subsuelo -3 del objetivo)
lat_fija_objetivo = st.sidebar.number_input("Latitud del QR (Objetivo)", value=-34.603722)
lon_fija_objetivo = st.sidebar.number_input("Longitud del QR (Objetivo)", value=-58.381592)

st.subheader("📲 Simulación de Escaneo en Campo")

legajo = st.text_input("Legajo del Vigilador:", value="VIG-4021")
id_punto = st.text_input("ID del Punto / QR Escaneado:", value="subsuelo_-3")

st.markdown("---")
st.markdown("📍 **Ubicación GPS actual del Dispositivo (Celular del Vigilador):**")
col1, col2 = st.columns(2)
with col1:
    lat_usuario = st.number_input("Su Latitud Actual", value=-34.603722, format="%.6f")
with col2:
    lon_usuario = st.number_input("Su Longitud Actual", value=-58.381592, format="%.6f")

if st.button("Validar Marcación con IA Táctica"):
    if not legajo or not id_punto:
        st.warning("⚠️ Completa el legajo y el ID del punto.")
    else:
        with st.spinner("Ejecutando capas de seguridad y validando contra Supabase..."):
            resultado = validator.validar_marcacion(
                legajo_vigilador=legajo,
                id_punto=id_punto,
                lat_objetivo=lat_fija_objetivo,
                lon_objetivo=lon_fija_objetivo,
                lat_usuario=lat_usuario,
                lon_usuario=lon_usuario,
                tolerancia_metros=15.0 # Máximo 15 metros de distancia permitida
            )
            
            if resultado["valido"]:
                st.success(f"✅ {resultado['mensaje']}")
            else:
                st.error(f"🚨 Marcación Rechazada [{resultado.get('tipo_error', 'FRAUDE')}]")
                st.warning(f"Motivo: {resultado['mensaje']}")
                if "distancia" in resultado:
                    st.info(f"📏 Distancia detectada respecto al puesto: {round(resultado['distancia'], 2)} metros.")
