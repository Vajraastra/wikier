"""
Classifier: clasifica líneas de diálogo en 5 categorías para curación de dataset.

Categorías:
    dialogue_clean          — diálogo puro, sin embebidos
    dialogue_mixed_thought  — diálogo real con pensamiento interno embebido
    dialogue_mixed_action   — diálogo real con acción/stage direction embebida
    thought_only            — solo pensamientos, sin diálogo real (archivado)
    action_only             — solo stage directions, sin diálogo real (archivado)

Cada categoría puede tener patrones regex configurables por perfil JSON.
Sin perfil, se usan los defaults (válidos para la mayoría de wikis Fandom).
"""

import re
from dataclasses import dataclass, field
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# Patrones por defecto
# ─────────────────────────────────────────────────────────────────────────────

# Acciones/stage directions: texto entre paréntesis — (walks to door)
_DEFAULT_ACTION_PATTERN = r"\(([^)]{1,200})\)"

# Pensamientos internos: texto en itálicas wiki — ''thinking out loud''
# También soporta formato RP común: *texto*
_DEFAULT_THOUGHT_PATTERNS = [
    r"''([^']{1,200})''",   # wiki italics
    r"\*([^*]{1,200})\*",   # asteriscos RP-style
]

# Texto mínimo fuera de embebidos para considerar que hay "diálogo real"
# Bajo (2) a propósito: exclamaciones cortas ("Ah!", "No.") son diálogo válido.
# quality_scorer filtrará por calidad en el siguiente paso del pipeline.
_MIN_DIALOGUE_CHARS = 2


# ─────────────────────────────────────────────────────────────────────────────
# Tipos de datos
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class EmbeddedSegment:
    """Un fragmento embebido dentro de la línea de diálogo."""
    type: str        # "action" | "thought"
    content: str     # texto sin los delimitadores
    position: str    # "start" | "middle" | "end"


@dataclass
class ClassifiedLine:
    """Resultado de clasificar una línea de diálogo."""
    category: str                            # una de las 5 categorías
    speaker: str                             # nombre del personaje
    original: str                            # texto original (sin prefijo speaker)
    clean: str                               # texto sin embebidos
    embedded: list[EmbeddedSegment] = field(default_factory=list)
    episode: Optional[str] = None
    context_prev: Optional[str] = None      # turno anterior (para context_builder)


# ─────────────────────────────────────────────────────────────────────────────
# Funciones internas
# ─────────────────────────────────────────────────────────────────────────────

def _strip_speaker(output_field: str) -> tuple[str, str]:
    """
    Separa 'Speaker: texto' en (speaker, texto).
    Si no hay ':', retorna ('', output_field).
    """
    if ":" in output_field:
        speaker, _, text = output_field.partition(":")
        return speaker.strip(), text.strip()
    return "", output_field.strip()


def _has_real_dialogue(text: str, min_chars: int = _MIN_DIALOGUE_CHARS) -> bool:
    """
    Retorna True si el texto tiene suficiente contenido real
    (no solo espacios, puntuación o markup residual).
    """
    # Eliminar puntuación y espacios para la comprobación
    stripped = re.sub(r"[\s.,!?;:\-–—\"'()[\]{}]", "", text)
    return len(stripped) >= min_chars


def _determine_position(match_start: int, match_end: int, text_len: int) -> str:
    """
    Estima si un segmento embebido está al inicio, medio o final del texto.
    """
    mid = text_len / 2
    if match_start < text_len * 0.25:
        return "start"
    elif match_end > text_len * 0.75:
        return "end"
    return "middle"


