"""Banco de ejercicios: carga, búsqueda, vista previa y eliminación (Fase 2)."""
import base64
import hashlib
import io
import html
import json
import re

from lxml import etree
from sqlalchemy import func, or_, select

from app import analisis, glosario, mathml
from app.bd import (Archivo, Bloque, CargaPendiente, Cartilla, CartillaArchivo, CartillaItem, Consecutivo,
                    Ejercicio, Materia, Sesion, Submateria,
                    ValorRegistrado)
from app.semilla import catalogo_validacion
from app.validador import analizar
from app.validador.docx_lector import NS, W, Parrafo, Tabla
from app.validador.validador import alineacion_impresa, letra_opcion

CAMPOS_REGISTRADOS = {"Temática": "tematica", "Competencia": "competencia", "Pensamiento": "pensamiento"}


# ====================================================================== utilidades
def xml_de(items):
    """Serializa una lista de párrafos/tablas del Word original, sin alterarlos."""
    cont = etree.Element(W + "body", nsmap={"w": NS["w"]})
    for it in items:
        cont.append(etree.fromstring(etree.tostring(it.el)))
    return etree.tostring(cont, encoding="unicode")


def texto_de(items):
    partes = []
    for it in items:
        if isinstance(it, Parrafo):
            partes.append(it.texto)
        else:
            partes += [p.texto for fila in it.filas for celda in fila for p in celda if isinstance(p, Parrafo)]
    return re.sub(r"\s+", " ", " ".join(partes)).strip()


def huella_de(unidad):
    base = [texto_de(unidad.recurso)]
    for pr in unidad.preguntas:
        base.append(texto_de(pr.enunciado))
        base += [texto_de([o]) for o in pr.opciones]
    return hashlib.sha256("\n".join(base).lower().encode("utf-8")).hexdigest()


def tiene(items, tipo):
    for it in items:
        if tipo == "imagen" and isinstance(it, Parrafo) and it.dibujos:
            return True
        if tipo == "tabla" and isinstance(it, Tabla):
            return True
        if tipo == "imagen" and isinstance(it, Tabla) and any(p.dibujos for f in it.filas for c in f for p in c if isinstance(p, Parrafo)):
            return True
    return False


def prefijo(s, materia, submateria):
    if submateria:
        sub = s.scalar(select(Submateria).join(Materia).where(Materia.nombre == materia, Submateria.nombre == submateria))
        if sub:
            return sub.prefijo
    m = s.scalar(select(Materia).where(Materia.nombre == materia))
    return m.prefijo or "GEN"


def siguiente_codigo(s, pre, grado, tipo):
    c = s.get(Consecutivo, (pre, grado, tipo))
    if c is None:
        c = Consecutivo(prefijo=pre, grado=grado, tipo=tipo, ultimo=0)
        s.add(c)
    c.ultimo += 1
    return f"{pre}-{grado}-B{c.ultimo:05d}" if tipo == "B" else f"{pre}-{grado}-{c.ultimo:06d}"


