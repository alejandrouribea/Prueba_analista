// Si el backend se levanta en otro puerto, apiBaseUrl es lo único que hay que cambiar.
export const environment = {
  produccion: false,
  apiBaseUrl: 'http://localhost:8000/api/v1',
  // CSV de ejemplo servidos desde public/, para probar sin buscar archivos.
  archivosEjemplo: {
    facturas: 'datos-ejemplo/facturas.csv',
    contabilidad: 'datos-ejemplo/contabilidad.csv',
  },
};
