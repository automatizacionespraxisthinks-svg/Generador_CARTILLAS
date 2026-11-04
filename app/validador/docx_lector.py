"""Lectura de un .docx de carga: cuerpo, estilos y formato efectivo de cada run.

Word guarda el formato en capas (valores por defecto, estilo de tabla, estilo de
párrafo, estilo de carácter y formato directo). El validador necesita el valor
EFECTIVO, así que aquí se resuelve esa herencia.
"""
import io
import zipfile
from dataclasses import dataclass, field

from lxml import etree

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "pic": "http://schemas.openxmlformats.org/drawingml/2006/picture",
    "m": "http://schemas.openxmlformats.org/officeDocument/2006/math",
    "mc": "http://schemas.openxmlformats.org/markup-compatibility/2006",
    "v": "urn:schemas-microsoft-com:vml",
    "o": "urn:schemas-microsoft-com:office:office",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}
W = "{%s}" % NS["w"]
M = "{%s}" % NS["m"]


def q(tag):
    pre, nombre = tag.split(":")
    return "{%s}%s" % (NS[pre], nombre)


def _activo(el):
    """Propiedad booleana de Word: presente y sin val=0/false/off."""
    if el is None:
        return None
    return el.get(W + "val", "true").lower() not in ("0", "false", "off", "none")


class ErrorLectura(Exception):
    pass


@dataclass
class Formato:
    fuente: str | None = None
    tam: int | None = None          # medios puntos (18 = 9 pt)
    negrita: bool = False
    cursiva: bool = False
    color: str | None = None        # hex o "auto"
    color_tema: str | None = None
    color_variado: bool = False     # themeTint / themeShade: el color del tema aclarado u oscurecido
    vert: str | None = None         # superscript / subscript
    resaltado: str | None = None
    subrayado: str | None = None    # valor de w:u (single, double…; none = sin subrayado)
    oculto: bool = False
    sombreado: str | None = None
    alternantes: dict = field(default_factory=dict, repr=False)


@dataclass
class Fragmento:
    texto: str
    fmt: Formato
    omml: object = None             # una ecuación de Word (m:oMath), en el sitio que le toca del párrafo


@dataclass
class Parrafo:
    el: object
    fragmentos: list = field(default_factory=list)
    alineacion: str = "left"                        # efectiva: formato directo, estilo o valor por defecto
    alineacion_directa: str | None = None           # la aplicada al párrafo con los botones de Word, si la hay
    numerado: bool = False
    dibujos: list = field(default_factory=list)      # elementos w:drawing
    tiene_ecuacion: bool = False
    objetos: list = field(default_factory=list)      # descripciones de objetos prohibidos

    @property
    def texto(self):
        return "".join(f.texto for f in self.fragmentos)

    @property
    def vacio(self):
        return not self.texto.strip() and not self.dibujos and not self.tiene_ecuacion and not self.objetos


@dataclass
class Tabla:
    el: object
    filas: list = field(default_factory=list)        # filas -> celdas -> [Parrafo | Tabla]
    anidada: bool = False
    trs: list = field(default_factory=list)          # elementos w:tr (también dentro de controles de contenido)
    tcs: list = field(default_factory=list)          # elementos w:tc por fila

    def textos(self):
        return [[" ".join(p.texto.strip() for p in celda if isinstance(p, Parrafo)).strip() for celda in fila] for fila in self.filas]


