from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum


class Severidad(str, Enum):
    ALTA = "Alta"       # Afecta la declaración tributaria o el valor en libros.
    MEDIA = "Media"     # Afecta la trazabilidad o el cierre del periodo.
    BAJA = "Baja"       # Calidad del dato, no mueve cifras.


class Clasificacion(str, Enum):
    CORRECTA = "Correcta"
    CON_INCONSISTENCIA = "Con inconsistencia"


@dataclass(frozen=True)
class Regla:
    codigo: str
    nombre: str
    descripcion: str
    severidad: Severidad
    categoria: str


CATALOGO_REGLAS: tuple[Regla, ...] = (
    # Reglas mínimas exigidas por el caso de negocio.
    Regla(
        codigo="IVA_CALCULADO_NO_COINCIDE",
        nombre="IVA liquidado distinto al IVA esperado",
        descripcion=(
            "El IVA esperado se calcula como base gravable x tarifa de IVA y se "
            "compara contra el valor_iva reportado en la factura."
        ),
        severidad=Severidad.ALTA,
        categoria="Impuestos",
    ),
    Regla(
        codigo="TOTAL_FACTURA_NO_COINCIDE",
        nombre="Total de la factura mal liquidado",
        descripcion=(
            "El total esperado se calcula como base gravable + IVA - retención, "
            "usando los valores reportados en la factura."
        ),
        severidad=Severidad.ALTA,
        categoria="Impuestos",
    ),
    Regla(
        codigo="FACTURA_DUPLICADA",
        nombre="Factura duplicada en el archivo de facturas",
        descripcion=(
            "El mismo id_factura aparece más de una vez en facturas.csv. "
            "Riesgo de doble causación y doble pago al proveedor."
        ),
        severidad=Severidad.ALTA,
        categoria="Integridad",
    ),
    Regla(
        codigo="SIN_REGISTRO_CONTABLE",
        nombre="Factura sin registro contable",
        descripcion=(
            "La factura no tiene ningún movimiento asociado en contabilidad.csv. "
            "Genera gasto no causado y diferencias en el cierre del periodo."
        ),
        severidad=Severidad.ALTA,
        categoria="Conciliación",
    ),
    # Controles complementarios.
    Regla(
        codigo="RETENCION_CALCULADA_NO_COINCIDE",
        nombre="Retención liquidada distinta a la esperada",
        descripcion=(
            "La retención esperada se calcula como base gravable x tarifa de "
            "retención. Una diferencia afecta el certificado de retención."
        ),
        severidad=Severidad.ALTA,
        categoria="Impuestos",
    ),
    Regla(
        codigo="DIFERENCIA_VALOR_CONTABILIZADO",
        nombre="Valor contabilizado distinto al total de la factura",
        descripcion=(
            "El valor_debito del registro contable no coincide con el "
            "total_factura. Indica una causación por un valor diferente."
        ),
        severidad=Severidad.ALTA,
        categoria="Conciliación",
    ),
    Regla(
        codigo="PARTIDA_DOBLE_DESCUADRADA",
        nombre="Partida doble descuadrada",
        descripcion=(
            "En el registro contable el valor_debito debe ser igual al "
            "valor_credito. Si difieren, el asiento está descuadrado."
        ),
        severidad=Severidad.ALTA,
        categoria="Conciliación",
    ),
    Regla(
        codigo="REGISTRO_CONTABLE_DUPLICADO",
        nombre="Registro contable duplicado",
        descripcion=(
            "La factura tiene más de un movimiento en contabilidad.csv. "
            "Riesgo de doble causación del gasto."
        ),
        severidad=Severidad.ALTA,
        categoria="Integridad",
    ),
    Regla(
        codigo="CAMPO_OBLIGATORIO_VACIO",
        nombre="Campo obligatorio vacío",
        descripcion=(
            "Campos requeridos para la causación y el reporte tributario "
            "(nit_proveedor, fecha_factura, concepto) llegan sin valor."
        ),
        severidad=Severidad.MEDIA,
        categoria="Calidad del dato",
    ),
    Regla(
        codigo="VALOR_NO_NUMERICO",
        nombre="Valor numérico ilegible",
        descripcion=(
            "Un campo monetario o de tarifa no se pudo interpretar como número; "
            "la factura no se puede liquidar automáticamente."
        ),
        severidad=Severidad.ALTA,
        categoria="Calidad del dato",
    ),
    Regla(
        codigo="ESTADO_NO_CONTABILIZADO",
        nombre="Factura con estado contable pendiente",
        descripcion=(
            "El registro contable existe pero su estado no es Contabilizada. "
            "Queda pendiente de cierre en el periodo."
        ),
        severidad=Severidad.MEDIA,
        categoria="Conciliación",
    ),
    Regla(
        codigo="FECHA_CONTABILIZACION_ANTERIOR",
        nombre="Contabilización anterior a la fecha de la factura",
        descripcion=(
            "La fecha_contabilizacion es anterior a la fecha_factura, lo que "
            "rompe la secuencia lógica de causación."
        ),
        severidad=Severidad.MEDIA,
        categoria="Conciliación",
    ),
    Regla(
        codigo="TARIFA_IVA_NO_VIGENTE",
        nombre="Tarifa de IVA fuera del catálogo vigente",
        descripcion=(
            "Las tarifas de IVA admitidas en Colombia son 0%, 5% y 19%. "
            "Cualquier otra tarifa debe revisarse manualmente."
        ),
        severidad=Severidad.MEDIA,
        categoria="Impuestos",
    ),
    Regla(
        codigo="TARIFA_RETENCION_NO_PARAMETRIZADA",
        nombre="Tarifa de retención no parametrizada",
        descripcion=(
            "La tarifa de retención en la fuente no corresponde a las tarifas "
            "parametrizadas para los conceptos del caso (0%, 2.5%, 3.5%, 4%)."
        ),
        severidad=Severidad.BAJA,
        categoria="Impuestos",
    ),
    Regla(
        codigo="CONTABILIDAD_SIN_FACTURA",
        nombre="Registro contable sin factura soporte",
        descripcion=(
            "Existe un movimiento en contabilidad.csv cuyo id_factura no está "
            "en facturas.csv. Se reporta aparte del detalle de facturas."
        ),
        severidad=Severidad.ALTA,
        categoria="Conciliación",
    ),
)

