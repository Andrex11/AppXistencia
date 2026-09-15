"""
Motor de comparación de asistencia (AttendanceEngine).

Compara los horarios programados de cada empleado contra los registros
biométricos reales para determinar el estado de asistencia de cada evento.

Diseñado para procesamiento vectorizado con Pandas para alto rendimiento
(100k+ registros, 1000+ empleados).
"""

from dataclasses import dataclass, field
from datetime import date, time, datetime, timedelta
from typing import Optional

import pandas as pd


# ──────────────────────────────────────────────────────────────────────
# Constantes de estado
# ──────────────────────────────────────────────────────────────────────
PUNTUAL = "PUNTUAL"
TARDE = "TARDE"
AUSENTE = "AUSENTE"
ANTICIPADO = "ANTICIPADO"
SIN_REGISTRO = "SIN_REGISTRO"
ERROR = "ERROR"
NO_APLICA = "NO_APLICA"

# Nombres legibles para la UI
ESTADO_DISPLAY = {
    PUNTUAL: "✔ Puntual",
    TARDE: "⏰ Tarde",
    AUSENTE: "✖ Ausente",
    ANTICIPADO: "⚡ Salida anticipada",
    SIN_REGISTRO: "❓ Sin registro",
    ERROR: "⚠ Error",
    NO_APLICA: "— No aplica",
}

# Nombres de eventos
ENTRADA_MANANA = "entrada_manana"
SALIDA_MANANA = "salida_manana"
ENTRADA_TARDE = "entrada_tarde"
SALIDA_TARDE = "salida_tarde"

EVENTOS_DISPLAY = {
    ENTRADA_MANANA: "Entrada Mañana",
    SALIDA_MANANA: "Salida Mañana",
    ENTRADA_TARDE: "Entrada Tarde",
    SALIDA_TARDE: "Salida Tarde",
}


@dataclass
class AttendanceResult:
    """Resultado de la verificación de un evento de asistencia."""

    codigo_empleado: str
    nombre_empleado: str
    municipio: str
    fecha: date
    evento: str  # entrada_manana, salida_manana, entrada_tarde, salida_tarde
    hora_programada: Optional[time]
    hora_real: Optional[time]
    estado: str  # PUNTUAL, TARDE, AUSENTE, etc.
    minutos_retraso: float = 0.0
    minutos_anticipacion: float = 0.0
    observacion: str = ""


