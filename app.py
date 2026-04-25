import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from datetime import datetime
import pytz
import numpy as np
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from streamlit_js_eval import get_geolocation

# ✅ Función para hora Argentina (va aquí, después de los imports)
def obtener_hora_argentina():
    tz = pytz.timezone("America/Argentina/Buenos_Aires")
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

# --- 1. CONFIGURACIÓN E IDENTIDAD VISUAL CORPORATIVA ---
st.set_page_config(page_title="AION-YAROKU", layout="wide", initial_sidebar_state="expanded")

# (CSS y estilos se mantienen igual...)

# --- 2. MEMORIA DE SESIÓN Y TELEMETRÍA (ANTI-RESETEO) ---
if 'rol_sel' not in st.session_state: st.session_state.rol_sel = "SUPERVISOR"
if 'user_sel' not in st.session_state: st.session_state.user_sel = "AYALA BRIAN"
if 'qr_mode' not in st.session_state: st.session_state.qr_mode = "Seleccionar..."
if 'hora_inicio_auditoria' not in st.session_state: st.session_state.hora_inicio_auditoria = None

# --- 3. NÚCLEO DE CONEXIÓN Y MATRIZ NUBE ---
ID_MAESTRO_DB = "1Md0VkOnwUJWldq0S1fB9UrmOKv4MG__JVG3tQsda0Uw"

def conectar_google():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
    return gspread.authorize(creds)

def escribir_registro(pestana, datos_fila):
    try:
        gc = conectar_google()
        hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
        hoja.append_row(datos_fila)
        return True
    except: return False

def actualizar_celda(pestana, fila_excel, col_letra, nuevo_valor):
    try:
        gc = conectar_google()
        hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
        hoja.update_acell(f"{col_letra}{fila_excel}", nuevo_valor)
        return True
    except: return False

def borrar_fila_excel(pestana, fila_excel):
    try:
        gc = conectar_google()
        hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet(pestana)
        hoja.delete_rows(fila_excel)
        return True
    except: return False

# (leer_matriz_nube, cargar_objetivos, calcular_objetivo_cercano se mantienen igual...)

# --- 5. ESTRUCTURA LATERAL E IDENTIDAD ---
with st.sidebar:
    # (Logo y selección de roles igual...)

    # Motor S.O.S Balístico
    if rol == "SUPERVISOR":
        if st.button("🚨 ACTIVAR PÁNICO", use_container_width=True):
            loc = get_geolocation()
            lat_sos, lon_sos = "Desconocida", "Desconocida"
            if loc: 
                lat_sos, lon_sos = loc['coords']['latitude'], loc['coords']['longitude']
            
            carga_sos = f"LAT: {lat_sos} | LON: {lon_sos}"
            if escribir_registro("ALERTAS", [obtener_hora_argentina(), usuario_auth, "CRÍTICO", "PENDIENTE", carga_sos, ""]):
                st.error("S.O.S TRANSMITIDO A LA MATRIZ. APOYO EN CAMINO.")

# --- 6. MÓDULO SUPERVISOR ---
if rol == "SUPERVISOR" and usuario_auth:
    # (Control de Unidad Móvil)
    if st.button("Sellar Odometría"):
        if km_out >= km_in:
            escribir_registro("CONTROL_FLOTA", [obtener_hora_argentina(), usuario_auth, movil_flota, km_in, km_out, comb_cargado])
            st.success("Logística de flota sellada en la matriz.")

    # (QR Control)
    if escribir_registro("LOG_PRESENCIA", [obtener_hora_argentina(), usuario_auth, dest, tipo, "QR_VALIDADO", delta_t]):
        st.success(f"✅ OPERACIÓN {tipo} CONFIRMADA EN MATRIZ.")

    # (Actas Flotas)
    escribir_registro("ACTAS_FLOTAS", [
        obtener_hora_argentina(),
        usuario_auth,
        f_mov,
        "",
        f_km,
        "",
        f_vig,
        f_dest,
        f_nov,
        grav_corta
    ])

    escribir_registro("MENSAJERIA", [
        obtener_hora_argentina(),
        usuario_auth,
        dest_msg,
        f"Acta {f_dest}",
        f_nov,
        "ENVIADO",
        grav_corta
    ])

