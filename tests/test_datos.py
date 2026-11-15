import pandas as pd
import numpy as np

from material_forecasting.datos import preparar_eventos, panel_mensual
from material_forecasting.evaluacion import wape, bias_pct, metricas_acumuladas


def _filas():
    return pd.DataFrame([
        {"fecha_instalacion":"2026-09-02","material":"A","constructora":"C01","slab_id":"S1","tipo_evento":"FULL","trabajo_id":"J1"},
        {"fecha_instalacion":"2026-09-02","material":"A","constructora":"C01","slab_id":"S1","tipo_evento":"REMNANT","trabajo_id":"J2"},
        {"fecha_instalacion":"2026-09-05","material":"A","constructora":"C01","slab_id":"S2","tipo_evento":"FULL","trabajo_id":"J3"},
        {"fecha_instalacion":"2026-11-11","material":"A","constructora":"C01","slab_id":"S3","tipo_evento":"FULL","trabajo_id":"J4"},
    ])


def test_fechas_y_deduplicacion():
    historico, revision = preparar_eventos(_filas(), "2026-11-01")
    assert len(historico) == 3
    assert len(revision) == 1
    assert revision.iloc[0]["motivo_revision"] == "PERIODO_NO_HISTORICO"
    panel = panel_mensual(historico, top_n=1, inicio="2026-08-01", fin="2026-10-01")
    assert list(panel["utilizacion"]) == [0, 2, 0]
    assert list(panel["full"]) == [0, 2, 0]


def test_wape_no_equivale_precision():
    assert abs(wape([10, 20], [15, 20]) - 100*5/30) < 1e-8
    assert np.isnan(wape([0, 0], [1, 2]))
    assert bias_pct([10, 20], [15, 20]) > 0


def test_acumulado_no_es_mes_puntual():
    bt = pd.DataFrame({"material": ["A"]*3, "origen": [pd.Timestamp("2026-01-01")]*3,
                      "metodo": ["Naive"]*3, "horizonte": [1,2,3],
                      "real": [10,20,30], "pronostico": [10,10,10]})
    df = metricas_acumuladas(bt, (1,3))
    assert df.loc[df.horizonte == 3, "real"].iloc[0] == 60
    assert df.loc[df.horizonte == 3, "pronostico"].iloc[0] == 30
