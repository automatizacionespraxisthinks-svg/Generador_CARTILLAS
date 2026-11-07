"""Cuadernillo de varias sesiones: dos cartillas en un solo Word, cada una con su numeración."""
import io
import re

import pytest
from docx import Document
from fastapi.testclient import TestClient

from app.generador import W
from app.main import app
from tests.fabrica import ejercicio

PALABRAS = ["uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve", "diez"]


@pytest.fixture(scope="module")
def c():
    with TestClient(app) as cliente:
        yield cliente


def sembrar(c, cuantos, tema, **kw):
    for i in range(cuantos):
        _, datos = ejercicio(tema, variante=PALABRAS[i], **kw)
        r = c.post("/api/cargar", files=[("archivos", (f"{tema[:5]}_{PALABRAS[i]}.docx", datos))],
                   data={"solo_revisar": "false"}).json()[0]
        assert r["estado"] == "aceptado", r.get("errores")


def armar_cartilla(c, nombre, materia, tema, cuantos, grado="77", codigo_materia="03", plantilla=1):
    """Deja una cartilla generada con `cuantos` preguntas de ese tema y devuelve su id y su código."""
    sembrar(c, cuantos, tema, grado=grado, materia=materia,
            submateria="Matemáticas I" if materia == "Matemáticas" else "")
    d = c.post("/api/cartillas", json={"grado": grado, "estructura": "E4", "tipo_material": "33",
                                       "plantilla": plantilla, "codigo_materia": codigo_materia,
                                       "institucion": "Colegio", "nombre": nombre, "simulacro_n": 1,
                                       "version": 1}).json()
    cid = d["id"]
    sec = c.put(f"/api/cartillas/{cid}/secciones", json={"secciones": [
        {"titulo": materia.upper(), "materia": materia, "submateria": "*", "cantidad": cuantos,
         "dificultad": "lib"}]}).json()["secciones"][0]
    cand = c.get(f"/api/cartillas/{cid}/candidatos", params={"seccion": sec["id"]}).json()["items"]
    for x in cand[:cuantos]:
        c.post(f"/api/cartillas/{cid}/items", json={"seccion": sec["id"], "ejercicio": x["id"]})
    g = c.post(f"/api/cartillas/{cid}/generar", json={})
    assert g.status_code == 200, g.json()
    return cid, d["codigo"]


@pytest.fixture(scope="module")
def dos(c):
    a = armar_cartilla(c, "SESION 1", "Matemáticas", "Ecuaciones de primer grado", 3)
    b = armar_cartilla(c, "SESION 2", "Ciencias Sociales", "Ramas del poder público", 2, codigo_materia="04")
    return a, b


def numeros_y_textos(datos):
    """Los números de pregunta del Word, en orden de lectura."""
    doc = Document(io.BytesIO(datos))
    return [int(m.group(1)) for p in doc.paragraphs
            for m in [re.match(r"^(\d+)\.\s", p.text.strip())] if m]


def test_previo_describe_las_sesiones(c, dos):
    (ida, cod_a), (idb, cod_b) = dos
    r = c.post("/api/cuadernillo", json={"cartillas": [ida, idb]})
    assert r.status_code == 200, r.json()
    d = r.json()
    assert [x["codigo"] for x in d["sesiones"]] == [cod_a, cod_b]
    assert [x["portada"] for x in d["sesiones"]] == ["completa", "media"]
    assert d["preguntas"] == 5


def test_cada_sesion_vuelve_a_numerar_desde_uno(c, dos):
    (ida, _), (idb, _) = dos
    r = c.post("/api/cuadernillo/generar", json={"cartillas": [ida, idb], "nombre": "Cuadernillo"})
    assert r.status_code == 200, r.content[:300]
    assert r.headers["content-disposition"].endswith("Cuadernillo.docx")
    assert numeros_y_textos(r.content) == [1, 2, 3, 1, 2]


def test_lleva_el_codigo_de_cada_sesion_a_la_vista(c, dos):
    (ida, cod_a), (idb, cod_b) = dos
    r = c.post("/api/cuadernillo/generar", json={"cartillas": [ida, idb]})
    texto = Document(io.BytesIO(r.content)).element.body.xml
    assert f"Código Cartilla: {cod_a}" in texto      # portada entera de la primera sesión
    assert f"Código Cartilla: {cod_b}" in texto      # media portada de la segunda
    assert "6606550101" not in texto                 # ningún código de ejemplo de la plantilla


