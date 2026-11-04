"""Pruebas de la API con una base de datos temporal."""
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

EJ = Path(__file__).resolve().parent.parent / "plantillas" / "ejemplos"


def test_catalogos_precargados():
    with TestClient(app) as c:
        cat = c.get("/api/catalogos").json()
        assert [g["codigo"] for g in cat["grados"]] == ["33", "44", "55", "66", "77", "88", "99", "10", "11", "13"]
        assert len(cat["plantillas"]) == 5 and all(len(p["secuencia"]) == 140 for p in cat["plantillas"])
        totales = {e["clave"]: e["total"] for e in cat["estructuras"]}
        assert totales == {"E1": 140, "E2": 140, "E3": 80, "E4": 0, "E5": 120, "E6": 134, "E7": 116}
        assert not any(t["codigo"] == "51" for t in cat["tipos"])


def test_validar_varios_archivos():
    with TestClient(app) as c:
        archivos = [("archivos", (p.name, p.read_bytes())) for p in sorted(EJ.glob("*.docx"))]
        archivos.append(("archivos", ("notas.txt", b"hola")))
        res = c.post("/api/validar", files=archivos).json()
        assert [r["estado"] for r in res] == ["aceptado", "aceptado", "aceptado", "rechazado"]


def test_descargar_formatos():
    with TestClient(app) as c:
        for f in c.get("/api/formatos").json():
            r = c.get(f"/formatos/{f['archivo']}")
            assert r.status_code == 200 and r.content[:2] == b"PK", f["archivo"]
        assert c.get("/formatos/../app/main.py").status_code == 404
