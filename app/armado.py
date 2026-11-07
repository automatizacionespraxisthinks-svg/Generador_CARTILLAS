"""Armado de cartillas (Fase 3): código, secciones, selección de ejercicios y vista previa.

Lo que el sistema decide solo es determinista y verificable a mano: el número de cada
pregunta por su posición, y la letra correcta leyendo la plantilla en esa posición.
"""
import io
import re
import unicodedata

from sqlalchemy import or_, select

from app import catalogos_base as base
from app import analisis, glosario, paginas
from app.bd import (Archivo, Bloque, Cartilla, CartillaArchivo, CartillaExcluida, CartillaItem, CartillaSeccion, Ejercicio,
                    Estructura, Grado, Materia, Plantilla, Sesion, TipoMaterial)
from app.semilla import catalogo_validacion
from app.validador import analizar
from app.validador.validador import letra_opcion

MEZCLAS = {
    "bm": ("Básica y media, mitad y mitad", {"Básico": 0.5, "Medio": 0.5}),
    "eq": ("Equilibrada, un tercio cada una", {"Básico": 1 / 3, "Medio": 1 / 3, "Avanzado": 1 / 3}),
    "b": ("Solo básica", {"Básico": 1.0}),
    "ma": ("Media y avanzada, mitad y mitad", {"Medio": 0.5, "Avanzado": 0.5}),
    "lib": ("Libre, sin repartir por nivel", {}),
}
TIEMPO_ICFES = "4 horas y 30 minutos"


class ErrorArmado(Exception):
    pass


# ====================================================================== utilidades
def tiempo_de(total, grado):
    if grado == base.GRADO_ICFES:
        return TIEMPO_ICFES
    minutos = total * 2
    h, m = divmod(minutos, 60)
    partes = ([f"{h} hora{'s' if h > 1 else ''}"] if h else []) + ([f"{m} minutos"] if m else [])
    return " y ".join(partes) or "0 minutos"


def cupos(cantidad, mezcla):
    """Reparte una cantidad entre niveles según la mezcla, sin perder ni inventar preguntas."""
    pesos = MEZCLAS.get(mezcla, MEZCLAS["lib"])[1]
    if not pesos:
        return {}
    cupo = {n: int(cantidad * p) for n, p in pesos.items()}
    for n in sorted(pesos, key=lambda x: ("Básico", "Medio", "Avanzado").index(x)):
        if sum(cupo.values()) >= cantidad:
            break
        cupo[n] += 1
    return cupo


def _combinaciones(sec):
    return [c for c in (sec.admitidas or "").split(";") if c]


def acepta(sec, e):
    """¿El ejercicio cabe en esta sección?"""
    if sec.mezclada:
        return f"{e.materia}|{e.submateria or ''}" in _combinaciones(sec)
    if e.materia != sec.materia:
        return False
    return (e.submateria or "") == (sec.submateria or "")


def _plantilla(s, numero):
    return s.get(Plantilla, numero).secuencia


def orden_items(c, sec, orden=None):
    """Los items de una sección en el orden en que se imprimen.

    orden: {id de sección: [id de ejercicio, …]} para probar otra maquetación sin tocar la base de datos.
    """
    items = [i for i in c.items if i.seccion_id == sec.id]
    propuesto = (orden or {}).get(sec.id)
    if propuesto and set(propuesto) == {i.ejercicio_id for i in items}:
        puesto = {eid: n for n, eid in enumerate(propuesto)}
        return sorted(items, key=lambda x: (puesto[x.ejercicio_id], x.ejercicio.orden_en_bloque))
    # si dos posiciones empataran, el bloque manda: sus preguntas se imprimen juntas y en su orden
    return sorted(items, key=lambda x: (x.posicion, x.ejercicio.bloque_id or 0, x.ejercicio.orden_en_bloque))


def posiciones(c, orden=None):
    """{id de ejercicio: número de la pregunta en la cartilla}, según el orden de secciones e items."""
    n, out = 1, {}
    for sec in sorted(c.secciones, key=lambda x: x.orden):
        for it in orden_items(c, sec, orden):
            out[it.ejercicio_id] = n
            n += 1
    return out


# ====================================================================== creación
def grados_ordenados(s):
    return sorted(s.scalars(select(Grado)), key=lambda g: base.orden_grado(g.codigo))


def seccion_admite_grado(materia, submateria, grado):
    """¿Una sección de esa materia y submateria puede llenarse con ejercicios de ese grado? (regla de submateria)"""
    regla = base.regla_submateria(materia, grado)
    if regla is False and submateria:
        return False
    if regla is True and not submateria:
        return False
    return True


def estructura_admite(e, grado):
    """ICFES solo con E5 y E6; en los demás grados, que cada sección fija se pueda llenar con ejercicios del grado
    (por eso E1 y E2, con Matemáticas I y Español, no sirven para 3° a 5°)."""
    if (grado == base.GRADO_ICFES) != (e.clave in ("E5", "E6")):
        return False
    return all(x.mezclada or seccion_admite_grado(x.materia, x.submateria, grado) for x in e.secciones)


def opciones_para_crear():
    from app.bd import Materia
    with Sesion() as s:
        estructuras = s.scalars(select(Estructura).order_by(Estructura.clave)).all()
        grados = grados_ordenados(s)
        return {
            "grados": [{"codigo": g.codigo, "nombre": g.nombre} for g in grados],
            "primaria": sorted(base.GRADOS_PRIMARIA),
            "tipos": [{"codigo": t.codigo, "nombre": t.nombre} for t in s.scalars(select(TipoMaterial).order_by(TipoMaterial.id))],
            "estructuras": [{"clave": e.clave, "nombre": e.nombre, "codigo_materia": e.codigo_materia,
                             "editable": e.editable, "total": sum(x.cantidad for x in e.secciones),
                             "grados": [g.codigo for g in grados if estructura_admite(e, g.codigo)]} for e in estructuras],
            "grupos": [{"nombre": n, "materias": ms} for n, ms in base.GRUPOS_MATERIA],
            "materias": [{"nombre": m.nombre, "submaterias": [x.nombre for x in m.submaterias],
                          "reglas": {g.codigo: base.regla_submateria(m.nombre, g.codigo) for g in grados}}
                         for m in s.scalars(select(Materia).order_by(Materia.id))],
            "mezclas": [{"clave": k, "nombre": v[0]} for k, v in MEZCLAS.items()],
            "agrupaciones": [{"codigo": c, "nombre": n} for n, c in base.AGRUPACIONES],
        }


def codigo_de(grado, materia, tipo, plantilla, version):
    return f"{grado}{materia}{tipo}{int(plantilla):02d}{version}"


