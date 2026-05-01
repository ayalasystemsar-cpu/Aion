
    st.subheader(f"📱 Estación: {st.session_state.user_sel}")
    apellido = st.session_state.user_sel.split()[-1].upper()
    df_zona = df_objetivos[df_objetivos['SUPERVISOR'].str.upper().str.contains(apellido, na=False)] if not df_objetivos.empty else pd.DataFrame()
    if df_zona.empty: df_zona = df_objetivos

    t1, t2, t3 = st.tabs(["📍 RADAR & GPS", "📝 NOVEDADES", "💬 COMUNICACIÓN"])
    with t1:
        st.markdown('<div class="radar-box">', unsafe_allow_html=True)
        if not df_zona.empty:
            m = folium.Map(location=[df_zona['LATITUD'].mean(), df_zona['LONGITUD'].mean()], zoom_start=12, tiles="CartoDB dark_matter")
            for _, r in df_zona.iterrows():
                folium.Marker([r['LATITUD'], r['LONGITUD']], popup=r['OBJETIVO'], icon=folium.Icon(color="blue", icon="shield", prefix="fa")).add_to(m)
            st_folium(m, width="100%", height=350)
        st.markdown('</div>', unsafe_allow_html=True)
    with t2:
        st.subheader("📝 REPORTE DE NOVEDADES")
        with st.form("acta_tactica"):
            f_dest = st.selectbox("Objetivo:", df_zona['OBJETIVO'].unique()) if not df_zona.empty else "N/A"
            f_vig = st.text_input("Personal en Puesto")
            f_nov = st.text_area("Informe de Novedad")
            gravedad = st.select_slider("GRAVEDAD:", options=["VERDE", "AMARILLO", "ROJO"])
            if st.form_submit_button("🚀 TRANSMITIR ACTA"):
                datos = [obtener_hora_argentina(), st.session_state.user_sel, "", "", "", "", f_vig, f_dest, f_nov, gravedad]
                if escribir_registro_nube("ACTAS_FLOTAS", datos):
                    st.success("Acta derivada a la matriz.")

# --- B. ROL: MONITOREO (CON MAPA INTEGRADO Y RUTA) ---
elif st.session_state.rol_sel == "MONITOREO":
    st.header("🛰️ CENTRAL DE INTELIGENCIA OPERATIVA")
    df_emergencias = leer_matriz_nube("ALERTAS")
    sos_activos = len(df_emergencias[df_emergencias['ESTADO'].astype(str).str.upper() == 'PENDIENTE']) if not df_emergencias.empty else 0
    
    m1, m2, m3 = st.columns(3)
    m1.metric("🚨 S.O.S ACTIVOS", sos_activos)
    m2.metric("📡 ESTADO DE RED", "OPERATIVO")
    m3.metric("🕒 HORA LOCAL", obtener_hora_argentina().split(" ")[1])

    t_radar, t_gestion, t_chat = st.tabs(["🚨 RADAR S.O.S", "📖 LIBRO DE BASE", "💬 COMUNICACIÓN"])
    
    with t_radar:
        if sos_activos > 0:
            datos_sos = df_emergencias[df_emergencias['ESTADO'].astype(str).str.upper() == 'PENDIENTE'].iloc[-1]
            op_en_riesgo = datos_sos['USUARIO']
            carga = str(datos_sos.get('CARGA_UTIL', ''))
            
            try:
                lat_sos = float(carga.split("|")[0].split(":")[1].strip())
                lon_sos = float(carga.split("|")[1].split(":")[1].strip())
            except: lat_sos, lon_sos = -34.6037, -58.3816 # Coordenadas base si falla GPS

            # Triangulación
            obj_cercano, policia_nombre, coords_apoyo = calcular_emergencia(lat_sos, lon_sos, df_objetivos)
            
            st.markdown(f"""
                <div style="background-color: #FF0000; color: white; padding: 20px; border-radius: 10px; text-align: center; border: 2px solid white; margin-bottom: 10px;">
                    <h2 style="color: white !important;">🚨 EMERGENCIA: {op_en_riesgo} 🚨</h2>
                    <p style="font-size: 18px;"><b>UBICADO EN:</b> {obj_cercano}</p>
                    <p style="font-size: 20px; font-weight: bold; color: #FFFF00;">🚓 COMISARÍA: {policia_nombre}</p>
                </div>
            """, unsafe_allow_html=True)

            st.markdown('<div class="radar-box">', unsafe_allow_html=True)
            m_sos = folium.Map(location=[lat_sos, lon_sos], zoom_start=15, tiles="CartoDB dark_matter")
            
            # Marcador Supervisor / Objetivo
            folium.Marker([lat_sos, lon_sos], tooltip=f"{op_en_riesgo} / {obj_cercano}", icon=folium.Icon(color="red", icon="warning")).add_to(m_sos)
            
            if coords_apoyo:
                # Marcador Comisaría
                folium.Marker([coords_apoyo[0], coords_apoyo[1]], tooltip=f"APOYO: {policia_nombre}", icon=folium.Icon(color="blue", icon="shield", prefix="fa")).add_to(m_sos)
                
                # Ruta Animada Táctica (Uber Style)
                AntPath(locations=[[lat_sos, lon_sos], [coords_apoyo[0], coords_apoyo[1]]], color="#00E5FF", pulse_color="#FFFFFF", weight=5, opacity=0.8).add_to(m_sos)
            
            st_folium(m_sos, width="100%", height=400, key="mapa_mon_sos")
            st.markdown('</div>', unsafe_allow_html=True)
            
            with st.form("cierre_crisis"):
                res_acta = st.text_area("Informe de Neutralización")
                if st.form_submit_button("✅ CERRAR ALERTA"):
                    fila_real = df_emergencias[df_emergencias['ESTADO'].astype(str).str.upper() == 'PENDIENTE'].index[-1] + 2
                    if actualizar_celda("ALERTAS", fila_real, "D", "RESUELTO"):
                        actualizar_celda("ALERTAS", fila_real, "F", res_acta)
                        st.success("Resuelto"); st.cache_data.clear(); st.rerun()
        else:
            st.success("✅ Sistema en Vigilancia Pasiva")
            st.markdown('<div class="radar-box">', unsafe_allow_html=True)
            if not df_objetivos.empty:
                m_pass = folium.Map(location=[df_objetivos['LATITUD'].mean(), df_objetivos['LONGITUD'].mean()], zoom_start=12, tiles="CartoDB dark_matter")
                for _, r in df_objetivos.iterrows():
                    folium.CircleMarker(location=[r['LATITUD'], r['LONGITUD']], radius=5, color="#00E5FF", fill=True, popup=f"Objetivo: {r['OBJETIVO']}").add_to(m_pass)
                st_folium(m_pass, width="100%", height=400, key="mapa_vigilancia_pasiva")
            st.markdown('</div>', unsafe_allow_html=True)

    with t_gestion:
        with st.form("acta_base"):
            op_nombre = st.text_input("Operador:", value=st.session_state.user_sel)
            nov = st.text_area("Novedades")
            if st.form_submit_button("🔒 SELLAR"):
                escribir_registro_nube("MENSAJERIA", [obtener_hora_argentina(), op_nombre, "SISTEMA", "LIBRO BASE", nov, "ENVIADO", "VERDE"])
                st.rerun()
                
    with t_chat:
        st.subheader("📨 CENTRO DE MENSAJERÍA SINCRONIZADO")
        df_m = leer_matriz_nube("MENSAJERIA")
        if not df_m.empty:
            for _, msg in df_m.tail(10).iloc[::-1].iterrows():
                emisor = msg.get('EMISOR', msg.get('Emisor', 'Desconocido'))
                contenido = msg.get('CONTENIDO', msg.get('Contenido', 'Sin mensaje'))
                with st.chat_message("user"):
                    st.write(f"**{emisor}**: {contenido}")

