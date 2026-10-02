# Conciliador de facturas y retenciones

Prototipo full stack para la **Gerencia de Evolución Contable y Tributaria**.
Cruza el archivo mensual de facturas de proveedores con el de registros
contabilizados, aplica las reglas de validación tributaria y presenta un
resumen ejecutivo y el detalle de las inconsistencias para su gestión.

- **Backend:** Python 3.12 + FastAPI (API REST, procesamiento *stateless*).
- **Frontend:** Angular 21 (pantalla única, componentes standalone + signals).

---

## 1. Tabla de contenido

1. [Requisitos](#2-requisitos)
2. [Instalación y ejecución](#3-instalación-y-ejecución)
3. [Verificación rápida](#4-verificación-rápida-de-la-entrega)
4. [Reglas de negocio](#5-reglas-de-negocio-implementadas)
5. [Resultados esperados con los archivos de prueba](#6-resultados-esperados-con-los-archivos-de-prueba)
6. [API REST](#7-api-rest)
7. [Estructura del proyecto](#8-estructura-del-proyecto)
8. [Decisiones técnicas y supuestos](#9-decisiones-técnicas-y-supuestos)
9. [Pruebas automatizadas](#10-pruebas-automatizadas)
10. [Funcionalidades no incluidas](#11-funcionalidades-no-incluidas)
11. [Solución de problemas](#12-solución-de-problemas)
12. [Presentación ejecutiva](#13-presentación-ejecutiva)
13. [Declaración de uso de IA](#14-declaración-de-uso-de-ia)

---

## 2. Requisitos

| Herramienta | Versión usada | Versión mínima | Verificación |
|-------------|---------------|----------------|--------------|
| Python      | 3.12.2        | 3.11           | `python --version` |
| Node.js     | 22.16.0       | 20.19          | `node --version` |
| npm         | 10.9.2        | 10             | `npm --version` |


### Dependencias principales

**Backend** (`backend/requirements.txt`)

| Paquete | Versión | Para qué |
|---------|---------|----------|
| `fastapi` | 0.115.6 | Framework de la API REST |
| `uvicorn[standard]` | 0.34.0 | Servidor ASGI |
| `python-multipart` | 0.0.20 | Recepción de archivos `multipart/form-data` |
| `pydantic` | 2.10.4 | Validación y serialización del contrato |
| `pydantic-settings` | 2.7.0 | Configuración por variables de entorno |


**Frontend** (`frontend/package.json`): Angular 21.2 (`common`, `core`,
`forms`, `compiler`, `platform-browser`), RxJS 7.8 y TypeScript 5.9. Sin
librerías de UI de terceros.

---

## 3. Instalación y ejecución

Se necesitan **dos terminales**: una para el backend y otra para el frontend.

### 3.1 Backend (terminal 1)

```bash
cd backend

# Crear y activar el entorno virtual
python -m venv .venv

# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1
# Windows (CMD)
.venv\Scripts\activate.bat
# macOS / Linux
source .venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Levantar la API en el puerto 8000
uvicorn app.main:app --reload --port 8000
```

El backend queda disponible en **http://localhost:8000** y la documentación
interactiva (Swagger UI) en **http://localhost:8000/docs**.

> Si PowerShell bloquea la activación del entorno virtual, ejecute una vez:
> `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`

### 3.2 Frontend (terminal 2)

```bash
cd frontend

npm install
npm start
```

La aplicación queda disponible en **http://localhost:4200**.

### 3.3 Configuración

Ambos lados funcionan sin configuración adicional. Los valores por defecto son:

| Parámetro | Valor | Dónde cambiarlo |
|-----------|-------|-----------------|
| Puerto del backend | 8000 | `uvicorn ... --port <puerto>` |
| URL de la API | `http://localhost:8000/api/v1` | `frontend/src/environments/environment.ts` |
| Orígenes CORS permitidos | `http://localhost:4200` | `CONCILIADOR_CORS_ORIGENES` |
| Tolerancia de comparación | 1 COP | `CONCILIADOR_TOLERANCIA_PESOS` |

Para sobreescribirlos, copie `backend/.env.example` como `backend/.env`.
**Si cambia el puerto del backend**, actualice también `apiBaseUrl` en
`frontend/src/environments/environment.ts`.

---

## 4. Verificación rápida de la entrega

Con ambos servicios arriba:

1. Abra **http://localhost:4200**.
2. Pulse **«Usar archivos de ejemplo»** (carga y procesa automáticamente los
   CSV incluidos en la entrega), o cargue manualmente `datos_prueba/facturas.csv`
   y `datos_prueba/contabilidad.csv` y pulse **«Procesar conciliación»**.
3. Debe ver el resumen con **50 facturas procesadas, 28 correctas y 22 con
   inconsistencia**.
4. Use el filtro **Estado → Con inconsistencia** para ver solo las novedades, o
   haga clic en cualquier regla del panel «Inconsistencias por regla» para
   filtrar por esa causa.
5. Expanda cualquier fila con el botón **+** para ver la trazabilidad del
   cálculo (valor reportado vs. esperado) y la explicación de cada hallazgo.

---

## 5. Reglas de negocio implementadas

Todas las reglas están declaradas en un único archivo auditable:
`backend/app/domain/reglas.py`. El catálogo también se expone en
`GET /api/v1/reglas`.

### 5.1 Reglas mínimas exigidas por el caso

| # | Regla | Código | Cálculo |
|---|-------|--------|---------|
| 1 | IVA esperado | `IVA_CALCULADO_NO_COINCIDE` | `base_gravable × tarifa_iva` comparado con `valor_iva` |
| 2 | Total de la factura | `TOTAL_FACTURA_NO_COINCIDE` | `base_gravable + valor_iva − valor_retencion` comparado con `total_factura` |
| 3a | Facturas duplicadas | `FACTURA_DUPLICADA` | `id_factura` repetido en `facturas.csv` |
| 3b | Facturas sin registro contable | `SIN_REGISTRO_CONTABLE` | `id_factura` ausente en `contabilidad.csv` |
| 4 | Clasificación | — | `Correcta` si no hay hallazgos; `Con inconsistencia` en caso contrario, indicando la causa |
| 5 | Resumen | — | Total de facturas, correctas, con inconsistencia y número de hallazgos |

### 5.2 Controles complementarios

Se añadieron porque son los que un analista revisa de todos modos al conciliar,
y porque los archivos de ejemplo los activan:

| Regla | Código | Severidad | Qué detecta |
|-------|--------|-----------|-------------|
| Retención mal liquidada | `RETENCION_CALCULADA_NO_COINCIDE` | Alta | `base_gravable × tarifa_retencion ≠ valor_retencion`; afecta el certificado de retención |
| Valor contabilizado distinto | `DIFERENCIA_VALOR_CONTABILIZADO` | Alta | `valor_debito ≠ total_factura`: se causó por un valor diferente |
| Partida doble descuadrada | `PARTIDA_DOBLE_DESCUADRADA` | Alta | `valor_debito ≠ valor_credito` en el asiento |
| Registro contable duplicado | `REGISTRO_CONTABLE_DUPLICADO` | Alta | La misma factura tiene más de un movimiento contable |
| Valor numérico ilegible | `VALOR_NO_NUMERICO` | Alta | Un importe o tarifa no se puede interpretar como número |
| Campo obligatorio vacío | `CAMPO_OBLIGATORIO_VACIO` | Media | Falta NIT, fecha, concepto, base gravable o total |
| Pendiente de contabilizar | `ESTADO_NO_CONTABILIZADO` | Media | El estado contable no es `Contabilizada` |
| Fecha incoherente | `FECHA_CONTABILIZACION_ANTERIOR` | Media | Se contabilizó antes de la fecha de emisión de la factura |
| Tarifa de IVA no vigente | `TARIFA_IVA_NO_VIGENTE` | Media | Tarifa distinta de 0 %, 5 % o 19 % |
| Tarifa de retención no parametrizada | `TARIFA_RETENCION_NO_PARAMETRIZADA` | Baja | Tarifa distinta de 0 %, 2,5 %, 3,5 % o 4 % |
| Contabilidad sin factura soporte | `CONTABILIDAD_SIN_FACTURA` | Alta | Movimiento contable cuyo `id_factura` no existe en `facturas.csv` |

### 5.3 Severidades

| Severidad | Criterio |
|-----------|----------|
| **Alta** | Afecta la declaración tributaria o el valor registrado en libros |
| **Media** | Afecta la trazabilidad o el cierre contable del periodo |
| **Baja** | Calidad del dato; no altera cifras |

---




## 6. API REST

Base: `http://localhost:8000/api/v1`

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/health` | Estado del servicio (el frontend lo consulta al abrir) |
| `GET` | `/reglas` | Catálogo de reglas con código, descripción y severidad |
| `POST` | `/conciliacion` | Procesa ambos CSV y devuelve resumen + detalle |

### `POST /api/v1/conciliacion`

**Entrada:** `multipart/form-data` con dos campos de archivo:

| Campo | Archivo | Columnas obligatorias |
|-------|---------|-----------------------|
| `facturas` | `facturas.csv` | `id_factura`, `nit_proveedor`, `fecha_factura`, `concepto`, `base_gravable`, `tarifa_iva`, `valor_iva`, `tarifa_retencion`, `valor_retencion`, `total_factura` |
| `contabilidad` | `contabilidad.csv` | `id_factura`, `fecha_contabilizacion`, `cuenta_contable`, `centro_costo`, `valor_debito`, `valor_credito`, `estado` |

**Ejemplo con curl:**

```bash
curl -X POST http://localhost:8000/api/v1/conciliacion \
  -F "facturas=@datos_prueba/facturas.csv" \
  -F "contabilidad=@datos_prueba/contabilidad.csv"
```

**Respuesta (`200 OK`, abreviada):**

```jsonc
{
  "procesado_en": "2026-10-01T02:29:00+00:00",
  "tolerancia_pesos": 1.0,
  "archivos": [
    { "nombre": "facturas.csv", "filas": 50, "columnas": ["id_factura", "..."] },
    { "nombre": "contabilidad.csv", "filas": 50, "columnas": ["id_factura", "..."] }
  ],
  "resumen": {
    "total_facturas": 50,
    "facturas_correctas": 28,
    "facturas_con_inconsistencia": 22,
    "total_inconsistencias": 31,
    "porcentaje_correctas": 56.0,
    "facturas_duplicadas": 4,
    "facturas_sin_registro_contable": 4,
    "registros_contables_sin_factura": 0,
    "facturas_pendientes_contabilizar": 3,
    "por_severidad": { "Alta": 24, "Media": 7 },
    "por_categoria": { "Integridad": 11, "Conciliación": 10, "Impuestos": 7, "Calidad del dato": 3 },
    "por_regla": [{ "codigo": "REGISTRO_CONTABLE_DUPLICADO", "cantidad": 7, "severidad": "Alta", "...": "..." }],
    "montos": {
      "total_facturado": 136823950.0,
      "monto_con_inconsistencia": 68229050.0,
      "diferencia_absoluta_detectada": 1765400.0
    }
  },
  "detalle": [
    {
      "fila": 7,
      "id_factura": "FAC-0006",
      "base_gravable": 3800000.0,
      "tarifa_iva": 0.05,
      "valor_iva": 215000.0,
      "iva_esperado": 190000.0,
      "diferencia_iva": 25000.0,
      "total_factura": 3990000.0,
      "total_esperado": 4015000.0,
      "diferencia_total": -25000.0,
      "clasificacion": "Con inconsistencia",
      "severidad_maxima": "Alta",
      "codigos_inconsistencia": ["IVA_CALCULADO_NO_COINCIDE", "TOTAL_FACTURA_NO_COINCIDE"],
      "causas": "IVA liquidado distinto al IVA esperado | Total de la factura mal liquidado",
      "hallazgos": [
        {
          "codigo": "IVA_CALCULADO_NO_COINCIDE",
          "severidad": "Alta",
          "mensaje": "El IVA facturado ($ 215.000) difiere del IVA esperado ($ 190.000) = base $ 3.800.000 x 5%. Diferencia: $ 25.000.",
          "valor_esperado": 190000.0,
          "valor_encontrado": 215000.0,
          "diferencia": 25000.0
        }
      ],
      "registros_contables": [{ "fila": 7, "valor_debito": 3990000.0, "estado": "Contabilizada" }]
    }
  ],
  "contabilidad_sin_factura": []
}
```

### Manejo de errores

Todos los errores comparten el mismo contrato:

```json
{ "error": { "codigo": "ESTRUCTURA_INVALIDA", "mensaje": "…", "detalle": { } } }
```

| HTTP | Código | Cuándo ocurre |
|------|--------|---------------|
| 400 | `ARCHIVO_INVALIDO` | Falta un archivo, no tiene extensión `.csv`, no se puede decodificar o no tiene encabezados |
| 422 | `ESTRUCTURA_INVALIDA` | Faltan columnas obligatorias (se listan en `detalle.columnas_faltantes`) |
| 422 | `ARCHIVO_VACIO` | El archivo no trae filas de datos |
| 422 | `SOLICITUD_INVALIDA` | La petición no cumple el contrato de FastAPI |
| 500 | `ERROR_INTERNO` | Error inesperado (nunca se devuelve el stacktrace) |

---



## 7. Decisiones técnicas y supuestos

### Supuestos de negocio

1. **La llave de cruce es `id_factura`.** Es el único campo común a ambos
   archivos. No se usa el NIT porque en los duplicados del archivo de ejemplo
   el mismo `id_factura` llega con proveedores distintos.
2. **Tolerancia de ±1 COP** al comparar importes. Los archivos vienen
   redondeados a la unidad, de modo que 1 peso absorbe el redondeo sin ocultar
   diferencias reales. Es configurable (`CONCILIADOR_TOLERANCIA_PESOS`).
3. **El total se valida con los valores reportados**, no con los esperados:
   `total = base_gravable + valor_iva − valor_retencion`. Así un error de IVA
   no contamina el diagnóstico del total, y se distingue «liquidaron mal el
   IVA» de «liquidaron mal la suma».
4. **Las duplicadas se marcan todas**, no solo la segunda ocurrencia: el
   analista debe decidir cuál es la válida, y cada fila indica su posición
   (`ocurrencia` / `total_ocurrencias`).
5. **Si una factura tiene varios registros contables**, se reporta el duplicado
   y las comparaciones de valor se hacen contra **el primer registro del
   archivo**. Los demás se muestran íntegros al expandir la fila.
6. **Una factura es `Correcta` solo si no tiene ningún hallazgo**, de cualquier
   severidad. Se prefirió un criterio estricto y mostrar la severidad para
   priorizar, antes que ocultar novedades menores.
7. **Los registros contables sin factura soporte se reportan aparte**, en su
   propia sección: no son facturas y contarlos en el total distorsionaría el
   indicador.

### Decisiones técnicas

| Decisión | Motivo |
|----------|--------|
| **FastAPI** sobre Flask | Validación y documentación OpenAPI automáticas; `/docs` sirve de evidencia funcional del backend |
| **`csv` + `Decimal`** en vez de pandas | Control fino sobre celdas vacías, separadores decimales y valores ilegibles —justo donde están los casos de prueba—, sin dependencias pesadas. `Decimal` evita errores de punto flotante en cifras tributarias |
| **Procesamiento *stateless*** | Nada se guarda en disco ni en memoria entre peticiones: no se persiste información de proveedores en el servidor |
| **Catálogo de reglas declarativo** | `reglas.py` concentra códigos, descripciones y severidades; backend, pruebas y frontend comparten el mismo vocabulario y la lógica es auditable en un archivo |
| **Capa `respuesta.py` separada** | El contrato de la API puede evolucionar sin tocar el motor de conciliación |
| **Importes como `float` en JSON** | Pydantic serializa `Decimal` como texto; se convierte en el borde para que Angular reciba números nativos. El cálculo interno siempre es `Decimal` |
| **Angular standalone + signals** | Es el estándar de Angular 21; el filtrado es un `computed()` reactivo en vez de recalcularse a mano en cada evento |
| **Store centralizado** | Los componentes quedan como vistas sin lógica (patrón contenedor/presentación) |
| **CSS propio, sin librería de UI** | Mantiene la entrega liviana y reproducible; tema claro/oscuro con variables CSS |
| **Tolerancia a formatos de CSV** | Se detectan automáticamente el separador (`,` `;` tab `|`) y la codificación (UTF-8 con/sin BOM, CP1252, Latin-1), y se aceptan `1.234.567,89`, `1,234,567.89` y fechas `dd/mm/aaaa`. Un export de Excel en español funciona sin configuración |

---

## 10. Pruebas automatizadas

El backend incluye **43 pruebas** (una por regla de negocio, más el flujo de la
API y el manejo de errores):

```bash
cd backend
pip install -r requirements-dev.txt
pytest
```

Salida esperada: `43 passed`.

Cubren:

- **Reglas de negocio** (`tests/test_reglas_negocio.py`): una prueba por regla,
  con los importes verificados a mano; tolerancia; parseo de decimales con
  separadores mixtos y de fechas en varios formatos.
- **API** (`tests/test_api.py`): flujo completo con los archivos reales del
  caso, coherencia del resumen contra el detalle, trazabilidad del cálculo,
  y los errores de archivo faltante, extensión inválida, columnas faltantes,
  archivo vacío y CSV con punto y coma en Latin-1.

---

## 11. Funcionalidades no incluidas

Declaradas de forma explícita, en línea con el alcance de prototipo:

| No incluido | Razón / alternativa |
|-------------|---------------------|
| **Persistencia e historial** | El procesamiento es *stateless* por diseño. Un siguiente paso sería guardar cada corrida para comparar periodos |
| **Autenticación y roles** | No aplica a un prototipo local sin datos reales |
| **Despliegue** | No se incluyen Dockerfile ni pipeline; la ejecución es local según este README |
| **Carga desde Excel (.xlsx)** | Solo CSV, como define el caso |
---

## 12. Solución de problemas

| Síntoma | Causa y solución |
|---------|------------------|
| La interfaz muestra «No se detecta el backend» | El backend no está arriba o usa otro puerto. Levántelo con `uvicorn app.main:app --reload --port 8000` y pulse «Reintentar» |
| Error de CORS en la consola del navegador | El frontend no está en `http://localhost:4200`. Agregue su origen a `CONCILIADOR_CORS_ORIGENES` en `backend/.env` |
| `ModuleNotFoundError: No module named 'app'` | Ejecute `uvicorn` **desde la carpeta `backend/`**, no desde la raíz |
| `ERROR: Could not find a version that satisfies...` | La versión de Python es menor a 3.11. Verifique con `python --version` |
| PowerShell bloquea la activación del venv | `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` |
| El puerto 8000 o 4200 está ocupado | Use otro puerto (`--port 8001`, `npm start -- --port 4300`) y actualice `apiBaseUrl` / `CONCILIADOR_CORS_ORIGENES` |
| Los acentos se ven mal al abrir el CSV exportado en Excel | El archivo se genera en UTF-8 con BOM y separador `;`. Si su Excel usa coma como separador de lista, use *Datos → Desde texto/CSV* |

---