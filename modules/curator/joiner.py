"""
Joiner: preparación final del dataset para entrenamiento.

Pasos del pipeline:
    1. merge      — combina sets del curator con pesos por objetivo
    2. shuffle    — ordena aleatoriamente con seed reproducible
    3. split      — divide en train / validation / test
    4. export     — escribe los archivos finales JSONL

Módulo de conversión de formatos (standalone):
    load_file     — carga cualquier archivo soportado (JSONL, CSV, TXT)
    detect_format — auto-detección de formato por contenido de la primera entrada
    convert_file  — convierte un archivo a un formato JSONL de destino

Formatos soportados:
    chatml    — {"messages": [...]}
    alpaca    — {"instruction": ..., "input": ..., "output": ...}
    sharegpt  — {"system": ..., "conversations": [...]}
    jsonl_raw — {"instruction": ..., "output": ...}
    csv       — columnas: system | instruction | output  (sin headers de formato)
    txt       — bloques [SYSTEM] / [USER] / [CHAR]

Uso básico:
    entries = merge(result.formatted, objective="dialogue")
    entries = shuffle(entries, seed=42)
    train, val, test = split(entries, train=0.8, val=0.1, test=0.1)
    paths = export(train, val, test, output_dir=Path("output"), prefix="Marinette")

Conversión de formato:
    n = convert_file(Path("dialogue_clean.csv"), Path("out.jsonl"), target_fmt="chatml")
"""

import csv
import json
import logging
import random
import re
from pathlib import Path
from typing import Optional

from modules.curator import formatter as _formatter

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Objetivos de entrenamiento
# ─────────────────────────────────────────────────────────────────────────────

# Cada objetivo define qué categorías del curator se incluyen y sus pesos
# relativos cuando se aplica muestreo proporcional (max_entries).
OBJECTIVES: dict[str, dict] = {
    "dialogue": {
        "label":      "Solo diálogo limpio",
        "categories": ["dialogue_clean"],
        "weights":    {"dialogue_clean": 1.0},
    },
    "roleplay": {
        "label":      "Roleplay (limpio + mixed)",
        "categories": ["dialogue_clean", "dialogue_mixed_thought", "dialogue_mixed_action"],
        "weights":    {"dialogue_clean": 0.5, "dialogue_mixed_thought": 0.3, "dialogue_mixed_action": 0.2},
    },
    "both": {
        "label":      "Diálogo + Roleplay",
        "categories": ["dialogue_clean", "dialogue_mixed_thought", "dialogue_mixed_action"],
        "weights":    {"dialogue_clean": 0.7, "dialogue_mixed_thought": 0.2, "dialogue_mixed_action": 0.1},
    },
}

SUPPORTED_FORMATS = ("chatml", "alpaca", "sharegpt", "jsonl_raw", "csv", "txt")


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline: merge → shuffle → split → export
# ─────────────────────────────────────────────────────────────────────────────

def merge(
    sets: dict[str, list[dict]],
    objective: str = "dialogue",
    max_entries: Optional[int] = None,
) -> list[dict]:
    """
    Combina los sets del curator en una sola lista según el objetivo.

    Sin max_entries: concatena todas las entradas de las categorías activas.
    Con max_entries: muestrea proporcionalmente a los pesos del objetivo,
                     respetando el total disponible si es menor al límite.

    Args:
        sets:        Dict {categoría: [entradas]} del CuratorResult.formatted.
        objective:   "dialogue", "roleplay" o "both".
        max_entries: Límite total de entradas. None = sin límite.

    Returns:
        Lista plana de entradas mezcladas.
    """
    if objective not in OBJECTIVES:
        logger.warning("Objetivo '%s' no reconocido. Usando 'dialogue'.", objective)
        objective = "dialogue"

    obj       = OBJECTIVES[objective]
    cats      = obj["categories"]
    weights   = obj["weights"]

    # Filtrar a las categorías activas disponibles en sets
    available = {c: sets[c] for c in cats if c in sets and sets[c]}

    if not available:
        logger.warning("No hay entradas para el objetivo '%s'.", objective)
        return []

    if max_entries is None:
        # Sin límite — concatenar todo
        result: list[dict] = []
        for cat in cats:
            result.extend(available.get(cat, []))
        return result

    # Con límite — muestreo proporcional a pesos
    # Normalizar pesos a las categorías disponibles
    total_weight = sum(weights[c] for c in available)
    result = []

    for cat, entries in available.items():
        w          = weights[cat] / total_weight
        target     = round(max_entries * w)
        target     = min(target, len(entries))   # nunca más del disponible
        result.extend(entries[:target])

    # Si quedamos cortos por redondeo, completar con lo que sobre
    if len(result) < max_entries:
        taken = {e["_idx"] for e in result if "_idx" in e}
        for cat, entries in available.items():
            for e in entries:
                if len(result) >= max_entries:
                    break
                if e not in result:
                    result.append(e)

    return result[:max_entries]


