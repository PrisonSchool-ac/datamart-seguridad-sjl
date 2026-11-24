
from datetime import date
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import DimDelito, DimUbicacion, Fact

from app.ai_model import (
    entrenar_modelo,
    estimar_delitos,
    obtener_metricas,
)


# ============================================================
# CONFIGURACION DE LA API
# ============================================================

app = FastAPI(
    title="DataMart Seguridad SJL",
    description="Plataforma de analisis y estimacion por zonas.",
    version="1.3.0",
    docs_url=None,
    redoc_url=None,
)


# ============================================================
# CONFIGURACION CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ============================================================
# DOCUMENTACION PERSONALIZADA SWAGGER UI
# ============================================================

@app.get("/docs", include_in_schema=False)
def documentacion_personalizada():
    html = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DataMart Seguridad SJL | API</title>

    <link
        rel="stylesheet"
        href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css"
    >

    <style>
        :root {
            color-scheme: dark;
        }

        * {
            box-sizing: border-box;
        }

        body {
            margin: 0;
            background: #0b1220;
            color: #f8fafc;
            font-family: "Segoe UI", Arial, sans-serif;
        }

        .encabezado {
            padding: 32px 6%;
            background: linear-gradient(135deg, #111c30, #12372f);
            border-bottom: 2px solid #22c55e;
        }

        .marca {
            display: flex;
            align-items: center;
            gap: 16px;
        }

        .logo {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 58px;
            height: 58px;
            flex-shrink: 0;
            border-radius: 15px;
            background: #16a34a;
            color: white;
            font-size: 24px;
            font-weight: 800;
        }

        h1 {
            margin: 0;
            color: white;
            font-size: clamp(24px, 4vw, 35px);
        }

        .subtitulo {
            margin: 9px 0 0;
            color: #e2e8f0;
            font-size: 15px;
            line-height: 1.6;
        }

        .etiquetas {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 20px;
        }

        .etiqueta {
            padding: 7px 12px;
            border: 1px solid #4ade80;
            border-radius: 20px;
            background: #153b2c;
            color: #dcfce7;
            font-size: 12px;
            font-weight: 700;
        }

        main {
            max-width: 1500px;
            margin: 28px auto;
            padding: 0 24px;
        }

        .introduccion {
            margin-bottom: 22px;
            padding: 22px;
            border: 1px solid #475569;
            border-radius: 14px;
            background: #172438;
        }

        .introduccion h2 {
            margin-top: 0;
            color: white;
            font-size: 21px;
        }

        .introduccion p {
            color: #f1f5f9;
            line-height: 1.8;
        }

        .ayuda {
            color: #bbf7d0 !important;
            font-size: 13px;
        }

        #swagger-ui {
            padding: 20px;
            border: 1px solid #475569;
            border-radius: 14px;
            background: #111c2e;
        }

        #swagger-ui,
        #swagger-ui .info,
        #swagger-ui .info *,
        #swagger-ui .opblock *,
        #swagger-ui .opblock-tag,
        #swagger-ui .responses-wrapper *,
        #swagger-ui .parameters-container *,
        #swagger-ui table *,
        #swagger-ui label,
        #swagger-ui p,
        #swagger-ui span,
        #swagger-ui small {
            color: #f1f5f9;
        }

        #swagger-ui .information-container {
            display: none;
        }

        #swagger-ui .opblock {
            margin-bottom: 16px;
            overflow: hidden;
            border-radius: 11px;
            box-shadow: none;
        }

        #swagger-ui .opblock.opblock-get {
            background: #123039 !important;
            border: 1px solid #22a6a1 !important;
        }

        #swagger-ui .opblock.opblock-post {
            background: #153526 !important;
            border: 1px solid #35c879 !important;
        }

        #swagger-ui .opblock .opblock-summary-method {
            border-radius: 6px;
            color: white !important;
            font-weight: 800;
        }

        #swagger-ui .opblock-summary-path,
        #swagger-ui .opblock-summary-description,
        #swagger-ui .opblock-summary-path *,
        #swagger-ui .opblock-tag {
            color: white !important;
        }

        #swagger-ui .opblock .opblock-section-header {
            background: #293b52 !important;
        }

        #swagger-ui .opblock-section-header * {
            color: white !important;
        }

        #swagger-ui input,
        #swagger-ui select,
        #swagger-ui textarea {
            border: 1px solid #64748b !important;
            border-radius: 7px !important;
            background: #080f1c !important;
            color: white !important;
        }

        #swagger-ui select option {
            background: #111c2e;
            color: white;
        }

        #swagger-ui pre,
        #swagger-ui code,
        #swagger-ui .highlight-code,
        #swagger-ui .microlight {
            background: #080f1c !important;
            color: #f8fafc !important;
        }

        #swagger-ui .btn {
            border-radius: 7px;
            color: white !important;
            font-weight: 700;
        }

        #swagger-ui .btn.execute {
            background: #15803d !important;
            border-color: #4ade80 !important;
        }

        #swagger-ui .prop-type,
        #swagger-ui .prop-format {
            color: #86efac !important;
        }

        #swagger-ui a {
            color: #86efac !important;
        }

        .pie {
            padding: 25px;
            color: #e2e8f0;
            text-align: center;
            font-size: 13px;
        }

        .pie span {
            color: #86efac;
            font-weight: 700;
        }

        @media (max-width: 700px) {
            .encabezado {
                padding: 25px 18px;
            }

            .marca {
                align-items: flex-start;
            }

            .logo {
                width: 46px;
                height: 46px;
                font-size: 19px;
            }

            main {
                padding: 0 9px;
            }

            #swagger-ui {
                padding: 8px;
            }
        }
    </style>
