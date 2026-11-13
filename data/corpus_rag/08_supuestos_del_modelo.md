# Supuestos y parámetros del modelo de rutas (copiloto)

**Fuente:** data/processed/supuestos.csv del proyecto. Cada parámetro indica si es CITADO (fuente oficial), PRENSA, NO_OFICIAL, DERIVADO o SUPUESTO del equipo.

## Parámetros usados por el planificador de rutas (A*)

| Parámetro | Valor | Unidad | Tipo | Fuente y notas |
|---|---|---|---|---|
| velocidad_metro | 37 | km/h | NO_OFICIAL | Presentación SITVA 2014 (CIDEU): 37 km/h velocidad comercial. mapa-metro.com reporta 40 km/h. Rango 37-40; se usa el valor conservador. |
| velocidad_tranvia | 15 | km/h | NO_OFICIAL | Presentación del Metro de Medellín (ALAMYS): 15 km/h velocidad comercial promedio. |
| velocidad_metrocable | 19 | km/h | NO_OFICIAL | LA FM: ~19 km/h para la Línea P. Se aplica por analogía a todas las líneas de cable. |
| velocidad_bus | =carro | km/h | SUPUESTO | Sin dato de velocidad de bus. Se usa la velocidad vehicular del grafo ajustada por hora; el bus real puede ser más lento (paradas) o más rápido (carril exclusivo). |
| velocidad_bicicleta | 15 | km/h | SUPUESTO | Valor típico de planeación urbana; sin fuente local verificada. |
| velocidad_caminata | 5 | km/h | SUPUESTO | Valor típico de planeación urbana; sin fuente local verificada. |
| intervalo_metro_pico | 170 | s | NO_OFICIAL | mapa-metro.com: Línea A cada 2 min 50 s en hora punta. No es fuente oficial. |
| intervalo_metro_valle | 300 | s | SUPUESTO | Sin dato. Supuesto del equipo. |
| intervalo_cable_tranvia | 300 | s | SUPUESTO | Sin dato. Supuesto del equipo. |
| espera_promedio | 0.5 | fraccion_intervalo | SUPUESTO | Espera promedio = mitad del intervalo (llegadas aleatorias de pasajeros). |
| tiempo_transbordo | 180 | s | SUPUESTO | Caminata entre andenes en estaciones de transbordo (San Antonio, Acevedo, etc.). No medido. |
| precio_gasolina_medellin | 16251 | COP/galon | CITADO | Gasolina motor corriente, Medellín, vigente desde el 1-nov-2026. Fuente oficial: CREG, Circular 371 de 2026 (30-oct-2026), tabla de 13 ciudades, pág. 3. Copia en data/raw/pdfs/creg_circular_371_2026.pdf. |
| rendimiento_carro | 40 | km/galon | SUPUESTO | Sin fuente (UPME/fabricantes no consultados). Supuesto del equipo. |
| costo_carro_km | 406 | COP/km | DERIVADO | precio_gasolina_medellin / rendimiento_carro = 16251/40. No incluye parqueadero, peajes ni desgaste. |
| tarifa_metro_civica | 3820 | COP/viaje | PRENSA | Cívica personalizada 2026 (Publimetro, El Tiempo). Ver corpus_rag/02. |
| tarifa_bus | 3820 | COP/viaje | SUPUESTO | Se asume la misma tarifa del sistema integrado; las rutas no integradas pueden diferir. |
| velocidad_vehicular_pico_manana_alt | 19.1 | km/h | PRENSA | Medellín 2025, 7-9 a. m. (prensa sobre TomTom). Franja más congestionada 13,9 km/h. Solo para contrastar con speed_factors.csv (15,9 km/h pico). |

## Datos que el modelo NO tiene

- Frecuencias y horarios oficiales del Metro (solo un intervalo no oficial en punta).
- Tiempo de la ventana de integración tarifaria (el reglamento no lo fija).
- Tráfico en tiempo real: los tiempos de carro y bus son SIMULADOS con factores por hora.
- Costo de parqueadero, peajes y desgaste del carro.

## Aviso

Estimaciones orientativas; no constituyen asesoría de movilidad oficial.