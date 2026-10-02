from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile

from app.config import Settings, get_settings
from app.core.errors import ArchivoInvalidoError
from app.domain.reglas import (
    CATALOGO_REGLAS,
    COLUMNAS_CONTABILIDAD,
    COLUMNAS_FACTURAS,
)
from app.models.schemas import (
    ConciliacionResponse,
    ErrorResponse,
    HealthResponse,
    ReglaSchema,
)
from app.services.conciliador import conciliar
from app.services.csv_reader import leer_csv
from app.services.respuesta import construir_respuesta

router = APIRouter(prefix="/api/v1", tags=["conciliación"])

SettingsDep = Annotated[Settings, Depends(get_settings)]

RESPUESTAS_ERROR: dict[int | str, dict] = {
    400: {"model": ErrorResponse, "description": "Archivo inválido o ilegible"},
    422: {"model": ErrorResponse, "description": "Estructura o contenido inválido"},
}


@router.get("/health", response_model=HealthResponse, summary="Estado del servicio")
def health(settings: SettingsDep) -> HealthResponse:
    return HealthResponse(
        estado="ok",
        aplicacion=settings.app_nombre,
        version=settings.app_version,
    )


@router.get(
    "/reglas",
    response_model=list[ReglaSchema],
    summary="Catálogo de reglas de validación",
)
def listar_reglas() -> list[ReglaSchema]:
    return [
        ReglaSchema(
            codigo=regla.codigo,
            nombre=regla.nombre,
            descripcion=regla.descripcion,
            severidad=regla.severidad.value,
            categoria=regla.categoria,
        )
        for regla in CATALOGO_REGLAS
    ]


async def _leer_subida(
    archivo: UploadFile | None,
    etiqueta: str,
    columnas: tuple[str, ...],
):
    if archivo is None or not archivo.filename:
        raise ArchivoInvalidoError(
            f"No se recibió el archivo de {etiqueta}.",
            {"campo": etiqueta},
        )

    contenido = await archivo.read()
    return leer_csv(
        contenido=contenido,
        nombre=archivo.filename,
        columnas_requeridas=columnas,
    )


@router.post(
    "/conciliacion",
    response_model=ConciliacionResponse,
    responses=RESPUESTAS_ERROR,
    summary="Procesa facturas.csv y contabilidad.csv y devuelve resumen + detalle",
)
async def procesar_conciliacion(
    settings: SettingsDep,
    facturas: Annotated[UploadFile, File(description="Archivo facturas.csv")] = None,
    contabilidad: Annotated[
        UploadFile, File(description="Archivo contabilidad.csv")
    ] = None,
) -> ConciliacionResponse:
    """Cruza ambos archivos, aplica las reglas y devuelve el resultado."""
    
    archivo_facturas = await _leer_subida(facturas, "facturas", COLUMNAS_FACTURAS)
    archivo_contabilidad = await _leer_subida(
        contabilidad, "contabilidad", COLUMNAS_CONTABILIDAD
    )

    resultado = conciliar(
        archivo_facturas=archivo_facturas,
        archivo_contabilidad=archivo_contabilidad,
        tolerancia=settings.tolerancia_pesos,
    )

    return construir_respuesta(
        resultado=resultado,
        archivo_facturas=archivo_facturas,
        archivo_contabilidad=archivo_contabilidad,
        tolerancia=settings.tolerancia_pesos,
    )
