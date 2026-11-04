"""Catálogos de fábrica, tomados del Estándar PRAXIS v1.2.

Son la única fuente de estos valores: con ellos se llena la base de datos la
primera vez y con ellos trabajan las pruebas del validador.
"""

GRADOS = [
    # (nombre, código, texto en la portada), en el orden en que se muestran
    ("3°", "33", "3°"),
    ("4°", "44", "4°"),
    ("5°", "55", "5°"),
    ("6°", "66", "6°"),
    ("7°", "77", "7°"),
    ("8°", "88", "8°"),
    ("9°", "99", "9°"),
    ("10°", "10", "10°"),
    ("11°", "11", "11°"),
    ("ICFES", "13", "Saber 11"),
]
GRADO_ICFES = "13"
GRADOS_PRIMARIA = {"33", "44", "55"}          # 3°, 4° y 5°


def orden_grado(codigo):
    """Posición del grado en GRADOS (3° … 11°, ICFES); los que se agreguen desde la aplicación van al final."""
    codigos = [c for _, c, _ in GRADOS]
    return codigos.index(codigo) if codigo in codigos else len(codigos)

# (nombre, código de simulacro especial o None, prefijo del código de ejercicio, color en la portada)
MATERIAS = [
    ("Matemáticas", "03", "MAT", "#3F6FB5"),
    ("Lengua Castellana", None, "LEN", "#B8860B"),     # LEN: Lengua Castellana sin submateria (3° a 5°)
    ("Ciencias Naturales", None, None, "#5E9632"),
    ("Ciencias Sociales", "06", "SOC", "#C8641E"),
    ("Filosofía", "07", "FIL", "#1F8A8A"),
    ("Inglés", "14", "ING", "#A0289A"),
    ("Informática", "15", "INF", "#6A4FB3"),
    ("Educación Física", "16", "EDF", "#C62828"),
    ("Educación Artística", "17", "ART", "#D2457F"),
    ("Religión", "18", "REL", "#8D5A2B"),
    ("Ética", "19", "ETI", "#2E7D5B"),
    ("Dibujo", "22", "DIB", "#4F6D7A"),
    ("Electricidad", "21", "ELE", "#1A3A6B"),
    ("Mecánica", "20", "MEC", "#555555"),
]

# (materia, submateria, código, prefijo)
SUBMATERIAS = [
    ("Matemáticas", "Matemáticas I", "01", "MA1"),
    ("Matemáticas", "Matemáticas II", "02", "MA2"),
    ("Lengua Castellana", "Español", "04", "ESP"),
    ("Lengua Castellana", "Comprensión Lectora", "05", "CLE"),
    ("Lengua Castellana", "Lectura Crítica", "23", "LCR"),
    ("Ciencias Naturales", "Biología", "09", "BIO"),
    ("Ciencias Naturales", "Física", "12", "FIS"),
    ("Ciencias Naturales", "Química", "13", "QUI"),
    ("Ciencias Naturales", "Tecnología y Medio Ambiente", "24", "TMA"),
    ("Ciencias Sociales", "Ciencias Económicas y Políticas", "08", "CEP"),
]

# Submateria obligatoria (True), opcional (None) o prohibida (False), por materia
SUBMATERIA_REGLA = {
    "Matemáticas": True,
    "Lengua Castellana": True,
    "Ciencias Naturales": True,
    "Ciencias Sociales": None,
}
# En 3°, 4° y 5° Matemáticas y Lengua Castellana van sin submateria (decisión del 21/09/2026);
# Ciencias Naturales y las demás siguen la regla general.
SUBMATERIA_REGLA_PRIMARIA = {"Matemáticas": False, "Lengua Castellana": False}


def regla_submateria(materia, grado):
    """True = obligatoria, None = opcional, False = va vacía; según la materia y el grado."""
    if grado in GRADOS_PRIMARIA and materia in SUBMATERIA_REGLA_PRIMARIA:
        return SUBMATERIA_REGLA_PRIMARIA[materia]
    return SUBMATERIA_REGLA.get(materia, False)

# Materias donde se aplica la regla de «x2 sin superíndice» (por materia o submateria)
MATERIAS_SUPERINDICE = {"Matemáticas", "Física", "Química", "Biología", "Tecnología y Medio Ambiente"}

AGRUPACIONES = [
    ("Todas las materias", "99"),
    ("M-L-N-S-I (Matemáticas, Español, Naturales, Sociales, Inglés)", "98"),
    ("Combinado especial", "97"),
    ("PARTE 1", "91"),
    ("PARTE 2", "92"),
    ("PARTE 2 con materia agregada (pedido especial)", "93"),
    ("PARTE 3", "94"),
    ("Mecánica (agrupación histórica)", "87"),
    ("Electricidad (agrupación histórica)", "88"),
    ("Dibujo (agrupación histórica)", "89"),
]

