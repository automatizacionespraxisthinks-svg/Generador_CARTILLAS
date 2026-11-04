from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, LargeBinary, String, Text, UniqueConstraint, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

from app.config import URL_BD

motor = create_engine(URL_BD, connect_args={"check_same_thread": False} if URL_BD.startswith("sqlite") else {})
Sesion = sessionmaker(bind=motor, expire_on_commit=False)


def usar_base(url):
    """Cambia la base de datos en caliente (las pruebas usan una temporal por archivo)."""
    global motor
    motor.dispose()
    motor = create_engine(url, connect_args={"check_same_thread": False} if url.startswith("sqlite") else {})
    Sesion.configure(bind=motor)
    return motor


class Base(DeclarativeBase):
    pass


class Grado(Base):
    __tablename__ = "grado"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(20), unique=True)
    codigo: Mapped[str] = mapped_column(String(2), unique=True)
    texto_portada: Mapped[str] = mapped_column(String(20))


class Materia(Base):
    __tablename__ = "materia"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(60), unique=True)
    codigo: Mapped[str | None] = mapped_column(String(2))
    prefijo: Mapped[str | None] = mapped_column(String(3))
    color: Mapped[str] = mapped_column(String(7))
    submaterias: Mapped[list["Submateria"]] = relationship(back_populates="materia", order_by="Submateria.id")


class Submateria(Base):
    __tablename__ = "submateria"
    __table_args__ = (UniqueConstraint("materia_id", "nombre"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    materia_id: Mapped[int] = mapped_column(ForeignKey("materia.id"))
    nombre: Mapped[str] = mapped_column(String(60))
    codigo: Mapped[str | None] = mapped_column(String(2))
    prefijo: Mapped[str] = mapped_column(String(3))
    materia: Mapped[Materia] = relationship(back_populates="submaterias")


class Agrupacion(Base):
    __tablename__ = "agrupacion"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80))
    codigo: Mapped[str] = mapped_column(String(2), unique=True)


class TipoMaterial(Base):
    __tablename__ = "tipo_material"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(60))
    codigo: Mapped[str] = mapped_column(String(2), unique=True)


class Plantilla(Base):
    __tablename__ = "plantilla"
    numero: Mapped[int] = mapped_column(Integer, primary_key=True)
    secuencia: Mapped[str] = mapped_column(String(140))


class Estructura(Base):
    __tablename__ = "estructura"
    id: Mapped[int] = mapped_column(primary_key=True)
    clave: Mapped[str] = mapped_column(String(4), unique=True)
    nombre: Mapped[str] = mapped_column(String(80))
    codigo_materia: Mapped[str | None] = mapped_column(String(2))
    editable: Mapped[bool] = mapped_column(Boolean, default=False)
    secciones: Mapped[list["EstructuraSeccion"]] = relationship(order_by="EstructuraSeccion.orden", cascade="all, delete-orphan")

    @property
    def total(self):
        return sum(s.cantidad for s in self.secciones)


class EstructuraSeccion(Base):
    __tablename__ = "estructura_seccion"
    id: Mapped[int] = mapped_column(primary_key=True)
    estructura_id: Mapped[int] = mapped_column(ForeignKey("estructura.id"))
    orden: Mapped[int] = mapped_column(Integer)
    titulo: Mapped[str] = mapped_column(String(80))
    materia: Mapped[str] = mapped_column(String(60))
    submateria: Mapped[str | None] = mapped_column(String(60))
    cantidad: Mapped[int] = mapped_column(Integer)
    mezclada: Mapped[bool] = mapped_column(Boolean, default=False)
    admitidas: Mapped[str | None] = mapped_column(Text)   # lista separada por «;»


