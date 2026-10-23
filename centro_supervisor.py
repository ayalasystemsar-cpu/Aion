# -*- coding: utf-8 -*-
"""
AION-YAROKU | CENTRO DEL SUPERVISOR
-----------------------------------
Se instala desde el archivo principal con:

    import centro_supervisor
    centro_supervisor.instalar(globals())      # debajo de aplicar_identidad_alfa() (la de después del login)
    ...
    centro_supervisor.enrutar()                # debajo del bloque de renderizar_personal_supervisor(...)

Agrega:
  * Supervisor  -> botón "CENTRO DEL SUPERVISOR": mapa de objetivos, pánico con comisaría zonal y cercanas,
                   alta y baja de objetivos, traspaso de objetivos y carga táctica.
  * Monitoreo   -> botón "COMISARÍA DERIVADA": ve qué comisaría eligió el supervisor.
  * Corrige registrar_objetivo (respeta las columnas OBJETIVO | CALLE | ALTURA | LOCALIDAD | SUPERVISOR).
  * Evita que el supervisor se mande el aviso de alta/baja a sí mismo.
"""
import re
import folium
import gspread
import pandas as pd
import streamlit as st
from branca.element import Element
from streamlit_folium import st_folium

_ORIGINALES = {}

# =========================================================================
# 1. CORRECCIONES A FUNCIONES EXISTENTES
# =========================================================================
def _sin_tilde(t):
    return (str(t).strip().upper().replace("Á", "A").replace("É", "E")
            .replace("Í", "I").replace("Ó", "O").replace("Ú", "U"))


def registrar_objetivo_v2(nombre_obj, calle, altura, localidad, supervisor, responsables=""):
    """Agrega el objetivo respetando los encabezados reales de la hoja OBJETIVOS."""
    try:
        gc = conectar_google()
        if not gc:
            return False
        hoja = _obtener_hoja_para_escribir(gc, obtener_mapeo_solapas().get("OBJETIVOS", "OBJETIVOS"))
        enc = [str(h).strip().upper() for h in _reintentar_429(lambda: hoja.row_values(1))]
        if not enc:
            enc = ["OBJETIVO", "CALLE", "ALTURA", "LOCALIDAD", "SUPERVISOR"]
            _reintentar_429(lambda: hoja.append_row(enc))
        claves = [_sin_tilde(h) for h in enc]
        for col in ("OBJETIVO", "CALLE", "ALTURA", "LOCALIDAD", "SUPERVISOR"):
            if col not in claves:
                _asegurar_columna(hoja, enc, col)
                claves.append(col)
        calle_u = str(calle).strip().upper()
        altura_u = str(altura).strip().upper()
        valores = {
            "OBJETIVO": str(nombre_obj).strip().upper(),
            "CALLE": calle_u,
            "ALTURA": altura_u,
            "DIRECCION": (calle_u + " " + altura_u).strip(),
            "LOCALIDAD": str(localidad).strip().upper(),
            "SUPERVISOR": str(supervisor).strip().upper(),
            "RESPONSABLES": str(responsables).strip().upper(),
            "RESPONSABLE": str(responsables).strip().upper(),
        }
        fila = [valores.get(k, "") for k in claves]
        try:
            _reintentar_429(lambda: hoja.append_row(fila, table_range="A1"))
        except TypeError:
            _reintentar_429(lambda: hoja.append_row(fila))
        st.cache_data.clear()
        return True
    except Exception as e:
        print(f"Error registrando objetivo: {e}")
        st.error(f"⚠️ Error técnico en nube (OBJETIVOS): {e}")
        return False


def _avisar_cambio_servicio_v2(supervisor, asunto, texto, usuario):
    """Si el supervisor hace el alta/baja él mismo, el aviso va solo a Jefe y Gerencia (no a sí mismo)."""
    if str(supervisor).strip().upper() == str(usuario).strip().upper():
        notificar_novedad(texto)
        return
    notificar_novedad(texto, extra=[supervisor])
    escribir_registro_nube("MENSAJERIA", [obtener_hora_argentina(), usuario, supervisor, asunto, texto, "PENDIENTE", "AMARILLO"])


# =========================================================================
# 2. AYUDAS DE PÁNICO / COMISARÍAS
# =========================================================================
_COLS_DERIV = ["FECHA_HORA", "SUPERVISOR", "VIGILADOR", "FECHA_PANICO", "OBJETIVO", "CALLE", "ALTURA", "LOCALIDAD",
               "COMISARIA", "TIPO", "DIRECCION_COMISARIA", "TELEFONO", "DISTANCIA_KM"]


