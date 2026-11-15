"""Interfaz de línea de comandos para reproducir el ejemplo."""
import argparse
from pathlib import Path

from .config import Config
from .ejemplo import generar_csv
from .pipeline import ejecutar


def main():
    parser = argparse.ArgumentParser(description="Pronóstico académico de demanda de slabs, RF30")
    parser.add_argument("--datos", default="data/simulada/eventos_simulados.csv",
                        help="Ruta al CSV estandarizado y anonimizado")
    parser.add_argument("--salida", default="outputs/ejecucion_demo")
    parser.add_argument("--fecha-corte", default="2026-11-01")
    parser.add_argument("--solo-generar", action="store_true")
    parser.add_argument("--sin-graficos", action="store_true")
    args = parser.parse_args()
    ruta = Path(args.datos)
    if args.solo_generar or (not ruta.exists() and str(ruta).endswith("eventos_simulados.csv")):
        generar_csv(ruta)
        print(f"Datos SIMULADOS generados: {ruta}")
        if args.solo_generar:
            return
    ejecutar(ruta, args.salida, Config(fecha_corte=args.fecha_corte), graficar=not args.sin_graficos)


if __name__ == "__main__":
    main()
