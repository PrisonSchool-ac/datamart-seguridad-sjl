"""ETL: Extracción (CSV) -> Transformación (limpieza + dimensiones) -> Carga (SQL Server)."""
import numpy as np
import pandas as pd
from sqlalchemy import delete

from .models import DIMENSIONES, DimDelito, DimHora, DimModalidad, DimTiempo, DimUbicacion, DimVictima, Fact

REQUIRED = [
    "fecha", "hora", "distrito", "zona", "sector", "referencia", "tipo_delito",
    "categoria_delito", "descripcion", "rango_edad", "genero", "tipo_victima",
    "modalidad_delictiva", "tipo_arma", "medio_utilizado",
]
DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def franja(h: int) -> str:
    if h < 6:
        return "Madrugada"
    if h < 12:
        return "Mañana"
    if h < 18:
        return "Tarde"
    return "Noche"


def run_etl(df_raw: pd.DataFrame, db) -> dict:
    faltan = [c for c in REQUIRED if c not in df_raw.columns]
    if faltan:
        raise ValueError(f"Faltan columnas en el CSV: {', '.join(faltan)}")

    # ---- Limpieza ----
    df = df_raw[REQUIRED].copy()
    leidos = len(df)
    df = df.dropna()
    for c in REQUIRED:
        df[c] = df[c].astype(str).str.strip()
    df["fecha_dt"] = pd.to_datetime(df["fecha"], errors="coerce")
    df["hora_dt"] = pd.to_datetime(df["hora"].str[:5], format="%H:%M", errors="coerce")
    df = df.dropna(subset=["fecha_dt", "hora_dt"]).drop_duplicates(subset=REQUIRED)
    if df.empty:
        raise ValueError("No quedaron registros válidos después de la limpieza.")
    df["fecha_k"] = df["fecha_dt"].dt.date
    df["hora_k"] = df["hora_dt"].dt.strftime("%H:%M")

    # ---- Dimensiones con claves sustitutas ----
    def dim(cols, id_name):
        d = df[cols].drop_duplicates().reset_index(drop=True)
        d.insert(0, id_name, d.index + 1)
        return d

    cols_delito = ["tipo_delito", "categoria_delito", "descripcion"]
    cols_ubic = ["distrito", "zona", "sector", "referencia"]
    cols_vict = ["rango_edad", "genero", "tipo_victima"]
    cols_mod = ["modalidad_delictiva", "tipo_arma", "medio_utilizado"]
    d_delito = dim(cols_delito, "id_delito")
    d_ubic = dim(cols_ubic, "id_ubicacion")
    d_vict = dim(cols_vict, "id_victima")
    d_mod = dim(cols_mod, "id_modalidad")
    d_tiempo = dim(["fecha_k"], "id_tiempo")
    d_hora = dim(["hora_k"], "id_hora")

    ts = pd.to_datetime(d_tiempo["fecha_k"])
    d_tiempo["fecha"] = d_tiempo["fecha_k"]
    d_tiempo["dia"] = ts.dt.day
    d_tiempo["dia_semana"] = ts.dt.dayofweek.map(lambda i: DIAS[i])
    d_tiempo["mes"] = ts.dt.month
    d_tiempo["trimestre"] = ts.dt.quarter
    d_tiempo["anio"] = ts.dt.year

    th = pd.to_datetime(d_hora["hora_k"], format="%H:%M")
    d_hora["hora"] = th.dt.time
    d_hora["hora_num"] = th.dt.hour
    d_hora["franja_horaria"] = d_hora["hora_num"].map(franja)
    d_hora["turno"] = d_hora["hora_num"].map(lambda h: "Diurno" if 6 <= h < 18 else "Nocturno")

    # ---- Tabla de hechos ----
    fact = (
        df.merge(d_delito, on=cols_delito)
        .merge(d_ubic, on=cols_ubic)
        .merge(d_vict, on=cols_vict)
        .merge(d_mod, on=cols_mod)
        .merge(d_tiempo[["id_tiempo", "fecha_k"]], on="fecha_k")
        .merge(d_hora[["id_hora", "hora_k"]], on="hora_k")
    )
    fact = fact[["id_delito", "id_ubicacion", "id_tiempo", "id_hora", "id_victima", "id_modalidad"]].reset_index(drop=True)
    fact.insert(0, "id_hecho", fact.index + 1)
    fact["cantidad_delitos"] = 1  # cada registro representa un delito

    # ---- Carga (recarga completa) ----
    db.execute(delete(Fact))
    for m in DIMENSIONES:
        db.execute(delete(m))
    cargas = [
        (DimDelito, d_delito), (DimUbicacion, d_ubic), (DimTiempo, d_tiempo),
        (DimHora, d_hora), (DimVictima, d_vict), (DimModalidad, d_mod), (Fact, fact),
    ]
    for model, d in cargas:
        cols = [c.name for c in model.__table__.columns]
        db.bulk_insert_mappings(model, d[cols].to_dict("records"))
    db.commit()

    return {
        "registros_leidos": leidos,
        "registros_cargados": len(fact),
        "registros_descartados": leidos - len(fact),
        "tablas": {m.__tablename__: len(d) for m, d in cargas},
    }


