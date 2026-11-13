"""Calibra factores de velocidad por periodo del día para el grafo vial (plan B de tráfico).

Problema: el grafo trae `travel_time` en condiciones libres de tráfico (velocidades por
tipo de vía de OSM). No existe una fuente abierta de tráfico en tiempo real, así que se
escalan los tiempos con un factor multiplicativo por periodo.

Método (reproducible, semilla fija):
  1. Se muestrean pares origen-destino aleatorios (2-15 km en línea recta) en el
     componente fuertemente conexo del grafo.
  2. Se calcula la velocidad media de las rutas más rápidas en el grafo (S_libre).
  3. factor = V_objetivo / S_libre, con V_objetivo tomada de TomTom Traffic Index 2025
     para Medellín (vía prensa): 20,7 km/h promedio del día y 15,9 km/h en hora pico.

Limitaciones: V_objetivo es un promedio de toda la ciudad, calculado por TomTom con su
propia metodología; el factor es una aproximación a nivel de red, no por calle.
Salidas: data/processed/speed_factors.csv y data/processed/speed_factors_hours.csv
Uso: python scripts/03_calibrate_speed_factors.py
"""
import csv
import random

import networkx as nx
import osmnx as ox

from common import PROCESSED

SEED = 42
N_PAIRS = 300
MIN_KM, MAX_KM = 2.0, 15.0

# Velocidades objetivo (km/h): TomTom Traffic Index 2025, Medellín (reportado en prensa).
V_DIA = 20.7
V_PICO = 15.9

# Asignación hora -> periodo: SUPUESTO del equipo (picos típicos 6-9 y 17-20).
HORAS = {h: "hora_pico" for h in (6, 7, 8, 17, 18, 19)}
HORAS.update({h: "libre" for h in (0, 1, 2, 3, 4, 22, 23)})
for h in range(24):
    HORAS.setdefault(h, "promedio_dia")


def main():
    G = ox.load_graphml(PROCESSED / "road_drive.graphml")
    H = G.subgraph(max(nx.strongly_connected_components(G), key=len)).copy()
    nodes = list(H.nodes)
    rng = random.Random(SEED)

    tot_len = tot_time = 0.0
    done = 0
    while done < N_PAIRS:
        a, b = rng.sample(nodes, 2)
        km = ox.distance.great_circle(
            H.nodes[a]["y"], H.nodes[a]["x"], H.nodes[b]["y"], H.nodes[b]["x"]) / 1000
        if not MIN_KM <= km <= MAX_KM:
            continue
        path = nx.shortest_path(H, a, b, weight="travel_time")
        for u, v in zip(path[:-1], path[1:]):
            e = min(H[u][v].values(), key=lambda d: d["travel_time"])
            tot_len += e["length"]
            tot_time += e["travel_time"]
        done += 1

    s_libre = (tot_len / 1000) / (tot_time / 3600)
    f_dia = V_DIA / s_libre
    f_pico = V_PICO / s_libre
    print(f"Velocidad media libre del grafo: {s_libre:.1f} km/h sobre {N_PAIRS} pares")
    print(f"Factor promedio_dia={f_dia:.3f}  hora_pico={f_pico:.3f}")

    rows = [
        ("libre", 1.0, round(s_libre, 1), "Velocidades del grafo sin congestión (OSM por tipo de vía)"),
        ("promedio_dia", round(f_dia, 3), V_DIA, "TomTom Traffic Index 2025 Medellín, promedio del día"),
        ("hora_pico", round(f_pico, 3), V_PICO, "TomTom Traffic Index 2025 Medellín, hora pico"),
    ]
    with open(PROCESSED / "speed_factors.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["periodo", "factor_velocidad", "velocidad_media_km_h", "fuente"])
        w.writerows(rows)
    with open(PROCESSED / "speed_factors_hours.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["hora", "periodo"])
        w.writerows(sorted(HORAS.items()))
    print("Guardado speed_factors.csv y speed_factors_hours.csv")
    print("Uso: tiempo_ajustado = travel_time / factor_velocidad")


if __name__ == "__main__":
    main()