class ValorRegistrado(Base):
    """Catálogo que se construye solo: temáticas, competencias, pensamientos."""
    __tablename__ = "valor_registrado"
    __table_args__ = (UniqueConstraint("campo", "valor"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    campo: Mapped[str] = mapped_column(String(20))
    valor: Mapped[str] = mapped_column(String(200))


class ExcepcionSuperindice(Base):
    __tablename__ = "excepcion_superindice"
    id: Mapped[int] = mapped_column(primary_key=True)
    texto: Mapped[str] = mapped_column(String(40), unique=True)


class FraseProhibida(Base):
    __tablename__ = "frase_prohibida"
    id: Mapped[int] = mapped_column(primary_key=True)
    frase: Mapped[str] = mapped_column(String(80), unique=True)
    distingue_mayusculas: Mapped[bool] = mapped_column(Boolean, default=False)


# ====================================================================== banco de ejercicios
class Archivo(Base):
    """El Word de carga tal como se subió: la garantía de que ningún dato se pierde."""
    __tablename__ = "archivo"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(255))
    datos: Mapped[bytes] = mapped_column(LargeBinary)
    huella: Mapped[str] = mapped_column(String(64), index=True)       # sha256 del contenido de las preguntas
    subido_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class Bloque(Base):
    """Bloque de lectura compartida o parte de Inglés: se usa siempre como unidad."""
    __tablename__ = "bloque"
    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(20), unique=True)
    tipo: Mapped[str] = mapped_column(String(10))                      # bloque | parte
    tipo_recurso: Mapped[str | None] = mapped_column(String(20))       # lectura | información
    titulo_parte: Mapped[str | None] = mapped_column(String(120))
    xml_cabecera: Mapped[str | None] = mapped_column(Text)
    xml_instruccion: Mapped[str | None] = mapped_column(Text)
    xml_recurso: Mapped[str | None] = mapped_column(Text)              # incluye la línea de crédito
    permite_recorte: Mapped[bool] = mapped_column(Boolean)
    archivo_id: Mapped[int] = mapped_column(ForeignKey("archivo.id"))
    ejercicios: Mapped[list["Ejercicio"]] = relationship(back_populates="bloque", order_by="Ejercicio.orden_en_bloque")


class Ejercicio(Base):
    __tablename__ = "ejercicio"
    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(20), unique=True)
    grado: Mapped[str] = mapped_column(String(2), index=True)          # código de grado
    materia: Mapped[str] = mapped_column(String(60), index=True)
    submateria: Mapped[str] = mapped_column(String(60), default="")
    pensamiento: Mapped[str] = mapped_column(String(200), default="")
    competencia: Mapped[str] = mapped_column(String(200), default="")
    dba: Mapped[str] = mapped_column(String(60), default="")
    tematica: Mapped[str] = mapped_column(String(200), index=True)
    nivel: Mapped[str] = mapped_column(String(10), default="")
    clave_original: Mapped[str] = mapped_column(String(1))
    justificacion: Mapped[str] = mapped_column(Text)
    bloque_id: Mapped[int | None] = mapped_column(ForeignKey("bloque.id"))
    orden_en_bloque: Mapped[int] = mapped_column(Integer, default=1)
    veces_usado: Mapped[int] = mapped_column(Integer, default=0)
    tiene_imagen: Mapped[bool] = mapped_column(Boolean, default=False)
    tiene_tabla: Mapped[bool] = mapped_column(Boolean, default=False)
    texto: Mapped[str] = mapped_column(Text)                           # texto plano para la búsqueda
    xml_enunciado: Mapped[str] = mapped_column(Text)
    xml_opcion_a: Mapped[str] = mapped_column(Text)
    xml_opcion_b: Mapped[str] = mapped_column(Text)
    xml_opcion_c: Mapped[str] = mapped_column(Text)
    xml_opcion_d: Mapped[str] = mapped_column(Text)
    glosario: Mapped[str] = mapped_column(Text, default="[]")          # JSON: [{"termino", "significado"}]
    archivo_id: Mapped[int] = mapped_column(ForeignKey("archivo.id"))
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    bloque: Mapped[Bloque | None] = relationship(back_populates="ejercicios")
    archivo: Mapped[Archivo] = relationship()


class Consecutivo(Base):
    """Último número usado por prefijo y grado. Nunca se reutiliza, aunque se borre el ejercicio."""
    __tablename__ = "consecutivo"
    prefijo: Mapped[str] = mapped_column(String(4), primary_key=True)
    grado: Mapped[str] = mapped_column(String(2), primary_key=True)
    tipo: Mapped[str] = mapped_column(String(1), primary_key=True)     # E ejercicio · B bloque
    ultimo: Mapped[int] = mapped_column(Integer, default=0)


class CargaPendiente(Base):
    """Archivo válido que espera confirmación de una temática, competencia o pensamiento parecido."""
    __tablename__ = "carga_pendiente"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(255))
    datos: Mapped[bytes] = mapped_column(LargeBinary)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


