from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class ModeloVehiculo:
    marca: str
    modelo: str
    valor_base_2024: float


def generar_catalogo_vehiculos() -> pd.DataFrame:
    registros = [
        # ── Autos ──────────────────────────────────────────────────────────────
        ("Volkswagen", "Gol", 13_500_000, "Auto"),
        ("Volkswagen", "Polo", 18_500_000, "Auto"),
        ("Volkswagen", "T-Cross", 32_000_000, "Auto"),
        ("Volkswagen", "Vento", 29_000_000, "Auto"),
        ("Volkswagen", "Taos", 36_000_000, "Auto"),
        ("Volkswagen", "Tiguan", 52_000_000, "Auto"),
        ("Volkswagen", "Nivus", 29_000_000, "Auto"),
        ("Fiat", "Cronos", 17_500_000, "Auto"),
        ("Fiat", "Argo", 16_000_000, "Auto"),
        ("Fiat", "Mobi", 12_500_000, "Auto"),
        ("Toyota", "Corolla", 29_000_000, "Auto"),
        ("Toyota", "Etios", 16_500_000, "Auto"),
        ("Toyota", "Yaris", 21_000_000, "Auto"),
        ("Toyota", "Raize", 26_000_000, "Auto"),
        ("Toyota", "GR86", 55_000_000, "Auto"),
        ("Chevrolet", "Onix", 18_500_000, "Auto"),
        ("Chevrolet", "Cruze", 24_000_000, "Auto"),
        ("Chevrolet", "Tracker", 31_000_000, "Auto"),
        ("Chevrolet", "Equinox", 45_000_000, "Auto"),
        ("Ford", "Ka", 15_500_000, "Auto"),
        ("Ford", "Focus", 22_000_000, "Auto"),
        ("Ford", "EcoSport", 25_000_000, "Auto"),
        ("Ford", "Territory", 42_000_000, "Auto"),
        ("Renault", "Sandero", 16_000_000, "Auto"),
        ("Renault", "Logan", 15_000_000, "Auto"),
        ("Renault", "Duster", 26_000_000, "Auto"),
        ("Renault", "Stepway", 22_000_000, "Auto"),
        ("Peugeot", "208", 18_000_000, "Auto"),
        ("Peugeot", "308", 22_000_000, "Auto"),
        ("Peugeot", "2008", 28_500_000, "Auto"),
        ("Citroën", "C3", 17_000_000, "Auto"),
        ("Citroën", "C4 Cactus", 26_500_000, "Auto"),
        ("Honda", "HR-V", 34_000_000, "Auto"),
        ("Honda", "Civic", 33_000_000, "Auto"),
        ("Honda", "City", 27_000_000, "Auto"),
        ("Honda", "WR-V", 30_000_000, "Auto"),
        ("Honda", "Fit", 22_000_000, "Auto"),
        ("Nissan", "Kicks", 30_000_000, "Auto"),
        ("Nissan", "Versa", 23_000_000, "Auto"),
        ("Nissan", "Sentra", 28_000_000, "Auto"),
        ("Jeep", "Renegade", 33_500_000, "Auto"),
        ("Jeep", "Compass", 42_000_000, "Auto"),
        ("Kia", "Picanto", 18_000_000, "Auto"),
        ("Kia", "Rio", 23_000_000, "Auto"),
        ("Kia", "Sportage", 38_000_000, "Auto"),
        ("Kia", "Seltos", 32_000_000, "Auto"),
        ("Kia", "Sorento", 52_000_000, "Auto"),
        ("Hyundai", "HB20", 19_000_000, "Auto"),
        ("Hyundai", "Creta", 30_000_000, "Auto"),
        ("Hyundai", "Tucson", 42_000_000, "Auto"),
        ("Hyundai", "Santa Fe", 58_000_000, "Auto"),
        ("Chery", "Tiggo 2 Pro", 24_000_000, "Auto"),
        ("Chery", "Tiggo 5X", 32_000_000, "Auto"),
        ("Chery", "Arrizo 5 Pro", 22_000_000, "Auto"),
        ("BYD", "Yuan Plus", 35_000_000, "Auto"),
        ("BYD", "Dolphin", 28_000_000, "Auto"),
        ("Suzuki", "Swift", 20_000_000, "Auto"),
        ("Suzuki", "Vitara", 30_000_000, "Auto"),
        ("Suzuki", "S-Cross", 28_000_000, "Auto"),
        # ── Camionetas ─────────────────────────────────────────────────────────
        ("Volkswagen", "Amarok", 42_000_000, "Camioneta"),
        ("Fiat", "Strada", 22_000_000, "Camioneta"),
        ("Toyota", "Hilux", 45_000_000, "Camioneta"),
        ("Toyota", "SW4", 52_000_000, "Camioneta"),
        ("Chevrolet", "S10", 41_000_000, "Camioneta"),
        ("Chevrolet", "Montana", 38_000_000, "Camioneta"),
        ("Ford", "Ranger", 43_000_000, "Camioneta"),
        ("Ford", "Maverick", 35_000_000, "Camioneta"),
        ("Renault", "Oroch", 30_000_000, "Camioneta"),
        ("Nissan", "Frontier", 42_000_000, "Camioneta"),
        ("Suzuki", "Jimny", 38_000_000, "Camioneta"),
        # ── Utilitarios ────────────────────────────────────────────────────────
        ("Renault", "Kangoo", 24_000_000, "Utilitario"),
        ("Peugeot", "Partner", 23_500_000, "Utilitario"),
        ("Citroën", "Berlingo", 23_000_000, "Utilitario"),
        # ── Motos ──────────────────────────────────────────────────────────────
        ("Honda", "CB190R", 4_500_000, "Moto"),
        ("Honda", "CB500F", 9_500_000, "Moto"),
        ("Honda", "XRE300", 6_800_000, "Moto"),
        ("Honda", "CG160", 2_800_000, "Moto"),
        ("Honda", "Wave", 1_800_000, "Moto"),
        ("Yamaha", "FZ25", 4_200_000, "Moto"),
        ("Yamaha", "MT-03", 8_500_000, "Moto"),
        ("Yamaha", "Xtz 125", 2_200_000, "Moto"),
        ("Yamaha", "FZ-S", 3_800_000, "Moto"),
        ("Kawasaki", "Z400", 9_000_000, "Moto"),
        ("Kawasaki", "Ninja 400", 10_500_000, "Moto"),
        ("Kawasaki", "Versys 650", 14_000_000, "Moto"),
        ("Zanella", "ZB 110", 1_400_000, "Moto"),
        ("Zanella", "ZR 70", 1_200_000, "Moto"),
        ("Motomel", "CG150", 1_600_000, "Moto"),
        ("Motomel", "S2 150", 2_000_000, "Moto"),
        ("Bajaj", "Boxer 150", 2_400_000, "Moto"),
        ("Bajaj", "Pulsar NS200", 5_500_000, "Moto"),
        ("Beta", "RR 125", 2_600_000, "Moto"),
        ("Beta", "Tempo 110", 1_500_000, "Moto"),
    ]
    return pd.DataFrame(
        registros,
        columns=["marca_vehiculo", "modelo_vehiculo", "valor_base_2024", "tipo_vehiculo"],
    )


