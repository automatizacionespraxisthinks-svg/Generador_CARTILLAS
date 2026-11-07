"""Pruebas del validador: los ejemplos oficiales pasan y cada daño se detecta por su regla."""
import copy
import io
from pathlib import Path

import pytest
from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from PIL import Image

from app.validador import ACEPTADO, PENDIENTE, RECHAZADO, CatalogoValidacion, validar

RAIZ = Path(__file__).resolve().parent.parent
EJ = RAIZ / "plantillas" / "ejemplos"
SUELTO = EJ / "EJEMPLO_1_EJERCICIO_SUELTO.docx"
BLOQUE = EJ / "EJEMPLO_2_BLOQUE_LECTURA.docx"
PARTE = EJ / "EJEMPLO_3_PARTE_INGLES_COMPLETAR_TEXTO.docx"


# ------------------------------------------------------------------ utilidades
def bytes_de(doc):
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def validar_doc(doc, catalogo=None):
    return validar(bytes_de(doc), "prueba.docx", catalogo)


def reglas(r):
    return {m.regla for m in r.errores}


def parrafo_con(doc, inicio):
    return next(p for p in doc.paragraphs if p.text.startswith(inicio))


def poner_texto(p, texto):
    """Reemplaza el texto conservando el formato del primer run."""
    runs = p.runs
    runs[0].text = texto
    for r in runs[1:]:
        r._r.getparent().remove(r._r)


def tabla_tras(doc, rotulo):
    """La tabla que sigue al rótulo (los ejemplos pueden traer además la TABLA DE GLOSARIO)."""
    from docx.table import Table
    hijos = list(doc.element.body)
    i = next(k for k, h in enumerate(hijos) if h.tag == qn("w:p") and "".join(t.text or "" for t in h.iter(qn("w:t"))).strip() == rotulo)
    return Table(next(h for h in hijos[i + 1:] if h.tag == qn("w:tbl")), doc._body)


def tabla_excel(doc):
    return tabla_tras(doc, "TABLA DE EXCEL")


def tabla_resp(doc):
    return tabla_tras(doc, "TABLA DE RESPUESTAS")


def celda(t, fila, col, texto):
    p = t.cell(fila, col).paragraphs[0]
    if p.runs:
        poner_texto(p, texto)
    else:
        r = p.add_run(texto)
        r.font.name = "Tahoma"
        r.font.size = Pt(8)


