"""Validador de archivos de carga · Estándar PRAXIS v1.2, sección 2.12.

Cada regla es exacta: el archivo se acepta completo o se rechaza con la lista de
motivos, cada uno con su ubicación y la forma de corregirlo.
"""
import io
import re
from dataclasses import dataclass, field

from PIL import Image, ImageChops

from app.catalogos_base import GRADOS_PRIMARIA, regla_submateria

from app import glosario
from .catalogo import CatalogoValidacion, clave
from .docx_lector import NS, W, DocxCarga, ErrorLectura, Parrafo, Tabla, q, texto_con_nivel
from .resultado import Resultado, Similitud

# ------------------------------------------------------------------ constantes
ENC_RESPUESTAS = ["N°", "Clave", "Justificación de la respuesta correcta"]
ENC_EXCEL = ["Preg.", "Correcta", "Grado", "Materia", "Submateria", "Pensamiento", "Competencia", "DBA", "Temática", "Nivel"]
ENC_GLOSARIO = ["Pregunta", "Término", "Significado"]
MAX_TERMINOS = 3            # por pregunta
MAX_LARGO_TERMINO = 40
MAX_LARGO_SIGNIFICADO = 150
ROTULOS = ("TABLA DE RESPUESTAS", "TABLA DE EXCEL", "TABLA DE GLOSARIO")
NOMBRE_ALINEACION = {"left": "a la izquierda", "center": "centrado", "right": "a la derecha"}
FRASES_REFERENCIA = {
    "Responde las preguntas #N a #M de acuerdo con la siguiente lectura.": "lectura",
    "Responde las preguntas #N a #M de acuerdo con la siguiente información.": "información",
}
NIVELES = ["Básico", "Medio", "Avanzado"]

ANCHO_MAX_EMU = int(8.4 * 360000)
ANCHO_AVISO_EMU = int(8.0 * 360000)
ANCHO_MAX_TWIPS = int(8.4 / 2.54 * 1440)          # 4762
PNG = b"\x89PNG\r\n\x1a\n"

RE_OPCION = re.compile(r"^([A-D])\.\s")
RE_OPCION_CASI = re.compile(r"^([A-Ea-e])\s*[.)\-]")
RE_PARTE = re.compile(r"^PARTE\s+#P\s*·\s*(?P<t>.+?)\s*[—–-]\s*preguntas\s+#N\s+a\s+#M$")
RE_NUMERO_INICIAL = re.compile(r"^\s*\d+[.)\-]\s")
RE_REF_CRUZADA = re.compile(r"\b(ejercicios?|preguntas?|puntos?|numeral(?:es)?)\s+(?:n[°º.]?\s*)?\d+|\bpreguntas?\s+(anterior|siguiente)\b", re.I)
RE_REF_POSICION = re.compile(r"\b(tabla|imagen|gr[aá]fica|figura|esquema|texto)\s+(?:de\s+)?(arriba|abajo|la\s+izquierda|la\s+derecha)\b", re.I)
# Una opción se rechaza cuando ES una referencia a las otras opciones. Se compara sobre el texto normalizado
# (sin mayúsculas ni tildes). Frases que siempre hablan de las opciones, en cualquier parte de la opción:
RE_OPCION_PROHIBIDA = re.compile(
    r"\b(?:todas|ninguna)\s+(?:de\s+)?las\s+(?:opciones\s+)?anteriores\b"
    r"|\b(?:la|el)\s+(?:primera|primero|ultima|ultimo)\s+(?:opcion|respuesta|alternativa)\b"
    r"|\b(?:opcion|opciones|respuesta|respuestas|alternativa|alternativas|literal|literales)\s+anterior(?:es)?\b")
# Y la opción completa, cuando no dice nada más que «las anteriores», «ninguna es correcta» o «A y B»:
RE_OPCION_SOLO_REFERENCIA = [
    re.compile(r"^(?:todas|ninguna)\s+(?:de\s+)?(?:las\s+)?(?:opciones\s+)?(?:anteriores|opciones)(?:\s+(?:son|es)\s+\w+)?$"),
    re.compile(r"^(?:todas|ninguna)\s+(?:las\s+)?(?:opciones\s+)?(?:son|es)\s+(?:correctas?|verdaderas?|validas?)$"),
    re.compile(r"^(?:la|las|los)\s+(?:dos\s+|tres\s+)?(?:opciones\s+)?anterior(?:es)?$"),
    re.compile(r"^[a-d](?:\s*(?:,|y|o|e)\s*[a-d])+(?:\s+(?:son|es)\s+(?:correctas?|verdaderas?|validas?))?$"),
]
# Letras de opción citadas como respuesta: «A y B son correctas», «las opciones A y C»
RE_LETRAS_UNIDAS = re.compile(
    r"\b(?:opciones|literales|respuestas|alternativas)\s+[A-D]\s+(?:y|o)\s+[A-D]\b"
    r"|\b[A-D]\s+(?:y|o)\s+[A-D]\s+(?:son|ser[ií]an)\s+(?:correctas|verdaderas|v[aá]lidas)\b", re.I)
RE_JUST_LETRA = [
    re.compile(r"\b(?i:opci[oó]n(?:es)?|literal(?:es)?|respuestas?|alternativas?)\s+[A-D]\b"),
    re.compile(r"\b(?:[Ll]as?|[Ee]l|[Ll]os)\s+[A-D]\s+(?i:es|no\s+es|son|ser[ií]a|resulta)\s+(?i:la\s+)?(?i:correcta|incorrecta|respuesta|opci[oó]n|verdadera|falsa|v[aá]lida)"),
    RE_LETRAS_UNIDAS,
]
RE_LETRA_PARENTESIS = re.compile(r"(?<![\w(])[A-D]\)")
DIGITOS = set("0123456789")   # «²» o «₅» ya son superíndice/subíndice: no cuentan
RE_POTENCIA_TEXTO = re.compile(r"\^\s*[-−]?\d|\*\*\s*[-−]?\d")   # x^2, 2**3: se escriben con superíndice
# la barra normal y las dos «barras de fracción» de Word, que a simple vista son iguales
BARRAS_FRACCION = "/⁄∕"
RE_MARCADOR = re.compile(r"\(#(\d+)\)")
SIN_DATO = {"no aplica", "no aplican", "na", "n/a", "ninguno", "ninguna", "no tiene", "no hay",
            "sin submateria", "sin dba", "-", "--", "---", "n.a.", "no corresponde"}


def dice_que_no_hay(valor):
    """¿La celda dice «aquí no va nada»? Mucha gente lo escribe en vez de dejarla vacía."""
    return clave(valor).strip(" .·—–-") in SIN_DATO


RE_DBA = re.compile(r"DBA\s*0*(\d+)", re.I)


@dataclass
class Pregunta:
    enunciado: list = field(default_factory=list)
    opciones: list = field(default_factory=list)
    rota: bool = False


@dataclass
class Unidad:
    tipo: str                       # suelto | bloque | parte
    cabecera: Parrafo | None = None
    instruccion: Parrafo | None = None
    recurso: list = field(default_factory=list)
    credito: Parrafo | None = None
    preguntas: list = field(default_factory=list)
    titulo_parte: str | None = None
    tipo_recurso: str | None = None


def recorte(texto, ini, fin, margen=18):
    a, b = max(0, ini - margen), min(len(texto), fin + margen)
    return ("…" if a else "") + texto[a:b].replace("\n", " ").replace("\t", " ") + ("…" if b < len(texto) else "")


def es_credito(p):
    return (isinstance(p, Parrafo) and p.alineacion == "right" and p.texto.strip()
            and all(f.fmt.cursiva for f in p.fragmentos if f.texto.strip()))


def solo_imagen(p):
    return isinstance(p, Parrafo) and p.dibujos and not p.texto.strip()