def crear(d):
    """Crea el borrador de una cartilla con las secciones de su estructura."""
    with Sesion() as s:
        est = s.scalar(select(Estructura).where(Estructura.clave == d["estructura"]))
        if est is None:
            raise ErrorArmado("La estructura no existe.")
        grado = d["grado"]
        if not s.scalar(select(Grado).where(Grado.codigo == grado)):
            raise ErrorArmado("El grado no existe en el catálogo.")
        if not s.scalar(select(TipoMaterial).where(TipoMaterial.codigo == d["tipo_material"])):
            raise ErrorArmado("El tipo de material no existe en el catálogo.")
        cod_materia = d.get("codigo_materia") or est.codigo_materia
        if not cod_materia:
            raise ErrorArmado("Falta el código de materia: en la estructura libre se elige a mano.")
        if est.codigo_materia and cod_materia != est.codigo_materia and not (est.clave == "E3" and cod_materia == "93"):
            raise ErrorArmado(f"La estructura {est.clave} usa el código de materia {est.codigo_materia}.")
        es_icfes = grado == base.GRADO_ICFES
        if es_icfes != (est.clave in ("E5", "E6")):
            raise ErrorArmado("El simulacro ICFES usa las estructuras E5 y E6, y solo con el grado ICFES.")
        if not estructura_admite(est, grado):
            raise ErrorArmado(f"La estructura {est.clave} no sirve para ese grado: tiene secciones con submaterias que en "
                              "3°, 4° y 5° no se usan (Matemáticas y Lengua Castellana van sin submateria). "
                              "Usa la estructura libre (E4) o la PARTE 2 (E3).")
        if not (d.get("institucion") or "").strip() or not (d.get("nombre") or "").strip():
            raise ErrorArmado("La institución y el nombre descriptivo son obligatorios.")
        plantilla = int(d.get("plantilla") or 1)
        if not 1 <= plantilla <= 5:
            raise ErrorArmado("La plantilla de respuestas va de 1 a 5.")
        version = f"{int(d.get('version') or 1):02d}"
        codigo = codigo_de(grado, cod_materia, d["tipo_material"], plantilla, version)
        existe = s.scalar(select(Cartilla).where(Cartilla.codigo == codigo))
        if existe:
            libre = siguiente_version(s, grado, cod_materia, d["tipo_material"], plantilla)
            raise ErrorArmado(f"El código {codigo} ya existe (cartilla «{existe.nombre}»). La siguiente versión libre es {libre}.")

        total = sum(x.cantidad for x in est.secciones)
        c = Cartilla(codigo=codigo, institucion=d["institucion"].strip(), nombre=d["nombre"].strip(), grado=grado,
                     estructura=est.clave, codigo_materia=cod_materia, tipo_material=d["tipo_material"], plantilla=plantilla,
                     version=version, simulacro_n=int(d.get("simulacro_n") or 1),
                     tiempo=(d.get("tiempo") or "").strip() or tiempo_de(total, grado),
                     dificultad="lib" if es_icfes else d.get("dificultad", "bm"),
                     glosario=str(d.get("glosario", "")).lower() in ("1", "true", "on", "si", "sí"))
        for x in sorted(est.secciones, key=lambda y: y.orden):
            c.secciones.append(CartillaSeccion(orden=x.orden, titulo=x.titulo, materia=x.materia, submateria=x.submateria,
                                               cantidad=x.cantidad, mezclada=x.mezclada, admitidas=x.admitidas))
        s.add(c)
        s.flush()
        for otra in emparejadas(s, c):
            s.add(CartillaExcluida(cartilla_id=c.id, excluida_id=otra.id, automatica=True))
        s.commit()
        return c.id


def siguiente_version(s, grado, materia, tipo, plantilla):
    usadas = {x.version for x in s.scalars(select(Cartilla).where(
        Cartilla.grado == grado, Cartilla.codigo_materia == materia, Cartilla.tipo_material == tipo,
        Cartilla.plantilla == plantilla))}
    for n in range(1, 100):
        if f"{n:02d}" not in usadas:
            return f"{n:02d}"
    return "99"


def emparejadas(s, c):
    """La otra sesión del mismo simulacro: mismo grado, plantilla y versión, con el par de códigos correspondiente."""
    parejas_materia = {"91": ("92", "93", "94"), "92": ("91",), "93": ("91",), "94": ("91",)}
    otras = []
    if c.codigo_materia in parejas_materia:
        otras += list(s.scalars(select(Cartilla).where(
            Cartilla.grado == c.grado, Cartilla.tipo_material == c.tipo_material, Cartilla.plantilla == c.plantilla,
            Cartilla.version == c.version, Cartilla.codigo_materia.in_(parejas_materia[c.codigo_materia]), Cartilla.id != c.id)))
    pareja_tipo = {"71": "72", "72": "71"}.get(c.tipo_material)
    if pareja_tipo:
        otras += list(s.scalars(select(Cartilla).where(
            Cartilla.grado == c.grado, Cartilla.codigo_materia == c.codigo_materia, Cartilla.plantilla == c.plantilla,
            Cartilla.version == c.version, Cartilla.tipo_material == pareja_tipo, Cartilla.id != c.id)))
    return otras


# ====================================================================== lectura
def _ejercicios_excluidos(s, c):
    ids = [x.excluida_id for x in s.scalars(select(CartillaExcluida).where(CartillaExcluida.cartilla_id == c.id))]
    if not ids:
        return set()
    return set(s.scalars(select(CartillaItem.ejercicio_id).where(CartillaItem.cartilla_id.in_(ids))))


