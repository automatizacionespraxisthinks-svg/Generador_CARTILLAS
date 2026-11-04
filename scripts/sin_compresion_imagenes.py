"""Activa «No comprimir las imágenes del archivo» en las plantillas y ejemplos de carga.

Word, por defecto, reduce las imágenes a 220 ppp al guardar; con esta opción
(guardada dentro de cada documento) conserva los 300 ppp que exige el estándar.

Uso:  python scripts/sin_compresion_imagenes.py
"""
import zipfile
from pathlib import Path

from lxml import etree

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
# Elementos de w:settings que el esquema ubica DESPUÉS de doNotAutoCompressPictures
POSTERIORES = ["forceUpgrade", "captions", "readModeInkLockDown", "smartTagType", "schemaLibrary",
               "shapeDefaults", "doNotEmbedSmartTags", "decimalSymbol", "listSeparator"]
RAIZ = Path(__file__).resolve().parent.parent


def aplicar(ruta: Path):
    with zipfile.ZipFile(ruta) as z:
        partes = {n: z.read(n) for n in z.namelist()}
    settings = etree.fromstring(partes["word/settings.xml"])
    if settings.find(f"{{{W}}}doNotAutoCompressPictures") is not None:
        return False
    nuevo = etree.Element(f"{{{W}}}doNotAutoCompressPictures")
    siguiente = next((h for h in settings if etree.QName(h).localname in POSTERIORES), None)
    if siguiente is not None:
        siguiente.addprevious(nuevo)
    else:
        settings.append(nuevo)
    partes["word/settings.xml"] = etree.tostring(settings, xml_declaration=True, encoding="UTF-8", standalone=True)
    with zipfile.ZipFile(ruta, "w", zipfile.ZIP_DEFLATED) as z:
        for n, datos in partes.items():
            z.writestr(n, datos)
    return True


if __name__ == "__main__":
    for ruta in sorted((RAIZ / "plantillas").glob("PLANTILLA_CARGA_*_v1.2.docx")) + sorted((RAIZ / "plantillas" / "ejemplos").glob("*.docx")):
        print(("activada  " if aplicar(ruta) else "ya estaba ") + ruta.name)
