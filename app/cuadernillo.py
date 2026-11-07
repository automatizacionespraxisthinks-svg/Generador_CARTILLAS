"""Cuadernillo de varias sesiones: dos o más cartillas impresas en un solo Word.

Un simulacro largo se aplica en sesiones: por ejemplo 140 preguntas por la mañana y 100 por la tarde.
Cada sesión **es una cartilla completa**, con su código de 10 dígitos, su hoja de respuestas y su
numeración propia que empieza en 1. Lo único que se junta es el papel.

Cómo queda el archivo:

    portada completa de la sesión 1
    cuerpo de la sesión 1, a dos columnas, numerado 1…N
    ── salto a página impar ──                 (la sesión 2 abre en la hoja derecha)
    media portada de la sesión 2, con SU código de cartilla a la vista
    cuerpo de la sesión 2, numerado otra vez desde 1
    cierre con el código QR, una sola vez al final

El Excel no se junta: cada sesión conserva el suyo, porque se usa una hoja de respuestas por sesión y
el lector OMR necesita el código de esa sesión. Aquí solo se arma el Word para imprimir.

Las cartillas tienen que estar **generadas** antes: así las letras de cada pregunta ya están fijadas y
el cuadernillo sale con exactamente las mismas claves que sus Excel.
"""
import copy
import io
import re
import zipfile

from docx import Document
from sqlalchemy import select

from app import generador, paginas
from app.bd import Cartilla, CartillaArchivo, Sesion
from app.generador import (BASE_DOCX, MARCA_CUERPO, MEDIA_DOCX, ORDEN_SECTPR, W, Copiadora, ErrorGeneracion,
                           _el, _ordenar, texto_de)

MINIMO, MAXIMO = 2, 6          # un cuadernillo tiene al menos dos sesiones; más de seis no se imprime


# ====================================================================== cortes entre sesiones
def _poner_tipo(sect, tipo):
    """El `w:type` de una sección dice **cómo empieza esa misma sección**, no la siguiente.

    Es fácil leerlo al revés, y leerlo al revés deja el salto de página en el sitio equivocado: la media
    portada de la sesión siguiente se parte, con sus recuadros en una hoja y las instrucciones en otra.
    """
    for viejo in sect.findall(W + "type"):
        sect.remove(viejo)
    sect.append(_el("w:type", **{"w:val": tipo}))
    _ordenar(sect, ORDEN_SECTPR)
    return sect


def _corte(sectpr_modelo, tipo, columnas):
    """Un párrafo vacío que cierra una sección, con el tipo y las columnas que esa sección necesita.

    El modelo se copia de una sección ya configurada del documento, así hereda el tamaño de hoja y los
    márgenes sin repetir aquí esos números.
    """
    sect = copy.deepcopy(sectpr_modelo)
    # se RETOCA el bloque de columnas de la plantilla, no se rehace: traía «w:sep», que es la línea
    # vertical entre las dos columnas. Rehacerlo la perdía, y la sesión 1 salía sin esa línea.
    cols = sect.find(W + "cols")
    if cols is None:
        cols = _el("w:cols")
        sect.append(cols)
    cols.set(W + "num", str(columnas))
    if columnas > 1:
        cols.set(W + "space", str(generador.ESPACIO_COLUMNAS))
        cols.set(W + "sep", "1")
    else:
        for sobra in (W + "space", W + "sep"):
            cols.attrib.pop(sobra, None)
    _poner_tipo(sect, tipo)
    p = _el("w:p")
    ppr = _el("w:pPr")
    ppr.append(sect)
    p.append(ppr)
    return p


def _secciones_de(doc):
    """(la del cuerpo a dos columnas, la de la portada) de la plantilla base, ya configuradas."""
    dentro = [p.find(W + "pPr/" + W + "sectPr") for p in doc.element.body.iter(W + "p")]
    dentro = [x for x in dentro if x is not None]
    if len(dentro) < 2:
        raise ErrorGeneracion("La plantilla de la cartilla no tiene las secciones esperadas.")
    portada, cuerpo = dentro[0], dentro[1]
    return cuerpo, portada


# ====================================================================== armado
def _sin_seccion(el):
    """Quita el `sectPr` que el elemento traiga de su plantilla de origen.

    El último párrafo de la media portada cierra la sección en SU plantilla, y ese `sectPr` apunta a los
    encabezados y pies de ese documento. Copiado tal cual, Word da el cuadernillo por dañado. La sección
    del cuadernillo la pone `_corte`, así que este sobra.
    """
    for ppr in el.iter(W + "pPr"):
        for sect in ppr.findall(W + "sectPr"):
            ppr.remove(sect)
    return el


