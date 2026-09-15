"""
Gestión de la conexión a la base de datos SQLite.

Proporciona un singleton DatabaseManager que maneja la creación de tablas,
sesiones y operaciones comunes de configuración.
"""

import os
from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from database.models import Base, Configuration


# Habilitar WAL mode y foreign keys en SQLite para mejor rendimiento
@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA foreign_keys=ON;")
    cursor.close()


class DatabaseManager:
    """
    Singleton para gestionar la conexión a SQLite.

    Crea la base de datos y las tablas automáticamente al instanciarse.
    Proporciona métodos para obtener sesiones y gestionar configuración.
    """

    _instance: Optional["DatabaseManager"] = None
    _initialized: bool = False

    def __new__(cls, db_path: Optional[str] = None) -> "DatabaseManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, db_path: Optional[str] = None) -> None:
        if DatabaseManager._initialized:
            return

        if db_path is None:
            import sys
            if getattr(sys, 'frozen', False):
                # Corriendo como ejecutable PyInstaller
                # Guardar la base de datos junto al ejecutable
                app_dir = Path(sys.executable).parent
            else:
                # Base de datos en el directorio del proyecto
                app_dir = Path(__file__).parent.parent
                
            db_path = str(app_dir / "data" / "asistencia.db")

        # Crear directorio si no existe
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

        self._engine = create_engine(
            f"sqlite:///{db_path}",
            echo=False,
            pool_pre_ping=True,
        )
        self._SessionFactory = sessionmaker(bind=self._engine)

        # Crear todas las tablas
        Base.metadata.create_all(self._engine)

        # Insertar configuración por defecto si no existe
        self._init_default_config()

        DatabaseManager._initialized = True

    def _init_default_config(self) -> None:
        """Inserta valores de configuración por defecto si no existen."""
        with self.get_session() as session:
            existing = session.query(Configuration).filter_by(clave="tolerancia_global").first()
            if existing is None:
                config = Configuration(clave="tolerancia_global", valor="2")
                session.add(config)
                session.commit()

    def get_session(self) -> Session:
        """Retorna una nueva sesión de base de datos."""
        return self._SessionFactory()

    def get_tolerance(self) -> int:
        """Obtiene la tolerancia global en minutos."""
        with self.get_session() as session:
            config = session.query(Configuration).filter_by(clave="tolerancia_global").first()
            if config is not None:
                return int(config.valor)
            return 2

    def set_tolerance(self, minutes: int) -> None:
        """Establece la tolerancia global en minutos."""
        with self.get_session() as session:
            config = session.query(Configuration).filter_by(clave="tolerancia_global").first()
            if config is not None:
                config.valor = str(minutes)
            else:
                config = Configuration(clave="tolerancia_global", valor=str(minutes))
                session.add(config)
            session.commit()

    def reset_schedules(self) -> None:
        """Elimina todos los horarios y empleados de la base de datos."""
        from database.models import Schedule, Employee, AttendanceRecord

        with self.get_session() as session:
            session.query(AttendanceRecord).delete()
            session.query(Schedule).delete()
            session.query(Employee).delete()
            session.commit()

    def get_employee_count(self) -> int:
        """Retorna la cantidad de empleados activos."""
        from database.models import Employee

        with self.get_session() as session:
            return session.query(Employee).filter_by(activo=True).count()

    def get_schedule_count(self) -> int:
        """Retorna la cantidad de registros de horarios."""
        from database.models import Schedule

        with self.get_session() as session:
            return session.query(Schedule).count()

    @classmethod
    def reset_instance(cls) -> None:
        """Resetea el singleton (útil para testing)."""
        cls._instance = None
        cls._initialized = False
