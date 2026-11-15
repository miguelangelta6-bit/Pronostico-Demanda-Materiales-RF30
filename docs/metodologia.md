# Metodología de la versión académica

## 1. Problema y alcance

El estudio estima la **utilización mensual de losas físicas** para apoyar la planificación de compras de materiales de superficies. No automatiza órdenes de compra y no incorpora precios, inventario disponible ni órdenes abiertas. El propósito es anticipar tendencias de consumo con incertidumbre explícita.

## 2. Procedencia y preparación

El notebook original de la tesis procesa notas operativas de asignación, cantidades y materiales. La versión pública comienza **después de la normalización y revisión humana del origen**, con eventos estructurados y anónimos. Se identifican losas físicas mediante un `slab_id` base, se evita el doble conteo de remanentes por material-mes, se excluye el mes incompleto y se construye un panel mensual con ceros observados.

Se seleccionan las `TOP_N` referencias con mayor utilización física en los últimos doce meses completos. La selección se documenta como paso del estudio; para evitar sesgos de evaluación, las pruebas de investigación más rigurosas deberían volver a seleccionar el Top 30 dentro de cada origen, si se compara el universo de materiales a través del tiempo.

## 3. Ingeniería de características

Se generan variables históricas del material: rezagos de 1, 2, 3, 4, 6, 9 y 12 meses; medias 3/6/12; mediana 3; desviaciones 3/6/12; tendencias lineales 3/6/12; tasas de consumo no nulo; composición FULL y remnant; número de trabajos; codificación del mes y del identificador de material. Todas las ventanas terminan en el mes de origen, por lo que no usan el resultado futuro.

## 4. Modelos candidatos

La configuración es consistente con el modelo inicial descrito en la tesis:

- `RandomForestRegressor(n_estimators=30, max_depth=8, min_samples_leaf=2, max_features="sqrt", bootstrap=True, random_state=42)`.
- Baselines: último valor observado, medias móviles, mediana, promedio ponderado, suavizamiento exponencial (SES), estacional ingenuo y Croston SBA.

El RF30 combina ejemplos de varios materiales (modelo global). El horizonte de 1 a 12 meses se incluye como característica de entrada. El objetivo predice las losas de **un mes específico** a distancia `h`.

## 5. Backtesting cronológico

Se seleccionan orígenes mensuales en la zona histórica con futuro completamente observado hasta `h=12`. En cada origen, Random Forest se **reentrena usando exclusivamente filas cuyo mes objetivo ya ocurrió**. Los métodos clásicos reciben sólo la historia hasta ese origen. Así se prohíbe la fuga temporal por objetivos futuros.

Para analizar el enfoque adaptativo, los orígenes disponibles se dividen **cronológicamente** en un grupo inicial de calibración y uno posterior de prueba. Se selecciona el método de menor WAPE por material y horizonte con los orígenes iniciales, y se evalúa la misma selección en el grupo posterior. La comparación puntual de los candidatos también se presenta sobre esos orígenes de prueba.

Para la proyección final, los métodos se seleccionan utilizando toda la evidencia retrospectiva disponible. La selección final sirve para despliegue, pero su error retrospectivo no es una validación independiente.

## 6. Métricas y horizontes

Si `y` es observado y `ŷ` es previsto:

- **MAE** = promedio de `|ŷ-y|`, expresado en losas.
- **RMSE** = raíz del promedio de `(ŷ-y)^2`, expresada en losas.
- **WAPE** = `100 * sum(|ŷ-y|) / sum(|y|)`, expresado en %, indefinido si el denominador es 0.
- **Bias** = `100 * sum(ŷ-y) / sum(|y|)`, positivo en sobrepronóstico y negativo en subpronóstico.

Se reportan por separado:

1. **Horizonte puntual**: predicción del mes a distancia h (h = 1, 3, 6, 12).
2. **Horizonte acumulado**: suma de las predicciones de los próximos h meses comparada con la suma observada en esos h meses.

Se presenta la **mediana entre materiales** de sus WAPE, no el WAPE combinado de todo el portafolio. Un WAPE de 30% no equivale a una exactitud del 70%.

## 7. Resultado operativo

El pronóstico orienta decisiones de negociación y reposición, pero la compra real requiere inventario disponible, compromisos, órdenes abiertas, tiempos de entrega, costo y un nivel de seguridad. El cálculo ilustrativo `pronóstico × proporción histórica FULL` no reemplaza esa conciliación. En la Figura 6 pública se usa la **participación histórica por constructora**, no un pronóstico específico por cuenta: este último requiere una extensión metodológica distinta.

## 8. Limitaciones de esta adaptación

La versión pública **no es una reproducción numérica exacta** del sistema privado V16.1: faltan sus reglas internas de transformación del CSV original, el motor específico de selección híbrida por perfil y la conciliación detallada de cuentas. Los datos de demostración se simulan y sus métricas nunca deben comunicarse como resultados de la empresa. La tesis mantiene los resultados obtenidos con la ejecución privada de noviembre de 2026; no se deben cambiar sus cifras con una simulación.
