"""
Tests unitarios del parser con muestras hardcodeadas de ambos formatos.
Basados en el transcript de Miraculous Ladybug como wiki primario.
"""
import pytest
from modules.scraper.parser import parse_dialogue, detect_format, DialogueLine


# ─────────────────────────────────────────────────────────────────────────────
# Muestras para multi-párrafo
# ─────────────────────────────────────────────────────────────────────────────

# Speaker con texto inicial + continuación en líneas siguientes
SAMPLE_MULTIPARAGRAPH_WITH_INITIAL = """\
'''Marinette:''' No puedo creer lo que pasó hoy.
Fue el peor día de mi vida.
De verdad. El peor.
'''Alya:''' ¿Tan malo fue?
'''Marinette:''' Sí. Pero mañana será mejor.
"""

# Speaker sin texto inicial + varias líneas de continuación
SAMPLE_MULTIPARAGRAPH_NO_INITIAL = """\
'''Marinette:'''
No puedo creer lo que pasó hoy.
Fue el peor día de mi vida.
'''Alya:''' ¿Tan malo fue?
"""

# Línea en blanco interrumpe la acumulación
SAMPLE_MULTIPARAGRAPH_BLANK_INTERRUPT = """\
'''Marinette:''' Primera línea.
Segunda línea.

'''Alya:''' ¡Hola!
'''Marinette:''' No sé nada de eso.
"""

# Action line interrumpe la acumulación
SAMPLE_MULTIPARAGRAPH_ACTION_INTERRUPT = """\
'''Marinette:''' Primera parte del discurso.
''[Marinette hace una pausa]''
'''Marinette:''' Segunda parte, separada por la acción.
"""

# Línea de narrador en cursiva (no es action line completa) no contamina el diálogo
SAMPLE_NARRATOR_ANNOTATION = """\
'''Chat Noir:''' ¿Lista, Milady?
''Mi-lady'' es un apodo cariñoso.
'''Ladybug:''' Siempre lista.
"""

# ─────────────────────────────────────────────────────────────────────────────
# Muestra realista de wikitext de Miraculous Ladybug
# ─────────────────────────────────────────────────────────────────────────────

SAMPLE_REALISTIC_ML = """\
==Intro==
''[Marinette está en su cuarto]''
'''Marinette:''' [narrando] Cada día tomo la misma ruta al colegio.
Y cada día pienso en Adrien.

==Escena 1==
'''Alya:''' ¡Marinette! ¿Escuchaste? ¡Hay un akuma en el centro!
'''Marinette:''' ¿Qué? Necesito encontrar un lugar para transformarme.
¡Te veo en la entrada del colegio!
''[Marinette corre hacia un callejón]''
'''Marinette:''' ¡Tikki, puntos activados!
''[Se transforma en Ladybug]''
'''Ladybug:''' ¡Vamos allá!
'''Alya:''' [al teléfono] ¡No puedo creer que me perdí la transformación otra vez!
"""


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


# ─────────────────────────────────────────────────────────────────────────────
# Tests de multi-párrafo
# ─────────────────────────────────────────────────────────────────────────────