# ====================================================================== carga
def cargar(datos, nombre, decisiones=None, solo_revisar=False, pendiente_id=None):
    """Valida un archivo y, si cumple, lo guarda en el banco. Devuelve el resultado como dict."""
    v = analizar(datos, nombre, catalogo_validacion())
    r = v.r
    if r.errores:
        return r.a_dict()
    huella = huella_de(v.unidad)
    with Sesion() as s:
        previo = s.scalar(select(Archivo).where(Archivo.huella == huella))
        if previo:
            codigos = s.scalars(select(Ejercicio.codigo).where(Ejercicio.archivo_id == previo.id)).all()
            if codigos:
                r.error(28, "Archivo", f"Este contenido ya está en el banco ({', '.join(codigos)}), subido el {previo.subido_en:%d/%m/%Y} como «{previo.nombre}». Para corregirlo, elimina el anterior y vuelve a subirlo.")
                return r.a_dict()

    # decisiones sobre valores parecidos: «misma» adopta el registrado, «nueva» lo deja como viene
    decisiones = decisiones or {}
    quedan = []
    for sim in r.similitudes:
        d = decisiones.get(f"{sim.campo}|{sim.valor}")
        if d == "misma":
            campo = CAMPOS_REGISTRADOS[sim.campo]
            for fila in r.filas:
                if fila[campo] == sim.valor:
                    fila[campo] = sim.parecido_a
        elif d != "nueva":
            quedan.append(sim)
    r.similitudes = quedan

    if solo_revisar:
        return r.a_dict()
    if r.similitudes:
        with Sesion() as s:
            if pendiente_id is None:
                p = CargaPendiente(nombre=nombre, datos=datos)
                s.add(p)
                s.commit()
                pendiente_id = p.id
        r.pendiente_id = pendiente_id
        return r.a_dict()

    r.guardado = guardar(v, datos, nombre, huella)
    if pendiente_id is not None:
        with Sesion() as s:
            p = s.get(CargaPendiente, pendiente_id)
            if p:
                s.delete(p)
                s.commit()
    return r.a_dict()


def guardar(v, datos, nombre, huella):
    u, r = v.unidad, v.r
    with Sesion() as s:
        arch = Archivo(nombre=nombre, datos=datos, huella=huella)
        s.add(arch)
        s.flush()
        primera = r.filas[0]
        pre = prefijo(s, primera["materia"], primera["submateria"])
        bloque = None
        if u.tipo in ("bloque", "parte"):
            bloque = Bloque(codigo=siguiente_codigo(s, pre, primera["grado"], "B"), tipo=u.tipo, tipo_recurso=u.tipo_recurso,
                            titulo_parte=u.titulo_parte, xml_cabecera=xml_de([u.cabecera]),
                            xml_instruccion=xml_de([u.instruccion]) if u.instruccion is not None else None,
                            xml_recurso=xml_de(u.recurso + ([u.credito] if u.credito is not None else [])),
                            permite_recorte=u.tipo == "bloque", archivo_id=arch.id)
            s.add(bloque)
            s.flush()
        codigos = []
        for k, (pr, fila) in enumerate(zip(u.preguntas, r.filas), 1):
            ops = {letra_opcion(o): o for o in pr.opciones}
            e = Ejercicio(
                codigo=siguiente_codigo(s, prefijo(s, fila["materia"], fila["submateria"]), fila["grado"], "E"),
                grado=fila["grado"], materia=fila["materia"], submateria=fila["submateria"], pensamiento=fila["pensamiento"],
                competencia=fila["competencia"], dba=fila["dba"], tematica=fila["tematica"], nivel=fila["nivel"],
                clave_original=r.claves[k - 1], justificacion=r.justificaciones[k - 1],
                bloque_id=bloque.id if bloque else None, orden_en_bloque=k,
                tiene_imagen=tiene(pr.enunciado + pr.opciones + u.recurso, "imagen"),
                tiene_tabla=tiene(pr.enunciado + u.recurso, "tabla"),
                texto=texto_de(u.recurso + pr.enunciado + pr.opciones),
                xml_enunciado=xml_de(pr.enunciado), xml_opcion_a=xml_de([ops["A"]]), xml_opcion_b=xml_de([ops["B"]]),
                xml_opcion_c=xml_de([ops["C"]]), xml_opcion_d=xml_de([ops["D"]]),
                glosario=json.dumps(r.glosarios[k - 1] if k - 1 < len(r.glosarios) else [], ensure_ascii=False),
                archivo_id=arch.id)
            s.add(e)
            codigos.append(e.codigo)
            for campo, atributo in CAMPOS_REGISTRADOS.items():
                valor = fila[atributo]
                if valor and not s.scalar(select(ValorRegistrado).where(ValorRegistrado.campo == campo, ValorRegistrado.valor == valor)):
                    s.add(ValorRegistrado(campo=campo, valor=valor))
                    s.flush()
        s.commit()
        return {"codigos": codigos, "bloque": bloque.codigo if bloque else None}


