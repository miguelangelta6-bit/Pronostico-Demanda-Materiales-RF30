# Diccionario de datos de entrada

Esta versión académica recibe **eventos operativos ya estructurados**. El CSV de entrada debe estar anonimizado y usar **una fila por evento de asignación**. No se deben publicar datos de clientes, direcciones, identificadores comerciales o notas internas.

| Variable | Tipo | Definición | Ejemplo artificial |
|---|---|---|---|
| `fecha_instalacion` | fecha ISO | Fecha del evento; sólo se usan meses históricos completos | `2024-04-18` |
| `material` | texto | Material canónico; mantener grosor/acabado cuando sean relevantes | `MATERIAL_01` |
| `constructora` | texto | Código anónimo de constructora | `C01` |
| `slab_id` | texto | Identificador de losa física **base**, sin sufijos de remanente | `S100350` |
| `tipo_evento` | categoría | `FULL` o `REMNANT` | `FULL` |
| `trabajo_id` | texto | Código anónimo del trabajo | `T50350` |

**Unidad de análisis:** por material y mes se cuenta una sola vez cada `slab_id`. Los eventos de remanentes asociados a una misma losa mantienen el `slab_id` base. Si el archivo original tiene `12345`, `12345-1` y `12345-1-1`, el proceso de extracción previo debe asociarlos correctamente al mismo ID base **sin colapsar identificadores ambiguos**.

**Tratamiento de fechas:** el mes en curso al corte se considera parcial y se excluye del entrenamiento. Registros de fecha inválida o del futuro se envían a la tabla `revision.csv`.

**Separaciones metodológicas:**

- **Utilización física**: losas distintas observadas por material-mes.
- **Solicitud**: cantidad de material solicitada, que requiere otro conjunto de variables y no se infiere de los ID.
- **Proxy de material nuevo**: evento FULL contado en su primera aparición; **no es una compra neta**.

**Reglas internas no incluidas:** interpretación de notas libres, validación de cantidades ambiguas, alias por cuenta, reconciliación de ids, excepciones por trabajo y conciliación de órdenes. Se mantuvieron fuera del repositorio por su naturaleza operativa y confidencial. Una exportación académica estructurada debe obtenerse con autorización y auditarse antes de usarse aquí.

**Regla de datos ausentes:** el pipeline completa meses sin eventos con cero para las series seleccionadas. Esto es válido únicamente si el periodo está cubierto por el sistema de origen; una interrupción de captura NO debe interpretarse como consumo cero.
