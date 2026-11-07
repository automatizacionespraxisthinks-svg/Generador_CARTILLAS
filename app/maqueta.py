"""Aprovechamiento del espacio de la cartilla (Estándar 3.8).

Cada pregunta se imprime entera: si no cabe en lo que queda de columna, salta completa y deja un hueco.
Con las preguntas altas (las que llevan imagen o tabla) esos huecos suman páginas enteras.

La solución es **reordenar**: cuando queda un hueco al final de una columna, se adelanta una pregunta
posterior **de la misma sección** que quepa en él. Nunca se cambia de sección, nunca se parte un bloque y
nunca se quita ni se agrega una pregunta: solo cambia el orden, y con él la numeración y el Excel.

Para no equivocarse, las alturas no se estiman: se miden con Microsoft Word.

1. **Documento de medición**: la misma anchura de columna, pero páginas muy altas y un salto de columna
   antes de cada pregunta. Así cada una empieza arriba de su columna y entra completa, y su altura es la
   distancia hasta el salto siguiente.
2. **Documento real**: dice en qué columna quedó cada pregunta y a qué altura empieza.
3. Con las dos cosas se sabe cuánto le sobra a cada columna y a quién se puede adelantar.
4. Se vuelve a armar y a medir: si no mejoró, se deja el orden que ya estaba.

Sin Word (o si Word falla) no se cambia nada: la cartilla se genera como siempre.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import io

from docx import Document

from app import generador
from app.armado import ErrorArmado, reordenar

RAIZ = Path(__file__).resolve().parent.parent
ESPERA = 900                    # segundos; medir una cartilla entera en Word tarda cerca de un minuto

MARGEN = 10                     # puntos que se dejan libres al meter una pregunta en un hueco (≈ 3,5 mm)
HUECO_MINIMO = 40               # desde 1,4 cm de hueco vale la pena intentar rellenarlo
RONDAS = 3                      # veces que se vuelve a medir y a repartir


# ====================================================================== medición con Word
def _medir_con_word(ruta, nombres):
    """Se ejecuta en el proceso aparte: página, columna y altura de cada marcador.

    Se mide el **comienzo** del marcador (un rango vacío): el final de un párrafo con salto de columna
    ya está en la columna siguiente, y daría una medida equivocada.
    """
    import pythoncom
    import win32com.client

    PAGINA, HORIZ, VERT = 3, 5, 6          # wdActiveEndPageNumber, wdHorizontal…, wdVerticalPositionRelativeToPage
    pythoncom.CoInitialize()
    word = doc = None
    try:
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0
        doc = word.Documents.Open(str(ruta), ReadOnly=True, AddToRecentFiles=False, OpenAndRepair=False,
                                  ConfirmConversions=False)
        doc.Repaginate()
        medidas = {}
        for nombre in nombres:
            if not doc.Bookmarks.Exists(nombre):
                continue
            inicio = doc.Bookmarks(nombre).Range.Start
            r = doc.Range(inicio, inicio)
            medidas[nombre] = [int(r.Information(PAGINA)), round(float(r.Information(HORIZ)), 1),
                               round(float(r.Information(VERT)), 1)]
        return {"paginas": int(doc.ComputeStatistics(2)), "medidas": medidas}
    finally:
        if doc is not None:
            doc.Close(False)
        if word is not None:
            word.Quit()
        pythoncom.CoUninitialize()


def medir(datos: bytes, nombres):
    """{paginas, medidas: {marcador: [página, x, y]}} o None si Word no pudo medirlo."""
    if os.environ.get("PRAXIS_SIN_WORD") == "1":
        return None
    with tempfile.TemporaryDirectory() as carpeta:
        ruta, pedido, salida = (Path(carpeta) / n for n in ("medir.docx", "pedido.json", "medida.json"))
        ruta.write_bytes(datos)
        pedido.write_text(json.dumps(list(nombres)), encoding="utf-8")
        try:
            r = subprocess.run([sys.executable, "-m", "app.maqueta", str(ruta), str(pedido), str(salida)],
                               capture_output=True, text=True, timeout=ESPERA, cwd=str(RAIZ))
        except (subprocess.TimeoutExpired, OSError):
            return None
        if r.returncode != 0 or not salida.exists():
            return None
        try:
            return json.loads(salida.read_text(encoding="utf-8"))
        except ValueError:
            return None


# ====================================================================== alturas y huecos
def alturas(cid, orden=None):
    """Altura en puntos de cada pieza (título de sección o pregunta), medida con Word.

    Devuelve (piezas, {clave: alto}); el alto es None si Word no pudo medir.
    """
    piezas = []
    datos = generador.construir(cid, orden, piezas, medicion=True)
    if datos is None:
        return [], None
    m = medir(datos, [p["marca"] for p in piezas] + [p["cierre"] for p in piezas])
    if m is None:
        return piezas, None
    pos, altos = m["medidas"], {}
    for pieza in piezas:
        ini, fin = pos.get(pieza["marca"]), pos.get(pieza["cierre"])
        if ini and fin and ini[0] == fin[0] and ini[1] == fin[1] and fin[2] > ini[2]:
            altos[pieza["clave"]] = round(fin[2] - ini[2], 1)
    return piezas, altos


def geometria(datos):
    """(tope, fondo) de la columna en puntos: dónde empieza y dónde termina el texto de la página."""
    doc = Document(io.BytesIO(datos))
    sect = list(doc.element.body.iter(generador.W + "sectPr"))[-1]
    sz, mar = sect.find(generador.W + "pgSz"), sect.find(generador.W + "pgMar")
    alto = int(sz.get(generador.W + "h")) / 20
    arriba = int(mar.get(generador.W + "top")) / 20
    abajo = int(mar.get(generador.W + "bottom")) / 20
    return arriba, alto - abajo


def columnas(piezas, altos, medida, fondo):
    """Las columnas del documento real: qué piezas lleva cada una, dónde termina y cuánto le sobra."""
    pos = medida["medidas"]
    sitios = [(p, pos.get(p["marca"])) for p in piezas]
    xs = sorted({s[1] for _, s in sitios if s})
    corte = (xs[0] + xs[-1]) / 2 if len(xs) > 1 else float("inf")
    cols, actual = [], None
    for pieza, s in sitios:
        if s is None:
            continue
        clave_col = (s[0], 0 if s[1] < corte else 1)
        if actual is None or actual["columna"] != clave_col:
            actual = {"columna": clave_col, "piezas": [], "fin": s[2]}
            cols.append(actual)
        actual["piezas"].append(pieza["clave"])
        actual["fin"] = min(fondo, s[2] + altos.get(pieza["clave"], 0))
    for c in cols:
        c["hueco"] = round(max(0.0, fondo - c["fin"]), 1)
    return cols


def desperdicio(cols):
    """Espacio que se pierde al final de las columnas, en puntos.

    **La última columna no cuenta.** Lo que sobra detrás de la última pregunta no es desperdicio: no hay
    nada después que se pueda adelantar hasta ahí. Contarlo inflaba la cifra —en una cartilla de 140
    preguntas eran 459 de los 460 puntos «perdidos»— y hacía creer que había mucho que ganar.
    """
    return round(sum(max(0.0, c["hueco"]) for c in cols[:-1]), 1)


def orden_por_seccion(piezas, orden):
    """{id de sección: [id de ejercicio, …]} tal como lo esperan el generador y armado.reordenar()."""
    por_clave = {p["clave"]: p for p in piezas}
    out = {}
    for clave in orden:
        p = por_clave[clave]
        if p["tipo"] == "pregunta":
            out.setdefault(p["seccion"], []).extend(p["ejercicios"])
    return out


def _medida_real(cid, piezas, orden):
    """Arma la cartilla con ese orden y mide dónde quedó cada pregunta."""
    marcadas = []
    datos = generador.construir(cid, orden_por_seccion(piezas, orden), marcadas)
    return datos, medir(datos, [p["marca"] for p in marcadas])


# ====================================================================== proceso completo
def _aplicar(orden, movimientos):
    """Adelanta cada pregunta al sitio que le corresponde. Los movimientos van en orden de documento."""
    nuevo = list(orden)
    for m in movimientos:
        if m["clave"] not in nuevo or m["tras"] not in nuevo:
            continue
        nuevo.remove(m["clave"])
        nuevo.insert(nuevo.index(m["tras"]) + 1, m["clave"])
    return nuevo


def proponer(piezas, altos, cols, orden):
    """Qué preguntas se podrían adelantar, mirando los huecos reales de arriba abajo."""
    por_clave = {p["clave"]: p for p in piezas}
    propuestas, tomadas = [], set()
    for col in cols:
        if col["hueco"] < HUECO_MINIMO or not col["piezas"]:
            continue
        ultima = col["piezas"][-1]
        if ultima not in orden or por_clave[ultima].get("bloque"):
            continue        # la columna termina dentro de un bloque: meter algo ahí lo partiría en dos
        seccion, libre = por_clave[ultima]["seccion"], col["hueco"] - MARGEN
        for clave in orden[orden.index(ultima) + 1:]:
            p = por_clave[clave]
            # solo preguntas sueltas de la misma sección: ni títulos ni preguntas que van dentro de un bloque
            if p["tipo"] != "pregunta" or p["seccion"] != seccion or p.get("bloque") or clave in tomadas:
                continue
            alto = altos.get(clave)
            if alto is None or alto > libre:
                continue
            propuestas.append({"clave": clave, "tras": ultima, "codigo": p["codigo"],
                               "alto": alto, "hueco": col["hueco"]})
            tomadas.add(clave)
            break
    return propuestas


def optimizar(cid, rondas=RONDAS, guardar=True, aviso=None):
    """Reordena las preguntas para que no sobre espacio al final de las columnas.

    Cada tanda de movimientos se **comprueba con Word**: si el resultado no es mejor, se prueba con la
    mitad de los movimientos, y así hasta uno. Nunca se cambia nada de sección, no se parten bloques y
    no se quita ni se agrega ninguna pregunta: solo cambia el orden, y con él la numeración y el Excel.
    """
    def paso(texto):
        if aviso:
            aviso(texto)

    paso("Midiendo la altura de cada pregunta…")
    piezas, altos = alturas(cid)
    if not altos:
        return {"ok": False, "motivo": "Word no pudo medir la cartilla: el orden queda como estaba."}
    sin_medir = [p["codigo"] for p in piezas if p["tipo"] == "pregunta" and p["clave"] not in altos]

    orden = [p["clave"] for p in piezas]
    paso("Mirando cómo queda la cartilla hoy…")
    datos, medida = _medida_real(cid, piezas, orden)
    if medida is None:
        return {"ok": False, "motivo": "Word no pudo medir la cartilla: el orden queda como estaba."}
    _, fondo = geometria(datos)
    cols = columnas(piezas, altos, medida, fondo)
    antes = {"paginas": medida["paginas"], "perdido": desperdicio(cols), "columnas": len(cols)}

    mejor = {"orden": list(orden), "paginas": antes["paginas"], "perdido": antes["perdido"], "movidas": []}
    historia = [dict(antes, ronda=0, probados=0)]
    for ronda in range(1, rondas + 1):
        propuestas = proponer(piezas, altos, cols, mejor["orden"])
        if not propuestas:
            break
        aceptada, cuantas = None, len(propuestas)
        while cuantas >= 1 and aceptada is None:
            paso(f"Probando {cuantas} cambio{'s' if cuantas > 1 else ''} de posición…")
            candidato = _aplicar(mejor["orden"], propuestas[:cuantas])
            _, m = _medida_real(cid, piezas, candidato)
            if m is None:
                break
            c = columnas(piezas, altos, m, fondo)
            perdido = desperdicio(c)
            historia.append({"ronda": ronda, "probados": cuantas, "paginas": m["paginas"],
                             "perdido": perdido, "columnas": len(c)})
            if (m["paginas"], perdido) < (mejor["paginas"], mejor["perdido"]):
                aceptada = {"orden": candidato, "paginas": m["paginas"], "perdido": perdido,
                            "movidas": mejor["movidas"] + propuestas[:cuantas], "cols": c}
            else:
                cuantas //= 2
        if aceptada is None:
            break
        cols = aceptada.pop("cols")
        mejor = aceptada

    mejoro = (mejor["paginas"], mejor["perdido"]) < (antes["paginas"], antes["perdido"])
    informe = {"ok": True, "mejoro": mejoro, "antes": antes, "guardado": False, "historia": historia,
               "despues": {"paginas": mejor["paginas"], "perdido": mejor["perdido"]},
               "movidas": [{k: m[k] for k in ("codigo", "alto", "hueco")} for m in mejor["movidas"]],
               "sin_medir": sin_medir}
    if mejoro and guardar:
        for seccion, ejercicios in orden_por_seccion(piezas, mejor["orden"]).items():
            try:
                reordenar(cid, seccion, ejercicios)
            except ErrorArmado as e:
                informe["ok"], informe["motivo"] = False, str(e)
                return informe
        informe["guardado"] = True
    return informe


if __name__ == "__main__":
    ruta, pedido, salida = sys.argv[1], sys.argv[2], sys.argv[3]
    medidas = _medir_con_word(ruta, json.loads(Path(pedido).read_text(encoding="utf-8")))
    Path(salida).write_text(json.dumps(medidas, ensure_ascii=False), encoding="utf-8")
