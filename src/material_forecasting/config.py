"""Parámetros explícitos y auditables del proyecto académico.

La configuración del RF30 reproduce los hiperparámetros descritos en la tesis.
Este repositorio público usa un esquema de datos previamente estructurado;
no incluye las reglas privadas de extracción de notas operativas.
"""
from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class Config:
    fecha_corte: str = "2026-11-01"
    fecha_inicio: str = "2022-01-01"
    top_n: int = 30
    horizontes: Tuple[int, ...] = (1, 3, 6, 12)
    meses_pronostico: int = 12
    rf_arboles: int = 30
    rf_profundidad: int = 8
    rf_min_hoja: int = 2
    rf_max_features: str = "sqrt"
    semilla: int = 42
    min_historia_meses: int = 18
    origenes_backtest: int = 8
    ratio_calibracion: float = 0.65