def generate_sample(n: int = 800, seed: int = 42) -> pd.DataFrame:
    """Datos SIMULADOS de San Juan de Lurigancho para probar el sistema."""
    rng = np.random.default_rng(seed)
    zonas = ["Canto Grande", "Zárate", "Campoy", "Huáscar", "Las Flores"]
    pz = [0.28, 0.18, 0.20, 0.14, 0.20]
    tipos = ["Robo", "Hurto", "Extorsión", "Asalto", "Vandalismo"]
    pt = [0.38, 0.22, 0.18, 0.12, 0.10]
    categoria = {"Robo": "Contra el patrimonio", "Hurto": "Contra el patrimonio",
                 "Extorsión": "Contra el patrimonio", "Asalto": "Contra la seguridad", "Vandalismo": "Daños"}
    modalidades = {
        "Robo": ["Arrebato", "Robo al paso", "Cogoteo"],
        "Hurto": ["Descuido", "Carterismo"],
        "Extorsión": ["Extorsión telefónica", "Cobro de cupos"],
        "Asalto": ["Asalto a mano armada", "Asalto en transporte"],
        "Vandalismo": ["Daño a propiedad", "Grafiti"],
    }
    ph = np.ones(24)
    ph[18:] = 3
    ph[:6] = 1.5
    ph = ph / ph.sum()
    fechas = pd.date_range("2026-01-01", "2026-07-31")

    filas = []
    for _ in range(n):
        tipo = rng.choice(tipos, p=pt)
        zona = rng.choice(zonas, p=pz)
        modalidad = rng.choice(modalidades[tipo])
        h = int(rng.choice(24, p=ph))
        filas.append({
            "fecha": fechas[int(rng.integers(len(fechas)))].strftime("%Y-%m-%d"),
            "hora": f"{h:02d}:{int(rng.integers(0, 60)):02d}",
            "distrito": "San Juan de Lurigancho",
            "zona": zona,
            "sector": f"Sector {int(rng.integers(1, 4))}",
            "referencia": f"Mz {chr(65 + int(rng.integers(0, 12)))} Lt {int(rng.integers(1, 30))}",
            "tipo_delito": tipo,
            "categoria_delito": categoria[tipo],
            "descripcion": f"{tipo} - {modalidad}",
            "rango_edad": rng.choice(["18-29", "30-44", "45-59", "60+"]),
            "genero": rng.choice(["Masculino", "Femenino"]),
            "tipo_victima": rng.choice(["Peatón", "Comerciante", "Transportista", "Ciudadano"]),
            "modalidad_delictiva": modalidad,
            "tipo_arma": rng.choice(["Ninguna", "Arma blanca", "Arma de fuego"]),
            "medio_utilizado": "Telefónico" if tipo == "Extorsión" else rng.choice(["A pie", "Motocicleta", "Vehículo"]),
        })
    return pd.DataFrame(filas)