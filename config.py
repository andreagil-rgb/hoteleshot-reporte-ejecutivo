# -*- coding: utf-8 -*-
"""
Configuración del Reporte Ejecutivo Semanal (Reclutamiento + Bajas)
Hoteles HOT
"""

# ---------------------------------------------------------------------------
# Fuentes de datos (Google Sheets)
# ---------------------------------------------------------------------------

# BASE RECLUTAMIENTO -> pestaña "BASE DE DATOS"
RECLUTAMIENTO_SHEET_ID = "1HSFoDgmkXhPBihMhI7qq_hnxNjwyeoa78ObZHRM2g_g"
RECLUTAMIENTO_TAB = "BASE DE DATOS"

# BASE HOTELES HOT -> pestaña "TRACKER"
TRACKER_SHEET_ID = "1eKrw_gD8SX9xEk3_7LB2ubnye8dkN7ERWx8KT4pI2_k"
TRACKER_TAB = "TRACKER"

# ---------------------------------------------------------------------------
# Destinatario del reporte ejecutivo
# ---------------------------------------------------------------------------
DESTINATARIOS_TO = ["manuel.salceda@hoteleshot.com"]   # <-- confirmar correo real de Manolo
DESTINATARIOS_CC = []

REMITENTE_NOMBRE = "Andrea Gil - Recursos Humanos"

# ---------------------------------------------------------------------------
# Ventana de tiempo del reporte
# ---------------------------------------------------------------------------
# El reporte corre los domingos y cubre los últimos 7 días naturales
# (lunes a domingo), terminando el día que corre el script.
DIAS_VENTANA_REPORTE = 7

# ---------------------------------------------------------------------------
# Valores de STATUS considerados "contratación" en BASE DE DATOS
# ---------------------------------------------------------------------------
STATUS_CONTRATADO = {"INGRESA"}

# Valores de STATUS en TRACKER que indican que la persona sigue activa
# (todo lo que no sea esto y tenga FECHA DE BAJA en la ventana, cuenta como baja)
STATUS_ACTIVO_TRACKER = {"ACTIVO"}
