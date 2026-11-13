"""Evaluación de la Parte 1: A* vs Dijkstra (UCS) vs BFS sobre pares origen-destino fijos.

Uso (desde la raíz del repo):  python -m eval.search_eval
Salidas: eval/results/search_results.csv y eval/results/search_summary.md

- 10 pares de estaciones con nombre + 10 pares de nodos viales aleatorios (semilla 42).
- Perfiles: carro y transporte público; hora 8 (hora pico); pesos iguales (1/3 cada uno).
- Validación: el costo de nuestro Dijkstra se compara con nx.dijkstra_path_length
  (networkx se usa SOLO para verificar, no para resolver).
"""
import random
from pathlib import Path

import networkx as nx
import pandas as pd

from src.data import loader
from src.data.network import build_profile, nearest
from src.search.algorithms import admissible_k, astar, bfs, dijkstra, edge_weight, normalize_weights
from src.search.planner import places

OUT = Path(__file__).resolve().parent / "results"
HOUR = 8
WEIGHTS = normalize_weights(1, 1, 1)
SEED = 42
STATION_PAIRS = [
    ("Niquía", "La Estrella"), ("Acevedo", "Poblado"), ("San Javier", "Oriente"),
    ("Bello", "Envigado"), ("Estadio", "Itagüí"), ("Santo Domingo", "Aguacatala"),
    ("Floresta", "Ayurá"), ("Alpujarra", "Caribe"), ("La Aurora", "Sabaneta"),
    ("Industriales", "Madera"),
]


def od_pairs():
    pl = places()
    near = nearest()
    pairs = []
    for a, b in STATION_PAIRS:
        if a in pl and b in pl:
            pairs.append((f"{a} -> {b}", near(*pl[a]), near(*pl[b])))
        else:
            print(f"[aviso] par omitido, estación no encontrada: {a} / {b}")
    rng = random.Random(SEED)
    road_nodes = sorted(build_profile("carro", "libre")[1].keys())
    for i in range(10):
        s, g = rng.sample(road_nodes, 2)
        pairs.append((f"aleatorio_{i + 1}", s, g))
    return pairs


def nx_reference(adj, s, g):
    G = nx.DiGraph()
    for u, nbrs in adj.items():
        for v, t, c, e, _ in nbrs:
            w = edge_weight(t, c, e, WEIGHTS)
            if not G.has_edge(u, v) or w < G[u][v]["weight"]:
                G.add_edge(u, v, weight=w)
    return G


def main():
    OUT.mkdir(exist_ok=True)
    per = loader.period(HOUR)
    pairs = od_pairs()
    rows = []
    for profile in ("carro", "transporte"):
        adj, coords = build_profile(profile, per)
        k = admissible_k(adj, coords, WEIGHTS)
        G = nx_reference(adj, None, None)
        print(f"Perfil {profile}: k = {k:.6f} (costo generalizado por metro en línea recta)")
        for name, s, g in pairs:
            ref = nx.dijkstra_path_length(G, s, g, weight="weight")
            for alg, fn in (("A*", lambda: astar(adj, coords, s, g, WEIGHTS, k)),
                            ("Dijkstra", lambda: dijkstra(adj, coords, s, g, WEIGHTS)),
                            ("BFS", lambda: bfs(adj, coords, s, g, WEIGHTS))):
                r = fn()
                rows.append({"perfil": profile, "par": name, "algoritmo": alg,
                             "nodos_expandidos": r["expanded"], "tiempo_ms": round(r["seconds"] * 1000, 1),
                             "costo_generalizado": round(r["cost"], 3),
                             "aristas_en_ruta": len(r["path"]) - 1 if r["path"] else None,
                             "optimo_segun_networkx": abs(r["cost"] - ref) < 1e-6})
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "search_results.csv", index=False)

    summ = (df.groupby(["perfil", "algoritmo"], sort=False)
              .agg(nodos_expandidos_prom=("nodos_expandidos", "mean"),
                   tiempo_ms_prom=("tiempo_ms", "mean"),
                   costo_prom=("costo_generalizado", "mean"),
                   pares_optimos=("optimo_segun_networkx", "sum"),
                   pares=("par", "count"))
              .round(1).reset_index())
    base = summ[summ.algoritmo == "Dijkstra"].set_index("perfil")["nodos_expandidos_prom"]
    summ["reduccion_vs_dijkstra_%"] = summ.apply(
        lambda r: round(100 * (1 - r.nodos_expandidos_prom / base[r.perfil]), 1), axis=1)
    md = ["# Resultados Parte 1: A* vs Dijkstra vs BFS", "",
          f"Hora {HOUR} (periodo `{per}`), pesos (tiempo, costo, emisiones) = (1/3, 1/3, 1/3), "
          f"{len(pairs)} pares O-D (10 estaciones + 10 aleatorios, semilla {SEED}).",
          "Costo generalizado = w_t·min + w_c·miles COP + w_e·100 g CO2e. "
          "`pares_optimos`: pares donde el costo coincide con `nx.dijkstra_path_length` (solo validación).", "",
          summ.to_markdown(index=False), "", "## Detalle por par", "", df.to_markdown(index=False)]
    (OUT / "search_summary.md").write_text("\n".join(md), encoding="utf-8")
    print(summ.to_string(index=False))


if __name__ == "__main__":
    main()
