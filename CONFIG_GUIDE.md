# Guía de parámetros — `config.py`

Referencia completa de cada parámetro de `Config`. Para cada uno se explica qué controla, qué pasa en los datos si se lo modifica, y qué restricciones hay que respetar.

---

## 1. Parámetros globales de generación

### `random_seed` (default: `42`)
Semilla del generador de números aleatorios. Cambiarla produce un dataset completamente distinto pero estadísticamente equivalente. Útil para generar múltiples versiones independientes del dataset. No afecta las distribuciones, solo el resultado puntual de cada sorteo.

### `cantidad_polizas` (default: `50_000`)
Número total de pólizas a generar. El número de siniestros escala aproximadamente proporcional (con la frecuencia target de 15–20%). A mayor cantidad, más estables son las distribuciones marginales y los LR por segmento. Con menos de 5 000 pólizas, segmentos pequeños (Utilitario, Formosa) pueden quedar con muy pocas observaciones.

### `fecha_inicio` / `fecha_fin` (default: `2021-01-01` / `2024-12-31`)
Ventana temporal de vigencia de pólizas. Las fechas de inicio se distribuyen uniformemente entre estos extremos (con pesos mensuales). Cambiar este rango afecta:
- El número de años en `inflacion_anual` que se aplican a los montos.
- La dispersión temporal del dataset: un rango mayor produce más varianza en `fecha_siniestro`.

### `ramo_principal` / `ramo_motovehiculos` (defaults: `"Automotor"` / `"Motovehiculos"`)
Etiquetas del campo `ramo` en el CSV. Son strings puramente descriptivos; cambiarlos solo renombra el campo. La asignación real depende del `tipo_vehiculo` (Moto → `ramo_motovehiculos`, todo lo demás → `ramo_principal`).

---

## 2. Calibración automática de frecuencia y loss ratio

El generador corre un loop que ajusta `lambda_scale` y `severidad_scale` hasta que la cartera completa quede dentro de las bandas definidas aquí.

### `target_freq` (default: `(0.15, 0.20)`)
Rango aceptable de **frecuencia de siniestros** de la cartera: `n_siniestros / n_polizas`. Con el default, entre el 15% y el 20% de las pólizas tendrá al menos un siniestro.
- Subir ambos valores → más siniestros por cartera → mayor presión sobre el loss ratio.
- Achicar el rango (ej. `(0.17, 0.18)`) → calibración más exigente, puede necesitar más iteraciones.

### `target_loss` (default: `(0.60, 0.80)`)
Rango aceptable de **loss ratio** de la cartera: `sum(monto_reclamado) / sum(prima)`. Con el default, el LR global queda entre 60% y 80%.
- Subir el rango (ej. `(0.80, 1.00)`) → la calibración inflará los montos o la frecuencia → más siniestralidad.
- Bajar el rango → cartera más "rentable", montos menores relativos a la prima.

### `tolerancia_distribucion` (default: `0.02`)
Tolerancia absoluta al evaluar si los targets se cumplen. Con `0.02`, la frecuencia se acepta si cae en `[target_freq[0] - 0.02, target_freq[1] + 0.02]`. Aumentarla acelera la convergencia pero hace el dataset menos preciso en sus targets.

### `max_iteraciones_calibracion` (default: `12`)
Número máximo de intentos del loop de calibración. Si se agota sin converger, el generador usa los mejores scales encontrados hasta ese punto y avisa por consola. Aumentarlo ayuda cuando los targets son muy estrechos.

### `lambda_scale_inicial` (default: `0.88`)
Punto de partida del multiplicador de frecuencia para el loop de calibración. Está en `0.88` (por debajo de 1) para compensar el uplift de frecuencia que introducen las motos (lambda ×1.7). Si se elimina el ramo Motovehiculos o se reduce mucho `pesos_tipo_vehiculo["Moto"]`, conviene subir este valor a `~0.95` para que el loop converja más rápido.

### `severidad_scale_inicial` (default: `1.0`)
Punto de partida del multiplicador de montos. En general no necesita ajustarse a menos que se modifiquen drásticamente los parámetros de `severidad_lognormal`.

---

## 3. Red de distribución

### `n_productores` (default: `1000`)
Número de productores únicos en el campo `codigo_productor`. Los productores se distribuyen con una ley de potencia (rango `1.15`), por lo que unos pocos concentran mucho volumen. Aumentar este valor → más diversidad de productores, menor concentración. Disminuirlo → más concentración, útil para simular mercados oligopólicos.

### `n_organizadores` (default: `50`)
Número de grupos organizadores (`ORG-01` a `ORG-50`). Cada organizador agrupa en promedio `n_productores × prob_productor_en_organizador / n_organizadores ≈ 16` productores. Reducir este número aumenta la concentración por organizador.

