import { Injectable, computed, inject, signal } from '@angular/core';

import {
  Clasificacion,
  ConciliacionResultado,
  FacturaDetalle,
  Severidad,
} from '../models/conciliacion.model';
import { ConciliacionService, ErrorConciliacion } from '../services/conciliacion.service';

export type EstadoProceso = 'inicial' | 'cargando' | 'listo' | 'error';

export type FiltroClasificacion = 'todas' | Clasificacion;
export type FiltroSeveridad = 'todas' | Severidad;

/**
 * Estado de la pantalla de conciliación. Teniendo el resultado y los filtros
 * acá los componentes quedan como vistas sin lógica y el filtrado se resuelve
 * con computed() en vez de recalcularlo a mano en cada evento.
 */
@Injectable({ providedIn: 'root' })
export class ConciliacionStore {
  private readonly api = inject(ConciliacionService);

  private readonly _estado = signal<EstadoProceso>('inicial');
  private readonly _resultado = signal<ConciliacionResultado | null>(null);
  private readonly _error = signal<ErrorConciliacion | null>(null);

  readonly estado = this._estado.asReadonly();
  readonly resultado = this._resultado.asReadonly();
  readonly error = this._error.asReadonly();

  readonly cargando = computed(() => this._estado() === 'cargando');
  readonly hayResultado = computed(() => this._resultado() !== null);
  readonly resumen = computed(() => this._resultado()?.resumen ?? null);

  readonly filtroClasificacion = signal<FiltroClasificacion>('todas');
  readonly filtroSeveridad = signal<FiltroSeveridad>('todas');
  readonly filtroRegla = signal<string>('todas');
  readonly busqueda = signal<string>('');

  readonly facturasFiltradas = computed<FacturaDetalle[]>(() => {
    const detalle = this._resultado()?.detalle ?? [];
    const clasificacion = this.filtroClasificacion();
    const severidad = this.filtroSeveridad();
    const regla = this.filtroRegla();
    const texto = this.busqueda().trim().toLowerCase();

    return detalle.filter((factura) => {
      if (clasificacion !== 'todas' && factura.clasificacion !== clasificacion) {
        return false;
      }
      if (severidad !== 'todas' && factura.severidad_maxima !== severidad) {
        return false;
      }
      if (regla !== 'todas' && !factura.codigos_inconsistencia.includes(regla)) {
        return false;
      }
      if (texto) {
        const campos = [
          factura.id_factura,
          factura.nit_proveedor ?? '',
          factura.concepto ?? '',
          factura.causas ?? '',
        ]
          .join(' ')
          .toLowerCase();
        if (!campos.includes(texto)) {
          return false;
        }
      }
      return true;
    });
  });

  readonly totalFiltradas = computed(() => this.facturasFiltradas().length);

  readonly hayFiltrosActivos = computed(
    () =>
      this.filtroClasificacion() !== 'todas' ||
      this.filtroSeveridad() !== 'todas' ||
      this.filtroRegla() !== 'todas' ||
      this.busqueda().trim() !== '',
  );

  procesar(facturas: File, contabilidad: File): void {
    this._estado.set('cargando');
    this._error.set(null);

    this.api.procesar(facturas, contabilidad).subscribe({
      next: (resultado) => {
        this._resultado.set(resultado);
        this.limpiarFiltros();
        this._estado.set('listo');
      },
      error: (error: ErrorConciliacion) => {
        this._resultado.set(null);
        this._error.set(error);
        this._estado.set('error');
      },
    });
  }

  limpiarFiltros(): void {
    this.filtroClasificacion.set('todas');
    this.filtroSeveridad.set('todas');
    this.filtroRegla.set('todas');
    this.busqueda.set('');
  }

  /** Lo usan las tarjetas del resumen para filtrar el detalle con un clic. */
  filtrarPorRegla(codigo: string): void {
    this.filtroClasificacion.set('todas');
    this.filtroSeveridad.set('todas');
    this.busqueda.set('');
    this.filtroRegla.set(codigo);
  }

  reiniciar(): void {
    this._estado.set('inicial');
    this._resultado.set(null);
    this._error.set(null);
    this.limpiarFiltros();
  }
}
