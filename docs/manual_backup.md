# Manual de copias de seguridad — JDM Empeños

> Estructura preparada en Fase 1 (`backups`). Flujo completo en Fase 7.

## Desarrollo local (SQLite)

1. Detenga la aplicación.
2. Copie `instance/jdm_empenos.db` a una carpeta segura.
3. Copie también la carpeta `uploads/`.

## Producción (PostgreSQL)

Use `pg_dump`:

```bash
pg_dump "$DATABASE_URL" > backup_jdm_$(date +%Y%m%d).sql
```

## Restauración

Ver [`manual_restore.md`](manual_restore.md).