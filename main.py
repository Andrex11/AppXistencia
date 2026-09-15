"""
Punto de entrada de la aplicación de Control de Asistencia.

Inicializa la base de datos, aplica el tema visual y lanza la ventana principal.
"""

import sys
import os

# Agregar el directorio del proyecto al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from database.database import DatabaseManager
from ui.main_window import MainWindow
from ui.styles import get_main_stylesheet


def main() -> None:
    """Función principal de la aplicación."""
    # Habilitar High DPI scaling
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"

    app = QApplication(sys.argv)
    app.setApplicationName("Control de Asistencia")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Asistencia App")

    # Aplicar stylesheet personalizado (tema monocromático claro: blanco, gris y texto negro)
    app.setStyleSheet(get_main_stylesheet())

    # Inicializar base de datos
    DatabaseManager()

    # Crear y mostrar ventana principal
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