# --- 7. MONITOREO ---
if alerta_critica:
    if st.form_submit_button("Neutralizar Alarma y Sellar Acta"):
        hora_cierre = obtener_hora_argentina()
        actualizar_celda("ALERTAS", fila_alerta, "D", "RESUELTO") 
        actualizar_celda("ALERTAS", fila_alerta, "F", f"Cierre: {hora_cierre} | OPE: {op} | Acta: {res}")

# --- 8. EJECUTIVO ---
if st.form_submit_button("Solicitar Alta a Admin"):
    escribir_registro("PETICIONES", [obtener_hora_argentina(), usuario_auth, "ALTA", f"{n} | {s}", "PENDIENTE", "OBJETIVO"])

if st.form_submit_button("Solicitar Baja a Admin"):
    escribir_registro("PETICIONES", [obtener_hora_argentina(), usuario_auth, "BAJA", rem, "PENDIENTE", "OBJETIVO"])

if st.form_submit_button("Ejecutar Directiva"):
    escribir_registro("MENSAJERIA", [obtener_hora_argentina(), usuario_auth, dest, a, m, "ENVIADO", grav])

# --- 9. ADMINISTRADOR (CANDADO DE TITANIO MANTENIDO Y PLENAMENTE OPERATIVO) ---
elif rol == "ADMINISTRADOR":
    st.header("⚙️ NÚCLEO MAESTRO AION-YAROKU")
    st.success("AUTENTICACIÓN EXITOSA. BIENVENIDO AL SISTEMA, AYALA BRIAN.")
    
    st.markdown("---")
    st.subheader("⚖️ Buzón de Peticiones y Ejecución (Gestión de Base)")
    df_pet = leer_matriz_nube("PETICIONES")
    if not df_pet.empty and 'ESTADO' in df_pet.columns:
        pendientes = df_pet[df_pet['ESTADO'].astype(str).str.strip().str.upper() == 'PENDIENTE']
        if pendientes.empty: st.info("No hay solicitudes pendientes de Gerencia o Jefatura.")
        else:
            for idx, r in pendientes.iterrows():
                tipo = str(r.get('ACCIÓN', r.get('ACCION', '')))
                detalle = str(r.get('DETALLE', ''))
                categoria = str(r.get('CATEGORIA', 'OBJETIVO'))
                fila_pet_real = idx + 2
                
                with st.expander(f"⚠️ Solicitud de {tipo} - De: {r.get('GERENTE', r.get('USUARIO', ''))} - Detalle: {detalle} ({categoria})"):
                    c_ok, c_no = st.columns(2)
                    if c_ok.button(f"✅ AUTORIZAR EJECUCIÓN", key=f"ok_{idx}"):
                        if tipo.upper() == "BAJA" and categoria.upper() == "OBJETIVO":
                            indice_borrar = df_objetivos[df_objetivos['OBJETIVO'] == detalle].index
                            if not indice_borrar.empty:
                                # Borra de la pestaña OBJETIVOS (+2 para convertir índice a fila Google Sheet)
                                if borrar_fila_excel("OBJETIVOS", int(indice_borrar[0]) + 2):
                                    actualizar_celda("PETICIONES", fila_pet_real, "E", "EJECUTADO") # Columna E = ESTADO
                                    st.success(f"Servicio {detalle} eliminado de la base.")
                                    st.cache_data.clear(); st.rerun()
                        elif tipo.upper() == "ALTA" and categoria.upper() == "OBJETIVO":
                            actualizar_celda("PETICIONES", fila_pet_real, "E", "EJECUTADO")
                            st.success(f"Autorizado. (El alta física en mapa requiere cargar lat/lon en el Excel).")
                            st.cache_data.clear(); st.rerun()

                    if c_no.button(f"❌ RECHAZAR SOLICITUD", key=f"no_{idx}"):
                        actualizar_celda("PETICIONES", fila_pet_real, "E", "RECHAZADO")
                        st.warning("Petición rechazada y archivada.")
                        st.cache_data.clear(); st.rerun()
    else: st.info("Matriz de peticiones no detectada o vacía.")

    st.markdown("---")
    st.subheader("Auditoría Cruda de Terreno (Logs Nube)")
    df_p = leer_matriz_nube("LOG_PRESENCIA")
    if not df_p.empty: st.dataframe(df_p.tail(30).iloc[::-1], use_container_width=True)
