import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, throwError } from 'rxjs';

import { environment } from '../../../environments/environment';
import { ConciliacionResultado, ErrorApi, Regla } from '../models/conciliacion.model';

/** Error ya traducido a un mensaje que se le puede mostrar al usuario. */
export class ErrorConciliacion extends Error {
  constructor(
    override readonly message: string,
    readonly codigo: string,
    readonly detalle?: Record<string, unknown>,
  ) {
    super(message);
    this.name = 'ErrorConciliacion';
  }
}

@Injectable({ providedIn: 'root' })
export class ConciliacionService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = environment.apiBaseUrl;

  procesar(facturas: File, contabilidad: File): Observable<ConciliacionResultado> {
    const formulario = new FormData();
    formulario.append('facturas', facturas, facturas.name);
    formulario.append('contabilidad', contabilidad, contabilidad.name);

    return this.http
      .post<ConciliacionResultado>(`${this.baseUrl}/conciliacion`, formulario)
      .pipe(catchError((error) => throwError(() => this.traducirError(error))));
  }

  reglas(): Observable<Regla[]> {
    return this.http
      .get<Regla[]>(`${this.baseUrl}/reglas`)
      .pipe(catchError((error) => throwError(() => this.traducirError(error))));
  }

  health(): Observable<{ estado: string; aplicacion: string; version: string }> {
    return this.http
      .get<{ estado: string; aplicacion: string; version: string }>(
        `${this.baseUrl}/health`,
      )
      .pipe(catchError((error) => throwError(() => this.traducirError(error))));
  }

  private traducirError(error: unknown): ErrorConciliacion {
    if (!(error instanceof HttpErrorResponse)) {
      return new ErrorConciliacion(
        'Ocurrió un error inesperado al contactar el servicio.',
        'ERROR_DESCONOCIDO',
      );
    }

    if (error.status === 0) {
      return new ErrorConciliacion(
        `No fue posible conectar con el backend en ${this.baseUrl}. ` +
          'Verifique que el servicio de Python esté ejecutándose.',
        'BACKEND_NO_DISPONIBLE',
      );
    }

    const cuerpo = error.error as { error?: ErrorApi } | null;
    if (cuerpo?.error?.mensaje) {
      return new ErrorConciliacion(
        cuerpo.error.mensaje,
        cuerpo.error.codigo,
        cuerpo.error.detalle,
      );
    }

    return new ErrorConciliacion(
      `El servicio respondió con un error ${error.status}.`,
      'ERROR_HTTP',
    );
  }
}
