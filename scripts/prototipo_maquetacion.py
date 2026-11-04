"""Prototipo de maquetación del cuerpo de la cartilla en Word real.

Sirve para verificar, antes de construir el sistema, que los ejercicios caben
bien en márgenes estrechos (1,27 cm, sin encuadernación, 2 columnas de 8,89 cm)
y que el espacio se aprovecha. Genera dos variantes:

  - vertical:  las cuatro opciones siempre una debajo de otra.
  - compacta:  opciones cortas en una fila (4) o en dos filas (2x2), medidas
               con las métricas reales de Tahoma; las demás, verticales.

Uso:  python scripts/prototipo_maquetacion.py <carpeta_salida>
"""
import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt
from PIL import Image, ImageDraw, ImageFont

FUENTES = Path("C:/Windows/Fonts")
TAHOMA = ImageFont.truetype(str(FUENTES / "tahoma.ttf"), 90)
TAHOMA_B = ImageFont.truetype(str(FUENTES / "tahomabd.ttf"), 90)
PLANTILLA_1 = ("BACDCDABDBACDCBABCDAACBDABCDCABDADBCCABDDCBACABDDABCCADBBCADDBCAABCDACDBDABCDCBAC"
               "ABDDACBBCDACDBAACBDCDABCADBBCADBACDDACBCBADBACDBCADBDACADCB")

# Medidas de página (twips: 1 cm = 567)
MARGEN = 720             # 1,27 cm
ESPACIO_COLUMNAS = 720   # 1,27 cm
ANCHO_COLUMNA_PT = (21.59 - 2 * 1.27 - 1.27) / 2 / 2.54 * 72   # 8,89 cm = 252 pt
SANGRIA_OPCION = 300     # twips: espacio para «A.» antes del texto


# ---------------------------------------------------------------- utilidades XML
def _el(tag, **attrs):
    e = OxmlElement(tag)
    for k, v in attrs.items():
        e.set(qn(k), str(v))
    return e


def fmt(p, antes=0, despues=0, alin=None, juntar=False, sangria=None, tabs=()):
    pf = p.paragraph_format
    pf.space_before = Pt(antes)
    pf.space_after = Pt(despues)
    pf.line_spacing = 1.0
    pf.keep_with_next = juntar
    pf.widow_control = True
    if alin is not None:
        p.alignment = alin
    if sangria:
        pf.left_indent = sangria
        pf.first_line_indent = -sangria
    for t in tabs:
        pf.tab_stops.add_tab_stop(t)
    return p


def texto(p, cadena, size=9, bold=False, italic=False):
    """Escribe texto con marcas: ^{sup} _{sub} ~cursiva~ y \\t para tabulador."""
    for trozo in re.split(r"(\^\{[^}]*\}|_\{[^}]*\}|~[^~]*~|\t)", cadena):
        if not trozo:
            continue
        if trozo == "\t":
            p.add_run().add_tab()
            continue
        run = p.add_run(re.sub(r"^[\^_]\{|\}$|~", "", trozo))
        run.font.name = "Tahoma"
        run.font.size = Pt(size)
        run.bold = bold
        run.italic = italic or trozo.startswith("~")
        if trozo.startswith("^{"):
            run.font.superscript = True
        elif trozo.startswith("_{"):
            run.font.subscript = True
    return p


def ancho_pt(cadena, bold=False):
    limpio = re.sub(r"\^\{|_\{|\}|~", "", cadena)
    fuente = TAHOMA_B if bold else TAHOMA
    return fuente.getlength(limpio) * 9 / 90


def borde_superior(p):
    ppr = p._p.get_or_add_pPr()
    bdr = _el("w:pBdr")
    bdr.append(_el("w:top", **{"w:val": "single", "w:sz": 2, "w:space": 4, "w:color": "000000"}))
    ppr.append(bdr)


# ---------------------------------------------------------------- imágenes de prueba
def imagen_grafica(ruta):
    w, h = 945, 560   # 8,0 cm a 300 ppp
    im = Image.new("L", (w, h), 255)
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(str(FUENTES / "tahoma.ttf"), 30)
    datos = [("Lun", 18), ("Mar", 22), ("Mié", 15), ("Jue", 25), ("Vie", 20)]
    d.line((90, 40, 90, 470), fill=0, width=3)
    d.line((90, 470, 900, 470), fill=0, width=3)
    for i, (dia, v) in enumerate(datos):
        x = 140 + i * 150
        y = 470 - v * 16
        d.rectangle((x, y, x + 90, 470), fill=140, outline=0, width=2)
        d.text((x + 20, 485), dia, fill=0, font=f)
        d.text((x + 25, y - 38), f"{v}°", fill=0, font=f)
    d.text((10, 10), "°C", fill=0, font=f)
    im.save(ruta, dpi=(300, 300))


