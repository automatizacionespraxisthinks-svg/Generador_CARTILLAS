"""Conteo de páginas y ajuste a múltiplo de 4 (Estándar 3.7)."""
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import paginas
from app.main import app
from tests.fabrica import ejercicio

RAIZ = Path(__file__).resolve().parent.parent
MUESTRA = RAIZ / "docs" / "muestra_generada" / "Cartilla de muestra 7791330101.docx"
DATOS = {"grado": "77", "estructura": "E1", "tipo_material": "33", "plantilla": 1,
         "institucion": "Institución Educativa de prueba", "nombre": "Páginas", "simulacro_n": 1}


@pytest.mark.parametrize("hay,faltan", [(1, 3), (3, 1), (4, 0), (7, 1), (8, 0), (12, 0), (13, 3), (None, None), (0, None)])
def test_faltan_para_el_multiplo(hay, faltan):
    assert paginas.faltan_para_multiplo(hay) == faltan


def test_sin_word_no_cuenta():
    assert os.environ.get("PRAXIS_SIN_WORD") == "1"          # lo pone conftest: las pruebas no abren Word
    assert paginas.contar(b"PK no importa") is None


@pytest.mark.skipif(not MUESTRA.exists(), reason="no está la cartilla de muestra")
def test_cuenta_con_word_de_verdad(monkeypatch):
    """La única prueba que abre Word: la cartilla de muestra tiene 4 páginas."""
    monkeypatch.delenv("PRAXIS_SIN_WORD", raising=False)
    assert paginas.contar(MUESTRA.read_bytes()) == 4


@pytest.fixture(scope="module")
def c():
    with TestClient(app) as cliente:
        for i, tema in enumerate(["Fracciones", "Porcentajes", "Probabilidad"]):
            nombre, datos = ejercicio(tema, clave="ABC"[i], normal_justificado=True)
            r = cliente.post("/api/cargar", files=[("archivos", (nombre, datos))], data={"solo_revisar": "false"}).json()[0]
            assert r["estado"] == "aceptado", r["errores"]
        yield cliente


def armar(c, version):
    d = c.post("/api/cartillas", json={**DATOS, "version": version}).json()
    cuerpo = [{"id": s["id"], "titulo": s["titulo"], "materia": s["materia"], "submateria": s["submateria"],
               "cantidad": 3 if s["titulo"] == "MATEMÁTICAS I" else 0, "dificultad": "lib"} for s in d["secciones"]]
    d = c.put(f"/api/cartillas/{d['id']}/secciones", json={"secciones": cuerpo}).json()
    sec = next(s for s in d["secciones"] if s["cantidad"])
    c.post(f"/api/cartillas/{d['id']}/secciones/{sec['id']}/automatica", json={})
    return c.get(f"/api/cartillas/{d['id']}").json()


def test_la_cartilla_informa_sus_paginas(c, monkeypatch):
    d = armar(c, 1)
    monkeypatch.setattr(paginas, "contar", lambda datos: 7)
    r = c.post(f"/api/cartillas/{d['id']}/generar", json={}).json()
    assert r["paginas"] == 7 and r["faltan_paginas"] == 1
    d = c.get(f"/api/cartillas/{d['id']}").json()
    assert d["paginas"] == 7 and d["faltan_paginas"] == 1
    # volver a contar: ahora el Word tiene 8 páginas (se agregó relleno del cierre)
    monkeypatch.setattr(paginas, "contar", lambda datos: 8)
    r = c.post(f"/api/cartillas/{d['id']}/paginas").json()
    assert r["paginas"] == 8 and r["faltan_paginas"] == 0 and r["cartilla"]["paginas"] == 8


def test_sin_word_la_generacion_sigue(c):
    d = armar(c, 2)
    r = c.post(f"/api/cartillas/{d['id']}/generar", json={}).json()
    assert r["preguntas"] == 3 and r["paginas"] is None and r["faltan_paginas"] is None
    assert c.get(f"/api/cartillas/{d['id']}/archivo/docx").status_code == 200       # el Word se genera igual
    assert c.post(f"/api/cartillas/{d['id']}/paginas").json()["paginas"] is None


def test_contar_sin_cartilla_generada(c):
    d = armar(c, 3)
    r = c.post(f"/api/cartillas/{d['id']}/paginas")
    assert r.status_code == 400 and "genérala primero" in r.json()["detail"]
