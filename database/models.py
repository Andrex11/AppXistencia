"""
Modelos SQLAlchemy para la aplicación de control de asistencia.

Define las tablas: Employee, Schedule, Configuration, AttendanceResult.
"""

from datetime import time, date
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    Float,
    ForeignKey,
    Integer,
    String,
    Time,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Clase base para todos los modelos SQLAlchemy."""
    pass


class Municipio(Base):
    """Modelo de municipio."""

    __tablename__ = "municipios"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    nombre: str = Column(String(100), unique=True, nullable=False, index=True)

    empleados = relationship("Employee", back_populates="municipio")

    def __repr__(self) -> str:
        return f"<Municipio(nombre={self.nombre})>"


class Employee(Base):
    """Modelo de empleado."""

    __tablename__ = "empleados"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    codigo_empleado: str = Column(String(50), unique=False, nullable=True, index=True)
    nombre: str = Column(String(200), nullable=False)
    activo: bool = Column(Boolean, default=True, nullable=False)
    municipio_id: Optional[int] = Column(Integer, ForeignKey("municipios.id"), nullable=True)

    # Relaciones
    municipio = relationship("Municipio", back_populates="empleados")
    horarios = relationship("Schedule", back_populates="empleado", cascade="all, delete-orphan")
    registros = relationship("AttendanceRecord", back_populates="empleado", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Employee(codigo={self.codigo_empleado}, nombre={self.nombre})>"


class Schedule(Base):
    """
    Modelo de horario por empleado y día de la semana.

    dia_semana: 0=Lunes, 1=Martes, 2=Miércoles, 3=Jueves, 4=Viernes, 5=Sábado, 6=Domingo
    
    Soporta horarios completamente diferentes entre empleados y días.
    Las excepciones se almacenan como texto y se interpretan en el motor de comparación.
    """

    __tablename__ = "horarios"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    empleado_id: int = Column(Integer, ForeignKey("empleados.id"), nullable=False, index=True)
    dia_semana: int = Column(Integer, nullable=False)  # 0-6

    # Horario mañana
    hora_entrada_manana: Optional[time] = Column(Time, nullable=True)
    hora_salida_manana: Optional[time] = Column(Time, nullable=True)

    # Horario tarde
    hora_entrada_tarde: Optional[time] = Column(Time, nullable=True)
    hora_salida_tarde: Optional[time] = Column(Time, nullable=True)

    # Flags especiales
    jornada_continua: bool = Column(Boolean, default=False, nullable=False)
    excepcion: Optional[str] = Column(Text, nullable=True)

    # Tolerancia personalizada (override global)
    tolerancia_minutos: Optional[int] = Column(Integer, nullable=True)

    # Relación
    empleado = relationship("Employee", back_populates="horarios")

    __table_args__ = (
        UniqueConstraint("empleado_id", "dia_semana", name="uq_empleado_dia"),
    )

    def __repr__(self) -> str:
        return f"<Schedule(empleado_id={self.empleado_id}, dia={self.dia_semana})>"


class Configuration(Base):
    """
    Modelo de configuración global.
    
    Almacena pares clave-valor para configuraciones del sistema.
    La clave principal es 'tolerancia_global' con valor por defecto de 2 minutos.
    """

    __tablename__ = "configuracion"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    clave: str = Column(String(100), unique=True, nullable=False)
    valor: str = Column(String(500), nullable=False)

    def __repr__(self) -> str:
        return f"<Configuration(clave={self.clave}, valor={self.valor})>"


class AttendanceRecord(Base):
    """
    Modelo de resultado de verificación de asistencia.

    Almacena el resultado del análisis de cada evento de asistencia
    (entrada mañana, salida mañana, entrada tarde, salida tarde)
    para cada empleado en cada fecha.
    """

    __tablename__ = "registros_asistencia"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    empleado_id: int = Column(Integer, ForeignKey("empleados.id"), nullable=False, index=True)
    fecha: date = Column(Date, nullable=False, index=True)

    # Evento: entrada_manana, salida_manana, entrada_tarde, salida_tarde
    evento: str = Column(String(50), nullable=False)

    # Horario programado vs real
    hora_programada: Optional[time] = Column(Time, nullable=True)
    hora_real: Optional[time] = Column(Time, nullable=True)

    # Estado: PUNTUAL, TARDE, AUSENTE, ANTICIPADO, SIN_REGISTRO, ERROR
    estado: str = Column(String(30), nullable=False)

    # Métricas
    minutos_retraso: float = Column(Float, default=0.0, nullable=False)
    minutos_anticipacion: float = Column(Float, default=0.0, nullable=False)

    # Observación libre
    observacion: Optional[str] = Column(Text, nullable=True)

    # Relación
    empleado = relationship("Employee", back_populates="registros")

    __table_args__ = (
        UniqueConstraint("empleado_id", "fecha", "evento", name="uq_empleado_fecha_evento"),
    )

    def __repr__(self) -> str:
        return f"<AttendanceRecord(empleado_id={self.empleado_id}, fecha={self.fecha}, evento={self.evento}, estado={self.estado})>"
