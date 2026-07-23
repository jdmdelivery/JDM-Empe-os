# Cierre Fase 7 — Notificaciones, exportaciones, backups

## Notificaciones
- Cola segura: **no envía** hasta configurar `WHATSAPP_API_TOKEN`, `SMS_API_TOKEN` o `SMTP_HOST`
- Ajustes: `notifications_enabled`, `notify_before_due_days`
- Recordatorios de vencimiento: `queue_due_reminders()`

## Exportaciones
- CSV: `/reports/export.csv?kind=payments|sales|contracts`
- Excel: `/reports/export.xlsx`

## Backups
- UI en **Configuración** → crear respaldo SQLite
- Restaurar desde la misma pantalla (copia de seguridad previa automática)
- PostgreSQL: registrar intención + usar `pg_dump` / `pg_restore` en servidor

## Fotos
- Optimización automática con Pillow (máx. 1600px, JPEG calidad 85) en `file_storage`
