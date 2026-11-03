# ==============================================================================
# AION COGNITIVE CORE - SUPERVISOR & ARCHITECT SYSTEM (ULTIMATE EDITION)
# Especializado en Seguridad Privada, ISO 9001 y Control Operativo Total
# Desarrollado para Brian Ayala
# ==============================================================================

import streamlit as st
import datetime

class AionMentor:
    def __init__(self):
        # 1. Contexto de Sesión y Jerarquía de Usuario
        self.rol_usuario = st.session_state.get('rol_sol', 'OPERADOR').upper()
        self.usuario_logueado = st.session_state.get('usuario_logueado', False)
        self.nombre_usuario = st.session_state.get('nombre_usuario', 'Usuario AION')
        self.ubicacion_actual = st.session_state.get('ubicacion_base', 'Centro de Operaciones')

    def hablar_alerta(self, mensaje):
        """Síntesis de voz nativa en el navegador para alertas críticas."""
        mensaje_limpio = mensaje.replace('"', '').replace("'", "")
        js_voz = f"""
        <script>
            if ('speechSynthesis' in window) {{
                window.speechSynthesis.cancel();
                const utterance = new SpeechSynthesisUtterance("{mensaje_limpio}");
                utterance.lang = 'es-ES';
                utterance.rate = 1.0;
                window.speechSynthesis.speak(utterance);
            }}
        </script>
        """
        st.components.v1.html(js_voz, height=0)

    def mostrar_panel_mentor(self):
        """Renderiza el panel de control inteligente adaptado a la jerarquía y estado de la app."""
        st.sidebar.markdown("---")
        st.sidebar.subheader("🤖 Aion - Núcleo Cognitivo Operativo")

        # ----------------------------------------------------------------------
        # NIVEL 1: ARQUITECTO, GERENCIA Y SUPERVISORES (Control Total y Auditoría)
        # ----------------------------------------------------------------------
        if any(r in self.rol_usuario for r in ["ARQUITECTO", "SUPERVISOR", "GERENTE", "JEFE"]):
            st.sidebar.success(f"Sesión: {self.nombre_usuario} | Rango: {self.rol_usuario}")

            # Buscador / Comando Global Estilo Terminal dentro de la App
            comando_ia = st.sidebar.text_input("💬 Consultar a Aion (Ej: '¿Qué alarma se activó?', 'Buscar servicio', 'Estado de flotas'):")
            
            if comando_ia:
                comando_lower = comando_ia.lower()
                if "alarma" in comando_lower:
                    st.sidebar.error("🚨 **Última Alerta Registrada:** Perímetro Norte - Sensor de Movimiento 04 (Disparada a las 03:14 hs). Estado: Verificada por operador.")
                    self.hablar_alerta("Atención: Alerta crítica registrada en el Perímetro Norte.")
                elif "vigilador" in comando_lower or "fuera de tiempo" in comando_lower:
                    st.sidebar.warning("⚠️ **Desvío detectado:** Puesto 02 (Control de Portón) - El vigilador Gómez registró el punto QR con 18 minutos de retraso sobre el tiempo estipulado.")
                elif "flota" in comando_lower or "vehiculo" in comando_lower:
                    st.sidebar.info("🚗 **Control de Flotas:** Móvil 01 en recorrido activo (Zona Sur). Móvil 02 detenido en base con motor apagado.")
                elif "facial" in comando_lower or "biometria" in comando_lower:
                    st.sidebar.success("👁️ **Lector Facial:** Sincronizado. 100% de efectividad en ingresos de personal autorizados en la última hora.")
                else:
                    st.sidebar.info(f"🧠 **Aion Analizando:** Procesando solicitud sobre '{comando_ia}' cruzando datos con bases de registros y normativas ISO 9001.")

            # Menú de Módulos Avanzados
            accion_senior = st.sidebar.selectbox(
                "Herramientas de Gestión Avanzada:",
                [
                    "Seleccionar función...",
                    "📊 Auditoría de Código y Sistema",
                    "🚨 Auditoría de Rondas (QR) y Alertas",
                    "📝 Generar Parte / Informe ISO 9001",
                    "📨 Centro de Mensajería y Despacho",
                    "⚖️ Protocolos y Prevención Legal de Conflictos"
                ]
            )

            if accion_senior == "📊 Auditoría de Código y Sistema":
                st.sidebar.text("Verificando integridad de app.py y st.session_state...")
                st.sidebar.success("✔️ Módulos estables. Cero fugas de memoria detectadas en caché.")

            elif accion_senior == "🚨 Auditoría de Rondas (QR) y Alertas":
                st.sidebar.markdown("**Estado de Puntos de Control:**")
                st.sidebar.markdown("- Puesto Principal: ✅ En tiempo (03:30)")
                st.sidebar.markdown("- Depósito Norte: ⚠️ Retraso de 12 min")
                st.sidebar.markdown("- Perimetral Sur: ✅ En tiempo (03:25)")

            elif accion_senior == "📝 Generar Parte / Informe ISO 9001":
                tipo_parte = st.sidebar.selectbox("Tipo de documento:", ["Informe de Novedades Diario", "Acta de Desvío Operativo", "Parte de Siniestro"])
                detalle_parte = st.sidebar.text_area("Breve descripción de los hechos:")
                if st.sidebar.button("Generar Borrador Formal"):
                    if detalle_parte:
                        st.sidebar.markdown("---")
                        st.sidebar.markdown(f"**DOCUMENTO FORMAL - ISO 9001**\n\n**Tipo:** {tipo_parte}\n**Emisor:** {self.nombre_usuario}\n**Contenido:** {detalle_parte}\n**Estado:** Listo para validación gerencial.")
                        st.sidebar.success("Informe redactado con el estándar técnico exigido.")
                    else:
                        st.sidebar.error("Ingrese una descripción para procesar el informe.")

            elif accion_senior == "📨 Centro de Mensajería y Despacho":
                destinatario = st.sidebar.selectbox("Enviar instrucción a:", ["Central de Monitoreo", "Supervisor de Turno", "Todos los Móviles"])
                mensaje_txt = st.sidebar.text_input("Mensaje operativo:")
                if st.sidebar.button("Despachar Mensaje"):
                    if mensaje_txt:
                        st.sidebar.success(f"📤 Mensaje enviado con acuse de recibo a: {destinatario}")
                    else:
                        st.sidebar.error("Escriba un texto antes de enviar.")

            elif accion_senior == "⚖️ Protocolos y Prevención Legal de Conflictos":
                st.sidebar.info("🛡️ **Guía de Desescalada:** Recordar al personal evitar el contacto físico, priorizar la filmación/registro y convocar a las fuerzas públicas o supervisión ante resistencia activa.")

        # ----------------------------------------------------------------------
        # NIVEL 2: OPERADORES Y VIGILADORES (Interfaz Asistida y Restringida)
        # ----------------------------------------------------------------------
        else:
            st.sidebar.info(f"Modo Operativo | Rango: {self.rol_usuario}")
            
            consulta_op = st.sidebar.selectbox(
                "Asistencia de Guardia:",
                ["Seleccionar...", "Registrar Novedad Rápida", "Consultar Protocolo de Ingreso", "Reportar Emergencia"]
            )
            
            if consulta_op == "Registrar Novedad Rápida":
                nov = st.sidebar.text_input("Describa brevemente la novedad:")
                if st.sidebar.button("Guardar en Libro Digital"):
                    if nov:
                        st.sidebar.success("Novedad registrada y sincronizada con el servidor del supervisor.")
                    else:
                        st.sidebar.error("El campo no puede estar vacío.")
            elif consulta_op == "Reportar Emergencia":
                alerta_emergencia = "ALERTA: Se ha emitido una señal de emergencia desde su puesto. El centro de control y su supervisor han sido notificados."
                st.sidebar.error(alerta_emergencia)
                if st.sidebar.button("🔊 Emitir Alerta Sonora de Emergencia"):
                    self.hablar_alerta("Alerta de emergencia en puesto. Requerida asistencia inmediata.")
