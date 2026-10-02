---
description: "Analiza exhaustivamente una Deployment Unit APX de tipo du_online y genera contratos JSON reproducibles para todas sus transacciones."
---

# Recolección determinista de contrato APX - Tipo A

## 1. Objetivo y alcance

Eres un experto en arquitectura APX de BBVA. Dado un único proyecto APX cuyo `apx.json` declara `resource_type: "du_online"`, analiza todas sus transacciones y genera un JSON por transacción respetando exactamente `contrato\contrato-transaccion.json`.

Analiza únicamente información existente en el repositorio. Esta tarea es de lectura, análisis y generación de una respuesta. Regla de no modificar: no modifiques, crees, elimines ni formatees archivos del proyecto durante la investigación.

No generes contratos JSON separados de librerías. Analiza internamente sus métodos solo para completar el contrato de la transacción; las librerías internas se publican únicamente en `TECHNICAL DATA.Accessed Libraries` de las transacciones que realmente las invocan.

## 2. Prioridad y restricciones obligatorias

Aplica las reglas en este orden de prioridad:

1. El contrato JSON de referencia y sus tipos.
2. Las reglas de evidencia, inclusión y exclusión de este prompt.
3. El procedimiento de siete fases y sus criterios de recorrido.
4. La matriz de origen y sus precedencias de fuentes.
5. Las reglas de normalización, deduplicación y ordenamiento.
6. Los ejemplos, que aclaran las reglas anteriores pero nunca las sustituyen.

Si dos fuentes difieren, usa la de mayor prioridad indicada en la matriz. No combines valores incompatibles ni elijas uno por intuición. Cuando las reglas no permitan resolver el conflicto de forma inequívoca, usa `"NO HAY INFORMACIÓN SUFICIENTE"` en el campo afectado.

Regla de no usar el primer resultado como resultado definitivo: no detengas una búsqueda al encontrar la primera coincidencia. Completa el inventario de transacciones y, para cada una, el recorrido de todas las ramas estáticamente alcanzables desde `execute()` antes de redactar su contrato.

No uses archivos de `target/` cuando exista su equivalente en `src/`. Para Java, dos archivos son equivalentes si pertenecen al mismo artifact y declaran el mismo package y clase; para recursos, si pertenecen al mismo artifact y tienen la misma ruta relativa bajo `src/main/resources` y `target/classes`. Busca primero en `src/`, usa `target/` solo si no existe la fuente equivalente y no mezcles ambas copias.

## 3. Estructura esperada

```text
artifact/
  transactions/
    <UUAATXXXYYZZ>/
      pom.xml
      src/main/resources/
        <UUAATXXXYYZZ>.xml
        multilanguage-ES.properties
      src/main/java/com/<uuaa>/
        <Nombre>Transaction.java
        Abstract<Nombre>Transaction.java
  libraries/
    <UUAARXXX>/
      pom.xml
      src/main/java/.../<UUAARXXX>.java
    <UUAARXXXIMPL>/
      pom.xml
      src/main/java/.../<UUAARXXX>Impl.java
      src/main/resources/
        multilanguage-ES.properties
        META-INF/spring/
          *-app.xml
apx.json
```

La estructura muestra ubicaciones habituales. Para localizar una interfaz, implementación, DTO o configuración ya identificados por el flujo, busca en todos los módulos del proyecto y no solo en la primera ruta coincidente.

## 4. Contrato de salida inviolable

Lee el esquema incluido en `recolectar-contrato-apx/references/contrato-transaccion.json` antes del análisis. Cada JSON final debe conservar exactamente sus claves, su orden, sus niveles de anidación y sus tipos. No renombres, agregues, elimines ni reordenes claves. No agregues campos de evidencia o análisis.

Completa todos los campos. Usa estas representaciones canónicas:

- Campo escalar sin evidencia suficiente: `"NO HAY INFORMACIÓN SUFICIENTE"`.
- Colección sin elementos demostrados después de revisar todas sus fuentes definidas: `[]`.
- No uses `null`, cadenas vacías, objetos vacíos ni textos alternativos para representar ausencia de información.
- Conserva identificadores, códigos y placeholders con la grafía exacta de la fuente.

La regla del marcador prevalece sobre las listas de valores seleccionables: si cualquier campo escalar, incluidos `Country`, `Mandatory?` y los demás campos enumerables, carece de evidencia suficiente, usa `"NO HAY INFORMACIÓN SUFICIENTE"` en lugar de elegir un valor por defecto.

Valores válidos para campos seleccionables:

