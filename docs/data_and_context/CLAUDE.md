# CLAUDE.md – Contexto del proyecto: Copiloto de movilidad (SI3003, EAFIT)

Lee este archivo completo antes de tocar nada. Resume el enunciado, lo ya hecho, lo que falta y las trampas conocidas.

## 1. Qué es esto
Proyecto final de **SI3003 – Inteligencia Artificial (EAFIT, 2026-1)**, 25 % de la nota del curso, trabajo en equipo con calificación grupal y evaluación individual. Profesor: Jorge Iván Padilla Buriticá.
**Idea elegida: 3.2 Copiloto de movilidad: rutas con A\* y asistente RAG.** Un usuario elige origen, destino y hora en el Valle de Aburrá; el sistema compara modos (carro, Metro/Tranvía/Metrocable, bus, bicicleta, a pie) por **tiempo, costo y emisiones**, y un agente LLM explica y responde dudas (pico y placa, tarifas, reglas del Metro).

**Fecha límite: viernes 13 de noviembre de 2026, 6:00 p. m.** (no se reciben entregas tardías). Congelar código el jueves 12. Alcance: **MVP que funcione de punta a punta**; es preferible poco y funcionando. Un componente que falla en la demo no recibe puntaje.

## 2. Requisitos obligatorios del enunciado
1. **Datos reales colombianos**, fuente identificada y citada, con plan B local.
2. **Parte 1 (técnica clásica) implementada por el equipo**, no invocada desde una librería que ya la resuelve: **búsqueda A\*/UCS con costo multiobjetivo y heurística admisible**, comparada contra **BFS/Dijkstra en nodos expandidos**, con métrica cuantitativa frente a una línea base. (No uses `nx.astar_path` como la implementación entregada; úsalo, si acaso, solo para validar resultados.)
3. **Agente LLM** con loop (con Tmáx y errores de herramientas devueltos como observación), **RAG** sobre el corpus y **≥ 2 herramientas** (tool calling). Debe **citar fuentes**. Debe combinar de forma no trivial la Parte 1 con la Parte 2: herramienta `plan_route()` + RAG; consultas que encadenen varias herramientas.
4. **≥ 2 visualizaciones** (mapa con rutas alternativas + tabla comparativa tiempo/costo/emisiones).
5. **Interacción**: seleccionar parámetros (origen, destino, hora, modo/preferencias) y **chatear con el agente** desde la interfaz.
6. **Reproducible**: corre siguiendo el README, sin intervención manual.
7. **Repositorio GitHub** con código, README, `requirements.txt`, datos o instrucciones.
8. **Declaración de uso de IA generativa** (herramientas y propósito). El uso de IA está permitido, pero la dependencia total o no entender el trabajo entregado es falta de integridad académica. **El estudiante debe poder explicar cada parte.** Explica tus decisiones y deja comentarios útiles.

**Stack sugerido por el enunciado:** Python; Lightning AI Studio (CPU); agente con loop manual o LangGraph; endpoint compatible con OpenAI de capa gratuita (NVIDIA NIM, Groq u Ollama); RAG con embeddings + FAISS o Chroma; dashboard Streamlit o Gradio.

### Entregables
1. Repo GitHub (app corriendo desde el README). 2. **Informe de máximo 4 páginas** (problema, datos, método Parte 1, diseño del agente y RAG, resultados, limitaciones). 3. Demo funcional (opcional como plan B: **video de 3-4 min**). 4. **Evaluación del agente: 10-15 preguntas fijas**, indicando si llamó a la herramienta correcta y si citó la fuente. 5. Declaración de uso de IA.
**Envío:** todos los integrantes envían el repo a jipadillab@eafit.edu.co con asunto `si3003-AI-grupo-nombre`. No hay sustentación: el repo debe explicarse solo. Nota aprobatoria: 3.0.

### Rúbrica
Parte 1 (implementación propia, corrección, métrica vs línea base) 20 % · Agente (loop, RAG, ≥2 herramientas, errores, citas) 20 % · Dashboard (visualización clara) 10 % · Interacción y funcionalidad (sin fallas en la demo) 15 % · Rigor experimental (evaluación del modelo y del agente, limitaciones) 15 % · Reproducibilidad 10 % · Presentación 5 % · Declaración y uso ético de IA 5 %.

## 3. Reparto del trabajo
- **Compañero A (quien te lee ahora):** código del modelo (A\*), agente, RAG y dashboard.
- **Compañero B (autor de la capa de datos):** consiguió y organizó los datos y el corpus. **Ya está entregado** (ver sección 4). Si hace falta más información, se pide a B o se busca con las mismas reglas de honestidad de la sección 7.
- Aún **no existe repositorio de GitHub**: lo crea A. Todo lo que hay en esta carpeta es el punto de partida.

## 4. Lo que YA está hecho (capa de datos)
Léelo en detalle en `README.md` y `FUENTES.md`. Resumen:

