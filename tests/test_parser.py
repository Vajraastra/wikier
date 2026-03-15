"""
Tests unitarios del parser con muestras hardcodeadas de ambos formatos.
Basados en el transcript de Miraculous Ladybug como wiki primario.
"""
import pytest
from modules.scraper.parser import parse_dialogue, detect_format, DialogueLine


# ─────────────────────────────────────────────────────────────────────────────
# Muestras hardcodeadas — Formato bold-colon
# ─────────────────────────────────────────────────────────────────────────────

SAMPLE_BOLD_COLON = """\
'''Marinette:''' ¡Buenos días, Tikki!
''[Marinette se estira en la cama]''
'''Tikki:''' ¡Buenos días, Marinette! Es hora de levantarse.
'''Marinette:''' Cinco minutos más...
'''Tikki:''' ¡Marinette, llegarás tarde!
'''Marinette (nerviosa):''' ¡Tienes razón!
'''Adrien:''' Hola, ¿todo bien?
'''Marinette:''' P-perfecto... todo perfectamente bien.
''[Marinette se sonroja]''
'''Nino:''' Adrien, tenemos que irnos.
'''Adrien:''' Nos vemos, Marinette.
"""

SAMPLE_BOLD_COLON_MIXED_ITALICS = """\
'''Chat Noir:''' ¿Lista, Milady?
''Mi-lady'' es un apodo cariñoso de Chat Noir.
'''Ladybug:''' Siempre lista. ¡Lucky Charm!
''[Una cuerda de saltar aparece en sus manos]''
'''Chat Noir:''' ¿Una cuerda? Creativo como siempre.
"""

# ─────────────────────────────────────────────────────────────────────────────
# Muestras hardcodeadas — Formato template
# ─────────────────────────────────────────────────────────────────────────────

SAMPLE_TEMPLATE = """\
{{Dialogue
|marinette=Marinette
|marinette|¡Buenos días, Tikki!
|tikki|Buenos días, Marinette.
|marinette|¿Estás lista para hoy?
|tikki|Siempre lista.
}}
"""

# ─────────────────────────────────────────────────────────────────────────────
# Tests de detección de formato
# ─────────────────────────────────────────────────────────────────────────────

class TestFormatDetection:
    def test_detect_bold_colon(self):
        fmt = detect_format(SAMPLE_BOLD_COLON)
        assert fmt == "bold-colon"

    def test_detect_template(self):
        fmt = detect_format(SAMPLE_TEMPLATE)
        assert fmt == "template"

    def test_detect_unknown_returns_unknown(self):
        fmt = detect_format("No hay diálogo aquí. Solo texto plano.")
        assert fmt == "unknown"

    def test_detect_empty_wikitext(self):
        fmt = detect_format("")
        assert fmt == "unknown"


# ─────────────────────────────────────────────────────────────────────────────
# Tests de parseo — bold-colon
# ─────────────────────────────────────────────────────────────────────────────

class TestBoldColonParser:
    def setup_method(self):
        self.lines, self.fmt = parse_dialogue(SAMPLE_BOLD_COLON, format_hint="bold-colon")

    def test_format_detected_correctly(self):
        assert self.fmt == "bold-colon"

    def test_extracts_correct_number_of_dialogue_lines(self):
        # Marinette x3, Tikki x2, Marinette(nerviosa) x1, Adrien x2, Nino x1 = 9
        dialogue_lines = [l for l in self.lines if not l.is_action]
        assert len(dialogue_lines) == 9

    def test_speaker_names_extracted_correctly(self):
        speakers = [l.speaker for l in self.lines if not l.is_action]
        assert "Marinette" in speakers
        assert "Tikki" in speakers
        assert "Adrien" in speakers
        assert "Nino" in speakers

    def test_action_lines_detected(self):
        actions = [l for l in self.lines if l.is_action]
        assert len(actions) == 2
        assert all(l.speaker is None for l in actions)

    def test_text_extracted_correctly(self):
        marinette_lines = [l for l in self.lines if l.speaker == "Marinette"]
        texts = [l.text for l in marinette_lines]
        assert "¡Buenos días, Tikki!" in texts
        assert "Cinco minutos más..." in texts

    def test_speaker_with_parenthetical(self):
        # '''Marinette (nerviosa):''' debe capturar "Marinette (nerviosa)" como speaker
        speakers = [l.speaker for l in self.lines if not l.is_action]
        assert any("nerviosa" in (s or "") for s in speakers)

    def test_no_empty_text_lines(self):
        for line in self.lines:
            assert line.text != ""

    def test_mixed_italics_sample(self):
        lines, _ = parse_dialogue(SAMPLE_BOLD_COLON_MIXED_ITALICS, format_hint="bold-colon")
        dialogue = [l for l in lines if not l.is_action]
        assert any(l.speaker == "Chat Noir" for l in dialogue)
        assert any(l.speaker == "Ladybug" for l in dialogue)


# ─────────────────────────────────────────────────────────────────────────────
# Tests de parseo — template
# ─────────────────────────────────────────────────────────────────────────────

class TestTemplateParser:
    def setup_method(self):
        self.lines, self.fmt = parse_dialogue(SAMPLE_TEMPLATE, format_hint="template")

    def test_format_detected_correctly(self):
        assert self.fmt == "template"

    def test_no_empty_text_lines(self):
        for line in self.lines:
            assert line.text != ""


# ─────────────────────────────────────────────────────────────────────────────
# Tests de auto-detección
# ─────────────────────────────────────────────────────────────────────────────

class TestAutoDetection:
    def test_auto_bold_colon(self):
        lines, fmt = parse_dialogue(SAMPLE_BOLD_COLON)
        assert fmt == "bold-colon"
        assert len(lines) > 0

    def test_auto_unknown_returns_empty(self):
        lines, fmt = parse_dialogue("Solo texto plano sin diálogo.")
        assert fmt == "unknown"
        assert lines == []


# ─────────────────────────────────────────────────────────────────────────────
# Tests de DialogueLine
# ─────────────────────────────────────────────────────────────────────────────

class TestDialogueLine:
    def test_dialogue_line_defaults(self):
        line = DialogueLine(speaker="Marinette", text="Hola")
        assert not line.is_action

    def test_action_line_has_no_speaker(self):
        line = DialogueLine(speaker=None, text="Marinette voltea", is_action=True)
        assert line.speaker is None
        assert line.is_action
