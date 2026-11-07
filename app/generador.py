"""Generación de la cartilla en Word y del Excel de claves (Fase 4).

El sistema no reinterpreta los ejercicios: copia los fragmentos del Word de carga y
los pega en la plantilla de la cartilla. Solo cambia el número de la pregunta, el
orden de las opciones (según la plantilla de respuestas), los rangos #N y #M, y la
portada. Antes de entregar, compara el Excel contra la cartilla posición por posición.
"""
import copy
import io
import re
from datetime import datetime

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from sqlalchemy import select

from app import catalogos_base as base
from app import analisis, glosario, paginas
from app.armado import _plantilla, _verificar, orden_items, posiciones
from app.bd import Archivo, Bloque, Cartilla, CartillaArchivo, Grado, Materia, Sesion, Submateria
from app.config import PLANTILLAS
from app.semilla import catalogo_validacion
from app.validador import analizar
from app.validador.docx_lector import NS, Parrafo, Tabla
from app.validador.validador import alineacion_impresa, letra_opcion

W = "{%s}" % NS["w"]
R = "{%s}" % NS["r"]
BASE_DOCX = PLANTILLAS / "PLANTILLA_CARTILLA_BASE.docx"       # portada de página entera
MEDIA_DOCX = PLANTILLAS / "PLANTILLA_CARTILLA_MEDIA.docx"     # media portada: el cuerpo arranca debajo
PORTADAS = {"completa": BASE_DOCX, "media": MEDIA_DOCX}
MARCA_CUERPO = "[[CUERPO]]"
NOTA_EXCEL = ("La 'Cartilla' debe coincidir EXACTAMENTE con el cuadernillo del OMR y de la lista. "
              "Incluye aquí las claves de TODAS las cartillas/simulacros. Las columnas grises son opcionales.")
ENC_EXCEL = ["Cartilla", "Pregunta", "Correcta", "Materia", "Submateria", "Pensamiento", "Competencia", "DBA",
             "Temática", "Nivel", "Justificación"]
PERIODOS = {"11": "1° Periodo", "22": "2° Periodo", "33": "3° Periodo", "44": "4° Periodo"}
ABREV_NIVEL = {"Básico": "BB", "Medio": "MM", "Avanzado": "AA"}
ESPACIO_COLUMNAS = 454          # 0,8 cm entre columnas: cada columna mide 9,12 cm
MARGEN_INFERIOR = 880           # twips (1,55 cm): 720 de margen + la holgura del pie (ver _configurar_pagina)
MARGEN_CELDA_VERTICAL = 20     # 1 pt arriba y abajo del texto de cada celda
ESPACIO_FIGURA = 6              # pt de aire arriba y abajo de cada imagen y de cada tabla
# tamaño al que se IMPRIME una ecuación: el mismo del texto que la rodea (ver _ecuacion_al_tamano)
TAM_ECUACION = 9                # cuerpo de la cartilla
TAM_ECUACION_CHICA = 8          # tablas y glosario
ESPACIO_TRAS_TABLA = ESPACIO_FIGURA * 20      # lo mismo, en twips, para el párrafo que rodea a la tabla
FIN_PREGUNTA = 14               # pt después de la última línea de cada pregunta (unos 5 mm hasta la siguiente)
COL_LETRA = 0.45                # cm que ocupa «A.» antes del texto de la opción
COL_NUMERO = 0.75               # cm que ocupa «12.» en las preguntas sin enunciado («completar el texto»)
# orden de los hijos que exige el esquema de Word
ORDEN_PPR = ["pStyle", "keepNext", "keepLines", "pageBreakBefore", "framePr", "widowControl", "numPr",
             "suppressLineNumbers", "pBdr", "shd", "tabs", "suppressAutoHyphens", "kinsoku", "wordWrap",
             "overflowPunct", "topLinePunct", "autoSpaceDE", "autoSpaceDN", "bidi", "adjustRightInd", "snapToGrid",
             "spacing", "ind", "contextualSpacing", "mirrorIndents", "suppressOverlap", "jc", "textDirection",
             "textAlignment", "textboxTightWrap", "outlineLvl", "divId", "cnfStyle", "rPr", "sectPr", "pPrChange"]
ORDEN_TCPR = ["cnfStyle", "tcW", "gridSpan", "hMerge", "vMerge", "tcBorders", "shd", "noWrap", "tcMar",
              "textDirection", "tcFitText", "vAlign", "hideMark", "headers", "cellIns", "cellDel", "cellMerge"]
ORDEN_TRPR = ["cnfStyle", "divId", "gridBefore", "gridAfter", "wBefore", "wAfter", "cantSplit", "trHeight",
              "tblHeader", "tblCellSpacing", "jc", "hidden", "ins", "del", "trPrChange"]
ORDEN_TBLPR = ["tblStyle", "tblpPr", "tblOverlap", "bidiVisual", "tblStyleRowBandSize", "tblStyleColBandSize", "tblW",
               "jc", "tblCellSpacing", "tblInd", "tblBorders", "shd", "tblLayout", "tblCellMar", "tblLook",
               "tblCaption", "tblDescription"]
ORDEN_RPR = ["ins", "del", "moveFrom", "moveTo", "rStyle", "rFonts", "b", "bCs", "i", "iCs", "caps", "smallCaps",
             "strike", "dstrike", "outline", "shadow", "emboss", "imprint", "noProof", "snapToGrid", "vanish", "webHidden",
             "color", "spacing", "w", "kern", "position", "sz", "szCs", "highlight", "u", "effect", "bdr", "shd",
             "fitText", "vertAlign", "rtl", "cs", "em", "lang", "eastAsianLayout", "specVanish", "oMath", "rPrChange"]
ORDEN_SECTPR = ["headerReference", "footerReference", "footnotePr", "endnotePr", "type", "pgSz", "pgMar", "paperSrc",
                "pgBorders", "lnNumType", "pgNumType", "cols", "formProt", "vAlign", "noEndnote", "titlePg",
                "textDirection", "bidi", "rtlGutter", "docGrid", "printerSettings", "sectPrChange"]
WP = "{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}"
PIC = "{http://schemas.openxmlformats.org/drawingml/2006/picture}"
W14 = "{http://schemas.microsoft.com/office/word/2010/wordml}"
LADOS = {"top": "top", "left": "left", "start": "left", "bottom": "bottom", "right": "right", "end": "right",
         "insideH": "insideH", "insideV": "insideV"}


class ErrorGeneracion(Exception):
    pass


# ====================================================================== utilidades de Word
def _el(tag, **attrs):
    e = OxmlElement(tag)
    for k, v in attrs.items():
        e.set(qn(k), str(v))
    return e


def texto_de(p):
    return "".join(t.text or "" for t in p.iter(W + "t"))


def poner_texto(p, nuevo):
    """Reemplaza el texto del párrafo conservando el formato del primer run."""
    runs = [r for r in p.iter(W + "r") if r.find(W + "t") is not None]
    if not runs:
        return False
    primero = runs[0]
    primero.find(W + "t").text = nuevo
    primero.find(W + "t").set(qn("xml:space"), "preserve")
    for r in runs[1:]:
        r.getparent().remove(r)
    return True


def _ppr(p):
    """w:pPr del párrafo (lo crea si no existe). Los fragmentos copiados son XML puro."""
    ppr = p.find(W + "pPr")
    if ppr is None:
        ppr = _el("w:pPr")
        p.insert(0, ppr)
    return ppr


def _ordenar(el, orden):
    """Reordena los hijos según el esquema de Word (lo desconocido queda al final, en su orden)."""
    hijos = list(el)
    pos = lambda h: orden.index(h.tag.split("}")[1]) if h.tag.startswith(W) and h.tag.split("}")[1] in orden else len(orden)
    for h in sorted(hijos, key=pos):
        el.append(h)


