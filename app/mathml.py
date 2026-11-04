"""Ecuaciones de Word a MathML, para verlas bien en la pantalla (Estándar 4B.0).

El Word guarda las ecuaciones en OMML. Hasta ahora la vista previa solo pegaba el texto suelto de la
fórmula, y eso **cambia lo que dice**: la ecuación «F₁/A₁ = F₂/A₂» se leía «F1A1 = F2A2», que es un
producto y no un cociente.

Aquí se traduce el OMML a MathML, que los navegadores dibujan sin necesidad de instalar nada. Si una
construcción no está contemplada, se procesan sus hijos: en el peor caso se ve el texto, nunca se pierde.
El Word de la cartilla no pasa por aquí: ahí la ecuación va tal cual, que es lo que imprime Word.
"""
import html
import re

M = "{http://schemas.openxmlformats.org/officeDocument/2006/math}"

OPERADORES = set("+-−±∓×·÷/=≠<>≤≥≈≅≡∼∝→←↔⇒⇔∈∉⊂⊃∪∩∧∨¬∀∃∅∞∫∑∏√%!,;:()[]{}|")
ACENTOS = {"̅": "‾", "⃗": "→", "̂": "^", "̃": "~", "̇": "˙", "̈": "¨"}


def _hijo(el, nombre):
    return el.find(M + nombre)


def _texto(el):
    return "".join(t.text or "" for t in el.iter(M + "t"))


def _hijos(el, nombre):
    return el.findall(M + nombre)


def _trozo(texto):
    """Un trozo de texto de la fórmula, repartido en números, letras y operadores."""
    out = []
    for parte in re.findall(r"\d+(?:[.,]\d+)?|[^\W\d_]+|\s+|.", texto, re.UNICODE):
        if not parte.strip():
            out.append("<mspace width='0.25em'/>")
        elif parte[0].isdigit():
            out.append(f"<mn>{html.escape(parte)}</mn>")
        elif parte in OPERADORES or not parte[0].isalnum():
            out.append(f"<mo>{html.escape(parte)}</mo>")
        else:
            out.append(f"<mi>{html.escape(parte)}</mi>")
    return "".join(out)


def _fila(partes):
    """Varias partes seguidas se agrupan, que es lo que MathML espera en cada hueco."""
    return partes if partes.count("<") == 1 or not partes else f"<mrow>{partes}</mrow>"


def _contenido(el):
    """Traduce los hijos de un elemento, en orden."""
    return "".join(_elemento(h) for h in el)


