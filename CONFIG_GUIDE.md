# Guía de parámetros — `config.py`

Referencia completa de cada parámetro de `Config`. Para cada uno se explica qué controla, qué pasa en los datos si se lo modifica, y qué restricciones hay que respetar.

---

## 1. Parámetros globales de generación

### `random_seed` (default: `42`)
Semilla del generador de números aleatorios. Cambiarla produce un dataset completamente distinto pero estadísticamente equivalente. Útil para generar múltiples versiones independientes del dataset. No afecta las distribuciones, solo el resultado puntual de cada sorteo.

### `cantidad_polizas` (default: `100_000`)
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

### `n_productores` (default: `120`)
Número de productores únicos en el campo `codigo_productor`. Calibrado contra el tamaño típico de una compañía aseguradora mediana argentina (100-150 productores activos). Los productores se distribuyen con una power-law sobre rank (`1/rank^productor_power_law_exponente`), por lo que unos pocos concentran mucho volumen — con los defaults, el top 1 productor tiene ~15% de las pólizas y los top 5 acumulan ~36%. Aumentar este valor → más diversidad, menor concentración. Disminuirlo → más concentración, útil para simular brokers oligopólicos.

### `productor_power_law_exponente` (default: `0.90`)
Exponente de la power-law sobre el rank del productor. Valores más altos (`1.5+`) producen concentraciones extremas (top 1 con >30%). Valores más bajos (`0.5-0.7`) producen una distribución más plana (top 1 ~5-8%). El default 0.9 ajusta la concentración esperada en una compañía mediana argentina.

### `n_organizadores` (default: `25`)
Número de grupos organizadores (`ORG-01` a `ORG-25`). Calibrado contra el tamaño típico (20-30 organizadores) de compañías medianas. Cada organizador agrupa en promedio `n_productores × prob_productor_en_organizador / n_organizadores ≈ 4` productores. Reducir este número aumenta la concentración por organizador.

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
Variables demográficas. Interactúan con `factor_demografico_frecuencia` (ver sección 9): combinaciones de edad + estado civil + ocupación modifican el lambda de frecuencia. Cambiar sus pesos ajusta las proporciones en el CSV y, de forma indirecta, la frecuencia media de la cartera.

### `pesos_canal`
Mix de canal de venta. Afecta:
- La **comisión pactada** (rango diferente por canal).
- La **mora**: canales Online y Directa tienen una corrección negativa en la probabilidad de mora alta.
- **No afecta** frecuencia ni severidad de siniestros directamente.

### `pesos_medio_pago`
Distribución de 6 medios de pago: Tarjeta de crédito / Tarjeta de débito / Débito automático CBU / Billetera virtual / Transferencia / Efectivo. Este campo interactúa con `prob_mora_por_medio_pago`: tarjeta de crédito y débito tienen mora prácticamente nula (auto-cobro), mientras que efectivo y transferencia dependen de la acción activa del cliente cada mes y tienen alta probabilidad de mora.

### `pesos_cuotas_por_medio_pago`
Distribución de cuotas (1/3/6/12) dentro de cada medio de pago. Solo los medios con financiación (Tarjeta de crédito y Débito automático CBU) admiten cuotas > 1; el resto se fuerza a 1. La columna `cantidad_cuotas` se asigna en función de este dict.

### `pesos_uso`
Proporción de uso Particular / Comercial / Profesional. Uso Comercial y Profesional aplican un multiplicador ×1.15 sobre lambda en `_lambda_por_segmento()`, por lo que aumentar su peso sube la frecuencia media de la cartera. El flag `es_flota` fuerza uso Comercial en ~2% de las pólizas independientemente de este peso.