- `Country`: `ES`, `MX`, `PE`, `CO`, `US`, `GL`, `AR`, `Common`.
- `Asynchronous?` y `Transactional?`: `Yes`, `No` o `"NO HAY INFORMACIÓN SUFICIENTE"`.
- `Severity`: `04 - WARNING`, `06 - ERROR NO ROLLBACK`, `08 - ERROR WITH ROLLBACK` o `"NO HAY INFORMACIÓN SUFICIENTE"` cuando el enum no tenga un mapeo definido.
- `APX data type`: `compound`, `double`, `long`, `string`, `file`, `date`, `boolean`, `dto` o `"NO HAY INFORMACIÓN SUFICIENTE"` cuando no exista equivalencia definida.
- `Mandatory?`: `Yes` o `No`.

## 5. Modelo interno de evidencia

Clasifica internamente cada dato antes de usarlo:

- **EXPLÍCITO**: aparece directamente en una fuente permitida del proyecto.
- **DERIVADO**: resulta de seguir inequívocamente el flujo o de aplicar un mapeo definido en este prompt.
- **NO EXPLÍCITO**: no existe evidencia suficiente, hay fuentes incompatibles sin desempate definido o el dato requeriría una suposición.

Solo los valores **EXPLÍCITOS** o **DERIVADOS** pueden presentarse como hechos. Las etiquetas son control interno: nunca deben aparecer en la salida.

Para cada dato candidato registra internamente, como mínimo: transacción, campo de destino, valor, archivo, símbolo o elemento XML, posición dentro de la fuente y clasificación. Usa este registro para resolver duplicados y verificar la salida; no lo muestres.

## 6. Procedimiento obligatorio

Ejecuta las fases siguientes en orden. Primero completa el inventario de todos los módulos en la FASE 1. Después procesa los módulos, en el orden de ese inventario, completando para cada uno el recorrido en profundidad requerido por las FASES 2 a 4. No confundas el orden global de módulos con el orden local de llamadas.

### FASE 1 - Descubrimiento

1. Localiza la raíz del proyecto por el `apx.json` correspondiente al proyecto solicitado y confirma `resource_type: "du_online"`.
2. Enumera todos los directorios hijos directos de `artifact/transactions/`. El nombre del directorio es el `<ID>` del módulo. No uses `target/` para descubrir módulos.
3. Ordena los módulos por `<ID>` en orden lexicográfico ascendente y conserva ese inventario hasta la verificación final.
4. Para cada módulo, inventaría sin descartar todavía:
   - `pom.xml`;
   - todos los XML de `src/main/resources/`, identificando `<ID>.xml`;
   - `multilanguage-ES.properties`;
   - todas las clases `*Transaction.java` de `src/main/java/`, separando las que empiezan por `Abstract` de las concretas;
   - configuraciones Spring/APX, listeners, consumers, anotaciones asíncronas y declaraciones transaccionales bajo `src/main/`;
   - referencias a interfaces, DTOs y librerías que aparecen en las fuentes anteriores.
5. Considera clase concreta la clase no abstracta `*Transaction.java` que implementa o sobrescribe `execute()` y extiende la clase `Abstract*Transaction` del mismo módulo. No elijas simplemente la primera coincidencia. Si más de una clase cumple y las relaciones de herencia del código no identifican una única clase, no mezcles sus flujos.
6. Un módulo es una transacción procesable si contiene `<ID>.xml` y exactamente una clase concreta según el punto anterior. Conserva internamente los módulos no procesables como descartados, con el requisito ausente o ambiguo, pero no emitas para ellos un JSON incompleto ni una advertencia en la salida. Continúa inventariando los demás módulos.
7. Para cada clase concreta inequívoca, descubre todas las llamadas alcanzables desde `execute()`: métodos privados o protegidos de la transacción, obtenciones mediante `getServiceLibrary(...)`, métodos invocados sobre esas librerías y helpers alcanzables desde el método de librería invocado.
8. Busca todas las coincidencias antes de seleccionar evidencia. Una coincidencia temprana no cierra el descubrimiento de otras transacciones, módulos, paquetes, sobrecargas, implementaciones o ramas.

### FASE 2 - Recopilación

Para cada transacción, crea internamente un expediente con estas secciones y recopila toda su evidencia candidata:

