"""
ScrapePanel: panel principal de scraping con pipeline completa.

Flujo:
  1. Seleccionar perfil → configurar opciones → [Iniciar indexación]
  2. Ver progreso de indexación → tabla de speakers aparece al terminar
  3. Seleccionar personaje + opciones → [Extraer]
  4. Ver progreso de extracción → resultados con ruta de output
"""
import json
from pathlib import Path

from PySide6.QtCore    import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QProgressBar, QPushButton, QScrollArea,
    QSizePolicy, QSpinBox, QTableWidget, QTableWidgetItem,
    QTextEdit, QVBoxLayout, QWidget,
)

from modules.scraper.config  import PROFILES_DIR
from modules.gui.workers.scrape_worker import ExtractWorker, IndexWorker


class _NumericItem(QTableWidgetItem):
    """QTableWidgetItem que ordena su contenido como entero."""
    def __lt__(self, other: QTableWidgetItem) -> bool:
        try:
            return int(self.text()) < int(other.text())
        except ValueError:
            return super().__lt__(other)


def _load_profiles() -> list[dict]:
    """Carga todos los perfiles del directorio profiles/."""
    profiles = []
    for path in sorted(PROFILES_DIR.glob("*.json")):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            data["_id"] = path.stem
            profiles.append(data)
        except Exception:
            pass
    return profiles


