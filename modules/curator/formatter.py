"""
Formatter: convierte entradas del curator al formato final para fine-tuning.

Formatos soportados:
    chatml    — LLaMA, Mistral, Qwen (default)
    alpaca    — instrucción / input / output
    sharegpt  — conversaciones multi-turno
    jsonl_raw — JSONL sin formato especial (instruction + output)

Cada entrada de entrada debe tener:
    'output'      — respuesta del personaje (campo del classifier)
    'clean'       — versión limpia del texto (sin stage directions)
    'instruction' — prompt del usuario (puede ser '[COMPLETAR]')
    'system'      — system prompt (opcional, inyectado por system_prompt_builder)

El formatter usa 'clean' para el output formateado, no 'output' original.
Si 'instruction' es '[COMPLETAR]' o vacío, se omite el turno de usuario
(el dataset queda listo para completar manualmente o con LLM).
"""

import json


# ─────────────────────────────────────────────────────────────────────────────
# Constantes
# ─────────────────────────────────────────────────────────────────────────────

PLACEHOLDER = "[COMPLETAR]"
SUPPORTED_FORMATS = ("chatml", "alpaca", "sharegpt", "jsonl_raw")


# ─────────────────────────────────────────────────────────────────────────────
# Formatos
# ─────────────────────────────────────────────────────────────────────────────

def _to_chatml(entry: dict) -> dict:
    """
    Formato ChatML — estándar para LLaMA 3, Mistral, Qwen.

    Estructura:
        {
            "messages": [
                {"role": "system",    "content": "..."},  # opcional
                {"role": "user",      "content": "..."},  # opcional si [COMPLETAR]
                {"role": "assistant", "content": "..."}
            ]
        }
    """
    messages = []

    system = entry.get("system", "")
    if system:
        messages.append({"role": "system", "content": system})

    instruction = entry.get("instruction", "")
    if instruction and instruction != PLACEHOLDER:
        messages.append({"role": "user", "content": instruction})

    messages.append({"role": "assistant", "content": entry.get("clean", "")})

    return {"messages": messages}


def _to_alpaca(entry: dict) -> dict:
    """
    Formato Alpaca — para modelos con template instrucción/respuesta.

    Estructura:
        {
            "instruction": "...",
            "input":       "",       # vacío si no hay contexto extra
            "output":      "..."
        }
    """
    instruction = entry.get("instruction", "")
    system = entry.get("system", "")

    # Si hay system prompt, se prepende a la instrucción
    if system:
        full_instruction = f"{system}\n\n{instruction}" if instruction and instruction != PLACEHOLDER else system
    else:
        full_instruction = instruction if instruction != PLACEHOLDER else ""

    return {
        "instruction": full_instruction,
        "input":       "",
        "output":      entry.get("clean", ""),
    }


def _to_sharegpt(entry: dict) -> dict:
    """
    Formato ShareGPT — conversaciones multi-turno.

    Estructura:
        {
            "system":         "...",         # opcional
            "conversations":  [
                {"from": "human", "value": "..."},  # opcional si [COMPLETAR]
                {"from": "gpt",   "value": "..."}
            ]
        }
    """
    result: dict = {}

    system = entry.get("system", "")
    if system:
        result["system"] = system

    conversations = []
    instruction = entry.get("instruction", "")
    if instruction and instruction != PLACEHOLDER:
        conversations.append({"from": "human", "value": instruction})

    conversations.append({"from": "gpt", "value": entry.get("clean", "")})
    result["conversations"] = conversations

    return result


def _to_jsonl_raw(entry: dict) -> dict:
    """
    JSONL crudo — mantiene instruction/output sin transformar.
    Incluye system prompt si está disponible.
    """
    result: dict = {
        "instruction": entry.get("instruction", ""),
        "output":      entry.get("clean", ""),
    }
    system = entry.get("system", "")
    if system:
        result["system"] = system
    return result


# ─────────────────────────────────────────────────────────────────────────────
# API pública
# ─────────────────────────────────────────────────────────────────────────────

_FORMATTERS = {
    "chatml":    _to_chatml,
    "alpaca":    _to_alpaca,
    "sharegpt":  _to_sharegpt,
    "jsonl_raw": _to_jsonl_raw,
}


def format_entry(entry: dict, fmt: str = "chatml") -> dict:
    """
    Formatea una entrada individual.

    Args:
        entry:  Entrada del curator con campos 'clean', 'instruction', 'system'.
        fmt:    Formato de salida: 'chatml', 'alpaca', 'sharegpt', 'jsonl_raw'.

    Returns:
        Dict en el formato solicitado.

    Raises:
        ValueError: Si el formato no es soportado.
    """
    fmt = fmt.lower()
    if fmt not in _FORMATTERS:
        raise ValueError(f"Formato no soportado: '{fmt}'. Usa: {SUPPORTED_FORMATS}")
    return _FORMATTERS[fmt](entry)


def format_sets(
    sets: dict[str, list[dict]],
    fmt: str = "chatml",
) -> dict[str, list[dict]]:
    """
    Formatea todos los sets del curator.

    Args:
        sets:  Dict {categoría: [entradas]} del pipeline curator.
        fmt:   Formato de salida.

    Returns:
        Dict {categoría: [entradas_formateadas]}.
    """
    return {
        cat: [format_entry(e, fmt) for e in entries]
        for cat, entries in sets.items()
        if entries
    }


def serialize(entries: list[dict]) -> str:
    """
    Serializa una lista de entradas a string JSONL (una por línea).
    Útil para preview en la GUI.
    """
    return "\n".join(json.dumps(e, ensure_ascii=False) for e in entries)
