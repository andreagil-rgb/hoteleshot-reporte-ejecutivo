# -*- coding: utf-8 -*-
"""
Reporte Ejecutivo Semanal - Reclutamiento y Bajas
Hoteles HOT

Se ejecuta los domingos vía GitHub Actions y envía un correo ejecutivo
a Dirección (Manolo) con:
  - Entrevistas de la semana (hotel, puesto, fuente, status, contratado)
  - Bajas de la semana (hotel, puesto, fecha ingreso/baja, antigüedad)

Autenticación: OAuth2 vía el secreto GOOGLE_TOKEN_JSON (mismo patrón que
hoteleshot-headcount y hoteleshot-reclutamiento), proyecto de Google Cloud
`hoteleshot-rrhh`.
"""
import base64
import datetime as dt
import json
import os
import zoneinfo
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

import charts
import config
from sheets_utils import (
    calcular_antiguedad,
    en_ventana,
    get_field,
    get_sheet_values,
    parse_fecha,
    rows_as_dicts,
)

TZ_CDMX = zoneinfo.ZoneInfo("America/Mexico_City")


def hoy_cdmx():
    """
    Fecha de HOY en hora de Ciudad de México, no la fecha UTC del servidor.
    Esto importa porque el workflow corre cerca de medianoche del domingo
    (23:00 CDMX), que en UTC ya es lunes de madrugada -- sin este ajuste,
    el reporte calcularía mal la semana ISO y las ventanas de fecha.
    """
    return dt.datetime.now(TZ_CDMX).date()


def domingo_de_referencia(hoy=None):
    """
    Devuelve el domingo más reciente (hoy mismo si hoy ya es domingo).

    GitHub avisa explícitamente que los workflows con `cron` pueden
    retrasarse (a veces varios minutos). Si el reporte estaba programado
    para las 23:00 del domingo y se retrasa cruzando a la madrugada del
    lunes, `hoy_cdmx()` ya reportaría "lunes" -- y con eso el número de
    semana ISO cambiaría a la semana que apenas empieza (sin datos todavía),
    en vez de la semana que se acaba de cerrar. Por eso siempre anclamos al
    domingo más reciente, sin importar a qué hora exacta corrió el script.
    """
    hoy = hoy or hoy_cdmx()
    dias_desde_domingo = (hoy.weekday() + 1) % 7  # domingo=6 -> 0, lunes=0 -> 1, ...
    return hoy - dt.timedelta(days=dias_desde_domingo)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]


def get_credentials():
    token_json = os.environ["GOOGLE_TOKEN_JSON"]
    info = json.loads(token_json)
    return Credentials.from_authorized_user_info(info, SCOPES)


def get_ventana_semana(hoy=None):
    """Últimos 7 días naturales (lunes a domingo), terminando en el domingo
    de referencia (no en la fecha/hora exacta en que corrió el script)."""
    fin = domingo_de_referencia(hoy)
    inicio = fin - dt.timedelta(days=config.DIAS_VENTANA_REPORTE - 1)
    return inicio, fin


def get_ventana_semana_anterior(hoy=None):
    """
    Ventana de la semana ANTERIOR (7 días antes de la semana actual).
    Se usa para bajas: los hoteles reportan sus bajas a más tardar el
    domingo, así que la semana que acaba de cerrar todavía puede estar
    incompleta el día que corre este reporte. Se reporta la semana previa,
    que para entonces ya debería estar cerrada por completo.
    """
    inicio_actual, fin_actual = get_ventana_semana(hoy)
    fin_anterior = inicio_actual - dt.timedelta(days=1)
    inicio_anterior = fin_anterior - dt.timedelta(days=config.DIAS_VENTANA_REPORTE - 1)
    return inicio_anterior, fin_anterior


# ---------------------------------------------------------------------------
# Reclutamiento
# ---------------------------------------------------------------------------

def obtener_semana_iso_actual(hoy=None):
    """Número de semana ISO del año (coincide con la columna SEMANA de la base)."""
    return domingo_de_referencia(hoy).isocalendar()[1]


def obtener_entrevistas_semana(sheets_service, semana_actual):
    """
    Personas que acudieron a entrevista / están en proceso esta semana.
    Se filtra por la columna A (SEMANA), tal como se alimenta la base
    -- NO por fecha, para evitar problemas de formato de fecha inconsistente.
    """
    values = get_sheet_values(
        sheets_service, config.RECLUTAMIENTO_SHEET_ID, config.RECLUTAMIENTO_TAB
    )
    filas = rows_as_dicts(values)

    entrevistas = []
    for f in filas:
        hotel = f.get("HOTEL", "").strip()
        if not hotel:
            continue
        semana = f.get("SEMANA", "").strip()
        if not semana.isdigit() or int(semana) != semana_actual:
            continue
        status = f.get("STATUS", "").strip().upper()
        entrevistas.append({
            "hotel": hotel,
            "puesto": f.get("PUESTO", "").strip() or "N/D",
            "fuente": get_field(f, "FUENTE") or "N/D",
            "status": status.title() if status else "N/D",
        })

    return entrevistas