TIPOS_MATERIAL = [
    ("Simulacro / Periodo 1", "11"),
    ("Simulacro / Periodo 2", "22"),
    ("Simulacro / Periodo 3", "33"),
    ("Simulacro / Periodo 4", "44"),
    ("Simulacro especial", "55"),
    ("Sesión 1 – REAL ICFES", "71"),
    ("Sesión 2 – REAL ICFES", "72"),
]

NIVELES = {"Básico": "BB", "Medio": "MM", "Avanzado": "AA"}

# Pensamiento y competencia que corresponden a cada materia y submateria (07/10/2026).
# El pensamiento depende de la **submateria**, no solo de la materia: Biología es «Entorno vivo» y
# Física o Química son «Entorno físico»; Español es Literatura o Producción textual y Comprensión
# Lectora es Lectura crítica. La clave "*" vale para toda la materia.
PEDAGOGIA = {
    "Matemáticas": {"*": (
        ["Numérico-variacional", "Geométrico-métrico", "Aleatorio"],
        ["Comunicación y representación", "Razonamiento y argumentación", "Planteamiento y resolución de problemas"])},
    "Lengua Castellana": {
        "Español": (["Literatura", "Producción textual"],
                    ["Comprensión e interpretación de textos literarios",
                     "Reconocimiento y uso de la estructura de la oración"]),
        "Comprensión Lectora": (["Lectura crítica"],
                                ["Recupera información literal", "Comprende el sentido local mediante inferencias",
                                 "Comprende el sentido global mediante inferencias", "Asume una posición crítica"]),
        "Lectura Crítica": (["Lectura crítica"],            # la de ICFES; sigue a Comprensión Lectora
                            ["Recupera información literal", "Comprende el sentido local mediante inferencias",
                             "Comprende el sentido global mediante inferencias", "Asume una posición crítica"]),
    },
    "Ciencias Sociales": {"*": (
        ["Historia y cultura", "Relaciones espaciales y ambientales", "Relaciones ético-políticas"],
        ["Temporalidad", "Espacialidad", "Culturalidad", "Institucionalidad y derechos humanos"])},
    "Ciencias Naturales": {
        "Biología": (["Entorno vivo"], []),
        "Física": (["Entorno físico"], []),
        "Química": (["Entorno físico"], []),
        "Tecnología y Medio Ambiente": (["Entorno físico", "Entorno vivo"], []),
        "*": ([], ["Uso comprensivo del conocimiento científico", "Explicación de fenómenos", "Indagación"]),
    },
    "Inglés": {"*": (
        ["Lectura", "Conversación", "Escritura", "Escucha", "Monólogo"],
        ["Competencia lingüística", "Competencia pragmática", "Competencia sociolingüística"])},
}

# Derechos Básicos de Aprendizaje de Inglés de 6° (MEN), para que la IA no los invente
DBA_INGLES_6 = [
    "DBA 1: datos personales en una conversación",
    "DBA 2: rutinas y actividades cotidianas",
    "DBA 3: instrucciones de clase y de la comunidad",
    "DBA 4: deletrear y aclarar palabras",
    "DBA 5: describir personas, cosas y lugares",
    "DBA 6: información personal en formatos",
    "DBA 7: preguntas qué/quién/cuándo/dónde sobre un texto corto",
    "DBA 8: tema general de un texto corto con ayudas (imágenes, títulos, avisos)",
]


def pedagogia(materia, submateria=None):
    """(pensamientos, competencias) que corresponden a esa materia y submateria."""
    mapa = PEDAGOGIA.get(materia)
    if not mapa:
        return [], []
    propio = mapa.get(submateria or "", ("", ""))
    general = mapa.get("*", ([], []))
    pensamientos = list(propio[0]) or list(general[0])
    competencias = list(propio[1]) or list(general[1])
    return pensamientos, competencias

# Grupos de materias para una sección que mezcla varias, como la «SOCIALES Y CIUDADANAS» del ICFES.
# (nombre que se ofrece al armar la sección, materias que entran)
GRUPOS_MATERIA = [
    ("Sociales y ciudadanas", ["Ciencias Sociales", "Filosofía"]),
]


