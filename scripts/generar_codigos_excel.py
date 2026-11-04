"""Genera plantillas/CODIGOS_PRAXIS.xlsx con los códigos del sistema, tomados de los catálogos de fábrica.

Hojas: código de cartilla, grados, materias y agrupaciones, tipos de material, plantillas de respuestas
y código de ejercicio. Si se agregan catálogos, se vuelve a correr y queda al día.

Uso:  python scripts/generar_codigos_excel.py
"""
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from app import catalogos_base as base           # noqa: E402
from app.semilla import leer_plantillas          # noqa: E402

DESTINO = RAIZ / "plantillas" / "CODIGOS_PRAXIS.xlsx"
VERDE = "E2EFD7"
GRIS = "F2F4F1"


def hoja(wb, titulo, intro, encabezados, filas, anchos, primera=None):
    h = wb.create_sheet(titulo)
    h["A1"] = titulo
    h["A1"].font = Font(bold=True, size=14)
    h["A2"] = intro
    h["A2"].alignment = Alignment(wrap_text=True, vertical="top")
    h.merge_cells(start_row=2, start_column=1, end_row=3, end_column=max(len(encabezados), 3))
    fila0 = 5
    for i, enc in enumerate(encabezados, 1):
        c = h.cell(row=fila0, column=i, value=enc)
        c.font = Font(bold=True)
        c.fill = PatternFill("solid", fgColor=VERDE)
        c.alignment = Alignment(vertical="center")
    for j, fila in enumerate(filas, fila0 + 1):
        for i, valor in enumerate(fila, 1):
            c = h.cell(row=j, column=i, value=valor)
            c.alignment = Alignment(wrap_text=i > 1 and isinstance(valor, str) and len(valor) > 40, vertical="top")
            if i == 1 and primera == "codigo":
                c.font = Font(name="Consolas")
    for i, ancho in enumerate(anchos, 1):
        h.column_dimensions[get_column_letter(i)].width = ancho
    h.freeze_panes = h.cell(row=fila0 + 1, column=1)
    return h


