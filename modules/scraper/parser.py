"""
Parser: detecta el formato de diálogo y extrae pares (speaker, text) del wikitext.

Formatos soportados:
  - bold-colon : '''Speaker:''' texto de la línea
  - template   : {{dialogue|speaker|texto}} (via mwparserfromhell)
  - auto       : detecta automáticamente por densidad de patrones
"""
import re
import logging
from dataclasses import dataclass, field

import mwparserfromhell

logger = logging.getLogger(__name__)

# Nombres de templates de diálogo conocidos en wikis de Fandom
DIALOGUE_TEMPLATE_NAMES = {
    "dialogue", "dialog", "diálogo",
    "ep dialogue", "episode dialogue",
    "script", "transcript line",
}

# Regex para el formato bold-colon
# Captura: '''Speaker (nota opcional):''' texto
_BOLD_COLON_RE = re.compile(
    r"^'''([^']+?):'''\s*(.*?)\s*$",
    re.MULTILINE,
)

# Regex para detectar action lines en cursiva: ''[acción]'' o ''narración''
_ACTION_LINE_RE = re.compile(r"^\s*''(.+?)''\s*$")

# Regex para limpiar marcado wikitext residual de un texto plano
_WIKITEXT_CLEAN_RE = re.compile(r"\[{2}[^\]]*?\|?([^\]]*?)\]{2}|'{2,3}|\{\{[^}]+\}\}")


@dataclass
class DialogueLine:
    """Representa una línea de diálogo parseada."""
    speaker: str | None       # None si es action line
    text: str
    is_action: bool = False
    raw: str = field(default="", repr=False)


def _clean_text(text: str) -> str:
    """Elimina marcado wikitext residual de un string de texto plano."""
    # Reemplaza [[link|texto]] → texto, [[link]] → link
    text = re.sub(r"\[\[(?:[^\]|]*?\|)?([^\]]+?)\]\]", r"\1", text)
    # Elimina negritas/cursivas
    text = re.sub(r"'{2,3}", "", text)
    # Elimina templates simples residuales
    text = re.sub(r"\{\{[^{}]+\}\}", "", text)
    return text.strip()


# ─────────────────────────────────────────────────────────────────────────────
# Detección de formato
# ─────────────────────────────────────────────────────────────────────────────

def detect_format(wikitext: str) -> str:
    """
    Detecta el formato de diálogo dominante en el wikitext.

    Returns:
        "bold-colon", "template", o "mixed"
    """
    bold_colon_count = len(_BOLD_COLON_RE.findall(wikitext))

    # Buscar templates de diálogo conocidos
    template_count = 0
    wikicode = mwparserfromhell.parse(wikitext)
    for template in wikicode.filter_templates():
        name = template.name.strip().lower()
        if any(known in name for known in DIALOGUE_TEMPLATE_NAMES):
            template_count += 1

    if bold_colon_count == 0 and template_count == 0:
        return "unknown"
    if template_count > bold_colon_count:
        return "template"
    if bold_colon_count > 0 and template_count > 0:
        return "mixed"
    return "bold-colon"


# ─────────────────────────────────────────────────────────────────────────────
# Parsers por formato
# ─────────────────────────────────────────────────────────────────────────────

def _parse_bold_colon(wikitext: str) -> list[DialogueLine]:
    """
    Extrae líneas de diálogo en formato bold-colon.
    También captura action lines en cursiva entre líneas de diálogo.
    """
    lines = []

    for raw_line in wikitext.split("\n"):
        # Intento de speaker line: '''Name:''' texto
        match = _BOLD_COLON_RE.match(raw_line.strip())
        if match:
            speaker = _clean_text(match.group(1))
            text = _clean_text(match.group(2))
            if text:
                lines.append(DialogueLine(speaker=speaker, text=text, raw=raw_line))
            else:
                # Línea de speaker sin texto inmediato — el texto viene en la siguiente línea
                # Se guarda el speaker para que el bloque siguiente lo adjunte
                lines.append(DialogueLine(speaker=speaker, text="", raw=raw_line))
            continue

        # Action line en cursiva: ''[acción]'' o ''narración''
        action_match = _ACTION_LINE_RE.match(raw_line)
        if action_match:
            text = _clean_text(action_match.group(1))
            if text:
                lines.append(DialogueLine(speaker=None, text=text, is_action=True, raw=raw_line))
            continue

        # Texto de continuación: si la última línea tenía speaker pero no texto
        if lines and lines[-1].speaker and not lines[-1].text:
            text = _clean_text(raw_line.strip())
            if text and not text.startswith("{") and not text.startswith("|"):
                lines[-1].text = text

    # Descartar entradas sin texto
    return [l for l in lines if l.text]


def _parse_template(wikitext: str) -> list[DialogueLine]:
    """
    Extrae líneas de diálogo de templates {{dialogue}} via mwparserfromhell.
    Soporta variantes comunes del template en wikis de Fandom.
    """
    lines = []
    wikicode = mwparserfromhell.parse(wikitext)

    for template in wikicode.filter_templates():
        name = template.name.strip().lower()
        if not any(known in name for known in DIALOGUE_TEMPLATE_NAMES):
            continue

        # Procesar parámetros posicionales y nombrados
        for param in template.params:
            key = param.name.strip().lower()
            value = _clean_text(str(param.value))

            # Parámetro nombrado speaker=nombre (metadata, ignorar)
            # Parámetro posicional |speaker|texto o |texto
            if "|" in str(param):
                parts = str(param).split("|")
                if len(parts) >= 2:
                    speaker = _clean_text(parts[0])
                    text = _clean_text(parts[-1])
                    if speaker and text:
                        lines.append(DialogueLine(speaker=speaker, text=text))
                        continue

            # Formato alternativo: parámetro key es speaker, value es texto
            if value and key not in ("1", "2", "3") and not key.isdigit():
                # Evitar capturar parámetros de estilo/configuración del template
                if len(key) > 1 and not key.startswith("class") and not key.startswith("style"):
                    lines.append(DialogueLine(speaker=key.title(), text=value))

    return [l for l in lines if l.text]


# ─────────────────────────────────────────────────────────────────────────────
# Interfaz pública
# ─────────────────────────────────────────────────────────────────────────────

def parse_dialogue(
    wikitext: str,
    format_hint: str = "auto",
) -> tuple[list[DialogueLine], str]:
    """
    Punto de entrada principal del parser.

    Args:
        wikitext:    Wikitext crudo de la página.
        format_hint: "auto", "bold-colon", "template", o "mixed".

    Returns:
        Tupla (lista de DialogueLine, formato detectado).
    """
    detected = format_hint if format_hint != "auto" else detect_format(wikitext)

    if detected == "bold-colon":
        return _parse_bold_colon(wikitext), detected

    if detected == "template":
        return _parse_template(wikitext), detected

    if detected == "mixed":
        # Combinar ambos parsers, eliminando duplicados por texto
        bc_lines = _parse_bold_colon(wikitext)
        tmpl_lines = _parse_template(wikitext)
        seen = {l.text for l in bc_lines}
        combined = bc_lines + [l for l in tmpl_lines if l.text not in seen]
        return combined, detected

    # Formato no reconocido
    logger.warning("Formato de diálogo no reconocido en el wikitext proporcionado.")
    return [], "unknown"
