"""
Fandom Dialogue Scraper — Entry point.

Uso:
  python main.py            → lanza la GUI (PySide6)
  python main.py --cli      → modo terminal (Typer + Rich)
  python main.py --cli scrape --wiki miraculousladybug ...
"""
import json
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich import box

from modules.scraper.fetcher import get_wikitext, setup_cache, clear_cache
from modules.scraper.walker import walk_category, parse_fandom_url
from modules.scraper.parser import parse_dialogue
from modules.scraper.filter import filter_character
from modules.scraper.exporter import export
from modules.scraper.discovery import build_index, load_index, delete_index, show_speakers_table
from modules.scraper.config import PROFILES_DIR, OUTPUT_DIR, INDEX_DIR

# ─────────────────────────────────────────────────────────────────────────────
# Configuración global
# ─────────────────────────────────────────────────────────────────────────────

console = Console()
LOG_FILE = OUTPUT_DIR / "unrecognized_pages.log"

app = typer.Typer(
    name="wikier",
    help="Extrae diálogos de personajes desde wikis de Fandom para datasets de fine-tuning.",
    add_completion=False,
    invoke_without_command=True,
)


@app.callback()
def default(ctx: typer.Context) -> None:
    """Muestra la pantalla de inicio si no se pasa ningún comando."""
    if ctx.invoked_subcommand is None:
        _print_header()
        _show_profiles_table()
        console.print(
            "\n[dim]Comandos:[/dim] scrape · profiles · profile-create · cache-clear\n"
            "[dim]Ejemplo:[/dim]  wikier scrape --url \"https://miraculousladybug.fandom.com/wiki/Category:Transcripts\"\n"
            "[dim]Ayuda:[/dim]    wikier --help\n"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Utilidades de TUI
# ─────────────────────────────────────────────────────────────────────────────

def _print_header() -> None:
    console.print(
        Panel.fit(
            "[bold cyan]Fandom Dialogue Scraper[/bold cyan]\n"
            "[dim]Extractor de diálogos para datasets de fine-tuning[/dim]",
            border_style="cyan",
            padding=(0, 2),
        )
    )


def _load_profile(wiki_name: str) -> dict:
    """Carga el perfil JSON de un wiki. Termina con error si no existe."""
    profile_path = PROFILES_DIR / f"{wiki_name}.json"
    if not profile_path.exists():
        available = [p.stem for p in PROFILES_DIR.glob("*.json")]
        console.print(f"[red]Perfil '{wiki_name}' no encontrado.[/red]")
        console.print(f"Perfiles disponibles: {', '.join(available)}")
        raise typer.Exit(1)
    with open(profile_path, encoding="utf-8") as f:
        return json.load(f)


def _show_profiles_table() -> None:
    """Muestra una tabla con todos los perfiles disponibles."""
    profiles = list(sorted(PROFILES_DIR.glob("*.json")))
    if not profiles:
        console.print("[dim]No hay perfiles guardados. Usá --url para empezar sin perfil.[/dim]")
        return

    table = Table(title="Perfiles guardados", box=box.ROUNDED, border_style="dim")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Nombre", style="white")
    table.add_column("URL base", style="dim")
    table.add_column("Categorías", justify="right")

    for p in profiles:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        table.add_row(
            p.stem,
            data.get("name", "—"),
            data.get("base_url", "—"),
            str(len(data.get("transcript_categories", []))),
        )
    console.print(table)


def _resolve_source(
    url: str | None,
    wiki: str | None,
) -> tuple[str, list[str], float, dict, str]:
    """
    Resuelve la fuente de datos desde --url o --wiki.

    Returns:
        (base_url, categories, rate_limit, aliases_dict, wiki_name)
    """
    url = url or ""
    wiki = wiki or ""

    if url and wiki:
        console.print("[red]Usá --url O --wiki, no ambos a la vez.[/red]")
        raise typer.Exit(1)

    if not url and not wiki:
        console.print("[red]Necesitás especificar --url o --wiki.[/red]")
        console.print("[dim]Ejemplo: wikier scrape --url \"https://miraculousladybug.fandom.com/wiki/Category:Transcripts\"[/dim]")
        raise typer.Exit(1)

    if url:
        try:
            base_url, category = parse_fandom_url(url)
        except ValueError as e:
            console.print(f"[red]{e}[/red]")
            raise typer.Exit(1)
        return base_url, [category], 0.5, {}, base_url.split("//")[1].split(".")[0].title()

    # Desde perfil
    profile = _load_profile(wiki)
    return (
        profile["base_url"],
        profile.get("transcript_categories", []),
        profile.get("rate_limit_seconds", 0.5),
        profile.get("character_aliases", {}),
        profile.get("name", wiki),
    )


def _resolve_aliases(character: str, aliases_dict: dict) -> list[str]:
    """Busca el personaje en el dict de aliases y retorna la lista de variantes."""
    for key, aliases in aliases_dict.items():
        if key.lower() == character.lower() or character.lower() in [a.lower() for a in aliases]:
            return [a for a in aliases if a.lower() != character.lower()]
    return []


# ─────────────────────────────────────────────────────────────────────────────
# Comando: scrape
# ─────────────────────────────────────────────────────────────────────────────

@app.command()
def scrape(
    url: str = typer.Option("", "--url", "-u",
        help="URL de la categoría de transcripts (desde el navegador)."),
    wiki: str = typer.Option("", "--wiki", "-w",
        help="ID del perfil guardado (alternativa a --url)."),
    character: list[str] = typer.Option([], "--character", "-c",
        help="Personaje(s) a extraer. Repetible: -c Marinette -c Adrien."),
    output: str = typer.Option("dataset", "--output", "-o",
        help="Ruta base del archivo de salida (sin extensión)."),
    formats: list[str] = typer.Option(["jsonl"], "--format", "-f",
        help="Formatos de salida. Repetible: -f jsonl -f csv"),
    context_window: int = typer.Option(3, "--context-window", "-n",
        help="Líneas de contexto anteriores a incluir."),
    include_actions: bool = typer.Option(False, "--include-actions",
        help="Incluir action lines en el contexto."),
    format_hint: str = typer.Option("auto", "--format-hint",
        help="Forzar formato del parser: auto | bold-colon | template"),
    no_cache: bool = typer.Option(False, "--no-cache",
        help="Ignorar cache HTTP (re-descarga todo)."),
    rebuild_index: bool = typer.Option(False, "--rebuild-index",
        help="Forzar re-indexación aunque ya exista el índice."),
    sample: int = typer.Option(0, "--sample", "-s",
        help="Procesar solo N páginas para pruebas (0 = todas)."),
) -> None:
    """
    Extrae diálogos de personaje(s) desde un wiki de Fandom.

    Flujo en dos fases:
      1. Indexación: descarga y cachea todos los transcripts, descubre personajes.
      2. Extracción: filtra por personaje y exporta el dataset.

    La segunda vez que corrés el mismo --url, la fase 1 es instantánea (usa cache).
    """
    _print_header()

    # Configurar cache HTTP
    if not no_cache:
        setup_cache()

    # Resolver fuente de datos
    base_url, categories, rate_limit, aliases_dict, wiki_name = _resolve_source(url, wiki)

    console.print(Panel(
        f"[bold]Fuente:[/bold]    {wiki_name}\n"
        f"[bold]URL base:[/bold]  {base_url}\n"
        f"[bold]Categorías:[/bold]\n" + "\n".join(f"  • {c}" for c in categories),
        title="Configuración",
        border_style="blue",
    ))

    # ── Fase 1: Índice ────────────────────────────────────────────────────────

    if rebuild_index:
        deleted = delete_index(base_url, categories)
        if deleted:
            console.print("[yellow]Índice anterior eliminado. Re-indexando...[/yellow]")

    index = load_index(base_url, categories)

    if index:
        console.print(
            f"[green]Índice cargado desde cache[/green] "
            f"({len(index['pages'])} páginas, {len(index['speakers'])} personajes)"
        )
    else:
        console.print("[cyan]Construyendo índice por primera vez...[/cyan]")
        if sample > 0:
            # En modo sample, construir índice parcial sin guardarlo
            console.print(f"[yellow]Modo muestra: solo {sample} páginas.[/yellow]")
            index = _build_sample_index(base_url, categories, rate_limit, format_hint, sample)
        else:
            index = build_index(base_url, categories, rate_limit, format_hint)

    if not index["pages"]:
        console.print("[red]No se indexaron páginas. Verificá la URL de la categoría.[/red]")
        raise typer.Exit(1)

    # ── Fase 2: Selección de personaje(s) ────────────────────────────────────

    show_speakers_table(index)

    if character:
        characters = list(character)
    else:
        raw = Prompt.ask(
            "\nPersonaje(s) a extraer [dim](nombre exacto o separados por coma)[/dim]"
        )
        characters = [c.strip() for c in raw.split(",") if c.strip()]

    if not characters:
        console.print("[red]No se especificó ningún personaje.[/red]")
        raise typer.Exit(1)

    # ── Fase 3: Extracción y exportación ─────────────────────────────────────

    unrecognized_global: list[str] = []

    for char in characters:
        char_aliases = _resolve_aliases(char, aliases_dict)
        console.print(f"\n[bold cyan]Extrayendo:[/bold cyan] {char}"
                      + (f" [dim](aliases: {', '.join(char_aliases)})[/dim]" if char_aliases else ""))

        all_pairs: list[dict] = []
        unrecognized: list[str] = []

        for title in index["pages"]:
            wikitext = get_wikitext(base_url, title, rate_limit)
            if not wikitext:
                continue

            lines, detected_fmt = parse_dialogue(wikitext, format_hint)

            if detected_fmt == "unknown":
                unrecognized.append(title)
                continue

            pairs = filter_character(
                lines,
                target=char,
                aliases=char_aliases,
                context_window=context_window,
                include_actions=include_actions,
            )
            for pair in pairs:
                pair["source_page"] = title
            all_pairs.extend(pairs)

        unrecognized_global.extend(unrecognized)

        # Nombre del archivo: dataset_Marinette.jsonl si hay múltiples personajes
        out_path = f"{output}_{char.replace(' ', '_')}" if len(characters) > 1 else output

        if all_pairs:
            export(all_pairs, out_path, formats)
        else:
            console.print(f"[yellow]No se encontraron líneas de '{char}'.[/yellow]")

        # Resumen por personaje
        summary = Table(box=box.SIMPLE_HEAD, show_header=False)
        summary.add_column("Métrica", style="dim")
        summary.add_column("Valor", style="bold")
        summary.add_row("Páginas procesadas", str(len(index["pages"])))
        summary.add_row("Pares extraídos", str(len(all_pairs)))
        console.print(summary)

    # Guardar páginas no reconocidas
    if unrecognized_global:
        unique_unrecognized = list(dict.fromkeys(unrecognized_global))
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(unique_unrecognized))
        console.print(f"[yellow]{len(unique_unrecognized)} páginas no reconocidas → {LOG_FILE}[/yellow]")


