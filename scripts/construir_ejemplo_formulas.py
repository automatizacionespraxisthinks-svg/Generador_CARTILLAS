# -*- coding: utf-8 -*-
"""Arma el EJEMPLO 4: matemáticas con fórmulas escritas como manda la norma (fracciones apiladas).

Es el ejemplo que se descarga desde la pantalla «Formatos». Enseña, sobre un bloque de lectura real,
cómo se escriben las fracciones, las raíces, las potencias y los números mixtos con el editor de
ecuaciones de Word, dentro del enunciado, dentro de las opciones, dentro de una tabla y en el glosario.

Se ejecuta a mano cuando haya que rehacerlo:  python -m scripts.construir_ejemplo_formulas
"""
import sys
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.shared import Cm, Pt
from lxml import etree

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from app.config import PLANTILLAS                                     # noqa: E402
from app.validador.docx_lector import NS                              # noqa: E402
from app.validador.validador import ENC_EXCEL, ENC_GLOSARIO, ENC_RESPUESTAS   # noqa: E402

SALIDA = PLANTILLAS / "ejemplos" / "EJEMPLO_4_MATEMATICAS_CON_FORMULAS.docx"
M = "http://schemas.openxmlformats.org/officeDocument/2006/math"
# dentro de las tablas todo va en 8 pt, como en los ejemplos oficiales
FUENTE, TAM, TAM_CREDITO, TAM_TABLA = "Tahoma", Pt(9), Pt(8), Pt(8)


# ====================================================================== fórmulas (OMML)
def r(t):
    return f"<m:r><m:t>{t}</m:t></m:r>"


def frac(num, den):
    return f"<m:f><m:num>{num}</m:num><m:den>{den}</m:den></m:f>"


def raiz(dentro, indice=None):
    if indice is None:
        return f'<m:rad><m:radPr><m:degHide m:val="1"/></m:radPr><m:deg/><m:e>{dentro}</m:e></m:rad>'
    return f"<m:rad><m:deg>{indice}</m:deg><m:e>{dentro}</m:e></m:rad>"


def pot(base, exp):
    return f"<m:sSup><m:e>{base}</m:e><m:sup>{exp}</m:sup></m:sSup>"


def ecuacion(cuerpo):
    return etree.fromstring(f'<m:oMath xmlns:m="{M}" xmlns:w="{NS["w"]}">{cuerpo}</m:oMath>')


# ====================================================================== piezas del documento
def parrafo(doc, texto="", alin=None, tam=TAM, cursiva=False, negrita=False):
    p = doc.add_paragraph()
    if alin is not None:
        p.alignment = alin
    if texto:
        escribir(p, texto, tam=tam, cursiva=cursiva, negrita=negrita)
    return p


def escribir(p, texto, tam=TAM, cursiva=False, negrita=False):
    run = p.add_run(texto)
    run.font.name, run.font.size = FUENTE, tam
    run.font.italic, run.font.bold = cursiva, negrita
    return run


def con_formulas(p, trozos, tam=TAM):
    """trozos: texto suelto (str) o fórmula (('f', omml))."""
    for t in trozos:
        if isinstance(t, tuple) and t[0] == "sup":
            escribir(p, t[1], tam=tam).font.superscript = True      # m², cm³: superíndice, no ecuación
        elif isinstance(t, tuple):
            p._p.append(ecuacion(t[1]))
        else:
            escribir(p, t, tam=tam)
    return p


def opcion(doc, letra, trozos):
    p = doc.add_paragraph()
    escribir(p, f"{letra}. ", negrita=True)
    return con_formulas(p, trozos)


def tabla(doc, filas, anchos=None):
    t = doc.add_table(rows=len(filas), cols=len(filas[0]))
    t.style = "Table Grid"
    t.autofit = False
    for i, fila in enumerate(filas):
        # ninguna fila se parte entre páginas (Propiedades de tabla › Fila)
        trpr = t.rows[i]._tr.get_or_add_trPr()
        trpr.append(etree.SubElement(etree.Element("x"), qn("w:cantSplit")))
        for j, valor in enumerate(fila):
            celda = t.cell(i, j)
            celda.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            celda.paragraphs[0].text = ""
            p = celda.paragraphs[0]
            if isinstance(valor, list):
                con_formulas(p, valor, tam=TAM_TABLA)
            else:
                escribir(p, str(valor), tam=TAM_TABLA, negrita=(i == 0))
            if anchos:
                celda.width = Cm(anchos[j])
    return t


