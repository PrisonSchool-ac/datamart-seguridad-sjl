"""Esquema estrella del Data Mart (Kimball). Las claves sustitutas las genera el ETL."""
from sqlalchemy import Date, ForeignKey, Integer, String, Time
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def pk():
    return mapped_column(Integer, primary_key=True, autoincrement=False)


class DimDelito(Base):
    __tablename__ = "dim_delito"
    id_delito: Mapped[int] = pk()
    tipo_delito: Mapped[str] = mapped_column(String(100))
    categoria_delito: Mapped[str] = mapped_column(String(100))
    descripcion: Mapped[str] = mapped_column(String(255))


class DimUbicacion(Base):
    __tablename__ = "dim_ubicacion"
    id_ubicacion: Mapped[int] = pk()
    distrito: Mapped[str] = mapped_column(String(100))
    zona: Mapped[str] = mapped_column(String(100))
    sector: Mapped[str] = mapped_column(String(100))
    referencia: Mapped[str] = mapped_column(String(255))


class DimTiempo(Base):
    __tablename__ = "dim_tiempo"
    id_tiempo: Mapped[int] = pk()
    fecha: Mapped[object] = mapped_column(Date)
    dia: Mapped[int] = mapped_column(Integer)
    dia_semana: Mapped[str] = mapped_column(String(20))
    mes: Mapped[int] = mapped_column(Integer)
    trimestre: Mapped[int] = mapped_column(Integer)
    anio: Mapped[int] = mapped_column(Integer)


class DimHora(Base):
    __tablename__ = "dim_hora"
    id_hora: Mapped[int] = pk()
    hora: Mapped[object] = mapped_column(Time)
    hora_num: Mapped[int] = mapped_column(Integer)
    franja_horaria: Mapped[str] = mapped_column(String(50))
    turno: Mapped[str] = mapped_column(String(50))


class DimVictima(Base):
    __tablename__ = "dim_victima"
    id_victima: Mapped[int] = pk()
    rango_edad: Mapped[str] = mapped_column(String(50))
    genero: Mapped[str] = mapped_column(String(50))
    tipo_victima: Mapped[str] = mapped_column(String(100))


class DimModalidad(Base):
    __tablename__ = "dim_modalidad"
    id_modalidad: Mapped[int] = pk()
    modalidad_delictiva: Mapped[str] = mapped_column(String(100))
    tipo_arma: Mapped[str] = mapped_column(String(100))
    medio_utilizado: Mapped[str] = mapped_column(String(100))


class Fact(Base):
    __tablename__ = "fact_delitos"
    id_hecho: Mapped[int] = pk()
    id_delito: Mapped[int] = mapped_column(ForeignKey("dim_delito.id_delito"))
    id_ubicacion: Mapped[int] = mapped_column(ForeignKey("dim_ubicacion.id_ubicacion"))
    id_tiempo: Mapped[int] = mapped_column(ForeignKey("dim_tiempo.id_tiempo"))
    id_hora: Mapped[int] = mapped_column(ForeignKey("dim_hora.id_hora"))
    id_victima: Mapped[int] = mapped_column(ForeignKey("dim_victima.id_victima"))
    id_modalidad: Mapped[int] = mapped_column(ForeignKey("dim_modalidad.id_modalidad"))
    cantidad_delitos: Mapped[int] = mapped_column(Integer, default=1)


# Orden de carga: dimensiones primero; de borrado: hechos primero.
DIMENSIONES = [DimDelito, DimUbicacion, DimTiempo, DimHora, DimVictima, DimModalidad]