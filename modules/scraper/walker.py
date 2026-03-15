"""
Walker: itera páginas de una categoría via MediaWiki API con paginación automática.
También provee utilidades para parsear URLs de Fandom.
"""
import time
from typing import Generator
from urllib.parse import urlparse, unquote

import requests
from rich.console import Console

console = Console()

HEADERS = {"User-Agent": "FandomDialogueScraper/1.0"}

# Códigos de idioma más comunes en Fandom
_LANG_CODES = [
    "es", "fr", "de", "pt-br", "it", "pl", "ru", "zh", "ja", "ko",
    "nl", "tr", "id", "pt", "sv", "fi", "hu", "cs", "ro", "uk",
]


def _root_url(base_url: str) -> str:
    """Retorna solo scheme://netloc, sin prefijo de idioma."""
    p = urlparse(base_url)
    return f"{p.scheme}://{p.netloc}"


def detect_languages(base_url: str) -> list[dict]:
    """
    Detecta los idiomas disponibles en un wiki de Fandom.

    Returns:
        Lista de dicts con: code, api_base, name, lang
        Siempre incluye el idioma principal (normalmente inglés).
    """
    root = _root_url(base_url)
    results: list[dict] = []
    main_site_base = ""

    # Wiki principal
    try:
        r = requests.get(f"{root}/api.php", params={
            "action": "query", "meta": "siteinfo", "siprop": "general", "format": "json",
        }, headers=HEADERS, timeout=10)
        g = r.json().get("query", {}).get("general", {})
        if g:
            main_site_base = g.get("base", "")
            results.append({
                "code": g.get("lang", "en"),
                "api_base": root,
                "name": g.get("sitename", root),
                "lang": g.get("lang", "en"),
            })
    except Exception:
        pass

    # Variantes de idioma
    for lang in _LANG_CODES:
        try:
            r = requests.get(f"{root}/{lang}/api.php", params={
                "action": "query", "meta": "siteinfo", "siprop": "general", "format": "json",
            }, headers=HEADERS, timeout=5)
            if r.status_code != 200:
                continue
            g = r.json().get("query", {}).get("general", {})
            lang_base = g.get("base", "")
            if g and lang_base and lang_base != main_site_base:
                results.append({
                    "code": lang,
                    "api_base": f"{root}/{lang}",
                    "name": g.get("sitename", lang),
                    "lang": g.get("lang", lang),
                })
        except Exception:
            continue

    return results


def detect_transcript_categories(api_base: str) -> list[dict]:
    """
    Detecta categorías de transcripts en un wiki buscando prefijo 'Trans'.

    Returns:
        Lista de dicts con: title (con namespace), name, pages
    """
    api_url = f"{api_base}/api.php"

    # Obtener nombre localizado del namespace Category (ID 14)
    cat_namespace = "Category"
    try:
        r = requests.get(api_url, params={
            "action": "query", "meta": "siteinfo", "siprop": "namespaces", "format": "json",
        }, headers=HEADERS, timeout=10)
        ns = r.json().get("query", {}).get("namespaces", {})
        cat_namespace = ns.get("14", {}).get("*", "Category")
    except Exception:
        pass

    results: list[dict] = []
    try:
        r = requests.get(api_url, params={
            "action": "query", "list": "allcategories",
            "acprefix": "Trans", "aclimit": "30", "format": "json",
        }, headers=HEADERS, timeout=10)
        cats = r.json().get("query", {}).get("allcategories", [])

        for cat in cats:
            name = cat["*"]
            full_title = f"{cat_namespace}:{name}"
            # Obtener conteo de páginas
            pages = 0
            try:
                cr = requests.get(api_url, params={
                    "action": "query", "titles": full_title,
                    "prop": "categoryinfo", "format": "json",
                }, headers=HEADERS, timeout=5)
                for p in cr.json().get("query", {}).get("pages", {}).values():
                    pages = p.get("categoryinfo", {}).get("pages", 0)
            except Exception:
                pass
            results.append({"title": full_title, "name": name, "pages": pages})
    except Exception:
        pass

    return results


