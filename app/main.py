"""Servidor del Generador de cartillas PRAXIS – THINKS."""
import base64
import os
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import quote

from fastapi import Body, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app import armado, banco, cuadernillo, estadisticas, generador, maqueta, prompt
from app.bd import (Agrupacion, Archivo, CargaPendiente, Ejercicio, Estructura, ExcepcionSuperindice, FraseProhibida, Grado,
                    Materia, Plantilla, Sesion, TipoMaterial)
from app.config import PLANTILLAS, WEB
from app.semilla import catalogo_validacion, poblar
from app.validador import validar
from app.validador.resultado import Resultado

MAX_BYTES = 25 * 1024 * 1024

FORMATOS = [
    ("Plantillas en blanco", "Ejercicio suelto", "PLANTILLA_CARGA_1_EJERCICIO_v1.2.docx", "Una pregunta con sus cuatro opciones, las dos tablas de control y la tabla de glosario opcional."),
    ("Plantillas en blanco", "Bloque de lectura", "PLANTILLA_CARGA_2_BLOQUE_LECTURA_v1.2.docx", "Una lectura o recurso con dos o más preguntas; glosario opcional por pregunta."),
    ("Plantillas en blanco", "Parte de Inglés", "PLANTILLA_CARGA_3_PARTE_INGLES_v1.2.docx", "Una parte completa, con subtítulo e instrucción; glosario opcional."),
    ("Plantillas en blanco", "Claves de respuestas (Excel)", "PLANTILLA_CLAVES_RESPUESTAS_v1.2.xlsx", "La hoja de claves que lee el OMR: una fila por pregunta, con las mismas columnas que genera el sistema. Trae dos filas de ejemplo y una hoja que explica cada columna."),
    ("Ejemplos llenos", "Ejercicio suelto", "ejemplos/EJEMPLO_1_EJERCICIO_SUELTO.docx", "Matemáticas I, 7°, con una tabla dentro del enunciado y glosario."),
    ("Ejemplos llenos", "Bloque de lectura", "ejemplos/EJEMPLO_2_BLOQUE_LECTURA.docx", "Comprensión Lectora, 7°, tres preguntas, línea de crédito y glosario en dos preguntas."),
    ("Ejemplos llenos", "Parte de Inglés", "ejemplos/EJEMPLO_3_PARTE_INGLES_COMPLETAR_TEXTO.docx", "Completar el texto, con los marcadores (#1) a (#5)."),
    ("Ejemplos llenos", "Matemáticas con fórmulas", "ejemplos/EJEMPLO_4_MATEMATICAS_CON_FORMULAS.docx", "Matemáticas I, 6°, tres preguntas: fracciones apiladas, raíces, potencias y números mixtos escritos con el editor de ecuaciones, dentro del enunciado, de las opciones, de una tabla y del glosario."),
    ("Guía", "Instructivo de normalización", "INSTRUCTIVO_NORMALIZACION_v1.2.docx", "Todas las reglas (alineación, glosario, tablas) y la lista de chequeo antes de subir."),
    ("Guía", "Códigos del sistema (Excel)", "CODIGOS_PRAXIS.xlsx", "Los cinco pares del código de la cartilla, los catálogos de grado, materia y tipo, las 5 plantillas de respuestas y los prefijos de los códigos de ejercicio."),
]


@asynccontextmanager
async def ciclo(_):
    poblar()
    yield


app = FastAPI(title="Generador de cartillas PRAXIS – THINKS", lifespan=ciclo)
app.mount("/static", StaticFiles(directory=WEB), name="static")


@app.get("/")
def inicio():
    return FileResponse(WEB / "index.html")


