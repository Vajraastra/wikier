"""
Discovery: indexa todos los speakers de un wiki con conteo de líneas.

Soporta dos modos de progreso:
  - CLI (on_progress=None): usa Rich Progress bars.
  - TUI (on_progress=callable): llama al callback en lugar de renderizar Rich.
    Firma del callback: on_progress(current: int, total: int, message: str)
"""
import json
import hashlib
from collections import Counter
from pathlib import Path
from typing import Callable

from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table
from rich import box

from modules.scraper.walker import walk_category
from modules.scraper.fetcher import get_wikitext
from modules.scraper.parser import parse_dialogue
from modules.scraper.config import INDEX_DIR

console = Console()

ProgressCb = Callable[[int, int, str], None]


# ─────────────────────────────────────────────────────────────────────────────
# Gestión del índice en disco
# ─────────────────────────────────────────────────────────────────────────────

def _index_path(base_url: str, categories: list[str]) -> Path:
    slug = base_url.replace("https://", "").replace("http://", "").split("/")[0].replace(".", "_")
    key = hashlib.md5((base_url + "|" + "|".join(sorted(categories))).encode()).hexdigest()[:10]
    return INDEX_DIR / f"{slug}_{key}.json"


def load_index(base_url: str, categories: list[str]) -> dict | None:
    path = _index_path(base_url, categories)
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return None


def delete_index(base_url: str, categories: list[str]) -> bool:
    path = _index_path(base_url, categories)
    if path.exists():
        path.unlink()
        return True
    return False


def _save_index(base_url: str, categories: list[str], index: dict) -> None:
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    path = _index_path(base_url, categories)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)


# ─────────────────────────────────────────────────────────────────────────────
# Construcción del índice
# ─────────────────────────────────────────────────────────────────────────────

