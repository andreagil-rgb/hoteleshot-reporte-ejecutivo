# -*- coding: utf-8 -*-
"""
Utilidades para leer Google Sheets y parsear fechas en los múltiples
formatos que se usan en las bases de Hoteles HOT.
"""
import re
import datetime as dt

MESES_ES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}


def parse_fecha(valor):
    """
    Convierte una fecha en cualquiera de los formatos usados en las bases a
    un objeto date. Devuelve None si no se puede interpretar o si viene vacía.

    Formatos soportados:
      - DD/MM/YY o DD/MM/YYYY   (08/09/25, 22/07/2026)
      - DD-MM-YY o DD-MM-YYYY   (24-07-2026, 24-07-26)
      - D de <mes> de YYYY      (9 de mayo de 2026)
      - D <mes>, YYYY           (16 septiembre, 1999)  -- usado en fecha de nacimiento
    """
    if valor is None:
        return None
    valor = str(valor).strip()
    if not valor:
        return None

    # Formato "D de <mes> de YYYY"
    m = re.match(r"^(\d{1,2})\s+de\s+([a-záéíóúñ]+)\s+de\s+(\d{4})$", valor, re.IGNORECASE)
    if m:
        dia, mes_txt, anio = m.groups()
        mes = MESES_ES.get(mes_txt.lower())
        if mes:
            try:
                return dt.date(int(anio), mes, int(dia))
            except ValueError:
                return None

    # Formato "D <mes>, YYYY"
    m = re.match(r"^(\d{1,2})\s+([a-záéíóúñ]+),?\s+(\d{4})$", valor, re.IGNORECASE)
    if m:
        dia, mes_txt, anio = m.groups()
        mes = MESES_ES.get(mes_txt.lower())
        if mes:
            try:
                return dt.date(int(anio), mes, int(dia))
            except ValueError:
                return None

    # Formato DD/MM/YYYY o DD-MM-YYYY o DD/MM/YY o DD-MM-YY
    m = re.match(r"^(\d{1,2})[/\-](\d{1,2})[/\-](\d{2,4})$", valor)
    if m:
        dia, mes, anio = m.groups()
        anio = int(anio)
        if anio < 100:
            anio += 2000
        try:
            return dt.date(anio, int(mes), int(dia))
        except ValueError:
            return None

    return None


def en_ventana(fecha, inicio, fin):
    """True si `fecha` (date) cae en el rango [inicio, fin] inclusive."""
    if fecha is None:
        return False
    return inicio <= fecha <= fin


def calcular_antiguedad(fecha_ingreso, fecha_baja):
    """Devuelve un string legible de antigüedad entre dos fechas."""
    if fecha_ingreso is None or fecha_baja is None:
        return "N/D"
    dias = (fecha_baja - fecha_ingreso).days
    if dias < 0:
        return "N/D"
    if dias < 30:
        return f"{dias} día{'s' if dias != 1 else ''}"
    meses = dias // 30
    dias_restantes = dias % 30
    if meses < 12:
        texto = f"{meses} mes{'es' if meses != 1 else ''}"
        if dias_restantes >= 7:
            texto += f", {dias_restantes} días"
        return texto
    anios = meses // 12
    meses_restantes = meses % 12
    texto = f"{anios} año{'s' if anios != 1 else ''}"
    if meses_restantes:
        texto += f", {meses_restantes} mes{'es' if meses_restantes != 1 else ''}"
    return texto


def get_sheet_values(sheets_service, spreadsheet_id, tab_name):
    """
    Lee todos los valores de una pestaña como lista de listas (incluye header).
    Usa la API de Sheets (v4) ya autenticada vía OAuth2.
    """
    result = sheets_service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=f"'{tab_name}'",
    ).execute()
    return result.get("values", [])


def get_field(fila, *palabras_clave):
    """
    Busca en las llaves de `fila` (un dict de rows_as_dicts) la primera que
    contenga TODAS las palabras clave dadas. Esto hace la lectura tolerante
    a errores de dedo en los encabezados de las bases (ej. "INCIO" en vez de
    "INICIO"), con tal de que las palabras clave que sí están bien escritas
    coincidan.
    """
    for llave, valor in fila.items():
        if all(p.upper() in llave for p in palabras_clave):
            return valor.strip()
    return ""


def rows_as_dicts(values):
    """
    Convierte una lista de listas (header + filas) en una lista de dicts,
    usando el header normalizado (mayúsculas, sin espacios extra) como llave.
    Rellena celdas faltantes con "".
    """
    if not values:
        return []
    header = [str(h).strip().upper() for h in values[0]]
    filas = []
    for row in values[1:]:
        row = list(row) + [""] * (len(header) - len(row))
        filas.append({header[i]: row[i] for i in range(len(header))})
    return filas
