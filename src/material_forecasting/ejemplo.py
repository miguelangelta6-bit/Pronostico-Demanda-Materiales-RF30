"""Generador determinista de datos artificiales, sin información empresarial."""
from pathlib import Path

import numpy as np
import pandas as pd


def generar_csv(ruta: str | Path, semilla: int = 42, materiales: int = 12) -> pd.DataFrame:
    """Crea una estructura de eventos compatible con el flujo académico.

    LOS DATOS NO SON REALES. Volúmenes, patrones y constructores son simulados.
    """
    rng = np.random.default_rng(semilla)
    meses = pd.date_range("2022-01-01", "2026-10-01", freq="MS")
    filas = []
    slab_ordinal = 100000
    job_ordinal = 50000
    for mi in range(materiales):
        historial_losas = []  # permite simular reutilización de remnants en meses siguientes
        material = f"MATERIAL_{mi+1:02d}"
        nivel = 7 + (mi % 6)*4
        for t, mes in enumerate(meses):
            estacional = 1 + 0.15*np.sin(2*np.pi*(mes.month-1)/12 + mi/3)
            tendencia = 1 + 0.003*t
            intermitente = (mi % 5 == 0 and rng.random() < 0.24)
            cantidad = 0 if intermitente else int(rng.poisson(nivel*estacional*tendencia))
            for _ in range(cantidad):
                reutilizar = len(historial_losas) > 5 and rng.random() < 0.09
                if reutilizar:
                    slab = str(rng.choice(historial_losas[-150:]))
                    tipo = "REMNANT"
                else:
                    slab_ordinal += 1
                    slab = f"S{slab_ordinal}"
                    historial_losas.append(slab)
                    tipo = "FULL"
                job_ordinal += 1
                trabajo = f"T{job_ordinal}"
                fecha = (mes + pd.Timedelta(days=int(rng.integers(0, 27)))).date().isoformat()
                constructora = rng.choice(["C01", "C02", "C03"], p=[0.58, 0.30, 0.12])
                filas.append({"fecha_instalacion": fecha, "material": material,
                              "constructora": constructora, "slab_id": slab,
                              "tipo_evento": tipo, "trabajo_id": trabajo})
                if tipo == "FULL" and rng.random() < 0.12:
                    job_ordinal += 1
                    filas.append({"fecha_instalacion": fecha, "material": material,
                                  "constructora": constructora, "slab_id": slab,
                                  "tipo_evento": "REMNANT", "trabajo_id": f"T{job_ordinal}"})
    df = pd.DataFrame(filas)
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(ruta, index=False)
    return df
