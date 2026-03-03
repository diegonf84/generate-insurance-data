from __future__ import annotations

import argparse
from pathlib import Path

from config import Config, construir_config
from generadores.polizas import ajustar_renovada_por_siniestros, generar_polizas
from generadores.siniestros import generar_siniestros
from validaciones import calcular_metricas, imprimir_reporte, validar_integridad


def _en_rango(valor: float, objetivo: tuple[float, float]) -> bool:
    return objetivo[0] <= valor <= objetivo[1]


def ejecutar_pipeline(cfg: Config, output_dir: Path) -> None:
    lambda_scale = cfg.lambda_scale_inicial
    severidad_scale = cfg.severidad_scale_inicial

    mejor = None
    convergio = False

    for it in range(1, cfg.max_iteraciones_calibracion + 1):
        polizas_seed = cfg.random_seed + it * 100
        siniestros_seed = cfg.random_seed + it * 100 + 1

        df_polizas = generar_polizas(cfg, seed=polizas_seed)
        df_siniestros = generar_siniestros(
            df_polizas,
            cfg,
            lambda_scale=lambda_scale,
            severidad_scale=severidad_scale,
            seed=siniestros_seed,
        )

        rng_renov = __import__("numpy").random.default_rng(cfg.random_seed + it * 100 + 2)
        df_polizas["renovada"] = ajustar_renovada_por_siniestros(df_polizas, df_siniestros, rng_renov)

        metricas = calcular_metricas(df_polizas, df_siniestros, cfg)
        freq = metricas["frecuencia_siniestral"]
        loss = metricas["loss_ratio"]

        mejor = (df_polizas, df_siniestros, metricas, lambda_scale, severidad_scale, it)

        ok_freq = _en_rango(freq, cfg.target_freq)
        ok_loss = _en_rango(loss, cfg.target_loss)

        print(
            f"Iteración {it:02d} | frecuencia={freq:.4f} | loss_ratio={loss:.4f} "
            f"| lambda_scale={lambda_scale:.4f} | severidad_scale={severidad_scale:.4f}"
        )

        if ok_freq and ok_loss:
            convergio = True
            break

        if freq < cfg.target_freq[0]:
            lambda_scale *= 1.12
        elif freq > cfg.target_freq[1]:
            lambda_scale *= 0.90

        if loss < cfg.target_loss[0]:
            severidad_scale *= 1.12
        elif loss > cfg.target_loss[1]:
            severidad_scale *= 0.90

    assert mejor is not None
    df_polizas, df_siniestros, metricas, lambda_scale, severidad_scale, it = mejor

    validaciones = validar_integridad(df_polizas, df_siniestros)
    imprimir_reporte(validaciones, metricas, cfg)

    output_dir.mkdir(parents=True, exist_ok=True)
    path_polizas = output_dir / "polizas_sinteticas.csv"
    path_siniestros = output_dir / "siniestros_sinteticos.csv"

    df_polizas.to_csv(path_polizas, index=False, encoding="utf-8")
    df_siniestros.to_csv(path_siniestros, index=False, encoding="utf-8")

    if convergio:
        print(
            "Calibración convergida.",
            f"Iteración={it}, lambda_scale={lambda_scale:.4f}, severidad_scale={severidad_scale:.4f}",
        )
    else:
        print(
            "ADVERTENCIA: no convergió completamente dentro del máximo de iteraciones.",
            f"Última iteración={it}, lambda_scale={lambda_scale:.4f}, severidad_scale={severidad_scale:.4f}",
        )

    print(f"CSV pólizas: {path_polizas}")
    print(f"CSV siniestros: {path_siniestros}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generador sintético de cartera automotor")
    parser.add_argument("--n-polizas", type=int, default=50000, help="Cantidad de pólizas a generar")
    parser.add_argument("--seed", type=int, default=42, help="Seed reproducible")
    parser.add_argument("--output-dir", type=str, default="output", help="Directorio de salida CSV")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cfg = construir_config(cantidad_polizas=args.n_polizas, seed=args.seed)
    ejecutar_pipeline(cfg, Path(args.output_dir))


if __name__ == "__main__":
    main()