def test_la_segunda_sesion_abre_en_pagina_impar(c, dos):
    """La media portada tiene que empezar su propia sección, y esa sección arranca en página impar."""
    (ida, idb) = dos[0][0], dos[1][0]
    r = c.post("/api/cuadernillo/generar", json={"cartillas": [ida, idb]})
    doc = Document(io.BytesIO(r.content))
    tipos = [t.get(W + "val") for sect in doc.element.body.iter(W + "sectPr")
             for t in sect.findall(W + "type")]
    # cada tipo dice cómo empieza SU sección: portada · cuerpo 1 · media portada 2 · cuerpo 2 · cierre
    assert tipos == ["nextPage", "nextPage", "oddPage", "continuous", "nextPage"], tipos


def test_una_sola_cartilla_no_es_un_cuadernillo(c, dos):
    r = c.post("/api/cuadernillo", json={"cartillas": [dos[0][0]]})
    assert r.status_code == 400 and "al menos" in r.json()["detail"]


def test_no_se_repite_la_misma_cartilla(c, dos):
    r = c.post("/api/cuadernillo", json={"cartillas": [dos[0][0], dos[0][0]]})
    assert r.status_code == 400 and "repetida" in r.json()["detail"]


def test_las_sesiones_son_del_mismo_grado(c, dos):
    otra, _ = armar_cartilla(c, "OTRO GRADO", "Matemáticas", "Áreas de polígonos", 2, grado="88")
    r = c.post("/api/cuadernillo", json={"cartillas": [dos[0][0], otra]})
    assert r.status_code == 400 and "mismo grado" in r.json()["detail"]


def test_hay_que_generar_las_cartillas_antes(c, dos):
    d = c.post("/api/cartillas", json={"grado": "77", "estructura": "E4", "tipo_material": "33", "plantilla": 1,
                                       "codigo_materia": "03", "institucion": "Colegio", "nombre": "BORRADOR",
                                       # otra versión: el código no puede repetir el de la sesión 1
                                       "simulacro_n": 2, "version": 2}).json()
    r = c.post("/api/cuadernillo", json={"cartillas": [dos[0][0], d["id"]]})
    assert r.status_code == 400 and "todavía no se ha generado" in r.json()["detail"]


def test_el_nombre_del_archivo_se_revisa(c, dos):
    (ida, _), (idb, _) = dos
    r = c.post("/api/cuadernillo/generar", json={"cartillas": [ida, idb], "nombre": "mal/nombre"})
    assert r.status_code == 400 and "caracteres" in r.json()["detail"]


def test_generar_el_cuadernillo_no_cambia_las_cartillas(c, dos):
    (ida, _), (idb, _) = dos
    antes = [c.get(f"/api/cartillas/{x}").json() for x in (ida, idb)]
    c.post("/api/cuadernillo/generar", json={"cartillas": [ida, idb]})
    despues = [c.get(f"/api/cartillas/{x}").json() for x in (ida, idb)]
    for a, d in zip(antes, despues):
        assert (a["estado"], a["elegidos"], a["codigo"]) == (d["estado"], d["elegidos"], d["codigo"])
        # y cada sesión conserva su propio Excel de claves
        assert [f["tipo"] for f in c.get(f"/api/cartillas/{a['id']}/archivos").json()] == ["docx", "xlsx"]


def test_las_hojas_se_numeran_seguidas_de_principio_a_fin(c, dos):
    """Decisión de la empresa: un cuadernillo es UN folleto grapado, así que la numeración no se reinicia.

    Si alguna sección trajera «pgNumType w:start», la sesión 2 volvería a empezar en 1 y habría dos
    páginas con el mismo número dentro del mismo cuadernillo.
    """
    (ida, _), (idb, _) = dos
    r = c.post("/api/cuadernillo/generar", json={"cartillas": [ida, idb]})
    doc = Document(io.BytesIO(r.content))
    reinicios = [pg.get(W + "start") for sect in doc.element.body.iter(W + "sectPr")
                 for pg in sect.findall(W + "pgNumType") if pg.get(W + "start")]
    assert not reinicios, f"hay secciones que reinician la numeración: {reinicios}"

    # y las portadas conservan su pie propio, el que va sin número
    primeros = [sect for sect in doc.element.body.iter(W + "sectPr")
                if any(f.get(W + "type") == "first" for f in sect.findall(W + "footerReference"))]
    assert len(primeros) >= 2, "la portada y la media portada deben tener cada una su pie de primera página"
