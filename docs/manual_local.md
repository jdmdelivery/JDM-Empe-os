# Manual de instalación local — JDM Empeños

## 1. Requisitos

- Windows 10/11
- Python 3.11 o superior
- PowerShell

## 2. Instalación rápida

```powershell
cd "C:\Users\...\JDM Empeños"
.\scripts\install_local.ps1
```

El script:

1. Crea entorno virtual `.venv`
2. Instala dependencias
3. Crea `.env` desde `.env.example`
4. Inicializa la base SQLite
5. Crea el superadministrador

## 3. Ejecutar

```powershell
.\.venv\Scripts\Activate.ps1
python run.py
```

URL: http://127.0.0.1:5000

## 4. Credenciales iniciales

- Usuario: `superadmin`
- Contraseña: `Cambiar123!`

El sistema pedirá cambiar la contraseña al primer ingreso.

## 5. Base de datos local

Por defecto se usa SQLite en:

`instance/jdm_empenos.db`

No configure PostgreSQL en desarrollo salvo que lo necesite explícitamente.

## 6. Pruebas

```powershell
pytest -q
```