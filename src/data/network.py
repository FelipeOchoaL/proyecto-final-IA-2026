"""Construcción del grafo de búsqueda multimodal.

osmnx/networkx se usan SOLO para leer el GraphML y extraer el componente fuertemente
conexo. La búsqueda (src/search) trabaja sobre listas de adyacencia propias:

    adj[u] = [(v, tiempo_s, costo_COP, emisiones_kg, modo), ...]

Perfiles (un grafo por modo, porque no se puede "soltar" el carro a mitad de ruta):
  - carro:      red vial dirigida; tiempo = travel_time / factor de velocidad de la hora.
  - bicicleta:  red vial en ambos sentidos a velocidad constante (supuesto).
  - caminata:   red vial en ambos sentidos a velocidad constante (supuesto).
  - transporte: caminata + líneas de Metro/Tranvía/Metrocable/bus (paradas de OSM).
"""
import math
import pickle
from functools import lru_cache

import numpy as np

from src.data import loader

PROFILES = ("carro", "transporte", "bicicleta", "caminata")
RAIL_SPEED_KEY = {"metro": "velocidad_metro", "tranvia": "velocidad_tranvia",
                  "metrocable": "velocidad_metrocable"}


def haversine_m(lat1, lon1, lat2, lon2) -> float:
    r = 6371008.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


@lru_cache(maxsize=1)
def road_base():
    """Nodos {id: (lat, lon)} y aristas [(u, v, length_m, travel_time_s)] del componente
    fuertemente conexo más grande. Se cachea en data/cache/road.pkl (la lectura del
    GraphML tarda ~1 min; el pickle, ~2 s)."""
    cache = loader.CACHE / "road.pkl"
    if cache.exists():
        with open(cache, "rb") as f:
            return pickle.load(f)
    import networkx as nx
    import osmnx as ox

    G = ox.load_graphml(loader.road_graphml_path())
    H = G.subgraph(max(nx.strongly_connected_components(G), key=len))
    coords = {n: (d["y"], d["x"]) for n, d in H.nodes(data=True)}
    best = {}  # multiaristas: se queda la de menor travel_time
    for u, v, d in H.edges(data=True):
        e = (float(d["length"]), float(d["travel_time"]))
        if (u, v) not in best or e[1] < best[(u, v)][1]:
            best[(u, v)] = e
    edges = [(u, v, l, t) for (u, v), (l, t) in best.items()]
    data = {"coords": coords, "edges": edges}
    loader.CACHE.mkdir(parents=True, exist_ok=True)
    with open(cache, "wb") as f:
        pickle.dump(data, f)
    return data


class NearestNode:
    """Nodo vial más cercano a un punto (búsqueda lineal vectorizada; 43k nodos)."""

    def __init__(self, coords: dict):
        self.ids = np.array(list(coords.keys()))
        arr = np.array(list(coords.values()))
        self.lat, self.lon = np.radians(arr[:, 0]), np.radians(arr[:, 1])

    def __call__(self, lat, lon):
        la, lo = math.radians(lat), math.radians(lon)
        # Aproximación equirectangular: suficiente para elegir el más cercano.
        x = (self.lon - lo) * math.cos(la)
        y = self.lat - la
        i = int(np.argmin(x * x + y * y))
        return self.ids[i].item()


@lru_cache(maxsize=1)
def nearest():
    return NearestNode(road_base()["coords"])


def _transit_layer():
    """Nodos de línea ('metro:A:Poblado') y aristas entre paradas consecutivas.

    Devuelve coords de los nodos de línea, aristas en vehículo
    [(u, v, dist_m, modo)] y la línea de cada nodo."""
    stops = loader.load_route_stops().dropna(subset=["name"])
    coords, ride, node_mode = {}, [], {}
    for _, g in stops.sort_values("seq").groupby("route_id"):
        prev = None
        for r in g.itertuples():
            ref = r.ref if isinstance(r.ref, str) else str(r.route_id)
            nid = f"{r.mode}:{ref}:{r.name}"
            coords.setdefault(nid, (r.lat, r.lon))
            node_mode[nid] = r.mode
            if prev is not None and prev != nid:
                (la1, lo1), (la2, lo2) = coords[prev], coords[nid]
                ride.append((prev, nid, haversine_m(la1, lo1, la2, lo2), r.mode))
            prev = nid
    return coords, ride, node_mode