def formato_parrafo(p, antes=0, despues=0, alin=None, juntar=False, sangria=None, izquierda=None, colgante=None,
                    tabs=None):
    """Espaciado propio de la cartilla. La sangría del archivo se conserva salvo en las opciones (sangría francesa).

    sangria: sangría izquierda en cm con sangría francesa igual (o «colgante», si se da); izquierda: sangría
    izquierda sin francesa; tabs: tabulaciones en cm (en las opciones reemplazan las del archivo de carga).
    """
    ppr = _ppr(p)
    quitar = ["w:pStyle", "w:spacing", "w:keepNext", "w:numPr", "w:widowControl", "w:contextualSpacing"]
    if alin:
        quitar.append("w:jc")
    if sangria or izquierda:
        quitar.append("w:ind")
    if sangria or tabs:
        quitar.append("w:tabs")
    for tag in quitar:
        for viejo in ppr.findall(qn(tag)):
            ppr.remove(viejo)
    ppr.append(_el("w:spacing", **{"w:before": int(antes * 20), "w:after": int(despues * 20),
                                   "w:line": 240, "w:lineRule": "auto"}))
    if alin:
        ppr.append(_el("w:jc", **{"w:val": alin}))
    if juntar:
        ppr.append(_el("w:keepNext"))
    ppr.append(_el("w:widowControl"))
    if tabs:
        t = _el("w:tabs")
        for pos in tabs:
            t.append(_el("w:tab", **{"w:val": "left", "w:pos": round(pos * 567)}))
        ppr.append(t)
    if sangria:
        ppr.append(_el("w:ind", **{"w:left": round(sangria * 567), "w:hanging": round((colgante or sangria) * 567)}))
    elif izquierda:
        ppr.append(_el("w:ind", **{"w:left": round(izquierda * 567)}))
    _ordenar(ppr, ORDEN_PPR)
    return p


def fijar_parrafo(p, estilos, tbl_sid=None):
    """Deja explícitas la alineación y la sangría efectivas del origen: la cartilla no tiene sus estilos."""
    efectivos = {tag: estilos.ppr_efectivo(p, tag, tbl_sid) for tag in ("jc", "ind")}
    ppr = _ppr(p)
    for tag, valor in efectivos.items():
        for viejo in ppr.findall(W + tag):
            ppr.remove(viejo)
        if valor is not None:
            ppr.append(copy.deepcopy(valor))
    _ordenar(ppr, ORDEN_PPR)
    return p


MAXIMO_CORTO = 12               # caracteres de una celda «corta»: un número, un dato, una palabra


def celda_corta(texto):
    """¿Esta celda es un número o una palabra corta? Entonces se ve mejor centrada que pegada a la izquierda."""
    t = (texto or "").strip()
    return bool(t) and len(t) <= MAXIMO_CORTO and len(t.split()) <= 2


def columnas_centradas(filas):
    """Qué columnas se centran: aquellas en las que **todas** las celdas con contenido son cortas.

    Se decide por columna y no por celda: centrar una celda suelta en una columna de texto largo se ve
    desalineado. Si la tabla tiene celdas combinadas (filas con distinto número de celdas) no se toca nada.
    """
    if not filas or len({len(f) for f in filas}) != 1:
        return set()
    centradas = set()
    for col in range(len(filas[0])):
        valores = [f[col] for f in filas[1:]]            # el encabezado ya va centrado aparte
        llenas = [v for v in valores if (v or "").strip()]
        if llenas and all(celda_corta(v) for v in llenas):
            centradas.add(col)
    return centradas


def formato_celda(p, juntar, centrar=False):
    """Párrafo dentro de una tabla: sin espacio antes ni después e interlineado sencillo, para que la tabla sea
    compacta. Se centran el encabezado y las columnas de números o palabras cortas."""
    ppr = _ppr(p)
    quitar = ["pStyle", "spacing", "keepNext", "contextualSpacing"] + (["jc"] if centrar else [])
    for tag in quitar:
        for viejo in ppr.findall(W + tag):
            ppr.remove(viejo)
    if centrar:
        ppr.append(_el("w:jc", **{"w:val": "center"}))
    ppr.append(_el("w:spacing", **{"w:before": 0, "w:after": 0, "w:line": 240, "w:lineRule": "auto"}))
    if juntar:
        ppr.append(_el("w:keepNext"))
    _ordenar(ppr, ORDEN_PPR)


def _centrar_vertical(tc):
    """Un dato corto al lado de un texto de tres líneas se ve mejor a media altura que arriba del todo."""
    pr = tc.find(W + "tcPr")
    if pr is None:
        pr = _el("w:tcPr")
        tc.insert(0, pr)
    for viejo in pr.findall(W + "vAlign"):
        pr.remove(viejo)
    pr.append(_el("w:vAlign", **{"w:val": "center"}))
    _ordenar(pr, ORDEN_TCPR)


def _fila_partible(tr, encabezado):
    """Una tabla larga puede seguir en la columna siguiente (3.8), pero con dos condiciones:

    - `cantSplit`: el corte cae **entre** dos filas; ninguna fila se parte por la mitad.
    - `tblHeader` en la primera: el encabezado se vuelve a dibujar arriba de la continuación, para que la
      segunda parte no se quede sin los títulos de sus columnas. Solo en tablas de más de dos filas: una
      de dos no se parte.
    """
    pr = tr.find(W + "trPr")
    if pr is None:
        pr = _el("w:trPr")
        tr.insert(0, pr)
    for tag in ("cantSplit", "tblHeader"):
        for viejo in pr.findall(W + tag):
            pr.remove(viejo)
    if encabezado:
        pr.append(_el("w:tblHeader"))
    pr.append(_el("w:cantSplit"))
    _ordenar(pr, ORDEN_TRPR)


def _acumular(capa, destino):
    if capa is not None:
        for h in capa:
            lado = LADOS.get(h.tag.split("}")[1])
            if lado:
                destino[lado] = h


def ajustar_tabla(tbl, estilos, juntar):
    """Tabla del ejercicio: centrada en la columna, compacta y con sus bordes escritos en la propia tabla.

    El estilo de tabla del archivo de carga (por ejemplo «Table Grid» de un Word en inglés) no existe en
    la cartilla, así que los bordes y márgenes de celda que venían de ese estilo se copian directos.
    """
    pr = tbl.find(W + "tblPr")
    if pr is None:
        pr = _el("w:tblPr")
        tbl.insert(0, pr)
    est = pr.find(W + "tblStyle")
    sid = est.get(W + "val") if est is not None else None
    bordes, margenes = {}, {}
    for st in estilos.cadena(sid):
        _acumular(st.find(f"{W}tblPr/{W}tblBorders"), bordes)
        _acumular(st.find(f"{W}tblPr/{W}tblCellMar"), margenes)
    _acumular(pr.find(W + "tblBorders"), bordes)
    _acumular(pr.find(W + "tblCellMar"), margenes)
    for tag in ("tblStyle", "jc", "tblInd", "tblBorders", "tblCellMar"):
        for viejo in pr.findall(W + tag):
            pr.remove(viejo)
    pr.append(_el("w:jc", **{"w:val": "center"}))
    if bordes:
        tb = _el("w:tblBorders")
        for lado in ("top", "left", "bottom", "right", "insideH", "insideV"):
            if lado in bordes:
                b = copy.deepcopy(bordes[lado])
                b.tag = W + lado
                tb.append(b)
        pr.append(tb)
    cm = _el("w:tblCellMar")
    for lado in ("top", "left", "bottom", "right"):
        m = margenes.get(lado)
        if lado in ("top", "bottom"):
            ancho = MARGEN_CELDA_VERTICAL          # compacta: 1 pt arriba y abajo, sin importar el archivo
        else:
            ancho = m.get(W + "w") if m is not None else 108
        cm.append(_el(f"w:{lado}", **{"w:w": ancho, "w:type": "dxa"}))
    pr.append(cm)
    _ordenar(pr, ORDEN_TBLPR)
    filas = tbl.findall(W + "tr")
    celdas = [fila.findall(W + "tc") for fila in filas]
    centradas = columnas_centradas([[texto_de(c) for c in fila] for fila in celdas])
    for i, tr in enumerate(filas):
        _fila_partible(tr, encabezado=i == 0 and len(filas) > 2)
        for j, tc in enumerate(celdas[i]):
            centrar = i == 0 or j in centradas
            if centrar:
                _centrar_vertical(tc)
            for p in tc.iter(W + "p"):
                # solo la última fila se amarra a lo que sigue: así la tabla puede continuar en la otra columna
                formato_celda(p, juntar and i == len(filas) - 1, centrar=centrar)
    return tbl


