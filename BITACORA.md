# BITACORA — Wikier

---

## 2026-03-16 — Settings, temas y visual candies

### Panel de Ajustes (Settings)

**Problema:** Los selectores de idioma y tema estaban en el footer del dashboard — poco visible, sin contexto, poco escalable.

**Solución:** Módulo independiente `SettingsPanel` accesible desde el botón "⚙ Ajustes" del footer del dashboard.

**Archivos creados/modificados:**
- `modules/gui/panels/settings_panel.py` (nuevo) — panel con QGroupBox "Apariencia", combos de idioma y tema, aviso inline de reinicio para idioma
- `modules/gui/dashboard.py` — footer simplificado: versión + botón ⚙
- `modules/gui/app_window.py` — factory case `"settings"`
- `locales/es.json`, `locales/en.json` — keys `settings.*`

**Patrón aplicado:** mismo patrón de widget embebible que ScraperWidget/CuratorWidget — back button + signal `back_requested` + navegación por QStackedWidget.

### QoS de temas + 3 temas nuevos

**Mejoras en temas existentes (default + light):**
- Botón primary con `qlineargradient` top→bottom (más profundidad visual)
- Progress bar chunk con gradiente left→right (acento1 → acento2)
- Module cards con gradiente de fondo sutil
- Card hover: `border-left: 3px solid <accent>` — indicador visual claro
- `border-radius: 12px` en cards (más amable, menos corporativo)

**Nuevos estilos en ambos temas:**
- `QSplitter::handle` — visible en hover
- `QTabWidget / QTabBar` — cobertura completa para paneles con pestañas
- `#editor-toolbar`, `#editor-footer`, `#search-bar` — barras del editor
- `#settings-*` — panel de ajustes
- `QLabel#help-text` — textos descriptivos secundarios
- `QToolTip` — tooltips con colores del tema

**Temas nuevos creados:**

| Archivo | Nombre | Personalidad |
|---------|--------|--------------|
| `themes/cyberpunk.qss` | Cyberpunk 2077 | Oscuro extremo, neon amarillo + cyan, angular (border-radius: 3px), letter-spacing, scrollbars neon, status bar con borde amarillo |
| `themes/nord.qss` | Nord | Polar Night palette, frío y limpio, muy redondeado (6-8px), Frost blue como acento |
| `themes/dracula.qss` | Dracula | Púrpura + rosa, progress bar purple→pink, fondos casi negros |

**Auto-detección de temas:** el sistema lee `/* display: Name */` al inicio de cada `.qss` — agregar un tema nuevo es soltar el archivo en `themes/`, sin tocar código.

---

## 2026-03-16 — Fase 7: Joiner + Editor de Dataset (Fase 9b)

### Fase 7 — `curator/joiner.py` + GUI completa

**Archivos creados/modificados:**
- `modules/curator/joiner.py` (nuevo)
- `modules/gui/panels/joiner_panel.py` (nuevo)
- `modules/gui/workers/joiner_worker.py` (nuevo)
- `modules/gui/joiner_window.py` (nuevo)
- `modules/gui/dashboard.py` — tarjeta "joiner" añadida
- `modules/gui/app_window.py` — factory `JoinerWidget` añadida
- `locales/es.json`, `locales/en.json` — keys `module.joiner.*`

**Diseño del módulo:**
- `merge(sets, objective, max_entries)` — combina sets con pesos por objetivo (dialogue/roleplay/both)
- `shuffle(entries, seed)` — seed fija para reproducibilidad
- `split(entries, train, val, test)` — ratios con normalización automática (suman a 1.0)
- `export(train, val, test, output_dir, prefix, fmt)` — escribe train/validation/test.jsonl
- `load_file(path)` — carga JSONL/CSV/TXT con auto-detección de formato
- `detect_format(entry)` — detecta chatml/alpaca/sharegpt/jsonl_raw desde estructura
- `convert_file(input, output, target_fmt)` — conversor standalone entre todos los formatos

**GUI (JoinerPanel):**
- Carga de carpeta `curated/` con auto-detección de categorías disponibles
- Selector de objetivo + split configurable + seed + límite opcional
- Sección conversor de formatos independiente del pipeline principal
- `JoinerWorker` (QThread) modos "pipeline" y "convert"

### Fase 9b — Editor de Dataset

**Archivos creados/modificados:**
- `modules/gui/panels/editor_panel.py` (nuevo — ~430 líneas)
- `modules/gui/editor_window.py` (nuevo)
- `modules/gui/dashboard.py` — tarjeta "editor" añadida
- `modules/gui/app_window.py` — factory `EditorWidget` añadida
- `locales/es.json`, `locales/en.json` — keys `module.editor.*`

