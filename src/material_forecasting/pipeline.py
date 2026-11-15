"""Orquestación completa del ejemplo académico, con salida reproducible."""
from pathlib import Path

import pandas as pd

from .config import Config
from .datos import leer_eventos, preparar_eventos, panel_mensual
from .modelos import panel_a_series
from .evaluacion import (backtesting, evaluar_adaptativo, metricas_puntuales,
                         metricas_acumuladas, pronostico_final, seleccionar_metodos)
from .graficos import generar_figuras


def ejecutar(ruta_csv: str | Path, carpeta_salida: str | Path, config: Config = Config(), graficar: bool = True) -> dict:
    """Ejecuta la demostración. No modifica el CSV de entrada."""
    carpeta = Path(carpeta_salida)
    carpeta.mkdir(parents=True, exist_ok=True)
    entrada = leer_eventos(ruta_csv)
    eventos, revision = preparar_eventos(entrada, config.fecha_corte)
    inicio = max(pd.Timestamp(config.fecha_inicio), eventos["mes"].min())
    eventos = eventos[eventos["mes"] >= inicio].copy()
    panel = panel_mensual(eventos, config.top_n, inicio=inicio,
                          fin=(pd.Timestamp(config.fecha_corte).to_period("M")-1).to_timestamp())
    meses, series = panel_a_series(panel)
    evaluaciones = backtesting(meses, series, config)
    adaptativo_test, seleccion_calibracion = evaluar_adaptativo(evaluaciones, config)
    prueba_origenes = adaptativo_test["origen"].unique()
    prueba_metodos = evaluaciones[evaluaciones["origen"].isin(prueba_origenes)]
    comparacion = metricas_puntuales(pd.concat([prueba_metodos, adaptativo_test], ignore_index=True), config.horizontes)
    acumulados = metricas_acumuladas(pd.concat([prueba_metodos, adaptativo_test], ignore_index=True), config.horizontes)
    metricas_acum = []
    for (metodo, h), grupo in acumulados.groupby(["metodo", "horizonte"]):
        metricas_materiales = []
        from .evaluacion import wape, mae, rmse, bias_pct
        for material, serie in grupo.groupby("material"):
            metricas_materiales.append((wape(serie.real, serie.pronostico), mae(serie.real, serie.pronostico),
                                        rmse(serie.real, serie.pronostico), bias_pct(serie.real, serie.pronostico)))
        tabla = pd.DataFrame(metricas_materiales, columns=["wape", "mae", "rmse", "bias"])
        metricas_acum.append({"metodo": metodo, "horizonte": h, "materiales": tabla.wape.notna().sum(),
                              "wape_mediano": tabla.wape.median(), "mae_medio": tabla.mae.mean(),
                              "rmse_medio": tabla.rmse.mean(), "bias_medio": tabla.bias.mean()})
    metricas_acum = pd.DataFrame(metricas_acum)
    futuro = pronostico_final(meses, series, evaluaciones, config)
    seleccion_final = pd.DataFrame([{"material": m, "horizonte": h, "metodo": metodo}
                                    for (m,h), metodo in seleccionar_metodos(evaluaciones).items()])
    archivos = {
        "revision": revision, "panel_mensual": panel, "backtesting": evaluaciones,
        "wape_puntual_prueba": comparacion, "wape_acumulado_prueba": metricas_acum,
        "seleccion_calibracion": seleccion_calibracion, "seleccion_final": seleccion_final,
        "pronosticos": futuro,
    }
    for nombre, tabla in archivos.items():
        tabla.to_csv(carpeta/f"{nombre}.csv", index=False, encoding="utf-8-sig")
    nombres_figuras = []
    if graficar:
        nombres_figuras = generar_figuras(panel, futuro, evaluaciones, adaptativo_test, eventos, carpeta/"figuras")
    print(f"Registros recibidos: {len(entrada):,}. Históricos aptos: {len(eventos):,}. En revisión: {len(revision):,}.")
    print(f"Materiales: {len(series)}. Meses históricos: {len(meses)}. Orígenes backtest: {evaluaciones.origen.nunique()}.")
    print(f"Archivos CSV: {len(archivos)}. Figuras: {len(nombres_figuras)}. Directorio: {carpeta.resolve()}")
    return {**archivos, "figuras": nombres_figuras}
