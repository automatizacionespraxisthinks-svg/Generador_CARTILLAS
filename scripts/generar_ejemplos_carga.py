"""Genera los tres archivos de carga de EJEMPLO, llenos y conformes al Estándar v1.2.

Sirven de modelo para quien normaliza ejercicios y, más adelante, como casos de
prueba del validador (deben ser aceptados sin observaciones).

Uso:  python scripts/generar_ejemplos_carga.py
"""
import re
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

DESTINO = Path(__file__).resolve().parent.parent / "plantillas" / "ejemplos"
CREDITO = "Texto elaborado para este simulacro. PRAXIS · THINKS."
ENC_RESP = ["N°", "Clave", "Justificación de la respuesta correcta"]
ENC_EXCEL = ["Preg.", "Correcta", "Grado", "Materia", "Submateria", "Pensamiento", "Competencia", "DBA", "Temática", "Nivel"]
ENC_GLOSARIO = ["Pregunta", "Término", "Significado"]


def _el(tag, **attrs):
    e = OxmlElement(tag)
    for k, v in attrs.items():
        e.set(qn(k), str(v))
    return e


def nuevo_documento():
    doc = Document()
    st = doc.styles["Normal"]
    st.font.name = "Tahoma"
    st.font.size = Pt(9)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), "Tahoma")
    st.element.rPr.rFonts.set(qn("w:cs"), "Tahoma")
    st.paragraph_format.space_after = Pt(0)
    st.paragraph_format.line_spacing = 1.0
    st.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY      # v1.2: el texto va justificado por defecto
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21.59), Cm(27.94)
    sec.top_margin = sec.bottom_margin = sec.left_margin = sec.right_margin = Cm(1.27)
    return doc


def escribir(p, cadena, size=9, bold=False, italic=False):
    """Texto con marcas: ^{sup} _{sub} ~cursiva~ **negrita**."""
    for trozo in re.split(r"(\^\{[^}]*\}|_\{[^}]*\}|~[^~]*~|\*\*[^*]*\*\*)", cadena):
        if not trozo:
            continue
        run = p.add_run(re.sub(r"^[\^_]\{|\}$|~|\*\*", "", trozo))
        run.font.name = "Tahoma"
        run.font.size = Pt(size)
        run.bold = bold or trozo.startswith("**")
        run.italic = italic or trozo.startswith("~")
        run.font.superscript = trozo.startswith("^{") or None
        run.font.subscript = trozo.startswith("_{") or None
    return p


def parrafo(doc, cadena="", alin=None, **kw):
    p = doc.add_paragraph()
    if alin is not None:
        p.alignment = alin
    if cadena:
        escribir(p, cadena, **kw)
    return p


def opcion(doc, letra, cadena):
    p = doc.add_paragraph()
    escribir(p, f"{letra}. ", bold=True)
    escribir(p, cadena)


def credito(doc):
    parrafo(doc, CREDITO, alin=WD_ALIGN_PARAGRAPH.RIGHT, size=8, italic=True)


def tabla(doc, filas, anchos_cm, size=8, centrar=True):
    t = doc.add_table(rows=len(filas), cols=len(filas[0]))
    t.style = doc.styles["Table Grid"]
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    # bordes negros de 0,5 pt (sz = 4 octavos de punto)
    bordes = _el("w:tblBorders")
    for lado in ("top", "left", "bottom", "right", "insideH", "insideV"):
        bordes.append(_el(f"w:{lado}", **{"w:val": "single", "w:sz": 4, "w:space": 0, "w:color": "000000"}))
    # los bordes van antes de tblLook, como exige el esquema de Word
    look = t._tbl.tblPr.find(qn("w:tblLook"))
    if look is not None:
        look.addprevious(bordes)
    else:
        t._tbl.tblPr.append(bordes)
    # ancho real de la tabla = suma de las columnas
    for col, ancho in zip(t._tbl.tblGrid.findall(qn("w:gridCol")), anchos_cm):
        col.set(qn("w:w"), str(int(round(ancho * 567))))
    for i, fila in enumerate(filas):
        t.rows[i]._tr.get_or_add_trPr().append(_el("w:cantSplit"))
        for j, valor in enumerate(fila):
            celda = t.cell(i, j)
            celda.width = Cm(anchos_cm[j])
            celda._tc.get_or_add_tcPr().append(_el("w:vAlign", **{"w:val": "center"}))
            p = celda.paragraphs[0]
            if centrar or i == 0:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            if valor:
                escribir(p, valor, size=size, bold=(i == 0))
    return t


