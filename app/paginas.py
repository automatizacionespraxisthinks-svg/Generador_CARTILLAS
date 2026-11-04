"""Conteo de páginas de la cartilla con Microsoft Word (Estándar 3.7).

La impresión tipo folleto necesita un múltiplo de 4 páginas. Word es el único que sabe cuántas páginas
ocupa el documento, así que se abre el Word generado, se repagina y se le pregunta.

El conteo corre en un proceso aparte: si Word no está instalado, se queda colgado o falla, el sistema
sigue funcionando y simplemente informa que no pudo contar.
"""
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ESPERA = 180          # segundos; abrir Word y repaginar toma unos pocos


def faltan_para_multiplo(paginas, multiplo=4):
    """Páginas que faltan para el siguiente múltiplo (0 si ya lo es)."""
    if not paginas:
        return None
    return (-int(paginas)) % multiplo


def contar(datos: bytes, intentos=2):
    """Páginas del .docx, o None si no se pudo contar (sin Word, con error o demorado).

    Se intenta dos veces: si Word estaba arrancando u ocupado, el primer intento puede fallar.
    """
    if os.environ.get("PRAXIS_SIN_WORD") == "1":
        return None
    with tempfile.TemporaryDirectory() as carpeta:
        ruta = Path(carpeta) / "cartilla.docx"
        ruta.write_bytes(datos)
        for intento in range(intentos):
            try:
                r = subprocess.run([sys.executable, "-m", "app.paginas", str(ruta)],
                                   capture_output=True, text=True, timeout=ESPERA, cwd=str(RAIZ))
            except (subprocess.TimeoutExpired, OSError):
                return None
            salida = (r.stdout or "").strip()
            if r.returncode == 0 and salida.isdigit():
                return int(salida)
            if intento + 1 < intentos:
                time.sleep(2)
        return None


def _contar_con_word(ruta):
    """Se ejecuta en el proceso aparte: abre el documento en Word y devuelve el número de páginas."""
    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()
    word = doc = None
    try:
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0
        doc = word.Documents.Open(str(ruta), ReadOnly=True, AddToRecentFiles=False, OpenAndRepair=False,
                                  ConfirmConversions=False)
        doc.Repaginate()
        return int(doc.ComputeStatistics(2))          # wdStatisticPages
    finally:
        if doc is not None:
            doc.Close(False)
        if word is not None:
            word.Quit()
        pythoncom.CoUninitialize()


if __name__ == "__main__":
    print(_contar_con_word(sys.argv[1]))