class TestMultiParagraph:
    def test_continuation_lines_merged_into_speaker_text(self):
        """Tres líneas de continuación se unen al texto inicial del speaker."""
        lines, _ = parse_dialogue(SAMPLE_MULTIPARAGRAPH_WITH_INITIAL, format_hint="bold-colon")
        marinette = [l for l in lines if l.speaker == "Marinette" and not l.is_action]
        # La primera intervención de Marinette tiene el texto de las 3 líneas fusionadas
        first = marinette[0]
        assert "No puedo creer" in first.text
        assert "peor día" in first.text
        assert "De verdad" in first.text

    def test_continuation_without_initial_text(self):
        """Speaker line sin texto inicial acumula las líneas siguientes."""
        lines, _ = parse_dialogue(SAMPLE_MULTIPARAGRAPH_NO_INITIAL, format_hint="bold-colon")
        marinette = [l for l in lines if l.speaker == "Marinette"]
        assert len(marinette) == 1
        assert "No puedo creer" in marinette[0].text
        assert "peor día" in marinette[0].text

    def test_blank_line_ends_accumulation(self):
        """Una línea en blanco cierra el párrafo; el texto posterior no se fusiona."""
        lines, _ = parse_dialogue(SAMPLE_MULTIPARAGRAPH_BLANK_INTERRUPT, format_hint="bold-colon")
        marinette_lines = [l for l in lines if l.speaker == "Marinette" and not l.is_action]
        # La segunda intervención de Marinette es una entrada separada
        assert len(marinette_lines) == 2
        assert "Primera línea" in marinette_lines[0].text
        assert "Segunda línea" in marinette_lines[0].text
        assert "No sé nada" in marinette_lines[1].text

    def test_action_line_ends_accumulation(self):
        """Una action line interrumpe la acumulación y genera dos entradas separadas."""
        lines, _ = parse_dialogue(SAMPLE_MULTIPARAGRAPH_ACTION_INTERRUPT, format_hint="bold-colon")
        dialogue = [l for l in lines if not l.is_action]
        actions = [l for l in lines if l.is_action]
        assert len(dialogue) == 2
        assert len(actions) == 1
        assert "Primera parte" in dialogue[0].text
        assert "Segunda parte" in dialogue[1].text

    def test_narrator_annotation_not_merged(self):
        """Línea de anotación narrativa (empieza con '') no se fusiona al diálogo."""
        lines, _ = parse_dialogue(SAMPLE_NARRATOR_ANNOTATION, format_hint="bold-colon")
        chat = [l for l in lines if l.speaker == "Chat Noir"]
        assert len(chat) == 1
        # La anotación no debe aparecer en el texto de Chat Noir
        assert "apodo" not in chat[0].text

    def test_consecutive_speakers_no_bleed(self):
        """Dos speakers consecutivos no comparten texto entre sí."""
        lines, _ = parse_dialogue(SAMPLE_MULTIPARAGRAPH_WITH_INITIAL, format_hint="bold-colon")
        alya = [l for l in lines if l.speaker == "Alya"]
        assert len(alya) == 1
        assert "¿Tan malo fue?" in alya[0].text
        # El texto de Marinette no debe aparecer en Alya
        assert "peor día" not in alya[0].text


# ─────────────────────────────────────────────────────────────────────────────
# Tests con wikitext realista de Miraculous Ladybug
# ─────────────────────────────────────────────────────────────────────────────

class TestRealWorldWikitext:
    def setup_method(self):
        self.lines, self.fmt = parse_dialogue(SAMPLE_REALISTIC_ML, format_hint="bold-colon")

    def test_format_detected(self):
        assert self.fmt == "bold-colon"

    def test_section_headers_not_captured(self):
        """Los headers de sección (== Título ==) no se capturan como diálogo."""
        for line in self.lines:
            assert "==" not in (line.text or "")
            assert "==" not in (line.speaker or "")

    def test_action_lines_detected(self):
        actions = [l for l in self.lines if l.is_action]
        assert len(actions) >= 2

    def test_speakers_correctly_identified(self):
        speakers = {l.speaker for l in self.lines if not l.is_action}
        assert "Marinette" in speakers or "Ladybug" in speakers
        assert "Alya" in speakers

    def test_multiline_speech_merged(self):
        """La intervención de Marinette con continuación se captura completa."""
        marinette_turns = [l for l in self.lines if l.speaker == "Marinette" and not l.is_action]
        # La primera intervención tiene la continuación "Y cada día pienso en Adrien."
        first = marinette_turns[0]
        assert "Cada día" in first.text or "cada día" in first.text
        assert "Adrien" in first.text

    def test_no_empty_lines(self):
        for line in self.lines:
            assert line.text.strip() != ""
