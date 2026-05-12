from __future__ import annotations

from typing import Any

from diagnostico.diff import comparar_snapshots
from diagnostico.schema import es_escalar, es_tabla


_STATUS_SIGNO = {"ok": "✓", "watch": "⚠", "info": "·"}


def _fmt_num(v: Any) -> str:
    if v is None:
        return "—"
    if isinstance(v, bool):
        return "sí" if v else "no"
    if isinstance(v, int):
        return f"{v:,}"
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v)
    if abs(f) >= 1_000_000:
        return f"{f:,.0f}"
    if abs(f) >= 1_000:
        return f"{f:,.2f}"
    if abs(f) < 1 and f != 0:
        return f"{f:.4f}"
    return f"{f:.4f}"


def _fmt_pct(v: float | None) -> str:
    if v is None:
        return "—"
    return f"{v*100:+.2f}%"


def _signo(status: str) -> str:
    return _STATUS_SIGNO.get(status, "·")


def _tabla(headers: list[str], filas: list[list[str]]) -> str:
    sep = "| " + " | ".join("---" for _ in headers) + " |"
    head = "| " + " | ".join(headers) + " |"
    body = "\n".join("| " + " | ".join(f) + " |" for f in filas)
    return f"{head}\n{sep}\n{body}\n"


def _render_escalar(nombre: str, m: dict[str, Any]) -> list[str]:
    banda = m.get("banda")
    banda_str = "—" if banda is None else f"[{_fmt_num(banda[0])}, {_fmt_num(banda[1])}]"
    return [nombre, _fmt_num(m.get("valor")), banda_str, _signo(m.get("status", "info")), m.get("nota", "")]


def _render_tabla_seccion(titulo: str, t: dict[str, Any], top_n: int = 10) -> str:
    valores = t.get("valores", {}) or {}
    if not valores:
        return f"\n_{titulo}: sin datos_\n"
    items = sorted(valores.items(), key=lambda kv: kv[1], reverse=True)[:top_n]
    esperado = t.get("esperado_config") or {}
    desvio = t.get("desvio_max")
    nota = t.get("nota", "")

    if t.get("tipo") == "distribucion":
        headers = ["categoría", "share obs.", "share cfg.", "desvío"]
        filas = []
        for k, v in items:
            esp = esperado.get(k)
            esp_s = _fmt_num(esp) if esp is not None else "—"
            dev_s = _fmt_num(abs(v - esp)) if esp is not None else "—"
            filas.append([str(k), _fmt_num(v), esp_s, dev_s])
        extra = f" (desvío máx. {_fmt_num(desvio)}, status {_signo(t.get('status','info'))})" if desvio is not None else ""
    else:
        headers = ["categoría", "valor"]
        filas = [[str(k), _fmt_num(v)] for k, v in items]
        extra = ""

    out = f"\n**{titulo}**{extra}\n"
    if nota:
        out += f"_{nota}_\n\n"
    out += _tabla(headers, filas)
    return out


def _sec_cabecera(snapshot: dict[str, Any]) -> str:
    meta = snapshot.get("meta", {})
    cal = meta.get("calibracion", {})
    return (
        f"# Diagnóstico de corrida\n\n"
        f"- **Timestamp:** `{meta.get('timestamp', '—')}`\n"
        f"- **Seed:** `{meta.get('seed', '—')}`\n"
        f"- **Config hash:** `{meta.get('config_hash', '—')}`\n"
        f"- **Pólizas:** {_fmt_num(meta.get('n_polizas'))}\n"
        f"- **Siniestros:** {_fmt_num(meta.get('n_siniestros'))}\n"
        f"- **Calibración:** convergió = {_fmt_num(cal.get('convergio'))}, "
        f"iteraciones = {_fmt_num(cal.get('iteraciones'))}, "
        f"`lambda_scale_final` = {_fmt_num(cal.get('lambda_scale_final'))}, "
        f"`severidad_scale_final` = {_fmt_num(cal.get('severidad_scale_final'))}\n"
    )


