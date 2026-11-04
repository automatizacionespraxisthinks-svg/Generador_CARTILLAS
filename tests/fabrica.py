"""Fábrica de archivos de carga válidos para las pruebas (ejercicios sueltos y bloques)."""
import io

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

ENC_RESP = ["N°", "Clave", "Justificación de la respuesta correcta"]
ENC_EXCEL = ["Preg.", "Correcta", "Grado", "Materia", "Submateria", "Pensamiento", "Competencia", "DBA", "Temática", "Nivel"]
ENC_GLOSARIO = ["Pregunta", "Término", "Significado"]
CREDITO = "Texto elaborado para este simulacro. PRAXIS · THINKS."


def _doc(normal_justificado=False):
    d = Document()
    st = d.styles["Normal"]
    if normal_justificado:           # como las plantillas v1.2: el texto viene justificado
        st.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    st.font.name = "Tahoma"
    st.font.size = Pt(9)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), "Tahoma")
    st.paragraph_format.space_after = Pt(0)
    sec = d.sections[0]
    sec.page_width, sec.page_height = Cm(21.59), Cm(27.94)
    sec.top_margin = sec.bottom_margin = sec.left_margin = sec.right_margin = Cm(1.27)
    return d


def _texto(p, cadena, **kw):
    r = p.add_run(cadena)
    r.font.name = "Tahoma"
    r.font.size = Pt(kw.get("size", 9))
    r.bold = kw.get("bold", False)
    r.italic = kw.get("italic", False)
    return p


def _tabla(d, filas, anchos_cm=None):
    t = d.add_table(rows=len(filas), cols=len(filas[0]))
    t.style = d.styles["Table Grid"]
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    if anchos_cm:
        for col, ancho in zip(t._tbl.tblGrid.findall(qn("w:gridCol")), anchos_cm):
            col.set(qn("w:w"), str(int(ancho * 567)))
        for fila in t.rows:
            for celda, ancho in zip(fila.cells, anchos_cm):
                celda.width = Cm(ancho)
    for i, fila in enumerate(filas):
        t.rows[i]._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
        for j, valor in enumerate(fila):
            celda = t.cell(i, j)
            v = OxmlElement("w:vAlign")
            v.set(qn("w:val"), "center")
            celda._tc.get_or_add_tcPr().append(v)
            p = celda.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            if valor:
                _texto(p, valor, size=8, bold=(i == 0))
    return t