def imagen_aviso(ruta, lineas):
    w, h = 650, 230   # 5,5 cm a 300 ppp
    im = Image.new("L", (w, h), 255)
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(str(FUENTES / "tahomabd.ttf"), 44)
    d.rounded_rectangle((6, 6, w - 6, h - 6), radius=24, outline=0, width=6)
    y = h / 2 - len(lineas) * 28
    for linea in lineas:
        tw = d.textlength(linea, font=f)
        d.text(((w - tw) / 2, y), linea, fill=0, font=f)
        y += 56
    im.save(ruta, dpi=(300, 300))


# ---------------------------------------------------------------- contenido de ejemplo
def Q(e, o, info="", img=None, tabla=None):
    return {"e": e if isinstance(e, list) else [e], "o": o, "info": info, "img": img, "tabla": tabla}


def contenido(tmp):
    grafica = tmp / "grafica.png"
    imagen_grafica(grafica)
    avisos = []
    for i, lin in enumerate([["PLEASE", "BE QUIET"], ["KEEP OFF", "THE GRASS"], ["PLATFORM 3", "TRAINS TO TUNJA"], ["WASH YOUR HANDS", "BEFORE EATING"]]):
        r = tmp / f"aviso{i}.png"
        imagen_aviso(r, lin)
        avisos.append(r)

    mat = [
        Q("Una tienda aplica un descuento del 20 % sobre un artículo que cuesta $45.000. ¿Cuál es el precio final del artículo?", ["$36.000", "$9.000", "$40.000", "$44.980"], "Numérico // Resolución de problemas // DBA 2 // BB"),
        Q("¿Cuál es el valor de ~x~ en la ecuación 3~x~ + 7 = 22?", ["5", "15", "^{29}/_{3}", "7"], "Variacional // Razonamiento // DBA 7 // BB"),
        Q("El área de un cuadrado es 49 cm^{2}. ¿Cuánto mide su perímetro?", ["28 cm", "14 cm", "49 cm", "196 cm"], "Espacial y métrico // Resolución de problemas // DBA 5 // MM"),
        Q("Si 2^{x} = 32, ¿cuál es el valor de ~x~?", ["5", "16", "6", "4"], "Numérico // Razonamiento // DBA 1 // MM"),
        {"blk": "información", "res": [("La tabla muestra el número de libros que leyeron cuatro estudiantes durante un mes.", None)],
         "tabla": [["Estudiante", "Libros"], ["Ana", "4"], ["Luis", "6"], ["Marta", "3"], ["Pedro", "7"]],
         "qs": [Q("¿Cuál es el promedio de libros leídos por estudiante?", ["5", "4", "6", "20"], "Aleatorio // Comunicación // DBA 9 // BB"),
                Q("¿Qué porcentaje del total de libros leyó Luis?", ["30 %", "6 %", "25 %", "60 %"], "Aleatorio // Razonamiento // DBA 9 // MM"),
                Q("Si el mes siguiente Marta lee el doble de libros, ¿cuántos leerá?", ["6", "5", "9", "3"], "Numérico // Resolución de problemas // DBA 2 // BB")]},
        Q("Un ángulo mide 35°. ¿Cuánto mide su ángulo complementario?", ["55°", "145°", "65°", "325°"], "Espacial y métrico // Razonamiento // DBA 4 // BB"),
        Q("En una bolsa hay 3 bolas rojas y 5 azules. Si se saca una bola al azar, ¿cuál es la probabilidad de que sea roja?", ["^{3}/_{8}", "^{3}/_{5}", "^{5}/_{8}", "^{1}/_{3}"], "Aleatorio // Resolución de problemas // DBA 10 // MM"),
        Q("¿Cuál expresión es equivalente a 4(~x~ − 3)?", ["4~x~ − 12", "4~x~ − 3", "~x~ − 12", "4~x~ + 12"], "Variacional // Comunicación // DBA 7 // BB"),
        Q(["Un ciclista recorre una pista circular de 400 m. En la primera vuelta tarda 80 segundos y en la segunda, 100 segundos.",
           "¿Cuál fue su rapidez media en las dos vueltas?"], ["4,4 m/s", "5 m/s", "4 m/s", "9 m/s"], "Variacional // Resolución de problemas // DBA 8 // AA"),
        Q("¿Cuál de los siguientes números es primo?", ["29", "27", "33", "39"], "Numérico // Razonamiento // DBA 1 // BB"),
    ]
    lectura = [
        {"blk": "lectura", "res": [
            ("En el pueblo de mi abuela, la luz se iba cada vez que llovía. Entonces alguien encendía una vela, y la casa se llenaba de sombras largas que parecían escuchar. Mi abuela aprovechaba la oscuridad para contar historias: la del río que cambió de lugar una noche, la del gallo que cantaba a medianoche y la de la mujer que tejía mapas con lana de colores.", None),
            ("Nunca supe cuáles eran ciertas. Con los años entendí que esa no era la pregunta importante. Las historias servían para que el miedo a la tormenta se volviera otra cosa: una reunión, una risa, un secreto compartido. Cuando por fin llegó la electricidad estable, nadie lo celebró tanto como esperábamos.", None)],
         "qs": [Q("¿Qué función cumplían las historias de la abuela según el narrador?", ["Transformar el miedo a la tormenta en un momento compartido.", "Enseñar a los niños la historia verdadera del pueblo.", "Explicar por qué se iba la luz cuando llovía.", "Advertir a la familia sobre los peligros del río."], "Comprende el sentido global del texto // MM"),
                Q("¿Por qué la llegada de la electricidad estable no se celebró tanto como se esperaba?", ["Porque con ella terminaron las reuniones alrededor de las historias.", "Porque la luz siguió yéndose cuando llovía.", "Porque la abuela no quería la electricidad.", "Porque el pueblo no tenía dinero para pagarla."], "Infiere información implícita // AA"),
                Q("En el texto, la expresión «sombras largas que parecían escuchar» es un ejemplo de", ["personificación.", "comparación.", "hipérbole.", "enumeración."], "Reconoce recursos del lenguaje // MM"),
                Q("¿Qué tipo de narrador tiene el texto?", ["Protagonista, que cuenta sus recuerdos.", "Omnisciente, que conoce todo.", "Testigo, que no participa en los hechos.", "Colectivo, que habla por todo el pueblo."], "Identifica la voz narrativa // BB")]},
    ]
    sociales = [
        Q("Durante la Colonia, el sistema de la encomienda consistía en", ["asignar a un español un grupo de indígenas que debían pagarle tributo a cambio de evangelización.", "repartir tierras entre los indígenas para que las cultivaran de forma libre.", "entregar a los esclavizados africanos el control de las minas de oro.", "permitir que los criollos eligieran a las autoridades de cada provincia."], "Temporal // Pensamiento social // DBA 3 // MM"),
        Q("¿Cuál de las siguientes es una función del Congreso de la República de Colombia?", ["Hacer las leyes.", "Administrar justicia.", "Dirigir la fuerza pública.", "Nombrar a los alcaldes."], "Espacial // Interpretación // DBA 5 // BB"),
        Q("Un grupo de estudiantes quiere proponer un cambio en el manual de convivencia del colegio. ¿Cuál es el mecanismo más adecuado para hacerlo?", ["Presentar la propuesta al consejo estudiantil para que la lleve al consejo directivo.", "Dejar de cumplir las normas hasta que las cambien.", "Publicar quejas anónimas en las redes sociales del colegio.", "Pedir a los padres que retiren a sus hijos del colegio."], "Ciudadanía // Pensamiento reflexivo // DBA 6 // MM"),
    ]
    bio = [
        Q("¿Qué organelo produce la mayor parte de la energía de la célula?", ["Mitocondria", "Ribosoma", "Vacuola", "Pared celular"], "Entorno vivo // Uso del conocimiento // DBA 3 // BB"),
        Q(["La gráfica muestra la temperatura máxima registrada en un municipio durante cinco días."],
          ["El jueves", "El lunes", "El miércoles", "El viernes"], "Entorno vivo // Indagación // DBA 5 // BB", img=grafica),
        Q("¿Qué proceso realizan las plantas para producir su alimento a partir de la luz solar?", ["Fotosíntesis", "Respiración", "Digestión", "Fermentación"], "Entorno vivo // Uso del conocimiento // DBA 4 // BB"),
    ]
    bio[1]["e"].append("¿Qué día se registró la temperatura más alta?")

    ingles = [
        {"parte": "Vocabulario en contexto", "instr": "Lee cada descripción y elige la palabra que le corresponde.",
         "qs": [Q("You use this to open a door.", ["key", "spoon", "pencil", "towel"], "Lingüística // DBA 1 // BB"),
                Q("People go here to see a doctor.", ["hospital", "library", "bakery", "stadium"], "Lingüística // DBA 1 // BB"),
                Q("You wear these on your feet.", ["shoes", "gloves", "glasses", "hats"], "Lingüística // DBA 1 // BB"),
                Q("This animal gives us milk.", ["cow", "eagle", "shark", "spider"], "Lingüística // DBA 1 // BB"),
                Q("You need this to know the time.", ["watch", "ruler", "map", "brush"], "Lingüística // DBA 1 // BB")]},
        {"parte": "Avisos y anuncios", "instr": "Observa cada aviso y elige el lugar donde puedes encontrarlo.",
         "qs": [Q([], ["library", "swimming pool", "football stadium", "market"], "Pragmática // DBA 2 // BB", img=avisos[0]),
                Q([], ["park", "kitchen", "bank", "cinema"], "Pragmática // DBA 2 // BB", img=avisos[1]),
                Q([], ["train station", "hospital", "school", "supermarket"], "Pragmática // DBA 2 // BB", img=avisos[2]),
                Q([], ["restaurant", "bookshop", "cinema", "bus stop"], "Pragmática // DBA 2 // BB", img=avisos[3])]},
        {"parte": "Completar el texto", "instr": "Lee el texto y elige la palabra que completa cada espacio.",
         "cloze": "Last Saturday my family and I {1} to the lake. We {2} up very early and took the bus. The weather {3} sunny and warm. My father {4} a big fish, and my mother made sandwiches {5} everybody. In the afternoon we swam {6} played cards. It was {7} best day of the holidays.",
         "qs": [Q([], o, "Lingüística // DBA 4 // MM") for o in [["went", "go", "goes", "going"], ["got", "get", "gets", "getting"], ["was", "were", "is", "be"], ["caught", "catch", "catches", "catching"], ["for", "at", "in", "on"], ["and", "but", "or", "so"], ["the", "a", "an", "some"]]]},
    ]
    return [("MATEMÁTICAS I", mat), ("COMPRENSIÓN LECTORA", lectura), ("CIENCIAS SOCIALES", sociales), ("BIOLOGÍA", bio), ("INGLÉS", ingles)]


