# Emisiones por modo y velocidades de tráfico: supuestos del modelo

Este documento describe los **supuestos** que usa el copiloto para estimar emisiones y tiempos. No son mediciones oficiales colombianas; el agente debe presentarlos como estimaciones aproximadas.

## Factores de emisión (kg de CO2e por pasajero-km)
Detalle y notas por fila en `data/processed/emission_factors.csv`.

| Modo | Factor | Origen del dato |
|---|---|---|
| Carro particular | 0,1097 | Derivado: 0,1645 kgCO2e/vehículo-km ÷ 1,5 ocupantes (la ocupación es un supuesto del equipo) |
| Bus | 0,03174 | Citado: bus local, UK GHG Conversion Factors 2024 |
| Metroplús | 0,03174 | Analogía con bus local |
| Metro | 0,0278 | Analogía: Metro de Londres, UK GHG Conversion Factors 2024 |
| Tranvía | 0,0278 | Analogía con el metro |
| Metrocable | 0,0278 | Analogía con el metro |
| Bicicleta y caminata | 0 | Emisión operativa nula (sin ciclo de vida) |

Fuente de los valores del Reino Unido: UK Government GHG Conversion Factors for Company Reporting 2024 (https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2024), consultados a través del espejo Climatiq, no del archivo oficial.

**Limitaciones importantes:**
- No existe en este corpus un factor oficial colombiano por pasajero-km (UPME FECOC+ cubre combustibles y vehículos pesados, no esta métrica).
- El Metro de Medellín es eléctrico y el mix de generación del país es distinto al del Reino Unido; el factor real del Metro sería distinto.
- Los factores sirven para **comparar modos entre sí**, no para reportar una huella de carbono.
- Contexto: el Metro de Medellín reportó una huella propia de 6.243 tCO2e en 2024 (medida de su operación, no un factor por pasajero).

## Velocidades de tráfico
- TomTom Traffic Index 2025 (reportado por prensa): velocidad promedio en Medellín de ~20,7 km/h durante el día y ~15,9 km/h en hora pico.
- Un estudio académico sobre corredores de Medellín (año no indicado) reportó 22,1 km/h en el pico de la mañana y 17 km/h en el de la tarde.
- La Secretaría de Movilidad de Medellín tiene una base de datos de tráfico, pero no se encontraron datos recientes publicados.

**Cómo se usan:** el grafo vial trae velocidades en condiciones libres (47 km/h de media en rutas de 2-15 km). Los tiempos se escalan dividiendo `travel_time` por un factor calibrado contra TomTom: 0,44 (promedio del día) y 0,338 (hora pico). Ver `data/processed/speed_factors.csv` y `scripts/03_calibrate_speed_factors.py`.
La asignación de horas a periodos (pico 6-9 y 17-20) es un **supuesto del equipo**.

**Limitación:** es una calibración a nivel de toda la red, no refleja el tráfico real de una calle o un día concretos.

## Aviso
Las estimaciones de emisiones y tiempos son orientativas y no constituyen asesoría de movilidad ni de seguridad.
