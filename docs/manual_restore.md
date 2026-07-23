# Manual de restauración — JDM Empeños

## SQLite local

1. Detenga la aplicación.
2. Reemplace `instance/jdm_empenos.db` por el respaldo.
3. Restaure `uploads/` si aplica.
4. Inicie la aplicación.

## PostgreSQL

```bash
psql "$DATABASE_URL" < backup_jdm_YYYYMMDD.sql
```

Luego verifique `/healthz` y el inicio de sesión.