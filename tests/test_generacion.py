"""Pruebas de la generación: Word con la plantilla aplicada, Excel de claves y verificación cruzada."""
import io
import re
import zipfile

import pytest
from docx import Document
from fastapi.testclient import TestClient
from openpyxl import load_workbook

from app.generador import _leer_cartilla_generada, _verificar_cruzado

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def textos_de(datos):
    """Todos los párrafos del Word, incluidos los de la portada (que van en cuadros de texto)."""
    from lxml import etree
    doc = etree.fromstring(zipfile.ZipFile(io.BytesIO(datos)).read("word/document.xml"))
    vistos, salida = set(), []
    for p in doc.iter(W + "p"):
        t = "".join(x.text or "" for x in p.iter(W + "t")).strip()
        if t and (t, id(p.getparent())) not in vistos:
            vistos.add((t, id(p.getparent())))
            salida.append(t)
    return salida
from app.main import app
from tests.fabrica import ejercicio, imagen_gris

PLANTILLA_1 = ("BACDCDABDBACDCBABCDAACBDABCDCABDADBCCABDDCBACABDDABCCADBBCADDBCAABCDACDBDABCDCBAC"
               "ABDDACBBCDACDBAACBDCDABCADBBCADBACDDACBCBADBACDBCADBDACADCB")
DATOS = {"grado": "77", "estructura": "E1", "tipo_material": "33", "plantilla": 1,
         "institucion": "Institución Educativa de prueba", "nombre": "Tercer periodo", "simulacro_n": 1}


@pytest.fixture(scope="module")
def c(tmp_path_factory):
    with TestClient(app) as cliente:
        img = imagen_gris(tmp_path_factory.mktemp("img") / "g.png")
        for i, tema in enumerate(["Fracciones", "Porcentajes", "Ecuaciones lineales", "Probabilidad"]):
            subir(cliente, ejercicio(tema, nivel=["Básico", "Medio", "Avanzado"][i % 3], clave="ABCD"[i % 4],
                                     imagen=img if i == 0 else None))
        subir(cliente, ejercicio("Comprensión de un texto narrativo", materia="Lengua Castellana",
                                 submateria="Comprensión Lectora", pensamiento="", dba="", n=3, bloque=True))
        subir(cliente, ejercicio("Vocabulario en contexto", materia="Inglés", submateria="", pensamiento="",
                                 competencia="Lingüística", dba="DBA 1", n=3, parte=True))
        subir(cliente, ejercicio("Completar el texto", materia="Inglés", submateria="", pensamiento="",
                                 competencia="Lingüística", dba="DBA 4", n=3, parte=True, cloze=True))
        for tema in ["Álgebra básica", "Geometría analítica", "Funciones"]:      # banco ICFES
            subir(cliente, ejercicio(tema, grado="ICFES", submateria="", nivel=""))
        yield cliente


def subir(cliente, archivo):
    nombre, datos = archivo
    r = cliente.post("/api/cargar", files=[("archivos", (nombre, datos))], data={"solo_revisar": "false"}).json()[0]
    assert r["estado"] == "aceptado", r["errores"]
    return r["guardado"]


def armar(c, cantidades, tematica=None, **extra):
    """Crea una cartilla, ajusta las secciones y la llena con la selección automática."""
    d = c.post("/api/cartillas", json={**DATOS, **extra}).json()
    cuerpo = [{"id": s["id"], "titulo": s["titulo"], "materia": s["materia"], "submateria": s["submateria"],
               "cantidad": cantidades.get(s["titulo"], 0), "dificultad": "lib"} for s in d["secciones"]]
    d = c.put(f"/api/cartillas/{d['id']}/secciones", json={"secciones": cuerpo}).json()
    for s in d["secciones"]:
        if not s["cantidad"]:
            continue
        if tematica:      # elección manual, para asegurar qué unidad entra
            cand = c.get(f"/api/cartillas/{d['id']}/candidatos", params={"seccion": s["id"], "tematica": tematica}).json()
            c.post(f"/api/cartillas/{d['id']}/items", json={"seccion": s["id"], "ejercicio": cand["items"][0]["id"]})
        else:
            c.post(f"/api/cartillas/{d['id']}/secciones/{s['id']}/automatica", json={})
    return c.get(f"/api/cartillas/{d['id']}").json()


