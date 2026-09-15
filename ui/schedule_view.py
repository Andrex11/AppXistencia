"""
Vista de configuración de horarios.

Permite importar, visualizar, reemplazar y eliminar horarios de empleados,
así como configurar la tolerancia global.
"""

from typing import Optional

from PySide6.QtCore import Qt, Signal, QThread, QSortFilterProxyModel, QRegularExpression
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTableView,
    QVBoxLayout,
    QWidget,
    QAbstractItemView,
    QLineEdit,
)
from PySide6.QtGui import QStandardItemModel, QStandardItem

from database.database import DatabaseManager
from database.models import Employee, Schedule, Municipio
from services.excel_reader import read_schedule_excel


class ImportWorker(QThread):
    """Worker thread para importar horarios sin bloquear la UI."""

    finished = Signal(list)  # Lista de datos importados
    error = Signal(str)
    progress = Signal(int)

    def __init__(self, file_path: str) -> None:
        super().__init__()
        self.file_path = file_path

    def run(self) -> None:
        try:
            self.progress.emit(30)
            data = read_schedule_excel(self.file_path)
            self.progress.emit(70)
            self.finished.emit(data)
        except Exception as e:
            self.error.emit(str(e))


class ScheduleView(QWidget):
    """Vista de configuración de horarios de empleados."""

    schedules_updated = Signal()  # Emitida cuando los horarios cambian

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.db = DatabaseManager()
        self._worker: Optional[ImportWorker] = None
        self._setup_ui()
        self._load_current_data()

    def _setup_ui(self) -> None:
        """Construye la interfaz de la vista de horarios."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 25, 30, 25)
        layout.setSpacing(20)

        # ── Encabezado ──
        header = QVBoxLayout()
        header.setSpacing(4)

        title = QLabel("⚙️  Configuración de Horarios")
        title.setProperty("class", "title")
        header.addWidget(title)

        subtitle = QLabel("Importe los horarios desde un archivo Excel y configure la tolerancia global.")
        subtitle.setProperty("class", "subtitle")
        header.addWidget(subtitle)

        layout.addLayout(header)

        # ── Tarjetas de estadísticas ──
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(16)

        self.card_empleados = self._create_stat_card("0", "EMPLEADOS")
        self.card_horarios = self._create_stat_card("0", "HORARIOS")
        self.card_tolerancia = self._create_stat_card("2 min", "TOLERANCIA GLOBAL")

        stats_layout.addWidget(self.card_empleados)
        stats_layout.addWidget(self.card_horarios)
        stats_layout.addWidget(self.card_tolerancia)
        stats_layout.addStretch()

        layout.addLayout(stats_layout)

        # ── Barra de acciones ──
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(12)

        self.btn_import = QPushButton("📂  Importar Archivos de Horarios")
        self.btn_import.setMinimumHeight(44)
        self.btn_import.setMinimumWidth(260)
        self.btn_import.clicked.connect(self._on_import_clicked)
        actions_layout.addWidget(self.btn_import)

        self.btn_replace = QPushButton("🔄  Reemplazar Horarios")
        self.btn_replace.setProperty("class", "secondary")
        self.btn_replace.setMinimumHeight(44)
        self.btn_replace.clicked.connect(self._on_replace_clicked)
        self.btn_replace.setEnabled(False)
        actions_layout.addWidget(self.btn_replace)

        self.btn_delete = QPushButton("🗑️  Eliminar Horarios")
        self.btn_delete.setProperty("class", "danger")
        self.btn_delete.setMinimumHeight(44)
        self.btn_delete.clicked.connect(self._on_delete_clicked)
        actions_layout.addWidget(self.btn_delete)

        actions_layout.addStretch()

        layout.addLayout(actions_layout)

        # ── Barra de progreso ──
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)

        # ── Sección de tolerancia ──
        tol_frame = QFrame()
        tol_frame.setProperty("class", "card")
        tol_layout = QHBoxLayout(tol_frame)
        tol_layout.setContentsMargins(16, 12, 16, 12)

        tol_label = QLabel("🕐  Tolerancia global (minutos):")
        tol_label.setStyleSheet("font-size: 14px; font-weight: 500;")
        tol_layout.addWidget(tol_label)

        self.spin_tolerancia = QSpinBox()
        self.spin_tolerancia.setRange(0, 60)
        self.spin_tolerancia.setValue(self.db.get_tolerance())
        self.spin_tolerancia.setFixedWidth(80)
        self.spin_tolerancia.setAlignment(Qt.AlignCenter)
        tol_layout.addWidget(self.spin_tolerancia)

        self.btn_save_tol = QPushButton("💾  Guardar")
        self.btn_save_tol.setProperty("class", "success")
        self.btn_save_tol.setFixedWidth(120)
        self.btn_save_tol.clicked.connect(self._on_save_tolerance)
        tol_layout.addWidget(self.btn_save_tol)

        tol_layout.addStretch()
        layout.addWidget(tol_frame)

        # ── Tabla de preview ──
        table_header_layout = QHBoxLayout()
        table_label = QLabel("📋  Horarios cargados")
        table_label.setStyleSheet("font-size: 15px; font-weight: 600; margin-top: 5px;")
        table_header_layout.addWidget(table_label)
        
        table_header_layout.addStretch()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Buscar empleado...")
        self.search_input.setFixedWidth(250)
        self.search_input.textChanged.connect(self._on_search_changed)
        table_header_layout.addWidget(self.search_input)
        
        layout.addLayout(table_header_layout)

        self.table = QTableView()
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setFixedHeight(38)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(34)

        self.model = QStandardItemModel()
        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.proxy_model.setFilterKeyColumn(0)  # Columna 0 es Empleado
        self.table.setModel(self.proxy_model)

        layout.addWidget(self.table, stretch=1)

        # Datos temporales para reemplazo
        self._pending_data: list[dict] = []

    def _on_search_changed(self, text: str) -> None:
        """Filtra la tabla según el texto ingresado en el buscador."""
        # Se usa QRegularExpression para filtrar ignorando mayúsculas y acentos (básico)
        regex = QRegularExpression(text, QRegularExpression.PatternOption.CaseInsensitiveOption)
        self.proxy_model.setFilterRegularExpression(regex)

    def _create_stat_card(self, value: str, label: str) -> QFrame:
        """Crea una tarjeta de estadística con valor y etiqueta."""
        card = QFrame()
        card.setProperty("class", "card")
        card.setMinimumWidth(190)
        card.setFixedHeight(85)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 8, 12, 8)
        card_layout.setSpacing(2)
        card_layout.setAlignment(Qt.AlignCenter)

        value_label = QLabel(value)
        value_label.setProperty("class", "stat-value")
        value_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(value_label)

        name_label = QLabel(label)
        name_label.setProperty("class", "stat-label")
        name_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(name_label)

        # Guardar referencia al label del valor para actualizarlo
        card.value_label = value_label
        return card

    def _load_current_data(self) -> None:
        """Carga los datos actuales de la BD en la tabla y las tarjetas."""
        emp_count = self.db.get_employee_count()
        sched_count = self.db.get_schedule_count()
        tolerance = self.db.get_tolerance()

        self.card_empleados.value_label.setText(str(emp_count))
        self.card_horarios.value_label.setText(str(sched_count))
        self.card_tolerancia.value_label.setText(f"{tolerance} min")
        self.spin_tolerancia.setValue(tolerance)

        # Cargar tabla
        self._populate_table_from_db()

    def _populate_table_from_db(self) -> None:
        """Llena la tabla con los horarios de la BD."""
        self.model.clear()
        self.model.setHorizontalHeaderLabels([
            "Empleado", "Código", "Municipio", "Día", "Ent. Mañana", "Sal. Mañana",
            "Ent. Tarde", "Sal. Tarde", "Jornada Cont.", "Excepción",
        ])

        days = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

        with self.db.get_session() as session:
            employees = session.query(Employee).filter_by(activo=True).all()
            for emp in employees:
                muni_name = emp.municipio.nombre if emp.municipio else "—"
                for sched in emp.horarios:
                    row = [
                        QStandardItem(emp.nombre),
                        QStandardItem(emp.codigo_empleado),
                        QStandardItem(muni_name),
                        QStandardItem(days[sched.dia_semana] if sched.dia_semana < len(days) else "?"),
                        QStandardItem(sched.hora_entrada_manana.strftime("%H:%M") if sched.hora_entrada_manana else "—"),
                        QStandardItem(sched.hora_salida_manana.strftime("%H:%M") if sched.hora_salida_manana else "—"),
                        QStandardItem(sched.hora_entrada_tarde.strftime("%H:%M") if sched.hora_entrada_tarde else "—"),
                        QStandardItem(sched.hora_salida_tarde.strftime("%H:%M") if sched.hora_salida_tarde else "—"),
                        QStandardItem("Sí" if sched.jornada_continua else "No"),
                        QStandardItem(sched.excepcion or "—"),
                    ]
                    for item in row:
                        item.setTextAlignment(Qt.AlignCenter)
                    self.model.appendRow(row)

        # Ajustar columnas
        header = self.table.horizontalHeader()
        for i in range(self.model.columnCount()):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        if self.model.columnCount() > 0:
            header.setSectionResizeMode(self.model.columnCount() - 1, QHeaderView.Stretch)

    def _on_import_clicked(self) -> None:
        """Maneja el clic en 'Importar Excel de Horarios'."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar archivo de horarios",
            "",
            "Archivos de Horario (*.csv *.xlsx *.xls);;Archivos CSV (*.csv);;Archivos Excel (*.xlsx *.xls);;Todos los archivos (*)",
        )
        if not file_path:
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(10)
        self.btn_import.setEnabled(False)

        self._worker = ImportWorker(file_path)
        self._worker.progress.connect(self.progress_bar.setValue)
        self._worker.finished.connect(self._on_import_finished)
        self._worker.error.connect(self._on_import_error)
        self._worker.start()

    def _on_import_finished(self, data: list[dict]) -> None:
        """Callback cuando la importación finaliza exitosamente."""
        self.progress_bar.setValue(100)
        self.btn_import.setEnabled(True)

        if not data:
            QMessageBox.warning(self, "Sin datos", "No se encontraron horarios en el archivo.")
            self.progress_bar.setVisible(False)
            return

        self._pending_data = data

        # Guardar en BD
        self._save_schedules_to_db(data)

        self.progress_bar.setVisible(False)
        self._load_current_data()
        self.btn_replace.setEnabled(True)
        self.schedules_updated.emit()

        QMessageBox.information(
            self,
            "Importación exitosa",
            f"Se importaron los horarios de {len(data)} empleados correctamente.",
        )

    def _on_import_error(self, error_msg: str) -> None:
        """Callback cuando la importación falla."""
        self.progress_bar.setVisible(False)
        self.btn_import.setEnabled(True)
        QMessageBox.critical(
            self,
            "Error de importación",
            f"No se pudo importar el archivo:\n\n{error_msg}",
        )

    def _save_schedules_to_db(self, data: list[dict]) -> None:
        """Guarda los datos de horarios importados en la base de datos."""
        # Limpiar datos previos
        self.db.reset_schedules()

        with self.db.get_session() as session:
            municipios_cache = {}

            for emp_data in data:
                muni_name = emp_data.get("municipio", "").strip()
                muni_id = None

                if muni_name:
                    if muni_name not in municipios_cache:
                        muni_obj = session.query(Municipio).filter_by(nombre=muni_name).first()
                        if not muni_obj:
                            muni_obj = Municipio(nombre=muni_name)
                            session.add(muni_obj)
                            session.flush()
                        municipios_cache[muni_name] = muni_obj.id
                    muni_id = municipios_cache[muni_name]

                # Crear empleado
                employee = Employee(
                    codigo_empleado=str(emp_data["codigo_empleado"]),
                    nombre=emp_data["nombre"],
                    activo=True,
                    municipio_id=muni_id,
                )
                session.add(employee)
                session.flush()  # Obtener el ID

                # Crear horarios
                for horario in emp_data.get("horarios", []):
                    schedule = Schedule(
                        empleado_id=employee.id,
                        dia_semana=horario["dia_semana"],
                        hora_entrada_manana=horario.get("hora_entrada_manana"),
                        hora_salida_manana=horario.get("hora_salida_manana"),
                        hora_entrada_tarde=horario.get("hora_entrada_tarde"),
                        hora_salida_tarde=horario.get("hora_salida_tarde"),
                        jornada_continua=horario.get("jornada_continua", False),
                        excepcion=horario.get("excepcion"),
                    )
                    session.add(schedule)

            session.commit()

    def _on_replace_clicked(self) -> None:
        """Maneja el clic en 'Reemplazar Horarios'."""
        reply = QMessageBox.question(
            self,
            "Confirmar reemplazo",
            "¿Está seguro de que desea reemplazar todos los horarios?\n\n"
            "Esta acción eliminará los horarios existentes y los reemplazará "
            "con los datos del último archivo importado.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            if self._pending_data:
                self._save_schedules_to_db(self._pending_data)
                self._load_current_data()
                self.schedules_updated.emit()
                QMessageBox.information(self, "Reemplazo exitoso", "Los horarios han sido reemplazados.")
            else:
                QMessageBox.warning(self, "Sin datos", "No hay datos pendientes para reemplazar. Importe un archivo primero.")

    def _on_delete_clicked(self) -> None:
        """Maneja el clic en 'Eliminar Horarios'."""
        reply = QMessageBox.warning(
            self,
            "Confirmar eliminación",
            "⚠️ ¿Está seguro de que desea ELIMINAR todos los horarios?\n\n"
            "Esta acción no se puede deshacer.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.db.reset_schedules()
            self._pending_data = []
            self._load_current_data()
            self.btn_replace.setEnabled(False)
            self.schedules_updated.emit()
            QMessageBox.information(self, "Eliminación exitosa", "Todos los horarios han sido eliminados.")

    def _on_save_tolerance(self) -> None:
        """Guarda la tolerancia global."""
        value = self.spin_tolerancia.value()
        self.db.set_tolerance(value)
        self.card_tolerancia.value_label.setText(f"{value} min")
        QMessageBox.information(
            self,
            "Tolerancia actualizada",
            f"La tolerancia global se ha establecido en {value} minutos.",
        )
