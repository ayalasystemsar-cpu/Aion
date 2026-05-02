# --- B. ROL: MONITOREO ---
elif st.session_state.rol_sel == "MONITOREO":
    st.header("🛰️ CENTRAL DE INTELIGENCIA OPERATIVA")
    df_emergencias = leer_matriz_nube("ALERTAS")
    sos_activos = len(df_emergencias[df_emergencias['ESTADO'].astype(str).str.upper() == 'PENDIENTE']) if not df_emergencias.empty else 0
    
    m1, m2, m3 = st.columns(3)
    m1.metric("🚨 S.O.S ACTIVOS", sos_activos)
    m2.metric("📡 ESTADO DE RED", "OPERATIVO")
    m3.metric("🕒 HORA LOCAL", obtener_hora_argentina().split(" ")[1])

    t_radar, t_gestion = st.tabs(["🚨 RADAR S.O.S", "📖 LIBRO DE BASE"])
    
    with t_radar:
        # 1. Definimos la base del mapa (coordenadas por defecto si no hay S.O.S)
        lat_mapa, lon_mapa = -34.6037, -58.3816 # Centro por defecto (Buenos Aires)
        if not df_objetivos.empty:
            lat_mapa, lon_mapa = df_objetivos['LATITUD'].mean(), df_objetivos['LONGITUD'].mean()

        # 2. Si hay S.O.S, priorizamos esa ubicación y mostramos la alerta
        info_sos = None
        if sos_activos > 0:
            datos_sos = df_emergencias[df_emergencias['ESTADO'].astype(str).str.upper() == 'PENDIENTE'].iloc[-1]
            op_riesgo = datos_sos['USUARIO']
            carga = str(datos_sos.get('CARGA_UTIL', ''))
            try:
                lat_mapa = float(carga.split("|")[0].split(":")[1].strip())
                lon_mapa = float(carga.split("|")[1].split(":")[1].strip())
                info_sos = {"user": op_riesgo, "lat": lat_mapa, "lon": lon_mapa}
            except: pass
            
            obj_cercano, policia, coords_apoyo = calcular_emergencia(lat_mapa, lon_mapa, df_objetivos)
            st.error(f"🚨 EMERGENCIA ACTIVA: {op_riesgo} | OBJETIVO MÁS CERCANO: {obj_cercano} | POLICÍA: {policia}")
        else:
            st.success("✅ Sistema en Vigilancia Pasiva - Radar de Objetivos Operativo")

        # 3. Renderizado del Mapa (Siempre visible)
        st.markdown('<div class="radar-box">', unsafe_allow_html=True)
        m_radar = folium.Map(location=[lat_mapa, lon_mapa], zoom_start=13, tiles="CartoDB dark_matter")
        
        # Dibujamos todos los objetivos del sistema
        for _, r in df_objetivos.iterrows():
            folium.Marker(
                [r['LATITUD'], r['LONGITUD']], 
                popup=r['OBJETIVO'],
                tooltip=r['OBJETIVO'],
                icon=folium.Icon(color="blue", icon="shield", prefix="fa")
            ).add_to(m_radar)

        # Si hay un S.O.S, dibujamos el marcador rojo y la ruta de apoyo
        if info_sos:
            folium.Marker(
                [info_sos["lat"], info_sos["lon"]], 
                tooltip="OPERADOR EN RIESGO", 
                icon=folium.Icon(color="red", icon="warning")
            ).add_to(m_radar)
            
            # Línea de respuesta táctica si hay coordenadas de apoyo
            if 'coords_apoyo' in locals() and coords_apoyo:
                AntPath(locations=[[info_sos["lat"], info_sos["lon"]], [coords_apoyo[0], coords_apoyo[1]]], 
                        color="#FF0000", weight=5, pulse_color="#ffffff").add_to(m_radar)

        st_folium(m_radar, width="100%", height=500, key="mapa_radar_sos")
        st.markdown('</div>', unsafe_allow_html=True)

        # 4. Panel de Neutralización (Solo si hay S.O.S)
        if sos_activos > 0:
            st.subheader("📝 PROTOCOLO DE CIERRE")
            inf_neutralizacion = st.text_area("INFORME DE NEUTRALIZACIÓN", placeholder="Detalle las novedades del cierre...")
            if st.button("FINALIZAR OPERATIVO"):
                if inf_neutralizacion.strip():
                    fila = df_emergencias[df_emergencias['ESTADO'].astype(str).str.upper() == 'PENDIENTE'].index[-1] + 2
                    actualizar_celda("ALERTAS", fila, "D", "RESUELTO")
                    actualizar_celda("ALERTAS", fila, "F", inf_neutralizacion)
                    st.success("Alerta Neutralizada.")
                    st.rerun()
                else:
                    st.warning("Debe completar el informe para cerrar el evento.")

    with t_gestion:
        st.subheader("📖 LIBRO DE BASE - REGISTROS")
        if not df_emergencias.empty:
            st.dataframe(df_emergencias.tail(20), use_container_width=True)
