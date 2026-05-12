from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from config import Config
from diagnostico.integridad import validar_integridad  # re-export


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

    metricas: dict[str, Any] = {
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

    # ── NEW: Additional metrics ─────────────────────────────────────────────
    if not df_siniestros.empty:
        # Pagos totales y gastos
        pagos_totales = float(df_siniestros["monto_pagado"].sum()) if "monto_pagado" in df_siniestros.columns else 0.0
        gastos_totales = float(df_siniestros["gasto_liquidacion"].sum()) if "gasto_liquidacion" in df_siniestros.columns else 0.0
        reservas_totales = float(df_siniestros["monto_reservado"].sum()) if "monto_reservado" in df_siniestros.columns else 0.0

        metricas["loss_ratio_pagado"] = pagos_totales / primas_totales if primas_totales > 0 else 0.0
        metricas["expense_ratio"] = gastos_totales / primas_totales if primas_totales > 0 else 0.0
        metricas["combined_ratio"] = metricas["loss_ratio_pagado"] + metricas["expense_ratio"]
        metricas["reservas_totales"] = reservas_totales
        metricas["pagos_totales"] = pagos_totales
        metricas["gastos_totales"] = gastos_totales

        # Estado distribution
        if "estado_siniestro" in df_siniestros.columns:
            metricas["distribucion_estado"] = df_siniestros["estado_siniestro"].value_counts(normalize=True).to_dict()

        # Rejection rate
        if "estado_siniestro" in df_siniestros.columns:
            metricas["tasa_rechazo"] = float(
                (df_siniestros["estado_siniestro"] == "Rechazado").mean()
            )
    else:
        metricas["loss_ratio_pagado"] = 0.0
        metricas["expense_ratio"] = 0.0
        metricas["combined_ratio"] = 0.0

    # Cancellation rate
    if "cancelada" in df_polizas.columns:
        metricas["tasa_cancelacion"] = float(df_polizas["cancelada"].mean())

    # Zone distribution
    metricas["distribucion_zona"] = df_polizas["zona_riesgo"].value_counts(normalize=True).to_dict()

    # Payment method distribution
    if "medio_pago" in df_polizas.columns:
        metricas["distribucion_medio_pago"] = df_polizas["medio_pago"].value_counts(normalize=True).to_dict()

    # Cohort stats
    if "id_cliente" in df_polizas.columns:
        metricas["n_clientes_unicos"] = int(df_polizas["id_cliente"].nunique())
        metricas["distribucion_renovaciones"] = (
            df_polizas.groupby("id_cliente").size().value_counts(normalize=True).sort_index().to_dict()
        )

    return metricas


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
        f"- Loss ratio global (reclamado): {loss:.4f} ({loss*100:.2f}%)"
        f" | Objetivo: {cfg.target_loss[0]*100:.0f}% - {cfg.target_loss[1]*100:.0f}%"
        f" | {'PASS' if in_loss else 'FAIL'}"
    )
    print(
        f"- Frecuencia siniestral: {freq:.4f} ({freq*100:.2f}%)"
        f" | Objetivo: {cfg.target_freq[0]*100:.0f}% - {cfg.target_freq[1]*100:.0f}%"
        f" | {'PASS' if in_freq else 'FAIL'}"
    )

    # ── NEW: Combined ratio and financial metrics ───────────────────────────
    if "loss_ratio_pagado" in metricas:
        lr_pagado = metricas["loss_ratio_pagado"]
        expense = metricas["expense_ratio"]
        combined = metricas["combined_ratio"]
        print(f"- Loss ratio (pagado): {lr_pagado:.4f} ({lr_pagado*100:.2f}%)")
        print(f"- Expense ratio: {expense:.4f} ({expense*100:.2f}%)")
        print(f"- Combined ratio: {combined:.4f} ({combined*100:.2f}%)")

    if "tasa_rechazo" in metricas:
        print(f"- Tasa de rechazo: {metricas['tasa_rechazo']*100:.2f}%")

    if "tasa_cancelacion" in metricas:
        print(f"- Tasa de cancelación: {metricas['tasa_cancelacion']*100:.2f}%")

    if "n_clientes_unicos" in metricas:
        print(f"- Clientes únicos: {metricas['n_clientes_unicos']:,}")

    print("- Distribución por provincia:", "PASS" if metricas["ok_distribucion_provincia"] else "FAIL")
    print("- Distribución por canal:", "PASS" if metricas["ok_distribucion_canal"] else "FAIL")
    print("- Distribución por cobertura:", "PASS" if metricas["ok_distribucion_cobertura"] else "FAIL")

    print("\n[Severidad promedio por tipo de daño]")
    if not metricas["severidad_promedio_tipo"]:
        print("- Sin siniestros para reportar")
    else:
        for tipo, sev in metricas["severidad_promedio_tipo"].items():
            print(f"- {tipo}: ARS {sev:,.2f}")

    if "distribucion_zona" in metricas:
        print("\n[Distribución por zona de riesgo]")
        for zona, pct in metricas["distribucion_zona"].items():
            print(f"- {zona}: {pct*100:.1f}%")

    if "distribucion_medio_pago" in metricas:
        print("\n[Distribución por medio de pago]")
        for mp, pct in metricas["distribucion_medio_pago"].items():
            print(f"- {mp}: {pct*100:.1f}%")

    # ── NEW: Renewal chain distribution ─────────────────────────────────────
    if "distribucion_renovaciones" in metricas:
        print("\n[Distribución de períodos por cliente]")
        for n_periodos, pct in metricas["distribucion_renovaciones"].items():
            print(f"- {n_periodos} período(s): {pct*100:.1f}%")

    print("\n=== FIN REPORTE ===\n")
