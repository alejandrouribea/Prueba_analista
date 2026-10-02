"""Una prueba por cada regla de negocio."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.domain.reglas import COLUMNAS_CONTABILIDAD, COLUMNAS_FACTURAS, Clasificacion
from app.services.conciliador import conciliar
from app.services.csv_reader import leer_csv, parsear_decimal, parsear_fecha
from tests.conftest import csv_contabilidad, csv_facturas

TOLERANCIA = Decimal("1")


def ejecutar(filas_facturas: list[str], filas_contabilidad: list[str]):
    facturas = leer_csv(csv_facturas(*filas_facturas), "facturas.csv", COLUMNAS_FACTURAS)
    contabilidad = leer_csv(
        csv_contabilidad(*filas_contabilidad), "contabilidad.csv", COLUMNAS_CONTABILIDAD
    )
    return conciliar(facturas, contabilidad, TOLERANCIA)


def codigos(evaluada) -> set[str]:
    return {h.codigo for h in evaluada.hallazgos}


FACTURA_OK = (
    "FAC-001,900123456,2026-01-10,Consultoría profesional,"
    "1000000,0.19,190000,0.04,40000,1150000"
)
CONTABILIDAD_OK = "FAC-001,2026-01-12,511005,CC1001,1150000,1150000,Contabilizada"


def test_factura_sin_novedades_se_clasifica_como_correcta():
    resultado = ejecutar([FACTURA_OK], [CONTABILIDAD_OK])
    evaluada = resultado.facturas[0]

    assert evaluada.clasificacion is Clasificacion.CORRECTA
    assert evaluada.hallazgos == []
    assert evaluada.iva_esperado == Decimal("190000.00")
    assert evaluada.retencion_esperada == Decimal("40000.00")
    assert evaluada.total_esperado == Decimal("1150000.00")


def test_iva_mal_liquidado_se_detecta_con_su_diferencia():
    # Base 1.000.000 al 19% debería dar 190.000, no 200.000.
    fila = (
        "FAC-002,900123456,2026-01-10,Soporte técnico,"
        "1000000,0.19,200000,0.04,40000,1160000"
    )
    resultado = ejecutar([fila], ["FAC-002,2026-01-12,511005,CC1001,1160000,1160000,Contabilizada"])
    evaluada = resultado.facturas[0]

    assert "IVA_CALCULADO_NO_COINCIDE" in codigos(evaluada)
    assert evaluada.iva_esperado == Decimal("190000.00")
    assert evaluada.diferencia_iva == Decimal("10000.00")
    assert evaluada.clasificacion is Clasificacion.CON_INCONSISTENCIA


def test_iva_al_cero_por_ciento_es_valido():
    fila = "FAC-003,900123456,2026-01-10,Arrendamiento,1000000,0.0,0,0.0,0,1000000"
    resultado = ejecutar([fila], ["FAC-003,2026-01-12,511005,CC1001,1000000,1000000,Contabilizada"])

    assert resultado.facturas[0].clasificacion is Clasificacion.CORRECTA


def test_total_mal_liquidado_se_detecta():
    fila = (
        "FAC-004,900123456,2026-01-10,Capacitación,"
        "1000000,0.19,190000,0.04,40000,1200000"
    )
    resultado = ejecutar([fila], ["FAC-004,2026-01-12,511005,CC1001,1200000,1200000,Contabilizada"])
    evaluada = resultado.facturas[0]

    assert "TOTAL_FACTURA_NO_COINCIDE" in codigos(evaluada)
    assert evaluada.total_esperado == Decimal("1150000.00")
    assert evaluada.diferencia_total == Decimal("50000.00")


def test_retencion_mal_liquidada_se_detecta():
    # 4% sobre 1.000.000 son 40.000, no 50.000.
    fila = (
        "FAC-005,900123456,2026-01-10,Capacitación,"
        "1000000,0.19,190000,0.04,50000,1140000"
    )
    resultado = ejecutar([fila], ["FAC-005,2026-01-12,511005,CC1001,1140000,1140000,Contabilizada"])
    evaluada = resultado.facturas[0]

    assert "RETENCION_CALCULADA_NO_COINCIDE" in codigos(evaluada)
    assert evaluada.retencion_esperada == Decimal("40000.00")
    # El total sí es coherente con los valores reportados.
    assert "TOTAL_FACTURA_NO_COINCIDE" not in codigos(evaluada)


def test_diferencia_dentro_de_la_tolerancia_no_genera_hallazgo():
    # 1 peso de diferencia por redondeo: se acepta.
    fila = (
        "FAC-006,900123456,2026-01-10,Soporte técnico,"
        "1000000,0.19,190001,0.04,40000,1150001"
    )
    resultado = ejecutar([fila], ["FAC-006,2026-01-12,511005,CC1001,1150001,1150001,Contabilizada"])

    assert resultado.facturas[0].clasificacion is Clasificacion.CORRECTA


def test_factura_duplicada_marca_todas_las_ocurrencias():
    resultado = ejecutar([FACTURA_OK, FACTURA_OK], [CONTABILIDAD_OK])

    assert len(resultado.facturas) == 2
    for indice, evaluada in enumerate(resultado.facturas, start=1):
        assert "FACTURA_DUPLICADA" in codigos(evaluada)
        assert evaluada.ocurrencia == indice
        assert evaluada.total_ocurrencias == 2


def test_factura_sin_registro_contable():
    otra = "FAC-999,2026-01-12,511005,CC1001,500000,500000,Contabilizada"
    resultado = ejecutar([FACTURA_OK], [otra])
    evaluada = resultado.facturas[0]

    assert "SIN_REGISTRO_CONTABLE" in codigos(evaluada)
    assert evaluada.registro_principal is None


def test_registro_contable_sin_factura_se_reporta_aparte():
    huerfano = "FAC-888,2026-01-12,511005,CC1001,500000,500000,Contabilizada"
    resultado = ejecutar([FACTURA_OK], [CONTABILIDAD_OK, huerfano])

    assert [r.id_factura for r in resultado.contabilidad_sin_factura] == ["FAC-888"]


def test_registro_contable_duplicado():
    resultado = ejecutar([FACTURA_OK], [CONTABILIDAD_OK, CONTABILIDAD_OK])

    assert "REGISTRO_CONTABLE_DUPLICADO" in codigos(resultado.facturas[0])


def test_campos_obligatorios_vacios():
    fila = "FAC-007,,2026-01-10,,1000000,0.19,190000,0.04,40000,1150000"
    resultado = ejecutar([fila], ["FAC-007,2026-01-12,511005,CC1001,1150000,1150000,Contabilizada"])
    evaluada = resultado.facturas[0]

    assert "CAMPO_OBLIGATORIO_VACIO" in codigos(evaluada)
    hallazgo = next(h for h in evaluada.hallazgos if h.codigo == "CAMPO_OBLIGATORIO_VACIO")
    assert set(hallazgo.campos) == {"nit_proveedor", "concepto"}


def test_valor_no_numerico():
    fila = (
        "FAC-008,900123456,2026-01-10,Soporte técnico,"
        "mil pesos,0.19,190000,0.04,40000,1150000"
    )
    resultado = ejecutar([fila], ["FAC-008,2026-01-12,511005,CC1001,1150000,1150000,Contabilizada"])

    assert "VALOR_NO_NUMERICO" in codigos(resultado.facturas[0])


def test_diferencia_entre_valor_contabilizado_y_total_factura():
    contable = "FAC-001,2026-01-12,511005,CC1001,1100000,1100000,Contabilizada"
    resultado = ejecutar([FACTURA_OK], [contable])
    evaluada = resultado.facturas[0]

    assert "DIFERENCIA_VALOR_CONTABILIZADO" in codigos(evaluada)
    assert evaluada.diferencia_contable == Decimal("-50000.00")


def test_partida_doble_descuadrada():
    contable = "FAC-001,2026-01-12,511005,CC1001,1150000,1000000,Contabilizada"
    resultado = ejecutar([FACTURA_OK], [contable])

    assert "PARTIDA_DOBLE_DESCUADRADA" in codigos(resultado.facturas[0])


def test_estado_pendiente_de_contabilizar():
    contable = "FAC-001,2026-01-12,511005,CC1001,1150000,1150000,Pendiente"
    resultado = ejecutar([FACTURA_OK], [contable])

    assert "ESTADO_NO_CONTABILIZADO" in codigos(resultado.facturas[0])


def test_contabilizacion_anterior_a_la_factura():
    contable = "FAC-001,2026-01-05,511005,CC1001,1150000,1150000,Contabilizada"
    resultado = ejecutar([FACTURA_OK], [contable])

    assert "FECHA_CONTABILIZACION_ANTERIOR" in codigos(resultado.facturas[0])


def test_tarifa_iva_no_vigente():
    fila = (
        "FAC-009,900123456,2026-01-10,Soporte técnico,"
        "1000000,0.16,160000,0.04,40000,1120000"
    )
    resultado = ejecutar([fila], ["FAC-009,2026-01-12,511005,CC1001,1120000,1120000,Contabilizada"])

    assert "TARIFA_IVA_NO_VIGENTE" in codigos(resultado.facturas[0])


def test_tarifa_retencion_no_parametrizada():
    fila = (
        "FAC-010,900123456,2026-01-10,Soporte técnico,"
        "1000000,0.19,190000,0.11,110000,1080000"
    )
    resultado = ejecutar([fila], ["FAC-010,2026-01-12,511005,CC1001,1080000,1080000,Contabilizada"])

    assert "TARIFA_RETENCION_NO_PARAMETRIZADA" in codigos(resultado.facturas[0])


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("1000000", Decimal("1000000")),
        ("1.234.567,89", Decimal("1234567.89")),
        ("1,234,567.89", Decimal("1234567.89")),
        ("$ 4.435.200", Decimal("4435200")),
        ("0.19", Decimal("0.19")),
        ("-1500", Decimal("-1500")),
        ("(1500)", Decimal("-1500")),
        ("", None),
        ("   ", None),
        ("no aplica", None),
    ],
)
def test_parseo_de_decimales(entrada: str, esperado: Decimal | None):
    assert parsear_decimal(entrada) == esperado


@pytest.mark.parametrize(
    ("entrada", "iso"),
    [
        ("2026-01-10", "2026-01-10"),
        ("10/01/2026", "2026-01-10"),
        ("10-01-2026", "2026-01-10"),
    ],
)
def test_parseo_de_fechas(entrada: str, iso: str):
    fecha = parsear_fecha(entrada)
    assert fecha is not None and fecha.isoformat() == iso


def test_fecha_invalida_devuelve_none():
    assert parsear_fecha("ayer") is None
