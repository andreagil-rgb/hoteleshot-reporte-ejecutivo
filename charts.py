# -*- coding: utf-8 -*-
"""
Genera las gráficas del reporte ejecutivo como imágenes PNG (bytes) para
insertarlas embebidas dentro del correo (inline, vía Content-ID).
"""
import io
from collections import Counter, OrderedDict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

VERDE = "#2ECC71"        # positivo: contrataciones / cubierto
AMARILLO = "#F1C40F"     # en proceso / precaución: entrevistas, continúan proceso
ROJO = "#E74C3C"         # atención: bajas
AZUL_OSCURO = "#2C3E50"  # texto de títulos
GRIS = "#7F8C8D"         # texto secundario / etiquetas

plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["axes.edgecolor"] = "#e0e0e0"
plt.rcParams["axes.linewidth"] = 0.8


def _fig_to_bytes(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", transparent=False, facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def grafica_entrevistas_por_hotel(entrevistas):
    """Barras horizontales: número de entrevistas por hotel."""
    conteo = Counter(e["hotel"] for e in entrevistas)
    conteo = OrderedDict(sorted(conteo.items(), key=lambda x: x[1]))

    fig, ax = plt.subplots(figsize=(7, max(2.5, 0.35 * len(conteo))))
    if conteo:
        ax.barh(list(conteo.keys()), list(conteo.values()), color=AMARILLO)
        for i, v in enumerate(conteo.values()):
            ax.text(v + 0.1, i, str(v), va="center", fontsize=9, color="#333")
    ax.set_title("Entrevistas de la semana por hotel", fontsize=12, fontweight="bold", color=AZUL_OSCURO, pad=10)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_xlabel("Número de entrevistas", fontsize=9, color=GRIS)
    ax.tick_params(labelsize=9)
    fig.tight_layout()
    return _fig_to_bytes(fig)


def grafica_contrataciones_por_hotel(contrataciones):
    """Barras horizontales: número de personal contratado (ingresos) por hotel."""
    conteo = Counter(c["hotel"] for c in contrataciones)
    conteo = OrderedDict(sorted(conteo.items(), key=lambda x: x[1]))

    fig, ax = plt.subplots(figsize=(7, max(2.5, 0.35 * max(len(conteo), 1))))
    if conteo:
        ax.barh(list(conteo.keys()), list(conteo.values()), color=VERDE)
        for i, v in enumerate(conteo.values()):
            ax.text(v + 0.1, i, str(v), va="center", fontsize=9, color="#333")
    else:
        ax.text(0.5, 0.5, "Sin contrataciones esta semana", ha="center", va="center",
                transform=ax.transAxes, color=GRIS, fontsize=10)
        ax.set_xticks([])
        ax.set_yticks([])
    ax.set_title("Personal contratado de la semana por hotel", fontsize=12, fontweight="bold", color=AZUL_OSCURO, pad=10)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_xlabel("Número de contrataciones", fontsize=9, color=GRIS)
    ax.tick_params(labelsize=9)
    fig.tight_layout()
    return _fig_to_bytes(fig)


def grafica_embudo_contratacion(entrevistas, total_contratados):
    """Embudo: candidatos totales -> continúan proceso -> contratados.
    `total_contratados` viene de un conteo independiente (columna SEMANA DE
    INGRESO), ya que no siempre corresponde a las mismas personas que
    aparecen en `entrevistas` (columna SEMANA) de esta semana.
    """
    total = len(entrevistas)
    continuan = sum(1 for e in entrevistas if e["status"].upper() in
                     {"CONTINUA", "2DA ENTREVISTA", "INGRESA"})

    etapas = ["Candidatos entrevistados", "Continúan proceso", "Contratados"]
    valores = [total, continuan, total_contratados]
    colores = [AMARILLO, "#E67E22", VERDE]

    fig, ax = plt.subplots(figsize=(7, 3.2))
    barras = ax.barh(etapas, valores, color=colores, height=0.55)
    for barra, v in zip(barras, valores):
        ax.text(v + max(valores, default=1) * 0.02, barra.get_y() + barra.get_height() / 2,
                str(v), va="center", fontsize=10, fontweight="bold", color="#333")
    ax.invert_yaxis()
    ax.set_title("Embudo de contratación de la semana", fontsize=12, fontweight="bold", color=AZUL_OSCURO, pad=10)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(labelsize=9)
    ax.set_xlim(0, max(valores, default=1) * 1.2 or 1)
    fig.tight_layout()
    return _fig_to_bytes(fig)


def grafica_bajas_por_hotel(bajas):
    """Barras horizontales: número de bajas por hotel."""
    conteo = Counter(b["hotel"] for b in bajas)
    conteo = OrderedDict(sorted(conteo.items(), key=lambda x: x[1]))

    fig, ax = plt.subplots(figsize=(7, max(2.5, 0.35 * max(len(conteo), 1))))
    if conteo:
        ax.barh(list(conteo.keys()), list(conteo.values()), color=ROJO)
        for i, v in enumerate(conteo.values()):
            ax.text(v + 0.1, i, str(v), va="center", fontsize=9, color="#333")
    else:
        ax.text(0.5, 0.5, "Sin bajas esta semana", ha="center", va="center",
                transform=ax.transAxes, color=GRIS, fontsize=10)
        ax.set_xticks([])
        ax.set_yticks([])
    ax.set_title("Bajas de la semana por hotel", fontsize=12, fontweight="bold", color=AZUL_OSCURO, pad=10)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_xlabel("Número de bajas", fontsize=9, color=GRIS)
    ax.tick_params(labelsize=9)
    fig.tight_layout()
    return _fig_to_bytes(fig)


def grafica_fuente_reclutamiento(entrevistas):
    """Dona: distribución de candidatos por fuente de reclutamiento."""
    conteo = Counter(e["fuente"] for e in entrevistas)
    conteo = OrderedDict(sorted(conteo.items(), key=lambda x: -x[1]))

    # Colores fijos por fuente conocida; el resto usa la paleta semáforo.
    COLOR_POR_FUENTE = {
        "FACEBOOK": "#1877F2",        # azul Facebook
        "DIRECTO HOTEL": "#F5A9A9",   # rojo clarito
    }
    paleta_generica = [VERDE, AMARILLO, AZUL_OSCURO, GRIS, "#E67E22"]

    fig, ax = plt.subplots(figsize=(5.5, 4))
    if conteo:
        colores = []
        idx_generico = 0
        for fuente in conteo:
            color_fijo = COLOR_POR_FUENTE.get(fuente.upper())
            if color_fijo:
                colores.append(color_fijo)
            else:
                colores.append(paleta_generica[idx_generico % len(paleta_generica)])
                idx_generico += 1
        wedges, _, autotexts = ax.pie(
            conteo.values(),
            labels=None,
            autopct=lambda pct: f"{pct:.0f}%" if pct >= 5 else "",
            startangle=90,
            colors=colores,
            wedgeprops={"width": 0.42, "edgecolor": "white"},
            pctdistance=0.79,
        )
        for t in autotexts:
            t.set_fontsize(9)
            t.set_color("white")
        ax.legend(
            wedges, [f"{k} ({v})" for k, v in conteo.items()],
            loc="center left", bbox_to_anchor=(1.02, 0.5), fontsize=9, frameon=False,
        )
    else:
        ax.text(0.5, 0.5, "Sin datos", ha="center", va="center", color=GRIS, fontsize=10)
    ax.set_title("Fuente de reclutamiento", fontsize=12, fontweight="bold", color=AZUL_OSCURO, pad=10)
    fig.tight_layout()
    return _fig_to_bytes(fig)
