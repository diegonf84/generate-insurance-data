from __future__ import annotations

import calendar
from datetime import date, timedelta

import numpy as np
import pandas as pd

from config import Config

# Monthly claim weight arrays by damage type (normalized, index 0=Jan … 11=Dec)
_PESOS_MES_DANIO: dict[str, list[float]] = {
    k: [x / sum(v) for x in v]
    for k, v in {
        #                              Jan  Feb  Mar  Apr  May  Jun  Jul  Aug  Sep  Oct  Nov  Dec
        "Granizo":                    [12., 12., 10.,  3.,  2.,  2.,  2.,  2.,  3., 10., 16., 14.],
        "Choque":                     [ 8.,  7.,  8.,  8.,  8.,  9., 10., 10.,  8.,  8.,  8.,  8.],
        "Robo total":                 [12., 12.,  9.,  8.,  7.,  7.,  7.,  7.,  8.,  8.,  7.,  8.],
        "Robo parcial":               [12., 12.,  9.,  8.,  7.,  7.,  7.,  7.,  8.,  8.,  7.,  8.],
        "Incendio":                   [ 8.,  8.,  8.,  8.,  8.,  9.,  9.,  9.,  8.,  8.,  8.,  9.],
        "Daño a terceros":            [ 8.,  8.,  8.,  8.,  8.,  9.,  9.,  9.,  8.,  8.,  8.,  9.],
        "Daño a terceros con lesiones":[ 8.,  8.,  8.,  8.,  8.,  9.,  9.,  9.,  8.,  8.,  8.,  9.],
        "Cristales":                  [ 9.,  9.,  8.,  7.,  7.,  7.,  7.,  8.,  9., 10.,  9., 10.],
        "Vandalismo":                 [10., 10.,  8.,  7.,  7.,  7.,  7.,  7.,  7.,  8., 10., 12.],
        "Inundación":                 [12., 12., 10.,  6.,  5.,  4.,  4.,  4.,  5., 10., 14., 14.],
        "Otros":                      [ 8.,  8.,  8.,  8.,  8.,  8.,  8.,  8.,  9.,  9.,  9.,  9.],
    }.items()
}


def _sample_weighted(rng: np.random.Generator, pesos: dict[str, float]) -> str:
    vals = np.array(list(pesos.keys()))
    probs = np.array(list(pesos.values()), dtype=float)
    probs = probs / probs.sum()
    return str(rng.choice(vals, p=probs))


def _lambda_por_segmento(row: pd.Series, cfg: Config) -> float:
    zona = row["zona_riesgo"]
    edad = int(row["edad_asegurado"])
    uso = row["tipo_uso"]

    lam = cfg.factor_frecuencia_por_zona.get(zona, 0.12)

    # Age + usage modifier
    if edad < 25 and uso in {"Comercial", "Profesional"}:
        lam *= 1.60
    elif edad < 25:
        lam *= 1.30
    elif edad > 55:
        lam *= 1.05

    if uso in {"Comercial", "Profesional"}:
        lam *= 1.15
    if row["plan_cobertura"] == "Todo Riesgo":
        lam *= 1.15

    tipo_vehiculo = row.get("tipo_vehiculo", "Auto")
    if tipo_vehiculo == "Moto":
        lam *= 1.7
    elif tipo_vehiculo == "Camioneta":
        lam *= 0.85

    # Demographic frequency factors
    estado_civil = row.get("estado_civil", "")
    ocupacion = row.get("ocupacion", "")
    factores = cfg.factor_demografico_frecuencia

    if estado_civil == "Soltero" and edad < 25:
        lam *= factores.get("soltero_joven", 1.0)
    if ocupacion == "Jubilado":
        lam *= factores.get("jubilado", 1.0)
    if estado_civil == "Divorciado" and edad < 35:
        lam *= factores.get("divorciado_joven", 1.0)

    # Driving experience (años de carnet)
    antig_carnet = int(row.get("antiguedad_carnet_anios", 0))
    factores_carnet = cfg.factor_antiguedad_carnet
    if antig_carnet < 2:
        lam *= factores_carnet.get("novel", 1.0)
    elif antig_carnet < 5:
        lam *= factores_carnet.get("intermedio", 1.0)
    elif antig_carnet >= 10:
        lam *= factores_carnet.get("experimentado", 1.0)
    else:
        lam *= factores_carnet.get("establecido", 1.0)

    # Productor quality
    lam *= float(row.get("factor_calidad_productor", 1.0))

    return lam


