"""Prompt para pasar un simulacro al formato de carga (Estándar 4B.0).

Un docente llega con un simulacro escrito a su manera —un Word, un PDF, una hoja suelta— y hay que
pasarlo al formato que el validador acepta. Esta pantalla le da el texto listo para pegar en una
inteligencia artificial, con **las reglas exactas** y **los valores que de verdad existen** en el banco.

El prompt no está escrito a mano en ningún archivo: se arma con los catálogos de la base y con lo que
ya se ha cargado, para que no se quede desactualizado cuando se agregue una materia o un grado nuevo.
"""
from sqlalchemy import distinct, select

from app import catalogos_base as base
from app.bd import Ejercicio, Materia, Sesion
from app.validador.validador import ENC_EXCEL, ENC_GLOSARIO, ENC_RESPUESTAS

MAXIMO_EJEMPLOS = 8          # pensamientos o competencias que se listan por materia


def _submaterias(s):
    """{materia: [submaterias]}, en el orden del catálogo."""
    return {m.nombre: [x.nombre for x in m.submaterias] for m in s.scalars(select(Materia).order_by(Materia.id))}


def _en_uso(s):
    """Lo que ya existe en el banco, por (materia, submateria): sirve para marcar lo que está en uso."""
    usados = set()
    for e in s.scalars(select(Ejercicio)):
        usados.add((e.materia, e.submateria or "", "p", e.pensamiento or ""))
        usados.add((e.materia, e.submateria or "", "c", e.competencia or ""))
    return usados


def _lista(valores, materia, sub, tipo, usados):
    """Los valores válidos; marca con ✓ los que ya se usan en el banco."""
    if not valores:
        return "los del plan de área (este sistema no los restringe)"
    return " · ".join(v + (" ✓" if (materia, sub, tipo, v) in usados else "") for v in valores)


def _bloque_materias(s):
    """Materia por materia y submateria por submateria: qué submateria lleva, qué pensamiento y qué competencia."""
    lineas, usados = [], _en_uso(s)
    for materia, subs in _submaterias(s).items():
        regla = base.SUBMATERIA_REGLA.get(materia)
        if subs:
            cola = "obligatoria" if regla is True else "puede ir vacía" if regla is None else "va vacía"
            lineas.append(f"**{materia}** — submateria {cola}:")
            for sub in subs:
                pens, comps = base.pedagogia(materia, sub)
                lineas.append(f"  - Submateria «{sub}»")
                lineas.append(f"      Pensamiento: {_lista(pens, materia, sub, 'p', usados)}")
                lineas.append(f"      Competencia: {_lista(comps, materia, sub, 'c', usados)}")
        else:
            pens, comps = base.pedagogia(materia)
            lineas.append(f"**{materia}** — submateria **vacía**")
            lineas.append(f"      Pensamiento: {_lista(pens, materia, '', 'p', usados)}")
            lineas.append(f"      Competencia: {_lista(comps, materia, '', 'c', usados)}")
    return chr(10).join(lineas)


def texto():
    """El prompt completo, listo para copiar y pegar."""
    with Sesion() as s:
        grados = " · ".join(g for g, _, _ in base.GRADOS)
        materias = _bloque_materias(s)
        primaria = ", ".join(m for m, v in base.SUBMATERIA_REGLA_PRIMARIA.items() if v is False)
    return PLANTILLA.format(
        grados=grados, materias=materias, primaria=primaria,
        niveles=" · ".join(base.NIVELES),
        dba_ingles=chr(10).join("  - " + x for x in base.DBA_INGLES_6),
        enc_respuestas=" | ".join(ENC_RESPUESTAS),
        enc_excel=" | ".join(ENC_EXCEL),
        enc_glosario=" | ".join(ENC_GLOSARIO))