def _wait_s(mode: str, per: str) -> float:
    a = loader.assumptions()
    if mode == "metro":
        headway = a["intervalo_metro_pico"] if per == "hora_pico" else a["intervalo_metro_valle"]
    else:
        headway = a["intervalo_cable_tranvia"]
    return headway * a["espera_promedio"]


@lru_cache(maxsize=12)
def build_profile(profile: str, per: str):
    """Lista de adyacencia y coordenadas para un perfil y periodo del día."""
    if profile not in PROFILES:
        raise ValueError(f"Perfil desconocido: {profile}. Use uno de {PROFILES}")
    a, ef = loader.assumptions(), loader.emission_factors()
    base = road_base()
    coords = dict(base["coords"])
    adj = {n: [] for n in coords}

    if profile == "carro":
        f = loader.speed_factor_for_period(per)
        cpm = a["costo_carro_km"] / 1000.0
        epm = ef["carro_particular"] / 1000.0
        for u, v, l, t in base["edges"]:
            adj[u].append((v, t / f, l * cpm, l * epm, "carro"))
        return adj, coords

    # Bicicleta, caminata y la parte a pie del transporte: red vial en ambos sentidos.
    walk_mode = "bicicleta" if profile == "bicicleta" else "caminata"
    v_ms = a[f"velocidad_{walk_mode}"] / 3.6
    seen = set()
    for u, v, l, _ in base["edges"]:
        for x, y in ((u, v), (v, u)):
            if (x, y) not in seen:
                seen.add((x, y))
                adj[x].append((y, l / v_ms, 0.0, 0.0, walk_mode))
    if profile != "transporte":
        return adj, coords

    t_coords, ride, node_mode = _transit_layer()
    coords.update(t_coords)
    for n in t_coords:
        adj[n] = []
    fare = a["tarifa_metro_civica"]
    bus_kmh = loader.free_flow_speed_kmh() * loader.speed_factor_for_period(per)
    walk_ms = a["velocidad_caminata"] / 3.6
    near = nearest()
    # Acceso/egreso: caminata en línea recta hasta el nodo vial más cercano.
    for n, (la, lo) in t_coords.items():
        r = near(la, lo)
        d = haversine_m(la, lo, *coords[r])
        m = node_mode[n]
        # Subir: caminar + esperar + pagar el pasaje (se cobra una vez por abordaje desde la calle).
        adj[r].append((n, d / walk_ms + _wait_s(m, per), fare, 0.0, "abordaje"))
        adj[n].append((r, d / walk_ms, 0.0, 0.0, "caminata"))
    for u, v, d, m in ride:
        kmh = bus_kmh if m in ("bus", "metroplus") else a[RAIL_SPEED_KEY[m]]
        adj[u].append((v, d / (kmh / 3.6), 0.0, d / 1000.0 * ef[m], m))
    # Transbordos entre líneas en la misma estación (mismo nombre, < 300 m).
    # SUPUESTO: integración tarifaria sin cobro adicional (el reglamento no fija la regla).
    by_name = {}
    for n in t_coords:
        by_name.setdefault(n.split(":", 2)[2], []).append(n)
    for group in by_name.values():
        for x in group:
            for y in group:
                if x.split(":")[:2] != y.split(":")[:2] and \
                        haversine_m(*t_coords[x], *t_coords[y]) < 300:
                    adj[x].append((y, a["tiempo_transbordo"] + _wait_s(node_mode[y], per),
                                   0.0, 0.0, "transbordo"))
    return adj, coords