# ====================================================================== el ejemplo
def construir():
    doc = Document()
    estilo = doc.styles["Normal"]
    estilo.font.name, estilo.font.size = FUENTE, TAM
    estilo.paragraph_format.space_after, estilo.paragraph_format.line_spacing = Pt(0), 1.0
    for sec in doc.sections:
        sec.page_width, sec.page_height = Cm(21.59), Cm(27.94)
        sec.top_margin = sec.bottom_margin = sec.left_margin = sec.right_margin = Cm(1.27)

    # ---------------------------------------------------------------- recurso compartido
    parrafo(doc, "Responde las preguntas #N a #M de acuerdo con la siguiente información.")
    con_formulas(parrafo(doc, alin=WD_ALIGN_PARAGRAPH.JUSTIFY), [
        "La huerta del colegio está dividida en parcelas del mismo tamaño y en cada una se sembró un "
        "cultivo distinto. La tabla muestra qué parte de la huerta ocupa cada cultivo."])
    tabla(doc, [["Cultivo", "Parte de la huerta"],
                ["Cilantro", [("f", frac(r("1"), r("8")))]],
                ["Cebolla", [("f", frac(r("1"), r("4")))]],
                ["Tomate", [("f", frac(r("3"), r("8")))]],
                ["Lechuga", [("f", frac(r("1"), r("4")))]]], anchos=[3.2, 4.0])
    parrafo(doc, "Elaboración propia. PRAXIS – THINKS, 2026.", alin=WD_ALIGN_PARAGRAPH.RIGHT,
            tam=TAM_CREDITO, cursiva=True)

    # ---------------------------------------------------------------- pregunta 1: suma de fracciones
    con_formulas(parrafo(doc), [
        "Marcela quiere saber qué parte de la huerta ocupan juntos el cilantro y la cebolla. "
        "¿Qué fracción de la huerta ocupan entre los dos?"])
    opcion(doc, "A", [("f", frac(r("2"), r("12")))])
    opcion(doc, "B", [("f", frac(r("3"), r("8")))])          # la correcta
    opcion(doc, "C", [("f", frac(r("1"), r("32")))])
    opcion(doc, "D", [("f", frac(r("2"), r("6")))])

    # ---------------------------------------------------------------- pregunta 2: raíz cuadrada
    con_formulas(parrafo(doc), [
        "La parcela del tomate es un cuadrado y su área es de 49 m", ("sup", "2"),
        ". Marcela necesita saber cuánto mide cada lado para cercarla. "
        "¿Cuál expresión permite hallar la medida del lado?"])
    opcion(doc, "A", [("f", frac(r("49"), r("2")))])
    opcion(doc, "B", [("f", pot(r("49"), r("2")))])
    opcion(doc, "C", [("f", raiz(r("49")))])                 # la correcta
    opcion(doc, "D", [("f", frac(r("49"), r("4")))])

    # ---------------------------------------------------------------- pregunta 3: números mixtos
    con_formulas(parrafo(doc), [
        "Para regar la huerta, Marcela usó ", ("f", r("2") + frac(r("1"), r("4"))),
        " litros de agua en la mañana y ", ("f", r("1") + frac(r("1"), r("2"))),
        " litros en la tarde. ¿Cuántos litros de agua usó en total ese día?"])
    opcion(doc, "A", [("f", r("3") + frac(r("2"), r("6")))])
    opcion(doc, "B", [("f", r("2") + frac(r("3"), r("4")))])
    opcion(doc, "C", [("f", r("4") + frac(r("1"), r("4")))])
    opcion(doc, "D", [("f", r("3") + frac(r("3"), r("4")))])  # la correcta

    # ---------------------------------------------------------------- tablas de control
    parrafo(doc)
    parrafo(doc, "TABLA DE RESPUESTAS", negrita=True)
    ANCHO_RESP, ANCHO_EXCEL, ANCHO_GLOS = ([1.2, 1.4, 16.4],
                                           [1.2, 1.6, 1.3, 2.2, 2.2, 2.2, 2.6, 1.3, 2.4, 1.6],
                                           [1.8, 4.0, 13.25])
    tabla(doc, [list(ENC_RESPUESTAS),
                ["", "B", "Porque al sumar las dos partes con denominador común se obtiene tres octavos "
                           "de la huerta."],
                ["", "C", "Porque el lado de un cuadrado es la raíz cuadrada de su área."],
                ["", "D", "Porque al sumar los enteros y las fracciones con denominador común resultan "
                           "tres litros y tres cuartos."]], anchos=ANCHO_RESP)
    parrafo(doc)
    parrafo(doc, "TABLA DE EXCEL", negrita=True)
    tabla(doc, [list(ENC_EXCEL),
                ["", "B", "6°", "Matemáticas", "Matemáticas I", "Numérico-variacional",
                 "Planteamiento y resolución de problemas", "DBA 1",
                 "Adición de fracciones con distinto denominador", "Medio"],
                ["", "C", "6°", "Matemáticas", "Matemáticas I", "Numérico-variacional",
                 "Razonamiento y argumentación", "DBA 1",
                 "Raíz cuadrada como operación inversa de elevar al cuadrado", "Medio"],
                ["", "D", "6°", "Matemáticas", "Matemáticas I", "Numérico-variacional",
                 "Planteamiento y resolución de problemas", "DBA 1",
                 "Adición de números mixtos con denominadores distintos", "Avanzado"]], anchos=ANCHO_EXCEL)
    parrafo(doc)
    parrafo(doc, "TABLA DE GLOSARIO", negrita=True)
    tabla(doc, [list(ENC_GLOSARIO),
                ["1", "fracción", [
                    "Parte de un todo dividido en partes iguales; por ejemplo ",
                    ("f", frac(r("3"), r("8"))), " de la huerta"]],
                ["2", "área", "Medida de la superficie que ocupa una figura, en metros cuadrados"],
                ["3", "litros", "Unidad para medir cuánto líquido cabe en un recipiente"]], anchos=ANCHO_GLOS)

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(SALIDA))
    return SALIDA


if __name__ == "__main__":
    ruta = construir()
    print("escrito:", ruta.name, ruta.stat().st_size, "bytes")

    from app.semilla import catalogo_validacion
    from app.validador import validar

    r_ = validar(ruta.read_bytes(), ruta.name, catalogo_validacion()).a_dict()
    print("validación:", r_["estado"])
    for e in r_["errores"]:
        print("   regla", e["regla"], "·", e["donde"], "·", e["mensaje"][:110])
    for a in r_.get("avisos", []):
        print("   aviso ·", a["mensaje"][:110])
