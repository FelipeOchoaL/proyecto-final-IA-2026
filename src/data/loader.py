"""Lectura de los archivos de data/processed (rutas relativas a la raíz del repo)."""
import gzip
import shutil
from functools import lru_cache
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
CACHE = ROOT / "data" / "cache"


def road_graphml_path() -> Path:
    """Descomprime road_drive.graphml.gz a data/cache la primera vez."""
    gz = PROCESSED / "road_drive.graphml.gz"
    plain = CACHE / "road_drive.graphml"
    if not plain.exists():
        if not gz.exists():
            raise FileNotFoundError(f"Falta {gz}. Vea data/FUENTES.md para regenerarlo.")
        CACHE.mkdir(parents=True, exist_ok=True)
        with gzip.open(gz, "rb") as src, open(plain, "wb") as dst:
            shutil.copyfileobj(src, dst)
    return plain


def load_stations() -> pd.DataFrame:
    return pd.read_csv(PROCESSED / "transit_stations.csv")


def load_route_stops() -> pd.DataFrame:
    return pd.read_csv(PROCESSED / "transit_route_stops.csv")


@lru_cache(maxsize=1)
def emission_factors() -> dict:
    """modo -> kgCO2e por pasajero-km."""
    df = pd.read_csv(PROCESSED / "emission_factors.csv")
    return dict(zip(df["modo"], df["factor"]))


@lru_cache(maxsize=1)
def assumptions() -> dict:
    """parametro -> valor (numérico cuando se puede) desde supuestos.csv."""
    df = pd.read_csv(PROCESSED / "supuestos.csv")
    out = {}
    for p, v in zip(df["parametro"], df["valor"]):
        try:
            out[p] = float(v)
        except ValueError:
            out[p] = v
    return out


@lru_cache(maxsize=1)
def _speed_tables():
    hours = pd.read_csv(PROCESSED / "speed_factors_hours.csv").set_index("hora")["periodo"]
    factors = pd.read_csv(PROCESSED / "speed_factors.csv").set_index("periodo")
    return hours.to_dict(), factors


def period(hour: int) -> str:
    """libre / promedio_dia / hora_pico (tiempos SIMULADOS por hora, plan B del enunciado)."""
    return _speed_tables()[0][int(hour) % 24]


def speed_factor_for_period(p: str) -> float:
    return float(_speed_tables()[1].loc[p, "factor_velocidad"])


def free_flow_speed_kmh() -> float:
    """Velocidad media del grafo sin congestión (fila 'libre' de speed_factors.csv)."""
    return float(_speed_tables()[1].loc["libre", "velocidad_media_km_h"])
