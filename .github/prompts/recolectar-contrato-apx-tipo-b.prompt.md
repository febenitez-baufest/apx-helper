---
description: "Analiza exhaustivamente una librería APX standalone (resource_type: lib) y genera un único contrato JSON reproducible con todos sus métodos execute*."
---

# Recolección determinista de contrato APX - Tipo B (librería standalone)

## 1. Objetivo y alcance

Eres un experto en arquitectura APX de BBVA. Dado un único proyecto APX cuyo `apx.json` declara `resource_type: "lib"`, analiza su interfaz pública y su implementación y genera un único JSON de contrato respetando exactamente `contrato-libreria.json`.

Analiza únicamente información existente en el repositorio. Esta tarea es de lectura, análisis y generación de una respuesta. Regla de no modificar: no modifiques, crees, elimines ni formatees archivos del proyecto durante la investigación.

No analices transacciones ni generes contratos de transacción. Si el proyecto invoca otras librerías APX (`getServiceLibrary`), documenta esa llamada en `Accessed libraries` del método que la realiza; no generes un contrato aparte para la librería invocada.

## 2. Prioridad y restricciones obligatorias

Aplica las reglas en este orden de prioridad:

1. El contrato JSON de referencia y sus tipos.
2. Las reglas de evidencia, inclusión y exclusión de este prompt.
3. El procedimiento de siete fases y sus criterios de recorrido.
4. La matriz de origen y sus precedencias de fuentes.
5. Las reglas de normalización, deduplicación y ordenamiento.
6. Los ejemplos, que aclaran las reglas anteriores pero nunca las sustituyen.

Si dos fuentes difieren, usa la de mayor prioridad indicada en la matriz. No combines valores incompatibles ni elijas uno por intuición. Cuando las reglas no permitan resolver el conflicto de forma inequívoca, usa `"NO HAY INFORMACIÓN SUFICIENTE"` en el campo afectado.

Regla de no usar el primer resultado como resultado definitivo: no detengas el análisis al encontrar el primer método o el primer error. Completa el inventario de métodos públicos de la interfaz y, para cada uno, el recorrido de todas las ramas estáticamente alcanzables desde su implementación antes de redactar su bloque del contrato.

No uses archivos de `target/` cuando exista su equivalente en `src/`. Para Java, dos archivos son equivalentes si pertenecen al mismo artifact y declaran el mismo package y clase; para recursos, si pertenecen al mismo artifact y tienen la misma ruta relativa bajo `src/main/resources` y `target/classes`. Busca primero en `src/`, usa `target/` solo si no existe la fuente equivalente y no mezcles ambas copias.

## 3. Estructura esperada

```text
<UUAARXXX>/                       # interfaz pública
  pom.xml                         # descripción en <description>
  src/main/java/com/<uuaa>/lib/rXXX/
    <UUAARXXX>.java               # métodos públicos (execute*), con Javadoc
<UUAARXXXIMPL>/                   # implementación
  pom.xml
  src/main/java/com/<uuaa>/lib/rXXX/impl/
    <UUAARXXX>Impl.java           # lógica de cada método
    <UUAARXXX>Abstract.java       # inyección de dependencias (APIConnector, ApplicationConfigurationService...)
    constants/Constants.java      # códigos de error con Javadoc ← usar cuando multilanguage vacío
    <paquetes internos>/          # helpers y servicios propios de la librería (p. ej. couchbase/service/)
  src/main/resources/
    multilanguage-ES.properties   # puede estar vacío; si lo está, usar Constants.java
    META-INF/spring/
      <UUAARXXX>-arc.xml          # infraestructura ← fuente primaria de accesos externos
      <UUAARXXX>-app.xml          # registro del bean (no es la fuente primaria de accesos)
apx.json                          # resource_type: "lib"
pom.xml                           # POM agregador/padre de los dos módulos anteriores
```

