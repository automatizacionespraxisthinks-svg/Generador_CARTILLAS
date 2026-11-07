"""Las ecuaciones de Word se ven bien en la pantalla (MathML).

Antes la vista previa pegaba el texto suelto de la fórmula, y eso **cambia lo que dice**:
«F₁/A₁ = F₂/A₂» se leía «F1A1 = F2A2», que es un producto y no un cociente.
"""
from lxml import etree

from app.mathml import a_mathml

M = 'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math"'


def omml(cuerpo):
    return etree.fromstring(f"<m:oMath {M}>{cuerpo}</m:oMath>")


def r(texto):
    return f"<m:r><m:t>{texto}</m:t></m:r>"


def test_una_fraccion_con_subindices_se_dibuja_como_fraccion():
    """El caso real: la prensa hidráulica de FIS-88-000013."""
    sub = f"<m:sSub><m:e>{r('F')}</m:e><m:sub>{r('1')}</m:sub></m:sSub>"
    den = f"<m:sSub><m:e>{r('A')}</m:e><m:sub>{r('1')}</m:sub></m:sSub>"
    salida = a_mathml(omml(f"<m:f><m:num>{sub}</m:num><m:den>{den}</m:den></m:f>"))
    assert "<mfrac>" in salida and "<msub>" in salida
    assert salida.count("<mfrac>") == 1
    assert "<mi>F</mi>" in salida and "<mn>1</mn>" in salida


def test_potencias_raices_y_parentesis():
    assert "<msup>" in a_mathml(omml(f"<m:sSup><m:e>{r('x')}</m:e><m:sup>{r('2')}</m:sup></m:sSup>"))
    assert "<msqrt>" in a_mathml(omml(f"<m:rad><m:deg/><m:e>{r('9')}</m:e></m:rad>"))
    cubica = a_mathml(omml(f"<m:rad><m:deg>{r('3')}</m:deg><m:e>{r('8')}</m:e></m:rad>"))
    assert "<mroot>" in cubica
    parent = a_mathml(omml(f"<m:d><m:e>{r('a')}</m:e></m:d>"))
    assert "<mo>(</mo>" in parent and "<mo>)</mo>" in parent


def test_sumatoria_con_limites():
    nary = (f'<m:nary><m:naryPr><m:chr m:val="∑"/></m:naryPr>'
            f"<m:sub>{r('i=1')}</m:sub><m:sup>{r('n')}</m:sup><m:e>{r('x')}</m:e></m:nary>")
    salida = a_mathml(omml(nary))
    assert "<msubsup>" in salida and "∑" in salida


def test_los_numeros_las_letras_y_los_signos_van_marcados_aparte():
    """MathML pone en cursiva las variables y derecho los números: así se lee como una fórmula."""
    salida = a_mathml(omml(r("2x+1")))
    assert "<mn>2</mn>" in salida and "<mi>x</mi>" in salida and "<mo>+</mo>" in salida


def test_lo_que_no_esta_contemplado_no_se_pierde():
    """Ante una construcción rara, se procesan sus hijos: en el peor caso se ve el texto."""
    salida = a_mathml(omml(f"<m:borderBox><m:e>{r('E=mc')}</m:e></m:borderBox>"))
    assert "<mi>E</mi>" in salida and "<mi>mc</mi>" in salida


def test_una_ecuacion_vacia_no_estorba():
    assert a_mathml(omml("")) == ""
    assert a_mathml(None) == ""


def test_el_titulo_guarda_el_texto_para_quien_no_vea_la_formula():
    salida = a_mathml(omml(r("x=1")))
    assert 'title="x=1"' in salida


# ================================================================== tamaño con el que se imprimen
def _fraccion():
    return etree.fromstring(
        f'<m:oMath {M} xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<m:f><m:num><m:r><m:t>3</m:t></m:r></m:num>'
        '<m:den><m:r><m:t>8</m:t></m:r></m:den></m:f>'
        '<m:r><m:t>=</m:t></m:r></m:oMath>')


def _tamanos(ecuacion):
    from app.generador import M as MM, W
    return [int(sz.get(W + "val")) / 2 for r in ecuacion.iter(MM + "r")
            for sz in r.findall(W + "rPr/" + W + "sz")]


def test_la_fraccion_dentro_de_una_frase_se_declara_mas_grande_para_salir_igual():
    """Word encoge al 73 % el numerador y el denominador: hay que compensarlo o la fracción sale diminuta."""
    from app.generador import _ecuacion_al_tamano

    tam = _tamanos(_ecuacion_al_tamano(_fraccion(), 9))
    assert sorted(tam) == [9.0, 12.5, 12.5], tam     # el «=» a 9; el 3 y el 8, compensados


def test_la_fraccion_sola_en_su_parrafo_no_se_compensa():
    """Sola en su párrafo —una celda de tabla— Word no la encoge: compensarla la dejaría enorme."""
    from docx import Document

    from app.generador import W, _ecuacion_al_tamano

    doc = Document()
    p = doc.add_paragraph()._p
    ec = _fraccion()
    p.append(ec)
    assert set(_tamanos(_ecuacion_al_tamano(ec, 8))) == {8.0}

    # y si el párrafo SÍ lleva texto, vuelve a compensarse
    r = p.makeelement(W + "r", {})
    t = p.makeelement(W + "t", {})
    t.text = "A. "
    r.append(t)
    p.insert(0, r)
    assert 11.0 in _tamanos(_ecuacion_al_tamano(ec, 8))
