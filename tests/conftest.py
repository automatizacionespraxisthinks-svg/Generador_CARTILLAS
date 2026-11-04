"""Cada archivo de pruebas trabaja sobre su propia base temporal, para no pisarse entre sí."""
import os

import pytest

os.environ.setdefault("PRAXIS_SIN_WORD", "1")      # las pruebas no abren Word para contar páginas

from app.bd import usar_base
from app.semilla import poblar


@pytest.fixture(scope="module", autouse=True)
def base_temporal(tmp_path_factory, request):
    carpeta = tmp_path_factory.mktemp(request.module.__name__.split(".")[-1])
    usar_base(f"sqlite:///{(carpeta / 'praxis.db').as_posix()}")
    poblar()
    yield