### `pesos_provincia`
Distribución geográfica. Dado que la zona de riesgo (CABA Premium / CABA Resto / GBA Norte / GBA Sur/Oeste / Media-Alta / Media / Baja) se deriva de provincia + localidad, cambiar estos pesos modifica indirectamente la mezcla de zonas:
- Más peso en CABA → más pólizas zona CABA Premium/Resto → mayor frecuencia y severidad promedio.
- Más peso en Buenos Aires → más pólizas zona GBA Norte/Sur-Oeste (GBA) y Media (interior).
- Más peso en provincias del interior → más pólizas zona Media-Alta (capitales) y Baja (resto).
- **Restricción**: las claves deben coincidir exactamente con las entradas de `localidades_por_provincia`.

---

## 5. Geografía

### `localidades_por_provincia`
Lista de localidades para cada provincia. Se samplea de forma uniforme dentro de cada provincia. La zona de riesgo se asigna en 7 niveles:
- CABA barrio en `CABA_PREMIUM_LOCALIDADES` (Palermo, Recoleta, Belgrano, Núñez, Puerto Madero) → CABA Premium
- Resto de CABA → CABA Resto
- Buenos Aires con localidad en `GBA_NORTE_LOCALIDADES` (San Isidro, Vicente López, Tigre, Pilar, Escobar, San Fernando) → GBA Norte
- Resto del GBA → GBA Sur/Oeste
- Grandes ciudades y capitales provinciales (en `CIUDADES_MEDIA_ALTA`, incluye Córdoba Capital y Rosario) → Media-Alta
- Restantes localidades de Buenos Aires, Santa Fe, Mendoza, Córdoba → Media
- Todo lo demás → Baja

Las constantes `GBA_LOCALIDADES`, `GBA_NORTE_LOCALIDADES`, `GBA_SUR_OESTE_LOCALIDADES`, `CABA_PREMIUM_LOCALIDADES` y `CIUDADES_MEDIA_ALTA` viven en `generadores/geografia.py`. Para mover una localidad de tier (por ejemplo, sumar un partido más al GBA Norte), editarlas ahí y asegurarse de que la zona resultante esté en todos los dicts de zonificación.

### `barrios_caba` / `barrios_gba`
Listas de barrios para pólizas de CABA y GBA respectivamente. Son puramente descriptivos: no afectan frecuencia, severidad ni zona de riesgo. Solo enriquecen la columna `barrio` del CSV.

---

## 6. Factores de tarificación

### Los tres efectos de la zona

La zona de riesgo (7 niveles: CABA Premium / CABA Resto / GBA Norte / GBA Sur/Oeste / Media-Alta / Media / Baja) afecta tres dimensiones distintas e independientes. No es duplicación — cada dict modela un efecto actuarial distinto:

| Parámetro | Qué modifica | Dónde se aplica |
|---|---|---|
| `factor_prima_por_zona` | Precio cobrado al cliente | `tarifa.py` al calcular `prima` |
| `factor_frecuencia_por_zona` | Cuán seguido ocurren siniestros (λ Poisson) | `siniestros.py` en `_lambda_por_segmento` |
| `factor_severidad_por_zona` | Cuánto cuesta cada siniestro | `siniestros.py` sobre `monto_reclamado` |

Ejemplo: en CABA cobramos más caro (prima ×1.5) porque ocurren más siniestros (λ=0.22 vs 0.08 en zona Baja) y porque cuestan más cuando ocurren (severidad ×1.25). Los tres efectos se calibran independientemente.

### `factor_prima_por_zona`
Rango uniforme del multiplicador de zona aplicado a la **prima** (no al siniestro):
```
prima ∝ suma_asegurada × tasa_base × factor_prima_por_zona × ...
```
Tiene 7 claves (las 7 zonas). Subir los rangos de zonas CABA/GBA → primas más altas en esos segmentos → mejora el LR de esos segmentos.

### `factor_frecuencia_por_zona`
Lambda base de la Poisson de siniestros, indexada por zona. Es el parámetro de **frecuencia** (no de severidad ni de prima):
- CABA Resto: 0.24 → frecuencia más alta de la cartera.
- CABA Premium: 0.18 → menor que CABA Resto (vehículos mejor cuidados).
- GBA Sur/Oeste: 0.20 / GBA Norte: 0.15 / Media-Alta: 0.15 / Media: 0.12 / Baja: 0.08.

