"""
uvicorn app.main:app --reload --port 8000
Documentación en http://localhost:8000/docs
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.requests import Request

from app.api.routes import router
from app.config import get_settings
from app.core.errors import (
    ErrorConciliador,
    manejar_error_conciliador,
    manejar_error_inesperado,
)

settings = get_settings()

app = FastAPI(
    title=settings.app_nombre,
    version=settings.app_version,
    description=(
        "API que cruza el archivo de facturas de proveedores con el de "
        "registros contables, aplica las reglas de validación tributaria y "
        "devuelve un resumen y el detalle de las inconsistencias."
    ),
    contact={"name": "Gerencia de Evolución Contable y Tributaria"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origenes,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.add_exception_handler(ErrorConciliador, manejar_error_conciliador)
app.add_exception_handler(Exception, manejar_error_inesperado)


@app.exception_handler(RequestValidationError)
async def manejar_validacion(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    # Para que los errores de FastAPI salgan con el mismo contrato que los míos.
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "codigo": "SOLICITUD_INVALIDA",
                "mensaje": (
                    "La solicitud no es válida. Verifique que está enviando los "
                    "dos archivos CSV en los campos 'facturas' y 'contabilidad'."
                ),
                "detalle": {"errores": _simplificar(exc.errors())},
            }
        },
    )


def _simplificar(errores: list[dict]) -> list[dict]:
    return [
        {
            "campo": ".".join(str(p) for p in error.get("loc", ())),
            "mensaje": error.get("msg", ""),
        }
        for error in errores
    ]


@app.get("/", include_in_schema=False)
def raiz() -> RedirectResponse:
    return RedirectResponse(url="/docs")


app.include_router(router)