@app.post("/api/validar")
async def api_validar(archivos: list[UploadFile] = File(...)):
    catalogo = catalogo_validacion()
    salida = []
    for a in archivos:
        nombre = a.filename or "archivo"
        datos = await a.read(MAX_BYTES + 1)
        if not nombre.lower().endswith(".docx"):
            r = Resultado(archivo=nombre)
            r.error(0, "Archivo", "Solo se aceptan archivos de Word .docx. Si está en .doc, ábrelo en Word y guárdalo como .docx.")
        elif len(datos) > MAX_BYTES:
            r = Resultado(archivo=nombre)
            r.error(0, "Archivo", "El archivo pesa más de 25 MB. Revisa que las imágenes no sean más grandes de lo necesario.")
        else:
            r = validar(datos, nombre, catalogo)
        salida.append(r.a_dict())
    return salida


def _rechazo(nombre, mensaje):
    r = Resultado(archivo=nombre)
    r.error(0, "Archivo", mensaje)
    return r.a_dict()


@app.post("/api/cargar")
async def api_cargar(archivos: list[UploadFile] = File(...), solo_revisar: bool = Form(False)):
    """Valida cada archivo y guarda en el banco los que cumplen (salvo que se pida solo revisar)."""
    salida = []
    for a in archivos:
        nombre = a.filename or "archivo"
        datos = await a.read(MAX_BYTES + 1)
        if not nombre.lower().endswith(".docx"):
            salida.append(_rechazo(nombre, "Solo se aceptan archivos de Word .docx. Si está en .doc, ábrelo en Word y guárdalo como .docx."))
        elif len(datos) > MAX_BYTES:
            salida.append(_rechazo(nombre, "El archivo pesa más de 25 MB. Revisa que las imágenes no sean más grandes de lo necesario."))
        else:
            salida.append(banco.cargar(datos, nombre, solo_revisar=solo_revisar))
    return salida


@app.post("/api/revisar")
async def api_revisar(archivos: list[UploadFile] = File(...)):
    """Revisa los archivos y deja en espera los que cumplen; se guardan al pulsar «Guardar»."""
    salida = []
    for a in archivos:
        nombre = a.filename or "archivo"
        datos = await a.read(MAX_BYTES + 1)
        if not nombre.lower().endswith(".docx"):
            salida.append(_rechazo(nombre, "Solo se aceptan archivos de Word .docx. Si está en .doc, ábrelo en Word y guárdalo como .docx."))
        elif len(datos) > MAX_BYTES:
            salida.append(_rechazo(nombre, "El archivo pesa más de 25 MB. Revisa que las imágenes no sean más grandes de lo necesario."))
        else:
            salida.append(banco.revisar(datos, nombre))
    return salida


@app.post("/api/pendientes/guardar")
def api_guardar_pendientes(cuerpo: dict = Body(...)):
    """Guarda en el banco los archivos en espera que se marcaron."""
    ids = [int(x) for x in (cuerpo.get("ids") or [])]
    return banco.guardar_pendientes(ids, cuerpo.get("decisiones") or {})


@app.get("/salud")
def salud():
    """Para el healthcheck del contenedor: responde sin tocar la base ni pedir clave."""
    return {"ok": True}


# Clave de acceso para el servidor. En el equipo local no se define y todo sigue igual.
_USUARIO = os.environ.get("PRAXIS_USUARIO", "")
_CLAVE = os.environ.get("PRAXIS_CLAVE", "")


@app.middleware("http")
async def con_clave(request, call_next):
    """Si PRAXIS_USUARIO y PRAXIS_CLAVE están definidas, pide usuario y clave (HTTP Basic) en todo menos /salud."""
    if not (_USUARIO and _CLAVE) or request.url.path == "/salud":
        return await call_next(request)
    cabecera = request.headers.get("authorization", "")
    if cabecera.lower().startswith("basic "):
        try:
            usuario, _, clave = base64.b64decode(cabecera[6:]).decode("utf-8").partition(":")
        except (ValueError, UnicodeDecodeError):
            usuario = clave = ""
        if secrets.compare_digest(usuario.encode(), _USUARIO.encode()) and secrets.compare_digest(clave.encode(), _CLAVE.encode()):
            return await call_next(request)
    return Response("Se necesita usuario y clave.", status_code=401,
                    headers={"WWW-Authenticate": 'Basic realm="Generador PRAXIS", charset="UTF-8"'})