Después se le aplican multiplicadores por edad, uso, tipo de vehículo, plan y demografía. Bajar todos los valores → menos siniestros globales → mejor LR. Aumentar el spread → diferencias más marcadas de frecuencia entre zonas.

### `factor_severidad_por_zona`
**Rango uniforme** (low, high) por zona, muestreado independientemente por cada siniestro. Multiplica el `monto_reclamado`. Tiene 7 claves:
- CABA Premium: (1.25, 1.55) — vehículos premium, costos elevados de reparación.
- CABA Resto / GBA Norte: (1.10, 1.30) — autos buenos en buen estado.
- GBA Sur/Oeste: (0.90, 1.10) — autos populares.
- Media-Alta: (0.95, 1.15) — grandes capitales provinciales.
- Media: (0.85, 1.05) — interior de Bs As/Santa Fe/Mendoza/Córdoba.
- Baja: (0.72, 0.92) — provincias menores / zonas rurales.

Antes de Tanda 3 este parámetro era un escalar fijo por zona; ahora es un rango. Aumentar el spread (rango más ancho) genera más variabilidad de severidad dentro de la misma zona — útil para entrenar modelos no triviales. Si se pone (1.0, 1.0) en todas, los LR por zona convergen.

### `tasa_base_rango` (default: `(0.04, 0.06)`)
Rango uniforme de la tasa técnica sobre la suma asegurada. Sube o baja la prima media de toda la cartera proporcionalmente. Subir el rango → más prima → mejor LR global (el loop de calibración puede ajustar menos agresivamente `severidad_scale`).

### `factor_cobertura_tarifa`
**Rango uniforme** (low, high) por plan de cobertura. Define cuánto más cara es cada cobertura relativa a Todo Riesgo (≈ 1.0). Cambiar estos rangos modifica la prima relativa entre planes pero **no** modifica la siniestralidad por plan — afecta sí el LR por plan. Antes de Tanda 3 era un escalar; ahora es un rango para evitar primas perfectamente alineadas dentro del mismo plan.

### `comision_por_canal`
Rangos de comisión por canal de venta `(min, max)`. Afectan únicamente la columna `comision_pactada` en el CSV. No entran en el cálculo de prima ni en la lógica de siniestros.

---

## 7. Inflación anual

### `inflacion_anual` (default: `{2021: 1.0, 2022: 1.9, 2023: 5.5, 2024: 12.0}`)
Multiplicador aplicado al **monto del siniestro** según el año de ocurrencia. Calibrado contra el IPC argentino real:
- 2021 → monto base (×1.0)
- 2022 → ×1.9 (inflación YoY 2022 ≈ 95%)
- 2023 → ×5.5 (inflación YoY 2023 ≈ 211%)
- 2024 → ×12.0 (inflación YoY 2024 ≈ 118%)

Esto introduce una tendencia temporal fuerte en `monto_reclamado`: los siniestros de 2024 son ~12× más caros nominalmente que los de 2021. Si se agrega 2025 (ej. `2025: 16.0`), los siniestros de ese año serán aún mayores.

**Efecto en el LR**: como las primas se fijan al inicio de la vigencia y no se reajustan, años con alta inflación tienden a tener LR más alto. Esto es intencional — simula el efecto del descalce temporal real en seguros argentinos. El loop de calibración auto-ajusta `severidad_scale` para mantener el LR global en target, pero los LR por año seguirán mostrando el descalce.

**Cambio de tanda 3**: en versiones anteriores, los factores eran 1.0/1.5/2.5/4.0 (subestimando el IPC real). Si se vuelve a esos valores, también hay que subir `severidad_scale_inicial` de 0.35 a ~1.0 para que la calibración converja.

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

## 9. Estado del siniestro, reservas y gastos de liquidación

