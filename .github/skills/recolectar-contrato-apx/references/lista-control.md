# Lista de control final

Marca cada punto antes de entregar. Si uno falla, corrige y vuelve a ejecutar `validate.py`.

- [ ] `validate.py` termina con `RESULTADO <ID>: OK`.
- [ ] No queda ningún `__TODO__`.
- [ ] Cada `AVISO` fue corregido o tiene una línea del expediente que lo justifica.
- [ ] `Error Management` contiene exactamente los códigos de la sección 5 del expediente (salvo omisiones demostradas), en su orden.
- [ ] Cada descripción de error es literal (o la candidata normalizada con `%s` / `{expr}`), sin traducir ni parafrasear.
- [ ] Cada severidad sale de un `setSeverity` que alcanza ese advice.
- [ ] Ninguna descripción de parámetro es tautológica, repite solo el nombre o inventa negocio.
- [ ] Los descendientes copiados en bloque usan la frase canónica `Returned without transformation inside <ruta>.` solo si llegan poblados; los que el mapper no rellena usan `Not populated by ...`.
- [ ] Ningún campo con accesor no trivial (sección 8) se describe como "without transformation".
- [ ] Los campos no poblados se describen como `null`, no "empty", salvo inicializador.
- [ ] Ninguna entrada no leída queda con marcador: usa `Received inside ... but not read or persisted by the reachable flow.`
- [ ] Ninguna rama `getX() == null` sobre un getter con default se describe como comportamiento.
- [ ] Ninguna salida menciona un default que solo existe en los parámetros SQL.
- [ ] Cada salida con mapeo nombra su columna o campo de origen.
- [ ] El punto 4 del flujo da, para cada código, su condición y el método que lo lanza.
- [ ] Cada paso del punto 3 del flujo está atribuido al método que realmente lo ejecuta.
- [ ] Ninguna salida se declara "no asignada" si su setter se ejecuta sin guarda.
- [ ] El flujo usa las cinco etiquetas fijas y menciona todas las librerías, códigos y setters.
- [ ] `Asynchronous?` / `Transactional?` = marcador salvo evidencia en la sección 6.
- [ ] El archivo se escribió con la herramienta de edición, sin PowerShell.
