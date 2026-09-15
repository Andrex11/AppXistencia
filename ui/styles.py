"""
Estilos QSS para la aplicación de control de asistencia.

Tema minimalista monocromático en tonalidades blanco, gris y texto negro.
"""

# ──────────────────────────────────────────────────────────────────────
# Paleta de colores
# ──────────────────────────────────────────────────────────────────────
COLORS = {
    # Fondos principales (blancos y grises)
    "bg_primary": "#f8f9fa",
    "bg_secondary": "#ffffff",
    "bg_card": "#ffffff",
    "bg_sidebar": "#f1f3f5",
    "bg_input": "#ffffff",
    "bg_hover": "#e9ecef",
    "bg_selected": "#e2e6ea",

    # Texto (negro y grises oscuros)
    "text_primary": "#111827",
    "text_secondary": "#374151",
    "text_muted": "#6b7280",
    "text_disabled": "#9ca3af",

    # Acentos (carbón y gris oscuro)
    "accent_primary": "#1f2937",
    "accent_secondary": "#374151",
    "accent_glow": "#111827",

    # Estados (tonos neutros de gris/carbón)
    "success": "#1f2937",
    "success_bg": "#f3f4f6",
    "warning": "#374151",
    "warning_bg": "#e5e7eb",
    "error": "#111827",
    "error_bg": "#d1d5db",
    "info": "#4b5563",
    "info_bg": "#f3f4f6",
    "anticipado": "#374151",
    "anticipado_bg": "#e5e7eb",
    "sin_registro": "#4b5563",
    "sin_registro_bg": "#f3f4f6",

    # Bordes
    "border": "#e5e7eb",
    "border_focus": "#111827",

    # Scrollbar
    "scrollbar_bg": "#f8f9fa",
    "scrollbar_handle": "#d1d5db",
}