@app.middleware("http")
async def sin_cache(request, call_next):
    """La pantalla se actualiza con el sistema: el navegador revisa siempre si hay versión nueva."""
    respuesta = await call_next(request)
    if request.url.path == "/" or request.url.path.startswith("/static"):
        respuesta.headers["Cache-Control"] = "no-cache, must-revalidate"
    return respuesta


@app.get("/api/prompt")
def api_prompt():
    """Texto para pedirle a una inteligencia artificial que pase un simulacro al formato de carga."""
    return {"texto": prompt.texto()}


@app.get("/api/estadisticas")
def api_estadisticas():
    return {"banco": estadisticas.resumen_banco(), "cobertura": estadisticas.cobertura()}


@app.get("/api/pendientes")
def api_pendientes():
    with Sesion() as s:
        return [{"id": p.id, "nombre": p.nombre, "creado": f"{p.creado_en:%d/%m/%Y %H:%M}"}
                for p in s.scalars(select(CargaPendiente).order_by(CargaPendiente.id))]


@app.post("/api/pendientes/{pid}")
def api_resolver(pid: int, cuerpo: dict = Body(default={})):
    r = banco.resolver_pendiente(pid, cuerpo.get("decisiones") or {})
    if r is None:
        raise HTTPException(404, "Carga pendiente no encontrada")
    return r


@app.delete("/api/pendientes/{pid}")
def api_descartar(pid: int):
    return banco.descartar_pendiente(pid) or {"ok": True}


@app.get("/api/banco")
def api_banco(request: Request):
    return banco.buscar(dict(request.query_params))


@app.get("/api/banco/opciones")
def api_banco_opciones(grado: str | None = None):
    return banco.opciones_filtro(grado)


@app.get("/api/banco/resumen")
def api_banco_resumen():
    return banco.resumen()


@app.get("/api/banco/{eid}")
def api_banco_detalle(eid: int):
    d = banco.detalle(eid)
    if d is None:
        raise HTTPException(404, "Ejercicio no encontrado")
    return d


@app.get("/api/banco/{eid}/original")
def api_banco_original(eid: int):
    with Sesion() as s:
        e = s.get(Ejercicio, eid)
        if e is None:
            raise HTTPException(404, "Ejercicio no encontrado")
        a = s.get(Archivo, e.archivo_id)
        return Response(a.datos, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(a.nombre)}"})


@app.post("/api/banco/eliminar")
def api_banco_eliminar_varios(cuerpo: dict = Body(...)):
    """Elimina en lote: los ejercicios marcados, o todos los que coincidan con los filtros de la pantalla.

    Con `solo_ver` no borra: devuelve lo que se iría, para poder avisarlo antes de preguntar.
    """
    return banco.eliminar_varios(cuerpo.get("ids"), cuerpo.get("filtro"), solo_ver=bool(cuerpo.get("solo_ver")))


@app.delete("/api/banco/{eid}")
def api_banco_eliminar(eid: int):
    r = banco.eliminar(eid)
    if r is None:
        raise HTTPException(404, "Ejercicio no encontrado")
    return r


@app.get("/api/banco/{eid}/usos")
def api_banco_usos(eid: int):
    r = banco.usos_de(eid)
    if r is None:
        raise HTTPException(404, "Ejercicio no encontrado")
    return r


# ====================================================================== cartillas (fase 3)
def _armado(fn, *a, **kw):
    try:
        return fn(*a, **kw)
    except armado.ErrorArmado as e:
        raise HTTPException(400, str(e))


@app.get("/api/cartillas/opciones")
def api_cartillas_opciones():
    return armado.opciones_para_crear()


@app.get("/api/cartillas")
def api_cartillas():
    return armado.listar()


