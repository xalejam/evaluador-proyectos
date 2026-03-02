# Troubleshooting

## 1) `NameError` en Planificacion (variable no definida)

Ejemplo:
- `final_hourly_rate is not defined`

Causa:
- variable renombrada o typo en texto interpolado.

Accion:
- usar la variable correcta (`avg_hourly_rate` en este caso),
- ejecutar `py_compile` para validar.

## 2) `KeyError` en campos financieros de proyecto

Ejemplo:
- `KeyError: 'initial_development_cost'`

Causa:
- filas antiguas sin esa columna o esquema DB desfasado.

Accion:
1. reiniciar app para ejecutar migracion de `shared.py`,
2. validar columna en SQLite,
3. usar lectura defensiva con `.get(..., 0)` en UI.

## 3) `StreamlitDuplicateElementId`

Causa:
- dos widgets con el mismo tipo/parametros sin `key` unica.

Accion:
- agregar `key` explicita en cada widget potencialmente repetido.

## 4) Error al instalar paquetes por SSL

Ejemplo:
- `CERTIFICATE_VERIFY_FAILED`

Accion temporal:
```powershell
pip install -r requirements.txt --trusted-host pypi.org --trusted-host files.pythonhosted.org --trusted-host pypi.python.org
```

## 5) Error de archivo bloqueado en `.venv` (OneDrive)

Ejemplo:
- `WinError 32 ... file is being used by another process`

Causa:
- OneDrive o antivirus bloqueando archivos durante install.

Accion:
1. reintentar instalacion,
2. pausar sync de OneDrive durante `pip install`,
3. evitar ejecutar la app mientras instala.

## 6) Cambios no reflejados en app

Causa:
- proceso Streamlit viejo en ejecucion.

Accion:
1. detener con `Ctrl+C`,
2. re-ejecutar `python start.py`.