### `prob_productor_en_organizador` (default: `0.80`)
Probabilidad de que un productor pertenezca a algún organizador. El 80% de los productores quedan asignados a un `ORG-xx`; el 20% restante tiene `codigo_organizador = NaN`. Bajar este valor → más productores independientes en el dataset.

### `p_outlier_poliza` (default: `0.005`)
Fracción de pólizas que reciben una `suma_asegurada` extrema (2x–4x el valor calculado, sin tope). Con el default, ~250 pólizas sobre 50 000 son outliers. Estas pólizas generan primas y potencialmente siniestros muy grandes. Aumentar este valor introduce más "ruido" en la distribución de suma asegurada y complica los modelos de clustering o scoring.

---

## 4. Distribuciones de variables categóricas de póliza

Todos estos parámetros son diccionarios `{categoría: peso}`. Los pesos **no necesitan sumar 1** — el código los normaliza automáticamente. Lo que importa es la proporción relativa entre categorías.

### `pesos_tipo_vehiculo`
Mezcla de la flota asegurada. Cambiar esta distribución tiene efectos encadenados importantes:
- **Más Motos** → mayor frecuencia media de la cartera (lambda ×1.7), menores montos medios, distinto mix de `tipo_danio`. El loop de calibración compensa con un `lambda_scale` menor, pero si la proporción de motos sube mucho (ej. >30%), conviene bajar `lambda_scale_inicial`.
- **Más Camionetas** → menor frecuencia media (lambda ×0.85), montos más altos.
- **Más Utilitarios** → efecto parecido a Camionetas, con uso Comercial forzado por el flag `es_flota`.

### `pesos_cobertura`
Mix de planes de cobertura. Afecta la **prima media** (a través de `factor_cobertura_tarifa`) y la **composición de siniestros** (solo "Terceros Completo" y "Todo Riesgo" habilitan cobertura Casco).
- Más "Todo Riesgo" → prima media más alta, más siniestros con `cobertura_casco = True`, LR potencialmente más alto.
- Más "Responsabilidad Civil" → cartera más barata, todos los siniestros Casco quedan sin cobertura y no se computan como costo.

### `pesos_genero`, `pesos_estado_civil`, `pesos_ocupacion`
Variables demográficas. Actualmente son atributos descriptivos; **no entran directamente en la lógica de frecuencia ni severidad**. Cambiarlos solo modifica las proporciones de esas columnas en el CSV. Si en el futuro se quiere que, por ejemplo, "Soltero" tenga mayor frecuencia, habría que agregar lógica en `_lambda_por_segmento()`.

### `pesos_canal`
Mix de canal de venta. Afecta:
- La **comisión pactada** (rango diferente por canal).
- La **mora**: canales Online y Directa tienen una corrección negativa en la probabilidad de mora alta.
- **No afecta** frecuencia ni severidad de siniestros directamente.

### `pesos_uso`
Proporción de uso Particular / Comercial / Profesional. Uso Comercial y Profesional aplican un multiplicador ×1.15 sobre lambda en `_lambda_por_segmento()`, por lo que aumentar su peso sube la frecuencia media de la cartera. El flag `es_flota` fuerza uso Comercial en ~2% de las pólizas independientemente de este peso.

### `pesos_provincia`
Distribución geográfica. Dado que la zona de riesgo (Alta/Media/Baja) se deriva de provincia + localidad, cambiar estos pesos modifica indirectamente la mezcla de zonas:
- Más peso en CABA → más pólizas zona Alta → mayor frecuencia y severidad promedio.
- Más peso en provincias del interior → más pólizas zona Baja/Media.
- **Restricción**: las claves deben coincidir exactamente con las entradas de `localidades_por_provincia`.

---

## 5. Geografía

### `localidades_por_provincia`
Lista de localidades para cada provincia. Se samplea de forma uniforme dentro de cada provincia. Las localidades del GBA que están en `_GBA_LOCALIDADES` (en `polizas.py`) reciben zona Alta; las demás de Buenos Aires quedan como zona Media.
- Agregar localidades GBA → más pólizas zona Alta en Buenos Aires.
- Agregar localidades del interior de Buenos Aires → más zona Media.

### `barrios_caba` / `barrios_gba`
Listas de barrios para pólizas de CABA y GBA respectivamente. Son puramente descriptivos: no afectan frecuencia, severidad ni zona de riesgo. Solo enriquecen la columna `barrio` del CSV.

---

## 6. Factores de tarificación

