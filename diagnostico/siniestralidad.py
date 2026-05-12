from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from config import Config
from diagnostico.schema import crear_distribucion, crear_metrica, crear_tabla


def _loss_ratio(df_polizas: pd.DataFrame, df_siniestros: pd.DataFrame, columna: str = "monto_reclamado") -> float:
    primas = float(df_polizas["prima"].sum())
    if primas <= 0:
        return 0.0
    if df_siniestros.empty or columna not in df_siniestros.columns:
        return 0.0
    return float(df_siniestros[columna].sum()) / primas


def _lr_por_grupo(
    df_polizas: pd.DataFrame, df_siniestros: pd.DataFrame, col_grupo: str
) -> dict[str, float]:
    if df_siniestros.empty:
        return {}
    primas = df_polizas.groupby(col_grupo)["prima"].sum()
    sin_merged = df_siniestros.merge(
        df_polizas[["id_poliza", col_grupo]], on="id_poliza", how="left"
    )
    reclamado = sin_merged.groupby(col_grupo)["monto_reclamado"].sum()
    lr = {}
    for grupo in primas.index:
        p = float(primas.loc[grupo])
        r = float(reclamado.get(grupo, 0.0))
        lr[str(grupo)] = (r / p) if p > 0 else 0.0
    return dict(sorted(lr.items()))


def _banda_calidad(factor: float) -> str:
    if factor < 0.85:
        return "estrella (<0.85)"
    if factor > 1.15:
        return "tóxico (>1.15)"
    return "neutral (0.85-1.15)"


def construir(df_polizas: pd.DataFrame, df_siniestros: pd.DataFrame, cfg: Config) -> dict[str, Any]:
    out: dict[str, Any] = {}

    primas_totales = float(df_polizas["prima"].sum())

    lr = _loss_ratio(df_polizas, df_siniestros, "monto_reclamado")
    out["loss_ratio"] = crear_metrica(
        lr, banda=cfg.target_loss, nota="reclamado / primas (banda = cfg.target_loss)"
    )

    pagado_total = float(df_siniestros["monto_pagado"].sum()) if not df_siniestros.empty and "monto_pagado" in df_siniestros.columns else 0.0
    lr_pagado = pagado_total / primas_totales if primas_totales > 0 else 0.0
    out["loss_ratio_pagado"] = crear_metrica(lr_pagado, nota="pagado / primas")

    if not df_siniestros.empty and "gasto_liquidacion" in df_siniestros.columns:
        gasto_total = float(df_siniestros["gasto_liquidacion"].sum())
        out["expense_ratio"] = crear_metrica(
            gasto_total / primas_totales if primas_totales > 0 else 0.0,
            nota="gasto de liquidación / primas",
        )
        out["combined_ratio"] = crear_metrica(
            lr_pagado + (gasto_total / primas_totales if primas_totales > 0 else 0.0),
            nota="loss ratio pagado + expense ratio",
        )

    pol_con_sin = df_siniestros["id_poliza"].nunique() if not df_siniestros.empty else 0
    freq = pol_con_sin / len(df_polizas) if len(df_polizas) > 0 else 0.0
    out["frecuencia_siniestral"] = crear_metrica(
        freq, banda=cfg.target_freq, nota="% pólizas con al menos un siniestro (banda = cfg.target_freq)"
    )

    if not df_siniestros.empty:
        out["severidad_promedio"] = crear_metrica(
            float(df_siniestros["monto_reclamado"].mean()),
            nota="monto reclamado promedio por siniestro (ARS)",
        )
        sev_tipo = (
            df_siniestros.groupby("tipo_danio")["monto_reclamado"].mean().sort_values(ascending=False)
        )
        out["severidad_por_tipo_dano"] = crear_tabla(
            {str(k): float(v) for k, v in sev_tipo.items()},
            nota="monto reclamado promedio por tipo de daño (ARS)",
        )

    out["loss_ratio_por_zona"] = crear_tabla(
        _lr_por_grupo(df_polizas, df_siniestros, "zona_riesgo"),
        nota="loss ratio por zona de riesgo",
    )
    out["loss_ratio_por_cobertura"] = crear_tabla(
        _lr_por_grupo(df_polizas, df_siniestros, "plan_cobertura"),
        nota="loss ratio por plan de cobertura",
    )

    if "factor_calidad_productor" in df_polizas.columns:
        df_aux = df_polizas.copy()
        df_aux["_banda_calidad"] = df_aux["factor_calidad_productor"].astype(float).apply(_banda_calidad)
        out["loss_ratio_por_banda_calidad_productor"] = crear_tabla(
            _lr_por_grupo(df_aux, df_siniestros, "_banda_calidad"),
            nota="loss ratio por banda de calidad de productor",
        )

    if not df_siniestros.empty and "fecha_denuncia" in df_siniestros.columns:
        fd = pd.to_datetime(df_siniestros["fecha_denuncia"])
        fs = pd.to_datetime(df_siniestros["fecha_siniestro"])
        lag = (fd - fs).dt.days
        out["lag_denuncia_p50"] = crear_metrica(
            float(np.nanpercentile(lag, 50)), nota="mediana de días entre siniestro y denuncia"
        )
        out["lag_denuncia_p90"] = crear_metrica(
            float(np.nanpercentile(lag, 90)), nota="percentil 90 de días entre siniestro y denuncia"
        )

    if not df_siniestros.empty and "estado_siniestro" in df_siniestros.columns:
        rate = float((df_siniestros["estado_siniestro"] == "Rechazado").mean())
        out["tasa_rechazo"] = crear_metrica(rate, nota="proporción de siniestros rechazados")

        if "motivo_rechazo" in df_siniestros.columns:
            rechazados = df_siniestros[df_siniestros["estado_siniestro"] == "Rechazado"]
            if len(rechazados) > 0:
                dist = rechazados["motivo_rechazo"].value_counts(normalize=True).to_dict()
                out["distribucion_motivos_rechazo"] = crear_distribucion(
                    {str(k): float(v) for k, v in dist.items()},
                    cfg.pesos_motivo_rechazo,
                    tolerancia=cfg.tolerancia_distribucion,
                    nota="share de motivos entre los siniestros rechazados",
                )

        out["distribucion_estado_siniestro"] = crear_distribucion(
            {
                str(k): float(v)
                for k, v in df_siniestros["estado_siniestro"].value_counts(normalize=True).items()
            },
            cfg.prob_estado_siniestro,
            tolerancia=cfg.tolerancia_distribucion,
            nota="share por estado del siniestro",
        )

    return out
