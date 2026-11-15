"""Validación del esquema, normalización básica y deduplicación física.

NO se infieren nombres de materiales ni cantidades ambiguas desde texto libre.
La extracción y validación especializada se realiza antes de esta etapa.
"""
import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

COLUMNAS = ["fecha_instalacion", "material", "constructora", "slab_id", "tipo_evento", "trabajo_id"]
COLUMNAS_OPCIONALES = ["solicitado"]


def _texto(valor: object) -> str:
    if pd.isna(valor):
        return ""
    texto = unicodedata.normalize("NFKC", str(valor)).strip()
    return re.sub(r"\s+", " ", texto).upper()


def leer_eventos(ruta: str | Path) -> pd.DataFrame:
    """Lee un CSV normalizado. Rechaza datos sin campos esenciales."""
    ruta = Path(ruta)
    if ruta.suffix.lower() != ".csv":
        raise ValueError("El repositorio académico trabaja con CSV estructurado y anonimizado.")
    datos = pd.read_csv(ruta, dtype={"slab_id": "string", "trabajo_id": "string"})
    faltantes = sorted(set(COLUMNAS) - set(datos.columns))
    if faltantes:
        raise ValueError(f"Faltan columnas: {faltantes}. Revisa docs/diccionario_datos.md")
    return datos


def preparar_eventos(datos: pd.DataFrame, fecha_corte: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Devuelve eventos históricos válidos y una tabla de incidencias.

    * Excluye del entrenamiento registros en el mes parcial/futuro del corte.
    * Un mismo slab físico puede tener varios registros por remanentes.
    * Conserva todos los eventos originales para auditoría (sin alterar entrada).
    """
    if any(c not in datos.columns for c in COLUMNAS):
        raise ValueError("El DataFrame no contiene las columnas esperadas.")
    df = datos.copy()
    df["fila_origen"] = np.arange(1, len(df) + 1)
    df["fecha"] = pd.to_datetime(df["fecha_instalacion"], errors="coerce")
    for col in ["material", "constructora", "slab_id", "trabajo_id", "tipo_evento"]:
        df[col] = df[col].map(_texto)
    df["tipo_evento"] = df["tipo_evento"].replace({"REMANENTE": "REMNANT", "NUEVA": "FULL"})
    corte = pd.Timestamp(fecha_corte)
    inicio_mes_corte = corte.to_period("M").to_timestamp()
    # Una fecha de corte en cualquier día excluye siempre su mes incompleto.
    df["mes"] = df["fecha"].dt.to_period("M").dt.to_timestamp()
    razones = pd.Series("", index=df.index, dtype="string")
    razones[df["fecha"].isna()] = "FECHA_INVALIDA"
    razones[(razones == "") & (df["mes"] >= inicio_mes_corte)] = "PERIODO_NO_HISTORICO"
    razones[(razones == "") & df[["material", "constructora", "slab_id", "trabajo_id"]].eq("").any(axis=1)] = "CAMPO_OBLIGATORIO_VACIO"
    razones[(razones == "") & ~df["tipo_evento"].isin(["FULL", "REMNANT"])] = "TIPO_EVENTO_INVALIDO"
    df["motivo_revision"] = razones
    revision = df.loc[df["motivo_revision"] != ""].copy()
    historico = df.loc[df["motivo_revision"] == ""].copy()
    # La información de una misma losa física se consolida por material-mes-ID.
    # Almacenar dos trabajos que comparten remanente no duplica la utilización.
    historico = historico.sort_values(["fecha", "fila_origen"])
    historico["clave_fisica"] = historico["material"] + "::" + historico["slab_id"]
    historico["evento_full_primero"] = (
        historico["tipo_evento"].eq("FULL")
        & ~historico.loc[historico["tipo_evento"].eq("FULL"), "clave_fisica"].duplicated().reindex(historico.index, fill_value=False)
    )
    return historico.reset_index(drop=True), revision.reset_index(drop=True)


def panel_mensual(eventos: pd.DataFrame, top_n: int = 30, inicio: str | None = None, fin: str | None = None) -> pd.DataFrame:
    """Construye panel material-mes con ceros observables y señales operativas.

    Las unidades son slabs físicos distintos por MATERIAL y MES; el proxy de nuevo
    material es el número de FULL únicos en todo el historial.
    """
    if eventos.empty:
        raise ValueError("No hay observaciones históricas válidas.")
    conteo = (eventos.groupby(["material", "mes"])["slab_id"].nunique()
              .rename("utilizacion").reset_index())
    ultimo_mes = pd.Timestamp(fin) if fin is not None else pd.Timestamp(eventos["mes"].max())
    primer_mes = pd.Timestamp(inicio) if inicio is not None else pd.Timestamp(eventos["mes"].min())
    ventana = conteo[(conteo["mes"] > ultimo_mes - pd.DateOffset(months=12)) & (conteo["mes"] <= ultimo_mes)]
    top = (ventana.groupby("material")["utilizacion"].sum().sort_values(ascending=False)
           .head(top_n).index.tolist())
    if not top:
        raise ValueError("No hay materiales para modelar.")
    meses = pd.date_range(primer_mes, ultimo_mes, freq="MS")
    indice = pd.MultiIndex.from_product([top, meses], names=["material", "mes"])
    panel = conteo.set_index(["material", "mes"]).reindex(indice, fill_value=0).reset_index()
    full = (eventos[eventos["evento_full_primero"]].groupby(["material", "mes"])["slab_id"]
            .nunique().rename("full").reset_index())
    remnant = (eventos[eventos["tipo_evento"] == "REMNANT"].groupby(["material", "mes"])["slab_id"]
               .nunique().rename("remnant").reset_index())
    jobs = (eventos.groupby(["material", "mes"])["trabajo_id"]
            .nunique().rename("trabajos").reset_index())
    for tabla in [full, remnant, jobs]:
        panel = panel.merge(tabla, on=["material", "mes"], how="left")
    for col in ["utilizacion", "full", "remnant", "trabajos"]:
        panel[col] = panel[col].fillna(0).astype(int)
    return panel.sort_values(["material", "mes"]).reset_index(drop=True)


def ratio_material_nuevo(eventos: pd.DataFrame, materiales: list[str]) -> dict[str, float]:
    """Proxy descriptivo FULL / uso físico, limitado al rango [0,1].

    No equivale a necesidad neta de compra ni considera inventario u órdenes.
    """
    p = panel_mensual(eventos, top_n=len(materiales))
    grupos = p.groupby("material")[["utilizacion", "full"]].sum()
    ratios = {}
    for material in materiales:
        if material not in grupos.index:
            ratios[material] = 0.0
        else:
            r = grupos.loc[material]
            ratios[material] = float(np.clip(r["full"] / r["utilizacion"], 0, 1)) if r["utilizacion"] else 0.0
    return ratios
