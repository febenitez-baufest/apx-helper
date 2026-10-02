# Reglas de redacción (librería Tipo B)

Idioma: el de la descripción funcional de la librería (si el Javadoc/POM está en inglés, todo lo derivado va en inglés). Los textos literales de error se copian sin traducir.

## `LIBRARY - FUNCTIONAL GROUPING DESCRIPTION`

Fuente: `<description>` del POM de la interfaz; si falta o es vacío, el del POM padre. No la reescribas ni la completes con negocio inventado aunque sea genérica (p. ej. `Deployment unit advsrXXX of uuaa advs`): es la única evidencia EXPLÍCITA disponible. Si de verdad no hay ninguna fuente, usa el marcador.

## `Brief description` (resumen del método)

Fuente primaria: Javadoc del método en la interfaz pública, recortado antes del primer `@tag` (`@param`, `@return`...). Descarta el Javadoc si es tautológico (`El método executeX`, `The executeX method`, `Execute X`): en ese caso usa el comportamiento observado en la implementación (una frase, verbo + objeto + medio), nunca el nombre del método repetido.

## `DESCRIPTION OF THE FUNCTIONALITY`

Una descripción más extensa (máximo 3-4 frases) de lo que hace la implementación, en orden: qué valida, qué transforma, a qué accede (librería/BBDD/proxy) y qué devuelve o persiste. Usa los nombres exactos de métodos y clases citados en el expediente. No repitas aquí el flujo paso a paso de una transacción: es un resumen funcional de la librería, no un EXECUTION FLOWS.

## Descripción de parámetros de entrada

Plantilla: `<Qué es, si la fuente lo dice> used to <operación observable> <objeto afectado>.`

Antes de afirmar un uso, confirma en el cuerpo del método (sección 2 del expediente) que ese parámetro concreto (o el campo del DTO) se lee y no una constante con el mismo valor. Si el parámetro no se usa en ninguna rama alcanzable, dilo explícitamente: `Received but not read by the reachable flow.`

Para un campo DTO cuyo origen no está disponible en el repositorio (solo `.class`/jar de un artifact externo), usa `"NO HAY INFORMACIÓN SUFICIENTE"` salvo que el Javadoc del parámetro en la interfaz ya describa su propósito con suficiente especificidad (en ese caso, cítalo).

## Descripción de parámetros de salida (valor de retorno)

- Si el método devuelve `void`, el array `Output Parameters` es `[]`: no inventes una fila.
- Si devuelve un DTO con fuente disponible, describe de dónde sale cada campo (mapeo, cálculo, copia) igual que en la skill de transacciones: nombra el origen concreto cuando el código lo muestre.
- Si devuelve el mismo objeto recibido sin transformación, usa la frase canónica `Returned without transformation.`
- Si no hay evidencia de mapeo ni de origen, usa el marcador.

## Descripción de `Accessed libraries` (otra librería APX invocada)

`<Verbo> <qué> <cómo, con la operación principal observada en el método implementado>.` Máximo dos frases. Nunca uses un Javadoc tautológico (`The execute method...`). El `Country` de la llamada solo se marca si el código lo fija explícitamente (p. ej. un parámetro `country` propagado) o si la librería invocada es explícitamente de un único país; si no hay evidencia, usa `"Common"` solo cuando el propio código declare ese alcance, y el marcador en cualquier otro caso.

## Descripción de `Other accesses` (JDBC, MongoDB, Proxy Service, etc.)

1. `Access Type`: ya lo determina el script a partir del bean de `*-arc.xml` (ver tabla en el prompt normativo). No lo cambies sin evidencia de que el script se equivocó de bean.
2. `Identifier`:
   - Para `Proxy Service` vía `internalApiConnector`, es el valor de la propiedad APX (`getPropertyValue("...")` / `applicationConfigurationService.getProperty("...")`) usada para resolver el `apiId`, no el id del bean Spring.
   - Para `JDBC`/`MongoDB`/`Document Manager`, es el nombre de la tabla, colección o bucket usado en la consulta.
3. `Access`: el verbo/operación real (`POST /v0/...`, `find(...)`, `upsert N1QL`, `SELECT ...`), tomado del método que usa el bean, no una paráfrasis genérica como "accede a la base de datos".
4. `Description`: una frase de la finalidad de negocio de ese acceso dentro del método.

## Error Management (solo `Error Code` + `Description of the error situation`, sin `Severity`)

1. Usa el orden DFS de primera emisión de la sección 6 del expediente, por método. No reordenes por código.
2. La descripción es el texto de `addAdviceWithDescription`, de la excepción, de `multilanguage-ES.properties`, o del Javadoc de la constante en `Constants.java` si el properties está vacío, en ese orden de precedencia. Conserva placeholders (`%s`) y literales exactos.
3. Nunca copies una descripción de un método `execute*` distinto aunque comparta código de error con otro.
4. Si dos emisiones alcanzables del mismo método usan el mismo código con descripciones distintas, aplica la misma regla de desempate que en transacciones: prioridad de fuente y, dentro de la misma prioridad, archivo lexicográficamente menor y primera posición.

## Metadatos

- `Visibility`: siempre `"Public"`. No uses el marcador ni otro valor para una librería standalone Tipo B.
- `Library Type`: el script lo deriva de las dependencias reales (`${apx.core.online.version}` / `${apx.core.batch.version}`); si da el marcador, confirma manualmente leyendo si el proyecto declara un módulo o perfil batch adicional antes de elegir un valor.
- `For other, indicate`: déjalo vacío `""` salvo que `Library Type` no tenga un valor de la lista cerrada y debas aclararlo en texto libre (caso excepcional).
- El marcador exacto es `NO HAY INFORMACIÓN SUFICIENTE` (con tilde en la Ó). El validador rechaza variantes.