@app.post("/api/cartillas")
def api_cartilla_crear(datos: dict = Body(...)):
    cid = _armado(armado.crear, datos)
    return armado.detalle(cid)


@app.get("/api/cartillas/{cid}")
def api_cartilla(cid: int):
    d = armado.detalle(cid)
    if d is None:
        raise HTTPException(404, "Cartilla no encontrada")
    return d


@app.delete("/api/cartillas/{cid}")
def api_cartilla_eliminar(cid: int):
    r = _armado(armado.eliminar, cid)
    if r is None:
        raise HTTPException(404, "Cartilla no encontrada")
    return r


@app.put("/api/cartillas/{cid}/glosario")
def api_cartilla_glosario(cid: int, cuerpo: dict = Body(...)):
    if armado.cambiar_glosario(cid, bool(cuerpo.get("incluir"))) is None:
        raise HTTPException(404, "Cartilla no encontrada")
    return armado.detalle(cid)


@app.put("/api/cartillas/{cid}/secciones")
def api_cartilla_secciones(cid: int, cuerpo: dict = Body(...)):
    return _armado(armado.actualizar_secciones, cid, cuerpo["secciones"])


@app.get("/api/cartillas/{cid}/candidatos")
def api_cartilla_candidatos(cid: int, seccion: int, request: Request):
    return _armado(armado.candidatos, cid, seccion, dict(request.query_params))


@app.post("/api/cartillas/{cid}/items")
def api_cartilla_agregar(cid: int, cuerpo: dict = Body(...)):
    codigos = _armado(armado.agregar, cid, int(cuerpo["seccion"]), int(cuerpo["ejercicio"]), bool(cuerpo.get("permitir_exceso")))
    return {"agregados": codigos, "cartilla": armado.detalle(cid)}


@app.delete("/api/cartillas/{cid}/items/{eid}")
def api_cartilla_quitar(cid: int, eid: int):
    codigos = _armado(armado.quitar, cid, eid)
    return {"quitados": codigos, "cartilla": armado.detalle(cid)}


@app.post("/api/cartillas/{cid}/secciones/{sid}/automatica")
def api_cartilla_automatica(cid: int, sid: int, cuerpo: dict = Body(default={})):
    r = _armado(armado.automatica, cid, sid, cuerpo.get("cuotas"))
    r["cartilla"] = armado.detalle(cid)
    return r


@app.post("/api/cartillas/{cid}/secciones/{sid}/orden")
def api_cartilla_orden(cid: int, sid: int, cuerpo: dict = Body(...)):
    return _armado(armado.reordenar, cid, sid, [int(x) for x in cuerpo["orden"]])


@app.get("/api/cartillas/{cid}/verificar")
def api_cartilla_verificar(cid: int):
    r = armado.verificar(cid)
    if r is None:
        raise HTTPException(404, "Cartilla no encontrada")
    return r


@app.get("/api/cartillas/{cid}/vista-previa")
def api_cartilla_vista_previa(cid: int):
    r = armado.vista_previa(cid)
    if r is None:
        raise HTTPException(404, "Cartilla no encontrada")
    return r


@app.post("/api/cartillas/{cid}/generar")
def api_cartilla_generar(cid: int, cuerpo: dict = Body(default={})):
    try:
        r = generador.generar(cid, (cuerpo or {}).get("nombre"))
    except generador.ErrorGeneracion as e:
        raise HTTPException(400, str(e))
    if r is None:
        raise HTTPException(404, "Cartilla no encontrada")
    return r


@app.put("/api/cartillas/{cid}/portada")
def api_cartilla_portada(cid: int, datos: dict):
    """Tipo de portada y título impreso."""
    return _armado(armado.cambiar_portada, cid, datos.get("portada"), datos.get("titulo"))