def detalle(cid):
    with Sesion() as s:
        c = s.get(Cartilla, cid)
        if c is None:
            return None
        num = posiciones(c)
        secuencia = _plantilla(s, c.plantilla)
        total = sum(x.cantidad for x in c.secciones)
        excluidas = s.scalars(select(Cartilla, CartillaExcluida).join(CartillaExcluida, CartillaExcluida.excluida_id == Cartilla.id)
                              .where(CartillaExcluida.cartilla_id == c.id)).all()
        secciones = []
        inicio = 1
        for sec in sorted(c.secciones, key=lambda x: x.orden):
            items = sorted([i for i in c.items if i.seccion_id == sec.id], key=lambda x: x.posicion)
            secciones.append({
                "id": sec.id, "orden": sec.orden, "titulo": sec.titulo, "materia": sec.materia,
                "submateria": sec.submateria or "", "cantidad": sec.cantidad, "mezclada": sec.mezclada,
                "admitidas": _combinaciones(sec), "dificultad": sec.dificultad,
                "rango": [inicio, inicio + sec.cantidad - 1] if sec.cantidad else [inicio, inicio],
                "elegidos": len(items),
                "items": [{
                    "ejercicio_id": i.ejercicio_id, "codigo": i.ejercicio.codigo, "numero": num[i.ejercicio_id],
                    "letra": secuencia[num[i.ejercicio_id] - 1], "clave_original": i.ejercicio.clave_original,
                    "materia": i.ejercicio.materia, "submateria": i.ejercicio.submateria, "tematica": i.ejercicio.tematica,
                    "nivel": i.ejercicio.nivel, "bloque_id": i.ejercicio.bloque_id, "veces_usado": i.ejercicio.veces_usado,
                    "glosario": len(glosario.terminos(i.ejercicio)), "texto": i.ejercicio.texto[:120],
                } for i in items],
            })
            inicio += sec.cantidad
        return {
            "id": c.id, "codigo": c.codigo, "institucion": c.institucion, "nombre": c.nombre, "grado": c.grado,
            "estructura": c.estructura, "codigo_materia": c.codigo_materia, "tipo_material": c.tipo_material,
            "plantilla": c.plantilla, "version": c.version, "simulacro_n": c.simulacro_n, "tiempo": c.tiempo,
            "dificultad": c.dificultad, "estado": c.estado, "total": total, "elegidos": len(c.items),
            "portada": c.portada, "titulo_portada": c.titulo_portada or "",
            "titulo_sugerido": generador_titulo(s, c), "imagen": bool(c.imagen), "imagen_nombre": c.imagen_nombre or "",
            "glosario": c.glosario, "con_glosario": sum(1 for i in c.items if glosario.terminos(i.ejercicio)),
            "paginas": c.paginas, "faltan_paginas": paginas.faltan_para_multiplo(c.paginas),
            "archivos": sorted(s.scalars(select(CartillaArchivo.tipo).where(CartillaArchivo.cartilla_id == c.id))),
            "secciones": secciones,
            "excluidas": [{"id": x.id, "codigo": x.codigo, "nombre": x.nombre} for x in excluidas],
            "verificacion": _verificar(s, c),
        }


def listar():
    with Sesion() as s:
        filas = s.scalars(select(Cartilla).order_by(Cartilla.id.desc())).all()
        return [{"id": c.id, "codigo": c.codigo, "nombre": c.nombre, "institucion": c.institucion, "grado": c.grado,
                 "estructura": c.estructura, "estado": c.estado, "total": sum(x.cantidad for x in c.secciones),
                 "elegidos": len(c.items), "creada": f"{c.creada_en:%d/%m/%Y}"} for c in filas]


def cambiar_glosario(cid, incluir):
    """Casilla «Incluir glosario»: decide si se imprime el glosario de las preguntas que lo tienen."""
    with Sesion() as s:
        c = s.get(Cartilla, cid)
        if c is None:
            return None
        if c.glosario != bool(incluir) and c.estado == "generada":
            # el Word guardado ya no corresponde: se retira para que nadie descargue la versión anterior
            for a in s.scalars(select(CartillaArchivo).where(CartillaArchivo.cartilla_id == c.id)):
                s.delete(a)
        c.glosario = bool(incluir)
        s.commit()
        return c.glosario


PORTADAS = {"completa": "Portada completa (página entera)",
            "media": "Media portada (el cuerpo arranca debajo)"}
IMAGEN_MAXIMA = 6 * 1024 * 1024          # 6 MB: de sobra para una ilustración de portada
IMAGEN_TIPOS = {"image/png": ".png", "image/jpeg": ".jpg", "image/jpg": ".jpg", "image/webp": ".webp"}


def generador_titulo(s, c):
    """El título que pondría el sistema si la cartilla no trae uno propio."""
    from app.generador import titulo_de_portada
    return titulo_de_portada(s, c)


def cambiar_portada(cid, portada=None, titulo=None):
    """Tipo de portada y título impreso. Si cambia y la cartilla ya se generó, su Word deja de servir."""
    with Sesion() as s:
        c = s.get(Cartilla, cid)
        if c is None:
            return None
        if portada is not None and portada not in PORTADAS:
            raise ErrorArmado("Esa portada no existe: elige portada completa o media portada.")
        nuevo_titulo = (titulo or "").strip() or None
        if (portada is not None and portada != c.portada) or nuevo_titulo != c.titulo_portada:
            _invalidar_generada(s, c)
        if portada is not None:
            c.portada = portada
        if titulo is not None:
            c.titulo_portada = nuevo_titulo
        s.commit()
    return detalle(cid)


def cambiar_imagen(cid, datos, nombre, tipo):
    """Guarda la ilustración de la portada de esa cartilla. Sin datos, vuelve a la de la plantilla."""
    with Sesion() as s:
        c = s.get(Cartilla, cid)
        if c is None:
            return None
        if datos:
            if tipo not in IMAGEN_TIPOS:
                raise ErrorArmado("La imagen debe ser PNG, JPG o WEBP.")
            if len(datos) > IMAGEN_MAXIMA:
                raise ErrorArmado(f"La imagen pesa {len(datos) // 1024} KB y el máximo son {IMAGEN_MAXIMA // 1024} KB.")
            try:
                from PIL import Image
                Image.open(io.BytesIO(datos)).verify()
            except Exception:
                raise ErrorArmado("Ese archivo no es una imagen que se pueda leer.")
        _invalidar_generada(s, c)
        c.imagen, c.imagen_nombre = (datos or None), (nombre if datos else None)
        s.commit()
    return detalle(cid)


def _invalidar_generada(s, c):
    """El Word guardado ya no corresponde a lo que se ve en pantalla: se retira para no descargarlo."""
    if c.estado == "generada":
        for a in s.scalars(select(CartillaArchivo).where(CartillaArchivo.cartilla_id == c.id)):
            s.delete(a)


def imagen_de(cid):
    with Sesion() as s:
        c = s.get(Cartilla, cid)
        return (c.imagen, c.imagen_nombre) if c is not None and c.imagen else (None, None)


