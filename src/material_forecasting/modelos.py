"""Modelos de referencia y Random Forest global para múltiples horizontes.

La arquitectura de variables RF30 se adaptó del notebook de la tesis.
Las decisiones de aceptación del método final se describen en evaluacion.py.
"""
from dataclasses import dataclass
import math

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

from .config import Config

METODOS_BASE = (
    "Naive", "Media móvil 3M", "Media móvil 6M", "Mediana 3M",
    "Ponderado 3M", "SES 0.2", "SES 0.6", "Tendencia amortiguada 6M",
    "Tendencia amortiguada 12M", "Estacional ingenuo", "Croston SBA"
)
METODOS = ("Random Forest RF30",) + METODOS_BASE


def panel_a_series(panel: pd.DataFrame) -> tuple[pd.DatetimeIndex, dict[str, dict[str, np.ndarray]]]:
    meses = pd.DatetimeIndex(sorted(panel["mes"].unique()))
    series = {}
    for material, grupo in panel.groupby("material"):
        grupo = grupo.set_index("mes").reindex(meses, fill_value=0)
        series[material] = {campo: grupo[campo].to_numpy(dtype=float)
                            for campo in ("utilizacion", "full", "remnant", "trabajos")}
    return meses, series


def _ventana(a: np.ndarray, posicion: int, n: int) -> np.ndarray:
    return a[max(0, posicion - n + 1): posicion + 1]


def _lag(a: np.ndarray, posicion: int, rezago: int) -> float:
    i = posicion - rezago + 1
    return float(a[i]) if i >= 0 else 0.0


def _pendiente(a: np.ndarray) -> float:
    return float(np.polyfit(np.arange(len(a)), a, 1)[0]) if len(a) >= 2 else 0.0


def crear_caracteristicas(material: str, datos: dict, origen: int, horizonte: int, mes_objetivo: pd.Timestamp) -> dict:
    """Usa exclusivamente valores visibles al cierre del mes de origen."""
    u, f, r, j = (datos[campo] for campo in ("utilizacion", "full", "remnant", "trabajos"))
    u3, u6, u12 = (_ventana(u, origen, n) for n in (3, 6, 12))
    f3, r3, j3 = (_ventana(a, origen, 3) for a in (f, r, j))
    mes = int(pd.Timestamp(mes_objetivo).month)
    primer_activo = int(np.flatnonzero(u > 0)[0]) if np.any(u > 0) else origen
    asignaciones = float(f3.sum() + r3.sum())
    fila = {
        "material": material,
        "horizonte": horizonte,
        "mes_objetivo": mes,
        "mes_seno": math.sin(2 * math.pi * mes / 12),
        "mes_coseno": math.cos(2 * math.pi * mes / 12),
        "edad_historia": max(0, origen - primer_activo + 1),
        "lag_1": _lag(u, origen, 1),
        "lag_2": _lag(u, origen, 2),
        "lag_3": _lag(u, origen, 3),
        "lag_4": _lag(u, origen, 4),
        "lag_6": _lag(u, origen, 6),
        "lag_9": _lag(u, origen, 9),
        "lag_12": _lag(u, origen, 12),
        "promedio_3": float(u3.mean()),
        "promedio_6": float(u6.mean()),
        "promedio_12": float(u12.mean()),
        "mediana_3": float(np.median(u3)),
        "desviacion_3": float(u3.std()),
        "desviacion_6": float(u6.std()),
        "desviacion_12": float(u12.std()),
        "pendiente_3": _pendiente(u3),
        "pendiente_6": _pendiente(u6),
        "pendiente_12": _pendiente(u12),
        "frecuencia_6": float((u6 > 0).mean()),
        "frecuencia_12": float((u12 > 0).mean()),
        "full_reciente": _lag(f, origen, 1),
        "remnant_reciente": _lag(r, origen, 1),
        "trabajos_recientes": _lag(j, origen, 1),
        "media_full_3": float(f3.mean()),
        "media_remnant_3": float(r3.mean()),
        "media_trabajos_3": float(j3.mean()),
        "ratio_remnant_3": (float(r3.sum()) / asignaciones) if asignaciones else 0.0,
    }
    return fila


