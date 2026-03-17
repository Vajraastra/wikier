# Guía de Temas QSS

Wikier usa hojas de estilo QSS (Qt Style Sheets) para sus temas visuales. Agregar un tema nuevo es tan simple como soltar un archivo `.qss` en la carpeta `themes/` — no hay que tocar ningún código.

---

## Temas incluidos

| Archivo | Nombre | Estilo |
|---------|--------|--------|
| `default.qss` | Oscuro (Catppuccin Mocha) | Oscuro cálido, morado/azul |
| `light.qss` | Claro (Catppuccin Latte) | Claro, tonos beige/lavanda |
| `cyberpunk.qss` | Cyberpunk 2077 | Oscuro extremo, neon amarillo/cyan |
| `nord.qss` | Nord | Polar Night, azul frío |
| `dracula.qss` | Dracula | Púrpura/rosa sobre fondo casi negro |

---

## Crear un tema nuevo

### 1. Estructura mínima del archivo

Cada `.qss` debe comenzar con un comentario especial que define el nombre visible en la GUI:

```css
/* display: Mi Tema */

QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: "Inter", "Segoe UI", sans-serif;
    font-size: 13px;
}
```

El texto después de `display:` es exactamente lo que aparece en el selector de temas. Sin este comentario, el archivo no se detecta.

### 2. Agregar el archivo

Guarda el archivo en `themes/tu_tema.qss`. El sistema lo detecta automáticamente al arrancar la app — no requiere ningún registro adicional.

---

## Variables de color (no hay variables nativas en QSS)

QSS no soporta variables CSS. La convención en este proyecto es definir los colores en comentarios al inicio del archivo para facilitar la edición:

```css
/* display: Mi Tema */
/*
  Paleta:
  bg-base:    #1e1e2e
  bg-surface: #313244
  bg-overlay: #45475a
  text:       #cdd6f4
  accent1:    #cba6f7   (morado)
  accent2:    #89b4fa   (azul)
  danger:     #f38ba8   (rojo)
  success:    #a6e3a1   (verde)
*/
```

---

## Selectores importantes

### Ventana y fondos

```css
QMainWindow, QDialog, QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
}

QFrame#sidebar {
    background-color: #181825;
    border-right: 1px solid #45475a;
}
```

### Botones

Los botones usan `property` para variantes de rol:

```css
/* Botón primario (acción principal) */
QPushButton[role="primary"] {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #cba6f7, stop:1 #9a86d9);
    color: #1e1e2e;
    border-radius: 6px;
    padding: 6px 16px;
    font-weight: bold;
}

/* Botón de peligro (eliminar, etc.) */
QPushButton[role="danger"] {
    background-color: #f38ba8;
    color: #1e1e2e;
}

/* Botón de navegación (back, nav) */
QPushButton[role="back"] {
    background: transparent;
    color: #cba6f7;
    border: none;
}
```

### Tarjetas del dashboard

```css
QFrame.module-card {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #313244, stop:1 #2a2a3d);
    border: 1px solid #45475a;
    border-radius: 12px;
}

QFrame.module-card:hover {
    border-left: 3px solid #cba6f7;
    background-color: #3b3b5c;
}
```

### Inputs

```css
QLineEdit, QTextEdit, QSpinBox, QComboBox {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 4px 8px;
}

QLineEdit:focus, QTextEdit:focus {
    border: 1px solid #cba6f7;
}
```

### Progress bar

```css
QProgressBar {
    background-color: #45475a;
    border-radius: 4px;
    text-align: center;
    color: #cdd6f4;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #cba6f7, stop:1 #89b4fa);
    border-radius: 4px;
}
```

### Tabla

```css
QTableWidget {
    background-color: #1e1e2e;
    alternate-background-color: #252535;
    gridline-color: #313244;
    color: #cdd6f4;
    border: none;
}

QHeaderView::section {
    background-color: #181825;
    color: #a6adc8;
    border: none;
    padding: 4px 8px;
    font-weight: bold;
}
```

### Paneles específicos del Editor y Ajustes

```css
/* Toolbar del editor */
QWidget#editor-toolbar {
    background-color: #181825;
    border-bottom: 1px solid #313244;
}

/* Barra de búsqueda */
QFrame#search-bar {
    background-color: #1e1e2e;
    border-bottom: 1px solid #45475a;
}

/* Footer del editor */
QFrame#editor-footer {
    background-color: #181825;
    border-top: 1px solid #313244;
}

/* Panel de ajustes */
QGroupBox#settings-appearance {
    border: 1px solid #45475a;
    border-radius: 8px;
    margin-top: 8px;
    padding-top: 8px;
}
```

---

## Tips

- **Hereda del tema activo**: si un selector no está en tu tema, Qt usa el estilo por defecto del sistema. Copia los selectores del `default.qss` como punto de partida para cobertura completa.
- **Prueba en caliente**: en la GUI puedes cambiar de tema sin reiniciar (desde Ajustes). Útil para iterar sobre colores rápidamente.
- **El tema se aplica a toda la app**: no es posible aplicar temas distintos a distintas ventanas. Un archivo = un tema global.
