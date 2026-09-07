# Diseño: `/presentacion-ejecutiva`

**Fecha:** 2026-09-04
**Estado:** propuesto, pendiente de plan de implementación
**Repos involucrados:** este vault (comando + lectura de datos) y el repo evaluador
(`Repositorio Evaluador` — ruta local en `.claude/sync-bitacora.local.json`, campo
`evaluator_repo_path`), donde vive el código que arma el `.pptx`.

## Problema

El equipo necesita un resumen ejecutivo corto — pensado para que el jefe directo
se lo presente a su jefe — que muestre impacto del portafolio de automatizaciones:
tiempo ahorrado, proyectos cerrados y en ejecución. Hoy existen dos piezas que no
se hablan entre sí:

- Este vault documenta cada proyecto en `proyectos/{slug}/index.md` con mucho más
  detalle (overview, objetivos de negocio, arquitectura) del que cabe en un slide.
- El repo evaluador ya genera una presentación operativa,
  `scripts/generate_execution_status_presentation.py`, con las anotaciones que se
  cargan en la app de Streamlit (`project_notes`: nota general, próximo paso,
  bloqueador, riesgo) — pero solo cubre proyectos `executing`, sin ningún
  agregado de portafolio, y lee de una SQLite local (`project_viability.db`), no
  de Supabase.

El objetivo no es construir un tercer artefacto, sino **extender el script que ya
existe** con una portada de resumen ejecutivo, y migrarlo a Supabase para que
tenga acceso al estado y horas ahorradas de los 21 proyectos del portafolio, no
solo a los `executing`.

## Qué no cambia

- **Obsidian se mantiene como repo puro de documentación.** No se agrega lógica
  de generación de `.pptx` aquí. El único código nuevo en este repo es el comando
  que junta datos y los entrega al script del evaluador — orquestador, no
  generador.
- **La generación de la presentación sigue siendo código determinístico**, no
  texto libre de un LLM: incluso el equivalente en tiempo-persona (semanas /
  meses / años) lo calcula el script con una fórmula fija, nunca lo redacta
  Claude, para que el número no cambie de una corrida a otra.
- **Sigue siendo un comando manual**, sin disparo automático — mismo patrón que
  `/revisar` y `/sync-bitacora`.
- **Solo lectura sobre Supabase.** Ningún paso de este flujo escribe en la base
  de datos.
- **El `.pptx` (y el JSON intermedio) nunca se comitean.** Los números cambian
  cada corrida; versionarlos solo ensuciaría el historial con binarios
  obsoletos.

## Qué se agrega

### Slide 1 — Resumen ejecutivo + pipeline (nuevo, portada)

Cuatro tarjetas de métrica, una frase de impacto, y el desglose de pipeline
fusionado en la misma slide (decisión explícita: el pipeline es parte del
resumen, no una slide aparte):

| Tarjeta | Cálculo |
|---|---|
| Horas ahorradas / mes | `SUM(hours_saved_per_month)` de proyectos `implemented` + `handed_off` |
| Equivale a | ese total convertido a tiempo-persona (ver fórmula abajo) |
| Proyectos cerrados | `COUNT(*)` con `status IN ('implemented','handed_off')` |
| En ejecución | `COUNT(*)` con `status = 'executing'` |

Debajo, una frase de impacto en lenguaje natural (plantilla fija, con los
números arriba interpolados):

> Cada mes, el equipo ahorra el equivalente a **{tiempo}** de trabajo de una
> persona a tiempo completo — con base en las {N} automatizaciones ya cerradas.

Y el pipeline completo (los 8 estados, incluidos los que están en cero — importa
mostrar que no hay nada en `rejected` ni `on_hold` hoy) como barra segmentada +
leyenda de chips con conteo, en el mismo orden que ya usa `dashboard.md`:
`evaluated → backlog → approved → executing → implemented → on_hold →
handed_off → rejected`. Los colores siguen la misma semántica que
`dashboard.md` (🟣 implementado, 🟢 ejecutando, 🔵 aprobado, ⚫ entregado, ⚪
evaluación/backlog, 🟡 pausa, 🔴 descartado) — no hace falta el mismo hex, solo
la misma familia de color por estado; la paleta exacta la define el skill
`worldpanel-brand`.

**Notas del presentador de esta slide** (panel de notas — nunca visible en
pantalla, solo si el presentador lo abre):

1. El supuesto de conversión (40h/semana = 1 FTE) y qué unidad se usó.
2. Qué proyecto concentra más ahorro (para que el presentador pueda explicar un
   número que domina el total, si preguntan).
3. Uno por uno, los 21 proyectos agrupados por estado: una frase de "qué es" +
   una frase de "estado actual" — viene del JSON que arma Claude (ver abajo).

### Fórmula de conversión a tiempo-persona

Determinística, vive en el script (no la calcula Claude):

