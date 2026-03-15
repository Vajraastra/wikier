#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# run.sh — Script de lanzamiento del Fandom Dialogue Scraper
# Sin argumentos   → GUI (PySide6)
# Con --cli ...    → CLI (Typer)
# Ejemplo CLI:     ./run.sh --cli scrape --wiki miraculousladybug -c Marinette
# ─────────────────────────────────────────────────────────────────────────────

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"
REQUIREMENTS="$PROJECT_DIR/requirements.txt"

echo "──────────────────────────────────────────────"
echo " Fandom Dialogue Scraper — Iniciando entorno"
echo "──────────────────────────────────────────────"

# 1. Verificar Python 3.10+
PYTHON=$(command -v python3 || command -v python)
if [ -z "$PYTHON" ]; then
    echo "[ERROR] Python no encontrado. Instalá Python 3.10+."
    exit 1
fi

PYTHON_VERSION=$($PYTHON -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "[OK] Python $PYTHON_VERSION encontrado en $PYTHON"

# 2. Detectar si el venv existente es compatible con el Python actual
VENV_PYTHON="$VENV_DIR/bin/python"
RECREATE=false

if [ ! -d "$VENV_DIR" ]; then
    RECREATE=true
elif [ -f "$VENV_PYTHON" ]; then
    VENV_VER=$("$VENV_PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "unknown")
    if [ "$VENV_VER" != "$PYTHON_VERSION" ]; then
        echo "[WARN] Venv creado con Python $VENV_VER, sistema tiene $PYTHON_VERSION. Recreando..."
        rm -rf "$VENV_DIR"
        RECREATE=true
    fi
fi

# 3. Crear venv si es necesario
if [ "$RECREATE" = true ]; then
    echo "[INFO] Creando entorno virtual en $VENV_DIR ..."
    $PYTHON -m venv "$VENV_DIR"
    echo "[OK] Entorno virtual creado."
else
    echo "[OK] Entorno virtual existente en $VENV_DIR"
fi

# 4. Bootstrapear pip si no está disponible
if ! "$VENV_DIR/bin/python" -m pip --version &>/dev/null; then
    echo "[INFO] pip no encontrado en venv, bootstrapeando con ensurepip..."
    "$VENV_DIR/bin/python" -m ensurepip --upgrade
    echo "[OK] pip instalado."
fi

# 5. Instalar/verificar dependencias
echo "[INFO] Verificando dependencias desde $REQUIREMENTS ..."
"$VENV_DIR/bin/python" -m pip install --quiet --upgrade pip
"$VENV_DIR/bin/python" -m pip install --quiet -r "$REQUIREMENTS"
echo "[OK] Dependencias instaladas."

echo "──────────────────────────────────────────────"

# 6. Lanzar GUI o CLI
if [ $# -eq 0 ]; then
    echo " Lanzando GUI (PySide6)..."
    echo "──────────────────────────────────────────────"
    "$VENV_DIR/bin/python" "$PROJECT_DIR/main.py"
else
    echo " Modo CLI: $*"
    echo "──────────────────────────────────────────────"
    "$VENV_DIR/bin/python" "$PROJECT_DIR/main.py" "$@"
fi
