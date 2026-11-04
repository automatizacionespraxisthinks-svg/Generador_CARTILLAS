"""Pruebas de la auditoría del 21/09/2026: archivos como los guarda Word (marcadores, hipervínculos, campos,
estilos de carácter, imágenes con el mismo número interno), orden del esquema de Word, glosario activado y
desactivado en cartillas periódicas e ICFES, y la casilla del glosario en una cartilla ya generada."""
import io
import re
import zipfile

import pytest
from fastapi.testclient import TestClient
from lxml import etree

from app.generador import _el, limpiar_fragmento
from app.main import app
from tests.fabrica import ejercicio, imagen_gris
from tests.ooxml_orden import desordenes

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
WP = "{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}"
NSW = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
DATOS = {"grado": "77", "estructura": "E1", "tipo_material": "33", "plantilla": 1,
         "institucion": "Institución Educativa de prueba", "nombre": "Auditoría", "simulacro_n": 1}
ICFES = {"grado": "13", "estructura": "E5", "tipo_material": "71", "plantilla": 2,
         "institucion": "Institución Educativa de prueba", "nombre": "Auditoría ICFES", "simulacro_n": 1}


def como_word(datos):
    """El archivo tal como lo deja Word tras editarlo: _GoBack, un hipervínculo sin color con estilo de carácter,
    un campo de referencia cruzada con su resultado y un párrafo con identificador w14."""
    z = zipfile.ZipFile(io.BytesIO(datos))
    partes = {n: z.read(n) for n in z.namelist()}
    x = partes["word/document.xml"].decode()
    marca = "<w:t>Enunciado 1 de prueba"
    i = x.index(marca)
    ini_run = x.rindex("<w:r>", 0, i) if "<w:r>" in x[:i] else x.rindex("<w:r ", 0, i)
    fin_run = x.index("</w:r>", i) + len("</w:r>")
    run = x[ini_run:fin_run]
    enlace = run.replace("<w:rPr>", '<w:rPr><w:rStyle w:val="Hipervnculo"/>', 1)
    campo = ('<w:r><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText xml:space="preserve"> REF dato \\h </w:instrText></w:r>'
             '<w:r><w:fldChar w:fldCharType="separate"/></w:r><w:r><w:t xml:space="preserve"> VALOR-CONGELADO</w:t></w:r>'
             '<w:r><w:fldChar w:fldCharType="end"/></w:r>')
    nuevo = ('<w:bookmarkStart w:id="0" w:name="_GoBack"/><w:bookmarkEnd w:id="0"/>'
             f'<w:hyperlink r:id="rId999" w:history="1">{enlace}</w:hyperlink>{campo}')
    x = x[:ini_run] + nuevo + x[fin_run:]
    if 'xmlns:r=' not in x[:2000]:
        x = x.replace("<w:document ", '<w:document xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" ', 1)
    partes["word/document.xml"] = x.encode()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zo:
        for n, d in partes.items():
            zo.writestr(n, d)
    return buf.getvalue()


@pytest.fixture(scope="module")
def c(tmp_path_factory):
    img = imagen_gris(tmp_path_factory.mktemp("img") / "g.png")
    with TestClient(app) as cliente:
        archivos = [
            ("word.docx", como_word(ejercicio("Editado en Word", normal_justificado=True, clave="B",
                                               glosario=[(1, "grado", "Curso escolar.")])[1])),
            ejercicio("Gráfica uno", normal_justificado=True, imagen=img, clave="C"),
            ejercicio("Gráfica dos", normal_justificado=True, imagen=img, clave="D"),
            ejercicio("Funciones", grado="ICFES", submateria="", nivel="", normal_justificado=True, clave="A",
                      glosario=[(1, "grado", "Nivel de estudios.")]),
            ejercicio("Razones", grado="ICFES", submateria="", nivel="", normal_justificado=True, clave="B"),
        ]
        for nombre, datos in archivos:
            r = cliente.post("/api/cargar", files=[("archivos", (nombre, datos))], data={"solo_revisar": "false"}).json()[0]
            assert r["estado"] == "aceptado", (nombre, r["errores"])
        yield cliente


def armar(c, datos, seccion, cantidad, glosario):
    d = c.post("/api/cartillas", json={**datos, "glosario": glosario}).json()
    assert "id" in d, d
    cuerpo = [{"id": s["id"], "titulo": s["titulo"], "materia": s["materia"], "submateria": s["submateria"],
               "cantidad": cantidad if s["titulo"] == seccion else 0, "dificultad": "lib"} for s in d["secciones"]]
    d = c.put(f"/api/cartillas/{d['id']}/secciones", json={"secciones": cuerpo}).json()
    sec = next(s for s in d["secciones"] if s["cantidad"])
    c.post(f"/api/cartillas/{d['id']}/secciones/{sec['id']}/automatica", json={})
    return c.get(f"/api/cartillas/{d['id']}").json()


def generar(c, cid):
    r = c.post(f"/api/cartillas/{cid}/generar", json={})
    assert r.status_code == 200, r.text
    return r.json(), c.get(f"/api/cartillas/{cid}/archivo/docx").content


def texto(p):
    return "".join(t.text or "" for t in p.iter(W + "t"))