def _media_portada_en(doc, s, c, total):
    """Copia la media portada de la plantilla al cuadernillo y le pone los datos de esa sesión.

    Devuelve los elementos ya insertados, en orden, para poder cambiarles la ilustración después.
    """
    plantilla = Document(str(MEDIA_DOCX))
    copiados = []
    for el in generador.elementos_de_portada(plantilla):
        nuevo = generador.traer_imagenes(generador.solo_dibujo_moderno(copy.deepcopy(el)), plantilla, doc)
        copiados.append(_sin_seccion(generador.limpiar_fragmento(nuevo)))
    generador._armar_portada_media(doc, s, c, total, elementos=copiados)
    if c.imagen:
        generador.cambiar_ilustracion(doc, c.imagen, elementos=copiados)
    return copiados


def _construir(s, cartillas):
    """El Word del cuadernillo entero. Devuelve (bytes, [claves de cada sesión])."""
    primera = cartillas[0]
    secciones = [{"titulo": x.titulo, "materia": x.materia, "submateria": x.submateria, "cantidad": x.cantidad}
                 for x in sorted(primera.secciones, key=lambda y: y.orden) if x.cantidad]
    total_primera = sum(x["cantidad"] for x in secciones)

    doc = Document(str(BASE_DOCX))                      # el cuadernillo siempre abre con portada entera
    generador._configurar_pagina(doc, media=False)
    generador._armar_portada(doc, s, primera, secciones, total_primera)
    if primera.imagen:
        generador.cambiar_ilustracion(doc, primera.imagen)
    sect_cuerpo, sect_portada = _secciones_de(doc)

    cop = Copiadora(doc)
    claves_por_sesion = [generador._armar_cuerpo(doc, s, primera, cop)[0]]

    # el ancla de las demás sesiones es el recuadro del QR: todo lo nuevo entra justo antes del cierre
    ancla = next((p for p in doc.element.body.iter(W + "p") if "ESCANEA Y APRENDE" in texto_de(p)), None)
    if ancla is None:
        raise ErrorGeneracion("La plantilla de la cartilla no tiene el recuadro del código QR.")

    # Las secciones quedan así, y cada «type» describe cómo empieza SU sección:
    #   portada entera · cuerpo 1 (nextPage) · media portada 2 (oddPage) · cuerpo 2 (continuous) · …
    primera_vez = True
    for c in cartillas[1:]:
        total = sum(x.cantidad for x in c.secciones if x.cantidad)
        # cierra el cuerpo de la sesión anterior: el primero empezó tras la portada entera, los demás
        # vienen pegados bajo su media portada
        ancla.addprevious(_corte(sect_cuerpo, "nextPage" if primera_vez else "continuous", 2))
        for el in _media_portada_en(doc, s, c, total):
            ancla.addprevious(el)
        ancla.addprevious(_corte(sect_portada, "oddPage", 1))      # la media portada abre en hoja derecha
        claves_por_sesion.append(generador._armar_cuerpo(doc, s, c, cop, ancla=ancla)[0])
        primera_vez = False
    # el cuerpo de la última sesión lo cierra la sección que ya traía la plantilla
    _poner_tipo(sect_cuerpo, "continuous")

    generador.numerar_dibujos(doc)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue(), claves_por_sesion


# ====================================================================== verificación
def _verificar(doc_bytes, cartillas, claves_por_sesion, s):
    """Que el Word impreso diga lo mismo que las claves: numeración por sesión, opciones y letras."""
    leidas = generador._leer_cartilla_generada(doc_bytes)
    esperadas = [k for claves in claves_por_sesion for k in claves]
    fallas = []
    if len(leidas) != len(esperadas):
        return [f"El cuadernillo tiene {len(leidas)} preguntas y las cartillas suman {len(esperadas)}."]
    i = 0
    for c, claves in zip(cartillas, claves_por_sesion):
        secuencia = generador._plantilla(s, c.plantilla)
        for k in claves:
            leida = leidas[i]
            i += 1
            if leida["numero"] != k["posicion"]:
                fallas.append(f"En {c.codigo}, la pregunta {k['posicion']} quedó numerada como {leida['numero']}.")
            if leida["opciones"][:4] != list("ABCD"):
                fallas.append(f"En {c.codigo}, la pregunta {k['posicion']} no tiene A, B, C y D en orden.")
            if k["letra"] != secuencia[k["posicion"] - 1]:
                fallas.append(f"En {c.codigo}, la clave de la pregunta {k['posicion']} no coincide con la plantilla.")
    return fallas