def obtener_contrataciones_semana(sheets_service, semana_actual):
    """
    Personas que ingresaron (fueron contratadas) esta semana.
    Se filtra por la columna K (SEMANA DE INGRESO) -- es un conjunto
    independiente de `obtener_entrevistas_semana`, porque alguien puede
    haber iniciado el proceso una semana e ingresar en otra.
    """
    values = get_sheet_values(
        sheets_service, config.RECLUTAMIENTO_SHEET_ID, config.RECLUTAMIENTO_TAB
    )
    filas = rows_as_dicts(values)

    contrataciones = []
    for f in filas:
        hotel = f.get("HOTEL", "").strip()
        if not hotel:
            continue
        semana_ingreso = f.get("SEMANA DE INGRESO", "").strip()
        if not semana_ingreso.isdigit() or int(semana_ingreso) != semana_actual:
            continue
        contrataciones.append({
            "hotel": hotel,
            "puesto": f.get("PUESTO", "").strip() or "N/D",
        })

    return contrataciones


# ---------------------------------------------------------------------------
# Bajas (TRACKER)
# ---------------------------------------------------------------------------

def obtener_bajas_semana(sheets_service, inicio, fin):
    values = get_sheet_values(
        sheets_service, config.TRACKER_SHEET_ID, config.TRACKER_TAB
    )
    filas = rows_as_dicts(values)

    bajas = []
    for f in filas:
        hotel = f.get("HOTEL", "").strip()
        if not hotel:
            continue
        fecha_baja = parse_fecha(f.get("FECHA DE BAJA", ""))
        if not en_ventana(fecha_baja, inicio, fin):
            continue
        fecha_ingreso = parse_fecha(f.get("FECHA DE INGRESO", ""))
        bajas.append({
            "hotel": hotel,
            "puesto": f.get("PUESTO", "").strip() or "N/D",
            "fecha_ingreso": fecha_ingreso.strftime("%d/%m/%Y") if fecha_ingreso else "N/D",
            "fecha_baja": fecha_baja.strftime("%d/%m/%Y"),
            "antiguedad": calcular_antiguedad(fecha_ingreso, fecha_baja),
        })

    return bajas


# ---------------------------------------------------------------------------
# Construcción del HTML del reporte
# ---------------------------------------------------------------------------

def generar_graficas(entrevistas, contrataciones, bajas):
    """
    Genera las 4 gráficas del reporte y devuelve un dict {cid: bytes_png}.
    """
    return {
        "grafica_entrevistas": charts.grafica_entrevistas_por_hotel(entrevistas),
        "grafica_contrataciones": charts.grafica_contrataciones_por_hotel(contrataciones),
        "grafica_embudo": charts.grafica_embudo_contratacion(entrevistas, len(contrataciones)),
        "grafica_bajas": charts.grafica_bajas_por_hotel(bajas),
        "grafica_fuente": charts.grafica_fuente_reclutamiento(entrevistas),
    }