### `prob_estado_siniestro` (default: `Cerrado: 0.68, Abierto: 0.25, Rechazado: 0.07`)
Distribución del estado de cada siniestro. Controla la mezcla de:
- **Cerrado**: liquidado y pagado. `monto_pagado` refleja el pago final.
- **Abierto**: en gestión. Tiene reserva activa y pago parcial (anticipo) que puede ser cero.
- **Rechazado**: sin pago. Tiene `motivo_rechazo` poblado y `monto_pagado = 0`.

Cambiar hacia más "Rechazado" baja el loss ratio (menos pagos). Cambiar hacia más "Abierto" aumenta las reservas activas.

### `factor_reserva_rango` (default: `(0.85, 1.30)`)
Rango del multiplicador sobre `monto_reclamado` para calcular `monto_reservado`. Un rango alto (ej. `(1.10, 1.50)`) simula subreservas agresivas. Un rango bajo simula reservas conservadoras.

### `factor_pago_cerrado_rango` (default: `(0.70, 1.05)`)
Qué porcentaje del `monto_reclamado` se paga en siniestros cerrados. Valores por debajo de 1.0 simulan negociaciones donde se paga menos de lo reclamado.

### `factor_pago_abierto_rango` (default: `(0.0, 0.40)`)
Pago parcial (anticipo) en siniestros abiertos, como fracción del `monto_reclamado`. Con el default, entre 0% y 40% ya pagado al momento del corte.

### `pesos_motivo_rechazo`
Distribución de motivos para siniestros rechazados:
- `Falta de cobertura` (0.28), `Mora en el pago` (0.22), `Exclusión contractual` (0.18), `Documentación incompleta` (0.17), `Fraude presunto` (0.15).

Cambiar estos pesos no afecta la frecuencia de rechazos (eso lo controla `prob_estado_siniestro`), solo la distribución de motivos dentro de los rechazados.

### `gasto_liquidacion_base` (default: `45_000`)
Mínimo fijo de gastos de liquidación por siniestro (honorarios perito, costos administrativos). En ARS del período base.

### `gasto_liquidacion_pct` (default: `0.05`)
Porcentaje del `monto_reclamado` que se suma como componente variable del gasto de liquidación.

### `gasto_liquidacion_mult_juicio` (default: `2.5`)
Multiplicador sobre el gasto base+variable cuando el siniestro está en juicio (incluye honorarios de abogados y costas procesales).

### `gasto_liquidacion_mult_mediacion` (default: `1.4`)
Multiplicador cuando hay mediación pero sin llegar a juicio.

---

## 10. Factores demográficos sobre frecuencia

### `factor_demografico_frecuencia`
Multiplicadores aplicados al lambda de frecuencia según características del asegurado:

| Clave | Condición | Multiplicador | Efecto |
|---|---|---|---|
| `soltero_joven` | Soltero + edad < 25 | 1.18 | Mayor riesgo en conductores jóvenes sin familia |
| `jubilado` | Ocupación = Jubilado | 0.85 | Menor exposición, menos kilómetros recorridos |
| `divorciado_joven` | Divorciado + edad < 35 | 1.08 | Leve incremento por perfil de vida |

Estos factores se aplican de forma acumulativa con los demás (zona, tipo vehículo, cobertura). Para desactivar un factor, ponerlo en `1.0`.

---

## 11. Cancelaciones mid-term

### `tasa_cancelacion_base` (default: `0.07`)
Proporción de pólizas canceladas antes de fin de vigencia. Con el default, ~7% de las pólizas tienen `cancelada = True` con una `fecha_cancelacion` válida dentro del período.

Las pólizas con `meses_en_mora >= mora_umbral_cancelacion` tienen el doble de probabilidad de cancelación.

### `prob_mora_por_medio_pago`
Probabilidad de que la lógica de mora se active según el medio de pago:
- `Tarjeta de crédito: 0.00` — auto-cobro, nunca genera mora.
- `Tarjeta de débito: 0.05` — eventual falta de saldo.
- `Débito automático CBU: 0.10` — rechazo por falta de fondos.
- `Billetera virtual: 0.15` — depende de la disponibilidad en la billetera.
- `Transferencia: 0.30` — requiere acción manual mensual.
- `Efectivo: 0.70` — alta probabilidad de generar mora.

