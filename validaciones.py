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

    # ── NEW: Estado siniestro validation ────────────────────────────────────
    if "estado_siniestro" in df_siniestros.columns:
        estados_validos = {"Cerrado", "Abierto", "Rechazado"}
        resultados["estado_siniestro_coherente"] = bool(
            df_siniestros["estado_siniestro"].isin(estados_validos).all()
        )
    else:
        resultados["estado_siniestro_coherente"] = True

    # ── NEW: Motivo rechazo only on rejected claims ─────────────────────────
    if "motivo_rechazo" in df_siniestros.columns and "estado_siniestro" in df_siniestros.columns:
        rechazados = df_siniestros["estado_siniestro"] == "Rechazado"
        no_rechazados = ~rechazados
        # All rejected should have a motivo
        rechazo_con_motivo = rechazados & df_siniestros["motivo_rechazo"].notna()
        # Non-rejected should NOT have a motivo
        no_rechazo_sin_motivo = no_rechazados & df_siniestros["motivo_rechazo"].isna()
        resultados["motivo_rechazo_coherente"] = bool(
            rechazo_con_motivo.sum() == rechazados.sum()
            and no_rechazo_sin_motivo.sum() == no_rechazados.sum()
        )
    else:
        resultados["motivo_rechazo_coherente"] = True

    # ── NEW: Financial amounts coherence ────────────────────────────────────
    if "monto_pagado" in df_siniestros.columns and "estado_siniestro" in df_siniestros.columns:
        rechazados = df_siniestros["estado_siniestro"] == "Rechazado"
        # Rejected claims must have monto_pagado == 0
        resultados["montos_financieros_coherentes"] = bool(
            (df_siniestros.loc[rechazados, "monto_pagado"] == 0.0).all()
            and (df_siniestros["monto_reservado"] >= 0).all()
            and (df_siniestros["monto_pagado"] >= 0).all()
        )
    else:
        resultados["montos_financieros_coherentes"] = True

    # ── NEW: Cancellation coherence ─────────────────────────────────────────
    if "cancelada" in df_polizas.columns:
        canceladas = df_polizas[df_polizas["cancelada"] == True]
        if len(canceladas) > 0:
            # Cancelled policies must have a cancellation date
            tiene_fecha = canceladas["fecha_cancelacion"].notna().all()
            # Cancelled policies should not be renewed
            no_renovada = (canceladas["renovada"] == False).all()
            resultados["cancelacion_coherente"] = bool(tiene_fecha and no_renovada)
        else:
            resultados["cancelacion_coherente"] = True
    else:
        resultados["cancelacion_coherente"] = True

    # ── NEW: Renewal chain coherence ────────────────────────────────────────
    if "id_cliente" in df_polizas.columns and "numero_renovacion" in df_polizas.columns:
        # Within each client, numero_renovacion should start at 0
        min_renov = df_polizas.groupby("id_cliente")["numero_renovacion"].min()
        resultados["cadena_renovacion_coherente"] = bool((min_renov == 0).all())
    else:
        resultados["cadena_renovacion_coherente"] = True

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

    # ── NEW: Renewal chain distribution ─────────────────────────────────────
    if "distribucion_renovaciones" in metricas:
        print("\n[Distribución de períodos por cliente]")
        for n_periodos, pct in metricas["distribucion_renovaciones"].items():
            print(f"- {n_periodos} período(s): {pct*100:.1f}%")

    print("\n=== FIN REPORTE ===\n")