def fijar_formato_runs(p, estilos, sid, tbl_sid=None):
    """Deja explícito en cada run el formato que tenía en su archivo de origen."""
    for r in list(p.iter(W + "r")):
        if r.find(W + "t") is None and r.find(W + "drawing") is None and r.find(W + "sym") is None:
            continue
        fmt = estilos.formato_run(r, sid, tbl_sid)
        rpr = r.find(W + "rPr")
        if rpr is None:
            rpr = _el("w:rPr")
            r.insert(0, rpr)
        # el estilo de carácter del archivo de carga se quita: su formato ya queda explícito, y un estilo con
        # el mismo nombre en la cartilla (Hipervínculo, Cita, Énfasis intenso…) podría traer color
        for tag in ("w:rStyle", "w:rFonts", "w:sz", "w:szCs", "w:b", "w:i", "w:vertAlign", "w:color", "w:u"):
            for viejo in rpr.findall(qn(tag)):
                rpr.remove(viejo)
        rpr.insert(0, _el("w:rFonts", **{"w:ascii": fmt.fuente or "Tahoma", "w:hAnsi": fmt.fuente or "Tahoma",
                                         "w:cs": fmt.fuente or "Tahoma"}))
        rpr.append(_el("w:sz", **{"w:val": fmt.tam or 18}))
        rpr.append(_el("w:szCs", **{"w:val": fmt.tam or 18}))
        if fmt.negrita:
            rpr.append(_el("w:b"))
        if fmt.cursiva:
            rpr.append(_el("w:i"))
        if fmt.vert:
            rpr.append(_el("w:vertAlign", **{"w:val": fmt.vert}))
        if fmt.subrayado and fmt.subrayado != "none":
            rpr.append(_el("w:u", **{"w:val": fmt.subrayado}))
        _ordenar(rpr, ORDEN_RPR)
    return p


def run_texto(texto, size=9, bold=False, italic=False, vert=None):
    r = _el("w:r")
    rpr = _el("w:rPr")
    rpr.append(_el("w:rFonts", **{"w:ascii": "Tahoma", "w:hAnsi": "Tahoma", "w:cs": "Tahoma"}))
    rpr.append(_el("w:sz", **{"w:val": int(size * 2)}))
    rpr.append(_el("w:szCs", **{"w:val": int(size * 2)}))
    if bold:
        rpr.append(_el("w:b"))
    if italic:
        rpr.append(_el("w:i"))
    if vert in ("sup", "sub"):
        rpr.append(_el("w:vertAlign", **{"w:val": "superscript" if vert == "sup" else "subscript"}))
    _ordenar(rpr, ORDEN_RPR)
    r.append(rpr)
    t = _el("w:t")
    t.set(qn("xml:space"), "preserve")
    t.text = texto
    r.append(t)
    return r


M = "{http://schemas.openxmlformats.org/officeDocument/2006/math}"


ESCALA_FRACCION = 0.73      # Cambria Math imprime al 73 % lo que va arriba y abajo de la barra


def _en_fraccion(r):
    """¿Este trozo va dentro del numerador o del denominador de alguna fracción?"""
    x = r.getparent()
    while x is not None:
        if x.tag in (M + "num", M + "den"):
            return True
        x = x.getparent()
    return False


def _ecuacion_sola(ecuacion):
    """¿La fórmula va sola en su párrafo? Entonces Word la imprime a tamaño completo.

    Word tiene dos modos: dentro de una frase encoge el numerador y el denominador al 73 %, y sola en su
    párrafo —una celda de tabla, por ejemplo— los deja al tamaño declarado. Medido sobre el PDF:

        declarada 11 pt  →  dentro de una frase 8 pt  ·  sola 11 pt
        declarada 12,5 pt → dentro de una frase 9 pt  ·  sola 12,5 pt

    Una ecuación que todavía no está en ningún párrafo (el glosario la mete después) cuenta como dentro
    de una frase, que es donde acaba.
    """
    p = ecuacion.getparent()
    while p is not None and p.tag != W + "p":
        p = p.getparent()
    if p is None:
        return False
    return not any("".join(t.text or "" for t in r.iter(W + "t")).strip() for r in p.findall(W + "r"))


def _ecuacion_al_tamano(ecuacion, size):
    """Imprime la ecuación al tamaño pedido, lo mande quien lo mande el archivo de carga.

    `size` es el tamaño con el que se quiere **ver** la fórmula, no el que se declara: Word encoge al
    73 % lo que va en el numerador y en el denominador, así que esos trozos se declaran más grandes para
    que salgan igual que el texto que los rodea. Medido sobre el PDF, con el cuerpo en 9 pt: declarando
    9 pt la fracción salía a 6,5; declarando 12,5 sale a 9.

    Lo que sí se deja encoger es el **exponente** y el índice de una raíz: un «x²» con el 2 tan grande
    como la x no se lee como matemáticas. Y una fracción dentro de otra también queda más pequeña, que
    es como se imprime en los libros.
    """
    sola = _ecuacion_sola(ecuacion)
    for r in ecuacion.iter(M + "r"):
        compensa = _en_fraccion(r) and not sola
        medios = round(size * 2 / ESCALA_FRACCION) if compensa else int(size * 2)
        rpr = r.find(W + "rPr")
        if rpr is None:
            rpr = _el("w:rPr")
            mpr = r.find(M + "rPr")
            (mpr.addnext(rpr) if mpr is not None else r.insert(0, rpr))
        for viejo in rpr.findall(W + "sz") + rpr.findall(W + "szCs"):
            rpr.remove(viejo)
        rpr.append(_el("w:sz", **{"w:val": str(medios)}))
        rpr.append(_el("w:szCs", **{"w:val": str(medios)}))
        _ordenar(rpr, ORDEN_RPR)
    return ecuacion


def parrafo_nuevo(texto="", **kw):
    p = _el("w:p")
    if texto:
        p.append(run_texto(texto, size=kw.pop("size", 9), bold=kw.pop("bold", False), italic=kw.pop("italic", False)))
    formato_parrafo(p, **kw)
    return p


def linea_superior(p):
    ppr = _ppr(p)
    bdr = _el("w:pBdr")
    bdr.append(_el("w:top", **{"w:val": "single", "w:sz": 2, "w:space": 4, "w:color": "000000"}))
    ppr.append(bdr)
    _ordenar(ppr, ORDEN_PPR)
    return p


def _desenvolver(e):
    """Reemplaza el elemento por su contenido (w:hyperlink, w:sdt, w:fldSimple…)."""
    padre = e.getparent()
    if padre is None:
        return
    contenido = e.find(W + "sdtContent") if e.tag == W + "sdt" else e
    i = padre.index(e)
    for h in list(contenido if contenido is not None else []):
        if h.tag in (W + "sdtPr", W + "sdtEndPr"):
            continue
        padre.insert(i, h)
        i += 1
    padre.remove(e)


