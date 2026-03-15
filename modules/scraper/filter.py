"""
Filter: extrae líneas del personaje objetivo para dataset de fine-tuning.
Normaliza aliases del personaje para unificar variantes del nombre.

Formato de salida:
  - "instruction": vacío (el curador lo rellena con la pregunta del usuario).
  - "output":      línea del personaje tal como aparece en el transcript.
"""
from modules.scraper.parser import DialogueLine


def _normalize(name: str) -> str:
    """Normaliza un nombre de personaje para comparación."""
    return name.strip().lower()


def build_alias_set(target: str, aliases: list[str]) -> set[str]:
    """
    Construye el set de aliases normalizados para el personaje objetivo.

    Args:
        target:  Nombre principal del personaje.
        aliases: Lista de variantes adicionales del nombre.

    Returns:
        Set de strings normalizados.
    """
    return {_normalize(a) for a in [target] + aliases}


def filter_character(
    lines: list[DialogueLine],
    target: str,
    aliases: list[str] | None = None,
    context_window: int = 3,
    include_actions: bool = False,
) -> list[dict]:
    """
    Filtra las líneas del personaje objetivo y construye pares instruction/output.

    Cada par contiene:
      - "instruction": las N líneas de contexto ANTES de la línea objetivo (diálogo previo).
      - "output":      la línea del personaje objetivo.
      - "page":        título de la página de origen (se añade externamente).

    Args:
        lines:          Lista de DialogueLine del parser.
        target:         Nombre del personaje objetivo.
        aliases:        Variantes adicionales del nombre (opcional).
        context_window: Número de líneas de contexto anteriores a incluir.
        include_actions: Si True, incluye action lines en el contexto.

    Returns:
        Lista de dicts con campos "instruction" y "output".
    """
    alias_set = build_alias_set(target, aliases or [])
    pairs = []

    # Filtrar action lines del flujo de contexto si no se solicitan
    relevant_lines = lines if include_actions else [l for l in lines if not l.is_action]

    for i, line in enumerate(relevant_lines):
        if line.speaker is None:
            continue  # action line, no es línea de personaje
        if _normalize(line.speaker) not in alias_set:
            continue

        output = f"{target}: {line.text}"

        pairs.append({
            "instruction": "[COMPLETAR]",
            "output": output,
        })

    return pairs
