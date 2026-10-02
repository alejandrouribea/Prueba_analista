from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal

from app.domain.reglas import REGLAS_POR_CODIGO, Clasificacion
from app.models.schemas import (
    ArchivoProcesadoSchema,
    ConciliacionResponse,
    ConteoRegla,
    ContabilidadHuerfanaSchema,
    FacturaDetalleSchema,
    HallazgoSchema,
    MontosSchema,
    RegistroContableSchema,
    ResumenSchema,
)
from app.services.conciliador import (
    FacturaEvaluada,
    RegistroContable,
    ResultadoConciliacion,
)
from app.services.csv_reader import ArchivoCsv


def _f(valor: Decimal | None) -> float | None:
    return float(valor) if valor is not None else None


def _texto(valor: str) -> str | None:
    # Cadena vacía a None, así el frontend puede pintar un guion.
    return valor or None


def _registro_a_schema(registro: RegistroContable) -> RegistroContableSchema:
    return RegistroContableSchema(
        fila=registro.numero_fila,
        fecha_contabilizacion=_texto(registro.fecha_contabilizacion_texto),
        cuenta_contable=_texto(registro.cuenta_contable),
        centro_costo=_texto(registro.centro_costo),
        valor_debito=_f(registro.valor_debito),
        valor_credito=_f(registro.valor_credito),
        estado=_texto(registro.estado),
    )


def _factura_a_schema(evaluada: FacturaEvaluada) -> FacturaDetalleSchema:
    factura = evaluada.factura
    principal = evaluada.registro_principal

    hallazgos = [
        HallazgoSchema(
            codigo=h.codigo,
            nombre=REGLAS_POR_CODIGO[h.codigo].nombre,
            categoria=REGLAS_POR_CODIGO[h.codigo].categoria,
            severidad=REGLAS_POR_CODIGO[h.codigo].severidad.value,
            mensaje=h.mensaje,
            valor_esperado=(
                _f(h.valor_esperado)
                if isinstance(h.valor_esperado, Decimal)
                else (str(h.valor_esperado) if h.valor_esperado is not None else None)
            ),
            valor_encontrado=(
                _f(h.valor_encontrado)
                if isinstance(h.valor_encontrado, Decimal)
                else (
                    str(h.valor_encontrado) if h.valor_encontrado is not None else None
                )
            ),
            diferencia=_f(h.diferencia),
            campos=list(h.campos),
        )
        for h in evaluada.hallazgos
    ]

    severidad = evaluada.severidad_maxima

    return FacturaDetalleSchema(
        fila=factura.numero_fila,
        id_factura=factura.id_factura or "(sin número)",
        nit_proveedor=_texto(factura.nit_proveedor),
        fecha_factura=_texto(factura.fecha_factura_texto),
        concepto=_texto(factura.concepto),
        base_gravable=_f(factura.base_gravable),
        tarifa_iva=_f(factura.tarifa_iva),
        valor_iva=_f(factura.valor_iva),
        iva_esperado=_f(evaluada.iva_esperado),
        diferencia_iva=_f(evaluada.diferencia_iva),
        tarifa_retencion=_f(factura.tarifa_retencion),
        valor_retencion=_f(factura.valor_retencion),
        retencion_esperada=_f(evaluada.retencion_esperada),
        diferencia_retencion=_f(evaluada.diferencia_retencion),
        total_factura=_f(factura.total_factura),
        total_esperado=_f(evaluada.total_esperado),
        diferencia_total=_f(evaluada.diferencia_total),
        ocurrencia=evaluada.ocurrencia,
        total_ocurrencias=evaluada.total_ocurrencias,
        contabilizada=bool(principal and principal.esta_contabilizada),
        estado_contable=(
            _texto(principal.estado) if principal else "Sin registro contable"
        ),
        valor_contabilizado=_f(principal.valor_debito) if principal else None,
        diferencia_contable=_f(evaluada.diferencia_contable),
        registros_contables=[
            _registro_a_schema(r) for r in evaluada.registros_contables
        ],
        clasificacion=evaluada.clasificacion.value,
        severidad_maxima=severidad.value if severidad else None,
        codigos_inconsistencia=[h.codigo for h in evaluada.hallazgos],
        causas=(
            " | ".join(REGLAS_POR_CODIGO[h.codigo].nombre for h in evaluada.hallazgos)
            or None
        ),
        hallazgos=hallazgos,
    )


