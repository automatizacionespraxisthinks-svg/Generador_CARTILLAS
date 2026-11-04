"""Grados 3°, 4° y 5° (21/09/2026): códigos 33, 44 y 55; Matemáticas y Lengua Castellana sin submateria;
Ciencias Naturales con submateria obligatoria; estructuras según el grado; secciones de la estructura libre."""
import io
import sqlite3
import zipfile

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook

from app.main import app
from app.validador import ACEPTADO, RECHAZADO, validar
from tests.fabrica import ejercicio

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def validar_fab(tema="Sumas", **kw):
    nombre, datos = ejercicio(tema, **kw)
    return validar(datos, nombre)


def mensajes(r):
    return [m.mensaje for m in r.errores]


# ================================================================== validador
@pytest.mark.parametrize("grado,materia,sub", [
    ("3°", "Matemáticas", ""),
    ("33", "Matemáticas", ""),                    # también por código
    ("3º", "Matemáticas", ""),                    # con el símbolo º
    ("4°", "Lengua Castellana", ""),
    ("5°", "Ciencias Naturales", "Biología"),
    ("5°", "Ciencias Sociales", ""),
    ("5°", "Inglés", ""),
])
def test_primaria_aceptada(grado, materia, sub):
    extra = {"pensamiento": "", "competencia": "Lingüística", "dba": ""} if materia == "Inglés" else {}
    r = validar_fab(grado=grado, materia=materia, submateria=sub, **extra)
    assert r.estado == ACEPTADO, mensajes(r)
    assert r.filas[0]["grado"] in ("33", "44", "55")


@pytest.mark.parametrize("grado,materia,sub,texto", [
    ("3°", "Matemáticas", "Matemáticas I", "va sin submateria"),
    ("4°", "Lengua Castellana", "Comprensión Lectora", "va sin submateria"),
    ("5°", "Ciencias Naturales", "", "Falta la Submateria"),
])
def test_primaria_submateria_como_la_pide_el_grado(grado, materia, sub, texto):
    r = validar_fab(grado=grado, materia=materia, submateria=sub)
    assert r.estado == RECHAZADO
    assert any(texto in m for m in mensajes(r)), mensajes(r)


def test_bachillerato_no_cambia():
    assert validar_fab(grado="6°", materia="Matemáticas", submateria="").estado == RECHAZADO     # sigue obligatoria
    assert validar_fab(grado="6°", materia="Matemáticas", submateria="Matemáticas I").estado == ACEPTADO


def test_mensaje_de_grado_con_los_nuevos():
    r = validar_fab(grado="2°")
    assert any("3°, 4°, 5°, 6°, 7°, 8°, 9°, 10°, 11° o ICFES" in m for m in mensajes(r)), mensajes(r)


# ================================================================== banco y cartillas
@pytest.fixture(scope="module")
def c():
    with TestClient(app) as cliente:
        yield cliente


def subir(c, archivo):
    nombre, datos = archivo
    r = c.post("/api/cargar", files=[("archivos", (nombre, datos))], data={"solo_revisar": "false"}).json()[0]
    assert r["estado"] == "aceptado", r["errores"]
    return r["guardado"]


def test_codigos_de_ejercicio_de_primaria(c):
    assert subir(c, ejercicio("Sumas", grado="3°", materia="Matemáticas", submateria=""))["codigos"] == ["MAT-33-000001"]
    g = subir(c, ejercicio("Cuentos", grado="4°", materia="Lengua Castellana", submateria="", pensamiento="", dba="",
                           n=2, bloque=True))
    assert g["bloque"] == "LEN-44-B00001" and g["codigos"] == ["LEN-44-000001", "LEN-44-000002"]
    assert subir(c, ejercicio("Seres vivos", grado="3°", materia="Ciencias Naturales", submateria="Biología"))["codigos"] == ["BIO-33-000001"]


def test_estructuras_segun_el_grado(c):
    op = c.get("/api/cartillas/opciones").json()
    assert [g["codigo"] for g in op["grados"]] == ["33", "44", "55", "66", "77", "88", "99", "10", "11", "13"]
    grados = {e["clave"]: e["grados"] for e in op["estructuras"]}
    for primaria in ("33", "44", "55"):
        assert primaria not in grados["E1"] and primaria not in grados["E2"]      # traen Matemáticas I, Español…
        assert primaria in grados["E4"] and primaria in grados["E3"]
    assert "66" in grados["E1"] and grados["E5"] == ["13"] and grados["E6"] == ["13"]
    mat = next(m for m in op["materias"] if m["nombre"] == "Matemáticas")
    assert mat["reglas"]["33"] is False and mat["reglas"]["66"] is True
    r = c.post("/api/cartillas", json={"grado": "33", "estructura": "E1", "tipo_material": "11", "plantilla": 1,
                                       "institucion": "IE", "nombre": "Primaria"})
    assert r.status_code == 400 and "no sirve para ese grado" in r.json()["detail"]


