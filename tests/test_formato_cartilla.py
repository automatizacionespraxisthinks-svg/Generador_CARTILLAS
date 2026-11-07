"""Pruebas del formato de la cartilla (Estándar v1.2): texto justificado con alineaciones del autor,
tablas centradas y compactas, columnas de 9,12 cm y glosario opcional por pregunta."""
import io
import sqlite3
import zipfile

import pytest
from docx.enum.text import WD_ALIGN_PARAGRAPH
from fastapi.testclient import TestClient
from lxml import etree

from app.main import app
from app.validador import ACEPTADO, RECHAZADO, validar
from app.validador.docx_lector import Parrafo
from app.validador.validador import alineacion_impresa
from tests.fabrica import ejercicio, imagen_gris

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
NSW = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"' 
DATOS = {"grado": "77", "estructura": "E1", "tipo_material": "33", "plantilla": 1,
         "institucion": "Institución Educativa de prueba", "nombre": "Formato", "simulacro_n": 1}
GLOSARIO = [(1, "prueba", "Ejercicio para medir lo aprendido."), (1, "grado", "Curso escolar")]


def reglas(r):
    return {m.regla for m in r.errores}


def validar_fab(**kw):
    nombre, datos = ejercicio(kw.pop("tema", "Fracciones"), **kw)
    return validar(datos, nombre)


# ================================================================== alineación que se imprime
@pytest.mark.parametrize("efectiva,directa,dibujo,esperada", [
    ("left", None, False, "both"),          # izquierda por defecto de Word: sale justificado
    ("both", None, False, "both"),
    ("left", "left", False, "left"),        # izquierda aplicada a mano: se conserva
    ("center", None, False, "center"),
    ("right", "right", False, "right"),
    ("left", None, True, "center"),         # imagen sola en su párrafo
])
def test_alineacion_impresa(efectiva, directa, dibujo, esperada):
    p = Parrafo(el=None, alineacion=efectiva, alineacion_directa=directa, dibujos=[object()] if dibujo else [])
    assert alineacion_impresa(p) == esperada


def test_aviso_de_alineacion_conservada():
    r = validar_fab(normal_justificado=True, alin_enunciado=WD_ALIGN_PARAGRAPH.CENTER)
    assert r.estado == ACEPTADO, r.errores
    assert any("centrado" in a.mensaje for a in r.avisos)
    r = validar_fab(normal_justificado=True, alin_enunciado=WD_ALIGN_PARAGRAPH.LEFT)
    assert any("a la izquierda" in a.mensaje for a in r.avisos)
    r = validar_fab(normal_justificado=True)
    assert not any("se imprimirá" in a.mensaje for a in r.avisos)


# ================================================================== TABLA DE GLOSARIO
def test_glosario_valido():
    r = validar_fab(glosario=GLOSARIO)
    assert r.estado == ACEPTADO, [(m.regla, m.mensaje) for m in r.errores]
    assert r.glosarios == [[{"termino": "prueba", "significado": "Ejercicio para medir lo aprendido."},
                            {"termino": "grado", "significado": "Curso escolar"}]]


def test_glosario_en_bloque_por_pregunta():
    r = validar_fab(tema="Lectura", materia="Lengua Castellana", submateria="Comprensión Lectora", pensamiento="", dba="",
                    n=2, bloque=True, glosario=[(2, "lectura", "Texto que se lee.")])
    assert r.estado == ACEPTADO, [(m.regla, m.mensaje) for m in r.errores]
    assert r.glosarios[0] == [] and r.glosarios[1][0]["termino"] == "lectura"


def test_glosario_termino_que_no_esta_en_el_texto():
    r = validar_fab(glosario=[(1, "hipotenusa", "Lado opuesto al ángulo recto.")])
    assert r.estado == RECHAZADO and reglas(r) == {29}
    assert "no aparece en el texto" in r.errores[0].mensaje


def test_glosario_maximo_tres_terminos():
    r = validar_fab(glosario=[(1, "prueba", "a."), (1, "grado", "b."), (1, "respuesta", "c."), (1, "opción", "d.")])
    assert r.estado == RECHAZADO and 29 in reglas(r)
    assert any("máximo es 3" in m.mensaje for m in r.errores)


@pytest.mark.parametrize("fila,texto", [
    ((2, "prueba", "Examen."), "número de la pregunta"),          # el suelto solo tiene la pregunta 1
    ((1, "prueba", ""), "Falta el significado"),
    ((1, "", "Examen."), "Falta el término"),
    ((1, "prueba", "x" * 151), "máximo es 150"),
    ((1, "prueba", "Examen [revisar esto luego]."), "corchetes"),
])
def test_glosario_filas_invalidas(fila, texto):
    r = validar_fab(glosario=[fila])
    assert r.estado == RECHAZADO, texto
    assert any(texto in m.mensaje for m in r.errores), [m.mensaje for m in r.errores]