La estructura muestra ubicaciones habituales. Localiza la interfaz como el único directorio hijo directo de la raíz (que no termine en `IMPL`) con `pom.xml` propio y una clase Java del mismo nombre bajo `src/main/java`; la implementación es `<ese_nombre>IMPL/`. No uses `target/` para descubrir la interfaz o la implementación.

## 4. Contrato de salida inviolable

Lee el esquema incluido en `recolectar-contrato-apx-libreria/references/contrato-libreria.json` antes del análisis. El JSON final debe conservar exactamente sus claves, su orden, sus niveles de anidación y sus tipos. No renombres, agregues, elimines ni reordenes claves. El esquema de librería **no tiene** el campo `Severity` que sí existe en el contrato de transacción: no lo añadas por analogía.

Completa todos los campos. Usa estas representaciones canónicas:

- Campo escalar sin evidencia suficiente: `"NO HAY INFORMACIÓN SUFICIENTE"`.
- Colección sin elementos demostrados después de revisar todas sus fuentes definidas: `[]`.
- No uses `null`, cadenas vacías, objetos vacíos ni textos alternativos para representar ausencia de información, salvo `"For other, indicate"`, que es `""` cuando no aplica.
- Conserva identificadores, códigos y placeholders con la grafía exacta de la fuente.

Valores válidos para campos seleccionables (ver `recolectar-contrato-apx-libreria/references/opciones-libreria.json`):

- `Visibility`: siempre `"Public"` para una librería standalone Tipo B (se publica entre DUs); no uses el marcador ni otro valor de la lista (`Private`, `Other`) salvo evidencia explícita en contra documentada en el propio repositorio.
- `Library Type`: `On-line`, `Batch`, `Both` o `"NO HAY INFORMACIÓN SUFICIENTE"`.
- `Country` (en `Accessed libraries` y `Other accesses`): `ES`, `MX`, `PE`, `CO`, `US`, `GL`, `AR`, `Common` o el marcador.
- `Access Type`: `Elastic`, `Document Manager`, `JDBC`, `JPA`, `Document Handling`, `MongoDB`, `Rules Engine`, `Proxy Service`, `Multichannel Service`, `IMSConnect`, `Neo4j`, `Remote Service`.
- `Format Type`: `array`, `bean`, `boolean`, `byte`, `char`, `date`, `double`, `float`, `int`, `list`, `long`, `map`, `queue`, `set`, `short`, `string`.
- `Mandatory?`: `Yes` o `No`.

La regla del marcador prevalece sobre las listas de valores seleccionables: si un campo escalar carece de evidencia suficiente (salvo `Visibility`, que siempre es `Public`), usa `"NO HAY INFORMACIÓN SUFICIENTE"` en lugar de elegir un valor por defecto.

## 5. Modelo interno de evidencia

Clasifica internamente cada dato antes de usarlo:

- **EXPLÍCITO**: aparece directamente en una fuente permitida del proyecto.
- **DERIVADO**: resulta de seguir inequívocamente el flujo o de aplicar un mapeo definido en este prompt.
- **NO EXPLÍCITO**: no existe evidencia suficiente, hay fuentes incompatibles sin desempate definido o el dato requeriría una suposición.

Solo los valores **EXPLÍCITOS** o **DERIVADOS** pueden presentarse como hechos. Las etiquetas son control interno: nunca deben aparecer en la salida.

## 6. Procedimiento obligatorio

### FASE 1 - Descubrimiento

1. Localiza la raíz del proyecto por el `apx.json` correspondiente y confirma `resource_type: "lib"`.
2. Identifica la interfaz (`<UUAARXXX>/`) y la implementación (`<UUAARXXX>IMPL/`) como se describe en la sección 3. Hay exactamente una librería por proyecto: no busques varias.
3. Enumera todos los métodos públicos declarados en `<UUAARXXX>.java` (típicamente `execute*`), en el orden en que aparecen en el archivo. Ese orden es el orden final del array `EXECUTE - METHODS SUMMARY`.
4. Para cada método, localiza su implementación exacta en `<UUAARXXX>Impl.java` (mismo nombre y misma firma; si hay sobrecargas, trata cada una por separado y repórtalo).
5. Busca todas las llamadas alcanzables desde cada método implementado: helpers privados/protegidos de la propia clase, de la superclase (`<UUAARXXX>Abstract`), de clases auxiliares del propio proyecto (cualquier paquete bajo la implementación) y de otras librerías APX obtenidas con `getServiceLibrary(...)`.
6. Busca todas las coincidencias antes de seleccionar evidencia. Una coincidencia temprana no cierra el descubrimiento de otros métodos, sobrecargas, helpers o ramas.