Si el sorteo falla (el random supera la probabilidad), `meses_en_mora = 0` directamente. Esto crea una dependencia causal realista entre medio de pago y morosidad. La mora se recomputa después de la propagación de medio_pago en `asignar_cadenas_renovacion`, para asegurar coherencia entre la columna final y la mora generada.

### `mora_umbral_cancelacion` (default: `3`)
Cantidad de meses de mora a partir de los cuales se duplica la probabilidad de cancelación. Refleja la baja de pólizas por falta de pago sostenida.

### `pesos_motivo_cancelacion`
Distribución de motivos de cancelación:
- `Mora prolongada` (0.35), `Venta del vehículo` (0.25), `Cambio de compañía` (0.25), `Voluntaria` (0.15).

---

## 12. Cadenas de renovación (cohortes de clientes)

### `pesos_periodos_cliente` (default: `{1: 0.45, 2: 0.28, 3: 0.18, 4: 0.09}`)
Distribución del número de períodos de póliza por cliente. Con el default:
- 45% de los clientes tiene una sola póliza (sin renovar)
- 28% renueva una vez (2 pólizas vinculadas)
- 18% renueva dos veces (3 pólizas)
- 9% renueva tres veces (4 pólizas)

Los clientes de una misma cadena comparten `id_cliente` y tienen `numero_renovacion` incremental. La demografía del asegurado se propaga coherentemente dentro de la cadena.

**Efecto sobre el tamaño del dataset**: sumar más períodos promedio por cliente produce más pólizas por cliente, manteniendo `cantidad_polizas` total constante. Para aumentar la retención aparente, subir el peso de las claves 3 y 4.

### `ajuste_prima_renovacion_rango` (default: `(1.10, 1.35)`)
Factor multiplicativo aplicado a la prima en cada renovación. Simula ajustes por inflación y experiencia siniestral. Con el default, la prima crece entre 10% y 35% en cada renovación.

### `prob_cambio_cobertura_renovacion` (default: `0.12`)
Probabilidad de que el cliente cambie de plan de cobertura al renovar. El 12% de las renovaciones tiene un plan distinto al período anterior. Cambiar a 0 produce cadenas con cobertura constante; subirlo a 0.30+ produce más variabilidad en la historia del cliente.

---

## 13. Otros parámetros de siniestros (en `siniestros.py`, no en config)

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

## 14. Variabilidad y variables extendidas

Conjunto de parámetros agregados para enriquecer realismo. Cada uno actúa sobre prima, frecuencia o severidad — la sección 7 del README los lista a nivel de columna.

### `pesos_lag_siniestro`
Mezcla de 4 regímenes para el lag (días entre inicio de vigencia y fecha de siniestro). Se combina con `_PESOS_MES_DANIO` (estacionalidad mensual) por producto de pesos por día:
- `extremo (0-7d): 0.01` — siniestros casi inmediatos. Señal de fraude.
- `temprano (8-30d): 0.04` — poca exposición acumulada.
- `adaptacion (31-90d): 0.10` — primeros meses aún suprimidos.
- `normal (91-365d): 0.85` — el grueso de la cartera.

Aumentar el peso de `extremo` enriquece la cola izquierda → útil para entrenar modelos de detección de fraude / early-claim score.

### Antigüedad de carnet

- **`edad_carnet_minimo` (default: `17`)** — edad legal mínima de carnet en Argentina. Define el techo: `antiguedad_carnet ≤ edad - edad_carnet_minimo`.
- **`antiguedad_carnet_beta` (default: `(5.0, 2.0)`)** — parámetros α, β de la Beta usada para muestrear la fracción del máximo posible. Sesgado al límite superior (la mayoría de conductores tiene muchos años de carnet relativos a su edad). Bajar α y subir β invierte el sesgo.
- **`factor_antiguedad_carnet`** — multiplicadores sobre λ por banda: novel (<2 años) ×1.25, intermedio (2-4) ×1.10, establecido (5-9) ×1.00, experimentado (≥10) ×0.95.

