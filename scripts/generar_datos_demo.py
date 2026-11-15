"""Genera CSV simulado. Ejecutar desde la raíz del repositorio."""
from material_forecasting.ejemplo import generar_csv

if __name__ == "__main__":
    data = generar_csv("data/simulada/eventos_simulados.csv")
    print(f"Generados {len(data)} eventos ficticios")