# ====================================================================== secciones
def actualizar_secciones(cid, cambios):
    """Ajusta cantidades, orden y dificultad. En E4 y en la PARTE 2 ampliada se pueden agregar o quitar secciones."""
    with Sesion() as s:
        c = s.get(Cartilla, cid)
        if c is None or c.estado != "borrador":
            raise ErrorArmado("La cartilla no existe o ya fue generada.")
        por_id = {x.id: x for x in c.secciones}
        vistos = set()
        total = 0                  # se suma aquí: las secciones nuevas aún no están en c.secciones
        for i, d in enumerate(cambios, 1):
            sec = por_id.get(d.get("id"))
            if sec is None:
                _validar_seccion_nueva(s, c, d)
                grupo = [x for x in (d.get("materias") or []) if x]
                todas = (d.get("submateria") or None) == TODAS
                if grupo:
                    admitidas = combinaciones_de_grupo(s, grupo, c.grado)
                else:
                    materia = s.scalar(select(Materia).where(Materia.nombre == d["materia"]))
                    admitidas = combinaciones_de_materia(s, materia, c.grado) if todas else []
                sec = CartillaSeccion(cartilla_id=c.id, orden=i, titulo=d["titulo"].strip().upper(),
                                      materia=(grupo[0] if grupo else d["materia"]),
                                      submateria=None if (todas or grupo) else (d.get("submateria") or None),
                                      cantidad=0, mezclada=bool(admitidas),
                                      admitidas=";".join(admitidas) or None)
                s.add(sec)
                s.flush()
            sec.orden = i
            sec.titulo = (d.get("titulo") or sec.titulo).strip().upper()
            sec.dificultad = d.get("dificultad", sec.dificultad)
            nueva = int(d["cantidad"])
            elegidos = len([x for x in c.items if x.seccion_id == sec.id])
            if nueva < elegidos:
                raise ErrorArmado(f"La sección {sec.titulo} ya tiene {elegidos} ejercicios elegidos: quítalos antes de bajar la cantidad a {nueva}.")
            sec.cantidad = nueva
            total += nueva
            vistos.add(sec.id)
        for sec in list(c.secciones):
            if sec.id not in vistos:
                if any(x.seccion_id == sec.id for x in c.items):
                    raise ErrorArmado(f"La sección {sec.titulo} tiene ejercicios elegidos: quítalos antes de eliminarla.")
                s.delete(sec)
        if c.grado != base.GRADO_ICFES:
            c.tiempo = tiempo_de(total, c.grado)
        s.commit()
    return detalle(cid)


TODAS = "*"          # en la submateria de una sección nueva: «todas las de esta materia»


def combinaciones_de_grupo(s, nombres, grado):
    """«Materia|Submateria» de varias materias juntas: una prueba general de Sociales con Filosofía."""
    from app.bd import Materia
    out = []
    for nombre in nombres:
        m = s.scalar(select(Materia).where(Materia.nombre == nombre))
        if m is not None:
            out += combinaciones_de_materia(s, m, grado)
    return out


def combinaciones_de_materia(s, materia, grado):
    """«Materia|Submateria» que admite una sección que toma **toda** la materia.

    Es lo que hace falta para una prueba general de Matemáticas: una sola sección que acepte Matemáticas I
    y Matemáticas II. Se arma con las submaterias del catálogo, y se agrega la materia sin submateria
    cuando el grado permite que vaya vacía.
    """
    from app.bd import Submateria
    subs = [x.nombre for x in s.scalars(select(Submateria).where(Submateria.materia_id == materia.id)
                                        .order_by(Submateria.id))]
    regla = base.regla_submateria(materia.nombre, grado)
    combinaciones = [f"{materia.nombre}|{x}" for x in subs] if regla is not False else []
    if regla is not True:
        combinaciones.append(f"{materia.nombre}|")
    return combinaciones


def _validar_seccion_nueva(s, c, d):
    """Sección agregada a mano (estructura libre o PARTE 2 con materia agregada): materia y submateria del
    catálogo, y la submateria como la exige el grado, para que la sección se pueda llenar."""
    from app.bd import Materia, Submateria
    est = s.scalar(select(Estructura).where(Estructura.clave == c.estructura))
    if not ((est is not None and est.editable) or c.codigo_materia == "93"):
        raise ErrorArmado(f"La estructura {c.estructura} tiene secciones fijas: no se pueden agregar secciones.")
    titulo = (d.get("titulo") or "").strip()
    if not titulo:
        raise ErrorArmado("La sección nueva necesita un título (es el que se imprime en la cartilla).")
    grupo = [x for x in (d.get("materias") or []) if x]
    if grupo:
        faltan = [x for x in grupo if not s.scalar(select(Materia).where(Materia.nombre == x))]
        if faltan:
            raise ErrorArmado(f"Estas materias no existen en el catálogo: {', '.join(faltan)}.")
        if len(combinaciones_de_grupo(s, grupo, c.grado)) < 2:
            raise ErrorArmado("Ese grupo de materias no aporta nada en este grado: elige la sección normal.")
        return
    materia = s.scalar(select(Materia).where(Materia.nombre == d.get("materia")))
    if materia is None:
        raise ErrorArmado(f"La materia «{d.get('materia')}» no existe en el catálogo.")
    sub = d.get("submateria") or None
    if sub == TODAS:
        if len(combinaciones_de_materia(s, materia, c.grado)) < 2:
            raise ErrorArmado(f"{materia.nombre} no tiene varias submaterias en este grado: elige la sección normal.")
        return
    if sub and not s.scalar(select(Submateria).where(Submateria.materia_id == materia.id, Submateria.nombre == sub)):
        raise ErrorArmado(f"La submateria «{sub}» no pertenece a {materia.nombre}.")
    regla = base.regla_submateria(materia.nombre, c.grado)
    if regla is False and sub:
        raise ErrorArmado(f"En este grado {materia.nombre} va sin submateria: quita «{sub}».")
    if regla is True and not sub:
        raise ErrorArmado(f"En este grado {materia.nombre} necesita submateria: elige una.")


# ====================================================================== selección
def _varios(filtros, campo):
    """Un filtro puede venir repetido o separado por «;» (varias temáticas, varios niveles…)."""
    valor = filtros.get(campo)
    if isinstance(valor, (list, tuple, set)):
        lista = list(valor)
    else:
        lista = str(valor or "").split(";")
    return [x.strip() for x in lista if x and x.strip()]


def sin_tildes(t):
    """Para buscar: «fotosintesis» tiene que encontrar «Fotosíntesis»."""
    return unicodedata.normalize("NFD", (t or "").lower()).encode("ascii", "ignore").decode()


ENLACES = {"y", "o", "de", "del", "la", "el", "las", "los", "un", "una", "unos", "unas",
           "en", "al", "con", "para", "por", "sobre", "que", "se", "su", "sus", "lo"}


def _variantes(palabra):
    """La palabra y su singular: quien escribe «fracciones» o «células» busca «fracción» y «célula»."""
    formas = {palabra}
    if palabra.endswith("es") and len(palabra) > 4:
        formas.add(palabra[:-2])
    if palabra.endswith("s") and len(palabra) > 3:
        formas.add(palabra[:-1])
    return formas


def temas_buscados(texto):
    """Lo escrito en el buscador, partido en temas: «fracciones, senos y cosenos» son dos búsquedas.

    Dentro de un tema tienen que estar todas sus palabras; basta con que coincida **uno** de los temas.
    Así un docente escribe de corrido lo que está viendo en clase y lo encuentra todo de una vez.
    Las palabras de enlace («de», «y», «la») no se exigen: no dicen nada del tema.
    """
    temas = []
    for trozo in re.split(r"[,;]|\s+/\s+|\s+\+\s+", texto or ""):
        palabras = sin_tildes(trozo).split()
        utiles = [p for p in palabras if p not in ENLACES and len(p) > 1] or palabras
        if utiles:
            temas.append(utiles)
    return temas


