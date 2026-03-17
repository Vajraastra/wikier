# Guía de Perfiles JSON

Los perfiles JSON definen cómo el Scraper debe conectarse a un wiki y qué personajes buscar. Se guardan en la carpeta `profiles/`.

---

## Estructura de un perfil

```json
{
  "name": "Miraculous Ladybug",
  "base_url": "https://miraculousladybug.fandom.com",
  "transcript_categories": [
    "Category:Episode transcripts"
  ],
  "dialogue_format": "auto",
  "rate_limit_seconds": 0.5,
  "language": "en",
  "character_aliases": {
    "Marinette": ["Marinette", "Marinette Dupain-Cheng", "Ladybug", "Bridgette"],
    "Adrien":    ["Adrien", "Adrien Agreste", "Chat Noir", "Cat Noir"]
  },
  "personality": "",
  "system_prompt_fields": {
    "character":    true,
    "show":         true,
    "aliases":      true,
    "personality":  true
  }
}
```

---

## Campos

### `name`
Nombre legible del wiki. Se muestra en la GUI.

### `base_url`
URL base del wiki **sin** slash final.

```json
"base_url": "https://gravityfalls.fandom.com"
```

### `transcript_categories`
Lista de categorías de MediaWiki que contienen las páginas de transcripciones. Puedes incluir varias si el wiki las organiza en subcategorías.

**Cómo encontrarlas:** ve al wiki en el navegador, busca una página de transcripción y mira en sus categorías al final de la página.

```json
"transcript_categories": [
  "Category:Episode transcripts",
  "Category:Season 2 transcripts"
]
```

### `dialogue_format`
Formato del diálogo en las páginas de transcripción.

| Valor | Descripción |
|-------|-------------|
| `"auto"` | Auto-detección (recomendado) |
| `"bold-colon"` | `'''Speaker:''' texto` |
| `"template"` | `{{dialogue\|speaker\|texto}}` |
| `"mixed"` | Ambos formatos mezclados |

La mayoría de wikis usan `"auto"`.

### `rate_limit_seconds`
Pausa en segundos entre peticiones HTTP. Respeta los servidores del wiki.
- `0.5` = una petición cada medio segundo (recomendado)
- `1.0` = más conservador para wikis pequeños
- `0.0` = sin pausa (no recomendado)

### `language`
Código ISO 639-1 del idioma de las transcripciones. Activa el filtro de idioma del Scraper.

```json
"language": "en"   // inglés
"language": "es"   // español
"language": ""     // sin filtro de idioma
```

### `character_aliases`
Mapa de `NombreCanónico → [lista de aliases]`. El Scraper busca líneas de diálogo donde el speaker coincida con cualquiera de los aliases.

```json
"character_aliases": {
  "Dipper": ["Dipper", "Dipper Pines", "Pine Tree"],
  "Mabel":  ["Mabel", "Mabel Pines"]
}
```

Incluye variantes de nombre, apodos, alter egos y formas alternas de escritura que puedan aparecer en las transcripciones.

### `personality`
Descripción de la personalidad del personaje para el system prompt. Puede dejarse vacío.

```json
"personality": "Optimista, creativa, apasionada por la moda y los superhéroes."
```

### `system_prompt_fields`
Controla qué secciones se incluyen en el system prompt generado por el Curator.

```json
"system_prompt_fields": {
  "character":   true,   // nombre del personaje
  "show":        true,   // nombre del show/wiki
  "aliases":     true,   // lista de aliases/alter egos
  "personality": true    // campo personality (solo si no está vacío)
}
```

---

## Crear un perfil nuevo

1. Copia uno de los perfiles existentes como base:
   ```bash
   cp profiles/miraculousladybug.json profiles/miwiki.json
   ```
2. Edita los campos según el nuevo wiki.
3. Busca las categorías de transcripciones en el wiki objetivo.
4. El perfil aparecerá automáticamente en el selector de la GUI al reiniciar.

---

## Ejemplo: Gravity Falls

```json
{
  "name": "Gravity Falls",
  "base_url": "https://gravityfalls.fandom.com",
  "transcript_categories": [
    "Category:Transcripts"
  ],
  "dialogue_format": "auto",
  "rate_limit_seconds": 0.5,
  "language": "en",
  "character_aliases": {
    "Dipper": ["Dipper", "Dipper Pines", "Pine Tree"],
    "Mabel":  ["Mabel", "Mabel Pines", "Shooting Star"],
    "Grunkle Stan": ["Stan", "Grunkle Stan", "Stanley", "Stanford"]
  },
  "personality": "",
  "system_prompt_fields": {
    "character":   true,
    "show":        true,
    "aliases":     true,
    "personality": false
  }
}
```

---

## Notas

- El nombre canónico en `character_aliases` es el que se usa como nombre de carpeta en `output/` y como nombre de archivo (`Dipper_dataset.jsonl`).
- Los aliases deben coincidir **exactamente** (case-sensitive) con como aparecen en las transcripciones del wiki.
- Si un personaje tiene muchos aliases y el Scraper captura líneas de otros personajes, revisa y afina los aliases.
