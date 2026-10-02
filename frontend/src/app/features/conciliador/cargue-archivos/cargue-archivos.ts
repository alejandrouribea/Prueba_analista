import { ChangeDetectionStrategy, Component, computed, input, output, signal } from '@angular/core';

import { environment } from '../../../../environments/environment';

export type RanuraArchivo = 'facturas' | 'contabilidad';

export interface ArchivosSeleccionados {
  facturas: File;
  contabilidad: File;
}

/**
 * Cargue de los dos CSV. Se valida en el navegador antes de llamar a la API
 * para que el usuario tenga respuesta de una y no se mande una petición que
 * el backend va a rechazar igual.
 */
@Component({
  selector: 'app-cargue-archivos',
  templateUrl: './cargue-archivos.html',
  styleUrl: './cargue-archivos.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CargueArchivos {
  readonly procesando = input<boolean>(false);

  readonly procesar = output<ArchivosSeleccionados>();

  protected readonly facturas = signal<File | null>(null);
  protected readonly contabilidad = signal<File | null>(null);
  protected readonly errorLocal = signal<string | null>(null);
  protected readonly ranuraActiva = signal<RanuraArchivo | null>(null);
  protected readonly cargandoEjemplo = signal(false);

  protected readonly listoParaProcesar = computed(
    () => this.facturas() !== null && this.contabilidad() !== null && !this.procesando(),
  );

  protected readonly ranuras = computed(() => [
    {
      id: 'facturas' as const,
      titulo: 'facturas.csv',
      descripcion: 'Facturas de proveedores',
      archivo: this.facturas(),
    },
    {
      id: 'contabilidad' as const,
      titulo: 'contabilidad.csv',
      descripcion: 'Registros contabilizados',
      archivo: this.contabilidad(),
    },
  ]);

  protected alSeleccionar(evento: Event, ranura: RanuraArchivo): void {
    const input = evento.target as HTMLInputElement;
    const archivo = input.files?.[0] ?? null;
    if (archivo) {
      this.asignar(archivo, ranura);
    }
    // Permite volver a elegir el mismo archivo tras corregirlo.
    input.value = '';
  }

  protected alArrastrar(evento: DragEvent, ranura: RanuraArchivo): void {
    evento.preventDefault();
    if (!this.procesando()) {
      this.ranuraActiva.set(ranura);
    }
  }

  protected alSalir(evento: DragEvent): void {
    evento.preventDefault();
    this.ranuraActiva.set(null);
  }

  protected alSoltar(evento: DragEvent, ranura: RanuraArchivo): void {
    evento.preventDefault();
    this.ranuraActiva.set(null);
    if (this.procesando()) {
      return;
    }
    const archivo = evento.dataTransfer?.files?.[0];
    if (archivo) {
      this.asignar(archivo, ranura);
    }
  }

  protected quitar(ranura: RanuraArchivo): void {
    this.destino(ranura).set(null);
    this.errorLocal.set(null);
  }

  protected enviar(): void {
    const facturas = this.facturas();
    const contabilidad = this.contabilidad();
    if (!facturas || !contabilidad) {
      this.errorLocal.set('Seleccione los dos archivos antes de procesar.');
      return;
    }
    this.errorLocal.set(null);
    this.procesar.emit({ facturas, contabilidad });
  }

  /** Carga los CSV de ejemplo que vienen con la entrega. */
  protected async usarArchivosDeEjemplo(): Promise<void> {
    this.cargandoEjemplo.set(true);
    this.errorLocal.set(null);
    try {
      const [facturas, contabilidad] = await Promise.all([
        this.descargarEjemplo(environment.archivosEjemplo.facturas, 'facturas.csv'),
        this.descargarEjemplo(
          environment.archivosEjemplo.contabilidad,
          'contabilidad.csv',
        ),
      ]);
      this.facturas.set(facturas);
      this.contabilidad.set(contabilidad);
      this.procesar.emit({ facturas, contabilidad });
    } catch {
      this.errorLocal.set(
        'No fue posible cargar los archivos de ejemplo incluidos en la aplicación.',
      );
    } finally {
      this.cargandoEjemplo.set(false);
    }
  }

  protected formatearTamano(bytes: number): string {
    if (bytes < 1024) {
      return `${bytes} B`;
    }
    const kb = bytes / 1024;
    return kb < 1024 ? `${kb.toFixed(1)} KB` : `${(kb / 1024).toFixed(1)} MB`;
  }

  private destino(ranura: RanuraArchivo) {
    return ranura === 'facturas' ? this.facturas : this.contabilidad;
  }

  private asignar(archivo: File, ranura: RanuraArchivo): void {
    const problema = this.validar(archivo);
    if (problema) {
      this.errorLocal.set(problema);
      return;
    }
    this.errorLocal.set(null);
    this.destino(ranura).set(archivo);
  }

  private validar(archivo: File): string | null {
    if (!archivo.name.toLowerCase().endsWith('.csv')) {
      return `"${archivo.name}" no es un archivo CSV. Exporte el archivo como CSV e intente de nuevo.`;
    }
    if (archivo.size === 0) {
      return `"${archivo.name}" está vacío.`;
    }
    return null;
  }

  private async descargarEjemplo(ruta: string, nombre: string): Promise<File> {
    const respuesta = await fetch(ruta);
    if (!respuesta.ok) {
      throw new Error(`No se pudo leer ${ruta}`);
    }
    const blob = await respuesta.blob();
    return new File([blob], nombre, { type: 'text/csv' });
  }
}
