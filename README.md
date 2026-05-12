# Generate Insurance Data

Herramienta en Python que genera datasets sintéticos realistas para **carteras de seguros automotor argentinas**. Produce dos archivos CSV vinculados — pólizas y siniestros — con distribuciones estadísticamente coherentes, loss ratios calibrados y estructuras fieles al dominio, listos para EDA, machine learning o análisis actuarial.

---

## Qué genera

### `polizas_sinteticas.csv` — Tabla de pólizas (42 columnas)
Cada fila es una póliza de seguro. Campos principales:

| Columna | Descripción |
|---|---|
| `id_poliza`, `numero_poliza` | Identificadores únicos |
| `ramo` | Ramo regulatorio: `Automotor` o `Motovehiculos` |
| `plan_cobertura` | Plan de cobertura: Responsabilidad Civil / Terceros Completo / Todo Riesgo |
| `categoria_cobertura` | Categoría legible (Solo RC / RC + Casco Básico / RC + Casco Total) |
| `tipo_vehiculo` | Auto / Moto / Camioneta / Utilitario |
| `marca_vehiculo`, `modelo_vehiculo`, `anio_vehiculo` | Datos del vehículo (~185 modelos, 39 marcas, con segmento premium representado) |
| `tipo_combustible` | Nafta / Diésel / GNC / Híbrido / Eléctrico (distribución dependiente de `tipo_vehiculo`) |
| `suma_asegurada`, `prima`, `premio` | Valores en ARS |
| `franquicia` | Deducible como fracción de la suma asegurada (0 / 0.05 / 0.20) — solo planes con casco |
| `tiene_rastreador` | Flag Lojack/Ituran — reduce probabilidad de robo total y baja la prima |
| `provincia`, `localidad`, `barrio` | 20 provincias argentinas, 200+ localidades |
| `zona_riesgo` | 7 niveles: CABA Premium / CABA Resto / GBA Norte / GBA Sur/Oeste / Media-Alta / Media / Baja (derivado de la geografía) |
| `edad_asegurado` | Distribución bimodal (picos en ~27 y ~46 años) |
| `antiguedad_carnet_anios` | Años desde la licencia de conducir; correlacionado con edad pero no idéntico |
| `genero_asegurado`, `estado_civil`, `ocupacion` | Demografía del asegurado |
| `medio_pago` | 6 categorías: Tarjeta de crédito / Tarjeta de débito / Débito automático CBU / Billetera virtual / Transferencia / Efectivo |
| `cantidad_cuotas` | 1 / 3 / 6 / 12 (solo medios con financiación admiten > 1) |
| `canal_venta` | Productor / Broker / Organizador / Directa / Online |
| `codigo_productor`, `codigo_organizador` | 120 productores, 25 organizadores (típico de compañía mediana argentina) |
| `factor_calidad_productor` | Factor N(1.0, 0.15) por productor — multiplica la frecuencia de siniestros. Permite identificar productores tóxicos vs estrella |
| `tiempo_productor_cia_meses` | Antigüedad del productor en la compañía |
| `nivel_bonus_malus` | Escala 0–5; random walk sobre renovaciones (0 = máx. descuento, 5 = máx. recargo) |
| `comision_pactada` | Comisión acordada por canal/productor |
| `es_flota` | True para ~2% de las pólizas (vehículos de flota → fuerza uso Comercial) |
| `tipo_uso` | Particular / Comercial / Profesional |
| `id_cliente`, `numero_renovacion` | Identidad del cliente a lo largo de la cadena de renovaciones |
| `renovada` | Indica si la póliza fue renovada |
| `cancelada`, `fecha_cancelacion`, `motivo_cancelacion` | Detalles de cancelación mid-term |
| `meses_en_mora` | Bucket de morosidad |
| `fecha_inicio_vigencia`, `fecha_fin_vigencia` | Vigencia anual de la póliza |

### `siniestros_sinteticos.csv` — Tabla de siniestros (24 columnas)
Cada fila es un siniestro vinculado a una póliza. Campos principales:

