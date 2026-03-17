# Guía del Scraper

El módulo Scraper recorre las páginas de transcripciones de un wiki Fandom, extrae los diálogos de un personaje específico y los exporta en los formatos que elijas.

---

## Flujo en la GUI

### Paso 1 — Configurar

1. Abre el módulo **Scraper** desde el Dashboard.
2. Selecciona un **perfil** del menú desplegable (ej. `Miraculous Ladybug`).
3. Ajusta el límite de páginas si quieres hacer una prueba con un subconjunto.

### Paso 2 — Indexar

1. Pulsa **Indexar wiki**.
2. El scraper recorre la categoría de transcripciones definida en el perfil y construye un índice de páginas disponibles.
3. Cuando termine verás el número de páginas encontradas.

> El índice se guarda en `.cache/` para no repetir esta consulta en la siguiente ejecución.

### Paso 3 — Extraer personaje

1. Escribe el nombre del personaje en el campo **Buscar** o selecciónalo en la tabla.
   - La tabla muestra todos los speakers encontrados en el wiki y el número de líneas de cada uno.
   - Puedes ordenar por cualquier columna haciendo clic en el encabezado.
2. Elige los **formatos de salida** (JSONL, CSV, TXT — pueden combinarse).
3. Elige si incluir **contexto** (la línea anterior del interlocutor como campo `instruction`).
4. Pulsa **Extraer**.

### Resultado

Los archivos se guardan en:
```
output/{Personaje}/
    {Personaje}_dataset.jsonl   ← formato principal
    {Personaje}_dataset.csv     ← si lo seleccionaste
    {Personaje}_dataset.txt     ← si lo seleccionaste
    {Personaje}_characters.json ← roster de personajes (para el Name Tagger)
```

---

## Formatos de exportación

### JSONL (recomendado)
Cada línea es un objeto JSON con los campos `instruction` y `output`:
```json
{"instruction": "[COMPLETAR]", "output": "texto del personaje"}
{"instruction": "¿Estás bien?", "output": "Sí, estoy bien."}
```
El campo `instruction` se deja como `[COMPLETAR]` cuando no hay contexto disponible. Se rellena manualmente en el **Editor** o automáticamente si activas el contexto.

### CSV
Columnas: `instruction`, `output` (y `system` si el Curator lo añade después).
Útil para editar en LibreOffice Calc o Excel.

### TXT
Bloques legibles por humanos:
```
[USER]   ¿Estás bien?
[CHAR]   Sí, estoy bien.

[USER]   [COMPLETAR]
[CHAR]   ¡Esto es increíble!
```

---

## Filtro de idioma

Si el perfil tiene `"language": "es"`, el scraper filtra automáticamente páginas que no estén escritas en ese idioma. El filtro usa `langdetect` y es **conservador**: si hay duda, incluye la página.

Para desactivar el filtro, deja `language` en blanco o elimina el campo.

---

## Cache HTTP

El scraper cachea todas las peticiones HTTP en un SQLite en `.cache/`. Esto significa que:
- La segunda ejecución es mucho más rápida.
- Si el wiki actualiza una página, el cache puede servir la versión antigua.

Para limpiar el cache: `python main.py cache-clear` (CLI) o borra la carpeta `.cache/` manualmente.

---

## Configurar un nuevo wiki

Ver [guia_perfiles.md](guia_perfiles.md) para crear un perfil JSON para cualquier wiki Fandom.