def _build_sample_index(
    base_url: str,
    categories: list[str],
    rate_limit: float,
    format_hint: str,
    sample: int,
) -> dict:
    """Construye un índice parcial con N páginas. No se guarda en disco."""
    from collections import Counter
    all_titles: list[str] = []
    for cat in categories:
        for title in walk_category(base_url, cat, rate_limit):
            all_titles.append(title)
            if len(all_titles) >= sample:
                break
        if len(all_titles) >= sample:
            break

    speaker_counts: Counter = Counter()
    pages_ok: list[str] = []

    for title in all_titles:
        wikitext = get_wikitext(base_url, title, rate_limit)
        if not wikitext:
            continue
        lines, fmt = parse_dialogue(wikitext, format_hint)
        if fmt != "unknown":
            for line in lines:
                if line.speaker and not line.is_action:
                    speaker_counts[line.speaker] += 1
            pages_ok.append(title)

    return {
        "base_url": base_url,
        "categories": categories,
        "pages": pages_ok,
        "speakers": dict(speaker_counts.most_common()),
        "unrecognized": [],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Comando: profiles
# ─────────────────────────────────────────────────────────────────────────────

@app.command()
def profiles() -> None:
    """Lista todos los perfiles de wiki guardados."""
    _print_header()
    _show_profiles_table()


# ─────────────────────────────────────────────────────────────────────────────
# Comando: profile-create (wizard interactivo)
# ─────────────────────────────────────────────────────────────────────────────

@app.command(name="profile-create")
def profile_create() -> None:
    """Wizard interactivo para guardar un perfil de wiki desde una URL."""
    _print_header()
    console.print(Panel("[bold]Guardar perfil de wiki[/bold]", border_style="green"))

    wiki_id = Prompt.ask("ID del perfil (sin espacios, ej: [cyan]miraculousladybug[/cyan])")
    name = Prompt.ask("Nombre legible del wiki")

    category_urls: list[str] = []
    console.print("[dim]Ingresá las URLs de categorías de transcripts (una por línea, Enter vacío para terminar).[/dim]")
    console.print("[dim]Ejemplo: https://miraculousladybug.fandom.com/wiki/Category:Transcripts[/dim]")
    while True:
        cat_url = Prompt.ask("  URL de categoría", default="")
        if not cat_url:
            break
        try:
            base_url_check, cat_name = parse_fandom_url(cat_url)
            category_urls.append(cat_name)
            if "base_url" not in locals():
                detected_base = base_url_check
        except ValueError as e:
            console.print(f"[red]{e}[/red]")

    if not category_urls:
        console.print("[red]Necesitás al menos una URL de categoría.[/red]")
        return

    base_url = Prompt.ask("URL base del wiki", default=detected_base if "detected_base" in locals() else "")
    rate_limit = float(Prompt.ask("Rate limit en segundos", default="0.5"))

    profile = {
        "name": name,
        "base_url": base_url,
        "transcript_categories": category_urls,
        "dialogue_format": "auto",
        "rate_limit_seconds": rate_limit,
        "character_aliases": {},
    }

    output_path = PROFILES_DIR / f"{wiki_id}.json"
    if output_path.exists():
        if not Confirm.ask(f"[yellow]El perfil '{wiki_id}' ya existe. ¿Sobreescribir?[/yellow]"):
            console.print("[dim]Cancelado.[/dim]")
            return

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)

    console.print(f"[green]Perfil guardado:[/green] {output_path}")


# ─────────────────────────────────────────────────────────────────────────────
# Comando: cache-clear
# ─────────────────────────────────────────────────────────────────────────────

@app.command(name="cache-clear")
def cache_clear_cmd(
    index_only: bool = typer.Option(False, "--index-only", help="Solo borrar índices, no el cache HTTP."),
) -> None:
    """Limpia el cache de páginas descargadas y/o los índices de personajes."""
    if not index_only:
        setup_cache()
        clear_cache()
        console.print("[green]Cache HTTP limpiado.[/green]")

    index_dir = Path(".cache/indexes")
    if index_dir.exists():
        count = 0
        for f in index_dir.glob("*.json"):
            f.unlink()
            count += 1
        console.print(f"[green]{count} índice(s) eliminado(s).[/green]")
    else:
        console.print("[dim]No hay índices guardados.[/dim]")


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Sin argumentos o primer arg no es un subcomando CLI → lanzar GUI
    if "--cli" not in sys.argv:
        from modules.gui.app import launch
        sys.exit(launch())
    else:
        # Remover --cli para que Typer no lo vea como argumento desconocido
        sys.argv.remove("--cli")
        app()
