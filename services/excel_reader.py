"""
Lectura y procesamiento de archivos Excel.

Maneja dos tipos de archivos:
1. Excel de horarios programados de empleados.
2. Excel de registros biométricos del reloj de huella.
"""

import re
from datetime import time, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd


# ──────────────────────────────────────────────────────────────────────
# Mapeo de nombres de días en español a números (1=Lunes ... 7=Domingo)
# ──────────────────────────────────────────────────────────────────────
DIAS_SEMANA = {
    "lunes": 1,
    "martes": 2,
    "miercoles": 3,
    "jueves": 4,
    "viernes": 5,
    "sabado": 6,
    "domingo": 7,
}


def _parse_time(value: Any, afternoon: bool = False) -> time | None:
    """
    Convierte un valor de celda Excel a un objeto time.
    
    Soporta:
    - datetime.time directamente
    - datetime.datetime (extrae la hora)
    - Strings con formato HH:MM, HH:MM:SS, H:MM
    - Floats de Excel (fracción del día)
    - None / NaN / vacíos
    """
    if value is None:
        return None

    if isinstance(value, time):
        return value

    if isinstance(value, datetime):
        return value.time()

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if pd.isna(value):
            return None
        # Excel puede guardar una hora como fracción del día o como número.
        if float(value) < 1:
            total_seconds = int(round(float(value) * 86400))
        else:
            hours = int(value)
            minutes = int(round((float(value) - hours) * 60))
            if afternoon and hours < 12:
                hours += 12
            total_seconds = hours * 3600 + minutes * 60
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        try:
            return time(hours % 24, minutes, seconds)
        except ValueError:
            return None

    # Los valores numéricos de pandas pueden ser tipos NumPy, no int/float.
    if hasattr(value, "item"):
        try:
            return _parse_time(value.item(), afternoon=afternoon)
        except (TypeError, ValueError):
            pass

    text = str(value).strip()
    if not text or text.lower() in ("nan", "nat", "none", "-", "n/a", ""):
        return None

    # Algunas exportaciones escriben las horas como "8" o "2.5".
    try:
        numeric_value = float(text.replace(",", "."))
    except ValueError:
        numeric_value = None
    if numeric_value is not None:
        return _parse_time(numeric_value, afternoon=afternoon)

    # Limpiar fracciones de segundo que hacen fallar strptime (ej: "08:00:00.0000000")
    time_text = text
    if ":" in time_text and "." in time_text:
        time_text = time_text.split(".")[0]

    # Intentar múltiples formatos
    for fmt in ("%H:%M:%S", "%H:%M", "%I:%M %p", "%I:%M:%S %p"):
        try:
            return datetime.strptime(time_text, fmt).time()
        except ValueError:
            continue

    return None