def png(ruta, ancho_px, color=False, alfa=False):
    modo = "RGBA" if alfa else ("RGB" if color else "L")
    fondo = (255, 255, 255, 0) if alfa else ((255, 255, 255) if color else 255)
    im = Image.new(modo, (ancho_px, ancho_px // 2), fondo)
    if color:
        im.putpixel((5, 5), (200, 30, 30) if not alfa else (200, 30, 30, 255))
    im.save(ruta)
    return ruta


def insertar_imagen(doc, ruta, ancho_cm, antes_de="¿Cuánto dinero"):
    ref = parrafo_con(doc, antes_de)
    p = ref.insert_paragraph_before()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(str(ruta), width=Cm(ancho_cm))
    return p


# ------------------------------------------------------------------ los ejemplos pasan
@pytest.mark.parametrize("ruta,tipo,n", [(SUELTO, "suelto", 1), (BLOQUE, "bloque", 3), (PARTE, "parte", 5)])
def test_ejemplos_aceptados(ruta, tipo, n):
    r = validar(ruta.read_bytes(), ruta.name)
    assert r.estado == ACEPTADO, [(m.regla, m.donde, m.mensaje) for m in r.errores]
    assert r.tipo == tipo and r.preguntas == n
    assert len(r.filas) == n


def test_plantillas_vacias_rechazadas():
    rutas = sorted((RAIZ / "plantillas").glob("PLANTILLA_CARGA_*_v1.2.docx"))
    assert len(rutas) == 3
    for ruta in rutas:
        r = validar(ruta.read_bytes(), ruta.name)
        assert r.estado == RECHAZADO
        assert 20 in reglas(r)          # corchetes y texto gris


def test_archivo_que_no_es_word():
    r = validar(b"esto no es un docx", "x.docx")
    assert r.estado == RECHAZADO and reglas(r) == {0}


# ------------------------------------------------------------------ estructura
def test_falta_tabla_de_excel():
    doc = Document(SUELTO)
    poner_texto(parrafo_con(doc, "TABLA DE EXCEL"), "Tabla de excel")
    r = validar_doc(doc)
    assert 1 in reglas(r)


def test_encabezado_excel_incorrecto():
    doc = Document(SUELTO)
    celda(tabla_excel(doc), 0, 2, "Curso")
    assert 2 in reglas(validar_doc(doc))


def test_falta_una_opcion():
    doc = Document(SUELTO)
    p = parrafo_con(doc, "D. ")
    p._p.getparent().remove(p._p)
    r = validar_doc(doc)
    assert 5 in reglas(r)


def test_opcion_en_dos_parrafos():
    doc = Document(SUELTO)
    parrafo_con(doc, "C. ").insert_paragraph_before("continuación de la opción B")
    assert 5 in reglas(validar_doc(doc))


def test_letra_de_opcion_sin_negrita():
    doc = Document(SUELTO)
    parrafo_con(doc, "B. ").runs[0].bold = False
    assert 5 in reglas(validar_doc(doc))


def test_bloque_sin_linea_de_credito():
    doc = Document(BLOQUE)
    parrafo_con(doc, "Texto elaborado").alignment = WD_ALIGN_PARAGRAPH.LEFT
    assert 7 in reglas(validar_doc(doc))


def test_frase_de_referencia_con_numeros():
    doc = Document(BLOQUE)
    poner_texto(doc.paragraphs[0], "Responde las preguntas 5 a 7 de acuerdo con la siguiente lectura.")
    assert 6 in reglas(validar_doc(doc))


def test_bloque_con_una_sola_pregunta():
    doc = Document(BLOQUE)
    cuerpo = doc.element.body
    # quita las preguntas 2 y 3 (8 párrafos) y sus filas en las dos tablas
    inicio = next(i for i, p in enumerate(doc.paragraphs) if p.text.startswith("¿Qué recurso"))
    for p in doc.paragraphs[inicio:inicio + 10]:
        cuerpo.remove(p._p)
    for t in (tabla_resp(doc), tabla_excel(doc)):
        for fila in t.rows[2:]:
            t._tbl.remove(fila._tr)
    assert 7 in reglas(validar_doc(doc))


# ------------------------------------------------------------------ datos
def test_clave_y_correcta_no_coinciden():
    doc = Document(SUELTO)
    celda(tabla_excel(doc), 1, 1, "A")
    assert 9 in reglas(validar_doc(doc))


def test_numero_en_columna_preg():
    doc = Document(SUELTO)
    celda(tabla_excel(doc), 1, 0, "12")
    assert 4 in reglas(validar_doc(doc))


@pytest.mark.parametrize("col,valor", [(2, ""), (2, "7"), (3, "Matemática"), (4, "Física"), (8, ""), (9, "Alto"), (7, "DBA tres")])
def test_datos_invalidos(col, valor):
    doc = Document(SUELTO)
    celda(tabla_excel(doc), 1, col, valor)
    assert 10 in reglas(validar_doc(doc))


def test_icfes_sin_nivel_y_matematicas_sin_submateria():
    doc = Document(SUELTO)
    t = tabla_excel(doc)
    celda(t, 1, 2, "ICFES")
    celda(t, 1, 4, "")
    celda(t, 1, 9, "")
    r = validar_doc(doc)
    assert r.estado == ACEPTADO, [(m.regla, m.mensaje) for m in r.errores]
    assert r.filas[0]["grado"] == "13"


def test_icfes_con_nivel_rechazado():
    doc = Document(SUELTO)
    celda(tabla_excel(doc), 1, 2, "ICFES")
    assert 10 in reglas(validar_doc(doc))


def test_normalizacion_de_valores():
    doc = Document(SUELTO)
    t = tabla_excel(doc)
    celda(t, 1, 7, "DBA03")
    celda(t, 1, 8, "● Operaciones con números naturales.")
    r = validar_doc(doc)
    assert r.estado == ACEPTADO
    assert r.filas[0]["dba"] == "DBA 3"
    assert r.filas[0]["tematica"] == "Operaciones con números naturales"


def test_varios_dba():
    doc = Document(SUELTO)
    celda(tabla_excel(doc), 1, 7, "DBA 3, DBA 05")
    r = validar_doc(doc)
    assert r.filas[0]["dba"] == "DBA 3, DBA 5"


def test_bloque_con_grados_distintos():
    doc = Document(BLOQUE)
    celda(tabla_excel(doc), 2, 2, "8°")
    assert 11 in reglas(validar_doc(doc))


def test_tematica_parecida_queda_pendiente():
    """Pocas letras de diferencia: parece un error de escritura y se pregunta."""
    cat = CatalogoValidacion.de_fabrica(registrados={"Temática": ["Operaciones con números naturals"]})
    r = validar(SUELTO.read_bytes(), "x.docx", cat)
    assert r.estado == PENDIENTE
    assert r.similitudes[0].parecido_a == "Operaciones con números naturals"


def test_tematica_identica_no_pregunta():
    cat = CatalogoValidacion.de_fabrica(registrados={"Temática": ["Operaciones con números naturales"]})
    assert validar(SUELTO.read_bytes(), "x.docx", cat).estado == ACEPTADO


def test_tematica_con_otras_tildes_adopta_la_registrada():
    """Mismo valor escrito de otra forma: se guarda con la escritura ya registrada, sin preguntar."""
    cat = CatalogoValidacion.de_fabrica(registrados={"Temática": ["operaciones con numeros naturales"]})
    r = validar(SUELTO.read_bytes(), "x.docx", cat)
    assert r.estado == ACEPTADO
    assert r.filas[0]["tematica"] == "operaciones con numeros naturales"


# ------------------------------------------------------------------ contenido
def test_numero_de_pregunta_a_mano():
    doc = Document(SUELTO)
    p = doc.paragraphs[0]
    p.runs[0].text = "12. " + p.runs[0].text
    assert 12 in reglas(validar_doc(doc))


def test_pregunta_sin_signo_de_interrogacion():
    doc = Document(SUELTO)
    poner_texto(parrafo_con(doc, "¿Cuánto dinero"), "Calcula el dinero que recibe de cambio.")
    assert 13 in reglas(validar_doc(doc))


@pytest.mark.parametrize("texto,regla", [
    ("Con los datos de la pregunta 12, Camila compra dos jugos y una empanada.", 14),
    ("Según la pregunta anterior, Camila compra dos jugos y una empanada.", 14),
    ("Según la tabla de arriba, Camila compra dos jugos y una empanada.", 15),
    ("NOTA: revisar precios. Camila compra dos jugos y una empanada.", 20),
    ("Camila compra [escribe aquí la cantidad] jugos y una empanada.", 20),
])
def test_textos_prohibidos(texto, regla):
    doc = Document(SUELTO)
    poner_texto(parrafo_con(doc, "Camila compra"), texto)
    assert regla in reglas(validar_doc(doc))


def test_pendiente_de_una_recta_no_es_texto_de_trabajo():
    doc = Document(SUELTO)
    poner_texto(parrafo_con(doc, "Camila compra"), "La pendiente de la recta es positiva y hay que revisar el cambio.")
    assert 20 not in reglas(validar_doc(doc))


@pytest.mark.parametrize("opcion", [
    "Todas las anteriores", "A y B son correctas", "Ninguna de las anteriores",
    "Las anteriores", "La anterior", "Las dos anteriores", "Ninguna de las opciones anteriores",
    "Ninguna es correcta", "Todas son correctas", "A y C", "A, B y C",
    "La primera opción del listado", "Lo mismo que la respuesta anterior", "Las opciones A y C son correctas",
])
def test_opciones_prohibidas(opcion):
    doc = Document(SUELTO)
    p = parrafo_con(doc, "D. ")
    p.runs[-1].text = opcion
    assert 16 in reglas(validar_doc(doc)), opcion


@pytest.mark.parametrize("opcion", [
    # habla del contenido, no de las otras opciones (ejercicio real de la pirámide de energía)
    "Tendría más energía disponible que la culebra, porque cada nivel concentra la energía de los anteriores.",
    "El resultado es mayor que el de los anteriores ejercicios del taller.",
    "La primera ley de Newton explica el reposo del cuerpo.",
    "El jugo aporta las vitaminas A y B necesarias.",
    "La anterior crecida del río dejó sedimentos en la orilla.",
])
def test_opciones_que_hablan_del_contenido(opcion):
    doc = Document(SUELTO)
    p = parrafo_con(doc, "D. ")
    p.runs[-1].text = opcion
    assert 16 not in reglas(validar_doc(doc)), opcion


@pytest.mark.parametrize("just", ["La B es correcta porque suma bien.", "La opción C es la correcta.", "Por eso C) es la respuesta."])
def test_justificacion_con_letra(just):
    doc = Document(SUELTO)
    celda(tabla_resp(doc), 1, 2, just)
    assert 17 in reglas(validar_doc(doc))


def test_superindice_sin_formato_en_matematicas():
    doc = Document(SUELTO)
    poner_texto(parrafo_con(doc, "Camila compra"), "Si x2 = 49, Camila compra dos jugos y una empanada.")
    assert 18 in reglas(validar_doc(doc))


def test_superindice_con_formato_pasa():
    doc = Document(SUELTO)
    p = parrafo_con(doc, "Camila compra")
    poner_texto(p, "Si x")
    r2 = p.add_run("2")
    r2.font.superscript = True
    r3 = p.add_run(" = 49, Camila compra dos jugos.")
    for r in (r2, r3):
        r.font.name, r.font.size = "Tahoma", Pt(9)
    assert 18 not in reglas(validar_doc(doc))


def test_excepcion_de_superindice():
    doc = Document(SUELTO)
    poner_texto(parrafo_con(doc, "Camila compra"), "Camila toma vitamina B12 y compra dos jugos.")
    assert 18 not in reglas(validar_doc(doc))


def test_superindice_no_aplica_en_lengua():
    doc = Document(BLOQUE)
    poner_texto(parrafo_con(doc, "Nunca supe"), "El grupo G7 y el MP5 aparecen en la historia.")
    assert 18 not in reglas(validar_doc(doc))


@pytest.mark.parametrize("barra", ["/", "⁄", "∕"])
def test_la_fraccion_a_tamano_normal_se_acepta(barra):
    """«3/4» a tamaño normal se lee grande y claro: se acepta, con cualquiera de las tres barras de Word."""
    doc = Document(SUELTO)
    p = parrafo_con(doc, "B. ")
    p.runs[-1].text = f"3{barra}4"
    assert 18 not in reglas(validar_doc(doc))


@pytest.mark.parametrize("arriba,abajo", [(True, False), (False, True)])
def test_la_fraccion_en_superindice_o_subindice_se_rechaza(arriba, abajo):
    """³/₄ se imprime diminuta y cuesta leerla; es el formato que la v1.2 pedía y que se revocó."""
    doc = Document(SUELTO)
    p = parrafo_con(doc, "B. ")
    p.runs[-1].text = ""
    for texto, sup, sub in (("3", arriba, abajo), ("/", False, False), ("4", False, False)):
        r = p.add_run(texto)
        r.font.superscript, r.font.subscript = sup, sub
        r.font.name, r.font.size = "Tahoma", Pt(9)
    assert 18 in reglas(validar_doc(doc))


def test_la_raiz_escrita_como_caracter_se_rechaza():
    doc = Document(SUELTO)
    poner_texto(parrafo_con(doc, "Camila compra"), "Camila calcula √49 y compra dos jugos.")
    assert 18 in reglas(validar_doc(doc))


@pytest.mark.parametrize("texto", ["Camila eleva x^2 y compra jugos.", "Camila calcula 2**3 y compra jugos."])
def test_la_potencia_con_simbolos_se_rechaza(texto):
    doc = Document(SUELTO)
    poner_texto(parrafo_con(doc, "Camila compra"), texto)
    assert 18 in reglas(validar_doc(doc))


def test_la_ecuacion_de_word_es_la_forma_correcta():
    """Una fracción hecha con el editor de ecuaciones no lleva barra en el texto: pasa sin tocarla."""
    from lxml import etree

    from app.validador.docx_lector import NS

    M = "http://schemas.openxmlformats.org/officeDocument/2006/math"
    tres_cuartos = (f'<m:oMath xmlns:m="{M}" xmlns:w="{NS["w"]}"><m:f>'
                    '<m:num><m:r><m:t>3</m:t></m:r></m:num>'
                    '<m:den><m:r><m:t>4</m:t></m:r></m:den></m:f></m:oMath>')
    doc = Document(SUELTO)
    p = parrafo_con(doc, "B. ")
    p.runs[-1].text = ""
    p._p.append(etree.fromstring(tres_cuartos))
    assert 18 not in reglas(validar_doc(doc))


def test_marcadores_de_completar_texto_desordenados():
    doc = Document(PARTE)
    p = parrafo_con(doc, "Last Saturday")
    poner_texto(p, p.text.replace("(#2)", "(#9)"))
    assert 19 in reglas(validar_doc(doc))


# ------------------------------------------------------------------ formato
def test_orientacion_horizontal():
    doc = Document(SUELTO)
    s = doc.sections[0]
    s.orientation = WD_ORIENT.LANDSCAPE
    assert 21 in reglas(validar_doc(doc))


def test_margenes_normales():
    doc = Document(SUELTO)
    doc.sections[0].left_margin = Cm(2.5)
    assert 21 in reglas(validar_doc(doc))


def test_fuente_arial():
    doc = Document(SUELTO)
    parrafo_con(doc, "Camila compra").runs[0].font.name = "Arial"
    assert 22 in reglas(validar_doc(doc))


def test_tamano_10_pt():
    doc = Document(SUELTO)
    parrafo_con(doc, "Camila compra").runs[0].font.size = Pt(10)
    assert 23 in reglas(validar_doc(doc))


def test_el_texto_de_color_se_admite():
    """Desde el 07/11/2026 hay ejercicios que necesitan color, y esas cartillas se imprimen a color."""
    doc = Document(SUELTO)
    parrafo_con(doc, "Camila compra").runs[0].font.color.rgb = RGBColor(0xC0, 0x00, 0x00)
    assert 20 not in reglas(validar_doc(doc))


def test_el_texto_casi_blanco_se_sigue_rechazando():
    """Sobre el papel no se vería: es un error de quien lo escribió, no una decisión de diseño."""
    doc = Document(SUELTO)
    parrafo_con(doc, "Camila compra").runs[0].font.color.rgb = RGBColor(0xFA, 0xFA, 0xFA)
    assert 20 in reglas(validar_doc(doc))


def test_el_resaltado_sigue_prohibido():
    """Resaltar es una marca de trabajo, no contenido: en la cartilla impresa no pinta nada."""
    doc = Document(SUELTO)
    parrafo_con(doc, "Camila compra").runs[0].font.highlight_color = WD_COLOR_INDEX.YELLOW
    assert 20 in reglas(validar_doc(doc))


def test_numeracion_automatica():
    doc = Document(SUELTO)
    parrafo_con(doc, "Camila compra").style = doc.styles["List Number"]
    assert 27 in reglas(validar_doc(doc))


def test_control_de_cambios():
    doc = Document(SUELTO)
    p = parrafo_con(doc, "Camila compra")
    ins = OxmlElement("w:ins")
    ins.set(qn("w:id"), "1")
    ins.set(qn("w:author"), "x")
    run = copy.deepcopy(p.runs[0]._r)
    ins.append(run)
    p._p.append(ins)
    assert 20 in reglas(validar_doc(doc))


def test_imagen_correcta(tmp_path):
    doc = Document(SUELTO)
    insertar_imagen(doc, png(tmp_path / "g.png", 900), 7.5)
    r = validar_doc(doc)
    assert r.estado == ACEPTADO, [(m.regla, m.mensaje) for m in r.errores]


@pytest.mark.parametrize("ancho_px,ancho_cm,color,alfa", [
    (1100, 9.0, False, False),     # más de 8,4 cm
    (400, 7.5, False, False),      # menos de 300 ppp
    (900, 7.5, True, True),        # tiene transparencia
])
def test_imagenes_rechazadas(tmp_path, ancho_px, ancho_cm, color, alfa):
    doc = Document(SUELTO)
    insertar_imagen(doc, png(tmp_path / "g.png", ancho_px, color, alfa), ancho_cm)
    assert 25 in reglas(validar_doc(doc))


def test_imagen_jpg(tmp_path):
    ruta = tmp_path / "g.jpg"
    Image.new("L", (900, 400), 255).save(ruta)
    doc = Document(SUELTO)
    insertar_imagen(doc, ruta, 7.5)
    assert 25 in reglas(validar_doc(doc))


def test_imagen_cerca_del_limite_solo_informa(tmp_path):
    doc = Document(SUELTO)
    insertar_imagen(doc, png(tmp_path / "g.png", 1000), 8.2)
    r = validar_doc(doc)
    assert r.estado == ACEPTADO and r.avisos


def test_tabla_de_cinco_columnas():
    doc = Document(SUELTO)
    t = doc.tables[0]
    for fila in t.rows:
        for _ in range(3):
            fila._tr.append(copy.deepcopy(fila.cells[-1]._tc))
    grid = t._tbl.tblGrid
    for _ in range(3):
        grid.append(copy.deepcopy(grid[-1]))
    assert 26 in reglas(validar_doc(doc))


def test_encabezado_de_tabla_sin_negrita_se_rechaza():
    doc = Document(SUELTO)
    for celda_ in doc.tables[0].rows[0].cells:
        for parrafo in celda_.paragraphs:
            for run in parrafo.runs:
                run.bold = False
    assert 26 in reglas(validar_doc(doc))


def test_encabezado_de_tabla_sin_centrar_pasa():
    """El autor marca el encabezado con la negrita; el centrado lo pone el sistema al armar la cartilla."""
    doc = Document(SUELTO)
    for celda_ in doc.tables[0].rows[0].cells:
        for parrafo in celda_.paragraphs:
            parrafo.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r = validar_doc(doc)
    assert r.estado == ACEPTADO, [(m.regla, m.mensaje) for m in r.errores]


def test_tabla_sin_no_dividir_fila():
    doc = Document(SUELTO)
    tr = doc.tables[0].rows[1]._tr
    trpr = tr.trPr
    trpr.remove(trpr.find(qn("w:cantSplit")))
    assert 26 in reglas(validar_doc(doc))


@pytest.mark.parametrize("texto", ["El terreno mide 144 m² de área y Camila compra.", "Camila gasta ⁵/₆ de su dinero en jugos."])
def test_caracteres_unicode_de_superindice_son_validos(texto):
    doc = Document(SUELTO)
    poner_texto(parrafo_con(doc, "Camila compra"), texto)
    assert 18 not in reglas(validar_doc(doc))



# ------------------------------------------------------------------ hallazgos de la auditoría independiente
def test_formato_strict_se_rechaza_sin_caerse():
    import zipfile
    buf = io.BytesIO()
    with zipfile.ZipFile(SUELTO) as z, zipfile.ZipFile(buf, "w") as out:
        for n in z.namelist():
            datos = z.read(n)
            if n == "word/document.xml":
                datos = datos.replace(b"http://schemas.openxmlformats.org/wordprocessingml/2006/main",
                                      b"http://purl.oclc.org/ooxml/wordprocessingml/main")
            out.writestr(n, datos)
    r = validar(buf.getvalue(), "strict.docx")
    assert r.estado == RECHAZADO and reglas(r) == {0} and "strict" in r.errores[0].mensaje


def _envolver_en_sdt(el):
    sdt, cont = OxmlElement("w:sdt"), OxmlElement("w:sdtContent")
    el.addprevious(sdt)
    sdt.append(OxmlElement("w:sdtPr"))
    sdt.append(cont)
    cont.append(el)


def test_control_de_contenido_en_celda_de_tabla_de_control():
    doc = Document(SUELTO)
    _envolver_en_sdt(tabla_resp(doc).rows[1].cells[1]._tc)
    _envolver_en_sdt(tabla_excel(doc).rows[1]._tr)
    r = validar_doc(doc)
    assert r.estado == ACEPTADO, [(m.regla, m.mensaje) for m in r.errores]


def test_control_de_contenido_en_tabla_del_enunciado_no_esconde_errores():
    doc = Document(SUELTO)
    p = doc.tables[0].rows[1].cells[0].paragraphs[0]
    p.runs[0].font.name = "Comic Sans MS"
    _envolver_en_sdt(p._p)
    assert 22 in reglas(validar_doc(doc))


def test_suelto_que_empieza_por_parte():
    doc = Document(SUELTO)
    poner_texto(doc.paragraphs[0], "Parte del dinero se gasta en la tienda escolar, donde hay estos precios.")
    r = validar_doc(doc)
    assert r.estado == ACEPTADO and r.tipo == "suelto", [(m.regla, m.mensaje) for m in r.errores]


def test_completar_texto_sin_credito_con_marcadores():
    doc = Document(PARTE)
    parrafo_con(doc, "Texto elaborado").alignment = WD_ALIGN_PARAGRAPH.LEFT
    assert 19 in reglas(validar_doc(doc))


def test_el_color_de_tema_tambien_se_admite():
    doc = Document(SUELTO)
    r = parrafo_con(doc, "Camila compra").runs[0]
    c = OxmlElement("w:color")
    c.set(qn("w:val"), "808080")
    c.set(qn("w:themeColor"), "text1")
    c.set(qn("w:themeTint"), "7F")
    r._r.get_or_add_rPr().append(c)
    assert 20 not in reglas(validar_doc(doc))


def test_negrita_alternante_entre_estilo_de_parrafo_y_de_caracter():
    from docx.enum.style import WD_STYLE_TYPE
    doc = Document(SUELTO)
    ep = doc.styles.add_style("ParrafoNegrita", WD_STYLE_TYPE.PARAGRAPH)
    ep.font.bold = True
    ec = doc.styles.add_style("CaracterNegrita", WD_STYLE_TYPE.CHARACTER)
    ec.font.bold = True
    p = parrafo_con(doc, "B. ")
    p.style = ep
    for run in p.runs:
        run.bold = None
        run.style = ec
    # negrita en el estilo de párrafo y en el de carácter se anulan: la letra B queda sin negrita
    assert 5 in reglas(validar_doc(doc))


@pytest.mark.parametrize("texto", ["Camila necesita una nota para aprobar y compra dos jugos.",
                                   "¿Qué no debe aparecer en la lista? Camila compra dos jugos."])
def test_frases_comunes_en_minuscula_no_se_rechazan(texto):
    doc = Document(SUELTO)
    poner_texto(parrafo_con(doc, "Camila compra"), texto)
    assert 20 not in reglas(validar_doc(doc))


@pytest.mark.parametrize("just", ["El jugo es rico en vitamina C) y se suma.", "Se suman los precios (tipo B) y se resta del billete.",
                                  "La probabilidad P(A ∩ B) se calcula con el total.", "El C es el símbolo del carbono."])
def test_justificaciones_legitimas_con_letras(just):
    doc = Document(SUELTO)
    celda(tabla_resp(doc), 1, 2, just.replace("vitamina C)", "(vitamina C)"))
    assert 17 not in reglas(validar_doc(doc))


@pytest.mark.parametrize("dba", ["DBA 2.", "● DBA 2"])
def test_dba_con_punto_o_vineta(dba):
    doc = Document(SUELTO)
    celda(tabla_excel(doc), 1, 7, dba)
    r = validar_doc(doc)
    assert r.estado == ACEPTADO and r.filas[0]["dba"] == "DBA 2"


def test_recorte_de_imagen_cuenta_en_los_ppp(tmp_path):
    doc = Document(SUELTO)
    p = insertar_imagen(doc, png(tmp_path / "g.png", 1200), 8.0)
    pic = p._p.find(".//" + qn("pic:blipFill"))
    rect = OxmlElement("a:srcRect")
    rect.set("l", "35000")
    rect.set("r", "35000")
    pic.find(qn("a:blip")).addnext(rect)
    assert 25 in reglas(validar_doc(doc))


def test_intervalo_entre_corchetes_es_valido():
    doc = Document(SUELTO)
    poner_texto(parrafo_con(doc, "Camila compra"), "El precio está en el intervalo [2000, 3000] y Camila compra dos jugos.")
    assert 20 not in reglas(validar_doc(doc))


def test_opcion_con_primera_ley_es_valida():
    doc = Document(SUELTO)
    parrafo_con(doc, "D. ").runs[-1].text = "La primera ley de Newton"
    assert 16 not in reglas(validar_doc(doc))


def test_ingles_suelto_sin_signo_de_interrogacion():
    doc = Document(SUELTO)
    poner_texto(parrafo_con(doc, "¿Cuánto dinero"), "Choose the word: Camila ___ two juices.")
    t = tabla_excel(doc)
    celda(t, 1, 3, "Inglés")
    celda(t, 1, 4, "")
    assert 13 not in reglas(validar_doc(doc))


def test_resta_al_inicio_no_es_numero_de_pregunta():
    doc = Document(SUELTO)
    poner_texto(doc.paragraphs[0], "10 - 3 = 7 es una resta. La tabla muestra algunos precios.")
    assert 12 not in reglas(validar_doc(doc))


@pytest.mark.parametrize("registrada,nueva", [
    ("Ángulos", "Triángulos"),
    ("Ángulos", "Ángulos internos"),                                   # una contiene a la otra: son dos temáticas
    ("Fracciones equivalentes representadas gráficamente", "Fracciones equivalentes"),
    ("Fracciones", "Fracciones heterogéneas"),
])
def test_tematicas_distintas_no_preguntan(registrada, nueva):
    cat = CatalogoValidacion.de_fabrica(registrados={"Temática": [registrada]})
    doc = Document(SUELTO)
    celda(tabla_excel(doc), 1, 8, nueva)
    r = validar_doc(doc, cat)
    assert r.estado == ACEPTADO, [(s.valor, s.parecido_a) for s in r.similitudes]
    assert r.filas[0]["tematica"] == nueva


def test_la_imagen_a_color_se_admite(tmp_path):
    """Mapas, banderas, reacciones químicas: hay ejercicios donde el color es parte de la pregunta."""
    doc = Document(SUELTO)
    insertar_imagen(doc, png(tmp_path / "c.png", 900, color=True), 7.5)
    r = validar_doc(doc)
    assert r.estado == ACEPTADO, [(m.regla, m.mensaje) for m in r.errores]


def test_la_tabla_con_celdas_de_color_se_admite():
    doc = Document(SUELTO)
    t = doc.tables[0]                            # la tabla del enunciado
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:fill"), "FFF2CC")              # amarillo claro
    t.cell(1, 1)._tc.get_or_add_tcPr().append(shd)
    assert 26 not in reglas(validar_doc(doc))


def test_la_celda_casi_negra_se_rechaza():
    """El texto va en negro: sobre un fondo casi negro no se leería."""
    doc = Document(SUELTO)
    t = doc.tables[0]                            # la tabla del enunciado
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:fill"), "1A1A1A")
    t.cell(1, 1)._tc.get_or_add_tcPr().append(shd)
    assert 26 in reglas(validar_doc(doc))