def shuffle(entries: list[dict], seed: int = 42) -> list[dict]:
    """
    Mezcla la lista con seed fija para reproducibilidad.

    Args:
        entries: Lista de entradas (salida de merge).
        seed:    Semilla aleatoria.

    Returns:
        Nueva lista mezclada (la original no se modifica).
    """
    result = list(entries)
    random.seed(seed)
    random.shuffle(result)
    return result


def split(
    entries: list[dict],
    train:   float = 0.8,
    val:     float = 0.1,
    test:    float = 0.1,
) -> tuple[list[dict], list[dict], list[dict]]:
    """
    Divide la lista en train / validation / test.

    Los ratios se normalizan automáticamente si no suman 1.0.

    Args:
        entries: Lista de entradas mezcladas.
        train:   Proporción para entrenamiento (default 0.8).
        val:     Proporción para validación (default 0.1).
        test:    Proporción para test (default 0.1).

    Returns:
        Tupla (train_list, val_list, test_list).
    """
    total = train + val + test
    if total == 0:
        raise ValueError("Los ratios de split no pueden sumar 0.")

    # Normalizar
    train /= total
    val   /= total
    # test = 1 - train - val (evita error de punto flotante)

    n       = len(entries)
    i_train = int(n * train)
    i_val   = i_train + int(n * val)

    return entries[:i_train], entries[i_train:i_val], entries[i_val:]