def test_glosario_repetido():
    r = validar_fab(glosario=[(1, "prueba", "Examen."), (1, "Prueba", "Otra vez.")])
    assert any("repetido" in m.mensaje for m in r.errores)


def test_glosario_filas_vacias_se_ignoran():
    r = validar_fab(glosario=[("", "", "")])
    assert r.estado == ACEPTADO, r.errores
    assert r.glosarios == [[]]


def test_glosario_encabezado_exacto():
    from docx import Document
    nombre, datos = ejercicio("Fracciones", glosario=GLOSARIO)
    doc = Document(io.BytesIO(datos))
    doc.tables[-1].cell(0, 2).paragraphs[0].runs[0].text = "Definición"
    buf = io.BytesIO()
    doc.save(buf)
    r = validar(buf.getvalue(), nombre)
    assert reglas(r) == {29} and "Pregunta · Término · Significado" in r.errores[0].mensaje


# ================================================================== fórmulas en el glosario (2.7B)
ECUACION_OMML = ('<m:oMath xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math">'
                 '<m:sSup><m:e><m:r><m:t>a</m:t></m:r></m:e><m:sup><m:r><m:t>2</m:t></m:r></m:sup></m:sSup>'
                 '<m:r><m:t>=</m:t></m:r><m:r><m:t>4</m:t></m:r></m:oMath>')


def test_la_vista_previa_dibuja_la_ecuacion_en_su_sitio(c):
    """La fórmula va donde está en el Word, no pegada al final del párrafo."""
    import io

    from docx import Document
    from lxml import etree
    nombre, datos = ejercicio("Ecuación en el enunciado", clave="A", variante="eq")
    doc = Document(io.BytesIO(datos))
    objetivo = next(p for p in doc.paragraphs if p.text.startswith("Enunciado 1"))
    objetivo._p.append(etree.fromstring(ECUACION_OMML))
    buf = io.BytesIO()
    doc.save(buf)
    g = c.post("/api/cargar", files=[("archivos", (nombre, buf.getvalue()))],
               data={"solo_revisar": "false"}).json()[0]
    assert g["estado"] == "aceptado", g["errores"]
    eid = g["guardado"]["ids"][0] if g["guardado"].get("ids") else None
    previa = c.get(f"/api/banco/{eid}").json()["html"] if eid else ""
    if previa:
        assert "<math" in previa and "<msup>" in previa
        # va dentro del párrafo del enunciado, no al final de la ficha
        assert previa.index("<math") < previa.index("opcion")


def test_el_glosario_conserva_los_superindices():
    """Antes se guardaba el texto plano: «i² = −1» se imprimía «i2 = −1», que dice otra cosa."""
    from app.glosario import a_html, partes

    fila = {"termino": "unidad imaginaria", "significado": "cumple que i2 = −1.",
            "formato": {"significado": [{"t": "cumple que i"}, {"t": "2", "v": "sup"}, {"t": " = −1."}]}}
    altos = [(t, v) for t, _b, _c, v, _o in partes([fila]) if v]
    assert altos == [("2", "sup")]
    assert "<sup>2</sup>" in a_html([fila])


def test_el_glosario_admite_ecuaciones_de_word():
    """2.7B: en Matemáticas y Ciencias un significado sin fórmula muchas veces no dice nada."""
    from app.glosario import a_html, ecuacion, partes

    fila = {"termino": "cuadrado", "significado": "cuando ",
            "formato": {"significado": [{"t": "cuando "}, {"omml": ECUACION_OMML}]}}
    trozos = partes([fila])
    conformula = [o for _t, _b, _c, _v, o in trozos if o]
    assert len(conformula) == 1
    assert ecuacion({"omml": conformula[0]}) is not None
    assert trozos[-1][0] == "."                       # el punto final va aparte de la fórmula
    assert "a2=4" in a_html([fila])                   # en pantalla se lee el contenido de la fórmula


def test_el_glosario_sigue_sin_admitir_imagenes(c, tmp_path):
    """Una imagen no cabe en una línea de 8 pt: eso se sigue rechazando."""
    import io

    from docx import Document
    from docx.shared import Cm
    nombre, datos = ejercicio("Figura en el glosario", glosario=GLOSARIO, clave="A")
    doc = Document(io.BytesIO(datos))
    tabla = next(t for t in doc.tables if t.rows[0].cells[0].text.strip() == "Pregunta")
    tabla.rows[1].cells[2].paragraphs[0].add_run().add_picture(str(imagen_gris(tmp_path / "g.png")), width=Cm(1))
    buf = io.BytesIO()
    doc.save(buf)
    r = c.post("/api/revisar", files=[("archivos", (nombre, buf.getvalue()))]).json()[0]
    assert r["estado"] == "rechazado"
    assert any(e["regla"] == 29 and "imágenes" in e["mensaje"] for e in r["errores"]), r["errores"]