class AttendanceEngine:
    """
    Motor de comparación de asistencia.

    Recibe los horarios programados y los registros biométricos,
    y produce una lista de resultados de verificación.
    """

    def __init__(self, tolerance_minutes: int = 2) -> None:
        self.tolerance_minutes = tolerance_minutes

    def process(
        self,
        schedules: list[dict],
        biometric_df: pd.DataFrame,
        tolerance_override: Optional[int] = None,
    ) -> list[AttendanceResult]:
        """
        Procesa la comparación completa de asistencia.

        Args:
            schedules: Lista de dicts con horarios (de la BD).
                Cada dict: {
                    'codigo_empleado', 'nombre', 'dia_semana',
                    'hora_entrada_manana', 'hora_salida_manana',
                    'hora_entrada_tarde', 'hora_salida_tarde',
                    'jornada_continua', 'excepcion', 'tolerancia_minutos'
                }
            biometric_df: DataFrame con registros biométricos limpios.
                Columnas: 'codigo_empleado', 'nombre', 'fecha', 'hora', 'datetime'
            tolerance_override: Tolerancia global (si None, usa self.tolerance_minutes).

        Returns:
            Lista de AttendanceResult con el análisis de cada evento.
        """
        global_tolerance = tolerance_override or self.tolerance_minutes
        results: list[AttendanceResult] = []

        if biometric_df.empty:
            return results

        # Crear un dict de horarios indexado por (codigo_empleado, dia_semana)
        schedule_map: dict[tuple[str, int], dict] = {}
        employee_names: dict[str, str] = {}
        employee_municipios: dict[str, str] = {}
        employee_tolerances: dict[str, Optional[int]] = {}

        for sched in schedules:
            key = (str(sched["codigo_empleado"]), sched["dia_semana"])
            schedule_map[key] = sched
            employee_names[str(sched["codigo_empleado"])] = sched.get("nombre", "")
            if str(sched["codigo_empleado"]) not in employee_municipios:
                employee_municipios[str(sched["codigo_empleado"])] = sched.get("municipio", "")
            tol = sched.get("tolerancia_minutos")
            if tol is not None:
                employee_tolerances[str(sched["codigo_empleado"])] = tol

        # Obtener las fechas únicas y los empleados del biométrico
        fechas = sorted(biometric_df["fecha"].unique())
        empleados_bio = biometric_df["codigo_empleado"].unique()

        # Determinar los municipios presentes en el archivo biométrico
        municipios_presentes = set()
        for emp_code in empleados_bio:
            muni = employee_municipios.get(emp_code)
            if muni:
                municipios_presentes.add(muni)

        # Filtrar empleados con horario: solo evaluar a los empleados de los municipios 
        # que tienen al menos un registro en el archivo biométrico.
        # Si el archivo tiene registros de Arauca, solo se evaluarán empleados de Arauca.
        empleados_sched = set()
        for s in schedules:
            emp_code = str(s["codigo_empleado"])
            muni = employee_municipios.get(emp_code, "")
            if not municipios_presentes or muni in municipios_presentes:
                empleados_sched.add(emp_code)

        for fecha_val in fechas:
            # dia_semana: 0=Lunes ... 6=Domingo
            if isinstance(fecha_val, date):
                dia_semana = fecha_val.weekday()
            else:
                dia_semana = pd.Timestamp(fecha_val).weekday()

            # Domingo: generalmente no hay horario
            if dia_semana == 6:
                continue

            # Registros del día
            registros_dia = biometric_df[biometric_df["fecha"] == fecha_val]

            # Procesar todos los empleados con horario para este día
            empleados_dia = set(registros_dia["codigo_empleado"].unique())
            # Agregar empleados con horario que no tienen registros (AUSENTE)
            for emp_code in empleados_sched:
                if (emp_code, dia_semana) in schedule_map:
                    empleados_dia.add(emp_code)

            for emp_code in empleados_dia:
                schedule = schedule_map.get((emp_code, dia_semana))

                if schedule is None:
                    # Empleado tiene registros pero no horario para este día
                    registros_emp = registros_dia[registros_dia["codigo_empleado"] == emp_code]
                    if not registros_emp.empty:
                        nombre = registros_emp.iloc[0]["nombre"]
                        muni = employee_municipios.get(emp_code, "")
                        # Solo agregar un registro de error genérico
                        results.append(AttendanceResult(
                            codigo_empleado=emp_code,
                            nombre_empleado=nombre,
                            municipio=muni,
                            fecha=fecha_val if isinstance(fecha_val, date) else pd.Timestamp(fecha_val).date(),
                            evento=ENTRADA_MANANA,
                            hora_programada=None,
                            hora_real=None,
                            estado=ERROR,
                            observacion="Sin horario programado para este día",
                        ))
                    continue

                nombre = employee_names.get(emp_code, emp_code)
                muni = employee_municipios.get(emp_code, "")
                tolerance = employee_tolerances.get(emp_code, global_tolerance)

                # Registros del empleado en este día
                registros_emp = registros_dia[registros_dia["codigo_empleado"] == emp_code]
                horas_empleado = sorted(registros_emp["hora"].tolist()) if not registros_emp.empty else []

                # Obtener los horarios programados
                h_ent_am = schedule.get("hora_entrada_manana")
                h_sal_am = schedule.get("hora_salida_manana")
                h_ent_pm = schedule.get("hora_entrada_tarde")
                h_sal_pm = schedule.get("hora_salida_tarde")
                jornada_continua = schedule.get("jornada_continua", False)

                # Definir los eventos a evaluar
                eventos = []
                if h_ent_am is not None:
                    eventos.append((ENTRADA_MANANA, h_ent_am, "entrada"))
                if h_sal_am is not None:
                    eventos.append((SALIDA_MANANA, h_sal_am, "salida"))
                if h_ent_pm is not None and not jornada_continua:
                    eventos.append((ENTRADA_TARDE, h_ent_pm, "entrada"))
                if h_sal_pm is not None and not jornada_continua:
                    eventos.append((SALIDA_TARDE, h_sal_pm, "salida"))

                # Asignar registros a eventos
                horas_usadas: set[int] = set()
                fecha_date = fecha_val if isinstance(fecha_val, date) else pd.Timestamp(fecha_val).date()

                for evento_nombre, hora_prog, tipo_evento in eventos:
                    hora_real, idx_used = self._find_best_match(
                        horas_empleado, hora_prog, tipo_evento, horas_usadas,
                    )

                    if idx_used is not None:
                        horas_usadas.add(idx_used)

                    result = self._evaluate_event(
                        codigo_empleado=emp_code,
                        nombre_empleado=nombre,
                        municipio=muni,
                        fecha=fecha_date,
                        evento=evento_nombre,
                        hora_programada=hora_prog,
                        hora_real=hora_real,
                        tipo_evento=tipo_evento,
                        tolerancia=tolerance,
                    )
                    results.append(result)

        return results

    def _find_best_match(
        self,
        horas: list[time],
        hora_programada: time,
        tipo: str,
        usadas: set[int],
    ) -> tuple[Optional[time], Optional[int]]:
        """
        Encuentra el registro biométrico más adecuado para un evento programado.

        Para entradas: busca el registro más cercano ANTES o poco después de la hora programada.
        Para salidas: busca el registro más cercano DESPUÉS o poco antes de la hora programada.

        Args:
            horas: Lista ordenada de horas de registro del empleado.
            hora_programada: Hora programada del evento.
            tipo: 'entrada' o 'salida'.
            usadas: Índices ya asignados a otros eventos.

        Returns:
            Tupla (hora_real, índice_usado) o (None, None) si no se encontró.
        """
        if not horas:
            return None, None

        prog_minutes = hora_programada.hour * 60 + hora_programada.minute

        best_idx: Optional[int] = None
        best_diff: float = float("inf")

        # Ventana de búsqueda: ±120 minutos alrededor de la hora programada
        window = 120

        for i, hora in enumerate(horas):
            if i in usadas:
                continue

            reg_minutes = hora.hour * 60 + hora.minute + hora.second / 60.0
            diff = reg_minutes - prog_minutes

            if tipo == "entrada":
                # Para entradas: preferir registros tempranos.
                # Al multiplicar diff negativo por 0.01, garantizamos que un registro
                # temprano siempre gane contra uno tardío, evitando marcar 'Tarde' 
                # si el empleado marcó antes de la hora.
                effective_diff = abs(diff) if diff > 0 else abs(diff) * 0.01
                if abs(diff) < window and effective_diff < best_diff:
                    best_diff = effective_diff
                    best_idx = i
            else:
                # Para salidas: preferir registros cercanos a la hora programada
                if abs(diff) < window and abs(diff) < best_diff:
                    best_diff = abs(diff)
                    best_idx = i

        if best_idx is not None:
            return horas[best_idx], best_idx
        return None, None

    def _evaluate_event(
        self,
        codigo_empleado: str,
        nombre_empleado: str,
        municipio: str,
        fecha: date,
        evento: str,
        hora_programada: Optional[time],
        hora_real: Optional[time],
        tipo_evento: str,
        tolerancia: int,
    ) -> AttendanceResult:
        """
        Evalúa un evento de asistencia individual.

        Determina el estado comparando hora programada vs hora real,
        considerando la tolerancia y el tipo de evento.
        """
        # Sin horario programado
        if hora_programada is None:
            return AttendanceResult(
                codigo_empleado=codigo_empleado,
                nombre_empleado=nombre_empleado,
                municipio=municipio,
                fecha=fecha,
                evento=evento,
                hora_programada=None,
                hora_real=hora_real,
                estado=NO_APLICA,
                observacion="No tiene horario programado para este evento",
            )

        # Sin registro biométrico
        if hora_real is None:
            return AttendanceResult(
                codigo_empleado=codigo_empleado,
                nombre_empleado=nombre_empleado,
                municipio=municipio,
                fecha=fecha,
                evento=evento,
                hora_programada=hora_programada,
                hora_real=None,
                estado=AUSENTE if tipo_evento == "entrada" else SIN_REGISTRO,
                observacion="No se encontró registro biométrico",
            )

        # Calcular diferencia en minutos
        prog_dt = datetime.combine(fecha, hora_programada)
        real_dt = datetime.combine(fecha, hora_real)
        diff = (real_dt - prog_dt).total_seconds() / 60.0

        if tipo_evento == "entrada":
            # Entrada: positivo = tarde, negativo = temprano
            if diff <= tolerancia:
                return AttendanceResult(
                    codigo_empleado=codigo_empleado,
                    nombre_empleado=nombre_empleado,
                    municipio=municipio,
                    fecha=fecha,
                    evento=evento,
                    hora_programada=hora_programada,
                    hora_real=hora_real,
                    estado=PUNTUAL,
                    minutos_retraso=max(0, diff),
                )
            else:
                return AttendanceResult(
                    codigo_empleado=codigo_empleado,
                    nombre_empleado=nombre_empleado,
                    municipio=municipio,
                    fecha=fecha,
                    evento=evento,
                    hora_programada=hora_programada,
                    hora_real=hora_real,
                    estado=TARDE,
                    minutos_retraso=round(diff, 1),
                    observacion=f"Llegó {round(diff, 1)} min tarde",
                )
        else:
            # Salida: negativo = salió antes, positivo = salió después
            if diff >= -tolerancia:
                return AttendanceResult(
                    codigo_empleado=codigo_empleado,
                    nombre_empleado=nombre_empleado,
                    municipio=municipio,
                    fecha=fecha,
                    evento=evento,
                    hora_programada=hora_programada,
                    hora_real=hora_real,
                    estado=PUNTUAL,
                    minutos_anticipacion=max(0, -diff),
                )
            else:
                return AttendanceResult(
                    codigo_empleado=codigo_empleado,
                    nombre_empleado=nombre_empleado,
                    municipio=municipio,
                    fecha=fecha,
                    evento=evento,
                    hora_programada=hora_programada,
                    hora_real=hora_real,
                    estado=ANTICIPADO,
                    minutos_anticipacion=round(abs(diff), 1),
                    observacion=f"Salió {round(abs(diff), 1)} min antes",
                )