### `factor_zona`
Rango uniforme del multiplicador de zona aplicado a la **prima** (no al siniestro):
```
prima ∝ suma_asegurada × tasa_base × factor_zona × ...
```
- Subir los rangos de zona Alta → primas más altas en CABA/GBA → mejora el LR de esos segmentos.
- Si se sube solo el factor de zona sin tocar `factor_severidad_por_zona`, el LR de zona Alta mejora.

### `factor_severidad_por_zona`
Multiplicador aplicado al **monto del siniestro** (no a la prima):
- Alta: 1.15 → los siniestros en zona Alta cuestan un 15% más.
- Media: 1.00 → sin ajuste.
- Baja: 0.85 → los siniestros en zona Baja cuestan un 15% menos.

Este parámetro controla la **variabilidad del loss ratio entre zonas**. Aumentar el spread (ej. Alta: 1.30, Baja: 0.70) produce diferencias más marcadas. Si se pone todos en 1.0, los LR por zona convergen.

### `tasa_base_rango` (default: `(0.04, 0.06)`)
Rango uniforme de la tasa técnica sobre la suma asegurada. Sube o baja la prima media de toda la cartera proporcionalmente. Subir el rango → más prima → mejor LR global (el loop de calibración puede ajustar menos agresivamente `severidad_scale`).

### `factor_cobertura_tarifa`
Multiplicador de la tasa según plan de cobertura. Define cuánto más cara es cada cobertura relativa a "Todo Riesgo" (que vale 1.0). Cambiar estos valores modifica la prima relativa entre planes pero **no** modifica la siniestralidad por plan — por lo tanto sí afecta el LR por plan de cobertura.

### `comision_por_canal`
Rangos de comisión por canal de venta `(min, max)`. Afectan únicamente la columna `comision_pactada` en el CSV. No entran en el cálculo de prima ni en la lógica de siniestros.

---

## 7. Inflación anual

### `inflacion_anual` (default: `{2021: 1.0, 2022: 1.5, 2023: 2.5, 2024: 4.0}`)
Multiplicador aplicado al **monto del siniestro** según el año de ocurrencia. Representa la inflación acumulada de costos de reparación/reposición.
- 2021 → monto base (×1.0)
- 2024 → los montos son 4× más altos en términos nominales que en 2021.

Esto introduce tendencia temporal en `monto_reclamado`: los siniestros recientes son nominalmente más caros. Si se agrega el año 2025 (ej. `2025: 6.0`), los siniestros de ese año serán aún mayores.

**Efecto en el LR**: como las primas se fijan al inicio de la vigencia y no se reajustan, años con alta inflación tienden a tener LR más alto. Esto es intencional — simula el efecto del descalce temporal real en seguros argentinos.

---

## 8. Distribuciones de siniestralidad — parámetros críticos

Estos son los parámetros con mayor impacto en las distribuciones del dataset de siniestros.

### `prob_tipo_danio_por_zona`
Distribución de probabilidad del **tipo de daño** para autos/camionetas/utilitarios, diferenciada por zona de riesgo. Los pesos se normalizan automáticamente.

| Efecto de cambio | Resultado en datos |
|---|---|
| Subir `"Robo total"` en zona Alta | Más siniestros de robo total en CABA/GBA → sube el LR de esa zona (robo total es el tipo más severo) |
| Subir `"Granizo"` | Más siniestros con estacionalidad Oct–Mar, montos medianos |
| Subir `"Choque"` | Más siniestros con terceros involucrados (60% probabilidad) → más casos en mediación/juicio |
| Subir `"Daño a terceros"` | 100% de esos siniestros involucran terceros → más mediación, mayor exposición legal |

**Restricción**: los 7 tipos de daño deben estar presentes en `prob_tipo_danio_por_zona`, `severidad_lognormal` y `_PESOS_MES_DANIO` (en `siniestros.py`). Agregar un tipo nuevo requiere actualizar los tres.

### `prob_tipo_danio_moto`
Equivalente al anterior, pero para motos (sin diferenciación por zona). Las motos tienen dominancia de Choque (45%) y Daño a terceros (18%), reflejando el perfil real de siniestralidad de motovehiculos. Cambios tienen el mismo tipo de efecto que en `prob_tipo_danio_por_zona`.

---

### `severidad_lognormal` y `severidad_lognormal_moto`

Son los parámetros más técnicos y de mayor impacto. Cada tipo de daño tiene `(mu, sigma)` de una **distribución log-normal**: el monto reclamado se genera como `exp(Normal(mu, sigma))`.

**Cómo interpretar mu y sigma:**

| Parámetro | Qué controla | Fórmula |
|---|---|---|
| `mu` | Mediana del monto (en ln-escala) | `mediana ≈ exp(mu)` |
| `sigma` | Dispersión / "cola" de la distribución | Cola derecha ∝ `exp(sigma²/2)` |