def _elemento(el):
    tag = el.tag if isinstance(el.tag, str) else ""
    if not tag.startswith(M):
        return ""
    nombre = tag[len(M):]

    if nombre == "r":                                   # un trozo de texto
        return _trozo(_texto(el))
    if nombre in ("rPr", "ctrlPr", "argPr", "fPr", "sSubPr", "sSupPr", "sSubSupPr", "radPr", "dPr",
                  "naryPr", "funcPr", "barPr", "accPr", "limLowPr", "limUppPr", "mPr", "mcPr", "eqArrPr",
                  "groupChrPr", "boxPr", "borderBoxPr", "phantPr", "sPrePr"):
        return ""                                       # propiedades: no se dibujan
    if nombre == "f":                                   # fracción
        return f"<mfrac>{_fila(_contenido(_hijo(el, 'num')))}{_fila(_contenido(_hijo(el, 'den')))}</mfrac>"
    if nombre in ("sSub", "sSup"):
        etiqueta = "msub" if nombre == "sSub" else "msup"
        parte = "sub" if nombre == "sSub" else "sup"
        return f"<{etiqueta}>{_fila(_contenido(_hijo(el, 'e')))}{_fila(_contenido(_hijo(el, parte)))}</{etiqueta}>"
    if nombre == "sSubSup":
        return ("<msubsup>" + _fila(_contenido(_hijo(el, "e"))) + _fila(_contenido(_hijo(el, "sub")))
                + _fila(_contenido(_hijo(el, "sup"))) + "</msubsup>")
    if nombre == "sPre":                                # índices a la izquierda
        return ("<mmultiscripts>" + _fila(_contenido(_hijo(el, "e"))) + "<mprescripts/>"
                + _fila(_contenido(_hijo(el, "sub"))) + _fila(_contenido(_hijo(el, "sup"))) + "</mmultiscripts>")
    if nombre == "rad":                                 # raíz
        grado = _hijo(el, "deg")
        cuerpo = _fila(_contenido(_hijo(el, "e")))
        if grado is not None and _contenido(grado).strip():
            return f"<mroot>{cuerpo}{_fila(_contenido(grado))}</mroot>"
        return f"<msqrt>{cuerpo}</msqrt>"
    if nombre == "d":                                   # paréntesis, corchetes, llaves
        pr = _hijo(el, "dPr")
        abre = (pr.find(M + "begChr").get(M + "val") if pr is not None and pr.find(M + "begChr") is not None else "(")
        cierra = (pr.find(M + "endChr").get(M + "val") if pr is not None and pr.find(M + "endChr") is not None else ")")
        sep = (pr.find(M + "sepChr").get(M + "val") if pr is not None and pr.find(M + "sepChr") is not None else "|")
        dentro = f"<mo>{html.escape(sep)}</mo>".join(_fila(_contenido(e)) for e in _hijos(el, "e"))
        return f"<mrow><mo>{html.escape(abre)}</mo>{dentro}<mo>{html.escape(cierra)}</mo></mrow>"
    if nombre == "nary":                                # sumatoria, integral, productoria
        pr = _hijo(el, "naryPr")
        signo = (pr.find(M + "chr").get(M + "val") if pr is not None and pr.find(M + "chr") is not None else "∫")
        sub, sup = _hijo(el, "sub"), _hijo(el, "sup")
        base = f"<mo>{html.escape(signo)}</mo>"
        if sub is not None and sup is not None:
            base = f"<msubsup>{base}{_fila(_contenido(sub))}{_fila(_contenido(sup))}</msubsup>"
        elif sub is not None:
            base = f"<msub>{base}{_fila(_contenido(sub))}</msub>"
        elif sup is not None:
            base = f"<msup>{base}{_fila(_contenido(sup))}</msup>"
        return f"<mrow>{base}{_fila(_contenido(_hijo(el, 'e')))}</mrow>"
    if nombre == "func":                                # sen, cos, log…
        return f"<mrow>{_fila(_contenido(_hijo(el, 'fName')))}{_fila(_contenido(_hijo(el, 'e')))}</mrow>"
    if nombre in ("limLow", "limUpp"):
        etiqueta = "munder" if nombre == "limLow" else "mover"
        return (f"<{etiqueta}>{_fila(_contenido(_hijo(el, 'e')))}"
                f"{_fila(_contenido(_hijo(el, 'lim')))}</{etiqueta}>")
    if nombre == "bar":
        return f"<mover>{_fila(_contenido(_hijo(el, 'e')))}<mo>‾</mo></mover>"
    if nombre == "acc":
        pr = _hijo(el, "accPr")
        chr_ = (pr.find(M + "chr").get(M + "val") if pr is not None and pr.find(M + "chr") is not None else "̂")
        return f"<mover>{_fila(_contenido(_hijo(el, 'e')))}<mo>{html.escape(ACENTOS.get(chr_, chr_))}</mo></mover>"
    if nombre == "groupChr":
        pr = _hijo(el, "groupChrPr")
        chr_ = (pr.find(M + "chr").get(M + "val") if pr is not None and pr.find(M + "chr") is not None else "⏟")
        return f"<munder>{_fila(_contenido(_hijo(el, 'e')))}<mo>{html.escape(chr_)}</mo></munder>"
    if nombre == "m":                                   # matriz
        filas = "".join("<mtr>" + "".join(f"<mtd>{_contenido(c)}</mtd>" for c in _hijos(f, "e")) + "</mtr>"
                        for f in _hijos(el, "mr"))
        return f"<mtable>{filas}</mtable>"
    if nombre == "eqArr":
        filas = "".join(f"<mtr><mtd>{_contenido(e)}</mtd></mtr>" for e in _hijos(el, "e"))
        return f"<mtable>{filas}</mtable>"
    return _contenido(el)                               # lo que no esté contemplado: sus hijos


def a_mathml(omath, titulo=None):
    """<math> listo para la pantalla, con el texto de la fórmula como alternativa accesible."""
    if omath is None:
        return ""
    cuerpo = _contenido(omath)
    if not cuerpo:
        return ""
    alt = html.escape(titulo if titulo is not None else _texto(omath))
    return f'<math xmlns="http://www.w3.org/1998/Math/MathML" class="ecuacion" title="{alt}">{cuerpo}</math>'
