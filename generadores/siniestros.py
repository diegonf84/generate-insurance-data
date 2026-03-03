from __future__ import annotations

import calendar
from datetime import date, timedelta

import numpy as np
import pandas as pd

from config import Config

# Monthly claim weight arrays by damage type (normalized, index 0=Jan … 11=Dec)
# Heavy Oct–Mar for Granizo (Argentine spring-summer hail season)
# Jul–Aug peak for Choque (winter fog/frost)
# Dec–Feb peak for Robo (summer vacations)
_PESOS_MES_DANIO: dict[str, list[float]] = {
    k: [x / sum(v) for x in v]
    for k, v in {
        #                    Jan  Feb  Mar  Apr  May  Jun  Jul  Aug  Sep  Oct  Nov  Dec
        "Granizo":          [12., 12., 10.,  3.,  2.,  2.,  2.,  2.,  3., 10., 16., 14.],
        "Choque":           [ 8.,  7.,  8.,  8.,  8.,  9., 10., 10.,  8.,  8.,  8.,  8.],
        "Robo total":       [12., 12.,  9.,  8.,  7.,  7.,  7.,  7.,  8.,  8.,  7.,  8.],
        "Robo parcial":     [12., 12.,  9.,  8.,  7.,  7.,  7.,  7.,  8.,  8.,  7.,  8.],
        "Incendio":         [ 8.,  8.,  8.,  8.,  8.,  9.,  9.,  9.,  8.,  8.,  8.,  9.],
        "Daño a terceros":  [ 8.,  8.,  8.,  8.,  8.,  9.,  9.,  9.,  8.,  8.,  8.,  9.],
        "Otros":            [ 8.,  8.,  8.,  8.,  8.,  8.,  8.,  8.,  9.,  9.,  9.,  9.],
    }.items()
}


def _sample_weighted(rng: np.random.Generator, pesos: dict[str, float]) -> str:
    vals = np.array(list(pesos.keys()))
    probs = np.array(list(pesos.values()), dtype=float)
    probs = probs / probs.sum()
    return str(rng.choice(vals, p=probs))


def _lambda_por_segmento(row: pd.Series) -> float:
    zona = row["zona_riesgo"]
    edad = int(row["edad_asegurado"])
    uso = row["tipo_uso"]

    if zona == "Alta" and edad < 25 and uso in {"Comercial", "Profesional"}:
        lam = 0.35
    elif zona == "Alta" and 25 <= edad <= 55 and uso == "Particular":
        lam = 0.20
    elif zona == "Media" and 25 <= edad <= 55 and uso == "Particular":
        lam = 0.15
    elif zona == "Baja" and 35 <= edad <= 55 and uso == "Particular":
        lam = 0.08
    else:
        lam = 0.12

    if uso in {"Comercial", "Profesional"}:
        lam *= 1.15
    if row["plan_cobertura"] == "Todo Riesgo":
        lam *= 1.15

    tipo_vehiculo = row.get("tipo_vehiculo", "Auto")
    if tipo_vehiculo == "Moto":
        lam *= 1.7
    elif tipo_vehiculo == "Camioneta":
        lam *= 0.85

    return lam


def _sample_fecha_siniestro(
    rng: np.random.Generator,
    inicio: date,
    fin: date,
    tipo_danio: str,
) -> date:
    dias_total = max(1, (fin - inicio).days)
    pesos_mes = _PESOS_MES_DANIO.get(tipo_danio)

    if pesos_mes is not None:
        anos_candidatos = list({inicio.year, fin.year})
        for _ in range(20):
            mes = int(rng.choice(np.arange(1, 13), p=pesos_mes))
            anio = int(rng.choice(anos_candidatos))
            dias_en_mes = calendar.monthrange(anio, mes)[1]
            dia = int(rng.integers(1, dias_en_mes + 1))
            candidata = date(anio, mes, dia)
            if inicio <= candidata <= fin:
                return candidata

    # Fallback: uniform within [inicio, fin]
    return inicio + timedelta(days=int(rng.integers(0, dias_total + 1)))


def _terceros_involucrados(rng: np.random.Generator, tipo_danio: str) -> bool:
    if tipo_danio == "Daño a terceros":
        return True
    if tipo_danio == "Choque":
        return bool(rng.random() < 0.60)
    return False