# ====================================================================== cartillas
class Cartilla(Base):
    __tablename__ = "cartilla"
    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(10), unique=True)
    institucion: Mapped[str] = mapped_column(String(160))
    nombre: Mapped[str] = mapped_column(String(160))                  # nombre descriptivo
    grado: Mapped[str] = mapped_column(String(2))
    estructura: Mapped[str] = mapped_column(String(4))                # E1…E7
    codigo_materia: Mapped[str] = mapped_column(String(2))
    tipo_material: Mapped[str] = mapped_column(String(2))
    plantilla: Mapped[int] = mapped_column(Integer)
    version: Mapped[str] = mapped_column(String(2), default="01")
    simulacro_n: Mapped[int] = mapped_column(Integer, default=1)
    tiempo: Mapped[str] = mapped_column(String(60))
    dificultad: Mapped[str] = mapped_column(String(10), default="bm")  # mezcla por defecto de las secciones
    glosario: Mapped[bool] = mapped_column(Boolean, default=False)     # imprimir el glosario de las preguntas
    portada: Mapped[str] = mapped_column(String(10), default="completa")   # completa (página entera) | media
    titulo_portada: Mapped[str | None] = mapped_column(String(120))        # vacío: lo pone el sistema
    imagen: Mapped[bytes | None] = mapped_column(LargeBinary)              # ilustración de la portada
    imagen_nombre: Mapped[str | None] = mapped_column(String(160))
    paginas: Mapped[int | None] = mapped_column(Integer)               # páginas del Word, contadas con Word (3.7)
    estado: Mapped[str] = mapped_column(String(12), default="borrador")  # borrador | generada
    creada_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    generada_en: Mapped[datetime | None] = mapped_column(DateTime)
    secciones: Mapped[list["CartillaSeccion"]] = relationship(order_by="CartillaSeccion.orden", cascade="all, delete-orphan")
    items: Mapped[list["CartillaItem"]] = relationship(order_by="CartillaItem.posicion", cascade="all, delete-orphan")


class CartillaSeccion(Base):
    __tablename__ = "cartilla_seccion"
    id: Mapped[int] = mapped_column(primary_key=True)
    cartilla_id: Mapped[int] = mapped_column(ForeignKey("cartilla.id"))
    orden: Mapped[int] = mapped_column(Integer)
    titulo: Mapped[str] = mapped_column(String(80))
    materia: Mapped[str] = mapped_column(String(60))
    submateria: Mapped[str | None] = mapped_column(String(60))
    cantidad: Mapped[int] = mapped_column(Integer)
    mezclada: Mapped[bool] = mapped_column(Boolean, default=False)
    admitidas: Mapped[str | None] = mapped_column(Text)               # «Materia|Submateria» separadas por «;»
    dificultad: Mapped[str] = mapped_column(String(10), default="=")   # «=» usa la de la cartilla


class CartillaItem(Base):
    __tablename__ = "cartilla_item"
    id: Mapped[int] = mapped_column(primary_key=True)
    cartilla_id: Mapped[int] = mapped_column(ForeignKey("cartilla.id"))
    seccion_id: Mapped[int] = mapped_column(ForeignKey("cartilla_seccion.id"))
    ejercicio_id: Mapped[int] = mapped_column(ForeignKey("ejercicio.id"))
    posicion: Mapped[int] = mapped_column(Integer)                     # orden dentro de la cartilla
    letra_final: Mapped[str | None] = mapped_column(String(1))         # la que va al Excel, al generar
    ejercicio: Mapped["Ejercicio"] = relationship()


class CartillaExcluida(Base):
    """Cartillas anteriores cuyos ejercicios no se pueden repetir."""
    __tablename__ = "cartilla_excluida"
    id: Mapped[int] = mapped_column(primary_key=True)
    cartilla_id: Mapped[int] = mapped_column(ForeignKey("cartilla.id"))
    excluida_id: Mapped[int] = mapped_column(ForeignKey("cartilla.id"))
    automatica: Mapped[bool] = mapped_column(Boolean, default=False)   # emparejamiento de sesiones


class CartillaArchivo(Base):
    """El Word y el Excel generados: se guardan dentro de la base para que entren en la copia de seguridad."""
    __tablename__ = "cartilla_archivo"
    id: Mapped[int] = mapped_column(primary_key=True)
    cartilla_id: Mapped[int] = mapped_column(ForeignKey("cartilla.id"))
    tipo: Mapped[str] = mapped_column(String(5))          # docx | xlsx
    nombre: Mapped[str] = mapped_column(String(255))
    datos: Mapped[bytes] = mapped_column(LargeBinary)
    generado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


def crear_tablas():
    Base.metadata.create_all(Sesion.kw["bind"])
