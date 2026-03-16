"""
NameTagger: reemplaza nombres de personajes por tags genéricos.

Usa spaCy dependency parsing para distinguir dos contextos:
  - Vocativo / interacción directa → {{user}}   (personaje habla CON alguien)
  - Referencia a tercero           → {{char}}   (personaje habla SOBRE alguien)

El nombre del personaje principal NUNCA se reemplaza.

Presets de tags:
  - sillyTavern: {{user}} / {{char}}
  - oobabooga:   <|user|> / <|bot|>
  - generic:     [USER] / [CHAR]
  - custom:      configurables por el usuario
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

# ─────────────────────────────────────────────────────────────────────────────
# Presets de tags
# ─────────────────────────────────────────────────────────────────────────────

TAG_PRESETS: dict[str, tuple[str, str]] = {
    "sillytavern": ("{{user}}", "{{char}}"),
    "oobabooga":   ("<|user|>", "<|bot|>"),
    "generic":     ("[USER]",   "[CHAR]"),
}


# ─────────────────────────────────────────────────────────────────────────────
# Carga del roster
# ─────────────────────────────────────────────────────────────────────────────

def load_roster(roster_path: str | Path) -> dict:
    """
    Carga el JSON de personajes generado por export_character_roster.

    Returns:
        Dict con main_character, main_aliases, language, supporting_characters.
    """
    with open(roster_path, encoding="utf-8") as f:
        return json.load(f)


def find_roster(dataset_path: str | Path) -> Path | None:
    """
    Busca automáticamente el archivo {Character}_characters.json junto al dataset.

    Args:
        dataset_path: Ruta al archivo JSONL del dataset.

    Returns:
        Path al roster si existe, None si no se encuentra.
    """
    dataset_path = Path(dataset_path)
    stem = dataset_path.stem  # ej. "Marinette_dataset"
    character = stem.split("_")[0] if "_" in stem else stem
    roster_path = dataset_path.parent / f"{character}_characters.json"
    return roster_path if roster_path.exists() else None


# ─────────────────────────────────────────────────────────────────────────────
# Lógica de etiquetado
# ─────────────────────────────────────────────────────────────────────────────

# Verbs that introduce reported speech — these indicate 3rd-party reference
_REPORTED_SPEECH_VERBS = {
    "say", "said", "tell", "told", "ask", "asked",
    "think", "thought", "believe", "believed",
    "decir", "dijo", "dice", "preguntar", "preguntó",
    "dire", "dit", "demander", "demandé",
}

# Dependency relations that indicate the name is being TALKED ABOUT (→ {{char}})
_REFERENCE_DEPS = {"nsubj", "nsubjpass", "pobj", "dobj", "nmod", "attr", "appos"}


def _is_vocative(token, doc) -> bool:
    """
    Determina si un token es un vocativo (se le habla DIRECTAMENTE).

    Patrones:
    1. dep_ == "vocative"
    2. Name, ... (name at start followed by comma)
    3. ..., Name[.!?] (name at end after comma)
    4. Name! (solo el nombre seguido de puntuación exclamativa)
    """
    if token.dep_ == "vocative":
        return True

    # Patrón: "Name," al inicio del doc (primeros 2 tokens)
    if token.i <= 1:
        next_tok = doc[token.i + 1] if token.i + 1 < len(doc) else None
        if next_tok and next_tok.text in (",", "!"):
            return True

    # Patrón: "Name." / "Name!" / "Name?" al final del doc
    if token.i >= len(doc) - 3:
        prev_tok = doc[token.i - 1] if token.i > 0 else None
        if prev_tok and prev_tok.text == ",":
            return True
        next_tok = doc[token.i + 1] if token.i + 1 < len(doc) else None
        if next_tok and next_tok.text in (".", "!", "?"):
            return True

    return False


def _is_reported_speech_ref(token) -> bool:
    """
    Detecta si el nombre aparece cerca de un verbo de discurso reportado.
    Ej: "Adrien said...", "...told Adrien"
    """
    # Verifica el head del token (verbo que lo rige)
    if token.head.lemma_.lower() in _REPORTED_SPEECH_VERBS:
        return True
    # Verifica children del head
    for child in token.head.children:
        if child.lemma_.lower() in _REPORTED_SPEECH_VERBS:
            return True
    return False


def _classify_mention(token, doc) -> str:
    """
    Clasifica una mención de nombre como 'user' o 'char'.

    Returns:
        'user' si es vocativo/interacción directa.
        'char' si es referencia a tercero (fallback conservador).
    """
    if _is_vocative(token, doc):
        return "user"

    # Referencia sintáctica como sujeto/objeto en oración → {{char}}
    if token.dep_ in _REFERENCE_DEPS:
        return "char"

    # Discurso reportado → {{char}}
    if _is_reported_speech_ref(token):
        return "char"

    # Posesivo (Name's) → {{char}}
    if token.i + 1 < len(doc) and doc[token.i + 1].text in ("'s", "'s"):
        return "char"

    # Fallback conservador
    return "char"


def _build_alias_index(roster: dict) -> dict[str, str]:
    """
    Construye un mapa alias_lower → canonical_name para búsqueda rápida.
    El personaje principal y sus aliases se excluyen (nunca se reemplazan).
    """
    main_lower = {a.lower() for a in roster.get("main_aliases", [])}
    alias_index: dict[str, str] = {}

    for char_name, aliases in roster.get("supporting_characters", {}).items():
        for alias in aliases:
            low = alias.lower()
            if low not in main_lower:
                alias_index[low] = char_name

    return alias_index


def tag_text(
    text: str,
    nlp,
    alias_index: dict[str, str],
    user_tag: str = "{{user}}",
    char_tag: str = "{{char}}",
) -> str:
    """
    Reemplaza nombres de personajes secundarios en el texto.

    Args:
        text:        Texto a etiquetar.
        nlp:         Modelo spaCy cargado.
        alias_index: Mapa alias_lower → canonical_name.
        user_tag:    Tag para vocativo/interlocutor directo.
        char_tag:    Tag para referencia a tercero.

    Returns:
        Texto con nombres reemplazados.
    """
    if not text or not alias_index:
        return text

    doc = nlp(text)
    replacements: list[tuple[int, int, str]] = []  # (start_char, end_char, tag)

    for token in doc:
        low = token.lower_
        if low in alias_index:
            tag_type = _classify_mention(token, doc)
            tag = user_tag if tag_type == "user" else char_tag
            replacements.append((token.idx, token.idx + len(token.text), tag))

    if not replacements:
        return text

    # Aplicar reemplazos de atrás hacia adelante para no desplazar índices
    result = list(text)
    for start, end, tag in reversed(replacements):
        result[start:end] = list(tag)

    return "".join(result)


# ─────────────────────────────────────────────────────────────────────────────
# API principal
# ─────────────────────────────────────────────────────────────────────────────

def tag_entry(
    entry: dict[str, Any],
    nlp,
    alias_index: dict[str, str],
    user_tag: str = "{{user}}",
    char_tag: str = "{{char}}",
) -> dict[str, Any]:
    """
    Aplica el etiquetado a una entrada de dataset (cualquier formato).

    Modifica el campo 'output' (respuesta del personaje) — es el único campo
    donde aparecen referencias a otros personajes en el habla del personaje.
    El campo 'instruction' no se modifica (es el turno del interlocutor).
    """
    entry = dict(entry)  # copia superficial

    # ChatML: {messages: [{role, content}, ...]}
    if "messages" in entry:
        entry["messages"] = [
            {
                **msg,
                "content": (
                    tag_text(msg["content"], nlp, alias_index, user_tag, char_tag)
                    if msg.get("role") == "assistant"
                    else msg["content"]
                ),
            }
            for msg in entry["messages"]
        ]
        return entry

    # ShareGPT: {conversations: [{from, value}, ...]}
    if "conversations" in entry:
        entry["conversations"] = [
            {
                **turn,
                "value": (
                    tag_text(turn["value"], nlp, alias_index, user_tag, char_tag)
                    if turn.get("from") == "gpt"
                    else turn["value"]
                ),
            }
            for turn in entry["conversations"]
        ]
        return entry

    # Raw curator format: el formatter lee 'clean', no 'output'.
    # Se etiqueta 'clean' (texto normalizado que va al output final).
    # 'output' se etiqueta también para mantener coherencia si se usa directamente.
    if "clean" in entry:
        entry["clean"] = tag_text(entry["clean"], nlp, alias_index, user_tag, char_tag)
    if "output" in entry:
        entry["output"] = tag_text(entry["output"], nlp, alias_index, user_tag, char_tag)

    return entry


def tag_dataset(
    sets: dict[str, list[dict]],
    roster: dict,
    lang: str,
    user_tag: str = "{{user}}",
    char_tag: str = "{{char}}",
) -> dict[str, list[dict]]:
    """
    Aplica el etiquetado de nombres a todas las categorías del dataset.

    Args:
        sets:     Dict categoría → lista de entradas formateadas.
        roster:   Roster de personajes cargado con load_roster().
        lang:     Código ISO 639-1 del idioma (para cargar el modelo spaCy).
        user_tag: Tag para vocativo.
        char_tag: Tag para referencia a tercero.

    Returns:
        Nuevo dict con las mismas categorías pero entradas etiquetadas.
    """
    from modules.core.spacy_manager import load as load_spacy

    nlp = load_spacy(lang)
    alias_index = _build_alias_index(roster)

    if not alias_index:
        # Sin personajes secundarios — nada que reemplazar
        return sets

    return {
        cat: [tag_entry(e, nlp, alias_index, user_tag, char_tag) for e in entries]
        for cat, entries in sets.items()
    }
