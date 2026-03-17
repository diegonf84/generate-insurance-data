from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class Config:
    random_seed: int = 42
    cantidad_polizas: int = 100_000
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
                # GBA (zona Alta)
                "San Isidro", "Quilmes", "Morón", "Lomas de Zamora", "Tigre",
                "San Martín", "Tres de Febrero", "Lanús", "Avellaneda", "San Fernando",
                "Merlo", "Hurlingham", "Florencio Varela", "Berazategui", "Esteban Echeverría",
                "Almirante Brown", "Ezeiza", "Ituzaingó", "Malvinas Argentinas", "José C. Paz",
                "San Miguel", "Moreno", "Pilar", "Escobar", "Vicente López",
                # Interior Bs As (zona Media)
                "La Plata", "Mar del Plata", "Bahía Blanca", "Campana", "Junín",
                "Tandil", "Azul", "Chivilcoy", "Zárate", "Olavarría",
                "Pergamino", "San Nicolás", "Necochea", "Luján", "Mercedes",
                "Chascomús", "Dolores", "Lobos", "San Pedro", "Ramallo",
                "Trenque Lauquen", "Pehuajó", "Bolívar", "9 de Julio", "Bragado",
                "Chacabuco", "Arrecifes", "Salto", "Rojas", "Lincoln",
                "General Villegas", "Tres Arroyos", "Coronel Suárez", "Balcarce", "Miramar",
                "Villa Gesell", "Pinamar", "San Clemente del Tuyú", "General Pueyrredón",
            ],
            "CABA": [
                "Palermo", "Caballito", "Belgrano", "Recoleta", "Flores",
                "Almagro", "Boedo", "Villa Urquiza", "Retiro", "La Boca",
                "Barracas", "Mataderos", "Liniers", "Colegiales", "Villa Crespo",
                "Parque Patricios", "Nueva Pompeya", "San Telmo", "Puerto Madero",
                "Núñez", "Saavedra", "Villa Devoto", "Paternal", "Villa del Parque",
                "Balvanera", "Constitución", "Villa Pueyrredón", "Versalles",
                "Chacarita", "Villa Ortúzar", "Agronomía", "Parque Chas",
                "Monte Castro", "Villa Luro", "Vélez Sarsfield", "Floresta",
                "Villa Real", "Villa Santa Rita", "Villa Soldati", "Parque Avellaneda",
                "San Cristóbal", "Monserrat", "San Nicolás", "Parque Centenario",
            ],
            "Córdoba": [
                "Córdoba Capital", "Villa Carlos Paz", "Río Cuarto", "San Francisco",
                "Villa María", "Bell Ville", "Jesús María", "Alta Gracia",
                "La Calera", "Río Tercero", "Oncativo", "Cruz del Eje",
                "Cosquín", "La Falda", "Unquillo", "Río Ceballos",
                "Dean Funes", "Morteros", "Las Varillas", "Marcos Juárez",
                "Laboulaye", "General Cabrera", "Hernando", "Arroyito",
                "Oliva", "Villa Dolores", "Mina Clavero", "Villa General Belgrano",
                "Almafuerte", "Colonia Caroya", "Villa Allende", "Mendiolaza",
                "Saldán", "General Deheza", "Leones", "Corral de Bustos",
            ],
            "Santa Fe": [
                "Rosario", "Santa Fe Capital", "Rafaela", "Venado Tuerto",
                "Villa Constitución", "Reconquista", "Santo Tomé", "Esperanza",
                "Cañada de Gómez", "San Lorenzo", "Casilda", "Firmat",
                "Sunchales", "San Jorge", "Rufino", "Tostado",
                "Gálvez", "Coronda", "Fray Luis Beltrán", "Capitán Bermúdez",
                "Granadero Baigorria", "Pérez", "Funes", "Roldán",
                "Arroyo Seco", "San Genaro", "Las Rosas", "Armstrong",
                "Las Parejas", "Carcarañá", "Totoras", "San Cristóbal",
                "Vera", "Avellaneda", "Villa Gobernador Gálvez", "Rosario Norte",
            ],
            "Mendoza": [
                "Mendoza Capital", "Godoy Cruz", "San Rafael", "Maipú",
                "Luján de Cuyo", "Las Heras", "Guaymallén", "San Martín",
                "Junín", "General Alvear", "Rivadavia", "Tunuyán",
                "Tupungato", "San Carlos", "Malargüe", "Alvear",
                "La Paz", "Santa Rosa", "Lavalle", "Palmira",
                "Chacras de Coria", "Vistalba", "Coquimbito", "Rodeo del Medio",
            ],
            "Tucumán": [
                "San Miguel de Tucumán", "Yerba Buena", "Tafí Viejo",
                "Banda del Río Salí", "Lules", "Concepción", "Monteros", "Aguilares",
                "Famaillá", "Simoca", "Juan Bautista Alberdi", "Tafí del Valle",
                "Bella Vista", "Burruyacú", "La Cocha", "Graneros",
            ],
            "Entre Ríos": [
                "Paraná", "Concordia", "Gualeguaychú", "Colón",
                "Villaguay", "La Paz", "Chajarí", "Victoria",
                "Concepción del Uruguay", "Nogoyá", "Federación", "Federal",
                "Diamante", "Crespo", "San José de Feliciano", "Gualeguay",
                "Basavilbaso", "Rosario del Tala", "San Salvador", "Larroque",
            ],
            "Neuquén": [
                "Neuquén Capital", "Plottier", "Cutral Có",
                "San Martín de los Andes", "Zapala", "Centenario", "Villa La Angostura",
                "Junín de los Andes", "Chos Malal", "Rincón de los Sauces",
                "Senillosa", "Vista Alegre", "Añelo", "Plaza Huincul",
            ],
            "Salta": [
                "Salta Capital", "Orán", "Tartagal", "Embarcación",
                "Metán", "Rosario de la Frontera", "Cerrillos", "Güemes",
                "San Lorenzo", "Cafayate", "Joaquín V. González", "General Mosconi",
                "Campo Quijano", "Chicoana", "La Merced", "Vaqueros",
            ],
            "Chaco": [
                "Resistencia", "Presidencia Roque Sáenz Peña", "Villa Ángela",
                "Charata", "Quitilipi", "Barranqueras", "General San Martín",
                "Las Breñas", "Machagai", "Juan José Castelli",
                "Fontana", "Puerto Tirol", "Tres Isletas", "Corzuela",
            ],
            "Río Negro": [
                "Bariloche", "General Roca", "Viedma", "Cipolletti",
                "Catriel", "El Bolsón", "Allen", "Choele Choel",
                "Villa Regina", "Cinco Saltos", "Ingeniero Huergo",
                "San Antonio Oeste", "Sierra Grande", "Luis Beltrán",
            ],
            "San Juan": [
                "San Juan Capital", "Rawson", "Chimbas", "Rivadavia", "Santa Lucía",
                "Pocito", "Caucete", "Albardón", "San José de Jáchal",
                "Calingasta", "Iglesia", "Valle Fértil", "25 de Mayo",
            ],
            "Misiones": [
                "Posadas", "Oberá", "Eldorado", "Apóstoles",
                "Puerto Iguazú", "San Vicente", "Leandro N. Alem",
                "Jardín América", "Puerto Rico", "Montecarlo",
                "San Pedro", "Wanda", "Aristóbulo del Valle", "Candelaria",
            ],
            "La Pampa": [
                "Santa Rosa", "General Pico", "Toay", "Eduardo Castex", "Realicó",
                "General Acha", "Victorica", "Intendente Alvear", "Macachín",
                "Guatraché", "Quemú Quemú", "Catriló", "Trenel",
            ],
            "Corrientes": [
                "Corrientes Capital", "Goya", "Curuzú Cuatiá", "Mercedes",
                "Paso de los Libres", "Empedrado", "Monte Caseros", "Santo Tomé",
                "Bella Vista", "Esquina", "Sauce", "Ituzaingó",
                "Alvear", "San Luis del Palmar", "Saladas", "San Roque",
            ],
            "Jujuy": [
                "San Salvador de Jujuy", "Palpalá", "San Pedro de Jujuy",
                "Libertador General San Martín", "Humahuaca",
                "Tilcara", "La Quiaca", "Abra Pampa", "Monterrico",
                "El Carmen", "Perico", "Fraile Pintado", "Calilegua",
            ],
            "Santiago del Estero": [
                "Santiago del Estero Capital", "La Banda", "Termas de Río Hondo",
                "Añatuya", "Frías", "Fernández", "Loreto",
                "Monte Quemado", "Quimilí", "Suncho Corral",
                "Campo Gallo", "Clodomira", "Beltrán", "Ojo de Agua",
            ],
            "San Luis": [
                "San Luis Capital", "Villa Mercedes", "Merlo",
                "San Francisco del Monte de Oro", "Justo Daract",
                "La Toma", "Concarán", "Tilisarao", "Naschel",
                "Buena Esperanza", "Santa Rosa del Conlara", "Quines",
            ],
            "Formosa": [
                "Formosa Capital", "Clorinda", "Pirané", "Las Lomitas",
                "El Colorado", "Ibarreta", "Comandante Fontana",
                "Laguna Blanca", "Ingeniero Juárez", "Villa General Güemes",
            ],
            "Catamarca": [
                "Catamarca Capital", "Belén", "Tinogasta", "Santa María",
                "Andalgalá", "Recreo", "Fiambalá", "Chumbicha",
                "Saujil", "Londres", "Hualfín", "Pomán",
            ],
        }
    )

    barrios_caba: list[str] = field(
        default_factory=lambda: [
            "Palermo", "Belgrano", "Caballito", "Flores", "Recoleta", "Boedo",
            "Almagro", "Villa Urquiza", "Retiro", "La Boca", "Barracas", "Mataderos",
            "Liniers", "Colegiales", "Villa Crespo", "Parque Patricios", "Nueva Pompeya",
            "San Telmo", "Puerto Madero", "Núñez", "Saavedra", "Villa Devoto",
            "Paternal", "Villa del Parque", "Balvanera", "Constitución",
            "Villa Pueyrredón", "Versalles", "Chacarita", "Villa Ortúzar",
            "Agronomía", "Parque Chas", "Monte Castro", "Villa Luro",
            "Vélez Sarsfield", "Floresta", "Villa Real", "Villa Santa Rita",
            "Villa Soldati", "Parque Avellaneda", "San Cristóbal", "Monserrat",
            "San Nicolás", "Parque Centenario", "Villa Riachuelo", "Villa Lugano",
            "Pompeya", "Barrio Norte",
        ]
    )
    barrios_gba: list[str] = field(
        default_factory=lambda: [
            "San Isidro Centro", "Olivos", "Lanús Centro", "Lomas Centro",
            "Ramos Mejía", "Quilmes Centro", "Tigre Centro", "San Fernando Centro",
            "Vicente López", "Avellaneda Centro", "Florencio Varela", "Berazategui",
            "Ezeiza Centro", "Merlo Centro", "Ituzaingó", "Morón Centro",
            "Tres de Febrero Centro", "El Palomar", "Hurlingham Centro", "Don Torcuato",
            "Pilar Centro", "José C. Paz", "Malvinas Argentinas", "Garín", "Escobar",
            "Martínez", "Acassuso", "Béccar", "Victoria", "Boulogne",
            "Munro", "Florida", "Carapachay", "Villa Adelina", "Caseros",
            "Santos Lugares", "Ciudadela", "Temperley", "Banfield", "Remedios de Escalada",
            "Adrogué", "Burzaco", "Monte Grande", "Canning", "Tristán Suárez",
            "Claypole", "Rafael Calzada", "Longchamps", "Glew", "San Justo",
            "Isidro Casanova", "González Catán", "Laferrere", "Tapiales",
            "San Miguel Centro", "Bella Vista", "Muñiz", "Grand Bourg",
            "Tortuguitas", "Del Viso", "Ingeniero Maschwitz", "Los Polvorines",
        ]
    )

    factor_zona: dict[str, tuple[float, float]] = field(
        default_factory=lambda: {
            "Alta": (1.30, 1.50),
            "Media": (1.00, 1.20),
            "Baja": (0.70, 0.90),
        }
    )

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
                "Robo total": 0.15, "Robo parcial": 0.10, "Choque": 0.35,
                "Incendio": 0.03, "Granizo": 0.05, "Daño a terceros": 0.25, "Otros": 0.07,
            },
            "Media": {
                "Robo total": 0.08, "Robo parcial": 0.05, "Choque": 0.40,
                "Incendio": 0.03, "Granizo": 0.08, "Daño a terceros": 0.28, "Otros": 0.08,
            },
            "Baja": {
                "Robo total": 0.03, "Robo parcial": 0.02, "Choque": 0.45,
                "Incendio": 0.04, "Granizo": 0.10, "Daño a terceros": 0.28, "Otros": 0.08,
            },
        }
    )

    prob_tipo_danio_moto: dict[str, float] = field(
        default_factory=lambda: {
            "Choque": 0.45, "Daño a terceros": 0.18, "Robo parcial": 0.12,
            "Robo total": 0.08, "Otros": 0.12, "Granizo": 0.03, "Incendio": 0.02,
        }
    )

    # ── NEW: Estado del siniestro + reservas/pagos ──────────────────────────
    # Probabilidad de cada estado del siniestro.
    # Cerrado = liquidado y pagado. Abierto = en gestión. Rechazado = sin pago.
    prob_estado_siniestro: dict[str, float] = field(
        default_factory=lambda: {
            "Cerrado": 0.68,
            "Abierto": 0.25,
            "Rechazado": 0.07,
        }
    )
    # Factor de ruido sobre el monto_reclamado para generar la reserva inicial.
    # reserva = monto_reclamado * uniform(rango[0], rango[1])
    factor_reserva_rango: tuple[float, float] = (0.85, 1.30)
    # Qué porcentaje del reclamado se paga en siniestros cerrados.
    factor_pago_cerrado_rango: tuple[float, float] = (0.70, 1.05)
    # Siniestros abiertos: pago parcial (anticipo) en este rango del reclamado.
    factor_pago_abierto_rango: tuple[float, float] = (0.0, 0.40)

    # ── NEW: Motivo de rechazo del siniestro ────────────────────────────────
    pesos_motivo_rechazo: dict[str, float] = field(
        default_factory=lambda: {
            "Falta de cobertura": 0.28,
            "Mora en el pago": 0.22,
            "Exclusión contractual": 0.18,
            "Documentación incompleta": 0.17,
            "Fraude presunto": 0.15,
        }
    )

    # ── NEW: Gastos de liquidación ──────────────────────────────────────────
    # gasto = max(gasto_base, monto_reclamado * gasto_pct) * mult_juicio_si_aplica
    # Mínimo fijo por siniestro (honorarios perito, gastos administrativos).
    gasto_liquidacion_base: float = 45_000
    # Porcentaje del monto reclamado que se suma como gasto variable.
    gasto_liquidacion_pct: float = 0.05
    # Multiplicador si el siniestro está en juicio (abogados, costas).
    gasto_liquidacion_mult_juicio: float = 2.5
    # Multiplicador si hay mediación (pero no juicio).
    gasto_liquidacion_mult_mediacion: float = 1.4

    # ── NEW: Factores demográficos sobre frecuencia ─────────────────────────
    # Multiplicadores aplicados a lambda en _lambda_por_segmento().
    # "soltero_joven": Soltero + edad < 25 → mayor riesgo.
    # "jubilado": Jubilado → menor exposición, menos km.
    # "divorciado_joven": Divorciado + edad < 35 → leve incremento.
    factor_demografico_frecuencia: dict[str, float] = field(
        default_factory=lambda: {
            "soltero_joven": 1.18,
            "jubilado": 0.85,
            "divorciado_joven": 1.08,
        }
    )

    # ── NEW: Cancelaciones mid-term ─────────────────────────────────────────
    # Tasa base de cancelación antes de fin de vigencia.
    tasa_cancelacion_base: float = 0.07
    # Distribución de motivos de cancelación.
    pesos_motivo_cancelacion: dict[str, float] = field(
        default_factory=lambda: {
            "Mora prolongada": 0.35,
            "Venta del vehículo": 0.25,
            "Cambio de compañía": 0.25,
            "Voluntaria": 0.15,
        }
    )
    # Pólizas con mora >= este umbral tienen mayor probabilidad de cancelación.
    mora_umbral_cancelacion: int = 3

    # ── NEW: Cadenas de renovación (cohortes) ───────────────────────────────
    # Distribución de cantidad de períodos por cliente.
    # La clave es el número de pólizas en la cadena (1 = solo una, sin renovación).
    # Estos pesos se aplican al generar clientes; el total de pólizas se mantiene
    # cercano a cantidad_polizas.
    pesos_periodos_cliente: dict[int, float] = field(
        default_factory=lambda: {
            1: 0.45,   # ~45% clientes con una sola póliza
            2: 0.28,   # ~28% con 1 renovación
            3: 0.18,   # ~18% con 2 renovaciones
            4: 0.09,   # ~9% con 3 renovaciones (más fieles)
        }
    )
    # Factor de ajuste de prima en cada renovación (simula inflación + experiencia).
    ajuste_prima_renovacion_rango: tuple[float, float] = (1.10, 1.35)
    # Probabilidad de cambiar de cobertura en una renovación.
    prob_cambio_cobertura_renovacion: float = 0.12


def construir_config(cantidad_polizas: int | None = None, seed: int | None = None) -> Config:
    cfg = Config()
    if cantidad_polizas is not None:
        cfg.cantidad_polizas = cantidad_polizas
    if seed is not None:
        cfg.random_seed = seed
    return cfg
