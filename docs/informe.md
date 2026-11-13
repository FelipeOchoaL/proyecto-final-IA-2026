# Copiloto de movilidad para el Valle de Aburrá: rutas con A\* y asistente RAG

SI3003 Inteligencia Artificial – EAFIT, 2026-1 · Proyecto 3.2 · Integrantes: Felipe Ochoa y Juan ginzalo

> Ningún resultado de este trabajo constituye asesoría legal, médica, de seguridad ni de movilidad
> oficial. Las cifras son estimaciones con datos abiertos y supuestos declarados.

## 1. Problema

Una persona que se mueve en el Valle de Aburrá debe elegir entre carro, Metro (y Tranvía,
Metrocable, buses integrados), bicicleta o caminata, con criterios en conflicto: **tiempo, costo y
emisiones**, además de reglas como el pico y placa o las condiciones para llevar bicicletas al Metro.
Construimos un MVP que (i) calcula la mejor ruta por modo con una búsqueda A\* propia y costo
multiobjetivo, y (ii) ofrece un agente LLM que combina esas rutas con un RAG sobre las reglas,
citando las fuentes, todo en un dashboard interactivo.

## 2. Datos

| Dato | Fuente | Estado |
|---|---|---|
| Red vial: 43.507 nodos, 95.511 aristas (Medellín, Bello, Itagüí, Envigado, Sabaneta, La Estrella); se usa el componente fuertemente conexo (43.356 nodos, 94.487 arcos tras fusionar multiaristas) | OpenStreetMap/OSMnx (ODbL) | Real |
| 52 estaciones, 176 paradas ordenadas en 29 rutas (Metro A/B, T-A, cables H/J/K/L/M, Metroplús parcial, buses integrados) | OpenStreetMap | Real, incompleto |
| Afluencia horaria por línea, ene-jul 2026 (12 líneas) | Datos abiertos Metro de Medellín | Real |
| Gasolina Medellín $16.251/gal (1-nov-2026) | CREG, Circular 371/2026 | Oficial |
| Pico y placa 2026-2; tarifas 2026 (Cívica $3.820); Reglamento del Usuario | Alcaldía, prensa, Metro | Oficial / prensa |
| Factores de velocidad por hora (libre 1,0; día 0,44; pico 0,338) | Calibrados con TomTom 2025 | **Simulado** (plan B) |
| Emisiones kgCO2e/pasajero-km (carro 0,1097; bus 0,0317; Metro 0,0278) | UK GHG 2024 y analogías | Aproximado |
| Metro 37, Tranvía 15, Cable 19 km/h; intervalo Línea A en punta 170 s | Fuentes no oficiales | No oficial |
| Bici 15 y caminata 5 km/h, transbordo 180 s, 40 km/gal, intervalo valle 300 s | Equipo | **Supuesto** |

Todos los parámetros están en `data/processed/supuestos.csv` con su tipo. No hay tráfico en tiempo
real; seguimos el plan B del enunciado (tiempos simulados por hora).

## 3. Método de la Parte 1: A\* multiobjetivo

**Grafo.** Un grafo por modo, porque el carro no se puede "dejar" a mitad de ruta
(`src/data/network.py`): *carro* (red vial dirigida, tiempo = `travel_time`/factor de la hora, costo
$406/km, emisiones 0,1097 kg/km); *bicicleta* y *caminata* (red vial en ambos sentidos a velocidad
constante); *transporte* (caminata + nodos "línea:estación" unidos entre paradas consecutivas, con
aristas de abordaje = caminata a la vía más cercana + espera de medio intervalo + pasaje $3.820, y
transbordos entre líneas de la misma estación = 180 s + espera, sin cobro adicional). osmnx/networkx
solo cargan el GraphML; la búsqueda usa listas de adyacencia propias.

