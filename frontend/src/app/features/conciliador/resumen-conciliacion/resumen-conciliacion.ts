import { ChangeDetectionStrategy, Component, computed, input, output } from '@angular/core';

import { Resumen } from '../../../core/models/conciliacion.model';
import { MonedaCopPipe } from '../../../shared/pipes/moneda-cop.pipe';


@Component({
  selector: 'app-resumen-conciliacion',
  templateUrl: './resumen-conciliacion.html',
  styleUrl: './resumen-conciliacion.scss',
  imports: [MonedaCopPipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ResumenConciliacion {
  readonly resumen = input.required<Resumen>();
  readonly procesadoEn = input<string | null>(null);

  readonly filtrarPorRegla = output<string>();

  
  protected readonly tarjetas = computed(() => {
    const r = this.resumen();
    return [
      {
        clave: 'total',
        etiqueta: 'Facturas procesadas',
        valor: r.total_facturas,
        detalle: `${r.filas_leidas_facturas} filas en facturas.csv · ${r.filas_leidas_contabilidad} en contabilidad.csv`,
        tono: 'neutro',
      },
      {
        clave: 'correctas',
        etiqueta: 'Facturas correctas',
        valor: r.facturas_correctas,
        detalle: `${r.porcentaje_correctas}% del total`,
        tono: 'exito',
      },
      {
        clave: 'inconsistentes',
        etiqueta: 'Con inconsistencia',
        valor: r.facturas_con_inconsistencia,
        detalle: `${r.total_inconsistencias} hallazgos en total`,
        tono: 'alerta',
      },
      {
        clave: 'duplicadas',
        etiqueta: 'Duplicadas',
        valor: r.facturas_duplicadas,
        detalle: 'Mismo número de factura repetido',
        tono: 'aviso',
      },
      {
        clave: 'sin-contabilizar',
        etiqueta: 'Sin registro contable',
        valor: r.facturas_sin_registro_contable,
        detalle: 'No aparecen en contabilidad.csv',
        tono: 'aviso',
      },
      {
        clave: 'pendientes',
        etiqueta: 'Pendientes de contabilizar',
        valor: r.facturas_pendientes_contabilizar,
        detalle: 'Estado distinto de Contabilizada',
        tono: 'aviso',
      },
    ] as const;
  });

  protected readonly anchoCorrectas = computed(() => {
    const r = this.resumen();
    return r.total_facturas === 0
      ? 0
      : (r.facturas_correctas / r.total_facturas) * 100;
  });

  protected readonly severidades = computed(() => {
    const porSeveridad = this.resumen().por_severidad;
    return (['Alta', 'Media', 'Baja'] as const)
      .map((nivel) => ({ nivel, cantidad: porSeveridad[nivel] ?? 0 }))
      .filter((item) => item.cantidad > 0);
  });

  protected readonly fechaProceso = computed(() => {
    const iso = this.procesadoEn();
    if (!iso) {
      return null;
    }
    const fecha = new Date(iso);
    return Number.isNaN(fecha.getTime())
      ? null
      : fecha.toLocaleString('es-CO', { dateStyle: 'medium', timeStyle: 'short' });
  });
}