def _construir_resumen(resultado: ResultadoConciliacion) -> ResumenSchema:
    facturas = resultado.facturas
    total = len(facturas)

    correctas = sum(
        1 for f in facturas if f.clasificacion is Clasificacion.CORRECTA
    )
    con_inconsistencia = total - correctas
    total_hallazgos = sum(len(f.hallazgos) for f in facturas)

    codigos = Counter(h.codigo for f in facturas for h in f.hallazgos)

    por_severidad: Counter[str] = Counter()
    por_categoria: Counter[str] = Counter()
    for codigo, cantidad in codigos.items():
        regla = REGLAS_POR_CODIGO[codigo]
        por_severidad[regla.severidad.value] += cantidad
        por_categoria[regla.categoria] += cantidad

    def _suma(extractor) -> Decimal:
        return sum((extractor(f) or Decimal("0") for f in facturas), Decimal("0"))

    total_facturado = _suma(lambda f: f.factura.total_factura)
    total_base = _suma(lambda f: f.factura.base_gravable)
    total_iva = _suma(lambda f: f.factura.valor_iva)
    total_retencion = _suma(lambda f: f.factura.valor_retencion)
    total_contabilizado = sum(
        (
            f.registro_principal.valor_debito or Decimal("0")
            for f in facturas
            if f.registro_principal
        ),
        Decimal("0"),
    )
    monto_inconsistente = sum(
        (
            f.factura.total_factura or Decimal("0")
            for f in facturas
            if f.clasificacion is Clasificacion.CON_INCONSISTENCIA
        ),
        Decimal("0"),
    )
    diferencia_absoluta = sum(
        (
            abs(h.diferencia)
            for f in facturas
            for h in f.hallazgos
            if h.diferencia is not None
        ),
        Decimal("0"),
    )

    return ResumenSchema(
        total_facturas=total,
        facturas_correctas=correctas,
        facturas_con_inconsistencia=con_inconsistencia,
        total_inconsistencias=total_hallazgos,
        porcentaje_correctas=round(correctas / total * 100, 2) if total else 0.0,
        facturas_duplicadas=codigos.get("FACTURA_DUPLICADA", 0),
        facturas_sin_registro_contable=codigos.get("SIN_REGISTRO_CONTABLE", 0),
        registros_contables_sin_factura=len(resultado.contabilidad_sin_factura),
        facturas_pendientes_contabilizar=codigos.get("ESTADO_NO_CONTABILIZADO", 0),
        filas_leidas_facturas=resultado.total_filas_facturas,
        filas_leidas_contabilidad=resultado.total_filas_contabilidad,
        por_severidad=dict(por_severidad),
        por_categoria=dict(por_categoria),
        por_regla=sorted(
            (
                ConteoRegla(
                    codigo=codigo,
                    nombre=REGLAS_POR_CODIGO[codigo].nombre,
                    categoria=REGLAS_POR_CODIGO[codigo].categoria,
                    severidad=REGLAS_POR_CODIGO[codigo].severidad.value,
                    cantidad=cantidad,
                )
                for codigo, cantidad in codigos.items()
            ),
            key=lambda c: (-c.cantidad, c.codigo),
        ),
        montos=MontosSchema(
            total_facturado=float(total_facturado),
            total_base_gravable=float(total_base),
            total_iva=float(total_iva),
            total_retencion=float(total_retencion),
            total_contabilizado=float(total_contabilizado),
            monto_con_inconsistencia=float(monto_inconsistente),
            diferencia_absoluta_detectada=float(diferencia_absoluta),
        ),
    )


def construir_respuesta(
    resultado: ResultadoConciliacion,
    archivo_facturas: ArchivoCsv,
    archivo_contabilidad: ArchivoCsv,
    tolerancia: Decimal,
) -> ConciliacionResponse:
    huerfanos = [
        ContabilidadHuerfanaSchema(
            fila=r.numero_fila,
            id_factura=r.id_factura or "(sin número)",
            fecha_contabilizacion=_texto(r.fecha_contabilizacion_texto),
            cuenta_contable=_texto(r.cuenta_contable),
            centro_costo=_texto(r.centro_costo),
            valor_debito=_f(r.valor_debito),
            valor_credito=_f(r.valor_credito),
            estado=_texto(r.estado),
            causa=REGLAS_POR_CODIGO["CONTABILIDAD_SIN_FACTURA"].nombre,
        )
        for r in resultado.contabilidad_sin_factura
    ]

    return ConciliacionResponse(
        procesado_en=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        tolerancia_pesos=float(tolerancia),
        archivos=[
            ArchivoProcesadoSchema(
                nombre=archivo_facturas.nombre,
                filas=archivo_facturas.total_filas,
                columnas=list(archivo_facturas.columnas),
            ),
            ArchivoProcesadoSchema(
                nombre=archivo_contabilidad.nombre,
                filas=archivo_contabilidad.total_filas,
                columnas=list(archivo_contabilidad.columnas),
            ),
        ],
        resumen=_construir_resumen(resultado),
        detalle=[_factura_a_schema(f) for f in resultado.facturas],
        contabilidad_sin_factura=huerfanos,
    )