### FASE 2 - Recopilación

Para la librería completa, crea internamente un expediente con estas secciones y recopila toda su evidencia candidata:

1. **Identidad**: `apx.json`, POM de interfaz e implementación (`<description>`, dependencias), `*-arc.xml`.
2. **Métodos**: firma completa y Javadoc de cada método de la interfaz.
3. **Flujo por método**: cuerpo de cada método implementado y todos los helpers alcanzables desde él, dentro y fuera de la clase `Impl`.
4. **Librerías invocadas**: cada clase pasada a `getServiceLibrary(...)` y cada método realmente llamado sobre la instancia, alcanzable desde el método `execute*` en análisis (no desde otro método de la misma librería).
5. **Accesos externos**: beans de infraestructura en `*-arc.xml` (`JdbcTemplate`/`DataSource`, `MongoTemplate`/`MongoClient`, `CouchbaseTemplate`/conectores Couchbase propios, `internalApiConnector` con `factory-method="getAPIConnector"`, `<osgi:reference interface="...Proxy...">`, `Neo4jTemplate`/`Neo4jClient`, `IMSConnect`, `EntityManager`/`JpaRepository`, motores de reglas) y su uso real dentro del método implementado.
6. **Errores**: emisiones propias y excepciones convertidas en advice de cada método, y de cada helper/clase auxiliar alcanzable desde él.
7. **Eventos**: publicaciones de eventos (`ApplicationEventPublisher`, productores JMS/Kafka, beans de publicación en `*-app.xml`) alcanzables desde el método. Una librería SÍ puede modelar eventos que genera (a diferencia de una transacción, que solo modela eventos a los que se suscribe).
8. **Descripciones de error**: textos en llamadas o excepciones alcanzables, `multilanguage-ES.properties` del módulo de implementación y, si está vacío, Javadoc de la constante en `Constants.java` (o clase equivalente) asociada al código.
9. **Parámetros**: tipo Java exacto de cada parámetro del método y de su valor de retorno; para parámetros/retornos de tipo DTO, localiza su clase por nombre simple en todo el proyecto (no solo bajo la implementación) y revisa sus campos privados en `src/`, usando `target/` solo si no existe fuente equivalente. Si el DTO pertenece a un artifact externo sin `.java` disponible en el repositorio (solo `.class` o jar), decláralo explícitamente y no inventes campos.

Recorre cada cuerpo de método en orden de aparición de las sentencias. Al encontrar una llamada a un método local, de la superclase, de una clase auxiliar del proyecto o de otra librería APX, sigue esa llamada antes de continuar con la sentencia siguiente. Identifica métodos por clase, nombre y firma; no mezcles sobrecargas. Visita cada firma una sola vez por ruta para evitar ciclos. Considera potencialmente alcanzables todas las ramas salvo aquellas cuya condición pueda demostrarse constante y falsa a partir del propio código.

### FASE 3 - Clasificación y filtrado

#### Matriz de origen de datos

