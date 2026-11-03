import streamlit as st
from aion_mentor import AionMentor

st.set_page_config(page_title="Aion Mentor", page_icon="🛡️", layout="wide")

st.markdown("# 🛡️ Núcleo Cognitivo: Aion Mentor")
st.markdown("---")

try:
    aion = AionMentor()
    aion.mostrar_panel_mentor()
except Exception as e:
    st.info("Módulo de asistencia Aion listo para operar.")
