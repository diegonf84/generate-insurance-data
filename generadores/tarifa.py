from __future__ import annotations

import numpy as np
import pandas as pd

from config import Config


CATEGORIA_COBERTURA: dict[str, str] = {
    "Responsabilidad Civil": "Solo RC",
    "Terceros Completo": "RC + Casco Básico",
    "Todo Riesgo": "RC + Casco Total",
}


def factor_edad(edad: int) -> float:
    if edad < 25:
        return 1.4
    if edad < 35:
        return 1.1
    if edad < 55:
        return 1.0
    if edad < 65:
        return 1.05
    return 1.2


def factor_antiguedad_vehiculo(anio: int) -> float:
    antiguedad = 2024 - anio
    if antiguedad < 3:
        return 1.0
    if antiguedad < 8:
        return 0.95
    if antiguedad < 15:
        return 1.1
    return 1.25


def calcular_prima_y_premio(df: pd.DataFrame, cfg: Config, rng: np.random.Generator) -> None:
    """Calculate prima and premio columns. Modifies df in place.

    Expects df to already have: suma_asegurada, plan_cobertura, zona_riesgo,
    edad_asegurado, anio_vehiculo.
    """
    n = len(df)
    tasa_base = rng.uniform(*cfg.tasa_base_rango, size=n)
    factor_cob = df["plan_cobertura"].map(cfg.factor_cobertura_tarifa).astype(float).values
    factor_z = np.array(
        [rng.uniform(*cfg.factor_prima_por_zona[z]) for z in df["zona_riesgo"].values]
    )
    factor_ed = np.array([factor_edad(e) for e in df["edad_asegurado"].values], dtype=float)
    factor_ant = np.array(
        [factor_antiguedad_vehiculo(a) for a in df["anio_vehiculo"].values], dtype=float
    )

    prima = df["suma_asegurada"].values * tasa_base * factor_cob * factor_z * factor_ed * factor_ant

    if "franquicia" in df.columns:
        factor_fr = np.array(
            [cfg.factor_franquicia.get(float(f), 1.0) for f in df["franquicia"].values]
        )
        prima *= factor_fr

    if "tiene_rastreador" in df.columns:
        prima = np.where(
            df["tiene_rastreador"].values,
            prima * cfg.factor_prima_rastreador,
            prima,
        )

    if "tipo_combustible" in df.columns:
        factor_comb = np.array(
            [cfg.factor_prima_combustible.get(str(c), 1.0) for c in df["tipo_combustible"].values]
        )
        prima *= factor_comb

    prima *= rng.uniform(0.88, 1.15, size=n)
    df["prima"] = np.round(prima, 2)

    recargo = rng.uniform(0.15, 0.25, size=n)
    df["premio"] = np.round(df["prima"].values * (1 + recargo), 2)