| Columna | Descripción |
|---|---|
| `id_siniestro`, `numero_siniestro` | Identificadores únicos |
| `id_poliza` | Foreign key a la tabla de pólizas |
| `tipo_danio` | 11 tipos: Robo total / Robo parcial / Choque / Incendio / Granizo / Cristales / Vandalismo / Inundación / Daño a terceros / Daño a terceros con lesiones / Otros |
| `estado_siniestro` | Cerrado / Abierto / Rechazado |
| `monto_reclamado` | Monto del siniestro en ARS (log-normal, ajustado por inflación según año) |
| `monto_reservado`, `monto_pagado` | Reserva inicial y pago efectivo (la franquicia se descuenta del pagado en siniestros de casco) |
| `gasto_liquidacion` | Gastos de liquidación (mayores en siniestros con juicio/mediación) |
| `motivo_rechazo` | Para siniestros rechazados — 8 motivos (Falta de cobertura, Mora, Exclusión, Documentación, Fraude presunto, Alcoholemia positiva, Conductor no habilitado, Denuncia tardía) |
| `categoria_siniestro` | Casco / RC / Mixto |
| `fecha_siniestro`, `fecha_denuncia`, `fecha_inicio_juicio` | Fechas con lags realistas |
| `en_mediacion`, `en_juicio`, `con_sentencia` | Flags de cadena legal (cascada coherente) |
| `cobertura_casco`, `cobertura_rc` | Aplicabilidad de cobertura por siniestro |
| `terceros_involucrados`, `conductor_es_asegurado` | Flags contextuales |
| `bien_recuperado` | Solo para siniestros de robo |
| `ubicacion_siniestro` | Provincia donde ocurrió (90% coincide con la de la póliza, 10% en otra) |

---

## Características de diseño

- **Calibración automática**: un loop ajusta frecuencia y severidad hasta que la cartera cae dentro de bandas configurables (default: frecuencia 15–20%, loss ratio 60–80%).
- **Cadenas de renovación**: las pólizas se agrupan en cohortes (`id_cliente`) con demografía propagada y primas ajustadas por inflación a lo largo de las renovaciones.
- **Cancelaciones mid-term**: ~7% de las pólizas se cancelan antes del vencimiento, con motivos contextuales (mora, venta del vehículo, cambio de compañía, voluntaria).
- **Ramo motovehículos**: las motos se asignan al ramo `Motovehiculos` con distribución de daños propia, severidad y uplift de frecuencia (×1.7).
- **Estados financieros del siniestro**: cada siniestro tiene un estado (Cerrado/Abierto/Rechazado) consistente con reserva, pago, gasto y motivo de rechazo.
- **Estacionalidad de siniestros**: cada tipo de daño tiene patrones mensuales (ej. Granizo pico Oct–Mar, Robo pico Dic–Feb, Inundación pico Oct–Mar).
- **Lag desde inicio de póliza**: las fechas de siniestro siguen una mezcla de 4 regímenes (1% extremo 0–7d, 4% temprano 8–30d, 10% adaptación 31–90d, 85% normal). La concentración temprana es señal de fraude.
- **Inflación anual**: los montos crecen año a año siguiendo el IPC argentino (2021 baseline → 2022 ×1.9 → 2023 ×5.5 → 2024 ×12.0).
- **Tres efectos independientes de la zona**: la zona afecta prima (`factor_prima_por_zona`), frecuencia (`factor_frecuencia_por_zona`) y severidad (`factor_severidad_por_zona`) por separado — modelado actuarial estándar.
- **Bonus-malus**: random walk sobre renovaciones. Clientes sin siniestros bajan de nivel (descuento); con siniestros suben (recargo). Cierra el loop renovación → precio futuro.
- **Rastreador, franquicia, antigüedad de carnet**: variables adicionales que afectan prima y/o probabilidad de tipos de siniestro específicos.
- **Calidad de productor**: factor único por productor ~ N(1.0, 0.15) que escala la frecuencia. Habilita análisis de cartera por productor (tóxicos vs estrella).
- **Cadena legal coherente**: `con_sentencia` implica `en_juicio` implica `en_mediacion`, siempre.
- **Validaciones de integridad**: 14 chequeos automáticos después de la generación (fechas, lógica de cobertura, integridad referencial, cadena legal, montos, cancelaciones, etc.).

---

## Instalación