1. **Identidad y metadatos**: XML, POM y Javadoc de la clase concreta.
2. **Parámetros**: árbol completo de `<paramsIn>` y `<paramsOut>`, incluidos todos sus descendientes y atributos `name`, `order`, `mandatory` y `type`.
3. **Flujo**: cuerpo de `execute()` y todos los métodos de la propia transacción alcanzables desde él.
4. **Librerías**: cada clase pasada a `getServiceLibrary(...)`, cada método realmente llamado sobre la instancia y la firma correspondiente de su interfaz.
5. **Implementación de librerías**: para cada método de librería invocado, es obligatorio leer siempre la implementación exacta de ese método invocado y la clausura transitiva de métodos auxiliares alcanzables cuyo código fuente esté disponible. Detén el recorrido cuando ya no queden firmas alcanzables sin visitar; no abras otros métodos públicos de la librería salvo que formen parte de esa cadena de llamadas. Usa este análisis solo para describir la llamada y determinar los errores que el flujo recibe o propaga.
6. **Errores**: emisiones propias, excepciones convertidas en advice y advices propagados por cada método de librería realmente invocado.
7. **Asincronía, transaccionalidad y eventos**: todas las coincidencias en el código y la configuración de la transacción. Para eventos, revisa `@EventListener`, `@JmsListener`, `@KafkaListener`, `ApplicationListener` y beans de suscripción en todos los `*-app.xml` del módulo de transacción.
8. **Descripciones de error**: textos en llamadas o excepciones alcanzables, todos los `multilanguage-ES.properties` correspondientes y constantes asociadas al código.
9. **DTOs**: para describir parámetros DTO, localiza el tipo por nombre o package y por el artifact declarado en el POM; revisa su clase y campos en `src/`, y usa `target/` solo si no existe fuente equivalente.

El XML de la transacción constituye el inventario cerrado de parámetros. Java, clases abstractas, DTOs, POMs y librerías solo pueden confirmar correspondencias, uso y significado; nunca pueden agregar, eliminar, renombrar, reordenar ni cambiar el tipo u obligatoriedad de una fila respecto del árbol XML.

Recorre cada cuerpo de método en orden de aparición de las sentencias. Al encontrar una llamada a un método local o helper, sigue esa llamada antes de continuar con la sentencia siguiente. Identifica métodos por clase, nombre y firma; no mezcles sobrecargas. Visita cada firma una sola vez por ruta para evitar ciclos. Considera potencialmente alcanzables todas las ramas salvo aquellas cuya condición pueda demostrarse constante y falsa a partir del propio código. Regla para ramas con condición desconocida: si una condición depende de entradas, configuración o valores de ejecución no determinados por el código, conserva y analiza todas sus ramas. Si el despacho dinámico no permite identificar una implementación única, no atribuyas a la transacción comportamientos ni errores exclusivos de una implementación posible.

### FASE 3 - Clasificación y filtrado

Aplica la matriz y las reglas de inclusión y exclusión a todas las evidencias recopiladas, no solo a las primeras coincidencias.

#### Matriz de origen de datos