def test_glosario_va_al_final():
    from docx import Document
    nombre, datos = ejercicio("Fracciones", glosario=GLOSARIO)
    doc = Document(io.BytesIO(datos))
    rotulo = next(p for p in doc.paragraphs if p.text == "TABLA DE GLOSARIO")._p
    tabla = doc.tables[-1]._tbl
    excel = next(p for p in doc.paragraphs if p.text == "TABLA DE EXCEL")._p
    excel.addprevious(rotulo)
    excel.addprevious(tabla)
    buf = io.BytesIO()
    doc.save(buf)
    r = validar(buf.getvalue(), nombre)
    assert r.estado == RECHAZADO and 1 in reglas(r)
    assert any("va al final" in m.mensaje for m in r.errores)


# ================================================================== cartilla generada
@pytest.fixture(scope="module")
def c(tmp_path_factory):
    img = imagen_gris(tmp_path_factory.mktemp("img") / "figura.png")
    with TestClient(app) as cliente:
        for archivo in (
            ejercicio("Tabla de precios", normal_justificado=True, tabla=True, glosario=GLOSARIO, clave="B"),
            ejercicio("Esquema con imagen", normal_justificado=True, imagen=img, clave="A"),
            ejercicio("Poema centrado", normal_justificado=True, alin_enunciado=WD_ALIGN_PARAGRAPH.CENTER, clave="C"),
            ejercicio("Texto a la izquierda", normal_justificado=True, alin_enunciado=WD_ALIGN_PARAGRAPH.LEFT, clave="D"),
        ):
            nombre, datos = archivo
            r = cliente.post("/api/cargar", files=[("archivos", (nombre, datos))], data={"solo_revisar": "false"}).json()[0]
            assert r["estado"] == "aceptado", r["errores"]
        yield cliente


def armar(c, version, temas=("Tabla de precios", "Poema centrado", "Texto a la izquierda"), **extra):
    d = c.post("/api/cartillas", json={**DATOS, "version": version, **extra}).json()
    cuerpo = [{"id": s["id"], "titulo": s["titulo"], "materia": s["materia"], "submateria": s["submateria"],
               "cantidad": len(temas) if s["titulo"] == "MATEMÁTICAS I" else 0, "dificultad": "lib"} for s in d["secciones"]]
    d = c.put(f"/api/cartillas/{d['id']}/secciones", json={"secciones": cuerpo}).json()
    sec = next(s for s in d["secciones"] if s["cantidad"])
    for tema in temas:                                                 # en este orden: preguntas 1, 2 y 3
        cand = c.get(f"/api/cartillas/{d['id']}/candidatos", params={"seccion": sec["id"], "tematica": tema}).json()
        c.post(f"/api/cartillas/{d['id']}/items", json={"seccion": sec["id"], "ejercicio": cand["items"][0]["id"]})
    return c.get(f"/api/cartillas/{d['id']}").json()


def cuerpo_de(c, cid):
    datos = c.get(f"/api/cartillas/{cid}/archivo/docx").content
    z = zipfile.ZipFile(io.BytesIO(datos))
    return etree.fromstring(z.read("word/document.xml")), etree.fromstring(z.read("word/settings.xml"))


def texto(p):
    """Texto del párrafo con sus tabulaciones como «\t»."""
    return "".join("\t" if x.tag == W + "tab" else (x.text or "") for r in p.iter(W + "r") for x in r if x.tag in (W + "t", W + "tab"))


def parrafo(doc, inicio):
    for p in doc.iter(W + "p"):
        if texto(p).startswith(inicio):
            return p
    raise AssertionError(f"No está el párrafo «{inicio}»")


def jc(p):
    el = p.find(f"{W}pPr/{W}jc")
    return el.get(W + "val") if el is not None else None


