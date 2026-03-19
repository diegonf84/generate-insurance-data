# Generate Insurance Data

A Python tool that generates realistic synthetic datasets for **Argentine automotive insurance portfolios**. It produces two linked CSV files — policies and claims — with statistically coherent distributions, calibrated loss ratios, and domain-accurate structures ready for EDA, machine learning, or actuarial analysis.

---

## What it generates

### `polizas_sinteticas.csv` — Policy table (35 columns)
Each row is one insurance policy. Key fields include:

| Column | Description |
|---|---|
| `id_poliza`, `numero_poliza` | Unique identifiers |
| `ramo` | Regulatory line: `Automotor` or `Motovehiculos` |
| `plan_cobertura` | Coverage plan: RC only / Terceros Completo / Todo Riesgo |
| `categoria_cobertura` | Human-readable coverage tier |
| `tipo_vehiculo` | Auto / Moto / Camioneta / Utilitario |
| `marca_vehiculo`, `modelo_vehiculo`, `anio_vehiculo` | Vehicle details (68 models in catalog) |
| `suma_asegurada`, `prima`, `premio` | Financial values in ARS |
| `provincia`, `localidad`, `barrio` | 20 Argentine provinces, 200+ localities |
| `zona_riesgo` | Muy Alta / Alta / Media-Alta / Media / Baja (derived from geography) |
| `edad_asegurado` | Bimodal distribution: peaks at ~27 and ~46 |
| `medio_pago` | Efectivo / Tarjeta de crédito / Otros |
| `canal_venta` | Productor / Broker / Organizador / Directa / Online |
| `codigo_productor`, `codigo_organizador` | 1 000 producers, 50 organization groups |
| `es_flota` | True for ~2% of policies (fleet vehicles) |
| `id_cliente`, `numero_renovacion` | Client cohort identity across renewal chains |
| `renovada` | Whether the policy was renewed |
| `cancelada`, `fecha_cancelacion`, `motivo_cancelacion` | Mid-term cancellation details |
| `meses_en_mora` | Payment delinquency bucket |

### `siniestros_sinteticos.csv` — Claims table (24 columns)
Each row is one claim linked to a policy. Key fields include:

| Column | Description |
|---|---|
| `id_siniestro`, `numero_siniestro` | Unique identifiers |
| `id_poliza` | Foreign key to policies table |
| `tipo_danio` | Robo total / Choque / Granizo / Incendio / Daño a terceros / … |
| `estado_siniestro` | Cerrado / Abierto / Rechazado |
| `monto_reclamado` | Claim amount in ARS (log-normal, inflation-adjusted by year) |
| `monto_reservado`, `monto_pagado` | Reserve and payment amounts |
| `gasto_liquidacion` | Settlement expenses (higher for claims in litigation) |
| `motivo_rechazo` | Populated for rejected claims |
| `categoria_siniestro` | Casco / RC / Mixto |
| `fecha_siniestro`, `fecha_denuncia` | Dates with realistic reporting lag |
| `en_mediacion`, `en_juicio`, `con_sentencia` | Legal chain flags (coherent cascade) |
| `cobertura_casco`, `cobertura_rc` | Coverage applicability per claim |
| `terceros_involucrados`, `conductor_es_asegurado` | Contextual flags |
| `bien_recuperado` | For theft claims only |

---

## Key design features