REGLAS_POR_CODIGO: dict[str, Regla] = {regla.codigo: regla for regla in CATALOGO_REGLAS}


# Tarifas parametrizadas: se cambian acá sin tocar la lógica de validación.
TARIFAS_IVA_VIGENTES: frozenset[Decimal] = frozenset(
    {Decimal("0"), Decimal("0.05"), Decimal("0.19")}
)

TARIFAS_RETENCION_PARAMETRIZADAS: frozenset[Decimal] = frozenset(
    {Decimal("0"), Decimal("0.025"), Decimal("0.035"), Decimal("0.04")}
)

COLUMNAS_FACTURAS: tuple[str, ...] = (
    "id_factura",
    "nit_proveedor",
    "fecha_factura",
    "concepto",
    "base_gravable",
    "tarifa_iva",
    "valor_iva",
    "tarifa_retencion",
    "valor_retencion",
    "total_factura",
)

COLUMNAS_CONTABILIDAD: tuple[str, ...] = (
    "id_factura",
    "fecha_contabilizacion",
    "cuenta_contable",
    "centro_costo",
    "valor_debito",
    "valor_credito",
    "estado",
)

# Sin estos campos la factura no es causable ni reportable.
CAMPOS_OBLIGATORIOS_FACTURA: tuple[str, ...] = (
    "id_factura",
    "nit_proveedor",
    "fecha_factura",
    "concepto",
    "base_gravable",
    "total_factura",
)

ESTADO_CONTABILIZADA: str = "Contabilizada"


@dataclass
class Hallazgo:
    codigo: str
    mensaje: str
    valor_esperado: Decimal | str | None = None
    valor_encontrado: Decimal | str | None = None
    diferencia: Decimal | None = None
    campos: tuple[str, ...] = field(default_factory=tuple)

    @property
    def regla(self) -> Regla:
        return REGLAS_POR_CODIGO[self.codigo]