def test_alineaciones_en_la_cartilla(c):
    d = armar(c, 1)
    assert c.post(f"/api/cartillas/{d['id']}/generar", json={}).status_code == 200
    doc, ajustes = cuerpo_de(c, d["id"])
    assert jc(parrafo(doc, "1. Enunciado 1 de prueba sobre Tabla")) == "both"           # justificado por defecto
    assert jc(parrafo(doc, "¿Cuál es la respuesta correcta de Tabla")) == "both"
    op = parrafo(doc, "A.\tLa opción")                                               # letra, tabulación y texto
    assert jc(op) == "both"                                                             # opciones justificadas
    ind = op.find(f"{W}pPr/{W}ind")
    assert ind.get(W + "left") == ind.get(W + "hanging") == str(round(0.45 * 567))
    assert jc(parrafo(doc, "2. Enunciado 1 de prueba sobre Poema")) == "center"         # alineación del autor
    assert jc(parrafo(doc, "3. Enunciado 1 de prueba sobre Texto")) == "left"
    # columnas de 9,12 cm (0,8 cm entre ellas) y versos que no se estiran
    cols = [x for x in doc.iter(W + "cols") if x.get(W + "num") == "2"]
    assert cols and cols[0].get(W + "space") == "454"
    assert ajustes.find(f"{W}compat/{W}doNotExpandShiftReturn") is not None


def test_tabla_centrada_compacta_y_con_bordes(c):
    d = armar(c, 2)
    assert c.post(f"/api/cartillas/{d['id']}/generar", json={}).status_code == 200
    doc, _ = cuerpo_de(c, d["id"])
    tabla = next(t for t in doc.iter(W + "tbl") if "Producto" in "".join(x.text or "" for x in t.iter(W + "t")))
    pr = tabla.find(W + "tblPr")
    assert pr.find(W + "tblStyle") is None                         # no depende de estilos del archivo de carga
    assert pr.find(W + "jc").get(W + "val") == "center" and pr.find(W + "tblInd") is None
    bordes = pr.find(W + "tblBorders")
    assert bordes is not None and {b.tag.split("}")[1] for b in bordes} >= {"top", "left", "bottom", "right", "insideH", "insideV"}
    for p in tabla.iter(W + "p"):
        sp = p.find(f"{W}pPr/{W}spacing")
        assert sp.get(W + "after") == "0" and sp.get(W + "before") == "0" and sp.get(W + "line") == "240"
    # 3.8: la tabla puede continuar en la columna siguiente, pero el corte cae entre filas y el
    # encabezado se repite; solo la última fila queda amarrada a lo que viene detrás
    filas = tabla.findall(W + "tr")
    assert len(filas) > 2
    for i, tr in enumerate(filas):
        assert tr.find(f"{W}trPr/{W}cantSplit") is not None, f"la fila {i} se podría partir por la mitad"
        assert (tr.find(f"{W}trPr/{W}tblHeader") is not None) is (i == 0)
        amarradas = [x for x in tr.iter(W + "p") if x.find(f"{W}pPr/{W}keepNext") is not None]
        assert bool(amarradas) is (i == len(filas) - 1), f"fila {i}: keepNext donde no toca"
    mar = pr.find(W + "tblCellMar")
    assert mar.find(W + "top").get(W + "w") == mar.find(W + "bottom").get(W + "w") == "20"   # 1 pt
    # 6 pt de aire a los dos lados: una tabla no tiene espaciado propio, se lo ponen sus vecinos (3.5B)
    assert tabla.getnext().find(f"{W}pPr/{W}spacing").get(W + "before") == "120"
    assert tabla.getprevious().find(f"{W}pPr/{W}spacing").get(W + "after") == "120"


def test_glosario_solo_si_la_cartilla_lo_incluye(c):
    d = armar(c, 3)
    assert d["glosario"] is False and d["con_glosario"] == 1
    r = c.post(f"/api/cartillas/{d['id']}/generar", json={}).json()
    assert r["glosarios"] == 0
    doc, _ = cuerpo_de(c, d["id"])
    assert not any("".join(x.text or "" for x in p.iter(W + "t")).startswith("Glosario") for p in doc.iter(W + "p"))
    assert "glosario" not in c.get(f"/api/cartillas/{d['id']}/vista-previa").json()["html"]

    d = c.put(f"/api/cartillas/{d['id']}/glosario", json={"incluir": True}).json()
    assert d["glosario"] is True
    assert 'class="glosario"' in c.get(f"/api/cartillas/{d['id']}/vista-previa").json()["html"]
    r = c.post(f"/api/cartillas/{d['id']}/generar", json={}).json()
    assert r["glosarios"] == 1
    doc, _ = cuerpo_de(c, d["id"])
    g = parrafo(doc, "Glosario:")
    assert texto(g) == "Glosario: prueba: Ejercicio para medir lo aprendido. grado: Curso escolar."   # el sistema pone el punto final
    negritas = ["".join(x.text or "" for x in r_.iter(W + "t")) for r_ in g.iter(W + "r") if r_.find(f"{W}rPr/{W}b") is not None]
    assert negritas == ["prueba:", " grado:"]
    assert all(r_.find(f"{W}rPr/{W}sz").get(W + "val") == "16" for r_ in g.iter(W + "r"))      # 8 pt
    # va debajo de la línea ➤, al margen, y es la última línea de la pregunta (14 pt hasta la siguiente)
    hermanos = list(g.getparent())
    i = hermanos.index(g)
    assert texto(hermanos[i - 1]).startswith("➤") and texto(hermanos[i - 2]).startswith("D.\t")
    assert g.find(f"{W}pPr/{W}ind") is None
    assert g.find(f"{W}pPr/{W}spacing").get(W + "after") == "280"
    assert hermanos[i - 1].find(f"{W}pPr/{W}spacing").get(W + "after") == "20"
    cursivas = [r_ for r_ in g.iter(W + "r") if r_.find(f"{W}rPr/{W}i") is not None]
    assert cursivas == []                                   # «Glosario:» en redonda


