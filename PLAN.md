# Plan: Expand Realism of Synthetic Insurance Dataset

## Context
The current dataset generates clean but overly "textbook" distributions — too uniform, too few categories, no noise or outliers. The goal is to expand variety and add domain-accurate Argentine insurance market structures without breaking the calibration loop or existing validations.

---

## Implementation Order
`config.py` → `vehiculos.py` → `polizas.py` → `siniestros.py`

---

## 1. `config.py` — New parameters + expanded geography

**Geography:**
- `localidades_por_provincia`: expand to 12–20 entries per major province, 5–10 for minor ones. Must keep all GBA trigger localities (`"San Isidro"`, `"Quilmes"`, `"Morón"`, `"Lomas de Zamora"`, `"Tigre"`) in Buenos Aires.
- `barrios_caba`: 8 → 28 (all 15 CABA communes represented, e.g. Retiro, La Boca, Barracas, Mataderos, Liniers, Colegiales, Villa Crespo…)
- `barrios_gba`: 7 → 25 (add San Fernando, Vicente López, Lanús, Avellaneda, Florencio Varela, Berazategui, Ezeiza, Merlo, Ituzaingó…)
- `pesos_provincia`: add 5 new provinces (Jujuy 0.02, Santiago del Estero 0.02, San Luis 0.01, Formosa 0.01, Catamarca 0.01) with their locality lists.

**Ramos (new):**
```python
ramo_principal: str = "Automotor"          # for Auto, Camioneta, Utilitario
ramo_motovehiculos: str = "Motovehiculos"  # for Moto tipo_vehiculo only
```
In Argentina, motos are regulated under a separate ramo ("Motovehiculos"), distinct from the broad "Automotor" umbrella.

**Vehicle types:**
```python
pesos_tipo_vehiculo: dict[str, float] = {"Auto": 0.78, "Moto": 0.12, "Camioneta": 0.07, "Utilitario": 0.03}
```

**Motorcycle-specific params (same 7 tipo_danio keys as cars — critical for validations):**
```python
prob_tipo_danio_moto: dict[str, float]  # Choque 45%, D.terceros 18%, R.parcial 12%, R.total 8%, Otros 12%, Granizo 3%, Incendio 2%
severidad_lognormal_moto: dict[str, tuple[float,float]]  # same keys, lower mu (e.g. Robo total: (14.2,0.6) vs car (15.5,0.6))
```

**Producers & Organizadores (new):**
```python
n_productores: int = 1000
n_organizadores: int = 50
prob_productor_en_organizador: float = 0.80  # 80% of productores belong to an organizador
```

**Other:**
```python
p_outlier_poliza: float = 0.005
lambda_scale_inicial: float = 0.88   # compensate for ~8-9% uplift from motos
comision_por_canal: {"Productor": (0.10, 0.28), "Broker": (0.08, 0.22), "Organizador": (0.09, 0.25), "Directa": (0.00,0.00), "Online": (0.03, 0.10)}
```

---

## 2. `generadores/vehiculos.py` — Expanded catalog

**Add `tipo_vehiculo` as 4th column** in `generar_catalogo_vehiculos()` — returns `["marca_vehiculo", "modelo_vehiculo", "valor_base_2024", "tipo_vehiculo"]`.

Classification for existing vehicles:
- `"Camioneta"`: Amarok, Hilux, Ranger, S10, Frontier, SW4, Strada
- `"Utilitario"`: Kangoo, Partner, Berlingo
- `"Auto"`: everything else (crossovers, sedans, hatchbacks)

**New car brands to add (~30 entries):**
- Kia: Picanto, Rio, Sportage, Seltos, Sorento
- Hyundai: HB20, Creta, Tucson, Santa Fe
- Chery: Tiggo 2 Pro, Tiggo 5X, Arrizo 5 Pro
- BYD: Yuan Plus, Dolphin
- Suzuki: Swift, Vitara, Jimny (Camioneta), S-Cross
- Extra VW: Taos, Tiguan, Nivus
- Extra Chevrolet: Equinox, Montana (Camioneta)
- Extra Ford: Territory, Maverick (Camioneta)
- Extra Renault: Oroch (Camioneta), Stepway
- Extra Toyota: Raize, GR86
- Extra Honda: City, WR-V, Fit
- Extra Nissan: Versa, Sentra

**Motorcycle section (~20 entries, `tipo_vehiculo="Moto"`):**
- Honda: CB190R, CB500F, XRE300, CG160, Wave
- Yamaha: FZ25, MT-03, Xtz 125, FZ-S
- Kawasaki: Z400, Ninja 400, Versys 650
- Zanella: ZB 110, ZR 70
- Motomel: CG150, S2 150
- Bajaj: Boxer 150, Pulsar NS200
- Beta: RR 125, Tempo 110