def get_main_stylesheet() -> str:
    """Retorna el stylesheet QSS principal para la aplicación."""
    c = COLORS
    return f"""
    /* ═══════════════════════════════════════════════════════════════
       VENTANA PRINCIPAL
       ═══════════════════════════════════════════════════════════════ */
    QMainWindow {{
        background-color: {c['bg_primary']};
        color: {c['text_primary']};
    }}

    QWidget {{
        font-family: 'Segoe UI', 'Roboto', 'Arial', sans-serif;
        font-size: 13px;
        color: {c['text_primary']};
    }}

    /* ═══════════════════════════════════════════════════════════════
       SIDEBAR
       ═══════════════════════════════════════════════════════════════ */
    #sidebar {{
        background-color: {c['bg_sidebar']};
        border-right: 1px solid {c['border']};
        min-width: 220px;
        max-width: 220px;
    }}

    #sidebar QPushButton {{
        background-color: transparent;
        color: {c['text_secondary']};
        border: none;
        border-radius: 8px;
        padding: 14px 18px;
        text-align: left;
        font-size: 14px;
        font-weight: 500;
        margin: 3px 10px;
    }}

    #sidebar QPushButton:hover {{
        background-color: {c['bg_hover']};
        color: {c['text_primary']};
    }}

    #sidebar QPushButton:checked,
    #sidebar QPushButton[active="true"] {{
        background-color: {c['accent_primary']};
        color: white;
        font-weight: 600;
    }}

    #appTitle {{
        color: {c['accent_glow']};
        font-size: 18px;
        font-weight: 700;
        padding: 20px 18px 10px 18px;
    }}

    #appSubtitle {{
        color: {c['text_muted']};
        font-size: 11px;
        padding: 0px 18px 20px 18px;
    }}

    /* ═══════════════════════════════════════════════════════════════
       BOTONES GENERALES
       ═══════════════════════════════════════════════════════════════ */
    QPushButton {{
        background-color: {c['accent_primary']};
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px 24px;
        font-size: 13px;
        font-weight: 600;
        min-height: 20px;
    }}

    QPushButton:hover {{
        background-color: {c['accent_glow']};
    }}

    QPushButton:pressed {{
        background-color: {c['accent_secondary']};
    }}

    QPushButton:disabled {{
        background-color: {c['bg_card']};
        color: {c['text_disabled']};
    }}

    /* Botones de acción secundarios */
    QPushButton[class="secondary"] {{
        background-color: {c['bg_card']};
        color: {c['text_primary']};
        border: 1px solid {c['border']};
    }}

    QPushButton[class="secondary"]:hover {{
        background-color: {c['bg_hover']};
        border-color: {c['accent_primary']};
    }}

    /* Botones de peligro */
    QPushButton[class="danger"] {{
        background-color: {c['error']};
        color: white;
    }}

    QPushButton[class="danger"]:hover {{
        background-color: {c['accent_secondary']};
    }}

    /* Botones de éxito */
    QPushButton[class="success"] {{
        background-color: {c['success']};
        color: white;
    }}

    QPushButton[class="success"]:hover {{
        background-color: {c['accent_secondary']};
    }}

    /* ═══════════════════════════════════════════════════════════════
       FILTROS (CHIPS / TAGS)
       ═══════════════════════════════════════════════════════════════ */
    QPushButton[class="chip"] {{
        background-color: {c['bg_card']};
        color: {c['text_secondary']};
        border: 1px solid {c['border']};
        border-radius: 16px;
        padding: 6px 16px;
        font-size: 12px;
        font-weight: 500;
        min-height: 16px;
    }}

    QPushButton[class="chip"]:hover {{
        background-color: {c['bg_hover']};
        color: {c['text_primary']};
        border-color: {c['accent_primary']};
    }}

    QPushButton[class="chip"]:checked,
    QPushButton[class="chip"][active="true"] {{
        background-color: {c['accent_primary']};
        color: white;
        border-color: {c['accent_primary']};
    }}

    /* ═══════════════════════════════════════════════════════════════
       INPUTS
       ═══════════════════════════════════════════════════════════════ */
    QLineEdit, QSpinBox, QComboBox, QDateEdit {{
        background-color: {c['bg_input']};
        color: {c['text_primary']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 8px 12px;
        font-size: 13px;
        min-height: 20px;
    }}

    QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QDateEdit:focus {{
        border-color: {c['border_focus']};
    }}

    QComboBox::drop-down {{
        border: none;
        padding-right: 10px;
    }}

    QComboBox::down-arrow {{
        image: none;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 6px solid {c['text_secondary']};
        margin-right: 8px;
    }}

    QComboBox QAbstractItemView {{
        background-color: {c['bg_card']};
        color: {c['text_primary']};
        border: 1px solid {c['border']};
        selection-background-color: {c['accent_primary']};
        selection-color: white;
    }}

    QSpinBox::up-button, QSpinBox::down-button {{
        background-color: {c['bg_hover']};
        border: none;
        width: 20px;
    }}

    QDateEdit::drop-down {{
        border: none;
        padding-right: 10px;
    }}

    /* ═══════════════════════════════════════════════════════════════
       TABLA
       ═══════════════════════════════════════════════════════════════ */
    QTableView {{
        background-color: {c['bg_secondary']};
        color: {c['text_primary']};
        border: 1px solid {c['border']};
        border-radius: 8px;
        gridline-color: {c['border']};
        selection-background-color: {c['bg_selected']};
        selection-color: {c['text_primary']};
        font-size: 12px;
        outline: none;
    }}

    QTableView::item {{
        padding: 4px 8px;
    }}

    QTableView::item:selected {{
        background-color: {c['bg_selected']};
        color: {c['text_primary']};
    }}

    QHeaderView::section {{
        background-color: {c['bg_sidebar']};
        color: {c['text_primary']};
        padding: 8px;
        border: none;
        border-bottom: 2px solid {c['accent_primary']};
        border-right: 1px solid {c['border']};
        font-weight: 600;
        font-size: 12px;
    }}

    QHeaderView::section:hover {{
        background-color: {c['bg_hover']};
    }}

    /* ═══════════════════════════════════════════════════════════════
       SCROLLBAR
       ═══════════════════════════════════════════════════════════════ */
    QScrollBar:vertical {{
        background: {c['scrollbar_bg']};
        width: 12px;
        margin: 0px;
        border-radius: 6px;
        border: none;
    }}

    QScrollBar::handle:vertical {{
        background-color: {c['scrollbar_handle']};
        min-height: 35px;
        border-radius: 6px;
    }}

    QScrollBar::handle:vertical:hover {{
        background-color: {c['accent_secondary']};
    }}

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: none;
        height: 0px;
    }}

    QScrollBar:horizontal {{
        background: {c['scrollbar_bg']};
        height: 12px;
        margin: 0px;
        border-radius: 6px;
        border: none;
    }}

    QScrollBar::handle:horizontal {{
        background-color: {c['scrollbar_handle']};
        min-width: 35px;
        border-radius: 6px;
    }}

    QScrollBar::handle:horizontal:hover {{
        background-color: {c['accent_secondary']};
    }}

    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
        background: none;
        width: 0px;
    }}

    /* ═══════════════════════════════════════════════════════════════
       LABELS Y CARDS
       ═══════════════════════════════════════════════════════════════ */
    QLabel {{
        color: {c['text_primary']};
    }}

    QLabel[class="title"] {{
        font-size: 22px;
        font-weight: 700;
        color: {c['text_primary']};
        padding: 5px 0;
    }}

    QLabel[class="subtitle"] {{
        font-size: 13px;
        color: {c['text_secondary']};
        padding: 2px 0;
    }}

    QLabel[class="stat-value"] {{
        font-size: 24px;
        font-weight: 700;
        color: {c['text_primary']};
    }}

    QLabel[class="stat-label"] {{
        font-size: 11px;
        color: {c['text_muted']};
        font-weight: 600;
    }}

    QFrame[class="card"] {{
        background-color: {c['bg_card']};
        border: 1px solid {c['border']};
        border-radius: 12px;
        padding: 0px;
    }}

    QFrame[class="card-success"] {{
        background-color: {c['success_bg']};
        border: 1px solid {c['success']};
        border-radius: 12px;
        padding: 16px;
    }}

    QFrame[class="card-warning"] {{
        background-color: {c['warning_bg']};
        border: 1px solid {c['warning']};
        border-radius: 12px;
        padding: 16px;
    }}

    QFrame[class="card-error"] {{
        background-color: {c['error_bg']};
        border: 1px solid {c['error']};
        border-radius: 12px;
        padding: 16px;
    }}

    /* ═══════════════════════════════════════════════════════════════
       BARRAS DE PROGRESO
       ═══════════════════════════════════════════════════════════════ */
    QProgressBar {{
        background-color: {c['bg_input']};
        border: none;
        border-radius: 6px;
        text-align: center;
        color: {c['text_primary']};
        font-size: 11px;
        min-height: 14px;
        max-height: 14px;
    }}

    QProgressBar::chunk {{
        background: qlineargradient(
            x1:0, y1:0, x2:1, y2:0,
            stop:0 {c['accent_primary']}, stop:1 {c['accent_secondary']}
        );
        border-radius: 6px;
    }}

    /* ═══════════════════════════════════════════════════════════════
       TOOLTIPS
       ═══════════════════════════════════════════════════════════════ */
    QToolTip {{
        background-color: {c['bg_card']};
        color: {c['text_primary']};
        border: 1px solid {c['border']};
        padding: 6px 10px;
        border-radius: 6px;
        font-size: 12px;
    }}

    /* ═══════════════════════════════════════════════════════════════
       MESSAGE BOX
       ═══════════════════════════════════════════════════════════════ */
    QMessageBox {{
        background-color: {c['bg_primary']};
    }}

    QMessageBox QLabel {{
        color: {c['text_primary']};
        font-size: 13px;
    }}

    QMessageBox QPushButton {{
        min-width: 80px;
    }}

    /* ═══════════════════════════════════════════════════════════════
       SEPARADOR
       ═══════════════════════════════════════════════════════════════ */
    QFrame[class="separator"] {{
        background-color: {c['border']};
        max-height: 1px;
        min-height: 1px;
    }}

    /* ═══════════════════════════════════════════════════════════════
       ZONA DE DROP (DRAG & DROP)
       ═══════════════════════════════════════════════════════════════ */
    QFrame[class="drop-zone"] {{
        background-color: {c['bg_card']};
        border: 2px dashed {c['border']};
        border-radius: 16px;
        min-height: 160px;
    }}

    QFrame[class="drop-zone"]:hover,
    QFrame[class="drop-zone-active"] {{
        border-color: {c['accent_primary']};
        background-color: {c['bg_hover']};
    }}

    /* ═══════════════════════════════════════════════════════════════
       STATUSBAR
       ═══════════════════════════════════════════════════════════════ */
    QStatusBar {{
        background-color: {c['bg_sidebar']};
        color: {c['text_muted']};
        border-top: 1px solid {c['border']};
        font-size: 11px;
        padding: 4px 12px;
    }}

    QStatusBar QLabel {{
        color: {c['text_muted']};
        font-size: 11px;
    }}
    """
