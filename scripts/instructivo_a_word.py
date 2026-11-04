"""Convierte el instructivo de normalización (Markdown) a Word, para descargarlo desde el sistema.

Uso:  python scripts/instructivo_a_word.py
"""
from pathlib import Path

import markdown
import win32com.client

RAIZ = Path(__file__).resolve().parent.parent
ORIGEN = RAIZ / "docs" / "INSTRUCTIVO_NORMALIZACION_v1.2.md"
DESTINO = RAIZ / "plantillas" / "INSTRUCTIVO_NORMALIZACION_v1.2.docx"

ESTILO = """<style>
body{font-family:Tahoma;font-size:10pt}
h1{font-size:16pt;color:#1F3A68} h2{font-size:12pt;color:#1F3A68;margin-top:14pt}
table{border-collapse:collapse} td,th{border:0.5pt solid #000;padding:3pt 5pt;font-size:9pt;vertical-align:top}
th{background:#E2EFD7} code{font-family:Consolas;font-size:9pt}
</style>"""

html = markdown.markdown(ORIGEN.read_text(encoding="utf-8"), extensions=["tables"])
tmp = DESTINO.with_suffix(".html")
tmp.write_text(f"<html><head><meta charset='utf-8'>{ESTILO}</head><body>{html}</body></html>", encoding="utf-8")
w = win32com.client.DispatchEx("Word.Application")
w.Visible = False
try:
    d = w.Documents.Open(str(tmp))
    d.PageSetup.TopMargin = d.PageSetup.BottomMargin = d.PageSetup.LeftMargin = d.PageSetup.RightMargin = 36
    d.SaveAs2(str(DESTINO), FileFormat=16)
    d.Close(False)
finally:
    w.Quit()
    tmp.unlink(missing_ok=True)
print("listo:", DESTINO.name)
