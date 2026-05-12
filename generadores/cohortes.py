from __future__ import annotations

import numpy as np
import pandas as pd

from config import Config
from generadores.sampling import sample_weighted
from generadores.tarifa import CATEGORIA_COBERTURA


def _simular_bonus_malus(
    numero_renovacion: np.ndarray,
    cfg: Config,
    rng: np.random.Generator,
) -> np.ndarray:
    """Random-walk bonus-malus level per policy.

    Each renewal: with probability p_sin_claim the level decreases by 1
    (no claims in prior period), otherwise it increases by 1. Clipped to
    [0, 5]. Starting level for renovacion=0 is `bonus_malus_nivel_inicial`.
    """
    p_sin = cfg.bonus_malus_p_sin_claim
    inicial = cfg.bonus_malus_nivel_inicial
    n = len(numero_renovacion)
    niveles = np.full(n, inicial, dtype=int)
    max_renov = int(numero_renovacion.max()) if n > 0 else 0
    if max_renov == 0:
        return niveles

    # Vectorized walk: precompute a transition matrix per step
    for step in range(1, max_renov + 1):
        mask = numero_renovacion >= step
        if not mask.any():
            break
        ups = rng.random(int(mask.sum())) >= p_sin
        delta = np.where(ups, 1, -1)
        niveles[mask] = np.clip(niveles[mask] + delta, 0, 5)
    return niveles


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
        "medio_pago", "cantidad_cuotas",
        "franquicia", "tiene_rastreador", "tipo_combustible",
    ]
    propagate_cols = [c for c in propagate_cols if c in df.columns]

    first_rows = df.groupby("id_cliente").first()
    for col in propagate_cols:
        first_map = first_rows[col]
        df[col] = df["id_cliente"].map(first_map)

    df["ramo"] = cfg.ramo_principal
    df.loc[df["tipo_vehiculo"] == "Moto", "ramo"] = cfg.ramo_motovehiculos
    df["categoria_cobertura"] = df["plan_cobertura"].map(CATEGORIA_COBERTURA)

    edad_base = df.groupby("id_cliente")["edad_asegurado"].transform("first")
    df["edad_asegurado"] = np.clip(edad_base + df["numero_renovacion"], 18, 85).astype(int)

    df["nivel_bonus_malus"] = _simular_bonus_malus(
        df["numero_renovacion"].values, cfg, rng
    )

    if "antiguedad_carnet_anios" in df.columns:
        carnet_base = df.groupby("id_cliente")["antiguedad_carnet_anios"].transform("first")
        df["antiguedad_carnet_anios"] = np.clip(
            carnet_base + df["numero_renovacion"], 0, 70
        ).astype(int)

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

    factor_bm = np.array(
        [cfg.factor_bonus_malus.get(int(n), 1.0) for n in df["nivel_bonus_malus"].values]
    )
    df["prima"] = np.round(df["prima"].values * factor_bm, 2)
    df["premio"] = np.round(df["premio"].values * factor_bm, 2)

    if cfg.prob_cambio_cobertura_renovacion > 0:
        cambio = mask_renov & (rng.random(len(df)) < cfg.prob_cambio_cobertura_renovacion)
        n_cambio = int(cambio.sum())
        if n_cambio > 0:
            nuevas_cob = sample_weighted(rng, cfg.pesos_cobertura, n_cambio)
            df.loc[cambio, "plan_cobertura"] = nuevas_cob
            df.loc[cambio, "categoria_cobertura"] = (
                df.loc[cambio, "plan_cobertura"].map(CATEGORIA_COBERTURA)
            )

    if "franquicia" in df.columns:
        # Franquicia only applies to plans with casco coverage. Force to 0
        # for any row whose plan_cobertura ended up as Responsabilidad Civil.
        df.loc[df["plan_cobertura"] == "Responsabilidad Civil", "franquicia"] = 0.0
        # Rows that gained casco coverage on renewal but had franquicia=0 from
        # the original RC plan get a fresh franquicia sample.
        sin_franquicia_con_casco = (
            df["plan_cobertura"].isin(["Terceros Completo", "Todo Riesgo"])
            & (df["franquicia"] == 0.0)
            & (df["numero_renovacion"] > 0)
        )
        n_resample = int(sin_franquicia_con_casco.sum())
        if n_resample > 0:
            df.loc[sin_franquicia_con_casco, "franquicia"] = (
                sample_weighted(rng, cfg.pesos_franquicia, n_resample).astype(float)
            )

    df.sort_values("id_poliza", inplace=True)
    df.reset_index(drop=True, inplace=True)