def test_banco_muestra_el_glosario(c):
    res = c.get("/api/banco", params={"texto": "Tabla de precios"}).json()
    item = res["items"][0]
    assert item["glosario"] == 2
    d = c.get(f"/api/banco/{item['id']}").json()
    assert d["glosario"][0]["termino"] == "prueba" and 'class="glosario"' in d["html"]


# ================================================================== 3.8 aprovechar el espacio
def keep(p):
    return p.find(f"{W}pPr/{W}keepNext") is not None


def test_la_pregunta_se_puede_cortar_donde_haga_falta(c):
    """3.8: la pregunta se reparte entre columnas por donde convenga —también entre las opciones—
    para no dejar espacio sin usar. Lo único que no se separa es la figura del texto que la acompaña."""
    d = armar(c, 20)
    assert c.post(f"/api/cartillas/{d['id']}/generar", json={}).status_code == 200
    doc, _ = cuerpo_de(c, d["id"])
    assert not keep(parrafo(doc, "¿Cuál es la respuesta correcta de Tabla"))      # último trozo del enunciado
    assert not keep(parrafo(doc, "1. Enunciado 1 de prueba sobre Tabla"))         # se puede cortar antes de la tabla
    for letra in "ABCD":                                                          # las opciones ya no se encadenan
        assert not keep(parrafo(doc, f"{letra}.	La opción"))
    assert not keep(parrafo(doc, "➤ "))                                           # la línea de datos, igual


def test_las_figuras_llevan_aire_arriba_y_abajo(c):
    """3.5B: la imagen no queda pegada al texto; lleva 6 pt por arriba y por abajo, igual que la tabla."""
    from app.generador import ESPACIO_FIGURA

    d = armar(c, 22, temas=("Esquema con imagen",))
    assert c.post(f"/api/cartillas/{d['id']}/generar", json={}).status_code == 200
    doc, _ = cuerpo_de(c, d["id"])
    # el párrafo de la imagen, ya dentro del cuerpo (la portada tiene sus propios logos)
    enunciado = parrafo(doc, "1. Enunciado 1 de prueba sobre Esquema")
    figura = enunciado.getnext()
    assert figura.find(f".//{W}drawing") is not None, "después del enunciado debería ir la imagen"
    sp = figura.find(f"{W}pPr/{W}spacing")
    assert sp.get(f"{W}before") == sp.get(f"{W}after") == str(ESPACIO_FIGURA * 20)


# ================================================================== portadas (completa y media)
def test_las_dos_portadas_existen_y_traen_el_qr():
    from docx import Document

    from app.generador import MEDIA_DOCX, PORTADAS, W, texto_de
    assert set(PORTADAS) == {"completa", "media"}
    for ruta in PORTADAS.values():
        assert ruta.exists(), f"falta la plantilla {ruta.name}"
        doc = Document(str(ruta))
        textos = [texto_de(x).strip() for x in doc.element.body.iter(f"{W}p")]
        assert "¡ESCANEA Y APRENDE!" in textos, f"{ruta.name} se quedó sin el recuadro del QR"
        assert "¡Prueba finalizada!" in textos, f"{ruta.name} se quedó sin el cierre"
        assert any("[[CUERPO]]" in x for x in textos), f"{ruta.name} se quedó sin la marca del cuerpo"
    # en la media portada el cuerpo arranca debajo, en la misma página
    doc = Document(str(MEDIA_DOCX))
    assert "INSTRUCCIONES:" in texto_de(doc.element.body)


