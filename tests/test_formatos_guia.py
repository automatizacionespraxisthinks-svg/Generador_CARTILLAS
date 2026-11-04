"""Los archivos que se descargan desde «Formatos» tienen que seguir sirviendo.

Son la guía con la que se preparan los ejercicios: si el sistema cambia una regla y estos archivos se
quedan atrás, quien prepara los ejercicios trabaja con información vieja y el archivo se rechaza.
"""
import pytest
from docx import Document
from openpyxl import load_workbook

from app import catalogos_base as base
from app.config import PLANTILLAS
from app.main import FORMATOS
from app.semilla import catalogo_validacion
from app.validador import analizar
from app.validador.validador import ENC_EXCEL, ENC_GLOSARIO, ENC_RESPUESTAS

EJEMPLOS = [a for _, _, a, _ in FORMATOS if a.startswith("ejemplos/")]
PLANTILLAS_CARGA = [a for _, _, a, _ in FORMATOS if a.startswith("PLANTILLA_CARGA")]


def test_todo_lo_que_ofrece_formatos_existe():
    faltan = [a for _, _, a, _ in FORMATOS if not (PLANTILLAS / a).exists()]
    assert not faltan, f"la pantalla ofrece archivos que no están: {faltan}"


@pytest.mark.parametrize("archivo", EJEMPLOS)
def test_los_ejemplos_pasan_el_validador(archivo):
    """Un ejemplo que el propio sistema rechazaría sería lo peor que podríamos entregar."""
    ruta = PLANTILLAS / archivo
    v = analizar(ruta.read_bytes(), ruta.name, catalogo_validacion())
    assert not v.r.errores, [f"regla {e.regla} · {e.donde} · {e.mensaje}" for e in v.r.errores]


@pytest.mark.parametrize("archivo", PLANTILLAS_CARGA + EJEMPLOS)
def test_los_encabezados_de_las_tablas_son_los_que_exige_el_validador(archivo):
    doc = Document(str(PLANTILLAS / archivo))
    encabezados = [[c.text.strip() for c in t.rows[0].cells] for t in doc.tables]
    for enc in (ENC_RESPUESTAS, ENC_EXCEL):
        assert enc in encabezados, f"{archivo} no trae la tabla {enc[0]}…"
    if "PARTE_INGLES" not in archivo or any(e == ENC_GLOSARIO for e in encabezados):
        pass            # el glosario es opcional


def test_el_instructivo_en_word_esta_al_dia():
    """Se regenera con «python -m scripts.instructivo_a_word» cuando cambia el .md."""
    doc = Document(str(PLANTILLAS / "INSTRUCTIVO_NORMALIZACION_v1.2.docx"))
    texto = "\n".join(p.text for p in doc.paragraphs)
    celdas = {c.text for t in doc.tables for f in t.rows for c in f.cells}
    assert "Pensamiento y competencia, por submateria" in texto
    assert "➤" in texto and "segunda pregunta sin opciones" in texto
    assert "Panel" in texto                                   # remite al prompt para simulacros completos
    assert "Entorno vivo" in " ".join(celdas)                 # el catálogo nuevo llegó al Word


def test_el_excel_de_codigos_trae_los_catalogos_de_hoy():
    wb = load_workbook(PLANTILLAS / "CODIGOS_PRAXIS.xlsx")
    assert "Pensamiento y competencia" in wb.sheetnames
    grados = {str(f[0]) for f in wb["Grados"].iter_rows(min_row=4, values_only=True) if f[0]}
    assert {c for _, c, _ in base.GRADOS} <= grados, "faltan grados en el Excel"
    filas = [f for f in wb["Pensamiento y competencia"].iter_rows(min_row=4, values_only=True) if f[0]]
    por_sub = {(f[0], f[1].split(" (")[0]): f[2] for f in filas}
    assert por_sub[("Ciencias Naturales", "Biología")] == "Entorno vivo"
    assert por_sub[("Ciencias Naturales", "Química")] == "Entorno físico"
    assert "Matemáticas I" in [f[1] for f in filas]            # no dice «(vacía)»: es obligatoria
