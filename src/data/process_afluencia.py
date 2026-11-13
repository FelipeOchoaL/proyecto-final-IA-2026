"""Convierte data/raw/Afluencia_Metro_2026.csv (formato ancho, una fila por día y línea)
en data/processed/afluencia_por_hora.csv: pasajeros promedio por línea, tipo de día y hora.

Uso: python -m src.data.process_afluencia
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "Afluencia_Metro_2026.csv"
OUT = ROOT / "data" / "processed" / "afluencia_por_hora.csv"


def main():
    # La fila 2 trae las horas; la 1 solo títulos agrupados.
    df = pd.read_csv(RAW, header=1, dtype=str, encoding="utf-8-sig")
    df = df.rename(columns={df.columns[0]: "fecha", df.columns[1]: "linea"})
    df = df.drop(columns=[c for c in df.columns if c.startswith("Total")])
    df["fecha"] = df["fecha"].ffill()
    df = df.dropna(subset=["linea"])
    hours = [c for c in df.columns if ":" in c]
    long = df.melt(id_vars=["fecha", "linea"], value_vars=hours, var_name="hora", value_name="pasajeros")
    # Números con separador de miles "," (p. ej. "1,955 ").
    long["pasajeros"] = pd.to_numeric(long["pasajeros"].str.replace(",", "").str.strip(), errors="coerce")
    long["hora"] = long["hora"].str.split(":").str[0].astype(int)
    long["fecha"] = pd.to_datetime(long["fecha"], format="%m/%d/%Y")
    long["tipo_dia"] = long["fecha"].dt.dayofweek.map(lambda d: "habil" if d < 5 else "fin_de_semana")
    out = (long.groupby(["linea", "tipo_dia", "hora"])["pasajeros"].mean().round(0)
           .reset_index().rename(columns={"pasajeros": "pasajeros_promedio"}))
    out.to_csv(OUT, index=False)
    print(f"{long['fecha'].min().date()} a {long['fecha'].max().date()}, "
          f"{long['linea'].nunique()} líneas -> {OUT.name} ({len(out)} filas)")


if __name__ == "__main__":
    main()
