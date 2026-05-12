from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from config import Config
from diagnostico.schema import crear_distribucion, crear_metrica, crear_tabla


def _banda_calidad(factor: float) -> str:
    if factor < 0.85:
        return "estrella (<0.85)"
    if factor > 1.15:
        return "tóxico (>1.15)"
    return "neutral (0.85-1.15)"


def construir(df_polizas: pd.DataFrame, df_siniestros: pd.DataFrame, cfg: Config) -> dict[str, Any]:
    out: dict[str, Any] = {}

    polizas_por_prod = df_polizas["codigo_productor"].value_counts(normalize=True)
    if len(polizas_por_prod) > 0:
        top_sorted = polizas_por_prod.sort_values(ascending=False)
        out["top1_share"] = crear_metrica(
            float(top_sorted.iloc[0]), nota="share del productor #1",
        )
        out["top5_share"] = crear_metrica(
            float(top_sorted.head(5).sum()), nota="share acumulado del top 5",
        )
        out["top10_share"] = crear_metrica(
            float(top_sorted.head(10).sum()), nota="share acumulado del top 10",
        )

        shares = top_sorted.values
        hhi = float(np.sum(shares ** 2))
        out["herfindahl_hhi"] = crear_metrica(
            hhi, nota="índice de Herfindahl-Hirschman (Σ share²); 0 = perfecta competencia, 1 = monopolio",
        )

        out["n_productores_activos"] = crear_metrica(
            int(len(polizas_por_prod)),
            nota=f"productores con ≥ 1 póliza (configurados: {cfg.n_productores})",
        )

    if "factor_calidad_productor" in df_polizas.columns:
        productores_unicos = df_polizas.drop_duplicates("codigo_productor")[
            ["codigo_productor", "factor_calidad_productor"]
        ]
        factores = productores_unicos["factor_calidad_productor"].astype(float)
        bandas = factores.apply(_banda_calidad)
        dist_bandas = bandas.value_counts(normalize=True)
        out["distribucion_calidad_productor"] = crear_distribucion(
            {str(k): float(v) for k, v in dist_bandas.items()},
            nota="share de productores por banda de calidad (estrella / neutral / tóxico)",
        )
        out["factor_calidad_promedio"] = crear_metrica(
            float(factores.mean()),
            nota="factor de calidad promedio (centrado teórico = 1.0)",
        )
        out["factor_calidad_std"] = crear_metrica(
            float(factores.std()),
            nota=f"desvío estándar del factor (configurado: {cfg.factor_calidad_productor_sigma})",
        )

        df_aux = df_polizas.copy()
        df_aux["_banda"] = df_aux["factor_calidad_productor"].astype(float).apply(_banda_calidad)

        if not df_siniestros.empty:
            primas = df_aux.groupby("_banda")["prima"].sum()
            sin_merged = df_siniestros.merge(
                df_aux[["id_poliza", "_banda"]], on="id_poliza", how="left"
            )
            reclamado = sin_merged.groupby("_banda")["monto_reclamado"].sum()
            lr_banda = {}
            for b in primas.index:
                p = float(primas.loc[b])
                r = float(reclamado.get(b, 0.0))
                lr_banda[str(b)] = (r / p) if p > 0 else 0.0
            out["loss_ratio_por_banda_calidad"] = crear_tabla(
                lr_banda, nota="loss ratio por banda de calidad de productor",
            )

    return out
