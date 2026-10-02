import { Pipe, PipeTransform } from '@angular/core';

/** 1234567 -> $ 1.234.567. Los nulos salen con guion, para no confundir
 *  "sin dato" con "cero". */
@Pipe({ name: 'monedaCop' })
export class MonedaCopPipe implements PipeTransform {
  private readonly formato = new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: 'COP',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  });

  transform(valor: number | null | undefined, vacio = '—'): string {
    if (valor === null || valor === undefined || Number.isNaN(valor)) {
      return vacio;
    }
    return this.formato.format(valor);
  }
}
