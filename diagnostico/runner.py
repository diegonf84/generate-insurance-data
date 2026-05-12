from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from config import Config
from diagnostico import cartera, cohortes, integridad, productores, siniestralidad, suscripcion
from diagnostico.markdown import render_markdown


def _config_hash(cfg: Config) -> str:
    """Hash sobre cfg excluyendo campos de ejecución (seed, tamaño de muestra),
    para que dos corridas con los mismos parámetros estructurales y distintas
    seeds compartan hash."""
    cfg_dict = asdict(cfg)
    cfg_dict.pop("random_seed", None)
    cfg_dict.pop("cantidad_polizas", None)
    payload = json.dumps(cfg_dict, sort_keys=True, default=str)
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _parametros_clave(cfg: Config) -> dict[str, Any]:
    return {
        "cantidad_polizas": cfg.cantidad_polizas,
        "n_productores": cfg.n_productores,
        "n_organizadores": cfg.n_organizadores,
        "productor_power_law_exponente": cfg.productor_power_law_exponente,
        "inflacion_anual": {str(k): float(v) for k, v in cfg.inflacion_anual.items()},
        "target_loss": list(cfg.target_loss),
        "target_freq": list(cfg.target_freq),
        "lambda_scale_inicial": cfg.lambda_scale_inicial,
        "severidad_scale_inicial": cfg.severidad_scale_inicial,
        "tasa_cancelacion_base": cfg.tasa_cancelacion_base,
        "bonus_malus_p_sin_claim": cfg.bonus_malus_p_sin_claim,
    }


def build_snapshot(
    df_polizas: pd.DataFrame,
    df_siniestros: pd.DataFrame,
    cfg: Config,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    meta = meta or {}
    cal = {
        "convergio": bool(meta.get("convergio", False)),
        "iteraciones": int(meta.get("iteraciones", 0)),
        "lambda_scale_final": float(meta.get("lambda_scale_final", 0.0)),
        "severidad_scale_final": float(meta.get("severidad_scale_final", 0.0)),
    }
    snapshot = {
        "meta": {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "seed": int(meta.get("seed", cfg.random_seed)),
            "config_hash": _config_hash(cfg),
            "n_polizas": int(len(df_polizas)),
            "n_siniestros": int(len(df_siniestros)),
            "calibracion": cal,
        },
        "parametros_clave": _parametros_clave(cfg),
        "integridad":     integridad.construir(df_polizas, df_siniestros, cfg),
        "cartera":        cartera.construir(df_polizas, df_siniestros, cfg),
        "suscripcion":    suscripcion.construir(df_polizas, df_siniestros, cfg),
        "siniestralidad": siniestralidad.construir(df_polizas, df_siniestros, cfg),
        "cohortes":       cohortes.construir(df_polizas, df_siniestros, cfg),
        "productores":    productores.construir(df_polizas, df_siniestros, cfg),
    }
    return snapshot


class _JsonEncoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.floating,)):
            return float(o)
        if isinstance(o, (np.bool_,)):
            return bool(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
        if isinstance(o, (datetime, date)):
            return o.isoformat()
        if isinstance(o, pd.Timestamp):
            return o.isoformat()
        return super().default(o)


def _listar_snapshots(directorio: Path) -> list[Path]:
    if not directorio.exists():
        return []
    candidatos = sorted(
        directorio.glob("snapshot_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidatos


def _rotar(directorio: Path) -> Path | None:
    """Mantiene como máximo 1 snapshot previo en disco.

    Devuelve la ruta del snapshot previo (más reciente) si existe, o None.
    Borra los pares más viejos (json + md con el mismo prefijo).
    """
    existentes = _listar_snapshots(directorio)
    if not existentes:
        return None
    previo = existentes[0]
    for viejo in existentes[1:]:
        viejo.unlink(missing_ok=True)
        md = viejo.with_suffix(".md")
        md.unlink(missing_ok=True)
    return previo


def escribir_artefactos(snapshot: dict[str, Any], directorio: Path) -> dict[str, Path]:
    directorio = Path(directorio)
    directorio.mkdir(parents=True, exist_ok=True)

    previo_path = _rotar(directorio)
    snapshot_previo: dict[str, Any] | None = None
    if previo_path is not None:
        with previo_path.open("r", encoding="utf-8") as f:
            snapshot_previo = json.load(f)

    meta = snapshot["meta"]
    ts = meta["timestamp"].replace(":", "").replace("-", "").replace("T", "-")
    seed = meta["seed"]
    nombre_base = f"snapshot_{ts}_seed{seed}"
    path_json = directorio / f"{nombre_base}.json"
    path_md = directorio / f"{nombre_base}.md"

    with path_json.open("w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2, cls=_JsonEncoder)

    md = render_markdown(snapshot, snapshot_previo)
    with path_md.open("w", encoding="utf-8") as f:
        f.write(md)

    return {"json": path_json, "md": path_md, "previo": previo_path}