**Costo.** Cada arista tiene (tiempo, costo, emisiones) y se escalariza como
\( w(e) = w_t \cdot \text{min} + w_c \cdot \text{miles COP} + w_e \cdot \text{100 g CO}_2\text{e} \),
con pesos del usuario normalizados a suma 1 (equivalencia 1 min ≈ $1.000 ≈ 100 g, decisión del equipo).

**Heurística.** \( h(n) = k \cdot d(n, meta) \), donde \(d\) es la distancia haversine y
\( k = \min_{(u,v)} w(u,v) / d(u,v) \) sobre todas las aristas del grafo y los pesos actuales. Es
**consistente** (y por tanto admisible): para toda arista,
\( h(u) = k\,d(u,g) \le k\,(d(u,v) + d(v,g)) \le w(u,v) + h(v) \), por la desigualdad triangular
y la definición de \(k\). Las aristas con \(d = 0\) (transbordos) tienen \( w \ge 0 \). Así la
heurística funciona para cualquier combinación de pesos y modos sin suponer una velocidad máxima.

**Algoritmos** (`src/search/algorithms.py`): A\* con cola de prioridad, conjunto cerrado y borrado
perezoso; Dijkstra/UCS = A\* con \(h = 0\); BFS minimiza el número de aristas. Se cuentan los nodos
expandidos (sacados de la frontera y cerrados).

## 4. Diseño del agente y del RAG

**RAG** (`src/rag/retriever.py`): 8 documentos Markdown (pico y placa, tarifas, bicicletas y
mascotas, medios de pago, emisiones y velocidades, red OSM, afluencia generada desde los datos del
Metro, supuestos del modelo), divididos en **30 fragmentos, uno por sección**, cada uno con su archivo
y URL de origen. Embeddings `paraphrase-multilingual-MiniLM-L12-v2` normalizados e índice FAISS de
producto interno (similitud coseno); top-4 por consulta.

**Herramientas** (`src/agent/tools.py`): `plan_route(origen, destino, modo, hora, pesos)`, que llama
a nuestro A\* (con `modo="todos"` compara los 4 modos), y `search_docs(consulta)`. Cualquier excepción
(estación inexistente, argumento faltante, JSON inválido) se devuelve al modelo como observación
`ERROR: ...`, con la lista de estaciones válidas.

**Loop** (`src/agent/agent.py`): loop manual con **T_max = 6**. En cada iteración se envía el
historial y los esquemas al LLM (Groq, `openai/gpt-oss-120b`, endpoint compatible con OpenAI); si
pide herramientas se ejecutan y su salida se agrega como mensaje `tool`; si responde texto, termina.
El prompt exige usar ambas herramientas en preguntas mixtas, no inventar datos y citar
`[archivo.md](URL)`. Si la API falla (sin clave, modelo inexistente, límite de uso, conexión), la
función devuelve un mensaje legible y la app sigue funcionando.

**Dashboard** (`app/app.py`, Streamlit): parámetros (origen, destino, hora con su escenario de
tráfico, pesos), mapa folium con las 4 rutas sobre la red de transporte, tabla comparativa y chat;
las rutas que calcula el agente se dibujan en el mapa.

## 5. Resultados

**Parte 1** (`python -m eval.search_eval`; 20 pares fijos: 10 entre estaciones y 10 aleatorios con
semilla 42; hora 8, pesos iguales):

| Perfil | Algoritmo | Nodos expandidos (prom.) | Tiempo (ms) | Costo | Óptimo |
|---|---|---|---|---|---|
| Carro | A\* | 5.995 | 32 | 18,8 | 20/20 |
| Carro | Dijkstra | 18.571 | 54 | 18,8 | 20/20 |
| Carro | BFS | 15.076 | 20 | 21,5 | 0/20 |
| Transporte | A\* | 4.401 | 24 | 16,8 | 20/20 |
| Transporte | Dijkstra | 9.922 | 34 | 16,8 | 20/20 |
| Transporte | BFS | 7.895 | 13 | 19,9 | 10/20 |

