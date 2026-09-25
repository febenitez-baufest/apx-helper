# Análisis del prompt tipo A

## Alcance

Se ajustó `Mejoras/recolectar-contrato-apx-tipo-a.prompt.md` y se generó un contrato JSON independiente para cada transacción vigente de `ud-pricing-rules`, usando las fuentes actuales del repositorio.

Reglas reforzadas:

- El XML es el inventario cerrado de parámetros.
- Se omite el DTO técnico `<dto name="Type">`, pero se conserva `<parameter name="Type">` como ruta `.Type`.
- Los Javadocs generados y tautológicos no son descripciones funcionales.
- `Severity.WARN` se mapea a `04 - WARNING`.
- El orden de errores usa un recorrido estático determinista en profundidad.
- Los logs adyacentes solo respaldan errores bajo cuatro condiciones acumulativas.
- Las concatenaciones dinámicas conservan la expresión, por ejemplo `{id}`.
- Un setter de salida sin guarda demuestra la asignación del contenedor incluso con valor `null`.
- La copia íntegra de DTOs solo permite descripciones estructurales de descendientes sin evidencia propia.
- No se infieren asincronía ni transaccionalidad por JDBC, nombres o ausencia de anotaciones.

## Validación estructural

El auditor reproducible `app/tools/audit_generated_transactions.py` comparó cada JSON con su XML homónimo, en secuencia, usando las tuplas `Name of APX field`, `Mandatory?` y `APX data type`.

Resultado final: **8/8 contratos correctos; 16/16 listas de parámetros correctas**.

| Transacción | Entradas | Salidas | Resultado |
|---|---:|---:|---|
| ABKOT000-01-AR | 15/15 | 46/46 | PASS |
| ABKOT001-01-AR | 18/18 | 21/21 | PASS |
| ABKOT002-01-AR | 1/1 | 40/40 | PASS |
| ABKOT003-01-AR | 1/1 | 0/0 | PASS |
| ABKOT004-01-AR | 19/19 | 21/21 | PASS |
| ABKOT005-01-AR | 1/1 | 21/21 | PASS |
| ABKOT006-01-AR | 1/1 | 21/21 | PASS |
| ABKOT060-01-AR | 19/19 | 22/22 | PASS |

## Auditoría semántica final

- **ABKOT000-01-AR: correcto.** Severity WARN correctamente documentada como `04 - WARNING`; filtros, librería y errores respaldados.
- **ABKOT001-01-AR: correcto.** Flujo de alta, validaciones, severidades y defaults respaldados.
- **ABKOT002-01-AR: correcto.** La salida se asigna sin guarda; sus descendientes usan descripción estructural y no se declaran como no asignados.
- **ABKOT003-01-AR: correcto.** Errores en orden DFS estático: `ABKO10000405`, `ABKO10000410`, `ABKO10000409`, `ABKO00000010`.
- **ABKOT004-01-AR: correcto.** Se corrigió la afirmación de “sin respuesta”; el setter se ejecuta sin guarda y las descripciones sin evidencia propia son estructurales.
- **ABKOT005-01-AR: correcto.** Flujo de aprobación y salida respaldados.
- **ABKOT006-01-AR: correcto.** Error dinámico representado con `{id}`, orden DFS y severidad respaldados.
- **ABKOT060-01-AR: correcto.** Flujo masivo, errores y mapeos respaldados.

En todos los contratos, `Migration - Origin from Host`, `Asynchronous?` y `Transactional?` permanecen como `NO HAY INFORMACIÓN SUFICIENTE` cuando no existe evidencia explícita.

## Comparación de ABKOT000

- `Json generados/prompt-01-180926/prueba6.json` ya coincidía estructuralmente con el XML actualizado: 15 entradas y 46 salidas, incluyendo `pricingRuleType.Type` y `pricingRuleStatus.Type`.
- `Json generados/prueba1.json` tenía 15 entradas y 51 salidas, duplicaba las rutas de listas primitivas y conservaba DTOs técnicos `Type`; además dejaba severidades y descripciones con marcadores.
- El resultado nuevo `ABKOT000-01-AR.json` conserva el comportamiento correcto del resultado anterior, pero añade reglas verificables para evitar esas regresiones en las ocho transacciones.

## Conclusión

El prompt ajustado mejora el resultado anterior en determinismo y verificabilidad sin cambiar el objetivo funcional. La estructura de los ocho JSON coincide con los contratos XML vigentes y la auditoría semántica final no dejó hallazgos abiertos.