def construir():
    wb = Workbook()
    wb.remove(wb.active)

    # ---------------------------------------------------------------- cartilla
    pares = [
        ("GG", "Grado", "33, 44, 55, 66, 77, 88, 99, 10, 11, 13", "Hoja «Grados»"),
        ("MM", "Materia o agrupación", "01–49 materias · 87–99 agrupaciones y partes", "Hoja «Materias y agrupaciones»"),
        ("TT", "Tipo de material", "11, 22, 33, 44, 55, 71, 72", "Hoja «Tipos de material»"),
        ("PP", "Plantilla de respuestas", "01, 02, 03, 04, 05", "Hoja «Plantillas de respuestas»"),
        ("VV", "Versión", "01 la primera; sube si se repiten grado, materia, tipo y plantilla", "El sistema propone la siguiente libre"),
    ]
    h = hoja(wb, "Código de cartilla",
             "Diez dígitos, cinco pares: GG MM TT PP VV. El sistema verifica que cada par exista en su catálogo, que "
             "coincida con lo elegido en pantalla y que el código no se haya usado antes. La sesión no es un par aparte: "
             "en los periódicos, 91 es la sesión 1 y 92, 93 o 94 la sesión 2; en el ICFES real, 71 y 72.",
             ["Par", "Qué es", "Valores", "Dónde ver la lista"],
             [[p, q, v, d] for p, q, v, d in pares], [8, 26, 46, 34], primera="codigo")
    inicio = h.max_row + 2
    h.cell(row=inicio, column=1, value="Ejemplos").font = Font(bold=True)
    ejemplos = [
        ("1199330101", "11°", "Todas las materias", "Periodo 3", "Plantilla 1", "Versión 1"),
        ("3391110101", "3°", "PARTE 1", "Periodo 1", "Plantilla 1", "Versión 1"),
        ("7792220102", "7°", "PARTE 2", "Periodo 2", "Plantilla 1", "Versión 2"),
        ("1399710301", "ICFES", "Todas las materias", "Sesión 1 – REAL ICFES", "Plantilla 3", "Versión 1"),
        ("7703550101", "7°", "Matemáticas (simulacro especial)", "Simulacro especial", "Plantilla 1", "Versión 1"),
    ]
    for i, enc in enumerate(["Código", "Grado", "Materia", "Tipo de material", "Plantilla", "Versión"], 1):
        c = h.cell(row=inicio + 1, column=i, value=enc)
        c.font = Font(bold=True)
        c.fill = PatternFill("solid", fgColor=GRIS)
    for j, fila in enumerate(ejemplos, inicio + 2):
        for i, valor in enumerate(fila, 1):
            c = h.cell(row=j, column=i, value=valor)
            if i == 1:
                c.font = Font(name="Consolas")

    # ---------------------------------------------------------------- grados
    hoja(wb, "Grados",
         "El primer par del código de la cartilla y el grado del código de ejercicio. En 3°, 4° y 5°, Matemáticas y "
         "Lengua Castellana van sin submateria; Ciencias Naturales sí lleva submateria.",
         ["Código", "Grado", "Se imprime en la portada", "Submateria de Matemáticas y Lengua Castellana"],
         [[c, n, t, "No va" if c in base.GRADOS_PRIMARIA else ("Opcional en Matemáticas" if c == base.GRADO_ICFES else "Obligatoria")]
          for n, c, t in base.GRADOS], [10, 12, 24, 44], primera="codigo")

    # ---------------------------------------------------------------- materias
    subs = {}
    for materia, sub, codigo, prefijo in base.SUBMATERIAS:
        subs.setdefault(materia, []).append((sub, codigo, prefijo))
    filas = [[c, n, "Agrupación o parte", "", ""] for n, c in base.AGRUPACIONES]
    for nombre, codigo, prefijo, _ in base.MATERIAS:
        filas.append([codigo or "", nombre, "Materia", "", prefijo or ""])
        for sub, cod_sub, pre_sub in subs.get(nombre, []):
            filas.append([cod_sub or "", sub, "Submateria", nombre, pre_sub])
    hoja(wb, "Materias y agrupaciones",
         "Segundo par del código de la cartilla. Las agrupaciones (87–99) se usan en los simulacros de varias materias; "
         "el código de una materia o submateria se usa cuando el simulacro es solo de ella. Los códigos 10 y 11 se saltan "
         "a propósito, para que ninguna materia se lea igual que un grado; el rango 25–49 queda libre. La columna "
         "«Prefijo» es la que lleva el código del ejercicio.",
         ["Código", "Nombre", "Qué es", "Materia a la que pertenece", "Prefijo del ejercicio"],
         filas, [10, 42, 20, 26, 20], primera="codigo")

    # ---------------------------------------------------------------- pensamiento y competencia
    filas = []
    subs_de = {}
    for m, sub, *_ in base.SUBMATERIAS:
        subs_de.setdefault(m, []).append(sub)
    for materia, mapa in base.PEDAGOGIA.items():
        propias = [k for k in mapa if k != "*"]
        # si el pensamiento vale para toda la materia, se listan igual sus submaterias reales
        for sub in propias or subs_de.get(materia) or [""]:
            pens, comps = base.pedagogia(materia, sub or None)
            regla = base.SUBMATERIA_REGLA.get(materia)
            etiqueta = sub or "(va vacía)"
            if sub and regla is None:
                etiqueta += " (o vacía)"
            filas.append([materia, etiqueta, " · ".join(pens), " · ".join(comps)])
    hoja(wb, "Pensamiento y competencia",
         "Lo que va en esas dos columnas de la TABLA DE EXCEL del archivo de carga. El pensamiento depende de la "
         "**submateria**, no solo de la materia: Biología es «Entorno vivo» y Física o Química son «Entorno físico». "
         "En las materias que no están aquí (Filosofía, Informática, Educación Física, Religión, Ética, Educación "
         "Artística, Dibujo, Electricidad y Mecánica) son libres: se usan los del plan de área, o se dejan vacíos. "
         "El DBA se toma de la malla del grado y se escribe «DBA 4».",
         ["Materia", "Submateria", "Pensamiento", "Competencia"], filas, [22, 26, 42, 60])

    # ---------------------------------------------------------------- tipos
    hoja(wb, "Tipos de material",
         "Tercer par del código. Los tipos 71 y 72 son las dos sesiones del simulacro ICFES real y solo se usan con el grado 13.",
         ["Código", "Tipo de material"], [[c, n] for n, c in base.TIPOS_MATERIAL], [10, 40], primera="codigo")

    # ---------------------------------------------------------------- plantillas
    secuencias = leer_plantillas()
    filas = [[i] + [secuencias[n][i - 1] for n in range(1, 6)] for i in range(1, 141)]
    hoja(wb, "Plantillas de respuestas",
         "Cuarto par del código. La plantilla decide en qué letra queda la respuesta correcta de cada posición: la "
         "pregunta 1 de una cartilla con plantilla 2 tiene su respuesta correcta en la letra que dice la fila 1 de esa "
         "columna. Son 140 posiciones, el máximo de preguntas de una cartilla.",
         ["Posición", "Plantilla 1", "Plantilla 2", "Plantilla 3", "Plantilla 4", "Plantilla 5"],
         filas, [10, 12, 12, 12, 12, 12])

    # ---------------------------------------------------------------- ejercicio
    filas = []
    for nombre, codigo, prefijo, _ in base.MATERIAS:
        if prefijo:
            filas.append([prefijo, nombre + (" (sin submateria)" if nombre in ("Matemáticas", "Lengua Castellana") else "")])
        for sub, cod_sub, pre_sub in subs.get(nombre, []):
            filas.append([pre_sub, sub])
    hoja(wb, "Código de ejercicio",
         "Lo asigna el banco al guardar cada pregunta: PRE-GG-NNNNNN, por ejemplo MAT-33-000012. PRE es el prefijo de la "
         "submateria, o de la materia si no tiene; GG es el código del grado; NNNNNN es un consecutivo por prefijo y "
         "grado, que nunca se reutiliza aunque el ejercicio se elimine. Un bloque de lectura o una parte de Inglés recibe "
         "además su propio código con una B antes del consecutivo (CLE-77-B00012), y cada pregunta de adentro conserva el suyo.",
         ["Prefijo", "Materia o submateria"], filas, [12, 46], primera="codigo")

    wb.save(DESTINO)
    return DESTINO


if __name__ == "__main__":
    ruta = construir()
    print("listo:", ruta.relative_to(RAIZ))
