"""
JoinerWorker: ejecuta el pipeline del Joiner en un QThread separado.

Dos modos de operación:
    "pipeline"  — carga sets de una carpeta, aplica merge/shuffle/split/export
    "convert"   — convierte un archivo a otro formato JSONL

Señales comunes:
    progress(percent, message)  — actualización de progreso (0–100)
    finished(report, out_paths) — reporte de texto + lista de rutas escritas
    error(message)              — mensaje si algo falla
"""

import json
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from modules.curator import joiner


# Nombres de archivo que el curator exporta por categoría
_CATEGORY_FILES = {
    "dialogue_clean":          "dialogue_clean.jsonl",
    "dialogue_mixed_thought":  "dialogue_mixed_thought.jsonl",
    "dialogue_mixed_action":   "dialogue_mixed_action.jsonl",
}


class JoinerWorker(QThread):
    """
    Worker para el módulo Joiner.

    Señales:
        progress(percent, message)   — progreso de 0 a 100.
        finished(report, out_paths)  — str con reporte + list[str] con rutas.
        error(message)               — descripción del error.
    """

    progress = Signal(int, str)
    finished = Signal(str, list)
    error    = Signal(str)

    def __init__(
        self,
        mode:        str,               # "pipeline" | "convert"
        # — pipeline
        input_dir:   str  = "",
        objective:   str  = "dialogue",
        train_ratio: float = 0.8,
        val_ratio:   float = 0.1,
        test_ratio:  float = 0.1,
        seed:        int   = 42,
        max_entries: int   = 0,         # 0 = sin límite
        prefix:      str   = "",
        # — convert
        input_file:  str  = "",
        target_fmt:  str  = "chatml",
        source_fmt:  str  = "",         # "" = auto-detectar
        parent = None,
    ):
        super().__init__(parent)
        self._mode        = mode
        self._input_dir   = Path(input_dir)   if input_dir  else Path()
        self._objective   = objective
        self._train_ratio = train_ratio
        self._val_ratio   = val_ratio
        self._test_ratio  = test_ratio
        self._seed        = seed
        self._max_entries = max_entries if max_entries > 0 else None
        self._prefix      = prefix
        self._input_file  = Path(input_file) if input_file else Path()
        self._target_fmt  = target_fmt
        self._source_fmt  = source_fmt or None

    # ─────────────────────────────────────────────────────────────────────────

    def run(self) -> None:
        try:
            if self._mode == "pipeline":
                self._run_pipeline()
            elif self._mode == "convert":
                self._run_convert()
            else:
                self.error.emit(f"Modo desconocido: '{self._mode}'")
        except Exception as exc:
            import traceback
            self.error.emit(f"{exc}\n{traceback.format_exc()}")

    # ─────────────────────────────────────────────────────────────────────────
    # Pipeline
    # ─────────────────────────────────────────────────────────────────────────

    def _run_pipeline(self) -> None:
        self.progress.emit(5, "Cargando sets del curator...")

        sets: dict[str, list[dict]] = {}
        for cat, filename in _CATEGORY_FILES.items():
            path = self._input_dir / filename
            if path.exists():
                entries, _ = joiner.load_file(path)
                if entries:
                    sets[cat] = entries

        if not sets:
            self.error.emit(
                f"No se encontraron archivos de categorías en:\n{self._input_dir}\n\n"
                "Asegurate de seleccionar la carpeta curated/ generada por el Curator."
            )
            return

        total_loaded = sum(len(v) for v in sets.values())
        self.progress.emit(20, f"Cargados {total_loaded} entradas en {len(sets)} categorías.")

        # — Merge
        self.progress.emit(35, f"Mergeando sets (objetivo: {self._objective})...")
        merged = joiner.merge(sets, objective=self._objective, max_entries=self._max_entries)

        if not merged:
            self.error.emit("El merge no produjo entradas. Verificá el objetivo y los archivos.")
            return

        # — Shuffle
        self.progress.emit(50, f"Shuffleando {len(merged)} entradas (seed={self._seed})...")
        shuffled = joiner.shuffle(merged, seed=self._seed)

        # — Split
        self.progress.emit(65, "Dividiendo en train / validation / test...")
        train, val, test = joiner.split(
            shuffled,
            train=self._train_ratio,
            val=self._val_ratio,
            test=self._test_ratio,
        )

        # — Export
        out_dir = self._input_dir / "joined"
        self.progress.emit(80, f"Exportando archivos en {out_dir}...")
        paths = joiner.export(train, val, test, output_dir=out_dir, prefix=self._prefix)

        # — Reporte
        obj_label = joiner.OBJECTIVES.get(self._objective, {}).get("label", self._objective)
        lines = [
            "── Joiner — Pipeline completado",
            f"   Objetivo       : {self._objective}  ({obj_label})",
            f"   Entradas totales: {len(merged):>7,}",
            f"   Train           : {len(train):>7,}",
            f"   Validation      : {len(val):>7,}",
            f"   Test            : {len(test):>7,}",
            f"   Seed            : {self._seed}",
            "",
            "   Archivos generados:",
        ]
        for p in paths:
            lines.append(f"     {Path(p).name}")
        lines.append(f"\n   Directorio: {out_dir}")

        report = "\n".join(lines)
        self.progress.emit(100, "Completado.")
        self.finished.emit(report, [str(p) for p in paths])

    # ─────────────────────────────────────────────────────────────────────────
    # Conversor de formatos
    # ─────────────────────────────────────────────────────────────────────────

    def _run_convert(self) -> None:
        self.progress.emit(10, "Cargando archivo de entrada...")

        if not self._input_file.exists():
            self.error.emit(f"Archivo no encontrado: {self._input_file}")
            return

        # Nombre de salida: mismo directorio, sufijo _converted + .jsonl
        stem       = self._input_file.stem
        out_path   = self._input_file.parent / f"{stem}_converted_{self._target_fmt}.jsonl"

        self.progress.emit(40, f"Convirtiendo a formato {self._target_fmt}...")
        count = joiner.convert_file(
            input_path  = self._input_file,
            output_path = out_path,
            target_fmt  = self._target_fmt,
            source_fmt  = self._source_fmt,
        )

        # Detectar formato fuente para mostrarlo en el reporte
        _, detected = joiner.load_file(self._input_file)
        source_label = self._source_fmt or detected

        lines = [
            "── Joiner — Conversión completada",
            f"   Formato fuente : {source_label}",
            f"   Formato destino: {self._target_fmt}",
            f"   Entradas       : {count:,}",
            f"   Archivo        : {out_path.name}",
            f"\n   Directorio: {out_path.parent}",
        ]
        report = "\n".join(lines)
        self.progress.emit(100, "Completado.")
        self.finished.emit(report, [str(out_path)])
