# Post-Implementacion

## Objetivo

Registrar y analizar resultados luego de publicar una automatizacion, con foco en adopcion, satisfaccion, ahorro de tiempo y recomendacion (NPS).

## Flujo

1. Usuario carga encuesta (tab Seguimiento o Feedback).
2. Se valida estructura y reglas de negocio.
3. Se consolidan respuestas por proyecto.
4. Se persiste en `tracking` y se actualizan visualizaciones.

## Contrato de encuesta vigente

Campos clave:
- Identificador de proyecto.
- Satisfaccion (1-10).
- Frecuencia de uso (`Diario`, `Semanal`, `Mensual`, `Ocasional`).
- Ahorro de tiempo reportado en porcentaje (0-100).
  - Se acepta notacion internacional: `12.5` o `12,5`.
- NPS (0-10).
- Beneficios adicionales (opcional).
- Problemas/dificultades (opcional).

## Reglas de procesamiento

- El porcentaje de ahorro no requiere conversion de escala; se guarda como porcentaje real.
- Se rechazan filas con valores fuera de rango.
- Si un proyecto tiene multiples respuestas, se agregan metricas numericas por promedio y textos por union unica.

## Indicadores del dashboard

- Promedio de satisfaccion post-implementacion.
- Promedio de ahorro de tiempo reportado (%).
- Promedio de NPS y NPS neto.
- Distribucion de frecuencia de uso.
- Distribucion Promotores / Pasivos / Detractores.
- Relacion NPS vs satisfaccion (dispersion).

## Persistencia

Tracking incluye (ademas de campos existentes):
- `survey_time_saved_percent`
- `usage_frequency`
- `nps_score`
- `nps_promoters`
- `nps_passives`
- `nps_detractors`

## Compatibilidad y migraciones

- Se asegura evolucion de esquema de `tracking` en inicializacion local e infraestructura de migraciones.
- Cambios son idempotentes (se agregan columnas faltantes sin romper datos existentes).
