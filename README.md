# Wikier

Herramienta modular para extraer diálogos de wikis Fandom y convertirlos en datasets listos para fine-tuning de LLMs.

## ¿Qué hace?

1. **Scraper** — recorre las páginas de transcripciones de un wiki, extrae los diálogos de un personaje y los exporta en JSONL, CSV o TXT.
2. **Curator** — limpia, clasifica, filtra y formatea el dataset en los formatos estándar de entrenamiento (ChatML, Alpaca, ShareGPT).
3. **Joiner** — combina sets del curator, mezcla con seed reproducible, divide en train/validation/test y convierte entre formatos.
4. **Editor** — revisor manual entrada por entrada, con búsqueda, reemplazo masivo y guardado incremental.

El resultado es un dataset listo para pasar directamente a tu trainer local (LLaMA-Factory, Axolotl, Unsloth, etc.).

---

## Instalación

```bash
git clone https://github.com/tu-usuario/wikier.git
cd wikier
./run.sh
```

`run.sh` gestiona todo automáticamente:
- Verifica e instala Python 3.13 via `uv`
- Crea el entorno virtual del proyecto
- Instala todas las dependencias de `requirements.txt`
- Lanza la GUI

> **Requisito:** tener [`uv`](https://github.com/astral-sh/uv) instalado.
> Instalación rápida: `curl -LsSf https://astral.sh/uv/install.sh | sh`

---

## Inicio rápido

### GUI (por defecto)
```bash
./run.sh
```

### CLI
```bash
./run.sh --cli --help
```

---

## Módulos

| Módulo | Descripción | Guía |
|--------|-------------|------|
| Scraper | Extrae diálogos de wikis Fandom | [guia_scraper.md](docs/guia_scraper.md) |
| Curator | Limpia y formatea el dataset | [guia_curator.md](docs/guia_curator.md) |
| Joiner | Combina, mezcla y divide en splits | [guia_joiner.md](docs/guia_joiner.md) |
| Editor | Revisión manual de entradas | [guia_editor.md](docs/guia_editor.md) |

---

## Flujo de trabajo típico

```
Wiki Fandom
    ↓  [Scraper]
output/{Personaje}/{Personaje}_dataset.jsonl
    ↓  [Curator]
output/{Personaje}/curated/dialogue_clean.jsonl
                           dialogue_mixed_*.jsonl
    ↓  [Joiner]
output/joined/Personaje_train.jsonl
              Personaje_validation.jsonl
              Personaje_test.jsonl
    ↓  [Editor]   ← opcional: revisión manual
    ↓
Fine-tuning con tu trainer preferido
```

---

## Documentación adicional

- [Perfiles JSON](docs/guia_perfiles.md) — cómo configurar un nuevo wiki
- [Temas QSS](docs/guia_temas.md) — cómo crear o modificar temas visuales

---

## Estructura del proyecto

```
wikier/
├── run.sh                  # Lanzador principal
├── main.py                 # Entry point (GUI por defecto, --cli para terminal)
├── requirements.txt
├── profiles/               # Perfiles JSON de wikis
│   ├── miraculousladybug.json
│   ├── gravityfalls.json
│   └── mlp.json
├── output/                 # Datasets generados (gitignored)
├── themes/                 # Temas QSS (default, light, cyberpunk, nord, dracula)
├── locales/                # Traducciones (es.json, en.json)
├── modules/
│   ├── core/               # Settings, i18n, temas, spaCy manager
│   ├── scraper/            # Scraping de wikis
│   ├── curator/            # Pipeline de curación
│   └── gui/                # Interfaz gráfica PySide6
├── tests/                  # Tests del parser
├── docs/                   # Guías de usuario
├── TASKS.md                # Lista de tareas del proyecto
└── BITACORA.md             # Log de desarrollo
```

---

## Dependencias principales

- **PySide6** — interfaz gráfica
- **mwparserfromhell** — parser de wikitext de MediaWiki
- **requests + requests-cache** — scraping con cache en disco
- **langdetect** — filtro de idioma opcional
- **spaCy** — name tagger (opcional, descarga modelos bajo demanda)