- **Calibrated targets**: a feedback loop adjusts claim frequency and severity until the portfolio lands within configurable bands (default: frequency 15–20%, loss ratio 60–80%).
- **Renewal chains**: policies are grouped into client cohorts (`id_cliente`) with propagated demographics and inflation-adjusted premiums across renewals.
- **Mid-term cancellations**: ~7% of policies are cancelled before expiry, with contextual reasons (mora, vehicle sale, competitor switch, voluntary).
- **Motorcycle ramo**: Motos are assigned to a separate `ramo_motovehiculos` line, with their own damage distributions, severity parameters, and frequency uplift (×1.7).
- **Claim financial states**: each claim has a status (Cerrado/Abierto/Rechazado) with consistent reserve, payment, expense, and rejection-reason fields.
- **Seasonal claim dates**: each damage type has monthly weight arrays (e.g. Granizo peaks Oct–Mar, Robo peaks Dec–Feb).
- **Inflation by year**: nominal claim amounts grow year-over-year (2021 baseline → 2024 ×4.0).
- **Zone-differentiated severity**: claims in Alta risk zones cost more than in Baja zones.
- **Coherent legal chain**: `con_sentencia` implies `en_juicio` implies `en_mediacion` — always.
- **Integrity validations**: 9 checks run automatically after generation (dates, coverage logic, referential integrity, legal chain, financial amounts, etc.).

---

## Installation

Requires [uv](https://docs.astral.sh/uv/) (fast Python package manager).

```bash
# 1. Clone the repository
git clone <repo-url>
cd generate-insurance-data

# 2. Create virtual environment and install dependencies
uv sync
```

That's it. No manual `pip install` or `venv` creation needed.

---

## Usage

### Default run — 100 000 policies, seed 42
```bash
uv run python main.py
```

### Custom parameters
```bash
# 10 000 policies with a different seed, output to a custom directory
uv run python main.py --n-polizas 10000 --seed 7 --output-dir data/
```

| Argument | Default | Description |
|---|---|---|
| `--n-polizas` | `100000` | Number of policies to generate |
| `--seed` | `42` | Random seed for reproducibility |
| `--output-dir` | `output/` | Directory where CSVs are written |

The script prints a calibration log and a validation report on each run:

```
Iteración 01 | frecuencia=0.1423 | loss_ratio=0.6812 | lambda_scale=0.8800 | severidad_scale=1.0000
Iteración 02 | frecuencia=0.1614 | loss_ratio=0.7231 | lambda_scale=0.9856 | severidad_scale=1.0000
Calibración convergida. Iteración=2, lambda_scale=0.9856, severidad_scale=1.0000

=== REPORTE DE VALIDACION ===
[Integridad y coherencia]
- id_poliza_referencial: PASS
- fecha_siniestro_en_vigencia: PASS
...
- Loss ratio global: 72.31% | Objetivo: 60% - 80% | PASS
- Frecuencia siniestral: 16.14% | Objetivo: 15% - 20% | PASS
```

### Customizing distributions
All statistical parameters live in `config.py`. No code changes are needed — just edit the values there. See `CONFIG_GUIDE.md` for a full explanation of every parameter and what changing it produces in the data.

---

## Exploratory analysis

An EDA notebook is included with 11 sections covering portfolio composition, loss ratio by segment, heatmaps, producer network analysis, vehicle type breakdown, seasonality, and outlier detection.

```bash
uv run jupyter lab
# Open: analisis_eda_cartera_completo_v2.ipynb
```

> Run `main.py` first to generate the CSVs before opening the notebook.

---

## Project structure

```
.
├── main.py                                    # Entry point and calibration loop
├── config.py                                  # All parameters (distributions, targets, geography)
├── validaciones.py                            # Integrity checks and metrics
├── generadores/
│   ├── polizas.py                             # Policy table generator
│   ├── siniestros.py                          # Claims table generator
│   └── vehiculos.py                           # Vehicle catalog (68 models)
├── analisis_eda_cartera_completo_v2.ipynb     # EDA notebook
├── CONFIG_GUIDE.md                            # Parameter reference and tuning guide
├── pyproject.toml                             # Project dependencies (managed by uv)
└── output/                                    # Generated CSVs (git-ignored)
```

---

## Requirements

- Python 3.12+
- uv 0.4+

Dependencies (managed automatically by `uv sync`): `pandas`, `numpy`, `matplotlib`, `seaborn`, `scipy`, `jupyterlab`.
