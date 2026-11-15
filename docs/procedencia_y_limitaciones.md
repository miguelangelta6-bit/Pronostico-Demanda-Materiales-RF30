# Procedencia, integridad y límites de publicación

## Archivos de trabajo consultados

- Notebook original (Google Colab): **Universal Material Analyzer V16.1 RF30 CTOP Forecasting Suite**.
- Documento académico: **Modelo predictivo de demanda de materiales para apoyar la planificación de compras mediante Random Forest**, 2026.
- CSV interno de trabajos y asignaciones: utilizado sólo como referencia de estructura y validación; **no se incluye**.

## Lo que reproduce este repositorio

- Flujo académico explicativo en español, organizado por etapas.
- RF de 30 árboles con profundidad máxima 8, hoja mínima 2 y `max_features="sqrt"`.
- Pronóstico global material-mes, transformaciones temporales y modelos base.
- Backtesting móvil con reentrenamiento cronológico y comparación de 1, 3, 6 y 12 meses.
- Tablas exportables, métricas WAPE/MAE/RMSE/Bias y figuras generadas desde datos.

## Lo que NO reproduce exactamente

- Extracción de IDs y materiales desde notas en texto libre del sistema interno.
- Alias específicos por constructora, modificaciones manualmente confirmadas, reglas por dirección y excepciones comerciales.
- Reglas de combinación dinámica y reconciliación por constructora del motor V16.1 (no equivalentes a la selección sencilla de este repo).
- Igualdad numérica de las tablas, métricas o gráficas finales de la tesis.

**No se debe llamar a este proyecto una reproducción validada de las cifras de la tesis sin integrar previamente un dataset autorizado, el motor interno original y pruebas de equivalencia.**

## Protección de datos

No publiques el CSV original, los outputs privados, direcciones, códigos de orden, precios, proveedores, identificadores de losas reales, modelos entrenados con datos internos ni capturas con información sensible. `.gitignore` ayuda, pero **NO elimina archivos que ya fueron versionados**. Antes del `git add`, inspecciona todo el contenido.

## Trazabilidad de gráficos

Las figuras de `figuras_demo/` y los outputs generados se producen con datos artificiales, incluyen una marca de demostración y no deben incorporarse como evidencia estadística de la investigación real. Los gráficos de la tesis deben generarse a partir de su salida auditada real y conservar su origen declarado.

## Licencia

No se asigna una licencia de software al motor original hasta confirmar derechos de publicación y utilización. Este paquete no debe interpretarse como autorización para difundir reglas comerciales o datos de terceros.