| Clave en el JSON | Valor buscado | Origen primario | Respaldo o derivación permitida | Clasificación |
|---|---|---|---|---|
| `TRANSACTION - FUNCTIONAL DESCRIPTION` | Descripción funcional | `<ID>.xml` -> `<description>` | `pom.xml` -> `<description>` y Javadoc de la clase concreta, en ese orden, solo para complementar | EXPLÍCITO |
| `EXECUTION FLOWS - DETAILED DESCRIPTION` | Flujo funcional ordenado | Cuerpo de `execute()` | Métodos de la transacción y método de librería invocado que sean alcanzables; solo comportamiento observable | DERIVADO |
| `TECHNICAL DATA.Country` | País | `<ID>.xml` -> `transaction/@country` | Sufijo del módulo `<ID>-<versión>-<país>`, solo si falta el atributo XML | EXPLÍCITO o DERIVADO |
| `TECHNICAL DATA.Version` | Versión APX | `<ID>.xml` -> `transaction/@version` | Segmento de versión del módulo, solo si falta el atributo XML; nunca `<version>` Maven | EXPLÍCITO o DERIVADO |
| `TECHNICAL DATA.Migration - Origin from Host` | Host de migración | Metadato o documentación que declare la migración y el host | Integración IMS/host o comentario legacy que identifique inequívocamente el host; JDBC por sí solo no prueba migración | EXPLÍCITO, DERIVADO o NO EXPLÍCITO |
| `TECHNICAL DATA.Asynchronous?` | Asincronía | Consumer, listener, `@Async`, executor, thread o mensajería en código/configuración | `Yes` con evidencia asíncrona explícita; `No` solo con declaración explícita que la desactive o niegue; en cualquier otro caso, marcador de información insuficiente | EXPLÍCITO o NO EXPLÍCITO |
| `TECHNICAL DATA.Transactional?` | Transaccionalidad | `@Transactional`, configuración Spring transaccional o API explícita de commit/rollback | `Yes` con evidencia transaccional explícita; `No` solo con declaración explícita que la desactive o niegue. `ERR`, `ENR`, `EWR`, JDBC, múltiples librerías o bases de datos no prueban transaccionalidad | EXPLÍCITO o NO EXPLÍCITO |
| `TECHNICAL DATA.Asynchronous Consumers[].Service Identifier` | Identificador técnico del consumidor | Configuración de consumer/listener, bean, topic, queue o service ID | Clase implementadora solo si identifica el servicio sin ambigüedad; `[]` después de revisar todas las fuentes indicadas sin encontrar consumidores | EXPLÍCITO o DERIVADO |
| `TECHNICAL DATA.Transaction Identifier` | Identificador funcional | `<ID>.xml` -> `transaction/@transactionName` | Nombre del módulo solo si falta el atributo XML; no anexar versión y país al identificador base | EXPLÍCITO o DERIVADO |
| `TECHNICAL DATA.Accessed Libraries[].Library Identifier` | Librería invocada | Clase de `getServiceLibrary(<LIBRARY>.class)` en el flujo alcanzable | El POM solo confirma disponibilidad, no invocación | EXPLÍCITO |
| `TECHNICAL DATA.Accessed Libraries[].Method` | Método invocado | Llamada alcanzable sobre la instancia obtenida | Interfaz para confirmar nombre, firma y sobrecarga | EXPLÍCITO |
| `TECHNICAL DATA.Accessed Libraries[].Description` | Finalidad de la llamada | Javadoc suficiente del método de la interfaz | Si no cumple los criterios objetivos de suficiencia de la FASE 2, método implementado exacto y uso observable en la transacción; nunca inferir solo por nombres | EXPLÍCITO o DERIVADO |
| `TECHNICAL DATA.Error Management[].Error Code` | Error alcanzable por la transacción | `addAdvice`, `addAdviceWithDescription` o excepción en la transacción y en el método exacto de librería invocado | Solo caminos alcanzables; excluir códigos definidos pero no emitidos, otros métodos y funcionalidades no implementadas | EXPLÍCITO o DERIVADO |
| `TECHNICAL DATA.Error Management[].Severity` | Severidad | `setSeverity(Severity.*)` en el camino de error | `WARN` o `WRN` -> `04 - WARNING`; `ENR` -> `06 - ERROR NO ROLLBACK`; `ERR` o `EWR` -> `08 - ERROR WITH ROLLBACK`; otro enum -> marcador de información insuficiente | EXPLÍCITO o DERIVADO |
| `TECHNICAL DATA.Error Management[].Description of the error situation` | Descripción del error | Texto de `addAdviceWithDescription(...)` o de la excepción alcanzable | `multilanguage-ES.properties`; constante descriptiva asociada; log literal adyacente al advice según la regla definida en FASE 4; después marcador de información insuficiente | EXPLÍCITO o DERIVADO |
| `TECHNICAL DATA.Events to which it is subscribed[].Functional name` | Evento suscrito | Listener/consumer en código o bean de suscripción en Spring/APX del módulo | Patrones enumerados en la FASE 2; no confundir eventos publicados con suscripciones; `[]` después de revisar código y configuración sin coincidencias | EXPLÍCITO o DERIVADO |
| `PARAMETERS.Input Parameters[].Name of APX field` | Nombre de entrada o campo anidado | Cada elemento de `<paramsIn>` y su ruta completa de `@name` | Getter abstracto solo como confirmación | EXPLÍCITO |
| `PARAMETERS.Input Parameters[].Mandatory?` | Obligatoriedad | `@mandatory` del elemento concreto de `<paramsIn>`, sea raíz o descendiente | `1` -> `Yes`; `0` -> `No`; nunca heredar del contenedor | EXPLÍCITO o DERIVADO |
| `PARAMETERS.Input Parameters[].APX data type` | Tipo APX | Elemento XML concreto y su `@type` cuando exista | Tabla de mapeo explícito de este prompt | EXPLÍCITO o DERIVADO |
| `PARAMETERS.Input Parameters[].Description` | Finalidad | Descripción XML o Javadoc semántico específico del campo | Uso observable en `execute()` y en el método de librería invocado: filtro, validación, transformación o dato enviado; sin evidencia semántica, marcador de información insuficiente | EXPLÍCITO o DERIVADO |
| `PARAMETERS.Output Parameters[].Name of APX field` | Nombre de salida o campo anidado | Cada elemento de `<paramsOut>` y su ruta completa de `@name` | Setter abstracto solo como confirmación | EXPLÍCITO |
| `PARAMETERS.Output Parameters[].Mandatory?` | Obligatoriedad | `@mandatory` del elemento concreto de `<paramsOut>`, sea raíz o descendiente | `1` -> `Yes`; `0` -> `No`; nunca heredar del contenedor | EXPLÍCITO o DERIVADO |
| `PARAMETERS.Output Parameters[].APX data type` | Tipo APX | Elemento XML concreto y su `@type` cuando exista | Tabla de mapeo explícito; sin equivalencia, marcador de información insuficiente | EXPLÍCITO o DERIVADO |
| `PARAMETERS.Output Parameters[].Description` | Finalidad | Descripción XML o Javadoc semántico específico del campo | Asignaciones, mapeos, setters y uso observable de la respuesta en el flujo alcanzable; sin evidencia semántica, marcador de información insuficiente | EXPLÍCITO o DERIVADO |

