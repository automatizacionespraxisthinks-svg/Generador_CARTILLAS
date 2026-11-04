# -*- coding: utf-8 -*-
"""Arma las plantillas de cartilla: portada completa, media portada y el cierre con el código QR.

La portada y el cierre viven en plantillas de Word, no en el código: así se pueden retocar a mano sin
tocar el programa. Este script las construye a partir de dos fuentes:

- `PLANTILLA_CARTILLA_BASE.docx`, que ya traía la portada completa.
- La cartilla de muestra del Día del Boyacencismo, de donde salen la **media portada** (título,
  ilustración, recuadros de datos e instrucciones) y el **cierre con el QR**.

Se ejecuta a mano cuando haya que rehacerlas:  python -m scripts.construir_plantillas_portada
"""
import copy
import io
import sys
from pathlib import Path

from docx import Document

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from app.config import PLANTILLAS                                  # noqa: E402
from app.generador import NS, ORDEN_TBLPR, R, W, _el, _ordenar, limpiar_fragmento   # noqa: E402

MUESTRA = Path(r"D:\Users\User\Downloads\Dia del Boyacencismo\Sexto\Cartilla 6.docx")
BASE = PLANTILLAS / "PLANTILLA_CARTILLA_BASE.docx"
BASE_ORIGEN = PLANTILLAS / "origen" / "PLANTILLA_CARTILLA_BASE_origen.docx"   # la portada completa, sin tocar
MEDIA = PLANTILLAS / "PLANTILLA_CARTILLA_MEDIA.docx"
MARCA_CUERPO = "[[CUERPO]]"


def texto(el):
    return "".join(t.text or "" for t in el.iter(W + "t"))


def traer_imagenes(el, origen, destino):
    """Copia al documento destino las imágenes que use el fragmento y reapunta sus referencias."""
    hechas = {}
    for blip in el.iter("{%s}blip" % NS["a"]):
        rid = blip.get(R + "embed")
        if not rid or rid in hechas:
            if rid:
                blip.set(R + "embed", hechas[rid])
            continue
        parte = origen.part.related_parts[rid]
        nuevo, _ = destino.part.get_or_add_image(io.BytesIO(parte.blob))
        hechas[rid] = nuevo
        blip.set(R + "embed", nuevo)
    # las formas de Word 2007 repiten la imagen en VML; sin relación válida Word se queja al abrir
    for imagedata in el.iter("{urn:schemas-microsoft-com:vml}imagedata"):
        rid = imagedata.get(R + "id")
        if rid and rid in hechas:
            imagedata.set(R + "id", hechas[rid])
    return el


MC = "{http://schemas.openxmlformats.org/markup-compatibility/2006}"


def solo_dibujo_moderno(run):
    """Deja únicamente la versión DrawingML de la forma y quita el respaldo VML de Word 2007.

    El respaldo repite la forma en otro formato y apunta a relaciones del documento de origen; sin
    ellas, Word da el archivo por dañado.
    """
    for alt in list(run.iter(MC + "AlternateContent")):
        choice = alt.find(MC + "Choice")
        if choice is None:
            continue
        padre = alt.getparent()
        sitio = list(padre).index(alt)
        for hijo in list(choice):
            padre.insert(sitio, hijo)
            sitio += 1
        padre.remove(alt)
    return run


def bloque_qr(muestra, destino, ancla):
    """El recuadro «¡ESCANEA Y APRENDE!» de la muestra, detrás del elemento indicado.

    Se copia la forma tal cual —rectángulo redondeado, borde grueso, el QR y su texto— en vez de
    rehacerla: así la cartilla sale exactamente como la diseñó PRAXIS.
    """
    for p in muestra.element.body.iter(W + "p"):
        for run in p.findall(W + "r"):
            if "ESCANEA Y APRENDE" not in texto(run):
                continue
            nuevo = _el("w:p")
            ppr = _el("w:pPr")
            ppr.append(_el("w:jc", **{"w:val": "center"}))
            nuevo.append(ppr)
            nuevo.append(traer_imagenes(solo_dibujo_moderno(copy.deepcopy(run)), muestra, destino))
            ancla.addnext(nuevo)
            return nuevo
    raise SystemExit("No encontré el recuadro del QR en la cartilla de muestra.")


def cierre_de(muestra):
    """Los párrafos del cierre de la muestra: «¡Prueba finalizada!» hasta la frase final.

    Se les quitan los hipervínculos y los campos: apuntan a relaciones del documento de origen y, en
    otro documento, Word daría el archivo por dañado. El correo queda como texto, que es lo que se imprime.
    """
    els = list(muestra.element.body)
    desde = next(i for i, el in enumerate(els) if texto(el).strip() == "¡Prueba finalizada!")
    hasta = next(i for i, el in enumerate(els) if texto(el).strip().startswith("¡Prepárate!"))
    return [limpiar_fragmento(copy.deepcopy(x)) for x in els[desde:hasta + 1]]


def marca_cuerpo():
    p = _el("w:p")
    r = _el("w:r")
    t = _el("w:t")
    t.text = MARCA_CUERPO + " — el sistema inserta aquí los títulos de sección y las preguntas"
    r.append(t)
    p.append(r)
    return p


def construir_media(muestra):
    """Media portada: la de la muestra, con el cuerpo vaciado y el cierre detrás."""
    doc = Document(str(MUESTRA))
    els = list(doc.element.body)
    # el cuerpo va desde la primera pregunta hasta el párrafo que cierra la sección a dos columnas
    inicio = next(i for i, el in enumerate(els) if texto(el).strip().startswith("1. "))
    fin = next(i for i, el in enumerate(els)
               if el.find(f"{W}pPr/{W}sectPr") is not None and i > inicio)
    for el in els[inicio:fin]:
        doc.element.body.remove(el)
    ancla = els[fin]
    marca = marca_cuerpo()
    ancla.addprevious(marca)
    bloque_qr(muestra, doc, marca)
    doc.save(str(MEDIA))
    return doc


def construir_completa(muestra):
    """Portada completa: la que ya existía, con el cierre y el QR de la muestra."""
    doc = Document(str(BASE_ORIGEN))
    els = list(doc.element.body)
    marca = next(el for el in els if MARCA_CUERPO in texto(el))
    bloque_qr(muestra, doc, marca)
    # fuera el cierre viejo («¡Objetivo cumplido!» … frase final) y dentro el de la muestra
    desde = next(i for i, el in enumerate(els) if texto(el).strip().startswith("¡Objetivo cumplido!"))
    hasta = next(i for i, el in enumerate(els) if texto(el).strip().startswith("¡Prepárate"))
    ancla = els[hasta]
    for p in cierre_de(muestra):
        ancla.addnext(p)
        ancla = p
    for el in els[desde:hasta + 1]:
        doc.element.body.remove(el)
    doc.save(str(BASE))
    return doc


if __name__ == "__main__":
    muestra = Document(str(MUESTRA))
    construir_media(muestra)
    print("escrita", MEDIA.name)
    construir_completa(muestra)
    print("reescrita", BASE.name)