**Diseño del panel:**
- Vista dual: `QSplitter` vertical entre tabla de resumen y editor de detalle
- Tabla: columnas `# | Instruction | Output | Estado` con colores por estado
- Campos con lock 🔒 (System, Instruction): al presionar Siguiente, el valor bloqueado se copia a la siguiente entrada
- Filtro "Solo incompletos": muestra solo entradas con `[COMPLETAR]`
- Búsqueda Ctrl+F con barra plegable: busca en todos los campos, ↑↓ navega resultados
- Reemplazo "Esta" (entrada actual) y "Todas" (masivo en todas las coincidencias)
- Eliminación no destructiva: marcado con `✗`, restaurable
- Guardado incremental en memoria; Ctrl+S / botón escribe al disco en formato fuente original
- Normalización interna a `{system, instruction, clean}` — convierte de/a cualquier formato al cargar/guardar

**Formatos soportados:** JSONL (ChatML, Alpaca, ShareGPT, raw), CSV, TXT

### Bugs encontrados y resueltos en esta sesión

**`AttributeError: 'QHeaderView' object has no attribute 'Stretch'`**
- Causa: se accedía al enum `Stretch` desde una instancia de `QHeaderView` en lugar de desde la clase.
- Fix: importar `QHeaderView` en el encabezado del módulo y usar `QHeaderView.Stretch` directamente.

**Bajo contraste tabla en tema oscuro**
- Causa: los colores de fondo originales eran variantes claras (amarillo `#FFF8D2`, gris `#D2D2D2`). El texto del tema oscuro es claro, generando contraste nulo.
- Fix: cambiar fondos a variantes oscuras (`#46 3C 14` para incompleto, `#50 50 50` para eliminado) y forzar el foreground de las celdas afectadas a un tono crema claro `#F0E6BE`. La columna Estado conserva sus propios colores de texto.

### Limpieza de archivos basura

Eliminados `=0.7` y `=3.7` del root del proyecto. Origen: `pip install paquete>=X.Y` sin comillas — el shell interpretó `>` como redirección y creó los archivos. Solución permanente: siempre usar comillas `pip install "paquete>=X.Y"`.

---

---

## 2026-03-15 — Fase 3: Robustez del parser

### Cambios implementados

**`modules/scraper/parser.py` — `_parse_bold_colon` refactorizado:**

El parser anterior manejaba continuaciones de forma incompleta: solo capturaba UNA línea de continuación, y únicamente cuando la línea de speaker no tenía texto inicial. Cualquier texto adicional de un parlamento multi-párrafo se perdía silenciosamente.

Nuevo algoritmo: máquina de estado con `pending_speaker`/`pending_parts`. Acumula líneas de continuación hasta que aparece:
- Una nueva línea de speaker `'''Name:'''`
- Una action line `''acción''` (línea completa en cursiva)
- Una línea en blanco (fin de párrafo)
- Marcado estructural: `=` (headers), `{` (templates), `|` (tablas), `!` (cabeceras tabla), `''` (anotaciones de narrador), `[` (links/archivos)

Al cierre del wikitext se llama `_flush()` para no perder el último parlamento.

**`tests/test_parser.py` — 12 nuevos tests (30 total):**
- `TestMultiParagraph` (6 tests): continuación con texto inicial, sin texto inicial, interrupción por línea en blanco, interrupción por action line, anotación de narrador no fusionada, sin contaminación entre speakers.
- `TestRealWorldWikitext` (6 tests): wikitext realista con headers de sección, action lines, multi-párrafo, speakers correctos.

### Verificado
- 30/30 tests pasan.
- Todos los tests anteriores (formato, parseo, auto-detección) siguen en verde.
- Anotaciones de narrador en cursiva (`''texto'' más texto`) no se fusionan al diálogo.
- Headers `==Sección==` no contaminan speakers ni texto.

### Nota sobre `unrecognized_pages.log`
No existe tal archivo. Las páginas con formato no reconocido se almacenan en el campo `"unrecognized"` del índice JSON generado por `discovery.build_index()`. Si se quiere listarlas, leer ese archivo de índice.



---

## 2026-03-15 — Fase 5: token_analyzer.py implementado

### Archivos creados/modificados
- `modules/curator/token_analyzer.py` (nuevo)
- `modules/curator/curator.py` — paso 5 actualizado para capturar el reporte de distribución
- `modules/gui/panels/curator_panel.py` — sección "Análisis de tokens" añadida

### Diseño
`filter_sets(sets, preset, tokenizer_name)` → `(filtered, overlength, report)`

