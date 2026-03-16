"""
Token Analyzer: filtra entradas del dataset que exceden el límite de tokens
del modelo objetivo.

Las entradas dentro del límite pasan al output normal.
Las que exceden se archivan en overlength.jsonl (recuperables).

El conteo usa el tokenizer real si está disponible (tiktoken / transformers),
o un proxy de caracteres como fallback conservador (~4 chars/token).

Uso:
    filtered, overlength, report = filter_sets(sets, preset="small")
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Presets de modelos con límites de tokens para fine-tuning.
# El rango de parámetros indica qué tamaño de modelo corresponde a cada preset.
PRESETS: dict[str, dict] = {
    "tiny":   {"limit": 1024,  "size": "1B–3B",   "models": "Phi-3 mini 3.8B, Gemma 2B, Qwen 1.5B"},
    "small":  {"limit": 2048,  "size": "7B–9B",   "models": "LLaMA 3 8B, Mistral 7B, Gemma 7B"},
    "medium": {"limit": 4096,  "size": "13B–30B",  "models": "Qwen 14B, Phi-3 medium 14B, Mistral Nemo 12B"},
    "large":  {"limit": 8192,  "size": "70B+",    "models": "LLaMA 3 70B, Qwen 72B, Mistral 8x22B"},
}

# Chars por token — proxy conservador (válido para inglés y español)
_CHARS_PER_TOKEN = 4


# ─────────────────────────────────────────────────────────────────────────────
# Tokenizer
# ─────────────────────────────────────────────────────────────────────────────

def _load_tokenizer(name: str):
    """
    Intenta cargar un tokenizer por nombre.
    Prueba tiktoken primero (ligero), luego transformers (universal).
    Retorna None si ninguno está disponible.

    Args:
        name: Encoding de tiktoken ("cl100k_base") o nombre de modelo
              HuggingFace ("meta-llama/Llama-2-7b-hf").
    """
    # tiktoken — OpenAI, ligero (~1 MB), soporta GPT-3.5/4
    try:
        import tiktoken
        try:
            return tiktoken.get_encoding(name)
        except KeyError:
            return tiktoken.encoding_for_model(name)
    except (ImportError, Exception):
        pass

    # transformers — HuggingFace, universal pero pesado
    try:
        from transformers import AutoTokenizer
        return AutoTokenizer.from_pretrained(name, use_fast=True)
    except (ImportError, Exception):
        pass

    logger.warning(
        "No se pudo cargar el tokenizer '%s'. "
        "Instala tiktoken o transformers para conteo exacto. "
        "Usando proxy de caracteres.",
        name,
    )
    return None


def _make_counter(tokenizer_name: Optional[str]):
    """
    Retorna una función count(text: str) -> int.

    Si tokenizer_name está disponible y el tokenizer se carga correctamente,
    usa .encode() para conteo exacto. En caso contrario, usa proxy de chars.
    """
    if tokenizer_name:
        tokenizer = _load_tokenizer(tokenizer_name)
        if tokenizer is not None and hasattr(tokenizer, "encode"):
            def count(text: str) -> int:
                try:
                    return len(tokenizer.encode(text))
                except Exception:
                    return max(1, len(text) // _CHARS_PER_TOKEN)
            return count

    def count(text: str) -> int:
        return max(1, len(text) // _CHARS_PER_TOKEN)

    return count


# ─────────────────────────────────────────────────────────────────────────────
# Distribución
# ─────────────────────────────────────────────────────────────────────────────

def _percentile(sorted_values: list[int], p: float) -> int:
    """Percentil p (0–100) de una lista ya ordenada ascendentemente."""
    if not sorted_values:
        return 0
    idx = int(len(sorted_values) * p / 100)
    return sorted_values[min(idx, len(sorted_values) - 1)]


def _compute_distribution(all_counts: list[int]) -> dict:
    """Calcula estadísticos de distribución a partir de todos los conteos."""
    if not all_counts:
        return {"p50": 0, "p90": 0, "p95": 0, "max": 0, "total": 0}
    s = sorted(all_counts)
    return {
        "p50":   _percentile(s, 50),
        "p90":   _percentile(s, 90),
        "p95":   _percentile(s, 95),
        "max":   s[-1],
        "total": len(s),
    }


def _format_report(
    dist: dict,
    preset: str,
    limit: int,
    overlength_count: int,
    tokenizer_name: Optional[str],
) -> str:
    """Genera el reporte de distribución de tokens en formato legible."""
    using_proxy = tokenizer_name is None
    source = (
        f"proxy (~{_CHARS_PER_TOKEN} chars/token)"
        if using_proxy
        else tokenizer_name
    )

    # max_seq_length recomendado: p95 redondeado al próximo múltiplo de 256, mínimo 512
    raw = dist["p95"]
    rec = max(512, ((raw + 255) // 256) * 256)

    p = PRESETS[preset]
    lines = [
        f"── Token Analyzer ({'proxy' if using_proxy else 'tokenizer real'}: {source})",
        f"   Preset         : {preset}  ({p['size']} — {p['models']}, límite: {limit:,} tokens)",
        f"   p50 (mediana)  : {dist['p50']:>7,} tokens",
        f"   p90            : {dist['p90']:>7,} tokens",
        f"   p95            : {dist['p95']:>7,} tokens",
        f"   Máximo         : {dist['max']:>7,} tokens",
        f"   Overlength     : {overlength_count:>7,} entradas archivadas",
        f"   max_seq_length recomendado: {rec:,}",
    ]
    if using_proxy:
        lines.append(
            "   ℹ  Conteo por proxy (~4 chars/token). Suficiente para fine-tuning local."
            " Para conteo exacto: pip install transformers"
        )
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# API pública
# ─────────────────────────────────────────────────────────────────────────────

def filter_sets(
    sets: dict[str, list[dict]],
    preset: str = "small",
    tokenizer_name: Optional[str] = None,
) -> tuple[dict[str, list[dict]], dict[str, list[dict]], str]:
    """
    Filtra entradas que exceden el límite de tokens del preset.

    Cuenta tokens del campo 'clean' (respuesta del personaje). Si 'clean' no
    existe, usa 'output' como fallback.

    Args:
        sets:           Dict {categoría: [entradas]} del pipeline curator.
        preset:         Preset de modelo: "tiny", "small", "medium", "large".
        tokenizer_name: Nombre del tokenizer (tiktoken encoding o modelo HF).
                        None → proxy de caracteres.

    Returns:
        Tupla de tres elementos:
          - filtered_sets:    entradas dentro del límite, misma estructura de sets.
          - overlength_sets:  entradas que exceden, misma estructura de sets.
          - distribution_report: reporte de distribución en texto legible.
    """
    if preset not in PRESETS:
        logger.warning("Preset '%s' no reconocido. Usando 'small'.", preset)
        preset = "small"

    limit  = PRESETS[preset]["limit"]
    count  = _make_counter(tokenizer_name)

    filtered:   dict[str, list[dict]] = {}
    overlength: dict[str, list[dict]] = {}
    all_counts: list[int] = []
    overlength_total = 0

    for cat, entries in sets.items():
        ok: list[dict]   = []
        over: list[dict] = []

        for entry in entries:
            text = entry.get("clean") or entry.get("output", "")
            n = count(text)
            all_counts.append(n)

            if n <= limit:
                ok.append(entry)
            else:
                over.append(entry)
                overlength_total += 1

        filtered[cat] = ok
        if over:
            overlength[cat] = over

    dist   = _compute_distribution(all_counts)
    report = _format_report(dist, preset, limit, overlength_total, tokenizer_name)

    return filtered, overlength, report
