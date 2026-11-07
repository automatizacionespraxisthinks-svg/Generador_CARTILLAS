"""Panel de estadísticas, buscador avanzado de ejercicios y carga en dos pasos (revisar y guardar)."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.fabrica import ejercicio, imagen_gris

DATOS = {"grado": "77", "estructura": "E1", "tipo_material": "33", "plantilla": 1,
         "institucion": "Institución Educativa de prueba", "nombre": "Buscador", "simulacro_n": 1}


@pytest.fixture(scope="module")
def c(tmp_path_factory):
    img = imagen_gris(tmp_path_factory.mktemp("img") / "g.png")
    with TestClient(app) as cliente:
        archivos = [
            ejercicio("Fracciones", nivel="Básico", clave="A", glosario=[(1, "grado", "Curso escolar.")]),
            ejercicio("Fracciones", nivel="Medio", clave="B", imagen=img, variante="dos"),
            ejercicio("Porcentajes", nivel="Avanzado", clave="C", tabla=True,
                      competencia="Modelación", pensamiento="Numérico", dba="DBA 5"),
            ejercicio("Lectura inicial", materia="Lengua Castellana", submateria="Comprensión Lectora",
                      pensamiento="", dba="", n=2, bloque=True),
        ]
        for nombre, datos in archivos:
            r = cliente.post("/api/cargar", files=[("archivos", (nombre, datos))], data={"solo_revisar": "false"}).json()[0]
            assert r["estado"] == "aceptado", r["errores"]
        yield cliente


def armar(c):
    """Una cartilla nueva por llamada: cada una lleva su propia versión en el código."""
    version = len(c.get("/api/cartillas").json()) + 1
    d = c.post("/api/cartillas", json={**DATOS, "version": version}).json()
    assert "secciones" in d, d
    cuerpo = [{"id": s["id"], "titulo": s["titulo"], "materia": s["materia"], "submateria": s["submateria"],
               "cantidad": 3 if s["titulo"] == "MATEMÁTICAS I" else 0, "dificultad": "lib"} for s in d["secciones"]]
    d = c.put(f"/api/cartillas/{d['id']}/secciones", json={"secciones": cuerpo}).json()
    return d, next(s for s in d["secciones"] if s["cantidad"])["id"]


# ================================================================== panel
def test_panel_cuenta_el_banco(c):
    e = c.get("/api/estadisticas").json()
    b = e["banco"]
    assert b["total"] == 5 and b["unidades"] == 1 and b["sin_usar"] == 5
    assert b["por_tipo"] == {"suelto": 3, "bloque": 2, "parte": 0}
    assert b["con_imagen"] == 1 and b["con_tabla"] == 1 and b["con_glosario"] == 1
    assert b["tematicas_distintas"] == 3                       # Fracciones, Porcentajes y Lectura inicial
    mat = next(x for x in b["por_materia"] if x["submateria"] == "Matemáticas I")
    assert mat["n"] == 3 and mat["nombre_grado"] == "7°"
    fracciones = next(t for t in b["tematicas"] if t["tematica"] == "Fracciones")
    assert fracciones["n"] == 2 and fracciones["sin_usar"] == 2


def test_panel_dice_que_falta_para_cada_estructura(c):
    cob = [x for x in c.get("/api/estadisticas").json()["cobertura"] if x["grado"] == "77"]
    e1 = next(x for x in cob if x["estructura"] == "E1")
    assert e1["necesita"] == 140 and e1["hay"] == 5 and e1["faltan"] == 135
    seccion = next(s for s in e1["secciones"] if s["titulo"] == "MATEMÁTICAS I")
    assert seccion["hay"] == 3 and seccion["necesita"] == 15 and seccion["faltan"] == 12
    assert not [x for x in cob if x["estructura"] in ("E5", "E6")]       # son de ICFES


# ================================================================== buscador
def test_buscador_cuenta_cada_tematica(c):
    d, sec = armar(c)
    r = c.get(f"/api/cartillas/{d['id']}/candidatos", params={"seccion": sec}).json()
    assert r["disponibles"] == 3 and r["total"] == 3 and r["faltan"] == 3
    tematicas = {x["valor"]: x["n"] for x in r["facetas"]["tematicas"]}
    assert tematicas == {"Fracciones": 2, "Porcentajes": 1}
    assert [x["valor"] for x in r["facetas"]["tematicas"]] == ["Fracciones", "Porcentajes"]   # orden alfabético
    assert all(x["elegidos"] == 0 for x in r["facetas"]["tematicas"])
    assert {x["valor"]: x["n"] for x in r["facetas"]["niveles"]} == {"Básico": 1, "Medio": 1, "Avanzado": 1}
    assert {x["valor"] for x in r["facetas"]["competencias"]} == {"Resolución de problemas", "Modelación"}


@pytest.mark.parametrize("filtros,esperado", [
    ({"tematica": "Fracciones"}, 2),
    ({"tematica": "Fracciones;Porcentajes"}, 3),
    ({"nivel": "Básico;Medio"}, 2),
    ({"competencia": "Modelación"}, 1),
    ({"dba": "DBA 5"}, 1),
    ({"recurso": "imagen"}, 1),
    ({"recurso": "tabla"}, 1),
    ({"recurso": "glosario"}, 1),
    ({"recurso": "sin_imagen"}, 2),
    ({"texto": "Porcentajes"}, 1),
    ({"texto": "no existe esto"}, 0),
    ({"sin_usar": "1"}, 3),
    ({"tipo": "suelto"}, 3),
    ({"tipo": "bloque"}, 0),
])
def test_buscador_filtra(c, filtros, esperado):
    d, sec = armar(c)
    r = c.get(f"/api/cartillas/{d['id']}/candidatos", params={"seccion": sec, **filtros}).json()
    assert r["total"] == esperado, [x["codigo"] for x in r["items"]]


def test_buscador_ordena(c):
    d, sec = armar(c)
    pedir = lambda orden: [x["tematica"] for x in c.get(f"/api/cartillas/{d['id']}/candidatos",
                                                        params={"seccion": sec, "orden": orden}).json()["items"]]
    assert pedir("tematica") == ["Fracciones", "Fracciones", "Porcentajes"]
    assert pedir("nivel")[0] == "Fracciones"                   # el Básico primero
    assert pedir("recientes")[0] == "Porcentajes"              # el último cargado


def test_la_tematica_sigue_en_la_lista_aunque_se_agote(c):
    """La columna de temáticas no puede cambiar de contenido al elegir: solo baja el número de disponibles."""
    d, sec = armar(c)
    url = f"/api/cartillas/{d['id']}/candidatos"
    for x in c.get(url, params={"seccion": sec, "tematica": "Porcentajes"}).json()["items"]:
        c.post(f"/api/cartillas/{d['id']}/items", json={"seccion": sec, "ejercicio": x["id"]})
    r = c.get(url, params={"seccion": sec}).json()
    por = {x["valor"]: x for x in r["facetas"]["tematicas"]}
    assert list(por) == ["Fracciones", "Porcentajes"]          # alfabético y completo
    assert por["Porcentajes"] == {"valor": "Porcentajes", "n": 0, "elegidos": 1}
    assert por["Fracciones"] == {"valor": "Fracciones", "n": 2, "elegidos": 0}
    assert r["seccion"] == {"titulo": "MATEMÁTICAS I", "cantidad": 3, "elegidos": 1}
    assert {x["valor"]: x["elegidos"] for x in r["facetas"]["niveles"]}["Avanzado"] == 1


def test_cada_candidato_dice_cuantos_de_su_tematica_ya_estan(c):
    d, sec = armar(c)
    url = f"/api/cartillas/{d['id']}/candidatos"
    uno = next(x for x in c.get(url, params={"seccion": sec}).json()["items"] if x["tematica"] == "Fracciones")
    assert uno["en_seccion"] == 0
    c.post(f"/api/cartillas/{d['id']}/items", json={"seccion": sec, "ejercicio": uno["id"]})
    r = c.get(url, params={"seccion": sec}).json()
    assert [x["en_seccion"] for x in r["items"] if x["tematica"] == "Fracciones"] == [1]
    assert [x["en_seccion"] for x in r["items"] if x["tematica"] == "Porcentajes"] == [0]


def test_las_facetas_no_se_recortan_con_un_filtro_puesto(c):
    """Con una temática filtrada, las demás siguen a la vista para poder sumarlas."""
    d, sec = armar(c)
    r = c.get(f"/api/cartillas/{d['id']}/candidatos", params={"seccion": sec, "tematica": "Fracciones"}).json()
    assert r["total"] == 2
    assert {x["valor"] for x in r["facetas"]["tematicas"]} == {"Fracciones", "Porcentajes"}
    assert {x["valor"] for x in r["facetas"]["niveles"]} == {"Básico", "Medio", "Avanzado"}


def test_los_ya_elegidos_salen_de_la_lista(c):
    d, sec = armar(c)
    r = c.get(f"/api/cartillas/{d['id']}/candidatos", params={"seccion": sec}).json()
    elegido = r["items"][0]["id"]
    c.post(f"/api/cartillas/{d['id']}/items", json={"seccion": sec, "ejercicio": elegido})
    r = c.get(f"/api/cartillas/{d['id']}/candidatos", params={"seccion": sec}).json()
    assert elegido not in [x["id"] for x in r["items"]] and r["disponibles"] == 2 and r["faltan"] == 2


def test_vista_previa_del_candidato(c):
    d, sec = armar(c)
    item = c.get(f"/api/cartillas/{d['id']}/candidatos", params={"seccion": sec}).json()["items"][0]
    previa = c.get(f"/api/banco/{item['id']}").json()
    assert previa["codigo"] == item["codigo"] and "opcion" in previa["html"] and previa["justificacion"]


# ================================================================== carga en dos pasos
def test_revisar_no_guarda_hasta_que_se_pulsa_guardar(c):
    antes = c.get("/api/banco/resumen").json()["total"]
    nombre, datos = ejercicio("Potenciación", clave="D")
    r = c.post("/api/revisar", files=[("archivos", (nombre, datos))]).json()[0]
    assert r["estado"] == "aceptado" and r["pendiente_id"] and r["guardado"] is None
    assert c.get("/api/banco/resumen").json()["total"] == antes          # todavía no entra
    assert [p["id"] for p in c.get("/api/pendientes").json()] == [r["pendiente_id"]]

    guardado = c.post("/api/pendientes/guardar", json={"ids": [r["pendiente_id"]]}).json()[0]
    assert guardado["estado"] == "aceptado" and guardado["guardado"]["codigos"]
    assert c.get("/api/banco/resumen").json()["total"] == antes + 1
    assert c.get("/api/pendientes").json() == []


def test_revisar_rechaza_sin_dejar_pendiente(c):
    import io

    from docx import Document
    nombre, datos = ejercicio("Mal hecho", clave="A")
    doc = Document(io.BytesIO(datos))
    next(x for x in doc.paragraphs if x.text == "TABLA DE EXCEL").runs[0].text = "TABLA DE EXCELL"   # rótulo mal escrito
    buf = io.BytesIO()
    doc.save(buf)
    r = c.post("/api/revisar", files=[("archivos", (nombre, buf.getvalue()))]).json()[0]
    assert r["estado"] == "rechazado" and not r.get("pendiente_id")
    assert c.get("/api/pendientes").json() == []


def test_descartar_lo_revisado(c):
    nombre, datos = ejercicio("Para descartar", clave="B")
    r = c.post("/api/revisar", files=[("archivos", (nombre, datos))]).json()[0]
    antes = c.get("/api/banco/resumen").json()["total"]
    assert c.delete(f"/api/pendientes/{r['pendiente_id']}").json()["descartado"] == nombre
    assert c.get("/api/pendientes").json() == []
    assert c.get("/api/banco/resumen").json()["total"] == antes


# ================================================================== Ciencias Sociales de 6° a 9°
def test_sociales_de_sexto_toma_la_materia_completa(tmp_path_factory):
    """En 6° a 9° no hay sección aparte de Ciencias Económicas y Políticas: todo lo de la materia entra
    en CIENCIAS SOCIALES, con submateria o sin ella (decisión del 07/10/2026)."""
    with TestClient(app) as c:
        for sub in ("", "Ciencias Económicas y Políticas"):
            nombre, datos = ejercicio("Las civilizaciones minoica y micénica", grado="66", materia="Ciencias Sociales",
                                      submateria=sub, pensamiento="Historia y cultura", competencia="Culturalidad",
                                      dba="DBA 4", clave="B", variante=sub or "sin")
            r = c.post("/api/cargar", files=[("archivos", (nombre, datos))], data={"solo_revisar": "false"}).json()[0]
            assert r["estado"] == "aceptado", r["errores"]
        version = len(c.get("/api/cartillas").json()) + 1
        d = c.post("/api/cartillas", json={**DATOS, "grado": "66", "version": version}).json()
        sec = next(x for x in d["secciones"] if x["titulo"] == "CIENCIAS SOCIALES")
        assert sec["mezclada"] and sec["admitidas"] == ["Ciencias Sociales|", "Ciencias Sociales|Ciencias Económicas y Políticas"]
        cuerpo = [{"id": x["id"], "titulo": x["titulo"], "materia": x["materia"], "submateria": x["submateria"],
                   "cantidad": 2 if x["titulo"] == "CIENCIAS SOCIALES" else 0, "dificultad": "lib"} for x in d["secciones"]]
        d = c.put(f"/api/cartillas/{d['id']}/secciones", json={"secciones": cuerpo}).json()
        sec = next(x for x in d["secciones"] if x["titulo"] == "CIENCIAS SOCIALES")["id"]
        r = c.get(f"/api/cartillas/{d['id']}/candidatos", params={"seccion": sec}).json()
        assert r["disponibles"] == 2, [x["codigo"] for x in r["items"]]
        assert {x["submateria"] for x in r["items"]} == {"", "Ciencias Económicas y Políticas"}
        for x in r["items"]:                                   # los dos se pueden agregar de verdad
            assert c.post(f"/api/cartillas/{d['id']}/items",
                          json={"seccion": sec, "ejercicio": x["id"]}).status_code == 200


# ================================================================== buscar por tema, como lo escribe un docente
@pytest.mark.parametrize("escrito,encuentra", [
    ("Fracciones", True),               # tal cual
    ("fracciones", True),               # sin mayúsculas
    ("FRACCION", True),                 # singular: «fracciones» y «fracción» son el mismo tema
    ("fraccion de un todo", False),     # pide dos cosas que no están juntas
    ("porcentajes, fracciones", True),  # varios temas separados por coma: basta con que coincida uno
    ("de la el", True),                 # solo palabras de enlace: no filtra nada
    ("mitosis", False),
])
def test_el_buscador_entiende_como_se_escribe(c, escrito, encuentra):
    d, sec = armar(c)
    r = c.get(f"/api/cartillas/{d['id']}/candidatos", params={"seccion": sec, "texto": escrito}).json()
    assert (r["total"] > 0) is encuentra, [x["tematica"] for x in r["items"]]


def test_buscar_dice_en_que_seccion_esta_cada_tema(c):
    """Un docente escribe los temas que está viendo y el sistema le dice dónde ponerlos."""
    d, _ = armar(c)
    r = c.get(f"/api/cartillas/{d['id']}/buscar", params={"texto": "fracciones, lectura inicial"}).json()
    assert r["total"] >= 3
    con = {s["titulo"]: s["encontrados"] for s in r["secciones"] if s["encontrados"]}
    assert con.get("MATEMÁTICAS I") == 2 and con.get("COMPRENSIÓN LECTORA") == 2   # el bloque trae 2 preguntas
    temas = {t["tematica"]: t for t in r["tematicas"]}
    assert temas["Fracciones"]["n"] == 2 and temas["Fracciones"]["secciones"] == ["MATEMÁTICAS I"]


def test_buscar_sin_texto_no_devuelve_nada(c):
    d, _ = armar(c)
    r = c.get(f"/api/cartillas/{d['id']}/buscar", params={"texto": "   "}).json()
    assert r["secciones"] == [] and r["tematicas"] == []


# ================================================================== eliminar cartillas
def test_eliminar_un_borrador(c):
    d, sec = armar(c)
    item = c.get(f"/api/cartillas/{d['id']}/candidatos", params={"seccion": sec}).json()["items"][0]
    c.post(f"/api/cartillas/{d['id']}/items", json={"seccion": sec, "ejercicio": item["id"]})
    antes = c.get(f"/api/banco/{item['id']}").json()["veces_usado"]
    r = c.delete(f"/api/cartillas/{d['id']}")
    assert r.status_code == 200 and r.json()["generada"] is False
    assert d["id"] not in [x["id"] for x in c.get("/api/cartillas").json()]
    assert c.get(f"/api/banco/{item['id']}").json()["veces_usado"] == antes      # el ejercicio sigue intacto


def test_eliminar_una_generada_devuelve_el_uso_y_borra_sus_archivos(c):
    """Antes no se dejaban eliminar y la página no decía por qué. Ahora sí, descontando el uso (07/10/2026)."""
    d, sec = armar(c)
    for x in c.get(f"/api/cartillas/{d['id']}/candidatos", params={"seccion": sec}).json()["items"][:3]:
        c.post(f"/api/cartillas/{d['id']}/items", json={"seccion": sec, "ejercicio": x["id"]})
    elegidos = [i["ejercicio_id"] for s_ in c.get(f"/api/cartillas/{d['id']}").json()["secciones"] for i in s_["items"]]
    antes = {e: c.get(f"/api/banco/{e}").json()["veces_usado"] for e in elegidos}
    assert c.post(f"/api/cartillas/{d['id']}/generar", json={}).status_code == 200
    assert all(c.get(f"/api/banco/{e}").json()["veces_usado"] == antes[e] + 1 for e in elegidos)
    assert c.get(f"/api/cartillas/{d['id']}/archivo/docx").status_code == 200

    r = c.delete(f"/api/cartillas/{d['id']}")
    assert r.status_code == 200 and r.json()["generada"] is True and r.json()["preguntas"] == 3
    assert d["id"] not in [x["id"] for x in c.get("/api/cartillas").json()]
    assert all(c.get(f"/api/banco/{e}").json()["veces_usado"] == antes[e] for e in elegidos)   # uso devuelto
    assert c.get(f"/api/cartillas/{d['id']}/archivo/docx").status_code == 404


def test_eliminar_una_que_no_existe(c):
    assert c.delete("/api/cartillas/999999").status_code == 404


# ================================================================== los bloques no se desordenan
def posiciones_guardadas(cid, seccion_id):
    """Las posiciones tal como quedaron en la base, que son las que mandan en el orden impreso."""
    from sqlalchemy import select

    from app.bd import CartillaItem, Ejercicio, Sesion
    with Sesion() as s:
        filas = s.execute(select(CartillaItem.posicion, Ejercicio.codigo, Ejercicio.bloque_id, Ejercicio.orden_en_bloque)
                          .join(Ejercicio, Ejercicio.id == CartillaItem.ejercicio_id)
                          .where(CartillaItem.cartilla_id == cid, CartillaItem.seccion_id == seccion_id)
                          .order_by(CartillaItem.posicion)).all()
    return [tuple(x) for x in filas]


def test_la_seleccion_automatica_no_repite_posiciones(c):
    """Error del 07/10/2026: la automática recalculaba la última posición sobre c.items, que todavía no
    traía lo recién agregado. Cada unidad empezaba otra vez en 1 y en el Word los bloques salían mezclados."""
    d, sec = armar(c)
    r = c.post(f"/api/cartillas/{d['id']}/secciones/{sec}/automatica", json={}).json()
    assert r["cartilla"]["elegidos"] >= 2, r["mensaje"]
    posiciones = [p for p, *_ in posiciones_guardadas(d["id"], sec)]
    assert posiciones == list(range(1, len(posiciones) + 1)), f"posiciones repetidas o con huecos: {posiciones}"


def test_los_bloques_quedan_seguidos_y_en_su_orden(c):
    """Dentro de un bloque el orden es parte del ejercicio: las preguntas se refieren al mismo texto."""
    version = len(c.get("/api/cartillas").json()) + 1
    d = c.post("/api/cartillas", json={**DATOS, "version": version}).json()
    sec = next(s for s in d["secciones"] if s["titulo"] == "COMPRENSIÓN LECTORA")
    cuerpo = [{"id": s["id"], "titulo": s["titulo"], "materia": s["materia"], "submateria": s["submateria"],
               "cantidad": 2 if s["id"] == sec["id"] else 0, "dificultad": "lib"} for s in d["secciones"]]
    c.put(f"/api/cartillas/{d['id']}/secciones", json={"secciones": cuerpo})
    c.post(f"/api/cartillas/{d['id']}/secciones/{sec['id']}/automatica", json={})
    filas = posiciones_guardadas(d["id"], sec["id"])
    por_bloque = {}
    for pos, _cod, bid, orden in filas:
        if bid:
            por_bloque.setdefault(bid, []).append((pos, orden))
    assert por_bloque, "la prueba necesita al menos un bloque"
    for bid, pares in por_bloque.items():
        pos = [p for p, _ in pares]
        assert pos == list(range(min(pos), min(pos) + len(pos))), f"el bloque {bid} quedó partido: {pos}"
        assert [o for _, o in pares] == sorted(o for _, o in pares), f"el bloque {bid} quedó al revés"


def test_el_reordenador_no_mete_preguntas_dentro_de_un_bloque():
    """Si una columna termina dentro de un bloque, no se adelanta nada ahí: lo partiría en dos."""
    from app import maqueta

    piezas = [{"clave": "E1", "tipo": "pregunta", "seccion": 1, "codigo": "A", "bloque": 7},
              {"clave": "E2", "tipo": "pregunta", "seccion": 1, "codigo": "B", "bloque": 7},
              {"clave": "E3", "tipo": "pregunta", "seccion": 1, "codigo": "C", "bloque": None}]
    altos = {"E1": 100, "E2": 100, "E3": 50}
    cols = [{"piezas": ["E1"], "hueco": 400}]                      # la columna acaba en mitad del bloque
    assert maqueta.proponer(piezas, altos, cols, ["E1", "E2", "E3"]) == []
    cols = [{"piezas": ["E1", "E2"], "hueco": 400}]                # acaba al final del bloque: tampoco
    assert maqueta.proponer(piezas, altos, cols, ["E1", "E2", "E3"]) == []


def test_el_reordenador_si_adelanta_una_pregunta_cuando_cabe():
    """Lo contrario del caso anterior: con un hueco de verdad tiene que proponer algo."""
    from app import maqueta

    piezas = [{"clave": "E1", "tipo": "pregunta", "seccion": 1, "codigo": "A", "bloque": None},
              {"clave": "E2", "tipo": "pregunta", "seccion": 1, "codigo": "B", "bloque": None},
              {"clave": "E3", "tipo": "pregunta", "seccion": 1, "codigo": "C", "bloque": None}]
    altos = {"E1": 100, "E2": 500, "E3": 120}
    # la columna acaba en E1 y le sobran 200 pt: E2 no cabe, pero E3 sí
    cols = [{"piezas": ["E1"], "hueco": 200}, {"piezas": ["E2", "E3"], "hueco": 0}]
    p = maqueta.proponer(piezas, altos, cols, ["E1", "E2", "E3"])
    assert [x["clave"] for x in p] == ["E3"] and p[0]["tras"] == "E1"

    # si no cupiera ninguna, no propone nada
    assert maqueta.proponer(piezas, {"E1": 100, "E2": 500, "E3": 500}, cols, ["E1", "E2", "E3"]) == []


def test_el_reordenador_no_mezcla_secciones():
    """Adelantar una pregunta de otra sección cambiaría de sitio un área entera de la prueba."""
    from app import maqueta

    piezas = [{"clave": "E1", "tipo": "pregunta", "seccion": 1, "codigo": "A", "bloque": None},
              {"clave": "S2", "tipo": "titulo", "seccion": 2, "codigo": None, "bloque": None},
              {"clave": "E2", "tipo": "pregunta", "seccion": 2, "codigo": "B", "bloque": None}]
    cols = [{"piezas": ["E1"], "hueco": 400}]
    assert maqueta.proponer(piezas, {"E1": 100, "E2": 80}, cols, ["E1", "S2", "E2"]) == []


def test_lo_que_sobra_tras_la_ultima_pregunta_no_es_desperdicio():
    """No hay nada después que adelantar hasta ahí: contarlo hacía creer que había mucho que ganar."""
    from app import maqueta

    assert maqueta.desperdicio([{"hueco": 30}, {"hueco": 50}, {"hueco": 659}]) == 80
    assert maqueta.desperdicio([{"hueco": 659}]) == 0          # una sola columna: toda ella es la cola
    assert maqueta.desperdicio([]) == 0


# ================================================================== prompt para pasar simulacros al formato
def test_el_prompt_sale_de_los_catalogos_de_verdad(c):
    """No está escrito a mano: si mañana hay una materia o un grado nuevo, el prompt lo dice solo."""
    t = c.get("/api/prompt").json()["texto"]
    assert "TABLA DE EXCEL" in t and "TABLA DE RESPUESTAS" in t and "TABLA DE GLOSARIO" in t
    for grado in ("3°", "6°", "11°"):
        assert grado in t
    for nivel in ("Básico", "Medio", "Avanzado"):
        assert nivel in t
    assert "Matemáticas I" in t and "Comprensión Lectora" in t          # submaterias del catálogo
    assert "todas las anteriores" in t.lower()                          # la regla que más se incumple
    assert len(t) > 3000


def test_el_prompt_liga_el_pensamiento_a_la_submateria(c):
    """Biología es «Entorno vivo» y Química «Entorno físico»: el pensamiento depende de la submateria."""
    t = c.get("/api/prompt").json()["texto"]
    bloques = {}
    actual = None
    for linea in t.splitlines():
        if linea.strip().startswith("- Submateria «"):
            actual = linea.split("«")[1].split("»")[0]
            bloques[actual] = []
        elif actual and linea.startswith("      "):
            bloques[actual].append(linea.strip())
    assert "Entorno vivo" in bloques["Biología"][0] and "Entorno físico" not in bloques["Biología"][0]
    assert "Entorno físico" in bloques["Química"][0]
    assert "Literatura" in bloques["Español"][0]
    assert "Lectura crítica" in bloques["Comprensión Lectora"][0]
    assert "Indagación" in bloques["Biología"][1]                       # la competencia sí es de toda la materia


def test_el_prompt_marca_lo_que_ya_se_usa_en_el_banco(c):
    """El ✓ ayuda a mantener la misma redacción en todo el banco."""
    t = c.get("/api/prompt").json()["texto"]
    assert "Numérico-variacional" in t and "Competencia sociolingüística" in t      # valores del catálogo
    assert "✓" in t and "ya se usan en el banco" in t


def test_el_prompt_trae_los_dba_de_ingles_y_la_regla_de_la_tematica(c):
    t = c.get("/api/prompt").json()["texto"]
    assert "DBA 8: tema general de un texto corto" in t
    assert "malla del grado" in t
    assert "consérvala tal cual" in t


def test_el_prompt_manda_escribir_las_matematicas_con_el_editor_de_ecuaciones(c):
    """La auditoría encontró 34 ejercicios con fracciones escritas «3/8»: se imprimen en línea, no apiladas."""
    t = c.get("/api/prompt").json()["texto"]
    assert "editor de ecuaciones" in t.lower()
    assert "Insertar › Ecuación" in t or "Insertar > Ecuación" in t
    for caso in ("Fracciones", "Raíces", "Números mixtos"):
        assert caso in t, f"el prompt no dice qué hacer con: {caso}"
    assert "se acepta" in t and "3/8" in t                     # a tamaño normal sí vale
    assert "se rechaza" in t and "³/₈" in t                    # la diminuta no
    assert "libro de texto" in t                               # el objetivo, dicho en una línea
    assert "H₂O" in t and "m²" in t                            # lo que va con superíndice, sin editor
    assert "como imagen" in t                                  # una fórmula nunca es una captura
    assert "Del tamaño no te preocupes" in t                   # lo pone la cartilla, no el archivo
    assert "No la agrandes a mano" in t


def test_el_prompt_pide_la_tematica_explicada(c):
    """Decisión del usuario: la temática se prefiere explicada, para elegir sin abrir la pregunta."""
    t = c.get("/api/prompt").json()["texto"]
    assert "explicada y precisa" in t
    assert "sin abrirla" in t                                  # para qué sirve que sea explicada
    assert "Así SÍ" in t and "Así NO" in t                     # la tabla de ejemplos buenos y malos
    assert "150 caracteres" in t                               # el límite que aguanta la base
    assert "letra por letra" in t                              # la misma redacción si evalúan lo mismo


def test_el_prompt_cubre_la_presentacion_y_las_opciones_con_figura(c):
    import re

    # el prompt va con saltos de línea: se comparan frases sin importar dónde corte la línea
    t = re.sub(r"\s+", " ", c.get("/api/prompt").json()["texto"])
    assert "El color se admite" in t                           # desde el 07/11/2026
    assert "casi blanco" in t and "casi negras" in t           # lo único que se sigue rechazando
    assert "8,4 cm" in t                                       # el ancho real de una columna
    assert "Tabla con cuadrícula" in t                         # el estilo de tabla que el sistema espera
    assert "mismo párrafo" in t and "letra" in t               # la opción que es una figura
    assert "submateria vacía" in t                             # Ciencias Sociales en 10° y 11°


def test_el_prompt_copia_los_encabezados_del_validador(c):
    """Si mañana cambia un encabezado, el prompt cambia solo: los toma de la misma constante."""
    from app.validador.validador import ENC_EXCEL, ENC_GLOSARIO, ENC_RESPUESTAS

    t = c.get("/api/prompt").json()["texto"]
    for enc in (ENC_RESPUESTAS, ENC_EXCEL, ENC_GLOSARIO):
        assert " | ".join(enc) in t, f"el prompt no trae los encabezados {enc}"
    assert "van VACÍAS" in t                                   # el error más caro: numerar a mano
    assert "sin nombrar ninguna letra" in t                    # la justificación no menciona letras
    assert "prohibido" in t and "ejercicio suelto" in t        # el crédito solo en bloques


@pytest.mark.parametrize("materia,sub", [
    ("Matemáticas", "Matemáticas I"), ("Lengua Castellana", "Español"),
    ("Lengua Castellana", "Comprensión Lectora"), ("Ciencias Sociales", ""),
    ("Ciencias Naturales", "Biología"), ("Ciencias Naturales", "Química"), ("Inglés", ""),
])
def test_los_valores_que_dicta_el_prompt_pasan_el_validador(c, materia, sub):
    """Lo que el prompt manda escribir tiene que entrar al banco sin un solo error."""
    from app.catalogos_base import pedagogia

    pens, comps = pedagogia(materia, sub or None)
    nombre, datos = ejercicio(f"Tema de prueba de {materia} {sub}".strip(), grado="66", materia=materia,
                              submateria=sub, pensamiento=pens[0] if pens else "", dba="DBA 3",
                              competencia=comps[0] if comps else "", clave="C", variante=materia + sub)
    r = c.post("/api/revisar", files=[("archivos", (nombre, datos))]).json()[0]
    assert r["estado"] == "aceptado", r["errores"]
    c.delete(f"/api/pendientes/{r['pendiente_id']}")


def test_el_prompt_explica_los_archivos_que_ya_traen_la_informacion(c):
    """Lo más común: el simulacro ya viene con sus dos tablas y su línea ➤. Reorganizar, no inventar."""
    t = c.get("/api/prompt").json()["texto"]
    assert "SI EL ARCHIVO YA TRAE LA INFORMACIÓN" in t
    assert "no inventes ni cambies nada" in t
    assert "Borra la línea ➤" in t and "segunda pregunta sin opciones" in t
    assert "Agrega la columna Grado" in t                       # la tabla original no la trae
    assert "BB, MM, AA" in t                                    # el nivel viene abreviado
    assert "archivo aparte" in t                                # el glosario suele venir por separado
    assert "Elaboración propia" in t                            # el crédito que falta en los bloques


def test_dejar_la_linea_de_datos_rompe_el_archivo(c):
    """Por qué el prompt insiste tanto: el validador la lee como otra pregunta."""
    import io

    from docx import Document
    nombre, datos = ejercicio("Con la línea de datos", clave="B")
    doc = Document(io.BytesIO(datos))
    for p in doc.paragraphs:
        if p.text.startswith("D. "):
            suelto = p.insert_paragraph_before("➤ Numérico // Resolución de problemas // DBA 2 // MM")
            p._p.addnext(suelto._p)
            break
    buf = io.BytesIO()
    doc.save(buf)
    r = c.post("/api/revisar", files=[("archivos", (nombre, buf.getvalue()))]).json()[0]
    assert r["estado"] == "rechazado"
    assert any("no tiene opciones" in e["mensaje"] for e in r["errores"])


# ================================================================== borrar un ejercicio del banco
def test_borrar_un_ejercicio_lo_saca_de_las_cartillas(c):
    """Error del 07/10/2026: al borrar un ejercicio del banco, las cartillas que lo usaban quedaban con
    una referencia colgando y **reventaban al generarse**. Ahora se le quita de la cartilla y se renumera."""
    from sqlalchemy import select

    from app.bd import CartillaItem, Ejercicio, Sesion
    d, sec = armar(c)
    elegidos = [x["id"] for x in c.get(f"/api/cartillas/{d['id']}/candidatos", params={"seccion": sec}).json()["items"][:3]]
    for eid in elegidos:
        c.post(f"/api/cartillas/{d['id']}/items", json={"seccion": sec, "ejercicio": eid})
    antes = len(c.get(f"/api/cartillas/{d['id']}").json()["secciones"])
    assert antes

    r = c.delete(f"/api/banco/{elegidos[0]}").json()
    assert any(x["codigo"] for x in r["cartillas"]), "no avisó de la cartilla afectada"

    with Sesion() as s:
        vivos = {e.id for e in s.scalars(select(Ejercicio))}
        colgando = [i for i in s.scalars(select(CartillaItem)) if i.ejercicio_id not in vivos]
    assert not colgando, "quedaron preguntas apuntando a un ejercicio que ya no existe"

    detalle = c.get(f"/api/cartillas/{d['id']}").json()
    items = [i for s_ in detalle["secciones"] for i in s_["items"]]
    assert elegidos[0] not in [i["ejercicio_id"] for i in items]
    posiciones = [i["numero"] for i in items]
    assert posiciones == list(range(1, len(posiciones) + 1))        # renumeradas, sin huecos
    assert c.get(f"/api/cartillas/{d['id']}/vista-previa").status_code == 200   # y se sigue pudiendo armar


# ================================================================== prueba general de una materia
def test_una_prueba_general_de_matematicas_usa_las_dos_submaterias(c):
    """Pedido del 07/10/2026: una sección que tome Matemáticas I y Matemáticas II a la vez."""
    version = len(c.get("/api/cartillas").json()) + 1
    d = c.post("/api/cartillas", json={"grado": "77", "estructura": "E4", "tipo_material": "33", "plantilla": 1,
                                       "codigo_materia": "03", "institucion": "Prueba general",
                                       "nombre": "Matemáticas", "simulacro_n": 1, "version": version}).json()
    cid = d["id"]
    r = c.put(f"/api/cartillas/{cid}/secciones", json={"secciones": [
        {"titulo": "MATEMÁTICAS", "materia": "Matemáticas", "submateria": "*", "cantidad": 3, "dificultad": "lib"}]})
    assert r.status_code == 200, r.json()
    sec = r.json()["secciones"][0]
    assert sec["mezclada"] is True
    assert sec["admitidas"] == ["Matemáticas|Matemáticas I", "Matemáticas|Matemáticas II"]

    # el buscador ofrece las dos submaterias
    cand = c.get(f"/api/cartillas/{cid}/candidatos", params={"seccion": sec["id"]}).json()
    submaterias = {x["submateria"] for x in cand["items"]}
    assert submaterias == {"Matemáticas I"}, submaterias     # el banco de prueba solo tiene de la I…
    assert {x["valor"] for x in cand["facetas"]["submaterias"]} == {"Matemáticas I"}

    # …y uno de Matemáticas II también entra
    nombre, datos = ejercicio("Área del rectángulo", grado="77", submateria="Matemáticas II",
                              pensamiento="Geométrico-métrico", clave="B", variante="general")
    guardado = c.post("/api/cargar", files=[("archivos", (nombre, datos))], data={"solo_revisar": "false"}).json()[0]
    assert guardado["estado"] == "aceptado", guardado["errores"]
    cand = c.get(f"/api/cartillas/{cid}/candidatos", params={"seccion": sec["id"]}).json()
    assert {x["submateria"] for x in cand["items"]} == {"Matemáticas I", "Matemáticas II"}
    for x in cand["items"][:3]:
        assert c.post(f"/api/cartillas/{cid}/items",
                      json={"seccion": sec["id"], "ejercicio": x["id"]}).status_code == 200
    assert c.get(f"/api/cartillas/{cid}").json()["elegidos"] == 3


def test_no_se_ofrece_mezclar_donde_no_hay_dos_submaterias(c):
    """En Inglés no hay submaterias, así que «todas» no tiene sentido."""
    version = len(c.get("/api/cartillas").json()) + 1
    d = c.post("/api/cartillas", json={"grado": "77", "estructura": "E4", "tipo_material": "33", "plantilla": 1,
                                       "codigo_materia": "08", "institucion": "Prueba", "nombre": "Inglés",
                                       "simulacro_n": 1, "version": version}).json()
    r = c.put(f"/api/cartillas/{d['id']}/secciones", json={"secciones": [
        {"titulo": "INGLÉS", "materia": "Inglés", "submateria": "*", "cantidad": 2, "dificultad": "lib"}]})
    assert r.status_code == 400 and "no tiene varias submaterias" in r.json()["detail"]


@pytest.mark.parametrize("materia,cod,subs,temas", [
    ("Matemáticas", "03", ["Matemáticas I", "Matemáticas II"],
     ["Fracciones equivalentes aquí", "Área del rectángulo aquí"]),
    ("Lengua Castellana", "04", ["Español", "Comprensión Lectora", "Lectura Crítica"],
     ["El sujeto de la oración", "Idea principal de un texto", "Intención del autor"]),
    ("Ciencias Naturales", "05", ["Biología", "Física", "Química", "Tecnología y Medio Ambiente"],
     ["Partes de la célula vegetal", "Caída libre de los cuerpos", "Mezclas homogéneas", "Manejo de residuos"]),
    ("Ciencias Sociales", "06", ["Ciencias Económicas y Políticas", ""],
     ["La oferta y la demanda", "El resguardo indígena"]),
])
def test_una_seccion_puede_tomar_toda_la_materia(c, materia, cod, subs, temas):
    """Una prueba general de una materia principal usa las preguntas de todas sus submaterias."""
    from app import catalogos_base as base

    version = len(c.get("/api/cartillas").json()) + 1
    d = c.post("/api/cartillas", json={"grado": "66", "estructura": "E4", "tipo_material": "33", "plantilla": 1,
                                       "codigo_materia": cod, "institucion": "General",
                                       "nombre": f"General {materia}", "simulacro_n": 1, "version": version}).json()
    cid = d["id"]
    r = c.put(f"/api/cartillas/{cid}/secciones", json={"secciones": [
        {"titulo": materia.upper(), "materia": materia, "submateria": "*",
         "cantidad": len(subs), "dificultad": "lib"}]}).json()
    sec = r["secciones"][0]
    esperadas = [f"{materia}|{x}" for x in subs if x] + ([f"{materia}|"] if "" in subs else [])
    assert sec["mezclada"] is True and sorted(sec["admitidas"]) == sorted(esperadas)

    for sub, tema in zip(subs, temas):
        pens, comps = base.pedagogia(materia, sub or None)
        nombre, datos = ejercicio(tema, grado="66", materia=materia, submateria=sub,
                                  pensamiento=pens[0] if pens else "", competencia=comps[0] if comps else "",
                                  dba="DBA 3", clave="A", variante=(sub or "general").replace(" ", ""))
        g = c.post("/api/cargar", files=[("archivos", (nombre, datos))], data={"solo_revisar": "false"}).json()[0]
        assert g["estado"] == "aceptado", (sub, g.get("errores"), g.get("similitudes"))

    cand = c.get(f"/api/cartillas/{cid}/candidatos", params={"seccion": sec["id"]}).json()
    assert {x["submateria"] for x in cand["items"]} == set(subs)

    # la selección automática también reparte entre todas las submaterias
    a = c.post(f"/api/cartillas/{cid}/secciones/{sec['id']}/automatica", json={}).json()
    assert a["cartilla"]["elegidos"] == len(subs), a["mensaje"]
    puestas = {i["submateria"] for s_ in a["cartilla"]["secciones"] for i in s_["items"]}
    assert puestas == set(subs), f"la automática no usó todas las submaterias: {puestas}"
    assert c.post(f"/api/cartillas/{cid}/generar", json={}).status_code == 200


# ================================================================== formas equivalentes de escribir lo mismo
def excel_cambiado(cambios, **kw):
    """Un ejercicio con esas celdas de la TABLA DE EXCEL cambiadas."""
    import io

    from docx import Document
    nombre, datos = ejercicio(kw.pop("tema", "Tema de normalización"), **kw)
    doc = Document(io.BytesIO(datos))
    for t in doc.tables:
        if [c.text.strip() for c in t.rows[0].cells][:2] == ["Preg.", "Correcta"]:
            for col, valor in cambios.items():
                celda = t.rows[1].cells[col].paragraphs[0]
                if celda.runs:
                    celda.runs[0].text = valor
                    for r in celda.runs[1:]:
                        r.text = ""
                else:
                    celda.add_run(valor)
    buf = io.BytesIO()
    doc.save(buf)
    return nombre, buf.getvalue()


def test_el_dba_que_dice_no_aplica_se_guarda_vacio(c):
    """Filosofía, Ética o Informática no tienen DBA oficial: decirlo no puede ser un error."""
    nombre, datos = excel_cambiado({3: "Filosofía", 4: "", 7: "No aplica"}, tema="Las ideas de Sócrates",
                                   grado="77", materia="Filosofía", submateria="", variante="dba")
    r = c.post("/api/revisar", files=[("archivos", (nombre, datos))]).json()[0]
    assert r["estado"] == "aceptado", r["errores"]
    assert any("se guarda vacío" in a["mensaje"] for a in r["avisos"]), r["avisos"]
    assert r["filas"][0]["dba"] == ""


def test_la_submateria_que_dice_no_aplica_se_guarda_vacia(c):
    nombre, datos = excel_cambiado({3: "Filosofía", 4: "Ninguna", 7: "DBA 2"}, tema="El concepto de virtud",
                                   grado="77", materia="Filosofía", submateria="", variante="sub")
    r = c.post("/api/revisar", files=[("archivos", (nombre, datos))]).json()[0]
    assert r["estado"] == "aceptado", r["errores"]
    assert any("no tiene submaterias" in a["mensaje"] for a in r["avisos"]), r["avisos"]
    assert r["filas"][0]["submateria"] == ""


def test_una_submateria_escrita_como_materia_se_entiende(c):
    """«Ciencias Económicas y Políticas» en la columna Materia: es inequívoco, ninguna submateria se
    llama como una materia. Se guarda en la forma canónica y se avisa (decisión del 08/10/2026)."""
    nombre, datos = excel_cambiado({3: "Ciencias Económicas y Políticas", 4: "", 5: "Historia y cultura",
                                    6: "Culturalidad"}, tema="El mercado y los precios", grado="77",
                                   materia="Ciencias Sociales", submateria="", variante="cep")
    r = c.post("/api/revisar", files=[("archivos", (nombre, datos))]).json()[0]
    assert r["estado"] == "aceptado", r["errores"]
    assert any("es una submateria de Ciencias Sociales" in a["mensaje"] for a in r["avisos"]), r["avisos"]
    assert r["filas"][0]["materia"] == "Ciencias Sociales"
    assert r["filas"][0]["submateria"] == "Ciencias Económicas y Políticas"


def test_una_materia_escrita_como_submateria_se_entiende(c):
    """Filosofía dentro de Ciencias Sociales: es materia propia y así se guarda."""
    nombre, datos = excel_cambiado({3: "Ciencias Sociales", 4: "Filosofía"}, tema="La duda metódica",
                                   grado="77", materia="Ciencias Sociales", submateria="", variante="fil")
    r = c.post("/api/revisar", files=[("archivos", (nombre, datos))]).json()[0]
    assert r["estado"] == "aceptado", r["errores"]
    assert any("es una materia propia" in a["mensaje"] for a in r["avisos"]), r["avisos"]
    assert r["filas"][0]["materia"] == "Filosofía" and r["filas"][0]["submateria"] == ""


def test_una_submateria_de_verdad_equivocada_se_sigue_rechazando(c):
    """La tolerancia no puede tapar un error real: Biología no es submateria de Matemáticas."""
    nombre, datos = excel_cambiado({3: "Matemáticas", 4: "Biología"}, tema="Un tema cualquiera",
                                   grado="77", variante="mala")
    r = c.post("/api/revisar", files=[("archivos", (nombre, datos))]).json()[0]
    assert r["estado"] == "rechazado"
    assert any("no pertenece a Matemáticas" in e["mensaje"] for e in r["errores"]), r["errores"]


def test_una_seccion_puede_mezclar_varias_materias(c):
    """Una prueba general de Sociales que incluya Filosofía, como la del ICFES (08/10/2026)."""
    version = len(c.get("/api/cartillas").json()) + 1
    d = c.post("/api/cartillas", json={"grado": "77", "estructura": "E4", "tipo_material": "33", "plantilla": 1,
                                       "codigo_materia": "06", "institucion": "General",
                                       "nombre": "Sociales y ciudadanas", "simulacro_n": 1,
                                       "version": version}).json()
    for materia, sub, tema in (("Ciencias Sociales", "", "El Frente Nacional"),
                               ("Filosofía", "", "El mito de la caverna")):
        nombre, datos = ejercicio(tema, grado="77", materia=materia, submateria=sub,
                                  pensamiento="Historia y cultura" if sub == "" and materia == "Ciencias Sociales" else "",
                                  competencia="Culturalidad" if materia == "Ciencias Sociales" else "",
                                  dba="DBA 3", clave="A", variante=tema.split()[-1])
        g = c.post("/api/cargar", files=[("archivos", (nombre, datos))], data={"solo_revisar": "false"}).json()[0]
        assert g["estado"] == "aceptado", g["errores"]
    r = c.put(f"/api/cartillas/{d['id']}/secciones", json={"secciones": [
        {"titulo": "SOCIALES Y CIUDADANAS", "materia": "Ciencias Sociales",
         "materias": ["Ciencias Sociales", "Filosofía"], "submateria": None,
         "cantidad": 2, "dificultad": "lib"}]})
    assert r.status_code == 200, r.json()
    sec = r.json()["secciones"][0]
    assert sec["mezclada"] is True
    assert set(sec["admitidas"]) == {"Ciencias Sociales|Ciencias Económicas y Políticas",
                                     "Ciencias Sociales|", "Filosofía|"}
    materias = {x["materia"] for x in c.get(f"/api/cartillas/{d['id']}/candidatos",
                                            params={"seccion": sec["id"]}).json()["items"]}
    assert "Filosofía" in materias and "Ciencias Sociales" in materias, materias


def test_adelantar_una_pregunta_conserva_la_cartilla_entera(c):
    """El camino que de verdad mueve: se aplica el orden nuevo y la cartilla tiene que quedar intacta.

    Cambia la numeración, y nada más: las mismas preguntas, en la misma sección y sin huecos.
    """
    from app.armado import reordenar

    version = len(c.get("/api/cartillas").json()) + 1
    d = c.post("/api/cartillas", json={**DATOS, "version": version}).json()
    sec = next(s for s in d["secciones"] if s["titulo"] == "MATEMÁTICAS I")      # preguntas sueltas
    cuerpo = [{"id": s["id"], "titulo": s["titulo"], "materia": s["materia"], "submateria": s["submateria"],
               "cantidad": 3 if s["id"] == sec["id"] else 0, "dificultad": "lib"} for s in d["secciones"]]
    c.put(f"/api/cartillas/{d['id']}/secciones", json={"secciones": cuerpo})
    c.post(f"/api/cartillas/{d['id']}/secciones/{sec['id']}/automatica", json={})

    antes = posiciones_guardadas(d["id"], sec["id"])
    assert len(antes) >= 2, "la prueba necesita varias preguntas sueltas"

    # se le da la vuelta al orden, como haría un adelanto, y se aplica igual que hace maqueta.optimizar
    from sqlalchemy import select

    from app.bd import Ejercicio, Sesion

    codigos = [cod for _pos, cod, _b, _o in antes]
    with Sesion() as s:
        ids = {e.codigo: e.id for e in s.scalars(select(Ejercicio).where(Ejercicio.codigo.in_(codigos)))}
    reordenar(d["id"], sec["id"], [ids[cod] for cod in reversed(codigos)])

    despues = posiciones_guardadas(d["id"], sec["id"])
    assert len(despues) == len(antes), "se perdió o se duplicó alguna pregunta"
    assert {cod for _p, cod, *_ in despues} == set(codigos), "cambiaron las preguntas"
    assert [p for p, *_ in despues] == list(range(1, len(despues) + 1)), "la numeración quedó con huecos"
    assert [cod for _p, cod, *_ in despues] == list(reversed(codigos)), "no se aplicó el orden pedido"


def test_no_se_puede_dar_la_vuelta_a_un_bloque(c):
    """Las preguntas de una lectura se apoyan en el mismo texto: barajarlas la deja sin sentido."""
    import pytest as _pytest

    from app.armado import ErrorArmado, reordenar

    version = len(c.get("/api/cartillas").json()) + 1
    d = c.post("/api/cartillas", json={**DATOS, "version": version}).json()
    sec = next(s for s in d["secciones"] if s["titulo"] == "COMPRENSIÓN LECTORA")
    cuerpo = [{"id": s["id"], "titulo": s["titulo"], "materia": s["materia"], "submateria": s["submateria"],
               "cantidad": 2 if s["id"] == sec["id"] else 0, "dificultad": "lib"} for s in d["secciones"]]
    c.put(f"/api/cartillas/{d['id']}/secciones", json={"secciones": cuerpo})
    c.post(f"/api/cartillas/{d['id']}/secciones/{sec['id']}/automatica", json={})

    filas = posiciones_guardadas(d["id"], sec["id"])
    assert any(bid for _p, _c, bid, _o in filas), "la prueba necesita un bloque"
    from sqlalchemy import select

    from app.bd import Ejercicio, Sesion

    codigos = [cod for _pos, cod, _b, _o in filas]
    with Sesion() as s:
        ids = {e.codigo: e.id for e in s.scalars(select(Ejercicio).where(Ejercicio.codigo.in_(codigos)))}
    with _pytest.raises(ErrorArmado, match="orden"):
        reordenar(d["id"], sec["id"], [ids[cod] for cod in reversed(codigos)])


def test_el_prompt_trae_la_ficha_tecnica_que_exige_el_validador(c):
    """La auditoría del 07/11/2026 encontró que el prompt callaba lo que más rechazos produce.

    Decía «una sola fuente» cuando el validador exige Tahoma, «un solo tamaño» cuando exige 9 pt y 8 pt
    en tablas, y no nombraba los límites de tabla ni los requisitos de las imágenes.
    """
    import re

    from app.validador.validador import (FUENTE, MARGEN_CM, MAX_ANCHO_CM, MAX_COLUMNAS_TABLA,
                                         PPP_MINIMO, TAM_CHICO, TAM_TEXTO)

    t = re.sub(r"\s+", " ", c.get("/api/prompt").json()["texto"])
    assert "ficha técnica del archivo" in t
    assert FUENTE in t, "el prompt no nombra la fuente que exige el validador"
    for valor in (f"{TAM_TEXTO} pt", f"{TAM_CHICO} pt", f"{MAX_COLUMNAS_TABLA} columnas", f"{PPP_MINIMO} ppp"):
        assert valor in t, f"el prompt no dice «{valor}»"
    assert f"{MARGEN_CM:g}".replace(".", ",") + " cm" in t
    assert f"{MAX_ANCHO_CM:g}".replace(".", ",") + " cm" in t
    assert "letra y el punto en negrita" in t          # la regla 5 que nadie adivina
    assert "Una sola" in t and "dos columnas" in t     # el archivo de carga va a una columna
    assert "no puede quedar nada" in t                 # nada entre las tablas de control ni después


def test_el_prompt_explica_completar_el_texto(c):
    """Las partes de Inglés tipo «cloze» tienen dos reglas propias que el validador exige."""
    import re

    t = re.sub(r"\s+", " ", c.get("/api/prompt").json()["texto"])
    assert "(#1), (#2)" in t and "van sin enunciado" in t
    assert "DBA 3, DBA 5" in t                         # varios DBA, con el formato que acepta el validador