| Clave en el JSON | Valor buscado | Origen primario | Respaldo o derivación permitida | Clasificación |
|---|---|---|---|---|
| `LIBRARY - FUNCTIONAL GROUPING DESCRIPTION` | Descripción funcional de la librería | POM de la interfaz -> `<description>` | POM padre -> `<description>`, solo si falta en la interfaz | EXPLÍCITO |
| `TECHNICAL DATA.Library Identifier` | Identificador de la librería | Nombre de la carpeta de interfaz / `<artifactId>` de su POM | — | EXPLÍCITO |
| `TECHNICAL DATA.Visibility` | Visibilidad | Fija: `"Public"` para Tipo B | — | DERIVADO |
| `TECHNICAL DATA.Library Type` | Tipo de librería | Dependencias reales del POM de interfaz/implementación (`${apx.core.online.version}`, `${apx.core.batch.version}`, artifacts `elara-online`/`elara-batch`) | Documentación explícita del README/DOC.md que declare el tipo | EXPLÍCITO, DERIVADO o NO EXPLÍCITO |
| `EXECUTE - METHODS SUMMARY[].Method name` | Nombre del método | Firma pública en `<UUAARXXX>.java` | — | EXPLÍCITO |
| `EXECUTE - METHODS SUMMARY[].Brief description` | Resumen breve | Javadoc del método en la interfaz | Comportamiento observado en la implementación, si el Javadoc es tautológico o falta | EXPLÍCITO o DERIVADO |
| `EXECUTE - METHODS SUMMARY[].DESCRIPTION OF THE FUNCTIONALITY` | Descripción funcional detallada | Javadoc del método implementado + cuerpo del método | — | DERIVADO |
| `Accessed libraries[].Library Identifier`/`Method` | Librería y método APX invocados | `getServiceLibrary(<LIB>.class)` + llamada, alcanzable desde ese método | Interfaz de la librería invocada, solo para confirmar firma | EXPLÍCITO |
| `Accessed libraries[].Description` | Finalidad de la llamada | Javadoc suficiente del método de la interfaz invocada | Método implementado exacto y uso observable, si el Javadoc no es suficiente | EXPLÍCITO o DERIVADO |
| `Other accesses[].Access Type` | Tipo de acceso externo | Bean de infraestructura en `*-arc.xml` según la tabla de la FASE 2.5 | — | EXPLÍCITO o DERIVADO |
| `Other accesses[].Identifier` | Identificador técnico del acceso | Propiedad APX resuelta en el código (`getPropertyValue`/`getProperty`) para `Proxy Service`; nombre de tabla/colección/bucket para JDBC/MongoDB/Document Manager | id del bean Spring, solo si no hay propiedad resuelta en código | EXPLÍCITO o DERIVADO |
| `Other accesses[].Access` | Operación realizada | Verbo/ruta/consulta usado en el método (`POST /...`, `find(...)`, upsert N1QL) | — | EXPLÍCITO o DERIVADO |
| `Error Management[].Error Code` | Error alcanzable por el método | `addAdvice`, `addAdviceWithDescription` o excepción en el método y en sus helpers alcanzables | Solo caminos alcanzables desde ese método concreto; excluir códigos definidos pero no emitidos, otros métodos y funcionalidades no implementadas | EXPLÍCITO o DERIVADO |
| `Error Management[].Description of the error situation` | Descripción del error | Texto de `addAdviceWithDescription(...)` o de la excepción alcanzable | `multilanguage-ES.properties`; si está vacío, Javadoc de la constante en `Constants.java`; después marcador | EXPLÍCITO o DERIVADO |
| `Event that is generated[].Functional name`/`Technical Identifier` | Evento publicado | Publicación explícita (`ApplicationEventPublisher.publishEvent`, productor JMS/Kafka, bean de publicación) alcanzable desde el método | `[]` después de revisar código y configuración sin coincidencias | EXPLÍCITO o DERIVADO |
| `PARAMETERS.Input/Output Parameters[].Name of APX field` | Nombre del parámetro o campo anidado | Nombre del parámetro en la firma Java; para campos de DTO, el nombre del campo privado | — | EXPLÍCITO |
| `PARAMETERS.Input/Output Parameters[].Mandatory?` | Obligatoriedad | Validación explícita en el método (null-check que lanza error, `@NotNull`, Javadoc `no puede ser nulo`) | `Yes` solo con evidencia explícita de obligatoriedad; en cualquier otro caso, revisa si el método tolera el valor nulo antes de marcar `No` | EXPLÍCITO o DERIVADO |
| `PARAMETERS.Input/Output Parameters[].Format Type` | Tipo de formato | Tipo Java de la firma, mapeado con la tabla de la FASE 4 | — | EXPLÍCITO o DERIVADO |
| `PARAMETERS.Input/Output Parameters[].Description` | Finalidad | Javadoc del parámetro en la interfaz | Uso observable en el método implementado y sus helpers alcanzables | EXPLÍCITO o DERIVADO |

