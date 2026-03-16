"""
EditorPanel: editor manual de datasets curados.

Permite cargar un archivo JSONL/CSV/TXT, revisar y editar entradas
campo por campo (system / instruction / output) y guardar el resultado.

Características:
- Vista dual: tabla de resumen + editor de detalle
- Fila activa resaltada; indicador "Entrada X de N"
- Navegación con botones Anterior/Siguiente y click directo en la tabla
- Campos con lock 🔒: el valor se propaga al siguiente al navegar
- Filtro "Solo incompletos" para focalizar el trabajo
- Búsqueda Ctrl+F con reemplazo por entrada o masivo
- Guardado incremental en memoria; botón "Guardar" escribe al disco
"""

import csv
import json
from pathlib import Path

from PySide6.QtCore    import Qt
from PySide6.QtGui     import QColor, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QCheckBox, QFileDialog, QFrame, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QPushButton, QSizePolicy,
    QSplitter, QTableWidget, QTableWidgetItem,
    QTextEdit, QVBoxLayout, QWidget,
)

from modules.curator import formatter as _fmt_mod
from modules.curator.joiner import load_file


PLACEHOLDER = "[COMPLETAR]"

# Colores de fondo de fila
_C_DELETED    = QColor(80,  80,  80)   # gris oscuro
_C_INCOMPLETE = QColor(70,  60,  20)   # amarillo muy oscuro (compatible con tema oscuro)
_C_MATCH      = QColor(100, 80,  0)    # naranja oscuro

# Texto general de filas con fondo especial (alto contraste en tema oscuro)
_C_ROW_TEXT   = QColor(240, 230, 190)  # crema claro sobre fondos oscuros

# Colores de texto en la columna Estado
_T_OK         = QColor(100, 210, 100)
_T_INCOMPLETE = QColor(255, 200, 60)
_T_DELETED    = QColor(200, 100, 100)


# ─────────────────────────────────────────────────────────────────────────────
# Normalización de formatos al canónico interno {system, instruction, clean}
# ─────────────────────────────────────────────────────────────────────────────

def _to_canonical(entry: dict, fmt: str) -> dict:
    """Convierte cualquier entrada al formato canónico del editor."""
    if fmt == "chatml":
        system, instruction, clean = "", PLACEHOLDER, ""
        for msg in entry.get("messages", []):
            r = msg.get("role", "")
            if   r == "system":    system      = msg.get("content", "")
            elif r == "user":      instruction = msg.get("content", "")
            elif r == "assistant": clean       = msg.get("content", "")
        return {"system": system, "instruction": instruction, "clean": clean}

    if fmt == "sharegpt":
        system = entry.get("system", "")
        instruction, clean = PLACEHOLDER, ""
        for turn in entry.get("conversations", []):
            if   turn.get("from") == "human": instruction = turn.get("value", "")
            elif turn.get("from") == "gpt":   clean       = turn.get("value", "")
        return {"system": system, "instruction": instruction, "clean": clean}

    # alpaca, jsonl_raw, csv, txt — estructura plana
    return {
        "system":      entry.get("system", ""),
        "instruction": entry.get("instruction", PLACEHOLDER),
        "clean":       entry.get("output", entry.get("clean", "")),
    }


def _is_incomplete(entry: dict) -> bool:
    instr = entry.get("instruction", "")
    return not instr or instr == PLACEHOLDER


# ─────────────────────────────────────────────────────────────────────────────
# Panel principal
# ─────────────────────────────────────────────────────────────────────────────

