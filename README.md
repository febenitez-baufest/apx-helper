# apx-helper

Rellena automáticamente las plantillas **APX Global Sheet** de BBVA (transacciones y librerías) a partir de un contrato JSON, respetando el formato, los estilos y los desplegables originales del Excel.

El flujo completo es:

```
Proyecto APX  →  agente IA  →  contrato JSON  →  apx-helper  →  hoja APX (.xlsx)
                (prompt)                          (esta app)      + reporte de pendientes
```

El agente analiza el código fuente del DU y produce el JSON. Esta app lo transforma en el Excel, marcando en ámbar todo lo que el agente no pudo determinar para que el desarrollador lo complete a mano.

---

## Puesta en marcha

Requiere Python 3.10+.

```powershell
cd app
pip install -r requirements.txt
python -m apx_helper serve
```

Abrí <http://127.0.0.1:8000/>.

---

## Uso desde la interfaz web (recomendado)

1. **Elegí el tipo de contrato**: Transacción o Librería.
2. **Importá el `.json`** que generó el agente (drag & drop o selector).
3. **Revisá el resultado**: la app muestra las hojas generadas, un contador de pendientes y una tabla filtrable con hoja, celda, campo y motivo. Botón para descargar el `.xlsx`.

Si el tipo elegido no coincide con el contenido del archivo, la app lo corta con un mensaje claro antes de generar nada.

### Reporte de pendientes

Cada pendiente queda **resaltado en ámbar** en la celda correspondiente del Excel.

| Severidad | Cuándo aparece |
|---|---|
| **Falta información** | El campo llega vacío, con `NO HAY INFORMACIÓN SUFICIENTE`, o un bloque obligatorio no tiene elementos |
| **A revisar** | El agente escribió `[REVISAR: valor-encontrado]` porque el valor real no estaba en la lista permitida |
| **Valor no permitido** | El valor no está en `contrato/opciones-*.json` |

Los arrays que legítimamente pueden ir vacíos (`Events to which it is subscribed`, `Asynchronous Consumers`, `Other accesses`) no generan ruido.

---

## Uso desde la CLI

```powershell
cd app

# Una transacción
python -m apx_helper render contrato-t501.json -o salida

# Varias transacciones -> UN libro con una hoja por transacción
python -m apx_helper render t501.json t511.json t521.json -o salida

# ...o un único .json que contenga una lista de contratos
python -m apx_helper render lote.json -o salida

# Un archivo por transacción en vez de combinarlas
python -m apx_helper render t501.json t511.json --split -o salida

# Una librería (el identificador sale del propio contrato)
python -m apx_helper render contrato-advsr500.json -o salida

# Validar sin generar nada
python -m apx_helper validate contrato-t501.json
```

| Opción | Para qué |
|---|---|
| `-o, --output` | Carpeta de salida (por defecto `./salida`) |
| `--split` | No combinar transacciones en un mismo libro |
| `--library-id` | Sobrescribe el identificador de la librería |
| `--name` | Sobrescribe el nombre base del archivo |

---

## API REST

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/health` | Estado y versión |
| `POST` | `/api/contracts/validate` | Valida la estructura del contrato |
| `POST` | `/api/contracts/process` | **La que usa la UI.** Multipart (`file`, `expected_kind`, `library_id`). Devuelve `{kind, filename, sheets, summary, issues[], fileBase64}` |
| `POST` | `/api/contracts/xlsx` | Body JSON (objeto o lista). Devuelve el `.xlsx` directo |

Documentación interactiva en `/docs`.

---

## Estructura del repo

```
contrato/              Contratos de referencia y listas de valores válidos
  contrato-transaccion.json      formato exacto que debe producir el agente
  contrato-libreria.json
  opciones-transaccion.json      valores permitidos por campo desplegable
  opciones-libreria.json
