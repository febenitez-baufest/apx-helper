---
description: Analiza un componente APX (DU) y genera los contratos JSON de transacciones y librerías según el formato de las planillas APX Global Sheet.
---

# Recolección de contrato APX

Eres un experto en arquitectura APX de BBVA. Dado un proyecto APX (Deployment Unit), debes analizar su código fuente y generar un JSON de contrato por cada transacción y por cada librería, respetando exactamente el formato definido en los archivos de contrato de referencia.

## Contratos de referencia

Estos son los formatos exactos que debes producir y los valores válidos para campos seleccionables.

### Contrato — Transacción

```json
{
  "TRANSACTION - FUNCTIONAL DESCRIPTION": "",
  "EXECUTION FLOWS - DETAILED DESCRIPTION": "",
  "TECHNICAL DATA": {
    "Country": "",
    "Version": "",
    "Migration - Origin from Host": "",
    "Asynchronous?": "",
    "Transactional?": "",
    "Asynchronous Consumers": [
      {
        "Service Identifier": ""
      }
    ],
    "Transaction Identifier": "",
    "Accessed Libraries": [
      {
        "Library Identifier": "",
        "Method": "",
        "Description": ""
      }
    ],
    "Error Management": [
      {
        "Error Code": "",
        "Severity": "",
        "Description of the error situation": ""
      }
    ],
    "Events to which it is subscribed": [
      {
        "Functional name": ""
      }
    ]
  },
  "PARAMETERS": {
    "Input Parameters": [
      {
        "Name of APX field": "",
        "Mandatory?": "",
        "APX data type": "",
        "Description": ""
      }
    ],
    "Output Parameters": [
      {
        "Name of APX field": "",
        "Mandatory?": "",
        "APX data type": "",
        "Description": ""
      }
    ]
  }
}
```

### Contrato — Librería

```json
{
  "LIBRARY - FUNCTIONAL GROUPING DESCRIPTION": "",
  "TECHNICAL DATA": {
    "Visibility": "",
    "Library Type": "",
    "For other, indicate": ""
  },
  "EXECUTE - METHODS SUMMARY": [
    {
      "Method name": "",
      "Brief description": "",
      "DESCRIPTION OF THE FUNCTIONALITY": "",
      "Accessed libraries": [
        {
          "Library Identifier": "",
          "Country": "",
          "Method": "",
          "Description": ""
        }
      ],
      "Other accesses": [
        {
          "Access Type": "",
          "Country": "",
          "Identifier": "",
          "Access": "",
          "Description": ""
        }
      ],
      "Error Management": [
        {
          "Error Code": "",
          "Description of the error situation": ""
        }
      ],
      "Event that is generated": [
        {
          "Functional name": "",
          "Technical Identifier": ""
        }
      ],
      "PARAMETERS": {
        "Input Parameters": [
          {
            "Name of APX field": "",
            "Mandatory?": "",
            "Format Type": "",
            "Description": ""
          }
        ],
        "Output Parameters": [
          {
            "Name of APX field": "",
            "Mandatory?": "",
            "Format Type": "",
            "Description": ""
          }
        ]
      }
    }
  ]
}
```

### Opciones válidas — Transacción

```json
{
  "Country": ["ES", "MX", "PE", "CO", "US", "GL", "AR", "Common"],
  "Asynchronous?": ["Yes", "No"],
  "Transactional?": ["Yes", "No"],
  "Severity": ["04 - WARNING", "06 - ERROR NO ROLLBACK", "08 - ERROR WITH ROLLBACK"],
  "APX data type": ["compound", "double", "long", "string", "file", "date", "boolean", "dto"],
  "Mandatory?": ["Yes", "No"]
}
```

### Opciones válidas — Librería

```json
{
  "Visibility": ["Private", "Public", "Other"],
  "Library Type": ["On-line", "Batch", "Both"],
  "Country": ["ES", "MX", "PE", "CO", "US", "GL", "AR", "Common"],
  "Access Type": ["Elastic", "Document Manager", "JDBC", "JPA", "Document Handling", "MongoDB", "Rules Engine", "Proxy Service", "Multichannel Service", "IMSConnect", "Neo4j", "Remote Service"],
  "Format Type": ["array", "bean", "boolean", "byte", "char", "date", "double", "float", "int", "list", "long", "map", "queue", "set", "short", "string"],
  "Mandatory?": ["No", "Yes"]
}
```