@app.post("/api/cartillas/{cid}/imagen")
async def api_cartilla_imagen(cid: int, archivo: UploadFile = File(...)):
    """Sube la ilustración de la portada de esa cartilla."""
    datos = await archivo.read()
    return _armado(armado.cambiar_imagen, cid, datos, archivo.filename, archivo.content_type)


@app.delete("/api/cartillas/{cid}/imagen")
def api_cartilla_imagen_quitar(cid: int):
    """Vuelve a la ilustración que trae la plantilla."""
    return _armado(armado.cambiar_imagen, cid, None, None, None)


@app.get("/api/cartillas/{cid}/imagen")
def api_cartilla_imagen_ver(cid: int):
    datos, nombre = armado.imagen_de(cid)
    if not datos:
        raise HTTPException(404, "Esta cartilla no tiene ilustración propia")
    tipo = "image/png" if (nombre or "").lower().endswith(".png") else "image/jpeg"
    return Response(content=datos, media_type=tipo)


@app.get("/api/cartillas/{cid}/buscar")
def api_cartilla_buscar(cid: int, texto: str = ""):
    """En qué sección de esta cartilla está cada tema que se busca."""
    r = armado.buscar_en_cartilla(cid, texto)
    if r is None:
        raise HTTPException(404, "Cartilla no encontrada")
    return r


@app.post("/api/cartillas/{cid}/maquetacion")
def api_cartilla_maquetacion(cid: int):
    """Reordena las preguntas para que no sobre espacio al final de las columnas (3.8)."""
    try:
        r = maqueta.optimizar(cid)
    except armado.ErrorArmado as e:
        raise HTTPException(400, str(e))
    if r is None:
        raise HTTPException(404, "Cartilla no encontrada")
    return {**r, "cartilla": armado.detalle(cid)}


@app.post("/api/cartillas/{cid}/paginas")
def api_cartilla_paginas(cid: int):
    try:
        r = generador.contar_paginas(cid)
    except generador.ErrorGeneracion as e:
        raise HTTPException(400, str(e))
    if r is None:
        raise HTTPException(404, "Cartilla no encontrada")
    return {**r, "cartilla": armado.detalle(cid)}


@app.post("/api/cuadernillo")
def api_cuadernillo_previo(cuerpo: dict = Body(...)):
    """Qué llevaría el cuadernillo de varias sesiones, sin armarlo."""
    try:
        return cuadernillo.previo([int(x) for x in cuerpo.get("cartillas") or []])
    except (TypeError, ValueError):
        raise HTTPException(400, "La lista de cartillas no es válida.")
    except generador.ErrorGeneracion as e:
        raise HTTPException(400, str(e))


@app.post("/api/cuadernillo/generar")
def api_cuadernillo_generar(cuerpo: dict = Body(...)):
    """Arma el Word con todas las sesiones y lo devuelve para descargar. No cambia las cartillas."""
    try:
        r = cuadernillo.generar([int(x) for x in cuerpo.get("cartillas") or []], cuerpo.get("nombre"))
    except (TypeError, ValueError):
        raise HTTPException(400, "La lista de cartillas no es válida.")
    except generador.ErrorGeneracion as e:
        raise HTTPException(400, str(e))
    return Response(r["datos"], media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(r['nombre'])}",
                             # el conteo necesita Word: sin él van vacías, y 0 es un dato, no un vacío
                             "X-Praxis-Paginas": "" if r["paginas"] is None else str(r["paginas"]),
                             "X-Praxis-Faltan": "" if r["faltan_paginas"] is None else str(r["faltan_paginas"])})


@app.get("/api/cartillas/{cid}/archivos")
def api_cartilla_archivos(cid: int):
    return generador.archivos(cid)


