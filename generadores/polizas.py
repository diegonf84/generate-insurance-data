from __future__ import annotations

from datetime import timedelta

import numpy as np
import pandas as pd

from config import Config
from generadores.vehiculos import (
    estimar_valor_vehiculo,
    generar_catalogo_vehiculos,
    muestrear_anio_vehiculo,
)

# GBA municipalities that trigger barrios_gba assignment and Alta risk zone
_GBA_LOCALIDADES: frozenset[str] = frozenset({
    "San Isidro", "Quilmes", "Morón", "Lomas de Zamora", "Tigre",
    "San Martín", "Tres de Febrero", "Lanús", "Avellaneda", "San Fernando",
    "Merlo", "Hurlingham", "Florencio Varela", "Berazategui", "Esteban Echeverría",
    "Almirante Brown", "Ezeiza", "Ituzaingó", "Malvinas Argentinas", "José C. Paz",
    "San Miguel", "Moreno", "Pilar", "Escobar", "Vicente López",
})

_CIUDADES_MEDIA_ALTA: frozenset[str] = frozenset({
    # Buenos Aires interior — large cities
    "La Plata", "Mar del Plata", "Bahía Blanca",
    # Mendoza metro
    "Mendoza Capital", "Godoy Cruz", "Guaymallén", "Las Heras", "Maipú",
    # Santa Fe Capital
    "Santa Fe Capital",
    # Córdoba secondary
    "Villa Carlos Paz", "Río Cuarto", "Villa María",
    # Provincial capitals and large cities
    "San Miguel de Tucumán", "Paraná", "Neuquén Capital", "Salta Capital",
    "Resistencia", "Posadas", "Corrientes Capital", "San Juan Capital",
    "San Salvador de Jujuy", "Santiago del Estero Capital", "San Luis Capital",
    "Formosa Capital", "Catamarca Capital", "Bariloche",
})

_CATEGORIA_COBERTURA: dict[str, str] = {
    "Responsabilidad Civil": "Solo RC",
    "Terceros Completo": "RC + Casco Básico",
    "Todo Riesgo": "RC + Casco Total",
}


def _sample_weighted(rng: np.random.Generator, pesos: dict, n: int) -> np.ndarray:
    valores = np.array(list(pesos.keys()))
    probs = np.array(list(pesos.values()), dtype=float)
    probs = probs / probs.sum()
    return rng.choice(valores, size=n, p=probs)


def _sample_weighted_single(rng: np.random.Generator, pesos: dict) -> object:
    """Sample a single value from a weighted dict."""
    valores = list(pesos.keys())
    probs = np.array(list(pesos.values()), dtype=float)
    probs = probs / probs.sum()
    return rng.choice(valores, p=probs)


def _sample_edad(rng: np.random.Generator, n: int) -> np.ndarray:
    n_young = int(round(n * 0.35))
    n_mature = n - n_young
    young = np.clip(rng.normal(loc=27, scale=7, size=n_young), 18, 35)
    mature = np.clip(rng.normal(loc=46, scale=12, size=n_mature), 25, 80)
    combined = np.concatenate([young, mature])
    rng.shuffle(combined)
    return np.round(combined).astype(int)


def _sample_fechas_inicio(cfg: Config, rng: np.random.Generator, n: int) -> pd.Series:
    anios = np.arange(cfg.fecha_inicio.year, cfg.fecha_fin.year + 1)
    pesos_mensuales = np.array([0.07, 0.07, 0.12, 0.07, 0.07, 0.08, 0.08, 0.08, 0.07, 0.12, 0.09, 0.08])
    pesos_mensuales = pesos_mensuales / pesos_mensuales.sum()

    years = rng.choice(anios, size=n)
    months = rng.choice(np.arange(1, 13), size=n, p=pesos_mensuales)

    fechas = []
    for y, m in zip(years, months):
        first = pd.Timestamp(year=int(y), month=int(m), day=1)
        last = first + pd.offsets.MonthEnd(1)
        day = int(rng.integers(1, last.day + 1))
        fecha = pd.Timestamp(year=int(y), month=int(m), day=day)
        if fecha < pd.Timestamp(cfg.fecha_inicio):
            fecha = pd.Timestamp(cfg.fecha_inicio)
        if fecha > pd.Timestamp(cfg.fecha_fin):
            fecha = pd.Timestamp(cfg.fecha_fin)
        fechas.append(fecha.date())
    return pd.Series(fechas)