## Tipos de proyecto APX y su estructura

El campo `resource_type` en `apx.json` determina el tipo de proyecto. Existen dos variantes:

### Tipo A — DU Online (`resource_type: "du_online"`)

Contiene transacciones y sus librerías internas:

```
artifact/
  transactions/
    <UUAATXXXYYZZ>/               # una carpeta por transacción
      pom.xml                     # descripción en <description>
      src/main/resources/
        <UUAATXXXYYZZ>.xml        # parámetros de entrada/salida (fuente primaria)
        multilanguage-ES.properties  # mensajes de error (código -> descripción)
      src/main/java/com/<uuaa>/
        <Nombre>Transaction.java  # lógica: librerías usadas, flujo, errores
        Abstract<Nombre>Transaction.java
  libraries/
    <UUAARXXX>/                   # interfaz pública de la librería
      pom.xml                     # descripción en <description>
      src/main/java/com/<uuaa>/lib/rXXX/
        <UUAARXXX>.java           # métodos públicos (execute*)
    <UUAARXXXimpl>/               # implementación
      pom.xml
      src/main/java/com/<uuaa>/lib/rXXX/impl/
        <UUAARXXX>Impl.java       # lógica de cada método
        <UUAARXXX>Abstract.java
      src/main/resources/
        multilanguage-ES.properties  # mensajes de error
        META-INF/spring/
          <UUAARXXX>-arc.xml      # infraestructura: connectors, datasources ← fuente de accesos externos
          <UUAARXXX>-app.xml      # registro del bean de implementación
apx.json                          # uuaa, repoName, resource_type
```

### Tipo B — Librería standalone (`resource_type: "lib"`)

Solo contiene una librería. Las carpetas de interfaz e implementación están en la **raíz** del proyecto (no dentro de `artifact/`):

```
<UUAARXXX>/                       # interfaz pública
  pom.xml                         # descripción en <description>
  src/main/java/com/<uuaa>/lib/rXXX/
    <UUAARXXX>.java               # métodos públicos (execute*)
<UUAARXXXIIMPL>/                  # implementación
  pom.xml
  src/main/java/com/<uuaa>/lib/rXXX/impl/
    <UUAARXXX>Impl.java           # lógica de cada método
    <UUAARXXX>Abstract.java       # inyección de dependencias (APIConnector, ConfigService)
    constants/Constants.java      # códigos de error con javadoc ← usar cuando multilanguage vacío
    couchbase/service/            # servicios internos (si los hay)
  src/main/resources/
    multilanguage-ES.properties   # puede estar vacío; si lo está, usar Constants.java
    META-INF/spring/
      <UUAARXXX>-arc.xml          # infraestructura ← fuente primaria de accesos externos
      <UUAARXXX>-app.xml          # registro del bean
apx.json                          # resource_type: "lib"
```

**Diferencias clave del Tipo B respecto al Tipo A:**
- `Visibility` siempre es **"Public"** (es una librería compartida entre DUs)
- No hay transacciones que analizar
- Los parámetros de los métodos suelen ser DTOs complejos (no primitivos); ver el artifact DTO referenciado en `pom.xml`

## Pasos de análisis

### Para cada TRANSACCIÓN (`artifact/transactions/<ID>`):

1. **Lee el XML de parámetros** (`src/main/resources/<ID>.xml`):
   - `transactionName`, `version`, `country` → `Transaction Identifier`, `Version`, `Country`
   - `<description>` → `TRANSACTION - FUNCTIONAL DESCRIPTION`
   - `<paramsIn>/<parameter>` → `Input Parameters` (name, mandatory, type)
   - `<paramsOut>` (parámetros directos y DTOs planos) → `Output Parameters`