def limpiar_fragmento(el):
    """Deja solo lo que se imprime, tal como se ve en el Word de carga.

    - Hipervínculos: queda el texto (su relación no existe en la cartilla).
    - Campos (referencias cruzadas, fechas, SEQ…): queda el resultado que se veía, congelado; así Word no
      los recalcula ni imprime «¡Error! Origen de la referencia no encontrado».
    - Marcadores (_GoBack y otros), controles de contenido y etiquetas inteligentes: se quitan; repetidos
      entre ejercicios dañarían el documento.
    """
    for tag in ("hyperlink", "sdt", "fldSimple", "smartTag", "customXml"):
        for e in list(el.iter(W + tag)):
            _desenvolver(e)
    pila = []                           # por campo abierto: "codigo" hasta el separador, luego "resultado"
    for r in list(el.iter(W + "r")):
        fc = r.find(W + "fldChar")
        if fc is not None:
            tipo = fc.get(W + "fldCharType")
            if tipo == "begin":
                pila.append("codigo")
            elif tipo == "separate" and pila:
                pila[-1] = "resultado"
            elif tipo == "end" and pila:
                pila.pop()
            r.getparent().remove(r)
        elif "codigo" in pila or r.find(W + "instrText") is not None:
            r.getparent().remove(r)
    for tag in ("bookmarkStart", "bookmarkEnd", "proofErr", "permStart", "permEnd"):
        for e in list(el.iter(W + tag)):
            e.getparent().remove(e)
    for e in list(el.iter("{%s}hlinkClick" % NS["a"], "{%s}hlinkHover" % NS["a"])):
        e.getparent().remove(e)
    for e in el.iter(W + "p"):
        for atributo in (W14 + "paraId", W14 + "textId"):
            e.attrib.pop(atributo, None)
    return el


def numerar_dibujos(doc):
    """Cada imagen del documento con su propio número interno (wp:docPr): al juntar ejercicios de archivos
    distintos, dos imágenes pueden traer el mismo, y Word puede declarar el archivo dañado."""
    usados = set()
    for parte in doc.part.package.iter_parts():
        nombre = str(parte.partname)
        if "header" in nombre or "footer" in nombre:
            usados |= {int(x) for x in re.findall(rb'<wp:docPr[^>]*\sid="(\d+)"', parte.blob)}
    n = max(usados, default=0)
    for e in doc.element.body.iter(WP + "docPr"):
        n += 1
        e.set("id", str(n))
    for i, e in enumerate(doc.element.body.iter(PIC + "cNvPr"), 1):
        e.set("id", str(i))


class Copiadora:
    """Copia fragmentos del Word de carga al de la cartilla, trayendo sus imágenes."""

    def __init__(self, destino):
        self.destino = destino
        self.imagenes = {}

    def copiar(self, item, origen, sid=None):
        el = limpiar_fragmento(copy.deepcopy(item.el))
        tbl_sid = None
        if isinstance(item, Tabla):
            estilo = el.find(f"{W}tblPr/{W}tblStyle")
            tbl_sid = estilo.get(W + "val") if estilo is not None else None
        for p in ([el] if el.tag == W + "p" else el.iter(W + "p")):
            ppr = p.find(W + "pPr")
            estilo_p = ppr.find(W + "pStyle") if ppr is not None else None
            fijar_formato_runs(p, origen.estilos, estilo_p.get(W + "val") if estilo_p is not None else None, tbl_sid)
            fijar_parrafo(p, origen.estilos, tbl_sid)
        for om in el.iter(M + "oMath"):
            # dentro de una tabla el texto va a 8 pt, fuera a 9: la ecuación se ajusta a su vecindario
            _ecuacion_al_tamano(om, TAM_ECUACION_CHICA if tbl_sid or el.tag == W + "tbl" else TAM_ECUACION)
        for blip in el.iter("{%s}blip" % NS["a"]):
            rid = blip.get(R + "embed")
            if not rid:
                continue
            clave = (id(origen), rid)
            if clave not in self.imagenes:
                datos, _ = origen.media(rid)
                if datos is None:
                    continue
                nuevo, _ = self.destino.part.get_or_add_image(io.BytesIO(datos))
                self.imagenes[clave] = nuevo
            blip.set(R + "embed", self.imagenes[clave])
        return el


# ====================================================================== portada
def _color_de_materia(s, nombre):
    m = s.scalar(select(Materia).where(Materia.nombre == nombre))
    if m:
        return m.color.lstrip("#")
    sub = s.scalar(select(Submateria).where(Submateria.nombre == nombre))
    return (sub.materia.color if sub else "#000000").lstrip("#")


def _armar_portada(doc, s, c, secciones, total):
    grado = s.scalar(select(Grado).where(Grado.codigo == c.grado))
    tipo = PERIODOS.get(c.tipo_material)
    linea = f"Simulacro N° {c.simulacro_n} | " + (tipo if tipo else ("Simulacro ICFES" if c.tipo_material in ("71", "72") else "Simulacro especial"))
    reemplazos = {
        "7°": grado.texto_portada,
        "4 horas y 40 minutos": c.tiempo,
        "Simulacro N° 1 | 3° Periodo": linea,
        "Código Cartilla: 77913301": f"Código Cartilla: {c.codigo}",
    }
    cuerpo = doc.element.body
    for p in cuerpo.iter(W + "p"):
        t = texto_de(p).strip()
        if t in reemplazos:
            poner_texto(p, reemplazos[t])
        elif re.fullmatch(r"[\d\s]+preguntas?", t):
            # el número puede venir partido en varios trozos («1» + «40»): el primero lleva el total y los demás se vacían
            primero = True
            for r in p.iter(W + "r"):
                tt = r.find(W + "t")
                if tt is None or not tt.text or not re.search(r"\d", tt.text):
                    continue
                tt.text = re.sub(r"\d+", str(total) if primero else "", tt.text)
                primero = False

    # tabla de áreas: una fila por sección, en el mismo orden del cuerpo
    for tbl in cuerpo.iter(W + "tbl"):
        filas = tbl.findall(W + "tr")
        celdas0 = filas[0].findall(W + "tc") if filas else []
        if len(celdas0) != 2 or not texto_de(filas[0]).strip().startswith("Matemáticas I"):
            continue
        modelo = copy.deepcopy(filas[0])
        for fila in filas[1:]:
            tbl.remove(fila)
        ancla = filas[0]
        for i, sec in enumerate(secciones):
            fila = ancla if i == 0 else copy.deepcopy(modelo)
            if i:
                ancla.addnext(fila)
                ancla = fila
            color = _color_de_materia(s, sec["submateria"] or sec["materia"])
            for celda, valor in zip(fila.findall(W + "tc"), [sec["titulo"].title(), str(sec["cantidad"])]):
                p = celda.find(W + "p")
                poner_texto(p, valor)
                for r in p.iter(W + "r"):
                    rpr = r.find(W + "rPr")
                    if rpr is None:
                        rpr = _el("w:rPr")
                        r.insert(0, rpr)
                    for viejo in rpr.findall(qn("w:color")):
                        rpr.remove(viejo)
                    rpr.append(_el("w:color", **{"w:val": color}))
                    _ordenar(rpr, ORDEN_RPR)


def _texto_portada_media(s, c, total):
    """Lo que cambia en la media portada, texto por texto tal como está en la plantilla."""
    grado = s.scalar(select(Grado).where(Grado.codigo == c.grado))
    tipo = PERIODOS.get(c.tipo_material)
    periodo = tipo or ("Simulacro ICFES" if c.tipo_material in ("71", "72") else f"Simulacro N° {c.simulacro_n}")
    return {
        "CIENCIAS SOCIALES Y CIUDADANAS": (c.titulo_portada or titulo_de_portada(s, c)).upper(),
        "Periodo 4°": periodo,
        "Código Cartilla: 6606550101": f"Código Cartilla: {c.codigo}",
        "6°": grado.texto_portada,
        "30 preguntas": f"{total} preguntas",
        "1 hora y 10 minutos": c.tiempo,
    }


