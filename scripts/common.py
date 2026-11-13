"""Utilidades compartidas por los scripts de descarga de datos.

Overpass se consulta con `curl` (subprocess) porque el `ssl` de algunos Python
de macOS (LibreSSL 2.8) falla el handshake TLS con overpass-api.de, mientras
que curl funciona en macOS, Linux y WSL.
"""
import json
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
USER_AGENT = "EAFIT-SI3003-student-project/1.0 (proyecto academico)"

# Caja del Valle de Aburrá (sur, oeste, norte, este) para consultas Overpass.
BBOX = "6.10,-75.70,6.45,-75.40"

OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]


def overpass_to_file(query_body: str, path: Path, timeout: int = 600, retries: int = 3) -> None:
    """Descarga una consulta Overpass en formato XML directamente a un archivo."""
    full = f"[out:xml][timeout:{timeout}];{query_body}"
    last_err = None
    for attempt in range(retries):
        for url in OVERPASS_ENDPOINTS:
            proc = subprocess.run(
                ["curl", "-sS", "-m", str(timeout + 60), "-A", USER_AGENT,
                 "--data-urlencode", f"data={full}", "-o", str(path), url],
                capture_output=True, text=True,
            )
            if proc.returncode == 0 and path.exists() and path.stat().st_size > 1000:
                head = path.read_text(encoding="utf-8", errors="ignore")[:300]
                if "<osm" in head:
                    return
                last_err = head
            else:
                last_err = proc.stderr.strip() or "respuesta vacía"
        time.sleep(10 * (attempt + 1))
    raise RuntimeError(f"Overpass falló tras {retries} intentos: {last_err}")


def overpass(query_body: str, timeout: int = 180, retries: int = 3) -> list:
    """Ejecuta una consulta Overpass y devuelve la lista `elements`."""
    full = f"[out:json][timeout:{timeout}];{query_body}"
    last_err = None
    for attempt in range(retries):
        for url in OVERPASS_ENDPOINTS:
            proc = subprocess.run(
                ["curl", "-sS", "-m", str(timeout + 30), "-A", USER_AGENT,
                 "--data-urlencode", f"data={full}", url],
                capture_output=True, text=True,
            )
            if proc.returncode == 0 and proc.stdout.lstrip().startswith("{"):
                try:
                    return json.loads(proc.stdout)["elements"]
                except (json.JSONDecodeError, KeyError) as exc:
                    last_err = exc
            else:
                last_err = proc.stderr.strip() or proc.stdout[:200]
        time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"Overpass falló tras {retries} intentos: {last_err}")
