"""Lo que el validador necesita saber de los catálogos, sin depender de la base de datos."""
import re
import unicodedata
from dataclasses import dataclass, field

from app import catalogos_base as base


def sin_tildes(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def clave(s):
    """Forma de comparación: sin mayúsculas, tildes ni espacios sobrantes."""
    return re.sub(r"\s+", " ", sin_tildes(s or "")).strip().lower()


@dataclass
class CatalogoValidacion:
    grados: dict = field(default_factory=dict)          # texto aceptado -> código
    materias: dict = field(default_factory=dict)        # clave -> nombre oficial
    submaterias: dict = field(default_factory=dict)     # clave materia -> {clave sub -> nombre}
    regla_submateria: dict = field(default_factory=dict)  # nombre materia -> True/None/False
    materias_superindice: set = field(default_factory=set)
    excepciones_superindice: set = field(default_factory=set)
    frases_prohibidas: list = field(default_factory=list)  # (frase, distingue mayúsculas)
    registrados: dict = field(default_factory=dict)     # «Temática» -> [valores ya registrados]
    grado_icfes: str = base.GRADO_ICFES
    nombres_grados: list = field(default_factory=list)  # para los mensajes: «3°, 4°, … 11° o ICFES»
    _claves: dict = field(default_factory=dict, repr=False)

    def claves_registradas(self, campo):
        """{valor registrado: forma de comparación}, calculado una sola vez por catálogo."""
        if campo not in self._claves:
            self._claves[campo] = {v: clave(v) for v in self.registrados.get(campo, [])}
        return self._claves[campo]

    @classmethod
    def de_fabrica(cls, registrados=None, excepciones=None, frases=None):
        c = cls()
        c.nombres_grados = [nombre for nombre, _, _ in base.GRADOS]
        for nombre, codigo, _ in base.GRADOS:
            c.grados[clave(nombre)] = codigo
            c.grados[clave(nombre.replace("°", "º"))] = codigo
            c.grados[codigo] = codigo
        for nombre, *_ in base.MATERIAS:
            c.materias[clave(nombre)] = nombre
            c.submaterias[clave(nombre)] = {}
        for materia, sub, *_ in base.SUBMATERIAS:
            c.submaterias[clave(materia)][clave(sub)] = sub
        c.regla_submateria = {m: base.SUBMATERIA_REGLA.get(m, False) for m, *_ in base.MATERIAS}
        c.materias_superindice = set(base.MATERIAS_SUPERINDICE)
        c.excepciones_superindice = set(excepciones if excepciones is not None else base.EXCEPCIONES_SUPERINDICE)
        c.frases_prohibidas = list(frases if frases is not None else base.FRASES_PROHIBIDAS)
        c.registrados = registrados or {}
        return c