def generar(c, cid, **cuerpo):
    return c.post(f"/api/cartillas/{cid}/generar", json=cuerpo)


# ------------------------------------------------------------------ generación completa
def test_genera_word_y_excel(c):
    d = armar(c, {"MATEMÁTICAS I": 4, "COMPRENSIÓN LECTORA": 3, "INGLÉS": 3}, version=1)
    r = generar(c, d["id"])
    assert r.status_code == 200, r.text
    info = r.json()
    assert info["preguntas"] == 10
    assert info["docx"] == "7791330101 - Tercer periodo.docx" and info["xlsx"].endswith(".xlsx")

    docx = c.get(f"/api/cartillas/{d['id']}/archivo/docx")
    assert docx.status_code == 200 and docx.content[:2] == b"PK"
    textos = textos_de(docx.content)
    # portada
    assert "Código Cartilla: 7791330101" in textos and "10 preguntas" in textos and "20 minutos" in textos
    # títulos de sección y numeración continua
    assert "MATEMÁTICAS I" in textos and "COMPRENSIÓN LECTORA" in textos and "INGLÉS" in textos
    preguntas = _leer_cartilla_generada(docx.content)
    assert [p["numero"] for p in preguntas] == list(range(1, 11))
    assert all(p["opciones"][:4] == list("ABCD") for p in preguntas)
    # bloque y parte con sus rangos reescritos
    assert "Responde las preguntas 5 a 7 de acuerdo con la siguiente lectura." in textos
    assert any(t.startswith("PARTE 1 · Vocabulario en contexto — preguntas 8 a 10") for t in textos)
    assert not any("#N" in t or "#M" in t or "#P" in t for t in textos)
    # la línea ➤ se imprime fuera del ICFES
    assert any(t.startswith("➤") for t in textos)
    # la imagen del ejercicio viajó al archivo final
    assert [n for n in zipfile.ZipFile(io.BytesIO(docx.content)).namelist() if n.startswith("word/media/")]


def test_excel_de_claves(c):
    cid = c.get("/api/cartillas").json()[0]["id"]
    datos = c.get(f"/api/cartillas/{cid}/archivo/xlsx").content
    hoja = load_workbook(io.BytesIO(datos))["Claves"]
    assert hoja.title == "Claves"
    assert str(hoja["A1"].value).startswith("CLAVES DE RESPUESTAS")
    assert "OMR" in str(hoja["M1"].value)
    encabezados = [hoja.cell(row=2, column=i).value for i in range(1, 12)]
    assert encabezados == ["Cartilla", "Pregunta", "Correcta", "Materia", "Submateria", "Pensamiento",
                           "Competencia", "DBA", "Temática", "Nivel", "Justificación"]
    filas = list(hoja.iter_rows(min_row=3, values_only=True))
    assert len(filas) == 10
    assert [f[1] for f in filas] == list(range(1, 11))
    assert [f[2] for f in filas] == list(PLANTILLA_1[:10])          # la letra la manda la plantilla
    assert all(f[0] == "7791330101" for f in filas)
    assert all(f[10] for f in filas)                                 # justificación en todas


