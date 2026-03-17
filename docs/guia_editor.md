# Guía del Editor de Dataset

El módulo Editor permite revisar y corregir manualmente las entradas de un dataset curado, entrada por entrada. Es especialmente útil para rellenar el campo `instruction` con preguntas o prompts que empaten con las respuestas del personaje.

---

## Interfaz

```
┌─────────────────────────────────────────────────────────────┐
│  [Abrir]  [Guardar]  │  [Solo incompletos]    42 completas  │  ← Toolbar
├─────────────────────────────────────────────────────────────┤
│  #  │  Instruction              │  Output          │ Estado │  ← Tabla
│  1  │  ¿Estás bien?             │  Sí, estoy bien  │ ✓ OK   │
│  2  │  [COMPLETAR]              │  ¡Increíble!     │ COMPLT │
│  3  │  ...                      │  ...             │ ✓ OK   │
├─────────────────────────────────────────────────────────────┤
│ 🔓  System:      │  [texto del system prompt...]           │  ← Editor
│ 🔓  Instruction: │  [texto de la instrucción...]           │
│     Output:      │  [respuesta del personaje...]           │
├─────────────────────────────────────────────────────────────┤
│  [← Anterior]          Entrada 2 de 15          [Siguiente →] │  ← Footer
│                                        [✗ Eliminar]           │
└─────────────────────────────────────────────────────────────┘
```

---

## Flujo de trabajo básico

1. Pulsa **Abrir** y selecciona tu archivo JSONL, CSV o TXT.
2. La tabla muestra todas las entradas. Las marcadas `[COMPLETAR]` tienen la instrucción vacía.
3. Activa **Solo incompletos** para ver únicamente las que necesitan trabajo.
4. Navega con los botones **Anterior / Siguiente** o haz clic directamente en la tabla.
5. Edita los campos en el área inferior.
6. Pulsa **Ctrl+S** o **Guardar** cuando quieras escribir al disco.

> Los cambios se acumulan en memoria hasta que guardas. El indicador `● cambios sin guardar` aparece en la toolbar cuando hay modificaciones pendientes.

---

## Lock de campos

El botón 🔓 a la izquierda de **System** e **Instruction** activa el "bloqueo de campo". Cuando está activo (🔒):

- Al pulsar **Siguiente**, el valor del campo bloqueado se copia automáticamente a la siguiente entrada.
- Útil para rellenar el mismo system prompt o la misma pregunta en un bloque de entradas consecutivas sin escribirlo cada vez.

**Ejemplo:** si tienes 20 respuestas a "¿Cómo te sientes hoy?", escribe la pregunta en la entrada 1, activa el lock de Instruction, y navega con Siguiente — el campo se propaga sola.

---

## Filtro "Solo incompletos"

Activa el checkbox en la toolbar. La tabla se filtra para mostrar únicamente las entradas donde `instruction` está vacío o es `[COMPLETAR]`.

Las entradas eliminadas no aparecen en este filtro.

---

## Búsqueda y reemplazo (Ctrl+F)

Abre la barra de búsqueda con **Ctrl+F** o ciérrala con la misma tecla / botón ✕.

**Buscar:**
- Escribe el texto a buscar. Las filas con coincidencias se resaltan en naranja.
- Navega entre resultados con ↑ / ↓.

**Reemplazar:**
- **Esta**: reemplaza en la entrada actualmente seleccionada y avanza al siguiente resultado.
- **Todas**: reemplaza en todas las entradas que tienen coincidencia de una vez.

La búsqueda opera sobre los campos `system`, `instruction` y `output` simultáneamente.

---

## Eliminar y restaurar entradas

- **✗ Eliminar**: marca la entrada como eliminada (fondo gris). No se borra del dataset en memoria.
- **↺ Restaurar**: desmarca la entrada eliminada.
- Al guardar, las entradas eliminadas se excluyen del archivo escrito.

Esto permite revisar y reconsiderar sin perder datos hasta el momento del guardado.

---

## Formatos soportados

El Editor carga y guarda en el mismo formato que detecta al abrir el archivo:

| Formato | Al guardar |
|---------|-----------|
| JSONL (ChatML, Alpaca, ShareGPT, raw) | Mismo formato JSONL |
| CSV | CSV con columnas `system`/`instruction`/`output` |
| TXT | Bloques `[SYSTEM]` / `[USER]` / `[CHAR]` |

El formato se detecta automáticamente al cargar. No necesitas especificarlo.

---

## Atajos de teclado

| Atajo | Acción |
|-------|--------|
| `Ctrl+S` | Guardar al disco |
| `Ctrl+F` | Abrir / cerrar barra de búsqueda |
| `↑ / ↓` en barra de búsqueda | Resultado anterior / siguiente |
