"""Revisa que los elementos de formato del Word generado estén en el orden que exige el esquema de Word
(ECMA-376). Word suele tolerar el desorden, pero otro programa o una versión futura podría no hacerlo."""
import io
import zipfile

from lxml import etree

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

SECUENCIAS = {
    "pPr": ["pStyle", "keepNext", "keepLines", "pageBreakBefore", "framePr", "widowControl", "numPr",
            "suppressLineNumbers", "pBdr", "shd", "tabs", "suppressAutoHyphens", "kinsoku", "wordWrap", "overflowPunct",
            "topLinePunct", "autoSpaceDE", "autoSpaceDN", "bidi", "adjustRightInd", "snapToGrid", "spacing", "ind",
            "contextualSpacing", "mirrorIndents", "suppressOverlap", "jc", "textDirection", "textAlignment",
            "textboxTightWrap", "outlineLvl", "divId", "cnfStyle", "rPr", "sectPr", "pPrChange"],
    "rPr": ["ins", "del", "moveFrom", "moveTo", "rStyle", "rFonts", "b", "bCs", "i", "iCs", "caps", "smallCaps", "strike",
            "dstrike", "outline", "shadow", "emboss", "imprint", "noProof", "snapToGrid", "vanish", "webHidden", "color",
            "spacing", "w", "kern", "position", "sz", "szCs", "highlight", "u", "effect", "bdr", "shd", "fitText",
            "vertAlign", "rtl", "cs", "em", "lang", "eastAsianLayout", "specVanish", "oMath", "rPrChange"],
    "tblPr": ["tblStyle", "tblpPr", "tblOverlap", "bidiVisual", "tblStyleRowBandSize", "tblStyleColBandSize", "tblW", "jc",
              "tblCellSpacing", "tblInd", "tblBorders", "shd", "tblLayout", "tblCellMar", "tblLook", "tblCaption",
              "tblDescription", "tblPrChange"],
    "tcPr": ["cnfStyle", "tcW", "gridSpan", "hMerge", "vMerge", "tcBorders", "shd", "noWrap", "tcMar", "textDirection",
             "tcFitText", "vAlign", "hideMark", "headers", "cellIns", "cellDel", "cellMerge", "tcPrChange"],
    "sectPr": ["headerReference|footerReference", "footnotePr", "endnotePr", "type", "pgSz", "pgMar", "paperSrc",
               "pgBorders", "lnNumType", "pgNumType", "cols", "formProt", "vAlign", "noEndnote", "titlePg",
               "textDirection", "bidi", "rtlGutter", "docGrid", "printerSettings", "sectPrChange"],
    "tblBorders": ["top", "left|start", "bottom", "right|end", "insideH", "insideV"],
    "tblCellMar": ["top", "left|start", "bottom", "right|end"],
}


def _indice(secuencia, nombre):
    for i, s in enumerate(secuencia):
        if nombre in s.split("|"):
            return i
    return None


def desordenes(datos, parte="word/document.xml"):
    """[(contenedor, hijos en orden actual)] donde el orden no respeta el esquema."""
    raiz = etree.fromstring(zipfile.ZipFile(io.BytesIO(datos)).read(parte))
    malos = []
    for nombre, secuencia in SECUENCIAS.items():
        for el in raiz.iter(f"{{{W}}}{nombre}"):
            hijos = [h.tag.split("}")[1] for h in el if isinstance(h.tag, str) and h.tag.startswith(f"{{{W}}}")]
            pos = [_indice(secuencia, h) for h in hijos]
            conocidos = [p for p in pos if p is not None]
            if conocidos != sorted(conocidos):
                malos.append((nombre, hijos))
    return malos
