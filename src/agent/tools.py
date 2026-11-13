"""Herramientas del agente: esquemas (formato OpenAI tool calling) y ejecución.

Cualquier excepción se convierte en un texto "ERROR: ..." que el loop devuelve al modelo
como observación, para que pueda corregir argumentos o explicar el problema al usuario.
"""
import json

from src.rag.retriever import search_docs
from src.search.planner import compare_modes, places, plan_route

MODES = ["carro", "transporte", "bicicleta", "caminata", "todos"]

TOOL_SCHEMAS = [
    {"type": "function", "function": {
        "name": "plan_route",
        "description": ("Calcula la ruta óptima con el algoritmo A* propio entre dos estaciones del "
                        "Valle de Aburrá y devuelve tiempo (min), costo (COP), emisiones (kgCO2e) y tramos. "
                        "modo='todos' compara carro, transporte público, bicicleta y caminata."),
        "parameters": {"type": "object", "properties": {
            "origen": {"type": "string", "description": "Nombre de estación de origen, p. ej. 'Poblado'"},
            "destino": {"type": "string", "description": "Nombre de estación de destino"},
            "modo": {"type": "string", "enum": MODES, "description": "Modo de transporte"},
            "hora": {"type": "integer", "description": "Hora de salida 0-23"},
            "peso_tiempo": {"type": "number", "description": "Importancia del tiempo (>=0)"},
            "peso_costo": {"type": "number", "description": "Importancia del costo (>=0)"},
            "peso_emisiones": {"type": "number", "description": "Importancia de las emisiones (>=0)"},
        }, "required": ["origen", "destino"]}}},
    {"type": "function", "function": {
        "name": "search_docs",
        "description": ("Busca en el corpus de documentos (pico y placa 2026-2, tarifas Metro 2026, "
                        "bicicletas y mascotas en el Metro, medios de pago Cívica, afluencia por hora, "
                        "emisiones y supuestos del modelo). Devuelve fragmentos con archivo y URL fuente."),
        "parameters": {"type": "object", "properties": {
            "consulta": {"type": "string", "description": "Pregunta o palabras clave en español"},
        }, "required": ["consulta"]}}},
]


def _route_summary(r: dict) -> dict:
    """Quita las coordenadas (largas e inútiles para el LLM)."""
    return {k: v for k, v in r.items() if k not in ("coords", "segment_modes")}


def run_tool(name: str, args: dict, defaults: dict) -> tuple:
    """Ejecuta una herramienta. Devuelve (texto_observación, rutas_para_el_mapa)."""
    try:
        if name == "plan_route":
            hour = int(args.get("hora", defaults.get("hora", 8)))
            w = (float(args.get("peso_tiempo", defaults.get("peso_tiempo", 1.0))),
                 float(args.get("peso_costo", defaults.get("peso_costo", 0.0))),
                 float(args.get("peso_emisiones", defaults.get("peso_emisiones", 0.0))))
            modo = args.get("modo", "todos")
            if modo not in MODES:
                raise ValueError(f"modo inválido '{modo}'. Opciones: {MODES}")
            if modo == "todos":
                routes = compare_modes(args["origen"], args["destino"], hour, w)
                if all("error" in r for r in routes):
                    raise ValueError(routes[0]["error"])
            else:
                routes = [plan_route(args["origen"], args["destino"], modo, hour, w)]
            obs = {"fuente": "Planificador A* propio (src/search). Supuestos: 08_supuestos_del_modelo.md",
                   "rutas": [_route_summary(r) for r in routes]}
            return json.dumps(obs, ensure_ascii=False), [r for r in routes if "coords" in r]
        if name == "search_docs":
            hits = search_docs(args["consulta"], k=4)
            obs = [{"archivo": h["archivo"], "url": h["url"], "seccion": h["seccion"],
                    "texto": h["texto"][:1500]} for h in hits]
            return json.dumps(obs, ensure_ascii=False), []
        raise ValueError(f"Herramienta desconocida: {name}")
    except KeyError as e:
        return f"ERROR: falta el argumento obligatorio {e}.", []
    except Exception as e:  # noqa: BLE001 - el error se devuelve al modelo como observación
        hint = ""
        if name == "plan_route":
            hint = " Estaciones válidas: " + ", ".join(places())
        return f"ERROR: {e}.{hint}", []