def test_cartilla_de_primaria_con_la_estructura_libre(c):
    d = c.post("/api/cartillas", json={"grado": "33", "estructura": "E4", "codigo_materia": "91", "tipo_material": "11",
                                       "plantilla": 1, "institucion": "IE", "nombre": "Primaria", "dificultad": "lib"}).json()
    assert d["codigo"] == "3391110101" and d["secciones"] == []

    def poner(secciones):
        return c.put(f"/api/cartillas/{d['id']}/secciones", json={"secciones": secciones})

    malas = [({"titulo": "MATEMÁTICAS I", "materia": "Matemáticas", "submateria": "Matemáticas I"}, "va sin submateria"),
             ({"titulo": "CIENCIAS", "materia": "Ciencias Naturales", "submateria": None}, "necesita submateria"),
             ({"titulo": "", "materia": "Matemáticas", "submateria": None}, "necesita un título"),
             ({"titulo": "X", "materia": "Astronomía", "submateria": None}, "no existe")]
    for sec, texto in malas:
        r = poner([{**sec, "cantidad": 1, "dificultad": "="}])
        assert r.status_code == 400 and texto in r.json()["detail"], r.text
    r = poner([{"titulo": "Matemáticas", "materia": "Matemáticas", "submateria": None, "cantidad": 1, "dificultad": "="},
               {"titulo": "Biología", "materia": "Ciencias Naturales", "submateria": "Biología", "cantidad": 1, "dificultad": "="}])
    assert r.status_code == 200, r.text
    d = r.json()
    assert [s["titulo"] for s in d["secciones"]] == ["MATEMÁTICAS", "BIOLOGÍA"] and d["total"] == 2
    assert d["tiempo"] == "4 minutos"                       # 2 min por pregunta, contando las secciones recién agregadas
    for s in d["secciones"]:
        c.post(f"/api/cartillas/{d['id']}/secciones/{s['id']}/automatica", json={})
    g = c.post(f"/api/cartillas/{d['id']}/generar", json={})
    assert g.status_code == 200, g.text
    docx = c.get(f"/api/cartillas/{d['id']}/archivo/docx").content
    x = zipfile.ZipFile(io.BytesIO(docx)).read("word/document.xml").decode()
    assert "Código Cartilla: 3391110101" in x and ">3°<" in x
    filas = list(load_workbook(io.BytesIO(c.get(f"/api/cartillas/{d['id']}/archivo/xlsx").content))["Claves"].iter_rows(min_row=3, values_only=True))
    assert [(f[0], f[3], f[4] or "") for f in filas] == [("3391110101", "Matemáticas", ""), ("3391110101", "Ciencias Naturales", "Biología")]
    # quitar una sección sin ejercicios
    d2 = c.post("/api/cartillas", json={"grado": "44", "estructura": "E4", "codigo_materia": "91", "tipo_material": "11",
                                        "plantilla": 1, "institucion": "IE", "nombre": "Primaria 4"}).json()
    d2 = c.put(f"/api/cartillas/{d2['id']}/secciones", json={"secciones": [
        {"titulo": "Lengua", "materia": "Lengua Castellana", "submateria": None, "cantidad": 5, "dificultad": "="}]}).json()
    assert len(d2["secciones"]) == 1 and d2["tiempo"] == "10 minutos"
    d2 = c.put(f"/api/cartillas/{d2['id']}/secciones", json={"secciones": []}).json()
    assert d2["secciones"] == []


def test_secciones_fijas_no_admiten_agregar(c):
    d = c.post("/api/cartillas", json={"grado": "66", "estructura": "E1", "tipo_material": "11", "plantilla": 2,
                                       "institucion": "IE", "nombre": "Sexto"}).json()
    actuales = [{"id": s["id"], "titulo": s["titulo"], "materia": s["materia"], "submateria": s["submateria"],
                 "cantidad": s["cantidad"], "dificultad": "="} for s in d["secciones"]]
    r = c.put(f"/api/cartillas/{d['id']}/secciones", json={"secciones": actuales + [
        {"titulo": "EXTRA", "materia": "Inglés", "submateria": None, "cantidad": 2, "dificultad": "="}]})
    assert r.status_code == 400 and "secciones fijas" in r.json()["detail"]


def test_migracion_agrega_los_grados(tmp_path):
    from app import migraciones
    from app.bd import usar_base
    from app.semilla import poblar
    ruta = tmp_path / "v5.db"
    usar_base(f"sqlite:///{ruta.as_posix()}")
    poblar()
    con = sqlite3.connect(ruta)       # una base de la versión 5: sin 3° a 5° y sin prefijo para Lengua Castellana
    con.execute("DELETE FROM grado WHERE codigo IN ('33', '44', '55')")
    con.execute("UPDATE materia SET prefijo = NULL WHERE nombre = 'Lengua Castellana'")
    con.execute("UPDATE version_esquema SET version = 5")
    con.commit()
    con.close()
    assert migraciones.aplicar() == migraciones.VERSION_ACTUAL
    con = sqlite3.connect(ruta)
    assert {r[0] for r in con.execute("SELECT codigo FROM grado")} >= {"33", "44", "55"}
    assert con.execute("SELECT prefijo FROM materia WHERE nombre = 'Lengua Castellana'").fetchone()[0] == "LEN"
    assert migraciones.aplicar() == migraciones.VERSION_ACTUAL                     # aplicarla dos veces no duplica
    assert con.execute("SELECT COUNT(*) FROM grado WHERE codigo = '33'").fetchone()[0] == 1
    con.close()