**Conteo de tokens:**
- Si `tokenizer_name` está vacío → proxy de caracteres (`len(text) // 4`). Cero dependencias extra.
- Si `tokenizer_name` tiene valor → intenta `tiktoken` (ligero), luego `transformers` (universal). Fallback silencioso a proxy si ninguno está instalado.
- Solo cuenta el campo `clean` (respuesta del personaje). El system prompt y la instruction no se cuentan — el límite se aplica al contenido variable por entrada.

**Presets:** tiny 1024 / small 2048 / medium 4096 / large 8192 tokens.

**Reporte incluye:** p50, p90, p95, máximo, total archivados, `max_seq_length` recomendado (p95 redondeado al próximo múltiplo de 256, mínimo 512).

**`curator.py`:** `_token_report` se inicializa a `""` antes del bloque condicional. Si el paso corre, el reporte se añade al `stats_report` del resultado. Si no corre, el reporte queda vacío y no aparece.

**GUI:** checkbox off por defecto. Preset combo con 4 opciones. Campo de tokenizer avanzado (vacío = proxy). Las opciones se muestran/ocultan con el checkbox.

### Verificado
- `filter_sets` filtra correctamente: 2 entradas OK, 1 overlength en prueba con texto de 10 000 chars (preset tiny).
- Reporte de distribución muestra percentiles y recomendación.
- Proxy fallback activo cuando no hay tokenizer.
- 30/30 tests del parser siguen en verde.
- `from modules.curator.curator import curate, CuratorConfig` importa sin errores.

---

## 2026-03-15 — Name Tagger: bug fix + Fase 9b planificada

### Bug corregido: name_tagger no modificaba el output final

**Síntoma:** El paso 4b ejecutaba (55% "Etiquetando nombres de personajes..." visible) pero los nombres NO eran reemplazados en el archivo de salida. "Everything okay, Nino?" salía sin cambios.

**Causa raíz:** El formatter (`formatter.py:59`) siempre lee `entry.get("clean", "")` para el contenido del asistente. Pero `tag_entry` en `name_tagger.py` modificaba `entry["output"]` — un campo que el formatter ignora completamente.

El pipeline de datos es:
1. Classifier produce `{"instruction": ..., "output": ..., "clean": ...}` — tres campos distintos
2. Cleaner normaliza `entry["clean"]`
3. Name Tagger (paso 4b) — **antes**: modificaba `"output"` ← ignorado por formatter; **ahora**: modifica `"clean"` ← campo que SÍ usa formatter
4. Formatter lee `entry["clean"]` → produce ChatML/Alpaca/etc.

**Fix:** `modules/curator/name_tagger.py` — en `tag_entry()`, para el formato raw se cambia de:
```python
if "output" in entry:
    entry["output"] = tag_text(...)
```
a:
```python
if "clean" in entry:
    entry["clean"] = tag_text(...)
if "output" in entry:
    entry["output"] = tag_text(...)  # por coherencia
```

**Lección:** Al agregar un paso al pipeline, verificar qué campo leen los pasos POSTERIORES, no asumir que `"output"` es el campo canónico. En este pipeline, `"clean"` es el campo de contenido del personaje que fluye hacia el formatter.

### Nueva fase planificada: Fase 9b — Editor de Dataset

Se añadió a TASKS.md la Fase 9b: módulo editor para revisar y corregir manualmente las muestras del dataset curado. Permite cargar JSONL/CSV del curator y editar entrada por entrada con filtros, marcado de eliminación, y guardado sin destruir el original.

### Estado de la sesión al cierre
- Name Tagger completamente funcional (precisión ~85-90%, aceptable para fine-tuning)
- Próximas tareas: `token_analyzer.py` (Fase 5) o `Editor de Dataset` (Fase 9b)

---

## 2026-03-15 — Fase 10: Name Tagger implementado

### Archivos creados/modificados
- `modules/core/spacy_manager.py` (nuevo) — gestor de modelos spaCy, 22 idiomas
- `modules/scraper/discovery.py` — añadido `export_character_roster()`
- `modules/gui/workers/scrape_worker.py` — `ExtractWorker` recibe `profile`, llama roster export
- `modules/gui/panels/scrape_panel.py` — pasa `profile` al `ExtractWorker`
- `modules/curator/name_tagger.py` (nuevo) — lógica de etiquetado con spaCy
- `modules/curator/curator.py` — campos name_tagging en CuratorConfig, paso 4b en pipeline
- `modules/gui/panels/languages_panel.py` (nuevo) — panel de descarga de modelos
- `modules/gui/curator_window.py` — pestaña "Idiomas" añadida
- `modules/gui/panels/curator_panel.py` — sección Name Tagger con preset, campos custom, indicador
- `requirements.txt` — añadido `spacy>=3.7`

