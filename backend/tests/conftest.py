"""Utilidades compartidas por las pruebas."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

DATOS_PRUEBA = Path(__file__).resolve().parents[2] / "datos_prueba"

CABECERA_FACTURAS = (
    "id_factura,nit_proveedor,fecha_factura,concepto,base_gravable,tarifa_iva,"
    "valor_iva,tarifa_retencion,valor_retencion,total_factura"
)
CABECERA_CONTABILIDAD = (
    "id_factura,fecha_contabilizacion,cuenta_contable,centro_costo,"
    "valor_debito,valor_credito,estado"
)


def csv_facturas(*filas: str) -> bytes:
    return ("\n".join((CABECERA_FACTURAS, *filas)) + "\n").encode("utf-8")


def csv_contabilidad(*filas: str) -> bytes:
    return ("\n".join((CABECERA_CONTABILIDAD, *filas)) + "\n").encode("utf-8")


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def facturas_reales() -> bytes:
    return (DATOS_PRUEBA / "facturas.csv").read_bytes()


@pytest.fixture
def contabilidad_real() -> bytes:
    return (DATOS_PRUEBA / "contabilidad.csv").read_bytes()
