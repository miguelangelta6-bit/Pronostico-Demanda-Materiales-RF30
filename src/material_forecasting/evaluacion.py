"""Evaluación cronológica con origen móvil y selección de métodos.

No se equipara WAPE con exactitud porcentual. El WAPE es indefinido
cuando el valor observado total es cero.
"""
import numpy as np
import pandas as pd

from .config import Config
from .modelos import METODOS, METODOS_BASE, crear_caracteristicas, ejemplos_entrenamiento, entrenar_rf30, clasicos


def wape(real, previsto) -> float:
    r = np.asarray(real, dtype=float)
    p = np.asarray(previsto, dtype=float)
    den = float(np.sum(np.abs(r)))
    return 100 * float(np.sum(np.abs(p-r))) / den if den > 0 else float("nan")


def mae(real, previsto) -> float:
    return float(np.mean(np.abs(np.asarray(real) - np.asarray(previsto))))


def rmse(real, previsto) -> float:
    return float(np.sqrt(np.mean((np.asarray(real) - np.asarray(previsto))**2)))


def bias_pct(real, previsto) -> float:
    r = np.asarray(real, dtype=float)
    den = float(np.sum(np.abs(r)))
    return 100 * float(np.sum(np.asarray(previsto) - r)) / den if den > 0 else float("nan")


def _origenes(n_meses: int, config: Config) -> list[int]:
    # Sólo se comparan orígenes que tienen todos los horizontes observados.
    inicio = max(12, config.min_historia_meses - 1)
    ultimo = n_meses - 1 - config.meses_pronostico
    if ultimo < inicio:
        raise ValueError(
            f"Historia insuficiente: se necesitan al menos {inicio + config.meses_pronostico + 1} meses "
            "para evaluar los 12 horizontes bajo un mismo conjunto de orígenes."
        )
    posiciones = np.linspace(inicio, ultimo, num=min(config.origenes_backtest, ultimo-inicio+1))
    return sorted(set(int(round(v)) for v in posiciones))


def backtesting(meses: pd.DatetimeIndex, series: dict, config: Config) -> pd.DataFrame:
    """Reentrena RF en cada origen usando sólo objetivos que ya ocurrieron."""
    origenes = _origenes(len(meses), config)
    ejemplos = ejemplos_entrenamiento(meses, series, config.meses_pronostico)
    resultados = []
    for indice_origen in origenes:
        entrenamiento = ejemplos.loc[ejemplos["indice_destino"] <= indice_origen]
        rf = entrenar_rf30(entrenamiento, config)
        filas_rf, metadatos = [], []
        for material, datos in series.items():
            for h in range(1, config.meses_pronostico+1):
                indice_objetivo = indice_origen + h
                fila = crear_caracteristicas(material, datos, indice_origen, h, meses[indice_objetivo])
                filas_rf.append(fila)
                metadatos.append((material, h, indice_objetivo))
        pred_rf = rf.predecir(filas_rf) if rf else np.full(len(filas_rf), np.nan)
        for i, (material, h, destino) in enumerate(metadatos):
            actual = float(series[material]["utilizacion"][destino])
            valores = clasicos(series[material]["utilizacion"][:indice_origen+1], h)
            if rf is not None:
                valores["Random Forest RF30"] = float(pred_rf[i])
            for metodo, estimacion in valores.items():
                resultados.append({
                    "material": material, "origen": meses[indice_origen],
                    "mes_objetivo": meses[destino], "horizonte": h,
                    "metodo": metodo, "real": actual, "pronostico": max(0.0, estimacion),
                })
    return pd.DataFrame(resultados).sort_values(["origen", "material", "horizonte", "metodo"]).reset_index(drop=True)


def metricas_puntuales(backtest: pd.DataFrame, horizontes=(1,3,6,12)) -> pd.DataFrame:
    """WAPE mediano entre materiales, NO WAPE de todos los registros agregados."""
    reportes = []
    for (metodo, h), grupo in backtest[backtest["horizonte"].isin(horizontes)].groupby(["metodo", "horizonte"]):
        stats = []
        for material, m in grupo.groupby("material"):
            stats.append({"material": material, "wape": wape(m.real, m.pronostico),
                          "mae": mae(m.real, m.pronostico), "rmse": rmse(m.real, m.pronostico),
                          "bias": bias_pct(m.real, m.pronostico)})
        t = pd.DataFrame(stats)
        reportes.append({"metodo": metodo, "horizonte": int(h),
                         "materiales": int(t["wape"].notna().sum()),
                         "wape_mediano": float(t["wape"].median()),
                         "mae_medio": float(t["mae"].mean()),
                         "rmse_medio": float(t["rmse"].mean()),
                         "bias_medio": float(t["bias"].mean())})
    return pd.DataFrame(reportes).sort_values(["horizonte", "wape_mediano"])


