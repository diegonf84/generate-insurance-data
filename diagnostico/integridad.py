from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from config import Config


def validar_integridad(df_polizas: pd.DataFrame, df_siniestros: pd.DataFrame) -> dict[str, bool]:
    resultados: dict[str, bool] = {}

    ids_polizas = set(df_polizas["id_poliza"].astype(int).values)
    ids_siniestros = set(df_siniestros["id_poliza"].astype(int).values) if not df_siniestros.empty else set()
    resultados["id_poliza_referencial"] = ids_siniestros.issubset(ids_polizas)

    if df_siniestros.empty:
        resultados["fecha_siniestro_en_vigencia"] = True
        resultados["fecha_denuncia_valida"] = True
        resultados["fecha_inicio_juicio_valida"] = True
        resultados["cobertura_casco_coherente"] = True
        resultados["bien_recuperado_coherente"] = True
        resultados["cadena_legal_coherente"] = True
        resultados["estado_siniestro_coherente"] = True
        resultados["motivo_rechazo_coherente"] = True
        resultados["montos_financieros_coherentes"] = True
        resultados["primas_y_suma_positivas"] = bool(
            (df_polizas["prima"] > 0).all() and (df_polizas["suma_asegurada"] > 0).all()
        )
        zonas_validas = {
            "CABA Premium", "CABA Resto", "GBA Norte", "GBA Sur/Oeste",
            "Media-Alta", "Media", "Baja",
        }
        resultados["zona_riesgo_valida"] = bool(
            df_polizas["zona_riesgo"].isin(zonas_validas).all()
        )
        if "cancelada" in df_polizas.columns:
            resultados["cancelacion_coherente"] = True
        if "id_cliente" in df_polizas.columns:
            resultados["cadena_renovacion_coherente"] = True
        return resultados

    merged = df_siniestros.merge(
        df_polizas[["id_poliza", "fecha_inicio_vigencia", "fecha_fin_vigencia", "plan_cobertura"]],
        on="id_poliza",
        how="left",
    )

    resultados["fecha_siniestro_en_vigencia"] = bool(
        (
            (merged["fecha_siniestro"] >= merged["fecha_inicio_vigencia"])
            & (merged["fecha_siniestro"] <= merged["fecha_fin_vigencia"])
        ).all()
    )

    resultados["fecha_denuncia_valida"] = bool((merged["fecha_denuncia"] >= merged["fecha_siniestro"]).all())

    juicio_mask = merged["fecha_inicio_juicio"].notna()
    if juicio_mask.any():
        resultados["fecha_inicio_juicio_valida"] = bool(
            (merged.loc[juicio_mask, "fecha_inicio_juicio"] >= merged.loc[juicio_mask, "fecha_denuncia"]).all()
        )
    else:
        resultados["fecha_inicio_juicio_valida"] = True

    invalida_casco = merged["cobertura_casco"] & ~merged["plan_cobertura"].isin(["Terceros Completo", "Todo Riesgo"])
    resultados["cobertura_casco_coherente"] = bool((~invalida_casco).all())

    mask_robo = merged["tipo_danio"].isin(["Robo total", "Robo parcial"])
    invalida_recupero = (~mask_robo) & merged["bien_recuperado"].notna()
    resultados["bien_recuperado_coherente"] = bool((~invalida_recupero).all())

    cadena_ok = (~merged["con_sentencia"] | merged["en_juicio"]) & (~merged["en_juicio"] | merged["en_mediacion"])
    resultados["cadena_legal_coherente"] = bool(cadena_ok.all())

    resultados["primas_y_suma_positivas"] = bool(
        (df_polizas["prima"] > 0).all() and (df_polizas["suma_asegurada"] > 0).all()
    )

    if "estado_siniestro" in df_siniestros.columns:
        estados_validos = {"Cerrado", "Abierto", "Rechazado"}
        resultados["estado_siniestro_coherente"] = bool(
            df_siniestros["estado_siniestro"].isin(estados_validos).all()
        )
    else:
        resultados["estado_siniestro_coherente"] = True

    if "motivo_rechazo" in df_siniestros.columns and "estado_siniestro" in df_siniestros.columns:
        rechazados = df_siniestros["estado_siniestro"] == "Rechazado"
        no_rechazados = ~rechazados
        rechazo_con_motivo = rechazados & df_siniestros["motivo_rechazo"].notna()
        no_rechazo_sin_motivo = no_rechazados & df_siniestros["motivo_rechazo"].isna()
        resultados["motivo_rechazo_coherente"] = bool(
            rechazo_con_motivo.sum() == rechazados.sum()
            and no_rechazo_sin_motivo.sum() == no_rechazados.sum()
        )
    else:
        resultados["motivo_rechazo_coherente"] = True

    if "monto_pagado" in df_siniestros.columns and "estado_siniestro" in df_siniestros.columns:
        rechazados = df_siniestros["estado_siniestro"] == "Rechazado"
        resultados["montos_financieros_coherentes"] = bool(
            (df_siniestros.loc[rechazados, "monto_pagado"] == 0.0).all()
            and (df_siniestros["monto_reservado"] >= 0).all()
            and (df_siniestros["monto_pagado"] >= 0).all()
        )
    else:
        resultados["montos_financieros_coherentes"] = True

    if "cancelada" in df_polizas.columns:
        canceladas = df_polizas[df_polizas["cancelada"] == True]
        if len(canceladas) > 0:
            tiene_fecha = canceladas["fecha_cancelacion"].notna().all()
            no_renovada = (canceladas["renovada"] == False).all()
            resultados["cancelacion_coherente"] = bool(tiene_fecha and no_renovada)
        else:
            resultados["cancelacion_coherente"] = True
    else:
        resultados["cancelacion_coherente"] = True

    zonas_validas = {
        "CABA Premium", "CABA Resto", "GBA Norte", "GBA Sur/Oeste",
        "Media-Alta", "Media", "Baja",
    }
    resultados["zona_riesgo_valida"] = bool(
        df_polizas["zona_riesgo"].isin(zonas_validas).all()
    )

    if "id_cliente" in df_polizas.columns and "numero_renovacion" in df_polizas.columns:
        min_renov = df_polizas.groupby("id_cliente")["numero_renovacion"].min()
        resultados["cadena_renovacion_coherente"] = bool((min_renov == 0).all())
    else:
        resultados["cadena_renovacion_coherente"] = True

    return resultados


def construir(df_polizas: pd.DataFrame, df_siniestros: pd.DataFrame, cfg: Config) -> dict[str, Any]:
    checks = validar_integridad(df_polizas, df_siniestros)
    return {
        "checks": {k: bool(v) for k, v in checks.items()},
        "todos_ok": bool(all(checks.values())),
    }
