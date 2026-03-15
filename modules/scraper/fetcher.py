"""
Fetcher: obtiene wikitext crudo desde la MediaWiki API de Fandom.
Incluye cache en disco para no re-descargar durante desarrollo.
"""
import time
import requests
import requests_cache
from rich.console import Console

from modules.scraper.config import CACHE_DIR

console = Console()

HEADERS = {"User-Agent": "FandomDialogueScraper/1.0"}


def setup_cache(cache_path: str | None = None) -> None:
    """Inicializa cache SQLite transparente sobre requests."""
    if cache_path is None:
        cache_path = str(CACHE_DIR / "fandom-scraper")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    requests_cache.install_cache(
        cache_path,
        backend="sqlite",
        expire_after=86400,  # 24 horas
    )
    console.log(f"[dim]Cache activado en[/dim] {cache_path}.sqlite")


def clear_cache() -> None:
    """Invalida todo el cache en disco."""
    requests_cache.clear()
    console.log("[yellow]Cache limpiado.[/yellow]")


def get_wikitext(base_url: str, title: str, rate_limit: float = 0.5) -> str | None:
    """
    Obtiene el wikitext crudo de una página via MediaWiki API.

    Args:
        base_url: URL base del wiki (ej: https://miraculousladybug.fandom.com)
        title:    Título de la página a obtener.
        rate_limit: Segundos de espera entre requests (no aplica si viene de cache).

    Returns:
        String con el wikitext, o None si hay error.
    """
    api_url = f"{base_url}/api.php"
    params = {
        "action": "parse",
        "page": title,
        "prop": "wikitext",
        "format": "json",
        "formatversion": "2",
    }

    try:
        response = requests.get(api_url, params=params, headers=HEADERS, timeout=15)
        response.raise_for_status()
        data = response.json()

        if "error" in data:
            console.log(f"[yellow]API error para '{title}': {data['error']['info']}[/yellow]")
            return None

        wikitext = data.get("parse", {}).get("wikitext", "")

        # Solo esperar si el response no vino de cache
        from_cache = getattr(response, "from_cache", False)
        if not from_cache:
            time.sleep(rate_limit)

        return wikitext

    except requests.RequestException as e:
        console.log(f"[red]Error fetching '{title}': {e}[/red]")
        return None
