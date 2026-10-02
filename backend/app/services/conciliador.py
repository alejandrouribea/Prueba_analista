from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from app.domain.reglas import (
    CAMPOS_OBLIGATORIOS_FACTURA,
    ESTADO_CONTABILIZADA,
    REGLAS_POR_CODIGO,
    TARIFAS_IVA_VIGENTES,
    TARIFAS_RETENCION_PARAMETRIZADAS,
    Clasificacion,
    Hallazgo,
    Severidad,
)
from app.services.csv_reader import ArchivoCsv, FilaCsv, parsear_decimal, parsear_fecha

DOS_DECIMALES = Decimal("0.01")

_PESO_SEVERIDAD = {Severidad.ALTA: 3, Severidad.MEDIA: 2, Severidad.BAJA: 1}

ETIQUETAS_CAMPO = {
    "id_factura": "número de factura",
    "nit_proveedor": "NIT del proveedor",
    "fecha_factura": "fecha de la factura",
    "concepto": "concepto",
    "base_gravable": "base gravable",
    "total_factura": "total de la factura",
}


def redondear(valor: Decimal) -> Decimal:
    return valor.quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP)


@dataclass
class Factura:
    numero_fila: int
    id_factura: str
    nit_proveedor: str
    fecha_factura: date | None
    fecha_factura_texto: str
    concepto: str
    base_gravable: Decimal | None
    tarifa_iva: Decimal | None
    valor_iva: Decimal | None
    tarifa_retencion: Decimal | None
    valor_retencion: Decimal | None
    total_factura: Decimal | None
    campos_vacios: tuple[str, ...]
    campos_no_numericos: tuple[str, ...]

    @classmethod
    def desde_fila(cls, fila: FilaCsv) -> Factura:
        numericos = {
            "base_gravable": parsear_decimal(fila.texto("base_gravable")),
            "tarifa_iva": parsear_decimal(fila.texto("tarifa_iva")),
            "valor_iva": parsear_decimal(fila.texto("valor_iva")),
            "tarifa_retencion": parsear_decimal(fila.texto("tarifa_retencion")),
            "valor_retencion": parsear_decimal(fila.texto("valor_retencion")),
            "total_factura": parsear_decimal(fila.texto("total_factura")),
        }
        # Un campo es "no numérico" solo si traía algo que no se pudo convertir;
        # si viene vacío se reporta como campo obligatorio faltante.
        no_numericos = tuple(
            campo
            for campo, valor in numericos.items()
            if valor is None and fila.texto(campo) != ""
        )
        vacios = tuple(
            campo
            for campo in CAMPOS_OBLIGATORIOS_FACTURA
            if fila.texto(campo) == ""
        )
        return cls(
            numero_fila=fila.numero_fila,
            id_factura=fila.texto("id_factura"),
            nit_proveedor=fila.texto("nit_proveedor"),
            fecha_factura=parsear_fecha(fila.texto("fecha_factura")),
            fecha_factura_texto=fila.texto("fecha_factura"),
            concepto=fila.texto("concepto"),
            campos_vacios=vacios,
            campos_no_numericos=no_numericos,
            **numericos,
        )


@dataclass
class RegistroContable:
    numero_fila: int
    id_factura: str
    fecha_contabilizacion: date | None
    fecha_contabilizacion_texto: str
    cuenta_contable: str
    centro_costo: str
    valor_debito: Decimal | None
    valor_credito: Decimal | None
    estado: str

    @classmethod
    def desde_fila(cls, fila: FilaCsv) -> RegistroContable:
        return cls(
            numero_fila=fila.numero_fila,
            id_factura=fila.texto("id_factura"),
            fecha_contabilizacion=parsear_fecha(fila.texto("fecha_contabilizacion")),
            fecha_contabilizacion_texto=fila.texto("fecha_contabilizacion"),
            cuenta_contable=fila.texto("cuenta_contable"),
            centro_costo=fila.texto("centro_costo"),
            valor_debito=parsear_decimal(fila.texto("valor_debito")),
            valor_credito=parsear_decimal(fila.texto("valor_credito")),
            estado=fila.texto("estado"),
        )

    @property
    def esta_contabilizada(self) -> bool:
        return self.estado.strip().lower() == ESTADO_CONTABILIZADA.lower()