```
semanas = horas_totales / 40

si semanas < 8:
    texto = "{semanas_enteras} semana(s) y {horas_restantes} h"
si no, si semanas < 52:
    meses = semanas / 4.345
    texto = "{meses redondeado a 1 decimal} meses"
si no:
    años = semanas / 52
    texto = "{años_enteros} año(s) y {meses_restantes} mes(es)"
```

Con los datos reales de hoy (2026-09-04, 8 proyectos cerrados, 5,662 h/mes
acumuladas — dominadas por `LA-OSCAROCHOA-0001` "SOP Latam" con 5,120 h/mes) da
"2 años y 9 meses", que es el ejemplo validado en el mockup.

### Slides 2+ — Detalle operativo (existente, migrado)

Mismas columnas que hoy: proyecto + id, badge de avance, nota / próximo paso,
bloqueador / riesgo, última actualización — 4 filas por slide, solo proyectos
`executing`. Cambia la fuente: de `project_viability.db` (SQLite local) a
Supabase (`projects` + `project_notes`), usando `DATABASE_URL` igual que
`/sync-bitacora`. La consulta CTE de "última nota por tipo" y "último avance"
que hoy usa SQLite se porta a Postgres — la tabla `project_notes` de Supabase
ya tiene columnas equivalentes (`note_type`, `note_text`, `progress_percent`,
`created_at`), así que no hace falta rediseñar el modelo, solo el dialecto SQL.

**Reskin completo a marca Worldpanel** (portada y detalle), reemplazando la
paleta actual del equipo D&D (`RGBColor(7,89,90)`, logo `logo_DDNola.png`) —
importa que el archivo se vea como un documento oficial de punta a punta, no
solo en la portada nueva.

### Mockup

Layout completo (con datos reales, colores placeholder) validado como artifact
antes de escribir esta spec: portada con las 4 tarjetas + frase de impacto +
pipeline fusionado, y una slide de detalle de ejemplo. Referencia visual, no
normativa — lo normativo es esta spec y el mockup puede quedar desactualizado.

## Flujo completo

1. **Claude, en este repo (`/presentacion-ejecutiva`):**
   a. Consulta Supabase (MCP, solo lectura) sobre `projects`:
      `project_id, name, status, description, closed_at`.
   b. Construye el mapa `project_id → slug` grepeando el frontmatter
      `project_id:` de `proyectos/*/index.md` (hoy 9 de los 21 proyectos de
      Supabase tienen documento en el vault).
   c. Por proyecto: si está en el mapa, lee el Overview de su `index.md` y la
      entrada más reciente de su `bitacora.md`, y condensa "qué es" + "estado
      actual" en una frase cada uno. Si no está, condensa el campo
      `description` de Supabase (20 de 21 proyectos ya lo tienen poblado con
      un párrafo utilizable; el que no, cae al fallback del script).
   d. Escribe `presentaciones/notas-YYYY-MM-DD.json`:
      ```json
      {
        "generated_at": "2026-09-04",
        "projects": [
          {
            "project_id": "MX-DDD-0005",
            "que_es": "Automatiza la generación y carga de Order Forms para clientes de MWP, eliminando el armado manual por cliente.",
            "estado_frase": "Implementado y cerrado el 2026-06-14."
          }
        ]
      }
      ```
   e. Verifica que `DATABASE_URL` esté seteada (mismo requisito que
      `/sync-bitacora`; si no, la pide al usuario, nunca la adivina ni la
      guarda en el repo) y que `presentaciones/` esté en `.gitignore` (la
      agrega si falta).
   f. Corre:
      ```
      python "<evaluator_repo_path>/scripts/generate_execution_status_presentation.py" ^
        --notes "presentaciones/notas-YYYY-MM-DD.json" ^
        --out "presentaciones/presentacion-ejecutiva-YYYY-MM-DD.pptx"
      ```
   g. Reporta al usuario y entrega el archivo.

2. **Script en el evaluador (código, migrado):**
   a. Se conecta a Supabase con `DATABASE_URL` (no a `project_viability.db`).
   b. Trae `projects` completo (21 filas) para portada + pipeline, y
      `project_notes`/progreso de los `executing` para el detalle.
   c. Calcula agregados y el equivalente en tiempo-persona con la fórmula fija.
   d. Lee `--notes` (opcional): si el archivo no existe o un `project_id` no
      aparece en él, usa un texto de respaldo (`"{name} — sin resumen
      disponible."` / `"Estado: {status en español}."`) — el script nunca
      falla por notas faltantes.
   e. Arma las slides con la paleta Worldpanel y guarda en `--out`.

## Dónde vive el código

- **Nuevo:** `.claude/commands/presentacion-ejecutiva.md` (este repo) — solo
  instrucciones, sin script.
- **Extendido:** `scripts/generate_execution_status_presentation.py` (repo
  evaluador) — se le agrega la función de la portada (tarjetas + pipeline +
  notas), se migra `fetch_executing_projects` y las consultas relacionadas de
  SQLite a Supabase, se agrega `argparse` para `--notes` y `--out` (hoy
  `OUTPUT_PATH` y `DB_PATH` están hardcodeados), y se reemplazan las
  constantes de color `C_*` por la paleta Worldpanel.