def _asignar_zona(provincia: str, localidad: str) -> str:
    if provincia == "CABA":
        return "Muy Alta"
    if provincia == "Buenos Aires" and localidad in _GBA_LOCALIDADES:
        return "Alta"
    if provincia == "Córdoba" and localidad == "Córdoba Capital":
        return "Alta"
    if provincia == "Santa Fe" and localidad == "Rosario":
        return "Alta"
    if localidad in _CIUDADES_MEDIA_ALTA:
        return "Media-Alta"
    if provincia in {"Buenos Aires", "Santa Fe", "Mendoza", "Córdoba"}:
        return "Media"
    return "Baja"


def _factor_edad(edad: int) -> float:
    if edad < 25:
        return 1.4
    if edad < 35:
        return 1.1
    if edad < 55:
        return 1.0
    if edad < 65:
        return 1.05
    return 1.2


def _factor_antiguedad_vehiculo(anio: int) -> float:
    antiguedad = 2024 - anio
    if antiguedad < 3:
        return 1.0
    if antiguedad < 8:
        return 0.95
    if antiguedad < 15:
        return 1.1
    return 1.25


def _sample_mora(
    rng: np.random.Generator, zona: str, canal: str,
    medio_pago: str, cfg: Config,
) -> int:
    # Check if mora logic even runs based on payment method
    prob_activa = cfg.prob_mora_por_medio_pago.get(medio_pago, 0.15)
    if rng.random() >= prob_activa:
        return 0

    probs = np.array([0.70, 0.15, 0.08, 0.05, 0.02], dtype=float)
    if zona in {"Muy Alta", "Alta"}:
        probs += np.array([-0.05, 0.02, 0.01, 0.01, 0.01])
    elif zona == "Media-Alta":
        probs += np.array([-0.03, 0.01, 0.01, 0.005, 0.005])
    if canal in {"Online", "Directa"}:
        probs += np.array([-0.03, 0.01, 0.01, 0.005, 0.005])
    probs = np.clip(probs, 0.001, None)
    probs = probs / probs.sum()
    bucket = int(rng.choice(np.arange(5), p=probs))
    if bucket < 4:
        return bucket
    return int(rng.integers(4, 7))


def ajustar_renovada_por_siniestros(
    df_polizas: pd.DataFrame,
    df_siniestros: pd.DataFrame,
    rng: np.random.Generator,
) -> pd.Series:
    counts = df_siniestros.groupby("id_poliza").size()
    base = np.full(len(df_polizas), 0.75)
    id_to_idx = {pid: i for i, pid in enumerate(df_polizas["id_poliza"].values)}

    for poliza_id, n in counts.items():
        idx = id_to_idx.get(poliza_id)
        if idx is not None:
            base[idx] -= min(0.30, 0.08 * n)

    base -= np.where(df_polizas["meses_en_mora"].values >= 2, 0.10, 0.0)
    base = np.clip(base, 0.20, 0.93)
    return pd.Series(rng.random(len(df_polizas)) < base)