def _sec_parametros(snapshot: dict[str, Any]) -> str:
    params = snapshot.get("parametros_clave", {})
    if not params:
        return ""
    filas = []
    for k, v in params.items():
        if isinstance(v, dict):
            v_s = ", ".join(f"{kk}={_fmt_num(vv)}" for kk, vv in v.items())
        elif isinstance(v, (list, tuple)):
            v_s = f"[{_fmt_num(v[0])}, {_fmt_num(v[1])}]" if len(v) == 2 else str(v)
        else:
            v_s = _fmt_num(v)
        filas.append([k, v_s])
    return "\n## Parámetros clave\n\n" + _tabla(["parámetro", "valor"], filas)


def _sec_generales(snapshot: dict[str, Any]) -> str:
    """Selecciona métricas escalares clave de varias secciones para una tabla resumen."""
    rutas = [
        ("siniestralidad.loss_ratio", "loss_ratio"),
        ("siniestralidad.loss_ratio_pagado", "loss_ratio_pagado"),
        ("siniestralidad.expense_ratio", "expense_ratio"),
        ("siniestralidad.combined_ratio", "combined_ratio"),
        ("siniestralidad.frecuencia_siniestral", "frecuencia"),
        ("siniestralidad.severidad_promedio", "severidad_promedio"),
        ("siniestralidad.tasa_rechazo", "tasa_rechazo"),
        ("cohortes.tasa_renovacion", "tasa_renovacion"),
        ("cohortes.tasa_cancelacion", "tasa_cancelacion"),
        ("cohortes.n_clientes_unicos", "n_clientes_unicos"),
        ("suscripcion.prima_media", "prima_media"),
    ]
    filas = []
    for ruta, label in rutas:
        seccion, clave = ruta.split(".", 1)
        m = snapshot.get(seccion, {}).get(clave)
        if not es_escalar(m):
            continue
        filas.append(_render_escalar(label, m))
    if not filas:
        return ""
    return "\n## Métricas generales\n\n" + _tabla(
        ["métrica", "valor", "banda", "status", "nota"], filas
    )


def _sec_integridad(snapshot: dict[str, Any]) -> str:
    intg = snapshot.get("integridad", {})
    checks = intg.get("checks", {})
    if not checks:
        return ""
    filas = [[k, "✓" if v else "✗"] for k, v in checks.items()]
    todos = "✓" if intg.get("todos_ok") else "✗"
    return f"\n## Integridad (todos ok: {todos})\n\n" + _tabla(["check", "estado"], filas)


def _sec_composicion(snapshot: dict[str, Any]) -> str:
    cartera = snapshot.get("cartera", {})
    if not cartera:
        return ""
    out = "\n## Composición de cartera\n"
    for nombre in ["distribucion_zona", "distribucion_canal", "distribucion_cobertura", "distribucion_tipo_vehiculo"]:
        if nombre in cartera:
            out += _render_tabla_seccion(nombre, cartera[nombre], top_n=10)
    return out


def _sec_siniestralidad_dim(snapshot: dict[str, Any]) -> str:
    sin_ = snapshot.get("siniestralidad", {})
    if not sin_:
        return ""
    out = "\n## Siniestralidad por dimensión\n"
    for nombre in ["loss_ratio_por_zona", "loss_ratio_por_cobertura", "loss_ratio_por_banda_calidad_productor", "severidad_por_tipo_dano"]:
        if nombre in sin_:
            out += _render_tabla_seccion(nombre, sin_[nombre], top_n=15)
    return out