def coincide(ficha, temas):
    """¿El ejercicio responde a alguno de los temas buscados?"""
    if not temas:
        return True
    donde = sin_tildes(f"{ficha['tematica']} {ficha['codigo']} {ficha['texto']}")
    return any(all(any(v in donde for v in _variantes(p)) for p in palabras) for palabras in temas)


def _cuenta(lista, clave, elegidos=None, alfabetico=False):
    """Cuántas preguntas hay de cada valor y, si se pasa, cuántas ya están elegidas en la sección.

    Un valor que ya se usó del todo sigue apareciendo (con 0 disponibles), para que la lista de temáticas
    sea siempre la misma y se vea qué se eligió de cada una.
    """
    cuentas = {}
    for e in lista:
        cuentas[clave(e)] = cuentas.get(clave(e), 0) + 1
    for v in (elegidos or {}):
        cuentas.setdefault(v, 0)
    orden = (lambda x: x[0].lower()) if alfabetico else (lambda x: (-x[1], x[0].lower()))
    return [{"valor": v, "n": n, "elegidos": (elegidos or {}).get(v, 0)}
            for v, n in sorted(cuentas.items(), key=orden) if v]


def candidatos(cid, seccion_id, filtros):
    """Ejercicios que caben en la sección, con filtros combinables y el conteo de cada valor.

    Los conteos (temáticas, niveles, competencias…) se calculan sobre todo lo que cabe en la sección, no sobre
    el resultado filtrado: así se ve de una cuántas preguntas hay de cada temática antes de elegir.
    """
    with Sesion() as s:
        c = s.get(Cartilla, cid)
        sec = s.get(CartillaSeccion, seccion_id)
        if c is None or sec is None or sec.cartilla_id != c.id:
            raise ErrorArmado("La sección no existe en esta cartilla.")
        usados = {i.ejercicio_id for i in c.items}
        excluidos = _ejercicios_excluidos(s, c)
        q = select(Ejercicio).where(Ejercicio.grado == c.grado)
        if sec.mezclada:
            pares = [x.split("|") for x in _combinaciones(sec)]
            q = q.where(or_(*[(Ejercicio.materia == m) & (Ejercicio.submateria == (sub or "")) for m, sub in pares]))
        else:
            q = q.where(Ejercicio.materia == sec.materia, Ejercicio.submateria == (sec.submateria or ""))
        bloques = {b.id: b for b in s.scalars(select(Bloque))}
        disponibles = [e for e in s.scalars(q.order_by(Ejercicio.veces_usado, Ejercicio.id)) if e.id not in usados]

        def ficha(e):
            b = bloques.get(e.bloque_id) if e.bloque_id else None
            return {"id": e.id, "codigo": e.codigo, "tematica": e.tematica, "nivel": e.nivel,
                    "competencia": e.competencia, "pensamiento": e.pensamiento, "dba": e.dba,
                    "materia": e.materia, "submateria": e.submateria, "veces_usado": e.veces_usado, "texto": e.texto[:220],
                    "excluido": e.id in excluidos, "glosario": len(glosario.terminos(e)),
                    "imagen": e.tiene_imagen, "tabla": e.tiene_tabla,
                    "bloque": b.codigo if b else None, "tipo": b.tipo if b else "suelto",
                    "hermanos": len(b.ejercicios) if b else 1, "creado": f"{e.creado_en:%d/%m/%Y}"}

        fichas = [ficha(e) for e in disponibles]
        # lo que ya está elegido en esta sección, para mostrarlo junto a cada temática y nivel
        en_seccion = [i.ejercicio for i in c.items if i.seccion_id == sec.id]
        por_tematica, por_nivel = {}, {}
        for e in en_seccion:
            por_tematica[e.tematica] = por_tematica.get(e.tematica, 0) + 1
            por_nivel[e.nivel] = por_nivel.get(e.nivel, 0) + 1
        facetas = {"materias": _cuenta(fichas, lambda x: x["materia"]),
                   "tematicas": _cuenta(fichas, lambda x: x["tematica"], por_tematica, alfabetico=True),
                   "niveles": _cuenta(fichas, lambda x: x["nivel"], por_nivel),
                   "competencias": _cuenta(fichas, lambda x: x["competencia"]),
                   "pensamientos": _cuenta(fichas, lambda x: x["pensamiento"]),
                   "dba": _cuenta(fichas, lambda x: x["dba"]),
                   "submaterias": _cuenta(fichas, lambda x: x["submateria"]),
                   "tipos": _cuenta(fichas, lambda x: x["tipo"])}

        tematicas, niveles = _varios(filtros, "tematica"), _varios(filtros, "nivel")
        competencias, pensamientos = _varios(filtros, "competencia"), _varios(filtros, "pensamiento")
        dbas, tipos = _varios(filtros, "dba"), _varios(filtros, "tipo")
        submaterias, materias_f = _varios(filtros, "submateria"), _varios(filtros, "materia")
        recursos = _varios(filtros, "recurso")          # imagen · tabla · glosario · sin_imagen
        temas = temas_buscados(filtros.get("texto"))
        sin_usar = str(filtros.get("sin_usar") or "").lower() in ("1", "true", "si", "sí", "on")
        max_usos = filtros.get("max_usos")
        ocultar_excluidos = str(filtros.get("ocultar_excluidos") or "").lower() in ("1", "true", "si", "sí", "on")

        def pasa(x):
            if tematicas and x["tematica"] not in tematicas:
                return False
            if niveles and x["nivel"] not in niveles:
                return False
            if competencias and x["competencia"] not in competencias:
                return False
            if pensamientos and x["pensamiento"] not in pensamientos:
                return False
            if submaterias and x["submateria"] not in submaterias:
                return False
            if materias_f and x["materia"] not in materias_f:
                return False
            if tipos and x["tipo"] not in tipos:
                return False
            if dbas and not any(d in (x["dba"] or "") for d in dbas):
                return False
            if "imagen" in recursos and not x["imagen"]:
                return False
            if "tabla" in recursos and not x["tabla"]:
                return False
            if "glosario" in recursos and not x["glosario"]:
                return False
            if "sin_imagen" in recursos and x["imagen"]:
                return False
            if sin_usar and x["veces_usado"]:
                return False
            if max_usos not in (None, "") and x["veces_usado"] > int(max_usos):
                return False
            if ocultar_excluidos and x["excluido"]:
                return False
            return coincide(x, temas)

        encontrados = [x for x in fichas if pasa(x)]
        orden = filtros.get("orden") or "menos_usados"
        if orden == "tematica":
            encontrados.sort(key=lambda x: (x["tematica"].lower(), x["codigo"]))
        elif orden == "recientes":
            encontrados.sort(key=lambda x: x["id"], reverse=True)
        elif orden == "nivel":
            encontrados.sort(key=lambda x: (["Básico", "Medio", "Avanzado"].index(x["nivel"]) if x["nivel"] in
                                            ("Básico", "Medio", "Avanzado") else 9, x["tematica"].lower()))
        # en cada ejercicio, cuántos de su misma temática ya están en la sección (para no repetir sin darse cuenta)
        for x in encontrados:
            x["en_seccion"] = por_tematica.get(x["tematica"], 0)
        return {"total": len(encontrados), "disponibles": len(fichas), "items": encontrados[:300],
                "facetas": facetas, "seccion": {"titulo": sec.titulo, "cantidad": sec.cantidad, "elegidos": len(en_seccion)},
                "faltan": sec.cantidad - len(en_seccion)}