@dataclass
class FacturaEvaluada:
    factura: Factura
    registros_contables: list[RegistroContable]
    ocurrencia: int
    total_ocurrencias: int
    iva_esperado: Decimal | None = None
    retencion_esperada: Decimal | None = None
    total_esperado: Decimal | None = None
    diferencia_iva: Decimal | None = None
    diferencia_retencion: Decimal | None = None
    diferencia_total: Decimal | None = None
    diferencia_contable: Decimal | None = None
    hallazgos: list[Hallazgo] = field(default_factory=list)

    @property
    def clasificacion(self) -> Clasificacion:
        return (
            Clasificacion.CORRECTA
            if not self.hallazgos
            else Clasificacion.CON_INCONSISTENCIA
        )

    @property
    def severidad_maxima(self) -> Severidad | None:
        if not self.hallazgos:
            return None
        return max(
            (REGLAS_POR_CODIGO[h.codigo].severidad for h in self.hallazgos),
            key=lambda s: _PESO_SEVERIDAD[s],
        )

    @property
    def registro_principal(self) -> RegistroContable | None:
        # Si hay duplicados me quedo con el primero del archivo y el duplicado
        # queda reportado como hallazgo aparte.
        return self.registros_contables[0] if self.registros_contables else None


@dataclass
class ResultadoConciliacion:
    facturas: list[FacturaEvaluada]
    contabilidad_sin_factura: list[RegistroContable]
    total_filas_facturas: int
    total_filas_contabilidad: int


def _validar_calidad_datos(evaluada: FacturaEvaluada) -> None:
    factura = evaluada.factura

    if factura.campos_vacios:
        etiquetas = [
            ETIQUETAS_CAMPO.get(campo, campo) for campo in factura.campos_vacios
        ]
        evaluada.hallazgos.append(
            Hallazgo(
                codigo="CAMPO_OBLIGATORIO_VACIO",
                mensaje=f"Faltan datos obligatorios: {', '.join(etiquetas)}.",
                campos=factura.campos_vacios,
            )
        )

    if factura.campos_no_numericos:
        evaluada.hallazgos.append(
            Hallazgo(
                codigo="VALOR_NO_NUMERICO",
                mensaje=(
                    "No se pudo interpretar como número: "
                    f"{', '.join(factura.campos_no_numericos)}."
                ),
                campos=factura.campos_no_numericos,
            )
        )


def _validar_tarifas(evaluada: FacturaEvaluada) -> None:
    factura = evaluada.factura

    if (
        factura.tarifa_iva is not None
        and factura.tarifa_iva not in TARIFAS_IVA_VIGENTES
    ):
        evaluada.hallazgos.append(
            Hallazgo(
                codigo="TARIFA_IVA_NO_VIGENTE",
                mensaje=(
                    f"La tarifa de IVA {_porcentaje(factura.tarifa_iva)} no "
                    f"corresponde a una tarifa vigente (0%, 5%, 19%)."
                ),
                valor_esperado="0%, 5% o 19%",
                valor_encontrado=_porcentaje(factura.tarifa_iva),
                campos=("tarifa_iva",),
            )
        )

    if (
        factura.tarifa_retencion is not None
        and factura.tarifa_retencion not in TARIFAS_RETENCION_PARAMETRIZADAS
    ):
        evaluada.hallazgos.append(
            Hallazgo(
                codigo="TARIFA_RETENCION_NO_PARAMETRIZADA",
                mensaje=(
                    f"La tarifa de retención {_porcentaje(factura.tarifa_retencion)} "
                    f"no está parametrizada (0%, 2.5%, 3.5%, 4%)."
                ),
                valor_esperado="0%, 2.5%, 3.5% o 4%",
                valor_encontrado=_porcentaje(factura.tarifa_retencion),
                campos=("tarifa_retencion",),
            )
        )


