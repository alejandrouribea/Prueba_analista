import { FacturaDetalle } from '../../core/models/conciliacion.model';

const COLUMNAS = [
  'id_factura',
  'nit_proveedor',
  'fecha_factura',
  'concepto',
  'base_gravable',
  'tarifa_iva',
  'valor_iva',
  'iva_esperado',
  'diferencia_iva',
  'tarifa_retencion',
  'valor_retencion',
  'retencion_esperada',
  'diferencia_retencion',
  'total_factura',
  'total_esperado',
  'diferencia_total',
  'estado_contable',
  'valor_contabilizado',
  'diferencia_contable',
  'clasificacion',
  'severidad',
  'codigos_inconsistencia',
  'causas',
  'detalle_hallazgos',
] as const;

function escapar(valor: unknown): string {
  if (valor === null || valor === undefined) {
    return '';
  }
  const texto = String(valor);
  return /[";\n\r]/.test(texto) ? `"${texto.replace(/"/g, '""')}"` : texto;
}

function aFila(factura: FacturaDetalle): string {
  const valores: unknown[] = [
    factura.id_factura,
    factura.nit_proveedor,
    factura.fecha_factura,
    factura.concepto,
    factura.base_gravable,
    factura.tarifa_iva,
    factura.valor_iva,
    factura.iva_esperado,
    factura.diferencia_iva,
    factura.tarifa_retencion,
    factura.valor_retencion,
    factura.retencion_esperada,
    factura.diferencia_retencion,
    factura.total_factura,
    factura.total_esperado,
    factura.diferencia_total,
    factura.estado_contable,
    factura.valor_contabilizado,
    factura.diferencia_contable,
    factura.clasificacion,
    factura.severidad_maxima,
    factura.codigos_inconsistencia.join(' | '),
    factura.causas,
    factura.hallazgos.map((h) => h.mensaje).join(' || '),
  ];
  return valores.map(escapar).join(';');
}

/* Descarga el detalle para seguimiento en Excel. */
export function descargarDetalleCsv(
  facturas: FacturaDetalle[],
  nombreArchivo = 'conciliacion-detalle.csv',
): void {
  const contenido = [COLUMNAS.join(';'), ...facturas.map(aFila)].join('\r\n');
  const blob = new Blob([`﻿${contenido}`], {
    type: 'text/csv;charset=utf-8;',
  });

  const url = URL.createObjectURL(blob);
  const enlace = document.createElement('a');
  enlace.href = url;
  enlace.download = nombreArchivo;
  enlace.click();
  URL.revokeObjectURL(url);
}
