export type Clasificacion = 'Correcta' | 'Con inconsistencia';
export type Severidad = 'Alta' | 'Media' | 'Baja';

export interface Hallazgo {
  codigo: string;
  nombre: string;
  categoria: string;
  severidad: Severidad;
  mensaje: string;
  valor_esperado: number | string | null;
  valor_encontrado: number | string | null;
  diferencia: number | null;
  campos: string[];
}

export interface RegistroContable {
  fila: number;
  fecha_contabilizacion: string | null;
  cuenta_contable: string | null;
  centro_costo: string | null;
  valor_debito: number | null;
  valor_credito: number | null;
  estado: string | null;
}

export interface FacturaDetalle {
  fila: number;
  id_factura: string;
  nit_proveedor: string | null;
  fecha_factura: string | null;
  concepto: string | null;

  base_gravable: number | null;
  tarifa_iva: number | null;
  valor_iva: number | null;
  iva_esperado: number | null;
  diferencia_iva: number | null;

  tarifa_retencion: number | null;
  valor_retencion: number | null;
  retencion_esperada: number | null;
  diferencia_retencion: number | null;

  total_factura: number | null;
  total_esperado: number | null;
  diferencia_total: number | null;

  ocurrencia: number;
  total_ocurrencias: number;

  contabilizada: boolean;
  estado_contable: string | null;
  valor_contabilizado: number | null;
  diferencia_contable: number | null;
  registros_contables: RegistroContable[];

  clasificacion: Clasificacion;
  severidad_maxima: Severidad | null;
  codigos_inconsistencia: string[];
  causas: string | null;
  hallazgos: Hallazgo[];
}

export interface ContabilidadHuerfana {
  fila: number;
  id_factura: string;
  fecha_contabilizacion: string | null;
  cuenta_contable: string | null;
  centro_costo: string | null;
  valor_debito: number | null;
  valor_credito: number | null;
  estado: string | null;
  causa: string;
}

export interface ConteoRegla {
  codigo: string;
  nombre: string;
  categoria: string;
  severidad: Severidad;
  cantidad: number;
}

export interface Montos {
  total_facturado: number;
  total_base_gravable: number;
  total_iva: number;
  total_retencion: number;
  total_contabilizado: number;
  monto_con_inconsistencia: number;
  diferencia_absoluta_detectada: number;
}

export interface Resumen {
  total_facturas: number;
  facturas_correctas: number;
  facturas_con_inconsistencia: number;
  total_inconsistencias: number;
  porcentaje_correctas: number;

  facturas_duplicadas: number;
  facturas_sin_registro_contable: number;
  registros_contables_sin_factura: number;
  facturas_pendientes_contabilizar: number;

  filas_leidas_facturas: number;
  filas_leidas_contabilidad: number;

  por_severidad: Record<string, number>;
  por_categoria: Record<string, number>;
  por_regla: ConteoRegla[];
  montos: Montos;
}

export interface ArchivoProcesado {
  nombre: string;
  filas: number;
  columnas: string[];
}

export interface ConciliacionResultado {
  procesado_en: string;
  tolerancia_pesos: number;
  archivos: ArchivoProcesado[];
  resumen: Resumen;
  detalle: FacturaDetalle[];
  contabilidad_sin_factura: ContabilidadHuerfana[];
}

export interface Regla {
  codigo: string;
  nombre: string;
  descripcion: string;
  severidad: Severidad;
  categoria: string;
}

export interface ErrorApi {
  codigo: string;
  mensaje: string;
  detalle: Record<string, unknown>;
}
