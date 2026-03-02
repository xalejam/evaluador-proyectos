# Configuracion

Archivo principal: `config/scoring_config.json`

## Estructura

```json
{
  "id_format": "{country}-{owner}-{sequence}",
  "n_digits": 4,
  "thresholds": { "impact": 3.5, "effort": 3.5 },
  "countries": ["MX", "BR", "CO"],
  "criteria": [ ... ],
  "default_weights": { "A": 1, ..., "H": 1 }
}
```

## Parametros clave

- `id_format`:
  - tokens soportados: `{country}`, `{owner}`, `{sequence}`
  - recomendado: mantener separadores claros (ej. guion).

- `n_digits`:
  - largo del consecutivo.
  - ejemplo: `4` -> `0001`, `0002`, etc.

- `thresholds.impact` y `thresholds.effort`:
  - lineas de corte para cuadrantes de Use Case Matrix.

- `criteria`:
  - definicion de A-H (codigo, dimension, label, help).

- `default_weights`:
  - pesos por criterio usados por defecto en matriz.

## Buenas practicas

1. Cambiar un parametro a la vez y validar en la UI.
2. Mantener `countries` en formato ISO2 (`MX`, `BR`, `CO`, etc.).
3. Si cambias `id_format` o `n_digits`, considerar impacto en IDs existentes.
4. Si modificas criterios/pesos, documentar la fecha y razon del cambio.

## Carga de config en codigo

- Loader: `infra/config_loader.py`
- Consumidores principales:
  - `ui/use_case_matrix.py`
  - `planning.py`
  - `shared.py` (formato de ID)