def export(
    train:      list[dict],
    val:        list[dict],
    test:       list[dict],
    output_dir: Path,
    prefix:     str = "",
) -> list[str]:
    """
    Escribe los tres splits como archivos JSONL.

    El formato de las entradas debe ser el ya producido por el formatter
    del curator (chatml, alpaca, sharegpt o jsonl_raw). El joiner no
    re-formatea — solo serializa.

    Args:
        train, val, test: Listas de entradas (salida de split).
        output_dir:       Directorio de destino.
        prefix:           Prefijo para los nombres de archivo (ej: "Marinette").

    Returns:
        Lista de rutas escritas (solo las que tienen entradas).
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    sep   = "_" if prefix else ""
    paths = []

    for name, data in [("train", train), ("validation", val), ("test", test)]:
        if not data:
            continue
        path = output_dir / f"{prefix}{sep}{name}.jsonl"
        with open(path, "w", encoding="utf-8") as f:
            for entry in data:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        logger.info("Exportado: %s (%d entradas)", path, len(data))
        paths.append(str(path))

    return paths


# ─────────────────────────────────────────────────────────────────────────────
# Conversor de formatos
# ─────────────────────────────────────────────────────────────────────────────

def detect_format(entry: dict) -> str:
    """
    Auto-detecta el formato de una entrada JSONL.

    Args:
        entry: Primera entrada del archivo.

    Returns:
        "chatml", "sharegpt", "alpaca" o "jsonl_raw".
    """
    if "messages" in entry:
        return "chatml"
    if "conversations" in entry:
        return "sharegpt"
    if "instruction" in entry and "input" in entry:
        return "alpaca"
    return "jsonl_raw"


def _normalize(entry: dict, source_fmt: str) -> dict:
    """
    Convierte una entrada de cualquier formato al dict canónico interno:
        {"system": str, "instruction": str, "clean": str}

    Este formato es el que espera formatter.format_entry().
    """
    if source_fmt == "chatml":
        system = ""
        instruction = "[COMPLETAR]"
        clean = ""
        for msg in entry.get("messages", []):
            role = msg.get("role", "")
            if role == "system":
                system = msg.get("content", "")
            elif role == "user":
                instruction = msg.get("content", "")
            elif role == "assistant":
                clean = msg.get("content", "")
        return {"system": system, "instruction": instruction, "clean": clean}

    if source_fmt == "sharegpt":
        system = entry.get("system", "")
        instruction = "[COMPLETAR]"
        clean = ""
        for turn in entry.get("conversations", []):
            if turn.get("from") == "human":
                instruction = turn.get("value", "")
            elif turn.get("from") == "gpt":
                clean = turn.get("value", "")
        return {"system": system, "instruction": instruction, "clean": clean}

    if source_fmt == "alpaca":
        # En Alpaca el system puede estar embebido al inicio de instruction
        return {
            "system":      entry.get("system", ""),
            "instruction": entry.get("instruction", ""),
            "clean":       entry.get("output", ""),
        }

    # jsonl_raw, csv (ya normalizado al leer), txt
    return {
        "system":      entry.get("system", ""),
        "instruction": entry.get("instruction", "[COMPLETAR]"),
        "clean":       entry.get("output", entry.get("clean", "")),
    }


def load_file(path: Path) -> tuple[list[dict], str]:
    """
    Carga un archivo de dataset en cualquier formato soportado.

    Args:
        path: Ruta al archivo (.jsonl, .json, .csv, .txt).

    Returns:
        Tupla (entries, source_fmt) donde source_fmt es uno de SUPPORTED_FORMATS.

    Raises:
        ValueError: Si el formato no es reconocible.
    """
    path = Path(path)
    ext  = path.suffix.lower()

    # ── CSV ───────────────────────────────────────────────────────────────────
    if ext == ".csv":
        entries = []
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                entries.append({
                    "system":      row.get("system", ""),
                    "instruction": row.get("instruction", "[COMPLETAR]"),
                    "output":      row.get("output", ""),
                })
        return entries, "csv"

    # ── TXT — bloques [SYSTEM] / [USER] / [CHAR] ─────────────────────────────
    if ext == ".txt":
        entries = _load_txt(path)
        return entries, "txt"

    # ── JSONL / JSON ──────────────────────────────────────────────────────────
    entries = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                logger.warning("Línea JSON inválida ignorada en %s", path)

    if not entries:
        return [], "jsonl_raw"

    return entries, detect_format(entries[0])


def _load_txt(path: Path) -> list[dict]:
    """
    Parsea el formato TXT del curator:
        [SYSTEM] texto  (opcional)
        [USER]   texto
        [CHAR]   texto
        (línea en blanco = fin de bloque)
    """
    entries = []
    system = ""
    instruction = "[COMPLETAR]"
    output = ""
    in_block = False

    _SYS  = re.compile(r"^\[SYSTEM\]\s*(.*)", re.IGNORECASE)
    _USER = re.compile(r"^\[USER\]\s*(.*)",   re.IGNORECASE)
    _CHAR = re.compile(r"^\[CHAR\]\s*(.*)",   re.IGNORECASE)

    def _flush():
        nonlocal system, instruction, output, in_block
        if in_block and output:
            entries.append({"system": system, "instruction": instruction, "output": output})
        system = ""
        instruction = "[COMPLETAR]"
        output = ""
        in_block = False

    for raw in path.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()

        if not stripped:
            _flush()
            continue

        m = _SYS.match(stripped)
        if m:
            system  = m.group(1).strip()
            in_block = True
            continue

        m = _USER.match(stripped)
        if m:
            instruction = m.group(1).strip()
            in_block = True
            continue

        m = _CHAR.match(stripped)
        if m:
            output  = m.group(1).strip()
            in_block = True
            continue

        # Línea de continuación — agregar al campo más reciente
        if in_block and output:
            output += " " + stripped
        elif in_block and instruction != "[COMPLETAR]":
            instruction += " " + stripped

    _flush()
    return entries


def convert_file(
    input_path:  Path,
    output_path: Path,
    target_fmt:  str,
    source_fmt:  Optional[str] = None,
) -> int:
    """
    Convierte un archivo de dataset a un formato JSONL de destino.

    Args:
        input_path:  Archivo fuente (.jsonl, .csv, .txt).
        output_path: Archivo de destino (.jsonl).
        target_fmt:  Formato de salida: "chatml", "alpaca", "sharegpt", "jsonl_raw".
        source_fmt:  Formato fuente. None = auto-detectar.

    Returns:
        Número de entradas convertidas.

    Raises:
        ValueError: Si target_fmt no es uno de los formatos JSONL válidos.
    """
    _jsonl_fmts = ("chatml", "alpaca", "sharegpt", "jsonl_raw")
    if target_fmt not in _jsonl_fmts:
        raise ValueError(
            f"target_fmt debe ser uno de {_jsonl_fmts}, no '{target_fmt}'."
        )

    entries, detected_fmt = load_file(input_path)
    if source_fmt is None:
        source_fmt = detected_fmt

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    count = 0
    with open(output_path, "w", encoding="utf-8") as f:
        for entry in entries:
            canonical = _normalize(entry, source_fmt)
            converted = _formatter.format_entry(canonical, fmt=target_fmt)
            f.write(json.dumps(converted, ensure_ascii=False) + "\n")
            count += 1

    logger.info(
        "Convertido: %s → %s (%s → %s, %d entradas)",
        input_path, output_path, source_fmt, target_fmt, count,
    )
    return count
