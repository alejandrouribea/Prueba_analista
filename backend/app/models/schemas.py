from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModeloBase(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class ReglaSchema(ModeloBase):
    codigo: str
    nombre: str
    descripcion: str
    severidad: str
    categoria: str


class HallazgoSchema(ModeloBase):
    codigo: str
    nombre: str
    categoria: str
    severidad: str
    mensaje: str
    valor_esperado: float | str | None = None
    valor_encontrado: float | str | None = None
    diferencia: float | None = None
    campos: list[str] = Field(default_factory=list)


class RegistroContableSchema(ModeloBase):
    fila: int
    fecha_contabilizacion: str | None = None
    cuenta_contable: str | None = None
    centro_costo: str | None = None
    valor_debito: float | None = None
    valor_credito: float | None = None
    estado: str | None = None


class FacturaDetalleSchema(ModeloBase):
    fila: int
    id_factura: str
    nit_proveedor: str | None = None
    fecha_factura: str | None = None
    concepto: str | None = None

    base_gravable: float | None = None
    tarifa_iva: float | None = None
    valor_iva: float | None = None
    iva_esperado: float | None = None
    diferencia_iva: float | None = None

    tarifa_retencion: float | None = None
    valor_retencion: float | None = None
    retencion_esperada: float | None = None
    diferencia_retencion: float | None = None

    total_factura: float | None = None
    total_esperado: float | None = None
    diferencia_total: float | None = None

    ocurrencia: int
    total_ocurrencias: int

    contabilizada: bool
    estado_contable: str | None = None
    valor_contabilizado: float | None = None
    diferencia_contable: float | None = None
    registros_contables: list[RegistroContableSchema] = Field(default_factory=list)

    clasificacion: str
    severidad_maxima: str | None = None
    codigos_inconsistencia: list[str] = Field(default_factory=list)
    causas: str | None = None
    hallazgos: list[HallazgoSchema] = Field(default_factory=list)


class ContabilidadHuerfanaSchema(ModeloBase):
    fila: int
    id_factura: str
    fecha_contabilizacion: str | None = None
    cuenta_contable: str | None = None
    centro_costo: str | None = None
    valor_debito: float | None = None
    valor_credito: float | None = None
    estado: str | None = None
    causa: str


class ConteoRegla(ModeloBase):
    codigo: str
    nombre: str
    categoria: str
    severidad: str
    cantidad: int


class MontosSchema(ModeloBase):
    total_facturado: float
    total_base_gravable: float
    total_iva: float
    total_retencion: float
    total_contabilizado: float
    monto_con_inconsistencia: float
    # Suma de los valores absolutos de todas las diferencias detectadas.
    diferencia_absoluta_detectada: float


class ResumenSchema(ModeloBase):
    total_facturas: int
    facturas_correctas: int
    facturas_con_inconsistencia: int
    total_inconsistencias: int
    porcentaje_correctas: float

    facturas_duplicadas: int
    facturas_sin_registro_contable: int
    registros_contables_sin_factura: int
    facturas_pendientes_contabilizar: int

    filas_leidas_facturas: int
    filas_leidas_contabilidad: int

    por_severidad: dict[str, int]
    por_categoria: dict[str, int]
    por_regla: list[ConteoRegla]
    montos: MontosSchema


class ArchivoProcesadoSchema(ModeloBase):
    nombre: str
    filas: int
    columnas: list[str]


class ConciliacionResponse(ModeloBase):
    procesado_en: str
    tolerancia_pesos: float
    archivos: list[ArchivoProcesadoSchema]
    resumen: ResumenSchema
    detalle: list[FacturaDetalleSchema]
    contabilidad_sin_factura: list[ContabilidadHuerfanaSchema] = Field(
        default_factory=list
    )


class ErrorDetalle(ModeloBase):
    codigo: str
    mensaje: str
    detalle: dict = Field(default_factory=dict)


class ErrorResponse(ModeloBase):
    error: ErrorDetalle


class HealthResponse(ModeloBase):
    estado: str
    aplicacion: str
    version: str
