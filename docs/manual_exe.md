# Manual de empaquetado `.exe` — JDM Empeños

## Requisitos
- Windows 10/11
- Entorno virtual del proyecto con dependencias instaladas
- PyInstaller (el script lo instala)

## Generar el ejecutable

```powershell
cd "ruta\del\proyecto"
.\.venv\Scripts\Activate.ps1
.\scripts\build_exe.ps1
```

Salida: `dist\JDM_Empenos\JDM_Empenos.exe`

## Primera ejecución en mostrador
1. Copie la carpeta `dist\JDM_Empenos` al PC destino.
2. Cree un archivo `.env` junto al `.exe` con al menos:
   - `SECRET_KEY=` (cadena larga aleatoria)
   - `FLASK_ENV=production`
   - `DATABASE_URL=` vacío o `sqlite:///...` en carpeta de datos
3. Arranque el exe; abra http://127.0.0.1:5000
4. Entre con superadmin (o ejecute `create_superadmin` en un PC de preparación y copie la BD).
5. Haga un respaldo desde Configuración.

## Notas
- No incruste secretos en el binario.
- Preferible guardar BD y `uploads` en `%APPDATA%\JDM Empenos`.
- Firmas/fotos siguen en disco, no en la base.
- Para actualizaciones: respalde, reemplace el exe/carpeta y restaure si hace falta.