### Franquicia

- **`pesos_franquicia` (default: `{0.00: 0.40, 0.05: 0.50, 0.20: 0.10}`)** — distribución de la franquicia (fracción de la suma asegurada). Solo aplica a planes con cobertura de Casco (Terceros Completo / Todo Riesgo). Responsabilidad Civil siempre tiene franquicia = 0.
- **`factor_franquicia` (default: `{0.00: 1.00, 0.05: 0.93, 0.20: 0.82}`)** — descuento sobre prima por nivel de franquicia.

La franquicia se descuenta de `monto_pagado` (no de `monto_reclamado`) solo para siniestros con `cobertura_casco=True`. Para siniestros de RC, no aplica (el pago va al tercero, no al asegurado).

### Bonus-malus

- **`bonus_malus_nivel_inicial` (default: `3`)** — nivel inicial para clientes con numero_renovacion = 0.
- **`bonus_malus_p_sin_claim` (default: `0.78`)** — probabilidad de bajar un nivel (sin siniestros) por renovación. El complemento (0.22) sube un nivel.
- **`factor_bonus_malus`** — factor multiplicativo sobre prima: nivel 0 = 0.80 (max descuento), nivel 3 = 1.00 (base), nivel 5 = 1.40 (max recargo).

El nivel se simula como random walk vectorizado sobre el número de renovaciones del cliente. Bajar `p_sin_claim` produce niveles más altos en la cartera (más recargos visibles).

### Rastreador (Lojack/Ituran)

- **`prob_rastreador_por_zona`** — probabilidad de que la póliza tenga rastreador, por zona. Mayor en zonas de mayor riesgo de robo (Muy Alta 35%, Baja 5%).
- **`factor_prima_rastreador` (default: `0.90`)** — descuento del 10% sobre prima.
- **`factor_robo_rastreador` (default: `0.50`)** — reduce a la mitad la probabilidad de Robo total y Robo parcial al sortear el tipo de daño.

### Tipo de combustible

- **`pesos_combustible_por_tipo`** — distribución por tipo de vehículo (Nafta / Diésel / GNC / Híbrido / Eléctrico). Motos siempre Nafta; camionetas y utilitarios mayoría Diésel; autos mezcla típica.
- **`factor_prima_combustible`** — recargo por combustible: GNC +5%, Eléctrico +8%, Híbrido +3%, Diésel +2%, Nafta base.
- **`factor_incendio_gnc` (default: `1.6`)** — multiplica la probabilidad de Incendio en vehículos GNC.
- **`factor_severidad_choque_electrico` (default: `1.30`)** — incrementa severidad de Choque para vehículos eléctricos (baterías costosas).

### Vehículo

El catálogo en `generadores/vehiculos.py` tiene 185 modelos en 39 marcas, con una columna `peso_relativo` por modelo que controla la frecuencia relativa dentro de cada `tipo_vehiculo`. Los autos populares (Gol, Cronos, Onix, Sandero, etc.) tienen pesos 8-15; los premium (Audi, BMW, Mercedes) pesos 0.3-1.0; las motos populares (Wave, CG160, Smash) pesos 8-12. Premium share resultante: ~2% en autos.

### Calidad de productor (Tanda 3)

- **`factor_calidad_productor_sigma` (default: `0.15`)** — desvío de la N(1.0, σ) usada para asignar un factor único por productor.
- **`factor_calidad_productor_clip` (default: `(0.55, 1.55)`)** — recortes para evitar productores con frecuencia degenerada.

El factor se sortea una sola vez por productor con un RNG independiente (`seed + 7777`), garantizando estabilidad entre iteraciones de calibración. Cada póliza hereda el factor de su productor (columna `factor_calidad_productor` en el CSV). En `_lambda_por_segmento`, multiplica la lambda de Poisson → productores con factor > 1.15 son "tóxicos" (más siniestros), factor < 0.85 son "estrella". Permite el análisis de red productores-organizadores ya mencionado en `analisis_recomendaciones.md`.

