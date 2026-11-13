"""Cargador de los datos del proyecto para el equipo de modelado.

Uso desde la raíz del repo:
    from scripts.data_loader import load_road_graph, load_stations, speed_factor
    G = load_road_graph()                      # grafo dirigido (networkx MultiDiGraph)
    stations = load_stations()                 # pandas.DataFrame
    t = edge["travel_time"] / speed_factor(8)  # segundos a las 8 a. m.

El grafo se guarda comprimido (road_drive.graphml.gz, ~10 MB) para no depender de
Overpass durante la demo; aquí se descomprime una sola vez a un caché local.
"""
import gzip
import shutil
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"


def load_road_graph():
    """Devuelve el grafo vial (carro). Requiere osmnx."""
    import osmnx as ox

    gz = PROCESSED / "road_drive.graphml.gz"
    plain = PROCESSED / "road_drive.graphml"
    if not plain.exists():
        if not gz.exists():
            raise FileNotFoundError("Falta road_drive.graphml(.gz): ejecute scripts/02_osm_road_network.py")
        with gzip.open(gz, "rb") as src, open(plain, "wb") as dst:
            shutil.copyfileobj(src, dst)
    return ox.load_graphml(plain)


def load_stations() -> pd.DataFrame:
    """Estaciones únicas por modo: mode, name, lat, lon, lines."""
    return pd.read_csv(PROCESSED / "transit_stations.csv")


def load_route_stops() -> pd.DataFrame:
    """Paradas ordenadas de cada ruta/sentido."""
    return pd.read_csv(PROCESSED / "transit_route_stops.csv")


def load_transfers() -> pd.DataFrame:
    """Transbordos entre modos con la distancia (m) entre los puntos de OSM."""
    return pd.read_csv(PROCESSED / "intermodal_transfers.csv")


def load_emission_factors() -> pd.DataFrame:
    return pd.read_csv(PROCESSED / "emission_factors.csv")


def speed_factor(hour: int) -> float:
    """Factor multiplicativo de velocidad para una hora del día (0-23).

    Tiempo ajustado = travel_time / speed_factor(hour).
    """
    hours = pd.read_csv(PROCESSED / "speed_factors_hours.csv").set_index("hora")["periodo"]
    factors = pd.read_csv(PROCESSED / "speed_factors.csv").set_index("periodo")["factor_velocidad"]
    return float(factors[hours[int(hour)]])