### Decisiones técnicas
- **Dependency parsing con spaCy sm (~12 MB/idioma)**: Suficiente para vocative detection.
  Heurísticas implementadas: `dep_ == "vocative"`, `Name,` al inicio, `, Name[.!?]` al final,
  discurso reportado (lemma en verbos de habla), posesivo `Name's`. Fallback conservador → `{{char}}`.
- **El personaje principal nunca se reemplaza**: Solo se etiquetan personajes secundarios del roster.
- **Roster generado por el scraper**: `{Character}_characters.json` junto al dataset JSONL.
  Si no existe, el paso de name_tagging se omite silenciosamente.
- **Paso 100% opcional**: Checkbox desactivado por defecto. El usuario recibe explicación clara.
- **Presets configurables**: SillyTavern, Oobabooga, genérico, personalizado.
- **`find_roster()`**: Busca automáticamente el roster junto al input por convención de nombre.

### Verificado
- `list_available()` retorna 22 modelos correctamente
- `is_installed("en")` detecta `en_core_web_sm` ya instalado
- `_build_alias_index(roster)` excluye aliases del personaje principal
- CuratorConfig acepta todos los nuevos campos sin error
- GUI imports sin errores de importación circular

---

## 2026-03-14 — Inicio del proyecto

### Decisiones de arquitectura

**Parser genérico vs especializado**
Se decidió implementar un parser genérico con detección automática de formato en lugar
de parsers especializados por wiki. Justificación: los formatos de diálogo (bold-colon
y template) son convenciones de MediaWiki compartidas. La variabilidad real está en
organización (URLs, categorías), no en formato de diálogo, y ya está cubierta por los
perfiles JSON. Si un wiki usa un formato completamente propietario, se extenderá el
parser genérico con `parser_hooks` en el perfil.

**TUI basada en Rich (no Textual)**
El usuario prefiere interfaces standalone (no web). Se eligió Rich sobre Textual porque:
- Rich ya viene incluido en `typer[all]`
- Evita una dependencia extra
- Progress bars, panels y tablas de Rich son suficientes para la complejidad del proyecto

*Nota: decisión revertida el 2026-03-15. Ver entrada correspondiente.*

**Cache de HTTP con requests-cache**
Se agrega `requests-cache` para cache transparente en disco durante desarrollo. Evita
re-descargar wikitext al iterar sobre el parser. Se invalida con `python main.py cache-clear`.

**Wiki primario: Miraculous Ladybug**
Cambiado de Gravity Falls a Miraculous Ladybug como wiki de referencia y caso de prueba
principal, por preferencia del usuario.

**Formato de aliases en perfil**
Los aliases en el perfil se estructuraron como dict `{nombre: [lista_de_aliases]}` en
lugar de lista plana, para soportar múltiples personajes con sus respectivas variantes
en el mismo perfil.

### Validación completada (2026-03-15)
- Categoría y formato de diálogo del wiki de Miraculous Ladybug verificados.
- Pipeline scraper funcional contra el wiki real. Fase 2 cerrada.

---

## 2026-03-15 — Think Tank: rediseño arquitectónico completo

### Contexto
El proyecto fue evaluado para crecer más allá del scraper original. Se identificó que
el valor real no está solo en obtener diálogos sino en entregarlos listos para
entrenamiento de LLMs. Esto implicó diseñar una capa entera de curación de datasets.

---

### Decisión: Capa Curator

Se añade el módulo `curator/` paralelo a `scraper/`. El principio central es
**no destructivo**: nada se elimina, todo se separa en listas recuperables.

**Las 5 listas de salida del classifier:**
- `dialogue_clean.jsonl` — diálogo puro, sin embebidos
- `dialogue_mixed_thought.jsonl` — diálogo real con pensamiento interno embebido
- `dialogue_mixed_action.jsonl` — diálogo real con acción embebida
- `thought_only.jsonl` — pensamientos puros (archivado, no apto para training)
- `action_only.jsonl` — acciones puras (archivado, no apto para training)
- `overlength.jsonl` — líneas que exceden el límite óptimo de tokens (archivado)

**Justificación de listas mixed:**
Las líneas que mezclan diálogo con pensamiento o acción embebida son valiosas para
entrenamiento de roleplay: aportan contexto emocional y preparan al modelo para
interacción narrativa. Solo los pensamientos/acciones puros (sin diálogo real) son
descartados del training principal.

**Formato de etiquetas RP:**
Se hardcodea `*texto*` como formato estándar. Los LLMs reconocen este formato de su
preentrenamiento en textos narrativos. Se descartaron `[texto]` (puede confundir con
tokens especiales) y `(texto)` (ambiguo con paréntesis de aclaración). No se expone
esta decisión al usuario final.

