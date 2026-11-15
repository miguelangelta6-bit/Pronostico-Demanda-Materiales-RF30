"""Ejecuta el flujo completo. Ejecutar desde la raíz del repositorio."""
from material_forecasting.config import Config
from material_forecasting.pipeline import ejecutar

if __name__ == "__main__":
    ejecutar("data/simulada/eventos_simulados.csv", "outputs/ejecucion_demo", Config())