def build_index(
    base_url: str,
    categories: list[str],
    rate_limit: float = 0.5,
    format_hint: str = "auto",
    on_progress: ProgressCb | None = None,
) -> dict:
    """
    Descarga y parsea todos los transcripts. Guarda el índice en disco.

    Args:
        base_url:     URL base del wiki.
        categories:   Lista de nombres de categoría.
        rate_limit:   Segundos entre requests.
        format_hint:  Hint de formato para el parser.
        on_progress:  Callback opcional para TUI. Si es None, usa Rich.
                      Firma: (current, total, message) → None

    Returns:
        Índice con speakers, páginas y páginas no reconocidas.
    """
    # ── Fase 1: recolectar títulos ────────────────────────────────────────────
    all_titles: list[str] = []

    if on_progress:
        on_progress(0, 0, "Listando páginas de transcripts...")
        for cat in categories:
            for title in walk_category(base_url, cat, rate_limit):
                all_titles.append(title)
        on_progress(0, len(all_titles), f"✓ {len(all_titles)} páginas encontradas")
    else:
        with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as prog:
            task = prog.add_task("Listando páginas...", total=None)
            for cat in categories:
                for title in walk_category(base_url, cat, rate_limit):
                    all_titles.append(title)
            prog.update(task, description=f"[green]{len(all_titles)} páginas encontradas.[/green]")

    if not all_titles:
        msg = "No se encontraron páginas. Verificá el nombre de la categoría."
        if on_progress:
            on_progress(0, 0, f"✗ {msg}")
        else:
            console.print(f"[red]{msg}[/red]")
        return {"base_url": base_url, "categories": categories, "pages": [], "speakers": {}, "unrecognized": []}

    # ── Fase 2: parsear y contar speakers ─────────────────────────────────────
    speaker_counts: Counter = Counter()
    pages_ok: list[str] = []
    unrecognized: list[str] = []
    total = len(all_titles)

    if on_progress:
        for i, title in enumerate(all_titles, 1):
            on_progress(i, total, title)
            wikitext = get_wikitext(base_url, title, rate_limit)
            if not wikitext:
                continue
            lines, fmt = parse_dialogue(wikitext, format_hint)
            if fmt == "unknown":
                unrecognized.append(title)
            else:
                for line in lines:
                    if line.speaker and not line.is_action:
                        speaker_counts[line.speaker] += 1
                pages_ok.append(title)
        on_progress(total, total, f"✓ Indexación completa ({len(pages_ok)} páginas)")
    else:
        with Progress(
            SpinnerColumn(),
            TextColumn("{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Indexando...", total=total)
            for title in all_titles:
                progress.update(task, description=f"[dim]{title[:55]}[/dim]")
                wikitext = get_wikitext(base_url, title, rate_limit)
                if not wikitext:
                    progress.advance(task)
                    continue
                lines, fmt = parse_dialogue(wikitext, format_hint)
                if fmt == "unknown":
                    unrecognized.append(title)
                else:
                    for line in lines:
                        if line.speaker and not line.is_action:
                            speaker_counts[line.speaker] += 1
                    pages_ok.append(title)
                progress.advance(task)

    index = {
        "base_url": base_url,
        "categories": categories,
        "pages": pages_ok,
        "speakers": dict(speaker_counts.most_common()),
        "unrecognized": unrecognized,
    }
    _save_index(base_url, categories, index)

    if unrecognized and not on_progress:
        console.log(f"[yellow]{len(unrecognized)} páginas con formato no reconocido.[/yellow]")

    return index


# ─────────────────────────────────────────────────────────────────────────────
# Character roster
# ─────────────────────────────────────────────────────────────────────────────

def export_character_roster(
    profile: dict,
    index: dict,
    character: str,
    output_dir,
):
    """
    Genera {Character}_characters.json en output_dir.

    Combina los aliases del perfil JSON con los speakers del índice para
    construir la lista de personajes secundarios que usará el name_tagger.

    Args:
        profile:     Perfil JSON del wiki (character_aliases, language, ...).
        index:       Índice de speakers generado por build_index.
        character:   Nombre canónico del personaje principal.
        output_dir:  Directorio donde se escribe el roster (str o Path).

    Returns:
        Path al archivo generado.
    """
    from pathlib import Path as _Path

    output_dir = _Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    aliases_map: dict = profile.get("character_aliases", {})

    # Aliases del personaje principal (busca coincidencia case-insensitive)
    main_aliases: list[str] = []
    for char_name, alias_list in aliases_map.items():
        if char_name.lower() == character.lower():
            main_aliases = alias_list
            break
    if not main_aliases:
        main_aliases = [character]

    main_lower = {a.lower() for a in main_aliases}

    # Personajes secundarios: speakers del índice que no son el principal
    all_speakers: dict[str, int] = index.get("speakers", {})
    supporting: dict[str, list[str]] = {}
    for speaker in all_speakers:
        if speaker.lower() not in main_lower:
            # Usa aliases del perfil si existen; si no, solo el nombre
            supporting[speaker] = aliases_map.get(speaker, [speaker])

    roster = {
        "main_character":        character,
        "main_aliases":          main_aliases,
        "language":              profile.get("language", "en"),
        "supporting_characters": supporting,
    }

    char_slug = character.replace(" ", "_")
    out_path = output_dir / f"{char_slug}_characters.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(roster, f, indent=2, ensure_ascii=False)

    return out_path


# ─────────────────────────────────────────────────────────────────────────────
# Presentación (modo CLI)
# ─────────────────────────────────────────────────────────────────────────────

def show_speakers_table(index: dict) -> None:
    speakers = index.get("speakers", {})
    pages_count = len(index.get("pages", []))

    if not speakers:
        console.print("[yellow]No se encontraron personajes en el índice.[/yellow]")
        return

    table = Table(
        title=f"Personajes encontrados en {pages_count} transcripts",
        box=box.ROUNDED,
        border_style="cyan",
    )
    table.add_column("#", style="dim", justify="right", no_wrap=True, width=4)
    table.add_column("Personaje", style="white")
    table.add_column("Líneas", style="cyan", justify="right")

    for i, (speaker, count) in enumerate(speakers.items(), 1):
        table.add_row(str(i), speaker, str(count))

    console.print(table)
