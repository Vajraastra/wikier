"""
JoinerPanel: panel principal del módulo Joiner.

Dos secciones independientes:

    1. Pipeline completo — carga los sets del curator, aplica merge/shuffle/
       split por objetivo y genera train.jsonl / validation.jsonl / test.jsonl.

    2. Conversor de formatos — convierte cualquier archivo JSONL/CSV/TXT a
       otro formato JSONL (chatml, alpaca, sharegpt, jsonl_raw). Útil para
       datasets editados manualmente en CSV o TXT que necesitan volver a JSONL.
"""

from pathlib import Path

from PySide6.QtCore    import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog,
    QFrame, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QProgressBar, QPushButton, QSizePolicy, QSpinBox,
    QTextEdit, QVBoxLayout, QWidget,
)

from modules.curator.joiner import OBJECTIVES, SUPPORTED_FORMATS
from modules.gui.workers.joiner_worker import JoinerWorker


class JoinerPanel(QWidget):
    """Panel del módulo Joiner."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._pipeline_worker:  JoinerWorker | None = None
        self._converter_worker: JoinerWorker | None = None
        self._build_ui()

    # ─────────────────────────────────────────────────────────────────────────
    # Construcción de la UI
    # ─────────────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        title = QLabel("Joiner — Dataset Final")
        title.setObjectName("panel-title")
        root.addWidget(title)

        # ── Sección 1: Pipeline completo ──────────────────────────────────────
        root.addWidget(self._build_pipeline_section())

        # ── Separador ─────────────────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        root.addWidget(sep)

        # ── Sección 2: Conversor de formatos ──────────────────────────────────
        root.addWidget(self._build_converter_section())

        # ── Progress y resultado (compartido) ─────────────────────────────────
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setVisible(False)
        root.addWidget(self._progress_bar)

        self._progress_label = QLabel("")
        self._progress_label.setVisible(False)
        root.addWidget(self._progress_label)

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

    def _build_pipeline_section(self) -> QGroupBox:
        grp = QGroupBox("Pipeline — Generar dataset final (train / validation / test)")
        lay = QVBoxLayout(grp)
        lay.setSpacing(10)

        # — Carpeta de entrada
        row_dir = QHBoxLayout()
        row_dir.addWidget(QLabel("Carpeta curated/:"))
        self._dir_edit = QLineEdit()
        self._dir_edit.setPlaceholderText(
            "Carpeta curated/ generada por el Curator (contiene los .jsonl por categoría)..."
        )
        self._dir_edit.setReadOnly(True)
        row_dir.addWidget(self._dir_edit)
        btn_dir = QPushButton("Examinar...")
        btn_dir.setFixedWidth(100)
        btn_dir.clicked.connect(self._browse_dir)
        row_dir.addWidget(btn_dir)
        lay.addLayout(row_dir)

        # — Objetivo
        row_obj = QHBoxLayout()
        row_obj.addWidget(QLabel("Objetivo:"))
        self._obj_combo = QComboBox()
        for key, meta in OBJECTIVES.items():
            self._obj_combo.addItem(f"{key}  —  {meta['label']}", key)
        self._obj_combo.setMinimumWidth(280)
        row_obj.addWidget(self._obj_combo)
        row_obj.addStretch()
        lay.addLayout(row_obj)

        # — Split
        row_split = QHBoxLayout()
        row_split.addWidget(QLabel("Split:  Train"))
        self._train_spin = self._make_ratio_spin(80)
        row_split.addWidget(self._train_spin)
        row_split.addWidget(QLabel("%   Val"))
        self._val_spin = self._make_ratio_spin(10)
        row_split.addWidget(self._val_spin)
        row_split.addWidget(QLabel("%   Test"))
        self._test_spin = self._make_ratio_spin(10)
        row_split.addWidget(self._test_spin)
        row_split.addWidget(QLabel("%"))
        lbl_note = QLabel("(se normalizan automáticamente)")
        lbl_note.setObjectName("help-text")
        row_split.addWidget(lbl_note)
        row_split.addStretch()
        lay.addLayout(row_split)

        # — Seed + Límite
        row_opts = QHBoxLayout()
        row_opts.addWidget(QLabel("Seed:"))
        self._seed_spin = QSpinBox()
        self._seed_spin.setRange(0, 999999)
        self._seed_spin.setValue(42)
        self._seed_spin.setFixedWidth(80)
        self._seed_spin.setToolTip(
            "Semilla aleatoria para el shuffle. Misma seed = mismo orden siempre.\n"
            "Útil para reproducir experimentos."
        )
        row_opts.addWidget(self._seed_spin)
        row_opts.addSpacing(24)

        self._limit_check = QCheckBox("Límite máx. de entradas:")
        self._limit_check.setChecked(False)
        self._limit_check.toggled.connect(lambda c: self._limit_spin.setEnabled(c))
        row_opts.addWidget(self._limit_check)
        self._limit_spin = QSpinBox()
        self._limit_spin.setRange(10, 999999)
        self._limit_spin.setValue(5000)
        self._limit_spin.setFixedWidth(90)
        self._limit_spin.setEnabled(False)
        self._limit_spin.setToolTip(
            "Limita el total de entradas en el dataset final.\n"
            "El joiner muestrea proporcionalmente por categoría según el objetivo."
        )
        row_opts.addWidget(self._limit_spin)
        row_opts.addStretch()
        lay.addLayout(row_opts)

        # — Botón
        row_btn = QHBoxLayout()
        self._pipeline_btn = QPushButton("Generar splits")
        self._pipeline_btn.setProperty("role", "primary")
        self._pipeline_btn.setFixedHeight(36)
        self._pipeline_btn.clicked.connect(self._run_pipeline)
        row_btn.addWidget(self._pipeline_btn)
        row_btn.addStretch()
        lay.addLayout(row_btn)

        return grp

    def _build_converter_section(self) -> QGroupBox:
        grp = QGroupBox("Conversor de formatos — JSONL / CSV / TXT → JSONL")
        lay = QVBoxLayout(grp)
        lay.setSpacing(10)

        # Descripción
        lbl_desc = QLabel(
            "Convierte archivos editados manualmente (CSV, TXT) o en otro formato JSONL "
            "de vuelta al formato que necesita tu framework de entrenamiento."
        )
        lbl_desc.setWordWrap(True)
        lbl_desc.setObjectName("help-text")
        lay.addWidget(lbl_desc)

        # — Archivo de entrada
        row_file = QHBoxLayout()
        row_file.addWidget(QLabel("Archivo de entrada:"))
        self._conv_input_edit = QLineEdit()
        self._conv_input_edit.setPlaceholderText(
            "Archivo .jsonl, .csv o .txt a convertir..."
        )
        self._conv_input_edit.setReadOnly(True)
        self._conv_input_edit.textChanged.connect(self._on_conv_input_changed)
        row_file.addWidget(self._conv_input_edit)
        btn_file = QPushButton("Examinar...")
        btn_file.setFixedWidth(100)
        btn_file.clicked.connect(self._browse_conv_input)
        row_file.addWidget(btn_file)
        lay.addLayout(row_file)

        # — Formato detectado + destino
        row_fmts = QHBoxLayout()
        row_fmts.addWidget(QLabel("Formato detectado:"))
        self._detected_fmt_label = QLabel("—")
        self._detected_fmt_label.setObjectName("help-text")
        self._detected_fmt_label.setMinimumWidth(100)
        row_fmts.addWidget(self._detected_fmt_label)
        row_fmts.addSpacing(24)
        row_fmts.addWidget(QLabel("Formato de destino:"))
        self._target_fmt_combo = QComboBox()
        for label, key in [
            ("ChatML — LLaMA / Mistral / Qwen",  "chatml"),
            ("Alpaca — instrucción / respuesta",   "alpaca"),
            ("ShareGPT — multi-turno",             "sharegpt"),
            ("JSONL crudo",                        "jsonl_raw"),
        ]:
            self._target_fmt_combo.addItem(label, key)
        self._target_fmt_combo.setMinimumWidth(240)
        row_fmts.addWidget(self._target_fmt_combo)
        row_fmts.addStretch()
        lay.addLayout(row_fmts)

        # — Botón
        row_btn = QHBoxLayout()
        self._convert_btn = QPushButton("Convertir")
        self._convert_btn.setProperty("role", "primary")
        self._convert_btn.setFixedHeight(36)
        self._convert_btn.clicked.connect(self._run_convert)
        row_btn.addWidget(self._convert_btn)
        row_btn.addStretch()
        lay.addLayout(row_btn)

        return grp

    @staticmethod
    def _make_ratio_spin(default: int) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(0, 100)
        spin.setValue(default)
        spin.setFixedWidth(60)
        return spin

    # ─────────────────────────────────────────────────────────────────────────
    # Handlers de UI
    # ─────────────────────────────────────────────────────────────────────────

    def _browse_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, "Seleccionar carpeta curated/", "."
        )
        if path:
            self._dir_edit.setText(path)

    def _browse_conv_input(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar archivo de dataset",
            ".",
            "Datasets (*.jsonl *.csv *.txt);;Todos los archivos (*)",
        )
        if path:
            self._conv_input_edit.setText(path)

    def _on_conv_input_changed(self, path: str) -> None:
        """Actualiza la etiqueta de formato detectado cuando cambia el archivo."""
        if not path:
            self._detected_fmt_label.setText("—")
            return
        p = Path(path)
        if not p.exists():
            self._detected_fmt_label.setText("—")
            return

        ext = p.suffix.lower()
        if ext == ".csv":
            self._detected_fmt_label.setText("csv")
        elif ext == ".txt":
            self._detected_fmt_label.setText("txt")
        else:
            # Leer la primera línea para detectar formato JSONL
            try:
                import json as _json
                with open(p, encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            entry = _json.loads(line)
                            from modules.curator.joiner import detect_format
                            self._detected_fmt_label.setText(detect_format(entry))
                            return
            except Exception:
                pass
            self._detected_fmt_label.setText("jsonl_raw")

    # ─────────────────────────────────────────────────────────────────────────
    # Ejecutar pipeline
    # ─────────────────────────────────────────────────────────────────────────

    def _run_pipeline(self) -> None:
        input_dir = self._dir_edit.text().strip()
        if not input_dir:
            self._set_status("Seleccioná una carpeta curated/ de entrada.")
            return

        max_entries = self._limit_spin.value() if self._limit_check.isChecked() else 0

        # Inferir prefijo del nombre de la carpeta padre
        prefix = Path(input_dir).parent.stem
        if prefix.endswith("_dataset") or prefix.endswith("_curated"):
            prefix = prefix.rsplit("_", 1)[0]

        self._set_busy(True)

        self._pipeline_worker = JoinerWorker(
            mode        = "pipeline",
            input_dir   = input_dir,
            objective   = self._obj_combo.currentData(),
            train_ratio = self._train_spin.value() / 100.0,
            val_ratio   = self._val_spin.value()   / 100.0,
            test_ratio  = self._test_spin.value()  / 100.0,
            seed        = self._seed_spin.value(),
            max_entries = max_entries,
            prefix      = prefix,
        )
        self._pipeline_worker.progress.connect(self._on_progress)
        self._pipeline_worker.finished.connect(self._on_finished)
        self._pipeline_worker.error.connect(self._on_error)
        self._pipeline_worker.start()

    # ─────────────────────────────────────────────────────────────────────────
    # Ejecutar conversión
    # ─────────────────────────────────────────────────────────────────────────

    def _run_convert(self) -> None:
        input_file = self._conv_input_edit.text().strip()
        if not input_file:
            self._set_status("Seleccioná un archivo de entrada para convertir.")
            return

        self._set_busy(True)

        detected = self._detected_fmt_label.text()
        source_fmt = detected if detected not in ("—", "") else ""

        self._converter_worker = JoinerWorker(
            mode       = "convert",
            input_file = input_file,
            target_fmt = self._target_fmt_combo.currentData(),
            source_fmt = source_fmt,
        )
        self._converter_worker.progress.connect(self._on_progress)
        self._converter_worker.finished.connect(self._on_finished)
        self._converter_worker.error.connect(self._on_error)
        self._converter_worker.start()

    # ─────────────────────────────────────────────────────────────────────────
    # Señales del worker
    # ─────────────────────────────────────────────────────────────────────────

    def _on_progress(self, percent: int, message: str) -> None:
        self._progress_bar.setValue(percent)
        self._progress_label.setText(message)

    def _on_finished(self, report: str, out_paths: list) -> None:
        self._progress_bar.setValue(100)
        self._progress_label.setText("Completado.")
        self._set_busy(False)
        self._result_box.setPlainText(report)
        self._result_box.setVisible(True)

    def _on_error(self, message: str) -> None:
        self._set_busy(False)
        self._progress_bar.setVisible(False)
        self._set_status(f"✗ {message}")

    # ─────────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _set_busy(self, busy: bool) -> None:
        self._pipeline_btn.setEnabled(not busy)
        self._convert_btn.setEnabled(not busy)
        self._progress_bar.setValue(0)
        self._progress_bar.setVisible(busy)
        self._progress_label.setText("Iniciando..." if busy else "")
        self._progress_label.setVisible(True)
        if busy:
            self._result_box.setVisible(False)

    def _set_status(self, msg: str) -> None:
        self._progress_label.setText(msg)
        self._progress_label.setVisible(True)