def revisar(datos, nombre):
    """Revisa un archivo y, si cumple, lo deja en espera para que la persona decida si lo guarda."""
    r = cargar(datos, nombre, solo_revisar=True)
    if r["errores"]:
        return r
    with Sesion() as s:
        p = CargaPendiente(nombre=nombre, datos=datos)
        s.add(p)
        s.commit()
        r["pendiente_id"] = p.id
    return r


def guardar_pendientes(ids, decisiones=None):
    """Guarda en el banco los archivos en espera indicados. Devuelve el resultado de cada uno."""
    salida = []
    for pid in ids:
        r = resolver_pendiente(pid, (decisiones or {}).get(str(pid)) or {})
        if r is not None:
            salida.append(r)
    return salida


def descartar_pendiente(pid):
    with Sesion() as s:
        p = s.get(CargaPendiente, pid)
        if p is None:
            return None
        s.delete(p)
        s.commit()
        return {"descartado": p.nombre}


def resolver_pendiente(pid, decisiones):
    with Sesion() as s:
        p = s.get(CargaPendiente, pid)
        if p is None:
            return None
        datos, nombre = p.datos, p.nombre
    return cargar(datos, nombre, decisiones, pendiente_id=pid)


# ====================================================================== búsqueda
def opciones_filtro(grado=None):
    with Sesion() as s:
        q = select(Ejercicio)
        if grado:
            q = q.where(Ejercicio.grado == grado)
        sub = q.subquery()
        col = lambda c: sorted(x for x in s.scalars(select(getattr(sub.c, c)).distinct()) if x)
        return {"tematicas": col("tematica"), "materias": col("materia"), "submaterias": col("submateria"),
                "competencias": col("competencia"), "pensamientos": col("pensamiento")}


def buscar(f):
    with Sesion() as s:
        q = select(Ejercicio, Bloque).outerjoin(Bloque, Ejercicio.bloque_id == Bloque.id)
        for campo in ("grado", "tematica", "materia", "submateria", "nivel", "competencia", "pensamiento"):
            if f.get(campo):
                q = q.where(getattr(Ejercicio, campo) == f[campo])
        if f.get("dba"):
            q = q.where(Ejercicio.dba.contains(f["dba"]))
        if f.get("tipo") == "suelto":
            q = q.where(Ejercicio.bloque_id.is_(None))
        elif f.get("tipo") in ("bloque", "parte"):
            q = q.where(Bloque.tipo == f["tipo"])
        if f.get("recurso") == "imagen":
            q = q.where(Ejercicio.tiene_imagen.is_(True))
        elif f.get("recurso") == "tabla":
            q = q.where(Ejercicio.tiene_tabla.is_(True))
        if f.get("max_usos") not in (None, ""):
            q = q.where(Ejercicio.veces_usado <= int(f["max_usos"]))
        if f.get("texto"):
            for palabra in f["texto"].split():
                q = q.where(or_(Ejercicio.texto.ilike(f"%{palabra}%"), Ejercicio.codigo.ilike(f"%{palabra}%")))
        total = s.scalar(select(func.count()).select_from(q.subquery()))
        filas = s.execute(q.order_by(Ejercicio.id.desc()).limit(200)).all()
        return {"total": total, "items": [{
            "id": e.id, "codigo": e.codigo, "grado": e.grado, "materia": e.materia, "submateria": e.submateria,
            "tematica": e.tematica, "nivel": e.nivel, "competencia": e.competencia, "veces_usado": e.veces_usado,
            "bloque": b.codigo if b else None, "tipo": b.tipo if b else "suelto", "orden": e.orden_en_bloque,
            "imagen": e.tiene_imagen, "tabla": e.tiene_tabla, "glosario": len(glosario.terminos(e)),
            "texto": e.texto[:180], "creado": f"{e.creado_en:%d/%m/%Y}",
        } for e, b in filas]}