def test_la_media_portada_lleva_los_datos_de_la_cartilla(c):
    from docx import Document

    d = armar(c, 30)
    assert c.put(f"/api/cartillas/{d['id']}/portada",
                 json={"portada": "media", "titulo": "Ciencias Sociales y Ciudadanas"}).status_code == 200
    assert c.post(f"/api/cartillas/{d['id']}/generar", json={}).status_code == 200
    doc, _ = cuerpo_de(c, d["id"])
    textos = [texto(x).strip() for x in doc.iter(f"{W}p")]
    assert "CIENCIAS SOCIALES Y CIUDADANAS" in textos          # el título va en mayúsculas
    assert f"Código Cartilla: {d['codigo']}" in textos
    assert "3 preguntas" in textos
    assert not [x for x in textos if "6606550101" in x], "quedó el código de la cartilla de muestra"


def test_la_ilustracion_de_la_portada_se_puede_cambiar_y_quitar(c, tmp_path):
    from app.bd import Cartilla, Sesion

    d = armar(c, 31)
    png = imagen_gris(tmp_path / "portada.png").read_bytes()
    r = c.post(f"/api/cartillas/{d['id']}/imagen", files={"archivo": ("portada.png", png, "image/png")})
    assert r.status_code == 200 and r.json()["imagen"] is True and r.json()["imagen_nombre"] == "portada.png"
    assert c.get(f"/api/cartillas/{d['id']}/imagen").content == png
    with Sesion() as s:                                        # y llega al Word
        assert s.get(Cartilla, d["id"]).imagen == png
    assert c.delete(f"/api/cartillas/{d['id']}/imagen").json()["imagen"] is False
    assert c.get(f"/api/cartillas/{d['id']}/imagen").status_code == 404


def test_la_portada_no_acepta_cualquier_archivo(c):
    d = armar(c, 32)
    r = c.post(f"/api/cartillas/{d['id']}/imagen", files={"archivo": ("x.txt", b"no soy una imagen", "text/plain")})
    assert r.status_code == 400 and "PNG" in r.json()["detail"]
    assert c.put(f"/api/cartillas/{d['id']}/portada", json={"portada": "triple"}).status_code == 400


def test_el_margen_inferior_deja_sitio_al_pie(c):
    """3.1: la línea que separa las dos columnas se dibuja hasta el borde de la caja del último párrafo,
    que incluye los 14 pt de detrás de cada pregunta. Con el margen de 1,27 cm esa línea se metía encima
    del número de página; con 1,55 cm ya no (comprobado en el PDF de una cartilla de 25 páginas)."""
    from app.generador import MARGEN_INFERIOR

    assert MARGEN_INFERIOR >= 880                                    # 1,55 cm en twips
    d = armar(c, 21)
    assert c.post(f"/api/cartillas/{d['id']}/generar", json={}).status_code == 200
    doc, _ = cuerpo_de(c, d["id"])
    for mar in doc.iter(f"{W}pgMar"):
        assert mar.get(f"{W}bottom") == str(MARGEN_INFERIOR)
        assert mar.get(f"{W}top") == "720" and mar.get(f"{W}footer") == "283"


def test_migracion_agrega_el_glosario(tmp_path):
    from app import migraciones
    from app.bd import usar_base
    from app.semilla import poblar
    ruta = tmp_path / "vieja.db"
    usar_base(f"sqlite:///{ruta.as_posix()}")
    poblar()
    con = sqlite3.connect(ruta)       # se simula una base de la versión 4, sin las columnas nuevas
    con.execute("ALTER TABLE ejercicio DROP COLUMN glosario")
    con.execute("ALTER TABLE cartilla DROP COLUMN glosario")
    con.execute("UPDATE version_esquema SET version = 4")
    con.commit()
    con.close()
    assert migraciones.aplicar() == migraciones.VERSION_ACTUAL
    con = sqlite3.connect(ruta)
    assert "glosario" in [f[1] for f in con.execute("PRAGMA table_info(ejercicio)")]
    assert "glosario" in [f[1] for f in con.execute("PRAGMA table_info(cartilla)")]
    con.close()


