"""
System Prompt Builder: genera el system prompt para fine-tuning desde el perfil JSON.

Sin dependencias de ML ni APIs externas — solo template filling.

Diseño:
    - Template con variables {character}, {show}, {personality}, {aliases}, etc.
    - Variables resueltas desde el perfil JSON del personaje.
    - Campos activos controlados por 'system_prompt_fields' del perfil.
    - El usuario puede proveer un template propio con cualquier variable.
    - Variables desconocidas en el template se dejan vacías (sin error).
    - Compatible con uso standalone (sin haber usado el scraper).
"""

from string import Formatter
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# Templates por defecto
# ─────────────────────────────────────────────────────────────────────────────

# Template base — siempre disponible aunque el perfil no tenga personality
DEFAULT_TEMPLATE = (
    "You are {character}, a character from {show}. "
    "Respond to all messages as {character} would, staying in character at all times."
)

# Template extendido — se usa automáticamente si el perfil tiene personality
DEFAULT_TEMPLATE_WITH_PERSONALITY = (
    "You are {character}, a character from {show}. "
    "{personality} "
    "Respond to all messages as {character} would, staying in character at all times."
)

# Template con aliases — cuando el personaje tiene nombres alternativos relevantes
DEFAULT_TEMPLATE_WITH_ALIASES = (
    "You are {character} (also known as {aliases}), a character from {show}. "
    "Respond to all messages as {character} would, staying in character at all times."
)

# Template completo — personality + aliases
DEFAULT_TEMPLATE_FULL = (
    "You are {character} (also known as {aliases}), a character from {show}. "
    "{personality} "
    "Respond to all messages as {character} would, staying in character at all times."
)


# ─────────────────────────────────────────────────────────────────────────────
# Construcción de variables desde perfil
# ─────────────────────────────────────────────────────────────────────────────

def _format_aliases(aliases: list[str], character: str) -> str:
    """
    Formatea la lista de aliases excluyendo el nombre principal.
    Ejemplo: ["Marinette", "Ladybug", "Bridgette"] → "Ladybug, Bridgette"
    """
    filtered = [a for a in aliases if a.lower() != character.lower()]
    return ", ".join(filtered) if filtered else ""


def build_variables(
    profile: dict,
    character: str,
    extra_vars: Optional[dict[str, str]] = None,
) -> dict[str, str]:
    """
    Construye el dict de variables para rellenar el template desde el perfil JSON.

    Variables estándar resueltas:
        {character}   — nombre del personaje objetivo
        {show}        — nombre del show/wiki (campo 'name' del perfil)
        {personality} — descripción de personalidad (campo 'personality' del perfil)
        {aliases}     — aliases del personaje, excluyendo el nombre principal
        {language}    — código ISO del idioma del perfil

    Args:
        profile:    Dict del perfil JSON cargado.
        character:  Nombre del personaje para quien se construye el prompt.
        extra_vars: Variables adicionales definidas por el usuario.

    Returns:
        Dict {nombre_variable: valor_string}.
    """
    character_aliases = profile.get("character_aliases", {})

    # Buscar aliases del personaje (case-insensitive)
    aliases_list: list[str] = []
    for name, alias_list in character_aliases.items():
        if name.lower() == character.lower():
            aliases_list = alias_list
            break

    variables: dict[str, str] = {
        "character":   character,
        "show":        profile.get("name", ""),
        "personality": profile.get("personality", ""),
        "aliases":     _format_aliases(aliases_list, character),
        "language":    profile.get("language", "en"),
    }

    # Campos extra definidos en el perfil (claves arbitrarias en system_prompt_fields)
    extra_fields = profile.get("system_prompt_fields", {})
    for key, active in extra_fields.items():
        if active and key not in variables:
            variables[key] = str(profile.get(key, ""))

    # Variables adicionales del usuario (tienen prioridad sobre todo)
    if extra_vars:
        variables.update(extra_vars)

    return variables


# ─────────────────────────────────────────────────────────────────────────────
# Selección automática de template
# ─────────────────────────────────────────────────────────────────────────────

