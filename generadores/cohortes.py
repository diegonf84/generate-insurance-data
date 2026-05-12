from __future__ import annotations

import numpy as np
import pandas as pd

from config import Config
from generadores.sampling import sample_weighted
from generadores.tarifa import CATEGORIA_COBERTURA


def ajustar_renovada_por_siniestros(
    df_polizas: pd.DataFrame,
    df_siniestros: pd.DataFrame,
    rng: np.random.Generator,
) -> pd.Series:
    counts = df_siniestros.groupby("id_poliza").size()
    base = np.full(len(df_polizas), 0.75)
    id_to_idx = {pid: i for i, pid in enumerate(df_polizas["id_poliza"].values)}

    for poliza_id, n in counts.items():
        idx = id_to_idx.get(poliza_id)
        if idx is not None:
            base[idx] -= min(0.30, 0.08 * n)

    base -= np.where(df_polizas["meses_en_mora"].values >= 2, 0.10, 0.0)
    base = np.clip(base, 0.20, 0.93)
    return pd.Series(rng.random(len(df_polizas)) < base)


def asignar_cadenas_renovacion(
    df: pd.DataFrame,
    cfg: Config,
    rng: np.random.Generator,
) -> None:
    """Assign id_cliente and numero_renovacion to create cohort chains.

    Within each client, propagates vehicle/geography/demographic columns from
    the first period; later periods have inflation-adjusted primas and aging.
    """
    n = len(df)
    pesos_per = cfg.pesos_periodos_cliente
    periodos = np.array(list(pesos_per.keys()))
    probs = np.array(list(pesos_per.values()), dtype=float)
    probs = probs / probs.sum()

    media_periodos = float(np.sum(periodos * probs))
    n_clientes = int(round(n / media_periodos))

    periodos_por_cliente = rng.choice(periodos, size=n_clientes, p=probs)

    asignaciones = []
    for cid, nper in enumerate(periodos_por_cliente, start=1):
        asignaciones.extend([cid] * int(nper))

    if len(asignaciones) > n:
        asignaciones = asignaciones[:n]
    elif len(asignaciones) < n:
        next_cid = n_clientes + 1
        while len(asignaciones) < n:
            asignaciones.append(next_cid)
            next_cid += 1

    rng.shuffle(asignaciones)

    df["id_cliente"] = asignaciones

    df.sort_values(["id_cliente", "fecha_inicio_vigencia"], inplace=True)
    df["numero_renovacion"] = df.groupby("id_cliente").cumcount()

    propagate_cols = [
        "tipo_vehiculo", "marca_vehiculo", "modelo_vehiculo", "anio_vehiculo",
        "provincia", "localidad", "zona_riesgo", "barrio",
        "genero_asegurado", "ocupacion",
        "codigo_productor", "codigo_organizador",
        "medio_pago",
    ]

    first_rows = df.groupby("id_cliente").first()
    for col in propagate_cols:
        first_map = first_rows[col]
        df[col] = df["id_cliente"].map(first_map)

    df["ramo"] = cfg.ramo_principal
    df.loc[df["tipo_vehiculo"] == "Moto", "ramo"] = cfg.ramo_motovehiculos
    df["categoria_cobertura"] = df["plan_cobertura"].map(CATEGORIA_COBERTURA)

    edad_base = df.groupby("id_cliente")["edad_asegurado"].transform("first")
    df["edad_asegurado"] = np.clip(edad_base + df["numero_renovacion"], 18, 85).astype(int)

    mask_renov = df["numero_renovacion"] > 0
    n_renov = int(mask_renov.sum())
    if n_renov > 0:
        ajuste = rng.uniform(
            cfg.ajuste_prima_renovacion_rango[0],
            cfg.ajuste_prima_renovacion_rango[1],
            size=n_renov,
        )
        nums = df.loc[mask_renov, "numero_renovacion"].values
        ajuste_compuesto = ajuste ** nums
        df.loc[mask_renov, "prima"] = np.round(
            df.loc[mask_renov, "prima"].values * ajuste_compuesto, 2
        )
        df.loc[mask_renov, "premio"] = np.round(
            df.loc[mask_renov, "prima"].values * rng.uniform(1.15, 1.25, size=n_renov), 2
        )

    if cfg.prob_cambio_cobertura_renovacion > 0:
        cambio = mask_renov & (rng.random(len(df)) < cfg.prob_cambio_cobertura_renovacion)
        n_cambio = int(cambio.sum())
        if n_cambio > 0:
            nuevas_cob = sample_weighted(rng, cfg.pesos_cobertura, n_cambio)
            df.loc[cambio, "plan_cobertura"] = nuevas_cob
            df.loc[cambio, "categoria_cobertura"] = (
                df.loc[cambio, "plan_cobertura"].map(CATEGORIA_COBERTURA)
            )

    df.sort_values("id_poliza", inplace=True)
    df.reset_index(drop=True, inplace=True)
