# Guía de Validaciones y Diagnóstico

Esta guía documenta el módulo `diagnostico/` y los artefactos que produce. Es la referencia para entender qué se mide en cada corrida, cómo leerlo y cómo agregar nuevos checks.

## 1. Propósito

El módulo de diagnóstico es un sistema de **sanity checks**, no de tests pass/fail. Cada métrica lleva un estado informativo:

- `ok` — el valor cae dentro de una banda esperada (configurada vía `cfg.target_*` o `cfg.pesos_*`).
- `watch` — el valor está fuera de la banda. No implica error; implica revisar.
- `info` — la métrica no tiene banda de referencia. Se reporta para que el usuario tenga visibilidad.

El sistema NO interrumpe la corrida si algo está fuera de banda. La idea es ofrecer un panorama después de cada generación para responder preguntas como: ¿cómo se movió el loss ratio cuando subí la inflación?, ¿la concentración de productores sigue siendo razonable después de bajar el exponente de la power-law?, ¿quedó alguna distribución desviada después de cambiar pesos en `config.py`?

Los 13 checks de integridad referencial (fechas coherentes, claves foráneas, montos no negativos, etc.) sí son booleanos estrictos y aparecen como ✓ / ✗ en el reporte.

## 2. Qué se genera tras cada corrida

Después de cada `python main.py`, en `output/diagnostico/` se escriben dos archivos:

- `snapshot_<YYYYMMDD-HHMMSS>_seed<N>.json` — snapshot estructurado machine-readable.
- `snapshot_<YYYYMMDD-HHMMSS>_seed<N>.md` — reporte Markdown legible. Si existía una corrida anterior, incluye una sección "Comparación vs corrida anterior".

**Política de rotación: se mantienen como máximo 2 pares en disco** (la corrida actual y la inmediata anterior). La tercera corrida borra la más vieja antes de escribir. Si necesitás conservar una corrida puntual, copiala manualmente fuera del directorio.

### config_hash

Cada snapshot incluye un `config_hash` de 16 caracteres, derivado de `dataclasses.asdict(cfg)` con sha256. Excluye campos de ejecución (`random_seed`, `cantidad_polizas`) para que dos corridas con los mismos parámetros estructurales y distinta seed compartan hash. Sirve para detectar de un vistazo si el delta entre dos corridas corresponde a un cambio de seed (ruido) o a un cambio de parámetros (señal).

En la sección de comparación del Markdown se muestra como `Mismo config hash: sí/no`.

## 3. Estructura del snapshot

El JSON tiene 8 bloques top-level:

- **meta** — timestamp ISO, seed, `config_hash`, n_polizas, n_siniestros, sub-bloque `calibracion` (convergió, iteraciones, scales finales).
- **parametros_clave** — subconjunto de `cfg` con los valores que más mueven el resultado: `n_productores`, `n_organizadores`, `inflacion_anual`, `target_loss`, `target_freq`, `lambda_scale_inicial`, `severidad_scale_inicial`, `tasa_cancelacion_base`, `bonus_malus_p_sin_claim`, etc.
- **integridad** — `checks` (dict con los 13 booleanos) + `todos_ok`.
- **cartera, suscripcion, siniestralidad, cohortes, productores** — las cinco áreas funcionales.

Dentro de cada área hay dos tipos de items:

- **Métrica escalar**: `{"valor": ..., "banda": [lo, hi] | null, "status": "ok|watch|info", "nota": "..."}`.
- **Tabla**: `{"tipo": "distribucion|magnitud", "valores": {label: numero}, "esperado_config": {label: share} | null, "desvio_max": ... | null, "status": ..., "nota": "..."}`. Las distribuciones son shares que suman ≈ 1; las magnitudes son números arbitrarios (por ejemplo, prima media por zona).

## 4. Catálogo de checks por área

### 4.1 `integridad` (13 booleanos)

Validan invariantes que **deben** cumplirse siempre. Si alguno aparece como ✗, hay un bug en el generador.

- `id_poliza_referencial` — todos los siniestros referencian una póliza existente.
- `fecha_siniestro_en_vigencia` — `fecha_inicio_vigencia ≤ fecha_siniestro ≤ fecha_fin_vigencia`.
- `fecha_denuncia_valida` — `fecha_denuncia ≥ fecha_siniestro`.
- `fecha_inicio_juicio_valida` — `fecha_inicio_juicio ≥ fecha_denuncia` cuando aplica.
- `cobertura_casco_coherente` — `cobertura_casco=True` solo en planes Terceros Completo / Todo Riesgo.
- `bien_recuperado_coherente` — `bien_recuperado` no nulo solo en Robo total / Robo parcial.
- `cadena_legal_coherente` — `con_sentencia ⇒ en_juicio ⇒ en_mediacion`.
- `primas_y_suma_positivas` — `prima > 0` y `suma_asegurada > 0` para toda póliza.
- `estado_siniestro_coherente` — `estado_siniestro ∈ {Cerrado, Abierto, Rechazado}`.
- `motivo_rechazo_coherente` — Rechazado ⇔ tiene motivo_rechazo no nulo.
- `montos_financieros_coherentes` — Rechazado ⇒ `monto_pagado = 0`; reservas y pagos ≥ 0.
- `cancelacion_coherente` — Cancelada ⇒ tiene fecha + no renovada.
- `zona_riesgo_valida` — `zona_riesgo` pertenece al conjunto de 7 zonas definidas.
- `cadena_renovacion_coherente` — todo cliente arranca en `numero_renovacion = 0`.

