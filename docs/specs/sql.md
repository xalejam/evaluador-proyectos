# SQL (Consultas)

## 1. Propósito

Terminal SQL de solo lectura que permite ejecutar consultas `SELECT` directamente sobre `project_viability.db`. Diseñado para análisis ad-hoc, debugging y exportación de datos sin necesidad de acceder a la base de datos con herramientas externas.

**Usuarios:** Analistas técnicos y developers del equipo.

---

## 2. Inputs

### Fuentes de datos
- `project_viability.db` — única DB accesible desde esta pestaña

### Parámetros del usuario
| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| Query SQL | text_area | `SELECT` o `WITH` — una sola sentencia |
| Botón "Ejecutar" | button | Dispara la query |
| Botón "Limpiar" | button | Hace `st.rerun()` para resetear el área |

---

## 3. Outputs

| Output | Formato | Dónde |
|--------|---------|-------|
| Resultado de la query | `st.dataframe` | Tras ejecutar |
| Conteo de filas | `st.success` | Mensaje superior al resultado |
| Exportación CSV | `st.download_button` | Bajo el resultado |
| Mensajes de error | `st.error` | Si query inválida o falla ejecución |

---

## 4. Lógica de negocio

### Validación de query (antes de ejecutar)
```
1. Query no vacía               → error "query vacía"
2. Una sola sentencia (sin ";") → error "solo una sentencia permitida"
3. Empieza con SELECT o WITH    → error "solo lecturas permitidas"
4. No contiene palabras clave destructivas:
   INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, REPLACE,
   TRUNCATE, ATTACH, DETACH, PRAGMA, VACUUM, REINDEX,
   BEGIN, COMMIT, ROLLBACK
   → error "keyword X no permitida"
```

La validación usa `re.search(rf"\b{keyword}\b", lowered)` — detecta keywords como palabras completas (no como substring de nombres de columnas).

### Normalización de query
```
strip() → elimina espacios al inicio/fin
si termina en ";" → elimina el ";"
```

### Ejecución
```python
sqlite3.connect(db_path) as conn:
    df = pd.read_sql_query(normalized_query, conn)
```
Conexión de solo lectura de facto (SQLite no tiene modo read-only explícito en esta implementación, pero el bloqueo por validación previene escrituras).

---

## 5. Flujo funcional

1. Renderiza área de texto con query de ejemplo (SELECT básico de `projects`)
2. Botones "Ejecutar" y "Limpiar" en columnas paralelas
3. Click "Limpiar" → `st.rerun()`
4. Click "Ejecutar":
   a. Valida query (`_validate_readonly_query`)
   b. Si inválida → `st.error` con mensaje específico
   c. Si válida → conecta a DB, ejecuta, lee resultado en DataFrame
   d. Muestra `st.success` con conteo de filas
   e. Muestra `st.dataframe` con resultado
   f. Botón de descarga CSV

---

## 6. Queries / lógica de datos

### Query de ejemplo (default en UI)
```sql
SELECT id, name, priority, viability_score, status
FROM projects
ORDER BY created_date DESC
LIMIT 50
```

### Tablas disponibles en `project_viability.db`
| Tabla | Descripción |
|-------|-------------|
| `projects` | Proyectos con todos sus campos de viabilidad y metadata |
| `tracking` | Seguimiento post-implementación |
| `project_notes` | Notas inmutables del seguimiento operativo |
| `project_evaluations` | Snapshots de cada evaluación guardada |

### Vistas disponibles (creadas por Seguimiento Operativo)
| Vista | Descripción |
|-------|-------------|
| `v_project_latest_notes` | Última nota por `(project_id, note_type)` |
| `v_project_last_note` | Última nota global por `project_id` |
| `v_project_progress_history` | Historial de `progress_percent` por proyecto |

---

## 7. Componentes UI

| Componente | Propósito |
|-----------|-----------|
| `st.header` + `st.caption` | Título y descripción del tab |
| `st.markdown` | Documentación de tablas disponibles |
| `st.text_area` (height=180) | Área de edición de la query |
| `st.columns([1,1])` + `st.button` × 2 | Ejecutar / Limpiar |
| `st.error` | Mensaje de validación fallida |
| `st.success` | Conteo de filas retornadas |
| `st.dataframe` | Resultado de la query |
| `st.download_button` | Descargar CSV del resultado |

