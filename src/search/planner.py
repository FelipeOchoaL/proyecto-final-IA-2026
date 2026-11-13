"""Interfaz de alto nivel: planear una ruta entre dos lugares con nuestro A*."""
import unicodedata
from functools import lru_cache

from src.data import loader
from src.data.network import PROFILES, build_profile, nearest
from src.search.algorithms import admissible_k, astar, normalize_weights

MODE_LABELS = {"carro": "Carro", "transporte": "Transporte público (Metro/Tranvía/Cable/bus) + caminata",
               "bicicleta": "Bicicleta", "caminata": "Caminata"}
TRANSIT_MODES = {"metro", "tranvia", "metrocable", "bus", "metroplus"}


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return " ".join(s.replace("estacion", "").split())


@lru_cache(maxsize=1)
def places() -> dict:
    """Lugares seleccionables: estaciones únicas por nombre -> (lat, lon)."""
    st = loader.load_stations()
    out = {}
    for r in st.itertuples():
        out.setdefault(r.name, (r.lat, r.lon))
    return dict(sorted(out.items()))


def resolve_place(name: str):
    """Nombre de estación (tolerante a tildes/mayúsculas) -> (nombre, lat, lon)."""
    if not name or not str(name).strip():
        raise ValueError("Lugar vacío.")
    target = _norm(name)
    idx = {_norm(n): n for n in places()}
    if target in idx:
        n = idx[target]
    else:
        matches = [orig for k, orig in idx.items() if target in k or k in target]
        if len(matches) != 1:
            raise ValueError(f"No reconozco el lugar '{name}'. Use una estación, p. ej.: "
                             + ", ".join(list(places())[:8]) + "...")
        n = matches[0]
    return (n, *places()[n])


@lru_cache(maxsize=64)
def _k_cached(profile, per, weights):
    adj, coords = build_profile(profile, per)
    return admissible_k(adj, coords, weights)


def plan_route(origin: str, destination: str, mode: str = "transporte", hour: int = 8,
               weights=(1.0, 0.0, 0.0)) -> dict:
    """Ruta óptima (costo generalizado) con A* para un modo y hora.

    weights = (tiempo, costo, emisiones), se normalizan para sumar 1."""
    if mode not in PROFILES:
        raise ValueError(f"Modo '{mode}' no válido. Opciones: {', '.join(PROFILES)}")
    if not 0 <= int(hour) <= 23:
        raise ValueError("La hora debe estar entre 0 y 23.")
    w = normalize_weights(*weights)
    o_name, o_lat, o_lon = resolve_place(origin)
    d_name, d_lat, d_lon = resolve_place(destination)
    per = loader.period(hour)
    adj, coords = build_profile(mode, per)
    s, g = nearest()(o_lat, o_lon), nearest()(d_lat, d_lon)
    k = _k_cached(mode, per, w)
    res = astar(adj, coords, s, g, w, k=k)
    if res["path"] is None:
        raise RuntimeError(f"No existe ruta en modo {mode} entre {o_name} y {d_name}.")
    t = sum(e[0] for e in res["edges"])
    c = sum(e[1] for e in res["edges"])
    em = sum(e[2] for e in res["edges"])
    # Tramos consecutivos del mismo modo (para explicar la ruta y colorear el mapa).
    legs = []
    for n_from, n_to, (et, _, _, m) in zip(res["path"], res["path"][1:], res["edges"]):
        m = "caminata" if m == "abordaje" else m
        if m == "transbordo":
            continue
        line = n_to.split(":")[1] if m in TRANSIT_MODES else None
        if legs and legs[-1]["modo"] == m and legs[-1]["linea"] == line:
            legs[-1]["tiempo_s"] += et
            legs[-1]["hasta"] = n_to
        else:
            legs.append({"modo": m, "linea": line, "desde": n_from, "hasta": n_to, "tiempo_s": et})
    for leg in legs:
        for key in ("desde", "hasta"):
            n = leg[key]
            leg[key] = n.split(":", 2)[2] if isinstance(n, str) else None
    return {
        "origen": o_name, "destino": d_name, "modo": mode, "hora": int(hour), "periodo": per,
        "pesos": {"tiempo": round(w[0], 3), "costo": round(w[1], 3), "emisiones": round(w[2], 3)},
        "tiempo_min": round(t / 60, 1), "costo_cop": round(c), "emisiones_kg": round(em, 3),
        "nodos_expandidos": res["expanded"],
        "tramos": [{"modo": l["modo"], "linea": l["linea"], "desde": l["desde"], "hasta": l["hasta"],
                    "tiempo_min": round(l["tiempo_s"] / 60, 1)} for l in legs if l["tiempo_s"] > 0],
        "coords": [coords[n] for n in res["path"]],
        "segment_modes": [e[3] for e in res["edges"]],
    }


def compare_modes(origin, destination, hour=8, weights=(1.0, 0.0, 0.0)) -> list:
    """Corre plan_route para los 4 modos; los errores por modo se reportan sin abortar."""
    out = []
    for m in PROFILES:
        try:
            out.append(plan_route(origin, destination, m, hour, weights))
        except Exception as e:  # noqa: BLE001 - se informa al usuario/agente
            out.append({"modo": m, "error": str(e)})
    return out