| Qué | Dónde | Notas |
|---|---|---|
| Red vial (carro), Medellín + Bello + Itagüí + Envigado + Sabaneta + La Estrella | `data/processed/road_drive.graphml.gz` (se descomprime sola con `load_road_graph()`) | 43.507 nodos, 95.511 aristas, 8.952 km. Atributos: `length` (m), `speed_kph`, `travel_time` (s, **sin tráfico**), `geometry`, `highway` |
| Estaciones únicas | `data/processed/transit_stations.csv` | `mode, name, lat, lon, lines`. 27 Metro, 8 Tranvía, 15 Metrocable, 2 Metroplús |
| Paradas ordenadas por ruta | `transit_route_stops.csv`, `transit_routes.csv`, `transit_routes.geojson` | Metro A y B, T-A, Metrocable H/J/K/L/M, Metroplús parcial, buses integrados parciales |
| Transbordos entre modos | `intermodal_transfers.csv` | Acevedo (A↔K), Oriente (H↔T-A), San Antonio (A/B↔T-A), San Javier (B↔J); 40-72 m |
| Factores de velocidad por periodo | `speed_factors.csv`, `speed_factors_hours.csv` | libre 1,0 · promedio_dia 0,44 · hora_pico 0,338. **Tiempo ajustado = `travel_time` / factor** |
| Factores de emisión | `emission_factors.csv` | kgCO2e por pasajero-km; columna `tipo_de_dato`: CITADO / DERIVADO / ANALOGIA / SUPUESTO |
| Corpus RAG | `corpus_rag/01..06_*.md` | pico y placa 2026-2, tarifas 2026, bici y mascotas en el Metro, medios de pago e integración, supuestos de emisiones/velocidades, red de transporte masivo |
| PDFs oficiales del Metro | `data/raw/pdfs/` | Reglamento del Usuario (Res. 263/2019) y condiciones de la funcionalidad Bici |
| Cargador | `scripts/data_loader.py` | `load_road_graph, load_stations, load_route_stops, load_transfers, load_emission_factors, speed_factor(hour)` |
| Scripts de regeneración | `scripts/01_osm_transit.py`, `02_osm_road_network.py`, `03_calibrate_speed_factors.py`, `common.py` | Fuente: OpenStreetMap vía Overpass (ODbL) |

**Fuentes y nivel de verificación de cada dato están en `FUENTES.md` y al inicio de cada documento del corpus. Respétalos al citar.**

## 5. Lo que FALTA (tu trabajo)
Orden sugerido (cronograma real: hoy es el 11-nov; congelar el jueves 12):

1. **Modelo Parte 1 (A\*) – prioridad máxima (20 %).**
   - Construir un grafo de decisión con costo multiobjetivo (tiempo, costo monetario, emisiones; pesos configurables por el usuario).
   - **Implementar tú mismo** A\*, y Dijkstra/UCS y BFS como líneas base; reportar **nodos expandidos, tiempo de cómputo y costo de la solución** sobre un conjunto fijo de pares origen-destino (semilla fija).
   - **Heurística admisible**: p. ej., distancia haversine / velocidad máxima del grafo para el tiempo; para costo y emisiones usa un límite inferior válido (puede ser 0 o la tarifa/factor mínimo). Demuestra o argumenta la admisibilidad en el informe.
   - Multimodal: nodos = nodos viales + estaciones; aristas de transporte masivo entre paradas consecutivas (de `transit_route_stops.csv`), acceso/egreso a pie, bicicleta. **Los datos NO incluyen velocidad ni frecuencia del Metro**: debes asumirlas y declararlas como supuestos en el informe (no hay fuente oficial verificada). Lo mismo para velocidad a pie/bici.
   - Costo del carro: no hay dato verificado (combustible, parqueadero, peajes). Declara supuestos o limítate a lo que sí tiene fuente.
   - Tarifa del Metro: viaje en un solo medio con Cívica personalizada **$3.820** (2026). Para transbordos, el **tiempo de integración no está definido** en las fuentes: si lo modelas, decláralo como supuesto del modelo.
2. **Agente LLM + RAG (20 %).**
   - Indexa `corpus_rag/*.md` (embeddings + FAISS/Chroma), un chunk por sección, conservando archivo y URL fuente para **citar**.
   - Herramientas mínimas: `plan_route(origen, destino, hora, preferencias)` (usa tu A\*), `search_docs(consulta)` (RAG). Recomendadas: `compare_modes(...)`, `get_station_info(nombre)`, `check_pico_y_placa(placa, día, hora)` (regla determinística).
   - Loop manual con **Tmáx** de iteraciones; los errores de herramienta se devuelven como observación.
   - Endpoint compatible con OpenAI de capa gratuita (Groq / NVIDIA NIM / Ollama).
3. **Dashboard (Streamlit o Gradio):** mapa con rutas alternativas (`transit_routes.geojson`, geometrías de aristas del grafo), tabla comparativa de tiempo/costo/emisiones, selección de origen/destino/hora/preferencias y **chat con el agente**.
4. **Evaluación (15 %):** (a) modelo: A\* vs Dijkstra vs BFS en nodos expandidos y tiempo; (b) agente: **10-15 preguntas fijas**, registrando si llamó a la herramienta correcta y si citó la fuente. Guardar resultados en un archivo reproducible.
5. **Informe (≤ 4 páginas), README de ejecución, declaración de uso de IA, video demo de 3-4 min (plan B).**

