# Declaración de uso de IA generativa

Proyecto: Copiloto de movilidad – Valle de Aburrá (SI3003, EAFIT, 2026-1).
Integrantes: Felipe Ochoa y Juan Gonzalo

## Herramientas usadas

| Herramienta | Quién la usó | Para qué |
|---|---|---|
| Claude Code (Anthropic) | Juan gonzalo (capa de datos) | Búsqueda de fuentes, scripts de descarga de OpenStreetMap, calibración de factores de velocidad y redacción de los documentos 01-06 del corpus RAG (cada cifra con su fuente y nivel de verificación). |
| Cursor con Claude Opus 5.5 (Anthropic) | Felipe Ochoa (modelo, agente, app) | Generación asistida del código de `src/`, `app/` y `eval/`: grafo multimodal, A\*/Dijkstra/BFS, RAG con FAISS, loop del agente, dashboard Streamlit, scripts de evaluación; lectura de la Circular CREG 371 (PDF escaneado); borradores del README, del informe, del guion y de esta declaración. |
| Groq – `openai/gpt-oss-120b` | El propio sistema | Es el LLM del agente (parte del producto, no una ayuda de desarrollo). |

## Qué decidió y verificó el equipo

- La elección del proyecto (3.2), del alcance MVP y de las fuentes de datos.
- La búsqueda y aporte de datos adicionales: afluencia del Metro (portal de datos abiertos),
  Circular CREG 371 de 2026 y las velocidades no oficiales de Metro, Tranvía y Metrocable.
- Las decisiones de modelado: costo del carro como supuesto declarado, proveedor Groq, pesos
  configurables, uso de estaciones como lugares.
- Todo el código se **ejecutó** antes de darlo por terminado; los números del README y del informe
  salen de `eval/search_eval.py` y `eval/agent_eval.py`, no fueron escritos a mano.
- networkx se usa solo para cargar el grafo y para **validar** que nuestro A\* devuelve el costo
  óptimo; la búsqueda entregada es propia.

## Cómo se usó la IA de forma responsable

- Cada cifra del corpus y de `data/processed/supuestos.csv` indica si es oficial, de prensa, no
  oficial o supuesto; no se inventaron datos.
- La clave de la API está en `.env` (no versionado).
- El equipo revisó el código y debe poder explicar cada parte: la heurística (y por qué es
  consistente), el loop del agente, el RAG y la evaluación. _[Confirmar que cada integrante lo revisó.]_

## Limitaciones de esta declaración

_[El equipo debe completar: qué partes se escribieron o modificaron manualmente, qué sugerencias de
la IA se descartaron y por qué.]_
