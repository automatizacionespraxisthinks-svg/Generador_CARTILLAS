"""Carga los catálogos de fábrica la primera vez que arranca el sistema."""
import csv

from sqlalchemy import select

from app import catalogos_base as base
from app.bd import (Agrupacion, Estructura, EstructuraSeccion, ExcepcionSuperindice, FraseProhibida, Grado, Materia,
                    Plantilla, Sesion, Submateria, TipoMaterial, ValorRegistrado, crear_tablas)
from app.config import PLANTILLAS
from app.validador.catalogo import CatalogoValidacion


def leer_plantillas():
    with open(PLANTILLAS / "PLANTILLAS_RESPUESTAS.csv", encoding="utf-8") as f:
        filas = list(csv.DictReader(f))
    secuencias = {n: "".join(fila[f"Plantilla{n}"] for fila in filas) for n in range(1, 6)}
    for n, s in secuencias.items():
        if len(s) != 140 or set(s) - set("ABCD"):
            raise ValueError(f"La plantilla {n} no tiene 140 letras A-D")
    return secuencias


def poblar():
    crear_tablas()
    from app.migraciones import aplicar
    aplicar()
    with Sesion() as s:
        if s.scalar(select(Grado).limit(1)):
            return False
        s.add_all(Grado(nombre=n, codigo=c, texto_portada=t) for n, c, t in base.GRADOS)
        materias = {}
        for nombre, codigo, prefijo, color in base.MATERIAS:
            materias[nombre] = Materia(nombre=nombre, codigo=codigo, prefijo=prefijo, color=color)
            s.add(materias[nombre])
        for materia, sub, codigo, prefijo in base.SUBMATERIAS:
            s.add(Submateria(materia=materias[materia], nombre=sub, codigo=codigo, prefijo=prefijo))
        s.add_all(Agrupacion(nombre=n, codigo=c) for n, c in base.AGRUPACIONES)
        s.add_all(TipoMaterial(nombre=n, codigo=c) for n, c in base.TIPOS_MATERIAL)
        s.add_all(Plantilla(numero=n, secuencia=sec) for n, sec in leer_plantillas().items())
        for clave, nombre, cod, editable, secciones in base.ESTRUCTURAS:
            e = Estructura(clave=clave, nombre=nombre, codigo_materia=cod, editable=editable)
            for i, (titulo, mat, sub, cant, mezcla, admitidas) in enumerate(secciones, 1):
                e.secciones.append(EstructuraSeccion(orden=i, titulo=titulo, materia=mat, submateria=sub, cantidad=cant,
                                                     mezclada=mezcla, admitidas=";".join(admitidas) if admitidas else None))
            s.add(e)
        s.add_all(ExcepcionSuperindice(texto=t) for t in base.EXCEPCIONES_SUPERINDICE)
        s.add_all(FraseProhibida(frase=f, distingue_mayusculas=m) for f, m in base.FRASES_PROHIBIDAS)
        s.commit()
    return True


def catalogo_validacion():
    """Catálogo del validador con las listas editables y los valores ya registrados en la base."""
    with Sesion() as s:
        registrados = {}
        for v in s.scalars(select(ValorRegistrado)):
            registrados.setdefault(v.campo, []).append(v.valor)
        excepciones = [e.texto for e in s.scalars(select(ExcepcionSuperindice))]
        frases = [(f.frase, f.distingue_mayusculas) for f in s.scalars(select(FraseProhibida))]
    return CatalogoValidacion.de_fabrica(registrados=registrados, excepciones=excepciones, frases=frases)