## 6. Trampas técnicas conocidas
- **Usa el componente fuertemente conexo**: `H = G.subgraph(max(nx.strongly_connected_components(G), key=len))`. El grafo completo tiene nodos aislados (99,7 % en el componente principal).
- `ox.distance.nearest_nodes` en un grafo no proyectado **requiere `scikit-learn`** (ya está en `requirements.txt`).
- `travel_time` es **sin tráfico** (media 47 km/h en rutas de 2-15 km). Divide por `speed_factor(hora)`; el pico da ≈ 17 km/h, coherente con TomTom 2025.
- **Python de macOS (LibreSSL)** falla el TLS con `overpass-api.de`; los scripts de descarga usan `curl`. El script 02 tarda ~8 min y el Overpass público a veces responde 502 "at capacity": **no regeneres los datos si no hace falta**.
- Overpass/OSMnx **no se debe llamar durante la demo**: todo funciona offline con los archivos de `data/processed/`.
- Para ubicar una estación en el grafo vial usa el nodo vial más cercano (o conéctalas a pie con la distancia haversine).
- El grafo y los datos no incluyen carriles bici ni red peatonal: caminata y bicicleta deben modelarse con distancia/velocidad asumidas o con el grafo `drive` como aproximación. Declara la limitación.
- El Metroplús tiene solo 2 estaciones en OSM y el Metrocable Línea P no tiene paradas; el tranvía puede estar incompleto. No afirmes que están completos.

## 7. Reglas de honestidad sobre los datos (importante para el agente y el informe)
- **No inventes cifras.** Si el corpus no tiene un dato (tiempo de integración tarifaria, frecuencias y horarios del Metro, tarifas por modo por separado), el agente debe decir que **no cuenta con ese dato** y remitir a metrodemedellin.gov.co.
- **Tarifas 2026** vienen de prensa (Publimetro y El Tiempo coinciden); falta el acuerdo metropolitano oficial. **Rotación del pico y placa** confirmada por dos medios; la lista de **vías exentas difiere** entre la Alcaldía y la prensa. Cítalo así.
- **Factores de emisión**: no hay factor colombiano oficial; son valores del Reino Unido (vía espejo) y analogías. Sirven para **comparar modos**, no para reportar huella. Decláralo.
- **Ningún resultado se presenta como asesoría médica, legal, de seguridad o de movilidad oficial.** Incluye esta advertencia en el dashboard y el agente.
- Cita siempre la fuente (archivo del corpus + URL) al responder con información del RAG.

## 8. Fuentes no accesibles (plan B ya aplicado)
- Portal de datos abiertos del AMVA (`datosabiertos.metropol.gov.co`, Encuesta Origen-Destino 2017): devolvió 502 en todos los intentos. Opcional para el MVP.
- Servidor de mapas de la Alcaldía de Medellín: 403 a clientes programáticos (no se evadió).
- Espejo TUMI: conexión rechazada.
- No hay datos de tráfico en tiempo real → plan B del enunciado: **tiempos simulados con parámetros por hora** (ya implementado en `speed_factors*.csv`).

## 9. Cómo trabajar (instrucciones para Claude)
- Responde en **español**. Sé directo y explica las decisiones: el estudiante debe entender y poder defender el código (integridad académica; no hay sustentación).
- **Construye primero una versión mínima de punta a punta** (A\* + una herramienta + dashboard esqueleto) y mejórala después. No sobre-ingenies.
- Mantén todo reproducible desde el README (semillas fijas, rutas relativas, sin pasos manuales).
- Antes de afirmar que algo funciona, **ejecútalo** y reporta el resultado real, incluidas las fallas.
- No modifiques ni regeneres `data/processed/` sin necesidad; si añades datos, registra la fuente en `FUENTES.md`.
- Al final, actualiza el `README.md` (cómo correr app y evaluación) y la sección de **declaración de uso de IA** con las herramientas usadas y su propósito.
- No subas a GitHub el PDF del enunciado ni el audio (ya están en `.gitignore`).

## 10. Estructura actual del repositorio
```
README.md  FUENTES.md  CLAUDE.md  requirements.txt  .gitignore
scripts/      01_osm_transit.py  02_osm_road_network.py  03_calibrate_speed_factors.py  common.py  data_loader.py
corpus_rag/   01_pico_y_placa_medellin_2026-2.md  02_tarifas_metro_sitva_2026.md
              03_bicicletas_y_mascotas_en_el_metro.md  04_medios_de_pago_e_integracion_civica.md
              05_emisiones_y_velocidades_supuestos.md  06_red_de_transporte_masivo_osm.md
data/processed/  road_drive.graphml.gz  transit_*.csv/.geojson  intermodal_transfers.csv
                 speed_factors*.csv  emission_factors.csv
data/raw/pdfs/   reglamento-del-usuario-11052019-1.pdf  condiciones-de-uso-funcionalidad-bici.pdf (+ .txt)
```
Por crear: `src/` (modelo A\*, agente, RAG), `app.py` (dashboard), `eval/` (evaluación), `informe/`.