- **Los colores oficiales se obtienen una sola vez, en implementación**,
  invocando el skill `worldpanel-brand` desde una sesión de Claude Code y
  transcribiendo la paleta a constantes `RGBColor` en el script — un script
  Python no puede invocar skills de Claude en tiempo de ejecución, así que esto
  no es una dependencia de runtime.

## Prerrequisito confirmado: sincronizar `project_notes` antes de migrar el detalle

Investigado directamente en el código del repo evaluador (no es especulación).
Resultado:

- **`effort_hours` es una tabla muerta — se ignora, no es un riesgo.** Ningún
  código vivo la crea ni la usa: `infra/db_migrations.py` solo agrega
  `effort_hours` como *columna* de `project_notes`, y
  `scripts/migrate_sqlite_to_supabase.py` no migra ninguna tabla con ese
  nombre. La única referencia es un plan de diseño viejo
  (`docs/superpowers/plans/2026-05-20-cloud-deployment.md`) que alguien
  ejecutó a mano al crear el proyecto Supabase, con un diseño que cambió
  después. No hay nada que migrar ni arreglar ahí.
- **`project_notes` vacía sí es real y sí bloquea el detalle (slides 2+),**
  por dos causas posibles y no excluyentes:
  1. `/sync-bitacora` no corrió contra este proyecto Supabase desde la
     migración inicial (o corrió y saltó proyectos cuyo `project_id` no
     existía aún en `projects` — el script imprime el skip, no falla, así
     que pasa desapercibido).
  2. La app de Streamlit en producción podría no tener `DATABASE_URL` seteada
     en sus secrets — en ese caso cada nota cargada desde la UI cae en un
     SQLite efímero del contenedor de Streamlit Cloud que se resetea en cada
     redeploy, y nunca llegaría a Supabase pase lo que pase con
     `/sync-bitacora`. Esto sería más grave que "falta sincronizar".
- El código de escritura (`infra/db/adapter.py`, `NotesRepository
  .insert_notes_batch`) sí soporta Supabase correctamente cuando
  `DATABASE_URL` está seteada — no hay bug de código, es una cuestión de
  configuración/operación pendiente de confirmar.
- `scripts/generate_execution_status_presentation.py` hoy ignora el adapter
  por completo (`sqlite3.connect(db_path)` hardcodeado) — nunca leyó
  Supabase, consistente con lo que ya sabíamos.

**Orden de implementación que esto impone** — no es negociable: migrar el
script antes de esto produce un detalle operativo vacío, peor que el estado
actual.

1. Confirmar que `wcicvyqvjbufpicvhoac` es el Supabase real de producción
   (comparar contra el host en los secrets de Streamlit Cloud, o `get_project`
   con esa ref).
2. Confirmar que `DATABASE_URL` está seteada en los secrets de Streamlit
   Cloud. Si no lo está, arreglar eso es prerrequisito antes que cualquier
   otra cosa — sin eso las notas nuevas tampoco persistirían de aquí en
   adelante.
3. Correr `/sync-bitacora` contra el vault actual y revisar los
   `skipped`/`failed` que imprime.
4. Recién con `project_notes` poblada y confirmada como fuente viva, migrar
   `generate_execution_status_presentation.py`.

**La portada nueva (slide 1) no depende de nada de esto** — solo lee
`projects`, que ya está poblada con las 21 filas. Solo el detalle operativo
(slides 2+) depende de este prerrequisito, así que la implementación puede
avanzar en ese orden: portada primero, detalle después de los 4 pasos de
arriba.

## Documentación a actualizar

- `AGENTS.md` / `CLAUDE.md`: agregar `/presentacion-ejecutiva` a la lista de
  comandos disponibles.
- Si el riesgo de arriba se resuelve tocando el flujo de `/sync-bitacora`,
  actualizar también su entrada y `_meta/convenciones.md` en consecuencia.

## Fuera de alcance

- **Valor en $ (ahorro mensual/anual).** Se descartó explícitamente por no ser
  una estimación confiable para presentarle al jefe del jefe — el headline
  usa horas y su equivalente en tiempo-persona, no dinero.
- **Slides o texto por proyecto individual en pantalla.** El contenido visible
  es agregado; el detalle por proyecto vive solo en las notas del presentador
  (slide 1) y en las filas operativas de `executing` (slides 2+, que ya
  existían).
- **Disparo automático o programado.** Sigue siendo manual.
- **Arreglar `DATABASE_URL` en los secrets de Streamlit Cloud, si falta.** Es
  prerrequisito bloqueante para el detalle (ver sección de arriba), pero es
  una tarea de configuración del repo evaluador, no algo que este comando
  resuelva.
- **`effort_hours`.** Confirmado como tabla muerta — no se migra, no se lee,
  no se menciona más en el código nuevo.
- **Alta o edición de proyectos en Supabase desde este flujo.** Solo lectura.