def resumen():
    with Sesion() as s:
        filas = s.execute(select(Ejercicio.grado, Ejercicio.materia, func.count()).group_by(Ejercicio.grado, Ejercicio.materia)).all()
        total = s.scalar(select(func.count(Ejercicio.id))) or 0
        bloques = s.scalar(select(func.count(Bloque.id))) or 0
        pendientes = s.scalar(select(func.count(CargaPendiente.id))) or 0
    return {"total": total, "bloques": bloques, "pendientes": pendientes,
            "por_grado_materia": [{"grado": g, "materia": m, "n": n} for g, m, n in filas]}


# ====================================================================== vista previa
def _run_html(fragmentos):
    out = []
    for f in fragmentos:
        if getattr(f, "omml", None) is not None:
            # la ecuación se dibuja de verdad y en su sitio, no como texto pegado al final
            out.append(mathml.a_mathml(f.omml))
            continue
        t = html.escape(f.texto).replace("\t", "&emsp;").replace("\n", "<br>")
        if f.fmt.vert == "superscript":
            t = f"<sup>{t}</sup>"
        elif f.fmt.vert == "subscript":
            t = f"<sub>{t}</sub>"
        if f.fmt.negrita:
            t = f"<b>{t}</b>"
        if f.fmt.cursiva:
            t = f"<i>{t}</i>"
        out.append(t)
    return "".join(out)


def miniatura(datos, ancho_px):
    """Imagen pequeña para la pantalla: el Word lleva la original; aquí basta con que se vea."""
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(datos))
        im.load()
        if im.width > 460:
            im = im.resize((460, max(1, round(im.height * 460 / im.width))), Image.LANCZOS)
        if im.mode not in ("L", "RGB"):
            im = im.convert("L" if im.mode in ("1", "LA", "I;16", "I") else "RGB")
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=70, optimize=True)
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return "data:image/png;base64," + base64.b64encode(datos).decode()


def _parrafo_html(p, doc, clase="", celda=False):
    cuerpo = _run_html(p.fragmentos)
    for d in p.dibujos:
        blip = d.find(".//a:blip", NS)
        ext = d.find(".//wp:extent", NS)
        if blip is None:
            continue
        datos, _ = doc.media(blip.get("{%s}embed" % NS["r"]))
        if datos:
            ancho = int(int(ext.get("cx", 0)) / 9525) if ext is not None else 300
            cuerpo += f'<img src="{miniatura(datos, ancho)}" style="width:{ancho}px;max-width:100%" alt="Imagen del ejercicio" loading="lazy">'
    # como sale impreso: fuera de las tablas, la alineación de la cartilla (3.5B); en las celdas, la del archivo
    alin = {"center": "center", "right": "right", "both": "justify"}.get(p.alineacion if celda else alineacion_impresa(p), "left")
    return f'<p class="{clase}" style="text-align:{alin}">{cuerpo or "&nbsp;"}</p>'


def _items_html(items, doc):
    out = []
    for it in items:
        if isinstance(it, Parrafo):
            out.append(_parrafo_html(it, doc))
        else:
            filas = "".join("<tr>" + "".join("<td>" + "".join(_parrafo_html(p, doc, celda=True) for p in c if isinstance(p, Parrafo)) + "</td>" for c in f) + "</tr>" for f in it.filas)
            out.append(f'<table class="tabla-ej">{filas}</table>')
    return "".join(out)


