---
description: Analiza una librería APX standalone y genera su contrato JSON según el formato de las planillas APX Global Sheet.
---

# Recolección de contrato APX — Tipo B

Eres un experto en arquitectura APX de BBVA. Dado un proyecto APX de tipo `lib`, analiza la librería y genera un único JSON de contrato respetando exactamente el formato definido en `contrato\contrato-libreria.json`.

No analices transacciones. Este prompt se trabajará de forma independiente del prompt de transacciones Tipo A.

## Tipo B — Librería standalone (`resource_type: "lib"`)

Solo contiene una librería. Las carpetas de interfaz e implementación están en la raíz del proyecto:

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

**Diferencias clave del Tipo B:**
- `Visibility` siempre es **"Public"** (es una librería compartida entre DUs)
- No hay transacciones que analizar
- Los parámetros de los métodos suelen ser DTOs complejos (no primitivos); ver el artifact DTO referenciado en `pom.xml`

## Pasos de análisis

### 1. Lee el `pom.xml` de la interfaz

- `<artifactId>` (o el nombre de la carpeta de la interfaz, p. ej. `ADVSR500`) → `Library Identifier`
- `<description>` → `LIBRARY - FUNCTIONAL GROUPING DESCRIPTION`
- `<dependencies>` → identificar el artifact DTO (`ADVSC___`) del que depende; lo necesitarás para describir los parámetros

### 2. Lee la interfaz Java (`<UUAARXXX>.java`)

- Cada método `execute*` es una entrada en `EXECUTE - METHODS SUMMARY`
- Nombre del método → `Method name`
- Javadoc del método → `Brief description`

### 3. Para cada método, lee la implementación (`<UUAARXXXIIMPL>Impl.java`)

- Javadoc del método implementado → `DESCRIPTION OF THE FUNCTIONALITY`
- **Patrones de error a detectar** (puede existir cualquiera de los dos):
  - Directo: `this.addAdviceWithDescription(CODIGO, "descripción")` → registrar código + descripción
  - Via excepción: `throw new BusinessException(CODIGO, ...)` capturado en un try/catch con `this.addAdvice(e.getAdviceCode())` → buscar el código en `Constants.java` para obtener su descripción
- Si `multilanguage-ES.properties` está **vacío**, obtener la descripción de error desde el **javadoc de la constante** en `constants/Constants.java`
- Parámetros del método Java:
  - Si son **tipos primitivos o Java** (`String`, `Long`, `Boolean`, `Map`, etc.) → usarlos directamente como `Name of APX field`
  - Si son **DTOs** (clases del artifact `ADVSC___`): buscar los archivos Java del DTO en el proyecto para listar sus campos; si no están disponibles, indicar el nombre del DTO y dejar la descripción como `"NO HAY INFORMACIÓN SUFICIENTE"`
- Tipo de retorno → `Output Parameters`; si devuelve `void`, dejar el array vacío `[]`

### 4. Lee el XML de Spring `-arc.xml` para detectar accesos externos (es la fuente correcta, no `-app.xml`)

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

### 5. Determina `Visibility` y `Library Type`

- **Tipo B (lib standalone):** `Visibility` siempre **"Public"** (es un artifact compartido entre DUs)
- **Tipo A (embebida en DU):** Si es usada solo por transacciones del mismo DU → "Private"; si es una dependencia Maven de otros DUs → "Public"
- `Library Type`: si las transacciones que la consumen son online → "On-line"; batch → "Batch"; ambos → "Both". Si no hay certeza → `"NO HAY INFORMACIÓN SUFICIENTE"`

### 6. `Event that is generated`

Buscar llamadas a publicadores de eventos en la implementación. Si no hay, `[]`.

## Reglas para el JSON de salida

> **CONTRATO INVIOLABLE:** La estructura del JSON de salida debe respetar el contrato al 100%.

- Usa exactamente las claves, tipos y estructuras de `contrato\contrato-libreria.json`.
- No renombres, agregues, elimines ni reordenes claves.
- Debes intentar completar todos los campos del contrato.
- Si un campo es ambiguo o no hay evidencia suficiente, usa `"NO HAY INFORMACIÓN SUFICIENTE"`; para arrays sin elementos demostrados, usa `[]`.
- Para campos con opciones válidas, usa únicamente los valores definidos en el contrato. Si el valor real no está disponible, usa `"NO HAY INFORMACIÓN SUFICIENTE"`.

## Formato de salida

Genera un único JSON para la librería:

```
### ADVSR500
```json
{
  "LIBRARY - FUNCTIONAL GROUPING DESCRIPTION": "...",
  "TECHNICAL DATA": { ... },
  "EXECUTE - METHODS SUMMARY": [
    { "Method name": "executeSaveBiometricEvents", ... }
  ]
}
```
```
