"""Borrado en lote del banco: marcar varios, borrar por filtro, y que los bloques salgan enteros."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.fabrica import ejercicio

EJ = Path(__file__).resolve().parent.parent / "plantillas" / "ejemplos"
BLOQUE = EJ / "EJEMPLO_2_BLOQUE_LECTURA.docx"


@pytest.fixture(scope="module")
def c():
    with TestClient(app) as cliente:
        yield cliente


def subir_archivo(c, nombre, datos):
    return c.post("/api/cargar", files=[("archivos", (nombre, datos))], data={"solo_revisar": "false"}).json()[0]


#  el validador rechaza los números sueltos (regla 18), así que las variantes se escriben con palabras
PALABRAS = ["uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho"]


def sembrar(c, cuantos, tema, **kw):
    """Deja `cuantos` ejercicios sueltos de ese tema en el banco y devuelve sus id."""
    ids = []
    for i in range(cuantos):
        nombre, datos = ejercicio(tema, variante=PALABRAS[i], **kw)
        r = subir_archivo(c, f"lote_{PALABRAS[i]}.docx", datos)
        assert r["estado"] == "aceptado", r.get("errores")
    for x in c.get("/api/banco", params={"tematica": tema}).json()["items"]:
        ids.append(x["id"])
    return ids


def borrar(c, **cuerpo):
    return c.post("/api/banco/eliminar", json=cuerpo).json()


def test_solo_ver_no_borra_nada(c):
    ids = sembrar(c, 3, "Fracciones equivalentes")
    p = borrar(c, ids=ids[:2], solo_ver=True)
    assert len(p["eliminados"]) == 2 and p["unidades"] == 2 and p["arrastrados"] == 0
    assert c.get("/api/banco", params={"tematica": "Fracciones equivalentes"}).json()["total"] == 3


def test_borrar_los_marcados_deja_los_demas(c):
    ids = c.get("/api/banco", params={"tematica": "Fracciones equivalentes"}).json()["items"]
    ids = [x["id"] for x in ids]
    r = borrar(c, ids=ids[:2])
    assert len(r["eliminados"]) == 2 and r["marcados"] == 2
    quedan = c.get("/api/banco", params={"tematica": "Fracciones equivalentes"}).json()
    assert quedan["total"] == 1 and quedan["items"][0]["id"] == ids[2]


def test_lista_vacia_no_hace_nada(c):
    assert borrar(c, ids=[])["eliminados"] == []
    assert borrar(c, ids=[999999])["eliminados"] == []


def test_los_id_como_texto_cuentan_igual(c):
    """La pantalla manda el valor de la casilla; si llegara como texto, «arrastrados» no debe mentir."""
    ids = sembrar(c, 1, "Área del círculo")
    p = borrar(c, ids=[str(ids[0])], solo_ver=True)
    assert len(p["eliminados"]) == 1 and p["arrastrados"] == 0 and p["marcados"] == 1
    assert borrar(c, ids=["no es un número", None], solo_ver=True)["eliminados"] == []
    assert len(borrar(c, ids=ids)["eliminados"]) == 1


def test_marcar_una_pregunta_arrastra_su_bloque(c):
    r = subir_archivo(c, BLOQUE.name, BLOQUE.read_bytes())
    assert r["estado"] == "aceptado"
    items = c.get("/api/banco", params={"tipo": "bloque"}).json()["items"]
    assert len(items) == 3                                   # el bloque de ejemplo trae tres preguntas
    p = borrar(c, ids=[items[0]["id"]], solo_ver=True)
    assert len(p["eliminados"]) == 3 and p["unidades"] == 1 and p["arrastrados"] == 2
    assert len(borrar(c, ids=[items[0]["id"]])["eliminados"]) == 3
    assert c.get("/api/banco", params={"tipo": "bloque"}).json()["total"] == 0


def test_borrar_por_filtro_se_lleva_todo_lo_que_coincide(c):
    sembrar(c, 4, "Teorema de Tales", submateria="Matemáticas II", pensamiento="Geométrico-métrico")
    otros = c.get("/api/banco", params={"tematica": "Fracciones equivalentes"}).json()["total"]
    assert otros == 1                                        # lo que debe sobrevivir al filtro
    r = borrar(c, filtro={"tematica": "Teorema de Tales"})
    assert len(r["eliminados"]) == 4
    assert c.get("/api/banco", params={"tematica": "Teorema de Tales"}).json()["total"] == 0
    assert c.get("/api/banco", params={"tematica": "Fracciones equivalentes"}).json()["total"] == otros


def test_borrar_avisa_de_las_cartillas_que_los_usan_y_las_limpia(c):
    sembrar(c, 2, "Regla de tres simple")
    d = c.post("/api/cartillas", json={"grado": "77", "estructura": "E4", "tipo_material": "33", "plantilla": 1,
                                       "codigo_materia": "03", "institucion": "Prueba", "nombre": "Lote",
                                       "simulacro_n": 1, "version": 1}).json()
    cid = d["id"]
    sec = c.put(f"/api/cartillas/{cid}/secciones", json={"secciones": [
        {"titulo": "MATEMÁTICAS", "materia": "Matemáticas", "submateria": "*", "cantidad": 2,
         "dificultad": "lib"}]}).json()["secciones"][0]
    usados = []
    for cand in c.get(f"/api/cartillas/{cid}/candidatos", params={"seccion": sec["id"]}).json()["items"][:2]:
        c.post(f"/api/cartillas/{cid}/items", json={"seccion": sec["id"], "ejercicio": cand["id"]})
        usados.append(cand["id"])
    assert len(usados) == 2

    p = borrar(c, ids=usados, solo_ver=True)
    assert [x["codigo"] for x in p["cartillas"]] == [d["codigo"]]
    assert c.get(f"/api/cartillas/{cid}").json()["elegidos"] == 2      # «solo ver» no tocó la cartilla

    r = borrar(c, ids=usados)
    assert [x["codigo"] for x in r["cartillas"]] == [d["codigo"]]
    assert c.get(f"/api/cartillas/{cid}").json()["elegidos"] == 0


def test_borrado_de_uno_solo_sigue_funcionando(c):
    ids = sembrar(c, 1, "Mínimo común múltiplo")
    r = c.delete(f"/api/banco/{ids[0]}").json()
    assert len(r["eliminados"]) == 1 and "usos" in r and "cartillas" in r
    assert c.delete("/api/banco/999999").status_code == 404