def seleccionar_metodos(backtest: pd.DataFrame) -> dict[tuple[str, int], str]:
    """Selección retrospectiva por material y horizonte, minimizando WAPE.

    Atención: selección y evaluación con los mismos orígenes produce optimismo.
    Para medir generalización de la solución adaptativa se utiliza evaluar_adaptativo().
    """
    ganadores = {}
    for (material, h), grupo in backtest.groupby(["material", "horizonte"]):
        valores = [(wape(g.real, g.pronostico), metodo) for metodo, g in grupo.groupby("metodo")]
        valores = [(e, metodo) for e, metodo in valores if np.isfinite(e)]
        if valores:
            ganadores[(material, int(h))] = min(valores, key=lambda item: (item[0], item[1]))[1]
        else:
            ganadores[(material, int(h))] = "Naive"
    return ganadores


def evaluar_adaptativo(backtest: pd.DataFrame, config: Config) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Selecciona métodos con orígenes tempranos y evalúa en orígenes posteriores.

    Se preserva el orden cronológico. El conjunto externo no determina
    cuál método habría sido elegido en el periodo de calibración.
    """
    origenes = sorted(backtest["origen"].unique())
    if len(origenes) < 3:
        raise ValueError("Se requieren al menos tres orígenes para calibración/prueba.")
    corte = min(len(origenes)-1, max(2, int(len(origenes)*config.ratio_calibracion)))
    calibracion = backtest[backtest["origen"].isin(origenes[:corte])]
    prueba = backtest[backtest["origen"].isin(origenes[corte:])]
    ganadores = seleccionar_metodos(calibracion)
    seleccion = pd.DataFrame([{"material": material, "horizonte": h, "metodo": metodo}
                               for (material, h), metodo in ganadores.items()])
    prueba = prueba.merge(seleccion, on=["material", "horizonte", "metodo"], how="inner")
    prueba = prueba.assign(metodo="Adaptativo (prueba temporal)")
    return prueba, seleccion


def metricas_acumuladas(backtest: pd.DataFrame, horizontes=(1,3,6,12)) -> pd.DataFrame:
    """Evalúa suma de los próximos h meses en cada origen material (no mes h)."""
    acumulados = []
    for (material, origen, metodo), grupo in backtest.groupby(["material", "origen", "metodo"]):
        orden = grupo.sort_values("horizonte").set_index("horizonte")
        for h in horizontes:
            if not set(range(1, h+1)).issubset(orden.index):
                continue
            meses = orden.loc[list(range(1, h+1))]
            acumulados.append({"material": material, "origen": origen, "metodo": metodo,
                               "horizonte": h, "real": float(meses.real.sum()),
                               "pronostico": float(meses.pronostico.sum())})
    return pd.DataFrame(acumulados)


def pronostico_final(meses: pd.DatetimeIndex, series: dict, backtest: pd.DataFrame, config: Config) -> pd.DataFrame:
    """Pronóstico de despliegue; método elegido usando todos los orígenes históricos.

    No se garantiza que el RF sea la solución seleccionada para todos los materiales.
    """
    ejemplos = ejemplos_entrenamiento(meses, series, config.meses_pronostico)
    rf = entrenar_rf30(ejemplos, config)
    ganadores = seleccionar_metodos(backtest)
    filas_rf, meta = [], []
    origen = len(meses)-1
    for material, datos in series.items():
        for h in range(1, config.meses_pronostico+1):
            mes = meses[-1] + pd.DateOffset(months=h)
            filas_rf.append(crear_caracteristicas(material, datos, origen, h, mes))
            meta.append((material, h, mes))
    pred_rf = rf.predecir(filas_rf) if rf is not None else np.full(len(filas_rf), np.nan)
    filas = []
    for i, (material, h, mes) in enumerate(meta):
        opciones = clasicos(series[material]["utilizacion"], h)
        if rf is not None:
            opciones["Random Forest RF30"] = float(pred_rf[i])
        metodo = ganadores.get((material, h), "Naive")
        if metodo not in opciones:
            metodo = "Naive"
        filas.append({"material": material, "mes": mes, "horizonte": h,
                      "metodo_seleccionado": metodo, "pronostico": opciones[metodo],
                      "rf30": opciones.get("Random Forest RF30", np.nan),
                      "naive": opciones["Naive"]})
    return pd.DataFrame(filas)