def buscar_en_cartilla(cid, texto):
    """Dónde está lo que se busca, sección por sección de esta cartilla.

    Sirve para lo que hace un docente de verdad: escribe los temas que está viendo («fracciones,
    células procariotas, guerra de los mil días») y necesita saber en qué sección de la cartilla
    puede poner cada uno, sin ir probando sección por sección.
    """
    temas = temas_buscados(texto)
    if not temas:
        return {"texto": texto or "", "secciones": [], "tematicas": []}
    with Sesion() as s:
        c = s.get(Cartilla, cid)
        if c is None:
            return None
        usados = {i.ejercicio_id for i in c.items}
        excluidos = _ejercicios_excluidos(s, c)
        bloques = {b.id: b for b in s.scalars(select(Bloque))}
        salida, tematicas = [], {}
        for sec in sorted(c.secciones, key=lambda x: x.orden):
            q = select(Ejercicio).where(Ejercicio.grado == c.grado)
            if sec.mezclada:
                pares = [x.split("|") for x in _combinaciones(sec)]
                q = q.where(or_(*[(Ejercicio.materia == m) & (Ejercicio.submateria == (sub or "")) for m, sub in pares]))
            else:
                q = q.where(Ejercicio.materia == sec.materia, Ejercicio.submateria == (sec.submateria or ""))
            libres = 0
            for e in s.scalars(q):
                ficha = {"tematica": e.tematica, "codigo": e.codigo, "texto": e.texto}
                if not coincide(ficha, temas):
                    continue
                if e.id in usados or e.id in excluidos:
                    continue
                libres += 1
                t = tematicas.setdefault(e.tematica, {"tematica": e.tematica, "n": 0, "secciones": set()})
                t["n"] += 1
                t["secciones"].add(sec.titulo)
            elegidos = len([i for i in c.items if i.seccion_id == sec.id])
            salida.append({"id": sec.id, "titulo": sec.titulo, "encontrados": libres,
                           "elegidos": elegidos, "cantidad": sec.cantidad, "faltan": sec.cantidad - elegidos})
        return {"texto": texto, "total": sum(x["encontrados"] for x in salida),
                "secciones": [x for x in salida if x["encontrados"] or x["cantidad"]],
                "tematicas": sorted(({**t, "secciones": sorted(t["secciones"])} for t in tematicas.values()),
                                    key=lambda x: (-x["n"], x["tematica"].lower()))[:40]}


def _unidad(s, e):
    """El ejercicio con sus hermanos, **en el orden del bloque**: un bloque o una parte entran completos.

    El orden dentro de un bloque no se negocia: las preguntas se refieren a un mismo texto o imagen y
    están escritas para leerse seguidas.
    """
    if not e.bloque_id:
        return [e]
    return s.scalars(select(Ejercicio).where(Ejercicio.bloque_id == e.bloque_id).order_by(Ejercicio.orden_en_bloque)).all()


def agregar(cid, seccion_id, ejercicio_id, permitir_exceso=False):
    with Sesion() as s:
        c = s.get(Cartilla, cid)
        sec = s.get(CartillaSeccion, seccion_id)
        e = s.get(Ejercicio, ejercicio_id)
        if c is None or sec is None or e is None or sec.cartilla_id != c.id:
            raise ErrorArmado("La cartilla, la sección o el ejercicio no existen.")
        if c.estado != "borrador":
            raise ErrorArmado("La cartilla ya fue generada.")
        if e.grado != c.grado:
            raise ErrorArmado(f"El ejercicio {e.codigo} es de otro grado.")
        if not acepta(sec, e):
            raise ErrorArmado(f"El ejercicio {e.codigo} ({e.materia}{' · ' + e.submateria if e.submateria else ''}) no corresponde a la sección {sec.titulo}.")
        excluidos = _ejercicios_excluidos(s, c)
        unidad = _unidad(s, e)
        usados = {i.ejercicio_id for i in c.items}
        nuevos = [x for x in unidad if x.id not in usados]
        if not nuevos:
            raise ErrorArmado("Ese ejercicio ya está en la cartilla.")
        repetidos = [x.codigo for x in nuevos if x.id in excluidos]
        if repetidos:
            raise ErrorArmado(f"{', '.join(repetidos)} ya se usó en una cartilla excluida (la otra sesión o un periodo anterior).")
        elegidos = len([i for i in c.items if i.seccion_id == sec.id])
        if elegidos + len(nuevos) > sec.cantidad and not permitir_exceso:
            b = s.get(Bloque, e.bloque_id) if e.bloque_id else None
            if b:
                raise ErrorArmado(f"El {'bloque' if b.tipo == 'bloque' else 'parte'} {b.codigo} trae {len(unidad)} preguntas y en {sec.titulo} solo faltan {sec.cantidad - elegidos}. "
                                  + ("Puedes quitarle preguntas al bloque después de agregarlo (mínimo 2) o ampliar la sección." if b.tipo == "bloque" else "Una parte de Inglés no se puede recortar: ajusta la cantidad de la sección."))
            raise ErrorArmado(f"La sección {sec.titulo} ya está completa.")
        siguiente = max([i.posicion for i in c.items if i.seccion_id == sec.id], default=0)
        for x in nuevos:
            siguiente += 1
            s.add(CartillaItem(cartilla_id=c.id, seccion_id=sec.id, ejercicio_id=x.id, posicion=siguiente))
        s.commit()
        return [x.codigo for x in nuevos]