# --- C. ROL: JEFE DE OPERACIONES ---
elif st.session_state.rol_sel == "JEFE DE OPERACIONES":
    st.subheader("📋 COMANDO DE OPERACIONES TÁCTICAS")
    df_actas = leer_matriz_nube("ACTAS_FLOTAS")
    c1, c2, c3 = st.columns(3)
    c1.metric("REPORTES", len(df_actas) if not df_actas.empty else 0)
    c2.metric("OBJETIVOS", len(df_objetivos))
    c3.metric("ESTADO", "SINCRO OK")
    t_inf, t_mapa = st.tabs(["📄 INFORMES", "🌍 MAPA"])
    with t_inf:
        if not df_actas.empty: st.dataframe(df_actas.tail(15), use_container_width=True)
    with t_mapa:
        st.markdown('<div class="radar-box">', unsafe_allow_html=True)
        if not df_objetivos.empty:
            m_ops = folium.Map(location=[df_objetivos['LATITUD'].mean(), df_objetivos['LONGITUD'].mean()], zoom_start=11, tiles="CartoDB dark_matter")
            for _, r in df_objetivos.iterrows():
                folium.Marker(location=[r['LATITUD'], r['LONGITUD']], popup=f"OBJETIVO: {r['OBJETIVO']}", icon=folium.Icon(color="blue", icon="shield", prefix="fa")).add_to(m_ops)
            st_folium(m_ops, width="100%", height=400, key="mapa_jefe_ops")
        st.markdown('</div>', unsafe_allow_html=True)

# --- D. ROL: GERENCIA ---
elif st.session_state.rol_sel == "GERENCIA":
    st.header("📈 DASHBOARD ESTRATÉGICO")
    col_a, col_b = st.columns([1, 2])
    with col_a:
        st.subheader("⚠️ Alertas")
        df_al = leer_matriz_nube("ALERTAS")
        if not df_al.empty: st.write(df_al['ESTADO'].value_counts())
    with col_b:
        st.subheader("🏢 Estructura")
        df_est = leer_matriz_nube("ESTRUCTURA")
        if not df_est.empty: st.dataframe(df_est, use_container_width=True)

# --- E. ROL: ADMINISTRADOR ---
elif st.session_state.rol_sel == "ADMINISTRADOR":
    st.header("⚙️ NÚCLEO MAESTRO")
    with st.expander("🔐 CREDENCIALES DE INFRAESTRUCTURA"):
        u_ing = st.text_input("ADMIN_USER").lower()
        p_ing = st.text_input("ADMIN_PASS", type="password")
        if u_ing == "admin" and p_ing == "aion2026":
            st.subheader("🏗️ GESTIÓN DE ESTRUCTURA")
            tipo = st.radio("Categoría:", ["SUPERVISOR", "SERVICIO"], horizontal=True)
            nuevo_nombre = st.text_input(f"Nombre del {tipo}:").upper()
            if st.button(f"PROCESAR ALTA"):
                if nuevo_nombre:
                    escribir_registro_nube("ESTRUCTURA", [obtener_hora_argentina(), tipo, nuevo_nombre, "ACTIVO", st.session_state.user_sel])
                    st.success("Alta Exitosa")
