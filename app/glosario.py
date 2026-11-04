"""Glosario corto por pregunta (Estándar 2.7B y 3.5B).

Viene en la TABLA DE GLOSARIO del archivo de carga, se guarda con cada ejercicio y
solo se imprime si la cartilla tiene marcada la casilla «Incluir glosario».

**Fórmulas (07/10/2026).** El glosario admite superíndices, subíndices y ecuaciones de Word: en
Matemáticas y en Ciencias un significado sin fórmula muchas veces no dice nada («i² = −1» escrito como
«i2 = −1» es otra cosa). Por eso, además del texto, se guarda **cómo está escrito**: una lista de partes,
cada una con su texto y, si la lleva, su posición (superíndice o subíndice) o su ecuación.

El texto plano se sigue guardando aparte, porque es con lo que se busca, se mide el largo y se comprueba
que el término aparezca en la pregunta.
"""
import html
import json

from lxml import etree

from app import mathml

NS_M = "http://schemas.openxmlformats.org/officeDocument/2006/math"


def terminos(ejercicio):
    """[{"termino", "significado", "formato"?}] del ejercicio, en el orden del archivo de carga."""
    try:
        return json.loads(ejercicio.glosario or "[]")
    except (TypeError, ValueError):
        return []


def significado(texto):
    """El significado se imprime como una frase: si no termina en punto, el sistema se lo pone."""
    texto = (texto or "").strip()
    return texto if texto[-1:] in (".", "!", "?", "…") else texto + "."


# ====================================================================== lectura del archivo de carga
def partes_de_celda(parrafos):
    """Las partes de una celda del glosario: su texto, sus superíndices y sus ecuaciones, en orden.

    Recibe los párrafos tal como los leyó el validador. Si la celda es texto corriente, devuelve una
    sola parte sin formato, y entonces no hace falta guardarla.
    """
    partes = []
    for p in parrafos:
        for f in getattr(p, "fragmentos", []):
            if getattr(f, "omml", None) is not None:
                partes.append({"omml": etree.tostring(f.omml, encoding="unicode")})
            elif f.texto:
                vert = getattr(f.fmt, "vert", None)
                parte = {"t": f.texto}
                if vert in ("superscript", "subscript"):
                    parte["v"] = "sup" if vert == "superscript" else "sub"
                partes.append(parte)
    return _juntar(partes)


def _juntar(partes):
    """Une las partes seguidas que se escriben igual, para no guardar una por cada trozo de Word."""
    out = []
    for parte in partes:
        if out and "omml" not in parte and "omml" not in out[-1] and parte.get("v") == out[-1].get("v"):
            out[-1] = {**out[-1], "t": out[-1]["t"] + parte["t"]}
        else:
            out.append(parte)
    return out


def _partes_de(entrada, campo, texto_plano):
    """Cómo se escribe ese campo: lo guardado si lleva fórmula, o el texto corriente."""
    guardado = (entrada.get("formato") or {}).get(campo)
    if guardado:
        return guardado
    return [{"t": texto_plano}] if texto_plano else []


def ecuacion(parte):
    """El elemento m:oMath de una parte, listo para insertarlo en el Word de la cartilla."""
    try:
        return etree.fromstring(parte["omml"])
    except (KeyError, etree.XMLSyntaxError):
        return None


def texto_de_parte(parte):
    """Lo que se lee de una parte cuando no se puede dibujar la fórmula (la vista previa en pantalla)."""
    if "omml" in parte:
        el = ecuacion(parte)
        return "".join(t.text or "" for t in el.iter(f"{{{NS_M}}}t")) if el is not None else ""
    return parte.get("t", "")


# ====================================================================== impresión
def partes(lista):
    """Las partes del párrafo impreso: «Glosario: término: significado. término: …».

    Cada una es (texto, negrita, cursiva, posición, ecuación): la posición es «sup», «sub» o None, y la
    ecuación es el elemento de Word cuando la parte es una fórmula.
    """
    out = [("Glosario: ", False, False, None, None)]
    for i, t in enumerate(lista):
        trozos_t = _partes_de(t, "termino", t.get("termino", ""))
        for j, parte in enumerate(trozos_t):
            texto = ("" if i == 0 or j else " ") + parte.get("t", "")
            # los dos puntos van pegados al último trozo del término, para no partir el run sin motivo
            ultimo = j == len(trozos_t) - 1
            if ultimo and "omml" not in parte and not parte.get("v"):
                out.append((texto + ":", True, False, None, None))
            else:
                out.append((texto, True, False, parte.get("v"), parte.get("omml")))
                if ultimo:
                    out.append((":", True, False, None, None))
        trozos = _partes_de(t, "significado", t.get("significado", ""))
        for j, parte in enumerate(trozos):
            texto = parte.get("t", "")
            if j == 0:
                texto = " " + texto.lstrip()          # un solo espacio tras los dos puntos
            if j == len(trozos) - 1 and "omml" not in parte:
                # el punto final lo pone el sistema, sin tocar el espacio con el que empieza el trozo
                cuerpo = texto.rstrip()
                texto = cuerpo + ("" if cuerpo[-1:] in (".", "!", "?", "…") else ".")
            out.append((texto, False, False, parte.get("v"), parte.get("omml")))
        if trozos and ("omml" in trozos[-1] or trozos[-1].get("v")):
            out.append((".", False, False, None, None))   # el significado termina en una fórmula: el punto va aparte
    return out


def a_html(lista):
    if not lista:
        return ""
    cuerpo = ""
    for texto, negrita, cursiva, vert, omml in partes(lista):
        if omml:
            cuerpo += mathml.a_mathml(ecuacion({"omml": omml})) or html.escape(texto_de_parte({"omml": omml}))
            continue
        trozo = html.escape(texto)
        if vert:
            trozo = f"<{'sup' if vert == 'sup' else 'sub'}>{trozo}</{'sup' if vert == 'sup' else 'sub'}>"
        if negrita:
            trozo = f"<b>{trozo}</b>"
        elif cursiva:
            trozo = f"<i>{trozo}</i>"
        cuerpo += trozo
    return f'<p class="glosario">{cuerpo}</p>'
