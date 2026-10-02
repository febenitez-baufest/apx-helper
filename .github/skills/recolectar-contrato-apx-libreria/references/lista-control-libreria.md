# Lista de control final (librería Tipo B)

Marca cada punto antes de entregar. Si uno falla, corrige y vuelve a ejecutar `validate_lib.py`.

- [ ] `validate_lib.py` termina con `RESULTADO <LIBRARY_ID>: OK`.
- [ ] No queda ningún `__TODO__`.
- [ ] Cada `AVISO` fue corregido o tiene una línea del expediente que lo justifica.
- [ ] `EXECUTE - METHODS SUMMARY` contiene exactamente los métodos públicos de la interfaz, en su mismo orden; ninguno falta ni sobra.
- [ ] `Visibility` es `"Public"` en todos los casos.
- [ ] El esquema de `Error Management` de librería **no** tiene campo `Severity`: no lo añadiste.
- [ ] Cada `Error Management` por método contiene exactamente los códigos alcanzables desde ese método (sección 6 del expediente), en su orden DFS.
- [ ] Cada descripción de error es literal (de `addAdviceWithDescription`, excepción, `multilanguage-ES.properties` o Javadoc de la constante), sin traducir ni parafrasear.
- [ ] Ninguna descripción (`Brief description`, `DESCRIPTION OF THE FUNCTIONALITY`, parámetros, librerías) es tautológica ni repite solo el nombre del método/campo.
- [ ] `Accessed libraries` de cada método coincide con las llamadas `getServiceLibrary(...)` realmente alcanzables desde ese método (no desde otros métodos de la misma librería).
- [ ] `Other accesses` cita el bean real de `*-arc.xml` y, para `Proxy Service`, el `Identifier` es el valor de la propiedad APX (no el id del bean Spring).
- [ ] Los parámetros de salida de un método `void` son `[]`.
- [ ] Los campos de DTO sin fuente disponible en el repositorio quedan con el marcador o una cita exacta del Javadoc de la interfaz, nunca con una suposición de negocio.
- [ ] `Library Type` tiene evidencia real de dependencias online/batch del propio módulo, no de las propiedades genéricas del POM agregador.
- [ ] El archivo se escribió con la herramienta de edición, sin PowerShell.