### 4.2 `cartera`

Distribuciones de composición. Cada una se compara contra el `cfg.pesos_*` correspondiente cuando existe, usando `cfg.tolerancia_distribucion` (default 0.02).

- `distribucion_provincia` — banda: `cfg.pesos_provincia`.
- `distribucion_zona` — sin banda (las zonas se derivan de provincia/localidad).
- `distribucion_canal` — banda: `cfg.pesos_canal`.
- `distribucion_cobertura` — banda: `cfg.pesos_cobertura`.
- `distribucion_tipo_vehiculo` — banda: `cfg.pesos_tipo_vehiculo`.
- `distribucion_ocupacion` — banda: `cfg.pesos_ocupacion`.
- `distribucion_medio_pago` — banda: `cfg.pesos_medio_pago`.
- `distribucion_combustible` — sin banda (depende del tipo de vehículo).
- `distribucion_franquicia` — banda: `cfg.pesos_franquicia` (solo aplica a planes con casco).
- `distribucion_rastreador` — sin banda (depende de la zona).

**Cómo interpretar:** un `desvio_max` alto en `distribucion_canal` después de cambiar el peso de un canal en config es esperable. El mismo desvío sin que hayas tocado el peso indica revisar el muestreo en `generadores/polizas.py`.

### 4.3 `suscripcion`

Prima media y dispersión, magnitudes por segmento.

- `prima_media`, `prima_p50`, `prima_p90`, `prima_p99` — escalares en ARS.
- `premio_medio` — prima + recargos/impuestos.
- `prima_media_por_cobertura`, `prima_media_por_zona`, `prima_media_por_tipo_vehiculo` — tablas de magnitudes.
- `mix_cuotas` — share por cantidad de cuotas (1, 3, 6, 12).
- `share_rastreador_por_zona` — proporción con rastreador por zona.

**Cómo interpretar:** las primas dependen de inflación, factores de zona, franquicia, rastreador y bonus-malus. Si subiste un factor de zona, esperá ver subir la prima media en esa zona.

### 4.4 `siniestralidad`

Núcleo del análisis técnico.

- `loss_ratio` — reclamado / primas. Banda: `cfg.target_loss` (default 0.60–0.80).
- `loss_ratio_pagado` — pagado / primas (siempre menor por rechazos y reservas abiertas).
- `expense_ratio` — gasto_liquidacion / primas.
- `combined_ratio` — loss_ratio_pagado + expense_ratio.
- `frecuencia_siniestral` — % pólizas con al menos un siniestro. Banda: `cfg.target_freq`.
- `severidad_promedio` — monto reclamado promedio por siniestro.
- `severidad_por_tipo_dano` — tabla de magnitudes por tipo (Robo total, Choque, etc.).
- `loss_ratio_por_zona`, `loss_ratio_por_cobertura`, `loss_ratio_por_banda_calidad_productor` — tablas para cruzar dimensiones.
- `lag_denuncia_p50`, `lag_denuncia_p90` — días entre siniestro y denuncia.
- `tasa_rechazo` — proporción de siniestros rechazados.
- `distribucion_motivos_rechazo` — share por motivo. Banda: `cfg.pesos_motivo_rechazo`.
- `distribucion_estado_siniestro` — share Cerrado/Abierto/Rechazado. Banda: `cfg.prob_estado_siniestro`.

**Cómo interpretar:** el loss ratio se mueve con la inflación (porque arrastra severidad). El loop de calibración compensa ajustando `severidad_scale`, pero si dejás un valor de `severidad_scale_inicial` muy lejos del óptimo, la calibración puede agotar las iteraciones. Si ves "no convergió completamente" en la consola, mirá `severidad_scale_final` en el snapshot y usalo como nuevo `severidad_scale_inicial` en `config.py`.

### 4.5 `cohortes`

Comportamiento longitudinal de los clientes.

- `n_clientes_unicos` — total de clientes distintos en la cartera.
- `distribucion_periodos_cliente` — share por cantidad de períodos. Banda: `cfg.pesos_periodos_cliente`.
- `tasa_renovacion` — proporción de pólizas marcadas como renovadas.
- `tasa_cancelacion` — proporción de pólizas canceladas mid-term (referencia: `cfg.tasa_cancelacion_base`).
- `distribucion_bonus_malus` — share por nivel (0 = mejor, 5 = peor).
- `retencion_por_bonus_malus` — tasa de renovación por nivel.

