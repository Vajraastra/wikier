"""
LanguagesPanel: descarga y gestión de modelos spaCy por idioma.

Muestra todos los idiomas soportados con su estado de instalación y permite
descargar modelos desde la GUI con una barra de progreso.
"""
from PySide6.QtCore    import QThread, Signal, Qt
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QProgressBar,
    QPushButton, QSizePolicy, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from modules.core.spacy_manager import list_available, download


# ─────────────────────────────────────────────────────────────────────────────
# Worker de descarga
# ─────────────────────────────────────────────────────────────────────────────

class _DownloadWorker(QThread):
    """Descarga un modelo spaCy en background."""

    progress = Signal(int, str)   # (percent, message)
    finished = Signal(str)        # lang descargado
    error    = Signal(str)        # mensaje de error

    def __init__(self, lang: str, parent=None):
        super().__init__(parent)
        self._lang = lang

    def run(self) -> None:
        try:
            download(self._lang, progress_cb=lambda pct, msg: self.progress.emit(pct, msg))
            self.finished.emit(self._lang)
        except Exception as exc:
            self.error.emit(str(exc))


# ─────────────────────────────────────────────────────────────────────────────
# Panel
# ─────────────────────────────────────────────────────────────────────────────

_COL_NAME    = 0
_COL_CODE    = 1
_COL_SIZE    = 2
_COL_STATUS  = 3
_COL_ACTION  = 4


class LanguagesPanel(QWidget):
    """Panel de gestión de modelos de idioma spaCy."""

    # Emitida cuando cambia el estado de instalación de algún modelo
    models_changed = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._worker: _DownloadWorker | None = None
        self._build_ui()
        self._populate_table()

    # ─────────────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)

        title = QLabel("Modelos de Idioma (spaCy)")
        title.setObjectName("panel-title")
        root.addWidget(title)

        desc = QLabel(
            "Los modelos se necesitan para el paso opcional de anonimización "
            "de personajes (Name Tagger). Cada modelo ocupa entre 12–30 MB."
        )
        desc.setWordWrap(True)
        root.addWidget(desc)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        root.addWidget(sep)

        # Tabla de modelos
        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(
            ["Idioma", "Código", "Tamaño", "Estado", ""]
        )
        self._table.horizontalHeader().setStretchLastSection(False)
        self._table.horizontalHeader().setDefaultSectionSize(120)
        self._table.setColumnWidth(_COL_NAME,   160)
        self._table.setColumnWidth(_COL_CODE,    60)
        self._table.setColumnWidth(_COL_SIZE,    80)
        self._table.setColumnWidth(_COL_STATUS, 110)
        self._table.setColumnWidth(_COL_ACTION,  90)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        root.addWidget(self._table)

        # Barra de progreso
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setVisible(False)
        root.addWidget(self._progress_bar)

        self._status_label = QLabel("")
        self._status_label.setVisible(False)
        root.addWidget(self._status_label)

        btn_refresh = QPushButton("Actualizar lista")
        btn_refresh.clicked.connect(self._populate_table)
        row = QHBoxLayout()
        row.addWidget(btn_refresh)
        row.addStretch()
        root.addLayout(row)

    def _populate_table(self) -> None:
        """Rellena la tabla con el estado actual de todos los modelos."""
        self._table.setRowCount(0)
        for info in list_available():
            row = self._table.rowCount()
            self._table.insertRow(row)

            self._table.setItem(row, _COL_NAME,   QTableWidgetItem(info["name"]))
            self._table.setItem(row, _COL_CODE,   QTableWidgetItem(info["lang"]))
            self._table.setItem(row, _COL_SIZE,   QTableWidgetItem(f"{info['size_mb']} MB"))

            if info["installed"]:
                status_item = QTableWidgetItem("✓ Instalado")
                status_item.setForeground(Qt.green)
                self._table.setItem(row, _COL_STATUS, status_item)
                # No botón — ya instalado
            else:
                self._table.setItem(row, _COL_STATUS, QTableWidgetItem("No instalado"))
                btn = QPushButton("Descargar")
                btn.setProperty("lang", info["lang"])
                btn.clicked.connect(lambda checked, lang=info["lang"]: self._download(lang))
                self._table.setCellWidget(row, _COL_ACTION, btn)

    # ─────────────────────────────────────────────────────────────────────────

    def _download(self, lang: str) -> None:
        if self._worker and self._worker.isRunning():
            return  # una descarga a la vez

        # Deshabilitar todos los botones de descarga mientras dura la operación
        self._set_download_buttons_enabled(False)
        self._progress_bar.setValue(0)
        self._progress_bar.setVisible(True)
        self._status_label.setText(f"Descargando modelo para '{lang}'...")
        self._status_label.setVisible(True)

        self._worker = _DownloadWorker(lang, self)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_progress(self, percent: int, message: str) -> None:
        self._progress_bar.setValue(percent)
        self._status_label.setText(message)

    def _on_finished(self, lang: str) -> None:
        self._progress_bar.setValue(100)
        self._status_label.setText(f"Modelo '{lang}' instalado correctamente.")
        self._set_download_buttons_enabled(True)
        self._populate_table()
        self.models_changed.emit()

    def _on_error(self, message: str) -> None:
        self._progress_bar.setVisible(False)
        self._status_label.setText(f"Error: {message}")
        self._set_download_buttons_enabled(True)

    def _set_download_buttons_enabled(self, enabled: bool) -> None:
        for row in range(self._table.rowCount()):
            widget = self._table.cellWidget(row, _COL_ACTION)
            if widget:
                widget.setEnabled(enabled)
