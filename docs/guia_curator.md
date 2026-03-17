# Guía del Curator

El módulo Curator toma el dataset crudo del Scraper y lo procesa a través de un pipeline de 8 pasos para producir un dataset limpio, filtrado y listo para fine-tuning.

---

## Pipeline de curación

```
Entrada: {Personaje}_dataset.jsonl
    ↓
1. Classifier      → separa en 5 categorías
2. Cleaner         → elimina markup residual, normaliza encoding
3. Quality Scorer  → filtra entradas demasiado cortas o repetitivas
4. Deduplicator    → elimina duplicados exactos (y opcionalmente fuzzy)
4b. Name Tagger    → reemplaza nombres por {{user}} / {{char}}  [opcional]
5. Token Analyzer  → archiva entradas que exceden el límite del modelo  [opcional]
6. System Prompt   → inyecta el system prompt del personaje  [opcional]
7. Formatter       → convierte al formato de salida (ChatML, Alpaca, etc.)
8. Stats           → genera reporte de métricas del pipeline
    ↓
Salida: output/{Personaje}/curated/
```

---

## Categorías del classifier

El classifier separa cada entrada en una de estas categorías:

| Categoría | Descripción | Incluida en output |
|-----------|-------------|-------------------|
| `dialogue_clean` | Diálogo puro, sin acciones ni pensamientos | Sí |
| `dialogue_mixed_thought` | Diálogo con pensamiento interno embebido | Sí (objetivo RP) |
| `dialogue_mixed_action` | Diálogo con acción narrada embebida | Sí (objetivo RP) |
| `thought_only` | Solo pensamientos, sin diálogo | Archivada |
| `action_only` | Solo acciones, sin diálogo | Archivada |

Las categorías archivadas se guardan en `curated/archived/` y no se incluyen en el training. Son recuperables si cambias de objetivo.

---

## Paso a paso en la GUI

### 1. Cargar dataset
1. Abre el módulo **Curator** desde el Dashboard.
2. Pulsa **Seleccionar archivo** y elige el `.jsonl` del Scraper.
3. El personaje se detecta automáticamente desde el nombre del archivo.

### 2. Configurar el pipeline

**Calidad mínima**
- `min_chars`: mínimo de caracteres en la respuesta (default: 10). Aumentar si quieres filtrar respuestas muy cortas que no aportan al training.
- `TTR threshold`: type-token ratio mínimo. Filtra respuestas con vocabulario muy repetitivo.

> Advertencia: filtrar agresivamente reduce el dataset. Para fine-tuning de voz de personaje, es preferible tener más entradas medianas que pocas perfectas.

**Deduplicación**
- Dedup exacto siempre activo (O(n), rápido).
- Dedup fuzzy: opcional, O(n²), lento en datasets grandes. Útil si hay muchas repeticiones con ligeras variaciones.

**Name Tagger** (opcional)
- Reemplaza nombres de personajes secundarios por `{{user}}` (vocativo) o `{{char}}` (referencia).
- Requiere un modelo spaCy instalado para el idioma del dataset.
- Presets: SillyTavern (`{{user}}/{{char}}`), Oobabooga (`<|user|>/<|bot|>`), Genérico (`[USER]/[CHAR]`), Custom.
- Gestiona los modelos de idioma en la pestaña **Idiomas** del módulo Curator.

**Token Analyzer** (opcional)
- Archiva entradas que exceden el límite de tokens del modelo objetivo.
- Presets: `tiny` (1024, modelos 1B–3B), `small` (2048, modelos 7B–9B), `medium` (4096, 13B–30B), `large` (8192, 70B+).
- Si no tienes `tiktoken` ni `transformers` instalado, usa un proxy de ~4 chars/token (suficiente para fine-tuning local).
- El reporte muestra p50, p90, p95 y `max_seq_length` recomendado para tu trainer.

**System Prompt** (opcional)
- Construye el system prompt desde los campos del perfil (`character`, `show`, `aliases`, `personality`).
- Ratio: `1.0` = todas las entradas reciben system prompt. `0.7` = 70% con prompt, 30% sin prompt. Mezclar es beneficioso para que el modelo sea robusto con y sin instrucciones.

**Formato de salida**
- `chatml`: `{"messages": [{"role": "system", ...}, {"role": "user", ...}, {"role": "assistant", ...}]}`
- `alpaca`: `{"instruction": ..., "input": "", "output": ...}`
- `sharegpt`: `{"system": ..., "conversations": [{"from": "human", ...}, {"from": "gpt", ...}]}`
- `jsonl_raw`: `{"instruction": ..., "output": ...}` — el más simple, compatible con el Editor

### 3. Ejecutar

Pulsa **Curar**. El progreso se muestra en la barra y el log. Al terminar verás:
- Estadísticas del pipeline (entradas por categoría, retención total)
- Reporte del Token Analyzer (si estaba activo)
- Archivos generados en `curated/`

---

## Archivos de salida

```
output/{Personaje}/curated/
    dialogue_clean.jsonl
    dialogue_mixed_thought.jsonl
    dialogue_mixed_action.jsonl
    archived/
        thought_only.jsonl
        action_only.jsonl
        overlength.jsonl        ← solo si Token Analyzer activo
```

Cada archivo contiene entradas en el formato que elegiste (ChatML, Alpaca, etc.).

---

## Formatos de exportación adicionales

Además del JSONL principal, puedes exportar también CSV y TXT simultáneamente. El CSV es útil para rellenar el campo `instruction` manualmente en una hoja de cálculo antes de volver a importar al **Editor**.
