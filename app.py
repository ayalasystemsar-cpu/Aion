
import streamlit as st
import datetime
from datetime import datetime
import pandas as pd
import pytz
import gspread
from oauth2client.service_account import ServiceAccountCredentials
# ... (mantén tus otros imports de mapas y librerías aquí)

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="AION-YAROKU | COMMAND", page_icon="🛡️", layout="wide", initial_sidebar_state="expanded")

# --- 2. LÓGICA DE LOGIN ---
def mostrar_landing():
    aplicar_identidad_alfa()
    st.markdown('<div class="contenedor-logo-central"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" class="logo-phoenix"></div>', unsafe_allow_html=True)
    st.markdown('<div class="estacion-titulo">AION-YAROKU | COMMAND</div>', unsafe_allow_html=True)
    
    modo = st.radio("Acceso al Sistema:", ["Iniciar Sesión", "Crear Cuenta"], horizontal=True, key="modo_radio_landing")
    
    # ÚNICO FORMULARIO CON TODA LA LÓGICA
    with st.form("form_acceso_unificado"):
        user = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        rol_usuario = st.selectbox("Seleccione su Rol:", ["VIGILADOR", "MONITOREO", "JEFE DE OPERACIONES", "GERENCIA", "SUPERVISOR", "ADMINISTRADOR"])
        
        btn_texto = "ENTRAR" if modo == "Iniciar Sesión" else "REGISTRARSE"
        
        if st.form_submit_button(btn_texto):
            if modo == "Iniciar Sesión":
                df_usuarios = leer_matriz_nube("USUARIOS")
                if df_usuarios.empty:
                    st.error("Error de conexión con la base.")
                else:
                    usuario_ok = df_usuarios[
                        (df_usuarios['USUARIO'] == user) & 
                        (df_usuarios['CONTRASEÑA'] == password) & 
                        (df_usuarios['ESTADO'] == "APROBADO")
                    ]
                    if not usuario_ok.empty:
                        st.session_state.usuario_logueado = True
                        st.session_state.user_sel = user
                        st.session_state.rol_sel = usuario_ok.iloc[0]['ROL']
                        st.rerun()
                    else:
                        st.error("❌ Credenciales incorrectas o cuenta no autorizada.")
            else:
                escribir_registro_nube("USUARIOS", [user, password, rol_usuario, "PENDIENTE"])
                st.success("✅ Solicitud enviada. Quedamos a la espera de autorización.")

# --- 3. CONTROL DE FLUJO (ESTO ES LA LLAVE) ---
if not st.session_state.usuario_logueado:
    mostrar_landing()
    st.stop()  # Detiene la carga del resto si no hay login



    