PLANTILLA = """Eres un asistente que prepara ejercicios para el sistema de cartillas de PRAXIS – THINKS.

Te voy a dar un simulacro (preguntas de opción múltiple, de cualquier materia y grado). Tu trabajo es
devolvérmelo **en el formato exacto de carga**, un archivo por ejercicio, para que yo lo copie en Word y lo
suba a la página. No cambies el contenido pedagógico de las preguntas: solo ordénalas en este formato y
completa los datos que faltan.

══════════════════════════════════════════════════════════════════════
1. QUÉ ME TIENES QUE DEVOLVER
══════════════════════════════════════════════════════════════════════

Un bloque por ejercicio, separados por una línea con «-----», y cada bloque con esta forma:

ARCHIVO: Ejercicio_001.docx
<contenido tal como va en el Word>

Hay tres formas de ejercicio. Usa la que corresponda:

**A. Ejercicio suelto** (una sola pregunta, se vale sola):

    [Enunciado. SIN número de pregunta: lo pone el sistema. Puede ocupar varios párrafos.]
    [La pregunta, en el último párrafo del enunciado, terminada en «?».]
    A. [opción, en un solo párrafo]
    B. [opción, en un solo párrafo]
    C. [opción, en un solo párrafo]
    D. [opción, en un solo párrafo]

    TABLA DE RESPUESTAS
    | {enc_respuestas} |
    |    | B | Por qué esa es la correcta, en una o dos frases, sin nombrar ninguna letra |

    TABLA DE EXCEL
    | {enc_excel} |
    |       | B | 6° | ... | ... | ... | ... | DBA 3 | ... | Medio |

    TABLA DE GLOSARIO   (opcional, máximo 3 términos por pregunta)
    | {enc_glosario} |
    | 1 | palabra difícil que APARECE en el texto de esa pregunta | explicación corta, máx. 150 caracteres |

    En el glosario **sí se pueden escribir fórmulas**: superíndices, subíndices y ecuaciones del editor de
    Word (i² = −1, H₂O, a²+b²=c²). Lo que no se puede meter ahí son imágenes ni objetos incrustados.

    **Los encabezados van escritos exactamente así, con esas tildes y esos puntos.**
    **La primera columna de RESPUESTAS (N°) y la de EXCEL (Preg.) van VACÍAS**: el número lo pone el
    sistema al armar la cartilla. En el GLOSARIO sí va el número de la pregunta dentro del archivo (1, 2, 3…).
    Una fila de datos por pregunta, en el mismo orden en que van las preguntas.

**B. Bloque de lectura** (varias preguntas que dependen de un mismo texto, tabla o gráfica):

    Responde las preguntas #N a #M de acuerdo con la siguiente lectura.
    [El texto o recurso compartido.]
    [Crédito del recurso. OBLIGATORIO, último párrafo del recurso, en cursiva y alineado a la derecha.]
    [Enunciado de la primera pregunta…]  + sus opciones A, B, C, D
    [Enunciado de la segunda pregunta…]  + sus opciones A, B, C, D
    …
    (y al final, las tres tablas, con una fila por pregunta)

    Deja «#N» y «#M» tal cual: los números los pone el sistema.

**C. Parte de Inglés** (un conjunto con título propio):

    PARTE #P · [Título de la parte] — preguntas #N a #M
    (igual que el bloque de lectura; deja «#P», «#N» y «#M» tal cual)

══════════════════════════════════════════════════════════════════════
2. REGLAS QUE EL VALIDADOR NO PERDONA
══════════════════════════════════════════════════════════════════════

**La pregunta**
1.  Exactamente **cuatro opciones**: A, B, C y D. Ni tres ni cinco.
2.  **Una opción = un párrafo**. Nunca dos opciones en la misma línea.
3.  La opción empieza por la letra, un punto y un espacio: «A. ».
4.  El enunciado **no lleva número**: ningún párrafo puede empezar por «1.», «2.»… El sistema numera.
5.  El último párrafo del enunciado es **la pregunta** y termina en «?».
6.  Nada de «todas las anteriores», «ninguna de las anteriores», «A y B son correctas», «la primera
    opción» ni opciones que se refieran a otras: al armar la cartilla el orden de las opciones cambia.
7.  Las cuatro opciones deben ser **verosímiles** y del mismo estilo y longitud aproximada.
8.  Una sola respuesta correcta. La Clave de RESPUESTAS y la columna Correcta de EXCEL deben decir lo mismo.
9.  **La justificación no puede nombrar letras de opción** («porque la B dice…»). Explica por qué el
    contenido es correcto, sin decir cuál letra: al barajar las opciones esa letra cambia.

**Las tablas**
10. Los rótulos **TABLA DE RESPUESTAS**, **TABLA DE EXCEL** y **TABLA DE GLOSARIO** van escritos tal cual,
    en mayúsculas, cada uno en su propio párrafo antes de su tabla.
11. En un bloque o en una parte, **todas las filas** llevan el mismo Grado, Materia y Submateria.
12. En el glosario, el término tiene que **aparecer en el texto de esa pregunta**, con 40 caracteres como
    máximo, y su significado con 150 como máximo. Hasta 3 términos por pregunta.

**El archivo**
13. El crédito del recurso es **obligatorio** en los bloques de lectura y en las partes de Inglés, y
    **está prohibido** en un ejercicio suelto. Va en el último párrafo del recurso, en cursiva y alineado
    a la derecha.
14. Una sola fuente en todo el archivo y un solo tamaño de letra. **Sin viñetas ni numeración automática**
    de Word: si hay que numerar algo, escribe el número a mano.
15. Nada de comentarios, notas para el autor, «TODO», ni control de cambios.
16. Las fórmulas y los símbolos van con **superíndice y subíndice de verdad** (H₂O, m², 10³), no como
    texto plano ni como imagen. Nada de objetos incrustados.
17. Las imágenes van **solas en su párrafo**, centradas, en línea con el texto y de 8,4 cm como máximo.
    Nunca una imagen en el mismo párrafo que el texto. Sin tablas dentro de otras tablas.
18. Página carta (21,59 × 27,94 cm), vertical.

══════════════════════════════════════════════════════════════════════
3. VALORES QUE PUEDES USAR (son los del sistema; no inventes otros)
══════════════════════════════════════════════════════════════════════

**Grado**: {grados}

**Nivel**: {niveles} — obligatorio, y reparte: la mayoría en Medio, y algunas en Básico y en Avanzado.
**Excepción:** en grado ICFES el Nivel va **vacío**; si lo llenas, el archivo se rechaza.

**Materias, submaterias, pensamiento y competencia.** El pensamiento depende de la **submateria**, no solo
de la materia. Escribe los valores **exactamente** como están aquí; los marcados con ✓ ya se usan en el banco.

{materias}

En 3°, 4° y 5°, {primaria} van **sin submateria**.

**Filosofía y Ciencias Económicas y Políticas.** Filosofía es una materia propia y Ciencias Económicas y
Políticas es una submateria de Ciencias Sociales. Si el simulacro las trae escritas de otra forma, el
sistema las entiende igual, así que respeta lo que diga el original. En las materias sin DBA oficial
(Filosofía, Ética, Informática, Educación Física, Educación Artística, Religión) deja el DBA vacío.

**DBA**: toma el número de la **malla del grado** y escríbelo como «DBA 4». Si la malla da varios DBA para el
mismo tema, elige el que corresponde al contenido de esa pregunta. Si no lo sabes con certeza, déjalo vacío:
es preferible vacío a equivocado.

Los DBA de **Inglés de 6°** (MEN) son estos:
{dba_ingles}

**Temática**: **obligatoria**, es el filtro principal del buscador. El tema concreto de la pregunta, en una
frase corta y específica, por ejemplo «Comparación de
fracciones con distinto denominador» o «Células procariotas y eucariotas». Es lo que después se usa para
buscar los ejercicios, así que sé preciso y usa siempre la misma redacción para el mismo tema.
**Si el simulacro ya trae la temática y el contenido de la pregunta no cambia, consérvala tal cual.**

══════════════════════════════════════════════════════════════════════
4. SI EL ARCHIVO YA TRAE LA INFORMACIÓN  ← LO MÁS IMPORTANTE
══════════════════════════════════════════════════════════════════════

La mayoría de los simulacros **ya vienen con todo**: la clave, la justificación y los datos pedagógicos.
En ese caso **no inventes ni cambies nada**: tu trabajo es solo reorganizarlo. Un dato inventado donde ya
había uno bueno es el peor error que puedes cometer.

Dónde suele estar cada cosa:

| Dato | De dónde lo tomas |
|---|---|
| Clave y justificación | la tabla del final, titulada «Clave de respuestas» o parecido |
| Materia, submateria, pensamiento, competencia, DBA, temática y nivel | la otra tabla del final, «Tabla para Excel» o parecido |
| Grado | la cabecera del archivo («Ciencias Sociales · Grado 6° · Preguntas 1-30»); esa tabla casi nunca lo trae |
| Pensamiento, competencia, DBA y nivel | también en la **línea ➤** que va debajo de cada pregunta |
| Glosario | muchas veces en un **archivo aparte**: una línea por pregunta, con el número, el término en negrita y su significado, separados por « · » |

Qué tienes que hacer con eso:

1.  **Copia los valores tal cual**, con la misma redacción. No los traduzcas, no los resumas, no los
    «mejores». Si la temática ya viene escrita, consérvala exactamente.
2.  **Vacía las columnas N° y Preg.**: en el archivo original vienen numeradas 1, 2, 3… y aquí van vacías.
3.  **Agrega la columna Grado** si la tabla original no la trae, con el grado de la cabecera.
4.  **Borra la línea ➤** de cada pregunta. Es lo que imprime la cartilla, no algo que se cargue: esos datos
    ya van en la TABLA DE EXCEL. Si la dejas, el validador la lee como **una segunda pregunta sin opciones**
    y rechaza el archivo.
5.  **Quita el número del comienzo del enunciado** («1. En un resguardo…» queda «En un resguardo…»).
6.  Cambia los rótulos de las tablas a **TABLA DE RESPUESTAS**, **TABLA DE EXCEL** y **TABLA DE GLOSARIO**,
    y pon los encabezados exactos de arriba (el original suele traer otros).
7.  Si el **nivel** viene abreviado —BB, MM, AA— escríbelo completo: Básico, Medio, Avanzado.
8.  Si el **DBA** viene vacío, déjalo vacío. No lo adivines.
9.  Si la **justificación menciona letras** («la opción B dice…»), reescríbela sin nombrarlas, diciendo lo
    mismo. Es el único dato que sí tienes que retocar.
10. El **glosario del archivo aparte** se reparte: los términos de la pregunta 7 van en la TABLA DE GLOSARIO
    del archivo que contenga esa pregunta, con el número que tenga **dentro de ese archivo** (si la pregunta
    7 quedó sola en su archivo, es la 1; si quedó segunda de un bloque, es la 2).
11. Las preguntas que **comparten** un texto, una tabla o una imagen van juntas en un bloque de lectura, con
    ese recurso una sola vez al principio. Si el recurso **no trae crédito**, escríbele uno —por ejemplo
    «Elaboración propia. PRAXIS – THINKS, 2026.»— porque en los bloques es obligatorio.

Antes de darme cada archivo, repásalo contra la lista de reglas del punto 2.

══════════════════════════════════════════════════════════════════════
5. CÓMO TRABAJAR
══════════════════════════════════════════════════════════════════════

- Si el simulacro **no** trae clave ni justificación, dedúcelas y escríbelas tú (si las trae, punto 4).
- Si una pregunta incumple alguna regla (tiene cinco opciones, dice «todas las anteriores», no termina en
  «?»), **corrígela** y avísame al final en una lista de «cambios que hice».
- Si una pregunta depende de un texto, una imagen o una tabla compartidos, agrúpala en un bloque de lectura
  con las demás que dependan de lo mismo. Nunca dejes un bloque de una sola pregunta.
- Si hay imágenes, déjalas indicadas así: «[IMAGEN: descripción de lo que debe ir aquí]», en su propio
  párrafo, y yo las pego en el Word.
- Al final, dime cuántos ejercicios quedaron de cada materia y de cada nivel.

Empieza cuando te pase el simulacro."""