---

## 8. Dependencias

### Otras pestañas
- Ninguna dependencia de estado con otras pestañas.
- Lee de la misma DB que usan Viabilidad y Seguimiento Operativo.

### Módulos Python
| Módulo | Uso |
|--------|-----|
| `sqlite3` | Conexión y ejecución de query |
| `pandas` | `read_sql_query` → resultado como DataFrame |
| `re` | Detección de keywords prohibidas (`\b...\b`) |
| `io` | `BytesIO` para exportación CSV |
| `ui.tabs.shared.t()` | Textos i18n |

---

## 9. Casos borde

| Caso | Comportamiento actual |
|------|----------------------|
| Query vacía | Error "query vacía" |
| Query con `;` al final | Se elimina el `;` antes de validar — pasa sin problema |
| Query con dos sentencias (ej. `SELECT 1; SELECT 2`) | Error "solo una sentencia" porque detecta `;` en el cuerpo |
| Keyword en nombre de columna (ej. `SELECT update_date`) | Puede dar falso positivo — `\b update \b` matchea `update` en `update_date` [POSIBLE BUG] |
| `WITH ... SELECT ...` (CTE) | Permitido — la validación acepta queries que empiezan con `WITH` |
| Resultado vacío | DataFrame vacío, `st.success` con "0 filas" |
| Error de SQLite (tabla no existe, syntax error) | `st.error` con mensaje de excepción |
| Query muy pesada (millones de filas sin LIMIT) | Sin límite impuesto — puede agotar memoria y congelar la app |

---

## 10. Performance

### Situación actual
- Sin límite de filas en el resultado — una query sin `LIMIT` puede devolver todo el dataset.
- Conexión nueva en cada ejecución (no hay pool).
- No hay timeout en la query.

### Mejoras necesarias
- [ ] Imponer `LIMIT 10000` automático si la query no lo incluye, con advertencia al usuario.
- [ ] Agregar timeout de ejecución (ej. 30 segundos) para queries largas.
- [ ] Abrir la conexión SQLite en modo `read-only` (`uri=True`, `?mode=ro`) para reforzar la restricción a nivel de driver, no solo de validación de texto.

---

## 11. Validación

### Validación actual
- Textual: keywords como palabras completas (`\b...\b`)
- Límite: no admite `;` en el cuerpo

### Gap de seguridad conocido
La validación actual es textual y puede tener falsos positivos/negativos:
- `SELECT update_date FROM projects` → puede ser bloqueado erróneamente si `update` matchea como palabra completa
- Un atacante creativo podría usar comentarios SQL `--` o encoding para evadir el regex

### Mejora recomendada
Usar SQLite en modo read-only a nivel de conexión:
```python
conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
```
Esto elimina la necesidad de validación textual para escrituras.

---

## 12. Historial de cambios

| Fecha | Cambio | Responsable |
|-------|--------|-------------|
| 2026-01 | Versión inicial con validación básica | Xiomara |
| 2026-02 | Agrega exportación CSV + botón limpiar | Xiomara |
| 2026-03 | Documenta tablas y vistas disponibles en UI | Xiomara |

---

## 13. Definición analítica

### Tipo de uso
- **Exploración ad-hoc**: el usuario construye su propia query.
- No hay métricas predefinidas — es un canvas en blanco.

### Supuestos
- Los usuarios de esta pestaña tienen conocimiento básico de SQL.
- Los datos en `project_viability.db` son la fuente completa y actualizada — no requiere joins con otras DBs.

### Limitaciones
- No accede a `data/projects.db` (Use Case Matrix) — para eso se necesitaría otra instancia o un `ATTACH DATABASE`.
- Sin historial de queries ejecutadas.

### Mejoras futuras
- Agregar autocompletado de nombres de tabla/columna.
- Guardar historial de queries de la sesión (en `st.session_state`).
- Permitir seleccionar entre `project_viability.db` y `data/projects.db` como fuente.
- Agregar botones de queries de ejemplo predefinidas (ej. "Proyectos por status", "Notas del último mes").