**`pesos_marca()`**: update to include new brands (kept for backward compat but no longer used for vehicle selection in polizas.py).

---

## 3. `generadores/polizas.py` — All structural changes

### 3a. Ramo by tipo_vehiculo
After assigning `df["ramo"] = cfg.ramo_principal`, overwrite motos:
```python
df.loc[df["tipo_vehiculo"] == "Moto", "ramo"] = cfg.ramo_motovehiculos
```

### 3b. Bimodal age distribution — replace `_sample_edad()`
```python
# 35% young: Normal(27, 7) clipped [18, 35]
# 65% mature: Normal(46, 12) clipped [25, 80]
# shuffle combined array → bimodal histogram
```

### 3c. Vehicle selection — tipo_vehiculo-first approach
Replace the current marca-first selection with:
```python
# 1. Sample tipo_vehiculo from cfg.pesos_tipo_vehiculo
# 2. catalogo_por_tipo = catalogo.groupby("tipo_vehiculo")
# 3. For each policy: filter by tipo_vehiculo, sample row uniformly
# 4. Assign marca_vehiculo, modelo_vehiculo, valor_base_2024, tipo_vehiculo
# Remove pesos_marca import — no longer needed
```

### 3d. Producers and Organizadores
Replace hardcoded `501` with `cfg.n_productores` (1000).

After assigning `codigo_productor` to each policy, build an organizador mapping:
```python
# Create 50 organizadores: ["ORG-01", ..., "ORG-50"]
organizadores = [f"ORG-{i:02d}" for i in range(1, cfg.n_organizadores + 1)]

# Assign each unique productor to an organizador or None (80/20 split)
rng_org = np.random.default_rng(cfg.random_seed + 999)
prod_to_org = {}
for prod in productores:
    if rng_org.random() < cfg.prob_productor_en_organizador:
        prod_to_org[prod] = rng_org.choice(organizadores)
    else:
        prod_to_org[prod] = None

# Map to policies
df["codigo_organizador"] = df["codigo_productor"].map(prod_to_org)
# Result: ~80% have a value like "ORG-03", ~20% are NaN/None
```

### 3e. Coverage category field (policy-level)
Add `categoria_cobertura` derived from `plan_cobertura`:
```python
_CATEGORIA_COBERTURA = {
    "Responsabilidad Civil": "Solo RC",
    "Terceros Completo":     "RC + Casco Básico",
    "Todo Riesgo":           "RC + Casco Total",
}
df["categoria_cobertura"] = df["plan_cobertura"].map(_CATEGORIA_COBERTURA)
```
This adds a clear Casco vs RC layer. "Solo RC" covers only third-party liability. "RC + Casco Básico" adds theft/partial casco. "RC + Casco Total" adds full own-damage coverage.

### 3f. Fleet flag
Add after `tipo_uso` is assigned (before premium calculation):
```python
df["es_flota"] = rng.random(n) < 0.02
df.loc[df["es_flota"], "tipo_uso"] = "Comercial"
```

### 3g. Outlier `suma_asegurada`
Save `valores` before clip, inject outliers, then overwrite:
```python
# Apply standard clip to all
df["suma_asegurada"] = np.clip(valores, 1_500_000, 45_000_000).round(2)
# Overwrite outlier rows (uncapped, 2x-4x premium vehicles)
outlier_idx = rng.choice(n, size=max(1, int(n * cfg.p_outlier_poliza)), replace=False)
df.loc[outlier_idx, "suma_asegurada"] = (
    valores[outlier_idx] * rng.uniform(2.0, 4.0, size=len(outlier_idx))
).round(2)
```
This must happen BEFORE computing `prima` so the premium reflects the inflated insured value.

### 3h. Wider noise
Change both `rng.uniform(0.92, 1.08)` → `rng.uniform(0.88, 1.15)`.

### 3i. GBA trigger set
Define module-level `_GBA_LOCALIDADES = frozenset({...})` with ~15 GBA entries, replacing both hardcoded set literals in `_asignar_zona()` and `generar_polizas()`.

---

## 4. `generadores/siniestros.py` — Moto claims, coverage category, extreme tail, seasonality

### 4a. Lambda by tipo_vehiculo
Add to `_lambda_por_segmento()`:
```python
tipo_vehiculo = row["tipo_vehiculo"] if "tipo_vehiculo" in row.index else "Auto"
if tipo_vehiculo == "Moto":        lam *= 1.7
elif tipo_vehiculo == "Camioneta": lam *= 0.85
```

