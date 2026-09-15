"""
Ventana principal de la aplicación de control de asistencia.

Contiene la barra lateral de navegación y el QStackedWidget
para alternar entre las vistas de verificación y configuración.
"""

from typing import Optional

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from database.database import DatabaseManager
from ui.results_view import ResultsView
from ui.schedule_view import ScheduleView


class MainWindow(QMainWindow):
    """
    Ventana principal con barra lateral de navegación y vistas apiladas.
    
    La barra lateral tiene 2 botones principales:
    - Verificar Asistencia (vista principal/resultados)
    - Configuración de Horarios
    """

    def __init__(self) -> None:
        super().__init__()
        self.db = DatabaseManager()
        self._setup_window()
        self._setup_ui()
        self._setup_statusbar()

    def _setup_window(self) -> None:
        """Configura las propiedades de la ventana."""
        self.setWindowTitle("Control de Asistencia — Verificación Biométrica")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)

    def _setup_ui(self) -> None:
        """Construye la interfaz principal."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Sidebar ──
        sidebar = self._create_sidebar()
        main_layout.addWidget(sidebar)

        # ── Contenido principal (Stacked Widget) ──
        self.stack = QStackedWidget()

        # Vista 0: Verificación de Asistencia (principal)
        self.results_view = ResultsView()
        self.stack.addWidget(self.results_view)

        # Vista 1: Configuración de Horarios
        self.schedule_view = ScheduleView()
        self.schedule_view.schedules_updated.connect(self._on_schedules_updated)
        self.stack.addWidget(self.schedule_view)

        main_layout.addWidget(self.stack, stretch=1)

        # Activar vista principal
        self.stack.setCurrentIndex(0)

    def _create_sidebar(self) -> QFrame:
        """Crea la barra lateral de navegación."""
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(230)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Logo / Título ──
        title = QLabel("📋 Asistencia")
        title.setObjectName("appTitle")
        layout.addWidget(title)

        subtitle = QLabel("Control y Verificación")
        subtitle.setObjectName("appSubtitle")
        layout.addWidget(subtitle)

        # ── Separador ──
        sep = QFrame()
        sep.setProperty("class", "separator")
        sep.setFixedHeight(1)
        layout.addWidget(sep)

        layout.addSpacing(10)

        # ── Botones de navegación ──
        self.nav_buttons: list[QPushButton] = []

        nav_items = [
            ("📊  Verificar Asistencia", 0),
            ("⚙️  Configuración Horarios", 1),
        ]

        for label, index in nav_items:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setMinimumHeight(48)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, idx=index: self._navigate_to(idx))
            layout.addWidget(btn)
            self.nav_buttons.append(btn)

        # Activar el primer botón
        self.nav_buttons[0].setChecked(True)
        self.nav_buttons[0].setProperty("active", "true")

        layout.addStretch()

        # ── Info en el footer del sidebar ──
        footer_sep = QFrame()
        footer_sep.setProperty("class", "separator")
        footer_sep.setFixedHeight(1)
        layout.addWidget(footer_sep)

        version_label = QLabel("v1.0.0")
        version_label.setProperty("class", "subtitle")
        version_label.setAlignment(Qt.AlignCenter)
        version_label.setStyleSheet("padding: 12px; font-size: 10px; color: #6b7280;")
        layout.addWidget(version_label)

        return sidebar

    def _navigate_to(self, index: int) -> None:
        """Navega a la vista indicada por el índice."""
        self.stack.setCurrentIndex(index)

        # Actualizar estado visual de botones
        for i, btn in enumerate(self.nav_buttons):
            is_active = (i == index)
            btn.setChecked(is_active)
            btn.setProperty("active", "true" if is_active else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _setup_statusbar(self) -> None:
        """Configura la barra de estado inferior."""
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)

        # Indicadores
        emp_count = self.db.get_employee_count()
        tolerance = self.db.get_tolerance()

        self.status_emp_label = QLabel(f"👥 Empleados: {emp_count}")
        self.status_tol_label = QLabel(f"🕐 Tolerancia: {tolerance} min")
        self.status_db_label = QLabel("💾 BD: Conectada")

        status_bar.addWidget(self.status_emp_label)
        status_bar.addWidget(self.status_tol_label)
        status_bar.addPermanentWidget(self.status_db_label)

    def _on_schedules_updated(self) -> None:
        """Callback cuando los horarios son actualizados."""
        emp_count = self.db.get_employee_count()
        tolerance = self.db.get_tolerance()
        self.status_emp_label.setText(f"👥 Empleados: {emp_count}")
        self.status_tol_label.setText(f"🕐 Tolerancia: {tolerance} min")