def titulo_de_portada(s, c):
    """Si la cartilla es de una sola materia, su nombre; si no, el del simulacro."""
    materia = s.scalar(select(Materia).where(Materia.codigo == c.codigo_materia))
    if materia is not None:
        return materia.nombre
    sub = s.scalar(select(Submateria).where(Submateria.codigo == c.codigo_materia))
    if sub is not None:
        return sub.nombre
    return "Simulacro de preparación estratégica"


def _armar_portada_media(doc, s, c, total, elementos=None):
    """`elementos`: media portada ya copiada dentro de otro documento (cuadernillo de dos sesiones).

    Sin ella se recorre el documento entero, que es el caso de una cartilla suelta.
    """
    cambios = _texto_portada_media(s, c, total)
    donde = elementos if elementos is not None else [doc.element.body]
    for raiz in donde:
        for p in raiz.iter(W + "p"):          # iter() incluye al propio elemento si ya es un párrafo
            t = texto_de(p).strip()
            if t in cambios:
                poner_texto(p, cambios[t])


def ilustracion_portada(doc, elementos=None):
    """El dibujo más grande de la portada: es la ilustración del tema, la única que se puede cambiar.

    `elementos`: una media portada ya copiada dentro de otro documento (cuadernillo de dos sesiones);
    sin ella se mira desde el principio del documento hasta la marca del cuerpo.
    """
    if elementos is not None:
        parrafos = [p for raiz in elementos for p in raiz.iter(W + "p")]
    else:
        marca = next((p for p in doc.element.body.iter(W + "p") if MARCA_CUERPO in texto_de(p)), None)
        parrafos = []
        for p in doc.element.body.iter(W + "p"):
            if p is marca:
                break
            parrafos.append(p)
    mayor, area = None, 0
    for p in parrafos:
        for ext in p.iter("{%s}extent" % NS["wp"]):
            tam = int(ext.get("cx", 0)) * int(ext.get("cy", 0))
            if tam > area:
                dibujo = ext.getparent().getparent()
                blip = next(iter(dibujo.iter("{%s}blip" % NS["a"])), None)
                if blip is not None:
                    mayor, area = blip, tam
    return mayor


def cambiar_ilustracion(doc, datos, elementos=None):
    """Pone la imagen de la cartilla en lugar de la ilustración que trae la plantilla."""
    blip = ilustracion_portada(doc, elementos)
    if blip is None or not datos:
        return False
    nuevo, _ = doc.part.get_or_add_image(io.BytesIO(datos))
    blip.set(R + "embed", nuevo)
    return True


MC = "{http://schemas.openxmlformats.org/markup-compatibility/2006}"


def solo_dibujo_moderno(el):
    """Deja solo la versión DrawingML de cada forma y quita el respaldo VML de Word 2007.

    El respaldo repite la forma en otro formato y apunta a relaciones del documento de origen; al
    copiarla a otro documento esas relaciones no existen y Word da el archivo por dañado.
    """
    for alt in list(el.iter(MC + "AlternateContent")):
        choice = alt.find(MC + "Choice")
        if choice is None:
            continue
        padre = alt.getparent()
        sitio = list(padre).index(alt)
        for hijo in list(choice):
            padre.insert(sitio, hijo)
            sitio += 1
        padre.remove(alt)
    return el


def traer_imagenes(el, origen, destino):
    """Copia al documento destino las imágenes que use el fragmento y reapunta sus referencias."""
    hechas = {}
    for blip in el.iter("{%s}blip" % NS["a"]):
        rid = blip.get(R + "embed")
        if not rid:
            continue
        if rid not in hechas:
            parte = origen.part.related_parts.get(rid)
            if parte is None:
                continue
            nuevo, _ = destino.part.get_or_add_image(io.BytesIO(parte.blob))
            hechas[rid] = nuevo
        blip.set(R + "embed", hechas[rid])
    for imagedata in el.iter("{urn:schemas-microsoft-com:vml}imagedata"):
        rid = imagedata.get(R + "id")
        if rid and rid in hechas:
            imagedata.set(R + "id", hechas[rid])
    return el


def elementos_de_portada(doc):
    """Los elementos de la portada de una plantilla: todo lo que va antes de la marca del cuerpo."""
    salida = []
    for el in doc.element.body:
        if MARCA_CUERPO in texto_de(el):
            return salida
        salida.append(el)
    raise ErrorGeneracion(f"La plantilla no tiene la marca {MARCA_CUERPO}.")


def _configurar_pagina(doc, media=False):
    """Carta vertical, márgenes estrechos sin encuadernación y pies distintos en pares e impares.

    media: con media portada el cuerpo arranca debajo de la portada, en la misma página, así que el
    corte entre la portada y el cuerpo es **continuo**; con portada entera, el cuerpo empieza en la
    página siguiente.

    El margen inferior deja sitio para la separación que va detrás de la última pregunta (FIN_PREGUNTA):
    la línea que separa las dos columnas se dibuja hasta el borde de esa caja, y si no hubiera holgura
    se metería encima del número de página.
    """
    for sect in doc.element.body.iter(W + "sectPr"):
        pg = sect.find(W + "pgSz")
        if pg is not None:
            pg.set(W + "w", "12240")
            pg.set(W + "h", "15840")
            if pg.get(W + "orient"):
                del pg.attrib[W + "orient"]
        mar = sect.find(W + "pgMar")
        if mar is not None:
            for lado in ("top", "right", "left"):
                mar.set(W + lado, "720")
            mar.set(W + "bottom", str(MARGEN_INFERIOR))
            mar.set(W + "gutter", "0")
            mar.set(W + "footer", "283")
            mar.set(W + "header", "283")
        cols = sect.find(W + "cols")
        if cols is not None and int(cols.get(W + "num", "1")) == 2:
            cols.set(W + "space", str(ESPACIO_COLUMNAS))
    primera = next((x for x in doc.element.body.iter(W + "sectPr")), None)
    if primera is not None:
        for viejo in primera.findall(W + "type"):
            primera.remove(viejo)
        primera.append(_el("w:type", **{"w:val": "continuous" if media else "nextPage"}))
        _ordenar(primera, ORDEN_SECTPR)
    ultimo = doc.element.body.find(W + "sectPr")
    if ultimo is not None:
        for viejo in ultimo.findall(W + "type"):
            ultimo.remove(viejo)
        ultimo.append(_el("w:type", **{"w:val": "nextPage"}))
        _ordenar(ultimo, ORDEN_SECTPR)
    doc.settings.odd_and_even_pages_header_footer = True
    # en un párrafo justificado, la línea que termina con Mayús+Enter (versos, direcciones) no se estira
    compat = doc.settings.element.find(W + "compat")
    if compat is None:
        compat = _el("w:compat")
        doc.settings.element.append(compat)
    if compat.find(W + "doNotExpandShiftReturn") is None:
        nuevo = _el("w:doNotExpandShiftReturn")
        ajuste = compat.find(W + "compatSetting")
        if ajuste is not None:
            ajuste.addprevious(nuevo)
        else:
            compat.append(nuevo)


# ====================================================================== cuerpo
def _numero(n, tab=False):
    """«12. » en negrita; en las preguntas sin enunciado, «12.» y una tabulación hasta la columna de la letra."""
    r = run_texto(f"{n}." if tab else f"{n}. ", bold=True)
    if tab:
        r.append(_el("w:tab"))
    return r


