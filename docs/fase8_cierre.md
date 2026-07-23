# Cierre Fase 8 — Pruebas, seguridad, despliegue

## Pruebas
```powershell
.\.venv\Scripts\Activate.ps1
Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
pytest -q
```
Cobertura clave: auth, clientes/artículos, finanzas Decimal, pagos idempotentes, caja, snapshot de %.

## Seguridad (checklist)
- CSRF en formularios
- Contraseña inicial obligatoria a cambiar
- Bloqueo por intentos fallidos
- Timeout de sesión
- Cabeceras de seguridad
- Rate limit en login
- Archivos fuera de BD (SHA-256 en disco)
- Roles/permisos en rutas sensibles
- No enviar notificaciones sin tokens de entorno

## Render
Ver [`manual_render.md`](manual_render.md). Migrar con `flask db upgrade` y crear superadmin en shell.

## Ejecutable Windows
```powershell
.\scripts\build_exe.ps1
```
Detalle: [`manual_exe.md`](manual_exe.md)

## Estado
Sistema operativo completo para uso local (SQLite) y producción (PostgreSQL/Render), con módulos de empeño, pagos, comercio, caja, reportes, backups y documentación.
