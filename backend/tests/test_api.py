"""Pruebas de la API: flujo completo y manejo de errores."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import csv_contabilidad, csv_facturas

ENDPOINT = "/api/v1/conciliacion"


def subir(client: TestClient, facturas: bytes, contabilidad: bytes):
    return client.post(
        ENDPOINT,
        files={
            "facturas": ("facturas.csv", facturas, "text/csv"),
            "contabilidad": ("contabilidad.csv", contabilidad, "text/csv"),
        },
    )


def test_health(client: TestClient):
    respuesta = client.get("/api/v1/health")

    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "ok"


def test_catalogo_de_reglas(client: TestClient):
    respuesta = client.get("/api/v1/reglas")

    assert respuesta.status_code == 200
    reglas = respuesta.json()
    codigos = {r["codigo"] for r in reglas}
    assert {
        "IVA_CALCULADO_NO_COINCIDE",
        "TOTAL_FACTURA_NO_COINCIDE",
        "FACTURA_DUPLICADA",
        "SIN_REGISTRO_CONTABLE",
    } <= codigos


def test_conciliacion_con_archivos_del_caso(
    client: TestClient, facturas_reales: bytes, contabilidad_real: bytes
):
    respuesta = subir(client, facturas_reales, contabilidad_real)

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    resumen = cuerpo["resumen"]

    assert resumen["total_facturas"] == len(cuerpo["detalle"])
    assert (
        resumen["facturas_correctas"] + resumen["facturas_con_inconsistencia"]
        == resumen["total_facturas"]
    )
    # Los archivos del caso traen, por diseño, duplicados y faltantes.
    assert resumen["facturas_duplicadas"] > 0
    assert resumen["facturas_sin_registro_contable"] > 0
    assert resumen["total_inconsistencias"] > 0

    # Toda factura con inconsistencia debe explicar su causa.
    for factura in cuerpo["detalle"]:
        if factura["clasificacion"] == "Con inconsistencia":
            assert factura["hallazgos"], factura["id_factura"]
            assert factura["causas"]
        else:
            assert factura["hallazgos"] == []


def test_la_suma_por_regla_coincide_con_el_total_de_inconsistencias(
    client: TestClient, facturas_reales: bytes, contabilidad_real: bytes
):
    resumen = subir(client, facturas_reales, contabilidad_real).json()["resumen"]

    assert sum(r["cantidad"] for r in resumen["por_regla"]) == (
        resumen["total_inconsistencias"]
    )
    assert sum(resumen["por_severidad"].values()) == resumen["total_inconsistencias"]


def test_trazabilidad_del_calculo_en_el_detalle(client: TestClient):
    facturas = csv_facturas(
        "FAC-001,900123456,2026-01-10,Consultoría,1000000,0.19,190000,0.04,40000,1150000"
    )
    contabilidad = csv_contabilidad(
        "FAC-001,2026-01-12,511005,CC1001,1150000,1150000,Contabilizada"
    )

    factura = subir(client, facturas, contabilidad).json()["detalle"][0]

    assert factura["iva_esperado"] == 190000.0
    assert factura["retencion_esperada"] == 40000.0
    assert factura["total_esperado"] == 1150000.0
    assert factura["clasificacion"] == "Correcta"
    assert factura["contabilizada"] is True


def test_falta_un_archivo(client: TestClient):
    respuesta = client.post(
        ENDPOINT,
        files={"facturas": ("facturas.csv", csv_facturas(), "text/csv")},
    )

    assert respuesta.status_code in (400, 422)
    assert "error" in respuesta.json()


def test_archivo_con_extension_no_csv(client: TestClient):
    respuesta = client.post(
        ENDPOINT,
        files={
            "facturas": ("facturas.xlsx", b"contenido binario", "application/vnd.ms-excel"),
            "contabilidad": (
                "contabilidad.csv",
                csv_contabilidad("FAC-001,2026-01-12,511005,CC1001,1,1,Contabilizada"),
                "text/csv",
            ),
        },
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["error"]["codigo"] == "ARCHIVO_INVALIDO"


def test_archivo_sin_columnas_obligatorias(client: TestClient):
    incompleto = b"id_factura,total\nFAC-001,1000\n"
    respuesta = client.post(
        ENDPOINT,
        files={
            "facturas": ("facturas.csv", incompleto, "text/csv"),
            "contabilidad": (
                "contabilidad.csv",
                csv_contabilidad("FAC-001,2026-01-12,511005,CC1001,1,1,Contabilizada"),
                "text/csv",
            ),
        },
    )

    assert respuesta.status_code == 422
    error = respuesta.json()["error"]
    assert error["codigo"] == "ESTRUCTURA_INVALIDA"
    assert "nit_proveedor" in error["detalle"]["columnas_faltantes"]


def test_archivo_vacio(client: TestClient):
    respuesta = client.post(
        ENDPOINT,
        files={
            "facturas": ("facturas.csv", b"", "text/csv"),
            "contabilidad": (
                "contabilidad.csv",
                csv_contabilidad("FAC-001,2026-01-12,511005,CC1001,1,1,Contabilizada"),
                "text/csv",
            ),
        },
    )

    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["codigo"] == "ARCHIVO_VACIO"


def test_archivo_solo_con_encabezados(client: TestClient):
    respuesta = client.post(
        ENDPOINT,
        files={
            "facturas": ("facturas.csv", csv_facturas(), "text/csv"),
            "contabilidad": (
                "contabilidad.csv",
                csv_contabilidad("FAC-001,2026-01-12,511005,CC1001,1,1,Contabilizada"),
                "text/csv",
            ),
        },
    )

    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["codigo"] == "ARCHIVO_VACIO"


def test_csv_con_punto_y_coma_y_codificacion_latin1(client: TestClient):
    """Un export de Excel en español debe procesarse sin configuración extra."""
    facturas = (
        "id_factura;nit_proveedor;fecha_factura;concepto;base_gravable;tarifa_iva;"
        "valor_iva;tarifa_retencion;valor_retencion;total_factura\n"
        "FAC-001;900123456;10/01/2026;Consultoría técnica;1000000;0,19;190000;"
        "0,04;40000;1150000\n"
    ).encode("latin-1")
    contabilidad = (
        "id_factura;fecha_contabilizacion;cuenta_contable;centro_costo;"
        "valor_debito;valor_credito;estado\n"
        "FAC-001;12/01/2026;511005;CC1001;1150000;1150000;Contabilizada\n"
    ).encode("latin-1")

    respuesta = subir(client, facturas, contabilidad)

    assert respuesta.status_code == 200
    detalle = respuesta.json()["detalle"][0]
    assert detalle["clasificacion"] == "Correcta"
    assert detalle["concepto"] == "Consultoría técnica"