def ejemplos_entrenamiento(meses: pd.DatetimeIndex, series: dict, meses_horizonte: int = 12) -> pd.DataFrame:
    filas = []
    for material, datos in series.items():
        uso = datos["utilizacion"]
        for origen in range(12, len(meses) - 1):
            for h in range(1, meses_horizonte + 1):
                destino = origen + h
                if destino >= len(meses):
                    break
                fila = crear_caracteristicas(material, datos, origen, h, meses[destino])
                fila.update({"indice_destino": destino, "indice_origen": origen, "objetivo": float(uso[destino])})
                filas.append(fila)
    return pd.DataFrame(filas)


def preparar_matriz(df: pd.DataFrame, columnas: list[str] | None = None) -> tuple[pd.DataFrame, list[str]]:
    X = df.drop(columns=["objetivo", "indice_destino", "indice_origen"], errors="ignore").copy()
    X = pd.get_dummies(X, columns=["material"], dtype=float)
    X = X.replace([np.inf, -np.inf], 0).fillna(0).astype(float)
    if columnas is not None:
        X = X.reindex(columns=columnas, fill_value=0.0)
    return X, list(X.columns)


@dataclass
class ModeloAjustado:
    modelo: RandomForestRegressor
    columnas: list[str]

    def predecir(self, filas: list[dict]) -> np.ndarray:
        X, _ = preparar_matriz(pd.DataFrame(filas), self.columnas)
        return np.clip(self.modelo.predict(X), 0, None)


def entrenar_rf30(ejemplos: pd.DataFrame, config: Config) -> ModeloAjustado | None:
    if len(ejemplos) < 30 or ejemplos["objetivo"].sum() == 0:
        return None
    X, columnas = preparar_matriz(ejemplos)
    modelo = RandomForestRegressor(
        n_estimators=config.rf_arboles,
        max_depth=config.rf_profundidad,
        min_samples_leaf=config.rf_min_hoja,
        max_features=config.rf_max_features,
        random_state=config.semilla,
        n_jobs=1,
        bootstrap=True,
        criterion="squared_error",
    )
    modelo.fit(X, ejemplos["objetivo"].to_numpy())
    return ModeloAjustado(modelo=modelo, columnas=columnas)


def clasicos(historia: np.ndarray, horizonte: int) -> dict[str, float]:
    """Candidatos no negativos; solo reciben el historial pasado."""
    y = np.asarray(historia, dtype=float)
    if len(y) == 0:
        return {nombre: 0.0 for nombre in METODOS_BASE}
    alpha = 0.2
    no_cero = np.flatnonzero(y > 0)
    if len(no_cero) == 0:
        croston = 0.0
    else:
        tamanos = y[no_cero]
        intervalos = np.diff(np.r_[-1, no_cero]).astype(float)
        z, p = float(tamanos[0]), float(intervalos[0])
        for tam, intervalo in zip(tamanos[1:], intervalos[1:]):
            z += alpha * (tam - z)
            p += alpha * (intervalo - p)
        croston = max(0.0, (1 - alpha / 2) * z / max(p, 1e-8))

    def suavizado(a):
        nivel = float(y[0])
        for val in y[1:]:
            nivel = a * float(val) + (1-a) * nivel
        return max(0.0, nivel)

    def tendencia(window, amortiguacion):
        if len(y) < 3:
            return float(y[-3:].mean())
        ultimos = y[-min(len(y), window):]
        pendiente, intercepto = np.polyfit(np.arange(len(ultimos)), ultimos, 1)
        base = float(intercepto + pendiente * (len(ultimos)-1))
        incremento = pendiente * sum(amortiguacion**k for k in range(1, horizonte+1))
        return max(0.0, base + incremento)

    p3 = y[-3:]
    pesos = np.arange(1, len(p3)+1, dtype=float)
    valores = {
        "Naive": y[-1],
        "Media móvil 3M": p3.mean(),
        "Media móvil 6M": y[-6:].mean(),
        "Mediana 3M": np.median(p3),
        "Ponderado 3M": np.average(p3, weights=pesos),
        "SES 0.2": suavizado(0.2),
        "SES 0.6": suavizado(0.6),
        "Tendencia amortiguada 6M": tendencia(6, 0.80),
        "Tendencia amortiguada 12M": tendencia(12, 0.85),
        "Estacional ingenuo": y[-12 + (horizonte - 1) % 12] if len(y) >= 12 else y[-1],
        "Croston SBA": croston,
    }
    return {k: max(0.0, float(v)) for k, v in valores.items()}