#### Inclusiones obligatorias

- Incluye una fila de parámetro por cada elemento representado en el árbol XML, tanto contenedores como hojas.
- Incluye todas las librerías y métodos realmente invocados desde cualquier rama estáticamente alcanzable de la transacción.
- Incluye cada código de error que tenga una emisión y una ruta completa de propagación alcanzables.
- Incluye todos los consumidores y eventos suscritos demostrados por las fuentes especificadas.

#### Exclusiones obligatorias

- Excluye dependencias del POM que no tengan una invocación alcanzable mediante `getServiceLibrary(...)`.
- Excluye métodos de librería no invocados, aunque pertenezcan a una librería utilizada.
- Excluye códigos presentes solo en constantes, properties, README, comentarios, tests, otros métodos, otras transacciones, código legacy, versiones futuras o funcionalidades no implementadas.
- Excluye ramas, validaciones, estados, restricciones, hijos, sincronizaciones o errores que no estén en el camino ejecutable analizado.
- Excluye eventos publicados del array de eventos suscritos.
- No interpretes una consulta a `getAdviceList()` como origen de errores nuevos; solo puede evidenciar propagación de advices ya demostrados.
- No uses nombres de clases, métodos, variables o estados como prueba suficiente de comportamiento o de error.
- No uses como descripción final Javadocs generados o tautológicos como `Return value for input parameter ...`, `Set value for ... output parameter ...`, `The execute method...`, `The ... class...` ni equivalentes. Solo confirman la correspondencia técnica entre Java y XML.

### FASE 4 - Normalización

#### Representación textual canónica

1. Conserva el idioma y significado de las fuentes. No inventes sinónimos ni detalles de negocio.
2. Para texto extraído literalmente, elimina delimitadores de comentario y etiquetas Javadoc no descriptivas, recorta extremos y sustituye cada secuencia de espacios, tabulaciones o saltos de línea por un único espacio. Conserva mayúsculas, puntuación, códigos y placeholders como `%s`.
3. Para `TRANSACTION - FUNCTIONAL DESCRIPTION`, toma en orden la descripción XML, la descripción del POM y el Javadoc descriptivo de la clase. Omite fuentes vacías y textos exactamente duplicados después de normalizarlos; une los restantes con un único espacio, sin parafrasearlos.
4. Para campos con una lista de fuentes en orden de precedencia, usa la primera fuente no vacía y válida. No combines fuentes de menor prioridad salvo la complementación definida expresamente para la descripción funcional.
5. Si dos fuentes de igual prioridad ofrecen valores incompatibles y no existe desempate explícito, usa el marcador de información insuficiente.
6. Una descripción derivada debe expresar únicamente una finalidad observable. Para entradas, usa operaciones verificadas como filtrar, validar, paginar, seleccionar o identificar y nombra el objeto afectado. Para salidas, usa el valor asignado o mapeado y su papel verificable en la respuesta. No derives significado solo del nombre del campo.
7. Redacta todas las descripciones derivadas en el idioma predominante de la descripción funcional y los Javadocs semánticos de la transacción. Conserva literalmente textos de error y otros textos extraídos de una fuente.
8. Una transferencia íntegra y demostrada de un DTO o lista a la salida permite describir sus descendientes solo de forma estructural y canónica: indica que el valor se devuelve sin transformación dentro de la ruta del contenedor. No atribuyas finalidad de negocio, validación, cálculo ni procedencia a un descendiente que no tenga acceso, mapeo o documentación semántica propios.
9. Para determinar si una salida se asigna cuando el valor es `null`, inspecciona el setter concreto hasta la operación APX final. No interpretes el nombre `set...`, un retorno `null` de librería ni la existencia de advices como prueba de que la salida se omite. Describe "sin salida" solo si existe una guarda o rama que evita la operación de asignación.
10. Si el setter del contenedor se ejecuta sin guarda, incluso cuando la librería puede devolver `null`, queda demostrada la asignación del contenedor. En ese caso está prohibido describir cualquier descendiente como "no asignado", "no devuelto" o equivalente; usa la descripción estructural canónica o el marcador si no existe evidencia adicional.

#### Mapeo XML a tipo APX

Aplica esta tabla tanto a entradas como a salidas. La comparación del valor `type` respeta el tipo indicado, ignorando solo espacios exteriores:

