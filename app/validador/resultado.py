import re
from dataclasses import asdict, dataclass, field

ACEPTADO, RECHAZADO, PENDIENTE = "aceptado", "rechazado", "pendiente"


@dataclass
class Motivo:
    regla: int          # número de la regla en el Estándar 2.12 (0 = lectura del archivo)
    donde: str          # «Pregunta 2 · opción C», «TABLA DE EXCEL · fila 1»…
    mensaje: str        # qué pasa y cómo corregirlo


@dataclass
class Similitud:
    campo: str          # Temática, Competencia, Pensamiento
    valor: str          # lo que trae el archivo
    parecido_a: str     # valor ya registrado


@dataclass
class Resultado:
    archivo: str
    tipo: str | None = None                 # suelto | bloque | parte
    preguntas: int = 0
    errores: list = field(default_factory=list)
    similitudes: list = field(default_factory=list)
    avisos: list = field(default_factory=list)
    filas: list = field(default_factory=list)   # datos normalizados de la TABLA DE EXCEL
    claves: list = field(default_factory=list)
    justificaciones: list = field(default_factory=list)
    glosarios: list = field(default_factory=list)   # por pregunta: [{"termino", "significado"}] (TABLA DE GLOSARIO)
    guardado: dict | None = None               # códigos asignados al entrar al banco
    pendiente_id: int | None = None

    def error(self, regla, donde, mensaje):
        clave = (regla, donde, mensaje)
        if clave not in {(m.regla, m.donde, m.mensaje) for m in self.errores}:
            self.errores.append(Motivo(regla, donde, mensaje))

    def aviso(self, donde, mensaje):
        self.avisos.append(Motivo(0, donde, mensaje))

    @property
    def estado(self):
        if self.errores:
            return RECHAZADO
        if self.similitudes:
            return PENDIENTE
        return ACEPTADO

    def a_dict(self):
        d = asdict(self)
        d["estado"] = self.estado
        d["errores"] = sorted(d["errores"], key=lambda m: orden_lectura(m["donde"]))
        return d


def orden_lectura(donde):
    """Ordena los motivos como se lee el Word: documento, contenido, preguntas y al final las tablas."""
    numero = lambda: int(re.search(r"(\d+)", donde).group(1)) if re.search(r"\d+", donde) else 0
    if donde.startswith(("Archivo", "Documento", "Configuración")):
        return (0, 0)
    if donde.startswith("TABLA DE RESPUESTAS"):
        return (3, numero())
    if donde.startswith("TABLA DE EXCEL"):
        return (4, numero())
    if donde.startswith("TABLA DE GLOSARIO"):
        return (5, numero())
    if donde.startswith("Pregunta "):
        return (2, numero())
    return (1, 0)
