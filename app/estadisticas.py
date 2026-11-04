"""Panel: qué hay hoy en el banco y qué falta para armar cada cartilla.

Todo sale de contar lo que está guardado; no cambia nada. Sirve para decidir qué ejercicios hacen falta
antes de armar un simulacro.
"""
from sqlalchemy import case, func, select

from app import catalogos_base as base
from app.armado import estructura_admite
from app.bd import Bloque, Cartilla, CargaPendiente, Ejercicio, Estructura, Grado, Sesion


def _lista(filas, claves):
    return [dict(zip(claves, fila)) for fila in filas]


def _conteo(s, *columnas, orden=None):
    q = select(*columnas, func.count(Ejercicio.id)).group_by(*columnas)
    return s.execute(q.order_by(orden) if orden is not None else q).all()


def resumen_banco():
    """Totales, reparto por grado, materia, submateria, nivel y tipo, y las temáticas con su número de preguntas."""
    with Sesion() as s:
        grados = {g.codigo: g.nombre for g in s.scalars(select(Grado))}
        nombre_grado = lambda c: grados.get(c, c)
        total = s.scalar(select(func.count(Ejercicio.id))) or 0
        unidades = s.scalar(select(func.count(Bloque.id))) or 0
        sin_usar = s.scalar(select(func.count(Ejercicio.id)).where(Ejercicio.veces_usado == 0)) or 0
        con_imagen = s.scalar(select(func.count(Ejercicio.id)).where(Ejercicio.tiene_imagen.is_(True))) or 0
        con_tabla = s.scalar(select(func.count(Ejercicio.id)).where(Ejercicio.tiene_tabla.is_(True))) or 0
        con_glosario = s.scalar(select(func.count(Ejercicio.id)).where(Ejercicio.glosario.notin_(("[]", "")))) or 0
        pendientes = s.scalar(select(func.count(CargaPendiente.id))) or 0
        cartillas = s.scalar(select(func.count(Cartilla.id)).where(Cartilla.estado == "generada")) or 0

        por_grado = [{"grado": g, "nombre": nombre_grado(g), "n": n}
                     for g, n in _conteo(s, Ejercicio.grado)]
        por_grado.sort(key=lambda x: base.orden_grado(x["grado"]))
        por_materia = [{"grado": g, "nombre_grado": nombre_grado(g), "materia": m, "submateria": sub or "", "n": n}
                       for g, m, sub, n in _conteo(s, Ejercicio.grado, Ejercicio.materia, Ejercicio.submateria)]
        por_materia.sort(key=lambda x: (base.orden_grado(x["grado"]), x["materia"], x["submateria"]))
        por_nivel = [{"grado": g, "nivel": nv or "(sin nivel)", "n": n}
                     for g, nv, n in _conteo(s, Ejercicio.grado, Ejercicio.nivel)]
        tipos = {"suelto": 0, "bloque": 0, "parte": 0}
        for tipo, n in s.execute(select(Bloque.tipo, func.count(Ejercicio.id)).join(Ejercicio, Ejercicio.bloque_id == Bloque.id)
                                 .group_by(Bloque.tipo)).all():
            tipos[tipo] = n
        tipos["suelto"] = s.scalar(select(func.count(Ejercicio.id)).where(Ejercicio.bloque_id.is_(None))) or 0
        tematicas = [{"grado": g, "materia": m, "submateria": sub or "", "tematica": t, "n": n, "sin_usar": su or 0}
                     for g, m, sub, t, n, su in s.execute(
                         select(Ejercicio.grado, Ejercicio.materia, Ejercicio.submateria, Ejercicio.tematica,
                                func.count(Ejercicio.id), func.sum(case((Ejercicio.veces_usado == 0, 1), else_=0)))
                         .group_by(Ejercicio.grado, Ejercicio.materia, Ejercicio.submateria, Ejercicio.tematica)).all()]
        tematicas.sort(key=lambda x: (base.orden_grado(x["grado"]), x["materia"], x["submateria"], x["tematica"]))
        return {"total": total, "unidades": unidades, "sin_usar": sin_usar, "usados": total - sin_usar,
                "con_imagen": con_imagen, "con_tabla": con_tabla, "con_glosario": con_glosario,
                "pendientes": pendientes, "cartillas_generadas": cartillas, "tematicas_distintas": len(tematicas),
                "por_grado": por_grado, "por_materia": por_materia, "por_nivel": por_nivel, "por_tipo": tipos,
                "tematicas": tematicas}


def cobertura():
    """Por cada grado con ejercicios, qué estructuras se pueden armar y cuántas preguntas faltan en cada sección."""
    with Sesion() as s:
        grados = {g.codigo: g.nombre for g in s.scalars(select(Grado))}
        hay = {(g, m, sub or ""): n for g, m, sub, n in
               _conteo(s, Ejercicio.grado, Ejercicio.materia, Ejercicio.submateria)}
        con_ejercicios = sorted({g for g, _, _ in hay}, key=base.orden_grado)
        estructuras = s.scalars(select(Estructura).order_by(Estructura.clave)).all()
        salida = []
        for grado in con_ejercicios:
            for e in estructuras:
                if not e.secciones or not estructura_admite(e, grado):
                    continue
                secciones = []
                for x in sorted(e.secciones, key=lambda y: y.orden):
                    if x.mezclada:
                        combos = [c.split("|") for c in (x.admitidas or "").split(";") if c]
                        disponibles = sum(hay.get((grado, m, sub), 0) for m, sub in combos)
                    else:
                        disponibles = hay.get((grado, x.materia, x.submateria or ""), 0)
                    secciones.append({"titulo": x.titulo, "materia": x.materia, "submateria": x.submateria or "",
                                      "necesita": x.cantidad, "hay": disponibles,
                                      "faltan": max(0, x.cantidad - disponibles)})
                salida.append({"grado": grado, "nombre_grado": grados.get(grado, grado), "estructura": e.clave,
                               "nombre": e.nombre, "necesita": sum(x["necesita"] for x in secciones),
                               "hay": sum(min(x["hay"], x["necesita"]) for x in secciones),
                               "faltan": sum(x["faltan"] for x in secciones), "secciones": secciones})
        return salida