def _cs_panicos_pendientes(objs=None, sup=None):
    """Pánicos PENDIENTES. Con objs/sup: solo los de esos objetivos o de ese supervisor. Sin nada: todos."""
    df = leer_matriz_nube("ALERTAS")
    if df.empty:
        return []
    limite = (datetime.strptime(obtener_hora_argentina(), "%Y-%m-%d %H:%M:%S")
              - pd.Timedelta(hours=HORAS_ALARMA_PANICO)).strftime("%Y-%m-%d %H:%M:%S")
    filtrar = objs is not None
    objs_u = {str(o).strip().upper() for o in (objs or [])}
    sup_u = str(sup or "").strip().upper()
    salida = []
    for _, r in df.iterrows():
        f = [str(x).strip() for x in r.tolist()] + [""] * 6
        if f[2].upper().replace("Á", "A") != "PANICO" or f[3].upper() != "PENDIENTE" or f[0] < limite:
            continue
        if filtrar and not (f[4].upper() in objs_u or (sup_u and f[5].upper() == sup_u)):
            continue
        salida.append({"FECHA": f[0], "VIGILADOR": f[1].upper(), "OBJETIVO": f[4].upper(), "SUPERVISOR": f[5].upper()})
    return salida


def _cs_firma(panicos):
    return tuple(sorted(p["FECHA"] + "|" + p["VIGILADOR"] for p in panicos))


def _cs_comisarias(lat, lon, n=5):
    """Comisarías cercanas (OpenStreetMap), de la más cercana a la más lejana. La primera es la ZONAL."""
    import time
    alm = _almacen_geo()
    cache = alm.setdefault("coms_lista", {})
    fallo = alm.setdefault("coms_lista_fallo", {})
    clave = (round(lat, 4), round(lon, 4))
    if clave in cache:
        return cache[clave][:n]
    if time.time() - fallo.get(clave, 0) < 120:
        return []
    cand = _buscar_comisarias_osm(lat, lon)
    if not cand:
        fallo[clave] = time.time()
        return []
    vistos, out = set(), []
    for c in cand:
        k = (c["nombre"], round(c["lat"], 4), round(c["lon"], 4))
        if k in vistos:
            continue
        vistos.add(k)
        c = dict(c)
        if not c.get("telefono"):
            c["telefono"] = "911"
        out.append(c)
    cache[clave] = out
    return out[:n]


def _cs_derivacion_vigente(df_d, fecha_panico, vigilador):
    if df_d.empty or not {"FECHA_PANICO", "VIGILADOR"} <= set(df_d.columns):
        return None
    m = ((col_texto(df_d, "FECHA_PANICO").str.strip() == str(fecha_panico).strip()) &
         (col_texto(df_d, "VIGILADOR").str.strip().str.upper() == str(vigilador).strip().upper()))
    sub = df_d[m]
    if sub.empty:
        return None
    return sub.iloc[-1].to_dict()


def _cs_registrar_derivacion(sup, p, fila, c, tipo):
    try:
        gc = conectar_google()
        if not gc:
            return False
        sh = gc.open_by_key(ID_MAESTRO_DB)
        try:
            hoja = sh.worksheet("COMISARIA DERIVADA")
        except Exception:
            hoja = sh.add_worksheet(title="COMISARIA DERIVADA", rows="300", cols=str(len(_COLS_DERIV)))
            hoja.append_row(_COLS_DERIV, value_input_option="RAW")
        dist = "%.2f" % float(c.get("distancia_km", 0))
        hoja.append_row([obtener_hora_argentina(), sup, p["VIGILADOR"], p["FECHA"], p["OBJETIVO"],
                         str(fila["CALLE"]), str(fila["ALTURA"]), str(fila["LOCALIDAD"]),
                         str(c["nombre"]), tipo, str(c.get("direccion", "")), str(c.get("telefono", "")), dist],
                        value_input_option="RAW")
        st.cache_data.clear()
        notificar_novedad("🚔 " + sup + " derivó el pánico de " + p["VIGILADOR"] + " (" + p["OBJETIVO"] + ") a la comisaría " +
                          str(c["nombre"]) + " (" + tipo + ", " + dist + " km).", extra=["OPERADOR CENTRAL"])
        return True
    except Exception as e:
        print(f"Error registrando derivación de comisaría: {e}")
        return False


# =========================================================================
# 3. MAPA (íconos propios, distintos a los de Monitoreo)
# =========================================================================
_CS_CSS = """
<style>
.leaflet-container { background: #262626 !important; }
.leaflet-tile-pane { filter: invert(100%) hue-rotate(180deg) grayscale(100%) brightness(0.8) contrast(1.25); }
@keyframes cspulse { from { transform: scale(1); opacity: 1; } to { transform: scale(1.6); opacity: .35; } }
</style>
"""

_CS_LEYENDA = ('<div style="display:flex;flex-wrap:wrap;gap:12px;font-size:12px;color:#CBD5E1;margin:6px 0 10px;">'
               '<span>🏢 <b style="color:#FFC107;">Mis objetivos</b></span>'
               '<span>🚨 <b style="color:#FF5252;">Pánico</b></span>'
               '<span>🚔 <b style="color:#2979FF;">Comisaría zonal</b></span>'
               '<span>🚓 <b style="color:#90A4AE;">Comisarías cercanas</b></span>'
               '<span>🟡 <b style="color:#FFD600;">Anillo dorado = elegida</b></span></div>')


