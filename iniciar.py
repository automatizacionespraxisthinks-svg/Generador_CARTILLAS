"""Arranca el Generador de cartillas y abre el navegador.

Uso:  .venv\Scripts\python iniciar.py
"""
import threading
import webbrowser

import uvicorn

PUERTO = 8765

if __name__ == "__main__":
    threading.Timer(1.5, lambda: webbrowser.open(f"http://127.0.0.1:{PUERTO}/#cargar")).start()
    uvicorn.run("app.main:app", host="127.0.0.1", port=PUERTO)
