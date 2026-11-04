"""Lectura de los Word del banco, guardada en memoria.

Armar la vista previa o generar una cartilla obliga a leer decenas de archivos de carga. Como un archivo
del banco nunca cambia (para corregir un ejercicio se elimina y se vuelve a subir), su lectura se guarda
en memoria y se reutiliza mientras el sistema esté abierto.
"""
import hashlib

from app.semilla import catalogo_validacion
from app.validador import analizar

_LEIDOS = {}
MAXIMO = 400            # archivos distintos guardados a la vez


def _clave(datos):
    """Por el contenido del archivo: así nunca se confunde con otro, aunque cambie la base de datos."""
    return hashlib.blake2b(datos, digest_size=16).digest()


def leer(archivo_id, datos, nombre):
    """Devuelve el archivo ya analizado (estructura, estilos e imágenes), leyéndolo solo la primera vez."""
    clave = _clave(datos)
    if clave in _LEIDOS:
        return _LEIDOS[clave]
    v = analizar(datos, nombre, catalogo_validacion())
    if len(_LEIDOS) >= MAXIMO:
        _LEIDOS.pop(next(iter(_LEIDOS)))
    _LEIDOS[clave] = v
    return v


def olvidar(datos=None):
    """Se llama al eliminar un ejercicio del banco; sin argumento, limpia todo."""
    if datos is None:
        _LEIDOS.clear()
    else:
        _LEIDOS.pop(_clave(datos), None)