# ====================================================================== entrada
def _traer(s, ids):
    if len(ids) < MINIMO:
        raise ErrorGeneracion(f"Un cuadernillo necesita al menos {MINIMO} sesiones.")
    if len(ids) > MAXIMO:
        raise ErrorGeneracion(f"Un cuadernillo admite como máximo {MAXIMO} sesiones.")
    if len(set(ids)) != len(ids):
        raise ErrorGeneracion("Hay una cartilla repetida: cada sesión tiene que ser una cartilla distinta.")
    cartillas = []
    for cid in ids:
        c = s.get(Cartilla, cid)
        if c is None:
            raise ErrorGeneracion("Una de las cartillas elegidas ya no existe.")
        if c.estado != "generada":
            raise ErrorGeneracion(f"La cartilla {c.codigo} todavía no se ha generado. Genérala antes de "
                                  "juntarla, para que sus claves y su Excel queden fijados.")
        cartillas.append(c)
    grados = {c.grado for c in cartillas}
    if len(grados) > 1:
        raise ErrorGeneracion("Las sesiones de un cuadernillo tienen que ser del mismo grado.")
    return cartillas


def previo(ids):
    """Qué llevaría el cuadernillo, sin armarlo: para enseñarlo antes de generar."""
    with Sesion() as s:
        cartillas = _traer(s, ids)
        return {"sesiones": [{"codigo": c.codigo, "nombre": c.nombre, "preguntas": len(c.items),
                              "paginas": c.paginas, "portada": "completa" if i == 0 else "media"}
                             for i, c in enumerate(cartillas)],
                "preguntas": sum(len(c.items) for c in cartillas),
                "nombre": nombre_sugerido(cartillas)}


def nombre_sugerido(cartillas):
    return f"{cartillas[0].codigo} y {len(cartillas) - 1} sesión más" if len(cartillas) == 2 else \
        f"{cartillas[0].codigo} y {len(cartillas) - 1} sesiones más"


def _excel_de(s, c):
    """El Excel de claves que ya tiene guardado esa sesión, tal cual se generó."""
    a = s.scalar(select(CartillaArchivo).where(CartillaArchivo.cartilla_id == c.id,
                                               CartillaArchivo.tipo == "xlsx"))
    if a is None:
        raise ErrorGeneracion(f"La cartilla {c.codigo} no tiene su Excel de claves guardado: genérala de nuevo.")
    return a.nombre, a.datos


def generar(ids, nombre_archivo=None):
    """Arma el cuadernillo y lo devuelve en un ZIP: el Word para imprimir y un Excel por sesión.

    Los Excel no se juntan —cada sesión se califica con su propia hoja de respuestas y el lector OMR
    necesita el código de esa sesión—, pero sí viajan con el Word, que es lo que se va a usar el mismo día.
    """
    with Sesion() as s:
        cartillas = _traer(s, ids)
        datos, claves = _construir(s, cartillas)
        fallas = _verificar(datos, cartillas, claves, s)
        if fallas:
            raise ErrorGeneracion("La verificación falló, no se generó nada: " + " · ".join(fallas))
        nombre = (nombre_archivo or nombre_sugerido(cartillas)).strip()
        if not nombre or re.search(r'[\\/:*?"<>|]', nombre):
            raise ErrorGeneracion('El nombre del archivo no puede ir vacío ni llevar estos caracteres: '
                                  '\\ / : * ? " < > |')
        excels = [_excel_de(s, c) for c in cartillas]
        n = paginas.contar(datos)

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr(f"{nombre}.docx", datos)
            for i, (nombre_xlsx, bytes_xlsx) in enumerate(excels, 1):
                # el número de sesión delante: así se ve de un vistazo cuál va en la mañana y cuál en la tarde
                z.writestr(f"Sesion {i} - {nombre_xlsx}", bytes_xlsx)
        return {"nombre": f"{nombre}.zip", "datos": buf.getvalue(), "paginas": n,
                "faltan_paginas": paginas.faltan_para_multiplo(n),
                "archivos": [f"{nombre}.docx"] + [f"Sesion {i} - {x[0]}" for i, x in enumerate(excels, 1)],
                "sesiones": [{"codigo": c.codigo, "nombre": c.nombre, "preguntas": len(k)}
                             for c, k in zip(cartillas, claves)]}