# ---------------------------------------------------------------- maquetador
class Maquetador:
    def __init__(self, variante):
        self.variante = variante
        self.n = 1
        self.parte = 1
        self.stats = {"fila": 0, "2x2": 0, "vertical": 0}
        self.doc = Document()
        st = self.doc.styles["Normal"]
        st.font.name = "Tahoma"
        st.font.size = Pt(9)
        st.element.rPr.rFonts.set(qn("w:eastAsia"), "Tahoma")
        st.paragraph_format.space_after = Pt(0)
        st.paragraph_format.line_spacing = 1.0
        sec = self.doc.sections[0]
        sec.page_width, sec.page_height = Cm(21.59), Cm(27.94)
        sec.top_margin = sec.bottom_margin = sec.left_margin = sec.right_margin = Cm(1.27)
        sec.gutter = Cm(0)
        sec.footer_distance = Cm(0.5)
        cols = sec._sectPr.xpath("./w:cols")
        c = cols[0] if cols else _el("w:cols")
        c.set(qn("w:num"), "2"); c.set(qn("w:space"), str(ESPACIO_COLUMNAS)); c.set(qn("w:sep"), "1")
        if not cols:
            sec._sectPr.append(c)
        self.doc.settings.odd_and_even_pages_header_footer = True
        self._pies(sec)

    def _pies(self, sec):
        for pie, par in ((sec.footer, False), (sec.even_page_footer, True)):
            p = pie.paragraphs[0]
            ppr = p._p.get_or_add_pPr()
            t = _el("w:tabs")
            for pos in (4680, 9360):
                t.append(_el("w:tab", **{"w:val": "clear", "w:pos": pos}))
            t.append(_el("w:tab", **{"w:val": "right", "w:pos": 10800}))
            ppr.append(t)
            campo = lambda: p._p.append(_el("w:fldSimple", **{"w:instr": "PAGE"}))
            if par:
                texto(p, "PRAXIS – THINKS | Educación & Práctica\t", size=7)
                campo()
            else:
                campo()
                texto(p, "\tPRAXIS – THINKS | Educación & Práctica", size=7)

    # -- piezas
    def titulo_seccion(self, t):
        p = fmt(self.doc.add_paragraph(), antes=4, despues=6, alin=WD_ALIGN_PARAGRAPH.CENTER, juntar=True)
        texto(p, t, size=12, bold=True)

    def parrafo(self, cadena, numero=None, juntar=False, lectura=False, **kw):
        alin = WD_ALIGN_PARAGRAPH.JUSTIFY if lectura else WD_ALIGN_PARAGRAPH.LEFT
        p = fmt(self.doc.add_paragraph(), despues=2, alin=alin, juntar=juntar)
        if numero is not None:
            texto(p, f"{numero}. ", bold=True)
        texto(p, cadena, **kw)
        return p

    def imagen(self, ruta, ancho_cm):
        p = fmt(self.doc.add_paragraph(), despues=3, alin=WD_ALIGN_PARAGRAPH.CENTER, juntar=True)
        p.add_run().add_picture(str(ruta), width=Cm(ancho_cm))

    def tabla(self, filas):
        t = self.doc.add_table(rows=len(filas), cols=len(filas[0]))
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        t.style = self.doc.styles["Table Grid"]
        for i, fila in enumerate(filas):
            tr = t.rows[i]._tr.get_or_add_trPr()
            tr.append(_el("w:cantSplit"))
            for j, valor in enumerate(fila):
                celda = t.cell(i, j)
                celda.width = Cm(2.6)
                p = fmt(celda.paragraphs[0], alin=WD_ALIGN_PARAGRAPH.CENTER)
                texto(p, valor, size=8, bold=(i == 0))

    def disposicion(self, opciones, ancho):
        if self.variante == "vertical":
            return "vertical"
        mayor = max(ancho_pt(f"{L}. ", True) + ancho_pt(o) for L, o in zip("ABCD", opciones))
        if mayor <= ancho / 4 - 6:
            return "fila"
        if mayor <= ancho / 2 - 8:
            return "2x2"
        return "vertical"

    def opciones(self, q, ultimo_despues, numero_en_linea=False, con_info=False):
        objetivo = "ABCD".index(PLANTILLA_1[(self.n - 1) % 140])
        o = q["o"][:]
        o[0], o[objetivo] = o[objetivo], o[0]
        # sin enunciado: el número va en la misma línea que las opciones
        pre = Pt(20) if numero_en_linea else Pt(0)
        ancho = ANCHO_COLUMNA_PT - pre.pt
        modo = self.disposicion(o, ancho)
        self.stats[modo] += 1
        if modo == "fila":
            filas = [list(range(4))]
            tabs = [Pt(pre.pt + ancho * k / 4) for k in (1, 2, 3)]
        elif modo == "2x2":
            filas = [[0, 1], [2, 3]]
            tabs = [Pt(pre.pt + ancho / 2)]
        else:
            filas = [[i] for i in range(4)]
            tabs = []
        for k, fila in enumerate(filas):
            ultimo = k == len(filas) - 1
            if modo == "vertical":
                sang = Pt(pre.pt + SANGRIA_OPCION / 20)
                p = fmt(self.doc.add_paragraph(), despues=ultimo_despues if ultimo else 0, juntar=not ultimo or con_info, sangria=sang, tabs=[sang])
                if pre.pt:
                    p.paragraph_format.first_line_indent = -sang
                    p.paragraph_format.tab_stops.add_tab_stop(pre)
            else:
                p = fmt(self.doc.add_paragraph(), despues=ultimo_despues if ultimo else 0, juntar=not ultimo, tabs=([pre] if pre.pt else []) + tabs)
                if pre.pt:
                    p.paragraph_format.left_indent = pre
                    p.paragraph_format.first_line_indent = -pre
            if pre.pt:
                if k == 0:
                    texto(p, f"{self.n}.", bold=True)
                p.add_run().add_tab()
            for idx, i in enumerate(fila):
                if idx:
                    p.add_run().add_tab()
                texto(p, f"{'ABCD'[i]}.", bold=True)
                if modo == "vertical":
                    p.add_run().add_tab()
                else:
                    texto(p, " ")
                texto(p, o[i])
        return p

    def pregunta(self, q, icfes=False):
        partes = q["e"]
        if q["img"] and not partes:           # aviso de Inglés: número y luego la imagen
            p = fmt(self.doc.add_paragraph(), despues=1, juntar=True)
            texto(p, f"{self.n}.", bold=True)
            self.imagen(q["img"], 4.4)
        elif not partes:                       # completar el texto: el número va con las opciones
            pass
        else:
            for i, e in enumerate(partes):
                ultimo = i == len(partes) - 1
                # la pregunta nunca se parte entre columnas: enunciado unido a sus opciones
                self.parrafo(e, self.n if i == 0 else None, juntar=True)
                if q["img"] and i == 0:
                    self.imagen(q["img"], 7.5)
        con_info = bool(q["info"]) and not icfes
        self.opciones(q, 1 if con_info else 7, numero_en_linea=not partes and not q["img"], con_info=con_info)
        if con_info:
            p = fmt(self.doc.add_paragraph(), despues=7)
            texto(p, "➤ " + q["info"], size=6, italic=True)
        self.n += 1

    def bloque(self, b):
        k = len(b["qs"])
        p = fmt(self.doc.add_paragraph(), despues=3, juntar=True)
        texto(p, f"Responde las preguntas {self.n} a {self.n + k - 1} de acuerdo con la siguiente {b['blk']}.", bold=True)
        for cad, _ in b["res"]:
            self.parrafo(cad, juntar=bool(b.get("tabla")), lectura=True)
        if b.get("tabla"):
            self.tabla(b["tabla"])
        p = fmt(self.doc.add_paragraph(), antes=2, despues=5, alin=WD_ALIGN_PARAGRAPH.RIGHT)
        texto(p, "Texto elaborado para este simulacro. PRAXIS · THINKS.", size=8, italic=True)
        for q in b["qs"]:
            self.pregunta(q)

    def parte_ingles(self, pt):
        k = len(pt["qs"])
        p = fmt(self.doc.add_paragraph(), antes=4, despues=1, juntar=True)
        borde_superior(p)
        texto(p, f"PARTE {self.parte} · {pt['parte']} — preguntas {self.n} a {self.n + k - 1}", bold=True)
        p = fmt(self.doc.add_paragraph(), despues=4, juntar=True)
        texto(p, pt["instr"], italic=True)
        if pt.get("cloze"):
            base = self.n
            cad = re.sub(r"\{(\d+)\}", lambda m: f"({base + int(m.group(1)) - 1}) _____", pt["cloze"])
            self.parrafo(cad, lectura=True)
            p = fmt(self.doc.add_paragraph(), despues=5, alin=WD_ALIGN_PARAGRAPH.RIGHT)
            texto(p, "Texto elaborado para este simulacro. PRAXIS · THINKS.", size=8, italic=True)
        for q in pt["qs"]:
            self.pregunta(q)
        self.parte += 1

    def construir(self, secciones):
        for titulo, unidades in secciones:
            self.titulo_seccion(titulo)
            for u in unidades:
                if "blk" in u:
                    self.bloque(u)
                elif "parte" in u:
                    self.parte_ingles(u)
                else:
                    self.pregunta(u)
        return self.doc


