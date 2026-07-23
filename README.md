# JDM Empeños

Sistema profesional para administrar compra, venta y empeño de artículos.

- **Idioma:** Español  
- **Moneda:** RD$ (Pesos dominicanos)  
- **Zona horaria:** America/Santo_Domingo  
- **Backend:** Flask + SQLAlchemy + Flask-Migrate  
- **BD:** SQLite (desarrollo) · PostgreSQL (producción / Render)  

## Estado

**Sistema completo (Fases 1–8):** autenticación, clientes, artículos, empeños, pagos, renovaciones, compras, inventario, ventas, caja, gastos, reportes, notificaciones (cola), backups, exportaciones y documentación de despliegue.

Documentación:

- [`docs/plan_jdm_empenos.md`](docs/plan_jdm_empenos.md)
- [`docs/fase2_cierre.md`](docs/fase2_cierre.md)
- [`docs/fase3_a_6_cierre.md`](docs/fase3_a_6_cierre.md)
- [`docs/fase7_cierre.md`](docs/fase7_cierre.md)
- [`docs/fase8_cierre.md`](docs/fase8_cierre.md)

## Requisitos

- Python 3.11+
- Windows 10/11 (también Linux/macOS)
- PostgreSQL (solo producción)

## Instalación local (Windows)

```powershell
cd "ruta\del\proyecto"
.\scripts\install_local.ps1
.\.venv\Scripts\Activate.ps1
Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
$env:FLASK_APP = "run.py"
flask db upgrade
python run.py
```

Abra: http://127.0.0.1:5000

Usuario inicial (cambiar al entrar):

- Usuario: `superadmin`
- Correo: `admin@example.com`
- Contraseña: `Cambiar123!`

## Variables de entorno

Copie `.env.example` a `.env` y ajuste los valores. **No** guarde secretos en el código.

Notificaciones (opcional): `SMTP_*`, `WHATSAPP_API_*`, `SMS_API_*`.

## Comandos útiles

```powershell
python scripts\create_superadmin.py

$env:FLASK_APP = "run.py"
flask db migrate -m "descripcion"
flask db upgrade

pytest -q

.\scripts\build_exe.ps1
```

## Render (producción)

1. Conecte el repositorio en Render.
2. Use `render.yaml` o configure:
   - Build: `pip install -r requirements.txt`
   - Start: `gunicorn "run:app" --bind 0.0.0.0:$PORT`
   - Health check: `/healthz`
3. Asigne `DATABASE_URL` de PostgreSQL y `SECRET_KEY`.
4. Ejecute migraciones y `scripts/create_superadmin.py` en un job/shell.

Manuales:

- [`docs/manual_local.md`](docs/manual_local.md)
- [`docs/manual_render.md`](docs/manual_render.md)
- [`docs/manual_exe.md`](docs/manual_exe.md)

## Módulos principales

| Ruta | Módulo |
|------|--------|
| `/dashboard` | Panel |
| `/customers` `/deliverers` `/items` | Clientes y artículos |
| `/search` | Búsqueda global |
| `/pawn` `/payments` `/renewals` `/expired` | Empeños y cobros |
| `/purchases` `/inventory` `/sales` | Comercio |
| `/cash` `/expenses` `/reports` | Caja y reportes |
| `/settings` | Configuración y backups |
| `/audit` | Auditoría |
| `/healthz` | Salud |

## Licencia / uso

Software privado para el negocio JDM Empeños.
