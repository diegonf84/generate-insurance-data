from __future__ import annotations

from typing import Any

from diagnostico.schema import es_escalar, es_tabla


def _delta_pct(prev: float, act: float) -> float | None:
    if prev == 0:
        return None
    return (act - prev) / abs(prev)


def _comparar_tabla(prev: dict, act: dict, top_k: int = 5) -> dict[str, Any]:
    """Compara dos tablas (mismo shape). Devuelve top movers por |delta|."""
    valores_prev = prev.get("valores", {}) or {}
    valores_act = act.get("valores", {}) or {}
    todas = set(valores_prev.keys()) | set(valores_act.keys())
    filas = []
    for k in todas:
        p = float(valores_prev.get(k, 0.0))
        a = float(valores_act.get(k, 0.0))
        filas.append({
            "categoria": k,
            "previo": p,
            "actual": a,
            "delta_abs": a - p,
        })
    filas.sort(key=lambda f: abs(f["delta_abs"]), reverse=True)
    return {
        "tipo": prev.get("tipo", act.get("tipo", "magnitud")),
        "top_movers": filas[:top_k],
        "total_categorias": len(filas),
    }


def _walk(prev: Any, act: Any, ruta: str, escalares: list, tablas: dict) -> None:
    if es_escalar(prev) and es_escalar(act):
        p = float(prev["valor"])
        a = float(act["valor"])
        escalares.append({
            "ruta": ruta,
            "previo": p,
            "actual": a,
            "delta_abs": a - p,
            "delta_pct": _delta_pct(p, a),
            "nota": act.get("nota", ""),
        })
        return
    if es_tabla(prev) and es_tabla(act):
        tablas[ruta] = _comparar_tabla(prev, act)
        return
    if isinstance(prev, dict) and isinstance(act, dict):
        for k in prev:
            if k in act:
                sub_ruta = f"{ruta}.{k}" if ruta else k
                _walk(prev[k], act[k], sub_ruta, escalares, tablas)


def comparar_snapshots(previo: dict[str, Any], actual: dict[str, Any]) -> dict[str, Any]:
    """Estructura: meta_diff, escalares (lista), tablas (dict ruta→top movers)."""
    meta_prev = previo.get("meta", {})
    meta_act = actual.get("meta", {})

    meta_diff = {
        "mismo_config_hash": meta_prev.get("config_hash") == meta_act.get("config_hash"),
        "config_hash_previo": meta_prev.get("config_hash"),
        "config_hash_actual": meta_act.get("config_hash"),
        "seed_previo": meta_prev.get("seed"),
        "seed_actual": meta_act.get("seed"),
        "n_polizas_previo": meta_prev.get("n_polizas"),
        "n_polizas_actual": meta_act.get("n_polizas"),
        "calibracion_previo": meta_prev.get("calibracion", {}),
        "calibracion_actual": meta_act.get("calibracion", {}),
    }

    escalares: list[dict[str, Any]] = []
    tablas: dict[str, dict[str, Any]] = {}

    secciones = ["integridad", "cartera", "suscripcion", "siniestralidad", "cohortes", "productores"]
    for s in secciones:
        if s in previo and s in actual:
            _walk(previo[s], actual[s], s, escalares, tablas)

    return {"meta_diff": meta_diff, "escalares": escalares, "tablas": tablas}
