"""
Vista de resultados de asistencia.

Combina la carga del archivo biométrico con la tabla de resultados y filtros.
Es la pantalla principal de la aplicación.
"""

from datetime import date, datetime
from typing import Optional

import pandas as pd
from PySide6.QtCore import Qt, Signal, QThread, QSortFilterProxyModel, QDate
from PySide6.QtGui import QStandardItemModel, QStandardItem, QColor, QBrush, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDateEdit,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from database.database import DatabaseManager
from database.models import Employee, Schedule
from services.attendance_engine import (
    PUNTUAL, TARDE, AUSENTE, ANTICIPADO, SIN_REGISTRO, ERROR, NO_APLICA,
    ESTADO_DISPLAY,
    AttendanceEngine,
    results_to_dataframe,
)
from services.excel_reader import read_biometric_excel
from services.report_generator import ReportGenerator
from ui.styles import COLORS


# ──────────────────────────────────────────────────────────────────────
# Colores de fondo para estados en la tabla (tonos sutiles de gris y blanco)
# ──────────────────────────────────────────────────────────────────────
ROW_COLORS = {
    PUNTUAL: QColor(255, 255, 255),
    TARDE: QColor(245, 245, 245),
    AUSENTE: QColor(230, 230, 230),
    ANTICIPADO: QColor(245, 245, 245),
    SIN_REGISTRO: QColor(240, 240, 240),
    ERROR: QColor(220, 220, 220),
    NO_APLICA: QColor(250, 250, 250),
}


class AnalysisWorker(QThread):
    """Worker thread para procesar la verificación de asistencia."""

    finished = Signal(pd.DataFrame)
    error = Signal(str)
    progress = Signal(int, str)  # (porcentaje, mensaje)

    def __init__(
        self,
        file_path: str,
        schedules: list[dict],
        tolerance: int,
    ) -> None:
        super().__init__()
        self.file_path = file_path
        self.schedules = schedules
        self.tolerance = tolerance

    def run(self) -> None:
        try:
            self.progress.emit(10, "Leyendo archivo biométrico...")
            biometric_df = read_biometric_excel(self.file_path)

            self.progress.emit(40, "Analizando registros...")
            engine = AttendanceEngine(tolerance_minutes=self.tolerance)
            results = engine.process(self.schedules, biometric_df, self.tolerance)

            self.progress.emit(75, "Generando tabla de resultados...")
            results_df = results_to_dataframe(results)

            self.progress.emit(100, "¡Análisis completado!")
            self.finished.emit(results_df)

        except Exception as e:
            self.error.emit(str(e))