**Schema de línea mixed:**
```json
{
  "speaker": "Marinette",
  "original": "Estoy bien. [pensando: mentira total] No te preocupes.",
  "clean": "Estoy bien. No te preocupes.",
  "embedded": [{"type": "thought", "content": "mentira total", "position": "middle"}],
  "episode": "S01E01",
  "context_prev": "Alya: ¿Estás segura de que estás bien?"
}
```

---

### Decisión: Token Analyzer integrado en Curator

El `token_analyzer.py` forma parte del curator, no es un paso separado. Actúa como
filtro final: las líneas dentro del límite van a los archivos de salida normales,
las que exceden van a `overlength.jsonl`.

**Presets de modelo:**
| Preset | Modelos | Límite fine-tuning |
|---|---|---|
| tiny | Phi-3 mini, Gemma 2B | 512-1024 tokens |
| small | LLaMA 3 8B, Mistral 7B | 1024-2048 tokens |
| medium | LLaMA 3 70B, Qwen 14B | 2048-4096 tokens |
| large | Mistral Nemo, Qwen 72B | 4096-8192 tokens |

El usuario elige preset por nombre, nunca un número.

---

### Decisión: System Prompt Builder sin dependencias de ML

El `system_prompt_builder.py` usa solo template filling desde el perfil JSON.
Sin modelos de lenguaje, sin APIs externas. Dependencias: ninguna nueva.

Diseñado para uso standalone: usuarios que quieran curar sus propios datasets sin
haber usado el scraper pueden usar el curator de forma independiente.

Los campos del system prompt son completamente configurables: se pueden agregar,
remover y renombrar desde el perfil JSON. Campos base: `character`, `show`,
`aliases`, `personality`.

---

### Decisión: Filtro de idioma en el Scraper

El filtro de idioma se mueve al módulo scraper (`scraper/lang_filter.py`), no al
curator. Justificación: filtrar antes de procesar es más eficiente, y el idioma
es una propiedad del material fuente, no del proceso de curación.

**Estrategia multilingüe:**
Datasets separados por idioma, no mezclados. Mezclar idiomas en fine-tuning:
- Funciona solo con modelos base multilingües (Qwen, mT5)
- Perjudica modelos base monolingües (LLaMA 2)
- Para voz de personaje, monolingüe siempre superior

El pipeline puede correrse múltiples veces con distinto `language` en el perfil
para generar versiones del mismo personaje en distintos idiomas.

---

### Decisión: Wizard de 4 pasos

El wizard reemplaza la configuración manual del curator. El usuario responde
en lenguaje natural, nunca ve flags ni parámetros técnicos.

**Orden de pasos (el formato va primero porque determina el resto):**
1. Formato de salida (ChatML / Alpaca / ShareGPT / JSONL crudo)
2. Objetivo (diálogo / roleplay / ambos) — responde implícitamente si incluir mixed
3. Calidad mínima — con advertencia explícita sobre daño de líneas cortas al training
4. División train/val/test (default: 80/10/10)

Config guardada en `curator_config.json`, reutilizable sin volver a correr el wizard.

---

### Decisión: Joiner como módulo de preparación final

El `joiner.py` no es solo un combinador de listas. Es el último paso de la pipeline:
merge con pesos → shuffle con seed fija → deduplicación cruzada → split train/val/test.

**Pesos por objetivo:**
- Diálogo: 100% clean
- RP: 50% clean / 30% mixed_thought / 20% mixed_action
- Ambos: 70% / 20% / 10%

Output final listo para pasar directamente al trainer: `train.jsonl`,
`validation.jsonl`, `test.jsonl`.

---

### Decisión: GUI PySide6 (reemplaza TUI Rich)

**Descartadas:**
- Gradio: requiere browser, wizard es ciudadano de segunda clase en su modelo
- Dear PyGui: excelente para dashboards en tiempo real, pero immediate mode es frágil
  para formularios con estado (wizard). Queda en radar para futuros proyectos.

**Elegida: PySide6**
- `QWizard` + `QWizardPage` — solución nativa exacta para el wizard de 4 pasos
- `QTableView` con modelo virtual — maneja 1M filas sin lag
- `Qt Charts` — dashboard de stats y distribución de tokens
- `QThread` — operaciones de scraping/curación sin congelar el UI
- El usuario ya tiene experiencia con PySide6 de proyectos anteriores

La CLI se mantiene con flag `--cli` para usuarios avanzados. Si en el futuro se
quiere una versión web deployable en HF Spaces, se puede agregar un módulo Gradio
separado sin tocar el core.

