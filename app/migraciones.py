"""Versión del esquema de la base de datos.

Desde la fase 2 el banco guarda datos reales, así que ningún cambio de estructura
puede borrarlos. Cada cambio futuro se agrega aquí como un paso numerado, que se
aplica una sola vez al arrancar el sistema.
"""
from sqlalchemy import Integer, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Mapped, mapped_column

from app.bd import Base, Sesion

VERSION_ACTUAL = 9

# «Materia|Submateria» que admite la sección CIENCIAS SOCIALES de 6° a 9° (ver app/catalogos_base.py)
ADMITE_SOCIALES_SQL = "Ciencias Sociales|;Ciencias Sociales|Ciencias Económicas y Políticas"

# versión -> lista de sentencias SQL que llevan la base desde la versión anterior
MIGRACIONES: dict[int, list[str]] = {
    3: [],   # fase 3: tablas nuevas de cartillas (las crea create_all; no hay columnas que migrar)
    4: [],   # fase 4: tabla de archivos generados
    5: [     # glosario por pregunta y casilla «Incluir glosario» de la cartilla
        "ALTER TABLE ejercicio ADD COLUMN glosario TEXT NOT NULL DEFAULT '[]'",
        "ALTER TABLE cartilla ADD COLUMN glosario BOOLEAN NOT NULL DEFAULT FALSE",
    ],
    6: [     # grados 3°, 4° y 5°; prefijo LEN para Lengua Castellana sin submateria (primaria)
        "INSERT INTO grado (nombre, codigo, texto_portada) SELECT '3°', '33', '3°' WHERE NOT EXISTS (SELECT 1 FROM grado WHERE codigo = '33')",
        "INSERT INTO grado (nombre, codigo, texto_portada) SELECT '4°', '44', '4°' WHERE NOT EXISTS (SELECT 1 FROM grado WHERE codigo = '44')",
        "INSERT INTO grado (nombre, codigo, texto_portada) SELECT '5°', '55', '5°' WHERE NOT EXISTS (SELECT 1 FROM grado WHERE codigo = '55')",
        "UPDATE materia SET prefijo = 'LEN' WHERE nombre = 'Lengua Castellana' AND (prefijo IS NULL OR prefijo = '')",
    ],
    7: [     # páginas de la cartilla, para el ajuste a múltiplo de 4
        "ALTER TABLE cartilla ADD COLUMN paginas INTEGER",
    ],
    8: [     # en 6° a 9° CIENCIAS SOCIALES admite la materia completa, con o sin submateria
        "UPDATE estructura_seccion SET mezclada = 1, admitidas = '" + ADMITE_SOCIALES_SQL + "' "
        "WHERE titulo = 'CIENCIAS SOCIALES' AND estructura_id = (SELECT id FROM estructura WHERE clave = 'E1')",
        "UPDATE cartilla_seccion SET mezclada = 1, admitidas = '" + ADMITE_SOCIALES_SQL + "' "
        "WHERE titulo = 'CIENCIAS SOCIALES' AND submateria IS NULL "
        "AND cartilla_id IN (SELECT id FROM cartilla WHERE estructura = 'E1')",
    ],
    9: [     # portada completa o media, con título e ilustración propios de cada cartilla
        "ALTER TABLE cartilla ADD COLUMN portada VARCHAR(10) NOT NULL DEFAULT 'completa'",
        "ALTER TABLE cartilla ADD COLUMN titulo_portada VARCHAR(120)",
        "ALTER TABLE cartilla ADD COLUMN imagen BLOB",
        "ALTER TABLE cartilla ADD COLUMN imagen_nombre VARCHAR(160)",
    ],
}


class VersionEsquema(Base):
    __tablename__ = "version_esquema"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version: Mapped[int] = mapped_column(Integer)


def aplicar():
    Base.metadata.create_all(Sesion.kw["bind"])
    with Sesion() as s:
        fila = s.get(VersionEsquema, 1)
        if fila is None:
            s.add(VersionEsquema(id=1, version=VERSION_ACTUAL))
            s.commit()
            return VERSION_ACTUAL
        for v in range(fila.version + 1, VERSION_ACTUAL + 1):
            for sentencia in MIGRACIONES.get(v, []):
                try:
                    s.execute(text(sentencia))
                    s.commit()
                except OperationalError as e:
                    # la columna ya existe (base creada con el modelo nuevo): el paso ya está hecho
                    s.rollback()
                    if "duplicate column" not in str(e).lower() and "already exists" not in str(e).lower():
                        raise
            fila = s.get(VersionEsquema, 1)
            fila.version = v
            s.commit()
        return fila.version