class ResultsView(QWidget):
    """
    Vista principal de verificación y resultados de asistencia.
    
    Combina la zona de carga del archivo biométrico con los resultados
    filtrados y la exportación a Excel.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.db = DatabaseManager()
        self._worker: Optional[AnalysisWorker] = None
        self._results_df: Optional[pd.DataFrame] = None
        self._filtered_df: Optional[pd.DataFrame] = None
        self._current_filter: str = "Todos"
        self.setAcceptDrops(True)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Construye la interfaz de la vista de resultados."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 25, 30, 25)
        layout.setSpacing(16)

        # ── Encabezado ──
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        header_text = QVBoxLayout()
        header_text.setSpacing(4)

        title = QLabel("📊  Verificación de Asistencia")
        title.setProperty("class", "title")
        header_text.addWidget(title)

        subtitle = QLabel("Cargue el archivo biométrico para iniciar el análisis automático.")
        subtitle.setProperty("class", "subtitle")
        header_text.addWidget(subtitle)

        header_layout.addLayout(header_text)
        header_layout.addStretch()

        # Botón para cambiar de archivo (inicialmente oculto)
        self.btn_change_file = QPushButton("📂  Cargar otro archivo")
        self.btn_change_file.setProperty("class", "secondary")
        self.btn_change_file.setMinimumHeight(40)
        self.btn_change_file.setVisible(False)
        self.btn_change_file.clicked.connect(self._on_change_file_clicked)
        header_layout.addWidget(self.btn_change_file)

        # Botón de exportación (inicialmente oculto)
        self.btn_export = QPushButton("📥  Exportar a Excel")
        self.btn_export.setProperty("class", "success")
        self.btn_export.setMinimumHeight(40)
        self.btn_export.setMinimumWidth(160)
        self.btn_export.setVisible(False)
        self.btn_export.clicked.connect(self._on_export_clicked)
        header_layout.addWidget(self.btn_export)

        layout.addLayout(header_layout)

        # ── Zona de carga (Drop Zone) ──
        self.drop_zone = QFrame()
        self.drop_zone.setProperty("class", "drop-zone")
        self.drop_zone.setMinimumHeight(140)
        self.drop_zone.setMaximumHeight(180)

        drop_layout = QVBoxLayout(self.drop_zone)
        drop_layout.setAlignment(Qt.AlignCenter)
        drop_layout.setSpacing(10)

        drop_icon = QLabel("📂")
        drop_icon.setStyleSheet("font-size: 40px;")
        drop_icon.setAlignment(Qt.AlignCenter)
        drop_layout.addWidget(drop_icon)

        drop_text = QLabel("Arrastre un archivo Excel aquí o haga clic para seleccionar")
        drop_text.setStyleSheet("font-size: 14px; font-weight: 500;")
        drop_text.setAlignment(Qt.AlignCenter)
        drop_layout.addWidget(drop_text)

        drop_formats = QLabel("Formatos soportados: .xlsx, .xls")
        drop_formats.setProperty("class", "subtitle")
        drop_formats.setAlignment(Qt.AlignCenter)
        drop_layout.addWidget(drop_formats)

        self.btn_load = QPushButton("Seleccionar archivo")
        self.btn_load.setFixedWidth(200)
        self.btn_load.clicked.connect(self._on_load_clicked)
        drop_layout.addWidget(self.btn_load, alignment=Qt.AlignCenter)

        layout.addWidget(self.drop_zone)

        # ── Barra de progreso ──
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)

        self.progress_label = QLabel("")
        self.progress_label.setProperty("class", "subtitle")
        self.progress_label.setVisible(False)
        layout.addWidget(self.progress_label)

        # ── Tarjetas de resumen ──
        self.stats_widget = QWidget()
        self.stats_widget.setVisible(False)
        stats_layout = QHBoxLayout(self.stats_widget)
        stats_layout.setContentsMargins(0, 0, 0, 0)
        stats_layout.setSpacing(12)

        self.card_total = self._create_stat_card("0", "TOTAL", COLORS["text_primary"])
        self.card_puntuales = self._create_stat_card("0", "PUNTUALES", COLORS["text_primary"])
        self.card_tarde = self._create_stat_card("0", "TARDE", COLORS["text_secondary"])
        self.card_ausentes = self._create_stat_card("0", "AUSENTES", COLORS["text_primary"])
        self.card_anticipado = self._create_stat_card("0", "SAL. ANTICIPADA", COLORS["text_secondary"])
        self.card_sin_registro = self._create_stat_card("0", "SIN REGISTRO", COLORS["text_muted"])

        stats_layout.addWidget(self.card_total)
        stats_layout.addWidget(self.card_puntuales)
        stats_layout.addWidget(self.card_tarde)
        stats_layout.addWidget(self.card_ausentes)
        stats_layout.addWidget(self.card_anticipado)
        stats_layout.addWidget(self.card_sin_registro)
        stats_layout.addStretch()

        layout.addWidget(self.stats_widget)

        # ── Filtros ──
        self.filters_widget = QWidget()
        self.filters_widget.setVisible(False)
        filters_layout = QVBoxLayout(self.filters_widget)
        filters_layout.setContentsMargins(0, 0, 0, 0)
        filters_layout.setSpacing(10)

        # Fila 1: Chips de filtro rápido
        chips_layout = QHBoxLayout()
        chips_layout.setSpacing(8)

        self.filter_buttons: dict[str, QPushButton] = {}
        filters = [
            ("Todos", "Todos"),
            ("Puntuales", PUNTUAL),
            ("Tarde", TARDE),
            ("Ausentes", AUSENTE),
            ("Sal. Anticipada", ANTICIPADO),
            ("Sin Registro", SIN_REGISTRO),
            ("Errores", ERROR),
        ]
        for label, filter_key in filters:
            btn = QPushButton(label)
            btn.setProperty("class", "chip")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, k=filter_key: self._on_filter_chip_clicked(k))
            chips_layout.addWidget(btn)
            self.filter_buttons[filter_key] = btn

        # Activar "Todos" por defecto
        self.filter_buttons["Todos"].setChecked(True)
        self.filter_buttons["Todos"].setProperty("active", "true")
        self.filter_buttons["Todos"].style().unpolish(self.filter_buttons["Todos"])
        self.filter_buttons["Todos"].style().polish(self.filter_buttons["Todos"])

        chips_layout.addStretch()
        filters_layout.addLayout(chips_layout)

        # Fila 2: Filtros avanzados
        adv_layout = QHBoxLayout()
        adv_layout.setSpacing(12)

        # Búsqueda por empleado
        search_label = QLabel("🔍")
        search_label.setStyleSheet("font-size: 16px;")
        adv_layout.addWidget(search_label)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar empleado...")
        self.search_input.setMinimumWidth(200)
        self.search_input.setMaximumWidth(300)
        self.search_input.textChanged.connect(self._on_search_changed)
        adv_layout.addWidget(self.search_input)

        # ComboBox de empleado
        emp_label = QLabel("Empleado:")
        adv_layout.addWidget(emp_label)

        self.combo_empleado = QComboBox()
        self.combo_empleado.setMinimumWidth(200)
        self.combo_empleado.setMaximumWidth(300)
        self.combo_empleado.addItem("— Todos —")
        self.combo_empleado.currentTextChanged.connect(self._apply_filters)
        adv_layout.addWidget(self.combo_empleado)

        # ComboBox de municipio
        muni_label = QLabel("Municipio:")
        adv_layout.addWidget(muni_label)

        self.combo_municipio = QComboBox()
        self.combo_municipio.setMinimumWidth(150)
        self.combo_municipio.setMaximumWidth(200)
        self.combo_municipio.addItem("— Todos —")
        self.combo_municipio.currentTextChanged.connect(self._apply_filters)
        adv_layout.addWidget(self.combo_municipio)

        # Rango de fechas
        date_label = QLabel("Desde:")
        adv_layout.addWidget(date_label)

        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addMonths(-1))
        self.date_from.setMaximumWidth(140)
        self.date_from.dateChanged.connect(self._apply_filters)
        adv_layout.addWidget(self.date_from)

        date_to_label = QLabel("Hasta:")
        adv_layout.addWidget(date_to_label)

        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setMaximumWidth(140)
        self.date_to.dateChanged.connect(self._apply_filters)
        adv_layout.addWidget(self.date_to)

        adv_layout.addStretch()
        filters_layout.addLayout(adv_layout)

        layout.addWidget(self.filters_widget)

        # ── Tabla de resultados ──
        self.table = QTableView()
        self.table.setAlternatingRowColors(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setFixedHeight(38)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(34)
        self.table.setVisible(False)

        self.table_model = QStandardItemModel()
        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.table_model)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.table.setModel(self.proxy_model)

        layout.addWidget(self.table, stretch=1)

        # ── Label de conteo ──
        self.count_label = QLabel("")
        self.count_label.setProperty("class", "subtitle")
        self.count_label.setVisible(False)
        layout.addWidget(self.count_label)

    def _create_stat_card(self, value: str, label: str, color: str) -> QFrame:
        """Crea una tarjeta de estadística compacta con color."""
        card = QFrame()
        card.setProperty("class", "card")
        card.setFixedHeight(85)
        card.setMinimumWidth(140)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 8, 12, 8)
        card_layout.setSpacing(2)
        card_layout.setAlignment(Qt.AlignCenter)

        value_label = QLabel(value)
        value_label.setStyleSheet(f"font-size: 24px; font-weight: 700; color: {color};")
        value_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(value_label)

        name_label = QLabel(label)
        name_label.setProperty("class", "stat-label")
        name_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(name_label)

        card.value_label = value_label
        return card

    # ──────────────────────────────────────────────────────────────
    # Drag & Drop
    # ──────────────────────────────────────────────────────────────
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if any(u.toLocalFile().lower().endswith(('.xlsx', '.xls')) for u in urls):
                event.acceptProposedAction()
                self.drop_zone.setProperty("class", "drop-zone-active")
                self.drop_zone.style().unpolish(self.drop_zone)
                self.drop_zone.style().polish(self.drop_zone)

    def dragLeaveEvent(self, event) -> None:
        self.drop_zone.setProperty("class", "drop-zone")
        self.drop_zone.style().unpolish(self.drop_zone)
        self.drop_zone.style().polish(self.drop_zone)

    def dropEvent(self, event: QDropEvent) -> None:
        self.drop_zone.setProperty("class", "drop-zone")
        self.drop_zone.style().unpolish(self.drop_zone)
        self.drop_zone.style().polish(self.drop_zone)

        urls = event.mimeData().urls()
        for url in urls:
            file_path = url.toLocalFile()
            if file_path.lower().endswith(('.xlsx', '.xls')):
                self._start_analysis(file_path)
                return

    # ──────────────────────────────────────────────────────────────
    # Carga y análisis
    # ──────────────────────────────────────────────────────────────
    def _on_load_clicked(self) -> None:
        """Abre un diálogo para seleccionar el archivo biométrico."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar archivo biométrico",
            "",
            "Archivos Excel (*.xlsx *.xls);;Todos los archivos (*)",
        )
        if file_path:
            self._start_analysis(file_path)

    def _start_analysis(self, file_path: str) -> None:
        """Inicia el análisis de asistencia con el archivo proporcionado."""
        # Verificar que hay horarios cargados
        if self.db.get_employee_count() == 0:
            QMessageBox.warning(
                self,
                "Sin horarios",
                "No hay horarios cargados en el sistema.\n\n"
                "Vaya a 'Configuración de Horarios' para importar los horarios primero.",
            )
            return

        # Obtener horarios de la BD
        schedules = self._get_schedules_from_db()
        tolerance = self.db.get_tolerance()

        # Mostrar progreso
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_label.setVisible(True)
        self.btn_load.setEnabled(False)

        self._worker = AnalysisWorker(file_path, schedules, tolerance)
        self._worker.progress.connect(self._on_analysis_progress)
        self._worker.finished.connect(self._on_analysis_finished)
        self._worker.error.connect(self._on_analysis_error)
        self._worker.start()

    def _get_schedules_from_db(self) -> list[dict]:
        """Obtiene los horarios de la BD como lista de dicts para el engine."""
        schedules: list[dict] = []
        with self.db.get_session() as session:
            employees = session.query(Employee).filter_by(activo=True).all()
            for emp in employees:
                muni_name = emp.municipio.nombre if emp.municipio else ""
                for sched in emp.horarios:
                    schedules.append({
                        "codigo_empleado": emp.codigo_empleado,
                        "nombre": emp.nombre,
                        "municipio": muni_name,
                        "dia_semana": sched.dia_semana,
                        "hora_entrada_manana": sched.hora_entrada_manana,
                        "hora_salida_manana": sched.hora_salida_manana,
                        "hora_entrada_tarde": sched.hora_entrada_tarde,
                        "hora_salida_tarde": sched.hora_salida_tarde,
                        "jornada_continua": sched.jornada_continua,
                        "excepcion": sched.excepcion,
                        "tolerancia_minutos": sched.tolerancia_minutos,
                    })
        return schedules

    def _on_analysis_progress(self, percent: int, message: str) -> None:
        """Actualiza la barra de progreso durante el análisis."""
        self.progress_bar.setValue(percent)
        self.progress_label.setText(message)

    def _on_analysis_finished(self, results_df: pd.DataFrame) -> None:
        """Callback cuando el análisis finaliza exitosamente."""
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.btn_load.setEnabled(True)

        self._results_df = results_df
        self._filtered_df = results_df.copy()

        if results_df.empty:
            QMessageBox.information(
                self,
                "Sin resultados",
                "No se encontraron coincidencias entre los registros biométricos "
                "y los horarios cargados.\n\n"
                "Verifique que los códigos de empleado coincidan.",
            )
            return

        # Ocultar zona de carga previa y mostrar elementos de resultado
        self.drop_zone.setVisible(False)
        self.stats_widget.setVisible(True)
        self.filters_widget.setVisible(True)
        self.table.setVisible(True)
        self.count_label.setVisible(True)
        self.btn_export.setVisible(True)
        self.btn_change_file.setVisible(True)

        # Actualizar estadísticas
        self._update_stats(results_df)

        # Llenar ComboBox de empleados
        self._populate_employee_combo(results_df)

        # Actualizar rango de fechas
        self._update_date_range(results_df)

        # Mostrar datos en la tabla
        self._populate_table(results_df)

    def _on_analysis_error(self, error_msg: str) -> None:
        """Callback cuando el análisis falla."""
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.btn_load.setEnabled(True)
        QMessageBox.critical(
            self,
            "Error de análisis",
            f"No se pudo procesar el archivo:\n\n{error_msg}",
        )

    def _on_change_file_clicked(self) -> None:
        """Restaura la zona de carga amplia para seleccionar un nuevo archivo."""
        self.stats_widget.setVisible(False)
        self.filters_widget.setVisible(False)
        self.table.setVisible(False)
        self.count_label.setVisible(False)
        self.btn_export.setVisible(False)
        self.btn_change_file.setVisible(False)
        self.drop_zone.setVisible(True)

    # ──────────────────────────────────────────────────────────────
    # Estadísticas
    # ──────────────────────────────────────────────────────────────
    def _update_stats(self, df: pd.DataFrame) -> None:
        """Actualiza las tarjetas de estadísticas."""
        if "Estado" not in df.columns:
            return

        total = len(df)
        puntuales = (df["Estado"] == PUNTUAL).sum()
        tarde = (df["Estado"] == TARDE).sum()
        ausentes = (df["Estado"] == AUSENTE).sum()
        anticipado = (df["Estado"] == ANTICIPADO).sum()
        sin_registro = (df["Estado"] == SIN_REGISTRO).sum()

        self.card_total.value_label.setText(str(total))
        self.card_puntuales.value_label.setText(str(puntuales))
        self.card_tarde.value_label.setText(str(tarde))
        self.card_ausentes.value_label.setText(str(ausentes))
        self.card_anticipado.value_label.setText(str(anticipado))
        self.card_sin_registro.value_label.setText(str(sin_registro))

    def _populate_employee_combo(self, df: pd.DataFrame) -> None:
        """Llena el ComboBox de empleados y municipios."""
        self.combo_empleado.blockSignals(True)
        self.combo_empleado.clear()
        self.combo_empleado.addItem("— Todos —")
        if "Empleado" in df.columns:
            empleados = sorted(df["Empleado"].unique())
            for emp in empleados:
                self.combo_empleado.addItem(str(emp))
        self.combo_empleado.blockSignals(False)

        self.combo_municipio.blockSignals(True)
        self.combo_municipio.clear()
        self.combo_municipio.addItem("— Todos —")
        
        # Poblar municipios directamente desde la base de datos para mostrar todos
        try:
            from database.models import Municipio
            with self.db.get_session() as session:
                munis = session.query(Municipio.nombre).all()
                municipios = [m[0] for m in munis if m[0] and str(m[0]).strip()]
                for muni in sorted(municipios):
                    self.combo_municipio.addItem(str(muni))
        except Exception:
            # Fallback a los datos del DataFrame si hay error
            if "Municipio" in df.columns:
                municipios = [m for m in df["Municipio"].unique() if m and str(m).strip()]
                for muni in sorted(municipios):
                    self.combo_municipio.addItem(str(muni))
                    
        self.combo_municipio.blockSignals(False)

    def _update_date_range(self, df: pd.DataFrame) -> None:
        """Actualiza los DateEdit con el rango de fechas de los datos."""
        if "Fecha" in df.columns and not df.empty:
            fechas = pd.to_datetime(df["Fecha"])
            min_date = fechas.min()
            max_date = fechas.max()

            self.date_from.blockSignals(True)
            self.date_to.blockSignals(True)
            self.date_from.setDate(QDate(min_date.year, min_date.month, min_date.day))
            self.date_to.setDate(QDate(max_date.year, max_date.month, max_date.day))
            self.date_from.blockSignals(False)
            self.date_to.blockSignals(False)

    # ──────────────────────────────────────────────────────────────
    # Tabla
    # ──────────────────────────────────────────────────────────────
    def _populate_table(self, df: pd.DataFrame) -> None:
        """Llena la tabla con los datos del DataFrame."""
        self.table_model.clear()

        if df.empty:
            self.count_label.setText("Sin resultados")
            return

        # Columnas visibles (excluir internas)
        visible_cols = [c for c in df.columns if not c.startswith("_")]
        self.table_model.setHorizontalHeaderLabels(visible_cols)

        for _, row in df.iterrows():
            items = []
            estado = row.get("Estado", "")

            for col in visible_cols:
                value = row[col]
                if isinstance(value, date):
                    text = value.strftime("%d/%m/%Y") if hasattr(value, 'strftime') else str(value)
                else:
                    text = str(value) if value is not None else "—"

                item = QStandardItem(text)
                item.setTextAlignment(Qt.AlignCenter)
                item.setForeground(QBrush(QColor(17, 24, 39)))

                # Color de fondo por estado general de la fila
                if estado in ROW_COLORS:
                    item.setBackground(QBrush(ROW_COLORS[estado]))

                # Color de fondo específico si es una celda 'Real'
                if col.endswith(" Real"):
                    display_name = col.replace(" Real", "")
                    estado_col = f"_{display_name}_estado"
                    if estado_col in df.columns:
                        cell_estado = row.get(estado_col)
                        
                        # Si llegó tarde, pintar de rojo (siempre)
                        if cell_estado == TARDE:
                            item.setBackground(QBrush(QColor(254, 226, 226)))
                            item.setForeground(QBrush(QColor(185, 28, 28)))
                            
                        # Si estamos en la tabla de Ausentes, diferenciar las celdas faltantes (la jornada ausente)
                        if self._current_filter == "Ausentes" and cell_estado in (AUSENTE, SIN_REGISTRO) and value in ("—", None, ""):
                            # Fondo naranja suave para indicar el registro faltante que causó la ausencia
                            item.setBackground(QBrush(QColor(255, 237, 213)))
                            item.setForeground(QBrush(QColor(154, 52, 18)))

                items.append(item)

            self.table_model.appendRow(items)

        # Ajustar columnas
        header = self.table.horizontalHeader()
        for i in range(len(visible_cols)):
            if i < len(visible_cols) - 1:
                header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
            else:
                header.setSectionResizeMode(i, QHeaderView.Stretch)

        self.count_label.setText(f"Mostrando {len(df)} registros")

    # ──────────────────────────────────────────────────────────────
    # Filtros
    # ──────────────────────────────────────────────────────────────
    def _on_filter_chip_clicked(self, filter_key: str) -> None:
        """Maneja el clic en un chip de filtro."""
        # Desactivar todos
        for key, btn in self.filter_buttons.items():
            btn.setChecked(key == filter_key)
            btn.setProperty("active", "true" if key == filter_key else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        self._current_filter = filter_key
        self._apply_filters()

    def _on_search_changed(self, text: str) -> None:
        """Filtra por búsqueda de texto en la columna de empleado."""
        self.proxy_model.setFilterKeyColumn(0)  # Columna "Empleado"
        self.proxy_model.setFilterFixedString(text)
        self._update_count_label()



    def _apply_filters(self) -> None:
        """Aplica todos los filtros activos y actualiza la tabla."""
        if self._results_df is None or self._results_df.empty:
            return

        df = self._results_df.copy()

        # Filtro por estado
        if self._current_filter != "Todos":
            df = df[df["Estado"] == self._current_filter]

        # Filtro por empleado
        emp_filter = self.combo_empleado.currentText()
        if emp_filter and emp_filter != "— Todos —" and "Empleado" in df.columns:
            df = df[df["Empleado"] == emp_filter]

        # Filtro por municipio
        muni_filter = self.combo_municipio.currentText()
        if muni_filter and muni_filter != "— Todos —" and "Municipio" in df.columns:
            df = df[df["Municipio"] == muni_filter]

        # Filtro por rango de fechas
        if "Fecha" in df.columns and not df.empty:
            from_date = self.date_from.date().toPython()
            to_date = self.date_to.date().toPython()
            df = df[
                (pd.to_datetime(df["Fecha"]).dt.date >= from_date)
                & (pd.to_datetime(df["Fecha"]).dt.date <= to_date)
            ]

        self._filtered_df = df
        self._populate_table(df)
        self._update_stats(df)

    def _update_count_label(self) -> None:
        """Actualiza el label de conteo de registros filtrados."""
        visible_rows = self.proxy_model.rowCount()
        self.count_label.setText(f"Mostrando {visible_rows} registros")

    # ──────────────────────────────────────────────────────────────
    # Exportación
    # ──────────────────────────────────────────────────────────────
    def _on_export_clicked(self) -> None:
        """Exporta los resultados filtrados a Excel."""
        if self._filtered_df is None or self._filtered_df.empty:
            QMessageBox.warning(self, "Sin datos", "No hay datos para exportar.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar reporte de asistencia",
            f"reporte_asistencia_{date.today().strftime('%Y%m%d')}.xlsx",
            "Archivos Excel (*.xlsx)",
        )
        if not file_path:
            return

        try:
            generator = ReportGenerator()
            output = generator.export_to_excel(
                self._filtered_df,
                file_path,
                title=f"Reporte de Asistencia — {self._current_filter}",
            )
            QMessageBox.information(
                self,
                "Exportación exitosa",
                f"El reporte se ha guardado en:\n\n{output}",
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error de exportación",
                f"No se pudo exportar el reporte:\n\n{str(e)}",
            )
