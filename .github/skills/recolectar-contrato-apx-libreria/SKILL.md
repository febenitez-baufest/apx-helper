---
name: recolectar-contrato-apx-libreria
description: "Genera contratos JSON de librerías APX standalone du_lib (contrato-libreria.json) de forma determinista y verificable. Use when: documentar librería APX Tipo B, recolectar contrato de librería, generar JSON de librería ADVSR___, EXECUTE - METHODS SUMMARY, Accessed libraries, Other accesses, Error Management de librería, validar contrato de librería generado contra POM, interfaz y código."
argument-hint: "<raíz del proyecto APX (resource_type: lib)> <carpeta de salida>"
---

# Recolección de contrato APX de librería (Tipo B) con herramientas deterministas

La norma completa es el prompt [recolectar-contrato-apx-tipo-b](../../prompts/recolectar-contrato-apx-tipo-b.prompt.md). Esta skill no la reemplaza: automatiza la parte mecánica y convierte sus reglas en comprobaciones ejecutables. Si algo de aquí contradice la norma, prevalece la norma.

El esquema canónico está incluido en [references/contrato-libreria.json](references/contrato-libreria.json) y las listas de valores seleccionables en [references/opciones-libreria.json](references/opciones-libreria.json). El proyecto APX analizado no necesita aportar una carpeta `contrato/`; si existe, se conserva únicamente como compatibilidad con ejecuciones antiguas.

Esta skill es hermana de [recolectar-contrato-apx](../recolectar-contrato-apx/SKILL.md) (transacciones, Tipo A) y reutiliza sus primitivas de texto/Java puras (`strip_code`, `method_spans`, `line_of`, etc.) vía `lib_common.py`. No la sustituye ni la modifica: una librería standalone (`apx.json` → `resource_type: "lib"`) vive en `<UUAARXXX>/` y `<UUAARXXX>IMPL/` en la raíz del proyecto, no bajo `artifact/transactions/`, así que el índice de clases, las constantes y el grafo de llamadas se recalculan con alcance a toda la raíz.

## Diferencias clave frente a una transacción (Tipo A)

| | Transacción (Tipo A) | Librería (Tipo B) |
|---|---|---|
| Unidad de contrato | Una por transacción (`<ID>.xml`) | Una por librería completa, con un array de métodos |
| Fuente de parámetros | `<paramsIn>`/`<paramsOut>` del XML | Firma Java del método público + campos del DTO si su fuente está en el repo |
| `Visibility` | No aplica | Siempre `"Public"` |
| `Severity` en errores | Sí (`setSeverity`) | No existe en el esquema de librería: solo `Error Code` + descripción |
| Llamadas a otras librerías | `TECHNICAL DATA.Accessed Libraries` | `Accessed libraries` por cada método `execute*` |
| Accesos externos (JDBC, MongoDB, Proxy Service…) | No se modela aparte | `Other accesses` por método, detectado en `*-arc.xml` |

## Reparto de trabajo

| Lo hacen los scripts (no lo rehagas a mano) | Lo haces tú leyendo el código |
|---|---|
| Inventario de métodos públicos de la interfaz, firma, Javadoc no tautológico | `DESCRIPTION OF THE FUNCTIONALITY` de cada método |
| Identificador, Visibility fija, Library Type derivado de las dependencias reales | `Brief description` cuando el Javadoc es tautológico o falta |
| Parámetros expandidos desde la firma y un nivel de campos del DTO (si hay fuente) | `Description` de cada parámetro y `Mandatory?` (requiere leer validaciones) |
| Librerías APX invocadas (`getServiceLibrary`) alcanzables por método | `Description` de cada librería invocada y su `Country` |
| Candidatos de `Other accesses` desde beans de `*-arc.xml` | `Identifier`, `Access` y `Description` exactos de cada acceso externo |
| Grafo de llamadas, códigos alcanzables, orden DFS por método | `Description of the error situation` de cada código |

## Procedimiento por librería

Todas las rutas de scripts son relativas a esta skill: `./scripts/`. Ejecuta con `python`. Solo hay una librería por proyecto, así que no se itera por ID como en transacciones.

