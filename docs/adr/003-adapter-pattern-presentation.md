# ADR 003: Adapter Pattern en Capa de Presentación

**Estado:** Aceptado  **Fecha:** 2026-04-24

## Contexto

El proyecto corre actualmente en local con SQLite y archivos Excel/CSV locales. En el futuro debe correr en nube con Azure Blob Storage / SharePoint Graph API como destino de presentaciones y reportes. Cambiar el backend no debe requerir modificar la lógica de UI.

## Decisión

`infra/presentation_ports.py` define protocolos (`DataSource`, `FileDestination`) para inyectar backends sin cambiar código de UI. `SqliteDataSource` e `InMemoryDestination` son las implementaciones actuales para entorno local.

## Consecuencias

- **Positivo:** migración a nube sin tocar la capa de presentación; cada backend es testeable independientemente
- **Negativo:** indirección adicional para operaciones locales simples; nuevos colaboradores deben entender los protocolos antes de agregar features
- **Evolución esperada:** implementar `AzureBlobDestination` y `SharePointGraphDestination` cuando se migre a nube, sin modificar `ui/` ni `domain/`
