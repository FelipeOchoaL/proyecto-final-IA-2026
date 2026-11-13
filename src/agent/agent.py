"""Agente LLM con loop agéntico manual (sin LangGraph).

Loop (máximo T_MAX iteraciones):
  1. Se envía el historial + esquemas de herramientas al LLM (endpoint compatible con OpenAI: Groq).
  2. Si el LLM pide herramientas, se ejecutan y su salida (o "ERROR: ...") se agrega como
     mensaje role="tool" (observación) y se repite.
  3. Si responde texto sin pedir herramientas, esa es la respuesta final.
Si se alcanza T_MAX sin respuesta final, se devuelve un mensaje explícito.
"""
import json
import os
import re

from dotenv import load_dotenv

from src.agent.tools import TOOL_SCHEMAS, run_tool
from src.data.loader import ROOT

T_MAX = 6
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
DISCLAIMER = ("Aviso: estimaciones orientativas con datos abiertos y supuestos; no es asesoría legal, "
              "de seguridad ni de movilidad oficial.")

SYSTEM_PROMPT = """Eres un copiloto de movilidad para el Valle de Aburrá (Medellín). Respondes en español, breve y claro.
Herramientas:
- plan_route: rutas con nuestro A* (tiempo, costo, emisiones) entre estaciones. Úsala para cualquier pregunta de ruta, modo o comparación.
- search_docs: reglas de pico y placa, tarifas, bicicletas/mascotas en el Metro, tarjeta Cívica, afluencia por hora y supuestos del modelo.
Reglas:
1. Si la pregunta combina ruta y reglas (p. ej. ir en carro y pico y placa), llama a AMBAS herramientas.
2. Usa SOLO la información de las herramientas. Si un dato no está, di que no cuentas con él y remite a https://www.metrodemedellin.gov.co o a la Alcaldía. No inventes cifras.
3. Cita SIEMPRE las fuentes al final, solo con este formato markdown (no uses 【】): "Fuentes: [archivo.md](URL)" para documentos y "[Planificador A* propio]" para rutas.
4. Si una herramienta devuelve ERROR, corrige los argumentos (p. ej. el nombre de la estación) o explica el problema.
5. Los tiempos de carro/bus son simulados por hora (sin tráfico real) y las emisiones son aproximadas: dilo cuando sea relevante. El periodo de la hora viene en el campo "periodo" de cada ruta; no lo deduzcas.
6. Al comparar modos, muestra todos los que devolvió plan_route (incluido el carro, aunque esté restringido por pico y placa, indicándolo).
Contexto de la interfaz (úsalo como valores por defecto si el usuario no dice otra cosa): {context}"""


def _client():
    load_dotenv(ROOT / ".env")
    key = os.getenv("GROQ_API_KEY", "").strip()
    if not key:
        raise RuntimeError("No hay GROQ_API_KEY. Copie .env.example a .env y agregue su clave de Groq.")
    from openai import OpenAI
    return OpenAI(api_key=key, base_url=os.getenv("LLM_BASE_URL", GROQ_BASE_URL), timeout=60, max_retries=1), \
        os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")


def _link_citations(text: str) -> str:
    """Convierte citas sueltas como 【01_x.md】 en enlaces markdown [01_x.md](URL del documento)."""
    from src.rag.retriever import chunk_corpus
    urls = {c["archivo"]: c["url"] for c in chunk_corpus()}
    return re.sub(r"【\s*([\w\-.]+\.md)[^】]*】",
                  lambda m: f"[{m.group(1)}]({urls[m.group(1)]})" if urls.get(m.group(1)) else m.group(1), text)


def run_agent(question: str, history=None, defaults=None) -> dict:
    """Devuelve {answer, trace, routes, error}. Nunca lanza excepción: los fallos del LLM/API
    se reportan en 'error' con un mensaje legible para la interfaz."""
    defaults = defaults or {}
    trace, routes = [], []
    try:
        client, model = _client()
    except Exception as e:  # noqa: BLE001
        return {"answer": f"El asistente no está disponible: {e}", "trace": trace, "routes": routes,
                "error": str(e)}
    messages = [{"role": "system", "content": SYSTEM_PROMPT.format(context=json.dumps(defaults, ensure_ascii=False))}]
    messages += list(history or [])
    messages.append({"role": "user", "content": question})
    for step in range(1, T_MAX + 1):
        try:
            resp = client.chat.completions.create(model=model, messages=messages, tools=TOOL_SCHEMAS,
                                                  tool_choice="auto", temperature=0)
        except Exception as e:  # noqa: BLE001 - API caída, límite de uso, clave inválida...
            return {"answer": f"No pude contactar al modelo de lenguaje ({type(e).__name__}). "
                              "Intente de nuevo en unos segundos; el mapa y la tabla siguen funcionando.",
                    "trace": trace, "routes": routes, "error": str(e)}
        msg = resp.choices[0].message
        if not msg.tool_calls:
            return {"answer": _link_citations((msg.content or "").strip()) + f"\n\n_{DISCLAIMER}_", "trace": trace,
                    "routes": routes, "error": None}
        messages.append({"role": "assistant", "content": msg.content or "",
                         "tool_calls": [tc.model_dump() for tc in msg.tool_calls]})
        for tc in msg.tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError as e:
                args, obs, new_routes = {}, f"ERROR: argumentos JSON inválidos ({e}).", []
            else:
                obs, new_routes = run_tool(tc.function.name, args, defaults)
            routes.extend(new_routes)
            trace.append({"paso": step, "herramienta": tc.function.name, "args": args,
                          "ok": not obs.startswith("ERROR"), "observacion": obs[:300]})
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": obs})
    return {"answer": f"No llegué a una respuesta final en {T_MAX} iteraciones (T_max). "
                      "Intente reformular la pregunta.", "trace": trace, "routes": routes,
            "error": "T_max alcanzado"}