hojas-apx/             Plantillas Excel maestras (NO se modifican al generar)
instructions/          Prompt del agente que produce los contratos
app/                   La aplicación
  apx_helper/
    api.py             FastAPI + montaje de la UI
    cli.py             Línea de comandos
    contracts.py       Carga y validación estricta contra contrato/*.json
    layout.py          MAPA DE CELDAS de las plantillas ← lo que se toca al cambiar de versión
    generator.py       Rellena las hojas y produce el reporte de pendientes
    xlsx.py            Helpers de openpyxl (merges, inserción de filas con estilo, copia de hojas)
    settings.py        Rutas de plantillas y contratos
    static/            Interfaz web (HTML + CSS + JS, sin build)
  examples/            Contratos de ejemplo listos para probar
  tests/               21 pruebas
  tools/               Utilidades de mantenimiento
```

---

## Cómo funciona por dentro

```
JSON  →  validate()  →  detect_kind()  →  render_transactions() / render_library()
                                              │
                                              ├─ load_workbook(plantilla)   copia en memoria
                                              ├─ renombrar hojas
                                              ├─ escribir campos escalares
                                              └─ escribir bloques (de abajo hacia arriba)
                                                     → RenderResult(workbook, filename, issues)
```

1. **Validación estricta**: se compara clave a clave contra `contrato/contrato-*.json`. Falla si falta una clave, si hay una de más o si cambia un tipo. El tipo de contrato se deduce de la clave raíz.
2. **La plantilla se carga en memoria**, nunca se abre en escritura. `RenderResult.save()` además rechaza escribir dentro de `hojas-apx/`.
3. **Bloques de abajo hacia arriba**: si un array trae más elementos que filas disponibles, se insertan filas clonando estilo, alto, celdas combinadas y desplegables; todo lo que está debajo baja en bloque. Procesar en orden inverso evita descuadrar los bloques superiores.
4. Las hojas `Parameters (Do not remove)` y `Change Log` viajan intactas, por eso los desplegables del archivo generado siguen funcionando.

---

## Convenciones de rellenado

Las hojas rellenadas a mano tienen errores humanos y se contradicen entre sí. Estas son las reglas que aplica la app, de forma determinista:

| Regla | Criterio |
|---|---|
| Posición del valor | **Siempre debajo del encabezado**, nunca a su derecha |
| Encabezados y rótulos | Intocables |
| Filas de muestra | Se limpian siempre (`executeA`, `executeB`) |
| Desbordamiento | Inserción de filas con estilo, no truncado |
| Arrays vacíos | Las filas de la plantilla quedan en blanco |
| Columna B de parámetros | `Input` / `Output` |
| Nombre de archivo | `<ID> - <nombre de la plantilla>.xlsx` |
| Agrupación | N transacciones → 1 libro con N hojas · 1 librería → hoja principal + 1 hoja por método |

---

## Mantenimiento

```powershell
cd app

# Pruebas
python -m pytest tests -q

# ¿Contratos, mapeo de celdas y desplegables siguen alineados?
python tools\audit_contracts.py

# Volcar la estructura de una plantilla (útil si BBVA publica una versión nueva)
python tools\inspect_sheets.py "..\hojas-apx\APX Transactions Global Sheet v1.1.xlsx"

# Sincronizar los desplegables de las plantillas con opciones-*.json
# (sin --apply solo informa; es lo único que modifica las plantillas maestras)
python tools\sync_template_options.py
python tools\sync_template_options.py --apply
```

`tests/test_consistencia.py` falla si alguien agrega una clave al contrato sin mapearla a una celda, o un valor de opciones que la plantilla no lista. Es la red de seguridad principal.

### Si cambia la versión de la plantilla

1. Dejá el nuevo `.xlsx` en `hojas-apx/` (se busca por patrón, la versión del nombre no importa).
2. Ejecutá `tools/inspect_sheets.py` para ver filas, merges y validaciones.
3. Ajustá las coordenadas en `apx_helper/layout.py`. **Es el único archivo con números de fila.**
4. Corré las pruebas.

### Variables de entorno

| Variable | Por defecto |
|---|---|
| `APX_TEMPLATES_DIR` | `hojas-apx/` en la raíz del repo |
| `APX_CONTRACTS_DIR` | `contrato/` en la raíz del repo |
