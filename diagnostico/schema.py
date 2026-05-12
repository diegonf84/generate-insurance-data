from __future__ import annotations

from typing import Any


def crear_metrica(
    valor: float | int,
    banda: tuple[float, float] | None = None,
    status: str | None = None,
    nota: str = "",
) -> dict[str, Any]:
    """Métrica escalar con shape uniforme.

    Si `status` es None y hay `banda`, se deriva: 'ok' si valor está adentro,
    'watch' si está afuera. Sin banda → 'info'.
    """
    if status is None:
        if banda is None:
            status = "info"
        else:
            status = "ok" if banda[0] <= valor <= banda[1] else "watch"
    return {
        "valor": valor,
        "banda": list(banda) if banda is not None else None,
        "status": status,
        "nota": nota,
    }


def crear_distribucion(
    valores: dict[str, float],
    esperado_config: dict[str, float] | None = None,
    tolerancia: float = 0.02,
    nota: str = "",
) -> dict[str, Any]:
    """Distribución (shares que suman ≈ 1)."""
    desvio_max: float | None = None
    status = "info"
    if esperado_config:
        desvios = [abs(float(valores.get(k, 0.0)) - p) for k, p in esperado_config.items()]
        desvio_max = float(max(desvios)) if desvios else 0.0
        status = "ok" if desvio_max <= tolerancia else "watch"
    return {
        "tipo": "distribucion",
        "valores": valores,
        "esperado_config": esperado_config,
        "desvio_max": desvio_max,
        "status": status,
        "nota": nota,
    }


def crear_tabla(valores: dict[str, float], nota: str = "") -> dict[str, Any]:
    """Tabla de magnitudes (label → número, no necesariamente shares)."""
    return {
        "tipo": "magnitud",
        "valores": valores,
        "esperado_config": None,
        "desvio_max": None,
        "status": "info",
        "nota": nota,
    }


def es_tabla(obj: Any) -> bool:
    return isinstance(obj, dict) and obj.get("tipo") in ("distribucion", "magnitud")


def es_escalar(obj: Any) -> bool:
    return isinstance(obj, dict) and "valor" in obj and obj.get("tipo") not in ("distribucion", "magnitud")