@app.get("/api/cartillas/{cid}/archivo/{tipo}")
def api_cartilla_archivo(cid: int, tipo: str):
    if tipo not in ("docx", "xlsx"):
        raise HTTPException(404, "Tipo de archivo no válido")
    r = generador.archivo(cid, tipo)
    if r is None:
        raise HTTPException(404, "Todavía no se ha generado esta cartilla")
    nombre, datos = r
    medios = {"docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
              "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}
    return Response(datos, media_type=medios[tipo],
                    headers={"Content-Disposition": f"attachment; filename*=UTF-8\'\'{quote(nombre)}"})


@app.get("/api/copia-seguridad")
def api_copia():
    """Copia completa del banco en un solo archivo (base SQLite con los Word originales dentro)."""
    import sqlite3
    import tempfile
    from datetime import datetime
    from app.config import URL_BD
    if not URL_BD.startswith("sqlite:///"):
        raise HTTPException(400, "La copia desde la pantalla solo aplica a la base local.")
    origen = sqlite3.connect(URL_BD.removeprefix("sqlite:///"))
    with tempfile.TemporaryDirectory() as tmp:
        destino_ruta = f"{tmp}/copia.db"
        destino = sqlite3.connect(destino_ruta)
        origen.backup(destino)
        destino.close()
        origen.close()
        with open(destino_ruta, "rb") as f:
            datos = f.read()
    nombre = f"praxis_copia_{datetime.now():%Y-%m-%d_%H%M}.db"
    return Response(datos, media_type="application/octet-stream", headers={"Content-Disposition": f'attachment; filename="{nombre}"'})


@app.get("/api/formatos")
def api_formatos():
    return [{"grupo": g, "titulo": t, "archivo": f, "descripcion": d, "nombre": f.split("/")[-1]} for g, t, f, d in FORMATOS]


@app.get("/formatos/{ruta:path}")
def descargar_formato(ruta: str):
    permitidos = {f for _, _, f, _ in FORMATOS}
    if ruta not in permitidos:
        raise HTTPException(404, "Formato no encontrado")
    tipos = {".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
             ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}
    return FileResponse(PLANTILLAS / ruta, filename=ruta.split("/")[-1],
                        media_type=tipos.get(Path(ruta).suffix.lower(), "application/octet-stream"))


@app.get("/api/catalogos")
def api_catalogos():
    with Sesion() as s:
        materias = s.scalars(select(Materia).options(selectinload(Materia.submaterias)).order_by(Materia.id)).all()
        estructuras = s.scalars(select(Estructura).options(selectinload(Estructura.secciones)).order_by(Estructura.clave)).all()
        return {
            "grados": [{"nombre": g.nombre, "codigo": g.codigo, "portada": g.texto_portada} for g in armado.grados_ordenados(s)],
            "materias": [{"nombre": m.nombre, "codigo": m.codigo, "prefijo": m.prefijo, "color": m.color,
                          "submaterias": [{"nombre": x.nombre, "codigo": x.codigo, "prefijo": x.prefijo} for x in m.submaterias]}
                         for m in materias],
            "agrupaciones": [{"nombre": a.nombre, "codigo": a.codigo} for a in s.scalars(select(Agrupacion).order_by(Agrupacion.codigo.desc()))],
            "tipos": [{"nombre": t.nombre, "codigo": t.codigo} for t in s.scalars(select(TipoMaterial).order_by(TipoMaterial.id))],
            "plantillas": [{"numero": p.numero, "secuencia": p.secuencia} for p in s.scalars(select(Plantilla).order_by(Plantilla.numero))],
            "estructuras": [{"clave": e.clave, "nombre": e.nombre, "codigo_materia": e.codigo_materia, "editable": e.editable, "total": e.total,
                             "secciones": [{"titulo": x.titulo, "materia": x.materia, "submateria": x.submateria, "cantidad": x.cantidad,
                                            "mezclada": x.mezclada} for x in e.secciones]} for e in estructuras],
            "excepciones": [e.texto for e in s.scalars(select(ExcepcionSuperindice).order_by(ExcepcionSuperindice.texto))],
            "frases": [{"frase": f.frase, "mayusculas": f.distingue_mayusculas} for f in s.scalars(select(FraseProhibida))],
        }