def _cs_mapa_base(centro, zoom):
    m = folium.Map(location=centro, zoom_start=zoom, max_zoom=19, tiles="OpenStreetMap")
    m.get_root().header.add_child(Element(_CS_CSS))
    return m


def _cs_icono_objetivo():
    html = ('<div style="width:34px;height:34px;border-radius:50% 50% 50% 0;transform:rotate(-45deg);'
            'background:linear-gradient(135deg,#FFC107,#FF8F00);border:2px solid #fff;'
            'box-shadow:0 0 10px rgba(255,160,0,.8);display:flex;align-items:center;justify-content:center;">'
            '<span style="transform:rotate(45deg);font-size:16px;">🏢</span></div>')
    return folium.DivIcon(icon_size=(34, 34), icon_anchor=(17, 41), html=html)


def _cs_icono_panico():
    html = ('<div style="width:34px;height:34px;border-radius:50%;background:#FF1744;border:3px solid #fff;'
            'display:flex;align-items:center;justify-content:center;font-size:17px;'
            'animation:cspulse .8s infinite alternate;box-shadow:0 0 16px #FF1744;">🚨</div>')
    return folium.DivIcon(icon_size=(34, 34), icon_anchor=(17, 17), html=html)


def _cs_icono_comisaria(zonal, elegida=False):
    borde = "#FFD600" if elegida else ("#2979FF" if zonal else "#90A4AE")
    if zonal:
        html = ('<div style="text-align:center;">'
                '<div style="width:38px;height:38px;border-radius:50%;background:#0D47A1;border:3px solid ' + borde + ';'
                'display:flex;align-items:center;justify-content:center;font-size:22px;box-shadow:0 0 14px #2979FF;">🚔</div>'
                '<div style="font:700 9px sans-serif;color:#fff;background:#0D47A1;border-radius:4px;padding:0 4px;margin-top:1px;">ZONAL</div></div>')
        return folium.DivIcon(icon_size=(44, 56), icon_anchor=(22, 19), html=html)
    html = ('<div style="width:26px;height:26px;border-radius:6px;background:#37474F;border:2px solid ' + borde + ';'
            'display:flex;align-items:center;justify-content:center;font-size:14px;">🚓</div>')
    return folium.DivIcon(icon_size=(26, 26), icon_anchor=(13, 13), html=html)


def _cs_ruta(m, lat, lon, com, color):
    ruta = obtener_ruta_calles_osrm(lat, lon, com["lat"], com["lon"])
    folium.PolyLine(locations=ruta, color="#000000", weight=6, opacity=0.4).add_to(m)
    folium.PolyLine(locations=ruta, color=color, weight=4, opacity=0.9).add_to(m)


def _cs_dibujar_comisarias(m, coms, nombre_elegida, dibujadas):
    for i, c in enumerate(coms):
        clave = (c["nombre"], round(c["lat"], 4), round(c["lon"], 4))
        if clave in dibujadas:
            continue
        dibujadas.add(clave)
        es_elegida = bool(nombre_elegida) and str(c["nombre"]).upper() == nombre_elegida
        etiqueta = "⭐ ZONAL / JURISDICCIONAL" if i == 0 else "🚓 CERCANA"
        tip = etiqueta + " · " + str(c["nombre"]) + " · " + ("%.2f" % float(c["distancia_km"])) + " km" + (" · ✅ ELEGIDA" if es_elegida else "")
        folium.Marker([c["lat"], c["lon"]], tooltip=tip, icon=_cs_icono_comisaria(i == 0, es_elegida)).add_to(m)


def _cs_etiqueta_comisaria(i, c):
    base = ("⭐ ZONAL · " if i == 0 else "🚓 CERCANA · ") + str(c["nombre"]) + " · " + ("%.2f" % float(c["distancia_km"])) + " km"
    d = str(c.get("direccion", "") or "").strip()
    return base + ((" · " + d) if d and d != "---" else "")


# =========================================================================
# 4. CENTRO DEL SUPERVISOR
# =========================================================================
@st.fragment(run_every=10)
def _cs_vigia(sup, objs):
    """Si entra o termina un pánico mientras el supervisor mira el mapa, recarga la pantalla sola."""
    try:
        nuevo = _cs_firma(_cs_panicos_pendientes(objs, sup))
    except Exception:
        return
    if nuevo != st.session_state.get("_cs_firma"):
        st.session_state["_cs_firma"] = nuevo
        st.rerun()


