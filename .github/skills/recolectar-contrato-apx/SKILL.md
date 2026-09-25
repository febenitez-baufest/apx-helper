---
name: recolectar-contrato-apx
description: "Genera contratos JSON de transacciones APX du_online (contrato-transaccion.json) de forma determinista y verificable. Use when: documentar transacciones APX, recolectar contrato APX, generar JSON de transacción, Error Management, parámetros paramsIn/paramsOut, ABKOT/UUAAT, validar contrato generado contra XML y código."
argument-hint: "<raíz del proyecto APX> <ID de transacción o 'todas'> <carpeta de salida>"
---

# Recolección de contrato APX con herramientas deterministas

La norma completa es el prompt [recolectar-contrato-apx-tipo-a](../../prompts/recolectar-contrato-apx-tipo-a.prompt.md). Esta skill no la reemplaza: automatiza la parte mecánica y convierte sus reglas en comprobaciones ejecutables. Si algo de aquí contradice la norma, prevalece la norma.

## Reparto de trabajo

| Lo hacen los scripts (no lo rehagas a mano) | Lo haces tú leyendo el código |
|---|---|
| Inventario de parámetros, rutas, `Type`, orden, `Mandatory?`, tipo APX | `Description` de cada parámetro |
| Country, Version, Transaction Identifier, descripción funcional XML+POM | Complemento con Javadoc descriptivo de la clase (solo si no es tautológico) |
| Librerías/métodos invocados | `Description` de cada librería |
| Grafo de llamadas, códigos alcanzables, orden DFS, textos de excepción | Confirmar propagación, severidad aplicable, descripción final |
| Marcadores explícitos de transaccionalidad/asincronía | Flujo de ejecución |

## Procedimiento por transacción

Todas las rutas de scripts son relativas a esta skill: `./scripts/`. Ejecuta con `python`.

1. **Esqueleto**: `python ./scripts/scaffold.py <raiz> <ID> <salida>/<ID>.json`
   Nunca edites a mano `Name of APX field`, `Mandatory?`, `APX data type`, el orden de filas ni las librerías: ya son canónicos.
2. **Expediente**: `python ./scripts/evidence.py <raiz> <ID> --out <salida>/_evidencia/<ID>.txt` y lee el archivo completo. Contiene la clase concreta, setters de salida, firma/Javadoc de librerías, grafo de llamadas desde `execute()`, cuerpo de cada método alcanzado, secuencia DFS de errores con su condición de disparo y descripciones candidatas, severidades, properties, marcadores, (sección 7) los accesos get/set/constructor de cada campo en métodos alcanzables y (sección 8) los getters/setters con lógica e inicializadores de cada DTO.
3. **Completa cada `__TODO__`** siguiendo [reglas de redacción](./references/reglas-redaccion.md). Cada placeholder es único: sustitúyelo con la herramienta de edición de archivos. Prohibido reescribir el JSON con PowerShell (`Set-Content`, `Out-File`, `>`): introduce BOM o concatena objetos.
4. **Valida**: `python ./scripts/validate.py <raiz> <salida>/<ID>.json`
   - `ERROR` bloquea: corrige y repite.
   - `AVISO` exige revisión con evidencia del expediente: corrige o conserva solo si puedes citar la línea que lo justifica.
   - Termina solo con `RESULTADO <ID>: OK`.
5. **Autorrevisión final** con la [lista de control](./references/lista-control.md).

## Uso del expediente para Error Management

- La sección 5 da los códigos alcanzables en orden DFS estático. Ese es el orden obligatorio del array.
- Un código de la sección 5 solo puede omitirse si demuestras que su excepción nunca llega a un `addAdvice*` (por ejemplo, se captura y descarta). Un código ausente del grafo no se incluye.
- `descripción candidata` es el texto normalizado de la emisión: `%s` se conserva, las concatenaciones aparecen como `{expr}`. Si hay una sola candidata, úsala literalmente. Si hay varias, aplica la regla 8 de la norma (misma prioridad: archivo lexicográficamente menor y primera posición).
- `[log adyacente candidato]` solo vale si cumple las cuatro condiciones de la norma; quita el prefijo.
- Severidad: mapea el `setSeverity` que alcanza cada advice (`WARN/WRN`→`04 - WARNING`, `ENR`→`06 - ERROR NO ROLLBACK`, `ERR/EWR`→`08 - ERROR WITH ROLLBACK`). Un `setSeverity` condicionado por `getAdviceList()` no vacío aplica a todos los advices que lo alcanzan.

## Límites conocidos de los scripts

- El grafo es léxico: resuelve tipos declarados, llamadas estáticas, `this`/`super`, `Clase::metodo` y librerías de `getServiceLibrary`. Lambdas complejas, reflexión o interfaces con varias implementaciones pueden quedar sin seguir: revisa la sección 4 si un helper esperado no aparece.
- No evalúa condiciones: toda rama es alcanzable salvo que demuestres que su condición es constante y falsa.
