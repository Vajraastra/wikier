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
        row_fmt.addWidget(self._fmt_combo)
        row_fmt.addStretch()
        lay_config.addLayout(row_fmt)

        # Formatos de salida (checkboxes)
        row_out = QHBoxLayout()
        row_out.addWidget(QLabel("Guardar como:"))
        self._chk_jsonl = QCheckBox("JSONL")
        self._chk_jsonl.setChecked(True)
        self._chk_csv   = QCheckBox("CSV")
        self._chk_csv.setChecked(True)
        self._chk_txt   = QCheckBox("TXT")
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
        row_quality.addWidget(self._min_chars_spin)
        row_quality.addStretch()
        lay_config.addLayout(row_quality)

        # System prompt — checkbox principal
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

        lbl_tpl = QLabel("Template del system prompt (dejar vacío para auto):")
        lay_sys.addWidget(lbl_tpl)
        self._sys_template_edit = QLineEdit()
        self._sys_template_edit.setPlaceholderText(
            "Ej: You are {character} from {show}. {personality}"
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

        # ── Sección 3: Acción ─────────────────────────────────────────────────
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

    def _browse_input(self) -> None:
        start_dir = str(OUTPUT_DIR) if OUTPUT_DIR.exists() else "."
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar dataset JSONL", start_dir, "JSONL (*.jsonl)"
        )
        if path:
            self._input_edit.setText(path)

    def _on_sys_prompt_toggled(self, checked: bool) -> None:
        self._sys_prompt_options.setVisible(checked)

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

        sys_enabled = self._sys_prompt_check.isChecked()
        config = CuratorConfig(
            min_chars=self._min_chars_spin.value(),
            output_format=self._fmt_combo.currentData(),
            system_prompt_enabled=sys_enabled,
            system_prompt_template=self._sys_template_edit.text().strip() or None,
            system_prompt_ratio=self._ratio_spin.value() / 100.0,
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
