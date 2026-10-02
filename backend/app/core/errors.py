from __future__ import annotations

from fastapi import Request, status
from fastapi.responses import JSONResponse


class ErrorConciliador(Exception):
    """Error de negocio previsible, que sí se le puede mostrar al usuario."""

    codigo: str = "ERROR_CONCILIADOR"
    http_status: int = status.HTTP_400_BAD_REQUEST

    def __init__(self, mensaje: str, detalle: dict | None = None) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.detalle = detalle or {}


class ArchivoInvalidoError(ErrorConciliador):
    codigo = "ARCHIVO_INVALIDO"
    http_status = status.HTTP_400_BAD_REQUEST


class EstructuraInvalidaError(ErrorConciliador):
    codigo = "ESTRUCTURA_INVALIDA"
    http_status = status.HTTP_422_UNPROCESSABLE_ENTITY


class ArchivoVacioError(ErrorConciliador):
    codigo = "ARCHIVO_VACIO"
    http_status = status.HTTP_422_UNPROCESSABLE_ENTITY


async def manejar_error_conciliador(
    _request: Request, exc: ErrorConciliador
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.http_status,
        content={
            "error": {
                "codigo": exc.codigo,
                "mensaje": exc.mensaje,
                "detalle": exc.detalle,
            }
        },
    )


async def manejar_error_inesperado(_request: Request, exc: Exception) -> JSONResponse:
    # Red de seguridad: pase lo que pase, nunca devolver el stacktrace.
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "codigo": "ERROR_INTERNO",
                "mensaje": (
                    "Ocurrió un error inesperado al procesar la solicitud. "
                    "Revise los archivos e intente nuevamente."
                ),
                "detalle": {"tipo": type(exc).__name__},
            }
        },
    )