def _sec_productores(snapshot: dict[str, Any]) -> str:
    p = snapshot.get("productores", {})
    if not p:
        return ""
    filas = []
    for k in ["n_productores_activos", "top1_share", "top5_share", "top10_share", "herfindahl_hhi", "factor_calidad_promedio", "factor_calidad_std"]:
        m = p.get(k)
        if es_escalar(m):
            filas.append(_render_escalar(k, m))
    out = "\n## Productores\n\n"
    if filas:
        out += _tabla(["métrica", "valor", "banda", "status", "nota"], filas)
    if "distribucion_calidad_productor" in p:
        out += _render_tabla_seccion("distribucion_calidad_productor", p["distribucion_calidad_productor"])
    if "loss_ratio_por_banda_calidad" in p:
        out += _render_tabla_seccion("loss_ratio_por_banda_calidad", p["loss_ratio_por_banda_calidad"])
    return out


def _sec_comparacion(snapshot_actual: dict[str, Any], snapshot_previo: dict[str, Any]) -> str:
    diff = comparar_snapshots(snapshot_previo, snapshot_actual)
    md = diff["meta_diff"]
    cal_p = md.get("calibracion_previo", {}) or {}
    cal_a = md.get("calibracion_actual", {}) or {}

    out = "\n## Comparación vs corrida anterior\n\n"
    out += f"- **Mismo config hash:** {_fmt_num(md['mismo_config_hash'])}\n"
    out += f"- **Seed:** {md.get('seed_previo')} → {md.get('seed_actual')}\n"
    out += f"- **n_polizas:** {_fmt_num(md.get('n_polizas_previo'))} → {_fmt_num(md.get('n_polizas_actual'))}\n"
    out += (
        f"- **Calibración:** convergió {_fmt_num(cal_p.get('convergio'))} → {_fmt_num(cal_a.get('convergio'))}, "
        f"iteraciones {_fmt_num(cal_p.get('iteraciones'))} → {_fmt_num(cal_a.get('iteraciones'))}, "
        f"severidad_scale {_fmt_num(cal_p.get('severidad_scale_final'))} → {_fmt_num(cal_a.get('severidad_scale_final'))}\n"
    )

    # Escalares: tabla con todos los pares
    if diff["escalares"]:
        # priorizar los más material por |delta_pct|, y desempatar por |delta_abs|
        ordenados = sorted(
            diff["escalares"],
            key=lambda e: (
                abs(e["delta_pct"]) if e["delta_pct"] is not None else 0,
                abs(e["delta_abs"]),
            ),
            reverse=True,
        )
        filas = []
        for e in ordenados[:25]:
            filas.append([
                e["ruta"],
                _fmt_num(e["previo"]),
                _fmt_num(e["actual"]),
                _fmt_num(e["delta_abs"]),
                _fmt_pct(e["delta_pct"]),
            ])
        out += "\n**Escalares (top 25 por magnitud de delta):**\n\n"
        out += _tabla(["ruta", "previo", "actual", "Δ abs", "Δ %"], filas)

    if diff["tablas"]:
        out += "\n**Top movers por tabla (hasta 5 categorías por sección):**\n"
        for ruta, info in diff["tablas"].items():
            movers = info.get("top_movers", [])
            if not movers or all(m["delta_abs"] == 0 for m in movers):
                continue
            out += f"\n_{ruta}_\n\n"
            filas = [
                [m["categoria"], _fmt_num(m["previo"]), _fmt_num(m["actual"]), _fmt_num(m["delta_abs"])]
                for m in movers
            ]
            out += _tabla(["categoría", "previo", "actual", "Δ abs"], filas)
    return out


def render_markdown(snapshot_actual: dict[str, Any], snapshot_previo: dict[str, Any] | None = None) -> str:
    partes = [
        _sec_cabecera(snapshot_actual),
        _sec_parametros(snapshot_actual),
        _sec_generales(snapshot_actual),
        _sec_integridad(snapshot_actual),
        _sec_composicion(snapshot_actual),
        _sec_siniestralidad_dim(snapshot_actual),
        _sec_productores(snapshot_actual),
    ]
    if snapshot_previo:
        partes.append(_sec_comparacion(snapshot_actual, snapshot_previo))
    return "\n".join(p for p in partes if p)