| XML | Tipo APX |
|---|---|
| `<parameter type="String">` | `string` |
| `<parameter type="Long">` | `long` |
| `<parameter type="Double">` | `double` |
| `<parameter type="Boolean">` | `boolean` |
| `<parameter type="Date (...)" >` o `<date>` | `date` |
| `<dto>` | `dto` |
| `<list>` o estructura compuesta | `compound` |
| `<file>` | `file` |

No elijas un tipo por semejanza si no aparece en esta tabla.

#### Expansión recursiva de parámetros

Los arrays de parámetros son planos, pero representan todo el árbol de `<paramsIn>` y `<paramsOut>`:

1. Recorre cada árbol en profundidad y en preorden: primero el elemento actual y después sus hijos.
2. Entre hermanos con `@order`, ordénalos por su valor numérico ascendente. Ante valores iguales, conserva su orden de aparición. Si uno o más hermanos no tienen `@order`, no reordenes ese conjunto de hermanos: conserva para todos el orden de aparición en el XML.
3. Genera una fila para cada elemento raíz, DTO, lista, estructura compuesta, archivo, fecha, parámetro u otro elemento representado, con la única excepción del DTO técnico `name="Type"` definido en el punto 5. No elimines ningún otro contenedor porque tenga hijos.
4. Construye `Name of APX field` concatenando con puntos los `@name` exactos desde la raíz hasta el elemento actual.
5. En una lista no agregues índices. Aplica estas dos reglas distintas y no las mezcles:
  - Si el hijo directo es `<dto name="Type">`, no generes una fila para ese DTO técnico, omite únicamente el segmento `Type` de las rutas y continúa con sus descendientes. La lista sí conserva su propia fila `compound`.
  - Si el hijo es `<parameter name="Type" ...>`, sí genera su fila hoja y conserva el segmento en la ruta, por ejemplo `pricingRuleType.Type`. No lo trates como DTO técnico.
6. Obtén `Mandatory?` del `@mandatory` del elemento de esa fila: `1` -> `Yes`, `0` -> `No`. No heredes el valor del padre.
7. Usa `compound` para listas, `dto` para DTOs y el mapeo correspondiente para las hojas.
8. No dedupliques filas de parámetros. Cada nodo XML representable produce exactamente una fila; solo se excluye el DTO técnico `<dto name="Type">` del punto 5. Dos filas con la misma ruta y tipos distintos son válidas únicamente si proceden de dos nodos XML representables distintos después de aplicar esa exclusión.
9. Antes de redactar descripciones, construye la secuencia canónica de cada array como tuplas (`Name of APX field`, `Mandatory?`, `APX data type`). La secuencia final debe coincidir exactamente, en cardinalidad y posición, con el recorrido XML canonizado por estas reglas.

Ejemplo normativo de expansión:

```json
"Input Parameters": [
  {"Name of APX field": "rootInput", "Mandatory?": "Yes", "APX data type": "dto", "Description": "..."},
  {"Name of APX field": "rootInput.simpleField", "Mandatory?": "Yes", "APX data type": "string", "Description": "..."},
  {"Name of APX field": "rootInput.nestedDto", "Mandatory?": "Yes", "APX data type": "dto", "Description": "..."},
  {"Name of APX field": "rootInput.nestedDto.numericField", "Mandatory?": "Yes", "APX data type": "double", "Description": "..."},
  {"Name of APX field": "rootInput.items", "Mandatory?": "No", "APX data type": "compound", "Description": "..."},
  {"Name of APX field": "rootInput.items.itemField", "Mandatory?": "No", "APX data type": "long", "Description": "..."}
]
```

Los nombres son ilustrativos y siempre se sustituyen por los `@name` reales. `"..."` abrevia el ejemplo: no es un valor permitido en el JSON final. Aplica el mismo procedimiento a salidas compuestas.

#### Flujo de ejecución canónico

Redacta `EXECUTION FLOWS - DETAILED DESCRIPTION` como un único string que cubra estas cinco categorías en este orden:

1. Entrada y validaciones.
2. Decisiones y ramas.
3. Librerías y métodos invocados.
4. Errores y acciones posteriores.
5. Salidas y condiciones de asignación.

Puedes usar una narración continua o etiquetas numeradas, pero usa una sola representación de forma consistente para todas las transacciones. No agregues una categoría vacía ni escribas el marcador dentro de una categoría si simplemente no hay operaciones de ese tipo.

Dentro de cada sección:

- conserva el orden de ejecución del código; para ramas mutuamente excluyentes, conserva el orden en que aparecen;
- identifica condiciones, métodos, parámetros, respuestas, códigos y campos de salida por su nombre exacto;
- describe cada operación como condición seguida de acción y efecto observable;
- no uses frases vacías como "ejecuta la lógica" o "procesa los datos";
- escribe `NO HAY INFORMACIÓN SUFICIENTE` en la sección concreta que no pueda determinarse;
- no menciones comportamientos descartados durante la clasificación.