def exportar_pdf(docx_path, pdf_path, exportar=True):
    import win32com.client
    w = win32com.client.DispatchEx("Word.Application")
    w.Visible = False
    try:
        d = w.Documents.Open(str(docx_path), ReadOnly=True)
        paginas = d.ComputeStatistics(2)
        lineas = d.ComputeStatistics(1)
        ultima = d.Paragraphs(d.Paragraphs.Count).Range
        alto = ultima.Information(6) / 72 * 2.54        # posición vertical en cm
        columna_derecha = ultima.Information(7) / 72 * 2.54 > 10
        if exportar:
            d.ExportAsFixedFormat(str(pdf_path), 17)
        d.Close(False)
        return paginas, lineas, alto, columna_derecha
    finally:
        w.Quit()


if __name__ == "__main__":
    salida = Path(sys.argv[1] if len(sys.argv) > 1 else "prototipo").resolve()
    salida.mkdir(parents=True, exist_ok=True)
    secciones = contenido(salida)
    for nombre, secs in (("muestra", secciones), ("volumen", (secciones * 4)[:17])):
        for variante in ("vertical",):
            m = Maquetador(variante)
            m.construir(secs)
            ruta = salida / f"{nombre}_{variante}.docx"
            m.doc.save(ruta)
            pag, lin, alto, der = exportar_pdf(ruta, salida / f"{nombre}_{variante}.pdf", exportar=(nombre == "muestra"))
            print(f"{nombre:8s} {variante:9s} preguntas={m.n - 1:3d} paginas={pag} lineas={lin} "
                  f"ultima_pagina: col {'2' if der else '1'} hasta {alto:.1f} cm  opciones={m.stats}")