def test_completar_el_texto_letras_alineadas(tmp_path):
    """Sin enunciado: «12.⇥A.⇥went» y debajo «B.⇥…» con la B justo bajo la A (Estándar 3.5B)."""
    from app.generador import COL_LETRA, COL_NUMERO, formato_parrafo, _letra_con_tab, _numero
    from app.generador import _el
    a = _el("w:p")
    r = _el("w:r")
    t = _el("w:t")
    t.text = "A. went"
    r.append(t)
    a.append(r)
    _letra_con_tab(a, "A")
    formato_parrafo(a, sangria=COL_NUMERO + COL_LETRA, tabs=[COL_NUMERO])
    a.insert(1, _numero(12, tab=True))
    assert texto(a) == "12.\tA.\twent"
    assert a.find(f"{W}pPr/{W}tabs/{W}tab").get(W + "pos") == str(round(COL_NUMERO * 567))
    b = _el("w:p")
    r = _el("w:r")
    t = _el("w:t")
    t.text = "B. "
    r.append(t)
    r2 = _el("w:r")
    t2 = _el("w:t")
    t2.text = "  goes"
    r2.append(t2)
    b.extend([r, r2])
    _letra_con_tab(b, "B")
    formato_parrafo(b, sangria=COL_NUMERO + COL_LETRA, colgante=COL_LETRA)
    assert texto(b) == "B.\tgoes"
    ind = b.find(f"{W}pPr/{W}ind")
    # la primera línea de B empieza donde está la A: sangría izquierda menos francesa = columna del número
    assert int(ind.get(W + "left")) - int(ind.get(W + "hanging")) == round((COL_NUMERO + COL_LETRA) * 567) - round(COL_LETRA * 567)


@pytest.mark.parametrize("filas,repite", [(2, False), (3, True), (8, True)])
def test_el_encabezado_se_repite_solo_si_vale_la_pena(filas, repite):
    """Una tabla de dos filas no se parte, así que no tiene sentido repetirle el encabezado."""
    from app.generador import ajustar_tabla
    from app.validador.docx_lector import Estilos

    celda = '<w:tc><w:p><w:r><w:t>x</w:t></w:r></w:p></w:tc>'
    tbl = etree.fromstring(f"<w:tbl {NSW}>" + f"<w:tr>{celda}</w:tr>" * filas + "</w:tbl>")
    ajustar_tabla(tbl, Estilos(None, None), juntar=True)
    trs = tbl.findall(W + "tr")
    assert all(tr.find(f"{W}trPr/{W}cantSplit") is not None for tr in trs)
    assert (trs[0].find(f"{W}trPr/{W}tblHeader") is not None) is repite
    assert all(tr.find(f"{W}trPr/{W}tblHeader") is None for tr in trs[1:])


def tabla_de(*filas):
    """Una tabla con esas filas, todas alineadas a la izquierda, para probar el centrado."""
    celda = '<w:tc><w:p><w:pPr><w:jc w:val="left"/></w:pPr><w:r><w:t>%s</w:t></w:r></w:p></w:tc>'
    cuerpo = "".join("<w:tr>" + "".join(celda % c for c in fila) + "</w:tr>" for fila in filas)
    return etree.fromstring(f"<w:tbl {NSW}>{cuerpo}</w:tbl>")


def alineaciones(tbl):
    """[[alineación de cada celda] por fila]"""
    return [[tc.find(f".//{W}jc").get(W + "val") for tc in fila.findall(W + "tc")] for fila in tbl.findall(W + "tr")]


def test_la_primera_fila_de_la_tabla_sale_centrada():
    """El encabezado siempre se centra; el texto largo conserva su alineación."""
    from app.generador import ajustar_tabla
    from app.validador.docx_lector import Estilos

    tbl = tabla_de(["Producto"], ["Jugo de naranja natural"])
    ajustar_tabla(tbl, Estilos(None, None), juntar=False)
    assert alineaciones(tbl) == [["center"], ["left"]]


def test_las_columnas_de_numeros_y_palabras_cortas_se_centran():
    """3.5B: una columna de datos cortos se ve mejor centrada; la de texto largo, no se toca."""
    from app.generador import ajustar_tabla
    from app.validador.docx_lector import Estilos

    tbl = tabla_de(["Objeto", "Material", "Masa (g)", "Observación"],
                   ["Clip pequeño", "Hierro", "8", "Se pega al imán con facilidad"],
                   ["Tornillo grande", "Hierro", "16", "Se pega solo por la punta"],
                   ["Borrador", "Caucho", "40", "No reacciona de ninguna manera"])
    ajustar_tabla(tbl, Estilos(None, None), juntar=False)
    filas = alineaciones(tbl)
    assert filas[0] == ["center"] * 4                                  # el encabezado, siempre
    for fila in filas[1:]:
        # «Tornillo grande» es largo, así que su columna no se centra; material y masa sí
        assert fila == ["left", "center", "center", "left"], fila
    # y las celdas centradas también quedan a media altura
    centradas = [tc for fila in tbl.findall(W + "tr") for tc in fila.findall(W + "tc")
                 if tc.find(f"{W}tcPr/{W}vAlign") is not None]
    assert len(centradas) == 4 + 2 * 3                                 # encabezado + dos columnas de datos


