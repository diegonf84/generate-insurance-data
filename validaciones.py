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
        resultados["primas_y_suma_positivas"] = bool((df_polizas["prima"] > 0).all() and (df_polizas["suma_asegurada"] > 0).all())
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

    resultados["primas_y_suma_positivas"] = bool((df_polizas["prima"] > 0).all() and (df_polizas["suma_asegurada"] > 0).all())
    return resultados


def _comparar_distribucion(
    serie: pd.Series,
    esperado: dict[str, float],
    tolerancia: float,
) -> tuple[bool, dict[str, dict[str, float]]]:
    obs = serie.value_counts(normalize=True).to_dict()
    detalle = {}
    ok = True
    for k, p in esperado.items():
        o = float(obs.get(k, 0.0))
        diff = abs(o - p)
        detalle[k] = {"observado": o, "esperado": p, "desvio": diff}
        if diff > tolerancia:
            ok = False
    return ok, detalle


def calcular_metricas(df_polizas: pd.DataFrame, df_siniestros: pd.DataFrame, cfg: Config) -> dict[str, Any]:
    primas_totales = float(df_polizas["prima"].sum())
    siniestros_totales = float(df_siniestros["monto_reclamado"].sum()) if not df_siniestros.empty else 0.0

    loss_ratio = siniestros_totales / primas_totales if primas_totales > 0 else 0.0

    polizas_con_siniestro = df_siniestros["id_poliza"].nunique() if not df_siniestros.empty else 0
    frecuencia = polizas_con_siniestro / len(df_polizas) if len(df_polizas) > 0 else 0.0

    severidad_promedio = (
        df_siniestros.groupby("tipo_danio")["monto_reclamado"].mean().sort_values(ascending=False).to_dict()
        if not df_siniestros.empty
        else {}
    )

    ok_prov, detalle_prov = _comparar_distribucion(df_polizas["provincia"], cfg.pesos_provincia, cfg.tolerancia_distribucion)
    ok_canal, detalle_canal = _comparar_distribucion(df_polizas["canal_venta"], cfg.pesos_canal, cfg.tolerancia_distribucion)
    ok_cob, detalle_cob = _comparar_distribucion(df_polizas["plan_cobertura"], cfg.pesos_cobertura, cfg.tolerancia_distribucion)

    return {
        "loss_ratio": loss_ratio,
        "frecuencia_siniestral": frecuencia,
        "severidad_promedio_tipo": severidad_promedio,
        "ok_distribucion_provincia": ok_prov,
        "ok_distribucion_canal": ok_canal,
        "ok_distribucion_cobertura": ok_cob,
        "detalle_provincia": detalle_prov,
        "detalle_canal": detalle_canal,
        "detalle_cobertura": detalle_cob,
    }


def imprimir_reporte(validaciones: dict[str, bool], metricas: dict[str, Any], cfg: Config) -> None:
    print("\n=== REPORTE DE VALIDACION ===")
    print("\n[Integridad y coherencia]")
    for clave, ok in validaciones.items():
        estado = "PASS" if ok else "FAIL"
        print(f"- {clave}: {estado}")

    print("\n[Métricas de control]")
    loss = metricas["loss_ratio"]
    freq = metricas["frecuencia_siniestral"]

    in_loss = cfg.target_loss[0] <= loss <= cfg.target_loss[1]
    in_freq = cfg.target_freq[0] <= freq <= cfg.target_freq[1]

    print(
        f"- Loss ratio global: {loss:.4f} ({loss*100:.2f}%) | Objetivo: {cfg.target_loss[0]*100:.0f}% - {cfg.target_loss[1]*100:.0f}% | {'PASS' if in_loss else 'FAIL'}"
    )
    print(
        f"- Frecuencia siniestral: {freq:.4f} ({freq*100:.2f}%) | Objetivo: {cfg.target_freq[0]*100:.0f}% - {cfg.target_freq[1]*100:.0f}% | {'PASS' if in_freq else 'FAIL'}"
    )

    print("- Distribución por provincia:", "PASS" if metricas["ok_distribucion_provincia"] else "FAIL")
    print("- Distribución por canal:", "PASS" if metricas["ok_distribucion_canal"] else "FAIL")
    print("- Distribución por cobertura:", "PASS" if metricas["ok_distribucion_cobertura"] else "FAIL")

    print("\n[Severidad promedio por tipo de daño]")
    if not metricas["severidad_promedio_tipo"]:
        print("- Sin siniestros para reportar")
    else:
        for tipo, sev in metricas["severidad_promedio_tipo"].items():
            print(f"- {tipo}: ARS {sev:,.2f}")

    print("\n=== FIN REPORTE ===\n")
