from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class Config:
    random_seed: int = 42
    cantidad_polizas: int = 50000
    fecha_inicio: date = date(2021, 1, 1)
    fecha_fin: date = date(2024, 12, 31)
    ramo_principal: str = "Automotor"
    ramo_motovehiculos: str = "Motovehiculos"

    target_freq: tuple[float, float] = (0.15, 0.20)
    target_loss: tuple[float, float] = (0.60, 0.80)
    tolerancia_distribucion: float = 0.02

    max_iteraciones_calibracion: int = 12
    lambda_scale_inicial: float = 0.88
    severidad_scale_inicial: float = 1.0

    n_productores: int = 1000
    n_organizadores: int = 50
    prob_productor_en_organizador: float = 0.80
    p_outlier_poliza: float = 0.005

    pesos_tipo_vehiculo: dict[str, float] = field(
        default_factory=lambda: {
            "Auto": 0.78,
            "Moto": 0.12,
            "Camioneta": 0.07,
            "Utilitario": 0.03,
        }
    )

    pesos_cobertura: dict[str, float] = field(
        default_factory=lambda: {
            "Responsabilidad Civil": 0.40,
            "Terceros Completo": 0.35,
            "Todo Riesgo": 0.25,
        }
    )

    pesos_genero: dict[str, float] = field(
        default_factory=lambda: {"M": 0.55, "F": 0.42, "X": 0.03}
    )
    pesos_estado_civil: dict[str, float] = field(
        default_factory=lambda: {
            "Soltero": 0.30,
            "Casado": 0.45,
            "Divorciado": 0.15,
            "Viudo": 0.10,
        }
    )
    pesos_ocupacion: dict[str, float] = field(
        default_factory=lambda: {
            "Empleado": 0.40,
            "Independiente": 0.25,
            "Comerciante": 0.15,
            "Profesional": 0.12,
            "Jubilado": 0.08,
        }
    )
    pesos_canal: dict[str, float] = field(
        default_factory=lambda: {
            "Productor": 0.50,
            "Broker": 0.20,
            "Organizador": 0.15,
            "Directa": 0.10,
            "Online": 0.05,
        }
    )
    pesos_uso: dict[str, float] = field(
        default_factory=lambda: {"Particular": 0.80, "Comercial": 0.15, "Profesional": 0.05}
    )

    pesos_provincia: dict[str, float] = field(
        default_factory=lambda: {
            "Buenos Aires": 0.36,
            "CABA": 0.11,
            "Córdoba": 0.09,
            "Santa Fe": 0.08,
            "Mendoza": 0.05,
            "Tucumán": 0.03,
            "Entre Ríos": 0.03,
            "Neuquén": 0.03,
            "Salta": 0.03,
            "Chaco": 0.02,
            "Río Negro": 0.02,
            "San Juan": 0.02,
            "Misiones": 0.02,
            "La Pampa": 0.02,
            "Corrientes": 0.02,
            "Jujuy": 0.02,
            "Santiago del Estero": 0.02,
            "San Luis": 0.01,
            "Formosa": 0.01,
            "Catamarca": 0.01,
        }
    )

    localidades_por_provincia: dict[str, list[str]] = field(
        default_factory=lambda: {
            "Buenos Aires": [
                "La Plata",
                "Mar del Plata",
                "Bahía Blanca",
                "San Isidro",
                "Quilmes",
                "Morón",
                "Lomas de Zamora",
                "Tigre",
                "San Martín",
                "Tres de Febrero",
                "Lanús",
                "Avellaneda",
                "San Fernando",
                "Merlo",
                "Hurlingham",
                "Campana",
                "Junín",
                "Tandil",
                "Azul",
                "Chivilcoy",
            ],
            "CABA": [
                "Palermo",
                "Caballito",
                "Belgrano",
                "Recoleta",
                "Flores",
                "Almagro",
                "Boedo",
                "Villa Urquiza",
            ],
            "Córdoba": [
                "Córdoba Capital",
                "Villa Carlos Paz",
                "Río Cuarto",
                "San Francisco",
                "Villa María",
                "Bell Ville",
                "Jesús María",
                "Alta Gracia",
                "La Calera",
                "Río Tercero",
                "Oncativo",
                "Cruz del Eje",
            ],
            "Santa Fe": [
                "Rosario",
                "Santa Fe Capital",
                "Rafaela",
                "Venado Tuerto",
                "Villa Constitución",
                "Reconquista",
                "Santo Tomé",
                "Esperanza",
                "Cañada de Gómez",
                "San Lorenzo",
                "Casilda",
                "Firmat",
            ],
            "Mendoza": [
                "Mendoza Capital",
                "Godoy Cruz",
                "San Rafael",
                "Maipú",
                "Luján de Cuyo",
                "Las Heras",
                "Guaymallén",
                "San Martín",
                "Junín",
                "General Alvear",
            ],
            "Tucumán": [
                "San Miguel de Tucumán",
                "Yerba Buena",
                "Tafí Viejo",
                "Banda del Río Salí",
                "Lules",
                "Concepción",
                "Monteros",
                "Aguilares",
            ],
            "Entre Ríos": [
                "Paraná",
                "Concordia",
                "Gualeguaychú",
                "Colón",
                "Villaguay",
                "La Paz",
                "Chajarí",
                "Victoria",
            ],
            "Neuquén": [
                "Neuquén Capital",
                "Plottier",
                "Cutral Có",
                "San Martín de los Andes",
                "Zapala",
                "Centenario",
                "Villa La Angostura",
            ],
            "Salta": [
                "Salta Capital",
                "Orán",
                "Tartagal",
                "Embarcación",
                "Metán",
                "Rosario de la Frontera",
                "Cerrillos",
                "Güemes",
            ],
            "Chaco": [
                "Resistencia",
                "Presidencia Roque Sáenz Peña",
                "Villa Ángela",
                "Charata",
                "Quitilipi",
                "Barranqueras",
            ],
            "Río Negro": [
                "Bariloche",
                "General Roca",
                "Viedma",
                "Cipolletti",
                "Catriel",
                "El Bolsón",
            ],
            "San Juan": [
                "San Juan Capital",
                "Rawson",
                "Chimbas",
                "Rivadavia",
                "Santa Lucía",
            ],
            "Misiones": [
                "Posadas",
                "Oberá",
                "Eldorado",
                "Apóstoles",
                "Puerto Iguazú",
                "San Vicente",
            ],
            "La Pampa": [
                "Santa Rosa",
                "General Pico",
                "Toay",
                "Eduardo Castex",
                "Realicó",
            ],
            "Corrientes": [
                "Corrientes Capital",
                "Goya",
                "Curuzú Cuatiá",
                "Mercedes",
                "Paso de los Libres",
                "Empedrado",
            ],
            "Jujuy": [
                "San Salvador de Jujuy",
                "Palpalá",
                "San Pedro de Jujuy",
                "Libertador General San Martín",
                "Humahuaca",
            ],
            "Santiago del Estero": [
                "Santiago del Estero Capital",
                "La Banda",
                "Termas de Río Hondo",
                "Añatuya",
                "Frías",
            ],
            "San Luis": [
                "San Luis Capital",
                "Villa Mercedes",
                "Merlo",
                "San Francisco del Monte de Oro",
            ],
            "Formosa": [
                "Formosa Capital",
                "Clorinda",
                "Pirané",
                "Las Lomitas",
            ],
            "Catamarca": [
                "Catamarca Capital",
                "Belén",
                "Tinogasta",
                "Santa María",
            ],
        }
    )

    barrios_caba: list[str] = field(
        default_factory=lambda: [
            "Palermo",
            "Belgrano",
            "Caballito",
            "Flores",
            "Recoleta",
            "Boedo",
            "Almagro",
            "Villa Urquiza",
            "Retiro",
            "La Boca",
            "Barracas",
            "Mataderos",
            "Liniers",
            "Colegiales",
            "Villa Crespo",
            "Parque Patricios",
            "Nueva Pompeya",
            "San Telmo",
            "Puerto Madero",
            "Núñez",
            "Saavedra",
            "Villa Devoto",
            "Paternal",
            "Villa del Parque",
            "Balvanera",
            "Constitución",
            "Villa Pueyrredón",
            "Versalles",
        ]
    )
    barrios_gba: list[str] = field(
        default_factory=lambda: [
            "San Isidro Centro",
            "Olivos",
            "Lanús Centro",
            "Lomas Centro",
            "Ramos Mejía",
            "Quilmes Centro",
            "Tigre Centro",
            "San Fernando Centro",
            "Vicente López",
            "Avellaneda Centro",
            "Florencio Varela",
            "Berazategui",
            "Ezeiza Centro",
            "Merlo Centro",
            "Ituzaingó",
            "Morón Centro",
            "Tres de Febrero Centro",
            "El Palomar",
            "Hurlingham Centro",
            "Don Torcuato",
            "Pilar Centro",
            "José C. Paz",
            "Malvinas Argentinas",
            "Garín",
            "Escobar",
        ]
    )

    factor_zona: dict[str, tuple[float, float]] = field(
        default_factory=lambda: {
            "Alta": (1.30, 1.50),
            "Media": (1.00, 1.20),
            "Baja": (0.70, 0.90),
        }
    )

    # Zone-based severity multiplier: urban claims cost more (repairs, lawsuits, theft)
    factor_severidad_por_zona: dict[str, float] = field(
        default_factory=lambda: {
            "Alta": 1.15,
            "Media": 1.00,
            "Baja": 0.85,
        }
    )

    tasa_base_rango: tuple[float, float] = (0.04, 0.06)
    factor_cobertura_tarifa: dict[str, float] = field(
        default_factory=lambda: {
            "Responsabilidad Civil": 0.50,
            "Terceros Completo": 0.75,
            "Todo Riesgo": 1.00,
        }
    )

    comision_por_canal: dict[str, tuple[float, float]] = field(
        default_factory=lambda: {
            "Productor": (0.10, 0.28),
            "Broker": (0.08, 0.22),
            "Organizador": (0.09, 0.25),
            "Directa": (0.00, 0.00),
            "Online": (0.03, 0.10),
        }
    )

    severidad_lognormal: dict[str, tuple[float, float]] = field(
        default_factory=lambda: {
            "Robo total": (15.5, 0.6),
            "Robo parcial": (13.5, 0.7),
            "Choque": (13.8, 0.8),
            "Incendio": (15.0, 0.7),
            "Granizo": (12.5, 0.5),
            "Daño a terceros": (14.5, 1.0),
            "Otros": (12.0, 0.6),
        }
    )

    severidad_lognormal_moto: dict[str, tuple[float, float]] = field(
        default_factory=lambda: {
            "Robo total": (14.2, 0.6),
            "Robo parcial": (12.5, 0.7),
            "Choque": (12.8, 0.8),
            "Incendio": (13.5, 0.7),
            "Granizo": (11.5, 0.5),
            "Daño a terceros": (13.5, 1.0),
            "Otros": (11.0, 0.6),
        }
    )

    inflacion_anual: dict[int, float] = field(
        default_factory=lambda: {2021: 1.0, 2022: 1.5, 2023: 2.5, 2024: 4.0}
    )

    prob_tipo_danio_por_zona: dict[str, dict[str, float]] = field(
        default_factory=lambda: {
            "Alta": {
                "Robo total": 0.15,
                "Robo parcial": 0.10,
                "Choque": 0.35,
                "Incendio": 0.03,
                "Granizo": 0.05,
                "Daño a terceros": 0.25,
                "Otros": 0.07,
            },
            "Media": {
                "Robo total": 0.08,
                "Robo parcial": 0.05,
                "Choque": 0.40,
                "Incendio": 0.03,
                "Granizo": 0.08,
                "Daño a terceros": 0.28,
                "Otros": 0.08,
            },
            "Baja": {
                "Robo total": 0.03,
                "Robo parcial": 0.02,
                "Choque": 0.45,
                "Incendio": 0.04,
                "Granizo": 0.10,
                "Daño a terceros": 0.28,
                "Otros": 0.08,
            },
        }
    )

    prob_tipo_danio_moto: dict[str, float] = field(
        default_factory=lambda: {
            "Choque": 0.45,
            "Daño a terceros": 0.18,
            "Robo parcial": 0.12,
            "Robo total": 0.08,
            "Otros": 0.12,
            "Granizo": 0.03,
            "Incendio": 0.02,
        }
    )


def construir_config(cantidad_polizas: int | None = None, seed: int | None = None) -> Config:
    cfg = Config()
    if cantidad_polizas is not None:
        cfg.cantidad_polizas = cantidad_polizas
    if seed is not None:
        cfg.random_seed = seed
    return cfg
