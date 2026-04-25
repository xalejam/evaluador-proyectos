# Revisión Arquitectural — Evaluador de Proyectos

> Generado: 2026-04-24. Basado en exploración completa del codebase.

---

## Diagnóstico general

La arquitectura tiene una base sólida (separación en `domain/`, `infra/`, `ui/`) pero tiene **brechas críticas** que aumentan el riesgo de bugs, dificultan el testing y frenarán el crecimiento. Los problemas se dividen en cuatro áreas independientes, cada una con su propio plan de mejora.

---

## Hallazgos por severidad

### 🔴 Alta — Rompen la arquitectura

| # | Problema | Archivo | Línea |
|---|---|---|---|
| A1 | `viability_service.py` importa `streamlit` y accede a `st.session_state` — dominio acoplado a UI | `domain/services/viability_service.py` | 7, 25, 41-44, 70-73 |
| A2 | `feedback_service.py` importa directamente desde `ui/tabs/` — inversión de dependencias | `domain/services/feedback_service.py` | 5 |
| A3 | 2 bases de datos con tabla `projects` sin sincronización transaccional; join manual en Python | `ui/use_case_matrix.py` | 24-76 |

### 🟡 Media — Generan deuda técnica acumulada

| # | Problema | Archivo | Línea |
|---|---|---|---|
| B1 | Lógica de scoring (`_impact_points`, `_risk_points`, `_complexity_points`) duplicada | `domain/scoring/score_engine.py` vs `ui/tabs/planning.py` | 34-56 vs 118-137 |
| B2 | `"project_viability.db"` hardcodeado como string literal en 8+ archivos | `infra/db_migrations.py`, `infra/db/repositories/*.py`, `domain/services/*.py`, `ui/tabs/shared.py`, `ui/use_case_matrix.py` | múltiples |
| B3 | `shared.py` God Object de 1711 líneas: traducciones + lógica + acceso a datos mezclados | `ui/tabs/shared.py` | todo el archivo |
| B4 | Módulos críticos sin ningún test: `viability_service`, `seguimiento_operativo_service`, `thresholds`, `repositories` SQLAlchemy | `domain/services/`, `infra/repositories.py` | — |

### 🟢 Baja — Fáciles de corregir

| # | Problema | Archivo | Línea |
|---|---|---|---|
| C1 | `"Xiomy"` hardcodeado como fallback de autor en `state.py` | `ui/state.py` | 31 |
| C2 | `config/folder_provisioner_config.json` tiene ruta personal hardcodeada no portable | `config/folder_provisioner_config.json` | 2 |
| C3 | `except:` desnudo sin logging ni tipo específico | `ui/tabs/planning.py` | 110 |
| C4 | 7 archivos wrapper de 10 líneas sin valor real | `ui/tabs/*_tab.py` | — |

---

## Principios SOLID — Cumplimiento actual

| Principio | Estado | Nota |
|---|---|---|
| **S** Single Responsibility | ❌ Parcial | `shared.py` tiene 5+ responsabilidades |
| **O** Open/Closed | ✅ Bueno | `FolderProvisioner` ABC es un buen ejemplo |
| **L** Liskov | ✅ N/A | Sin jerarquías complejas |
| **I** Interface Segregation | ✅ Bueno | Interfaces pequeñas en `infra/` |
| **D** Dependency Inversion | ❌ Roto | `feedback_service` y `viability_service` dependen de capas superiores |

---

## Planes de implementación priorizados

Los problemas se agrupan en **3 planes independientes** que pueden ejecutarse en cualquier orden:

| Plan | Título | Impacto | Esfuerzo | Prioridad |
|---|---|---|---|---|
| [Plan 1](2026-04-24-fix-domain-coupling.md) | Desacoplar dominio de Streamlit | Alto | Medio | **1° — Ejecutar primero** |
| [Plan 2](2026-04-24-fix-db-path-and-scoring-duplication.md) | Centralizar DB_PATH + eliminar scoring duplicado | Medio | Bajo | **2° — Rápido de ejecutar** |
| [Plan 3](2026-04-24-add-missing-tests.md) | Tests para módulos críticos sin cobertura | Medio | Medio | **3° — Mejora de seguridad** |

> **No incluido en planes:** El refactor de `shared.py` (B3) es el cambio de mayor riesgo — 1711 líneas con dependencias en toda la app. Se recomienda abordarlo solo después de tener cobertura de tests adecuada (Plan 3) para poder refactorizar con seguridad.

---

## Arquitectura objetivo (post-planes)

```
main.py
  └── ui/tabs/*              (solo presentación — sin lógica de negocio)
        └── domain/services/*  (orquestación — sin imports de Streamlit)
              └── domain/scoring/*   (cálculos puros — ya bien aislados)
              └── infra/db/*         (acceso a datos — constante DB_PATH centralizada)
        └── infra/config_loader.py  (config centralizada)

Constantes globales:
  config/app_config.py → DB_PATH, APP_NAME, DEFAULT_AUTHOR
```