#### Inclusiones obligatorias

- Incluye un bloque de método por cada método público de la interfaz, sin excepción.
- Incluye una fila de parámetro por cada parámetro de la firma y, si su tipo es un DTO con fuente disponible, una fila adicional por cada campo privado declarado (un solo nivel adicional salvo que el propio campo sea a su vez otro DTO con fuente disponible, en cuyo caso continúa expandiendo).
- Incluye todas las librerías APX y métodos realmente invocados desde cualquier rama estáticamente alcanzable de ese método concreto.
- Incluye todos los accesos externos (`Other accesses`) demostrados por beans de `*-arc.xml` efectivamente usados en el método.
- Incluye cada código de error que tenga una emisión y una ruta completa de propagación alcanzables desde ese método.

#### Exclusiones obligatorias

- Excluye dependencias del POM que no tengan una invocación alcanzable mediante `getServiceLibrary(...)`.
- Excluye beans de `*-arc.xml` que no se usen en ningún método alcanzable (p. ej. infraestructura declarada pero no invocada desde ningún `execute*`).
- Excluye códigos presentes solo en constantes, properties, README, comentarios, tests, otros métodos de la misma librería, código legacy o funcionalidades no implementadas.
- Excluye ramas, validaciones o errores que no estén en el camino ejecutable analizado desde ese método.
- No interpretes una consulta a `getAdviceList()` como origen de errores nuevos; solo puede evidenciar propagación de advices ya demostrados.
- No uses nombres de clases, métodos, variables o estados como prueba suficiente de comportamiento o de error.
- No uses como descripción final Javadocs generados o tautológicos como `El método executeX`, `The executeX method...`, `Return value for input parameter ...` ni equivalentes.

### FASE 4 - Normalización

#### Mapeo de tipo Java a `Format Type`

| Tipo Java | `Format Type` |
|---|---|
| `String`, `CharSequence` | `string` |
| `Long`/`long` | `long` |
| `Integer`/`int` | `int` |
| `Double`/`double` | `double` |
| `Float`/`float` | `float` |
| `Boolean`/`boolean` | `boolean` |
| `Byte`/`byte` | `byte` |
| `Character`/`char` | `char` |
| `Short`/`short` | `short` |
| `Date`, `LocalDate`, `LocalDateTime`, `Calendar` | `date` |
| `List<T>`, `Collection<T>`, `Iterable<T>` | `list` |
| `Set<T>` | `set` |
| `Queue<T>`, `Deque<T>` | `queue` |
| `Map<K,V>` | `map` |
| `T[]` | `array` |
| Clase propia o DTO (`CamelCase`, no colección ni primitivo) | `bean` |
| `void` como tipo de retorno | `Output Parameters` = `[]` (no genera fila) |

No elijas un tipo por semejanza si no aparece en esta tabla; usa el marcador si el tipo es genérico o no resoluble (`T`, `Object`, `?`).

#### Expansión de parámetros DTO

1. Cada parámetro de la firma genera una fila raíz con su nombre, `Mandatory?`, `Format Type` y `Description`.
2. Si el `Format Type` es `bean` (o el contenido de una colección es un bean) y la clase del DTO tiene fuente `.java` disponible en el proyecto, genera una fila adicional por cada campo privado no estático declarado, con `Name of APX field` = `<parámetro>.<campo>`.
3. Si ese campo es a su vez otro DTO con fuente disponible, continúa expandiendo recursivamente con el mismo criterio.
4. Si la fuente del DTO no está disponible en el repositorio (solo artifact compilado), no generes filas de campos: dilo en la `Description` de la fila raíz (`"NO HAY INFORMACIÓN SUFICIENTE"` o una cita del Javadoc de la interfaz si lo hay) y continúa.
5. Si el método devuelve `void`, `Output Parameters` es `[]`. Si devuelve un tipo no-DTO, genera una única fila con `Name of APX field` = `returnValue`.

