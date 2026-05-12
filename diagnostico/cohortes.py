from __future__ import annotations

from typing import Any

import pandas as pd

from config import Config
from diagnostico.schema import crear_distribucion, crear_metrica, crear_tabla


def construir(df_polizas: pd.DataFrame, df_siniestros: pd.DataFrame, cfg: Config) -> dict[str, Any]:
    out: dict[str, Any] = {}

    if "id_cliente" in df_polizas.columns:
        out["n_clientes_unicos"] = crear_metrica(
            int(df_polizas["id_cliente"].nunique()),
            nota="cantidad de clientes únicos en el portafolio",
        )

        periodos = df_polizas.groupby("id_cliente").size()
        dist_periodos = periodos.value_counts(normalize=True).sort_index()
        esperado_per = {str(int(k)): float(v) for k, v in cfg.pesos_periodos_cliente.items()}
        out["distribucion_periodos_cliente"] = crear_distribucion(
            {str(int(k)): float(v) for k, v in dist_periodos.items()},
            esperado_per,
            tolerancia=cfg.tolerancia_distribucion,
            nota="share de clientes por cantidad de períodos (banda contra cfg.pesos_periodos_cliente)",
        )

    if "renovada" in df_polizas.columns:
        out["tasa_renovacion"] = crear_metrica(
            float(df_polizas["renovada"].astype(bool).mean()),
            nota="proporción de pólizas marcadas como renovadas",
        )

    if "cancelada" in df_polizas.columns:
        out["tasa_cancelacion"] = crear_metrica(
            float(df_polizas["cancelada"].astype(bool).mean()),
            nota=f"proporción de pólizas canceladas mid-term (target ≈ cfg.tasa_cancelacion_base = {cfg.tasa_cancelacion_base})",
        )

    if "nivel_bonus_malus" in df_polizas.columns:
        dist_bm = df_polizas["nivel_bonus_malus"].astype(int).value_counts(normalize=True).sort_index()
        out["distribucion_bonus_malus"] = crear_distribucion(
            {str(int(k)): float(v) for k, v in dist_bm.items()},
            nota="share de pólizas por nivel de bonus-malus (0 = mejor, 5 = peor)",
        )

        if "renovada" in df_polizas.columns:
            ret = df_polizas.groupby("nivel_bonus_malus")["renovada"].mean().sort_index()
            out["retencion_por_bonus_malus"] = crear_tabla(
                {str(int(k)): float(v) for k, v in ret.items()},
                nota="tasa de renovación por nivel de bonus-malus",
            )

    return out