def _normalize_column_name(name: str) -> str:
    """Normaliza un nombre de columna: minúsculas, sin espacios extra, sin acentos comunes."""
    text = str(name).strip().lower()
    # Reemplazar acentos comunes
    replacements = {
        "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u",
        "ñ": "n",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    # Reemplazar múltiples espacios por uno
    text = re.sub(r"\s+", " ", text)
    return text


def _normalize_employee_code(value: Any) -> str:
    """Convierte el código a texto sin alterar identificadores alfanuméricos."""
    text = str(value).strip()
    if text.startswith("'"):
        text = text[1:].strip()
    if text.lower() in ("nan", "none", ""):
        return ""
    if re.fullmatch(r"\d+\.0", text):
        return text[:-2]
    return text


# ──────────────────────────────────────────────────────────────────────
# Lectura del Excel/CSV de horarios
# ──────────────────────────────────────────────────────────────────────

def read_schedule_excel(file_path: str) -> list[dict]:
    """
    Lee el archivo CSV o Excel de horarios y retorna una lista de diccionarios
    con la información normalizada de cada empleado.

    Soporta:
    1. Estructura tabular: codigo;empleado;dia_semana;hora_inicio;hora_fin;es_segunda_jornada;activo
    2. Estructura matriz: L-V / Sabado, Mañana / Tarde (como en FUENTE_HORARIO_V_FINAL.xlsx)
    """
    path = Path(file_path)
    if path.suffix.lower() == ".csv":
        try:
            df = pd.read_csv(file_path, sep=";", dtype=str, header=None)
            if len(df.columns) < 2:
                df = pd.read_csv(file_path, sep=",", dtype=str, header=None)
        except Exception:
            df = pd.read_excel(file_path, dtype=str, header=None)
    elif path.suffix.lower() == ".xls":
        df = pd.read_excel(file_path, engine="xlrd", dtype=str, header=None)
    else:
        df = pd.read_excel(file_path, engine="openpyxl", dtype=str, header=None)

    if df.empty:
        return []

    # Detectar el tipo de formato
    format_type = "tabular"
    header_row_idx = 0

    for idx, row in df.head(10).iterrows():
        row_str = " ".join([str(val).lower() for val in row.values])
        if "codigo" in row_str and "empleado" in row_str:
            if "dia_semana" in row_str or "dia" in row_str or "activo" in row_str:
                format_type = "tabular"
                header_row_idx = idx
                break
            elif "inicio" in row_str and "salida" in row_str:
                format_type = "matrix"
                header_row_idx = idx
                break
            else:
                format_type = "tabular"
                header_row_idx = idx
                break

    employees_dict: dict[str, dict] = {}

    if format_type == "matrix":
        # Formato de matriz tipo FUENTE_HORARIO_V_FINAL
        for idx in range(header_row_idx + 1, len(df)):
            row = df.iloc[idx]
            if len(row) < 10:
                continue

            codigo = _normalize_employee_code(row.iloc[0])
            nombre = str(row.iloc[1]).strip()

            if not codigo or codigo.lower() in ("nan", "none"):
                codigo = ""

            if not codigo and not nombre:
                continue

            if codigo not in employees_dict and nombre not in [e["nombre"] for e in employees_dict.values()]:
                # Usar un identificador temporal para el dict si no hay código, por ejemplo el nombre
                dict_key = codigo if codigo else f"__name__{nombre}"
                employees_dict[dict_key] = {
                    "codigo_empleado": codigo,
                    "nombre": nombre,
                    "municipio": "",
                    "horarios_dict": {}
                }
            else:
                dict_key = codigo if codigo else f"__name__{nombre}"

            if dict_key not in employees_dict:
                 employees_dict[dict_key] = {
                    "codigo_empleado": codigo,
                    "nombre": nombre,
                    "municipio": "",
                    "horarios_dict": {}
                }

            horarios = employees_dict[dict_key]["horarios_dict"]
            observacion = str(row.iloc[10]) if len(row) > 10 and pd.notna(row.iloc[10]) and str(row.iloc[10]).lower() not in ("nan", "none") else None

            # Lunes a Viernes (días 0 al 4)
            for d in range(5):
                if d not in horarios:
                    horarios[d] = {
                        "dia_semana": d,
                        "hora_entrada_manana": _parse_time(row.iloc[2], afternoon=False),
                        "hora_salida_manana": _parse_time(row.iloc[3], afternoon=False),
                        "hora_entrada_tarde": _parse_time(row.iloc[4], afternoon=True),
                        "hora_salida_tarde": _parse_time(row.iloc[5], afternoon=True),
                        "jornada_continua": False,
                        "excepcion": observacion,
                    }

            # Sábado (día 5)
            if 5 not in horarios:
                horarios[5] = {
                    "dia_semana": 5,
                    "hora_entrada_manana": _parse_time(row.iloc[6], afternoon=False),
                    "hora_salida_manana": _parse_time(row.iloc[7], afternoon=False),
                    "hora_entrada_tarde": _parse_time(row.iloc[8], afternoon=True),
                    "hora_salida_tarde": _parse_time(row.iloc[9], afternoon=True),
                    "jornada_continua": False,
                    "excepcion": observacion,
                }
    else:
        # Formato tabular
        # Establecer la fila de encabezados correcta
        df.columns = [_normalize_column_name(c) for c in df.iloc[header_row_idx]]
        df = df.iloc[header_row_idx + 1:].reset_index(drop=True)
        col_muni = _find_column(df.columns, ["municipio"])

        for _, row in df.iterrows():
            activo = str(row.get("activo", "1")).strip().lower()
            if activo in ("0", "false", "no", "0.0"):
                continue

            codigo = _normalize_employee_code(row.get("codigo", ""))
            nombre = str(row.get("empleado", "")).strip()

            if not codigo or codigo.lower() in ("nan", "none"):
                codigo = ""

            if not codigo and not nombre:
                continue

            dict_key = codigo if codigo else f"__name__{nombre}"

            if dict_key not in employees_dict:
                muni_val = ""
                if col_muni and pd.notna(row.get(col_muni)):
                    muni_val = str(row.get(col_muni)).strip()

                employees_dict[dict_key] = {
                    "codigo_empleado": codigo,
                    "nombre": nombre,
                    "municipio": muni_val,
                    "horarios_dict": {}
                }

            try:
                dia_raw = row.get("dia_semana")
                if pd.isna(dia_raw):
                    continue
                dia_semana_raw = int(float(str(dia_raw).strip()))
                dia_semana_db = dia_semana_raw - 1
                if dia_semana_db < 0 or dia_semana_db > 6:
                    continue
            except (ValueError, TypeError):
                continue

            es_segunda = str(row.get("es_segunda_jornada", "0")).strip().lower()
            is_pm = es_segunda in ("1", "true", "si", "sí", "yes", "1.0")

            ent = _parse_time(row.get("hora_inicio"), afternoon=is_pm)
            sal = _parse_time(row.get("hora_fin"), afternoon=is_pm)

            horarios = employees_dict[dict_key]["horarios_dict"]
            if dia_semana_db not in horarios:
                horarios[dia_semana_db] = {
                    "dia_semana": dia_semana_db,
                    "hora_entrada_manana": None,
                    "hora_salida_manana": None,
                    "hora_entrada_tarde": None,
                    "hora_salida_tarde": None,
                    "jornada_continua": False,
                    "excepcion": None,
                }

            day_sched = horarios[dia_semana_db]

            if is_pm:
                day_sched["hora_entrada_tarde"] = ent
                day_sched["hora_salida_tarde"] = sal
            else:
                day_sched["hora_entrada_manana"] = ent
                day_sched["hora_salida_manana"] = sal

    employees_data: list[dict] = []
    for emp_data in employees_dict.values():
        employees_data.append({
            "codigo_empleado": emp_data["codigo_empleado"],
            "nombre": emp_data["nombre"],
            "municipio": emp_data.get("municipio", ""),
            "horarios": list(emp_data["horarios_dict"].values()),
        })

    return employees_data


# ──────────────────────────────────────────────────────────────────────
# Lectura del Excel biométrico
# ──────────────────────────────────────────────────────────────────────

def read_biometric_excel(file_path: str) -> pd.DataFrame:
    """
    Lee el archivo Excel del reloj biométrico y retorna un DataFrame limpio.

    Columnas esperadas del archivo (pueden estar en español o inglés):
    ID de persona | Nombre | Departamento | Hora | Estado de asistencia | ...

    El DataFrame resultante tiene las columnas:
    - codigo_empleado: str
    - nombre: str  
    - fecha: date
    - hora: time
    - datetime: datetime (fecha + hora combinados)
    """
    path = Path(file_path)
    if path.suffix.lower() == ".xls":
        df = pd.read_excel(file_path, engine="xlrd", dtype=str)
    else:
        df = pd.read_excel(file_path, engine="openpyxl", dtype=str)

    if df.empty:
        raise ValueError("El archivo biométrico está vacío.")

    # Normalizar columnas
    df.columns = [_normalize_column_name(c) for c in df.columns]

    # Mapear columnas del biométrico
    col_id = _find_column(df.columns, ["id de persona", "id persona", "id", "codigo", "numero"])
    col_nombre = _find_column(df.columns, ["nombre", "name", "empleado", "trabajador"])
    col_hora = _find_column(df.columns, ["hora", "time", "fecha", "date", "fecha/hora", "fecha hora", "fechahora"])

    if col_hora is None:
        raise ValueError(
            "No se encontró la columna 'Hora' en el archivo biométrico. "
            f"Columnas disponibles: {list(df.columns)}"
        )

    # Construir DataFrame limpio
    result = pd.DataFrame()

    # Código de empleado
    if col_id is not None:
        result["codigo_empleado"] = df[col_id].apply(_normalize_employee_code)
    elif col_nombre is not None:
        result["codigo_empleado"] = df[col_nombre].apply(_normalize_employee_code)
    else:
        raise ValueError("No se encontró columna de identificación de empleado.")

    # Nombre
    if col_nombre is not None:
        result["nombre"] = df[col_nombre].astype(str).str.strip()
    else:
        result["nombre"] = result["codigo_empleado"]

    # Parsear la columna de fecha/hora
    result["datetime"] = pd.to_datetime(df[col_hora], errors="coerce")

    # Eliminar filas con fecha inválida
    invalid_count = result["datetime"].isna().sum()
    if invalid_count > 0:
        result = result.dropna(subset=["datetime"])

    # Separar fecha y hora
    result["fecha"] = result["datetime"].dt.date
    result["hora"] = result["datetime"].dt.time

    # Ordenar por empleado y fecha/hora
    result = result.sort_values(["codigo_empleado", "datetime"]).reset_index(drop=True)

    # Eliminar duplicados consecutivos (registros con < 60 segundos de diferencia)
    result = _remove_consecutive_duplicates(result, threshold_seconds=60)

    return result


def _find_column(columns: list[str], keywords: list[str]) -> str | None:
    """Busca la primera columna que contenga alguno de los keywords."""
    for col in columns:
        for kw in keywords:
            if kw in col:
                return col
    return None


def _remove_consecutive_duplicates(
    df: pd.DataFrame,
    threshold_seconds: int = 60,
) -> pd.DataFrame:
    """
    Elimina registros duplicados consecutivos del mismo empleado
    con diferencia de tiempo menor al umbral.

    Conserva siempre el primer registro de cada secuencia duplicada.
    """
    if df.empty:
        return df

    # Calcular diferencia de tiempo con el registro anterior del mismo empleado
    df = df.copy()
    df["prev_datetime"] = df.groupby("codigo_empleado")["datetime"].shift(1)
    df["time_diff"] = (df["datetime"] - df["prev_datetime"]).dt.total_seconds()

    # Mantener registros donde la diferencia es >= umbral o es el primero del empleado
    mask = df["time_diff"].isna() | (df["time_diff"] >= threshold_seconds)
    result = df[mask].drop(columns=["prev_datetime", "time_diff"]).reset_index(drop=True)

    return result
