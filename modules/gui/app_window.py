"""
AppWindow: ventana raíz de la aplicación.

Gestiona la navegación entre el dashboard y los módulos usando un
QStackedWidget. Los módulos se instancian de forma lazy (solo cuando
el usuario los abre por primera vez).

Flujo:
    AppWindow
    └── QStackedWidget
        ├── [0] DashboardPanel     ← pantalla inicial
        └── [1] ScraperWidget      ← instanciado al primer uso
        └── [N] FuturemoduloWidget ← idem
"""
from PySide6.QtCore    import Qt
from PySide6.QtWidgets import QMainWindow, QStackedWidget

from modules.core.i18n     import t
from modules.gui.dashboard import DashboardPanel


class AppWindow(QMainWindow):
    """
    Ventana principal de Wikier.

    Contiene el dashboard y todos los módulos en un QStackedWidget.
    El módulo activo se muestra al frente; el botón "← Módulos" de
    cada módulo llama a show_dashboard() para volver.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle(t("app.name"))
        self.setMinimumSize(960, 640)

        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)

        # Módulos cargados (lazy init)
        self._module_widgets: dict[str, object] = {}

        # Dashboard siempre en índice 0
        self._dashboard = DashboardPanel()
        self._dashboard.module_selected.connect(self._open_module)
        self._stack.addWidget(self._dashboard)

        self.statusBar().showMessage(t("status.ready"))

    # ── Navegación ────────────────────────────────────────────────────────────

    def _open_module(self, module_id: str) -> None:
        """
        Abre el widget del módulo indicado.
        Si es la primera vez, lo instancia y lo agrega al stack.
        """
        if module_id not in self._module_widgets:
            widget = self._create_module_widget(module_id)
            if widget is None:
                return
            self._module_widgets[module_id] = widget
            self._stack.addWidget(widget)

        self._stack.setCurrentWidget(self._module_widgets[module_id])
        self.statusBar().showMessage(t(f"module.{module_id}.name"))

    def show_dashboard(self) -> None:
        """Vuelve al dashboard desde cualquier módulo."""
        self._stack.setCurrentIndex(0)
        self.statusBar().showMessage(t("status.ready"))

    # ── Factory de módulos ────────────────────────────────────────────────────

    def _create_module_widget(self, module_id: str):
        """
        Instancia el widget del módulo. Retorna None si el ID no existe.

        Para agregar un nuevo módulo en el futuro:
            1. Implementar su widget en modules/gui/
            2. Agregar un caso aquí con su module_id
        """
        if module_id == "scraper":
            from modules.gui.main_window import ScraperWidget
            widget = ScraperWidget()
            widget.back_requested.connect(self.show_dashboard)
            return widget

        if module_id == "curator":
            from modules.gui.curator_window import CuratorWidget
            widget = CuratorWidget()
            widget.back_requested.connect(self.show_dashboard)
            return widget

        if module_id == "joiner":
            from modules.gui.joiner_window import JoinerWidget
            widget = JoinerWidget()
            widget.back_requested.connect(self.show_dashboard)
            return widget

        if module_id == "editor":
            from modules.gui.editor_window import EditorWidget
            widget = EditorWidget()
            widget.back_requested.connect(self.show_dashboard)
            return widget

        if module_id == "settings":
            from modules.gui.panels.settings_panel import SettingsPanel
            widget = SettingsPanel()
            widget.back_requested.connect(self.show_dashboard)
            return widget

        return None