def _extract_embedded(
    text: str,
    action_pattern: str,
    thought_patterns: list[str],
) -> tuple[str, list[EmbeddedSegment]]:
    """
    Extrae todos los segmentos embebidos del texto.

    Retorna:
        (texto_limpio, lista_de_segmentos)
    """
    segments: list[EmbeddedSegment] = []
    text_len = len(text)
    clean = text

    # — Acciones (paréntesis)
    for match in re.finditer(action_pattern, text, re.IGNORECASE):
        pos = _determine_position(match.start(), match.end(), text_len)
        segments.append(EmbeddedSegment(
            type="action",
            content=match.group(1).strip(),
            position=pos,
        ))
    clean = re.sub(action_pattern, "", clean, flags=re.IGNORECASE)

    # — Pensamientos (múltiples patrones)
    for tpat in thought_patterns:
        for match in re.finditer(tpat, text):
            pos = _determine_position(match.start(), match.end(), text_len)
            segments.append(EmbeddedSegment(
                type="thought",
                content=match.group(1).strip(),
                position=pos,
            ))
        clean = re.sub(tpat, "", clean)

    # Normalizar espacios residuales
    clean = re.sub(r"\s{2,}", " ", clean).strip()

    return clean, segments


# ─────────────────────────────────────────────────────────────────────────────
# API pública
# ─────────────────────────────────────────────────────────────────────────────

def classify(
    entry: dict,
    action_pattern: Optional[str] = None,
    thought_patterns: Optional[list[str]] = None,
) -> ClassifiedLine:
    """
    Clasifica una entrada del dataset (formato instruction/output de exporter.py).

    Args:
        entry:            Dict con al menos la clave 'output' ("Speaker: texto").
                          Opcionalmente 'episode' y 'context_prev'.
        action_pattern:   Regex para stage directions. None → usa default.
        thought_patterns: Lista de regex para pensamientos. None → usa defaults.

    Returns:
        ClassifiedLine con categoría, texto limpio y segmentos embebidos.
    """
    ap = action_pattern or _DEFAULT_ACTION_PATTERN
    tp = thought_patterns or _DEFAULT_THOUGHT_PATTERNS

    speaker, original = _strip_speaker(entry.get("output", ""))
    clean, embedded = _extract_embedded(original, ap, tp)

    has_actions = any(s.type == "action" for s in embedded)
    has_thoughts = any(s.type == "thought" for s in embedded)
    has_dialogue = _has_real_dialogue(clean)

    # — Clasificación
    if not embedded:
        category = "dialogue_clean"
    elif has_dialogue and has_thoughts and not has_actions:
        category = "dialogue_mixed_thought"
    elif has_dialogue and has_actions:
        # mixed_action tiene prioridad si hay acciones (más comunes en Fandom)
        category = "dialogue_mixed_action"
    elif not has_dialogue and has_thoughts:
        category = "thought_only"
    else:
        # sin diálogo real, solo acciones (o embebidos sin diálogo fuera)
        category = "action_only"

    return ClassifiedLine(
        category=category,
        speaker=speaker,
        original=original,
        clean=clean,
        embedded=embedded,
        episode=entry.get("episode"),
        context_prev=entry.get("context_prev"),
    )


def classify_dataset(
    entries: list[dict],
    action_pattern: Optional[str] = None,
    thought_patterns: Optional[list[str]] = None,
) -> dict[str, list[dict]]:
    """
    Clasifica una lista completa de entradas y agrupa por categoría.

    Retorna un dict listo para pasar a exporter.export_sets():
        {
            "dialogue_clean":         [...],
            "dialogue_mixed_thought": [...],
            "dialogue_mixed_action":  [...],
            "thought_only":           [...],
            "action_only":            [...],
        }

    Cada entrada del dict incluye el schema extendido:
        {
            "instruction": ...,
            "output": ...,          # original sin modificar
            "clean": ...,           # texto limpio (sin embebidos)
            "speaker": ...,
            "embedded": [...],      # lista de {type, content, position}
            "episode": ...,
            "context_prev": ...,
        }
    """
    sets: dict[str, list[dict]] = {
        "dialogue_clean": [],
        "dialogue_mixed_thought": [],
        "dialogue_mixed_action": [],
        "thought_only": [],
        "action_only": [],
    }

    for entry in entries:
        result = classify(entry, action_pattern, thought_patterns)
        extended = {
            "instruction": entry.get("instruction", ""),
            "output": entry.get("output", ""),
            "clean": result.clean,
            "speaker": result.speaker,
            "embedded": [
                {"type": s.type, "content": s.content, "position": s.position}
                for s in result.embedded
            ],
            "episode": result.episode,
            "context_prev": result.context_prev,
        }
        sets[result.category].append(extended)

    return sets