def _validar_liquidacion(evaluada: FacturaEvaluada, tolerancia: Decimal) -> None:
    factura = evaluada.factura

    if factura.base_gravable is not None and factura.tarifa_iva is not None:
        evaluada.iva_esperado = redondear(factura.base_gravable * factura.tarifa_iva)
        if factura.valor_iva is not None:
            evaluada.diferencia_iva = redondear(
                factura.valor_iva - evaluada.iva_esperado
            )
            if abs(evaluada.diferencia_iva) > tolerancia:
                evaluada.hallazgos.append(
                    Hallazgo(
                        codigo="IVA_CALCULADO_NO_COINCIDE",
                        mensaje=(
                            f"El IVA facturado ({_moneda(factura.valor_iva)}) difiere "
                            f"del IVA esperado ({_moneda(evaluada.iva_esperado)}) "
                            f"= base {_moneda(factura.base_gravable)} x "
                            f"{_porcentaje(factura.tarifa_iva)}. "
                            f"Diferencia: {_moneda(evaluada.diferencia_iva)}."
                        ),
                        valor_esperado=evaluada.iva_esperado,
                        valor_encontrado=factura.valor_iva,
                        diferencia=evaluada.diferencia_iva,
                        campos=("valor_iva",),
                    )
                )

    if factura.base_gravable is not None and factura.tarifa_retencion is not None:
        evaluada.retencion_esperada = redondear(
            factura.base_gravable * factura.tarifa_retencion
        )
        if factura.valor_retencion is not None:
            evaluada.diferencia_retencion = redondear(
                factura.valor_retencion - evaluada.retencion_esperada
            )
            if abs(evaluada.diferencia_retencion) > tolerancia:
                evaluada.hallazgos.append(
                    Hallazgo(
                        codigo="RETENCION_CALCULADA_NO_COINCIDE",
                        mensaje=(
                            f"La retención practicada "
                            f"({_moneda(factura.valor_retencion)}) difiere de la "
                            f"esperada ({_moneda(evaluada.retencion_esperada)}) "
                            f"= base {_moneda(factura.base_gravable)} x "
                            f"{_porcentaje(factura.tarifa_retencion)}. "
                            f"Diferencia: {_moneda(evaluada.diferencia_retencion)}."
                        ),
                        valor_esperado=evaluada.retencion_esperada,
                        valor_encontrado=factura.valor_retencion,
                        diferencia=evaluada.diferencia_retencion,
                        campos=("valor_retencion",),
                    )
                )

    # Ojo: el total se valida contra los valores que trae la factura, no contra
    # los esperados. Así un error de IVA no contamina el diagnóstico del total
    # y se distingue "liquidaron mal el IVA" de "liquidaron mal la suma".
    if (
        factura.base_gravable is not None
        and factura.valor_iva is not None
        and factura.valor_retencion is not None
    ):
        evaluada.total_esperado = redondear(
            factura.base_gravable + factura.valor_iva - factura.valor_retencion
        )
        if factura.total_factura is not None:
            evaluada.diferencia_total = redondear(
                factura.total_factura - evaluada.total_esperado
            )
            if abs(evaluada.diferencia_total) > tolerancia:
                evaluada.hallazgos.append(
                    Hallazgo(
                        codigo="TOTAL_FACTURA_NO_COINCIDE",
                        mensaje=(
                            f"El total facturado "
                            f"({_moneda(factura.total_factura)}) difiere del total "
                            f"esperado ({_moneda(evaluada.total_esperado)}) = base "
                            f"{_moneda(factura.base_gravable)} + IVA "
                            f"{_moneda(factura.valor_iva)} - retención "
                            f"{_moneda(factura.valor_retencion)}. "
                            f"Diferencia: {_moneda(evaluada.diferencia_total)}."
                        ),
                        valor_esperado=evaluada.total_esperado,
                        valor_encontrado=factura.total_factura,
                        diferencia=evaluada.diferencia_total,
                        campos=("total_factura",),
                    )
                )


def _validar_duplicidad(evaluada: FacturaEvaluada) -> None:
    # Se marcan todas las ocurrencias, no solo la segunda: el analista es quien
    # decide cuál es la válida.
    if evaluada.total_ocurrencias > 1:
        evaluada.hallazgos.append(
            Hallazgo(
                codigo="FACTURA_DUPLICADA",
                mensaje=(
                    f"La factura {evaluada.factura.id_factura} aparece "
                    f"{evaluada.total_ocurrencias} veces en el archivo de facturas "
                    f"(ocurrencia {evaluada.ocurrencia} de "
                    f"{evaluada.total_ocurrencias}, fila "
                    f"{evaluada.factura.numero_fila})."
                ),
                valor_esperado=1,
                valor_encontrado=evaluada.total_ocurrencias,
                campos=("id_factura",),
            )
        )


