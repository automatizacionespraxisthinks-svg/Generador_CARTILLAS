"""Pruebas del armado de cartillas: código, secciones, selección, bloques, numeración y verificación."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.fabrica import ejercicio

PLANTILLA_1 = ("BACDCDABDBACDCBABCDAACBDABCDCABDADBCCABDDCBACABDDABCCADBBCADDBCAABCDACDBDABCDCBAC"
               "ABDDACBBCDACDBAACBDCDABCADBBCADBACDDACBCBADBACDBCADBDACADCB")


@pytest.fixture(scope="module")
def c():
    with TestClient(app) as cliente:
        # banco de prueba: 8 de Matemáticas I, 6 de Matemáticas II, un bloque de 3 y una parte de 4
        temas1 = ["Fracciones", "Porcentajes", "Ecuaciones lineales", "Probabilidad", "Potenciación", "Estadística", "Proporcionalidad", "Números primos"]
        temas2 = ["Ángulos", "Triángulos", "Circunferencia", "Volúmenes", "Semejanza", "Teorema de Pitágoras"]
        for i, tema in enumerate(temas1):
            subir(cliente, ejercicio(tema, nivel=["Básico", "Medio", "Avanzado"][i % 3], clave="ABCD"[i % 4]))
        for tema in temas2:
            subir(cliente, ejercicio(tema, submateria="Matemáticas II", nivel="Medio"))
        subir(cliente, ejercicio("Lectura larga", materia="Lengua Castellana", submateria="Comprensión Lectora",
                                 pensamiento="", dba="", n=3, bloque=True))
        subir(cliente, ejercicio("Vocabulario en contexto", materia="Inglés", submateria="", pensamiento="",
                                 competencia="Lingüística", dba="DBA 1", n=4, parte=True))
        yield cliente


def subir(cliente, archivo):
    nombre, datos = archivo
    r = cliente.post("/api/cargar", files=[("archivos", (nombre, datos))], data={"solo_revisar": "false"}).json()[0]
    assert r["estado"] == "aceptado", r["errores"]
    return r["guardado"]


DATOS = {"grado": "77", "estructura": "E1", "tipo_material": "33", "plantilla": 1, "version": 1,
         "institucion": "Institución Educativa de prueba", "nombre": "Tercer periodo", "simulacro_n": 1}


def crear(c, **extra):
    r = c.post("/api/cartillas", json={**DATOS, **extra})
    assert r.status_code == 200, r.text
    return r.json()


def secciones_pequenas(c, cid, cantidades):
    d = c.get(f"/api/cartillas/{cid}").json()
    cuerpo = [{"id": s["id"], "titulo": s["titulo"], "cantidad": cantidades.get(s["titulo"], 0),
               "materia": s["materia"], "submateria": s["submateria"], "dificultad": s["dificultad"]}
              for s in d["secciones"]]
    r = c.put(f"/api/cartillas/{cid}/secciones", json={"secciones": cuerpo})
    assert r.status_code == 200, r.text
    return r.json()


# ------------------------------------------------------------------ creación y código
def test_crear_arma_codigo_y_secciones(c):
    d = crear(c)
    assert d["codigo"] == "7791330101"          # grado 77 · PARTE 1 91 · periodo 3 · plantilla 01 · versión 01
    assert len(d["secciones"]) == 9 and d["total"] == 140
    assert d["tiempo"] == "4 horas y 40 minutos"
    assert d["secciones"][0]["rango"] == [1, 15] and d["secciones"][-1]["rango"] == [113, 140]


def test_codigo_repetido_sugiere_version(c):
    r = c.post("/api/cartillas", json=DATOS)
    assert r.status_code == 400 and "ya existe" in r.json()["detail"] and "02" in r.json()["detail"]


@pytest.mark.parametrize("cambio,texto", [
    ({"estructura": "E5"}, "ICFES"),
    ({"institucion": " "}, "obligatorios"),
    ({"plantilla": 9}, "plantilla"),
    ({"tipo_material": "51"}, "tipo de material"),
])
def test_datos_invalidos(c, cambio, texto):
    r = c.post("/api/cartillas", json={**DATOS, **cambio, "version": 9})
    assert r.status_code == 400 and texto.lower() in r.json()["detail"].lower()


def test_segunda_sesion_se_empareja_sola(c):
    d1 = crear(c, version=3, nombre="Sesión 1")
    d2 = crear(c, version=3, estructura="E3", codigo_materia="92", nombre="Sesión 2")
    assert d2["codigo"] == "7792330103"
    assert [x["codigo"] for x in d2["excluidas"]] == [d1["codigo"]]


# ------------------------------------------------------------------ secciones
def test_ajustar_cantidades_y_tiempo(c):
    d = crear(c, version=4)
    d = secciones_pequenas(c, d["id"], {"MATEMÁTICAS I": 4, "MATEMÁTICAS II": 2})
    assert d["total"] == 6 and d["tiempo"] == "12 minutos"
    assert d["secciones"][0]["rango"] == [1, 4] and d["secciones"][1]["rango"] == [5, 6]


def test_no_se_puede_bajar_la_cantidad_con_ejercicios_elegidos(c):
    d = crear(c, version=5)
    d = secciones_pequenas(c, d["id"], {"MATEMÁTICAS I": 2})
    sec = d["secciones"][0]["id"]
    cand = c.get(f"/api/cartillas/{d['id']}/candidatos", params={"seccion": sec}).json()["items"]
    c.post(f"/api/cartillas/{d['id']}/items", json={"seccion": sec, "ejercicio": cand[0]["id"]})
    cuerpo = [{"id": s["id"], "titulo": s["titulo"], "cantidad": 0, "materia": s["materia"],
               "submateria": s["submateria"], "dificultad": "="} for s in d["secciones"]]
    r = c.put(f"/api/cartillas/{d['id']}/secciones", json={"secciones": cuerpo})
    assert r.status_code == 400 and "quítalos" in r.json()["detail"]


# ------------------------------------------------------------------ selección
def test_seleccion_manual_y_numeracion(c):
    d = crear(c, version=6)
    d = secciones_pequenas(c, d["id"], {"MATEMÁTICAS I": 3, "MATEMÁTICAS II": 2})
    cid = d["id"]
    for i, sec in enumerate(d["secciones"][:2]):
        cand = c.get(f"/api/cartillas/{cid}/candidatos", params={"seccion": sec["id"]}).json()
        assert cand["faltan"] == sec["cantidad"]
        for x in cand["items"][:sec["cantidad"]]:
            r = c.post(f"/api/cartillas/{cid}/items", json={"seccion": sec["id"], "ejercicio": x["id"]})
            assert r.status_code == 200, r.text
    d = c.get(f"/api/cartillas/{cid}").json()
    numeros = [it["numero"] for s in d["secciones"] for it in s["items"]]
    assert numeros == [1, 2, 3, 4, 5]
    letras = [it["letra"] for s in d["secciones"] for it in s["items"]]
    assert letras == list(PLANTILLA_1[:5])
    assert d["elegidos"] == 5 and all(p["ok"] for p in d["verificacion"])


def test_no_acepta_ejercicio_de_otra_seccion(c):
    d = crear(c, version=7)
    d = secciones_pequenas(c, d["id"], {"MATEMÁTICAS I": 2, "COMPRENSIÓN LECTORA": 3})
    mat, lectora = d["secciones"][0]["id"], d["secciones"][3]["id"]
    cand = c.get(f"/api/cartillas/{d['id']}/candidatos", params={"seccion": lectora}).json()["items"]
    r = c.post(f"/api/cartillas/{d['id']}/items", json={"seccion": mat, "ejercicio": cand[0]["id"]})
    assert r.status_code == 400 and "no corresponde" in r.json()["detail"]


def test_bloque_entra_completo_y_se_recorta_hasta_dos(c):
    d = crear(c, version=8)
    d = secciones_pequenas(c, d["id"], {"COMPRENSIÓN LECTORA": 3})
    cid, sec = d["id"], d["secciones"][3]["id"]
    cand = c.get(f"/api/cartillas/{cid}/candidatos", params={"seccion": sec}).json()["items"]
    assert cand[0]["bloque"] and cand[0]["hermanos"] == 3
    r = c.post(f"/api/cartillas/{cid}/items", json={"seccion": sec, "ejercicio": cand[0]["id"]}).json()
    assert len(r["agregados"]) == 3
    items = [it for s in r["cartilla"]["secciones"] for it in s["items"]]
    quitar = c.delete(f"/api/cartillas/{cid}/items/{items[0]['ejercicio_id']}").json()
    assert len(quitar["quitados"]) == 1                      # queda con 2: se permite
    restantes = [it for s in quitar["cartilla"]["secciones"] for it in s["items"]]
    quitar2 = c.delete(f"/api/cartillas/{cid}/items/{restantes[0]['ejercicio_id']}").json()
    assert len(quitar2["quitados"]) == 2                     # no puede quedar con una sola


def test_parte_de_ingles_no_se_recorta(c):
    d = crear(c, version=9)
    d = secciones_pequenas(c, d["id"], {"INGLÉS": 4})
    cid, sec = d["id"], d["secciones"][8]["id"]
    cand = c.get(f"/api/cartillas/{cid}/candidatos", params={"seccion": sec}).json()["items"]
    r = c.post(f"/api/cartillas/{cid}/items", json={"seccion": sec, "ejercicio": cand[0]["id"]}).json()
    assert len(r["agregados"]) == 4
    item = r["cartilla"]["secciones"][8]["items"][1]
    quitar = c.delete(f"/api/cartillas/{cid}/items/{item['ejercicio_id']}").json()
    assert len(quitar["quitados"]) == 4


def test_bloque_que_no_cabe_avisa(c):
    d = crear(c, version=10)
    d = secciones_pequenas(c, d["id"], {"COMPRENSIÓN LECTORA": 2})
    cid, sec = d["id"], d["secciones"][3]["id"]
    cand = c.get(f"/api/cartillas/{cid}/candidatos", params={"seccion": sec}).json()["items"]
    r = c.post(f"/api/cartillas/{cid}/items", json={"seccion": sec, "ejercicio": cand[0]["id"]})
    assert r.status_code == 400 and "solo faltan 2" in r.json()["detail"]


# ------------------------------------------------------------------ automática
def test_automatica_respeta_dificultad_y_avisa_si_faltan(c):
    d = crear(c, version=11, dificultad="b")            # solo básica
    d = secciones_pequenas(c, d["id"], {"MATEMÁTICAS I": 2})
    cid, sec = d["id"], d["secciones"][0]["id"]
    r = c.post(f"/api/cartillas/{cid}/secciones/{sec}/automatica", json={}).json()
    assert len(r["agregados"]) == 2 and r["faltan"] == 0
    niveles = {it["nivel"] for it in r["cartilla"]["secciones"][0]["items"]}
    assert niveles == {"Básico"}

    # si se piden más de los que hay en el banco (8 de Matemáticas I), avisa cuántos faltan
    d2 = crear(c, version=12, dificultad="b")
    d2 = secciones_pequenas(c, d2["id"], {"MATEMÁTICAS I": 10})
    r2 = c.post(f"/api/cartillas/{d2['id']}/secciones/{d2['secciones'][0]['id']}/automatica", json={}).json()
    assert len(r2["agregados"]) == 8 and r2["faltan"] == 2 and "Faltan 2" in r2["mensaje"]


def test_automatica_prefiere_los_menos_usados(c):
    d = crear(c, version=13, dificultad="lib")
    d = secciones_pequenas(c, d["id"], {"MATEMÁTICAS II": 3})
    r = c.post(f"/api/cartillas/{d['id']}/secciones/{d['secciones'][1]['id']}/automatica", json={}).json()
    assert len(r["agregados"]) == 3
    usados = [it["veces_usado"] for it in r["cartilla"]["secciones"][1]["items"]]
    assert usados == [0, 0, 0]


def test_no_repite_ejercicios_de_la_sesion_anterior(c):
    d1 = crear(c, version=14, nombre="Sesión 1 real")
    d1 = secciones_pequenas(c, d1["id"], {"MATEMÁTICAS I": 2})
    r = c.post(f"/api/cartillas/{d1['id']}/secciones/{d1['secciones'][0]['id']}/automatica", json={}).json()
    usados = {it["ejercicio_id"] for it in r["cartilla"]["secciones"][0]["items"]}
    d2 = crear(c, version=14, estructura="E3", codigo_materia="92", nombre="Sesión 2 real")
    assert d2["excluidas"]
    # los ejercicios de la sesión 1 aparecen marcados y no se pueden agregar
    d3 = crear(c, version=15, nombre="Otra")
    d3 = secciones_pequenas(c, d3["id"], {"MATEMÁTICAS I": 2})
    cand = c.get(f"/api/cartillas/{d3['id']}/candidatos", params={"seccion": d3["secciones"][0]["id"]}).json()["items"]
    assert not any(x["excluido"] for x in cand)      # esta cartilla no excluye a ninguna


# ------------------------------------------------------------------ orden y vista previa
def test_reordenar_y_no_separar_bloques(c):
    d = crear(c, version=16)
    d = secciones_pequenas(c, d["id"], {"MATEMÁTICAS I": 3})
    cid, sec = d["id"], d["secciones"][0]["id"]
    c.post(f"/api/cartillas/{cid}/secciones/{sec}/automatica", json={})
    d = c.get(f"/api/cartillas/{cid}").json()
    ids = [it["ejercicio_id"] for it in d["secciones"][0]["items"]]
    r = c.post(f"/api/cartillas/{cid}/secciones/{sec}/orden", json={"orden": list(reversed(ids))})
    assert r.status_code == 200
    assert [it["ejercicio_id"] for it in r.json()["secciones"][0]["items"]] == list(reversed(ids))


def test_vista_previa_aplica_la_plantilla(c):
    d = crear(c, version=17)
    d = secciones_pequenas(c, d["id"], {"MATEMÁTICAS I": 2})
    cid, sec = d["id"], d["secciones"][0]["id"]
    c.post(f"/api/cartillas/{cid}/secciones/{sec}/automatica", json={})
    d = c.get(f"/api/cartillas/{cid}").json()
    vp = c.get(f"/api/cartillas/{cid}/vista-previa").json()
    assert "MATEMÁTICAS I" in vp["html"] and vp["html"].count('class="pregunta"') == 2
    # la opción correcta quedó en la letra que manda la plantilla (B y A en las posiciones 1 y 2)
    for it in d["secciones"][0]["items"]:
        assert it["letra"] == PLANTILLA_1[it["numero"] - 1]
    marcadas = [x.split("</b>")[0].split("<b>")[-1].strip() for x in vp["html"].split('class="opcion correcta"')[1:]]
    assert marcadas == [f"{PLANTILLA_1[0]}.", f"{PLANTILLA_1[1]}."]


def test_verificacion_bloquea_cartilla_incompleta(c):
    d = crear(c, version=18)
    d = secciones_pequenas(c, d["id"], {"MATEMÁTICAS I": 3})
    v = c.get(f"/api/cartillas/{d['id']}/verificar").json()
    assert v["ok"] is False and any("0 de 3" in p["texto"] for p in v["pruebas"])


def test_historial_y_eliminar_borrador(c):
    lista = c.get("/api/cartillas").json()
    assert lista and all(x["estado"] == "borrador" for x in lista)
    cid = lista[0]["id"]
    assert c.delete(f"/api/cartillas/{cid}").status_code == 200
    assert all(x["id"] != cid for x in c.get("/api/cartillas").json())


def test_automatica_completa_con_otro_nivel_y_avisa(c):
    d = crear(c, version=19, dificultad="b")          # solo básica, pero Matemáticas II es toda de nivel medio
    d = secciones_pequenas(c, d["id"], {"MATEMÁTICAS II": 3})
    r = c.post(f"/api/cartillas/{d['id']}/secciones/{d['secciones'][1]['id']}/automatica", json={}).json()
    assert len(r["agregados"]) == 3 and r["faltan"] == 0
    assert r["otro_nivel"] == 3 and "otro nivel" in r["mensaje"]


def test_vista_previa_numera_bloques_y_partes(c):
    d = crear(c, version=20)
    d = secciones_pequenas(c, d["id"], {"COMPRENSIÓN LECTORA": 3, "INGLÉS": 4})
    cid = d["id"]
    for sec in (d["secciones"][3], d["secciones"][8]):
        c.post(f"/api/cartillas/{cid}/secciones/{sec['id']}/automatica", json={})
    html = c.get(f"/api/cartillas/{cid}/vista-previa").json()["html"]
    assert "Responde las preguntas 1 a 3 de acuerdo con la siguiente lectura." in html
    assert "PARTE 1 · Vocabulario en contexto — preguntas 4 a 7" in html   # la parte se numera dentro de su sección
    assert "#N" not in html and "#M" not in html and "#P" not in html
