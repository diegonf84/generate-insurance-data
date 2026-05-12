from __future__ import annotations

import numpy as np
import pandas as pd

from config import Config
from generadores.sampling import sample_weighted


GBA_LOCALIDADES: frozenset[str] = frozenset({
    "San Isidro", "Quilmes", "Morón", "Lomas de Zamora", "Tigre",
    "San Martín", "Tres de Febrero", "Lanús", "Avellaneda", "San Fernando",
    "Merlo", "Hurlingham", "Florencio Varela", "Berazategui", "Esteban Echeverría",
    "Almirante Brown", "Ezeiza", "Ituzaingó", "Malvinas Argentinas", "José C. Paz",
    "San Miguel", "Moreno", "Pilar", "Escobar", "Vicente López",
})

CIUDADES_MEDIA_ALTA: frozenset[str] = frozenset({
    "La Plata", "Mar del Plata", "Bahía Blanca",
    "Mendoza Capital", "Godoy Cruz", "Guaymallén", "Las Heras", "Maipú",
    "Santa Fe Capital",
    "Villa Carlos Paz", "Río Cuarto", "Villa María",
    "San Miguel de Tucumán", "Paraná", "Neuquén Capital", "Salta Capital",
    "Resistencia", "Posadas", "Corrientes Capital", "San Juan Capital",
    "San Salvador de Jujuy", "Santiago del Estero Capital", "San Luis Capital",
    "Formosa Capital", "Catamarca Capital", "Bariloche",
})


def asignar_zona(provincia: str, localidad: str) -> str:
    if provincia == "CABA":
        return "Muy Alta"
    if provincia == "Buenos Aires" and localidad in GBA_LOCALIDADES:
        return "Alta"
    if provincia == "Córdoba" and localidad == "Córdoba Capital":
        return "Alta"
    if provincia == "Santa Fe" and localidad == "Rosario":
        return "Alta"
    if localidad in CIUDADES_MEDIA_ALTA:
        return "Media-Alta"
    if provincia in {"Buenos Aires", "Santa Fe", "Mendoza", "Córdoba"}:
        return "Media"
    return "Baja"


def asignar_geografia(df: pd.DataFrame, cfg: Config, rng: np.random.Generator) -> None:
    """Assigns provincia, localidad, barrio and zona_riesgo columns to df."""
    n = len(df)
    df["provincia"] = sample_weighted(rng, cfg.pesos_provincia, n)

    localidades = []
    barrios = []
    zonas = []
    for provincia in df["provincia"].values:
        localidad = rng.choice(cfg.localidades_por_provincia[str(provincia)])
        localidades.append(localidad)
        zona = asignar_zona(str(provincia), str(localidad))
        zonas.append(zona)
        if str(provincia) == "CABA":
            barrios.append(rng.choice(cfg.barrios_caba))
        elif str(provincia) == "Buenos Aires" and str(localidad) in GBA_LOCALIDADES:
            barrios.append(rng.choice(cfg.barrios_gba))
        else:
            barrios.append(pd.NA)

    df["localidad"] = localidades
    df["barrio"] = barrios
    df["zona_riesgo"] = zonas
