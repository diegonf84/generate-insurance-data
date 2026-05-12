from __future__ import annotations

from typing import Any

import pandas as pd

from config import Config
from diagnostico.schema import crear_distribucion


def _share(serie: pd.Series) -> dict[str, float]:
    return {str(k): float(v) for k, v in serie.value_counts(normalize=True).to_dict().items()}


def construir(df_polizas: pd.DataFrame, df_siniestros: pd.DataFrame, cfg: Config) -> dict[str, Any]:
    tol = cfg.tolerancia_distribucion
    out: dict[str, Any] = {}

    out["distribucion_provincia"] = crear_distribucion(
        _share(df_polizas["provincia"]), cfg.pesos_provincia, tolerancia=tol,
        nota="share de pólizas por provincia",
    )
    out["distribucion_zona"] = crear_distribucion(
        _share(df_polizas["zona_riesgo"]), nota="share de pólizas por zona de riesgo",
    )
    out["distribucion_canal"] = crear_distribucion(
        _share(df_polizas["canal_venta"]), cfg.pesos_canal, tolerancia=tol,
        nota="share de pólizas por canal de venta",
    )
    out["distribucion_cobertura"] = crear_distribucion(
        _share(df_polizas["plan_cobertura"]), cfg.pesos_cobertura, tolerancia=tol,
        nota="share de pólizas por plan de cobertura",
    )
    out["distribucion_tipo_vehiculo"] = crear_distribucion(
        _share(df_polizas["tipo_vehiculo"]), cfg.pesos_tipo_vehiculo, tolerancia=tol,
        nota="share de pólizas por tipo de vehículo",
    )
    out["distribucion_ocupacion"] = crear_distribucion(
        _share(df_polizas["ocupacion"]), cfg.pesos_ocupacion, tolerancia=tol,
        nota="share de pólizas por ocupación del asegurado",
    )

    if "medio_pago" in df_polizas.columns:
        out["distribucion_medio_pago"] = crear_distribucion(
            _share(df_polizas["medio_pago"]), cfg.pesos_medio_pago, tolerancia=tol,
            nota="share de pólizas por medio de pago",
        )

    if "tipo_combustible" in df_polizas.columns:
        out["distribucion_combustible"] = crear_distribucion(
            _share(df_polizas["tipo_combustible"]),
            nota="share de pólizas por tipo de combustible",
        )

    if "franquicia" in df_polizas.columns:
        franq_str = df_polizas["franquicia"].apply(lambda v: f"{float(v):.2f}")
        esperado_franq = {f"{float(k):.2f}": v for k, v in cfg.pesos_franquicia.items()}
        out["distribucion_franquicia"] = crear_distribucion(
            _share(franq_str), esperado_franq, tolerancia=tol,
            nota="share de pólizas por nivel de franquicia (fracción de suma asegurada)",
        )

    if "tiene_rastreador" in df_polizas.columns:
        out["distribucion_rastreador"] = crear_distribucion(
            _share(df_polizas["tiene_rastreador"].astype(bool)),
            nota="share de pólizas con/sin rastreador",
        )

    return out