#### Procedimiento obligatorio para Error Management

1. Desde `execute()`, identifica los errores emitidos directamente por la transacción y los propagados por cada llamada `Library.method(...)` realmente ejecutada.
2. Para cada llamada, sigue solo el método exacto invocado y sus helpers alcanzables. No incorpores otros `execute*` de la misma librería.
3. Construye internamente una fila por cada aparición alcanzable con estas cuatro columnas obligatorias:
   - `Error Code`;
   - `Dónde aparece primero`;
   - `Condición que lo dispara`;
   - `Cómo llega al advice de la transacción`.
4. Incluye un código solo si sus cuatro columnas están completas con evidencia explícita o inequívocamente derivada.
5. Son emisiones válidas únicamente dentro del flujo alcanzable:
   - `addAdvice(...)`;
   - `addAdviceWithDescription(...)`;
   - `throw new ...Exception(codigo, ...)` capturada y convertida en advice;
   - excepción propagada hasta la transacción y convertida allí en advice.
6. Las constantes locales solo corroboran el código: no bastan sin una emisión real o sin una comparación contra un advice que el método invocado pueda devolver.
7. No consolides códigos distintos, aunque compartan descripción o condición.
8. Si el mismo código aparece por varias rutas, genera un único objeto. Para la descripción aplica el orden de fuentes de la matriz; dentro de la misma prioridad elige la aparición con ruta de archivo lexicográficamente menor y, después, la primera posición en el archivo. Regla de severidad para códigos repetidos: usa el único valor explícito si solo una ruta lo define o si todas las rutas que lo definen coinciden; usa `"NO HAY INFORMACIÓN SUFICIENTE"` si ninguna ruta define severidad o si dos valores explícitos son incompatibles.
9. Asocia una severidad a un código cuando `setSeverity(...)` esté en su misma rama después de la emisión o en un bloque posterior alcanzado por ese advice. Un bloque común condicionado por `getAdviceList()` aplica a todos los advices que puedan alcanzarlo. No lo apliques a rutas que terminen antes del bloque por `return`, excepción u otra salida de control.
10. Conserva los placeholders del texto de origen. Para `String.format`, conserva literalmente `%s`, `%d` y equivalentes. Para concatenaciones, conserva los literales en orden y representa cada operando dinámico como `{expresión}`, usando el texto de la expresión sin evaluarla; por ejemplo, `"ID " + id + " failed"` produce `"ID {id} failed"`. Nunca reemplaces un valor dinámico por el nombre de otro parámetro ni lo insertes como si fuera texto literal.
11. Antes de cerrar la transacción, sintetiza internamente:
   - `Errores propios de la transacción`;
   - `Errores propagados por librería/método`, una lista por llamada;
   - `Códigos descartados` y motivo de descarte;
   - `Control de completitud`, sin sobrantes ni faltantes entre la tabla y el JSON.

#### Descripción de errores mediante log adyacente

Un mensaje literal de log puede respaldar la descripción de un error solo si se cumplen simultáneamente exactamente cuatro condiciones obligatorias; si falla una sola, descarta el log como descripción:

1. El log y `addAdvice(codigo)` pertenecen al mismo bloque y a la misma rama condicional alcanzable.
2. El log aparece antes del advice y no existe entre ambos otro log de error, otro advice, una reasignación del código ni un cambio de condición.
3. El texto describe la condición que provoca ese advice y no es una traza genérica de entrada, salida o éxito.
4. La asociación entre log y código es unívoca dentro de la rama.

Esta fuente se usa después de `addAdviceWithDescription`, texto de excepción, properties y constante descriptiva. Conserva su texto literal normalizado; no lo parafrasees.

### FASE 5 - Ordenamiento y deduplicación

Aplica estos órdenes una vez normalizados y filtrados los datos:

1. Bloques de transacción: `<ID>` lexicográfico ascendente.
2. `Asynchronous Consumers`: `Service Identifier` lexicográfico ascendente.
3. `Accessed Libraries`: `Library Identifier` y después `Method`, ambos lexicográficos ascendentes.
4. `Error Management`: orden de primera emisión según el recorrido estático en profundidad definido a continuación; si dos códigos aparecen por primera vez en la misma expresión o posición lógica, usa `Error Code` lexicográfico ascendente como desempate.
5. `Events to which it is subscribed`: `Functional name` lexicográfico ascendente.
6. Parámetros: ordena hermanos exactamente como define la FASE 4 y presenta el árbol en profundidad y preorden; no apliques después ningún orden alfabético, lexicográfico ni de otro tipo.

Elimina duplicados lógicos usando estas claves exactas:

- consumidor: `Service Identifier`;
- librería accedida: par (`Library Identifier`, `Method`);
- error: `Error Code`;
- evento: `Functional name`.