def quitar(cid, ejercicio_id):
    with Sesion() as s:
        c = s.get(Cartilla, cid)
        it = next((i for i in (c.items if c else []) if i.ejercicio_id == ejercicio_id), None)
        if c is None or it is None:
            raise ErrorArmado("El ejercicio no está en la cartilla.")
        if c.estado != "borrador":
            raise ErrorArmado("La cartilla ya fue generada.")
        e = s.get(Ejercicio, ejercicio_id)
        quitados = [it]
        if e.bloque_id:
            b = s.get(Bloque, e.bloque_id)
            hermanos = [i for i in c.items if i.ejercicio.bloque_id == e.bloque_id]
            if not b.permite_recorte:
                quitados = hermanos          # una parte de Inglés entra y sale completa
            elif len(hermanos) - 1 < 2:
                quitados = hermanos          # un bloque no puede quedar con menos de 2 preguntas
        for i in quitados:
            s.delete(i)
        s.flush()
        for sec in c.secciones:
            for n, i in enumerate(sorted([x for x in c.items if x.seccion_id == sec.id and x not in quitados], key=lambda x: x.posicion), 1):
                i.posicion = n
        s.commit()
        return [s.get(Ejercicio, i.ejercicio_id).codigo for i in quitados]


def reordenar(cid, seccion_id, orden_ids):
    with Sesion() as s:
        c = s.get(Cartilla, cid)
        if c is None or c.estado != "borrador":
            raise ErrorArmado("La cartilla no existe o ya fue generada.")
        items = {i.ejercicio_id: i for i in c.items if i.seccion_id == seccion_id}
        if set(orden_ids) != set(items):
            raise ErrorArmado("La lista de orden no coincide con los ejercicios de la sección.")
        bloques = {}
        for sitio, eid in enumerate(orden_ids):
            e = s.get(Ejercicio, eid)
            if e.bloque_id:
                bloques.setdefault(e.bloque_id, []).append((sitio, e.orden_en_bloque))
        for pares in bloques.values():
            sitios = [x for x, _ in pares]
            if sitios != list(range(min(sitios), min(sitios) + len(sitios))):
                raise ErrorArmado("Las preguntas de un bloque o de una parte van seguidas: no se pueden separar.")
            # y en SU orden: las preguntas de una lectura se refieren al mismo texto y se apoyan entre sí
            if [o for _, o in pares] != sorted(o for _, o in pares):
                raise ErrorArmado("Las preguntas de un bloque o de una parte conservan el orden que traía "
                                  "el archivo: no se pueden barajar entre ellas.")
        for n, eid in enumerate(orden_ids, 1):
            items[eid].posicion = n
        s.commit()
    return detalle(cid)


def automatica(cid, seccion_id, cuotas=None):
    """Completa la sección con los ejercicios menos usados, repartiendo por nivel y temática."""
    with Sesion() as s:
        c = s.get(Cartilla, cid)
        sec = s.get(CartillaSeccion, seccion_id)
        if c is None or sec is None:
            raise ErrorArmado("La sección no existe.")
        faltan = sec.cantidad - len([i for i in c.items if i.seccion_id == sec.id])
        if faltan <= 0:
            return {"agregados": [], "faltan": 0, "mensaje": "La sección ya está completa."}
        usados = {i.ejercicio_id for i in c.items}
        excluidos = _ejercicios_excluidos(s, c)
        q = select(Ejercicio).where(Ejercicio.grado == c.grado)
        if sec.mezclada:
            pares = [x.split("|") for x in _combinaciones(sec)]
            q = q.where(or_(*[(Ejercicio.materia == m) & (Ejercicio.submateria == (sub or "")) for m, sub in pares]))
        else:
            q = q.where(Ejercicio.materia == sec.materia, Ejercicio.submateria == (sec.submateria or ""))
        disponibles = [e for e in s.scalars(q.order_by(Ejercicio.veces_usado, Ejercicio.id))
                       if e.id not in usados and e.id not in excluidos]
        mezcla = c.dificultad if sec.dificultad == "=" else sec.dificultad
        cupo = dict(cuotas) if cuotas else cupos(faltan, mezcla)
        agregados, avisos = [], []
        # la última posición ocupada de la sección; se lleva aquí porque c.items todavía no trae lo que se
        # agrega en esta misma pasada: recalcularlo en cada bloque hacía que todos empezaran en 1
        siguiente = max([i.posicion for i in c.items if i.seccion_id == sec.id], default=0)
        por_tematica = {}
        for e in disponibles:
            por_tematica.setdefault(e.tematica, []).append(e)
        orden_tematicas = sorted(por_tematica, key=lambda t: -len(por_tematica[t]))
        cola = []
        while any(por_tematica.values()):
            for t in orden_tematicas:
                if por_tematica.get(t):
                    cola.append(por_tematica[t].pop(0))
        fuera_de_cupo = []

        def intentar(e, respetar_cupo):
            nonlocal siguiente
            if len(agregados) >= faltan:
                return
            if respetar_cupo and cupo and e.nivel and cupo.get(e.nivel, 0) <= 0:
                fuera_de_cupo.append(e)
                return
            unidad = _unidad(s, e)
            nuevos = [x for x in unidad if x.id not in usados and x.id not in excluidos]
            if len(nuevos) != len(unidad):
                return
            if len(agregados) + len(nuevos) > faltan:
                if e.bloque_id:
                    b = s.get(Bloque, e.bloque_id)
                    aviso = f"El {'bloque' if b.tipo == 'bloque' else 'parte'} {b.codigo} trae {len(unidad)} preguntas y no cabe en lo que falta; agrégalo a mano si quieres recortarlo."
                    if aviso not in avisos:
                        avisos.append(aviso)
                return
            for x in nuevos:
                siguiente += 1
                s.add(CartillaItem(cartilla_id=c.id, seccion_id=sec.id, ejercicio_id=x.id, posicion=siguiente))
                usados.add(x.id)
                agregados.append(x.codigo)
                if cupo and x.nivel in cupo:
                    cupo[x.nivel] -= 1
            s.flush()

        for e in cola:
            intentar(e, respetar_cupo=True)
        # si no alcanzaron los del nivel pedido, se completa con los demás y se avisa
        completados_con_otro_nivel = 0
        for e in fuera_de_cupo:
            antes = len(agregados)
            intentar(e, respetar_cupo=False)
            completados_con_otro_nivel += len(agregados) - antes
        s.commit()
        quedan = faltan - len(agregados)
        mensaje = "Se agregó 1 ejercicio." if len(agregados) == 1 else f"Se agregaron {len(agregados)} ejercicios."
        if completados_con_otro_nivel:
            mensaje += f" {completados_con_otro_nivel} son de otro nivel: no había suficientes con la dificultad pedida."
        if quedan:
            mensaje += f" Faltan {quedan}: no hay más ejercicios disponibles para esta sección. " + " ".join(avisos)
        return {"agregados": agregados, "faltan": quedan, "mensaje": mensaje.strip(),
                "otro_nivel": completados_con_otro_nivel}


