"""
Config: rutas compartidas del proyecto.

Centraliza constantes de paths para que CLI y GUI usen siempre los mismos
directorios independientemente del directorio de trabajo actual.
"""
from pathlib import Path

# Raíz del proyecto: modules/scraper/ → modules/ → /wikier/
ROOT_DIR     = Path(__file__).parent.parent.parent

PROFILES_DIR = ROOT_DIR / "profiles"
OUTPUT_DIR   = ROOT_DIR / "output"
CACHE_DIR    = ROOT_DIR / ".cache"
INDEX_DIR    = CACHE_DIR / "indexes"