---

### Refactoring pendiente del Scraper

El scraper actual es funcional pero fue diseñado para una herramienta CLI simple.
Debe adaptarse al nuevo paradigma antes de implementar el curator:
- Agregar `lang_filter.py`
- Extender el schema del perfil JSON (language, personality, system_prompt_fields)
- Adaptar `exporter.py` para producir las 6 listas de salida del curator

---

## 2026-03-15 — Refactoring del scraper + GUI base (PySide6)

### Cambios implementados

**Scraper — Fase 4 completa:**
- `scraper/config.py` (nuevo): centraliza ROOT_DIR, PROFILES_DIR, OUTPUT_DIR, CACHE_DIR, INDEX_DIR para que CLI y GUI usen paths absolutos independientemente del CWD.
- `scraper/lang_filter.py` (nuevo): detección de idioma via langdetect. Función `matches_language(wikitext, target_lang)` con comportamiento conservador (no descarta en caso de duda). Requiere `langdetect` instalado; sin él, el filtro se desactiva silenciosamente.
- `scraper/fetcher.py`: `setup_cache()` ahora usa CACHE_DIR para path absoluto del SQLite. Evita problema de CWD cuando se llama desde la GUI.
- `scraper/discovery.py`: INDEX_DIR migrado a `scraper/config.py`.
- `scraper/exporter.py`: agrega `export_sets(sets, output_dir)` para producir las 6 listas categorizadas del curator (`dialogue_clean`, `dialogue_mixed_thought`, `dialogue_mixed_action`, `thought_only`, `action_only`, `overlength`). Mantiene `export()` para compatibilidad con el pipeline CLI.
- Perfiles JSON: actualizados con campos `language` (ISO 639-1), `personality` (vacío por ahora), `system_prompt_fields` (dict con toggles).

**GUI base — Fase 8 (parcial):**
- `gui/app.py`: entry point de la QApplication. Llama `setup_cache()` antes de abrir la ventana.
- `gui/main_window.py`: QMainWindow con sidebar oscura (estilo Catppuccin Mocha) y QStackedWidget. 3 paneles: Scraping, Perfiles, Caché.
- `gui/panels/profiles_panel.py`: tabla de perfiles con botones Nuevo y Eliminar. `NewProfileDialog` crea perfiles con el nuevo schema (language, personality, etc.).
- `gui/panels/scrape_panel.py`: pipeline completa en 3 pasos secuenciales. Secciones se activan progresivamente (config → indexación → personaje → resultados). Conectada a IndexWorker y ExtractWorker.
- `gui/workers/scrape_worker.py`: `IndexWorker` y `ExtractWorker` como QThread subclasses. Señales `progress`, `finished`, `error` para comunicación segura con el UI thread.
- `main.py`: lanza GUI por default. Flag `--cli` para modo terminal (Typer).
- `run.sh`: actualizado — sin args lanza GUI, con args pasa todo a `main.py`.
- `requirements.txt`: reemplaza `textual` por `PySide6>=6.7` y `langdetect>=1.0.9`.

### Decisiones técnicas

**Paths absolutos via config.py:** El problema central era que `discovery.py` y `fetcher.py` usaban paths relativos (`.cache/`). Desde la GUI, el CWD puede no ser el root del proyecto, lo que causaría que el cache y los índices se crearan en ubicaciones incorrectas. `config.py` resuelve esto con `Path(__file__).parent.parent`.

**Comportamiento conservador del lang_filter:** Si langdetect no está instalado, o si la detección falla, o si el texto es muy corto, `matches_language()` retorna True. Esto garantiza que el filtro de idioma NUNCA descarte páginas por error técnico — solo filtra cuando tiene certeza.

**PySide6 con QThread:** Los workers de scraping corren en threads separados y se comunican con la GUI únicamente via señales Qt (patrón estándar). Ninguna operación de red toca el UI thread.

**tui.py:** Archivo legacy (usaba Textual). No se eliminó pero ya no es el entry point. `textual` fue removido de requirements.txt. Si se importa directamente fallará con ImportError, lo cual es esperado.

---

## 2026-03-15 — Dashboard, i18n y sistema de temas

### Cambios implementados

**Error de diseño corregido:** La GUI arrancaba directamente en el módulo scraper. En un proyecto multi-módulo esto es incorrecto — cada nuevo módulo requeriría cambiar el entry point. Se introdujo un dashboard de selección de módulos como pantalla inicial.