def _validar_conciliacion_contable(
    evaluada: FacturaEvaluada, tolerancia: Decimal
) -> None:
    factura = evaluada.factura
    registros = evaluada.registros_contables

    if not registros:
        evaluada.hallazgos.append(
            Hallazgo(
                codigo="SIN_REGISTRO_CONTABLE",
                mensaje=(
                    f"La factura {factura.id_factura} no tiene ningún registro "
                    f"en el archivo de contabilidad."
                ),
                campos=("id_factura",),
            )
        )
        return

    if len(registros) > 1:
        filas = ", ".join(str(r.numero_fila) for r in registros)
        evaluada.hallazgos.append(
            Hallazgo(
                codigo="REGISTRO_CONTABLE_DUPLICADO",
                mensaje=(
                    f"La factura {factura.id_factura} tiene {len(registros)} "
                    f"registros contables (filas {filas}). Se concilia contra el "
                    f"primero."
                ),
                valor_esperado=1,
                valor_encontrado=len(registros),
                campos=("id_factura",),
            )
        )

    principal = registros[0]

    if principal.valor_debito is not None and principal.valor_credito is not None:
        descuadre = redondear(principal.valor_debito - principal.valor_credito)
        if abs(descuadre) > tolerancia:
            evaluada.hallazgos.append(
                Hallazgo(
                    codigo="PARTIDA_DOBLE_DESCUADRADA",
                    mensaje=(
                        f"El asiento tiene débito {_moneda(principal.valor_debito)} "
                        f"y crédito {_moneda(principal.valor_credito)}. "
                        f"Descuadre: {_moneda(descuadre)}."
                    ),
                    valor_esperado=principal.valor_credito,
                    valor_encontrado=principal.valor_debito,
                    diferencia=descuadre,
                    campos=("valor_debito", "valor_credito"),
                )
            )

    if factura.total_factura is not None and principal.valor_debito is not None:
        evaluada.diferencia_contable = redondear(
            principal.valor_debito - factura.total_factura
        )
        if abs(evaluada.diferencia_contable) > tolerancia:
            evaluada.hallazgos.append(
                Hallazgo(
                    codigo="DIFERENCIA_VALOR_CONTABILIZADO",
                    mensaje=(
                        f"El valor contabilizado "
                        f"({_moneda(principal.valor_debito)}) difiere del total de "
                        f"la factura ({_moneda(factura.total_factura)}). "
                        f"Diferencia: {_moneda(evaluada.diferencia_contable)}."
                    ),
                    valor_esperado=factura.total_factura,
                    valor_encontrado=principal.valor_debito,
                    diferencia=evaluada.diferencia_contable,
                    campos=("valor_debito",),
                )
            )

    if not principal.esta_contabilizada:
        evaluada.hallazgos.append(
            Hallazgo(
                codigo="ESTADO_NO_CONTABILIZADO",
                mensaje=(
                    f"El registro contable está en estado "
                    f"'{principal.estado or 'sin estado'}'; se esperaba "
                    f"'{ESTADO_CONTABILIZADA}'."
                ),
                valor_esperado=ESTADO_CONTABILIZADA,
                valor_encontrado=principal.estado or "(vacío)",
                campos=("estado",),
            )
        )

    if (
        factura.fecha_factura is not None
        and principal.fecha_contabilizacion is not None
        and principal.fecha_contabilizacion < factura.fecha_factura
    ):
        evaluada.hallazgos.append(
            Hallazgo(
                codigo="FECHA_CONTABILIZACION_ANTERIOR",
                mensaje=(
                    f"La factura se contabilizó el "
                    f"{principal.fecha_contabilizacion.isoformat()}, antes de su "
                    f"fecha de emisión ({factura.fecha_factura.isoformat()})."
                ),
                valor_esperado=f">= {factura.fecha_factura.isoformat()}",
                valor_encontrado=principal.fecha_contabilizacion.isoformat(),
                campos=("fecha_contabilizacion",),
            )
        )


def conciliar(
    archivo_facturas: ArchivoCsv,
    archivo_contabilidad: ArchivoCsv,
    tolerancia: Decimal,
) -> ResultadoConciliacion:
    facturas = [Factura.desde_fila(f) for f in archivo_facturas.filas]
    registros = [RegistroContable.desde_fila(f) for f in archivo_contabilidad.filas]

    contabilidad_por_id: dict[str, list[RegistroContable]] = defaultdict(list)
    for registro in registros:
        contabilidad_por_id[registro.id_factura].append(registro)

    ocurrencias_por_id = Counter(f.id_factura for f in facturas)
    vistas: Counter[str] = Counter()

    evaluadas: list[FacturaEvaluada] = []
    for factura in facturas:
        vistas[factura.id_factura] += 1
        evaluada = FacturaEvaluada(
            factura=factura,
            registros_contables=list(contabilidad_por_id.get(factura.id_factura, [])),
            ocurrencia=vistas[factura.id_factura],
            total_ocurrencias=ocurrencias_por_id[factura.id_factura],
        )

        _validar_calidad_datos(evaluada)
        _validar_tarifas(evaluada)
        _validar_liquidacion(evaluada, tolerancia)
        _validar_duplicidad(evaluada)
        _validar_conciliacion_contable(evaluada, tolerancia)

        evaluadas.append(evaluada)

    ids_facturados = {f.id_factura for f in facturas}
    huerfanos = [r for r in registros if r.id_factura not in ids_facturados]

    return ResultadoConciliacion(
        facturas=evaluadas,
        contabilidad_sin_factura=huerfanos,
        total_filas_facturas=archivo_facturas.total_filas,
        total_filas_contabilidad=archivo_contabilidad.total_filas,
    )


def _moneda(valor: Decimal | None) -> str:
    if valor is None:
        return "sin dato"
    entero = redondear(valor)
    signo = "-" if entero < 0 else ""
    absoluto = abs(entero)
    partes = f"{absoluto:,.2f}".replace(",", "@").replace(".", ",").replace("@", ".")
    if partes.endswith(",00"):
        partes = partes[:-3]
    return f"{signo}$ {partes}"


def _porcentaje(valor: Decimal | None) -> str:
    if valor is None:
        return "sin dato"
    porcentaje = (valor * 100).normalize()
    texto = format(porcentaje, "f").rstrip("0").rstrip(".")
    return f"{texto or '0'}%"