def tablas_control(doc, filas_resp, filas_excel, glosario=None):
    doc.add_paragraph()
    parrafo(doc, "TABLA DE RESPUESTAS", bold=True)
    tabla(doc, [ENC_RESP] + [["", c, j] for c, j in filas_resp], [1.2, 1.4, 16.4], centrar=False)
    doc.add_paragraph()
    parrafo(doc, "TABLA DE EXCEL", bold=True)
    tabla(doc, [ENC_EXCEL] + [[""] + f for f in filas_excel], [1.2, 1.6, 1.3, 2.2, 2.2, 2.2, 2.6, 1.3, 2.4, 1.6], centrar=False)
    if glosario:          # opcional: solo se imprime si la cartilla marca «Incluir glosario»
        doc.add_paragraph()
        parrafo(doc, "TABLA DE GLOSARIO", bold=True)
        tabla(doc, [ENC_GLOSARIO] + [[str(k), t, s] for k, t, s in glosario], [1.8, 4.0, 13.25], centrar=False)


# --------------------------------------------------------------------- ejemplo 1
def ejemplo_ejercicio():
    doc = nuevo_documento()
    parrafo(doc, "La tabla muestra el precio de algunos productos en una tienda escolar.")
    tabla(doc, [["Producto", "Precio"], ["Jugo", "$2.500"], ["Empanada", "$1.800"], ["Galletas", "$1.200"]], [3.0, 2.4], size=8)
    parrafo(doc, "Camila compra dos jugos y una empanada, y paga con un billete de $10.000.")
    parrafo(doc, "¿Cuánto dinero recibe de cambio?")
    opcion(doc, "A", "$6.800")
    opcion(doc, "B", "$5.700")
    opcion(doc, "C", "$3.200")
    opcion(doc, "D", "$4.300")
    tablas_control(doc,
                   [("C", "Dos jugos cuestan $5.000 y con la empanada el total es $6.800; al restarlo de $10.000 quedan $3.200.")],
                   [["C", "7°", "Matemáticas", "Matemáticas I", "Numérico", "Resolución de problemas", "DBA 2", "Operaciones con números naturales", "Básico"]],
                   glosario=[(1, "cambio", "Dinero que se devuelve cuando se paga con un valor mayor al de la compra.")])
    return doc


