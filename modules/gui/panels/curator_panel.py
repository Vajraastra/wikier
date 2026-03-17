"""
CuratorPanel: panel principal del módulo Curator.

Flujo en 3 pasos progresivos:
    1. Configuración  — seleccionar JSONL input, formato de salida, opciones
    2. Procesando     — progress bar mientras corre el pipeline en QThread
    3. Resultado      — estadísticas y archivos generados

El personaje se auto-detecta del nombre del archivo ({Personaje}_dataset.jsonl).
El directorio de salida es: mismo directorio del input / curated/
"""
from pathlib import Path

from PySide6.QtCore    import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QFrame,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QProgressBar, QPushButton, QSizePolicy,
    QSpinBox, QTextEdit, QVBoxLayout, QWidget,
)

from modules.scraper.config import OUTPUT_DIR
from modules.curator.curator import CuratorConfig
from modules.curator.name_tagger import TAG_PRESETS, find_roster
from modules.core.spacy_manager import is_installed
from modules.gui.workers.curator_worker import CuratorWorker


class CuratorPanel(QWidget):
    """Panel de curación de datasets."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._worker: CuratorWorker | None = None
        self._build_ui()

    # ─────────────────────────────────────────────────────────────────────────
    # Construcción de la UI
    # ─────────────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        title = QLabel("Curación de Dataset")
        title.setObjectName("panel-title")
        root.addWidget(title)

        # ── Sección 1: Archivo de entrada ─────────────────────────────────────
        grp_input = QGroupBox("Datos de entrada")
        lay_input = QHBoxLayout(grp_input)
        lay_input.setSpacing(8)

        lay_input.addWidget(QLabel("Archivo JSONL:"))
        self._input_edit = QLineEdit()
        self._input_edit.setPlaceholderText("Ruta al archivo .jsonl del scraper...")
        self._input_edit.setReadOnly(True)
        lay_input.addWidget(self._input_edit)

        btn_browse = QPushButton("Examinar...")
        btn_browse.setFixedWidth(100)
        btn_browse.clicked.connect(self._browse_input)
        lay_input.addWidget(btn_browse)

        root.addWidget(grp_input)

        # ── Sección 2: Configuración del pipeline ─────────────────────────────
        grp_config = QGroupBox("Configuración")
        lay_config = QVBoxLayout(grp_config)
        lay_config.setSpacing(10)

        # Formato de dataset (ChatML, Alpaca, etc.)
        row_fmt = QHBoxLayout()
        row_fmt.addWidget(QLabel("Formato dataset:"))
        self._fmt_combo = QComboBox()
        for label, val in [("ChatML (LLaMA / Mistral / Qwen)", "chatml"),
                            ("Alpaca", "alpaca"),
                            ("ShareGPT", "sharegpt"),
                            ("JSONL crudo", "jsonl_raw")]:
            self._fmt_combo.addItem(label, val)
        self._fmt_combo.setMinimumWidth(240)
        self._fmt_combo.currentIndexChanged.connect(self._on_fmt_changed)
        row_fmt.addWidget(self._fmt_combo)
        row_fmt.addStretch()
        lay_config.addLayout(row_fmt)

        # Ayuda dinámica del formato seleccionado
        self._fmt_help_lbl = QLabel()
        self._fmt_help_lbl.setWordWrap(True)
        self._fmt_help_lbl.setObjectName("help-text")
        lay_config.addWidget(self._fmt_help_lbl)
        self._on_fmt_changed(0)   # inicializar con el valor por defecto

        # Formatos de salida (checkboxes)
        row_out = QHBoxLayout()
        row_out.addWidget(QLabel("Guardar como:"))
        self._chk_jsonl = QCheckBox("JSONL")
        self._chk_jsonl.setChecked(True)
        self._chk_jsonl.setToolTip("Formato principal para entrenamiento. Requerido por todos los frameworks (LLaMA-Factory, Axolotl, Unsloth).")
        self._chk_csv   = QCheckBox("CSV")
        self._chk_csv.setChecked(True)
        self._chk_csv.setToolTip("Tabla editable en Excel o LibreOffice Calc. Útil para rellenar manualmente el campo 'instruction' (la pregunta que el usuario le haría al personaje).")
        self._chk_txt   = QCheckBox("TXT")
        self._chk_txt.setToolTip("Formato legible por humanos con bloques [USER] / [CHAR]. Útil para revisar el dataset visualmente antes de entrenar.")
        row_out.addWidget(self._chk_jsonl)
        row_out.addWidget(self._chk_csv)
        row_out.addWidget(self._chk_txt)
        row_out.addStretch()
        lay_config.addLayout(row_out)

        # Separador
        sep_cfg = QFrame()
        sep_cfg.setFrameShape(QFrame.HLine)
        lay_config.addWidget(sep_cfg)

        # Calidad mínima
        row_quality = QHBoxLayout()
        row_quality.addWidget(QLabel("Longitud mínima (chars):"))
        self._min_chars_spin = QSpinBox()
        self._min_chars_spin.setRange(1, 500)
        self._min_chars_spin.setValue(10)
        self._min_chars_spin.setFixedWidth(70)
        self._min_chars_spin.setToolTip(
            "Descarta respuestas más cortas que este número de caracteres.\n"
            "Las respuestas muy cortas ('Sí.', 'No sé.') aportan poco al entrenamiento\n"
            "y pueden degradar la calidad del modelo.\n\n"
            "Recomendado: 10–20 chars.\n"
            "Subir a 30+ si el personaje habla en oraciones completas y quieres descartar monosílabos."
        )
        row_quality.addWidget(self._min_chars_spin)
        lbl_quality_hint = QLabel("— respuestas más cortas se descartan del dataset")
        lbl_quality_hint.setObjectName("help-text")
        row_quality.addWidget(lbl_quality_hint)
        row_quality.addStretch()
        lay_config.addLayout(row_quality)

        # System prompt — explicación + checkbox
        lbl_sys_explain = QLabel(
            "El system prompt es el mensaje inicial que le dice al modelo quién debe ser "
            "durante el chat (\"Eres Marinette, personaje de Miraculous Ladybug...\"). "
            "Sin él, el modelo no sabrá qué rol asumir. Se recomienda dejarlo activado."
        )
        lbl_sys_explain.setWordWrap(True)
        lbl_sys_explain.setObjectName("help-text")
        lay_config.addWidget(lbl_sys_explain)

        row_sys = QHBoxLayout()
        self._sys_prompt_check = QCheckBox("Incluir system prompt")
        self._sys_prompt_check.setChecked(True)
        self._sys_prompt_check.toggled.connect(self._on_sys_prompt_toggled)
        row_sys.addWidget(self._sys_prompt_check)
        row_sys.addStretch()
        lay_config.addLayout(row_sys)

        # Contenedor de opciones del system prompt (se oculta cuando está desmarcado)
        self._sys_prompt_options = QWidget()
        lay_sys = QVBoxLayout(self._sys_prompt_options)
        lay_sys.setContentsMargins(0, 0, 0, 0)
        lay_sys.setSpacing(8)

        # Ratio de entradas con system prompt
        row_ratio = QHBoxLayout()
        row_ratio.addWidget(QLabel("% de entradas con system prompt:"))
        self._ratio_spin = QSpinBox()
        self._ratio_spin.setRange(10, 100)
        self._ratio_spin.setValue(100)
        self._ratio_spin.setSuffix(" %")
        self._ratio_spin.setFixedWidth(80)
        self._ratio_spin.setToolTip(
            "100% = todas las entradas incluyen el system prompt.\n"
            "70% = 70% con prompt, 30% sin él.\n"
            "Mezclar mejora la robustez del modelo entrenado."
        )
        row_ratio.addWidget(self._ratio_spin)
        row_ratio.addStretch()
        lay_sys.addLayout(row_ratio)

        lbl_tpl = QLabel(
            "Template personalizado (dejar vacío para generación automática):\n"
            "Variables disponibles: {character}  {show}  {aliases}  {personality}"
        )
        lbl_tpl.setObjectName("help-text")
        lay_sys.addWidget(lbl_tpl)
        self._sys_template_edit = QLineEdit()
        self._sys_template_edit.setPlaceholderText(
            "Ej: You are {character} from {show}. {personality}"
        )
        self._sys_template_edit.setToolTip(
            "Si lo dejas vacío, el sistema construye el prompt automáticamente\n"
            "usando los campos activados en 'system_prompt_fields' del perfil.\n\n"
            "Variables disponibles:\n"
            "  {character}  — nombre del personaje\n"
            "  {show}       — nombre del show/wiki\n"
            "  {aliases}    — lista de alter egos (ej: Ladybug, Marinette)\n"
            "  {personality}— descripción de personalidad (del campo de abajo)"
        )
        lay_sys.addWidget(self._sys_template_edit)

        lbl_pers = QLabel("Personalidad del personaje (opcional):")
        lay_sys.addWidget(lbl_pers)
        self._personality_edit = QTextEdit()
        self._personality_edit.setPlaceholderText(
            "Describe la personalidad del personaje para incluirla en el system prompt..."
        )
        self._personality_edit.setFixedHeight(60)
        lay_sys.addWidget(self._personality_edit)

        lay_config.addWidget(self._sys_prompt_options)

        root.addWidget(grp_config)

        # ── Sección 3: Name Tagger ────────────────────────────────────────────
        grp_tagger = QGroupBox("Anonimizar personajes (Name Tagger)")
        lay_tagger = QVBoxLayout(grp_tagger)
        lay_tagger.setSpacing(8)

        # Checkbox principal
        row_tagger_chk = QHBoxLayout()
        self._tagger_check = QCheckBox("Activar Name Tagger")
        self._tagger_check.setChecked(False)
        self._tagger_check.toggled.connect(self._on_tagger_toggled)
        row_tagger_chk.addWidget(self._tagger_check)
        row_tagger_chk.addStretch()
        lay_tagger.addLayout(row_tagger_chk)

        # Explicación
        lbl_tagger_desc = QLabel(
            "Reemplaza nombres de personajes secundarios por tags genéricos "
            "({{user}} para interlocutores, {{char}} para referencias a terceros). "
            "El personaje principal nunca se reemplaza. "
            "Objetivo: transferir estilo comunicativo sin bagaje histórico del personaje."
        )
        lbl_tagger_desc.setWordWrap(True)
        lbl_tagger_desc.setObjectName("help-text")
        lay_tagger.addWidget(lbl_tagger_desc)

        # Contenedor de opciones (se oculta cuando está desmarcado)
        self._tagger_options = QWidget()
        lay_tagger_opts = QVBoxLayout(self._tagger_options)
        lay_tagger_opts.setContentsMargins(0, 0, 0, 0)
        lay_tagger_opts.setSpacing(6)

        # Preset de tags
        row_preset = QHBoxLayout()
        row_preset.addWidget(QLabel("Preset de tags:"))
        self._preset_combo = QComboBox()
        for label, key in [
            ("SillyTavern  ({{user}} / {{char}})", "sillytavern"),
            ("Oobabooga    (<|user|> / <|bot|>)",  "oobabooga"),
            ("Genérico      ([USER] / [CHAR])",     "generic"),
            ("Personalizado",                        "custom"),
        ]:
            self._preset_combo.addItem(label, key)
        self._preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        row_preset.addWidget(self._preset_combo)
        row_preset.addStretch()
        lay_tagger_opts.addLayout(row_preset)

        # Campos personalizados (solo visible cuando preset = "custom")
        self._custom_tags_widget = QWidget()
        lay_custom = QHBoxLayout(self._custom_tags_widget)
        lay_custom.setContentsMargins(0, 0, 0, 0)
        lay_custom.addWidget(QLabel("Tag usuario:"))
        self._custom_user_edit = QLineEdit()
        self._custom_user_edit.setText("[USER]")
        self._custom_user_edit.setFixedWidth(100)
        lay_custom.addWidget(self._custom_user_edit)
        lay_custom.addWidget(QLabel("Tag personaje:"))
        self._custom_char_edit = QLineEdit()
        self._custom_char_edit.setText("[CHAR]")
        self._custom_char_edit.setFixedWidth(100)
        lay_custom.addWidget(self._custom_char_edit)
        lay_custom.addStretch()
        self._custom_tags_widget.setVisible(False)
        lay_tagger_opts.addWidget(self._custom_tags_widget)

        # Indicador de estado del modelo
        self._lang_status_label = QLabel("")
        self._lang_status_label.setObjectName("help-text")
        lay_tagger_opts.addWidget(self._lang_status_label)

        self._tagger_options.setVisible(False)
        lay_tagger.addWidget(self._tagger_options)

        root.addWidget(grp_tagger)

        # ── Sección 4: Token Analyzer ─────────────────────────────────────────
        grp_token = QGroupBox("Análisis de tokens (Token Analyzer)")
        lay_token = QVBoxLayout(grp_token)
        lay_token.setSpacing(8)

        # Checkbox principal
        row_token_chk = QHBoxLayout()
        self._token_check = QCheckBox("Activar Token Analyzer")
        self._token_check.setChecked(False)
        self._token_check.toggled.connect(self._on_token_toggled)
        row_token_chk.addWidget(self._token_check)
        row_token_chk.addStretch()
        lay_token.addLayout(row_token_chk)

        # Descripción
        lbl_token_desc = QLabel(
            "Filtra entradas cuya respuesta excede el límite de tokens del modelo "
            "objetivo. Las entradas que exceden se archivan en overlength.jsonl "
            "(recuperables). Incluye reporte de distribución con percentiles."
        )
        lbl_token_desc.setWordWrap(True)
        lbl_token_desc.setObjectName("help-text")
        lay_token.addWidget(lbl_token_desc)

        # Opciones (se ocultan cuando el checkbox está desmarcado)
        self._token_options = QWidget()
        lay_token_opts = QVBoxLayout(self._token_options)
        lay_token_opts.setContentsMargins(0, 0, 0, 0)
        lay_token_opts.setSpacing(8)

        # Preset de modelo
        row_preset_token = QHBoxLayout()
        row_preset_token.addWidget(QLabel("Modelo objetivo:"))
        self._token_preset_combo = QComboBox()
        for label, key in [
            ("tiny   — 1B–3B    (Phi-3 mini, Gemma 2B)         límite: 1 024 tokens", "tiny"),
            ("small  — 7B–9B    (LLaMA 3 8B, Mistral 7B)       límite: 2 048 tokens", "small"),
            ("medium — 13B–30B  (Qwen 14B, Mistral Nemo 12B)   límite: 4 096 tokens", "medium"),
            ("large  — 70B+     (LLaMA 3 70B, Qwen 72B)        límite: 8 192 tokens", "large"),
        ]:
            self._token_preset_combo.addItem(label, key)
        self._token_preset_combo.setCurrentIndex(1)   # small por defecto
        row_preset_token.addWidget(self._token_preset_combo)
        row_preset_token.addStretch()
        lay_token_opts.addLayout(row_preset_token)

        # Tokenizer avanzado (opcional)
        row_tokenizer = QHBoxLayout()
        row_tokenizer.addWidget(QLabel("Tokenizer (avanzado):"))
        self._tokenizer_edit = QLineEdit()
        self._tokenizer_edit.setPlaceholderText(
            "Vacío → proxy de chars (recomendado para modelos locales)"
        )
        self._tokenizer_edit.setToolTip(
            "Para LLaMA, Mistral, Qwen, Phi y similares:\n"
            "  Deja vacío. El proxy (~4 chars/token) es suficiente para filtrar\n"
            "  overlength en datasets de fine-tuning.\n"
            "\n"
            "Conteo exacto (avanzado — requiere: pip install transformers):\n"
            "  meta-llama/Meta-Llama-3-8B\n"
            "  mistralai/Mistral-7B-v0.1\n"
            "  Qwen/Qwen2-7B\n"
            "  microsoft/Phi-3-mini-4k-instruct\n"
            "\n"
            "⚠  tiktoken solo funciona con modelos GPT de OpenAI, no con modelos locales."
        )
        row_tokenizer.addWidget(self._tokenizer_edit)
        lay_token_opts.addLayout(row_tokenizer)

        self._token_options.setVisible(False)
        lay_token.addWidget(self._token_options)

        root.addWidget(grp_token)

        # ── Sección 5: Acción ─────────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        root.addWidget(sep)

        row_action = QHBoxLayout()
        self._run_btn = QPushButton("Iniciar curación")
        self._run_btn.setProperty("role", "primary")
        self._run_btn.setFixedHeight(36)
        self._run_btn.clicked.connect(self._run)
        row_action.addWidget(self._run_btn)
        row_action.addStretch()
        root.addLayout(row_action)

        # ── Progress bar ──────────────────────────────────────────────────────
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setVisible(False)
        root.addWidget(self._progress_bar)

        self._progress_label = QLabel("")
        self._progress_label.setVisible(False)
        root.addWidget(self._progress_label)

        # ── Resultado ─────────────────────────────────────────────────────────
        self._result_box = QTextEdit()
        self._result_box.setReadOnly(True)
        self._result_box.setVisible(False)
        self._result_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        font = self._result_box.font()
        font.setFamily("monospace")
        font.setPointSize(10)
        self._result_box.setFont(font)
        root.addWidget(self._result_box)

        root.addStretch()

    # ─────────────────────────────────────────────────────────────────────────
    # Handlers
    # ─────────────────────────────────────────────────────────────────────────

    # Mensajes de ayuda por formato — explican qué es cada formato y quién lo usa
    _FMT_HELP: dict[str, str] = {
        "chatml":    "Recomendado para la mayoría de usuarios. Compatible con LLaMA-Factory, Axolotl, Unsloth y casi todos los frameworks modernos. Estructura: system → user → assistant.",
        "alpaca":    "Formato clásico de instrucción/respuesta. Compatible con frameworks más antiguos. Buena opción si tu trainer solo acepta Alpaca.",
        "sharegpt":  "Multi-turno por defecto. Usado en conjuntos de datos de conversaciones largas. Elige este si tu trainer lo requiere explícitamente.",
        "jsonl_raw": "Formato mínimo sin estructura de roles. Útil para edición manual o como paso intermedio. No incluye información de roles (system/user/assistant).",
    }

    def _on_fmt_changed(self, _index: int) -> None:
        key = self._fmt_combo.currentData()
        self._fmt_help_lbl.setText(self._FMT_HELP.get(key, ""))

    def _browse_input(self) -> None:
        start_dir = str(OUTPUT_DIR) if OUTPUT_DIR.exists() else "."
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar dataset JSONL", start_dir, "JSONL (*.jsonl)"
        )
        if path:
            self._input_edit.setText(path)
            self._update_lang_status(path)

    def _on_sys_prompt_toggled(self, checked: bool) -> None:
        self._sys_prompt_options.setVisible(checked)

    def _on_tagger_toggled(self, checked: bool) -> None:
        self._tagger_options.setVisible(checked)
        if checked:
            self._update_lang_status(self._input_edit.text())

    def _on_token_toggled(self, checked: bool) -> None:
        self._token_options.setVisible(checked)

    def _on_preset_changed(self, _index: int) -> None:
        self._custom_tags_widget.setVisible(
            self._preset_combo.currentData() == "custom"
        )

    def _update_lang_status(self, input_path: str) -> None:
        """Actualiza el indicador de estado del modelo spaCy según el roster detectado."""
        if not input_path:
            return
        from pathlib import Path
        roster_path = find_roster(input_path)
        if roster_path:
            import json
            try:
                with open(roster_path, encoding="utf-8") as f:
                    roster = json.load(f)
                lang = roster.get("language", "en")
                if is_installed(lang):
                    self._lang_status_label.setText(
                        f"✓ Modelo '{lang}' instalado y listo."
                    )
                else:
                    self._lang_status_label.setText(
                        f"⚠ Modelo '{lang}' no instalado — "
                        f"descárgalo desde la pestaña Idiomas."
                    )
            except Exception:
                self._lang_status_label.setText("No se pudo leer el roster de personajes.")
        else:
            self._lang_status_label.setText(
                "No se encontró el archivo de personajes junto al dataset.\n"
                "Ejecuta el scraper para generarlo."
            )

    def refresh_language_status(self) -> None:
        """Llamado desde LanguagesPanel cuando cambia el estado de instalación."""
        self._update_lang_status(self._input_edit.text())

    def _run(self) -> None:
        input_path = self._input_edit.text().strip()
        if not input_path:
            self._set_status("Selecciona un archivo JSONL de entrada.")
            return

        # Formatos de salida seleccionados
        formats = []
        if self._chk_jsonl.isChecked():
            formats.append("jsonl")
        if self._chk_csv.isChecked():
            formats.append("csv")
        if self._chk_txt.isChecked():
            formats.append("txt")
        if not formats:
            formats = ["jsonl"]   # fallback

        sys_enabled    = self._sys_prompt_check.isChecked()
        tagger_enabled = self._tagger_check.isChecked()

        # Resolver roster_path si el tagger está activo
        roster_path: str | None = None
        if tagger_enabled:
            found = find_roster(input_path)
            roster_path = str(found) if found else None

        # Tags del Name Tagger
        preset = self._preset_combo.currentData()
        if preset == "custom":
            user_tag = self._custom_user_edit.text() or "[USER]"
            char_tag = self._custom_char_edit.text() or "[CHAR]"
        else:
            user_tag, char_tag = TAG_PRESETS.get(preset, ("{{user}}", "{{char}}"))

        token_enabled = self._token_check.isChecked()
        tokenizer_name = self._tokenizer_edit.text().strip() or None

        config = CuratorConfig(
            min_chars=self._min_chars_spin.value(),
            output_format=self._fmt_combo.currentData(),
            system_prompt_enabled=sys_enabled,
            system_prompt_template=self._sys_template_edit.text().strip() or None,
            system_prompt_ratio=self._ratio_spin.value() / 100.0,
            name_tagging_enabled=tagger_enabled,
            name_tag_preset=preset,
            name_tag_user=user_tag,
            name_tag_char=char_tag,
            name_tag_roster_path=roster_path,
            token_analyzer_enabled=token_enabled,
            token_preset=self._token_preset_combo.currentData(),
            tokenizer_name=tokenizer_name,
        )

        personality = self._personality_edit.toPlainText().strip() if sys_enabled else ""

        # — Preparar UI
        self._run_btn.setEnabled(False)
        self._progress_bar.setValue(0)
        self._progress_bar.setVisible(True)
        self._progress_label.setText("Iniciando...")
        self._progress_label.setVisible(True)
        self._result_box.setVisible(False)

        # — Lanzar worker
        self._worker = CuratorWorker(input_path, personality, config, formats)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    # ─────────────────────────────────────────────────────────────────────────
    # Señales del worker
    # ─────────────────────────────────────────────────────────────────────────

    def _on_progress(self, percent: int, message: str) -> None:
        self._progress_bar.setValue(percent)
        self._progress_label.setText(message)

    def _on_finished(self, result, out_dir: Path) -> None:
        self._progress_bar.setValue(100)
        self._progress_label.setText("Completado.")
        self._run_btn.setEnabled(True)

        lines = [result.stats_report, ""]
        lines.append(f"Archivos exportados en: {out_dir}")

        for cat, items in result.formatted.items():
            if not items:
                continue
            if self._chk_jsonl.isChecked():
                lines.append(f"  {cat}.jsonl  ({len(items)} entradas)")
            if self._chk_csv.isChecked():
                lines.append(f"  {cat}.csv")
            if self._chk_txt.isChecked():
                lines.append(f"  {cat}.txt")

        archived = {k: v for k, v in result.archived.items() if v}
        if archived:
            lines.append(f"\nArchivados en: {out_dir / 'archived'}")
            for cat, items in archived.items():
                lines.append(f"  {cat}.jsonl  ({len(items)} entradas)")

        self._result_box.setPlainText("\n".join(lines))
        self._result_box.setVisible(True)

    def _on_error(self, message: str) -> None:
        self._run_btn.setEnabled(True)
        self._progress_bar.setVisible(False)
        self._set_status(f"✗ {message}")

    def _set_status(self, msg: str) -> None:
        self._progress_label.setText(msg)
        self._progress_label.setVisible(True)
