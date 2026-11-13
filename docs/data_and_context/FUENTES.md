# Fuentes de datos – Copiloto de movilidad (SI3003, proyecto 3.2)

Estado al 11-nov-2026. Cada fuente indica si fue **verificada en la fuente primaria** o solo en prensa.

## 1. Descargado con scripts reproducibles

| Dato | Fuente | Licencia | Script | Salida |
|---|---|---|---|---|
| Rutas, paradas y estaciones de Metro (A, B), Tranvía (T-A), Metrocable (H, J, K, L, M), Metroplús parcial y buses integrados | OpenStreetMap vía Overpass API | ODbL, © colaboradores de OSM | `scripts/01_osm_transit.py` | `data/processed/transit_*.csv`, `transit_routes.geojson` |
| Red vial para carro (Medellín, Bello, Itagüí, Envigado, Sabaneta, La Estrella) con velocidad y tiempo de viaje | OpenStreetMap vía Overpass + OSMnx | ODbL | `scripts/02_osm_road_network.py` | `data/processed/road_drive.graphml` (**listo y validado**: 43.507 nodos, 95.511 aristas, 8.952 km, 99,7 % fuertemente conexo; atributos `length`, `speed_kph`, `travel_time` en tiempo libre de tráfico) |

Resultado verificado de `01_osm_transit.py`: Metro 27 estaciones, Tranvía 8, Metrocable 15, Metroplús 2.

**Huecos conocidos de OSM**: Metrocable Línea P sin paradas; Metroplús con solo 2 estaciones; el tranvía T-A trae 8 estaciones (confirmar contra el mapa oficial del Metro si el modelo lo necesita).

## 2. Reglas para el corpus RAG (documentos ya redactados en `corpus_rag/`)

### Pico y placa Medellín, segundo semestre 2026 — *fuente primaria verificada*
- Alcaldía de Medellín, Secretaría de Movilidad, publicado 24-jul-2026: https://www.medellin.gov.co/es/sala-de-prensa/noticias/la-nueva-rotacion-del-pico-y-placa-en-medellin-comenzara-a-regir-a-partir-del-lunes-3-de-agosto/
- Vigente desde el lunes 3-ago-2026, lunes a viernes 5:00 a. m.–8:00 p. m.
- Carros (incluye camperos, motocarros, cuatrimotos): último dígito de la placa. Motos: primer dígito.
- Exentos: eléctricos de cero emisiones, vehículos a gas, híbridos registrados en el RUNT.
- Sanción pedagógica 3–6 ago; desde el 10-ago comparendo de 15 SMDLV y posible inmovilización.
- Vías exentas: las mismas de 2025-2 (acceso Terminal del Norte, calle 78, carrera 64C, calle 88, Autopista Sur en Itagüí).
- Taxis: rotación quincenal aparte.
- **Rotación por dígitos** (la página oficial la trae en imagen; coincide en que el lunes inicia con 5 y 8): Lun 5-8 · Mar 1-4 · Mié 0-2 · Jue 3-6 · Vie 7-9. **Confirmada con tabla idéntica en dos medios** (Noticias Caracol, El Espectador); falta contrastarla con la imagen oficial.
- **Vías exentas**: las listas de la Alcaldía y de la prensa difieren (ver `corpus_rag/01_*`); multa reportada $633.232 (El Tiempo).

### Tarifas Metro/SITVA 2026 — *prensa (dos medios coinciden: Publimetro y El Tiempo); falta el acuerdo metropolitano*
- Fija el Área Metropolitana del Valle de Aburrá; vigentes desde el 10-ene-2026, ajuste promedio ~12 %.
- Cívica personalizada (frecuente) **$3.820** (antes $3.430); portador/eventual **$4.400**; estudiantes municipales $1.600; adulto mayor $3.330; discapacidad $2.720.
- Fuentes: Publimetro (9-ene-2026), El Tiempo, Noticias Caracol, El Nuevo Siglo.
- **Sin confirmar**: reglas y ventana de tiempo de la integración tarifaria (transbordo).
- Las tarjetas Cívica Classic dejaron de operar el 1-jul-2026 (una sola fuente).