class EditorPanel(QWidget):
    """Panel del editor de datasets."""

    # Columnas de la tabla
    _C_NUM   = 0
    _C_INSTR = 1
    _C_OUT   = 2
    _C_STATE = 3

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        self._entries:    list[dict]  = []      # canónico: {system, instruction, clean}
        self._original:   list[dict]  = []      # copia intacta para restaurar
        self._deleted:    set[int]    = set()
        self._visible:    list[int]   = []      # índices mostrados en la tabla
        self._matches:    list[int]   = []      # índices con coincidencia de búsqueda
        self._match_pos:  int         = -1
        self._current:    int         = -1      # índice de entrada activa
        self._source_path: Path | None = None
        self._source_fmt:  str         = ""
        self._building:    bool        = False  # flag anti-recursión al reconstruir tabla
        self._unsaved:     bool        = False

        self._build_ui()
        self._setup_shortcuts()

    # ─────────────────────────────────────────────────────────────────────────
    # Construcción de la UI
    # ─────────────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_toolbar())
        root.addWidget(self._build_search_bar())   # oculta por defecto

        splitter = QSplitter(Qt.Vertical)
        splitter.setContentsMargins(12, 8, 12, 0)

        splitter.addWidget(self._build_table())
        splitter.addWidget(self._build_editor_area())
        splitter.setSizes([220, 400])

        root.addWidget(splitter, stretch=1)
        root.addWidget(self._build_footer())

        self._set_controls_enabled(False)

    def _build_toolbar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("editor-toolbar")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(8)

        btn_open = QPushButton("Abrir")
        btn_open.clicked.connect(self._open_file)
        lay.addWidget(btn_open)

        self._save_btn = QPushButton("Guardar")
        self._save_btn.clicked.connect(self._save_file)
        lay.addWidget(self._save_btn)

        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        lay.addWidget(sep)

        self._filter_check = QCheckBox("Solo incompletos")
        self._filter_check.setChecked(False)
        self._filter_check.toggled.connect(self._on_filter_toggled)
        lay.addWidget(self._filter_check)

        lay.addStretch()

        self._counter_lbl = QLabel("Sin archivo")
        self._counter_lbl.setObjectName("help-text")
        lay.addWidget(self._counter_lbl)

        return bar

    def _build_search_bar(self) -> QFrame:
        self._search_bar = QFrame()
        self._search_bar.setObjectName("search-bar")
        self._search_bar.setVisible(False)

        lay = QHBoxLayout(self._search_bar)
        lay.setContentsMargins(12, 4, 12, 4)
        lay.setSpacing(6)

        lay.addWidget(QLabel("Buscar:"))
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("Texto a buscar...")
        self._search_edit.setFixedWidth(200)
        self._search_edit.textChanged.connect(self._run_search)
        lay.addWidget(self._search_edit)

        btn_prev_match = QPushButton("↑")
        btn_prev_match.setFixedWidth(28)
        btn_prev_match.clicked.connect(self._search_prev)
        lay.addWidget(btn_prev_match)

        btn_next_match = QPushButton("↓")
        btn_next_match.setFixedWidth(28)
        btn_next_match.clicked.connect(self._search_next)
        lay.addWidget(btn_next_match)

        self._match_lbl = QLabel("")
        self._match_lbl.setObjectName("help-text")
        self._match_lbl.setFixedWidth(80)
        lay.addWidget(self._match_lbl)

        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        lay.addWidget(sep)

        lay.addWidget(QLabel("Reemplazar:"))
        self._replace_edit = QLineEdit()
        self._replace_edit.setPlaceholderText("Nuevo texto...")
        self._replace_edit.setFixedWidth(200)
        lay.addWidget(self._replace_edit)

        btn_replace = QPushButton("Esta")
        btn_replace.setFixedWidth(50)
        btn_replace.clicked.connect(self._replace_current)
        lay.addWidget(btn_replace)

        btn_replace_all = QPushButton("Todas")
        btn_replace_all.setFixedWidth(55)
        btn_replace_all.clicked.connect(self._replace_all)
        lay.addWidget(btn_replace_all)

        lay.addStretch()

        btn_close = QPushButton("✕")
        btn_close.setFixedWidth(28)
        btn_close.clicked.connect(self._toggle_search)
        lay.addWidget(btn_close)

        return self._search_bar

    def _build_table(self) -> QTableWidget:
        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["#", "Instruction", "Output", "Estado"])
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setSelectionMode(QTableWidget.SingleSelection)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.horizontalHeader().setStretchLastSection(False)
        self._table.setColumnWidth(self._C_NUM,   42)
        self._table.setColumnWidth(self._C_STATE, 110)
        self._table.horizontalHeader().setSectionResizeMode(
            self._C_INSTR, QHeaderView.Stretch
        )
        self._table.horizontalHeader().setSectionResizeMode(
            self._C_OUT, QHeaderView.Stretch
        )
        self._table.verticalHeader().setVisible(False)
        self._table.setAlternatingRowColors(False)
        self._table.cellClicked.connect(self._on_table_clicked)
        return self._table

    def _build_editor_area(self) -> QWidget:
        area = QWidget()
        lay  = QVBoxLayout(area)
        lay.setContentsMargins(0, 8, 0, 0)
        lay.setSpacing(6)

        # — System
        self._sys_lock, self._sys_edit = self._make_field_row(
            lay, "System:", height=48, lockable=True
        )

        # — Instruction
        self._instr_lock, self._instr_edit = self._make_field_row(
            lay, "Instruction:", height=64, lockable=True
        )

        # — Output
        _, self._out_edit = self._make_field_row(
            lay, "Output:", height=0, lockable=False, expanding=True
        )

        return area

    def _make_field_row(
        self,
        parent_layout: QVBoxLayout,
        label: str,
        height: int,
        lockable: bool,
        expanding: bool = False,
    ) -> tuple:
        """
        Crea una fila con: [botón lock] [label] [QTextEdit].
        Retorna (lock_button, text_edit). lock_button es None si lockable=False.
        """
        row = QHBoxLayout()
        row.setSpacing(6)

        if lockable:
            lock_btn = QPushButton("🔓")
            lock_btn.setCheckable(True)
            lock_btn.setFixedSize(28, 28)
            lock_btn.setToolTip(
                "Bloquear campo: al presionar Siguiente, este valor\n"
                "se copia automáticamente a la siguiente entrada."
            )
            row.addWidget(lock_btn)
        else:
            lock_btn = None
            spacer = QWidget()
            spacer.setFixedSize(28, 28)
            row.addWidget(spacer)

        lbl = QLabel(label)
        lbl.setFixedWidth(88)
        row.addWidget(lbl)

        edit = QTextEdit()
        edit.setAcceptRichText(False)
        if height:
            edit.setFixedHeight(height)
        else:
            edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        font = edit.font()
        font.setFamily("monospace")
        edit.setFont(font)
        row.addWidget(edit)

        parent_layout.addLayout(row)
        return lock_btn, edit

    def _build_footer(self) -> QWidget:
        footer = QFrame()
        footer.setObjectName("editor-footer")
        lay = QHBoxLayout(footer)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(8)

        self._prev_btn = QPushButton("← Anterior")
        self._prev_btn.setFixedHeight(34)
        self._prev_btn.setMinimumWidth(110)
        self._prev_btn.clicked.connect(self._on_prev)
        lay.addWidget(self._prev_btn)

        lay.addStretch()

        self._footer_counter = QLabel("—")
        self._footer_counter.setAlignment(Qt.AlignCenter)
        self._footer_counter.setObjectName("card-title")
        self._footer_counter.setMinimumWidth(160)
        lay.addWidget(self._footer_counter)

        lay.addStretch()

        self._next_btn = QPushButton("Siguiente →")
        self._next_btn.setFixedHeight(34)
        self._next_btn.setMinimumWidth(110)
        self._next_btn.clicked.connect(self._on_next)
        lay.addWidget(self._next_btn)

        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        lay.addWidget(sep)

        self._delete_btn = QPushButton("✗ Eliminar")
        self._delete_btn.setFixedHeight(34)
        self._delete_btn.clicked.connect(self._toggle_delete)
        lay.addWidget(self._delete_btn)

        self._restore_btn = QPushButton("↺ Restaurar")
        self._restore_btn.setFixedHeight(34)
        self._restore_btn.setVisible(False)
        self._restore_btn.clicked.connect(self._toggle_delete)
        lay.addWidget(self._restore_btn)

        return footer

    def _setup_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+F"), self, self._toggle_search)
        QShortcut(QKeySequence("Ctrl+S"), self, self._save_file)

    # ─────────────────────────────────────────────────────────────────────────
    # Carga y guardado
    # ─────────────────────────────────────────────────────────────────────────

    def _open_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Abrir dataset",
            ".",
            "Datasets (*.jsonl *.csv *.txt);;Todos los archivos (*)",
        )
        if path:
            self._load_file(Path(path))

    def _load_file(self, path: Path) -> None:
        raw_entries, fmt = load_file(path)
        if not raw_entries:
            self._counter_lbl.setText("Archivo vacío.")
            return

        self._source_path = path
        self._source_fmt  = fmt
        self._entries     = [_to_canonical(e, fmt) for e in raw_entries]
        self._original    = [dict(e) for e in self._entries]
        self._deleted     = set()
        self._current     = -1
        self._matches     = []
        self._match_pos   = -1
        self._unsaved     = False

        self._rebuild_visible()
        self._rebuild_table()
        self._set_controls_enabled(True)

        if self._visible:
            self._jump_to(self._visible[0])

    def _save_file(self) -> None:
        if not self._source_path or not self._entries:
            return

        self._save_current()

        active = [self._entries[i] for i in range(len(self._entries))
                  if i not in self._deleted]
        ext = self._source_path.suffix.lower()

        if ext == ".csv":
            has_system = any(e["system"] for e in active)
            fields     = (["system", "instruction", "output"] if has_system
                          else ["instruction", "output"])
            with open(self._source_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
                writer.writeheader()
                for e in active:
                    row = {"instruction": e["instruction"], "output": e["clean"]}
                    if has_system:
                        row["system"] = e["system"]
                    writer.writerow(row)

        elif ext == ".txt":
            with open(self._source_path, "w", encoding="utf-8") as f:
                for e in active:
                    if e["system"]:
                        f.write(f"[SYSTEM] {e['system']}\n")
                    f.write(f"[USER]   {e['instruction']}\n")
                    f.write(f"[CHAR]   {e['clean']}\n")
                    f.write("\n")

        else:  # JSONL — cualquier formato
            with open(self._source_path, "w", encoding="utf-8") as f:
                for e in active:
                    converted = _fmt_mod.format_entry(e, self._source_fmt)
                    f.write(json.dumps(converted, ensure_ascii=False) + "\n")

        self._unsaved = False
        self._update_counter()

    # ─────────────────────────────────────────────────────────────────────────
    # Sincronización editor ↔ modelo de datos
    # ─────────────────────────────────────────────────────────────────────────

    def _load_entry_into_editor(self, idx: int) -> None:
        """Carga los campos de la entrada idx en los QTextEdit."""
        e = self._entries[idx]
        self._sys_edit.blockSignals(True)
        self._instr_edit.blockSignals(True)
        self._out_edit.blockSignals(True)

        self._sys_edit.setPlainText(e.get("system", ""))
        self._instr_edit.setPlainText(e.get("instruction", ""))
        self._out_edit.setPlainText(e.get("clean", ""))

        self._sys_edit.blockSignals(False)
        self._instr_edit.blockSignals(False)
        self._out_edit.blockSignals(False)

        # Botón eliminar/restaurar
        is_del = idx in self._deleted
        self._delete_btn.setVisible(not is_del)
        self._restore_btn.setVisible(is_del)

    def _save_current(self) -> None:
        """Persiste los valores del editor en self._entries[_current]."""
        if self._current < 0 or self._current >= len(self._entries):
            return
        e = self._entries[self._current]
        e["system"]      = self._sys_edit.toPlainText()
        e["instruction"] = self._instr_edit.toPlainText()
        e["clean"]       = self._out_edit.toPlainText()
        self._unsaved    = True
        self._update_row(self._current)

    def _apply_locks(self, target_idx: int) -> None:
        """Copia los campos bloqueados de la entrada actual a target_idx."""
        if self._current < 0:
            return
        src = self._entries[self._current]
        dst = self._entries[target_idx]
        if self._sys_lock.isChecked():
            dst["system"] = src["system"]
        if self._instr_lock.isChecked():
            dst["instruction"] = src["instruction"]

    # ─────────────────────────────────────────────────────────────────────────
    # Tabla
    # ─────────────────────────────────────────────────────────────────────────

    def _rebuild_visible(self) -> None:
        """Reconstruye la lista de índices visibles según el filtro activo."""
        filter_on = self._filter_check.isChecked()
        if filter_on:
            self._visible = [
                i for i in range(len(self._entries))
                if i not in self._deleted and _is_incomplete(self._entries[i])
            ]
        else:
            self._visible = list(range(len(self._entries)))

    def _rebuild_table(self) -> None:
        """Reconstruye la tabla completa a partir de _visible."""
        self._building = True
        self._table.clearContents()
        self._table.setRowCount(len(self._visible))

        for row, idx in enumerate(self._visible):
            self._fill_row(row, idx)

        self._building = False
        self._update_counter()

    def _fill_row(self, row: int, idx: int) -> None:
        """Llena una fila con los datos de la entrada idx."""
        e     = self._entries[idx]
        instr = e.get("instruction", "")
        out   = e.get("clean", "")

        num_item   = QTableWidgetItem(str(idx + 1))
        instr_item = QTableWidgetItem(_preview(instr))
        out_item   = QTableWidgetItem(_preview(out))
        state_item = self._make_state_item(idx)

        num_item.setTextAlignment(Qt.AlignCenter)

        for item in (num_item, instr_item, out_item, state_item):
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)

        self._table.setItem(row, self._C_NUM,   num_item)
        self._table.setItem(row, self._C_INSTR, instr_item)
        self._table.setItem(row, self._C_OUT,   out_item)
        self._table.setItem(row, self._C_STATE, state_item)

        self._color_row(row, idx)

    def _make_state_item(self, idx: int) -> QTableWidgetItem:
        if idx in self._deleted:
            item = QTableWidgetItem("✗ Eliminada")
            item.setForeground(_T_DELETED)
        elif _is_incomplete(self._entries[idx]):
            item = QTableWidgetItem("[COMPLETAR]")
            item.setForeground(_T_INCOMPLETE)
        else:
            item = QTableWidgetItem("✓ Completa")
            item.setForeground(_T_OK)
        item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        return item

    def _color_row(self, row: int, idx: int) -> None:
        """Aplica color de fondo y texto a la fila según su estado."""
        if idx in self._matches:
            bg, fg = _C_MATCH, _C_ROW_TEXT
        elif idx in self._deleted:
            bg, fg = _C_DELETED, _C_ROW_TEXT
        elif _is_incomplete(self._entries[idx]):
            bg, fg = _C_INCOMPLETE, _C_ROW_TEXT
        else:
            bg = QColor(0, 0, 0, 0)   # transparente — hereda del tema
            fg = None

        for col in range(self._table.columnCount()):
            item = self._table.item(row, col)
            if item:
                item.setBackground(bg)
                if fg is not None:
                    # Solo sobreescribir el foreground en celdas sin color propio
                    # (la columna Estado tiene su propio color de texto)
                    if col != self._C_STATE:
                        item.setForeground(fg)

    def _update_row(self, idx: int) -> None:
        """Actualiza visualmente una sola fila sin reconstruir toda la tabla."""
        row = self._row_of(idx)
        if row < 0:
            return
        e     = self._entries[idx]
        instr = e.get("instruction", "")
        out   = e.get("clean", "")

        self._table.item(row, self._C_INSTR).setText(_preview(instr))
        self._table.item(row, self._C_OUT).setText(_preview(out))
        state_item = self._make_state_item(idx)
        self._table.setItem(row, self._C_STATE, state_item)
        self._color_row(row, idx)

    def _row_of(self, idx: int) -> int:
        """Retorna la fila en la tabla para el índice de entrada dado, o -1."""
        try:
            return self._visible.index(idx)
        except ValueError:
            return -1

    def _refresh_row_colors(self) -> None:
        """Re-colorea todas las filas (tras búsqueda o filtro)."""
        for row, idx in enumerate(self._visible):
            self._color_row(row, idx)

    # ─────────────────────────────────────────────────────────────────────────
    # Navegación
    # ─────────────────────────────────────────────────────────────────────────

    def _jump_to(self, entry_idx: int) -> None:
        """Salta a la entrada dada, sincroniza tabla y editor."""
        if entry_idx < 0 or entry_idx >= len(self._entries):
            return

        # Si la entrada no está en visible (filtro activo), agregarla temporalmente
        if entry_idx not in self._visible:
            self._visible.append(entry_idx)
            self._visible.sort()
            self._rebuild_table()

        self._current = entry_idx
        self._load_entry_into_editor(entry_idx)

        row = self._row_of(entry_idx)
        if row >= 0:
            self._building = True
            self._table.selectRow(row)
            self._table.scrollToItem(self._table.item(row, 0))
            self._building = False

        self._update_counter()

    def _on_next(self) -> None:
        self._save_current()
        nxt = self._next_non_deleted(self._current, forward=True)
        if nxt >= 0:
            self._apply_locks(nxt)
            self._jump_to(nxt)

    def _on_prev(self) -> None:
        self._save_current()
        prv = self._next_non_deleted(self._current, forward=False)
        if prv >= 0:
            self._jump_to(prv)

    def _next_non_deleted(self, from_idx: int, forward: bool) -> int:
        """Devuelve el siguiente/anterior índice no eliminado (en visible)."""
        step = 1 if forward else -1
        i    = from_idx + step
        while 0 <= i < len(self._entries):
            if i not in self._deleted:
                if not self._filter_check.isChecked() or _is_incomplete(self._entries[i]):
                    return i
                if not self._filter_check.isChecked():
                    return i
            i += step
        return -1

    def _on_table_clicked(self, row: int, _col: int) -> None:
        if self._building or row < 0 or row >= len(self._visible):
            return
        target = self._visible[row]
        if target == self._current:
            return
        self._save_current()
        # Aplicar locks solo si avanzamos (no al retroceder)
        if target > self._current:
            self._apply_locks(target)
        self._jump_to(target)

    # ─────────────────────────────────────────────────────────────────────────
    # Contador
    # ─────────────────────────────────────────────────────────────────────────

    def _update_counter(self) -> None:
        total   = len(self._entries)
        if total == 0:
            self._counter_lbl.setText("Sin archivo")
            self._footer_counter.setText("—")
            return

        deleted    = len(self._deleted)
        incomplete = sum(1 for i, e in enumerate(self._entries)
                         if i not in self._deleted and _is_incomplete(e))
        complete   = total - deleted - incomplete

        # Posición dentro de _visible
        if self._current >= 0 and self._current in self._visible:
            pos = self._visible.index(self._current) + 1
            n   = len(self._visible)
        else:
            pos, n = 0, len(self._visible)

        saved_txt = "● cambios sin guardar" if self._unsaved else ""
        self._counter_lbl.setText(
            f"{complete} completas · {incomplete} incompletas · {deleted} eliminadas  {saved_txt}"
        )
        self._footer_counter.setText(
            f"Entrada {pos} de {n}" if pos else "—"
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Filtro
    # ─────────────────────────────────────────────────────────────────────────

    def _on_filter_toggled(self, _checked: bool) -> None:
        self._rebuild_visible()
        self._rebuild_table()
        if self._visible:
            # Intentar mantener la entrada actual visible
            if self._current in self._visible:
                self._jump_to(self._current)
            else:
                self._jump_to(self._visible[0])

    # ─────────────────────────────────────────────────────────────────────────
    # Búsqueda y reemplazo
    # ─────────────────────────────────────────────────────────────────────────

    def _toggle_search(self) -> None:
        visible = not self._search_bar.isVisible()
        self._search_bar.setVisible(visible)
        if visible:
            self._search_edit.setFocus()
            self._search_edit.selectAll()
        else:
            self._matches   = []
            self._match_pos = -1
            self._match_lbl.setText("")
            self._refresh_row_colors()

    def _run_search(self) -> None:
        q = self._search_edit.text().strip().lower()
        self._matches   = []
        self._match_pos = -1

        if q:
            for i, e in enumerate(self._entries):
                text = f"{e.get('system','')} {e.get('instruction','')} {e.get('clean','')}".lower()
                if q in text:
                    self._matches.append(i)

        n = len(self._matches)
        if n == 0:
            self._match_lbl.setText("Sin resultados" if q else "")
        else:
            self._match_pos = 0
            self._match_lbl.setText(f"1 de {n}")
            self._jump_to(self._matches[0])

        self._refresh_row_colors()

    def _search_next(self) -> None:
        if not self._matches:
            return
        self._match_pos = (self._match_pos + 1) % len(self._matches)
        self._match_lbl.setText(f"{self._match_pos + 1} de {len(self._matches)}")
        self._jump_to(self._matches[self._match_pos])

    def _search_prev(self) -> None:
        if not self._matches:
            return
        self._match_pos = (self._match_pos - 1) % len(self._matches)
        self._match_lbl.setText(f"{self._match_pos + 1} de {len(self._matches)}")
        self._jump_to(self._matches[self._match_pos])

    def _replace_current(self) -> None:
        """Reemplaza en la entrada actual los campos que contienen el texto buscado."""
        if self._current < 0:
            return
        q   = self._search_edit.text()
        rep = self._replace_edit.text()
        if not q:
            return

        self._save_current()
        e   = self._entries[self._current]
        changed = False
        for field in ("system", "instruction", "clean"):
            if q in e[field]:
                e[field] = e[field].replace(q, rep)
                changed = True

        if changed:
            self._load_entry_into_editor(self._current)
            self._update_row(self._current)
            self._unsaved = True

        # Avanzar al siguiente resultado
        self._search_next()

    def _replace_all(self) -> None:
        """Reemplaza en todas las entradas que tienen coincidencia."""
        q   = self._search_edit.text()
        rep = self._replace_edit.text()
        if not q or not self._matches:
            return

        self._save_current()
        count = 0
        for idx in self._matches:
            e = self._entries[idx]
            for field in ("system", "instruction", "clean"):
                if q in e[field]:
                    e[field] = e[field].replace(q, rep)
                    count += 1

        self._match_lbl.setText(f"{count} reemplazos")
        self._matches = []
        self._refresh_row_colors()
        self._rebuild_table()
        self._unsaved = True

        if self._current >= 0:
            self._load_entry_into_editor(self._current)

    # ─────────────────────────────────────────────────────────────────────────
    # Eliminar / Restaurar
    # ─────────────────────────────────────────────────────────────────────────

    def _toggle_delete(self) -> None:
        if self._current < 0:
            return
        if self._current in self._deleted:
            self._deleted.discard(self._current)
        else:
            self._deleted.add(self._current)

        self._unsaved = True
        self._update_row(self._current)
        self._load_entry_into_editor(self._current)   # actualiza botones
        self._update_counter()

    # ─────────────────────────────────────────────────────────────────────────
    # Habilitar / deshabilitar controles
    # ─────────────────────────────────────────────────────────────────────────

    def _set_controls_enabled(self, enabled: bool) -> None:
        for w in (
            self._save_btn, self._filter_check,
            self._prev_btn, self._next_btn,
            self._delete_btn, self._restore_btn,
            self._sys_edit, self._instr_edit, self._out_edit,
            self._sys_lock, self._instr_lock,
        ):
            w.setEnabled(enabled)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _preview(text: str, length: int = 80) -> str:
    """Trunca el texto para mostrarlo en la tabla."""
    text = text.replace("\n", " ").strip()
    return text[:length] + "…" if len(text) > length else text