# Estructuras: clave, nombre, código de materia, editable, secciones
# sección: (título impreso, materia, submateria, cantidad, mezclada, combinaciones admitidas «Materia|Submateria»)
_M, _LC, _CN, _CS = "Matemáticas", "Lengua Castellana", "Ciencias Naturales", "Ciencias Sociales"
_P2 = [
    ("INFORMÁTICA", "Informática", None, 16, False, None),
    ("EDUCACIÓN FÍSICA", "Educación Física", None, 16, False, None),
    ("EDUCACIÓN ARTÍSTICA", "Educación Artística", None, 16, False, None),
    ("RELIGIÓN", "Religión", None, 16, False, None),
    ("ÉTICA", "Ética", None, 16, False, None),
]
ESTRUCTURAS = [
    ("E1", "Periódico PARTE 1 · 6° a 9°", "91", False, [
        ("MATEMÁTICAS I", _M, "Matemáticas I", 15, False, None),
        ("MATEMÁTICAS II", _M, "Matemáticas II", 15, False, None),
        ("LENGUA CASTELLANA", _LC, "Español", 14, False, None),
        ("COMPRENSIÓN LECTORA", _LC, "Comprensión Lectora", 12, False, None),
        ("CIENCIAS SOCIALES", _CS, None, 20, True, ["Ciencias Sociales|", "Ciencias Sociales|Ciencias Económicas y Políticas"]),
        ("BIOLOGÍA", _CN, "Biología", 12, False, None),
        ("FÍSICA", _CN, "Física", 12, False, None),
        ("QUÍMICA", _CN, "Química", 12, False, None),
        ("INGLÉS", "Inglés", None, 28, False, None),
    ]),
    ("E2", "Periódico PARTE 1 · 10° y 11°", "91", False, [
        ("MATEMÁTICAS I", _M, "Matemáticas I", 13, False, None),
        ("MATEMÁTICAS II", _M, "Matemáticas II", 13, False, None),
        ("LENGUA CASTELLANA", _LC, "Español", 14, False, None),
        ("COMPRENSIÓN LECTORA", _LC, "Comprensión Lectora", 10, False, None),
        ("CIENCIAS SOCIALES", _CS, None, 10, False, None),
        ("FILOSOFÍA", "Filosofía", None, 12, False, None),
        ("CIENCIAS ECONÓMICAS Y POLÍTICAS", _CS, "Ciencias Económicas y Políticas", 10, False, None),
        ("BIOLOGÍA", _CN, "Biología", 10, False, None),
        ("FÍSICA", _CN, "Física", 10, False, None),
        ("QUÍMICA", _CN, "Química", 10, False, None),
        ("INGLÉS", "Inglés", None, 28, False, None),
    ]),
    ("E3", "Periódico PARTE 2", "92", False, _P2),
    ("E4", "Libre · simulacros especiales", None, True, []),
    ("E5", "Simulacro ICFES · Sesión 1", "99", False, [
        ("MATEMÁTICAS", _M, None, 25, True, ["Matemáticas|Matemáticas I", "Matemáticas|Matemáticas II", "Matemáticas|"]),
        ("LECTURA CRÍTICA", _LC, "Lectura Crítica", 41, False, None),
        ("SOCIALES Y CIUDADANAS", _CS, None, 25, True, ["Ciencias Sociales|", "Ciencias Sociales|Ciencias Económicas y Políticas", "Filosofía|"]),
        ("CIENCIAS NATURALES", _CN, None, 29, True, ["Ciencias Naturales|Biología", "Ciencias Naturales|Física", "Ciencias Naturales|Química", "Ciencias Naturales|Tecnología y Medio Ambiente"]),
    ]),
    ("E6", "Simulacro ICFES · Sesión 2", "99", False, [
        ("MATEMÁTICAS", _M, None, 25, True, ["Matemáticas|Matemáticas I", "Matemáticas|Matemáticas II", "Matemáticas|"]),
        ("SOCIALES Y CIUDADANAS", _CS, None, 25, True, ["Ciencias Sociales|", "Ciencias Sociales|Ciencias Económicas y Políticas", "Filosofía|"]),
        ("CIENCIAS NATURALES", _CN, None, 29, True, ["Ciencias Naturales|Biología", "Ciencias Naturales|Física", "Ciencias Naturales|Química", "Ciencias Naturales|Tecnología y Medio Ambiente"]),
        ("INGLÉS", "Inglés", None, 55, False, None),
    ]),
    ("E7", "Periódico PARTE 3", "94", False, _P2 + [
        ("DIBUJO", "Dibujo", None, 12, False, None),
        ("ELECTRICIDAD", "Electricidad", None, 12, False, None),
        ("MECÁNICA", "Mecánica", None, 12, False, None),
    ]),
]

# Validador: listas editables desde la aplicación
EXCEPCIONES_SUPERINDICE = ["B12", "B6", "MP3", "MP4", "COVID19", "G20", "4G", "5G"]
# (frase, distingue mayúsculas)
FRASES_PROHIBIDAS = [
    ("Qué NO debe aparecer", True),
    ("Nota para", True),
    ("NOTA:", True),
    ("TODO", True),
    ("PENDIENTE", True),
    ("REVISAR", True),
    ("BORRAR", True),
]
