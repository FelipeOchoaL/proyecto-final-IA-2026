"""Evaluación del agente sobre preguntas fijas (eval/questions.json).

Uso (desde la raíz, con GROQ_API_KEY en .env):  python -m eval.agent_eval
Salidas: eval/results/agent_results.csv y eval/results/agent_summary.md

Por pregunta se registra:
- herramientas esperadas vs. llamadas; "herramienta_correcta" = se llamaron TODAS las esperadas.
- "cito_fuente": la respuesta menciona un archivo del corpus (.md) cuando la pregunta requiere
  documentos, o "[Planificador A* propio]" cuando solo requiere rutas.
- errores de herramienta observados (p. ej. estación inexistente) e iteraciones usadas.
"""
import json
import re
import time
from pathlib import Path

import pandas as pd

from src.agent.agent import run_agent

HERE = Path(__file__).resolve().parent
OUT = HERE / "results"
PAUSE_S = 12  # pausa entre preguntas para no exceder el límite de uso de la capa gratuita


def cited(answer: str, needs_doc: bool) -> bool:
    if needs_doc:
        return bool(re.search(r"\d{2}_[\w\-]+\.md", answer))
    return "planificador a*" in answer.lower() or bool(re.search(r"\d{2}_[\w\-]+\.md", answer))


def main():
    OUT.mkdir(exist_ok=True)
    questions = json.loads((HERE / "questions.json").read_text(encoding="utf-8"))
    rows = []
    for q in questions:
        t0 = time.perf_counter()
        res = run_agent(q["pregunta"], defaults={"hora": 8})
        called = [t["herramienta"] for t in res["trace"]]
        expected = q["herramientas_esperadas"]
        rows.append({
            "id": q["id"], "pregunta": q["pregunta"],
            "esperadas": "+".join(expected), "llamadas": "+".join(called) or "(ninguna)",
            "herramienta_correcta": all(e in called for e in expected),
            "cito_fuente": cited(res["answer"], q["requiere_cita_doc"]),
            "errores_herramienta": sum(not t["ok"] for t in res["trace"]),
            "iteraciones": max([t["paso"] for t in res["trace"]], default=0) + 1,
            "error_llm": (res["error"] or "").split(" in organization")[0][:80],
            "segundos": round(time.perf_counter() - t0, 1),
            "respuesta": res["answer"].replace("\n", " ")[:400],
        })
        r = rows[-1]
        print(f"[{q['id']:>2}] esperadas={r['esperadas']:<22} llamadas={r['llamadas']:<30} "
              f"ok={r['herramienta_correcta']} cita={r['cito_fuente']} {r['error_llm'][:60]}")
        time.sleep(PAUSE_S)
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "agent_results.csv", index=False)
    n = len(df)
    ok = df[df.error_llm == ""]
    md = ["# Evaluación del agente", "",
          f"{n} preguntas fijas (`eval/questions.json`), modelo según `.env`, T_max = 6.", "",
          f"- Herramienta correcta: **{df.herramienta_correcta.sum()}/{n}** "
          f"({100 * df.herramienta_correcta.mean():.0f} %)",
          f"- Citó la fuente: **{df.cito_fuente.sum()}/{n}** ({100 * df.cito_fuente.mean():.0f} %)",
          f"- Preguntas con error del LLM/API (conexión, límite de uso): {(df.error_llm != '').sum()}",
          f"- Sin contar errores de API: herramienta correcta "
          f"{ok.herramienta_correcta.sum()}/{len(ok)}, citó fuente {ok.cito_fuente.sum()}/{len(ok)}", "",
          df.drop(columns=["respuesta"]).to_markdown(index=False), "",
          "## Respuestas (primeros 400 caracteres)", ""]
    md += [f"**{r.id}. {r.pregunta}**\n\n> {r.respuesta}\n" for r in df.itertuples()]
    (OUT / "agent_summary.md").write_text("\n".join(md), encoding="utf-8")
    print(f"\nHerramienta correcta {df.herramienta_correcta.sum()}/{n} | Citó fuente {df.cito_fuente.sum()}/{n}")


if __name__ == "__main__":
    main()