**Infraestructura core (`modules/core/`):**
- `settings.py`: persistencia de configuración de usuario en `.settings.json` (idioma, tema). API simple: `load()`, `save()`, `get(key)`, `set(key, value)`.
- `i18n.py`: motor de traducciones basado en JSON. `t("key")` retorna string traducido con fallback al key. `load(lang)` lee `locales/<lang>.json`. `available_langs()` auto-detecta archivos `.json` disponibles.
- `themes.py`: motor de temas QSS. `apply(app, name)` carga `themes/<name>.qss`. `list_themes()` auto-detecta archivos `.qss` y lee el comentario `/* display: Nombre */` para nombre visible.

**Dashboard (`modules/gui/dashboard.py`):**
- `ModuleCard(QFrame)`: tarjeta por módulo con botón "Abrir". Módulos no disponibles muestran badge "Próximamente" y no son clickeables.
- `DashboardPanel(QWidget)`: grid de tarjetas + footer con selector de idioma y tema en vivo. Cambio de tema se aplica sin reiniciar; cambio de idioma requiere reinicio (tooltip de aviso).
- `_MODULES`: lista central para registrar módulos. Agregar uno = una entrada en la lista.

**AppWindow (`modules/gui/app_window.py`):**
- `QStackedWidget` con dashboard en índice 0 y módulos cargados lazy (solo al primer acceso).
- Factory `_create_module_widget(module_id)`: agregar módulo futuro = un bloque `if module_id == "X"`.

**ScraperWidget (`modules/gui/main_window.py`):**
- Refactorizado de `MainWindow(QMainWindow)` a `ScraperWidget(QWidget)` embebible.
- Añadida señal `back_requested` que dispara el botón "← Módulos".
- Eliminado stylesheet inline (ahora viene del QSS global).

**Tema Catppuccin Mocha (`themes/default.qss`):**
- Cobertura completa: botones con variantes `role` (primary, danger, nav, back), inputs, ComboBox, SpinBox, CheckBox, GroupBox, ProgressBar, QTableWidget, ScrollBar, StatusBar, frames del sidebar, tarjetas del dashboard.

**Locales (`locales/es.json`, `locales/en.json`):**
- Todas las cadenas visibles del dashboard y la ventana principal externalizadas.
- `en.json` creado como placeholder (en.json tiene las cadenas en inglés listas).

### Decisiones técnicas

**Orden de arranque:** `settings.load()` → `i18n.load()` → `QApplication` → `themes.apply()` → `setup_cache()` → `AppWindow`. El tema debe aplicarse después de crear la QApplication pero antes de mostrar la ventana para evitar flash de estilo sin aplicar.

**Auto-detección de temas/idiomas:** Ambos sistemas escanean sus directorios al arrancar. Agregar un nuevo tema o idioma = soltar el archivo en la carpeta correcta, sin tocar código.

---

## 2026-03-15 — Módulo Curator completo + GUI Curator

### Módulo Curator — scripts implementados

**Pipeline funcional validado contra 4508 líneas reales (Marinette / Miraculous Ladybug):**
- `classifier.py` — clasifica en 5 categorías usando regex. Resultado: 2526 clean, 1953 mixed_action, 29 action_only.
- `cleaner.py` — elimina HTML residual (span con tooltips), normaliza Unicode, puntuación tipográfica, espacios. 5 spans eliminados en los datos reales.
- `quality_scorer.py` — filtra por longitud mínima (default 10 chars) y TTR. 405 rechazadas (9%).
- `deduplicator.py` — exact match O(n) por hash. 73 duplicados eliminados. Fuzzy deshabilitado por default (O(n²) prohibitivo en datasets grandes).
- `system_prompt_builder.py` — template filling desde perfil JSON. Auto-selección de template según campos disponibles. Template custom con variables libres {var}. Ratio configurable: % de entradas que reciben system prompt (mezcla con/sin es beneficiosa para robustez).
- `formatter.py` — ChatML, Alpaca, ShareGPT, JSONL crudo.
- `stats.py` — distribución de longitudes, vocabulario único, detección de desbalances, reporte de retención.
- `curator.py` — orquestador del pipeline completo con callbacks de progreso para GUI.

**Retención final del pipeline:** 4030/4508 (89%).

### GUI Curator

- `CuratorWidget` + `CuratorPanel` + `CuratorWorker` implementados.
- Auto-detección de personaje desde nombre de archivo ({Personaje}_dataset.jsonl).
- Exportación en JSONL / CSV / TXT (combinables). CSV con columnas planas para edición manual del campo instruction.
- Sin system prompt → columna system ausente del CSV. Con system prompt → columna presente según ratio.
- Directorio de salida: `{input_dir}/curated/`

### Decisiones técnicas

