from __future__ import annotations

from datetime import timedelta

import numpy as np
import pandas as pd

from config import Config
from generadores.cohortes import (
    ajustar_renovada_por_siniestros,
    asignar_cadenas_renovacion,
)
from generadores.geografia import asignar_geografia
from generadores.mora_cancelacion import aplicar_cancelaciones, aplicar_mora
from generadores.sampling import sample_edad, sample_fechas_inicio, sample_weighted
from generadores.tarifa import CATEGORIA_COBERTURA, calcular_prima_y_premio
from generadores.vehiculos import (
    estimar_valor_vehiculo,
    generar_catalogo_vehiculos,
    muestrear_anio_vehiculo,
)


__all__ = ["ajustar_renovada_por_siniestros", "generar_polizas"]


def _asignar_vigencia(df: pd.DataFrame, cfg: Config, rng: np.random.Generator) -> None:
    n = len(df)
    df["fecha_inicio_vigencia"] = sample_fechas_inicio(cfg, rng, n)
    df["fecha_fin_vigencia"] = df["fecha_inicio_vigencia"].apply(
        lambda d: d + timedelta(days=365)
    )
    df["numero_poliza"] = [
        f"AUT-{f.year}-{i:06d}"
        for i, f in zip(df["id_poliza"], df["fecha_inicio_vigencia"])
    ]


def _asignar_demograficos(df: pd.DataFrame, cfg: Config, rng: np.random.Generator) -> None:
    n = len(df)
    df["edad_asegurado"] = sample_edad(rng, n)
    df["genero_asegurado"] = sample_weighted(rng, cfg.pesos_genero, n)
    df["estado_civil"] = sample_weighted(rng, cfg.pesos_estado_civil, n)
    df["ocupacion"] = sample_weighted(rng, cfg.pesos_ocupacion, n)
    df["canal_venta"] = sample_weighted(rng, cfg.pesos_canal, n)
    df["medio_pago"] = sample_weighted(rng, cfg.pesos_medio_pago, n)


def _asignar_productor_organizador(
    df: pd.DataFrame, cfg: Config, rng: np.random.Generator
) -> None:
    n = len(df)
    productores = np.array([f"PROD-{i:04d}" for i in range(1, cfg.n_productores + 1)])
    ranks = np.arange(1, cfg.n_productores + 1)
    probs_prod = 1 / np.power(ranks, 1.15)
    probs_prod = probs_prod / probs_prod.sum()
    df["codigo_productor"] = rng.choice(productores, size=n, p=probs_prod)

    rank_map = {prod: idx + 1 for idx, prod in enumerate(productores)}
    ranks_asignados = np.array(
        [rank_map[p] for p in df["codigo_productor"].values], dtype=float
    )
    antig = (
        240
        - (ranks_asignados / ranks_asignados.max()) * 180
        + rng.normal(0, 15, size=n)
    )
    df["tiempo_productor_cia_meses"] = np.clip(np.round(antig), 1, 240).astype(int)

    organizadores = [f"ORG-{i:02d}" for i in range(1, cfg.n_organizadores + 1)]
    rng_org = np.random.default_rng(cfg.random_seed + 999)
    prod_to_org: dict[str, str | None] = {}
    for prod in productores:
        if rng_org.random() < cfg.prob_productor_en_organizador:
            prod_to_org[prod] = str(rng_org.choice(organizadores))
        else:
            prod_to_org[prod] = None
    df["codigo_organizador"] = df["codigo_productor"].map(prod_to_org)

    comisiones = []
    for canal in df["canal_venta"].values:
        low, high = cfg.comision_por_canal[str(canal)]
        if low == high:
            comisiones.append(low)
        else:
            comisiones.append(float(rng.uniform(low, high)))
    df["comision_pactada"] = np.round(comisiones, 4)