def alineacion_impresa(p):
    """Alineación con que el párrafo sale en la cartilla (Estándar 3.5B).

    Todo sale justificado, salvo lo que el autor alineó a mano: Centrar y Alinear a la derecha
    se conservan siempre; Alinear a la izquierda, solo si está aplicado al párrafo (si viene del
    estilo es el valor por defecto de Word y no una decisión del autor). Las imágenes van centradas.
    """
    if p.dibujos and not p.texto.strip():
        return "center"
    if p.alineacion in ("center", "right"):
        return p.alineacion
    if p.alineacion == "left" and p.alineacion_directa == "left":
        return "left"
    return "both"


def letra_opcion(p):
    if not isinstance(p, Parrafo):
        return None
    m = RE_OPCION.match(p.texto.lstrip())
    return m.group(1) if m else None


class Validador:
    def __init__(self, datos: bytes, nombre: str, catalogo: CatalogoValidacion):
        self.unidad = None
        self.r = Resultado(archivo=nombre)
        self.cat = catalogo
        self.datos = datos

    # ================================================================== flujo
    def ejecutar(self):
        try:
            self.doc = DocxCarga(self.datos)
        except ErrorLectura as e:
            self.r.error(0, "Archivo", str(e))
            return self.r
        self.revisar_documento()
        contenido, t_resp, t_excel, t_glos = self.separar_tablas_control()
        if contenido is None:
            return self.r
        u = self.leer_unidad(contenido)
        self.unidad = u
        self.r.tipo = u.tipo
        self.r.preguntas = len(u.preguntas)
        filas = self.revisar_tablas_control(u, t_resp, t_excel)
        self.revisar_glosario(u, t_glos)
        self.revisar_contenido(u, filas)
        return self.r

    # ================================================================== documento
    def revisar_documento(self):
        raiz = self.doc.doc
        cambios = [e for tag in ("ins", "del", "moveFrom", "moveTo", "rPrChange", "pPrChange", "sectPrChange", "tblPrChange", "trPrChange", "tcPrChange")
                   for e in raiz.iter(W + tag)]
        if cambios:
            self.r.error(20, "Documento", f"Tiene control de cambios ({len(cambios)} marcas). Acepta o rechaza todos los cambios y desactiva el control de cambios.")
        if raiz.find(".//w:commentReference", NS) is not None or (self.doc.comentarios and b"<w:comment " in self.doc.comentarios):
            self.r.error(20, "Documento", "Tiene comentarios de Word. Elimínalos todos antes de subir el archivo.")
        for sect in raiz.iter(W + "sectPr"):
            pg, mar, cols = sect.find("w:pgSz", NS), sect.find("w:pgMar", NS), sect.find("w:cols", NS)
            if pg is not None:
                ancho, alto = int(pg.get(W + "w", 0)), int(pg.get(W + "h", 0))
                if abs(ancho - 12240) > 20 or abs(alto - 15840) > 20:
                    self.r.error(21, "Configuración de página", f"La página mide {ancho / 567:.2f} × {alto / 567:.2f} cm. Debe ser carta (21,59 × 27,94 cm).")
                if pg.get(W + "orient") == "landscape":
                    self.r.error(21, "Configuración de página", "La orientación es horizontal. Debe ser vertical.")
            if mar is not None:
                malos = [n for n, a in (("superior", "top"), ("inferior", "bottom"), ("izquierdo", "left"), ("derecho", "right"))
                         if abs(int(float(mar.get(W + a, 0))) - 720) > 10]
                if malos:
                    self.r.error(21, "Configuración de página", f"Los márgenes {', '.join(malos)} no miden 1,27 cm. Usa Márgenes › Estrecho en Word.")
            if cols is not None and int(cols.get(W + "num", 1)) > 1:
                self.r.error(21, "Configuración de página", "El documento está a varias columnas. Debe ir a una sola columna.")

    def separar_tablas_control(self):
        items = self.doc.items
        idx = {}
        for etiqueta in ROTULOS:
            opcional = etiqueta == "TABLA DE GLOSARIO"
            exactos = [i for i, it in enumerate(items) if isinstance(it, Parrafo) and it.texto.strip() == etiqueta]
            casi = [i for i, it in enumerate(items) if isinstance(it, Parrafo) and clave(it.texto) == clave(etiqueta) and i not in exactos]
            if casi:
                self.r.error(1, etiqueta, f"El rótulo está escrito «{items[casi[0]].texto.strip()}». Debe ser exactamente «{etiqueta}», en mayúsculas.")
                exactos = exactos or casi
            if not exactos:
                if opcional:           # el glosario es opcional
                    continue
                self.r.error(1, etiqueta, f"Falta el rótulo «{etiqueta}» con su tabla.")
                return None, None, None, None
            if len(exactos) > 1:
                self.r.error(1, etiqueta, f"El rótulo «{etiqueta}» aparece {len(exactos)} veces. Debe aparecer una sola vez.")
            idx[etiqueta] = exactos[0]
        i_resp, i_excel = idx["TABLA DE RESPUESTAS"], idx["TABLA DE EXCEL"]
        i_glos = idx.get("TABLA DE GLOSARIO")
        if i_excel < i_resp:
            self.r.error(1, "Tablas de control", "La TABLA DE EXCEL va después de la TABLA DE RESPUESTAS.")
            return None, None, None, None
        if i_glos is not None and i_glos < i_excel:
            self.r.error(1, "Tablas de control", "La TABLA DE GLOSARIO va al final, después de la TABLA DE EXCEL.")
            return None, None, None, None
        fin_excel = i_glos if i_glos is not None else len(items)

        def tabla_tras(i, etiqueta, hasta):
            for it in items[i + 1:hasta]:
                if isinstance(it, Tabla):
                    return it
                if not it.vacio:
                    break
            self.r.error(1, etiqueta, f"Después del rótulo «{etiqueta}» debe ir su tabla.")
            return None

        t_resp = tabla_tras(i_resp, "TABLA DE RESPUESTAS", i_excel)
        t_excel = tabla_tras(i_excel, "TABLA DE EXCEL", fin_excel)
        t_glos = tabla_tras(i_glos, "TABLA DE GLOSARIO", len(items)) if i_glos is not None else None
        sobra = lambda desde, hasta, tabla: [it for it in items[desde + 1:hasta] if it is not tabla and not (isinstance(it, Parrafo) and it.vacio)]
        entre = sobra(i_resp, i_excel, t_resp) + sobra(i_excel, fin_excel, t_excel)
        despues = sobra(i_glos, len(items), t_glos) if i_glos is not None else []
        if entre or despues:
            self.r.error(1, "Tablas de control", "Hay contenido entre las tablas de control o después de la última. Las tablas van al final (RESPUESTAS, EXCEL y, si hay glosario, GLOSARIO) y no puede haber nada más.")
        contenido = [it for it in items[:i_resp] if not (isinstance(it, Parrafo) and it.vacio)]
        if not contenido:
            self.r.error(5, "Contenido", "El archivo no tiene ninguna pregunta antes de las tablas de control.")
            return None, None, None, None
        return contenido, t_resp, t_excel, t_glos

    # ================================================================== estructura
    def leer_unidad(self, items):
        primero = items[0]
        texto0 = re.sub(r"\s+", " ", primero.texto).strip() if isinstance(primero, Parrafo) else ""
        if texto0 in FRASES_REFERENCIA:
            u = Unidad("bloque", cabecera=primero, tipo_recurso=FRASES_REFERENCIA[texto0])
        elif texto0.lower().startswith("responde las pregunta"):
            u = Unidad("bloque", cabecera=primero)
            self.r.error(6, "Frase de referencia", f"La frase de referencia dice «{texto0}». Debe ser exactamente «Responde las preguntas #N a #M de acuerdo con la siguiente lectura.» (o «…siguiente información.»), con #N y #M sin números.")
        elif RE_PARTE.match(texto0):
            u = Unidad("parte", cabecera=primero, titulo_parte=RE_PARTE.match(texto0).group("t"))
        elif re.match(r"^PARTE\s+(#P|\d+)\b", texto0):
            u = Unidad("parte", cabecera=primero)
            self.r.error(6, "Subtítulo de la parte", f"El subtítulo dice «{texto0}». Debe tener la forma «PARTE #P · Título — preguntas #N a #M», con #P, #N y #M sin números.")
        else:
            u = Unidad("suelto")

        # frase de referencia o subtítulo fuera del primer párrafo
        for it in items[1:]:
            if isinstance(it, Parrafo):
                t = re.sub(r"\s+", " ", it.texto).strip()
                if t in FRASES_REFERENCIA or RE_PARTE.match(t):
                    self.r.error(6, "Contenido", f"«{recorte(t, 0, 40)}» debe ser el primer párrafo del archivo.")

        creditos = [i for i, it in enumerate(items) if es_credito(it)]
        primera_opcion = next((i for i, it in enumerate(items) if letra_opcion(it)), len(items))
        resto_inicio = 0
        if u.tipo == "suelto":
            if creditos:
                self.r.error(8, "Contenido", "Hay un párrafo con formato de línea de crédito (derecha y cursiva). En un ejercicio suelto no va línea de crédito; cambia su alineación o su formato.")
        elif u.tipo == "bloque":
            validos = [i for i in creditos if i < primera_opcion]
            if not validos:
                self.r.error(7, "Lectura", "El bloque no tiene línea de crédito. Debe ser el último párrafo de la lectura: alineado a la derecha, todo en cursiva, 8 pt (por ejemplo «Texto elaborado para este simulacro. PRAXIS · THINKS.»).")
                resto_inicio = 1
            else:
                c = validos[0]
                u.credito, u.recurso, resto_inicio = items[c], items[1:c], c + 1
                if not u.recurso:
                    self.r.error(7, "Lectura", "El bloque no tiene lectura ni recurso entre la frase de referencia y la línea de crédito.")
            for i in creditos[1:] if validos else creditos:
                if not validos or i != validos[0]:
                    self.r.error(8, "Contenido", f"«{recorte(items[i].texto, 0, 40)}» tiene formato de línea de crédito (derecha y cursiva) pero no es el final de la lectura.")
        else:  # parte
            if len(items) < 2 or letra_opcion(items[1]) or not isinstance(items[1], Parrafo) or es_credito(items[1]):
                self.r.error(7, "Instrucción de la parte", "Después del subtítulo debe ir la línea de instrucción de la parte, en un solo párrafo.")
                resto_inicio = 1
            else:
                u.instruccion = items[1]
                resto_inicio = 2
                validos = [i for i in creditos if i < primera_opcion]
                if validos:
                    c = validos[0]
                    u.credito, u.recurso, resto_inicio = items[c], items[2:c], c + 1
                    if not u.recurso:
                        self.r.error(7, "Recurso de la parte", "Hay línea de crédito pero no hay recurso entre la instrucción y el crédito.")
                for i in creditos:
                    if not validos or i != validos[0]:
                        self.r.error(8, "Contenido", f"«{recorte(items[i].texto, 0, 40)}» tiene formato de línea de crédito (derecha y cursiva) pero no es el final del recurso.")

        u.preguntas = self.partir_preguntas(items[resto_inicio:], u.tipo)
        n = len(u.preguntas)
        if u.tipo == "suelto" and n > 1:
            self.r.error(6, "Contenido", f"El archivo tiene {n} preguntas. Un ejercicio suelto lleva una sola; si varias preguntas comparten un recurso, usa la plantilla de bloque de lectura.")
        if u.tipo in ("bloque", "parte") and n < 2:
            nombre = "bloque" if u.tipo == "bloque" else "parte"
            self.r.error(7, "Contenido", f"El {nombre} tiene {n} pregunta{'s' if n != 1 else ''}. Debe tener mínimo 2.")
        return u

    def partir_preguntas(self, items, tipo):
        preguntas, actual = [], Pregunta()

        def cerrar():
            nonlocal actual
            if actual.enunciado or actual.opciones:
                preguntas.append(actual)
            actual = Pregunta()

        for it in items:
            k = len(preguntas) + 1
            letra = letra_opcion(it)
            if letra:
                n = len(actual.opciones)
                if n == 4:
                    if letra == "A":
                        cerrar()
                        actual.opciones.append(it)
                    else:
                        self.r.error(5, f"Pregunta {k}", f"Hay más de cuatro opciones: después de la D aparece otra «{letra}.».")
                        actual.rota = True
                    continue
                esperada = "ABCD"[n]
                if letra != esperada:
                    self.r.error(5, f"Pregunta {k}", f"{'Después de la opción ' + 'ABCD'[n - 1] if n else 'Al inicio de las opciones'} aparece la {letra}. Falta la opción {esperada}; las opciones van siempre A, B, C, D, en orden.")
                    actual.rota = True
                actual.opciones.append(it)
                continue
            if actual.opciones and len(actual.opciones) < 4:
                ultima = "ABCD"[len(actual.opciones) - 1]
                if isinstance(it, Tabla):
                    self.r.error(5, f"Pregunta {k} · opción {ultima}", "Hay una tabla dentro de las opciones. Las opciones no pueden llevar tablas.")
                else:
                    casi = RE_OPCION_CASI.match(it.texto.lstrip())
                    if casi:
                        self.r.error(5, f"Pregunta {k}", f"La opción «{recorte(it.texto, 0, 20)}» está mal escrita. Cada opción empieza exactamente con la letra mayúscula, punto y espacio: «{casi.group(1).upper()}. ».")
                    else:
                        self.r.error(5, f"Pregunta {k} · opción {ultima}", f"Después de la opción {ultima} sigue «{recorte(it.texto, 0, 40)}». Cada opción ocupa un solo párrafo y deben estar las cuatro: A, B, C, D.")
                actual.rota = True
                continue   # se ignora el párrafo intruso y se siguen leyendo las opciones
            if actual.opciones and len(actual.opciones) == 4:
                if isinstance(it, Parrafo) and re.match(r"^[Ee]\s*[.)]", it.texto.lstrip()):
                    self.r.error(5, f"Pregunta {k}", "Hay una opción E. Toda pregunta tiene exactamente cuatro opciones: A, B, C y D.")
                    continue
                cerrar()
            actual.enunciado.append(it)
        k = len(preguntas) + 1
        if actual.enunciado and not actual.opciones:
            pista = ""
            if any(isinstance(p, Parrafo) and p.numerado for p in actual.enunciado):
                pista = " Parece que las letras están hechas con numeración automática de Word: escríbelas a mano («A. », «B. »…)."
            elif any(isinstance(p, Parrafo) and RE_OPCION_CASI.match(p.texto.lstrip()) for p in actual.enunciado):
                pista = " Revisa el formato de las letras: deben ser «A. », «B. », «C. », «D. » (mayúscula, punto y espacio)."
            self.r.error(5, f"Pregunta {k}", "Esta pregunta no tiene opciones." + pista)
            actual.rota = True
        elif actual.opciones and len(actual.opciones) < 4:
            faltan = ", ".join("ABCD"[len(actual.opciones):])
            self.r.error(5, f"Pregunta {k}", f"Faltan las opciones {faltan}.")
            actual.rota = True
        cerrar()
        return preguntas

    # ================================================================== tablas de control
    def revisar_tablas_control(self, u, t_resp, t_excel):
        n = len(u.preguntas)
        claves = []
        if t_resp is not None:
            filas = t_resp.textos()
            enc = [re.sub(r"\s+", " ", c) for c in filas[0]] if filas else []
            enc_ok = [e.replace("Nº", "N°") for e in enc]
            if enc_ok != ENC_RESPUESTAS:
                self.r.error(2, "TABLA DE RESPUESTAS", f"Los encabezados deben ser exactamente: {' · '.join(ENC_RESPUESTAS)}. El archivo tiene: {' · '.join(enc) or '(vacío)'}.")
            datos = filas[1:]
            if len(datos) != n:
                self.r.error(3, "TABLA DE RESPUESTAS", f"Tiene {len(datos)} fila{'s' if len(datos) != 1 else ''} de datos y el archivo tiene {n} pregunta{'s' if n != 1 else ''}. Debe haber una fila por pregunta.")
            for i, fila in enumerate(datos, 1):
                donde = f"TABLA DE RESPUESTAS · fila {i}"
                fila = (fila + ["", "", ""])[:3]
                if fila[0]:
                    self.r.error(4, donde, f"La columna N° debe ir vacía; tiene «{fila[0]}». El número lo pone el sistema.")
                clave_ = fila[1].strip()
                if clave_ not in ("A", "B", "C", "D"):
                    self.r.error(9, donde, f"La Clave debe ser una sola letra mayúscula A, B, C o D; tiene «{clave_ or '(vacía)'}».")
                claves.append(clave_)
                just = fila[2]
                self.r.justificaciones.append(re.sub(r"\s+", " ", just).strip())
                if not just:
                    self.r.error(9, donde, "Falta la justificación de la respuesta correcta.")
                coincidencias = [rx.search(just) for rx in RE_JUST_LETRA]
                for m in RE_LETRA_PARENTESIS.finditer(just):
                    if just[:m.start()].count("(") <= just[:m.start()].count(")"):
                        coincidencias.append(m)
                        break
                for m in coincidencias:
                    if m:
                        self.r.error(17, donde, f"La justificación menciona una letra de opción: «{recorte(just, m.start(), m.end())}». Como el sistema cambia las letras, refiérete al contenido de la respuesta, no a su letra.")
                        break
                celda = t_resp.filas[i][2] if len(t_resp.filas[i]) > 2 else []
                if any(isinstance(p, Parrafo) and (p.dibujos or p.objetos) for p in celda):
                    self.r.error(17, donde, "La justificación tiene una imagen u objeto. Debe ser solo texto.")
                self.revisar_texto_de_trabajo(just, donde)
                self.revisar_runs_marcados([p for p in celda if isinstance(p, Parrafo)], donde)
        self.r.claves = claves

        filas_ok = []
        if t_excel is not None:
            filas = t_excel.textos()
            enc = [re.sub(r"\s+", " ", c) for c in filas[0]] if filas else []
            if enc != ENC_EXCEL:
                self.r.error(2, "TABLA DE EXCEL", f"Los encabezados deben ser exactamente estos {len(ENC_EXCEL)}: {' · '.join(ENC_EXCEL)}. El archivo tiene {len(enc)}: {' · '.join(enc) or '(vacío)'}.")
            datos = filas[1:]
            if len(datos) != n:
                self.r.error(3, "TABLA DE EXCEL", f"Tiene {len(datos)} fila{'s' if len(datos) != 1 else ''} de datos y el archivo tiene {n} pregunta{'s' if n != 1 else ''}. Debe haber una fila por pregunta.")
            if enc == ENC_EXCEL:
                for i, fila in enumerate(datos, 1):
                    filas_ok.append(self.revisar_fila_excel(i, fila, claves[i - 1] if i - 1 < len(claves) else None))
                grupos = {(f["grado"], f["materia"], f["submateria"]) for f in filas_ok if f}
                if u.tipo in ("bloque", "parte") and len(grupos) > 1:
                    self.r.error(11, "TABLA DE EXCEL", "En un bloque o una parte, todas las filas deben tener el mismo Grado, Materia y Submateria.")
        self.r.filas = [f for f in filas_ok if f]
        return self.r.filas

    def materia_de_submateria(self, texto):
        """(materia, submateria) si ese nombre es en realidad una submateria. Ninguna se llama como una materia."""
        for materia, subs in self.cat.submaterias.items():
            nombre = subs.get(clave(texto))
            if nombre:
                return self.cat.materias.get(materia, materia), nombre
        return None, None

    def revisar_fila_excel(self, i, fila, clave_resp):
        donde = f"TABLA DE EXCEL · fila {i}"
        fila = (fila + [""] * 10)[:10]
        preg, correcta, grado, materia, sub, pens, comp, dba, tema, nivel = [c.strip() for c in fila]
        if preg:
            self.r.error(4, donde, f"La columna Preg. debe ir vacía; tiene «{preg}». El número lo pone el sistema.")
        if correcta not in ("A", "B", "C", "D"):
            self.r.error(9, donde, f"La columna Correcta debe ser una sola letra A, B, C o D; tiene «{correcta or '(vacía)'}».")
        elif clave_resp and correcta != clave_resp:
            self.r.error(9, donde, f"La columna Correcta dice «{correcta}» y la Clave de la TABLA DE RESPUESTAS dice «{clave_resp}». Deben coincidir.")

        cod_grado = self.cat.grados.get(clave(grado))
        validos = ", ".join(self.cat.nombres_grados[:-1]) + " o " + self.cat.nombres_grados[-1]
        if not grado:
            self.r.error(10, donde, f"Falta el Grado. Escribe {validos}.")
        elif not cod_grado:
            self.r.error(10, donde, f"El Grado «{grado}» no existe en el catálogo. Escribe {validos}.")
        es_icfes = cod_grado == self.cat.grado_icfes

        nombre_materia = self.cat.materias.get(clave(materia))
        nombre_sub = None
        if not nombre_materia and materia:
            # el nombre de una submateria escrito en la columna Materia: se entiende y se avisa
            dueno, sub_real = self.materia_de_submateria(materia)
            if dueno:
                self.r.aviso(donde, f"«{materia}» es una submateria de {dueno}. Se guarda como "
                                    f"Materia «{dueno}» y Submateria «{sub_real}».")
                nombre_materia, materia, sub = dueno, dueno, sub_real
        if nombre_materia and sub and clave(sub) in self.cat.materias and not self.cat.submaterias.get(
                clave(nombre_materia), {}).get(clave(sub)):
            # una materia propia escrita como submateria (Filosofía dentro de Ciencias Sociales)
            propia = self.cat.materias[clave(sub)]
            self.r.aviso(donde, f"«{sub}» es una materia propia, no una submateria de {nombre_materia}. "
                                f"Se guarda como Materia «{propia}», sin submateria.")
            nombre_materia, materia, sub = propia, propia, ""
        if not materia:
            self.r.error(10, donde, "Falta la Materia.")
        elif not nombre_materia:
            self.r.error(10, donde, f"La Materia «{materia}» no existe en el catálogo.")
        else:
            subs = self.cat.submaterias.get(clave(nombre_materia), {})
            regla = self.cat.regla_submateria.get(nombre_materia, False)
            if cod_grado in GRADOS_PRIMARIA:
                regla = regla_submateria(nombre_materia, cod_grado)
            if sub and cod_grado in GRADOS_PRIMARIA and regla is False and subs:
                self.r.error(10, donde, f"En 3°, 4° y 5°, {nombre_materia} va sin submateria: deja vacía la columna Submateria (tiene «{sub}»).")
            elif sub:
                nombre_sub = subs.get(clave(sub))
                if not nombre_sub:
                    opciones = ", ".join(subs.values())
                    if opciones:
                        self.r.error(10, donde, f"La Submateria «{sub}» no pertenece a {nombre_materia}. Las posibles son: {opciones}.")
                    elif dice_que_no_hay(sub) or clave(sub) == clave(nombre_materia):
                        self.r.aviso(donde, f"La Submateria dice «{sub}»; {nombre_materia} no tiene submaterias, "
                                            "así que se guarda vacía.")
                        nombre_sub = None
                    else:
                        self.r.error(10, donde, f"{nombre_materia} no tiene submaterias: la columna Submateria va vacía.")
            elif regla is True and not (es_icfes and nombre_materia == "Matemáticas"):
                self.r.error(10, donde, f"Falta la Submateria. En {nombre_materia} es obligatoria: {', '.join(subs.values())}.")

        pens_n, comp_n, tema_n = (self.normalizar(v) for v in (pens, comp, tema))
        dba_n = ""
        dba = self.normalizar(dba)
        if dba and dice_que_no_hay(dba):
            # hay materias sin DBA oficial (Filosofía, Ética, Informática…): decirlo es correcto
            self.r.aviso(donde, f"El DBA dice «{dba}»: se guarda vacío.")
            dba = ""
        if dba:
            numeros = RE_DBA.findall(dba)
            sobra = re.sub(r"[\s,;y]+", "", RE_DBA.sub("", dba), flags=re.I)
            if not numeros or sobra:
                self.r.error(10, donde, f"El DBA «{dba}» no tiene el formato correcto. Escribe «DBA 3», o si son varios «DBA 3, DBA 5».")
            else:
                dba_n = ", ".join(f"DBA {int(x)}" for x in numeros)
        if not tema_n:
            self.r.error(10, donde, "Falta la Temática. Es obligatoria porque es el filtro principal del buscador.")

        nivel_n = next((nv for nv in NIVELES if clave(nv) == clave(nivel)), None)
        if es_icfes:
            if nivel:
                self.r.error(10, donde, f"En grado ICFES el Nivel va vacío; tiene «{nivel}».")
        elif not nivel:
            self.r.error(10, donde, "Falta el Nivel: Básico, Medio o Avanzado.")
        elif not nivel_n:
            self.r.error(10, donde, f"El Nivel «{nivel}» no es válido. Escribe Básico, Medio o Avanzado.")

        # si el valor ya está registrado con otras tildes o mayúsculas, se guarda con esa escritura (1.7)
        tema_n = self.buscar_similar("Temática", tema_n)
        comp_n = self.buscar_similar("Competencia", comp_n)
        pens_n = self.buscar_similar("Pensamiento", pens_n)
        for valor in (pens, comp, tema, dba):
            self.revisar_texto_de_trabajo(valor, donde)
        return {"correcta": correcta, "grado": cod_grado, "materia": nombre_materia, "submateria": nombre_sub or "",
                "pensamiento": pens_n, "competencia": comp_n, "dba": dba_n, "tematica": tema_n, "nivel": nivel_n or ""}

    def revisar_glosario(self, u, t):
        """TABLA DE GLOSARIO (opcional, 2.7B): hasta 3 términos cortos por pregunta, escritos como en el texto."""
        n = len(u.preguntas)
        self.r.glosarios = [[] for _ in range(n)]
        if t is None:
            return
        filas = t.textos()
        enc = [re.sub(r"\s+", " ", c) for c in filas[0]] if filas else []
        if enc != ENC_GLOSARIO:
            self.r.error(29, "TABLA DE GLOSARIO", f"Los encabezados deben ser exactamente: {' · '.join(ENC_GLOSARIO)}. El archivo tiene: {' · '.join(enc) or '(vacío)'}.")
            return
        comun = [it for it in ([u.instruccion] if u.instruccion is not None else []) + u.recurso]
        textos = []
        for pr in u.preguntas:
            partes = []
            for it in comun + pr.enunciado + pr.opciones:
                if isinstance(it, Parrafo):
                    partes.append(it.texto)
                else:
                    partes += [p.texto for fila in it.filas for celda in fila for p in celda if isinstance(p, Parrafo)]
            textos.append(re.sub(r"\s+", " ", " ".join(partes)).lower())
        rango = "1" if n == 1 else f"1 a {n}"
        por_pregunta = [0] * n
        for i, fila in enumerate(filas[1:], 1):
            donde = f"TABLA DE GLOSARIO · fila {i}"
            fila = [re.sub(r"\s+", " ", c).strip() for c in (fila + ["", "", ""])[:3]]
            if not any(fila):
                continue                     # filas vacías: se ignoran (la plantilla trae una)
            num, termino, significado = fila
            celdas = t.filas[i][1:3] if len(t.filas[i]) >= 3 else []
            parrafos = [p for celda in celdas for p in celda if isinstance(p, Parrafo)]
            if any(p.dibujos or p.objetos for p in parrafos):
                # las fórmulas sí se admiten (2.7B); lo que no cabe en una línea de 8 pt es una imagen
                self.r.error(29, donde, "El glosario no lleva imágenes ni objetos incrustados. "
                                        "Las fórmulas sí: escríbelas con superíndice, subíndice o el editor de ecuaciones.")
            self.revisar_runs_marcados(parrafos, donde)
            self.revisar_texto_de_trabajo(termino, donde)
            self.revisar_texto_de_trabajo(significado, donde)
            if not re.fullmatch(r"\d+", num) or not 1 <= int(num) <= n:
                self.r.error(29, donde, f"La columna Pregunta lleva el número de la pregunta dentro de este archivo ({rango}); tiene «{num or '(vacía)'}».")
                continue
            k = int(num)
            por_pregunta[k - 1] += 1
            bien = True
            if not termino:
                self.r.error(29, donde, "Falta el término.")
                bien = False
            elif len(termino) > MAX_LARGO_TERMINO:
                self.r.error(29, donde, f"El término tiene {len(termino)} caracteres. El máximo es {MAX_LARGO_TERMINO}: el glosario es de palabras o expresiones cortas.")
                bien = False
            elif termino.lower() not in textos[k - 1]:
                self.r.error(29, donde, f"«{termino}» no aparece en el texto de la pregunta {k}. Escribe el término igual que en el texto (las mayúsculas no importan).")
                bien = False
            if not significado:
                self.r.error(29, donde, "Falta el significado.")
                bien = False
            elif len(significado) > MAX_LARGO_SIGNIFICADO:
                self.r.error(29, donde, f"El significado tiene {len(significado)} caracteres. El máximo es {MAX_LARGO_SIGNIFICADO}.")
                bien = False
            if bien:
                if any(x["termino"].lower() == termino.lower() for x in self.r.glosarios[k - 1]):
                    self.r.error(29, donde, f"El término «{termino}» está repetido en la pregunta {k}.")
                else:
                    fila_glosario = {"termino": termino, "significado": significado}
                    # si el término o el significado llevan fórmula, se guarda también cómo se escribe
                    for campo, celda in (("termino", 0), ("significado", 1)):
                        partes = glosario.partes_de_celda(celdas[celda] if len(celdas) > celda else [])
                        if any(x.get("v") or x.get("omml") for x in partes):
                            fila_glosario.setdefault("formato", {})[campo] = partes
                    self.r.glosarios[k - 1].append(fila_glosario)
        for k, cuantos in enumerate(por_pregunta, 1):
            if cuantos > MAX_TERMINOS:
                self.r.error(29, "TABLA DE GLOSARIO", f"La pregunta {k} tiene {cuantos} términos. El máximo es {MAX_TERMINOS} por pregunta.")

    @staticmethod
    def normalizar(v):
        v = (v or "").strip()
        v = re.sub(r"^[●•▪◦·\-–—*]+\s*", "", v)
        v = re.sub(r"^\d+[.)]\s+", "", v)
        v = re.sub(r"\s+", " ", v).strip()
        return v.rstrip(".").strip()

    def buscar_similar(self, campo, valor):
        """Devuelve con qué escritura se guarda el valor, y deja pendiente el archivo si parece un error de escritura.

        Dos valores son el mismo si solo cambian mayúsculas, tildes o espacios: se adopta la escritura registrada
        sin preguntar. Si difieren en pocas letras (1 hasta 7 caracteres, 2 hasta 15 y 3 de ahí en adelante), se
        pregunta. Lo demás son valores distintos, aunque uno contenga al otro: «Fracciones equivalentes» y
        «Fracciones equivalentes representadas gráficamente» son dos temáticas.
        """
        if not valor:
            return valor
        registrados = self.cat.claves_registradas(campo)
        if valor in registrados:
            return valor
        cv = clave(valor)
        for existente, ce in registrados.items():
            if ce == cv:
                return existente
        for existente, ce in registrados.items():
            # si las longitudes difieren en más de 3, la distancia de edición también: no hace falta calcularla
            # el margen de error depende del largo: en textos cortos, 3 letras ya son otra palabra
            largo = max(len(ce), len(cv))
            tope = 1 if largo < 8 else (2 if largo < 16 else 3)
            if abs(len(ce) - len(cv)) <= tope and distancia(ce, cv, tope) <= tope:
                if all(s.valor != valor or s.campo != campo for s in self.r.similitudes):
                    self.r.similitudes.append(Similitud(campo, valor, existente))
                return valor
        return valor

    # ================================================================== contenido impreso
    def impresos(self, u):
        """(dónde, elemento) de todo lo que se imprime en la cartilla."""
        out = []
        if u.instruccion is not None:
            out.append(("Instrucción de la parte", u.instruccion))
        nombre_rec = "Lectura" if u.tipo == "bloque" and u.tipo_recurso == "lectura" else "Recurso"
        for j, it in enumerate(u.recurso, 1):
            out.append((f"{nombre_rec} · {'tabla' if isinstance(it, Tabla) else 'párrafo ' + str(j)}", it))
        if u.credito is not None:
            out.append(("Línea de crédito", u.credito))
        solo = u.tipo == "suelto"
        for k, pr in enumerate(u.preguntas, 1):
            base = "Enunciado" if solo else f"Pregunta {k}"
            for it in pr.enunciado:
                out.append((f"{base}{'' if solo else ' · enunciado'}{' · tabla' if isinstance(it, Tabla) else ''}", it))
            for op in pr.opciones:
                out.append((f"{'Pregunta' if solo else base} · opción {letra_opcion(op)}", op))
        return out

    def revisar_contenido(self, u, filas):
        materias_fila = {f["materia"] for f in filas} | {f["submateria"] for f in filas}
        aplica_superindice = bool(materias_fila & self.cat.materias_superindice)
        es_ingles = u.tipo == "parte" or "Inglés" in materias_fila
        impresos = self.impresos(u)

        # --- enunciados
        for k, pr in enumerate(u.preguntas, 1):
            base = "Enunciado" if u.tipo == "suelto" else f"Pregunta {k} · enunciado"
            parrafos = [p for p in pr.enunciado if isinstance(p, Parrafo)]
            for p in parrafos:
                if RE_NUMERO_INICIAL.match(p.texto):
                    self.r.error(12, base, f"El párrafo empieza con un número de pregunta: «{recorte(p.texto, 0, 25)}». Quítalo: el número lo pone el sistema.")
            if u.tipo != "parte" and not es_ingles and not pr.rota:
                if not pr.enunciado:
                    self.r.error(13, base, "La pregunta no tiene enunciado.")
                else:
                    ultimo = pr.enunciado[-1]
                    fin = ultimo.texto.rstrip().rstrip("»”\")").rstrip() if isinstance(ultimo, Parrafo) else ""
                    if not fin.endswith("?"):
                        self.r.error(13, base, "El último párrafo del enunciado debe ser la pregunta y terminar en «?».")

        # --- marcadores (#n) de «completar el texto» fuera del recurso
        fuera = [donde for donde, it in impresos
                 if not donde.startswith(("Recurso", "Lectura", "Línea de crédito")) and isinstance(it, Parrafo) and RE_MARCADOR.search(it.texto)]
        if fuera:
            self.r.error(19, fuera[0], "Hay marcadores de espacio (#1), (#2)… fuera del recurso. En «completar el texto» el texto con los espacios es el recurso de la parte y debe terminar con su línea de crédito (derecha y cursiva).")

        # --- parte de «completar el texto»
        if u.tipo == "parte":
            texto_rec = " ".join(p.texto for p in u.recurso if isinstance(p, Parrafo))
            marcas = [int(x) for x in RE_MARCADOR.findall(texto_rec)]
            if marcas:
                esperado = list(range(1, len(u.preguntas) + 1))
                if marcas != esperado:
                    self.r.error(19, "Recurso de la parte", f"Los espacios del texto deben marcarse (#1) a (#{len(u.preguntas)}), uno por pregunta y en orden. El texto tiene: {', '.join(f'(#{m})' for m in marcas)}.")
                for k, pr in enumerate(u.preguntas, 1):
                    if pr.enunciado:
                        self.r.error(19, f"Pregunta {k} · enunciado", "En «completar el texto» las preguntas van sin enunciado: solo sus cuatro opciones.")

        # --- opciones
        for k, pr in enumerate(u.preguntas, 1):
            for op in pr.opciones:
                donde = f"Pregunta {k} · opción {letra_opcion(op)}" if u.tipo != "suelto" else f"Opción {letra_opcion(op)}"
                cuerpo = RE_OPCION.sub("", op.texto.lstrip(), count=1)
                plano = clave(cuerpo).rstrip(". ")          # sin mayúsculas, tildes ni punto final
                m = RE_OPCION_PROHIBIDA.search(plano) or RE_LETRAS_UNIDAS.search(cuerpo)
                if m is None and any(rx.match(plano) for rx in RE_OPCION_SOLO_REFERENCIA):
                    m = re.match(r".*", plano)
                if m and not es_ingles:
                    self.r.error(16, donde, f"La opción depende de otras opciones («{recorte(cuerpo, m.start(), m.end())}»). Como el sistema cambia el orden, cada opción debe entenderse sola.")
                negrita = [f.fmt.negrita for f in op.fragmentos for ch in f.texto if not ch.isspace()][:2]
                if negrita != [True, True]:
                    self.r.error(5, donde, "La letra y el punto de la opción deben ir en negrita.")

        # --- texto de cada elemento impreso
        for donde, it in impresos:
            parrafos = [it] if isinstance(it, Parrafo) else [p for fila in it.filas for celda in fila for p in celda if isinstance(p, Parrafo)]
            for p in parrafos:
                t = p.texto
                for rx, regla, msg in ((RE_REF_CRUZADA, 14, "menciona otra pregunta"), (RE_REF_POSICION, 15, "usa una referencia de posición")):
                    m = rx.search(t)
                    if m:
                        consejo = "Si dos preguntas comparten un recurso, usa un bloque de lectura." if regla == 14 else "Escribe «la siguiente tabla», «la imagen»."
                        self.r.error(regla, donde, f"El texto {msg}: «{recorte(t, m.start(), m.end())}». {consejo}")
                self.revisar_texto_de_trabajo(t, donde)
                self.revisar_notacion(p, donde, aplica_superindice)
                if p.numerado:
                    self.r.error(27, donde, f"El párrafo «{recorte(t, 0, 30)}» usa viñetas o numeración automática de Word. Escribe los números o viñetas como texto.")
                for obj in p.objetos:
                    self.r.error(24, donde, f"Contiene {obj}. Usa superíndices o el editor de ecuaciones de Word (Insertar › Ecuación); las imágenes van como PNG en línea.")
            self.revisar_runs_marcados(parrafos, donde)

        self.revisar_formato(u, impresos)

    def revisar_texto_de_trabajo(self, texto, donde):
        if not texto:
            return
        # corchetes de plantilla: texto de 3 o más palabras entre corchetes (un intervalo como [0, 1] sí vale)
        m = re.search(r"\[[^\]]*?\S\s+\S[^\]]*?\s+\S[^\]]*\]", texto)
        i = m.start() if m else -1
        if i >= 0:
            self.r.error(20, donde, f"Tiene corchetes: «{recorte(texto, i, i + 1)}». Los corchetes son de las plantillas; reemplaza ese texto por el contenido real.")
        for frase, mayus in self.cat.frases_prohibidas:
            patron = (r"\b" if frase[0].isalnum() else "") + re.escape(frase) + (r"\b" if frase[-1].isalnum() else "")
            m = re.search(patron, texto, 0 if mayus else re.I)
            if m:
                self.r.error(20, donde, f"Tiene texto de trabajo: «{recorte(texto, m.start(), m.end())}». Todo lo que queda en el archivo se imprime.")

    def revisar_runs_marcados(self, parrafos, donde):
        for p in parrafos:
            for f in p.fragmentos:
                if not f.texto.strip():
                    continue
                if f.fmt.oculto:
                    self.r.error(20, donde, f"Tiene texto oculto: «{recorte(f.texto, 0, 30)}». Elimínalo.")
                if f.fmt.resaltado and f.fmt.resaltado != "none" or (f.fmt.sombreado and f.fmt.sombreado.upper() not in ("AUTO", "FFFFFF")):
                    self.r.error(20, donde, f"Tiene texto resaltado o sombreado: «{recorte(f.texto, 0, 30)}». Quita el resaltado.")
                tema = (f.fmt.color_tema or "").lower()
                color = (f.fmt.color or "auto").upper()
                if f.fmt.color_variado or (tema and tema not in ("text1", "dark1")) or (not tema and color not in ("AUTO", "000000")):
                    self.r.error(20, donde, f"Tiene texto de color: «{recorte(f.texto, 0, 30)}». Todo el texto va en negro.")

    def revisar_notacion(self, p, donde, aplica_superindice):
        chars = texto_con_nivel(p)
        texto = "".join(c for c, _ in chars)
        if aplica_superindice:
            for i in range(len(chars) - 1):
                c, _ = chars[i]
                d, vd = chars[i + 1]
                if (c.isalpha() or c in ")θ") and d in DIGITOS and vd is None:
                    a = i
                    while a > 0 and (chars[a - 1][0].isalnum() or chars[a - 1][0] == "θ"):
                        a -= 1
                    b = i + 1
                    while b < len(chars) and (chars[b][0].isalnum() or chars[b][0] == "θ"):
                        b += 1
                    palabra = texto[a:b]
                    if palabra.upper() in {e.upper() for e in self.cat.excepciones_superindice}:
                        continue
                    self.r.error(18, donde, f"«{palabra}» tiene un número sin superíndice ni subíndice. Escríbelo con el formato de Word (x², H₂O). Si es una escritura correcta, pide que se agregue a la lista de excepciones.")
                    break
        for i, (c, _) in enumerate(chars):
            if c not in BARRAS_FRACCION:
                continue
            j = i - 1
            while j >= 0 and chars[j][0] == " ":
                j -= 1
            k = i + 1
            while k < len(chars) and chars[k][0] == " ":
                k += 1
            if j >= 0 and k < len(chars) and chars[j][0] in DIGITOS and chars[k][0] in DIGITOS:
                # desde el 06/11/2026 tampoco vale ³/₄: la fracción va APILADA, como en un libro de texto
                self.r.error(18, donde, f"«{recorte(texto, j, k + 1, 6)}» es una fracción escrita con barra. "
                                        "Escríbela con el editor de ecuaciones de Word (Insertar › Ecuación), "
                                        "apilada como en un libro: ni «3/8» ni «³/₈». Las fechas van sin barra.")
                break
        raiz = texto.find("√")
        if raiz >= 0:
            self.r.error(18, donde, f"«{recorte(texto, raiz, raiz + 6)}» lleva el signo de raíz escrito como "
                                    "carácter. La raíz va con el editor de ecuaciones de Word (Insertar › "
                                    "Ecuación), con su barra sobre todo lo que está dentro.")
        m = RE_POTENCIA_TEXTO.search(texto)
        if m:
            self.r.error(18, donde, f"«{recorte(texto, m.start(), m.end())}» es una potencia escrita con "
                                    "símbolos. Usa superíndice de Word (x²) o el editor de ecuaciones.")

    # ================================================================== formato
    def revisar_formato(self, u, impresos):
        previo = None
        for donde, it in impresos:
            if isinstance(it, Tabla):
                self.revisar_tabla(it, donde)
            else:
                pie_de_imagen = previo is not None and solo_imagen(previo) and it.alineacion == "center"
                alin = alineacion_impresa(it)
                if alin != "both" and it.texto.strip() and it is not u.credito and not pie_de_imagen:
                    self.r.aviso(donde, f"«{recorte(it.texto, 0, 40)}» va {NOMBRE_ALINEACION[alin]} y así se imprimirá; el resto del texto sale justificado.")
                esperado = {18}
                if it is u.credito:
                    esperado = {16}
                elif previo is not None and solo_imagen(previo) and it.alineacion == "center":
                    esperado = {16, 18}
                self.revisar_fuente(it, donde, esperado)
                es_opcion = letra_opcion(it) is not None
                for d in it.dibujos:
                    self.revisar_imagen(d, donde)
                if it.dibujos and not es_opcion and it is not u.cabecera:
                    if it.texto.strip():
                        self.r.error(25, donde, "La imagen comparte el párrafo con texto. En el enunciado y en la lectura la imagen va sola en su párrafo.")
                    elif it.alineacion != "center":
                        self.r.error(25, donde, "La imagen debe ir centrada.")
            previo = it

    def revisar_fuente(self, p, donde, tamanos, en_tabla=False):
        for f in p.fragmentos:
            if not f.texto.strip():
                continue
            if (f.fmt.fuente or "").strip().lower() != "tahoma":
                self.r.error(22, donde, f"«{recorte(f.texto, 0, 30)}» está en {f.fmt.fuente or 'la fuente por defecto'}. Todo el texto va en Tahoma.")
                break
        for f in p.fragmentos:
            if not f.texto.strip():
                continue
            tam = f.fmt.tam or 20
            if tam not in tamanos:
                deb = " u ".join(f"{t / 2:g} pt" for t in sorted(tamanos))
                self.r.error(23, donde, f"«{recorte(f.texto, 0, 30)}» está en {tam / 2:g} pt. {'Dentro de las tablas' if en_tabla else 'Aquí'} va en {deb}.")
                break

    def revisar_imagen(self, dibujo, donde):
        if dibujo.find("wp:anchor", NS) is not None:
            self.r.error(25, donde, "Hay una imagen flotante. Cámbiala a «En línea con el texto» (Formato de imagen › Ajustar texto).")
            return
        if dibujo.find("wp:inline", NS) is None:
            return
        if any(e.tag.endswith("}txbx") or e.tag.endswith("}txbxContent") for e in dibujo.iter()):
            self.r.error(25, donde, "Hay un cuadro de texto. Los rótulos deben ir dentro de la imagen PNG.")
            return
        gd = dibujo.find(".//a:graphicData", NS)
        uri = gd.get("uri", "") if gd is not None else ""
        if not uri.endswith("/picture"):
            tipo = "un gráfico de Word" if "chart" in uri else "una forma o un dibujo de Word"
            self.r.error(25, donde, f"Hay {tipo}. Conviértelo en imagen PNG en escala de grises.")
            return
        ext = dibujo.find(".//wp:extent", NS)
        cx = int(ext.get("cx", 0)) if ext is not None else 0
        ancho_cm = cx / 360000
        medida = f"{ancho_cm:.1f}".replace(".", ",")
        if cx > ANCHO_MAX_EMU:
            self.r.error(25, donde, f"Una imagen mide {medida} cm de ancho. El máximo es 8,4 cm.")
        elif cx > ANCHO_AVISO_EMU:
            self.r.aviso(donde, f"Una imagen mide {medida} cm" + (": es el máximo permitido." if medida == "8,4"
                                                                  else ", cerca del máximo de 8,4 cm."))
        sppr = dibujo.find(".//pic:spPr", NS)
        if sppr is not None:
            efectos = sppr.find("a:effectLst", NS)
            if efectos is not None and len(efectos):
                self.r.error(25, donde, "La imagen tiene efectos de Word (sombra, reflejo, bordes suaves…). Quítalos.")
            ln = sppr.find("a:ln", NS)
            if ln is not None and ln.find("a:noFill", NS) is None and len(ln):
                self.r.error(25, donde, "La imagen tiene un borde de Word. Quítalo.")
        blip = dibujo.find(".//a:blip", NS)
        if blip is None:
            return
        if any(h.tag != q("a:extLst") for h in blip) or any(e.tag.endswith("imgProps") or e.tag.endswith("imgLayer") for e in blip.iter()):
            self.r.error(25, donde, "La imagen tiene ajustes o efectos artísticos de Word (color, brillo, efectos). Restablece la imagen y quítalos.")
        rid = blip.get(q("r:embed"))
        datos, ruta = self.doc.media(rid)
        if datos is None:
            self.r.error(25, donde, "La imagen está vinculada a un archivo externo. Insértala dentro del documento.")
            return
        if not datos.startswith(PNG):
            ext_ = (ruta or "").rsplit(".", 1)[-1].upper()
            self.r.error(25, donde, f"La imagen está en formato {ext_}. Debe ser PNG.")
            return
        try:
            im = Image.open(io.BytesIO(datos))
            im.load()
        except Exception:
            self.r.error(25, donde, "No se pudo leer la imagen PNG; puede estar dañada.")
            return
        recorte_img = dibujo.find(".//a:srcRect", NS)
        visible = 1.0
        if recorte_img is not None:
            visible = 1 - (int(recorte_img.get("l", 0)) + int(recorte_img.get("r", 0))) / 100000
        if cx:
            ppp = im.width * visible / (cx / 914400)
            if ppp < 299.5:
                necesarios = int(cx / 914400 * 300 + 0.999)
                self.r.error(25, donde, f"La imagen tiene {ppp:.0f} ppp a su tamaño en la página. El mínimo es 300 ppp: a {ancho_cm:.1f} cm necesita al menos {necesarios} píxeles de ancho visibles (tiene {round(im.width * visible)}).")
        tiene_alfa = im.mode in ("RGBA", "LA", "PA") or "transparency" in im.info
        if tiene_alfa and im.convert("RGBA").getchannel("A").getextrema()[0] < 255:
            self.r.error(25, donde, "La imagen tiene transparencia. Debe tener fondo blanco sin transparencia.")
        if im.mode not in ("L", "1", "LA", "I", "I;16"):
            rgb = im.convert("RGB")
            if ImageChops.difference(rgb, rgb.convert("L").convert("RGB")).getbbox() is not None:
                self.r.error(25, donde, "La imagen tiene color. Debe estar en escala de grises o blanco y negro.")

    def revisar_tabla(self, t, donde):
        tbl = t.el
        if any(isinstance(x, Tabla) for fila in t.filas for celda in fila for x in celda):
            self.r.error(26, donde, "Hay una tabla dentro de otra tabla. No se permiten tablas anidadas.")
        grid = [int(g.get(W + "w", 0)) for g in tbl.findall("w:tblGrid/w:gridCol", NS)]
        # columnas visibles = celdas de la fila (una celda combinada con gridSpan cuenta como una)
        max_celdas = max((len(tcs) for tcs in t.tcs), default=0)
        if max_celdas > 4:
            self.r.error(26, donde, f"La tabla tiene {max_celdas} columnas. El máximo es 4.")
        anchos = [tc.find("w:tcPr/w:tcW", NS) for tc in t.tcs[0]] if t.tcs else []
        if anchos and all(a is not None and a.get(W + "type") == "dxa" for a in anchos):
            ancho = sum(int(a.get(W + "w", 0)) for a in anchos)
        else:
            ancho = sum(grid)
        if ancho > ANCHO_MAX_TWIPS:
            self.r.error(26, donde, f"La tabla mide {ancho / 567:.1f} cm de ancho. El máximo es 8,4 cm.")
        filas_tr = t.trs
        if any(tr.find("w:trPr/w:cantSplit", NS) is None for tr in filas_tr):
            self.r.error(26, donde, "Marca «No dividir la fila entre páginas» en todas las filas (Propiedades de tabla › Fila).")
        # bordes: los de la tabla o los de su estilo
        estilo = tbl.find("w:tblPr/w:tblStyle", NS)
        capas = [st.find("w:tblPr/w:tblBorders", NS) for st in self.doc.estilos.cadena(estilo.get(W + "val") if estilo is not None else None)]
        capas.append(tbl.find("w:tblPr/w:tblBorders", NS))
        bordes = {}
        for capa in capas:
            if capa is not None:
                for b in capa:
                    bordes[b.tag.split("}")[1]] = b
        def borde_ok(b):
            return (b is not None and b.get(W + "val") == "single" and b.get(W + "sz") == "4"
                    and (b.get(W + "color") or "auto").upper() in ("AUTO", "000000"))
        faltan = [lado for lado in ("top", "left", "bottom", "right", "insideH", "insideV") if not borde_ok(bordes.get(lado))]
        faltan += ["celda" for tcb in tbl.iter(W + "tcBorders") for b in tcb if not borde_ok(b)]
        if faltan:
            self.r.error(26, donde, "Los bordes deben ser sencillos, negros y de 0,5 pt en toda la tabla.")
        # sombreado
        fondos = [s.get(W + "fill") for s in tbl.iter(W + "shd")]
        for st in self.doc.estilos.cadena(estilo.get(W + "val") if estilo is not None else None):
            fondos += [s.get(W + "fill") for s in st.iter(W + "shd")]
        if any(f and f.upper() not in ("AUTO", "FFFFFF") for f in fondos):
            self.r.error(26, donde, "La tabla tiene sombreado de color. El fondo debe ser blanco.")
        # alineación vertical centrada
        celdas = [tc for tcs in t.tcs for tc in tcs]
        if any((tc.find("w:tcPr/w:vAlign", NS) is None or tc.find("w:tcPr/w:vAlign", NS).get(W + "val") != "center") for tc in celdas):
            self.r.error(26, donde, "La alineación vertical de las celdas debe ser centrada.")
        # encabezado y texto
        for i, fila in enumerate(t.filas):
            for celda in fila:
                for p in celda:
                    if not isinstance(p, Parrafo):
                        continue
                    self.revisar_fuente(p, donde, {16}, en_tabla=True)
                    if i == 0 and p.texto.strip() and not all(f.fmt.negrita for f in p.fragmentos if f.texto.strip()):
                        # el centrado lo aplica el sistema al armar la cartilla; la negrita la pone el autor,
                        # porque es lo que distingue el encabezado de una fila de datos
                        self.r.error(26, donde, "La primera fila (encabezado) debe ir en negrita. El centrado lo pone el sistema.")
                    for d in p.dibujos:
                        self.revisar_imagen(d, donde)


def distancia(a, b, tope=3):
    """Distancia de edición (Levenshtein). Si supera el tope, devuelve tope + 1 sin terminar el cálculo."""
    if a == b:
        return 0
    if abs(len(a) - len(b)) > tope:
        return tope + 1
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        if min(cur) > tope:
            return tope + 1
        prev = cur
    return prev[-1]


def validar(datos: bytes, nombre: str, catalogo: CatalogoValidacion | None = None) -> Resultado:
    return Validador(datos, nombre, catalogo or CatalogoValidacion.de_fabrica()).ejecutar()


def analizar(datos: bytes, nombre: str, catalogo: CatalogoValidacion | None = None) -> Validador:
    """Valida y devuelve el validador completo: resultado (.r), estructura leída (.unidad) y documento (.doc)."""
    v = Validador(datos, nombre, catalogo or CatalogoValidacion.de_fabrica())
    v.ejecutar()
    return v
