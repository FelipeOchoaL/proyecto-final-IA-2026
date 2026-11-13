"""Genera dos documentos del corpus RAG a partir de datos tabulares del repo:

  07_afluencia_metro_2026.md     <- data/processed/afluencia_por_hora.csv
  08_supuestos_del_modelo.md     <- data/processed/supuestos.csv

Uso: python -m src.data.make_corpus_docs
"""
import pandas as pd

from src.data.loader import PROCESSED, ROOT

CORPUS = ROOT / "data" / "corpus_rag"
AFLUENCIA_URL = "https://datosabiertos-metrodemedellin.opendata.arcgis.com/"


def afluencia_doc():
    df = pd.read_csv(PROCESSED / "afluencia_por_hora.csv")
    lines = ["# Afluencia de pasajeros por hora en el Metro de Medellín (enero-julio 2026)", "",
             f"**Fuente:** Portal de datos abiertos del Metro de Medellín, {AFLUENCIA_URL} "
             "(archivo Afluencia_Metro_2026, procesado por el equipo: promedio de pasajeros por hora).", ""]
    for tipo, titulo in (("habil", "días hábiles (lunes a viernes)"), ("fin_de_semana", "fines de semana")):
        lines += [f"## Horas de mayor afluencia en {titulo}", "",
                  "| Línea | Hora más cargada | Pasajeros promedio en esa hora | 3 horas más cargadas |",
                  "|---|---|---|---|"]
        for linea, g in df[df.tipo_dia == tipo].groupby("linea"):
            top = g.sort_values("pasajeros_promedio", ascending=False).head(3)
            first = top.iloc[0]
            horas = ", ".join(f"{int(h)}:00" for h in top.hora)
            lines.append(f"| {linea} | {int(first.hora)}:00 | {int(first.pasajeros_promedio):,} | {horas} |")
        lines.append("")
    lines += ["## Cómo interpretar", "",
              "La hora indica el inicio de la franja (p. ej. 17:00 = de 5:00 a 6:00 p. m.). Son promedios "
              "históricos de 2026, no una predicción de la ocupación de un día concreto. "
              "El portal no publica la ocupación por vagón ni frecuencias.", "",
              "## Aviso", "", "Información orientativa; no constituye asesoría de movilidad oficial."]
    (CORPUS / "07_afluencia_metro_2026.md").write_text("\n".join(lines), encoding="utf-8")


def supuestos_doc():
    df = pd.read_csv(PROCESSED / "supuestos.csv")
    lines = ["# Supuestos y parámetros del modelo de rutas (copiloto)", "",
             "**Fuente:** data/processed/supuestos.csv del proyecto. Cada parámetro indica si es CITADO "
             "(fuente oficial), PRENSA, NO_OFICIAL, DERIVADO o SUPUESTO del equipo.", "",
             "## Parámetros usados por el planificador de rutas (A*)", "",
             "| Parámetro | Valor | Unidad | Tipo | Fuente y notas |", "|---|---|---|---|---|"]
    for r in df.itertuples():
        lines.append(f"| {r.parametro} | {r.valor} | {r.unidad} | {r.tipo_de_dato} | {r.fuente_y_notas} |")
    lines += ["", "## Datos que el modelo NO tiene", "",
              "- Frecuencias y horarios oficiales del Metro (solo un intervalo no oficial en punta).",
              "- Tiempo de la ventana de integración tarifaria (el reglamento no lo fija).",
              "- Tráfico en tiempo real: los tiempos de carro y bus son SIMULADOS con factores por hora.",
              "- Costo de parqueadero, peajes y desgaste del carro.", "",
              "## Aviso", "", "Estimaciones orientativas; no constituyen asesoría de movilidad oficial."]
    (CORPUS / "08_supuestos_del_modelo.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    afluencia_doc()
    supuestos_doc()
    print("Corpus: 07_afluencia_metro_2026.md y 08_supuestos_del_modelo.md generados.")
