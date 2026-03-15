"""
Exporter: escribe el dataset en los formatos de salida soportados.

Formatos clásicos (CLI): JSONL, CSV, TXT.
Formato curator: export_sets() — una categoría por archivo JSONL.
"""
import csv
import json
from pathlib import Path

import jsonlines
from rich.console import Console

console = Console()


# ─────────────────────────────────────────────────────────────────────────────
# Exportadores clásicos (compatibilidad con el pipeline CLI existente)
# ─────────────────────────────────────────────────────────────────────────────

def export_jsonl(pairs: list[dict], output_path: str) -> int:
    """
    Exporta pares instruction/output a formato JSONL para fine-tuning.

    Returns:
        Número de entradas escritas.
    """
    path = Path(output_path).with_suffix(".jsonl")
    path.parent.mkdir(parents=True, exist_ok=True)
    with jsonlines.open(path, mode="w") as writer:
        for pair in pairs:
            writer.write({"instruction": pair["instruction"], "output": pair["output"]})
    console.log(f"[green]JSONL exportado:[/green] {path} ({len(pairs)} entradas)")
    return len(pairs)


def export_csv(pairs: list[dict], output_path: str) -> int:
    """
    Exporta pares instruction/output a formato CSV.

    Returns:
        Número de entradas escritas.
    """
    path = Path(output_path).with_suffix(".csv")
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["instruction", "output"], extrasaction="ignore")
        writer.writeheader()
        writer.writerows(pairs)
    console.log(f"[green]CSV exportado:[/green] {path} ({len(pairs)} entradas)")
    return len(pairs)


def export_txt(pairs: list[dict], output_path: str) -> int:
    """
    Exporta pares instruction/output a texto plano.
    Formato: bloque de contexto + línea del personaje, separados por línea en blanco.

    Returns:
        Número de entradas escritas.
    """
    path = Path(output_path).with_suffix(".txt")
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for pair in pairs:
            if pair["instruction"]:
                f.write(pair["instruction"] + "\n")
            f.write(pair["output"] + "\n")
            f.write("\n")
    console.log(f"[green]TXT exportado:[/green] {path} ({len(pairs)} entradas)")
    return len(pairs)


def export(
    pairs: list[dict],
    output_path: str,
    formats: list[str],
) -> dict[str, int]:
    """
    Exporta el dataset en todos los formatos solicitados.

    Args:
        pairs:       Lista de pares instruction/output.
        output_path: Ruta base del archivo de salida (sin extensión).
        formats:     Lista de formatos: ["jsonl", "csv", "txt"].

    Returns:
        Dict {formato: cantidad_de_entradas}.
    """
    results = {}
    exporters = {
        "jsonl": export_jsonl,
        "csv": export_csv,
        "txt": export_txt,
    }

    for fmt in formats:
        fmt = fmt.lower()
        if fmt in exporters:
            results[fmt] = exporters[fmt](pairs, output_path)
        else:
            console.log(f"[yellow]Formato no soportado ignorado: '{fmt}'[/yellow]")

    return results


# ─────────────────────────────────────────────────────────────────────────────
# Exportador curator — 6 listas categorizadas
# ─────────────────────────────────────────────────────────────────────────────

# Nombres estándar de categorías producidas por curator/classifier.py
CURATOR_CATEGORIES = [
    "dialogue_clean",
    "dialogue_mixed_thought",
    "dialogue_mixed_action",
    "thought_only",       # archivado — no apto para training principal
    "action_only",        # archivado — no apto para training principal
    "overlength",         # archivado — excede tokens óptimos
]


def export_sets(
    sets: dict[str, list[dict]],
    output_dir: str,
) -> dict[str, int]:
    """
    Exporta conjuntos de datos clasificados a archivos JSONL separados.

    Cada clave del dict `sets` genera su propio archivo JSONL en output_dir.
    Los archivos vacíos (lista vacía) no se crean.

    Args:
        sets:       Dict {nombre_categoria: [entradas]}.
                    Categorías estándar: dialogue_clean, dialogue_mixed_thought,
                    dialogue_mixed_action, thought_only, action_only, overlength.
        output_dir: Directorio donde escribir los archivos.

    Returns:
        Dict {nombre_categoria: cantidad_de_entradas} para sets no vacíos.
    """
    dir_path = Path(output_dir)
    dir_path.mkdir(parents=True, exist_ok=True)

    results = {}
    for set_name, entries in sets.items():
        if not entries:
            continue
        path = dir_path / f"{set_name}.jsonl"
        with jsonlines.open(path, mode="w") as writer:
            for entry in entries:
                writer.write(entry)
        console.log(f"[green]{set_name}:[/green] {path} ({len(entries)} entradas)")
        results[set_name] = len(entries)

    return results
