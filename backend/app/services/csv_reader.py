from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from app.core.errors import (
    ArchivoInvalidoError,
    ArchivoVacioError,
    EstructuraInvalidaError,
)

CODIFICACIONES = ("utf-8-sig", "utf-8", "cp1252", "latin-1")

DELIMITADORES = (",", ";", "\t", "|")

_SOLO_DIGITOS_Y_SEPARADORES = re.compile(r"^-?[\d.,\s]+$")


@dataclass(frozen=True)
class FilaCsv:
    numero_fila: int
    datos: dict[str, str]

    def texto(self, campo: str) -> str:
        return (self.datos.get(campo) or "").strip()


@dataclass(frozen=True)
class ArchivoCsv:
    nombre: str
    columnas: tuple[str, ...]
    filas: tuple[FilaCsv, ...]

    @property
    def total_filas(self) -> int:
        return len(self.filas)


def _decodificar(contenido: bytes, nombre: str) -> str:
    for codificacion in CODIFICACIONES:
        try:
            return contenido.decode(codificacion)
        except UnicodeDecodeError:
            continue
    raise ArchivoInvalidoError(
        f"No fue posible decodificar el archivo '{nombre}'. "
        f"Guárdelo como CSV UTF-8 e intente nuevamente.",
        {"archivo": nombre, "codificaciones_intentadas": list(CODIFICACIONES)},
    )


def _detectar_delimitador(muestra: str) -> str:
    try:
        dialecto = csv.Sniffer().sniff(muestra, delimiters="".join(DELIMITADORES))
        return dialecto.delimiter
    except csv.Error:
        # Si el Sniffer no se decide, gana el separador más frecuente.
        primera_linea = muestra.splitlines()[0] if muestra.splitlines() else ""
        conteos = {d: primera_linea.count(d) for d in DELIMITADORES}
        mejor = max(conteos, key=lambda d: conteos[d])
        return mejor if conteos[mejor] > 0 else ","


def _normalizar_columna(nombre: str) -> str:
    return nombre.replace("﻿", "").strip().lower().replace(" ", "_")


def leer_csv(
    contenido: bytes,
    nombre: str,
    columnas_requeridas: tuple[str, ...],
) -> ArchivoCsv:
    """Lee un CSV en memoria y valida que traiga las columnas mínimas."""
    if not nombre.lower().endswith(".csv"):
        raise ArchivoInvalidoError(
            f"El archivo '{nombre}' no tiene extensión .csv. "
            f"Solo se aceptan archivos CSV.",
            {"archivo": nombre},
        )

    if not contenido.strip():
        raise ArchivoVacioError(
            f"El archivo '{nombre}' está vacío.", {"archivo": nombre}
        )

    texto = _decodificar(contenido, nombre)
    delimitador = _detectar_delimitador(texto[:4096])

    try:
        lector = csv.DictReader(io.StringIO(texto), delimiter=delimitador)
        encabezados_crudos = lector.fieldnames or []
        columnas = tuple(_normalizar_columna(c) for c in encabezados_crudos if c)
    except csv.Error as exc:
        raise ArchivoInvalidoError(
            f"El archivo '{nombre}' no se pudo interpretar como CSV: {exc}",
            {"archivo": nombre},
        ) from exc

    if not columnas:
        raise ArchivoInvalidoError(
            f"El archivo '{nombre}' no tiene fila de encabezados.",
            {"archivo": nombre},
        )

    faltantes = [c for c in columnas_requeridas if c not in columnas]
    if faltantes:
        raise EstructuraInvalidaError(
            f"Al archivo '{nombre}' le faltan columnas obligatorias: "
            f"{', '.join(faltantes)}.",
            {
                "archivo": nombre,
                "columnas_faltantes": faltantes,
                "columnas_encontradas": list(columnas),
                "columnas_esperadas": list(columnas_requeridas),
            },
        )

    filas: list[FilaCsv] = []
    # Arranca en 2 porque la línea 1 del archivo es el encabezado.
    for numero_fila, fila_cruda in enumerate(lector, start=2):
        normalizada = {
            _normalizar_columna(clave): (valor if valor is not None else "")
            for clave, valor in fila_cruda.items()
            if clave is not None
        }
        if not any(str(v).strip() for v in normalizada.values()):
            continue
        filas.append(FilaCsv(numero_fila=numero_fila, datos=normalizada))

    if not filas:
        raise ArchivoVacioError(
            f"El archivo '{nombre}' tiene encabezados pero ninguna fila de datos.",
            {"archivo": nombre},
        )

    return ArchivoCsv(nombre=nombre, columnas=columnas, filas=tuple(filas))


def parsear_decimal(valor: str) -> Decimal | None:
    """Texto a Decimal. Devuelve None si viene vacío o no se puede leer.

    Acepta tanto `1.234.567,89` como `1,234,567.89` y `1234567.89`.
    """
    texto = (valor or "").strip().replace(" ", "").replace("$", "")
    if not texto:
        return None

    negativo = texto.startswith("-") or (texto.startswith("(") and texto.endswith(")"))
    texto = texto.lstrip("-").strip("()")

    if not _SOLO_DIGITOS_Y_SEPARADORES.match(texto):
        return None

    if "," in texto and "." in texto:
        # El separador decimal es el que aparece de último.
        if texto.rfind(",") > texto.rfind("."):
            texto = texto.replace(".", "").replace(",", ".")
        else:
            texto = texto.replace(",", "")
    elif "," in texto:
        entero, _, decimales = texto.rpartition(",")
        # "1,234" con 3 dígitos a la derecha lo tomo como separador de miles.
        texto = (
            texto.replace(",", "")
            if len(decimales) == 3 and entero
            else texto.replace(",", ".")
        )
    elif texto.count(".") > 1:
        # Varios puntos solo pueden ser separadores de miles: "4.435.200".
        texto = texto.replace(".", "")

    try:
        numero = Decimal(texto)
    except InvalidOperation:
        return None
    return -numero if negativo else numero


def parsear_fecha(valor: str) -> date | None:
    texto = (valor or "").strip()
    if not texto:
        return None
    for formato in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    return None