A\* encuentra siempre el costo óptimo (validado contra `nx.dijkstra_path_length`) y expande **68 %
menos nodos que Dijkstra en carro y 56 % menos en transporte**. BFS es rápido por expansión pero
devuelve rutas un 14-18 % más costosas en promedio, porque ignora los pesos. La reducción es menor en
transporte porque los tramos de Metro son mucho más rápidos que caminar, lo que baja \(k\) y debilita
la heurística.

Ejemplo (dashboard, Niquía → Poblado, 7 a. m., pesos 0,6/0,2/0,2): transporte 27,5 min, $3.820,
0,42 kg (caminata + Metro A); carro 34,7 min, $6.269, 1,69 kg; bicicleta 61,8 min; caminata 185 min.

**Parte 2** (`python -m eval.agent_eval`; 13 preguntas fijas: 6 solo de documentos, 3 solo de rutas,
3 que encadenan ambas herramientas y 1 con estación inexistente):

| Corrida | Herramienta correcta | Citó la fuente | Errores de API (Groq) |
|---|---|---|---|
| 1 (pausa 3 s entre preguntas) | 12/13 (92 %) | 10/13 (77 %) | 2 (conexión; límite de tokens/min) |
| 2 (pausa 12 s; `eval/results/agent_summary.md`) | **13/13 (100 %)** | **11/13 (85 %)** | 1 (límite de tokens/min, pregunta 12) |

En la corrida 2, sin contar el error de API, el agente llamó a las herramientas correctas en 12/12 y
citó en 11/12. La única pregunta sin cita es la de la estación inexistente ("Narnia"): el error de
`plan_route` volvió como observación y el agente pidió una estación válida, pero citó una página
genérica en vez de un documento. Las 3 preguntas mixtas encadenaron `search_docs` y `plan_route`, y
la pregunta sobre la ventana de integración tarifaria (dato inexistente) se respondió correctamente
con "no dispongo del dato". La métrica de cita es automática (detecta el nombre del archivo) y **no
verifica la fidelidad**; al revisar las respuestas a mano encontramos dos problemas: en la pregunta 11
el agente afirmó que el costo del carro "incluye peajes y desgaste" (solo incluye combustible), y en
la pregunta 7, con peso solo en tiempo, A\* propuso bajarse y volver a abordar pagando dos pasajes
($7.640) porque es más rápido que el transbordo supuesto de 180 s. Los errores 429 muestran que la capa
gratuita de Groq (8.000 tokens/min) limita preguntas largas seguidas; la app los maneja con un mensaje.

## 6. Limitaciones

- **Tiempos simulados:** 3 factores de velocidad por periodo para toda la ciudad; la asignación de
  horas es un supuesto y la afluencia real del Metro muestra picos ~1 h antes (5-7 a. m., 4-6 p. m.).
- **Transporte público aproximado:** sin frecuencias ni horarios oficiales; velocidades no oficiales;
  tramos en línea recta entre paradas; integración tarifaria asumida; OSM incompleto (Metroplús con 2
  estaciones, Línea P sin paradas, pocos buses). Salir a la calle y volver a abordar cobra un pasaje
  nuevo, por lo que con peso solo en tiempo pueden aparecer rutas con dos pasajes.
- **Bici y caminata** sobre la red de carros, sin ciclorrutas, pendientes ni seguridad vial.
- **Carro:** solo combustible (rendimiento supuesto); sin parqueadero ni peajes; el pico y placa lo
  responde el agente, no lo aplica el planificador.
- **Emisiones** del Reino Unido y analogías: útiles para comparar modos, no para reportar huella.
- **Lugares** limitados a 52 estaciones (no hay geocodificación).
- **Agente:** LLM externo no determinista y con límite de uso gratuito; puede omitir datos o citar con
  formato irregular; la evaluación detecta citas por nombre de archivo, no verifica que la afirmación
  sea fiel al documento.
- **Evaluación pequeña:** 20 pares O-D y 13 preguntas; no es una muestra representativa de viajes reales.
