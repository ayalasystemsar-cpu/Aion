
        carga_sos = f"LAT: {lat_act} | LON: {lon_act}"
        escribir_registro_nube("ALERTAS", [obtener_hora_argentina(), st.session_state.user_sel, "PÁNICO", "PENDIENTE", carga_sos])
    st.markdown('</div>', unsafe_allow_html=True)

# --- 6. FLUJO DE INTERFAZ POR ROLES ---
st.markdown('<div class="contenedor-logo-central"><img src="https://raw.githubusercontent.com/ayalasystemsar-cpu/Aion/main/assets/LOGO%20-%20AION-YAROKU.jpeg" class="logo-phoenix"></div>', unsafe_allow_html=True)

df_objetivos = cargar_objetivos()

# --- A. ROL: SUPERVISOR ---
if st.session_state.rol_sel == "SUPERVISOR":
    st.subheader(f"📱 Estación: {st.session_state.user_sel}")
    apellido = st.session_state.user_sel.split()[-1].upper()
    df_zona = df_objetivos[df_objetivos['SUPERVISOR'].str.upper().str.contains(apellido, na=False)] if not df_objetivos.empty else pd.DataFrame()
    if df_zona.empty: df_zona = df_objetivos

    t1, t2 = st.tabs(["📍 RADAR & GPS", "📝 NOVEDADES"])
    with t1:
        st.markdown('<div class="radar-box">', unsafe_allow_html=True)
        if not df_zona.empty:
            m = folium.Map(location=[df_zona['LATITUD'].mean(), df_zona['LONGITUD'].mean()], zoom_start=12, tiles="CartoDB dark_matter")
            for _, r in df_zona.iterrows():
                folium.Marker([r['LATITUD'], r['LONGITUD']], popup=r['OBJETIVO'], icon=folium.Icon(color="blue", icon="shield", prefix="fa")).add_to(m)
            st_folium(m, width="100%", height=350)
        st.markdown('</div>', unsafe_allow_html=True)
    with t2:
        with st.form("nov_sup"):
            f_dest = st.selectbox("Objetivo:", df_zona['OBJETIVO'].unique()) if not df_zona.empty else "N/A"
            f_nov = st.text_area("Informe de Novedad")
            if st.form_submit_button("🚀 TRANSMITIR"):
                escribir_registro_nube("ACTAS_FLOTAS", [obtener_hora_argentina(), st.session_state.user_sel, "", "", "", "", "", f_dest, f_nov, "VERDE"])
                st.success("Enviado.")

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
        if sos_activos > 0:
            datos_sos = df_emergencias[df_emergencias['ESTADO'].astype(str).str.upper() == 'PENDIENTE'].iloc[-1]
            op_riesgo = datos_sos['USUARIO']
            carga = str(datos_sos.get('CARGA_UTIL', ''))
            try:
                lat_sos = float(carga.split("|")[0].split(":")[1].strip())
                lon_sos = float(carga.split("|")[1].split(":")[1].strip())
            except: lat_sos, lon_sos = -34.6037, -58.3816
            
            obj_cercano, policia, coords_apoyo = calcular_emergencia(lat_sos, lon_sos, df_objetivos)
            st.error(f"🚨 EMERGENCIA: {op_riesgo} | {obj_cercano} | POLICÍA: {policia}")
            
            st.markdown('<div class="radar-box">', unsafe_allow_html=True)
            m_sos = folium.Map(location=[lat_sos, lon_sos], zoom_start=15, tiles="CartoDB dark_matter")
            folium.Marker([lat_sos, lon_sos], tooltip=op_riesgo, icon=folium.Icon(color="red", icon="warning")).add_to(m_sos)
            if coords_apoyo:
                folium.Marker([coords_apoyo[0], coords_apoyo[1]], icon=folium.Icon(color="blue", icon="shield", prefix="fa")).add_to(m_sos)
                AntPath(locations=[[lat_sos, lon_sos], [coords_apoyo[0], coords_apoyo[1]]], color="#00E5FF", weight=5).add_to(m_sos)
            st_folium(m_sos, width="100%", height=400)
            st.markdown('</div>', unsafe_allow_html=True)
            if st.button("CERRAR ALERTA"):
                fila = df_emergencias[df_emergencias['ESTADO'].astype(str).str.upper() == 'PENDIENTE'].index[-1] + 2
                actualizar_celda("ALERTAS", fila, "D", "RESUELTO")
                st.rerun()
        else:
            st.success("✅ Sistema en Vigilancia Pasiva")

# --- C. ROL: JEFE DE OPERACIONES ---
elif st.session_state.rol_sel == "JEFE DE OPERACIONES":
    st.subheader("📋 COMANDO DE OPERACIONES TÁCTICAS")
    df_actas = leer_matriz_nube("ACTAS_FLOTAS")
    t_inf, t_mapa = st.tabs(["📄 INFORMES", "🌍 MAPA"])
    with t_inf:
        if not df_actas.empty: st.dataframe(df_actas.tail(20), use_container_width=True)
    with t_mapa:
        st.markdown('<div class="radar-box">', unsafe_allow_html=True)
        if not df_objetivos.empty:
            m_ops = folium.Map(location=[df_objetivos['LATITUD'].mean(), df_objetivos['LONGITUD'].mean()], zoom_start=11, tiles="CartoDB dark_matter")
            for _, r in df_objetivos.iterrows():
                folium.Marker([r['LATITUD'], r['LONGITUD']], popup=r['OBJETIVO']).add_to(m_ops)
            st_folium(m_ops, width="100%", height=450)
        st.markdown('</div>', unsafe_allow_html=True)

# --- D. ROL: GERENCIA ---
elif st.session_state.rol_sel == "GERENCIA":
    st.header("📈 DASHBOARD ESTRATÉGICO")
    df_al = leer_matriz_nube("ALERTAS")
    if not df_al.empty: st.write(df_al['ESTADO'].value_counts())

# --- E. ROL: ADMINISTRADOR ---
elif st.session_state.rol_sel == "ADMINISTRADOR":
    st.header("⚙️ NÚCLEO MAESTRO")
    u_ing = st.text_input("ADMIN_USER")
    p_ing = st.text_input("ADMIN_PASS", type="password")
    if u_ing == "admin" and p_ing == "aion2026":
        tipo = st.radio("Categoría:", ["SUPERVISOR", "SERVICIO"], horizontal=True)
        nuevo_nombre = st.text_input(f"Nombre del {tipo}:").upper()
        if st.button("PROCESAR ALTA"):
            escribir_registro_nube("ESTRUCTURA", [obtener_hora_argentina(), tipo, nuevo_nombre, "ACTIVO", st.session_state.user_sel])
            st.success("Alta Exitosa")
