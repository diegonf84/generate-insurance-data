from __future__ import annotations

import numpy as np
import pandas as pd

from config import Config


def sample_weighted(rng: np.random.Generator, pesos: dict, n: int) -> np.ndarray:
    valores = np.array(list(pesos.keys()))
    probs = np.array(list(pesos.values()), dtype=float)
    probs = probs / probs.sum()
    return rng.choice(valores, size=n, p=probs)


def sample_weighted_single(rng: np.random.Generator, pesos: dict) -> object:
    valores = list(pesos.keys())
    probs = np.array(list(pesos.values()), dtype=float)
    probs = probs / probs.sum()
    return rng.choice(valores, p=probs)


def sample_edad(rng: np.random.Generator, n: int) -> np.ndarray:
    n_young = int(round(n * 0.35))
    n_mature = n - n_young
    young = np.clip(rng.normal(loc=27, scale=7, size=n_young), 18, 35)
    mature = np.clip(rng.normal(loc=46, scale=12, size=n_mature), 25, 80)
    combined = np.concatenate([young, mature])
    rng.shuffle(combined)
    return np.round(combined).astype(int)


def sample_fechas_inicio(cfg: Config, rng: np.random.Generator, n: int) -> pd.Series:
    anios = np.arange(cfg.fecha_inicio.year, cfg.fecha_fin.year + 1)
    pesos_mensuales = np.array([0.07, 0.07, 0.12, 0.07, 0.07, 0.08, 0.08, 0.08, 0.07, 0.12, 0.09, 0.08])
    pesos_mensuales = pesos_mensuales / pesos_mensuales.sum()

    years = rng.choice(anios, size=n)
    months = rng.choice(np.arange(1, 13), size=n, p=pesos_mensuales)

    fechas = []
    for y, m in zip(years, months):
        first = pd.Timestamp(year=int(y), month=int(m), day=1)
        last = first + pd.offsets.MonthEnd(1)
        day = int(rng.integers(1, last.day + 1))
        fecha = pd.Timestamp(year=int(y), month=int(m), day=day)
        if fecha < pd.Timestamp(cfg.fecha_inicio):
            fecha = pd.Timestamp(cfg.fecha_inicio)
        if fecha > pd.Timestamp(cfg.fecha_fin):
            fecha = pd.Timestamp(cfg.fecha_fin)
        fechas.append(fecha.date())
    return pd.Series(fechas)