def parse_fandom_url(url: str) -> tuple[str, str]:
    """
    Parsea una URL de Fandom del navegador y extrae base_url y nombre de categoría.

    Ejemplos:
        "https://miraculousladybug.fandom.com/wiki/Category:Transcripts"
        → ("https://miraculousladybug.fandom.com", "Category:Transcripts")

        "https://mlp.fandom.com/wiki/Category:Season_1_transcripts"
        → ("https://mlp.fandom.com", "Category:Season 1 transcripts")

    Args:
        url: URL completa copiada desde el navegador.

    Returns:
        Tupla (base_url, category_name).

    Raises:
        ValueError: Si la URL no tiene el formato esperado de Fandom.
    """
    parsed = urlparse(url)

    if not parsed.netloc or "fandom.com" not in parsed.netloc:
        raise ValueError(
            f"URL no reconocida como wiki de Fandom: '{url}'\n"
            "Formato esperado: https://[wiki].fandom.com/wiki/Category:[Nombre]"
        )

    path = parsed.path

    # Soporta /wiki/ y /es/wiki/ (wikis con prefijo de idioma)
    if "/wiki/" not in path:
        raise ValueError(
            f"No se pudo extraer la categoría de la URL: '{url}'\n"
            "El path debe contener /wiki/Category:[Nombre]"
        )

    # Extraer prefijo de idioma si existe (ej: /es/, /pt-br/, etc.)
    lang_prefix, wiki_part = path.split("/wiki/", 1)
    # lang_prefix es "" para /wiki/... o "/es" para /es/wiki/...
    base_url = f"{parsed.scheme}://{parsed.netloc}{lang_prefix}"
    category = unquote(wiki_part)

    # Reemplazar guiones bajos por espacios (convención de MediaWiki)
    category = category.replace("_", " ")

    return base_url, category


def walk_category(
    base_url: str,
    category: str,
    rate_limit: float = 0.5,
) -> Generator[str, None, None]:
    """
    Itera todos los títulos de páginas en una categoría, manejando paginación.

    Args:
        base_url:   URL base del wiki.
        category:   Nombre de la categoría incluyendo prefijo (ej: "Category:Transcripts").
        rate_limit: Segundos entre requests a la API.

    Yields:
        Títulos de página (str).
    """
    api_url = f"{base_url}/api.php"
    params: dict = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": category,
        "cmtype": "page",
        "cmlimit": "500",
        "format": "json",
    }

    while True:
        try:
            response = requests.get(api_url, params=params, headers=HEADERS, timeout=15)
            response.raise_for_status()
            data = response.json()

            members = data.get("query", {}).get("categorymembers", [])
            for member in members:
                yield member["title"]

            # Paginación: cmcontinue indica que hay más resultados
            if "continue" in data:
                params["cmcontinue"] = data["continue"]["cmcontinue"]
                time.sleep(rate_limit)
            else:
                break

        except requests.RequestException as e:
            console.log(f"[red]Error al recorrer categoría '{category}': {e}[/red]")
            break


def count_category(base_url: str, category: str) -> int:
    """
    Cuenta el total de páginas en una categoría sin descargar su contenido.
    Útil para inicializar progress bars.
    """
    api_url = f"{base_url}/api.php"
    params = {
        "action": "query",
        "titles": category,
        "prop": "categoryinfo",
        "format": "json",
    }

    try:
        response = requests.get(api_url, params=params, headers=HEADERS, timeout=15)
        response.raise_for_status()
        data = response.json()
        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            return page.get("categoryinfo", {}).get("pages", 0)
    except requests.RequestException as e:
        console.log(f"[yellow]No se pudo contar categoría '{category}': {e}[/yellow]")

    return 0