def test_fragmento_limpio():
    p = etree.fromstring(f'<w:p {NSW} xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml" w14:paraId="1A2B3C4D">'
                         '<w:bookmarkStart w:id="0" w:name="_GoBack"/><w:bookmarkEnd w:id="0"/>'
                         '<w:hyperlink><w:r><w:t>enlace</w:t></w:r></w:hyperlink>'
                         '<w:r><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText>REF x</w:instrText></w:r>'
                         '<w:r><w:fldChar w:fldCharType="separate"/></w:r><w:r><w:t> resultado</w:t></w:r>'
                         '<w:r><w:fldChar w:fldCharType="end"/></w:r>'
                         '<w:fldSimple w:instr="DATE"><w:r><w:t> 21/09</w:t></w:r></w:fldSimple>'
                         '<w:sdt><w:sdtPr><w:id w:val="5"/></w:sdtPr><w:sdtContent><w:r><w:t> control</w:t></w:r></w:sdtContent></w:sdt>'
                         '</w:p>')
    limpiar_fragmento(p)
    assert texto(p) == "enlace resultado 21/09 control"
    for tag in ("hyperlink", "fldChar", "instrText", "fldSimple", "sdt", "bookmarkStart", "bookmarkEnd"):
        assert next(p.iter(W + tag), None) is None, tag
    assert not any("paraId" in k for k in p.attrib)
    assert _el("w:p") is not None


def test_cartilla_con_archivos_de_word(c):
    d = armar(c, {**DATOS, "version": 1}, "MATEMÁTICAS I", 3, True)
    r, docx = generar(c, d["id"])
    raiz = etree.fromstring(zipfile.ZipFile(io.BytesIO(docx)).read("word/document.xml"))
    # nada del archivo de carga que pueda dañar el Word o imprimir algo distinto
    cuerpo = [p for p in raiz.iter(W + "p") if "info@praxisthinks.com" not in texto(p)]    # el correo del cierre es de la plantilla
    assert not [h for p in cuerpo for h in p.iter(W + "hyperlink")]
    assert not list(raiz.iter(W + "fldSimple")) and not [x for x in raiz.iter(W + "instrText") if "REF" in (x.text or "")]
    assert "VALOR-CONGELADO" in "".join(texto(p) for p in cuerpo)
    assert not [b for b in raiz.iter(W + "bookmarkStart") if b.get(W + "name") == "_GoBack"]
    assert not [s for p in cuerpo for s in p.iter(W + "rStyle")]
    # cada imagen con su propio número interno
    ids = [e.get("id") for e in raiz.iter(WP + "docPr")]
    assert len(ids) == len(set(ids)) and len(ids) >= 2
    # todo en el orden que exige el esquema de Word
    assert desordenes(docx) == []
    assert r["glosarios"] == 1


@pytest.mark.parametrize("datos,seccion,con,glosarios", [
    ({**DATOS, "version": 2}, "MATEMÁTICAS I", True, 1),
    ({**DATOS, "version": 3}, "MATEMÁTICAS I", False, 0),
    ({**ICFES, "version": 1}, "MATEMÁTICAS", True, 1),
    ({**ICFES, "version": 2}, "MATEMÁTICAS", False, 0),
])
def test_glosario_activado_y_desactivado(c, datos, seccion, con, glosarios):
    d = armar(c, datos, seccion, 2 if datos["grado"] == "13" else 3, con)
    r, docx = generar(c, d["id"])
    assert r["glosarios"] == glosarios
    raiz = etree.fromstring(zipfile.ZipFile(io.BytesIO(docx)).read("word/document.xml"))
    parrafos = list(raiz.iter(W + "p"))
    glos = [p for p in parrafos if texto(p).startswith("Glosario: ")]
    assert len(glos) == glosarios
    icfes = datos["grado"] == "13"
    assert not [p for p in parrafos if texto(p).startswith("➤")] if icfes else True
    # la última línea de cada pregunta deja 14 pt; lo que va antes queda unido a la pregunta
    for p in parrafos:
        t = texto(p)
        sp = p.find(f"{W}pPr/{W}spacing")
        if t.startswith("Glosario: "):
            anterior = texto(p.getprevious())
            assert anterior.startswith("D.") if icfes else anterior.startswith("➤")
            assert sp.get(W + "after") == "280" and p.find(f"{W}pPr/{W}keepNext") is None
        elif t.startswith("➤"):
            siguiente = texto(p.getnext())
            assert sp.get(W + "after") == ("20" if siguiente.startswith("Glosario: ") else "280")
        elif re.match(r"^D\.", t):
            siguiente = texto(p.getnext())
            final = not (siguiente.startswith("➤") or siguiente.startswith("Glosario: "))
            assert sp.get(W + "after") == ("280" if final else "20")
    assert desordenes(docx) == []


def test_cambiar_el_glosario_despues_de_generar(c):
    d = armar(c, {**DATOS, "version": 4}, "MATEMÁTICAS I", 3, False)
    generar(c, d["id"])
    usos = {x["ejercicio_id"]: x["veces_usado"] for s in c.get(f"/api/cartillas/{d['id']}").json()["secciones"] for x in s["items"]}
    d = c.put(f"/api/cartillas/{d['id']}/glosario", json={"incluir": True}).json()
    assert d["estado"] == "generada" and d["archivos"] == []          # el Word anterior ya no se puede descargar
    assert c.get(f"/api/cartillas/{d['id']}/archivo/docx").status_code == 404
    r, _ = generar(c, d["id"])
    assert r["glosarios"] == 1
    d = c.get(f"/api/cartillas/{d['id']}").json()
    assert d["archivos"] == ["docx", "xlsx"]
    # generar de nuevo no vuelve a contar el uso de los ejercicios
    assert {x["ejercicio_id"]: x["veces_usado"] for s in d["secciones"] for x in s["items"]} == usos
    # la misma casilla sin cambio no borra nada
    d = c.put(f"/api/cartillas/{d['id']}/glosario", json={"incluir": True}).json()
    assert d["archivos"] == ["docx", "xlsx"]