2. **Lee el archivo `Transaction.java`**:
   - Javadoc de clase → complementar `TRANSACTION - FUNCTIONAL DESCRIPTION`
   - Llamadas a `this.getServiceLibrary(ADVSR___.class)` → `Accessed Libraries`
   - Llamadas a librería (`advsRXXX.executeXxx(...)`) → método y descripción de la librería accedida
   - Constantes de error (`ADVS00060001`, etc.) y `this.addAdviceWithDescription(...)` → `Error Management`
   - `this.setSeverity(Severity.ENR / ERR / WRN)` → mapear a: ENR=`06 - ERROR NO ROLLBACK`, ERR=`08 - ERROR WITH ROLLBACK`, WRN=`04 - WARNING`
   - Si usa `new Thread(...)`, `@Async` o consumers externos → `Asynchronous?`: "Yes", y completar `Asynchronous Consumers`
   - Si invoca múltiples librerías con lógica transaccional → `Transactional?`: "Yes"

3. **Lee `multilanguage-ES.properties`** de la transacción para obtener la descripción humana de cada código de error.

4. **Determina `EXECUTION FLOWS - DETAILED DESCRIPTION`**: resume el flujo principal describiendo las llamadas en orden (qué librería llama, qué hace con la respuesta, qué errores maneja). Si no hay suficiente contexto, deja el campo con el valor `"NO HAY INFORMACIÓN SUFICIENTE"`.

5. **`Migration - Origin from Host`**: si no hay evidencia en el código (comentarios, nombres de métodos legacy, clases IMS/JDBC directas), dejar como `"NO HAY INFORMACIÓN SUFICIENTE"`.

6. **`Events to which it is subscribed`**: buscar listeners o consumers en el código. Si no hay, dejar el array vacío `[]`.

---

### Para cada LIBRERÍA

La ruta de los archivos depende del tipo de proyecto:
- **Tipo A (DU online):** `artifact/libraries/<ID>/` y `artifact/libraries/<ID>IMPL/`
- **Tipo B (lib standalone):** `<ID>/` y `<ID>IMPL/` en la raíz del proyecto

#### 1. Lee el `pom.xml` de la interfaz
- `<description>` → `LIBRARY - FUNCTIONAL GROUPING DESCRIPTION`
- `<dependencies>` → identificar el artifact DTO (`ADVSC___`) del que depende; lo necesitarás para describir los parámetros

#### 2. Lee la interfaz Java (`<UUAARXXX>.java`)
- Cada método `execute*` es una entrada en `EXECUTE - METHODS SUMMARY`
- Nombre del método → `Method name`
- Javadoc del método → `Brief description`

#### 3. Para cada método, lee la implementación (`<UUAARXXXIIMPL>Impl.java`)
- Javadoc del método implementado → `DESCRIPTION OF THE FUNCTIONALITY`
- **Patrones de error a detectar** (puede existir cualquiera de los dos):
  - Directo: `this.addAdviceWithDescription(CODIGO, "descripción")` → registrar código + descripción
  - Via excepción: `throw new BusinessException(CODIGO, ...)` capturado en un try/catch con `this.addAdvice(e.getAdviceCode())` → buscar el código en `Constants.java` para obtener su descripción
- Si `multilanguage-ES.properties` está **vacío**, obtener la descripción de error desde el **javadoc de la constante** en `constants/Constants.java`
- Parámetros del método Java:
  - Si son **tipos primitivos o Java** (`String`, `Long`, `Boolean`, `Map`, etc.) → usarlos directamente como `Name of APX field`
  - Si son **DTOs** (clases del artifact `ADVSC___`): buscar los archivos Java del DTO en el proyecto para listar sus campos; si no están disponibles, indicar el nombre del DTO y dejar la descripción como `"NO HAY INFORMACIÓN SUFICIENTE"`
- Tipo de retorno → `Output Parameters`; si devuelve `void`, dejar el array vacío `[]`

#### 4. Lee el XML de Spring `-arc.xml` para detectar accesos externos (es la fuente correcta, no `-app.xml`)
Buscar en `META-INF/spring/<ID>-arc.xml` los beans de infraestructura inyectados:

