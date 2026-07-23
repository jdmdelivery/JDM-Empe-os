# Manual de despliegue en Render — JDM Empeños

## 1. Preparación

- Repositorio Git con el código
- Cuenta en Render
- `render.yaml` incluido en el proyecto

## 2. Variables requeridas

| Variable | Valor |
|----------|-------|
| `FLASK_ENV` | `production` |
| `SECRET_KEY` | generada (no compartir) |
| `DATABASE_URL` | conexión PostgreSQL de Render |
| `SESSION_COOKIE_SECURE` | `1` |
| `BUSINESS_CURRENCY_SYMBOL` | `RD$` |
| `BUSINESS_TIMEZONE` | `America/Santo_Domingo` |

## 3. Base de datos

Use PostgreSQL gestionado por Render. El sistema convierte automáticamente URLs `postgres://` a `postgresql://`.

## 4. Migraciones y superadmin

Desde el Shell de Render:

```bash
export FLASK_APP=run.py
flask db upgrade
python scripts/create_superadmin.py --password "UNA_CLAVE_SEGURA"
```

## 5. Health check

Ruta: `/healthz`

## 6. Archivos / uploads

En el plan gratuito de Render el disco es efímero. Para producción real configure almacenamiento persistente (S3 u otro) en fases posteriores.