def _construir_pesos_lag(cfg: Config, dias_total: int) -> np.ndarray:
    """Build per-day lag weights over [0, dias_total] from the mixture in cfg.

    Each regime contributes uniformly within its day range; total mass
    matches the regime's `peso`. Days outside any defined range get the
    "normal" regime weight as fallback.
    """
    pesos = np.zeros(dias_total + 1, dtype=float)
    normal_per_day = 0.0
    for regimen in cfg.pesos_lag_siniestro.values():
        lo, hi = regimen["rango_dias"]
        peso_total = regimen["peso"]
        span = hi - lo + 1
        per_day = peso_total / span
        d_lo = max(0, lo)
        d_hi = min(dias_total, hi)
        if d_hi >= d_lo:
            pesos[d_lo : d_hi + 1] = per_day
        if lo <= 91 <= hi:
            normal_per_day = per_day
    # Fallback for any day past the last defined range (e.g. policies > 365 days)
    if normal_per_day > 0:
        pesos[pesos == 0.0] = normal_per_day
    if pesos.sum() == 0:
        pesos[:] = 1.0
    return pesos


def _sample_fecha_siniestro(
    rng: np.random.Generator,
    inicio: date,
    fin: date,
    tipo_danio: str,
    cfg: Config,
) -> date:
    """Sample claim date combining month-of-year seasonality and lag-from-start.

    Per-day weight = peso_lag(d) * peso_mes(month(inicio + d)), normalized over
    [inicio, fin]. The lag mixture comes from cfg.pesos_lag_siniestro; the
    monthly weights from _PESOS_MES_DANIO.
    """
    dias_total = max(0, (fin - inicio).days)
    if dias_total == 0:
        return inicio

    pesos_lag = _construir_pesos_lag(cfg, dias_total)
    pesos_mes = _PESOS_MES_DANIO.get(tipo_danio)

    if pesos_mes is not None:
        meses = np.array(
            [(inicio + timedelta(days=int(d))).month for d in range(dias_total + 1)]
        )
        pesos_mes_arr = np.array(pesos_mes)[meses - 1]
        pesos = pesos_lag * pesos_mes_arr
    else:
        pesos = pesos_lag

    total = pesos.sum()
    if total <= 0:
        return inicio + timedelta(days=int(rng.integers(0, dias_total + 1)))
    pesos = pesos / total
    dia_offset = int(rng.choice(dias_total + 1, p=pesos))
    return inicio + timedelta(days=dia_offset)


def _terceros_involucrados(rng: np.random.Generator, tipo_danio: str) -> bool:
    if tipo_danio in {"Daño a terceros", "Daño a terceros con lesiones"}:
        return True
    if tipo_danio == "Choque":
        return bool(rng.random() < 0.60)
    return False


_DANIOS_CASCO: frozenset[str] = frozenset({
    "Robo total", "Robo parcial", "Choque", "Incendio", "Granizo",
    "Cristales", "Vandalismo", "Inundación", "Otros",
})

_DANIOS_RC: frozenset[str] = frozenset({
    "Daño a terceros", "Daño a terceros con lesiones",
})


def _cobertura_casco(plan: str, tipo_danio: str) -> bool:
    if plan not in {"Terceros Completo", "Todo Riesgo"}:
        return False
    return tipo_danio in _DANIOS_CASCO


def _bien_recuperado(rng: np.random.Generator, tipo_danio: str):
    if tipo_danio == "Robo total":
        return bool(rng.random() < 0.20)
    if tipo_danio == "Robo parcial":
        return bool(rng.random() < 0.45)
    return pd.NA


def _p90_lognormal(mu: float, sigma: float) -> float:
    z90 = 1.2815515655446004
    return float(np.exp(mu + sigma * z90))


def _asignar_estado_siniestro(
    rng: np.random.Generator,
    cfg: Config,
    monto: float,
    en_juicio: bool,
    meses_mora: int,
) -> str:
    """Determine claim status with contextual biases."""
    probs = dict(cfg.prob_estado_siniestro)

    # Claims in litigation are less likely to be closed
    if en_juicio:
        probs["Abierto"] = probs.get("Abierto", 0.25) * 1.8
        probs["Cerrado"] = probs.get("Cerrado", 0.68) * 0.6

    # High-mora policies more likely to have rejected claims
    if meses_mora >= 3:
        probs["Rechazado"] = probs.get("Rechazado", 0.07) * 2.0

    vals = list(probs.keys())
    p = np.array(list(probs.values()), dtype=float)
    p = p / p.sum()
    return str(rng.choice(vals, p=p))