def aplicar_cancelaciones(
    df_polizas: pd.DataFrame,
    cfg: Config,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Assign mid-term cancellations to a fraction of policies.

    Adds columns: `cancelada`, `fecha_cancelacion`, `motivo_cancelacion`.
    Cancelled policies also get `renovada = False`.
    """
    n = len(df_polizas)

    # Base cancellation probability, elevated for high-mora policies
    p_cancel = np.full(n, cfg.tasa_cancelacion_base)
    mora_alta = df_polizas["meses_en_mora"].values >= cfg.mora_umbral_cancelacion
    p_cancel[mora_alta] *= 2.5  # mora prolongada → mucho más probable

    # Young drivers slightly more likely to cancel (change company)
    joven = df_polizas["edad_asegurado"].values < 28
    p_cancel[joven] *= 1.20

    p_cancel = np.clip(p_cancel, 0.0, 0.50)
    cancelada = rng.random(n) < p_cancel

    df_polizas["cancelada"] = cancelada
    df_polizas["fecha_cancelacion"] = pd.NaT
    df_polizas["motivo_cancelacion"] = pd.NA

    idx_cancel = df_polizas.index[cancelada]
    if len(idx_cancel) > 0:
        # Cancellation date: between 30 and 300 days after inicio
        for idx in idx_cancel:
            inicio = df_polizas.at[idx, "fecha_inicio_vigencia"]
            fin = df_polizas.at[idx, "fecha_fin_vigencia"]
            max_dias = max(30, (fin - inicio).days - 30)
            lag = int(rng.integers(30, max_dias + 1))
            df_polizas.at[idx, "fecha_cancelacion"] = pd.Timestamp(inicio + timedelta(days=lag))

            # Assign motivo — mora prolongada gets biased toward "Mora prolongada"
            if df_polizas.at[idx, "meses_en_mora"] >= cfg.mora_umbral_cancelacion:
                if rng.random() < 0.65:
                    df_polizas.at[idx, "motivo_cancelacion"] = "Mora prolongada"
                else:
                    df_polizas.at[idx, "motivo_cancelacion"] = str(
                        _sample_weighted_single(rng, cfg.pesos_motivo_cancelacion)
                    )
            else:
                df_polizas.at[idx, "motivo_cancelacion"] = str(
                    _sample_weighted_single(rng, cfg.pesos_motivo_cancelacion)
                )

        # Cancelled policies are never renewed
        df_polizas.loc[cancelada, "renovada"] = False

    return df_polizas


def generar_polizas(cfg: Config, seed: int | None = None) -> pd.DataFrame:
    rng = np.random.default_rng(cfg.random_seed if seed is None else seed)
    n = cfg.cantidad_polizas

    df = pd.DataFrame({"id_poliza": np.arange(1, n + 1, dtype=int)})
    df["fecha_inicio_vigencia"] = _sample_fechas_inicio(cfg, rng, n)
    df["fecha_fin_vigencia"] = df["fecha_inicio_vigencia"].apply(lambda d: d + timedelta(days=365))
    df["numero_poliza"] = [f"AUT-{f.year}-{i:06d}" for i, f in zip(df["id_poliza"], df["fecha_inicio_vigencia"])]

    df["ramo"] = cfg.ramo_principal
    df["plan_cobertura"] = _sample_weighted(rng, cfg.pesos_cobertura, n)

    df["provincia"] = _sample_weighted(rng, cfg.pesos_provincia, n)
    localidades = []
    barrios = []
    zonas = []
    for provincia in df["provincia"].values:
        localidad = rng.choice(cfg.localidades_por_provincia[str(provincia)])
        localidades.append(localidad)
        zona = _asignar_zona(str(provincia), str(localidad))
        zonas.append(zona)
        if str(provincia) == "CABA":
            barrios.append(rng.choice(cfg.barrios_caba))
        elif str(provincia) == "Buenos Aires" and str(localidad) in _GBA_LOCALIDADES:
            barrios.append(rng.choice(cfg.barrios_gba))
        else:
            barrios.append(pd.NA)

    df["localidad"] = localidades
    df["barrio"] = barrios
    df["zona_riesgo"] = zonas

    df["edad_asegurado"] = _sample_edad(rng, n)
    df["genero_asegurado"] = _sample_weighted(rng, cfg.pesos_genero, n)
    df["estado_civil"] = _sample_weighted(rng, cfg.pesos_estado_civil, n)
    df["ocupacion"] = _sample_weighted(rng, cfg.pesos_ocupacion, n)
    df["canal_venta"] = _sample_weighted(rng, cfg.pesos_canal, n)
    df["medio_pago"] = _sample_weighted(rng, cfg.pesos_medio_pago, n)

    # Producers with power-law distribution
    productores = np.array([f"PROD-{i:04d}" for i in range(1, cfg.n_productores + 1)])
    ranks = np.arange(1, cfg.n_productores + 1)
    probs_prod = 1 / np.power(ranks, 1.15)
    probs_prod = probs_prod / probs_prod.sum()
    df["codigo_productor"] = rng.choice(productores, size=n, p=probs_prod)

    rank_map = {prod: idx + 1 for idx, prod in enumerate(productores)}
    ranks_asignados = np.array([rank_map[p] for p in df["codigo_productor"].values], dtype=float)
    antig = 240 - (ranks_asignados / ranks_asignados.max()) * 180 + rng.normal(0, 15, size=n)
    df["tiempo_productor_cia_meses"] = np.clip(np.round(antig), 1, 240).astype(int)

    # Organizadores: 80% of producers belong to one of 50 groups
    organizadores = [f"ORG-{i:02d}" for i in range(1, cfg.n_organizadores + 1)]
    rng_org = np.random.default_rng(cfg.random_seed + 999)
    prod_to_org: dict[str, str | None] = {}
    for prod in productores:
        if rng_org.random() < cfg.prob_productor_en_organizador:
            prod_to_org[prod] = str(rng_org.choice(organizadores))
        else:
            prod_to_org[prod] = None
    df["codigo_organizador"] = df["codigo_productor"].map(prod_to_org)

    comisiones = []
    for canal in df["canal_venta"].values:
        low, high = cfg.comision_por_canal[str(canal)]
        if low == high:
            comisiones.append(low)
        else:
            comisiones.append(float(rng.uniform(low, high)))
    df["comision_pactada"] = np.round(comisiones, 4)

    # Vehicle selection: tipo_vehiculo-first approach
    catalogo = generar_catalogo_vehiculos()
    catalogo_por_tipo = {
        str(tipo): grp.reset_index(drop=True)
        for tipo, grp in catalogo.groupby("tipo_vehiculo")
    }
    tipo_vehiculos = _sample_weighted(rng, cfg.pesos_tipo_vehiculo, n)

    marcas = []
    modelos = []
    valores_base = []
    for tv in tipo_vehiculos:
        opciones = catalogo_por_tipo[str(tv)]
        idx = int(rng.integers(0, len(opciones)))
        marcas.append(str(opciones.loc[idx, "marca_vehiculo"]))
        modelos.append(str(opciones.loc[idx, "modelo_vehiculo"]))
        valores_base.append(float(opciones.loc[idx, "valor_base_2024"]))

    df["marca_vehiculo"] = marcas
    df["modelo_vehiculo"] = modelos
    df["tipo_vehiculo"] = [str(tv) for tv in tipo_vehiculos]

    # Override ramo for motorcycles
    df.loc[df["tipo_vehiculo"] == "Moto", "ramo"] = cfg.ramo_motovehiculos

    df["anio_vehiculo"] = muestrear_anio_vehiculo(rng, n)
    valores = np.array(
        [estimar_valor_vehiculo(vb, anio) for vb, anio in zip(valores_base, df["anio_vehiculo"].values)],
        dtype=float,
    )
    valores *= rng.uniform(0.88, 1.15, size=n)
    df["suma_asegurada"] = np.clip(valores, 1_500_000, 45_000_000).round(2)

    # Outlier injection: ~0.5% of policies get uncapped, 2x-4x premium vehicles
    n_outliers = max(1, int(n * cfg.p_outlier_poliza))
    outlier_idx = rng.choice(n, size=n_outliers, replace=False)
    df.loc[outlier_idx, "suma_asegurada"] = (
        valores[outlier_idx] * rng.uniform(2.0, 4.0, size=n_outliers)
    ).round(2)

    df["tipo_uso"] = _sample_weighted(rng, cfg.pesos_uso, n)

    # Fleet flag: 2% of policies are fleet (forces Comercial uso)
    df["es_flota"] = rng.random(n) < 0.02
    df.loc[df["es_flota"], "tipo_uso"] = "Comercial"

    # Coverage category derived from plan
    df["categoria_cobertura"] = df["plan_cobertura"].map(_CATEGORIA_COBERTURA)

    tasa_base = rng.uniform(*cfg.tasa_base_rango, size=n)
    factor_cob = df["plan_cobertura"].map(cfg.factor_cobertura_tarifa).astype(float).values
    factor_z = np.array([rng.uniform(*cfg.factor_zona[z]) for z in df["zona_riesgo"].values])
    factor_ed = np.array([_factor_edad(e) for e in df["edad_asegurado"].values], dtype=float)
    factor_ant = np.array([_factor_antiguedad_vehiculo(a) for a in df["anio_vehiculo"].values], dtype=float)

    prima = df["suma_asegurada"].values * tasa_base * factor_cob * factor_z * factor_ed * factor_ant
    prima *= rng.uniform(0.88, 1.15, size=n)
    df["prima"] = np.round(prima, 2)

    recargo = rng.uniform(0.15, 0.25, size=n)
    df["premio"] = np.round(df["prima"].values * (1 + recargo), 2)

    df["meses_en_mora"] = [
        _sample_mora(rng, zona, canal, medio_pago, cfg)
        for zona, canal, medio_pago in zip(
            df["zona_riesgo"].values, df["canal_venta"].values, df["medio_pago"].values,
        )
    ]

    prob_base_renov = 0.75 - np.where(df["meses_en_mora"].values >= 2, 0.08, 0.0)
    prob_base_renov = np.clip(prob_base_renov, 0.20, 0.93)
    df["renovada"] = rng.random(n) < prob_base_renov

    # ── NEW: Renewal chains / cohortes ──────────────────────────────────────
    # Assign id_cliente and numero_renovacion.
    # Strategy: group policies into client chains. Policies in the same chain
    # share vehicle, province, and demographic profile. Later periods have
    # adjusted primas and progressing ages.
    _asignar_cadenas_renovacion(df, cfg, rng)

    # ── NEW: Cancellations (applied after chains so the chain is visible) ───
    aplicar_cancelaciones(df, cfg, rng)

    return df


def _asignar_cadenas_renovacion(
    df: pd.DataFrame,
    cfg: Config,
    rng: np.random.Generator,
) -> None:
    """Assign id_cliente and numero_renovacion to create cohort chains.

    Modifies `df` in place. The approach:
    1. Determine how many unique clients we need so that
       sum(periods_per_client) ≈ len(df).
    2. Assign each row to a client, grouping rows that share similar
       attributes (same tipo_vehiculo, provincia, similar edad).
    3. Within each client, order by fecha_inicio and assign
       numero_renovacion = 0, 1, 2, ...
    4. Adjust prima on renewals to reflect inflation/experience.
    """
    n = len(df)
    pesos_per = cfg.pesos_periodos_cliente
    periodos = np.array(list(pesos_per.keys()))
    probs = np.array(list(pesos_per.values()), dtype=float)
    probs = probs / probs.sum()

    # Estimate number of unique clients needed
    media_periodos = float(np.sum(periodos * probs))
    n_clientes = int(round(n / media_periodos))

    # Sample how many periods each client has
    periodos_por_cliente = rng.choice(periodos, size=n_clientes, p=probs)

    # Expand into a flat assignment: each element is the client_id for one row
    asignaciones = []
    for cid, nper in enumerate(periodos_por_cliente, start=1):
        asignaciones.extend([cid] * int(nper))

    # Trim or pad to exactly n rows
    if len(asignaciones) > n:
        asignaciones = asignaciones[:n]
    elif len(asignaciones) < n:
        # Add single-period clients to fill
        next_cid = n_clientes + 1
        while len(asignaciones) < n:
            asignaciones.append(next_cid)
            next_cid += 1

    rng.shuffle(asignaciones)

    df["id_cliente"] = asignaciones

    # Sort within each client by fecha_inicio to assign renewal number
    df.sort_values(["id_cliente", "fecha_inicio_vigencia"], inplace=True)
    df["numero_renovacion"] = df.groupby("id_cliente").cumcount()

    # Within each client chain, make later periods share key attributes
    # with the first period (the "original" policy).
    # We propagate: tipo_vehiculo, marca, modelo, anio_vehiculo,
    # provincia, localidad, zona_riesgo, genero, estado_civil, ocupacion.
    _propagate_cols = [
        "tipo_vehiculo", "marca_vehiculo", "modelo_vehiculo", "anio_vehiculo",
        "provincia", "localidad", "zona_riesgo", "barrio",
        "genero_asegurado", "ocupacion",
        "codigo_productor", "codigo_organizador",
        "medio_pago",
    ]

    first_rows = df.groupby("id_cliente").first()
    for col in _propagate_cols:
        first_map = first_rows[col]
        df[col] = df["id_cliente"].map(first_map)

    # Re-derive fields that depend on propagated columns
    df["ramo"] = cfg.ramo_principal
    df.loc[df["tipo_vehiculo"] == "Moto", "ramo"] = cfg.ramo_motovehiculos
    df["categoria_cobertura"] = df["plan_cobertura"].map(_CATEGORIA_COBERTURA)

    # Age progresses with each renewal (~1 year per period)
    edad_base = df.groupby("id_cliente")["edad_asegurado"].transform("first")
    df["edad_asegurado"] = np.clip(edad_base + df["numero_renovacion"], 18, 85).astype(int)

    # Adjust prima on renewals (inflation + experience)
    mask_renov = df["numero_renovacion"] > 0
    n_renov = int(mask_renov.sum())
    if n_renov > 0:
        ajuste = rng.uniform(
            cfg.ajuste_prima_renovacion_rango[0],
            cfg.ajuste_prima_renovacion_rango[1],
            size=n_renov,
        )
        # Compound: each additional renewal period applies the factor
        nums = df.loc[mask_renov, "numero_renovacion"].values
        ajuste_compuesto = ajuste ** nums
        df.loc[mask_renov, "prima"] = np.round(
            df.loc[mask_renov, "prima"].values * ajuste_compuesto, 2
        )
        df.loc[mask_renov, "premio"] = np.round(
            df.loc[mask_renov, "prima"].values * rng.uniform(1.15, 1.25, size=n_renov), 2
        )

    # Chance of coverage change on renewal
    if cfg.prob_cambio_cobertura_renovacion > 0:
        cambio = mask_renov & (rng.random(len(df)) < cfg.prob_cambio_cobertura_renovacion)
        n_cambio = int(cambio.sum())
        if n_cambio > 0:
            nuevas_cob = _sample_weighted(rng, cfg.pesos_cobertura, n_cambio)
            df.loc[cambio, "plan_cobertura"] = nuevas_cob
            df.loc[cambio, "categoria_cobertura"] = (
                df.loc[cambio, "plan_cobertura"].map(_CATEGORIA_COBERTURA)
            )

    # Re-sort by id_poliza for consistency
    df.sort_values("id_poliza", inplace=True)
    df.reset_index(drop=True, inplace=True)