1. **Esqueleto**: `python ./scripts/scaffold_lib.py <raiz> <salida>/<LIBRARY_ID>.json`
   Nunca edites a mano `Method name`, el orden de métodos, ni las filas de parámetros ya expandidas desde la firma: ya son canónicos.
2. **Expediente**: `python ./scripts/evidence_lib.py <raiz> --out <salida>/_evidencia/<LIBRARY_ID>.txt` y lee el archivo completo. Contiene, para cada método: el cuerpo completo de la implementación, las librerías APX alcanzables, el grafo de llamadas con emisiones, el cuerpo de cada helper alcanzado, la secuencia DFS de códigos con su condición de disparo, el contenido de `multilanguage-ES.properties` o el Javadoc de la constante cuando está vacío, y los campos de cada DTO de parámetro si su fuente está en el proyecto.
3. **Completa cada `__TODO__`** siguiendo [reglas de redacción](./references/reglas-redaccion-libreria.md). Cada placeholder es único: sustitúyelo con la herramienta de edición de archivos. Prohibido reescribir el JSON con PowerShell (`Set-Content`, `Out-File`, `>`): introduce BOM o concatena objetos.
4. **Valida**: `python ./scripts/validate_lib.py <raiz> <salida>/<LIBRARY_ID>.json`
   - `ERROR` bloquea: corrige y repite.
   - `AVISO` exige revisión con evidencia del expediente: corrige o conserva solo si puedes citar la línea que lo justifica.
   - Termina solo con `RESULTADO <LIBRARY_ID>: OK`.
5. **Autorrevisión final** con la [lista de control](./references/lista-control-libreria.md).

## Uso del expediente para Error Management de librería

- La sección 6 del expediente (por método) da los códigos alcanzables en orden DFS estático. Ese es el orden obligatorio del array `Error Management` de ese método.
- Un código solo puede omitirse si demuestras que su excepción nunca llega a un advice de la librería (por ejemplo, se captura y descarta sin propagarse). Un código ausente del grafo no se incluye.
- El esquema de librería **no tiene campo `Severity`**: no lo inventes ni lo añadas.
- Si `multilanguage-ES.properties` está vacío (caso frecuente en librerías), usa el Javadoc de la constante en `Constants.java` (sección 7 del expediente) como fuente de la descripción.

## Uso del expediente para `Other accesses`

- La sección 0 imprime el `*-arc.xml` completo; identifica los beans de infraestructura (`JdbcTemplate`, `MongoTemplate`, `internalApiConnector`, etc.) según la tabla de la norma.
- El scaffold ya detecta candidatos por bean y los deja como filas `__TODO__` con la línea exacta del XML citada en `Identifier`: confirma el `Access` (verbo/ruta/consulta) leyendo cómo se usa ese bean en el método implementado (sección 2 del expediente).
- Si el acceso es `internalApiConnector` (Proxy Service), el `Identifier` real suele ser el valor de la propiedad (`getPropertyValue(...)` / `applicationConfigurationService.getProperty(...)`) usada para construir el conector, no el id del bean Spring.

## Límites conocidos de los scripts

- El grafo es léxico: resuelve tipos declarados, llamadas estáticas, `this`/`super` y clases del propio proyecto (toda la raíz, no solo `artifact/`). Lambdas complejas, reflexión o interfaces con varias implementaciones pueden quedar sin seguir: revisa la sección 5 del expediente si un helper esperado no aparece.
- No evalúa condiciones: toda rama es alcanzable salvo que demuestres que su condición es constante y falsa.
- Los DTOs de artifacts externos (dependencias `ADVSC___` sin fuente `.java` en el repositorio, solo `.class` o jar) no se pueden expandir en campos: el scaffold deja una única fila con el nombre del parámetro y lo indica explícitamente en la descripción; complétala con `"NO HAY INFORMACIÓN SUFICIENTE"` salvo que encuentres la fuente en otro módulo del repositorio.
- `Library Type` se deriva solo de las dependencias reales declaradas en los POM de interfaz e implementación (`${apx.core.online.version}` / `${apx.core.batch.version}` o artifacts `elara-online`/`elara-batch`); si el POM agregador declara ambas propiedades pero el módulo solo usa una, el script ya lo filtra, pero confírmalo si el resultado te sorprende.
