# Wikier

Modular toolkit for extracting dialogue from Fandom wikis and converting it into datasets ready for LLM fine-tuning. Also scrapes free-form text from web sources (AO3, FanFiction.net, Wattpad, Literotica, and generic sites).

The output is a clean, formatted dataset you can feed directly to your local trainer (LLaMA-Factory, Axolotl, Unsloth, etc.).

---

## Modules

| Module | What it does |
|---|---|
| **Scraper** | Crawls a Fandom wiki's transcript pages, extracts a character's dialogue, and exports to JSONL, CSV, or TXT. |
| **Curator** | Cleans, classifies, filters, and formats the dataset into standard training formats (ChatML, Alpaca, ShareGPT). |
| **Joiner** | Merges multiple curated sets, shuffles with a reproducible seed, splits into train/validation/test, and converts between formats. |
| **Editor** | Manual entry-by-entry reviewer with search, bulk replace, soft delete, and incremental save. |
| **Story Scraper** | Downloads free-form text from any web source. Supports automatic URL-list resolution from tag/search pages, auto-pagination, retry queue for timeouts, and per-site profiles. |

---

## Typical workflow

```
Fandom Wiki                      Web sources (AO3, Literotica, etc.)
    ↓  [Scraper]                      ↓  [Story Scraper]
output/{Character}/              output/stories/*.txt
  {Character}_dataset.jsonl
    ↓  [Curator]
output/{Character}/curated/dialogue_clean.jsonl
    ↓  [Joiner]
output/joined/Character_train.jsonl
              Character_validation.jsonl
              Character_test.jsonl
    ↓  [Editor]   ← optional manual review
    ↓
Fine-tune with your trainer
```

---

## Installation

```bash
git clone https://github.com/Vajraastra/wikier.git
cd wikier
./run.sh
```

`run.sh` handles everything automatically:
- Verifies and installs Python 3.13 via `uv`
- Creates the project virtual environment
- Installs all `requirements.txt` dependencies
- Launches the GUI

> **Requirement:** [`uv`](https://github.com/astral-sh/uv) must be installed.
> Quick install: `curl -LsSf https://astral.sh/uv/install.sh | sh`

---

## Usage

```bash
./run.sh          # Launch GUI (default)
./run.sh --cli --help   # CLI mode
```

---

## Supported training formats

- **ChatML** — standard multi-turn format (`<|im_start|>`, `<|im_end|>`)
- **Alpaca** — instruction/input/output triplets
- **ShareGPT** — conversation array format
- **JSONL raw** — unformatted, for custom processing

---

## Key features

- **Wiki profiles** — JSON config per wiki (category paths, character aliases, system prompt fields, language)
- **5 visual themes** — Dark (Catppuccin Mocha), Light (Catppuccin Latte), Cyberpunk 2077, Nord, Dracula
- **i18n** — Spanish and English UI
- **Token analyzer** — proxy-based by default (no deps); optional exact counting via `transformers` for LLaMA/Mistral/Qwen
- **Name tagger** — spaCy-powered character name detection across 22 languages (optional, downloaded on demand)
- **Story Scraper profiles** — built-in support for AO3, FanFiction.net, Wattpad, and Literotica; heuristic fallback for generic sites

---

## Project structure

```
wikier/
├── run.sh
├── main.py
├── requirements.txt
├── profiles/          # Wiki JSON profiles (miraculousladybug, gravityfalls, mlp…)
├── output/            # Generated datasets (gitignored)
├── themes/            # QSS themes
├── locales/           # UI translations (es.json, en.json)
├── modules/
│   ├── core/          # Settings, i18n, themes, spaCy manager
│   ├── scraper/       # Fandom wiki scraping
│   ├── story_scraper/ # Free-form web text scraping
│   ├── curator/       # Curation pipeline
│   └── gui/           # PySide6 interface
├── tests/
└── docs/              # User guides per module
```

---

## License

Business Source License 1.1 — free for non-commercial use.  
Commercial use requires a separate license. See [LICENSE](LICENSE) for details.  
Converts to MIT on 2030-04-18.
