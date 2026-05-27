# CI Ruff Format Failures — Causa Raíz y Runbook

## Síntoma

El pipeline de CI falla con:

```
would reformat /home/vsts/work/1/s/tests/unit/some_file.py
Oh no! 💥 💔 💥
1 file would be reformatted, N files would be left unchanged.
```

El mismo archivo pasa `ruff format` localmente en Windows pero falla en Linux.

---

## Causa raíz

| Factor | Valor |
|--------|-------|
| `git config core.autocrlf` (Windows) | `true` |
| Efecto | Git convierte LF → CRLF al hacer `checkout` en Windows |
| Resultado | Los archivos en disco tienen terminaciones CRLF |
| CI (Linux) | `ruff format` usa LF; ve CRLF → reporta "would reformat" |

**El ciclo del error:**

```
Dev escribe código en Windows
       ↓
Git checkout con core.autocrlf=true → archivo tiene CRLF
       ↓
ruff format local (Windows) → no toca CRLF, dice "OK"
       ↓
git push → archivo subido con CRLF (o LF si Git convierte en push)
       ↓
CI en Linux → ruff format ve CRLF → "would reformat" → ❌ FAIL
```

---

## Solución permanente (ya aplicada)

Se creó `.gitattributes` en la raíz del repo:

```
* text=auto eol=lf
*.py text eol=lf
...
```

Esto fuerza LF en todos los archivos de texto **independientemente de `core.autocrlf`**. Git normaliza al commit y al checkout. El archivo ya está en `main` desde el commit `4c4d978`.

---

## Si el error vuelve a aparecer

### Diagnóstico rápido

```powershell
# ¿El archivo tiene CRLF?
$bytes = [IO.File]::ReadAllBytes("path\al\archivo.py")
($bytes | Where-Object { $_ -eq 13 }).Count  # > 0 → tiene CRLF

# ¿core.autocrlf está activo?
git config core.autocrlf   # debe ser false o input, no true
```

### Fix inmediato (re-normalizar todo el repo)

```powershell
# Desde la raíz del repo:
git add --renormalize .
git status   # verifica qué archivos cambiaron
git commit -m "chore: renormalize line endings to LF"
git push origin main
git push github main
```

### Fix de raíz en la máquina local (opcional)

Si quieres que tu Git local deje de convertir:

```bash
git config core.autocrlf input
# o globalmente:
git config --global core.autocrlf input
```

`input` significa: convierte CRLF→LF al hacer commit, pero no convierte al hacer checkout. Es el valor correcto para desarrollo en Windows con CI en Linux.

---

## Checklist antes de cada push

Estos dos comandos deben pasar en verde **localmente** antes de hacer push:

```powershell
# Desde la raíz del repo:
python -m ruff check .
python -m ruff format --check .
```

Si `ruff format --check` reporta archivos que serían reformateados:

```powershell
python -m ruff format .
git add -u
git commit -m "style: ruff format"
```

---

## Checklist para subagentes

Cuando un subagente implementa código y hace commit, debe ejecutar en este orden:

```
1. python -m ruff check <archivos modificados>
2. python -m ruff format <archivos modificados>
3. git diff --stat    ← verifica que ruff format no generó cambios sin commitear
4. git add -u && git commit (si hubo cambios de formato)
5. python -m ruff format --check .   ← verificación final de todo el repo
```

El paso 5 (check global) evita que un archivo olvidado rompa CI. El subagente del status-machine corrió `ruff format` solo sobre los archivos nuevos pero no verificó el repo completo — por eso se escapó el CRLF en `test_status_machine.py`.

---

## Por qué `.gitattributes` es la solución correcta

| Alternativa | Problema |
|-------------|----------|
| `core.autocrlf=false` en cada máquina | Manual, no se propaga a nuevos colaboradores |
| `core.autocrlf=input` en cada máquina | Idem — depende de configuración local |
| `.editorconfig` con `end_of_line = lf` | No afecta a Git ni a ruff |
| **`.gitattributes eol=lf`** | ✅ Se versionea con el repo, aplica a todos automáticamente |