</head>

<body>
    <header class="encabezado">
        <div class="marca">
            <div class="logo">SJL</div>
            <div>
                <h1>DataMart Seguridad SJL</h1>
                <p class="subtitulo">
                    Plataforma de inteligencia artificial y análisis por zonas
                </p>
            </div>
        </div>

        <div class="etiquetas">
            <span class="etiqueta">API REST</span>
            <span class="etiqueta">FastAPI</span>
            <span class="etiqueta">Machine Learning</span>
            <span class="etiqueta">Versión 1.3.0</span>
        </div>
    </header>

    <main>
        <section class="introduccion">
            <h2>Centro de documentación de la API</h2>
            <p>
                Consulta los servicios disponibles, revisa los parámetros
                y ejecuta solicitudes para probar las funcionalidades
                del sistema. Las respuestas JSON y los mensajes de
                validación se muestran a continuación.
            </p>
            <p class="ayuda">
                Selecciona un endpoint y pulsa Try it out para probarlo.
            </p>
        </section>

        <div id="swagger-ui"></div>

        <footer class="pie">
            DataMart Seguridad SJL · <span>API Analytics</span>
        </footer>
    </main>

    <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>

    <script>
        window.onload = function () {
            SwaggerUIBundle({
                url: "/openapi.json",
                dom_id: "#swagger-ui",
                deepLinking: true,
                displayRequestDuration: true,
                filter: true,
                defaultModelsExpandDepth: 2,
                defaultModelExpandDepth: 2,
                docExpansion: "list",
                showExtensions: true,
                showCommonExtensions: true,
                presets: [
                    SwaggerUIBundle.presets.apis
                ],
                layout: "BaseLayout"
            });
        };
    </script>
