#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# run.sh — Script de lanzamiento del Fandom Dialogue Scraper
#
# Gestión de entorno completamente autónoma via uv:
#   - Descarga uv (binario único ~10 MB) si no está presente
#   - Instala Python 3.13 localmente si el sistema no lo tiene
#   - Crea y valida el venv con la versión correcta
#   - Instala dependencias
#
# Sin argumentos   → GUI (PySide6)
# Con --cli ...    → CLI (Typer)
# Ejemplo CLI:     ./run.sh --cli scrape --wiki miraculousladybug -c Marinette
# ─────────────────────────────────────────────────────────────────────────────

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"
TOOLS_DIR="$PROJECT_DIR/.tools"
UV="$TOOLS_DIR/uv"
REQUIREMENTS="$PROJECT_DIR/requirements.txt"

# Versión de Python requerida. spaCy 3.8 no es compatible con Python 3.14+.
REQUIRED_PYTHON="3.13"

echo "──────────────────────────────────────────────"
echo " Fandom Dialogue Scraper — Iniciando entorno"
echo "──────────────────────────────────────────────"

# ── 1. Obtener uv ─────────────────────────────────────────────────────────────
if [ ! -f "$UV" ]; then
    echo "[INFO] Descargando uv (gestor de Python y dependencias)..."
    mkdir -p "$TOOLS_DIR"

    ARCH=$(uname -m)
    case "$ARCH" in
        x86_64)  UV_ARCH="x86_64"  ;;
        aarch64) UV_ARCH="aarch64" ;;
        armv7l)  UV_ARCH="armv7"   ;;
        *)
            echo "[ERROR] Arquitectura '$ARCH' no soportada por uv."
            exit 1
            ;;
    esac

    UV_URL="https://github.com/astral-sh/uv/releases/latest/download/uv-${UV_ARCH}-unknown-linux-musl.tar.gz"
    curl -fsSL "$UV_URL" | tar -xz -C "$TOOLS_DIR" --strip-components=1
    chmod +x "$UV"
    echo "[OK] uv instalado en $UV"
else
    echo "[OK] uv disponible ($("$UV" --version 2>/dev/null || echo 'versión desconocida'))"
fi

# ── 2. Asegurar Python REQUIRED_PYTHON ────────────────────────────────────────
echo "[INFO] Verificando Python $REQUIRED_PYTHON..."
"$UV" python install "$REQUIRED_PYTHON" --quiet
echo "[OK] Python $REQUIRED_PYTHON disponible."

# ── 3. Crear o validar el venv ────────────────────────────────────────────────
RECREATE=false

if [ ! -d "$VENV_DIR" ]; then
    RECREATE=true
else
    # Verificar que el venv usa la versión de Python correcta
    PYVENV_CFG="$VENV_DIR/pyvenv.cfg"
    if [ -f "$PYVENV_CFG" ]; then
        # uv usa "version_info", pip usa "version" — aceptar ambos
        CFG_VER=$(grep -E "^version(_info)? " "$PYVENV_CFG" | head -1 | cut -d'=' -f2 | tr -d ' ' | cut -d'.' -f1-2)
        if [ "$CFG_VER" != "$REQUIRED_PYTHON" ]; then
            echo "[WARN] Venv usa Python $CFG_VER, se requiere $REQUIRED_PYTHON. Recreando..."
            rm -rf "$VENV_DIR"
            RECREATE=true
        fi
    else
        RECREATE=true
    fi
fi

if [ "$RECREATE" = true ]; then
    echo "[INFO] Creando entorno virtual con Python $REQUIRED_PYTHON..."
    "$UV" venv --python "$REQUIRED_PYTHON" --seed "$VENV_DIR"
    echo "[OK] Entorno virtual creado."
else
    echo "[OK] Entorno virtual existente (Python $REQUIRED_PYTHON)."
fi

# ── 4. Instalar / verificar dependencias ──────────────────────────────────────
echo "[INFO] Verificando dependencias desde $REQUIREMENTS ..."
"$UV" pip install --quiet -r "$REQUIREMENTS" --python "$VENV_DIR/bin/python"
echo "[OK] Dependencias instaladas."

echo "──────────────────────────────────────────────"

# ── 5. Lanzar GUI o CLI ───────────────────────────────────────────────────────
if [ $# -eq 0 ]; then
    echo " Lanzando GUI (PySide6)..."
    echo "──────────────────────────────────────────────"
    "$VENV_DIR/bin/python" "$PROJECT_DIR/main.py"
else
    echo " Modo CLI: $*"
    echo "──────────────────────────────────────────────"
    "$VENV_DIR/bin/python" "$PROJECT_DIR/main.py" "$@"
fi