**CSV para edición manual del instruction:**
El campo `instruction` se deja como `[COMPLETAR]` por diseño. El usuario puede abrir el CSV en cualquier editor de tablas (LibreOffice Calc, Excel, etc.) y rellenar la columna instruction con preguntas que empaten con las respuestas del personaje, simulando conversación.

**Ratio de system prompt:**
Mezclar entradas con y sin system prompt en el training produce modelos más robustos: aprenden a responder como el personaje con o sin instrucciones explícitas. Default: 100% (todas las entradas tienen system prompt). Configurable desde la GUI.

**Joiner (Fase 7) — pendiente de análisis:**
No se integra en el curator por ahora. El joiner (merge de listas con pesos, shuffle, split train/val/test) puede o no ser necesario según el uso. Se analizará por separado.

---

## 2026-03-15 — Name Tagger — diseño planificado (Fase 10)

### Contexto y decisión

El usuario quiere transferir el **estilo comunicativo** de un personaje a un LLM sin transferir la identidad ni el bagaje histórico. El modelo aprende a hablar COMO el personaje (calidez, energía, maneras de expresarse), no a SER el personaje ni a conocer su historia.

**Ejemplo de transformación:**
- Antes: `"Are you okay, Adrien?"` / `"I wonder if Alya is home."`
- Después: `"Are you okay, {{user}}?"` / `"I wonder if {{char}} is home."`

### Por qué spaCy y no regex puro

El problema es de resolución de roles conversacionales, no de sustitución de cadenas. El mismo nombre puede ser vocativo (→ `{{user}}`) o referencia en tercera persona (→ `{{char}}`). spaCy con dependency parsing detecta el rol gramatical del token, lo que permite clasificar con ~85-90% de precisión sin LLM.

spaCy `sm` models (~12 MB por idioma) son suficientes — incluyen tokenizer, POS tagger y dependency parser. Los `md` añaden word vectors no necesarios para esta tarea.

### Multilingüe desde el inicio

El campo `language` del perfil JSON ya determina el idioma. `spacy_manager.py` gestiona la descarga y carga del modelo correcto automáticamente. Idiomas planificados: en, es, fr, de, it, pt, zh, ja, nl, ko, pl, ru, sv, da, nb, uk, ro, el, fi, ca.

### Paso opcional en el pipeline

El name tagger es completamente opcional. Se activa desde la GUI con un checkbox y una explicación clara de qué hace. Los usuarios que quieran un dataset con nombres reales (para fine-tuning de personaje específico) simplemente no lo activan.

---

## 2026-03-15 — Pulido del módulo Scraper (GUI)

### Cambios implementados

**Tabla de personajes — sorting por columna:**
- `setSortingEnabled(True)` habilitado en `speakers_table`.
- Clase `_NumericItem(QTableWidgetItem)` con `__lt__` sobrescrito para ordenar la columna "Líneas" como entero. Sin esto Qt ordena lexicográficamente ("100" < "20").
- Clic en cabecera de columna alterna A→Z / Z→A (Personaje) o menor→mayor / mayor→menor (Líneas).

**Tabla de personajes — filtrado dinámico:**
- El campo de búsqueda (antes "Personaje:") pasa a llamarse "Buscar:" y se ubica encima de la tabla.
- `textChanged` dispara `_apply_speakers_filter(text)` que repopula la tabla con solo los nombres que contienen la subcadena (case-insensitive).
- Al seleccionar una fila, el input se actualiza con el nombre exacto sin re-disparar el filtro (`blockSignals`).
- Limpiar el campo restaura la lista completa.

**Selección única:**
- `setSelectionMode(QTableWidget.SingleSelection)` — elimina la posibilidad de seleccionar múltiples filas con Shift/Ctrl. La selección múltiple no estaba implementada en el backend y generaba confusión silenciosa.

**Selección de formato de salida:**
- Tres checkboxes debajo de las opciones de contexto: JSONL (marcado por defecto), CSV, TXT.
- Se pueden combinar libremente. Si se desmarcan todos, se fuerza JSONL como fallback.
- Los formatos seleccionados se pasan al `ExtractWorker` que llama a `export()` con la lista.

**Prefijo de personaje en archivos de salida:**
- Los archivos pasan de `output/<personaje>/dataset.jsonl` a `output/<personaje>/<personaje>_dataset.jsonl` (y `.csv`, `.txt`).
- El panel de resultados muestra el directorio de salida y la lista de archivos generados.

### Bugs potenciales vigilados

**Sorting + repoblado:** Al re-filtrar, el sorting se desactiva temporalmente (`setSortingEnabled(False)`) antes de escribir las filas y se reactiva al terminar. Esto evita que Qt reordene filas a mitad de escritura, lo cual podría mezclar datos entre celdas.