def test_una_tabla_con_celdas_combinadas_no_se_toca():
    """Si las filas no tienen el mismo número de celdas, no se puede razonar por columna."""
    from app.generador import ajustar_tabla
    from app.validador.docx_lector import Estilos

    tbl = tabla_de(["Resumen"], ["Dato", "8"])
    ajustar_tabla(tbl, Estilos(None, None), juntar=False)
    assert alineaciones(tbl) == [["center"], ["left", "left"]]


@pytest.mark.parametrize("items,esperado", [
    (["texto", "texto"], [False, False]),          # texto corrido: se puede partir donde haga falta
    (["texto", "figura", "texto"], [False, True, False]),   # se puede cortar antes de la figura, no después
    (["figura", "texto"], [True, False]),          # la figura nunca se separa de lo que la interpreta
    (["texto"], [False]),                          # un solo trozo: suelto, para que bajen las opciones
])
def test_que_se_queda_pegado_dentro_del_enunciado(items, esperado):
    from app.generador import _pegar_al_siguiente

    class Trozo:
        def __init__(self, clase):
            self.dibujos = ["img"] if clase == "figura" else []

    enunciado = [Trozo(x) for x in items]
    assert [_pegar_al_siguiente(enunciado, j) for j in range(len(items))] == esperado


def test_la_verificacion_lee_las_opciones_que_son_imagenes():
    """«¿Cuál de estos rectángulos…?»: la opción es una figura y el párrafo dice solo «A.».

    Exigir un espacio tras el punto dejaba esas preguntas sin opciones, y la verificación cruzada
    impedía generar la cartilla entera aunque el Word estuviera bien.
    """
    import io

    from docx import Document

    from app.generador import _leer_cartilla_generada

    doc = Document()
    for texto in ("12. ¿En cuál rectángulo está sombreada esa fracción?", "A.", "B.", "C.", "D.",
                  "13. Pregunta normal", "A. uno", "B. dos", "C. tres", "D. cuatro"):
        doc.add_paragraph(texto)
    buf = io.BytesIO()
    doc.save(buf)

    leidas = _leer_cartilla_generada(buf.getvalue())
    assert [(q["numero"], q["opciones"]) for q in leidas] == [
        (12, ["A", "B", "C", "D"]), (13, ["A", "B", "C", "D"])]


def test_el_color_del_ejercicio_llega_a_la_cartilla(c, tmp_path):
    """No basta con admitirlo al subir: el generador borraba el color de cada run al copiarlo."""
    import io
    import re

    from docx import Document
    from docx.shared import RGBColor

    from app.generador import W
    from tests.fabrica import ejercicio

    nombre, datos = ejercicio("Banderas de América", grado="77", materia="Ciencias Sociales",
                              submateria="", pensamiento="Pensamiento social", dba="DBA 2",
                              competencia="Interpretación y análisis de perspectivas", clave="B",
                              variante="color")
    doc = Document(io.BytesIO(datos))
    objetivo = next(p for p in doc.paragraphs if p.text.startswith("A. "))
    objetivo.runs[-1].font.color.rgb = RGBColor(0xC0, 0x00, 0x00)     # rojo
    buf = io.BytesIO()
    doc.save(buf)

    r = c.post("/api/cargar", files=[("archivos", (nombre, buf.getvalue()))],
               data={"solo_revisar": "false"}).json()[0]
    assert r["estado"] == "aceptado", r.get("errores")

    d = c.post("/api/cartillas", json={"grado": "77", "estructura": "E4", "tipo_material": "55",
                                       "plantilla": 1, "codigo_materia": "04", "institucion": "Color",
                                       "nombre": "COLOR", "simulacro_n": 8, "version": 40}).json()
    cid = d["id"]
    sec = c.put(f"/api/cartillas/{cid}/secciones", json={"secciones": [
        {"titulo": "CIENCIAS SOCIALES", "materia": "Ciencias Sociales", "submateria": "", "cantidad": 1,
         "dificultad": "lib"}]}).json()["secciones"][0]
    cand = c.get(f"/api/cartillas/{cid}/candidatos", params={"seccion": sec["id"]}).json()["items"]
    elegido = next(x for x in cand if x["tematica"] == "Banderas de América")
    c.post(f"/api/cartillas/{cid}/items", json={"seccion": sec["id"], "ejercicio": elegido["id"]})
    assert c.post(f"/api/cartillas/{cid}/generar", json={}).status_code == 200

    word = c.get(f"/api/cartillas/{cid}/archivo/docx").content
    colores = set(re.findall(r'<w:color w:val="([0-9A-Fa-f]{6})"', Document(io.BytesIO(word)).element.body.xml))
    assert "C00000" in {x.upper() for x in colores}, f"el rojo no llegó a la cartilla: {colores}"
