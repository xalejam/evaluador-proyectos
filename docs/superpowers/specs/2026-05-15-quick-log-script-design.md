# Spec: quick_log.py — Ingreso rápido a la bitácora desde consola

**Fecha:** 2026-05-15

## Problema

El ingreso de actualizaciones a la bitácora requiere abrir la app Streamlit, navegar al proyecto y llenar formularios. Cuando el usuario ya tiene las notas redactadas en texto libre, este proceso es lento y repetitivo.

## Solución

Un script de consola (`scripts/quick_log.py`) que acepta un bloque de texto libre, extrae los campos de la bitácora mediante detección flexible de keywords, pregunta interactivamente solo los campos no encontrados, y llama `OperationalTrackingService.add_update()` directamente, produciendo exactamente el mismo resultado que la app.

## Invocación

```
python scripts/quick_log.py <project_id>
```

## Flujo detallado

1. **Validar proyecto** — busca `project_id` en la BD via `ProjectRepository.get_project()`. Si no existe, termina con mensaje de error. Si existe, imprime el nombre del proyecto para confirmación visual.

2. **Leer bloque de texto** — solicita al usuario que pegue texto multiline. Finaliza entrada con `Ctrl+Z + Enter` (Windows) / `Ctrl+D` (Unix). Lee desde `sys.stdin`.

3. **Parsear campos** — extrae los siguientes campos usando regex con keywords flexibles (case-insensitive):

   | Campo DB         | Keywords                                                         |
   |------------------|------------------------------------------------------------------|
   | `general`        | status, estado, general, actualización, actualizacion, update    |
   | `proximo_paso`   | próximo paso, proximos pasos, next step, siguiente, próximos     |
   | `bloqueador`     | bloqueador, bloqueadores, bloqueo, blocked, blocker              |
   | `riesgo`         | riesgo, riesgos, risk, risks                                     |
   | `progress_percent` | avance, progreso, progress + número, o número seguido de %     |

   El parser asume que el texto de un campo se extiende hasta la siguiente keyword encontrada o hasta el final del bloque.

4. **Pedir campos faltantes** — para cada campo que no pudo extraerse, pregunta interactivamente. `Enter` vacío omite el campo (campo omitido no se guarda).

5. **Mostrar resumen y confirmar** — imprime todos los valores parseados/ingresados y pregunta `¿Guardar? [s/n]`. Si el usuario responde `n`, cancela sin modificar la BD.

6. **Guardar** — llama `OperationalTrackingService.add_update()` con:
   - `project_id`: el provisto como argumento
   - `payload_4_textareas`: dict con los cuatro campos de texto
   - `author`: resultado de `git config user.name`; fallback a `"console"`
   - `tags`: cadena vacía
   - `note_title`: cadena vacía
   - `progress_percent`: entero extraído o `None`
   - `estimated_end_date`: `None`
   - `created_at`: fecha ingresada por el usuario en formato `YYYY-MM-DD HH:MM:SS`; si el usuario no especifica, usa `datetime.now()`

8. **Fecha de la entrada** — después de parsear el bloque, el script pregunta:
   `Fecha del registro [Enter = hoy YYYY-MM-DD]:`. El usuario puede escribir una fecha pasada (ej. `2026-05-10`) para registrar la actualización como si la hubiera hecho ese día. Se almacena como `YYYY-MM-DD 00:00:00`.

7. **Confirmar éxito** — imprime cantidad de notas guardadas y termina.

## Archivos afectados

- `scripts/quick_log.py` — archivo nuevo
- `infra/db/repositories/notes_repo.py` — agregar soporte de `created_at` opcional en `insert_notes_batch`: si el dict de la nota incluye `"created_at"`, se usa en el INSERT; si no, se omite y la BD usa su default.

## Sin cambios a

- La base de datos (esquema sin cambios)
- El servicio `OperationalTrackingService` (se usa sin modificar)
- La app Streamlit

## Dependencias

Solo stdlib + las dependencias ya existentes del proyecto (`sqlite3`, `pathlib`, `subprocess` para git config).

## Ejemplo de uso

```
$ python scripts/quick_log.py abc123

Proyecto encontrado: "Atlas Q2 - Integración SharePoint"

Pega el texto de actualización (Ctrl+Z + Enter para terminar):
Status: en progreso, ya terminamos el módulo de autenticación
Avance: 65%
Próximos pasos: finalizar integración con la API de permisos
Bloqueadores: falta aprobación de TI para credenciales de producción
^Z

--- Resumen a guardar ---
General/Status : en progreso, ya terminamos el módulo de autenticación
Próximo paso   : finalizar integración con la API de permisos
Bloqueador     : falta aprobación de TI para credenciales de producción
Riesgo         : (no encontrado)
Avance         : 65%

Campo "Riesgo" no detectado. Ingresa manualmente (Enter para omitir): retraso si credenciales llegan después del viernes

--- Resumen final ---
General/Status : en progreso, ya terminamos el módulo de autenticación
Próximo paso   : finalizar integración con la API de permisos
Bloqueador     : falta aprobación de TI para credenciales de producción
Riesgo         : retraso si credenciales llegan después del viernes
Avance         : 65%

Fecha del registro [Enter = hoy 2026-05-15]: 2026-05-12

¿Guardar? [s/n]: s
✓ 4 notas guardadas correctamente (fecha: 2026-05-12).
```
