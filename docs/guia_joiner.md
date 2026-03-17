# Guía del Joiner

El módulo Joiner toma los archivos del Curator y prepara el dataset final: combina categorías según el objetivo de entrenamiento, mezcla con seed reproducible y divide en train/validation/test.

También incluye un conversor de formatos standalone que no requiere haber pasado por el pipeline anterior.

---

## Pipeline del Joiner

```
curated/
    dialogue_clean.jsonl
    dialogue_mixed_thought.jsonl
    dialogue_mixed_action.jsonl
         ↓
    1. merge   → combina categorías con pesos por objetivo
    2. shuffle → mezcla aleatoriamente (seed fija)
    3. split   → divide en train / validation / test
    4. export  → escribe archivos JSONL finales
         ↓
output/joined/
    {Prefijo}_train.jsonl
    {Prefijo}_validation.jsonl
    {Prefijo}_test.jsonl
```

---

## Paso a paso en la GUI

### Sección Pipeline

**1. Seleccionar carpeta de entrada**
Elige la carpeta `curated/` generada por el Curator. El Joiner detecta automáticamente qué categorías están disponibles.

**2. Objetivo de entrenamiento**

| Objetivo | Categorías incluidas | Pesos |
|----------|---------------------|-------|
| `dialogue` | `dialogue_clean` | 100% clean |
| `roleplay` | clean + mixed_thought + mixed_action | 50% / 30% / 20% |
| `both` | clean + mixed_thought + mixed_action | 70% / 20% / 10% |

- **Diálogo puro**: el modelo aprende el estilo de habla del personaje en conversación directa.
- **Roleplay**: incluye entradas con pensamientos y acciones narradas (`*acción*`). Ideal para bots de chat con personalidad inmersiva.
- **Ambos**: balance entre diálogo limpio y roleplay narrativo.

**3. Límite de entradas** (opcional)
Si el dataset es muy grande, puedes limitar el total. El Joiner muestrea proporcionalmente según los pesos del objetivo.

**4. Split train/val/test**
- Ratios en porcentaje. Se normalizan automáticamente si no suman 100.
- Default: 80 / 10 / 10.

**5. Seed**
Número entero para reproducibilidad. La misma seed produce siempre el mismo orden de mezcla.

**6. Prefijo de salida**
Nombre que se antepone a los archivos generados (ej. `"Marinette"` → `Marinette_train.jsonl`).

**7. Ejecutar**
Pulsa **Unir y dividir**. Los archivos se guardan en `output/joined/` por defecto.

---

## Sección Conversor de formatos

Permite convertir un archivo de dataset entre formatos **sin pasar por el pipeline completo**.

**Formatos soportados:**

| Formato | Estructura |
|---------|-----------|
| `chatml` | `{"messages": [{"role": "system"/"user"/"assistant", "content": "..."}]}` |
| `alpaca` | `{"instruction": ..., "input": "", "output": ...}` |
| `sharegpt` | `{"system": ..., "conversations": [{"from": "human"/"gpt", "value": "..."}]}` |
| `jsonl_raw` | `{"instruction": ..., "output": ...}` |
| CSV | columnas: `system`, `instruction`, `output` |
| TXT | bloques `[SYSTEM]` / `[USER]` / `[CHAR]` |

**Uso:**
1. Selecciona el **archivo fuente** (el formato se auto-detecta).
2. Elige el **formato de destino** JSONL.
3. Selecciona la **ruta de salida**.
4. Pulsa **Convertir**.

> El conversor solo produce JSONL como formato de salida. Para exportar CSV o TXT usa el Curator directamente.

---

## Ejemplo de uso típico

Tienes tres sesiones de curación de Marinette con distintas configuraciones. Quieres combinarlas:

1. Cura cada sesión por separado con el Curator → obtienes tres carpetas `curated/`.
2. En el Joiner, apunta a la primera carpeta con objetivo `roleplay`, sin límite.
3. Exporta a `output/joined/`.
4. Repite para las otras dos carpetas, ajustando la seed si quieres variación.
5. Usa el **Conversor** para unificar si los formatos difieren.

> Para merge manual entre múltiples carpetas curated, el flujo actual es correr el Joiner por cada carpeta y concatenar los JSONL manualmente. Una futura versión soportará selección múltiple de carpetas.