# ====================================================================== verificación
def _verificar(s, c):
    """Las comprobaciones del estándar (Parte 8) antes de generar."""
    out = []
    add = lambda ok, texto: out.append({"ok": ok, "texto": texto})
    total = sum(x.cantidad for x in c.secciones)
    for sec in sorted(c.secciones, key=lambda x: x.orden):
        n = len([i for i in c.items if i.seccion_id == sec.id])
        add(n == sec.cantidad, f"{sec.titulo}: {n} de {sec.cantidad} ejercicios")
    add(total > 0 and total <= 140, f"Total de {total} preguntas (máximo 140, el largo de las plantillas)")
    add(len(c.items) == total, f"Suma de las secciones: {len(c.items)} de {total}")
    otra = s.scalar(select(Cartilla).where(Cartilla.codigo == c.codigo, Cartilla.id != c.id))
    add(otra is None, f"El código {c.codigo} no está repetido en el histórico")
    esperado = codigo_de(c.grado, c.codigo_materia, c.tipo_material, c.plantilla, c.version)
    add(c.codigo == esperado, f"El código corresponde a lo seleccionado ({esperado})")
    add(bool(c.institucion.strip() and c.nombre.strip()), "Institución y nombre descriptivo")
    excluidos = _ejercicios_excluidos(s, c)
    repetidos = [i.ejercicio.codigo for i in c.items if i.ejercicio_id in excluidos]
    add(not repetidos, "Ningún ejercicio se repite con las cartillas excluidas" + (f": {', '.join(repetidos)}" if repetidos else ""))
    return out


def verificar(cid):
    with Sesion() as s:
        c = s.get(Cartilla, cid)
        if c is None:
            return None
        pruebas = _verificar(s, c)
        return {"ok": all(p["ok"] for p in pruebas), "pruebas": pruebas}


# ====================================================================== vista previa
def vista_previa(cid):
    from app.banco import _items_html, _parrafo_html

    with Sesion() as s:
        c = s.get(Cartilla, cid)
        if c is None:
            return None
        secuencia = _plantilla(s, c.plantilla)
        num = posiciones(c)
        es_icfes = c.grado == base.GRADO_ICFES
        archivos = {}
        partes_html = []
        bloques_vistos = set()
        for sec in sorted(c.secciones, key=lambda x: x.orden):
            items = sorted([i for i in c.items if i.seccion_id == sec.id], key=lambda x: x.posicion)
            partes_html.append(f'<h3 class="st">{sec.titulo}</h3>')
            numero_parte = 0          # las partes de Inglés se numeran dentro de su sección
            if not items:
                partes_html.append('<p class="nota">Sin ejercicios todavía.</p>')
            for it in items:
                e = it.ejercicio
                if e.archivo_id not in archivos:
                    arch = s.get(Archivo, e.archivo_id)
                    archivos[e.archivo_id] = analisis.leer(e.archivo_id, arch.datos, arch.nombre)
                v = archivos[e.archivo_id]
                pr = v.unidad.preguntas[e.orden_en_bloque - 1]
                if e.bloque_id and e.bloque_id not in bloques_vistos:
                    bloques_vistos.add(e.bloque_id)
                    hermanos = [x for x in items if x.ejercicio.bloque_id == e.bloque_id]
                    ini, fin = num[hermanos[0].ejercicio_id], num[hermanos[-1].ejercicio_id]
                    cab = v.unidad.cabecera
                    texto_cab = re.sub(r"#N", str(ini), re.sub(r"#M", str(fin), cab.texto)) if cab is not None else ""
                    if s.get(Bloque, e.bloque_id).tipo == "parte":
                        numero_parte += 1
                        texto_cab = re.sub(r"PARTE\s+#P", f"PARTE {numero_parte}", texto_cab)
                    partes_html.append(f'<p class="ref">{texto_cab}</p>')
                    if v.unidad.instruccion is not None:
                        partes_html.append(_parrafo_html(v.unidad.instruccion, v.doc, "instruccion"))
                    if v.unidad.recurso:
                        partes_html.append(f'<div class="recurso">{_items_html(v.unidad.recurso, v.doc)}'
                                           f'{_parrafo_html(v.unidad.credito, v.doc) if v.unidad.credito is not None else ""}</div>')
                n = num[e.id]
                letra = secuencia[n - 1]
                opciones = {letra_opcion(o): o for o in pr.opciones}
                ops = []
                for destino in "ABCD":
                    # la correcta pasa a la letra de la plantilla y la que estaba ahí toma su lugar (5.2)
                    origen = e.clave_original if destino == letra else (letra if destino == e.clave_original else destino)
                    html = _parrafo_html(opciones[origen], v.doc, "opcion" + (" correcta" if destino == letra else ""))
                    ops.append(re.sub(r"<b>\s*" + origen + r"\.", "<b>" + destino + ".", html, count=1))
                info = ""
                if not es_icfes:
                    campos = [e.pensamiento, e.competencia, e.dba, {"Básico": "BB", "Medio": "MM", "Avanzado": "AA"}.get(e.nivel, "")]
                    campos = [x for x in campos if x]
                    info = f'<p class="inf">➤ {" // ".join(campos)}</p>' if campos else ""
                glos = glosario.a_html(glosario.terminos(e)) if c.glosario else ""
                partes_html.append(f'<div class="pregunta"><div class="numero">{n}.</div><div class="cuerpo-preg">'
                                   f'{_items_html(pr.enunciado, v.doc)}{"".join(ops)}{info}{glos}</div></div>')
        return {"codigo": c.codigo, "total": sum(x.cantidad for x in c.secciones), "elegidos": len(c.items),
                "html": "".join(partes_html)}


def eliminar(cid):
    """Borra la cartilla. Si ya estaba generada, también su Word y su Excel, y devuelve el uso contado.

    Al generar, cada ejercicio suma un uso; al eliminar la cartilla ese uso se descuenta, para que el
    banco siga diciendo la verdad sobre qué se ha usado y qué no. Los ejercicios no se tocan.
    """
    with Sesion() as s:
        c = s.get(Cartilla, cid)
        if c is None:
            return None
        generada = c.estado == "generada"
        if generada:
            for i in c.items:
                if i.ejercicio.veces_usado > 0:
                    i.ejercicio.veces_usado -= 1
        for a in s.scalars(select(CartillaArchivo).where(CartillaArchivo.cartilla_id == cid)):
            s.delete(a)
        for x in s.scalars(select(CartillaExcluida).where(or_(CartillaExcluida.cartilla_id == cid, CartillaExcluida.excluida_id == cid))):
            s.delete(x)
        datos = {"codigo": c.codigo, "nombre": c.nombre, "generada": generada, "preguntas": len(c.items)}
        s.delete(c)
        s.commit()
        return datos
