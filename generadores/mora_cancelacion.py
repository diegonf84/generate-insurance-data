from __future__ import annotations

from datetime import timedelta

import numpy as np
import pandas as pd

from config import Config
from generadores.sampling import sample_weighted_single


def sample_mora(
    rng: np.random.Generator,
    zona: str,
    canal: str,
    medio_pago: str,
    cfg: Config,
) -> int:
    prob_activa = cfg.prob_mora_por_medio_pago.get(medio_pago, 0.15)
    if rng.random() >= prob_activa:
        return 0

    probs = np.array([0.70, 0.15, 0.08, 0.05, 0.02], dtype=float)
    if zona in {"Muy Alta", "Alta"}:
        probs += np.array([-0.05, 0.02, 0.01, 0.01, 0.01])
    elif zona == "Media-Alta":
        probs += np.array([-0.03, 0.01, 0.01, 0.005, 0.005])
    if canal in {"Online", "Directa"}:
        probs += np.array([-0.03, 0.01, 0.01, 0.005, 0.005])
    probs = np.clip(probs, 0.001, None)
    probs = probs / probs.sum()
    bucket = int(rng.choice(np.arange(5), p=probs))
    if bucket < 4:
        return bucket
    return int(rng.integers(4, 7))


def aplicar_mora(df: pd.DataFrame, cfg: Config, rng: np.random.Generator) -> None:
    df["meses_en_mora"] = [
        sample_mora(rng, zona, canal, medio_pago, cfg)
        for zona, canal, medio_pago in zip(
            df["zona_riesgo"].values,
            df["canal_venta"].values,
            df["medio_pago"].values,
        )
    ]


def aplicar_cancelaciones(
    df_polizas: pd.DataFrame,
    cfg: Config,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Assign mid-term cancellations to a fraction of policies.

    Adds columns: `cancelada`, `fecha_cancelacion`, `motivo_cancelacion`.
    Cancelled policies also get `renovada = False`.
    """
    n = len(df_polizas)

    p_cancel = np.full(n, cfg.tasa_cancelacion_base)
    mora_alta = df_polizas["meses_en_mora"].values >= cfg.mora_umbral_cancelacion
    p_cancel[mora_alta] *= 2.5

    joven = df_polizas["edad_asegurado"].values < 28
    p_cancel[joven] *= 1.20

    p_cancel = np.clip(p_cancel, 0.0, 0.50)
    cancelada = rng.random(n) < p_cancel

    df_polizas["cancelada"] = cancelada
    df_polizas["fecha_cancelacion"] = pd.NaT
    df_polizas["motivo_cancelacion"] = pd.NA

    idx_cancel = df_polizas.index[cancelada]
    if len(idx_cancel) > 0:
        for idx in idx_cancel:
            inicio = df_polizas.at[idx, "fecha_inicio_vigencia"]
            fin = df_polizas.at[idx, "fecha_fin_vigencia"]
            max_dias = max(30, (fin - inicio).days - 30)
            lag = int(rng.integers(30, max_dias + 1))
            df_polizas.at[idx, "fecha_cancelacion"] = pd.Timestamp(inicio + timedelta(days=lag))

            if df_polizas.at[idx, "meses_en_mora"] >= cfg.mora_umbral_cancelacion:
                if rng.random() < 0.65:
                    df_polizas.at[idx, "motivo_cancelacion"] = "Mora prolongada"
                else:
                    df_polizas.at[idx, "motivo_cancelacion"] = str(
                        sample_weighted_single(rng, cfg.pesos_motivo_cancelacion)
                    )
            else:
                df_polizas.at[idx, "motivo_cancelacion"] = str(
                    sample_weighted_single(rng, cfg.pesos_motivo_cancelacion)
                )

        df_polizas.loc[cancelada, "renovada"] = False

    return df_polizas