# --------------------------------------------------------------------- ejemplo 2
def ejemplo_bloque():
    doc = nuevo_documento()
    parrafo(doc, "Responde las preguntas #N a #M de acuerdo con la siguiente lectura.", bold=True)
    parrafo(doc, "En el pueblo de mi abuela, la luz se iba cada vez que llovía. Entonces alguien encendía una vela, y la casa se llenaba de sombras largas que parecían escuchar. Mi abuela aprovechaba la oscuridad para contar historias: la del río que cambió de lugar una noche, la del gallo que cantaba a medianoche y la de la mujer que tejía mapas con lana de colores.", alin=WD_ALIGN_PARAGRAPH.JUSTIFY)
    parrafo(doc, "Nunca supe cuáles eran ciertas. Con los años entendí que esa no era la pregunta importante. Las historias servían para que el miedo a la tormenta se volviera otra cosa: una reunión, una risa, un secreto compartido.", alin=WD_ALIGN_PARAGRAPH.JUSTIFY)
    credito(doc)
    preguntas = [
        ("¿Qué función cumplían las historias de la abuela según el narrador?",
         ["Enseñar a los niños la historia verdadera del pueblo.", "Transformar el miedo a la tormenta en un momento compartido.", "Explicar por qué se iba la luz cuando llovía.", "Advertir a la familia sobre los peligros del río."]),
        ("¿Qué recurso del lenguaje se usa en la expresión «sombras largas que parecían escuchar»?",
         ["Comparación", "Hipérbole", "Enumeración", "Personificación"]),
        ("¿Qué tipo de narrador tiene el texto?",
         ["Protagonista, que cuenta sus propios recuerdos.", "Omnisciente, que conoce lo que piensan todos.", "Testigo, que no participa en los hechos.", "Colectivo, que habla en nombre del pueblo."]),
    ]
    for enunciado, ops in preguntas:
        parrafo(doc, enunciado)
        for letra, o in zip("ABCD", ops):
            opcion(doc, letra, o)
    base = ["7°", "Lengua Castellana", "Comprensión Lectora", "", ""]
    tablas_control(doc,
                   [("B", "El narrador afirma que las historias convertían el miedo a la tormenta en una reunión y un secreto compartido."),
                    ("D", "Se atribuye a las sombras una acción humana, escuchar."),
                    ("A", "Quien narra habla en primera persona sobre su abuela y sus recuerdos.")],
                   [["B"] + base[:3] + ["", "Comprende el sentido global del texto", "", "Idea global", "Medio"],
                    ["D"] + base[:3] + ["", "Reconoce recursos del lenguaje", "", "Figuras literarias", "Medio"],
                    ["A"] + base[:3] + ["", "Identifica la voz narrativa", "", "Tipos de narrador", "Básico"]],
                   glosario=[(1, "narrador", "Voz que cuenta la historia."),
                             (2, "recurso del lenguaje", "Forma de usar las palabras para lograr un efecto en quien lee.")])
    return doc


# --------------------------------------------------------------------- ejemplo 3
def ejemplo_parte_ingles():
    doc = nuevo_documento()
    parrafo(doc, "PARTE #P · Completar el texto — preguntas #N a #M", bold=True)
    parrafo(doc, "Lee el texto y elige la palabra que completa cada espacio.")
    parrafo(doc, "Last Saturday my family and I (#1) to the lake. We (#2) up very early and took the bus. The weather (#3) sunny and warm. My father (#4) a big fish, and my mother made sandwiches (#5) everybody.", alin=WD_ALIGN_PARAGRAPH.JUSTIFY)
    credito(doc)
    opciones = [["go", "goes", "went", "going"], ["got", "get", "gets", "getting"], ["were", "is", "be", "was"],
                ["catch", "caught", "catches", "catching"], ["for", "at", "in", "on"]]
    claves = ["C", "A", "D", "B", "A"]
    for ops in opciones:
        for letra, o in zip("ABCD", ops):
            opcion(doc, letra, o)
    just = ["El relato ocurre en el pasado y el verbo irregular en pasado es el que corresponde.",
            "La expresión «levantarse» va en pasado simple, igual que el resto del relato.",
            "El sujeto es singular y la acción está en pasado.",
            "El verbo irregular en pasado completa la acción del padre.",
            "La preposición que indica destinatario es la que completa la frase."]
    tablas_control(doc, list(zip(claves, just)),
                   [[c, "7°", "Inglés", "", "", "Lingüística", "DBA 4", "Completar texto", "Medio"] for c in claves])
    return doc


if __name__ == "__main__":
    DESTINO.mkdir(parents=True, exist_ok=True)
    for nombre, fn in [("EJEMPLO_1_EJERCICIO_SUELTO.docx", ejemplo_ejercicio),
                       ("EJEMPLO_2_BLOQUE_LECTURA.docx", ejemplo_bloque),
                       ("EJEMPLO_3_PARTE_INGLES_COMPLETAR_TEXTO.docx", ejemplo_parte_ingles)]:
        fn().save(DESTINO / nombre)
        print("listo:", nombre)