**Cómo interpretar:** la retención debería ser menor en niveles altos de bonus-malus (clientes con más siniestros). Si no se ve esa pendiente, revisar `ajustar_renovada_por_siniestros` en `generadores/cohortes.py`.

### 4.6 `productores`

Concentración y calidad de la fuerza de ventas.

- `n_productores_activos` — productores con ≥ 1 póliza.
- `top1_share`, `top5_share`, `top10_share` — share acumulado.
- `herfindahl_hhi` — índice de concentración (Σ share²). En cartera mediana esperar valores bajos (orden de 0.03–0.06).
- `distribucion_calidad_productor` — share por banda (estrella < 0.85, neutral 0.85–1.15, tóxico > 1.15).
- `factor_calidad_promedio`, `factor_calidad_std` — referencia: media teórica = 1.0, std configurado en `cfg.factor_calidad_productor_sigma`.
- `loss_ratio_por_banda_calidad` — debería mostrar gradiente: estrella < neutral < tóxico.

**Cómo interpretar:** si bajás `cfg.productor_power_law_exponente`, esperá que `top1_share` y `top5_share` caigan (cartera más uniforme). El HHI también debería bajar.

## 5. Cómo leer el Markdown

Orden recomendado de lectura:

1. **Cabecera** — primero verificá que la calibración convergió. Si dice "no" o ves iteraciones = `cfg.max_iteraciones_calibracion`, el loop agotó intentos y los scales finales pueden no estar cerca del óptimo.
2. **Métricas generales** — chequeá la columna `status`. Cualquier ⚠ es señal de mirar más abajo. Las dos métricas que más importan son `loss_ratio` y `frecuencia_siniestral`; ambas tienen banda explícita en config.
3. **Integridad** — si algún check está ✗, hay un bug en el generador. No es responsabilidad del que tunea config.
4. **Comparación vs corrida anterior** (si existe) — leé el bloque de metadata primero. Si `mismo_config_hash = no`, los deltas son explicables por el cambio de parámetros; si `sí`, los deltas son ruido de seed.
5. Tabla **Escalares (top 25 por magnitud de delta)** — sirve para identificar qué se movió más en términos relativos.
6. Bloque **Top movers por tabla** — para ver qué categorías específicas se desplazaron en cada distribución.

### Señales típicas

- `loss_ratio` en watch + `frecuencia` en ok → ajustar `severidad_scale_inicial`.
- `frecuencia` en watch + `loss_ratio` en ok → ajustar `lambda_scale_inicial`.
- Calibración no convergió → bajar la magnitud del cambio o subir `max_iteraciones_calibracion`.
- HHI en 0.15+ con n_productores grande → revisar exponente de power-law (demasiado alto).
- Loss ratio por banda de calidad sin gradiente → revisar `factor_calidad_productor_sigma`.

## 6. Flujo recomendado para tunear parámetros

1. Hacer una corrida baseline. Mirar el Markdown.
2. Cambiar **un solo parámetro** en `config.py`.
3. Volver a correr.
4. Abrir el Markdown nuevo. Ir directo a "Comparación vs corrida anterior".
5. Verificar:
   - `mismo_config_hash = no` (cambió la config).
   - El delta material aparece en la métrica esperada (si subiste inflación, esperá movimiento en severidad / loss ratio / prima media).
   - Ningún check de integridad pasó a ✗.
   - Ninguna distribución no relacionada se desvió.
6. Si el resultado es el esperado, ese parámetro queda fijo y se sigue con el próximo.

Cambiar varios parámetros a la vez complica atribuir el delta a cada uno. Una corrida es barata; vale la pena ir de a uno.

## 7. Cómo agregar un check nuevo

El paquete `diagnostico/` está organizado por área. Cada área expone una sola función pública:

```
construir(df_polizas, df_siniestros, cfg) -> dict
```

que devuelve el sub-árbol completo de esa área para el snapshot. Para agregar un check:

1. Decidir a qué área corresponde (cartera / suscripcion / siniestralidad / cohortes / productores). Si no encaja, crear un módulo nuevo y registrarlo en `runner.build_snapshot`.
2. Calcular el valor usando los DataFrames existentes.
3. Envolverlo con uno de los helpers de `diagnostico/schema.py`:
   - `crear_metrica(valor, banda=None, status=None, nota="")` para escalares.
   - `crear_distribucion(valores, esperado_config=None, tolerancia=..., nota="")` para distribuciones (shares).
   - `crear_tabla(valores, nota="")` para magnitudes por categoría.
4. Agregarlo al dict de salida con una clave descriptiva.

No hace falta tocar `runner.py`, `markdown.py` ni `diff.py`: el reporte Markdown itera sobre las métricas conocidas y muestra el resto automáticamente cuando aplican los heurísticos genéricos (por ejemplo, la sección "Comparación vs corrida anterior" detecta cualquier escalar nuevo por la presencia de la clave `valor`).

Si el check nuevo requiere una sección destacada en el Markdown, agregar una función `_sec_*` en `diagnostico/markdown.py` y llamarla desde `render_markdown`.