def detalle(eid):
    with Sesion() as s:
        e = s.get(Ejercicio, eid)
        if e is None:
            return None
        arch = s.get(Archivo, e.archivo_id)
        hermanos = s.scalars(select(Ejercicio).where(Ejercicio.archivo_id == e.archivo_id).order_by(Ejercicio.orden_en_bloque)).all()
        bloque = s.get(Bloque, e.bloque_id) if e.bloque_id else None
        datos, nombre = arch.datos, arch.nombre
    v = analisis.leer(e.archivo_id, datos, nombre)
    u, doc = v.unidad, v.doc
    partes = []
    if u.cabecera is not None:
        partes.append(_parrafo_html(u.cabecera, doc, "cabecera"))
    if u.instruccion is not None:
        partes.append(_parrafo_html(u.instruccion, doc, "instruccion"))
    if u.recurso:
        partes.append(f'<div class="recurso">{_items_html(u.recurso, doc)}{_parrafo_html(u.credito, doc) if u.credito is not None else ""}</div>')
    for k, (pr, ej) in enumerate(zip(u.preguntas, hermanos), 1):
        ops = "".join(
            _parrafo_html(o, doc, "opcion correcta" if letra_opcion(o) == ej.clave_original else "opcion") for o in pr.opciones)
        partes.append(f'<div class="pregunta{" actual" if ej.id == eid else ""}"><div class="num">{ej.codigo}</div>'
                      f'{_items_html(pr.enunciado, doc)}{ops}{glosario.a_html(glosario.terminos(ej))}</div>')
    return {
        "id": e.id, "codigo": e.codigo, "bloque": bloque.codigo if bloque else None, "tipo": bloque.tipo if bloque else "suelto",
        "grado": e.grado, "materia": e.materia, "submateria": e.submateria, "pensamiento": e.pensamiento,
        "competencia": e.competencia, "dba": e.dba, "tematica": e.tematica, "nivel": e.nivel, "clave": e.clave_original,
        "justificacion": e.justificacion, "veces_usado": e.veces_usado, "archivo": nombre, "creado": f"{e.creado_en:%d/%m/%Y %H:%M}",
        "hermanos": len(hermanos), "glosario": glosario.terminos(e), "html": "".join(partes),
    }


def eliminar(eid):
    """Elimina el ejercicio; si pertenece a un bloque o parte, elimina la unidad completa.

    Si alguna cartilla lo estaba usando, también se le quita de ahí y se renumeran sus preguntas: dejar
    la referencia colgando rompía la cartilla entera al generarla. Las cartillas ya generadas pierden sus
    archivos, porque el Word guardado deja de corresponder a lo que tienen.
    """
    with Sesion() as s:
        e = s.get(Ejercicio, eid)
        if e is None:
            return None
        grupo = s.scalars(select(Ejercicio).where(Ejercicio.archivo_id == e.archivo_id)).all()
        codigos = [x.codigo for x in grupo]
        usos = sum(x.veces_usado for x in grupo)
        tocadas = _sacar_de_las_cartillas(s, [x.id for x in grupo])
        for x in grupo:
            s.delete(x)
        if e.bloque_id:
            s.delete(s.get(Bloque, e.bloque_id))
        arch = s.get(Archivo, e.archivo_id)
        datos_arch = arch.datos
        s.flush()
        s.delete(arch)
        s.commit()
        analisis.olvidar(datos_arch)
    return {"eliminados": codigos, "usos": usos, "cartillas": tocadas}


def _sacar_de_las_cartillas(s, ids):
    """Quita esas preguntas de las cartillas que las usen y deja las posiciones seguidas otra vez."""
    items = list(s.scalars(select(CartillaItem).where(CartillaItem.ejercicio_id.in_(ids))))
    if not items:
        return []
    afectadas, tocadas = {i.cartilla_id for i in items}, []
    for it in items:
        s.delete(it)
    s.flush()
    for cid in sorted(afectadas):
        c = s.get(Cartilla, cid)
        if c is None:
            continue
        tocadas.append({"codigo": c.codigo, "nombre": c.nombre, "estado": c.estado})
        for sec in c.secciones:
            quedan = sorted([i for i in c.items if i.seccion_id == sec.id], key=lambda x: x.posicion)
            for n, i in enumerate(quedan, 1):
                i.posicion = n
        if c.estado == "generada":
            for a in s.scalars(select(CartillaArchivo).where(CartillaArchivo.cartilla_id == c.id)):
                s.delete(a)
    return tocadas


def usos_de(eid):
    with Sesion() as s:
        e = s.get(Ejercicio, eid)
        if e is None:
            return None
        grupo = s.scalars(select(Ejercicio).where(Ejercicio.archivo_id == e.archivo_id)).all()
        return {"codigos": [x.codigo for x in grupo], "usos": sum(x.veces_usado for x in grupo)}
