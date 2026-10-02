import { Pipe, PipeTransform } from '@angular/core';

/** Tarifa decimal a porcentaje: 0.19 -> 19%. */
@Pipe({ name: 'tarifa' })
export class TarifaPipe implements PipeTransform {
  transform(valor: number | null | undefined, vacio = '—'): string {
    if (valor === null || valor === undefined || Number.isNaN(valor)) {
      return vacio;
    }
    // Redondeo para no sacar cosas como "19.000000000000002%".
    const redondeado = Math.round(valor * 100 * 1000) / 1000;
    return `${redondeado}%`;
  }
}
