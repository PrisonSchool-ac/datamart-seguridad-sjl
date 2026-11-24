
"""Modelo de IA para estimar registros diarios por zona.
Los datos actuales son simulados.
"""

import pandas as pd
from sqlalchemy import text
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

from .db import engine


_modelo = None
_columnas = []
_zonas = []
_fecha_minima = None
_fecha_maxima = None
_metricas = None


def cargar_datos():
    """Consulta los registros diarios por zona en SQL Server."""
    consulta = text("""
        SELECT
            t.fecha,
            u.zona,
            SUM(f.cantidad_delitos) AS cantidad_delitos
        FROM fact_delitos AS f
        INNER JOIN dim_tiempo AS t
            ON f.id_tiempo = t.id_tiempo
        INNER JOIN dim_ubicacion AS u
            ON f.id_ubicacion = u.id_ubicacion
        GROUP BY t.fecha, u.zona
        ORDER BY t.fecha, u.zona
    """)

    with engine.connect() as conexion:
        df = pd.read_sql(consulta, conexion)

    if df.empty:
        raise ValueError("No hay datos disponibles para entrenar el modelo.")

    df["fecha"] = pd.to_datetime(df["fecha"])
    return df


def preparar_datos(df):
    """Construye una fila por día y zona, incluidos los días con cero registros."""
    fechas = pd.date_range(
        df["fecha"].min(),
        df["fecha"].max(),
        freq="D",
    )
    zonas = sorted(df["zona"].dropna().unique())

    indice = pd.MultiIndex.from_product(
        [fechas, zonas],
        names=["fecha", "zona"],
    )

    df_diario = (
        df.set_index(["fecha", "zona"])["cantidad_delitos"]
        .reindex(indice, fill_value=0)
        .rename("cantidad_delitos")
        .reset_index()
    )

    df_diario["dia_semana"] = df_diario["fecha"].dt.dayofweek
    df_diario["mes"] = df_diario["fecha"].dt.month
    df_diario["dia_mes"] = df_diario["fecha"].dt.day

    X = pd.get_dummies(
        df_diario[["zona", "dia_semana", "mes", "dia_mes"]],
        columns=["zona"],
        dtype=int,
    )
    y = df_diario["cantidad_delitos"]

    return df_diario, X, y, zonas


def entrenar_modelo():
    """Entrena, evalúa y conserva el modelo y sus métricas."""
    global _modelo, _columnas, _zonas
    global _fecha_minima, _fecha_maxima, _metricas

    df = cargar_datos()
    df_diario, X, y, zonas = preparar_datos(df)

    if len(df_diario) < 20 or y.nunique() < 2:
        raise ValueError(
            "Hay pocos datos o poca variación para evaluar el modelo."
        )

    # Separación cronológica: las fechas posteriores se reservan para evaluar.
    corte = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:corte], X.iloc[corte:]
    y_train, y_test = y.iloc[:corte], y.iloc[corte:]

    modelo = RandomForestRegressor(
        n_estimators=200,
        random_state=42,
        min_samples_leaf=2,
    )
    modelo.fit(X_train, y_train)

    predicciones = modelo.predict(X_test)

    mae = mean_absolute_error(y_test, predicciones)
    rmse = mean_squared_error(y_test, predicciones) ** 0.5

    # Guardar las métricas de la evaluación.
    metricas = {
        "mae": round(float(mae), 3),
        "rmse": round(float(rmse), 3),
        "filas_entrenamiento": len(X_train),
        "filas_evaluacion": len(X_test),
    }

    # Entrenar el modelo definitivo con todos los datos disponibles.
    modelo.fit(X, y)

    # Conservar el modelo y los datos necesarios para estimar.
    _modelo = modelo
    _columnas = list(X.columns)
    _zonas = list(zonas)
    _fecha_minima = df_diario["fecha"].min().date()
    _fecha_maxima = df_diario["fecha"].max().date()
    _metricas = metricas

    return {
        "modelo": _modelo,
        "columnas": _columnas,
        **_metricas,
        "zonas": _zonas,
        "fecha_ultima": str(_fecha_maxima),
        "origen_datos": "simulados; verificar antes de uso real",
    }


def obtener_metricas():
    """Devuelve las métricas guardadas sin volver a entrenar el modelo."""
    if _metricas is None:
        return {
            "disponible": False,
            "mensaje": (
                "No hay métricas disponibles en esta ejecución. "
                "Ejecuta POST /modelo/entrenar para generarlas."
            ),
            "metricas": None,
            "fecha_ultima": None,
            "origen_datos": "simulados; verificar antes de uso real",
        }

    return {
        "disponible": True,
        "metricas": _metricas.copy(),
        "fecha_ultima": str(_fecha_maxima),
        "origen_datos": "simulados; verificar antes de uso real",
    }


def estimar_delitos(fecha: str, zona: str):
    """Estima la cantidad de registros para una fecha y zona conocidas."""
    if _modelo is None:
        entrenar_modelo()

    zona = zona.strip()

    if zona not in _zonas:
        raise ValueError(
            f"Zona no reconocida. Zonas disponibles: {', '.join(_zonas)}"
        )

    fecha_dt = pd.to_datetime(fecha, errors="coerce")

    if pd.isna(fecha_dt):
        raise ValueError("La fecha no es válida. Usa el formato AAAA-MM-DD.")

    entrada = pd.DataFrame([{
        "zona": zona,
        "dia_semana": fecha_dt.dayofweek,
        "mes": fecha_dt.month,
        "dia_mes": fecha_dt.day,
    }])

    X_nuevo = pd.get_dummies(
        entrada,
        columns=["zona"],
        dtype=int,
    )

    # Mantener exactamente las columnas usadas durante el entrenamiento.
    X_nuevo = X_nuevo.reindex(columns=_columnas, fill_value=0)

    prediccion = float(_modelo.predict(X_nuevo)[0])
    prediccion = max(0.0, prediccion)

    fuera_del_periodo = (
        fecha_dt.date() < _fecha_minima
        or fecha_dt.date() > _fecha_maxima
    )

    return {
        "fecha": str(fecha_dt.date()),
        "zona": zona,
        "cantidad_estimada": round(prediccion),
        "estimacion_decimal": round(prediccion, 2),
        "periodo_entrenamiento": {
            "desde": str(_fecha_minima),
            "hasta": str(_fecha_maxima),
        },
        "fuera_del_periodo_entrenado": fuera_del_periodo,
        "origen_datos": "simulados",
        "advertencia": (
            "Estimación demostrativa; no representa un pronóstico validado "
            "de delincuencia real."
        ),
    }
