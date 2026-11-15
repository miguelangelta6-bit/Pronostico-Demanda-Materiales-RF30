"""Visualizaciones reproducibles en SVG y PNG para revisión académica.

Todas las figuras hechas a partir de datos simulados llevan la marca DEMOSTRACIÓN.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

from .evaluacion import metricas_puntuales


def configurar():
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 10,
        "axes.labelsize": 11, "xtick.labelsize": 9, "ytick.labelsize": 9,
        "axes.spines.top": False, "axes.spines.right": False,
        "figure.facecolor": "white", "savefig.facecolor": "white",
    })


def _guardar(fig, carpeta: Path, nombre: str):
    fig.text(0.99, 0.985, "DATOS SIMULADOS · DEMOSTRACIÓN", ha="right", va="top", fontsize=6.5, color="#777777")
    fig.savefig(carpeta/f"{nombre}.png", dpi=250, bbox_inches="tight")
    fig.savefig(carpeta/f"{nombre}.svg", bbox_inches="tight")
    plt.close(fig)


def _grilla(ax, eje="y"):
    ax.grid(axis=eje, color="#888888", alpha=0.12, linewidth=0.7)
    ax.set_axisbelow(True)


def generar_figuras(panel: pd.DataFrame, pronostico: pd.DataFrame, backtest: pd.DataFrame,
                     adaptativo_prueba: pd.DataFrame, eventos: pd.DataFrame, carpeta: str | Path) -> list[str]:
    configurar()
    salida = Path(carpeta)
    salida.mkdir(parents=True, exist_ok=True)
    nombres = []
    def guardar(fig, n):
        _guardar(fig, salida, n)
        nombres.append(n)

    # 1. Historia mensual del portafolio.
    historico = panel.groupby("mes")["utilizacion"].sum().sort_index()
    fig, ax = plt.subplots(figsize=(9.1, 4.2), constrained_layout=True)
    ax.plot(historico.index, historico.values, "-o", linewidth=1.8, markersize=3.5, color="#2d6b95")
    ax.set_ylabel("Losas físicas utilizadas")
    ax.set_xlabel("Mes")
    _grilla(ax)
    fig.autofmt_xdate(rotation=25)
    guardar(fig, "figura_01_utilizacion_historica")

    # 2. Relación entre periodos consecutivos para series de materiales.
    datos_lags = panel.sort_values(["material", "mes"]).copy()
    datos_lags["lag_1"] = datos_lags.groupby("material")["utilizacion"].shift(1)
    datos_lags = datos_lags.dropna(subset=["lag_1"])
    fig, ax = plt.subplots(figsize=(7.8, 5), constrained_layout=True)
    ax.scatter(datos_lags["lag_1"], datos_lags["utilizacion"], color="#2d6b95", s=17, alpha=0.45,
               linewidth=0.2, edgecolors="none")
    ax.set_xlabel("Losas en el mes anterior")
    ax.set_ylabel("Losas en el mes siguiente")
    _grilla(ax)
    guardar(fig, "figura_02_relacion_meses")

    # 3. Comparativa de WAPE en orígenes reservados para prueba temporal.
    origenes_prueba = adaptativo_prueba["origen"].unique()
    comparables = backtest[(backtest["origen"].isin(origenes_prueba)) &
                           (backtest["metodo"].isin(["Random Forest RF30", "Croston SBA", "Naive"]))]
    comp = pd.concat([comparables, adaptativo_prueba], ignore_index=True)
    tabla = metricas_puntuales(comp)
    metodos = ["Adaptativo (prueba temporal)", "Random Forest RF30", "Croston SBA", "Naive"]
    h_vals = [1, 3, 6, 12]
    fig, ax = plt.subplots(figsize=(9.1, 4.8), constrained_layout=True)
    x = np.arange(4)
    for i, metodo in enumerate(metodos):
        valores = []
        for h in h_vals:
            v = tabla[(tabla.metodo == metodo) & (tabla.horizonte == h)]["wape_mediano"]
            valores.append(float(v.iloc[0]) if len(v) else np.nan)
        ax.bar(x+(i-1.5)*0.2, valores, 0.19, label=metodo, alpha=0.95)
    ax.set_xticks(x, [f"{h} mes" if h==1 else f"{h} meses" for h in h_vals])
    ax.set_ylabel("WAPE mediano (%)")
    ax.set_ylim(0, max(40, float(tabla["wape_mediano"].max()) + 10))
    ax.legend(fontsize=8, ncol=2, frameon=False, loc="upper left")
    _grilla(ax)
    guardar(fig, "figura_03_modelos_wape_puntual")

    # 4. Pronóstico agregado mensual.
    futuro = pronostico.groupby("mes")["pronostico"].sum().sort_index()
    fig, ax = plt.subplots(figsize=(9.1, 4.2), constrained_layout=True)
    ax.plot(futuro.index, futuro.values, "o-", color="#2d6b95", lw=2, markersize=4)
    ax.set_ylabel("Losas previstas por mes")
    ax.set_xlabel("Mes futuro")
    _grilla(ax)
    fig.autofmt_xdate(rotation=25)
    guardar(fig, "figura_04_pronostico_agregado")

    # 5. Promedio mensual pasado 12M frente a promedio pronosticado próximos 3M.
    fin = panel["mes"].max()
    ultimos = panel[panel["mes"] > fin-pd.DateOffset(months=12)].groupby("material")["utilizacion"].mean()
    proximos = pronostico[pronostico["horizonte"] <= 3].groupby("material")["pronostico"].mean()
    mat = proximos.sort_values(ascending=False).head(10).index
    y = np.arange(len(mat))
    fig, ax = plt.subplots(figsize=(9.1, 5.4), constrained_layout=True)
    ax.barh(y-0.18, ultimos.reindex(mat).fillna(0).values, height=0.34, label="Promedio histórico 12M", color="#9ab8cc")
    ax.barh(y+0.18, proximos.reindex(mat).fillna(0).values, height=0.34, label="Pronóstico 3M / mes", color="#2d6b95")
    ax.set_yticks(y, list(mat)); ax.invert_yaxis()
    ax.set_xlabel("Losas físicas por mes")
    ax.legend(frameon=False, fontsize=9)
    _grilla(ax, "x")
    guardar(fig, "figura_05_historico_vs_pronostico")

    # 6. Participación HISTÓRICA por constructora. No es forecast por cuenta.
    ult_eventos = eventos[eventos["mes"] > fin-pd.DateOffset(months=12)]
    participacion = ult_eventos.groupby("constructora")["slab_id"].nunique()
    participacion = (100*participacion/participacion.sum()).sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=(8.4, 4.7), constrained_layout=True)
    barras = ax.bar(participacion.index, participacion.values, color="#2d6b95", width=0.6)
    ax.bar_label(barras, labels=[f"{v:.1f}%" for v in participacion], padding=3, fontsize=10)
    ax.set_ylabel("Participación histórica 12M (%)")
    ax.set_xlabel("Constructora (códigos simulados)")
    ax.set_ylim(0, max(participacion)*1.16)
    _grilla(ax)
    guardar(fig, "figura_06_concentracion_historica")

    # 7. Proxy de nuevos materiales, NO órdenes ni necesidad neta.
    ratios = (eventos[eventos["evento_full_primero"]].groupby("material")["slab_id"].nunique() /
              eventos.groupby("material")["slab_id"].nunique()).fillna(0).clip(0,1)
    valores = []
    for h in [3,6,12]:
        p = pronostico[pronostico["horizonte"] <= h]
        total = sum(p[p["material"] == material].pronostico.sum() * ratios.get(material, 0.0) for material in p.material.unique())
        valores.append(total)
    fig, ax = plt.subplots(figsize=(8.3, 4.6), constrained_layout=True)
    barras = ax.bar(["3 meses", "6 meses", "12 meses"], valores, color="#2d6b95", width=0.6)
    ax.bar_label(barras, labels=[f"{v:,.0f}".replace(",", ".") for v in valores], padding=4, fontsize=10)
    ax.set_ylabel("Slabs nuevos estimados acumulados")
    ax.set_ylim(0, max(valores)*1.16)
    _grilla(ax)
    guardar(fig, "figura_07_proxy_nuevo_material")
    return nombres