def _asignar_vehiculo(df: pd.DataFrame, cfg: Config, rng: np.random.Generator) -> None:
    n = len(df)
    catalogo = generar_catalogo_vehiculos()
    catalogo_por_tipo: dict[str, dict] = {}
    for tipo, grp in catalogo.groupby("tipo_vehiculo"):
        grp = grp.reset_index(drop=True)
        probs = grp["peso_relativo"].astype(float).values
        probs = probs / probs.sum()
        catalogo_por_tipo[str(tipo)] = {"df": grp, "probs": probs}
    tipo_vehiculos = sample_weighted(rng, cfg.pesos_tipo_vehiculo, n)

    marcas = []
    modelos = []
    valores_base = []
    for tv in tipo_vehiculos:
        entry = catalogo_por_tipo[str(tv)]
        opciones = entry["df"]
        idx = int(rng.choice(len(opciones), p=entry["probs"]))
        marcas.append(str(opciones.loc[idx, "marca_vehiculo"]))
        modelos.append(str(opciones.loc[idx, "modelo_vehiculo"]))
        valores_base.append(float(opciones.loc[idx, "valor_base_2024"]))

    df["marca_vehiculo"] = marcas
    df["modelo_vehiculo"] = modelos
    df["tipo_vehiculo"] = [str(tv) for tv in tipo_vehiculos]
    df.loc[df["tipo_vehiculo"] == "Moto", "ramo"] = cfg.ramo_motovehiculos

    df["anio_vehiculo"] = muestrear_anio_vehiculo(rng, n)
    valores = np.array(
        [
            estimar_valor_vehiculo(vb, anio)
            for vb, anio in zip(valores_base, df["anio_vehiculo"].values)
        ],
        dtype=float,
    )
    valores *= rng.uniform(0.88, 1.15, size=n)
    df["suma_asegurada"] = np.clip(valores, 1_500_000, 45_000_000).round(2)

    n_outliers = max(1, int(n * cfg.p_outlier_poliza))
    outlier_idx = rng.choice(n, size=n_outliers, replace=False)
    df.loc[outlier_idx, "suma_asegurada"] = (
        valores[outlier_idx] * rng.uniform(2.0, 4.0, size=n_outliers)
    ).round(2)


def _asignar_uso(df: pd.DataFrame, cfg: Config, rng: np.random.Generator) -> None:
    n = len(df)
    df["tipo_uso"] = sample_weighted(rng, cfg.pesos_uso, n)
    df["es_flota"] = rng.random(n) < 0.02
    df.loc[df["es_flota"], "tipo_uso"] = "Comercial"


def _aplicar_renovacion_base(df: pd.DataFrame, rng: np.random.Generator) -> None:
    n = len(df)
    prob_base_renov = 0.75 - np.where(df["meses_en_mora"].values >= 2, 0.08, 0.0)
    prob_base_renov = np.clip(prob_base_renov, 0.20, 0.93)
    df["renovada"] = rng.random(n) < prob_base_renov


def generar_polizas(cfg: Config, seed: int | None = None) -> pd.DataFrame:
    rng = np.random.default_rng(cfg.random_seed if seed is None else seed)
    n = cfg.cantidad_polizas

    df = pd.DataFrame({"id_poliza": np.arange(1, n + 1, dtype=int)})

    _asignar_vigencia(df, cfg, rng)

    df["ramo"] = cfg.ramo_principal
    df["plan_cobertura"] = sample_weighted(rng, cfg.pesos_cobertura, n)

    asignar_geografia(df, cfg, rng)
    _asignar_demograficos(df, cfg, rng)
    _asignar_productor_organizador(df, cfg, rng)
    _asignar_vehiculo(df, cfg, rng)
    _asignar_uso(df, cfg, rng)

    df["categoria_cobertura"] = df["plan_cobertura"].map(CATEGORIA_COBERTURA)

    calcular_prima_y_premio(df, cfg, rng)
    aplicar_mora(df, cfg, rng)
    _aplicar_renovacion_base(df, rng)

    asignar_cadenas_renovacion(df, cfg, rng)
    aplicar_cancelaciones(df, cfg, rng)

    return df