def _letra_con_tab(el, destino):
    """«A. texto» pasa a «A.⇥texto»: la tabulación lleva el texto a la sangría de la opción, así la primera
    línea queda alineada con las siguientes y el espacio tras la letra no se estira al justificar."""
    ts = list(el.iter(W + "t"))
    for i, t in enumerate(ts):
        if t.text and re.match(r"^\s*[A-D]\.", t.text):
            resto = re.sub(r"^\s*[A-D]\.\s*", "", t.text, count=1)
            t.text = f"{destino}."
            tab = _el("w:tab")
            t.addnext(tab)
            if resto:
                nuevo = _el("w:t")
                nuevo.set(qn("xml:space"), "preserve")
                nuevo.text = resto
                tab.addnext(nuevo)
            else:                      # el texto sigue en otro run: sin los espacios iniciales
                for sig in ts[i + 1:]:
                    if sig.text:
                        sig.text = sig.text.lstrip()
                        if sig.text:
                            break
            return True
    return False


def _es_figura(item):
    """Una tabla o un párrafo con imagen: lo que no se puede separar del texto que lo explica."""
    return isinstance(item, Tabla) or bool(getattr(item, "dibujos", None))


def _pegar_al_siguiente(enunciado, j):
    """¿Este trozo del enunciado tiene que quedar pegado al que le sigue? (Estándar 3.8)

    La pregunta puede cortarse por donde haga falta para no desperdiciar espacio: entre el enunciado y
    las opciones, entre las opciones, y también antes de una imagen o de una tabla (la frase que las
    presenta se queda al final de la columna y la figura abre la siguiente).

    Lo único que no se separa es una figura de lo que viene **detrás** de ella: lo que la interpreta
    («densidad = masa ÷ volumen», la pregunta que la acompaña) tiene que verse junto con la figura.
    """
    if j >= len(enunciado) - 1:
        return False
    return _es_figura(enunciado[j])


def _separar(p, lado):
    """Deja al menos el aire de una figura a ese lado del párrafo (el vecino de una tabla)."""
    sp = _ppr(p).find(W + "spacing")
    if sp is not None and int(sp.get(W + lado, "0")) < ESPACIO_TRAS_TABLA:
        sp.set(W + lado, str(ESPACIO_TRAS_TABLA))


def _numerar_espacios(el, primera):
    """En «completar el texto», (#1), (#2)… pasan a ser el número real de la pregunta y su raya."""
    for t in el.iter(W + "t"):
        if t.text and "(#" in t.text:
            t.text = re.sub(r"\(#(\d+)\)", lambda m: f"({primera + int(m.group(1)) - 1}) ______", t.text)
            t.set(qn("xml:space"), "preserve")


def _armar_cuerpo(doc, s, c, cop, orden=None, piezas=None, ancla=None):
    """`ancla`: dónde se insertan las preguntas. Sin ella se usa la marca de la plantilla y se retira.

    El cuadernillo de dos sesiones pasa su propia ancla, porque el cuerpo de la segunda sesión no va en
    la marca de la plantilla sino detrás de su media portada.
    """
    # «ancla or …» no sirve: un elemento de lxml sin hijos es falso, y el ancla es un párrafo vacío
    marca = ancla if ancla is not None else next(
        (p for p in doc.element.body.iter(W + "p") if MARCA_CUERPO in texto_de(p)), None)
    if marca is None:
        raise ErrorGeneracion(f"La plantilla de la cartilla no tiene la marca {MARCA_CUERPO}.")
    num = posiciones(c, orden)
    secuencia = _plantilla(s, c.plantilla)
    es_icfes = c.grado == base.GRADO_ICFES
    archivos, salida, claves = {}, [], []
    glosarios = 0
    for sec in sorted(c.secciones, key=lambda x: x.orden):
        items = orden_items(c, sec, orden)
        if not items:
            continue
        titulo = formato_parrafo(parrafo_nuevo(sec.titulo, size=12, bold=True), antes=4, despues=6,
                                 alin="center", juntar=True)
        if piezas is not None:
            piezas.append({"clave": f"S{sec.id}", "tipo": "titulo", "seccion": sec.id,
                           "ejercicios": [], "elemento": titulo})
        salida.append(titulo)
        bloques_vistos, numero_parte = set(), 0
        for it in items:
            e = it.ejercicio
            if piezas is not None:
                # una pieza por pregunta; lo que antecede al bloque (cabecera, texto, imagen) va con la primera
                piezas.append({"clave": f"E{e.id}", "tipo": "pregunta", "seccion": sec.id, "ejercicios": [e.id],
                               "elemento": None, "bloque": e.bloque_id, "codigo": e.codigo, "desde": len(salida)})
            if e.archivo_id not in archivos:
                arch = s.get(Archivo, e.archivo_id)
                archivos[e.archivo_id] = analisis.leer(e.archivo_id, arch.datos, arch.nombre)
            v = archivos[e.archivo_id]
            origen = v.doc
            pregunta = v.unidad.preguntas[e.orden_en_bloque - 1]
            n = num[e.id]
            letra = secuencia[n - 1]

            if e.bloque_id and e.bloque_id not in bloques_vistos:
                bloques_vistos.add(e.bloque_id)
                hermanos = [x for x in items if x.ejercicio.bloque_id == e.bloque_id]
                ini, fin = num[hermanos[0].ejercicio_id], num[hermanos[-1].ejercicio_id]
                bloque = s.get(Bloque, e.bloque_id)
                cab = cop.copiar(v.unidad.cabecera, origen)
                texto_cab = texto_de(cab)
                texto_cab = texto_cab.replace("#N", str(ini)).replace("#M", str(fin))
                if bloque.tipo == "parte":
                    numero_parte += 1
                    texto_cab = re.sub(r"PARTE\s+#P", f"PARTE {numero_parte}", texto_cab)
                poner_texto(cab, texto_cab)
                formato_parrafo(cab, antes=4 if bloque.tipo == "parte" else 0, despues=1 if bloque.tipo == "parte" else 3,
                                alin="left" if bloque.tipo == "parte" else "both", juntar=True)
                if bloque.tipo == "parte":
                    linea_superior(cab)
                salida.append(cab)
                if v.unidad.instruccion is not None:
                    ins = cop.copiar(v.unidad.instruccion, origen)
                    formato_parrafo(ins, despues=4, alin=alineacion_impresa(v.unidad.instruccion), juntar=True)
                    for r in ins.iter(W + "r"):
                        rpr = r.find(W + "rPr")
                        if rpr is not None and rpr.find(W + "i") is None:
                            rpr.append(_el("w:i"))
                            _ordenar(rpr, ORDEN_RPR)
                    salida.append(ins)
                for r_item in v.unidad.recurso:
                    el = cop.copiar(r_item, origen)
                    if el.tag == W + "p":
                        centrado = bool(r_item.dibujos) and not r_item.texto.strip()
                        aire = ESPACIO_FIGURA if r_item.dibujos else 0
                        formato_parrafo(el, antes=aire, despues=aire or 2,
                                        alin=alineacion_impresa(r_item), juntar=centrado)
                    else:
                        ajustar_tabla(el, origen.estilos, juntar=False)
                    _numerar_espacios(el, ini)          # «completar el texto»: (#1) pasa a ser el número real
                    salida.append(el)
                if v.unidad.credito is not None:
                    cred = cop.copiar(v.unidad.credito, origen)
                    formato_parrafo(cred, antes=2, despues=5, alin="right")
                    salida.append(cred)

            vacio = not pregunta.enunciado
            for j, item_en in enumerate(pregunta.enunciado):
                el = cop.copiar(item_en, origen)
                juntar = _pegar_al_siguiente(pregunta.enunciado, j)
                if el.tag == W + "p":
                    aire = ESPACIO_FIGURA if item_en.dibujos else 0
                    formato_parrafo(el, antes=aire, despues=aire or 2,
                                    alin=alineacion_impresa(item_en), juntar=juntar)
                    if j == 0:
                        el.insert(len(el.findall(W + "pPr")), _numero(n))
                else:
                    ajustar_tabla(el, origen.estilos, juntar=juntar)
                salida.append(el)

            opciones = {letra_opcion(o): o for o in pregunta.opciones}
            # columna del texto de las opciones; sin enunciado, el número va antes de la A y las letras se alinean
            sangria = COL_NUMERO + COL_LETRA if vacio else COL_LETRA
            # lo que va después de la opción D: línea ➤ (salvo ICFES) y debajo el glosario (si la cartilla lo incluye)
            terminos = glosario.terminos(e) if c.glosario else []
            campos = [] if es_icfes else [x for x in (e.pensamiento, e.competencia, e.dba, ABREV_NIVEL.get(e.nivel, "")) if x]
            cola, pg = [], None
            if campos:
                cola.append(parrafo_nuevo("➤ " + " // ".join(campos), size=6, italic=True))
            if terminos:
                pg = _el("w:p")
                for texto, negrita, cursiva, vert, omml in glosario.partes(terminos):
                    if omml:                       # una fórmula escrita con el editor de ecuaciones
                        ecuacion = glosario.ecuacion({"omml": omml})
                        if ecuacion is not None:
                            pg.append(_ecuacion_al_tamano(ecuacion, TAM_ECUACION_CHICA))
                            continue
                    if texto:
                        pg.append(run_texto(texto, size=8, bold=negrita, italic=cursiva, vert=vert))
                cola.append(pg)
                glosarios += 1
            for k, destino in enumerate("ABCD"):
                origen_letra = e.clave_original if destino == letra else (letra if destino == e.clave_original else destino)
                el = cop.copiar(opciones[origen_letra], origen)
                _letra_con_tab(el, destino)
                ultimo = k == 3 and not cola
                formato_parrafo(el, despues=FIN_PREGUNTA if ultimo else (1 if k == 3 else 0),
                                alin=alineacion_impresa(opciones[origen_letra]),
                                juntar=bool(opciones[origen_letra].dibujos), sangria=sangria,
                                colgante=COL_LETRA if (vacio and k > 0) else None,
                                tabs=[COL_NUMERO] if (vacio and k == 0) else None)
                if vacio and k == 0:
                    el.insert(len(el.findall(W + "pPr")), _numero(n, tab=True))
                salida.append(el)
            for j, el in enumerate(cola):
                final = j == len(cola) - 1
                formato_parrafo(el, antes=0, despues=FIN_PREGUNTA if final else 1, alin="both" if el is pg else None,
                                juntar=False)
                salida.append(el)
            claves.append({"posicion": n, "letra": letra, "ejercicio": e, "item": it})

    for p in piezas or []:
        if p["tipo"] == "pregunta":
            p["elemento"] = salida[p.pop("desde")]

    # aire a los dos lados de cada tabla: una tabla no tiene espaciado propio, se lo ponen sus vecinos
    for antes, despues in zip(salida, salida[1:]):
        if antes.tag == W + "tbl" and despues.tag == W + "p":
            _separar(despues, "before")
        elif antes.tag == W + "p" and despues.tag == W + "tbl":
            _separar(antes, "after")
    for el in salida:
        marca.addprevious(el)
    if ancla is None:
        marca.getparent().remove(marca)      # el ancla prestada no es nuestra: se deja donde está
    return sorted(claves, key=lambda x: x["posicion"]), glosarios