def test_la_correcta_del_excel_es_la_opcion_marcada_en_el_word(c):
    cid = c.get("/api/cartillas").json()[0]["id"]
    detalle = c.get(f"/api/cartillas/{cid}").json()
    textos = textos_de(c.get(f"/api/cartillas/{cid}/archivo/docx").content)
    cuerpo = textos[textos.index("MATEMÁTICAS I"):]        # deja fuera la portada, que numera sus instrucciones
    for sec in detalle["secciones"]:
        for it in sec["items"]:
            # el texto de la opción correcta del banco debe estar en la letra que dice el Excel
            i = next(k for k, t in enumerate(cuerpo) if t.startswith(f"{it['numero']}. Enunciado"))
            opciones = [t for t in cuerpo[i:i + 8] if re.match(r"^[A-D]\.", t)][:4]
            correcta = next(t for t in opciones if t.startswith(it["letra"] + "."))
            # en la fábrica, la opción A dice «primera», la B «segunda»… la correcta conserva su texto y cambia de letra
            esperado = {"A": "primera", "B": "segunda", "C": "tercera", "D": "cuarta"}[it["clave_original"]]
            assert esperado in correcta, (it, correcta)
            assert len(set(opciones)) == 4                            # ninguna opción se duplicó al intercambiarlas


def test_marca_la_cartilla_como_generada_y_cuenta_los_usos(c):
    cid = c.get("/api/cartillas").json()[0]["id"]
    d = c.get(f"/api/cartillas/{cid}").json()
    assert d["estado"] == "generada"
    eid = d["secciones"][0]["items"][0]["ejercicio_id"]
    assert c.get(f"/api/banco/{eid}").json()["veces_usado"] == 1
    # una cartilla generada ya no se edita
    r = c.post(f"/api/cartillas/{cid}/items", json={"seccion": d["secciones"][0]["id"], "ejercicio": eid})
    assert r.status_code == 400 and "generada" in r.json()["detail"]


def test_no_genera_si_falta_algo(c):
    d = armar(c, {"MATEMÁTICAS I": 4}, version=2)
    c.delete(f"/api/cartillas/{d['id']}/items/{d['secciones'][0]['items'][0]['ejercicio_id']}")
    r = generar(c, d["id"])
    assert r.status_code == 400 and "3 de 4" in r.json()["detail"]


def test_nombre_de_archivo_personalizado_y_validado(c):
    d = armar(c, {"MATEMÁTICAS I": 2}, version=3)
    r = generar(c, d["id"], nombre='Simulacro: 3/2026')
    assert r.status_code == 400 and "caracteres" in r.json()["detail"]
    r = generar(c, d["id"], nombre="Simulacro 3 de 2026")
    assert r.status_code == 200 and r.json()["docx"] == "Simulacro 3 de 2026.docx"
    cd = c.get(f"/api/cartillas/{d['id']}/archivo/docx").headers["content-disposition"]
    assert "Simulacro%203%20de%202026.docx" in cd


def test_icfes_sin_linea_y_con_columnas_vacias(c):
    d = c.post("/api/cartillas", json={**DATOS, "grado": "13", "estructura": "E5", "tipo_material": "71",
                                       "codigo_materia": "99", "version": 4, "nombre": "Simulacro ICFES"}).json()
    cuerpo = [{"id": s["id"], "titulo": s["titulo"], "materia": s["materia"], "submateria": s["submateria"],
               "cantidad": 3 if s["titulo"] == "MATEMÁTICAS" else 0, "dificultad": "lib"} for s in d["secciones"]]
    d = c.put(f"/api/cartillas/{d['id']}/secciones", json={"secciones": cuerpo}).json()
    c.post(f"/api/cartillas/{d['id']}/secciones/{d['secciones'][0]['id']}/automatica", json={})
    r = generar(c, d["id"])
    assert r.status_code == 200, r.text
    textos = textos_de(c.get(f"/api/cartillas/{d['id']}/archivo/docx").content)
    assert not any(t.startswith("➤") for t in textos)               # en ICFES no va la línea ➤
    assert "Saber 11" in textos                                      # y el grado se imprime así
    hoja = load_workbook(io.BytesIO(c.get(f"/api/cartillas/{d['id']}/archivo/xlsx").content))["Claves"]
    filas = list(hoja.iter_rows(min_row=3, values_only=True))
    assert len(filas) == 3
    for f in filas:
        assert f[3] == "Matemáticas" and not f[4]                    # submateria vacía en MATEMÁTICAS
        assert not any(f[5:10])                                      # F a J vacías
        assert f[10]                                                 # la justificación sí va


