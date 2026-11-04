from .catalogo import CatalogoValidacion
from .resultado import ACEPTADO, PENDIENTE, RECHAZADO, Resultado
from .validador import analizar, validar

__all__ = ["validar", "analizar", "CatalogoValidacion", "Resultado", "ACEPTADO", "RECHAZADO", "PENDIENTE"]