def pesos_marca() -> dict[str, float]:
    return {
        "Volkswagen": 0.12,
        "Fiat": 0.09,
        "Toyota": 0.10,
        "Chevrolet": 0.08,
        "Ford": 0.07,
        "Renault": 0.07,
        "Peugeot": 0.04,
        "Citroën": 0.03,
        "Honda": 0.07,
        "Nissan": 0.04,
        "Jeep": 0.03,
        "Kia": 0.05,
        "Hyundai": 0.05,
        "Chery": 0.03,
        "BYD": 0.02,
        "Suzuki": 0.02,
        "Yamaha": 0.04,
        "Kawasaki": 0.02,
        "Zanella": 0.03,
        "Motomel": 0.03,
        "Bajaj": 0.03,
        "Beta": 0.02,
    }


def estimar_valor_vehiculo(valor_base_2024: float, anio_vehiculo: int) -> float:
    antiguedad = max(0, 2024 - anio_vehiculo)
    factor = max(0.15, (1.0 - 0.12) ** antiguedad)
    return valor_base_2024 * factor


def muestrear_anio_vehiculo(rng: np.random.Generator, n: int) -> np.ndarray:
    anios = np.arange(2005, 2025)
    pesos = np.exp(np.linspace(0.0, 2.4, len(anios)))
    pesos = pesos / pesos.sum()
    return rng.choice(anios, size=n, p=pesos)