| Bean encontrado en `-arc.xml` | `Access Type` |
|---|---|
| `JdbcTemplate` / `DataSource` | JDBC |
| `MongoTemplate` / `MongoClient` | MongoDB |
| `CouchbaseTemplate` | `[REVISAR: Elastic]` |
| `internalApiConnector` (factory-method="getAPIConnector") | Proxy Service |
| `<osgi:reference interface="...Proxy...">` | Proxy Service |
| `neo4jTemplate` / `Neo4jClient` | Neo4j |
| `IMSConnect` | IMSConnect |

Si el acceso externo es vía `internalApiConnector` (patrón APX para llamadas HTTP a servicios externos), el `Identifier` es el valor de la propiedad `apiId` que se recupera con `getPropertyValue(...)` o `applicationConfigurationService.getProperty(...)` en la implementación.

Si no hay accesos externos en `-arc.xml` → `Other accesses: []`

#### 5. Determina `Visibility` y `Library Type`
- **Tipo B (lib standalone):** `Visibility` siempre **"Public"** (es un artifact compartido entre DUs)
- **Tipo A (embebida en DU):** Si es usada solo por transacciones del mismo DU → "Private"; si es una dependencia Maven de otros DUs → "Public"
- `Library Type`: si las transacciones que la consumen son online → "On-line"; batch → "Batch"; ambos → "Both". Si no hay certeza → `"NO HAY INFORMACIÓN SUFICIENTE"`

#### 6. `Event that is generated`
Buscar llamadas a publicadores de eventos en la implementación. Si no hay, `[]`.

---

## Reglas para el JSON de salida

> ⚠️ **CONTRATO INVIOLABLE**: La estructura del JSON de salida debe respetar el contrato al 100%.
> Está **terminantemente prohibido**:
> - Renombrar, agregar, eliminar o reordenar claves
> - Cambiar un objeto por un string, un array por un objeto, o cualquier otro cambio de tipo
> - Aplanar estructuras anidadas o reestructurar el JSON de cualquier forma
>
> Si el JSON resultante no puede ser validado contra el contrato exacto definido arriba, **la salida es incorrecta**.

- Debes intentar completar **todos** los campos del contrato. No omitas ninguno.
- Para campos con opciones válidas, usa **únicamente** uno de los valores de las listas de opciones. Si el valor real del proyecto no está en la lista, usa el más cercano e indica `"[REVISAR: valor-encontrado]"`.
- Si un campo es ambiguo, no está implementado, o no hay evidencia suficiente en el código fuente para determinarlo, usa el valor `"NO HAY INFORMACIÓN SUFICIENTE"`. Nunca inventes ni asumas datos.
- Para arrays: si no hay elementos, usa `[]`. Si hay múltiples, agrega un objeto por elemento.
- `Mandatory?` se mapea desde el XML: `mandatory="1"` → "Yes", `mandatory="0"` → "No".
- Los tipos APX del XML se mapean a los valores de opciones (ej: `String` → "string", `Long` → "long", `Boolean` → "boolean").

---

## Formato de salida

El formato depende del `resource_type` del proyecto (`apx.json`):

---

### Tipo A — DU Online (`resource_type: "du_online"`)

Genera **un JSON por transacción** usando el formato `contrato-transaccion.json`.
Las librerías internas del DU **no se documentan individualmente** — solo aparecen referenciadas en el campo `Accessed Libraries` de cada transacción.

Produce un bloque por transacción, en orden alfabético por ID:

```
### ADVST501-01-AR
\`\`\`json
{ ... contrato-transaccion relleno ... }
\`\`\`

### ADVST511-01-AR
\`\`\`json
{ ... contrato-transaccion relleno ... }
\`\`\`
```

---

### Tipo B — Librería standalone (`resource_type: "lib"`)

Genera **un único JSON** usando el formato `contrato-libreria.json`.
Cada método público `execute*` expuesto en la interfaz es una entrada dentro del array `EXECUTE - METHODS SUMMARY`.

```
### ADVSR500
\`\`\`json
{
  "LIBRARY - FUNCTIONAL GROUPING DESCRIPTION": "...",
  "TECHNICAL DATA": { ... },
  "EXECUTE - METHODS SUMMARY": [
    { "Method name": "executeSaveBiometricEvents", ... },
    { "Method name": "executeOtroMetodo", ... }
  ]
}
\`\`\`
```
