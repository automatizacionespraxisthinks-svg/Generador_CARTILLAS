import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DATOS = Path(os.environ.get("PRAXIS_DATOS", RAIZ / "datos"))
DATOS.mkdir(parents=True, exist_ok=True)

# En el servidor basta con cambiar esta variable a una URL de PostgreSQL.
URL_BD = os.environ.get("PRAXIS_BD", f"sqlite:///{(DATOS / 'praxis.db').as_posix()}")

PLANTILLAS = RAIZ / "plantillas"
DOCS = RAIZ / "docs"
WEB = Path(__file__).resolve().parent / "web"
