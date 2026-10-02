import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { FacturaDetalle } from '../../../core/models/conciliacion.model';
import { ConciliacionStore } from '../../../core/state/conciliacion.store';
import { MonedaCopPipe } from '../../../shared/pipes/moneda-cop.pipe';
import { TarifaPipe } from '../../../shared/pipes/tarifa.pipe';
import { descargarDetalleCsv } from '../../../shared/utils/exportar-csv';

/**
 * Detalle con filtros por estado, severidad y regla. Cada fila se expande
 * para ver la trazabilidad del cálculo y los hallazgos explicados.
 */
@Component({
  selector: 'app-tabla-facturas',
  templateUrl: './tabla-facturas.html',
  styleUrl: './tabla-facturas.scss',
  imports: [FormsModule, MonedaCopPipe, TarifaPipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TablaFacturas {
  private readonly store = inject(ConciliacionStore);

  protected readonly facturas = this.store.facturasFiltradas;
  protected readonly totalFiltradas = this.store.totalFiltradas;
  protected readonly hayFiltrosActivos = this.store.hayFiltrosActivos;
  protected readonly filtroClasificacion = this.store.filtroClasificacion;
  protected readonly filtroSeveridad = this.store.filtroSeveridad;
  protected readonly filtroRegla = this.store.filtroRegla;
  protected readonly busqueda = this.store.busqueda;

  // Se guarda el número de fila, que identifica bien incluso a las duplicadas.
  protected readonly expandidas = signal<ReadonlySet<number>>(new Set());

  protected readonly totalGeneral = computed(
    () => this.store.resultado()?.detalle.length ?? 0,
  );

  protected readonly reglasDisponibles = computed(
    () => this.store.resumen()?.por_regla ?? [],
  );

  protected readonly huerfanos = computed(
    () => this.store.resultado()?.contabilidad_sin_factura ?? [],
  );

  protected readonly opcionesClasificacion = [
    { valor: 'todas', etiqueta: 'Todas' },
    { valor: 'Correcta', etiqueta: 'Correctas' },
    { valor: 'Con inconsistencia', etiqueta: 'Con inconsistencia' },
  ] as const;

  protected readonly opcionesSeveridad = [
    { valor: 'todas', etiqueta: 'Todas' },
    { valor: 'Alta', etiqueta: 'Alta' },
    { valor: 'Media', etiqueta: 'Media' },
    { valor: 'Baja', etiqueta: 'Baja' },
  ] as const;

  protected estaExpandida(factura: FacturaDetalle): boolean {
    return this.expandidas().has(factura.fila);
  }

  protected alternar(factura: FacturaDetalle): void {
    const siguiente = new Set(this.expandidas());
    if (siguiente.has(factura.fila)) {
      siguiente.delete(factura.fila);
    } else {
      siguiente.add(factura.fila);
    }
    this.expandidas.set(siguiente);
  }

  protected limpiarFiltros(): void {
    this.store.limpiarFiltros();
  }

  protected exportar(): void {
    descargarDetalleCsv(this.facturas(), 'conciliacion-detalle.csv');
  }

  protected tonoFila(factura: FacturaDetalle): string {
    if (factura.clasificacion === 'Correcta') {
      return 'exito';
    }
    return factura.severidad_maxima === 'Alta' ? 'alerta' : 'aviso';
  }
}