class Estilos:
    def __init__(self, xml_estilos, xml_tema):
        self.estilos = {}
        self.rpr_def = None
        self.ppr_def = None
        self.parrafo_def = None
        self.fuentes_tema = {}
        if xml_estilos is not None:
            raiz = etree.fromstring(xml_estilos)
            self.rpr_def = raiz.find("w:docDefaults/w:rPrDefault/w:rPr", NS)
            self.ppr_def = raiz.find("w:docDefaults/w:pPrDefault/w:pPr", NS)
            for st in raiz.findall("w:style", NS):
                sid = st.get(W + "styleId")
                self.estilos[sid] = st
                if st.get(W + "type") == "paragraph" and st.get(W + "default") in ("1", "true"):
                    self.parrafo_def = sid
        if xml_tema is not None:
            tema = etree.fromstring(xml_tema)
            for clase in ("minor", "major"):
                latin = tema.find(f".//a:{clase}Font/a:latin", NS)
                if latin is not None:
                    self.fuentes_tema[clase] = latin.get("typeface")

    def cadena(self, sid):
        """Estilos desde el más general hasta sid (siguiendo basedOn)."""
        out, vistos = [], set()
        while sid and sid in self.estilos and sid not in vistos:
            vistos.add(sid)
            st = self.estilos[sid]
            out.append(st)
            base = st.find("w:basedOn", NS)
            sid = base.get(W + "val") if base is not None else None
        return list(reversed(out))

    def _fuente_de(self, rfonts):
        tema = rfonts.get(W + "asciiTheme")
        if tema:
            return self.fuentes_tema.get("major" if tema.startswith("major") else "minor", tema)
        return rfonts.get(W + "ascii")

    def _aplicar_rpr(self, f, rpr):
        if rpr is None:
            return
        rf = rpr.find("w:rFonts", NS)
        if rf is not None:
            nombre = self._fuente_de(rf)
            if nombre:
                f.fuente = nombre
        sz = rpr.find("w:sz", NS)
        if sz is not None and sz.get(W + "val"):
            f.tam = int(float(sz.get(W + "val")))
        for tag, attr in (("b", "negrita"), ("i", "cursiva"), ("vanish", "oculto")):
            v = _activo(rpr.find(f"w:{tag}", NS))
            if v is not None:
                setattr(f, attr, v)
                f.alternantes[attr] = v
        c = rpr.find("w:color", NS)
        if c is not None:
            f.color = c.get(W + "val")
            f.color_tema = c.get(W + "themeColor")
            f.color_variado = bool(c.get(W + "themeTint") or c.get(W + "themeShade"))
        va = rpr.find("w:vertAlign", NS)
        if va is not None:
            v = va.get(W + "val")
            f.vert = v if v in ("superscript", "subscript") else None
        u = rpr.find("w:u", NS)
        if u is not None:
            f.subrayado = u.get(W + "val")
        hl = rpr.find("w:highlight", NS)
        if hl is not None:
            f.resaltado = hl.get(W + "val")
        shd = rpr.find("w:shd", NS)
        if shd is not None:
            f.sombreado = shd.get(W + "fill")

    def formato_run(self, run, estilo_parrafo, estilo_tabla):
        f = Formato()
        self._aplicar_rpr(f, self.rpr_def)
        f.alternantes = {}
        if estilo_parrafo not in self.estilos:          # estilo inexistente: Word usa el párrafo normal
            estilo_parrafo = self.parrafo_def
        rpr = run.find("w:rPr", NS)
        rs = rpr.find("w:rStyle", NS) if rpr is not None else None
        capas = [self.cadena(estilo_tabla), self.cadena(estilo_parrafo), self.cadena(rs.get(W + "val") if rs is not None else None)]
        # Negrita, cursiva y oculto son «alternantes»: entre estilos de tabla, párrafo y carácter se combinan
        # con O exclusivo (dos estilos en cursiva dan texto normal); dentro de una cadena basedOn manda el derivado.
        alternantes = {}
        for cadena in capas:
            propios = {}
            for st in cadena:
                self._aplicar_rpr(f, st.find("w:rPr", NS))
                propios.update(f.alternantes)
                f.alternantes = {}
            for attr, v in propios.items():
                alternantes[attr] = alternantes.get(attr, False) ^ v
        for attr, v in alternantes.items():
            setattr(f, attr, v)
        self._aplicar_rpr(f, rpr)
        f.alternantes = {}
        return f

    def ppr_efectivo(self, p, tag, estilo_tabla=None):
        """Último valor de un hijo de pPr (p. ej. jc, numPr) en la cadena de estilos."""
        encontrado = None
        capas = [self.ppr_def] + [st.find("w:pPr", NS) for st in self.cadena(estilo_tabla)]
        ppr = p.find("w:pPr", NS)
        sid = None
        if ppr is not None and ppr.find("w:pStyle", NS) is not None:
            sid = ppr.find("w:pStyle", NS).get(W + "val")
        capas += [st.find("w:pPr", NS) for st in self.cadena(sid if sid in self.estilos else self.parrafo_def)]
        capas.append(ppr)
        for capa in capas:
            if capa is not None and capa.find(f"w:{tag}", NS) is not None:
                encontrado = capa.find(f"w:{tag}", NS)
        return encontrado


