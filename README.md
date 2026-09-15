# 📋 Control de Asistencia — Verificación Biométrica

Aplicación de escritorio en Python para verificar automáticamente la asistencia de empleados, comparando los horarios programados contra los registros de un dispositivo de asistencia. Esta aplicacion es compatible con los dispositivos de asistencia de la marca Hikvision, herramienta ivms-4200. 

## De importancia:
> Esta version solo esta preparada para funcionar con los reportes de asistencia exportados en formato excel de dichos dispositivos.

## 🚀 Instalación

### Requisitos previos
- Python 3.13 o superior

### Pasos

1. **Crear un entorno virtual** (recomendado):
```bash
python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # Linux/Mac
```

2. **Instalar dependencias**:
```bash
pip install -r requirements.txt
```

3. **Ejecutar la aplicación**:
```bash
python main.py
```

## 📖 Uso

### 1. Configurar Horarios
- Abra la sección **"Configuración Horarios"** desde la barra lateral.
- Haga clic en **"Importar Excel de Horarios"** y seleccione su archivo.
- Configure la **tolerancia global** (por defecto: 2 minutos).

### 2. Verificar Asistencia
- En la pantalla principal **"Verificar Asistencia"**, cargue el archivo Excel del reloj biométrico.
- Puede arrastrar y soltar el archivo o usar el botón de selección.
- El análisis se ejecuta automáticamente.

### 3. Resultados
- Use los **filtros rápidos** (Puntuales, Tarde, Ausentes, etc.) para filtrar los resultados.
- Filtre por **empleado**, **fecha** o **rango de fechas**.
- Exporte los resultados filtrados a Excel con el botón **"Exportar a Excel"**.

## 📄 Formato de archivos Excel

### Excel de Horarios
| Empleado | Entrada Mañana | Salida Mañana | Entrada Tarde | Salida Tarde | Entrada Mañana Sábado | Salida Mañana Sábado | Entrada Tarde Sábado | Salida Tarde Sábado | Observación |
|----------|----------------|---------------|---------------|--------------|----------------------|---------------------|---------------------|---------------------|-------------|
| 001 - Juan Pérez | 08:00 | 12:00 | 14:00 | 18:00 | 08:00 | 12:00 | | | |
| 002 - María López | 07:30 | 12:30 | 14:00 | 17:30 | | | | | No trabaja sábados |
| 003 - Carlos Ruiz | 08:00 | 17:00 | | | | | | | Jornada continua |

### Excel Biométrico
El archivo exportado directamente desde el reloj biométrico con las columnas:
- ID de persona
- Nombre
- Departamento
- Hora (formato: `2026-07-29 08:59:39`)
- Estado de asistencia
- (otras columnas...)

## 🏗️ Arquitectura

```
attendance_app/
├── main.py                    # Punto de entrada
├── database/
│   ├── models.py              # Modelos SQLAlchemy (ORM)
│   └── database.py            # Gestión de conexión SQLite
├── services/
│   ├── attendance_engine.py   # Motor de comparación de asistencia
│   ├── excel_reader.py        # Lectura de archivos Excel
│   └── report_generator.py    # Exportación a Excel formateado
├── ui/
│   ├── main_window.py         # Ventana principal con sidebar
│   ├── schedule_view.py       # Vista de configuración de horarios
│   ├── results_view.py        # Vista de resultados y filtros
│   └── styles.py              # Tema oscuro QSS
└── requirements.txt
```

## 🔧 Tecnologías
- **Python 3.13+**
- **PySide6** — Interfaz gráfica
- **SQLAlchemy** — ORM para SQLite
- **Pandas** — Procesamiento de datos
- **openpyxl / xlrd** — Lectura/escritura de Excel
- **QDarkStyle** — Tema oscuro base
