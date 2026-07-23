# Cierre Fase 1 — JDM Empeños

## Archivos creados (principales)

- `docs/plan_jdm_empenos.md`
- `docs/manual_local.md`, `docs/manual_render.md`, `docs/manual_exe.md`, `docs/fase1_cierre.md`
- `app/` (factory, config, extensions, models, services, repositories, forms, blueprints, templates, static)
- `scripts/install_local.ps1`, `scripts/install_local.sh`, `scripts/create_superadmin.py`
- `tests/test_phase1_auth.py`, `tests/test_phase1_branches_users.py`, `tests/conftest.py`
- `requirements.txt`, `.env.example`, `Procfile`, `render.yaml`, `run.py`, `README.md`

## Rutas implementadas

- `/`, `/login`, `/logout`, `/forgot-password`, `/reset-password/<token>`
- `/dashboard/`
- `/branches/`, `/branches/create`, `/branches/<id>/edit`, activate/deactivate
- `/users/`, `/users/create`, `/users/<id>/edit`, `/users/profile/password`
- `/settings/`
- `/audit/`, `/audit/logins`
- `/healthz`

## Tablas creadas

- `roles`, `permissions`, `role_permissions`
- `branches`, `users`
- `settings`, `backups`
- `audit_logs`, `login_logs`

## Funciones pendientes (siguientes fases)

- Clientes, deliverers, fotos, firmas (Fase 2)
- Empeños y cálculos (Fase 3)
- Pagos/renovaciones (Fase 4)
- Compras/ventas/inventario (Fase 5)
- Caja/reportes (Fase 6)
- Notificaciones/backups avanzados (Fase 7)
- `.exe` y endurecimiento final (Fase 8)

## Pruebas ejecutadas

```text
pytest → 12 passed
```

Cobertura Fase 1: healthz, login, bloqueo por intentos, permisos, Decimal/RD$, sucursales, usuarios, configuración, auditoría, dashboard protegido.

## Resultado

**Fase 1 completada sin errores críticos.** Lista para iniciar Fase 2.

## Riesgos controlados en Fase 1

- Secretos solo por entorno
- Permisos validados en backend
- Bloqueo por intentos fallidos
- Timeout de sesión
- CSRF activo fuera de testing
- Dinero con `Decimal` (utilidad lista)
- `DATABASE_URL=null` del sistema ignorada (fallback SQLite)
- Driver PostgreSQL: `psycopg` v3 (compatible Python 3.13)

## Errores corregidos durante la fase

1. `psycopg2-binary` no compilaba en Python 3.13 → migrado a `psycopg[binary]`.
2. `DATABASE_URL=null` rompía el arranque → validación de placeholders.
3. Comparación aware/naive en bloqueo de login con SQLite → normalización UTC.
4. Emails `.local` rechazados por validador → dominio `example.com` en seeds/pruebas.