class DocxCarga:
    """Un archivo de carga abierto y listo para validar."""

    def __init__(self, datos: bytes):
        try:
            self.zip = zipfile.ZipFile(io.BytesIO(datos))
            self.doc = etree.fromstring(self.zip.read("word/document.xml"))
        except (zipfile.BadZipFile, KeyError, etree.XMLSyntaxError) as e:
            raise ErrorLectura("El archivo no es un Word (.docx) válido o está dañado.") from e
        nombres = set(self.zip.namelist())
        leer = lambda n: self.zip.read(n) if n in nombres else None
        self.estilos = Estilos(leer("word/styles.xml"), leer("word/theme/theme1.xml"))
        self.comentarios = leer("word/comments.xml")
        self.rels = {}
        rels = leer("word/_rels/document.xml.rels")
        if rels is not None:
            for r in etree.fromstring(rels).findall("rel:Relationship", NS):
                self.rels[r.get("Id")] = (r.get("Target"), r.get("TargetMode"))
        self.cuerpo = self.doc.find("w:body", NS)
        if self.cuerpo is None:
            raise ErrorLectura("El archivo está guardado como «Documento Open XML strict». Ábrelo en Word y guárdalo como «Documento de Word (.docx)».")
        self.items = self._leer_bloque(self.cuerpo, None)

    def media(self, rid):
        destino = self.rels.get(rid)
        if not destino or destino[1] == "External":
            return None, destino[0] if destino else None
        ruta = destino[0].lstrip("/")
        ruta = ruta if ruta.startswith("word/") else "word/" + ruta
        try:
            return self.zip.read(ruta), ruta
        except KeyError:
            return None, ruta

    # ------------------------------------------------------------------ cuerpo
    def _leer_bloque(self, contenedor, estilo_tabla):
        items = []
        for hijo in contenedor:
            if hijo.tag == W + "p":
                items.append(self._leer_parrafo(hijo, estilo_tabla))
            elif hijo.tag == W + "tbl":
                items.append(self._leer_tabla(hijo))
            elif hijo.tag == W + "sdt":
                cont = hijo.find("w:sdtContent", NS)
                if cont is not None:
                    items.extend(self._leer_bloque(cont, estilo_tabla))
        return items

    def _leer_tabla(self, tbl, anidada=False):
        estilo = tbl.find("w:tblPr/w:tblStyle", NS)
        sid = estilo.get(W + "val") if estilo is not None else None
        t = Tabla(el=tbl, anidada=anidada)
        for tr in hijos(tbl, "tr"):
            fila, tcs = [], []
            for tc in hijos(tr, "tc"):
                celda = []
                for hijo in hijos(tc, "p", "tbl"):
                    if hijo.tag == W + "p":
                        celda.append(self._leer_parrafo(hijo, sid))
                    else:
                        celda.append(self._leer_tabla(hijo, anidada=True))
                fila.append(celda)
                tcs.append(tc)
            t.filas.append(fila)
            t.trs.append(tr)
            t.tcs.append(tcs)
        return t

    def _leer_parrafo(self, p, estilo_tabla):
        ppr = p.find("w:pPr", NS)
        sid = None
        if ppr is not None and ppr.find("w:pStyle", NS) is not None:
            sid = ppr.find("w:pStyle", NS).get(W + "val")
        jc = self.estilos.ppr_efectivo(p, "jc", estilo_tabla)
        alin = jc.get(W + "val") if jc is not None else "left"
        alin = {"start": "left", "end": "right", "distribute": "both"}.get(alin, alin)
        jc_dir = ppr.find("w:jc", NS) if ppr is not None else None
        directa = jc_dir.get(W + "val") if jc_dir is not None else None
        directa = {"start": "left", "end": "right", "distribute": "both"}.get(directa, directa)
        num = self.estilos.ppr_efectivo(p, "numPr", estilo_tabla)
        numerado = False
        if num is not None:
            nid = num.find("w:numId", NS)
            numerado = nid is not None and nid.get(W + "val") not in (None, "0")
        par = Parrafo(el=p, alineacion=alin, alineacion_directa=directa, numerado=numerado)

        for el in p.iter():
            # solo lo que pertenece a este párrafo (no a cuadros de texto anidados)
            if el is not p and el.tag == W + "p":
                continue
            dueno = next((a for a in el.iterancestors(W + "p")), None)
            if el is not p and dueno is not p:
                continue
            if el.tag == W + "r" and not any(a.tag.startswith(M) for a in el.iterancestors()):
                fmt = self.estilos.formato_run(el, sid, estilo_tabla)
                texto = []
                for h in el:
                    if h.tag == W + "t":
                        texto.append(h.text or "")
                    elif h.tag == W + "tab":
                        texto.append("\t")
                    elif h.tag in (W + "br", W + "cr"):
                        texto.append("\n")
                    elif h.tag == W + "noBreakHyphen":
                        texto.append("-")
                    elif h.tag == W + "sym":
                        if texto:
                            par.fragmentos.append(Fragmento("".join(texto), fmt))
                            texto = []
                        fmt_sym = Formato(**{**fmt.__dict__, "alternantes": {}})
                        fmt_sym.fuente = h.get(W + "font") or fmt.fuente
                        par.fragmentos.append(Fragmento("□", fmt_sym))
                    elif h.tag == W + "footnoteReference" or h.tag == W + "endnoteReference":
                        par.objetos.append("una nota al pie")
                if texto:
                    par.fragmentos.append(Fragmento("".join(texto), fmt))
            elif el.tag == W + "drawing":
                par.dibujos.append(el)
            elif el.tag == M + "oMath":
                par.tiene_ecuacion = True
                # se guarda el elemento en su posición: el glosario puede llevar fórmulas (2.7B)
                par.fragmentos.append(Fragmento("", Formato(), omml=el))
            elif el.tag == W + "object":
                prog = el.find(".//o:OLEObject", NS)
                progid = prog.get("ProgID", "") if prog is not None else ""
                if progid.startswith("Equation"):
                    par.objetos.append("una ecuación de Microsoft Equation 3.0")
                elif "DSMT" in progid or "MathType" in progid:
                    par.objetos.append("una ecuación de MathType")
                else:
                    par.objetos.append(f"un objeto incrustado ({progid or 'OLE'})")
            elif el.tag == W + "pict":
                if el.find(".//o:OLEObject", NS) is None:
                    par.objetos.append("una forma, cuadro de texto o imagen antigua (VML)")
        return par


def hijos(el, *tags):
    """Hijos directos con esas etiquetas, entrando en los controles de contenido (w:sdt) de Word."""
    buscados = {W + t for t in tags}
    for h in el:
        if h.tag in buscados:
            yield h
        elif h.tag == W + "sdt":
            cont = h.find("w:sdtContent", NS)
            if cont is not None:
                yield from hijos(cont, *tags)


def texto_con_nivel(parrafo):
    """Lista de (carácter, vert) para las reglas de superíndice y fracciones."""
    out = []
    for f in parrafo.fragmentos:
        for ch in f.texto:
            out.append((ch, f.fmt.vert))
    return out
