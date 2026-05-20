---
name: deployment-design
description: Diseño de despliegue del Evaluador de Proyectos en Streamlit Community Cloud con Supabase PostgreSQL y autenticación propia para equipo de hasta 5 personas sin acceso Azure admin
metadata:
  type: project
---

# Diseño: Despliegue del Evaluador de Proyectos

**Fecha:** 2026-05-20
**Autora:** Xiomara
**Estado:** Aprobado

---

## Contexto

La app es un evaluador de proyectos construido en Streamlit con dos bases de datos SQLite locales (`project_viability.db` y `data/projects.db`). Actualmente solo puede usarla quien tenga el repo en su máquina. El objetivo es que los 5 integrantes del equipo puedan ingresar sus propias notas y datos desde cualquier navegador, sin depender de Xiomara.

**Restricciones:**
- Sin acceso de administrador a Azure (no está dentro del tenant corporativo)
- Código en Azure DevOps
- Cuentas corporativas Microsoft disponibles pero sin Azure AD para OAuth
- Presupuesto: $0

---

## Arquitectura

```
Tu máquina
    │  git push (flujo normal)
    ▼
Azure DevOps (repo actual)
    │  mirror automático vía azure-pipelines.yml
    ▼
GitHub (repo privado, cuenta personal)
    │  trigger en cada push a main
    ▼
Streamlit Community Cloud
    ├── app Streamlit (sin cambios mayores)
    └── st.secrets (credenciales cifradas, no en el repo)
          │  conexión SSL
          ▼
     Supabase PostgreSQL
     ├── projects
     ├── evaluations
     ├── tracking
     ├── effort_hours
     └── users  (tabla nueva)
```

---

## Componentes

### 1. Mirror Azure DevOps → GitHub

Se agrega una tarea en `azure-pipelines.yml` que hace `git push --mirror` al repo privado de GitHub cada vez que hay un push a `main`. Las credenciales de GitHub se guardan como variable secreta del pipeline (nunca en el código).

### 2. Base de datos: Supabase PostgreSQL

Los dos SQLite se consolidan en una sola base de datos PostgreSQL en Supabase (plan gratuito, 500 MB).

**Tablas migradas sin cambio de estructura:**
- `projects` (de `project_viability.db`)
- `tracking`
- `evaluations` (de `data/projects.db`)
- `effort_hours`
- `project_notes`
- `project_members`

**Tabla nueva:**
```sql
CREATE TABLE users (
    email       TEXT PRIMARY KEY,
    password_hash TEXT NOT NULL,   -- bcrypt
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMP DEFAULT NOW()
);
```

**Cambio en el código:** reemplazar el driver `sqlite3` / `SQLAlchemy` local por conexión a Supabase vía `SQLAlchemy + psycopg2`. La URL de conexión va en `st.secrets`, nunca en el repo.

### 3. Autenticación

Pantalla de login al inicio de la app. Flujo:

1. Usuario ingresa email + contraseña
2. App busca el email en tabla `users`
3. Verifica contraseña con `bcrypt.checkpw`
4. Si es válido: guarda `st.session_state["authenticated"] = True`
5. Si no: muestra error, no revela si el email existe o no

`main.py` verifica `st.session_state` al inicio. Si no hay sesión activa, muestra login en lugar de la app.

**Archivos nuevos:**
- `ui/login.py` — formulario de Streamlit
- `scripts/create_user.py` — script de administración para crear/desactivar cuentas (corre Xiomara localmente, no es parte de la app)

### 4. Streamlit Community Cloud

- Conecta directamente al repo privado de GitHub
- Despliega automáticamente en cada push
- Las credenciales de Supabase se cargan como `st.secrets` en el panel de SCC (nunca en el repo)
- URL fija para compartir con el equipo: `https://<nombre>.streamlit.app`

---

## Seguridad

| Riesgo | Mitigación |
|---|---|
| Credenciales de DB expuestas | `st.secrets` cifrado en SCC, `.gitignore` para `secrets.toml` local |
| Acceso no autorizado a la app | Login con bcrypt, `is_active` para revocar acceso |
| Contraseñas en texto plano | Nunca se almacenan; solo el hash bcrypt |
| Código expuesto en GitHub | Repo privado |
| Datos sensibles en repo | Solo código, nunca datos ni credenciales |

**Limitación conocida:** No es SSO corporativo. Cada persona tiene contraseña propia creada por Xiomara. Adecuado para equipo de confianza de 5 personas.

---

## Flujo de actualización (post-despliegue)

```
Xiomara edita código → git push a DevOps
    → pipeline mirror → GitHub
    → Streamlit Community Cloud redespliega (~2 min)
    → datos en Supabase intactos
```

---

## Fuera de alcance

- SSO con Azure AD / Microsoft OAuth
- Roles y permisos por usuario (todos ven todo)
- Backup automatizado de Supabase (el plan gratuito incluye backups diarios de 7 días)
- Dominio personalizado

---

## Costo

| Servicio | Plan | Costo |
|---|---|---|
| Streamlit Community Cloud | Community (hasta 3 apps privadas) | $0 |
| Supabase | Free (500 MB, 50k filas) | $0 |
| GitHub | Free (repos privados ilimitados) | $0 |
| **Total** | | **$0** |