### 4b. Moto-specific damage routing
Sample `tipo_danio` BEFORE `fecha_siniestro` (order change needed):
```python
if poliza.get("tipo_vehiculo") == "Moto":
    tipo_danio = _sample_weighted(rng, cfg.prob_tipo_danio_moto)
    mu, sigma = cfg.severidad_lognormal_moto[tipo_danio]
else:
    tipo_danio = _sample_weighted(rng, cfg.prob_tipo_danio_por_zona[zona])
    mu, sigma = cfg.severidad_lognormal[tipo_danio]
```

### 4c. Coverage category at claim level
After computing `cobertura_casco` and `cobertura_rc`, derive `categoria_siniestro`:
```python
if casco and not cobertura_rc:    categoria = "Casco"
elif cobertura_rc and not casco:  categoria = "RC"
else:                             categoria = "Mixto"  # Choque con terceros
```
Add `"categoria_siniestro": categoria` to the `rows.append({...})` dict.
Also update the empty-DataFrame column list in the `if not rows:` guard.

### 4d. Extreme severity tail
After computing `monto`:
```python
if rng.random() < 0.01:
    monto *= rng.uniform(2.5, 5.0)   # ~1% catastrophic / fraud signal
```

### 4e. Improved seasonality — new `_sample_fecha_siniestro()`
New signature: accepts `tipo_danio` parameter.

Add module-level `_PESOS_MES_DANIO` dict (normalized monthly weight arrays):
- `"Granizo"`: heavy Oct–Mar (Argentine spring-summer hail season)
- `"Choque"`: slight Jul–Aug peak (winter fog/frost)
- `"Robo total"` / `"Robo parcial"`: slight Dec–Feb peak (summer, vacations)
- others: near-uniform with mild variation

Implementation: sample month with type-specific weights → sample day within month → validate within `[inicio, fin]` (retry up to 20 times, fallback to uniform). Add `import calendar` at top of file.

**Update all call sites** to pass `tipo_danio`.

---

## Summary of new fields added

**`polizas_sinteticas.csv` new columns:**
| Column | Description |
|--------|-------------|
| `ramo` | Now "Automotor" or "Motovehiculos" (was always "Automotor") |
| `tipo_vehiculo` | Auto / Moto / Camioneta / Utilitario |
| `codigo_organizador` | ORG-01…ORG-50 (~80%) or NaN (~20%) |
| `es_flota` | True/False (2% fleet vehicles) |
| `categoria_cobertura` | "Solo RC" / "RC + Casco Básico" / "RC + Casco Total" |

**`siniestros_sinteticos.csv` new columns:**
| Column | Description |
|--------|-------------|
| `categoria_siniestro` | "Casco" / "RC" / "Mixto" |

---

## Files Modified
| File | Type of change |
|------|---------------|
| `config.py` | Add new fields, expand all geographic dicts |
| `generadores/vehiculos.py` | Add `tipo_vehiculo` column, expand catalog to ~110 entries |
| `generadores/polizas.py` | Bimodal age, tipo_vehiculo-first selection, 1000 producers + 50 organizadores, ramo override, categoria_cobertura, es_flota, outliers, wider noise |
| `generadores/siniestros.py` | Lambda by vehicle type, moto routing, categoria_siniestro, extreme tail, new seasonality |
| `validaciones.py` | **No changes** — existing checks don't reference new columns |
| `main.py` | **No changes** |

---

## Verification

**Fast smoke test:**
```bash
python main.py --n-polizas 5000 --seed 99 --output-dir /tmp/test_output
```
Expected: all validations PASS, frequency 15–20%, loss ratio 60–80%, converges within 12 iterations.

**Distribution checks (polizas CSV):**
- `ramo`: ~88% "Automotor", ~12% "Motovehiculos"
- `tipo_vehiculo`: ~Auto 78%, Moto 12%, Camioneta 7%, Utilitario 3%
- `edad_asegurado`: bimodal histogram with peaks ~27 and ~46
- `codigo_productor`: ~1000 unique values
- `codigo_organizador`: ~80% populated, ~20% NaN; ~50 unique ORG codes
- `es_flota`: ~2% True
- `suma_asegurada`: some values > 45M (outliers present)
- `categoria_cobertura`: distribution matching `pesos_cobertura` (RC 40%, Básico 35%, Total 25%)

**Distribution checks (siniestros CSV):**
- `categoria_siniestro`: split across Casco / RC / Mixto
- Granizo claims: concentrated months 10–3
- Choque: slight elevation months 7–8
- Moto policies: damage type follows `prob_tipo_danio_moto`
- `monto_reclamado`: visible heavy right tail

**Full run:**
```bash
python main.py --n-polizas 50000 --seed 42 --output-dir output
```
