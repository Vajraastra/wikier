"""
CuratorWorker: ejecuta el pipeline de curación en un QThread separado.

El personaje se auto-detecta del nombre del archivo de entrada
(patrón: {Personaje}_dataset.jsonl → "Personaje").

El directorio de salida es siempre: mismo directorio que el input / curated/
"""
import csv
import json
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from modules.curator.curator import curate, CuratorConfig, CuratorResult
from modules.scraper.exporter import export_sets


class CuratorWorker(QThread):
    """
    Corre curate() en background y emite progreso paso a paso.

    Señales:
        progress(percent, message) — actualización de progreso (0–100).
        finished(result, out_dir)  — al terminar: CuratorResult + Path de salida.
        error(message)             — mensaje si algo falla.
    """

    progress = Signal(int, str)
    finished = Signal(object, object)   # (CuratorResult, Path)
    error    = Signal(str)

    def __init__(
        self,
        input_path:  str,
        personality: str,
        config:      CuratorConfig,
        formats:     list[str],       # ["jsonl", "csv", "txt"]
        parent=None,
    ):
        super().__init__(parent)
        self._input_path  = Path(input_path)
        self._personality = personality
        self._config      = config
        self._formats     = formats

    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def detect_character(path: Path) -> str:
        """
        Extrae el nombre del personaje del nombre del archivo.
        "Marinette_dataset.jsonl" → "Marinette"
        Si el patrón no aplica, retorna el stem completo.
        """
        stem = path.stem  # sin extensión
        if "_" in stem:
            return stem.split("_")[0]
        return stem

    # ─────────────────────────────────────────────────────────────────────────

    def run(self) -> None:
        try:
            character = self.detect_character(self._input_path)

            # — Perfil mínimo construido desde el nombre del archivo
            profile = {
                "name":              character,
                "character_aliases": {character: [character]},
                "personality":       self._personality,
                "system_prompt_fields": {
                    "character":   True,
                    "show":        False,   # sin show info disponible
                    "aliases":     False,
                    "personality": True,
                },
            }

            # — Cargar entradas
            entries = []
            with open(self._input_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        entries.append(json.loads(line))

            if not entries:
                self.error.emit("El archivo de entrada está vacío.")
                return

            # — Ejecutar pipeline
            result: CuratorResult = curate(
                entries,
                profile,
                character,
                self._config,
                progress_cb=lambda pct, msg: self.progress.emit(pct, msg),
            )

            # — Directorio de salida: junto al input, en subcarpeta "curated"
            out_dir = self._input_path.parent / "curated"
            out_dir.mkdir(parents=True, exist_ok=True)

            self.progress.emit(97, "Exportando archivos...")

            # — Exportar en los formatos solicitados
            if "jsonl" in self._formats:
                export_sets(result.formatted, str(out_dir))

            if "csv" in self._formats:
                _export_flat_csv(result.formatted, out_dir)

            if "txt" in self._formats:
                _export_flat_txt(result.formatted, out_dir)

            # — Archivados siempre en JSONL (para inspección)
            archived_non_empty = {k: v for k, v in result.archived.items() if v}
            if archived_non_empty:
                export_sets(archived_non_empty, str(out_dir / "archived"))

            self.finished.emit(result, out_dir)

        except Exception as exc:
            import traceback
            self.error.emit(f"{exc}\n{traceback.format_exc()}")


# ─────────────────────────────────────────────────────────────────────────────
# Exportadores planos (CSV y TXT) — estructura apta para edición manual
# ─────────────────────────────────────────────────────────────────────────────

def _export_flat_csv(sets: dict[str, list[dict]], out_dir: Path) -> None:
    """
    Exporta cada categoría a un CSV plano para edición manual.

    Columnas:  instruction | output              (si no hay system prompt)
    Columnas:  system | instruction | output     (si alguna entrada tiene system)

    'instruction' sale como [COMPLETAR] — el usuario lo rellena en el editor.
    'output' contiene el texto limpio del personaje.
    """
    for cat, entries in sets.items():
        if not entries:
            continue

        # Determinar si incluir columna system según los datos reales
        rows = [_flatten_entry(e) for e in entries]
        has_system = any(r["system"] for r in rows)
        fieldnames = (["system", "instruction", "output"] if has_system
                      else ["instruction", "output"])

        path = out_dir / f"{cat}.csv"
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)


def _export_flat_txt(sets: dict[str, list[dict]], out_dir: Path) -> None:
    """
    Exporta cada categoría a TXT.
    Formato por entrada:
        [SYSTEM] texto del system prompt
        [USER]   [COMPLETAR]
        [CHAR]   texto del personaje
        (línea en blanco)
    """
    for cat, entries in sets.items():
        if not entries:
            continue
        path = out_dir / f"{cat}.txt"
        with open(path, "w", encoding="utf-8") as f:
            for entry in entries:
                row = _flatten_entry(entry)
                if row["system"]:      # solo si la entrada tiene system prompt
                    f.write(f"[SYSTEM] {row['system']}\n")
                f.write(f"[USER]   {row['instruction']}\n")
                f.write(f"[CHAR]   {row['output']}\n")
                f.write("\n")


def _flatten_entry(entry: dict) -> dict:
    """
    Convierte cualquier formato de entrada (ChatML, Alpaca, ShareGPT, raw)
    a un dict plano {system, instruction, output}.
    """
    # ChatML: {"messages": [...]}
    if "messages" in entry:
        system = ""
        instruction = "[COMPLETAR]"
        output = ""
        for msg in entry["messages"]:
            role = msg.get("role", "")
            if role == "system":
                system = msg["content"]
            elif role == "user":
                instruction = msg["content"]
            elif role == "assistant":
                output = msg["content"]
        return {"system": system, "instruction": instruction, "output": output}

    # ShareGPT: {"system": ..., "conversations": [...]}
    if "conversations" in entry:
        system = entry.get("system", "")
        instruction = "[COMPLETAR]"
        output = ""
        for turn in entry["conversations"]:
            if turn.get("from") == "human":
                instruction = turn["value"]
            elif turn.get("from") == "gpt":
                output = turn["value"]
        return {"system": system, "instruction": instruction, "output": output}

    # Alpaca / JSONL raw
    return {
        "system":      entry.get("system", ""),
        "instruction": entry.get("instruction", "[COMPLETAR]"),
        "output":      entry.get("output", ""),
    }