def _calcular_montos_financieros(
    rng: np.random.Generator,
    cfg: Config,
    monto_reclamado: float,
    estado: str,
    cobertura_casco: bool,
    franquicia_pesos: float,
) -> tuple[float, float]:
    """Return (monto_reservado, monto_pagado) based on claim status.

    Franquicia (deductible) is deducted from monto_pagado only when the claim
    is paid under casco coverage. RC claims pay the third party directly, so
    the deductible does not apply.
    """
    reserva = monto_reclamado * rng.uniform(*cfg.factor_reserva_rango)
    reserva = round(max(0, reserva), 2)

    if estado == "Rechazado":
        return reserva, 0.0
    elif estado == "Cerrado":
        pago = monto_reclamado * rng.uniform(*cfg.factor_pago_cerrado_rango)
    else:  # Abierto
        pago = monto_reclamado * rng.uniform(*cfg.factor_pago_abierto_rango)

    if cobertura_casco and franquicia_pesos > 0:
        pago = max(0.0, pago - franquicia_pesos)
    return reserva, round(max(0, pago), 2)


def _calcular_gasto_liquidacion(
    rng: np.random.Generator,
    cfg: Config,
    monto_reclamado: float,
    en_mediacion: bool,
    en_juicio: bool,
    estado: str,
) -> float:
    """Settlement/adjustment expenses per claim."""
    if estado == "Rechazado":
        # Rejected claims still incur some admin cost
        return round(cfg.gasto_liquidacion_base * rng.uniform(0.3, 0.6), 2)

    gasto = max(
        cfg.gasto_liquidacion_base,
        monto_reclamado * cfg.gasto_liquidacion_pct,
    )

    if en_juicio:
        gasto *= cfg.gasto_liquidacion_mult_juicio
    elif en_mediacion:
        gasto *= cfg.gasto_liquidacion_mult_mediacion

    # Add noise
    gasto *= rng.uniform(0.85, 1.20)
    return round(gasto, 2)


def _asignar_motivo_rechazo(
    rng: np.random.Generator,
    cfg: Config,
    estado: str,
    cobertura_casco: bool,
    plan_cobertura: str,
    meses_mora: int,
    lag_denuncia: int,
) -> object:
    """Assign rejection reason. Returns pd.NA for non-rejected claims."""
    if estado != "Rechazado":
        return pd.NA

    pesos = dict(cfg.pesos_motivo_rechazo)

    # Contextual biases
    if not cobertura_casco and plan_cobertura == "Responsabilidad Civil":
        pesos["Falta de cobertura"] = pesos.get("Falta de cobertura", 0.22) * 2.0
    if meses_mora >= 3:
        pesos["Mora en el pago"] = pesos.get("Mora en el pago", 0.18) * 2.5
    if lag_denuncia > 3:
        pesos["Denuncia tardía (>72hs)"] = pesos.get("Denuncia tardía (>72hs)", 0.08) * 3.0

    vals = list(pesos.keys())
    p = np.array(list(pesos.values()), dtype=float)
    p = p / p.sum()
    return str(rng.choice(vals, p=p))


