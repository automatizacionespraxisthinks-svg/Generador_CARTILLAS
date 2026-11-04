"""Pruebas del banco: carga, códigos, duplicados, pendientes, búsqueda, vista previa y eliminación."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

EJ = Path(__file__).resolve().parent.parent / "plantillas" / "ejemplos"
SUELTO, BLOQUE, PARTE = (EJ / n for n in ("EJEMPLO_1_EJERCICIO_SUELTO.docx", "EJEMPLO_2_BLOQUE_LECTURA.docx",
                                          "EJEMPLO_3_PARTE_INGLES_COMPLETAR_TEXTO.docx"))


@pytest.fixture(scope="module")
def c():
    with TestClient(app) as cliente:
        yield cliente


def subir(c, *rutas, solo_revisar=False, nombre=None):
    archivos = [("archivos", (nombre or r.name, r.read_bytes())) for r in rutas]
    return c.post("/api/cargar", files=archivos, data={"solo_revisar": str(solo_revisar).lower()}).json()


def test_solo_revisar_no_guarda(c):
    r = subir(c, SUELTO, solo_revisar=True)[0]
    assert r["estado"] == "aceptado" and r["guardado"] is None
    assert c.get("/api/banco/resumen").json()["total"] == 0


def test_carga_asigna_codigos(c):
    r1, r2, r3 = subir(c, SUELTO, BLOQUE, PARTE)
    assert r1["guardado"]["codigos"] == ["MA1-77-000001"] and r1["guardado"]["bloque"] is None
    assert r2["guardado"]["codigos"] == ["CLE-77-000001", "CLE-77-000002", "CLE-77-000003"]
    assert r2["guardado"]["bloque"] == "CLE-77-B00001"
    assert r3["guardado"]["bloque"] == "ING-77-B00001" and len(r3["guardado"]["codigos"]) == 5
    res = c.get("/api/banco/resumen").json()
    assert res["total"] == 9 and res["bloques"] == 2


def test_duplicado_rechazado(c):
    r = subir(c, SUELTO, nombre="copia.docx")[0]
    assert r["estado"] == "rechazado" and r["errores"][0]["regla"] == 28
    assert "MA1-77-000001" in r["errores"][0]["mensaje"]


def test_busqueda_por_grado_y_tematica(c):
    res = c.get("/api/banco", params={"grado": "77", "tematica": "Figuras literarias"}).json()
    assert res["total"] == 1 and res["items"][0]["codigo"] == "CLE-77-000002" and res["items"][0]["bloque"] == "CLE-77-B00001"
    assert c.get("/api/banco", params={"grado": "77", "texto": "Camila"}).json()["total"] == 1
    assert c.get("/api/banco", params={"grado": "77", "tipo": "parte"}).json()["total"] == 5
    assert c.get("/api/banco", params={"grado": "77", "recurso": "tabla"}).json()["total"] == 1
    assert c.get("/api/banco", params={"grado": "11"}).json()["total"] == 0
    op = c.get("/api/banco/opciones", params={"grado": "77"}).json()
    assert "Idea global" in op["tematicas"] and "Inglés" in op["materias"]


def test_vista_previa(c):
    eid = c.get("/api/banco", params={"texto": "Camila"}).json()["items"][0]["id"]
    d = c.get(f"/api/banco/{eid}").json()
    assert d["clave"] == "C" and "Camila" in d["html"] and "opcion correcta" in d["html"] and "<table" in d["html"]
    assert c.get(f"/api/banco/{eid}/original").content[:2] == b"PK"


def test_tematica_parecida_pendiente_y_resuelta(c, tmp_path):
    from docx import Document
    doc = Document(SUELTO)
    excel = next(t for t in doc.tables if t.cell(0, 0).text.strip() == "Preg.")
    celda = excel.cell(1, 8).paragraphs[0]
    celda.runs[0].text = "Operaciones con números naturals"       # le falta una letra: parece error de escritura
    p = next(x for x in doc.paragraphs if x.text.startswith("Camila"))
    p.runs[0].text = "Andrés compra dos jugos y una empanada, y paga con un billete de $10.000."
    ruta = tmp_path / "parecida.docx"
    doc.save(ruta)
    r = subir(c, ruta)[0]
    assert r["estado"] == "pendiente" and r["pendiente_id"]
    sim = r["similitudes"][0]
    assert c.get("/api/pendientes").json()[0]["id"] == r["pendiente_id"]
    r2 = c.post(f"/api/pendientes/{r['pendiente_id']}", json={"decisiones": {f"{sim['campo']}|{sim['valor']}": "misma"}}).json()
    assert r2["estado"] == "aceptado" and r2["guardado"]["codigos"] == ["MA1-77-000002"]
    assert c.get("/api/pendientes").json() == []
    assert c.get("/api/banco", params={"grado": "77", "tematica": "Operaciones con números naturales"}).json()["total"] == 2


def test_eliminar_bloque_completo_y_no_reusar_codigo(c):
    eid = c.get("/api/banco", params={"tematica": "Figuras literarias"}).json()["items"][0]["id"]
    assert c.get(f"/api/banco/{eid}/usos").json()["codigos"] == ["CLE-77-000001", "CLE-77-000002", "CLE-77-000003"]
    r = c.delete(f"/api/banco/{eid}").json()
    assert len(r["eliminados"]) == 3
    assert c.get("/api/banco", params={"materia": "Lengua Castellana"}).json()["total"] == 0
    r = subir(c, BLOQUE)[0]
    assert r["guardado"]["codigos"][0] == "CLE-77-000004" and r["guardado"]["bloque"] == "CLE-77-B00002"


def test_copia_de_seguridad(c):
    import sqlite3
    r = c.get("/api/copia-seguridad")
    assert r.status_code == 200 and r.content[:15] == b"SQLite format 3"
    assert "attachment" in r.headers["content-disposition"]