# ------------------------------------------------------------------ verificación cruzada
def test_la_verificacion_detecta_una_desalineacion():
    claves = [{"posicion": 1, "letra": "B"}, {"posicion": 2, "letra": "A"}]
    docx = _documento_de_prueba([("1.", "ABCD"), ("2.", "ABCD")])
    assert _verificar_cruzado(docx, claves, PLANTILLA_1) == []
    docx_mal = _documento_de_prueba([("1.", "ABCD"), ("3.", "ABCD")])
    fallas = _verificar_cruzado(docx_mal, claves, PLANTILLA_1)
    assert fallas and "quedó numerada como 3" in fallas[0]
    docx_sin_d = _documento_de_prueba([("1.", "ABCD"), ("2.", "ABC")])
    assert any("no tiene las opciones" in f for f in _verificar_cruzado(docx_sin_d, claves, PLANTILLA_1))


def _documento_de_prueba(preguntas):
    doc = Document()
    for numero, letras in preguntas:
        doc.add_paragraph(f"{numero} Enunciado de prueba")
        for L in letras:
            doc.add_paragraph(f"{L}. opción")
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def test_la_verificacion_entiende_el_numero_junto_a_la_opcion_a():
    """En «completar el texto» la línea es «9. A. went»: eso también es una pregunta completa."""
    doc = Document()
    doc.add_paragraph("9. A. went")
    for L in "BCD":
        doc.add_paragraph(f"{L}. opción")
    buf = io.BytesIO()
    doc.save(buf)
    leidas = _leer_cartilla_generada(buf.getvalue())
    assert leidas == [{"numero": 9, "opciones": ["A", "B", "C", "D"]}]


def test_completar_el_texto_numera_los_espacios(c):
    """Los marcadores (#1), (#2)… del texto se cambian por el número real de cada pregunta."""
    d = armar(c, {"INGLÉS": 3}, version=5, nombre="Ingles de prueba", tematica="Completar el texto")
    r = generar(c, d["id"], nombre="Ingles de prueba")
    assert r.status_code == 200, r.text
    textos = textos_de(c.get(f"/api/cartillas/{d['id']}/archivo/docx").content)
    recurso = next(t for t in textos if "lake" in t)
    assert "(#1)" not in recurso and "(1)" in recurso and "(3)" in recurso
    assert "______" in recurso


def test_las_paginas_se_pueden_anotar_a_mano_donde_no_hay_word(c):
    """En el servidor no hay Word ni las fuentes de la cartilla: contar allí daría otro número."""
    d = armar(c, {"MATEMÁTICAS I": 4}, version=61)
    assert generar(c, d["id"]).status_code == 200
    cid = d["id"]
    r = c.post(f"/api/cartillas/{cid}/paginas", json={"paginas": 26})
    assert r.status_code == 200, r.json()
    assert (r.json()["paginas"], r.json()["faltan_paginas"]) == (26, 2)
    assert c.get(f"/api/cartillas/{cid}").json()["paginas"] == 26

    # ya múltiplo de 4
    assert c.post(f"/api/cartillas/{cid}/paginas", json={"paginas": 28}).json()["faltan_paginas"] == 0

    # y no se traga cualquier cosa
    for malo in (0, -3, 5000, "muchas"):
        r = c.post(f"/api/cartillas/{cid}/paginas", json={"paginas": malo})
        assert r.status_code == 400, f"aceptó {malo!r}"


def test_la_pantalla_sabe_si_este_equipo_puede_contar_paginas(c):
    """La pantalla ofrece contar o pedir el número según dónde esté corriendo el sistema."""
    assert c.get("/api/cartillas/opciones").json()["hay_word"] is False      # las pruebas corren sin Word
