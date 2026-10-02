import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';

import { ConciliacionService } from '../../../core/services/conciliacion.service';
import { ConciliacionStore } from '../../../core/state/conciliacion.store';
import { ArchivosSeleccionados, CargueArchivos } from '../cargue-archivos/cargue-archivos';
import { ResumenConciliacion } from '../resumen-conciliacion/resumen-conciliacion';
import { TablaFacturas } from '../tabla-facturas/tabla-facturas';


@Component({
  selector: 'app-conciliador-page',
  templateUrl: './conciliador-page.html',
  styleUrl: './conciliador-page.scss',
  imports: [CargueArchivos, ResumenConciliacion, TablaFacturas],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ConciliadorPage {
  private readonly store = inject(ConciliacionStore);
  private readonly api = inject(ConciliacionService);

  protected readonly estado = this.store.estado;
  protected readonly cargando = this.store.cargando;
  protected readonly error = this.store.error;
  protected readonly resultado = this.store.resultado;
  protected readonly resumen = this.store.resumen;

  // Se verifica al abrir la pantalla, para avisar si el backend no está arriba.
  protected readonly backendDisponible = signal<boolean | null>(null);

  protected readonly archivosProcesados = computed(
    () => this.resultado()?.archivos ?? [],
  );

  constructor() {
    this.verificarBackend();
  }

  protected procesar(archivos: ArchivosSeleccionados): void {
    this.store.procesar(archivos.facturas, archivos.contabilidad);
  }

  protected filtrarPorRegla(codigo: string): void {
    this.store.filtrarPorRegla(codigo);
    document
      .getElementById('titulo-detalle')
      ?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  protected reiniciar(): void {
    this.store.reiniciar();
  }

  protected verificarBackend(): void {
    this.api.health().subscribe({
      next: () => this.backendDisponible.set(true),
      error: () => this.backendDisponible.set(false),
    });
  }
}
