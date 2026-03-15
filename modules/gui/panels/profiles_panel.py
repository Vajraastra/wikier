"""
ProfilesPanel: gestión de perfiles de wiki guardados.

Permite ver, crear y eliminar perfiles desde la GUI.
NewProfileDialog: diálogo de creación de perfil con campos básicos.
"""
import json
from pathlib import Path

from PySide6.QtCore    import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPlainTextEdit, QPushButton, QSizePolicy, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget, QComboBox,
)

from modules.scraper.config import PROFILES_DIR


# ─────────────────────────────────────────────────────────────────────────────
# Diálogo de creación / edición de perfil
# ─────────────────────────────────────────────────────────────────────────────

class NewProfileDialog(QDialog):
    """
    Diálogo para crear un nuevo perfil de wiki.

    Campos:
        - ID (slug sin espacios)
        - Nombre legible
        - URL base del wiki
        - Categorías de transcripts (una por línea)
        - Idioma (código ISO)
        - Rate limit en segundos
    """

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Nuevo perfil de wiki")
        self.setMinimumWidth(480)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setSpacing(10)

        self.id_edit      = QLineEdit()
        self.id_edit.setPlaceholderText("ej: miraculousladybug")

        self.name_edit    = QLineEdit()
        self.name_edit.setPlaceholderText("ej: Miraculous Ladybug")

        self.url_edit     = QLineEdit()
        self.url_edit.setPlaceholderText("https://miraculousladybug.fandom.com")

        self.cats_edit    = QPlainTextEdit()
        self.cats_edit.setPlaceholderText(
            "Category:Episode transcripts\nCategory:Movie transcripts"
        )
        self.cats_edit.setFixedHeight(80)

        self.lang_combo   = QComboBox()
        langs = [
            ("any — sin filtro",  "any"),
            ("en — Inglés",       "en"),
            ("es — Español",      "es"),
            ("fr — Francés",      "fr"),
            ("pt — Portugués",    "pt"),
            ("de — Alemán",       "de"),
            ("ja — Japonés",      "ja"),
            ("ko — Coreano",      "ko"),
            ("zh — Chino",        "zh"),
        ]
        for label, code in langs:
            self.lang_combo.addItem(label, code)
        self.lang_combo.setCurrentIndex(1)  # default: en

        self.rate_spin    = QDoubleSpinBox()
        self.rate_spin.setRange(0.1, 5.0)
        self.rate_spin.setSingleStep(0.1)
        self.rate_spin.setValue(0.5)
        self.rate_spin.setSuffix(" s")

        form.addRow("ID del perfil:", self.id_edit)
        form.addRow("Nombre:",        self.name_edit)
        form.addRow("URL base:",      self.url_edit)
        form.addRow("Categorías:",    self.cats_edit)
        form.addRow("Idioma:",        self.lang_combo)
        form.addRow("Rate limit:",    self.rate_spin)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_accept(self) -> None:
        profile_id = self.id_edit.text().strip().replace(" ", "_")
        name       = self.name_edit.text().strip()
        base_url   = self.url_edit.text().strip().rstrip("/")
        cats_raw   = self.cats_edit.toPlainText().strip()

        if not profile_id:
            QMessageBox.warning(self, "Campo vacío", "El ID del perfil es obligatorio.")
            return
        if not base_url.startswith("http"):
            QMessageBox.warning(self, "URL inválida", "La URL base debe comenzar con http(s)://")
            return
        if not cats_raw:
            QMessageBox.warning(self, "Campo vacío", "Ingresá al menos una categoría.")
            return

        categories = [c.strip() for c in cats_raw.splitlines() if c.strip()]
        language   = self.lang_combo.currentData()

        dest = PROFILES_DIR / f"{profile_id}.json"
        if dest.exists():
            ans = QMessageBox.question(
                self, "Perfil existente",
                f"El perfil '{profile_id}' ya existe. ¿Sobreescribir?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if ans != QMessageBox.Yes:
                return

        profile = {
            "name":                 name or profile_id,
            "base_url":             base_url,
            "transcript_categories": categories,
            "dialogue_format":      "auto",
            "rate_limit_seconds":   self.rate_spin.value(),
            "language":             language,
            "character_aliases":    {},
            "personality":          "",
            "system_prompt_fields": {
                "character":   True,
                "show":        True,
                "aliases":     True,
                "personality": True,
            },
        }

        PROFILES_DIR.mkdir(parents=True, exist_ok=True)
        with open(dest, "w", encoding="utf-8") as f:
            json.dump(profile, f, indent=2, ensure_ascii=False)

        self.accept()


# ─────────────────────────────────────────────────────────────────────────────
# Panel principal de perfiles
# ─────────────────────────────────────────────────────────────────────────────

class ProfilesPanel(QWidget):
    """
    Panel que muestra la lista de perfiles guardados y permite gestionarlos.

    Señales:
        profiles_changed — emitida tras crear o eliminar un perfil.
    """

    profiles_changed = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ── encabezado ────────────────────────────────────────────────────────
        header = QHBoxLayout()
        title  = QLabel("Perfiles de wiki")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        header.addWidget(title)
        header.addStretch()

        btn_new = QPushButton("+ Nuevo perfil")
        btn_new.clicked.connect(self._on_new)
        header.addWidget(btn_new)

        layout.addLayout(header)

        # ── tabla ─────────────────────────────────────────────────────────────
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Nombre", "URL base", "Idioma"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        layout.addWidget(self.table)

        # ── botones inferiores ────────────────────────────────────────────────
        footer = QHBoxLayout()
        self.btn_delete = QPushButton("Eliminar perfil")
        self.btn_delete.setEnabled(False)
        self.btn_delete.clicked.connect(self._on_delete)
        footer.addWidget(self.btn_delete)
        footer.addStretch()

        layout.addLayout(footer)

        self.table.selectionModel().selectionChanged.connect(
            lambda: self.btn_delete.setEnabled(bool(self.table.selectedItems()))
        )

    # ── slots ─────────────────────────────────────────────────────────────────

    def refresh(self) -> None:
        """Recarga la tabla desde disco."""
        self.table.setRowCount(0)
        profiles = sorted(PROFILES_DIR.glob("*.json"))
        self.table.setRowCount(len(profiles))

        for row, path in enumerate(profiles):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}

            self.table.setItem(row, 0, QTableWidgetItem(path.stem))
            self.table.setItem(row, 1, QTableWidgetItem(data.get("name", "—")))
            self.table.setItem(row, 2, QTableWidgetItem(data.get("base_url", "—")))
            self.table.setItem(row, 3, QTableWidgetItem(data.get("language", "any")))

        self.table.resizeColumnsToContents()

    def _on_new(self) -> None:
        dlg = NewProfileDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh()
            self.profiles_changed.emit()

    def _on_delete(self) -> None:
        selected = self.table.selectedItems()
        if not selected:
            return
        row        = self.table.currentRow()
        profile_id = self.table.item(row, 0).text()

        ans = QMessageBox.question(
            self, "Eliminar perfil",
            f"¿Eliminar el perfil '{profile_id}'?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if ans != QMessageBox.Yes:
            return

        path = PROFILES_DIR / f"{profile_id}.json"
        if path.exists():
            path.unlink()

        self.refresh()
        self.profiles_changed.emit()
