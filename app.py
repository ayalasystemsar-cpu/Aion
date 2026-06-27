import streamlit as st
# ... (MANTENÉ TODOS TUS IMPORTS ORIGINALES DE INTENTO 1.txt) ...

# 1. CONFIGURACIÓN DE PÁGINA (Solo una vez)
st.set_page_config(page_title="AION-YAROKU | COMMAND", page_icon="🛡️", layout="wide", initial_sidebar_state="expanded")

# 2. INICIALIZACIÓN DE ESTADO
if 'usuario_logueado' not in st.session_state: st.session_state.usuario_logueado = False

# 3. LÓGICA DE LOGIN (Lo que querés ver al entrar)
if not st.session_state.usuario_logueado:
    # --- Estilo para que la pantalla de Login no sea negra ---
    st.markdown("""<style>.stApp { background: #0A0F1E !important; }</style>""", unsafe_allow_html=True)
    
    st.image("https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg", width=300)
    st.subheader("🔐 ACCESO AION-YAROKU")
    
    user = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")
    
    if st.button("ENTRAR"):
        if user == "admin" and password == "1234":
            st.session_state.usuario_logueado = True
            st.rerun()
        else:
            st.error("Credenciales incorrectas")
            
    st.stop() # ESTO ES LO QUE EVITA QUE EL CÓDIGO OPERATIVO APAREZCA ANTES DE TIEMPO

# 4. SI LLEGAMOS ACÁ, EL LOGIN FUE EXITOSO. 
# AQUÍ PEGÁS TODO TU CÓDIGO DE INTENTO 1.txt (DESDE LAS FUNCIONES HASTA EL FINAL)

# --- TU LÓGICA DE ROLES (INTENTO 1.txt) ---
# ... (Pegá aquí desde 'def conectar_google():' hasta el final de tu archivo original) ...
