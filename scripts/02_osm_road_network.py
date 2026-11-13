"""Descarga la red vial (carro) del núcleo del Valle de Aburrá y la prepara para A*.

Fuente: OpenStreetMap (Overpass API), licencia ODbL, © colaboradores de OSM.
Salidas:
  raw/osm_road_drive.osm               XML crudo de Overpass
  processed/road_drive.graphml         grafo dirigido (OSMnx) con speed_kph y travel_time (s)
  processed/road_drive_summary.json    nodos, aristas, km totales y municipios

Uso: python scripts/02_osm_road_network.py
Cargar luego con: osmnx.load_graphml("data/processed/road_drive.graphml")

Nota: OSMnx usa `requests`, que en algunos Python de macOS falla el TLS con
overpass-api.de. Por eso el XML se baja con curl y el grafo se construye con
osmnx.graph_from_xml (Nominatim sí funciona desde Python).
"""
import json

import osmnx as ox

from common import PROCESSED, RAW, USER_AGENT, overpass_to_file

MUNICIPIOS = [
    "Medellín", "Bello", "Itagüí", "Envigado", "Sabaneta", "La Estrella",
]

# Mismo criterio que osmnx para network_type="drive".
HIGHWAY_EXCLUDE = (
    "footway|bridleway|bus_guideway|corridor|cycleway|elevator|escalator|path|"
    "pedestrian|steps|abandoned|construction|no|planned|platform|proposed|raceway|razed"
)
SERVICE_EXCLUDE = "alley|driveway|emergency_access|parking|parking_aisle|private"


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    ox.settings.http_user_agent = USER_AGENT
    ox.settings.cache_folder = str(RAW / "osmnx_cache")  # evita crear ./cache en la raíz

    print("Geocodificando municipios (Nominatim)...")
    area_ids = []
    for muni in MUNICIPIOS:
        gdf = ox.geocode_to_gdf(f"{muni}, Antioquia, Colombia")
        row = gdf.iloc[0]
        if row["osm_type"] != "relation":
            raise RuntimeError(f"{muni}: se esperaba una relación OSM, llegó {row['osm_type']}")
        area_ids.append(int(row["osm_id"]))
        print(f"  {muni}: relación {row['osm_id']}")

    areas = "".join(f"area({3600000000 + i});" for i in area_ids)
    query = (
        f"({areas})->.a;"
        f'way["highway"]["area"!~"yes"]["highway"!~"{HIGHWAY_EXCLUDE}"]'
        f'["motor_vehicle"!~"no"]["motorcar"!~"no"]["service"!~"{SERVICE_EXCLUDE}"](area.a);'
        "(._;>;);out;"
    )
    osm_path = RAW / "osm_road_drive.osm"
    print("Descargando red vial desde Overpass (puede tardar varios minutos)...")
    overpass_to_file(query, osm_path)
    print(f"  XML: {osm_path.stat().st_size / 1e6:.1f} MB")

    print("Construyendo grafo...")
    G = ox.graph_from_xml(osm_path, bidirectional=False, simplify=True, retain_all=False)
    G = ox.add_edge_speeds(G, fallback=30)  # km/h; imputa por tipo de vía
    G = ox.add_edge_travel_times(G)         # segundos
    ox.save_graphml(G, PROCESSED / "road_drive.graphml")

    total_km = sum(d.get("length", 0) for _, _, d in G.edges(data=True)) / 1000
    summary = {
        "municipios": MUNICIPIOS,
        "nodos": G.number_of_nodes(),
        "aristas": G.number_of_edges(),
        "longitud_total_km": round(total_km, 1),
        "fuente": "OpenStreetMap vía Overpass API (ODbL)",
    }
    (PROCESSED / "road_drive_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(summary)


if __name__ == "__main__":
    main()