def results_to_dataframe(results: list[AttendanceResult]) -> pd.DataFrame:
    """
    Convierte una lista de AttendanceResult en un DataFrame para la tabla de resultados.

    Pivotea los eventos para mostrar una fila por empleado por fecha con
    las 4 columnas de entrada/salida.
    """
    if not results:
        return pd.DataFrame()

    # Construir filas raw
    rows = []
    for r in results:
        rows.append({
            "codigo_empleado": r.codigo_empleado,
            "nombre_empleado": r.nombre_empleado,
            "municipio": r.municipio,
            "fecha": r.fecha,
            "evento": r.evento,
            "hora_programada": r.hora_programada,
            "hora_real": r.hora_real,
            "estado": r.estado,
            "minutos_retraso": r.minutos_retraso,
            "minutos_anticipacion": r.minutos_anticipacion,
            "observacion": r.observacion,
        })

    df = pd.DataFrame(rows)

    # Para la vista pivot (una fila por empleado/fecha), agrupar por empleado+fecha
    pivot_rows = []
    grouped = df.groupby(["codigo_empleado", "nombre_empleado", "municipio", "fecha"])

    for (cod, nom, muni, fch), group in grouped:
        row: dict = {
            "Empleado": nom,
            "Código": cod,
            "Municipio": muni,
            "Fecha": fch,
        }

        estados = []
        observaciones = []
        total_retraso = 0.0
        total_anticipacion = 0.0

        for evento_key, display_name in EVENTOS_DISPLAY.items():
            evento_data = group[group["evento"] == evento_key]
            if not evento_data.empty:
                ev = evento_data.iloc[0]
                prog = ev["hora_programada"]
                real = ev["hora_real"]
                row[f"{display_name} Prog."] = _format_time(prog)
                row[f"{display_name} Real"] = _format_time(real)
                row[f"_{display_name}_estado"] = ev["estado"]
                estados.append(ev["estado"])
                if ev["observacion"]:
                    observaciones.append(ev["observacion"])
                total_retraso += ev["minutos_retraso"]
                total_anticipacion += ev["minutos_anticipacion"]
            else:
                row[f"{display_name} Prog."] = "—"
                row[f"{display_name} Real"] = "—"
                row[f"_{display_name}_estado"] = NO_APLICA

        # Determinar estado general del día
        row["Estado"] = _determine_day_status(estados)
        row["Observación"] = "; ".join(observaciones) if observaciones else ""
        row["Min. Tarde"] = round(total_retraso, 1) if total_retraso > 0 else 0
        row["Min. Anticipación"] = round(total_anticipacion, 1) if total_anticipacion > 0 else 0
        # Guardar estados individuales para filtros
        row["_estados_raw"] = estados

        pivot_rows.append(row)

    result_df = pd.DataFrame(pivot_rows)
    if not result_df.empty:
        result_df = result_df.sort_values(["Fecha", "Empleado"]).reset_index(drop=True)
    return result_df


def _format_time(t: Optional[time]) -> str:
    """Formatea un objeto time para mostrar en la tabla."""
    if t is None:
        return "—"
    return t.strftime("%H:%M:%S")


def _determine_day_status(estados: list[str]) -> str:
    """Determina el estado general de un empleado en un día dado sus estados por evento."""
    if not estados:
        return NO_APLICA

    if ERROR in estados:
        return ERROR
    if AUSENTE in estados:
        return AUSENTE
    if SIN_REGISTRO in estados:
        return SIN_REGISTRO
    if TARDE in estados:
        return TARDE
    if ANTICIPADO in estados:
        return ANTICIPADO

    # Filtrar NO_APLICA
    real_states = [s for s in estados if s != NO_APLICA]
    if not real_states:
        return NO_APLICA
    if all(s == PUNTUAL for s in real_states):
        return PUNTUAL

    return PUNTUAL