# ====================================================================== Excel
def _armar_excel(c, claves):
    wb = Workbook()
    hoja = wb.active
    hoja.title = "Claves"
    es_icfes = c.grado == base.GRADO_ICFES
    hoja["A1"] = "CLAVES DE RESPUESTAS — una fila por pregunta de cada cartilla"
    hoja["A1"].font = Font(bold=True)
    hoja["M1"] = NOTA_EXCEL
    hoja["M1"].alignment = Alignment(wrap_text=True, vertical="top")
    for i, enc in enumerate(ENC_EXCEL, 1):
        celda = hoja.cell(row=2, column=i, value=enc)
        celda.font = Font(bold=True)
        celda.fill = PatternFill("solid", fgColor="E2EFD7")
    for fila, k in enumerate(claves, 3):
        e = k["ejercicio"]
        vacio_icfes = "" if es_icfes else None
        submateria = "" if (es_icfes and e.materia == "Matemáticas") else e.submateria
        valores = [c.codigo, k["posicion"], k["letra"], e.materia, submateria,
                   vacio_icfes if es_icfes else e.pensamiento, vacio_icfes if es_icfes else e.competencia,
                   vacio_icfes if es_icfes else e.dba, vacio_icfes if es_icfes else e.tematica,
                   vacio_icfes if es_icfes else e.nivel, e.justificacion]
        for col, valor in enumerate(valores, 1):
            hoja.cell(row=fila, column=col, value=valor if valor is not None else "")
    anchos = [12, 10, 10, 20, 22, 20, 26, 10, 26, 10, 70]
    for i, ancho in enumerate(anchos, 1):
        hoja.column_dimensions[get_column_letter(i)].width = ancho
    hoja.freeze_panes = "A3"
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ====================================================================== verificación cruzada
def _leer_cartilla_generada(datos):
    """Lee el Word generado y devuelve, por pregunta, su número y las letras de sus opciones."""
    doc = Document(io.BytesIO(datos))
    preguntas, actual = [], None
    for p in doc.paragraphs:
        t = p.text.strip()
        # «9. A. went»: en «completar el texto» el número va en la misma línea que la opción A
        #
        # Tras el punto puede no venir NADA: cuando la opción es una imagen (¿cuál rectángulo está
        # sombreado?), el párrafo dice solo «A.» y la figura va al lado. Exigir un espacio dejaba esas
        # preguntas sin opciones y la verificación impedía generar la cartilla entera.
        junto = re.match(r"^(\d+)\.\s+([A-D])\.(?:\s|$)", t)
        numero = re.match(r"^(\d+)\.(?:\s|$)", t)
        opcion = re.match(r"^([A-D])\.(?:\s|$)", t)
        if junto:
            actual = {"numero": int(junto.group(1)), "opciones": [junto.group(2)]}
            preguntas.append(actual)
        elif numero:
            actual = {"numero": int(numero.group(1)), "opciones": []}
            preguntas.append(actual)
        elif opcion and actual is not None:
            actual["opciones"].append(opcion.group(1))
    return preguntas


def _contar_glosarios(datos):
    return sum(1 for p in Document(io.BytesIO(datos)).paragraphs if p.text.startswith("Glosario: "))


def _verificar_cruzado(docx_datos, claves, secuencia, glosarios=None):
    fallas = []
    leidas = _leer_cartilla_generada(docx_datos)
    if glosarios is not None and _contar_glosarios(docx_datos) != glosarios:
        fallas.append(f"La cartilla debía llevar {glosarios} glosarios y tiene {_contar_glosarios(docx_datos)}.")
    if len(leidas) != len(claves):
        fallas.append(f"La cartilla tiene {len(leidas)} preguntas y el Excel {len(claves)}.")
    for k, leida in zip(claves, leidas):
        if leida["numero"] != k["posicion"]:
            fallas.append(f"La pregunta en la posición {k['posicion']} quedó numerada como {leida['numero']}.")
        if leida["opciones"][:4] != list("ABCD"):
            fallas.append(f"La pregunta {k['posicion']} no tiene las opciones A, B, C y D en orden: {''.join(leida['opciones'])}.")
        if k["letra"] != secuencia[k["posicion"] - 1]:
            fallas.append(f"La clave de la pregunta {k['posicion']} no coincide con la plantilla.")
    return fallas


# ====================================================================== generación
ALTO_MEDICION = 31680           # 22 pulgadas en twips: el máximo de Word


def _marca_medicion():
    """Párrafo vacío y diminuto: su posición es el final de la pieza que lo antecede.

    No puede ser el propio párrafo del salto de columna: Word informa la posición de ese después del
    salto, es decir, ya en la columna siguiente.
    """
    p = _el("w:p")
    ppr = _ppr(p)
    ppr.append(_el("w:spacing", **{"w:before": 0, "w:after": 0, "w:line": 20, "w:lineRule": "exact"}))
    r = _el("w:r")
    rpr = _el("w:rPr")
    rpr.append(_el("w:sz", **{"w:val": "2"}))
    r.append(rpr)
    p.append(r)
    return p


