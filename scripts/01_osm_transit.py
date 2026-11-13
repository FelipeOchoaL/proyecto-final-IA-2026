"""Descarga el transporte público del Valle de Aburrá desde OpenStreetMap.

Fuente: OpenStreetMap (Overpass API), licencia ODbL, © colaboradores de OSM.
Salidas (data/raw y data/processed):
  raw/osm_transit_raw.json          respuesta cruda de Overpass (para auditoría)
  processed/transit_routes.csv      una fila por ruta/sentido (relación OSM)
  processed/transit_route_stops.csv paradas de cada ruta en orden de recorrido
  processed/transit_stations.csv    estaciones únicas por modo (Metro/Tranvía/Cable)
  processed/transit_routes.geojson  trazado de cada ruta (para dibujar en el mapa)

Uso: python scripts/01_osm_transit.py
"""
import csv
import json
from collections import defaultdict

from common import BBOX, PROCESSED, RAW, overpass

ROUTE_REGEX = "subway|tram|light_rail|train|funicular|trolleybus|bus|aerialway"


def normalize_mode(tags: dict) -> str:
    route = tags.get("route", "")
    network = (tags.get("network") or "").lower()
    if route == "subway":
        return "metro"
    if route == "tram":
        return "tranvia"
    if route == "aerialway":
        return "metrocable"
    if route in ("train", "light_rail"):
        return "tren"
    if route == "bus":
        return "metroplus" if "metroplus" in network else "bus"
    return route


def clean_station_name(name: str) -> str:
    """'Estación del Metro Poblado' -> 'Poblado' (OSM usa ambas variantes)."""
    for prefix in ("Estación del Metro ", "Estación Metro ", "Estación "):
        if name.startswith(prefix):
            return name[len(prefix):].strip()
    return name.strip()


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)

    print("Descargando relaciones de ruta y sus miembros desde Overpass...")
    elements = overpass(
        f'relation["route"~"{ROUTE_REGEX}"]({BBOX});out body;>;out geom;',
        timeout=240,
    )
    (RAW / "osm_transit_raw.json").write_text(
        json.dumps(elements, ensure_ascii=False), encoding="utf-8"
    )

    relations = [e for e in elements if e["type"] == "relation"]
    nodes = {e["id"]: e for e in elements if e["type"] == "node"}
    ways = {e["id"]: e for e in elements if e["type"] == "way"}
    print(f"  {len(relations)} relaciones, {len(nodes)} nodos, {len(ways)} vías")

    # En OSM las paradas del tranvía están modeladas como relaciones stop_area
    # (miembros 'platform' de tipo relation), no como nodos: se piden aparte.
    area_ids = sorted({
        m["ref"] for r in relations if r["tags"].get("route") == "tram"
        for m in r.get("members", []) if m["type"] == "relation"
    })
    stop_areas = {}
    if area_ids:
        body = "(" + "".join(f"relation({i});" for i in area_ids) + ");out center tags;"
        for e in overpass(body):
            if "center" in e:
                stop_areas[e["id"]] = e

    routes_rows, stops_rows, features = [], [], []
    stations = {}  # (modo, nombre) -> fila
    stop_roles = ("stop", "stop_entry_only", "stop_exit_only", "platform")

    for rel in relations:
        tags = rel.get("tags", {})
        mode = normalize_mode(tags)
        rid = rel["id"]
        routes_rows.append({
            "route_id": rid,
            "mode": mode,
            "ref": tags.get("ref", ""),
            "name": tags.get("name", ""),
            "from": tags.get("from", ""),
            "to": tags.get("to", ""),
            "network": tags.get("network", ""),
            "operator": tags.get("operator", ""),
            "colour": tags.get("colour", ""),
        })

        # Terminales sin nombre en OSM: se infieren de from/to (o del "A -> B").
        first_name, last_name = tags.get("from", ""), tags.get("to", "")
        if not (first_name and last_name):
            parts = (tags.get("name", "").split(": ")[-1]).replace("→", "->").split("->")
            if len(parts) == 2:
                first_name, last_name = parts[0].strip(), parts[1].strip()

        stop_members = []  # (rol, id, nombre, lat, lon)
        for m in rel.get("members", []):
            if m["type"] == "node" and m.get("role") in stop_roles:
                node = nodes.get(m["ref"])
                if node:
                    stop_members.append((m["role"], node["id"],
                                         node.get("tags", {}).get("name", ""),
                                         node["lat"], node["lon"]))
            elif m["type"] == "relation" and m.get("role") == "platform" and m["ref"] in stop_areas:
                area = stop_areas[m["ref"]]
                stop_members.append((m["role"], area["id"], area["tags"].get("name", ""),
                                     area["center"]["lat"], area["center"]["lon"]))

        seq = 0
        line_coords = []
        for role, node_id, raw_name, lat, lon in stop_members:
            seq += 1
            name = clean_station_name(raw_name)
            if not name:
                name = first_name if seq == 1 else last_name if seq == len(stop_members) else ""
            stops_rows.append({
                "route_id": rid, "mode": mode, "ref": tags.get("ref", ""),
                "seq": seq, "node_id": node_id, "name": name,
                "role": role, "lat": lat, "lon": lon,
            })
            if mode in ("metro", "tranvia", "metrocable", "metroplus") and name:
                st = stations.setdefault((mode, name), {
                    "mode": mode, "name": name, "lat": lat, "lon": lon, "lines": set(),
                })
                st["lines"].add(tags.get("ref", ""))

        for m in rel.get("members", []):
            if m["type"] == "way" and m["ref"] in ways:
                geom = ways[m["ref"]].get("geometry") or []
                if geom:
                    line_coords.append([[p["lon"], p["lat"]] for p in geom])

        if line_coords and mode != "bus":
            features.append({
                "type": "Feature",
                "properties": {"route_id": rid, "mode": mode, "ref": tags.get("ref", ""),
                               "name": tags.get("name", "")},
                "geometry": {"type": "MultiLineString", "coordinates": line_coords},
            })

    def write_csv(path, rows, fields):
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)

    write_csv(PROCESSED / "transit_routes.csv", routes_rows,
              ["route_id", "mode", "ref", "name", "from", "to", "network", "operator", "colour"])
    write_csv(PROCESSED / "transit_route_stops.csv", stops_rows,
              ["route_id", "mode", "ref", "seq", "node_id", "name", "role", "lat", "lon"])
    station_rows = [
        {**{k: v for k, v in s.items() if k != "lines"}, "lines": "|".join(sorted(s["lines"]))}
        for s in sorted(stations.values(), key=lambda s: (s["mode"], s["name"]))
    ]
    write_csv(PROCESSED / "transit_stations.csv", station_rows,
              ["mode", "name", "lat", "lon", "lines"])
    (PROCESSED / "transit_routes.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False),
        encoding="utf-8",
    )

    by_mode = defaultdict(int)
    for r in routes_rows:
        by_mode[r["mode"]] += 1
    print("Rutas por modo:", dict(by_mode))
    print(f"Paradas (ruta x parada): {len(stops_rows)} | estaciones únicas: {len(station_rows)}")


if __name__ == "__main__":
    main()