def construir_html(entrevistas, contrataciones, bajas, inicio, fin, semana_actual, inicio_bajas, fin_bajas):
    total_entrevistas = len(entrevistas)
    total_contratados = len(contrataciones)
    tasa = f"{(total_contratados / total_entrevistas * 100):.0f}%" if total_entrevistas else "N/D"
    total_bajas = len(bajas)
    inicio_bajas_txt = inicio_bajas.strftime("%d/%m/%Y")
    fin_bajas_txt = fin_bajas.strftime("%d/%m/%Y")

    filas_bajas = "".join(
        f"""<tr>
            <td style="padding:8px;border:1px solid #e5e7eb;">{b['hotel']}</td>
            <td style="padding:8px;border:1px solid #e5e7eb;">{b['puesto']}</td>
            <td style="padding:8px;border:1px solid #e5e7eb;">{b['fecha_ingreso']}</td>
            <td style="padding:8px;border:1px solid #e5e7eb;">{b['fecha_baja']}</td>
            <td style="padding:8px;border:1px solid #e5e7eb;">{b['antiguedad']}</td>
        </tr>"""
        for b in bajas
    ) or '<tr><td colspan="5" style="padding:8px;text-align:center;color:#9CA3AF;">Sin bajas reportadas para esta semana</td></tr>'

    def tarjeta(valor, etiqueta, color="#2C3E50"):
        return f"""
        <td style="padding:14px 18px;text-align:center;border:1px solid #eee;">
          <div style="font-size:26px;font-weight:bold;color:{color};">{valor}</div>
          <div style="font-size:11px;color:#7F8C8D;text-transform:uppercase;letter-spacing:0.5px;">{etiqueta}</div>
        </td>"""

    html = f"""
    <html>
    <body style="font-family:Arial,sans-serif;color:#222;max-width:760px;margin:0 auto;">
      <h2 style="color:#2C3E50;border-bottom:2px solid #F1C40F;padding-bottom:6px;">
        Reporte Ejecutivo Semanal - Reclutamiento y Bajas
      </h2>
      <p><b>Periodo:</b> {inicio.strftime('%d/%m/%Y')} al {fin.strftime('%d/%m/%Y')} (Semana {semana_actual})</p>

      <table style="border-collapse:collapse;width:100%;margin-bottom:24px;">
        <tr>
          {tarjeta(total_entrevistas, "Entrevistas", "#F1C40F")}
          {tarjeta(total_contratados, "Contrataciones", "#2ECC71")}
          {tarjeta(tasa, "Tasa de conversión", "#2C3E50")}
          {tarjeta(total_bajas, "Bajas", "#E74C3C")}
        </tr>
      </table>

      <div style="text-align:center;margin-bottom:20px;">
        <img src="cid:grafica_entrevistas" style="max-width:100%;height:auto;" alt="Entrevistas por hotel">
      </div>

      <div style="text-align:center;margin-bottom:20px;">
        <img src="cid:grafica_contrataciones" style="max-width:100%;height:auto;" alt="Contrataciones por hotel">
      </div>

      <div style="text-align:center;margin-bottom:20px;">
        <img src="cid:grafica_embudo" style="max-width:100%;height:auto;" alt="Embudo de contratación">
      </div>

      <div style="text-align:center;margin-bottom:8px;">
        <img src="cid:grafica_fuente" style="max-width:100%;height:auto;" alt="Fuente de reclutamiento">
      </div>

      <div style="text-align:center;margin:24px 0 8px;">
        <img src="cid:grafica_bajas" style="max-width:100%;height:auto;" alt="Bajas por hotel">
      </div>

      <h3 style="color:#2C3E50;margin-top:8px;">Detalle de bajas</h3>
      <table style="border-collapse:collapse;width:100%;font-size:13px;">
        <tr style="background-color:#E74C3C;color:white;">
          <th style="padding:8px;border:1px solid #e5e7eb;">Hotel</th>
          <th style="padding:8px;border:1px solid #e5e7eb;">Puesto</th>
          <th style="padding:8px;border:1px solid #e5e7eb;">Fecha ingreso</th>
          <th style="padding:8px;border:1px solid #e5e7eb;">Fecha baja</th>
          <th style="padding:8px;border:1px solid #e5e7eb;">Antigüedad</th>
        </tr>
        {filas_bajas}
      </table>

      <p style="margin-top:24px;color:#9CA3AF;font-size:12px;">
        Reporte generado automáticamente. Fuente: BASE RECLUTAMIENTO (BASE DE DATOS) y BASE HOTELES HOT (TRACKER).
      </p>
    </body>
    </html>
    """
    return html


# ---------------------------------------------------------------------------
# Envío de correo
# ---------------------------------------------------------------------------

def enviar_correo(gmail_service, html_body, graficas, inicio, fin):
    """
    Arma un correo multipart/related: el cuerpo HTML referencia cada gráfica
    con <img src="cid:NOMBRE">, y aquí se adjunta cada imagen con ese mismo
    Content-ID para que el cliente de correo la muestre embebida (no como
    archivo adjunto aparte).
    """
    asunto = f"Reporte Ejecutivo Semanal - Reclutamiento y Bajas ({inicio.strftime('%d/%m')} - {fin.strftime('%d/%m')})"

    message = MIMEMultipart("related")
    message["to"] = ", ".join(config.DESTINATARIOS_TO)
    if config.DESTINATARIOS_CC:
        message["cc"] = ", ".join(config.DESTINATARIOS_CC)
    message["subject"] = asunto

    message.attach(MIMEText(html_body, "html"))

    for cid, png_bytes in graficas.items():
        img = MIMEImage(png_bytes, "png")
        img.add_header("Content-ID", f"<{cid}>")
        img.add_header("Content-Disposition", "inline", filename=f"{cid}.png")
        message.attach(img)

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    gmail_service.users().messages().send(userId="me", body={"raw": raw}).execute()


def main():
    creds = get_credentials()
    sheets_service = build("sheets", "v4", credentials=creds)
    gmail_service = build("gmail", "v1", credentials=creds)

    inicio, fin = get_ventana_semana()
    semana_actual = obtener_semana_iso_actual(fin)

    entrevistas = obtener_entrevistas_semana(sheets_service, semana_actual)
    contrataciones = obtener_contrataciones_semana(sheets_service, semana_actual)
    bajas = obtener_bajas_semana(sheets_service, inicio, fin)

    graficas = generar_graficas(entrevistas, contrataciones, bajas)
    html = construir_html(entrevistas, contrataciones, bajas, inicio, fin, semana_actual, inicio, fin)
    enviar_correo(gmail_service, html, graficas, inicio, fin)

    print(f"Reporte enviado. Semana {semana_actual} | Entrevistas: {len(entrevistas)} | "
          f"Contrataciones: {len(contrataciones)} | Bajas (misma semana): {len(bajas)}")


if __name__ == "__main__":
    main()
