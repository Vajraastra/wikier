# TASKS — Wikier

## Estado actual: Pipeline completo — GUI con 5 temas — Próxima sesión: documentación

---

## ✅ COMPLETADAS

### Fase 1 — Core Scraper
- [x] Estructura de directorios, `requirements.txt`, `run.sh`
- [x] Perfiles JSON: `miraculousladybug.json`, `gravityfalls.json`, `mlp.json`
- [x] `scraper/fetcher.py` — Wikitext Fetcher con cache en disco
- [x] `scraper/walker.py` — Category Walker con paginación
- [x] `scraper/parser.py` — Parser dual (bold-colon + template) con auto-detección
- [x] `scraper/filter.py` — Character Filter con ventana de contexto y aliases
- [x] `scraper/exporter.py` — Exportación a JSONL, CSV, TXT
- [x] `main.py` — CLI con flag `--cli`; GUI por defecto
- [x] `tests/test_parser.py` — 30 tests unitarios del parser

### Fase 2 — Validación con Miraculous Ladybug
- [x] Categoría y formato de diálogo verificados en el wiki real
- [x] Pipeline scraper funcional contra el wiki real

### Fase 3 — Robustez del parser
- [x] Parlamentos multi-párrafo (máquina de estado con `pending_speaker`/`pending_parts`)
- [x] Tests con wikitext realista de Miraculous Ladybug (6 nuevos tests)
- [x] Anotaciones de narrador `''texto''` no se fusionan al diálogo

### Fase 4 — Refactoring del Scraper
- [x] `scraper/lang_filter.py` — detección de idioma via langdetect
- [x] `scraper/config.py` — paths absolutos centralizados
- [x] Perfil JSON extendido: `language`, `personality`, `system_prompt_fields`
- [x] `exporter.py` — produce 6 listas categorizadas del curator
- [x] GUI base PySide6: AppWindow + QStackedWidget + Dashboard

### Fase 5 — Módulo Curator
- [x] `classifier.py`, `cleaner.py`, `quality_scorer.py`, `deduplicator.py`
- [x] `system_prompt_builder.py`, `formatter.py`, `stats.py`
- [x] `curator.py` — orquestador con callbacks de progreso
- [x] `token_analyzer.py` — presets tiny/small/medium/large, proxy + transformers
- [x] `context_builder.py`, `prefix_injector.py` — marcados opcionales/pendientes

### Fase 5b — GUI Curator
- [x] `CuratorWidget` + `CuratorPanel` + `CuratorWorker` (QThread)
- [x] Auto-detección de personaje, formatos JSONL/CSV/TXT, system prompt con ratio
- [x] Token Analyzer: checkbox, preset combo, campo tokenizer avanzado

### Fase 7 — Módulo Joiner
- [x] `joiner.py`: `merge`, `shuffle`, `split`, `export`, `load_file`, `detect_format`, `convert_file`
- [x] `JoinerPanel` + `JoinerWorker` — modos pipeline y convert
- [x] Conversor de formatos standalone (JSONL/CSV/TXT ↔ chatml/alpaca/sharegpt/jsonl_raw)

### Fase 8 (parcial) — GUI PySide6
- [x] Dashboard con tarjetas de módulos y lazy loading
- [x] Sistema de temas QSS con auto-detección (`themes/`)
- [x] Sistema de i18n con auto-detección (`locales/`)
- [x] Panel de scraping + tabla de personajes con sorting y filtrado
- [x] Panel de Ajustes: idioma y tema en su propia sección (`settings_panel.py`)
- [x] 5 temas: Oscuro (Catppuccin Mocha), Claro (Catppuccin Latte), Cyberpunk 2077, Nord, Dracula
- [x] Visual candies: gradientes en botones y progress bars, hover con border accent en tarjetas

### Fase 9b — Editor de Dataset
- [x] Vista dual: tabla + editor con QSplitter ajustable
- [x] Navegación con tabla + botones, lock 🔒, filtro de incompletos
- [x] Búsqueda Ctrl+F + reemplazo individual y masivo
- [x] Eliminación no destructiva, guardado incremental Ctrl+S
- [x] Soporte JSONL (ChatML/Alpaca/ShareGPT/raw), CSV, TXT

### Fase 10 — Name Tagger
- [x] `spacy_manager.py` — gestor de modelos spaCy (22 idiomas)
- [x] `name_tagger.py` — etiquetado con heurísticas + dependency parsing
- [x] `discovery.py` — `export_character_roster()`
- [x] GUI: panel de idiomas, sección en CuratorPanel

---

## 🔜 PRÓXIMA SESIÓN — Documentación y guías de usuario

### Código — Docstrings y comentarios
- [ ] Docstrings completos en módulos core: `curator.py`, `joiner.py`, `token_analyzer.py`
- [ ] Comentarios explicativos en la máquina de estado del parser (`parser.py`)
- [ ] Docstrings en la API pública del curator (`CuratorConfig`, `curate()`)
- [ ] Comentarios en el pipeline de pasos de `curator.py` (qué hace cada paso)
- [ ] Docstrings en `name_tagger.py` (lógica de clasificación vocativo vs referencia)
- [ ] Docstrings en `editor_panel.py` (lógica de sincronización tabla ↔ editor)

### Documentación de usuario
- [ ] `README.md` — descripción del proyecto, instalación, uso rápido
- [ ] `docs/guia_scraper.md` — flujo completo del Scraper con capturas/ejemplos
- [ ] `docs/guia_curator.md` — pipeline de curación paso a paso
- [ ] `docs/guia_joiner.md` — merge, split y conversión de formatos
- [ ] `docs/guia_editor.md` — uso del editor: filtros, lock, búsqueda
- [ ] `docs/guia_perfiles.md` — formato del perfil JSON, campos disponibles
- [ ] `docs/guia_temas.md` — cómo crear un tema QSS personalizado

---

## 📋 PLANES FUTUROS

### Fase 6 — Wizard de Configuración
*4 pasos guiados. El usuario nunca ve flags técnicos.*
- Paso 1: Formato de salida (ChatML / Alpaca / ShareGPT / JSONL crudo)
- Paso 2: Objetivo (diálogo / roleplay / ambos)
- Paso 3: Calidad mínima
- Paso 4: División train/val/test (default: 80/10/10)
- Guardar config como `curator_config.json` reutilizable

### Fase 8 (resto) — GUI PySide6
- Preview de dataset curado (`QTableView` con modelo virtual)
- Dashboard de stats con Qt Charts (distribución de tokens, líneas por personaje)
- File browser para outputs (`QTreeView`)
- Editor de system prompt con preview en tiempo real

### Fase 9 — Tests
- Tests unitarios del curator (classifier, cleaner)
- Tests de integración: scrape → curate → format → join
- Tests del token_analyzer con diferentes presets
- Tests del joiner (merge, split, export)

### Opcionales / Análisis pendiente
- `curator/context_builder.py` — ventana de N turnos previos configurable
- `curator/prefix_injector.py` — prefijos `[responding to X]`, `[initiating]`
- Versión web en HF Spaces (módulo Gradio separado, sin tocar el core)
- CLI mejorado con Rich TUI para usuarios avanzados
