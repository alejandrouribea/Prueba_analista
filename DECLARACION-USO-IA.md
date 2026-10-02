# Declaración sobre el uso de inteligencia artificial generativa


## Resumen

**Sí se utilizó inteligencia artificial generativa** durante el desarrollo de
esta prueba, como herramienta de apoyo. A continuación indico en qué partes
concretas de la solución se empleó y con qué propósito.


---

## En qué partes se empleó

### 1. Pruebas automatizadas del backend

**Archivos:** `backend/tests/test_reglas_negocio.py`, `backend/tests/test_api.py`,
`backend/tests/conftest.py`

**Para qué:** generar la batería de pruebas unitarias y de integración a partir
de las reglas de negocio que ya había definido. Le pedí una prueba por cada
regla, más los casos de error de la API (archivo faltante, extensión inválida,
columnas faltantes, archivo vacío, CSV con punto y coma en Latin-1).

**Qué aportó:** la estructura de los casos, los *fixtures* para construir CSV en
memoria y la cobertura de los caminos de error, que es la parte más repetitiva
de escribir.

**Qué verifiqué yo:** los importes de cada caso de prueba están calculados y
comprobados a mano. Por ejemplo, en `test_iva_mal_liquidado_se_detecta_con_su_diferencia`
la base es 1.000.000 al 19 %, el IVA esperado es 190.000 y la diferencia contra
los 200.000 reportados es 10.000. Cada aserción refleja un resultado contable
que validé por aparte antes de darla por buena.

---

### 2. Ampliación del catálogo de reglas del backend

**Archivo:** `backend/app/domain/reglas.py`

**Para qué:** las cuatro reglas mínimas que pide el caso (IVA esperado, total de
la factura, duplicados y facturas sin registro contable) las definí yo, porque
vienen dadas en el enunciado. Lo que consulté con la IA fue **qué otros
controles tiene sentido agregar** en una conciliación de cuentas por pagar, para
no quedarme solo con el mínimo.

**Qué aportó:** la propuesta de los controles complementarios y su agrupación por
categoría y severidad. De ahí salieron reglas como partida doble descuadrada,
registro contable duplicado, diferencia entre el valor contabilizado y el total
de la factura, coherencia de fechas de causación y validación de tarifas contra
un catálogo parametrizado.

**Qué decidí yo:** cuáles de las propuestas aplicaban realmente al caso y a los
datos entregados, y cuáles descarté. También la asignación final de severidades,
con el criterio de que **Alta** es lo que afecta la declaración tributaria o el
valor en libros, **Media** lo que afecta el cierre o la trazabilidad, y **Baja**
lo que es calidad del dato. Las tarifas parametrizadas (IVA 0 %, 5 % y 19 %;
retención 0 %, 2,5 %, 3,5 % y 4 %) las fijé según la normativa colombiana y los
conceptos que aparecen en los archivos de prueba.

---

### 3. Forma de presentar la trazabilidad del cálculo

**Archivos:** `frontend/src/app/features/conciliador/tabla-facturas/tabla-facturas.html`
y los mensajes de hallazgo en `backend/app/services/conciliador.py`

**Para qué:** tenía claro que no bastaba con marcar una factura en rojo, que el
analista necesita ver por qué. Lo que consulté fue **cómo mostrar esa
trazabilidad** de forma que se entienda de un vistazo.

**Qué aportó:** la idea de la tabla comparativa de tres columnas —valor
reportado, valor esperado y diferencia— dentro de la fila expandible, y la de
redactar cada hallazgo con la operación completa en el texto, en lugar de un
mensaje genérico. Por ejemplo: «El IVA facturado ($ 215.000) difiere del IVA
esperado ($ 190.000) = base $ 3.800.000 x 5 %. Diferencia: $ 25.000».

**Qué definí yo:** qué conceptos entran en esa comparación (IVA, retención,
total y valor contabilizado) y cómo se calcula cada uno, que es la parte
contable de la decisión.

---

### 4. Redacción de los README

**Archivos:** `README.md` (raíz del proyecto) y `frontend/README.md`

**Para qué:** redactar la documentación de instalación y ejecución sobre la
solución ya construida, de manera que el evaluador pueda reproducir la entrega
siguiendo únicamente el README, como lo pide el enunciado.

**Qué aportó:** la estructura del documento y la redacción. En concreto: la
tabla de requisitos con versiones, los pasos de instalación diferenciados por
sistema operativo, la tabla de parámetros configurables, la documentación de los
tres endpoints con su ejemplo de respuesta, la tabla de códigos de error y el
apartado de solución de problemas.

**Qué verifiqué yo:** que los comandos funcionan tal como están escritos, que
las versiones de la tabla de requisitos corresponden a las que realmente usé,
y que las cifras del apartado «Resultados esperados» coinciden con lo que
devuelve la herramienta al procesar los archivos de prueba. El contenido de las
secciones «Decisiones técnicas y supuestos» y «Funcionalidades no incluidas»
son decisiones mías; la IA solo las puso en palabras.

---