def _salto_columna():
    p = _el("w:p")
    ppr = _ppr(p)
    ppr.append(_el("w:spacing", **{"w:before": 0, "w:after": 0, "w:line": 20, "w:lineRule": "exact"}))
    r = _el("w:r")
    r.append(_el("w:br", **{"w:type": "column"}))
    p.append(r)
    return p


def _preparar_medicion(doc, piezas):
    """Deja el documento listo para medir alturas: cada pieza empieza arriba de una columna y cabe entera.

    La anchura de la columna no cambia (de ella depende la altura de cada pregunta); solo se estira la
    página, para que ninguna pregunta tenga que partirse.
    """
    for pgsz in doc.element.body.iter(W + "pgSz"):
        pgsz.set(qn("w:h"), str(ALTO_MEDICION))
        pgsz.set(qn("w:orient"), "portrait")
    for anterior, p in zip(piezas, piezas[1:]):
        marca = _marca_medicion()
        p["elemento"].addprevious(marca)
        p["elemento"].addprevious(_salto_columna())
        anterior["cierre"] = marca
    final = _marca_medicion()          # cierra la última pieza, para poder medirla igual que las demás
    ultimo = doc.element.body.find(W + "sectPr")
    if ultimo is not None:
        ultimo.addprevious(final)
    else:
        doc.element.body.append(final)
    piezas[-1]["cierre"] = final


def marcar(elemento, nombre, bid):
    """Pone un marcador de Word al comienzo del elemento, para poder preguntarle después dónde quedó.

    Los marcadores solo se ponen en las copias que se miden, nunca en el Word que se entrega.
    """
    inicio = _el("w:bookmarkStart", **{"w:id": str(bid), "w:name": nombre})
    fin = _el("w:bookmarkEnd", **{"w:id": str(bid)})
    if elemento.tag == W + "p":
        ppr = elemento.find(W + "pPr")
        sitio = list(elemento).index(ppr) + 1 if ppr is not None else 0
        elemento.insert(sitio, fin)
        elemento.insert(sitio, inicio)
    else:                                   # una tabla: el marcador va justo antes, al nivel del cuerpo
        elemento.addprevious(inicio)
        elemento.addprevious(fin)
    return nombre


def _construir(s, c, orden=None, piezas=None, medicion=False):
    """Arma el Word completo en memoria y devuelve (bytes, claves, glosarios). No guarda nada.

    medicion: documento para medir alturas (ver app/maqueta.py): páginas muy altas y un salto de columna
    antes de cada pregunta, de modo que cada una empiece arriba de su columna y entre completa.
    """
    secciones = [{"titulo": x.titulo, "materia": x.materia, "submateria": x.submateria, "cantidad": x.cantidad}
                 for x in sorted(c.secciones, key=lambda y: y.orden) if x.cantidad]
    total = sum(x["cantidad"] for x in secciones)
    media = c.portada == "media"
    doc = Document(str(PORTADAS.get(c.portada, BASE_DOCX)))
    _configurar_pagina(doc, media)
    if media:
        _armar_portada_media(doc, s, c, total)
    else:
        _armar_portada(doc, s, c, secciones, total)
    if c.imagen:
        cambiar_ilustracion(doc, c.imagen)
    cop = Copiadora(doc)
    anotar = piezas if piezas is not None else ([] if medicion else None)
    claves, glosarios = _armar_cuerpo(doc, s, c, cop, orden, anotar)
    numerar_dibujos(doc)
    if medicion:
        _preparar_medicion(doc, anotar)
    for k, p in enumerate(anotar or []):
        # el nombre del marcador sale de la pieza, no de su posición: así no cambia al reordenar
        p["marca"] = marcar(p.pop("elemento"), "PZ" + p["clave"], 9000 + 2 * k)
        if "cierre" in p:
            p["cierre"] = marcar(p.pop("cierre"), "FIN" + p["clave"], 9001 + 2 * k)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue(), claves, glosarios


def construir(cid, orden=None, piezas=None, medicion=False):
    """El Word de la cartilla tal como quedaría hoy, sin guardarlo: sirve para medir la maquetación."""
    with Sesion() as s:
        c = s.get(Cartilla, cid)
        if c is None:
            return None
        return _construir(s, c, orden, piezas, medicion)[0]


def generar(cid, nombre_archivo=None):
    with Sesion() as s:
        c = s.get(Cartilla, cid)
        if c is None:
            return None
        pruebas = _verificar(s, c)
        if not all(p["ok"] for p in pruebas):
            faltan = [p["texto"] for p in pruebas if not p["ok"]]
            raise ErrorGeneracion("No se puede generar todavía: " + " · ".join(faltan))
        docx_datos, claves, glosarios = _construir(s, c)

        secuencia = _plantilla(s, c.plantilla)
        fallas = _verificar_cruzado(docx_datos, claves, secuencia, glosarios)
        if fallas:
            raise ErrorGeneracion("La verificación falló, no se generó nada: " + " · ".join(fallas))

        xlsx_datos = _armar_excel(c, claves)
        nombre = (nombre_archivo or f"{c.codigo} - {c.nombre}").strip()
        if not nombre or re.search(r'[\\/:*?"<>|]', nombre):
            raise ErrorGeneracion('El nombre del archivo no puede ir vacío ni llevar estos caracteres: \\ / : * ? " < > |')

        for viejo in s.scalars(select(CartillaArchivo).where(CartillaArchivo.cartilla_id == c.id)):
            s.delete(viejo)
        s.add(CartillaArchivo(cartilla_id=c.id, tipo="docx", nombre=f"{nombre}.docx", datos=docx_datos))
        s.add(CartillaArchivo(cartilla_id=c.id, tipo="xlsx", nombre=f"{nombre}.xlsx", datos=xlsx_datos))
        for k in claves:
            k["item"].letra_final = k["letra"]
            if c.estado != "generada":
                k["ejercicio"].veces_usado += 1
        c.estado = "generada"
        c.generada_en = datetime.now()
        c.paginas = paginas.contar(docx_datos)        # para el ajuste a múltiplo de 4 (3.7)
        s.commit()
        return {"codigo": c.codigo, "nombre": nombre, "preguntas": len(claves), "glosarios": glosarios,
                "docx": f"{nombre}.docx", "xlsx": f"{nombre}.xlsx", "paginas": c.paginas,
                "faltan_paginas": paginas.faltan_para_multiplo(c.paginas),
                "verificacion": [p["texto"] for p in pruebas]}


def contar_paginas(cid):
    """Vuelve a contar las páginas del Word guardado (por ejemplo, si Word no estaba disponible al generar)."""
    with Sesion() as s:
        c = s.get(Cartilla, cid)
        if c is None:
            return None
        a = s.scalar(select(CartillaArchivo).where(CartillaArchivo.cartilla_id == cid, CartillaArchivo.tipo == "docx"))
        if a is None:
            raise ErrorGeneracion("La cartilla no tiene Word guardado: genérala primero.")
        c.paginas = paginas.contar(a.datos)
        s.commit()
        return {"paginas": c.paginas, "faltan_paginas": paginas.faltan_para_multiplo(c.paginas)}


def archivos(cid):
    with Sesion() as s:
        return [{"tipo": a.tipo, "nombre": a.nombre, "bytes": len(a.datos)}
                for a in s.scalars(select(CartillaArchivo).where(CartillaArchivo.cartilla_id == cid))]


def archivo(cid, tipo):
    with Sesion() as s:
        a = s.scalar(select(CartillaArchivo).where(CartillaArchivo.cartilla_id == cid, CartillaArchivo.tipo == tipo))
        return (a.nombre, a.datos) if a else None
