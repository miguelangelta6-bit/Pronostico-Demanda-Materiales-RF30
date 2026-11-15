import numpy as np
import pandas as pd
from material_forecasting.config import Config
from material_forecasting.modelos import clasicos, crear_caracteristicas, entrenar_rf30
from material_forecasting.datos import preparar_eventos, panel_mensual
from material_forecasting.ejemplo import generar_csv
from material_forecasting.modelos import panel_a_series, ejemplos_entrenamiento


def test_caracteristicas_no_miran_mes_futuro():
    valores = {c:np.arange(32, dtype=float) for c in ("utilizacion", "full", "remnant", "trabajos")}
    meses = pd.date_range("2023-01-01", periods=32, freq="MS")
    antes = crear_caracteristicas("M1", valores, 18, 3, meses[21])
    valores["utilizacion"][21:] = 9999
    despues = crear_caracteristicas("M1", valores, 18, 3, meses[21])
    assert antes == despues


def test_clasicos_sin_negativos():
    p = clasicos(np.array([0, 10, 0, 1, 0, 0, 3, 2]), 3)
    assert all(v >= 0 for v in p.values())
    assert "Croston SBA" in p


def test_rf30_configuracion(tmp_path):
    csv = tmp_path/"demo.csv"
    generar_csv(csv, semilla=7, materiales=3)
    eventos, _ = preparar_eventos(pd.read_csv(csv), "2026-11-01")
    panel = panel_mensual(eventos, top_n=3)
    meses, series = panel_a_series(panel)
    ejemplos = ejemplos_entrenamiento(meses, series, 12)
    modelo = entrenar_rf30(ejemplos, Config())
    assert modelo is not None
    assert modelo.modelo.n_estimators == 30
    assert modelo.modelo.max_depth == 8
    assert modelo.modelo.min_samples_leaf == 2