**Valores de referencia actuales (autos):**

| Tipo daño | mu | sigma | Mediana aprox. | P90 aprox. |
|---|---|---|---|---|
| Robo total | 15.5 | 0.6 | $5.5M | $12.8M |
| Incendio | 15.0 | 0.7 | $3.3M | $8.4M |
| Daño a terceros | 14.5 | 1.0 | $2.0M | $7.4M |
| Choque | 13.8 | 0.8 | $1.0M | $2.8M |
| Robo parcial | 13.5 | 0.7 | $0.7M | $1.8M |
| Granizo | 12.5 | 0.5 | $0.3M | $0.6M |
| Otros | 12.0 | 0.6 | $0.2M | $0.4M |

*(Valores en pesos; multiplicados luego por `inflacion_anual` y `factor_severidad_por_zona`)*

**Efectos de cambiar mu:**
- Subir `mu` en 0.5 → mediana del tipo ×1.65. Sube el LR de ese tipo de daño directamente.
- Bajar `mu` → montos menores, mejor resultado técnico en ese tipo.

**Efectos de cambiar sigma:**
- Subir `sigma` → mayor dispersión: más siniestros de monto bajo Y más siniestros catastróficos. La media sube aunque la mediana no cambie tanto.
- Sigma muy alto (> 1.5) → distribución con cola extremadamente pesada; muchos siniestros de monto ridículo y algunos de monto astronómico.
- Sigma muy bajo (< 0.3) → montos muy concentrados alrededor de la mediana, poco realismo.

**Relación con el loop de calibración:** si se sube `mu` en varios tipos de daño, el loop compensará bajando `severidad_scale` para mantener el LR dentro de `target_loss`. El efecto de la distribución interna (qué tipos cuestan más) sí queda reflejado en el dataset.

**Motos vs autos:** `severidad_lognormal_moto` tiene valores de `mu` entre 1.0 y 1.3 puntos menores que autos para el mismo tipo, reflejando que los vehículos son menos valiosos y los daños más acotados.

---

## 9. Otros parámetros de sinestros (en `siniestros.py`, no en config)

Estos valores no son configurables por `Config` pero vale documentarlos para referencia:

| Parámetro | Valor | Qué hace |
|---|---|---|
| `lag_denuncia` | `Exponential(5)`, máx. 30 días | Días entre siniestro y denuncia |
| `p_terceros_choque` | 0.60 | 60% de los choques involucran terceros |
| `p_mediacion_base` | 0.20 (×1.5 si hay terceros) | Probabilidad de mediación prejudicial |
| `p_juicio_base` | 0.11 (×2 si monto > P90) | Probabilidad de juicio dado mediación |
| `p_sentencia` | 0.35 | Probabilidad de sentencia dado juicio |
| `p_bien_recuperado_robo_total` | 0.20 | 20% de robos totales: bien recuperado |
| `p_bien_recuperado_robo_parcial` | 0.45 | |
| `p_extreme_tail` | 0.01 | 1% de siniestros: monto ×(2.5–5.0) |
| `lag_juicio` | `Exponential(180)` días desde denuncia | Inicio del proceso judicial |

---

## 10. Reglas de consistencia importantes

Al modificar los parámetros, respetar estas dependencias:

1. **Suma de pesos de provincia**: No es estrictamente necesario que sumen 1 (se normalizan), pero si se agregan provincias nuevas hay que agregarlas también en `localidades_por_provincia`.

2. **Tipos de daño**: Los 7 tipos (`Robo total`, `Robo parcial`, `Choque`, `Incendio`, `Granizo`, `Daño a terceros`, `Otros`) deben existir como claves en `prob_tipo_danio_por_zona`, `severidad_lognormal`, `prob_tipo_danio_moto` y `severidad_lognormal_moto`. También están hardcodeados en `_PESOS_MES_DANIO` en `siniestros.py`.

3. **GBA localities**: Las localidades de Buenos Aires que deben disparar zona Alta están en `_GBA_LOCALIDADES` (frozenset en `polizas.py`). Si se agregan localidades GBA a `localidades_por_provincia["Buenos Aires"]`, agregarlas también a ese frozenset.

4. **`inflacion_anual`**: debe tener una entrada para cada año entre `fecha_inicio.year` y `fecha_fin.year`. Si se extiende `fecha_fin` a 2025, agregar `2025: <factor>`.

5. **`target_freq` vs `lambda_scale_inicial`**: si se sube mucho `pesos_tipo_vehiculo["Moto"]`, la frecuencia base sube. Bajar `lambda_scale_inicial` para que el loop de calibración empiece más cerca del valor correcto y converja antes.