def generar_siniestros(
    df_polizas: pd.DataFrame,
    cfg: Config,
    lambda_scale: float = 1.0,
    severidad_scale: float = 1.0,
    seed: int | None = None,
) -> pd.DataFrame:
    rng = np.random.default_rng(cfg.random_seed + 1 if seed is None else seed)

    # ── NEW: pass cfg to _lambda_por_segmento for demographic factors
    lambdas = df_polizas.apply(lambda row: _lambda_por_segmento(row, cfg), axis=1).values * lambda_scale
    lambdas = np.clip(lambdas, 0.001, 3.0)

    # ── NEW: cancelled policies → reduced exposure (fewer claims)
    if "cancelada" in df_polizas.columns and "fecha_cancelacion" in df_polizas.columns:
        canceladas = df_polizas["cancelada"].fillna(False).values
        # Scale lambda by fraction of year the policy was active
        for i in range(len(df_polizas)):
            if canceladas[i]:
                inicio = df_polizas.iloc[i]["fecha_inicio_vigencia"]
                cancel = df_polizas.iloc[i]["fecha_cancelacion"]
                if pd.notna(cancel):
                    if hasattr(cancel, 'date'):
                        cancel = cancel.date()
                    fraccion = max(0.0, (cancel - inicio).days / 365.0)
                    lambdas[i] *= fraccion

    n_siniestros = rng.poisson(lambdas)

    rows: list[dict] = []
    today = date.today()
    provincias = df_polizas["provincia"].unique()

    for _, poliza in df_polizas.loc[n_siniestros > 0].iterrows():
        n = int(n_siniestros[int(poliza.name)])

        # Determine effective end date (cancellation or normal expiry)
        fecha_fin_efectiva = poliza["fecha_fin_vigencia"]
        if "cancelada" in poliza.index and poliza.get("cancelada", False):
            cancel_date = poliza.get("fecha_cancelacion")
            if pd.notna(cancel_date):
                fecha_fin_efectiva = cancel_date.date() if hasattr(cancel_date, 'date') else cancel_date

        meses_mora = int(poliza.get("meses_en_mora", 0))

        tiene_rastreador = bool(poliza.get("tiene_rastreador", False))
        tipo_combustible = str(poliza.get("tipo_combustible", "Nafta"))
        for _ in range(n):
            tipo_veh = poliza.get("tipo_vehiculo", "Auto")
            if tipo_veh == "Moto":
                probs_base = cfg.prob_tipo_danio_moto
                sev_dict = cfg.severidad_lognormal_moto
            else:
                probs_base = cfg.prob_tipo_danio_por_zona[poliza["zona_riesgo"]]
                sev_dict = cfg.severidad_lognormal

            probs_efectivas = dict(probs_base)
            if tiene_rastreador:
                for k in ("Robo total", "Robo parcial"):
                    if k in probs_efectivas:
                        probs_efectivas[k] *= cfg.factor_robo_rastreador
            if tipo_combustible == "GNC" and "Incendio" in probs_efectivas:
                probs_efectivas["Incendio"] *= cfg.factor_incendio_gnc

            tipo_danio = _sample_weighted(rng, probs_efectivas)
            mu, sigma = sev_dict[tipo_danio]

            fecha_siniestro = _sample_fecha_siniestro(
                rng,
                poliza["fecha_inicio_vigencia"],
                fecha_fin_efectiva,
                tipo_danio,
                cfg,
            )
            lag_denuncia = int(min(30, max(0, round(rng.exponential(5.0)))))
            fecha_denuncia = min(today, fecha_siniestro + timedelta(days=lag_denuncia))

            factor_zona_sev = rng.uniform(
                *cfg.factor_severidad_por_zona.get(str(poliza["zona_riesgo"]), (1.0, 1.0))
            )

            monto = float(np.exp(rng.normal(mu, sigma)))
            monto *= cfg.inflacion_anual.get(fecha_siniestro.year, 4.0)
            monto *= severidad_scale
            monto *= factor_zona_sev

            if tipo_combustible == "Eléctrico" and tipo_danio == "Choque":
                monto *= cfg.factor_severidad_choque_electrico

            # Extreme severity tail: ~1% catastrophic / fraud signal
            if rng.random() < 0.01:
                monto *= rng.uniform(2.5, 5.0)

            monto = round(monto, 2)

            terceros = _terceros_involucrados(rng, tipo_danio)
            casco = _cobertura_casco(poliza["plan_cobertura"], tipo_danio)
            cobertura_rc = tipo_danio in _DANIOS_RC or (tipo_danio == "Choque" and terceros)

            if casco and not cobertura_rc:
                categoria_siniestro = "Casco"
            elif cobertura_rc and not casco:
                categoria_siniestro = "RC"
            else:
                categoria_siniestro = "Mixto"

            p_mediacion = 0.20
            if terceros:
                p_mediacion *= 1.5
            p_mediacion = min(0.9, p_mediacion)
            en_mediacion = bool(rng.random() < p_mediacion)

            p90 = _p90_lognormal(mu, sigma) * cfg.inflacion_anual.get(fecha_siniestro.year, 4.0) * severidad_scale * factor_zona_sev
            monto_alto = monto > p90

            en_juicio = False
            if en_mediacion or monto_alto:
                p_juicio = 0.11
                if monto_alto:
                    p_juicio *= 2.0
                if not en_mediacion:
                    p_juicio *= 0.7
                p_juicio = min(0.95, p_juicio)
                en_juicio = bool(rng.random() < p_juicio)

            con_sentencia = bool(en_juicio and (rng.random() < 0.35))

            fecha_inicio_juicio = pd.NaT
            if en_juicio:
                lag_juicio = int(max(0, round(rng.exponential(180.0))))
                fecha_inicio_juicio = fecha_denuncia + timedelta(days=lag_juicio)

            conductor_es_asegurado = bool(rng.random() < 0.85)
            bien_recuperado = _bien_recuperado(rng, tipo_danio)

            ubicacion = poliza["provincia"]
            if rng.random() < 0.10:
                ubicacion = str(rng.choice(provincias))

            # ── NEW: Claim status, financial amounts, expenses, rejection ────
            estado = _asignar_estado_siniestro(
                rng, cfg, monto, en_juicio, meses_mora
            )
            franquicia_pct = float(poliza.get("franquicia", 0.0) or 0.0)
            franquicia_pesos = franquicia_pct * float(poliza.get("suma_asegurada", 0.0))
            monto_reservado, monto_pagado = _calcular_montos_financieros(
                rng, cfg, monto, estado, casco, franquicia_pesos
            )
            gasto_liquidacion = _calcular_gasto_liquidacion(
                rng, cfg, monto, en_mediacion, en_juicio, estado
            )
            motivo_rechazo = _asignar_motivo_rechazo(
                rng, cfg, estado, casco, poliza["plan_cobertura"], meses_mora, lag_denuncia
            )

            rows.append(
                {
                    "id_poliza": int(poliza["id_poliza"]),
                    "ramo": poliza["ramo"],
                    "fecha_siniestro": fecha_siniestro,
                    "fecha_denuncia": fecha_denuncia,
                    "fecha_inicio_juicio": fecha_inicio_juicio,
                    "tipo_danio": tipo_danio,
                    "monto_reclamado": monto,
                    "monto_reservado": monto_reservado,
                    "monto_pagado": monto_pagado,
                    "estado_siniestro": estado,
                    "motivo_rechazo": motivo_rechazo,
                    "gasto_liquidacion": gasto_liquidacion,
                    "cobertura_casco": casco,
                    "cobertura_rc": cobertura_rc,
                    "categoria_siniestro": categoria_siniestro,
                    "en_mediacion": en_mediacion,
                    "en_juicio": en_juicio,
                    "con_sentencia": con_sentencia,
                    "terceros_involucrados": terceros,
                    "conductor_es_asegurado": conductor_es_asegurado,
                    "bien_recuperado": bien_recuperado,
                    "ubicacion_siniestro": ubicacion,
                }
            )

    if not rows:
        cols = [
            "id_siniestro", "numero_siniestro", "id_poliza", "ramo",
            "fecha_siniestro", "fecha_denuncia", "fecha_inicio_juicio",
            "tipo_danio", "monto_reclamado", "monto_reservado", "monto_pagado",
            "estado_siniestro", "motivo_rechazo", "gasto_liquidacion",
            "cobertura_casco", "cobertura_rc", "categoria_siniestro",
            "en_mediacion", "en_juicio", "con_sentencia",
            "terceros_involucrados", "conductor_es_asegurado",
            "bien_recuperado", "ubicacion_siniestro",
        ]
        return pd.DataFrame(columns=cols)

    df = pd.DataFrame(rows)
    df.insert(0, "id_siniestro", np.arange(1, len(df) + 1, dtype=int))
    df.insert(
        1,
        "numero_siniestro",
        [f"SIN-{f.year}-{i:06d}" for i, f in zip(df["id_siniestro"], df["fecha_siniestro"])],
    )

    # Maintain strict legal chain coherence
    df.loc[~df["en_mediacion"], ["en_juicio", "con_sentencia", "fecha_inicio_juicio"]] = [False, False, pd.NaT]
    df.loc[df["en_mediacion"] & ~df["en_juicio"], ["con_sentencia", "fecha_inicio_juicio"]] = [False, pd.NaT]

    return df