class ScrapePanel(QWidget):
    """
    Panel que guía al usuario a través del pipeline de scraping en 3 pasos:
    configuración → indexación → extracción.
    """

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._index:          dict | None = None
        self._index_worker:   IndexWorker | None = None
        self._extract_worker: ExtractWorker | None = None
        self._all_speakers:   list[tuple[str, int]] = []
        self._build_ui()
        self.refresh_profiles()

    # ─────────────────────────────────────────────────────────────────────────
    # Construcción de la UI
    # ─────────────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        # Scroll area para que el panel sea navegable si la ventana es pequeña
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)

        container = QWidget()
        root_layout = QVBoxLayout(container)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(16)

        # Título
        title = QLabel("Scraping de diálogos")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        root_layout.addWidget(title)

        # ── Sección 1: configuración ──────────────────────────────────────────
        self._grp_config = self._build_config_section()
        root_layout.addWidget(self._grp_config)

        # ── Sección 2: progreso de indexación ─────────────────────────────────
        self._grp_index = self._build_index_section()
        self._grp_index.setVisible(False)
        root_layout.addWidget(self._grp_index)

        # ── Sección 3: selección de personaje ─────────────────────────────────
        self._grp_character = self._build_character_section()
        self._grp_character.setVisible(False)
        root_layout.addWidget(self._grp_character)

        # ── Sección 4: resultados ─────────────────────────────────────────────
        self._grp_results = self._build_results_section()
        self._grp_results.setVisible(False)
        root_layout.addWidget(self._grp_results)

        root_layout.addStretch()
        scroll.setWidget(container)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    # ── Sección config ────────────────────────────────────────────────────────

    def _build_config_section(self) -> QGroupBox:
        grp    = QGroupBox("Paso 1 — Configuración")
        layout = QVBoxLayout(grp)
        layout.setSpacing(10)

        # Selector de perfil
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Perfil:"))
        self.profile_combo = QComboBox()
        self.profile_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        row1.addWidget(self.profile_combo)
        layout.addLayout(row1)

        # Opciones secundarias
        row2 = QHBoxLayout()
        self.rebuild_chk = QCheckBox("Reconstruir índice")
        self.rebuild_chk.setToolTip("Ignorar el índice en cache y re-descargar todo")
        row2.addWidget(self.rebuild_chk)

        row2.addSpacing(20)
        row2.addWidget(QLabel("Muestra (0 = todo):"))
        self.sample_spin = QSpinBox()
        self.sample_spin.setRange(0, 9999)
        self.sample_spin.setValue(0)
        self.sample_spin.setToolTip("Procesar solo N páginas (útil para pruebas)")
        self.sample_spin.setFixedWidth(70)
        row2.addWidget(self.sample_spin)
        row2.addStretch()
        layout.addLayout(row2)

        # Botón iniciar
        self.btn_index = QPushButton("Iniciar indexación")
        self.btn_index.setFixedHeight(36)
        self.btn_index.clicked.connect(self._on_start_index)
        layout.addWidget(self.btn_index)

        return grp

    # ── Sección indexación ────────────────────────────────────────────────────

    def _build_index_section(self) -> QGroupBox:
        grp    = QGroupBox("Paso 2 — Indexación")
        layout = QVBoxLayout(grp)
        layout.setSpacing(8)

        self.index_progress = QProgressBar()
        self.index_progress.setTextVisible(True)
        self.index_progress.setValue(0)
        layout.addWidget(self.index_progress)

        self.index_log = QTextEdit()
        self.index_log.setReadOnly(True)
        self.index_log.setFixedHeight(120)
        self.index_log.setStyleSheet("font-family: monospace; font-size: 11px;")
        layout.addWidget(self.index_log)

        return grp

    # ── Sección personaje ─────────────────────────────────────────────────────

    def _build_character_section(self) -> QGroupBox:
        grp    = QGroupBox("Paso 3 — Selección de personaje")
        layout = QVBoxLayout(grp)
        layout.setSpacing(10)

        # Buscador dinámico (filtra la tabla al escribir)
        row_search = QHBoxLayout()
        row_search.addWidget(QLabel("Buscar:"))
        self.char_input = QLineEdit()
        self.char_input.setPlaceholderText("Filtrar por nombre…")
        self.char_input.setClearButtonEnabled(True)
        self.char_input.textChanged.connect(self._apply_speakers_filter)
        row_search.addWidget(self.char_input)
        layout.addLayout(row_search)

        # Tabla de speakers (con sorting por columna)
        self.speakers_table = QTableWidget()
        self.speakers_table.setColumnCount(2)
        self.speakers_table.setHorizontalHeaderLabels(["Personaje", "Líneas"])
        self.speakers_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.speakers_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.speakers_table.setAlternatingRowColors(True)
        self.speakers_table.verticalHeader().setVisible(False)
        self.speakers_table.setFixedHeight(200)
        self.speakers_table.setSortingEnabled(True)
        self.speakers_table.setSelectionMode(QTableWidget.SingleSelection)
        self.speakers_table.itemSelectionChanged.connect(self._on_speaker_selected)
        layout.addWidget(self.speakers_table)

        # Opciones de extracción
        row_opts = QHBoxLayout()
        row_opts.addWidget(QLabel("Contexto:"))
        self.context_spin = QSpinBox()
        self.context_spin.setRange(0, 10)
        self.context_spin.setValue(3)
        self.context_spin.setFixedWidth(55)
        self.context_spin.setToolTip("Número de líneas previas como contexto")
        row_opts.addWidget(self.context_spin)
        row_opts.addWidget(QLabel("líneas"))

        row_opts.addSpacing(20)
        self.actions_chk = QCheckBox("Incluir acciones en contexto")
        row_opts.addWidget(self.actions_chk)
        row_opts.addStretch()
        layout.addLayout(row_opts)

        # Selección de formatos de salida
        row_fmt = QHBoxLayout()
        row_fmt.addWidget(QLabel("Formatos:"))
        self.fmt_jsonl = QCheckBox("JSONL")
        self.fmt_jsonl.setChecked(True)
        self.fmt_jsonl.setToolTip("JSON Lines — ideal para fine-tuning")
        self.fmt_csv = QCheckBox("CSV")
        self.fmt_csv.setToolTip("Valores separados por coma")
        self.fmt_txt = QCheckBox("TXT")
        self.fmt_txt.setToolTip("Texto plano — contexto + línea, separados por línea en blanco")
        row_fmt.addWidget(self.fmt_jsonl)
        row_fmt.addWidget(self.fmt_csv)
        row_fmt.addWidget(self.fmt_txt)
        row_fmt.addStretch()
        layout.addLayout(row_fmt)

        # Botón extraer
        self.btn_extract = QPushButton("Extraer")
        self.btn_extract.setFixedHeight(36)
        self.btn_extract.clicked.connect(self._on_start_extract)
        layout.addWidget(self.btn_extract)

        return grp

    # ── Sección resultados ────────────────────────────────────────────────────

    def _build_results_section(self) -> QGroupBox:
        grp    = QGroupBox("Resultados")
        layout = QVBoxLayout(grp)
        layout.setSpacing(8)

        self.extract_progress = QProgressBar()
        self.extract_progress.setTextVisible(True)
        self.extract_progress.setValue(0)
        layout.addWidget(self.extract_progress)

        self.extract_log = QTextEdit()
        self.extract_log.setReadOnly(True)
        self.extract_log.setFixedHeight(80)
        self.extract_log.setStyleSheet("font-family: monospace; font-size: 11px;")
        layout.addWidget(self.extract_log)

        self.result_label = QLabel("")
        self.result_label.setWordWrap(True)
        layout.addWidget(self.result_label)

        # Botón para volver a extraer otro personaje
        self.btn_again = QPushButton("Extraer otro personaje")
        self.btn_again.setVisible(False)
        self.btn_again.clicked.connect(self._on_extract_again)
        layout.addWidget(self.btn_again)

        return grp

    # ─────────────────────────────────────────────────────────────────────────
    # Lógica de perfil
    # ─────────────────────────────────────────────────────────────────────────

    def refresh_profiles(self) -> None:
        """Recarga el combo de perfiles desde disco."""
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        self._profiles = _load_profiles()
        if not self._profiles:
            self.profile_combo.addItem("— No hay perfiles guardados —")
            self.btn_index.setEnabled(False)
        else:
            for p in self._profiles:
                self.profile_combo.addItem(f"{p.get('name', p['_id'])}  [{p['_id']}]")
            self.btn_index.setEnabled(True)
        self.profile_combo.blockSignals(False)

    def _current_profile(self) -> dict | None:
        idx = self.profile_combo.currentIndex()
        if 0 <= idx < len(self._profiles):
            return self._profiles[idx]
        return None

    # ─────────────────────────────────────────────────────────────────────────
    # Pipeline Paso 1 → Indexación
    # ─────────────────────────────────────────────────────────────────────────

    def _on_start_index(self) -> None:
        profile = self._current_profile()
        if not profile:
            return

        # Reset estado
        self._index = None
        self.index_log.clear()
        self.index_progress.setValue(0)
        self.index_progress.setMaximum(0)  # indeterminate hasta saber total
        self._grp_character.setVisible(False)
        self._grp_results.setVisible(False)

        self._grp_index.setVisible(True)
        self.btn_index.setEnabled(False)

        self._index_worker = IndexWorker(
            base_url    = profile["base_url"],
            categories  = profile.get("transcript_categories", []),
            rate_limit  = profile.get("rate_limit_seconds", 0.5),
            format_hint = profile.get("dialogue_format", "auto"),
            rebuild     = self.rebuild_chk.isChecked(),
            sample      = self.sample_spin.value(),
        )
        self._index_worker.progress.connect(self._on_index_progress)
        self._index_worker.finished.connect(self._on_index_finished)
        self._index_worker.error.connect(self._on_index_error)
        self._index_worker.start()

    def _on_index_progress(self, current: int, total: int, message: str) -> None:
        if total > 0:
            self.index_progress.setMaximum(total)
            self.index_progress.setValue(current)
        self.index_log.append(message)
        # Auto-scroll al final
        self.index_log.verticalScrollBar().setValue(
            self.index_log.verticalScrollBar().maximum()
        )

    def _on_index_finished(self, index: dict) -> None:
        self._index = index
        self.btn_index.setEnabled(True)

        n_pages    = len(index.get("pages", []))
        n_speakers = len(index.get("speakers", {}))
        self.index_progress.setMaximum(n_pages or 1)
        self.index_progress.setValue(n_pages)
        self.index_log.append(f"✓ Completado: {n_pages} páginas, {n_speakers} personajes")

        self._populate_speakers(index)
        self._grp_character.setVisible(True)

    def _on_index_error(self, message: str) -> None:
        self.btn_index.setEnabled(True)
        self.index_log.append(f"✗ Error: {message}")

    # ─────────────────────────────────────────────────────────────────────────
    # Speakers table
    # ─────────────────────────────────────────────────────────────────────────

    def _populate_speakers(self, index: dict) -> None:
        """Carga todos los speakers en memoria y renderiza la tabla completa."""
        speakers = index.get("speakers", {})
        self._all_speakers = list(speakers.items())
        self.char_input.clear()          # limpia filtro anterior
        self._apply_speakers_filter("")  # renderiza todo

    def _apply_speakers_filter(self, text: str) -> None:
        """Filtra la tabla por subcadena (case-insensitive). Mantiene el sorting activo."""
        query = text.strip().lower()
        filtered = [
            (name, count) for name, count in self._all_speakers
            if not query or query in name.lower()
        ]
        self.speakers_table.setSortingEnabled(False)
        self.speakers_table.clearSelection()
        self.speakers_table.setRowCount(len(filtered))
        for row, (name, count) in enumerate(filtered):
            self.speakers_table.setItem(row, 0, QTableWidgetItem(name))
            item_count = _NumericItem(str(count))
            item_count.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.speakers_table.setItem(row, 1, item_count)
        self.speakers_table.setSortingEnabled(True)
        self.speakers_table.resizeColumnsToContents()

    def _on_speaker_selected(self) -> None:
        items = self.speakers_table.selectedItems()
        if items:
            # Bloquear señal para no re-filtrar al seleccionar de la tabla
            self.char_input.blockSignals(True)
            self.char_input.setText(items[0].text())
            self.char_input.blockSignals(False)

    # ─────────────────────────────────────────────────────────────────────────
    # Pipeline Paso 2 → Extracción
    # ─────────────────────────────────────────────────────────────────────────

    def _on_start_extract(self) -> None:
        if not self._index:
            return

        character = self.char_input.text().strip()
        if not character:
            return

        formats = [
            fmt for fmt, chk in [
                ("jsonl", self.fmt_jsonl),
                ("csv",   self.fmt_csv),
                ("txt",   self.fmt_txt),
            ] if chk.isChecked()
        ]
        if not formats:
            self.fmt_jsonl.setChecked(True)   # garantizar al menos uno
            formats = ["jsonl"]

        profile = self._current_profile()
        aliases_dict = profile.get("character_aliases", {}) if profile else {}
        aliases = self._resolve_aliases(character, aliases_dict)

        # Reset resultados
        self.extract_log.clear()
        self.extract_progress.setValue(0)
        self.extract_progress.setMaximum(len(self._index["pages"]))
        self.result_label.setText("")
        self.btn_again.setVisible(False)
        self._grp_results.setVisible(True)
        self.btn_extract.setEnabled(False)

        self._extract_worker = ExtractWorker(
            index           = self._index,
            character       = character,
            aliases         = aliases,
            context_window  = self.context_spin.value(),
            include_actions = self.actions_chk.isChecked(),
            rate_limit      = profile.get("rate_limit_seconds", 0.5) if profile else 0.5,
            format_hint     = profile.get("dialogue_format", "auto") if profile else "auto",
            formats         = formats,
            profile         = profile or {},
        )
        self._extract_worker.progress.connect(self._on_extract_progress)
        self._extract_worker.finished.connect(self._on_extract_finished)
        self._extract_worker.error.connect(self._on_extract_error)
        self._extract_worker.start()

    def _on_extract_progress(self, current: int, total: int, title: str) -> None:
        self.extract_progress.setValue(current)
        self.extract_log.append(title)
        self.extract_log.verticalScrollBar().setValue(
            self.extract_log.verticalScrollBar().maximum()
        )

    def _on_extract_finished(self, pairs: list, out_dir: str) -> None:
        self.btn_extract.setEnabled(True)
        n = len(pairs)
        if n > 0:
            from pathlib import Path
            char      = self.char_input.text().strip()
            char_slug = char.replace(" ", "_")
            formats   = [
                fmt for fmt, chk in [
                    ("jsonl", self.fmt_jsonl),
                    ("csv",   self.fmt_csv),
                    ("txt",   self.fmt_txt),
                ] if chk.isChecked()
            ]
            files = ", ".join(f"{char_slug}_dataset.{f}" for f in formats)
            self.result_label.setText(
                f"✓ {n} pares extraídos\n"
                f"Directorio: {out_dir}\n"
                f"Archivos:   {files}"
            )
            self.result_label.setStyleSheet("color: #2a9d2a; font-weight: bold;")
        else:
            char = self.char_input.text().strip()
            self.result_label.setText(
                f"No se encontraron líneas de '{char}'.\n"
                "Verificá el nombre exacto o los aliases en el perfil."
            )
            self.result_label.setStyleSheet("color: #c0392b;")
        self.btn_again.setVisible(True)

    def _on_extract_error(self, message: str) -> None:
        self.btn_extract.setEnabled(True)
        self.extract_log.append(f"✗ Error: {message}")

    def _on_extract_again(self) -> None:
        """Vuelve al paso de selección para extraer otro personaje."""
        self.speakers_table.clearSelection()
        self.char_input.clear()          # también restaura el filtro completo
        self.extract_log.clear()
        self.extract_progress.setValue(0)
        self.result_label.setText("")
        self.btn_again.setVisible(False)
        self._grp_results.setVisible(False)

    # ─────────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _resolve_aliases(character: str, aliases_dict: dict) -> list[str]:
        """Busca el personaje en el dict de aliases y retorna sus variantes."""
        for key, aliases in aliases_dict.items():
            if (key.lower() == character.lower() or
                    character.lower() in [a.lower() for a in aliases]):
                return [a for a in aliases if a.lower() != character.lower()]
        return []