def imagen_gris(ruta, ancho_px=1000):
    """PNG en escala de grises con resolución suficiente para 8 cm (300 ppp)."""
    from PIL import Image, ImageDraw
    im = Image.new("L", (ancho_px, ancho_px // 2), 255)
    ImageDraw.Draw(im).rectangle((40, 40, ancho_px - 40, ancho_px // 2 - 40), outline=0, width=6)
    im.save(ruta, dpi=(300, 300))
    return ruta


def ejercicio(tema, grado="77", materia="Matemáticas", submateria="Matemáticas I", nivel="Básico",
              competencia="Resolución de problemas", pensamiento="Numérico", dba="DBA 2", clave="A", n=1, bloque=False,
              parte=False, imagen=None, cloze=False, glosario=None, normal_justificado=False, alin_enunciado=None,
              tabla=False, variante=""):
    """Devuelve (nombre, bytes) de un archivo de carga válido: suelto, bloque o parte de Inglés.

    glosario: [(pregunta, término, significado)] para la TABLA DE GLOSARIO.
    alin_enunciado: alineación aplicada a mano al primer párrafo del enunciado de la pregunta 1.
    tabla: una tabla de datos (bordes del estilo «Table Grid») en el enunciado de la pregunta 1.
    variante: texto que cambia el enunciado, para tener dos ejercicios distintos de la misma temática.
    """
    d = _doc(normal_justificado)
    if parte:
        _texto(d.add_paragraph(), f"PARTE #P · {tema} — preguntas #N a #M", bold=True)
        _texto(d.add_paragraph(), "Lee cada descripción y elige la palabra que le corresponde.")
        if cloze:
            espacios = " ".join(f"word (#{k})" for k in range(1, n + 1))
            _texto(d.add_paragraph(), f"Last Saturday my family and I went to the lake: {espacios} end of the text.")
            pc = d.add_paragraph()
            pc.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            _texto(pc, CREDITO, size=8, italic=True)
    if bloque:
        _texto(d.add_paragraph(), "Responde las preguntas #N a #M de acuerdo con la siguiente lectura.", bold=True)
        _texto(d.add_paragraph(), f"Lectura de prueba sobre {tema}. El texto sirve para varias preguntas seguidas.")
        p = d.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        _texto(p, CREDITO, size=8, italic=True)
    for k in range(1, n + 1):
        if cloze:      # en «completar el texto» la pregunta son solo sus cuatro opciones
            for letra, valor in zip("ABCD", ["went", "goes", "going", "gone"]):
                p = d.add_paragraph()
                _texto(p, f"{letra}. ", bold=True)
                _texto(p, valor)
            continue
        pe = _texto(d.add_paragraph(), f"Enunciado {k} de prueba sobre {tema} para el grado {grado}."
                    + (f" Caso {variante}." if variante else ""))
        if alin_enunciado is not None and k == 1:
            pe.alignment = alin_enunciado
        if tabla and k == 1:
            _tabla(d, [["Producto", "Precio"], ["Jugo", "$2.500"], ["Pan", "$1.200"]], anchos_cm=[3.0, 2.4])
        if imagen and k == 1:
            p = d.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.add_run().add_picture(str(imagen), width=Cm(7.5))
        _texto(d.add_paragraph(), f"¿Cuál es la respuesta correcta de {tema} número {k}?")
        for letra, valor in zip("ABCD", ["primera", "segunda", "tercera", "cuarta"]):
            p = d.add_paragraph()
            _texto(p, f"{letra}. ", bold=True)
            _texto(p, f"La opción {valor} de {tema} {k}")
    d.add_paragraph()
    _texto(d.add_paragraph(), "TABLA DE RESPUESTAS", bold=True)
    _tabla(d, [ENC_RESP] + [["", clave, f"La respuesta se deduce de {tema}."] for _ in range(n)])
    d.add_paragraph()
    _texto(d.add_paragraph(), "TABLA DE EXCEL", bold=True)
    _tabla(d, [ENC_EXCEL] + [["", clave, grado, materia, submateria, pensamiento, competencia, dba, tema, nivel] for _ in range(n)])
    if glosario:
        d.add_paragraph()
        _texto(d.add_paragraph(), "TABLA DE GLOSARIO", bold=True)
        _tabla(d, [ENC_GLOSARIO] + [[str(k), t, sig] for k, t, sig in glosario])
    buf = io.BytesIO()
    d.save(buf)
    nombre = f"{tema}_{grado}_{materia}_{n}.docx".replace(" ", "_")
    return nombre, buf.getvalue()


TEMAS = ["Fracciones", "Porcentajes", "Ecuaciones lineales", "Probabilidad", "Potenciación", "Estadística",
         "Proporcionalidad", "Números primos", "Áreas y perímetros", "Sucesiones"]


def llenar_banco(cargar, cuantos=6, **kw):
    """Carga «cuantos» ejercicios sueltos con temáticas distintas y devuelve sus códigos."""
    codigos = []
    for i in range(cuantos):
        nivel = kw.pop("nivel", None) or ["Básico", "Medio", "Avanzado"][i % 3]
        nombre, datos = ejercicio(TEMAS[i % len(TEMAS)], nivel=nivel, **kw)
        r = cargar(datos, nombre)
        assert r["estado"] == "aceptado", r["errores"]
        codigos += r["guardado"]["codigos"]
    return codigos