Requiere [uv](https://docs.astral.sh/uv/) (gestor de paquetes Python).

```bash
# 1. Clonar el repositorio
git clone <repo-url>
cd generate-insurance-data

# 2. Crear entorno virtual e instalar dependencias
uv sync
```

Sin necesidad de `pip install` ni crear `venv` manualmente.

---

## Uso

### Corrida default — 100 000 pólizas, seed 42
```bash
uv run python main.py
```

### Parámetros custom
```bash
# 10 000 pólizas con otra seed, salida en directorio custom
uv run python main.py --n-polizas 10000 --seed 7 --output-dir data/
```

| Argumento | Default | Descripción |
|---|---|---|
| `--n-polizas` | `100000` | Cantidad de pólizas a generar |
| `--seed` | `42` | Seed reproducible |
| `--output-dir` | `output/` | Directorio de salida CSV |

El script imprime un log de calibración y un reporte de validación en cada corrida:

```
Iteración 01 | frecuencia=0.1188 | loss_ratio=1.1033 | lambda_scale=0.8800 | severidad_scale=0.3500
...
Iteración 09 | frecuencia=0.1614 | loss_ratio=0.7552 | lambda_scale=1.2363 | severidad_scale=0.1507
Calibración convergida. Iteración=9, lambda_scale=1.2363, severidad_scale=0.1507

=== REPORTE DE VALIDACION ===
[Integridad y coherencia]
- id_poliza_referencial: PASS
- fecha_siniestro_en_vigencia: PASS
...
- Loss ratio global (reclamado): 75.52% | Objetivo: 60% - 80% | PASS
- Frecuencia siniestral: 16.14% | Objetivo: 15% - 20% | PASS
```

### Customizar distribuciones
Todos los parámetros estadísticos viven en `config.py`. No hace falta tocar código — basta con editar valores. Ver `CONFIG_GUIDE.md` para una explicación de cada parámetro y su efecto sobre los datos.

---

## Análisis exploratorio

Se incluye un notebook EDA con 11 secciones que cubren composición de cartera, loss ratio por segmento, heatmaps, análisis de red de productores, desglose por tipo de vehículo, estacionalidad y detección de outliers.

```bash
uv run jupyter lab
# Abrir: analisis_eda_cartera_completo_v2.ipynb
```

> Correr `main.py` primero para generar los CSVs antes de abrir el notebook.

Ver también `analisis_recomendaciones.md` para una guía completa de KPIs, gráficos sugeridos por slide y análisis avanzados (modelado predictivo, segmentación, detección de fraude).

---

## Estructura del proyecto

```
.
├── main.py                                    # Entry point y loop de calibración
├── config.py                                  # Todos los parámetros (distribuciones, targets, geografía)
├── validaciones.py                            # Chequeos de integridad y métricas
├── generadores/
│   ├── sampling.py                            # Helpers de muestreo (weighted, edad, fechas, antig. carnet)
│   ├── geografia.py                           # Asignación de provincia/localidad/barrio/zona
│   ├── tarifa.py                              # Cálculo de prima/premio y factores de tarificación
│   ├── mora_cancelacion.py                    # Lógica de mora y cancelaciones mid-term
│   ├── cohortes.py                            # Cadenas de renovación, bonus-malus, propagación
│   ├── vehiculos.py                           # Catálogo de vehículos (185 modelos, 39 marcas)
│   ├── polizas.py                             # Orquestador de generación de pólizas
│   └── siniestros.py                          # Generador de siniestros
├── analisis_eda_cartera_completo_v2.ipynb     # Notebook EDA
├── CONFIG_GUIDE.md                            # Referencia de parámetros y guía de tuning
├── analisis_recomendaciones.md                # Guía de KPIs y análisis para presentaciones
├── pyproject.toml                             # Dependencias (gestionadas por uv)
└── output/                                    # CSVs generados (git-ignored)
```

---

## Requisitos

- Python 3.12+
- uv 0.4+

Dependencias (gestionadas automáticamente por `uv sync`): `pandas`, `numpy`, `matplotlib`, `seaborn`, `scipy`, `jupyterlab`.

---

## Notas de calibración

El sistema usa **inflación realista** alineada con el IPC argentino reciente (factores 1.0/1.9/5.5/12.0 para 2021-2024). Esto produce montos absolutos coherentes con la realidad — un siniestro promedio en 2024 ronda los 5–6 millones de pesos. Si se cambia la inflación a valores más bajos (o se extiende a 2025+), ajustar `severidad_scale_inicial` en `config.py` para que la calibración converja en las 15 iteraciones máximas.

La concentración de productores está calibrada para una compañía mediana argentina: 120 productores activos, top productor con ~15% del volumen, top 5 con ~36%. Para simular un mercado más fragmentado, subir `n_productores` y bajar `productor_power_law_exponente`.
