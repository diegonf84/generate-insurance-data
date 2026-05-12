from __future__ import annotations

from typing import Any

import pandas as pd

from config import Config
from diagnostico.schema import crear_metrica, crear_tabla


def construir(df_polizas: pd.DataFrame, df_siniestros: pd.DataFrame, cfg: Config) -> dict[str, Any]:
    out: dict[str, Any] = {}

    prima = df_polizas["prima"].astype(float)
    out["prima_media"] = crear_metrica(float(prima.mean()), nota="prima media (ARS)")
    out["prima_p50"] = crear_metrica(float(prima.quantile(0.50)), nota="mediana de prima (ARS)")
    out["prima_p90"] = crear_metrica(float(prima.quantile(0.90)), nota="percentil 90 de prima (ARS)")
    out["prima_p99"] = crear_metrica(float(prima.quantile(0.99)), nota="percentil 99 de prima (ARS)")

    if "premio" in df_polizas.columns:
        out["premio_medio"] = crear_metrica(
            float(df_polizas["premio"].astype(float).mean()),
            nota="premio medio (prima + recargos/impuestos)",
        )

    pm_cob = df_polizas.groupby("plan_cobertura")["prima"].mean().sort_index()
    out["prima_media_por_cobertura"] = crear_tabla(
        {str(k): float(v) for k, v in pm_cob.items()},
        nota="prima media por plan de cobertura (ARS)",
    )

    pm_zona = df_polizas.groupby("zona_riesgo")["prima"].mean().sort_index()
    out["prima_media_por_zona"] = crear_tabla(
        {str(k): float(v) for k, v in pm_zona.items()},
        nota="prima media por zona de riesgo (ARS)",
    )

    pm_tipo = df_polizas.groupby("tipo_vehiculo")["prima"].mean().sort_index()
    out["prima_media_por_tipo_vehiculo"] = crear_tabla(
        {str(k): float(v) for k, v in pm_tipo.items()},
        nota="prima media por tipo de vehículo (ARS)",
    )

    if "cantidad_cuotas" in df_polizas.columns:
        cuotas = df_polizas["cantidad_cuotas"].astype(int).value_counts(normalize=True).sort_index()
        out["mix_cuotas"] = crear_tabla(
            {str(int(k)): float(v) for k, v in cuotas.items()},
            nota="share por cantidad de cuotas",
        )

    if "tiene_rastreador" in df_polizas.columns:
        share_zona = df_polizas.groupby("zona_riesgo")["tiene_rastreador"].mean().sort_index()
        out["share_rastreador_por_zona"] = crear_tabla(
            {str(k): float(v) for k, v in share_zona.items()},
            nota="proporción de pólizas con rastreador por zona",
        )

    return out