def _select_default_template(variables: dict[str, str], fields: dict) -> str:
    """Elige el template por defecto más completo según los campos disponibles."""
    has_personality = bool(variables.get("personality"))
    has_aliases = bool(variables.get("aliases"))

    show_aliases = fields.get("aliases", True)
    show_personality = fields.get("personality", True)

    if has_personality and has_aliases and show_personality and show_aliases:
        return DEFAULT_TEMPLATE_FULL
    elif has_personality and show_personality:
        return DEFAULT_TEMPLATE_WITH_PERSONALITY
    elif has_aliases and show_aliases:
        return DEFAULT_TEMPLATE_WITH_ALIASES
    return DEFAULT_TEMPLATE


def _safe_format(template: str, variables: dict[str, str]) -> str:
    """
    Rellena el template con las variables disponibles.
    Variables desconocidas se dejan como string vacío (sin lanzar KeyError).
    """
    # Extraer todas las variables referenciadas en el template
    keys_in_template = {
        field_name
        for _, field_name, _, _ in Formatter().parse(template)
        if field_name is not None
    }

    # Construir dict con solo las claves necesarias, vacío si no existe
    safe_vars = {k: variables.get(k, "") for k in keys_in_template}
    return template.format(**safe_vars).strip()


# ─────────────────────────────────────────────────────────────────────────────
# API pública
# ─────────────────────────────────────────────────────────────────────────────

def build(
    profile: dict,
    character: str,
    template: Optional[str] = None,
    extra_vars: Optional[dict[str, str]] = None,
) -> str:
    """
    Genera el system prompt para un personaje a partir del perfil JSON.

    Args:
        profile:    Dict del perfil JSON (miraculousladybug.json, etc.).
        character:  Nombre del personaje objetivo.
        template:   Template con variables {var}. None → selección automática.
        extra_vars: Variables adicionales {nombre: valor} para el template.

    Returns:
        System prompt listo para incrustar en las muestras del dataset.
    """
    fields = profile.get("system_prompt_fields", {})
    variables = build_variables(profile, character, extra_vars)

    selected_template = template or _select_default_template(variables, fields)
    return _safe_format(selected_template, variables)


def preview(
    profile: dict,
    character: str,
    template: Optional[str] = None,
    extra_vars: Optional[dict[str, str]] = None,
) -> dict:
    """
    Retorna un dict con el prompt generado y los metadatos para mostrar en la GUI.

    Returns:
        {
            "prompt":     system prompt final,
            "template":   template utilizado,
            "variables":  dict de variables resueltas,
            "character":  nombre del personaje,
        }
    """
    fields = profile.get("system_prompt_fields", {})
    variables = build_variables(profile, character, extra_vars)
    selected_template = template or _select_default_template(variables, fields)
    prompt = _safe_format(selected_template, variables)

    return {
        "prompt":    prompt,
        "template":  selected_template,
        "variables": variables,
        "character": character,
    }


def inject_system_prompt(
    sets: dict[str, list[dict]],
    system_prompt: str,
    ratio: float = 1.0,
    seed: Optional[int] = 42,
) -> dict[str, list[dict]]:
    """
    Inyecta el system prompt en las entradas del dataset según el ratio indicado.

    ratio=1.0 → todas las entradas reciben el system prompt.
    ratio=0.7 → 70% reciben system prompt, 30% no tienen campo 'system'.
    Mezclar es recomendable: el modelo aprende a responder con y sin instrucciones.

    Args:
        sets:          Dict {categoría: [entradas]}.
        system_prompt: Texto del system prompt a incrustar.
        ratio:         Proporción de entradas que reciben el prompt (0.0–1.0).
        seed:          Seed para reproducibilidad. None = no reproducible.

    Returns:
        El mismo dict mutado.
    """
    import random
    rng = random.Random(seed)

    for entries in sets.values():
        for entry in entries:
            if ratio >= 1.0 or rng.random() < ratio:
                entry["system"] = system_prompt
            # Si no se asigna, el campo 'system' permanece ausente
    return sets