def _cs_tab_mapa(sup, mis):
    if mis.empty:
        st.info("No tenés objetivos a cargo. Podés darlos de alta en la solapa 🟢 ALTA.")
        return
    objs = [str(o).strip().upper() for o in mis["OBJETIVO"]]
    panicos = _cs_panicos_pendientes(objs, sup)
    st.session_state["_cs_firma"] = _cs_firma(panicos)
    _cs_vigia(sup, objs)

    if st.button("🔄 ACTUALIZAR MAPA", key="cs_btn_act", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    with st.spinner("Ubicando objetivos en el mapa..."):
        ub = con_coordenadas(mis)
    sin_ubicar = ub[ub["LATITUD"].isna() | ub["LONGITUD"].isna()]["OBJETIVO"].astype(str).tolist()
    ub = ub.dropna(subset=["LATITUD", "LONGITUD"]).copy()
    if ub.empty:
        st.warning("⚠️ No se pudo ubicar ningún objetivo en el mapa. Revisá calle, altura y localidad.")
        return

    df_d = leer_matriz_nube("COMISARIA DERIVADA")
    por_panico = []
    for p in panicos:
        f = ub[col_texto(ub, "OBJETIVO").str.strip().str.upper() == p["OBJETIVO"]]
        fila = f.iloc[0] if not f.empty else None
        coms = _cs_comisarias(float(fila["LATITUD"]), float(fila["LONGITUD"]), 5) if fila is not None else []
        der = _cs_derivacion_vigente(df_d, p["FECHA"], p["VIGILADOR"])
        por_panico.append((p, fila, coms, der))

    if por_panico and por_panico[0][1] is not None:
        centro = [float(por_panico[0][1]["LATITUD"]), float(por_panico[0][1]["LONGITUD"])]
        zoom = 14
    else:
        centro = [float(ub["LATITUD"].mean()), float(ub["LONGITUD"].mean())]
        zoom = 12
    m = _cs_mapa_base(centro, zoom)

    obj_panico = {p["OBJETIVO"] for p, _, _, _ in por_panico}
    for _, r in ub.iterrows():
        nom = str(r["OBJETIVO"]).strip().upper()
        dir_txt = str(r["CALLE"]) + " " + str(r["ALTURA"]) + ", " + str(r["LOCALIDAD"])
        if nom in obj_panico:
            folium.Marker([float(r["LATITUD"]), float(r["LONGITUD"])], tooltip="🚨 PÁNICO | " + nom + " | " + dir_txt,
                          icon=_cs_icono_panico()).add_to(m)
        else:
            folium.Marker([float(r["LATITUD"]), float(r["LONGITUD"])], tooltip="🏢 " + nom + " | " + dir_txt,
                          icon=_cs_icono_objetivo()).add_to(m)

    dibujadas = set()
    for p, fila, coms, der in por_panico:
        if fila is None or not coms:
            continue
        lat, lon = float(fila["LATITUD"]), float(fila["LONGITUD"])
        nombre_elegida = str(der.get("COMISARIA", "")).strip().upper() if der else ""
        _cs_dibujar_comisarias(m, coms, nombre_elegida, dibujadas)
        _cs_ruta(m, lat, lon, coms[0], "#39FF14")
        if nombre_elegida and nombre_elegida != str(coms[0]["nombre"]).upper():
            for c in coms[1:]:
                if str(c["nombre"]).upper() == nombre_elegida:
                    _cs_ruta(m, lat, lon, c, "#FFD600")

    st.markdown(_CS_LEYENDA, unsafe_allow_html=True)
    st_folium(m, use_container_width=True, height=460, key="cs_mapa_supervisor", returned_objects=[])
    if sin_ubicar:
        st.caption("⚠️ No se pudo ubicar en el mapa: " + ", ".join(sin_ubicar) + ". Revisá calle, altura y localidad.")

    if not por_panico:
        st.success("✅ Sin pánicos activos en tus objetivos.")
        return

    st.markdown("#### 🚨 PÁNICOS ACTIVOS EN MIS OBJETIVOS")
    for p, fila, coms, der in por_panico:
        if fila is not None:
            donde = str(fila["CALLE"]) + " " + str(fila["ALTURA"]) + ", " + str(fila["LOCALIDAD"])
        else:
            donde = "dirección sin ubicar"
        st.error("🚨 " + p["VIGILADOR"] + " · " + p["OBJETIVO"] + " (" + donde + ") · " + p["FECHA"])
        if fila is None:
            st.warning("⚠️ No se pudo ubicar este objetivo en el mapa; no se pueden calcular comisarías.")
            continue
        if not coms:
            st.warning("⚠️ No se encontraron comisarías cercanas. Motivo: " + str(_almacen_geo().get("com_error", "sin datos")) +
                       ". Probá con 🔄 ACTUALIZAR MAPA.")
            continue
        etiquetas = [_cs_etiqueta_comisaria(i, c) for i, c in enumerate(coms)]
        idx_def = 0
        if der:
            nom_e = str(der.get("COMISARIA", "")).strip().upper()
            for i, c in enumerate(coms):
                if str(c["nombre"]).upper() == nom_e:
                    idx_def = i
        clave = re.sub(r"\W", "", p["FECHA"] + p["VIGILADOR"])
        sel = st.radio("Elegí la comisaría de derivación:", list(range(len(coms))), index=idx_def,
                       format_func=lambda i, L=etiquetas: L[i], key="cs_rad_" + clave)
        c_sel = coms[sel]
        st.markdown("📞 [" + str(c_sel.get("telefono", "911")) + "](tel:" + str(c_sel.get("telefono", "911")) + ")")
        if der:
            st.caption("✅ Ya derivaste a " + str(der.get("COMISARIA", "")) + " (" + str(der.get("TIPO", "")) + ") el " +
                       str(der.get("FECHA_HORA", "")) + ". Podés cambiarla y confirmar de nuevo.")
        if st.button("✅ CONFIRMAR COMISARÍA", key="cs_conf_" + clave, use_container_width=True):
            ok = _cs_registrar_derivacion(sup, p, fila, c_sel, "ZONAL" if sel == 0 else "CERCANA")
            st.session_state.cs_msg = (ok, ("✅ Comisaría confirmada: " + str(c_sel["nombre"]) + ". Monitoreo ya puede verla.")
                                       if ok else "❌ No se pudo registrar la derivación. Revisá la conexión con Google Sheets.")
            st.rerun()


def _cs_tab_alta(sup):
    st.subheader("ALTA DE OBJETIVO")
    with st.form("cs_form_alta", clear_on_submit=True):
        a_nom = st.text_input("Nombre del objetivo:")
        a_calle = st.text_input("Calle:")
        a_altura = st.text_input("Altura:")
        a_loc = st.text_input("Localidad:")
        if st.form_submit_button("🟢 DAR DE ALTA", use_container_width=True):
            if not (a_nom.strip() and a_calle.strip() and a_altura.strip() and a_loc.strip()):
                st.session_state.cs_msg = (False, "⚠️ Completá nombre del objetivo, calle, altura y localidad.")
            elif not a_altura.strip().isdigit():
                st.session_state.cs_msg = (False, "⚠️ La altura debe ser un número (ej: 1234).")
            else:
                ok, txt = alta_servicio(a_nom, a_calle, a_altura.strip(), a_loc, sup, "", sup)
                if ok:
                    txt = "Objetivo " + a_nom.strip().upper() + " dado de alta."
                    if not geocodificar_direccion(a_calle, a_altura.strip(), a_loc):
                        txt += " Ojo: no se pudo ubicar en el mapa; revisá calle, altura y localidad."
                st.session_state.cs_msg = (ok, ("✅ " if ok else "❌ ") + txt)
            st.rerun()


def _cs_tab_baja(sup, mis):
    st.subheader("BAJA DE OBJETIVO")
    objs = sorted({str(o).strip().upper() for o in mis["OBJETIVO"]}) if not mis.empty else []
    if not objs:
        st.info("No tenés objetivos para dar de baja.")
        return
    with st.form("cs_form_baja", clear_on_submit=True):
        b_obj = st.selectbox("Objetivo que se da de baja:", objs)
        b_mot = st.text_input("Motivo de la baja:")
        b_ok = st.checkbox("Confirmo que quiero dar de baja este objetivo")
        if st.form_submit_button("🔴 DAR DE BAJA", use_container_width=True):
            if not (b_obj and b_mot.strip() and b_ok):
                st.session_state.cs_msg = (False, "⚠️ Elegí el objetivo, escribí el motivo y tildá la confirmación.")
            else:
                ok, txt = baja_servicio(b_obj, b_mot, sup)
                if ok:
                    txt = "Objetivo " + b_obj + " dado de baja."
                st.session_state.cs_msg = (ok, ("✅ " if ok else "❌ ") + txt)
            st.rerun()


def _cs_traspasar(origen, destino, objetivos, motivo):
    try:
        gc = conectar_google()
        hoja = gc.open_by_key(ID_MAESTRO_DB).worksheet("OBJETIVOS")
        filas = hoja.get_all_values()
        enc = [str(h).strip().upper() for h in filas[0]]
        i_obj, i_sup = enc.index("OBJETIVO"), enc.index("SUPERVISOR")
        i_est = enc.index("ESTADO") if "ESTADO" in enc else None
        objs_u = {str(o).strip().upper() for o in objetivos}
        A = gspread.utils.rowcol_to_a1
        cambios, movidos = [], []
        for n, f in enumerate(filas[1:], start=2):
            if len(f) <= max(i_obj, i_sup):
                continue
            if (f[i_obj].strip().upper() in objs_u and f[i_sup].strip().upper() == origen and
                    not (i_est is not None and len(f) > i_est and f[i_est].strip().upper() == "BAJA")):
                cambios.append({"range": A(n, i_sup + 1), "values": [[destino]]})
                movidos.append(f[i_obj].strip().upper())
        if not cambios:
            return False, "No se encontraron esos objetivos a tu cargo."
        hoja.batch_update(cambios)

        sh = gc.open_by_key(ID_MAESTRO_DB)
        try:
            h_log = sh.worksheet("TRASPASOS OBJETIVOS")
        except Exception:
            h_log = sh.add_worksheet(title="TRASPASOS OBJETIVOS", rows="300", cols="6")
            h_log.append_row(["FECHA_HORA", "ORIGEN", "DESTINO", "OBJETIVO", "MOTIVO", "REGISTRADO_POR"], value_input_option="RAW")
        fecha = obtener_hora_argentina()
        h_log.append_rows([[fecha, origen, destino, o, motivo, origen] for o in movidos], value_input_option="RAW")
        st.cache_data.clear()

        lista = ", ".join(movidos)
        texto = ("🔁 TRASPASO DE OBJETIVOS: " + origen + " traspasó a " + destino + " " + str(len(movidos)) +
                 " objetivo(s): " + lista + ". Motivo: " + motivo + ". Ya figuran en tu panel, con su personal.")
        notificar_novedad(texto, extra=[destino])
        escribir_registro_nube("MENSAJERIA", [fecha, origen, destino, "TRASPASO DE OBJETIVOS", texto, "PENDIENTE", "AMARILLO"])
        return True, "Traspasaste " + str(len(movidos)) + " objetivo(s) a " + destino + ". Se le avisó."
    except Exception as e:
        print(f"Error traspasando objetivos: {e}")
        return False, "No se pudo hacer el traspaso: " + str(e)


def _cs_tab_traspaso(sup, mis):
    st.subheader("TRASPASO DE OBJETIVOS")
    st.caption("Si te enfermás, salís de licencia o de vacaciones, pasás tus objetivos a otro supervisor. "
               "El cambio es directo y a él le llega el aviso. Su personal pasa con cada objetivo.")
    objs = sorted({str(o).strip().upper() for o in mis["OBJETIVO"]}) if not mis.empty else []
    otros = [s for s in obtener_lista_supervisores_dinamica() if str(s).strip().upper() != sup]
    if not objs:
        st.info("No tenés objetivos para traspasar.")
    elif not otros:
        st.info("No hay otros supervisores aprobados a quienes traspasar.")
    else:
        with st.form("cs_form_tras", clear_on_submit=True):
            todos = st.checkbox("Traspasar TODOS mis objetivos")
            sel = st.multiselect("O elegí los objetivos:", objs)
            dest = st.selectbox("Supervisor que los cubre:", otros)
            motivo = st.selectbox("Motivo:", ["ENFERMEDAD", "LICENCIA", "VACACIONES", "BAJA DEL SUPERVISOR", "OTRO"])
            det = st.text_input("Detalle (opcional):")
            conf = st.checkbox("Confirmo el traspaso")
            if st.form_submit_button("🔁 TRASPASAR OBJETIVOS", use_container_width=True):
                elegidos = objs if todos else sel
                if not elegidos:
                    st.session_state.cs_msg = (False, "⚠️ Elegí al menos un objetivo.")
                elif not conf:
                    st.session_state.cs_msg = (False, "⚠️ Tildá la confirmación para traspasar.")
                else:
                    mot = motivo + ((" - " + det.strip().upper()) if det.strip() else "")
                    ok, txt = _cs_traspasar(sup, str(dest).strip().upper(), elegidos, mot)
                    st.session_state.cs_msg = (ok, ("✅ " if ok else "❌ ") + txt)
                st.rerun()

    df = leer_matriz_nube("TRASPASOS OBJETIVOS")
    if not df.empty and {"ORIGEN", "DESTINO"} <= set(df.columns):
        m = ((col_texto(df, "ORIGEN").str.strip().str.upper() == sup) | (col_texto(df, "DESTINO").str.strip().str.upper() == sup))
        mios = df[m]
        if not mios.empty:
            st.markdown("**Mis traspasos (hechos y recibidos)**")
            cols = [c for c in ["FECHA_HORA", "OBJETIVO", "ORIGEN", "DESTINO", "MOTIVO"] if c in mios.columns]
            st.dataframe(mios[cols].iloc[::-1].head(20), use_container_width=True, hide_index=True)


def _cs_tab_carga(sup, mis):
    st.subheader("CARGA TÁCTICA")
    st.caption("Registrá novedades operativas de tus objetivos. Les llega aviso a Jefe de Operaciones y Gerencia, "
               "y se cuentan en el relevamiento mensual.")
    objs = sorted({str(o).strip().upper() for o in mis["OBJETIVO"]}) if not mis.empty else []
    if not objs:
        st.info("No tenés objetivos a cargo.")
        return
    with st.form("cs_form_car", clear_on_submit=True):
        obj = st.selectbox("Objetivo:", objs)
        tipo = st.selectbox("Tipo:", ["NOVEDAD OPERATIVA", "INCIDENTE", "ANOMALÍA / DESPERFECTO", "PEDIDO LOGÍSTICO", "OTRO"])
        txt = st.text_area("Detalle:")
        if st.form_submit_button("📋 CARGAR REGISTRO", use_container_width=True):
            if not txt.strip():
                st.session_state.cs_msg = (False, "⚠️ Escribí el detalle antes de cargar.")
            else:
                detalle = txt.strip().upper()
                ok = escribir_registro_nube("NOVEDADES GUARDIA", [obtener_hora_argentina(), obj, "NOVEDAD OPERATIVA",
                                                                 "[" + tipo + "] " + detalle, sup, "---", "PROCESADO", sup])
                if ok:
                    notificar_novedad("📋 CARGA TÁCTICA: " + sup + " registró en " + obj + " · " + tipo + ": " + detalle[:200])
                st.session_state.cs_msg = (bool(ok), "✅ Carga táctica registrada." if ok else "❌ No se pudo registrar.")
            st.rerun()

    df = leer_matriz_nube("NOVEDADES GUARDIA")
    if not df.empty and df.shape[1] >= 5:
        d = df.iloc[:, :5].copy()
        d.columns = ["FECHA", "OBJETIVO", "TIPO", "DETALLE", "SUPERVISOR"]
        d = d[(d["TIPO"].astype(str).str.strip().str.upper() == "NOVEDAD OPERATIVA") &
              (d["SUPERVISOR"].astype(str).str.strip().str.upper() == sup)]
        if not d.empty:
            st.markdown("**Mis últimas cargas tácticas**")
            st.dataframe(d[["FECHA", "OBJETIVO", "DETALLE"]].iloc[::-1].head(15), use_container_width=True, hide_index=True)


def renderizar_centro_supervisor(sup):
    sup = str(sup).strip().upper()
    alarma_panico_sonora("SUPERVISOR", sup, solo_cartel=True)
    st.markdown("### 🧭 CENTRO DEL SUPERVISOR")
    msg = st.session_state.pop("cs_msg", None)
    if msg:
        (st.success if msg[0] else st.error)(msg[1])

    df_o = cargar_objetivos()
    if not df_o.empty and "SUPERVISOR" in df_o.columns:
        mis = df_o[col_texto(df_o, "SUPERVISOR").str.strip().str.upper() == sup].copy()
    else:
        mis = pd.DataFrame()

    t_mapa, t_alta, t_baja, t_tras, t_car = st.tabs(["🗺️ MAPA", "🟢 ALTA", "🔴 BAJA", "🔁 TRASPASO", "📋 CARGA TÁCTICA"])
    with t_mapa:
        _cs_tab_mapa(sup, mis)
    with t_alta:
        _cs_tab_alta(sup)
    with t_baja:
        _cs_tab_baja(sup, mis)
    with t_tras:
        _cs_tab_traspaso(sup, mis)
    with t_car:
        _cs_tab_carga(sup, mis)


# =========================================================================
# 5. MONITOREO: COMISARÍA DERIVADA POR EL SUPERVISOR
# =========================================================================
@st.fragment(run_every=10)
def _cs_vigia_mon():
    try:
        pan = _cs_firma(_cs_panicos_pendientes())
        df_d = leer_matriz_nube("COMISARIA DERIVADA")
        nuevo = (pan, len(df_d))
    except Exception:
        return
    if nuevo != st.session_state.get("_cs_firma_mon"):
        st.session_state["_cs_firma_mon"] = nuevo
        st.rerun()


def renderizar_derivacion_monitoreo():
    alarma_panico_sonora("MONITOREO", st.session_state.get("user_sel", ""))
    st.markdown("### 🚔 COMISARÍA DERIVADA POR EL SUPERVISOR")

    panicos = _cs_panicos_pendientes()
    df_o = cargar_objetivos()
    df_d = leer_matriz_nube("COMISARIA DERIVADA")
    st.session_state["_cs_firma_mon"] = (_cs_firma(panicos), len(df_d))
    _cs_vigia_mon()

    if st.button("🔄 ACTUALIZAR", key="cs_mon_act", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    if not panicos:
        st.success("✅ No hay pánicos activos en este momento.")

    for k, p in enumerate(panicos):
        fila = None
        if not df_o.empty:
            f = df_o[col_texto(df_o, "OBJETIVO").str.strip().str.upper() == p["OBJETIVO"]]
            if not f.empty:
                fila = f.iloc[0]
        der = _cs_derivacion_vigente(df_d, p["FECHA"], p["VIGILADOR"])

        st.error("🚨 PÁNICO · " + p["VIGILADOR"] + " · " + p["FECHA"])
        if fila is not None:
            st.markdown("**Objetivo:** " + p["OBJETIVO"] + "  \n**Calle:** " + str(fila["CALLE"]) + "  \n**Altura:** " +
                        str(fila["ALTURA"]) + "  \n**Localidad:** " + str(fila["LOCALIDAD"]) + "  \n**Supervisor:** " + str(p["SUPERVISOR"]))
        else:
            st.markdown("**Objetivo:** " + p["OBJETIVO"] + "  \n**Supervisor:** " + str(p["SUPERVISOR"]))

        nombre_elegida = ""
        if der:
            nombre_elegida = str(der.get("COMISARIA", "")).strip().upper()
            tipo = str(der.get("TIPO", "")).upper()
            etiqueta = "⭐ COMISARÍA ZONAL / JURISDICCIONAL" if tipo == "ZONAL" else "🚓 COMISARÍA CERCANA (no zonal)"
            tel = str(der.get("TELEFONO", "") or "911")
            st.success(etiqueta + "\n\n**" + str(der.get("COMISARIA", "")) + "** · " + str(der.get("DISTANCIA_KM", "")) + " km  \n" +
                       "Dirección: " + str(der.get("DIRECCION_COMISARIA", "") or "---") + "  \nElegida por " +
                       str(der.get("SUPERVISOR", "")) + " el " + str(der.get("FECHA_HORA", "")))
            st.markdown("📞 [" + tel + "](tel:" + tel + ")")
        else:
            st.warning("⏳ El supervisor todavía no eligió comisaría.")

        if fila is not None:
            g = geocodificar_direccion(fila["CALLE"], fila["ALTURA"], fila["LOCALIDAD"])
            if g:
                coms = _cs_comisarias(g[0], g[1], 5)
                m = _cs_mapa_base([g[0], g[1]], 14)
                folium.Marker([g[0], g[1]], tooltip="🚨 PÁNICO | " + p["OBJETIVO"], icon=_cs_icono_panico()).add_to(m)
                if coms:
                    _cs_dibujar_comisarias(m, coms, nombre_elegida, set())
                    destino = coms[0]
                    color = "#39FF14"
                    for c in coms:
                        if nombre_elegida and str(c["nombre"]).upper() == nombre_elegida:
                            destino, color = c, "#FFD600"
                    _cs_ruta(m, g[0], g[1], destino, color)
                st.markdown(_CS_LEYENDA, unsafe_allow_html=True)
                st_folium(m, use_container_width=True, height=380, key="cs_mon_mapa_" + str(k), returned_objects=[])
        st.markdown("---")

    if not df_d.empty:
        with st.expander("🕘 HISTORIAL DE COMISARÍAS DERIVADAS"):
            cols = [c for c in ["FECHA_HORA", "SUPERVISOR", "VIGILADOR", "OBJETIVO", "CALLE", "ALTURA", "LOCALIDAD",
                                "COMISARIA", "TIPO", "DISTANCIA_KM"] if c in df_d.columns]
            st.dataframe(df_d[cols].iloc[::-1].head(20), use_container_width=True, hide_index=True)


# =========================================================================
# 6. BOTONES DE LA BARRA LATERAL Y RUTEO
# =========================================================================
def _cs_boton_centro():
    if st.session_state.get("rol_sel") != "SUPERVISOR" or not st.session_state.get("sup_autenticado"):
        return
    st.markdown("---")
    activo = st.session_state.get("ver_centro_sup", False)
    if st.button("⬅️ VOLVER A MI ESTACIÓN" if activo else "🧭 CENTRO DEL SUPERVISOR",
                 use_container_width=True, key="btn_centro_sup_sidebar"):
        st.session_state["ver_centro_sup"] = not activo
        st.session_state["ver_personal_sup"] = False
        st.rerun()


def _cs_boton_derivacion():
    if st.session_state.get("rol_sel") != "MONITOREO":
        return
    st.markdown("---")
    activo = st.session_state.get("ver_derivacion_mon", False)
    if st.button("⬅️ VOLVER AL RADAR" if activo else "🚔 COMISARÍA DERIVADA",
                 use_container_width=True, key="btn_derivacion_mon_sidebar"):
        st.session_state["ver_derivacion_mon"] = not activo
        st.rerun()


def boton_personal_ampliado():
    """Reemplaza a mostrar_boton_personal_supervisor: agrega los dos botones nuevos y deja el original igual."""
    if st.session_state.get("ver_personal_sup"):
        st.session_state["ver_centro_sup"] = False
    _cs_boton_centro()
    _cs_boton_derivacion()
    original = _ORIGINALES.get("boton_personal")
    if original:
        original()


def enrutar():
    ss = st.session_state
    if ss.get("rol_sel") == "SUPERVISOR" and ss.get("sup_autenticado") and ss.get("ver_centro_sup", False):
        renderizar_centro_supervisor(ss.get("user_sel", ""))
        st.stop()
    if ss.get("rol_sel") == "MONITOREO" and ss.get("ver_derivacion_mon", False):
        renderizar_derivacion_monitoreo()
        st.stop()


_PROPIOS = set(globals().keys())


def instalar(g):
    """Se llama una vez por ejecución desde el archivo principal: instala las funciones nuevas y corregidas."""
    for k, v in g.items():
        if k.startswith("__") or k in _PROPIOS:
            continue
        globals()[k] = v
    _ORIGINALES["boton_personal"] = g.get("mostrar_boton_personal_supervisor")
    g["registrar_objetivo"] = registrar_objetivo_v2
    g["_avisar_cambio_servicio"] = _avisar_cambio_servicio_v2
    g["mostrar_boton_personal_supervisor"] = boton_personal_ampliado
    g["renderizar_centro_supervisor"] = renderizar_centro_supervisor
    g["renderizar_derivacion_monitoreo"] = renderizar_derivacion_monitoreo
