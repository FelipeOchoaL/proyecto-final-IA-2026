"""Dashboard del copiloto de movilidad (Streamlit).

Ejecutar desde la raíz del repo:  streamlit run app/app.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import folium  # noqa: E402
import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402
from streamlit_folium import st_folium  # noqa: E402

from src.agent.agent import DISCLAIMER, run_agent  # noqa: E402
from src.data import loader  # noqa: E402
from src.data.network import PROFILES, build_profile  # noqa: E402
from src.search.planner import MODE_LABELS, compare_modes, places  # noqa: E402

st.set_page_config(page_title="Copiloto de movilidad – Valle de Aburrá", layout="wide")

SHORT_LABELS = {"carro": "Carro", "transporte": "Transporte público", "bicicleta": "Bicicleta",
                "caminata": "Caminata"}
MODE_COLORS = {"carro": "#d62728", "transporte": "#1f77b4", "bicicleta": "#2ca02c", "caminata": "#9467bd"}


@st.cache_resource(show_spinner="Cargando la red vial y de transporte (la primera vez tarda ~1 min)...")
def warm_up():
    """Precarga los grafos de los 3 periodos para que las consultas respondan rápido."""
    for per in ("libre", "promedio_dia", "hora_pico"):
        for p in PROFILES:
            build_profile(p, per)
    return True


@st.cache_data
def transit_geojson():
    path = loader.PROCESSED / "transit_routes.geojson"
    return path.read_text(encoding="utf-8") if path.exists() else None


def build_map(routes):
    m = folium.Map(location=[6.245, -75.575], zoom_start=12, tiles="OpenStreetMap")
    gj = transit_geojson()
    if gj:
        folium.GeoJson(gj, name="Red de transporte masivo (OSM)",
                       style_function=lambda f: {"color": "#888888", "weight": 2, "opacity": 0.5}).add_to(m)
    bounds = []
    for r in routes:
        if "coords" not in r:
            continue
        folium.PolyLine(r["coords"], color=MODE_COLORS.get(r["modo"], "black"), weight=5, opacity=0.8,
                        tooltip=f"{MODE_LABELS[r['modo']]}: {r['tiempo_min']} min, ${r['costo_cop']:,}, "
                                f"{r['emisiones_kg']} kg CO2e").add_to(m)
        bounds += r["coords"]
    if routes and "coords" in routes[0]:
        folium.Marker(routes[0]["coords"][0], tooltip=f"Origen: {routes[0]['origen']}",
                      icon=folium.Icon(color="green")).add_to(m)
        folium.Marker(routes[0]["coords"][-1], tooltip=f"Destino: {routes[0]['destino']}",
                      icon=folium.Icon(color="red")).add_to(m)
    if bounds:
        m.fit_bounds([[min(p[0] for p in bounds), min(p[1] for p in bounds)],
                      [max(p[0] for p in bounds), max(p[1] for p in bounds)]])
    folium.LayerControl().add_to(m)
    return m


def comparison_table(routes):
    rows = []
    for r in routes:
        if "error" in r:
            rows.append({"Modo": SHORT_LABELS.get(r["modo"], r["modo"]), "Tiempo (min)": None,
                         "Costo (COP)": None, "Emisiones (kg CO2e)": None, "Tramos": f"Error: {r['error']}"})
            continue
        tramos = " → ".join(f"{t['modo']}{' ' + t['linea'] if t['linea'] else ''} ({t['tiempo_min']} min)"
                            for t in r["tramos"])
        rows.append({"Modo": SHORT_LABELS[r["modo"]], "Tiempo (min)": r["tiempo_min"],
                     "Costo (COP)": r["costo_cop"], "Emisiones (kg CO2e)": r["emisiones_kg"],
                     "Nodos expandidos (A*)": r["nodos_expandidos"], "Tramos": tramos})
    return pd.DataFrame(rows)


# ---------------- Barra lateral: parámetros ----------------
st.sidebar.header("Parámetros del viaje")
names = list(places())
origin = st.sidebar.selectbox("Origen (estación)", names, index=names.index("Niquía") if "Niquía" in names else 0)
dest = st.sidebar.selectbox("Destino (estación)", names, index=names.index("Poblado") if "Poblado" in names else 1)
hour = st.sidebar.slider("Hora de salida", 0, 23, 7)
st.sidebar.caption(f"Escenario de tráfico: **{loader.period(hour)}** (tiempos simulados por hora)")
st.sidebar.subheader("Preferencias (pesos)")
wt = st.sidebar.slider("Tiempo", 0.0, 1.0, 0.6, 0.05)
wc = st.sidebar.slider("Costo", 0.0, 1.0, 0.2, 0.05)
we = st.sidebar.slider("Emisiones", 0.0, 1.0, 0.2, 0.05)
run = st.sidebar.button("Calcular rutas", type="primary", width="stretch")

st.title("Copiloto de movilidad – Valle de Aburrá")
st.caption("Rutas con A\\* propio (tiempo, costo, emisiones) + asistente con RAG. " + DISCLAIMER)

warm_up()

if "routes" not in st.session_state:
    st.session_state.routes = []
    st.session_state.routes_label = ""
if run:
    if origin == dest:
        st.sidebar.error("El origen y el destino deben ser distintos.")
    elif wt + wc + we == 0:
        st.sidebar.error("Al menos un peso debe ser mayor que 0.")
    else:
        with st.spinner("Buscando rutas con A*..."):
            st.session_state.routes = compare_modes(origin, dest, hour, (wt, wc, we))
            st.session_state.routes_label = f"{origin} → {dest}, {hour}:00, pesos t={wt} c={wc} e={we}"

# ---------------- Visualizaciones ----------------
col_map, col_tab = st.columns([3, 2])
routes = st.session_state.routes
with col_map:
    st.subheader("Mapa de rutas alternativas")
    if st.session_state.routes_label:
        st.caption(st.session_state.routes_label)
    st_folium(build_map(routes), height=480, use_container_width=True, returned_objects=[])
with col_tab:
    st.subheader("Comparación por modo")
    if routes:
        st.dataframe(comparison_table(routes), hide_index=True, width="stretch")
        st.caption("Costo: pasaje Cívica \\$3.820 o carro \\$406/km (gasolina CREG 371/2026 ÷ 40 km/gal supuesto). "
                   "Emisiones: factores UK 2024 por pasajero-km (aproximados). Velocidades de Metro/Cable/Tranvía "
                   "no oficiales; bici 15 km/h y caminata 5 km/h supuestas. Ver data/processed/supuestos.csv.")
    else:
        st.info("Elija origen, destino, hora y pesos en la barra lateral y presione **Calcular rutas**, "
                "o pregúntele al asistente.")

# ---------------- Chat con el agente ----------------
st.subheader("Asistente (agente LLM con RAG)")
if "chat" not in st.session_state:
    st.session_state.chat = []
for msg in st.session_state.chat:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"].replace("$", "\\$"))
        if msg.get("trace"):
            with st.expander("Herramientas usadas"):
                st.json(msg["trace"])

question = st.chat_input("Ej.: ¿Me conviene ir en carro de Niquía a Poblado a las 7 a. m. si mi placa termina en 6 y es jueves?")
if question:
    with st.chat_message("user"):
        st.markdown(question)
    defaults = {"origen": origin, "destino": dest, "hora": hour,
                "peso_tiempo": wt, "peso_costo": wc, "peso_emisiones": we}
    history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.chat[-6:]]
    with st.chat_message("assistant"):
        with st.spinner("Pensando..."):
            try:
                res = run_agent(question, history=history, defaults=defaults)
            except Exception as e:  # noqa: BLE001 - la interfaz nunca debe mostrar un traceback
                res = {"answer": f"Ocurrió un error inesperado en el asistente: {e}", "trace": [], "routes": []}
        st.markdown(res["answer"].replace("$", "\\$"))
        if res["trace"]:
            with st.expander("Herramientas usadas"):
                st.json(res["trace"])
    st.session_state.chat += [{"role": "user", "content": question},
                              {"role": "assistant", "content": res["answer"], "trace": res["trace"]}]
    if res.get("routes"):
        # Las rutas calculadas por el agente se muestran en el mapa y la tabla.
        st.session_state.routes = res["routes"]
        st.session_state.routes_label = "Rutas calculadas por el asistente"
        st.rerun()
