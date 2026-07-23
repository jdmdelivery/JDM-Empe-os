# Documentación de base de datos — JDM Empeños

## Motor

| Entorno | Motor |
|---------|-------|
| development | SQLite (`instance/jdm_empenos.db`) |
| testing | SQLite en memoria |
| production | PostgreSQL (`DATABASE_URL` → `postgresql+psycopg://`) |

## Tablas Fase 1

| Tabla | Descripción |
|-------|-------------|
| `roles` | Roles del sistema |
| `permissions` | Catálogo de permisos |
| `role_permissions` | Relación N:M rol-permiso |
| `branches` | Sucursales |
| `users` | Usuarios / empleados |
| `settings` | Configuración clave-valor |
| `backups` | Registro de respaldos (estructura) |
| `audit_logs` | Auditoría de acciones |
| `login_logs` | Historial de accesos |

## Convenciones

- Eliminación lógica: `is_deleted`, `deleted_at`
- Fechas con zona horaria (UTC en almacenamiento; UI en `America/Santo_Domingo`)
- Dinero futuro: `Numeric` + `Decimal` (nunca `float`)
- Migraciones: Flask-Migrate / Alembic en `migrations/`