# Manual de despliegue en Render — JDM Empeños

## 0. Versión de Python

En Environment de Render agregue:

| Variable | Valor |
|----------|-------|
| `PYTHON_VERSION` | `3.11.11` |

También hay un archivo `.python-version` en el repo. Sin esto, Render puede usar Python 3.14 y fallar con SQLAlchemy.

## 1. Preparación

- Repositorio Git con el código
- Cuenta en Render
- `render.yaml` incluido en el proyecto

## 2. Comandos del servicio

| Campo | Valor |
|-------|-------|
| Build Command | `pip install -r requirements.txt` |
| Start Command | `flask db upgrade && python scripts/create_superadmin.py && gunicorn "run:app" --bind 0.0.0.0:$PORT --workers 2 --timeout 120` |

## 3. Variables requeridas

| Variable | Valor |
|----------|-------|
| `FLASK_APP` | `run.py` |
| `FLASK_ENV` | `production` |
| `SECRET_KEY` | generada (no compartir) |
| `DATABASE_URL` | conexión PostgreSQL de Render |
| `SESSION_COOKIE_SECURE` | `1` |
| `BUSINESS_CURRENCY_SYMBOL` | `RD$` |
| `BUSINESS_TIMEZONE` | `America/Santo_Domingo` |
| `SUPERADMIN_USERNAME` | su usuario admin |
| `SUPERADMIN_EMAIL` | correo admin |
| `SUPERADMIN_PASSWORD` | contraseña segura |

## 4. Base de datos

Use PostgreSQL gestionado por Render. El sistema convierte automáticamente URLs `postgres://` a `postgresql://`.

Sin `DATABASE_URL` o sin `flask db upgrade`, `/login` puede devolver Internal Server Error.

## 5. Health check

Ruta: `/healthz`

## 6. Archivos / uploads

En el plan gratuito de Render el disco es efímero. Para producción real configure almacenamiento persistente (S3 u otro) en fases posteriores.