### Nuevos tipos de daño (Tanda 3)

Se agregaron cuatro tipos al catálogo original de 7:
- **Cristales/Parabrisas**: alta frecuencia, baja severidad (μ=13.2, σ=0.4). Solo casco. No aplica a motos.
- **Vandalismo**: media frecuencia, severidad media. Pico en Dic-Feb (público en la calle).
- **Inundación**: baja frecuencia, alta severidad. Pico Oct-Mar (estación lluviosa argentina).
- **Daño a terceros con lesiones**: severidad muy alta (μ=16.5, σ=0.9 — mediana ~15M). RC pura, mayor incidencia en motos (μ=16.8).

Todos los tipos están consistentemente definidos en `prob_tipo_danio_por_zona`, `prob_tipo_danio_moto`, `severidad_lognormal`, `severidad_lognormal_moto` y `_PESOS_MES_DANIO`. La lógica `_cobertura_casco` usa los frozensets `_DANIOS_CASCO` y `_DANIOS_RC` en `siniestros.py`.

### Motivos de rechazo adicionales (Tanda 3)

A los 5 motivos originales se sumaron 3:
- **Alcoholemia positiva** (0.08)
- **Conductor no habilitado** (0.08)
- **Denuncia tardía (>72hs)** (0.08) — sesgo contextual ×3 cuando `lag_denuncia > 3` días.

---

## 15. Reglas de consistencia importantes

Al modificar los parámetros, respetar estas dependencias:

1. **Suma de pesos de provincia**: No es estrictamente necesario que sumen 1 (se normalizan), pero si se agregan provincias nuevas hay que agregarlas también en `localidades_por_provincia`.

2. **Tipos de daño**: Ver la regla 6 más abajo — la lista canónica son los 11 tipos extendidos (Tanda 3).

3. **GBA localities**: Las localidades de Buenos Aires que deben disparar zona Alta están en `GBA_LOCALIDADES` (frozenset en `generadores/geografia.py`). Las ciudades que deben disparar zona Media-Alta están en `CIUDADES_MEDIA_ALTA`. Si se agregan localidades, actualizar el frozenset correspondiente.

5. **Zone dict key alignment**: todos los dicts con claves de zona (`factor_prima_por_zona`, `factor_frecuencia_por_zona`, `factor_severidad_por_zona`, `prob_tipo_danio_por_zona`, `prob_rastreador_por_zona`) deben tener las mismas 7 claves: `CABA Premium`, `CABA Resto`, `GBA Norte`, `GBA Sur/Oeste`, `Media-Alta`, `Media`, `Baja`. La lista canónica de zonas válidas también está en `validaciones.py:zonas_validas`.

6. **Tipos de daño extendidos**: Los 11 tipos (`Robo total`, `Robo parcial`, `Choque`, `Incendio`, `Granizo`, `Cristales`, `Vandalismo`, `Inundación`, `Daño a terceros`, `Daño a terceros con lesiones`, `Otros`) deben aparecer en `prob_tipo_danio_por_zona`, `severidad_lognormal` y `_PESOS_MES_DANIO`. Para motos, `prob_tipo_danio_moto` y `severidad_lognormal_moto` omiten `Cristales` (no aplica). La lógica casco/RC vive en los frozensets `_DANIOS_CASCO` y `_DANIOS_RC`.

4. **`inflacion_anual`**: debe tener una entrada para cada año entre `fecha_inicio.year` y `fecha_fin.year`. Si se extiende `fecha_fin` a 2025, agregar `2025: <factor>`.

5. **`target_freq` vs `lambda_scale_inicial`**: si se sube mucho `pesos_tipo_vehiculo["Moto"]`, la frecuencia base sube. Bajar `lambda_scale_inicial` para que el loop de calibración empiece más cerca del valor correcto y converja antes.