def _cobertura_casco(plan: str, tipo_danio: str) -> bool:
    if plan not in {"Terceros Completo", "Todo Riesgo"}:
        return False
    return tipo_danio in {"Robo total", "Robo parcial", "Choque", "Incendio", "Granizo", "Otros"}


def _bien_recuperado(rng: np.random.Generator, tipo_danio: str):
    if tipo_danio == "Robo total":
        return bool(rng.random() < 0.20)
    if tipo_danio == "Robo parcial":
        return bool(rng.random() < 0.45)
    return pd.NA


def _p90_lognormal(mu: float, sigma: float) -> float:
    z90 = 1.2815515655446004
    return float(np.exp(mu + sigma * z90))


def generar_siniestros(
    df_polizas: pd.DataFrame,
    cfg: Config,
    lambda_scale: float = 1.0,
    severidad_scale: float = 1.0,
    seed: int | None = None,
) -> pd.DataFrame:
    rng = np.random.default_rng(cfg.random_seed + 1 if seed is None else seed)

    lambdas = df_polizas.apply(_lambda_por_segmento, axis=1).values * lambda_scale
    lambdas = np.clip(lambdas, 0.001, 3.0)
    n_siniestros = rng.poisson(lambdas)

    rows: list[dict] = []
    today = date.today()
    provincias = df_polizas["provincia"].unique()

    for _, poliza in df_polizas.loc[n_siniestros > 0].iterrows():
        n = int(n_siniestros[int(poliza.name)])
        for _ in range(n):
            # Sample tipo_danio first (needed for seasonality routing)
            tipo_veh = poliza.get("tipo_vehiculo", "Auto")
            if tipo_veh == "Moto":
                tipo_danio = _sample_weighted(rng, cfg.prob_tipo_danio_moto)
                mu, sigma = cfg.severidad_lognormal_moto[tipo_danio]
            else:
                tipo_danio = _sample_weighted(rng, cfg.prob_tipo_danio_por_zona[poliza["zona_riesgo"]])
                mu, sigma = cfg.severidad_lognormal[tipo_danio]

            fecha_siniestro = _sample_fecha_siniestro(
                rng,
                poliza["fecha_inicio_vigencia"],
                poliza["fecha_fin_vigencia"],
                tipo_danio,
            )
            lag_denuncia = int(min(30, max(0, round(rng.exponential(5.0)))))
            fecha_denuncia = min(today, fecha_siniestro + timedelta(days=lag_denuncia))

            factor_zona_sev = cfg.factor_severidad_por_zona.get(
                str(poliza["zona_riesgo"]), 1.0
            )

            monto = float(np.exp(rng.normal(mu, sigma)))
            monto *= cfg.inflacion_anual.get(fecha_siniestro.year, 4.0)
            monto *= severidad_scale
            monto *= factor_zona_sev

            # Extreme severity tail: ~1% catastrophic / fraud signal
            if rng.random() < 0.01:
                monto *= rng.uniform(2.5, 5.0)

            monto = round(monto, 2)

            terceros = _terceros_involucrados(rng, tipo_danio)
            casco = _cobertura_casco(poliza["plan_cobertura"], tipo_danio)
            cobertura_rc = tipo_danio == "Daño a terceros" or (tipo_danio == "Choque" and terceros)

            # Claim coverage category
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

            rows.append(
                {
                    "id_poliza": int(poliza["id_poliza"]),
                    "ramo": poliza["ramo"],
                    "fecha_siniestro": fecha_siniestro,
                    "fecha_denuncia": fecha_denuncia,
                    "fecha_inicio_juicio": fecha_inicio_juicio,
                    "tipo_danio": tipo_danio,
                    "monto_reclamado": monto,
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
            "id_siniestro",
            "numero_siniestro",
            "id_poliza",
            "ramo",
            "fecha_siniestro",
            "fecha_denuncia",
            "fecha_inicio_juicio",
            "tipo_danio",
            "monto_reclamado",
            "cobertura_casco",
            "cobertura_rc",
            "categoria_siniestro",
            "en_mediacion",
            "en_juicio",
            "con_sentencia",
            "terceros_involucrados",
            "conductor_es_asegurado",
            "bien_recuperado",
            "ubicacion_siniestro",
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
