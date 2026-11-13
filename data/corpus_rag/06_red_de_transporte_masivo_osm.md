# Red de transporte masivo del Valle de Aburrá (según OpenStreetMap)

**Fuente:** OpenStreetMap vía Overpass API (ODbL, © colaboradores de OSM), descargado con `scripts/01_osm_transit.py` el 11-nov-2026. Los datos son colaborativos y pueden estar incompletos o desactualizados; no son información oficial del Metro de Medellín.

## Resumen
- Metro: 27 estaciones únicas en las líneas A y B (San Antonio es el transbordo entre ambas).
- Tranvía de Ayacucho (T-A): 8 estaciones mapeadas.
- Metrocable: 15 estaciones en las líneas H, J, K, L y M (la línea P existe en OSM pero sin paradas mapeadas).
- Metroplús: solo 2 estaciones mapeadas (datos incompletos en OSM).
- Además hay rutas de buses integrados mapeadas, pero su cobertura es parcial.

## Secuencia de estaciones por línea (según OSM)
- **Metro línea A:** La Estrella → Sabaneta → Itagüí → Envigado → Ayurá → Aguacatala → Poblado → Industriales → Exposiciones → Alpujarra → San Antonio → Parque Berrío → Prado → Hospital → Universidad → Caribe → Tricentenario → Acevedo → Madera → Bello → Niquía
- **Metro línea B:** San Antonio → Cisneros → Suramericana → Estadio → Floresta → Santa Lucía → San Javier
- **Tranvía T-A:** Oriente → Alejandro Echavarría → Loyola → Buenos Aires → Bicentenario → Pabellón del Agua → San José → San Antonio
- **Metrocable H:** Villa Sierra → Las Torres → Oriente
- **Metrocable J:** San Javier → Juan XXIII → Vallejuelos → La Aurora
- **Metrocable K:** Santo Domingo → Popular → Andalucía → Acevedo
- **Metrocable L (Arví):** Santo Domingo → Arví
- **Metrocable M:** Trece de Noviembre → El Pinal → Miraflores

Nota: el orden del tranvía viene de relaciones `stop_area` sin orden garantizado, y puede faltar alguna estación; verificar contra el mapa oficial antes de afirmar un orden o un número de estaciones.

## Transbordos identificados por nombre de estación
- San Antonio (metro): líneas A, B
- Santo Domingo (metrocable): líneas K, L

Transbordos entre modos distintos (misma estación por nombre; distancia entre los puntos de OSM):
- Acevedo: metro (A) ↔ metrocable (K), ~49 m entre los puntos mapeados
- Oriente: metrocable (H) ↔ tranvia (T-A), ~40 m entre los puntos mapeados
- San Antonio: metro (A, B) ↔ tranvia (T-A), ~66 m entre los puntos mapeados
- San Javier: metro (B) ↔ metrocable (J), ~72 m entre los puntos mapeados

## Limitaciones
- No hay en este corpus frecuencias, tiempos de recorrido ni horarios oficiales de los trenes.
- El agente no debe afirmar conexiones, horarios o frecuencias que no estén en este documento ni en las herramientas.
