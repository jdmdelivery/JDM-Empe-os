#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> JDM Empeños · instalación local"

python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Archivo .env creado desde .env.example"
fi

mkdir -p instance uploads
export FLASK_APP=run.py
flask db init || true
flask db migrate -m "fase1_inicial" || true
flask db upgrade
python scripts/create_superadmin.py

echo ""
echo "Instalación completada."
echo "Active el entorno: source .venv/bin/activate"
echo "Ejecute: python run.py"