</body>
</html>
    """

    return HTMLResponse(content=html)


# ============================================================
# MODELO DE SOLICITUD DE ESTIMACION
# ============================================================

class SolicitudEstimacion(BaseModel):
    fecha: date
    zona: str = Field(min_length=1, max_length=100)


# ============================================================
# ENDPOINT: INICIO
# ============================================================

@app.get("/")
def inicio():
    return {
        "mensaje": "API de Seguridad SJL funcionando",
        "documentacion": "/docs",
        "datos": "Los endpoints de filtros consultan SQL Server; "
                 "las estimaciones dependen del modelo configurado.",
    }


# ============================================================
# ENDPOINT: SALUD
# ============================================================

@app.get("/salud")
def salud():
    return {"estado": "correcto"}


# ============================================================
# ENDPOINT: CONSULTAR METRICAS
# ============================================================

@app.get("/modelo/metricas")
def consultar_metricas():
    """Consulta las métricas guardadas sin volver a entrenar."""
    try:
        return obtener_metricas()
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"No se pudieron consultar las métricas: {error}",
        ) from error


# ============================================================
# ENDPOINT: ENTRENAR MODELO
# ============================================================

@app.post("/modelo/entrenar")
def entrenar():
    try:
        resultado = entrenar_modelo()

        return {
            "mensaje": "Modelo entrenado y evaluado correctamente",
            "metricas": {
                "mae": resultado["mae"],
                "rmse": resultado["rmse"],
                "filas_entrenamiento": resultado["filas_entrenamiento"],
                "filas_evaluacion": resultado["filas_evaluacion"],
            },
            "fecha_ultima": resultado["fecha_ultima"],
            "origen_datos": resultado["origen_datos"],
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"No se pudo entrenar el modelo: {error}",
        ) from error


# ============================================================
# ENDPOINT: ESTIMAR UNA ZONA
# ============================================================

@app.post("/modelo/estimar")
def estimar(solicitud: SolicitudEstimacion):
    try:
        return estimar_delitos(
            fecha=solicitud.fecha.isoformat(),
            zona=solicitud.zona,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"No se pudo generar la estimación: {error}",
        ) from error


# ============================================================
# ENDPOINT: ESTIMAR TODAS LAS ZONAS
# ============================================================

@app.get("/modelo/estimar-zonas")
def estimar_zonas(fecha: date):
    zonas = [
        "Campoy",
        "Canto Grande",
        "Huáscar",
        "Las Flores",
        "Zárate",
    ]

    resultados = []

    for zona in zonas:
        try:
            resultado = estimar_delitos(
                fecha=fecha.isoformat(),
                zona=zona,
            )
            resultados.append(resultado)

        except ValueError as error:
            raise HTTPException(
                status_code=400,
                detail=str(error),
            ) from error

        except Exception as error:
            raise HTTPException(
                status_code=500,
                detail=f"Error al estimar la zona {zona}: {error}",
            ) from error

    return {
        "fecha": fecha.isoformat(),
        "total_zonas": len(resultados),
        "resultados": resultados,
        "origen_datos": "según la configuración del modelo",
        "advertencia": (
            "Verifica el origen y la validación del modelo antes "
            "de interpretar estas estimaciones como pronósticos reales."
        ),
    }


# ============================================================
# ENDPOINT: DATOS PARA GRAFICOS DE ESTIMACIONES
# ============================================================

@app.get("/modelo/grafica")
def datos_grafica(fecha: date):
    zonas = [
        "Campoy",
        "Canto Grande",
        "Huáscar",
        "Las Flores",
        "Zárate",
    ]

    etiquetas = []
    cantidades = []
    estimaciones_decimales = []

    for zona in zonas:
        try:
            resultado = estimar_delitos(
                fecha=fecha.isoformat(),
                zona=zona,
            )

            etiquetas.append(zona)
            cantidades.append(resultado["cantidad_estimada"])
            estimaciones_decimales.append(
                resultado["estimacion_decimal"]
            )

        except ValueError as error:
            raise HTTPException(
                status_code=400,
                detail=str(error),
            ) from error

        except Exception as error:
            raise HTTPException(
                status_code=500,
                detail=f"Error al estimar la zona {zona}: {error}",
            ) from error

    return {
        "fecha": fecha.isoformat(),
        "etiquetas": etiquetas,
        "cantidades": cantidades,
        "estimaciones_decimales": estimaciones_decimales,
        "advertencia": (
            "Interpreta los valores de acuerdo con el origen de datos "
            "y la validación del modelo."
        ),
    }


# ============================================================
# ENDPOINT: OPCIONES PARA LOS FILTROS DEL DASHBOARD
# ============================================================

@app.get("/datos/filtros")
def obtener_opciones_filtros(
    db: Session = Depends(get_db),
):
    """
    Obtiene los tipos de delito y las zonas desde SQL Server.
    """
    try:
        tipos_delito = db.scalars(
            select(DimDelito.tipo_delito)
            .distinct()
            .where(DimDelito.tipo_delito.is_not(None))
            .order_by(DimDelito.tipo_delito)
        ).all()

        zonas = db.scalars(
            select(DimUbicacion.zona)
            .distinct()
            .where(DimUbicacion.zona.is_not(None))
            .order_by(DimUbicacion.zona)
        ).all()

        return {
            "tipos_delito": list(tipos_delito),
            "zonas": list(zonas),
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Error al consultar los filtros: {error}",
        ) from error


# ============================================================
# ENDPOINT: FILTRAR DELITOS DESDE SQL SERVER
# ============================================================

@app.get("/datos/filtrar")
def filtrar_delitos(
    tipo_delito: Optional[str] = None,
    zona: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Consulta y agrupa los delitos por tipo y zona.
    Ambos filtros son opcionales.
    """
    try:
        consulta = (
            select(
                DimDelito.tipo_delito.label("tipo_delito"),
                DimUbicacion.zona.label("zona"),
                func.sum(
                    Fact.cantidad_delitos
                ).label("cantidad"),
            )
            .select_from(Fact)
            .join(
                DimDelito,
                Fact.id_delito == DimDelito.id_delito,
            )
            .join(
                DimUbicacion,
                Fact.id_ubicacion == DimUbicacion.id_ubicacion,
            )
        )

        if tipo_delito:
            consulta = consulta.where(
                DimDelito.tipo_delito == tipo_delito
            )

        if zona:
            consulta = consulta.where(
                DimUbicacion.zona == zona
            )

        consulta = (
            consulta
            .group_by(
                DimDelito.tipo_delito,
                DimUbicacion.zona,
            )
            .order_by(
                DimDelito.tipo_delito,
                DimUbicacion.zona,
            )
        )

        filas = db.execute(consulta).all()

        resultados = [
            {
                "tipo_delito": fila.tipo_delito,
                "zona": fila.zona,
                "cantidad": int(fila.cantidad or 0),
            }
            for fila in filas
        ]

        return {
            "total_registros": len(resultados),
            "total_delitos": sum(
                fila["cantidad"] for fila in resultados
            ),
            "filtros": {
                "tipo_delito": tipo_delito,
                "zona": zona,
            },
            "resultados": resultados,
            "origen_datos": "SQL Server",
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Error al consultar los delitos: {error}",
        ) from error