#### Reglas de texto

1. Conserva el idioma y significado de las fuentes. No inventes sinónimos ni detalles de negocio.
2. Para texto extraído literalmente, elimina delimitadores de comentario y etiquetas Javadoc no descriptivas (`@param`, `@return`, `@throws`), recorta extremos y sustituye cada secuencia de espacios, tabulaciones o saltos de línea por un único espacio.
3. Conserva placeholders del texto de origen (`%s`, `%d`) y representa cada operando dinámico de una concatenación como `{expresión}`, igual que en la norma de transacciones.
4. No uses como `Brief description` ni `DESCRIPTION OF THE FUNCTIONALITY` un Javadoc que solo repita el nombre del método (`El método executeX`, `The executeX method`, `Execute X`).

### FASE 5 - Ordenamiento y deduplicación

1. `EXECUTE - METHODS SUMMARY`: orden de aparición en la interfaz pública (no alfabético).
2. `Accessed libraries` de cada método: `Library Identifier` y después `Method`, ambos lexicográficos ascendentes.
3. `Other accesses` de cada método: `Access Type` y después `Identifier`, ambos lexicográficos ascendentes.
4. `Error Management` de cada método: orden de primera emisión según el recorrido estático en profundidad desde ese método (misma regla que en la norma de transacciones); desempate por `Error Code` lexicográfico ascendente si dos códigos aparecen en la misma posición lógica.
5. `Event that is generated`: `Functional name` lexicográfico ascendente.
6. Parámetros: orden de la firma Java para las filas raíz; para campos expandidos de un DTO, el orden de declaración de los campos en la clase.

Elimina duplicados lógicos usando estas claves exactas: librería accedida (`Library Identifier`, `Method`); acceso externo (`Access Type`, `Identifier`); error (`Error Code`); evento (`Functional name`).

### FASE 6 - Verificación

Antes de responder, ejecuta una segunda comprobación completa e independiente de la redacción:

1. Compara el array `EXECUTE - METHODS SUMMARY` con el inventario de métodos públicos de la interfaz: mismo conjunto, mismo orden, ninguno falta ni sobra.
2. Confirma que `Visibility` sea `"Public"` en todos los casos y que no exista el campo `Severity` en ningún objeto de `Error Management`.
3. Compara cada fila de parámetros con la firma Java y, si aplica, con los campos del DTO correspondiente.
4. Compara cada librería accedida y cada acceso externo con una invocación/bean efectivamente alcanzable desde ese método concreto.
5. Comprueba bidireccionalmente los errores: cada emisión alcanzable del método aparece exactamente una vez en su `Error Management` y cada entrada del JSON tiene una emisión que la sustenta.
6. Verifica que ninguna descripción sea tautológica y que cada afirmación tenga evidencia registrada (archivo y línea).
7. Valida el JSON contra el esquema incluido en la skill: mismas claves en el mismo orden, mismos tipos, todos los campos presentes, valores seleccionables válidos y JSON sintácticamente válido.
8. Confirma que no se generaron contratos de otras librerías invocadas, tablas internas, clasificación de evidencia, advertencias, razonamientos ni resultados intermedios.

Si una comprobación falla, corrige el expediente y repite las comprobaciones afectadas antes de generar la respuesta.

### FASE 7 - Salida

Genera únicamente el bloque definitivo de la librería. No muestres el procedimiento, el expediente, las fuentes, la tabla de errores, los descartes ni la verificación.

Usa exactamente esta envoltura:

````text
### ADVSR500
```json
{ ... contrato-libreria relleno ... }
```
````

Sustituye el encabezado por el `Library Identifier` real. El contenido debe ser JSON completo, no elipsis. No agregues introducción, conclusión ni texto entre bloques.