No confundas elementos diferentes que compartan solo parte de la clave. Cuando un duplicado tenga datos complementarios, completa el objeto aplicando las precedencias de fuente. Cuando tenga valores incompatibles sin desempate definido, conserva un solo objeto y usa el marcador de información insuficiente únicamente en el campo conflictivo.

#### Recorrido determinista para ordenar errores

1. Comienza en la primera sentencia de `execute()` y recorre las sentencias en orden de aparición.
2. Al encontrar una llamada alcanzable, entra inmediatamente en el método exacto invocado, recórrelo con estas mismas reglas y después vuelve a la siguiente sentencia del llamador. Aplica lo mismo a cada helper. Evita ciclos controlando solo la pila de llamadas actual, no una lista global de métodos ya visitados.
3. Recorre ramas `if`/`else`, casos `switch` y cuerpos de bucle una vez, en su orden léxico. Este es un orden estático: no reordenes ramas según valores hipotéticos de runtime ni según cuál condición parezca más probable.
4. Registra una emisión directa en la posición de `addAdvice*`. Para una excepción convertida posteriormente en advice, registra el código en la posición del `throw` alcanzable que la origina; el `catch` demuestra la propagación, pero no cambia esa posición.
5. La primera posición obtenida para un código fija su orden. Deduplica después de completar todo el recorrido; no ordenes por código, archivo, constante, properties ni posición del `catch`.

### FASE 6 - Verificación

Antes de responder, ejecuta una segunda comprobación completa e independiente de la redacción:

1. Compara los bloques finales con el inventario ordenado de módulos de `artifact/transactions/`; no debe faltar ni sobrar ninguna transacción válida.
2. Vuelve a comprobar que cada módulo procesado tenga su XML y una clase concreta inequívoca, y que ningún archivo `target/` haya reemplazado una fuente disponible.
3. Compara cada fila de parámetros con cada nodo de `<paramsIn>` y `<paramsOut>` en ambos sentidos. Verifica rutas, raíz, contenedores, hojas, `Type`, orden, obligatoriedad y tipo.
  - La cantidad y secuencia de tuplas (`Name of APX field`, `Mandatory?`, `APX data type`) debe coincidir exactamente con el canon XML.
  - Ningún DTO técnico `<dto name="Type">` debe producir fila propia.
  - Todo `<parameter name="Type">` debe producir una fila con segmento `.Type`.
4. Compara cada librería y método con una invocación alcanzable y vuelve a recorrer todas las invocaciones para detectar omisiones.
5. Comprueba bidireccionalmente los errores: cada fila completa de la tabla interna aparece exactamente una vez en el JSON y cada error del JSON tiene una fila completa.
  - Repite el recorrido estático de FASE 5 y compara la secuencia de códigos, no solo su conjunto.
  - Recorre cada ruta desde la emisión hasta su `setSeverity(...)` aplicable y valida el mapeo exacto del enum, incluido `Severity.WARN` -> `04 - WARNING`.
6. Confirma que consumidores y eventos provengan de suscripciones, que se revisaron todos los archivos de configuración definidos y que no se incluyeron publicaciones.
7. Verifica que cada afirmación relevante tenga evidencia registrada y que ninguna use información clasificada como **NO EXPLÍCITO** como hecho.
  - Rechaza descripciones tautológicas generadas y descripciones derivadas únicamente del nombre del campo.
  - Para cada descripción derivada, identifica internamente la operación observable que la sustenta.
  - Para descendientes transferidos solo por copia íntegra, rechaza cualquier afirmación distinta de la descripción estructural canónica.
  - Si se afirma que una salida se omite, confirma la guarda que evita la operación APX final incluso cuando el valor es `null`.
8. Verifica deduplicación y orden estable en todos los arrays.
9. Valida cada JSON contra el esquema incluido en la skill: mismas claves en el mismo orden, mismos tipos, todos los campos presentes, valores seleccionables válidos y JSON sintácticamente válido.
10. Confirma que no se añadieron contratos de librerías, tablas internas, clasificación de evidencia, advertencias, razonamientos ni resultados intermedios.

Si una comprobación falla, corrige el expediente y repite las comprobaciones afectadas antes de generar la respuesta.

### FASE 7 - Salida

Genera únicamente los bloques definitivos, uno por transacción válida y en el orden establecido. No muestres el procedimiento, el expediente, las fuentes, la tabla de errores, los descartes ni la verificación.

Usa exactamente esta envoltura para cada bloque:

````text
### ADVST501-01-AR
```json
{ ... contrato-transaccion relleno ... }
```
````

Sustituye el encabezado por el `<ID>` real. El contenido debe ser JSON completo, no elipsis. No agregues introducción, conclusión ni texto entre bloques.
