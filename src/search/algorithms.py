"""A*, Dijkstra (UCS) y BFS implementados a mano sobre listas de adyacencia.

Costo multiobjetivo de una arista (escalar, "costo generalizado"):

    w(e) = w_t * tiempo_min + w_c * costo_miles_COP + w_e * emisiones_100g

Unidades de normalización (decisión del equipo): 1 minuto ~ 1.000 COP ~ 100 g CO2e.
Los pesos w_t, w_c, w_e los elige el usuario (se normalizan para sumar 1).

Heurística (ver admissible_k): h(n) = k * haversine(n, meta), donde
    k = min sobre todas las aristas (u,v) con haversine(u,v) > 0 de w(u,v) / haversine(u,v).
Es CONSISTENTE (y por tanto admisible): para toda arista,
    h(u) = k*d(u,g) <= k*(d(u,v) + d(v,g)) <= w(u,v) + h(v)
por la desigualdad triangular de la distancia haversine y la definición de k.
Aristas con haversine = 0 (p. ej. transbordos) tienen w >= 0 = k*0 y no rompen la cota.
"""
import heapq
import time
from collections import deque

from src.data.network import haversine_m


def edge_weight(t_s, c_cop, e_kg, weights):
    wt, wc, we = weights
    return wt * t_s / 60.0 + wc * c_cop / 1000.0 + we * e_kg * 10.0


def normalize_weights(wt, wc, we):
    s = wt + wc + we
    if s <= 0:
        raise ValueError("Al menos un peso debe ser positivo.")
    return (wt / s, wc / s, we / s)


def admissible_k(adj, coords, weights):
    """Menor costo generalizado por metro en línea recta entre todas las aristas."""
    k = float("inf")
    for u, nbrs in adj.items():
        lu = coords[u]
        for v, t, c, e, _ in nbrs:
            d = haversine_m(*lu, *coords[v])
            if d > 1.0:  # se ignoran aristas casi nulas (redondeo de coordenadas)
                k = min(k, edge_weight(t, c, e, weights) / d)
    return 0.0 if k == float("inf") else k


def _reconstruct(parent, goal):
    path = [goal]
    while parent[path[-1]] is not None:
        path.append(parent[path[-1]][0])
    path.reverse()
    return path


def _edges_along(parent, path):
    """Atributos (t, c, e, modo) de cada arista del camino."""
    return [parent[n][1] for n in path[1:]]


def astar(adj, coords, start, goal, weights, k=0.0):
    """A* con conjunto cerrado. k=0 lo convierte en Dijkstra/UCS.

    Devuelve dict con path, edges, cost, expanded, seconds (o path=None si no hay ruta)."""
    t0 = time.perf_counter()
    gl = coords[goal]

    def h(n):
        return k * haversine_m(*coords[n], *gl) if k else 0.0

    g = {start: 0.0}
    parent = {start: None}
    closed = set()
    counter = 0  # desempate estable en el heap
    frontier = [(h(start), counter, start)]
    expanded = 0
    while frontier:
        _, _, u = heapq.heappop(frontier)
        if u in closed:
            continue  # entrada obsoleta (borrado perezoso)
        closed.add(u)
        expanded += 1
        if u == goal:
            path = _reconstruct(parent, goal)
            return {"path": path, "edges": _edges_along(parent, path), "cost": g[u],
                    "expanded": expanded, "seconds": time.perf_counter() - t0}
        for v, t, c, e, mode in adj[u]:
            if v in closed:
                continue
            ng = g[u] + edge_weight(t, c, e, weights)
            if ng < g.get(v, float("inf")):
                g[v] = ng
                parent[v] = (u, (t, c, e, mode))
                counter += 1
                heapq.heappush(frontier, (ng + h(v), counter, v))
    return {"path": None, "edges": [], "cost": float("inf"), "expanded": expanded,
            "seconds": time.perf_counter() - t0}


def dijkstra(adj, coords, start, goal, weights):
    """Línea base: UCS = A* con heurística nula."""
    return astar(adj, coords, start, goal, weights, k=0.0)


def bfs(adj, coords, start, goal, weights):
    """Línea base no informada: minimiza el NÚMERO de aristas, ignora los costos.
    El costo generalizado del camino hallado se calcula después para comparar."""
    t0 = time.perf_counter()
    parent = {start: None}
    q = deque([start])
    expanded = 0
    while q:
        u = q.popleft()
        expanded += 1
        if u == goal:
            path = _reconstruct(parent, goal)
            edges = _edges_along(parent, path)
            cost = sum(edge_weight(t, c, e, weights) for t, c, e, _ in edges)
            return {"path": path, "edges": edges, "cost": cost, "expanded": expanded,
                    "seconds": time.perf_counter() - t0}
        for v, t, c, e, mode in adj[u]:
            if v not in parent:
                parent[v] = (u, (t, c, e, mode))
                q.append(v)
    return {"path": None, "edges": [], "cost": float("inf"), "expanded": expanded,
            "seconds": time.perf_counter() - t0}