### Documentos oficiales del Metro de Medellín — *fuente primaria verificada (PDF en `data/raw/pdfs/`)*
- Resolución 263 de 2019, Reglamento del Usuario (medios de pago, integración, mascotas, bicicletas): https://www.metrodemedellin.gov.co/hubfs/reglamento-del-usuario-11052019-1.pdf  → `corpus_rag/03_*` y `04_*`
- Condiciones de uso funcionalidad Bici (horarios por línea; sin fecha en el documento): https://www.metrodemedellin.gov.co/hubfs/condiciones-de-uso-funcionalidad-bici.pdf → `corpus_rag/03_*`
- Dato clave: el reglamento **no fija** el tiempo de integración (lo define la autoridad de transporte) y la Cívica Eventual **no** permite integración.

### Factores de emisión — *solo espejo de terceros, sin factor colombiano oficial*
- No se halló tabla colombiana por pasajero-km (UPME FECOC+ cubre combustibles/vehículos pesados).
- Datos del conjunto UK GHG Conversion Factors 2024 vistos vía Climatiq (espejo, no el archivo oficial): bus local 0,03174 kgCO2e/pasajero-km; Metro de Londres 0,0278 kgCO2e/pasajero-km; carro gasolina promedio 0,1645 kgCO2e/vehículo-km (requiere supuesto de ocupación). Sin cifra para tranvía ni cable.
- **Uso recomendado:** supuestos declarados explícitamente en el informe como aproximación (el Metro de Medellín es eléctrico, otro mix energético). Oficial: https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2024
- Huella propia del Metro de Medellín en 2024: 6.243 tCO2e (no es un factor por pasajero).

## 3. No accesible / no encontrado (plan B necesario)

- `datosabiertos.metropol.gov.co` (AMVA): HTTP 502 al consultarlo. Allí está la Encuesta Origen-Destino 2017 (hogares, viajes, moradores). **Reintentar.**
- Servidor de mapas de la Alcaldía (`medellin.gov.co/servidormapas`): 403 a clientes programáticos; no se evadió.
- Espejo TUMI (`hub.tumidata.org`): conexión rechazada.
- `datos.gov.co`: sin datasets útiles de movilidad de Medellín (solo Copacabana; el de tarifas del AMVA es de 2021).
- **Factores de emisión oficiales colombianos por modo**: no encontrados (ver sección 2, supuestos con factores UK).
- Tiempos/tráfico en tiempo real: no hay fuente abierta; usar tiempos simulados por hora (plan B del enunciado).

### Datos derivados (generados en este proyecto)
- `data/processed/speed_factors*.csv`: factores 0,44 (promedio día) y 0,338 (hora pico), calibrados con `scripts/03_calibrate_speed_factors.py` contra TomTom Traffic Index 2025 (20,7 y 15,9 km/h, reportados por prensa). La asignación de horas a periodos es un supuesto.
- `data/processed/emission_factors.csv`: cada fila marca si es CITADO, DERIVADO, ANALOGIA o SUPUESTO.
- `data/processed/intermodal_transfers.csv`: transbordos por coincidencia de nombre entre modos (Acevedo, Oriente, San Antonio, San Javier; 40-72 m).

## 4. Pendiente (no bloquea al equipo de modelado)

1. Obtener el acuerdo metropolitano de tarifas 2026 y confirmar las cifras.
2. Contrastar la rotación de dígitos con la imagen oficial de la Alcaldía.
3. Encuesta Origen-Destino 2017 (`datosabiertos.metropol.gov.co`): el portal devolvía 502 en todos los intentos; es opcional para el MVP.
4. Frecuencias y horarios oficiales del Metro: no se encontraron fuentes oficiales verificables; el agente no debe afirmarlos.
5. Factor de emisión colombiano oficial por pasajero-km (UPME u otro), si aparece.
