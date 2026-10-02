# Reglas de redacción

Idioma: el de la descripción funcional de la transacción (si está en inglés, todo lo derivado va en inglés). Los textos literales de error se copian sin traducir.

## Descripción de parámetros de entrada

Plantilla: `<Qué es, si la fuente lo dice> used to <operación observable> <objeto afectado>.`

Antes de afirmar que una entrada se usa en una consulta o validación, comprueba en el cuerpo del método que se lee **ese** campo (sección 7) y no una constante con el mismo valor.

Si la sección 7 no detecta acceso y confirmas que ningún método alcanzable lo lee ni lo mapea, no uses el marcador: escribe `Received inside <ruta del contenedor> but not read or persisted by the reachable flow.` (es evidencia negativa verificada, no falta de información).

Operaciones válidas solo si las ves en el código alcanzable: filtra una consulta, valida, identifica el registro a leer/modificar, pagina, se copia a otro DTO que se envía a la librería, se persiste en una columna.

| Mal | Por qué | Bien |
|---|---|---|
| `Return value for input parameter customerId` | Javadoc generado | `Customer identifier used to filter the query by CUSTOMER_ID.` |
| `The customer identifier.` | Solo repite el nombre | idem, con la operación observada |
| `Customer identifier, required by the business.` | Inventa negocio | idem |
| `Branch identifier used to filter by branchId.` | Circular: la operación no añade nada | `Branch identifier used to filter orders through the BRANCH_ID condition of the count and page queries.` |

## Descripción de parámetros de salida

Antes de redactar, mira la sección 7 (accesos) y la sección 8 (accesores no triviales del DTO) del expediente para ese campo.

0. Si la sección 8 muestra un getter/setter con lógica para el campo (default, conversión, generación), descríbelo: `Returned as <origen>; <getter/setter> applies <regla> (e.g. defaults to X when null).` Esta regla prevalece sobre la frase canónica del punto 2.

1. Hay mapeo propio (setter, constructor, `row.get("COL")`, cálculo): nombra el origen concreto. `<Valor> mapped from column <COL> in <Mapper.metodo>.` / `calculated as <regla>.` Nombrar la columna o el campo de origen es lo que más valor aporta: hazlo siempre que el código lo muestre.
2. El contenedor se asigna completo y este descendiente **llega poblado** sin transformación (p. ej. se devuelve el mismo DTO de entrada, o una copia campo a campo): usa **exactamente** la frase canónica
   `Returned without transformation inside <ruta del contenedor>.`
   No la uses si el descendiente nunca se rellena: si la sección 7 no muestra acceso y el objeto se construyó con un mapper que no lo asigna, escribe `Not populated by <Mapper.metodo>; null inside <ruta del contenedor>.` (null, no "empty", salvo que la sección 8 muestre un inicializador).
3. Un default que solo aparece al construir parámetros SQL (`Map.of`, `put` para INSERT/UPDATE) describe lo que se persiste, no lo que se devuelve. En la salida, solo menciona defaults aplicados en el DTO devuelto (getter/setter del propio DTO).
4. No hay ninguna evidencia (ni mapeo, ni copia, ni mapper que lo omita): `NO HAY INFORMACIÓN SUFICIENTE`.
5. Nunca escribas "not assigned", "not returned", "without response" si el setter del contenedor se ejecuta sin guarda (mira la sección 1b del expediente: `addParameter` sin `if`). Un `null` asignado sigue siendo asignación.

Contenedores (`dto`/`compound`): describe qué agrupa y de dónde sale, p. ej. `List of orders returned by LIBX.executeGetOrders, one element per retrieved row.`

## Descripción de librería

`<Verbo> <qué> <cómo, con las operaciones principales observadas en el método implementado>.` Máximo dos frases. No uses el Javadoc si es `The execute method...`.

## Flujo de ejecución

Un único string con estas cinco etiquetas fijas, en este orden y en el idioma de la transacción:

`1. Input and validations: ... 2. Decisions and branches: ... 3. Invoked libraries and methods: ... 4. Errors and subsequent actions: ... 5. Outputs and assignment conditions: ...`

- Cada frase: condición → acción → efecto, con nombres exactos de métodos, parámetros y códigos.
- En 3, atribuye cada paso al método que realmente lo ejecuta (mira en la sección 3 del expediente quién llama a quién); no atribuyas a un helper lo que hace su llamador.
- En 4, menciona cada código de `Error Management` en el mismo orden DFS **con su condición de disparo y el método que lo lanza** (líneas `disparo en` de la sección 5). Una lista de códigos sin condiciones es insuficiente.
- En 5, di cuándo se llama a cada setter de salida y con qué valor (incluido `null` si puede serlo).
- Distingue lo que hace la transacción de lo que hace un getter o la librería: un getter que devuelve `null` no es un retorno temprano de `execute()`.
- Si una rama compara `dto.getX() == null` y la sección 8 muestra que `getX()` aplica un default, esa rama nunca se ejecuta: no la describas como comportamiento (ni en el flujo ni en los parámetros).
- Si una categoría no tiene operaciones, escribe una frase breve que lo diga (p. ej. `No input validations are performed in execute().`), no el marcador.

## Metadatos

- `Migration - Origin from Host`: marcador salvo documentación/metadato explícito de migración y host.
- `Asynchronous?` / `Transactional?`: marcador salvo que la sección 6 del expediente muestre coincidencias. JDBC, varias escrituras, `EWR` o rollback de APX no prueban nada.
- `Asynchronous Consumers` y `Events to which it is subscribed`: `[]` si la sección 6 no muestra listeners/consumers.
- El marcador exacto es `NO HAY INFORMACIÓN SUFICIENTE` (con tilde en la Ó). El validador rechaza variantes.
