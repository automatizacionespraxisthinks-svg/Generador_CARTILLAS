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
from app.validador.validador import (ENC_EXCEL, ENC_GLOSARIO, ENC_RESPUESTAS, FUENTE, MARGEN_CM,
                                     MAX_ANCHO_CM, MAX_COLUMNAS_TABLA, PPP_MINIMO, TAM_CHICO,
                                     TAM_TEXTO)

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
        enc_glosario=" | ".join(ENC_GLOSARIO),
        pagina="21,59 × 27,94 cm", margen=f"{MARGEN_CM:g}".replace(".", ","),
        fuente=FUENTE, tam_texto=TAM_TEXTO, tam_chico=TAM_CHICO,
        max_col=MAX_COLUMNAS_TABLA, max_ancho=f"{MAX_ANCHO_CM:g}".replace(".", ","), ppp=PPP_MINIMO)


PLANTILLA = """Eres un asistente que prepara ejercicios para el sistema de cartillas de PRAXIS – THINKS.

Te voy a dar un simulacro (preguntas de opción múltiple, de cualquier materia y grado). Tu trabajo es
devolvérmelo **en el formato exacto de carga**, un archivo por ejercicio, para que yo lo copie en Word y lo
suba a la página. No cambies el contenido pedagógico de las preguntas: solo ordénalas en este formato y
completa los datos que faltan.

Estos ejercicios **se van a volver a usar durante años**, así que sé estricto con la calidad: un archivo mal
armado se rechaza al subirlo y hay que rehacerlo entero.

**Antes de empezar, dime en una línea:** el **grado** y la **materia** (y la submateria, si la lleva) que
detectaste en el simulacro, y con qué valores de pensamiento y competencia vas a trabajar, tomados del
punto 5. Si el simulacro mezcla materias o grados, dilo y sepáralos. Así yo confirmo antes de que empieces,
y no se pierde el trabajo.

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

    Si las opciones **son figuras** («¿en cuál de estos rectángulos está sombreada la fracción?»), la
    figura va en el **mismo párrafo** que su letra, detrás de ella: «A. [IMAGEN: …]». Es el único sitio
    donde una imagen comparte párrafo con texto; en el enunciado y en la lectura va siempre sola.

    TABLA DE RESPUESTAS
    | {enc_respuestas} |
    |    | B | Por qué esa es la correcta, en una o dos frases, sin nombrar ninguna letra |

    TABLA DE EXCEL
    | {enc_excel} |
    |       | B | 6° | ... | ... | ... | ... | DBA 3 | ... | Medio |

    TABLA DE GLOSARIO   (opcional, máximo 3 términos por pregunta)
    | {enc_glosario} |
    | 1 | palabra difícil que APARECE en el texto de esa pregunta | explicación corta, máx. 150 caracteres |

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
    [La instrucción de la parte, en un solo párrafo.]
    [El recurso: la lectura, el diálogo o el texto con espacios.]
    [Crédito del recurso. OBLIGATORIO, igual que en el bloque de lectura.]
    (luego las preguntas y, al final, las tres tablas)

    Deja «#P», «#N» y «#M» tal cual: los números los pone el sistema.

    **Si la parte es de «completar el texto»**, hay dos reglas más:
    - los espacios del texto se marcan **(#1), (#2), (#3)…**, uno por pregunta, en orden y dentro del
      recurso, nunca fuera;
    - esas preguntas **van sin enunciado**: debajo del texto va solo la letra con su opción.

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
14. **Sin viñetas ni numeración automática** de Word: si hay que numerar algo, escribe el número a mano.
15. Nada de comentarios, notas para el autor, «TODO», ni control de cambios.
16. Las fórmulas van con el **editor de ecuaciones de Word** o con superíndices y subíndices de verdad
    (ver el punto 3, que es donde se explica con detalle). Nada de objetos incrustados ni de capturas.
17. Las imágenes van **solas en su párrafo**, centradas y en línea con el texto. La única excepción son
    las opciones que son figuras: ahí la imagen va detrás de su letra, en el mismo párrafo.
18. Las tablas de control van **al final y en este orden**: RESPUESTAS, EXCEL y GLOSARIO. Entre ellas y
    después de la última **no puede quedar nada**: ni un párrafo suelto, ni una nota, ni un espacio.

**La ficha técnica del archivo** (es lo que más rechazos produce, y no se adivina)

| Qué | Cómo tiene que estar |
|---|---|
| Página | Carta, {pagina}, **vertical** |
| Márgenes | **{margen} cm** por los cuatro lados: en Word, Márgenes › Estrecho |
| Columnas | **Una sola**. El documento de carga nunca va a dos columnas; eso lo hace la cartilla |
| Fuente | **{fuente}** en todo el archivo, sin excepción |
| Tamaño | **{tam_texto} pt** en el enunciado y las opciones · **{tam_chico} pt** dentro de las tablas, en la línea de crédito y en el pie de una imagen |
| La letra de la opción | «A. » con la **letra y el punto en negrita**, y el resto de la opción normal |
| Tablas del contenido | Máximo **{max_col} columnas** y **{max_ancho} cm** de ancho · encabezado en negrita · todas las celdas centradas verticalmente · marcada «No dividir la fila entre páginas» · sin tablas anidadas · sin tablas dentro de las opciones |
| Imágenes | **PNG**, mínimo **{ppp} ppp** al tamaño en que se ven, máximo **{max_ancho} cm** de ancho, fondo blanco **sin transparencia**, en línea con el texto · sin bordes, sombras ni efectos de Word · sin cuadros de texto: los rótulos van dentro del PNG |

══════════════════════════════════════════════════════════════════════
3. LAS MATEMÁTICAS SE ESCRIBEN CON EL EDITOR DE ECUACIONES
══════════════════════════════════════════════════════════════════════

Esto es lo que más se hace mal y lo que más se nota al imprimir. La cartilla tiene que verse **como un
libro de texto**: las fracciones apiladas, las raíces con su signo y su barra, los exponentes arriba.

En Word: **Insertar › Ecuación** (o Alt + «=»). La ecuación va **en la misma línea del texto**, nunca como
imagen aparte ni como captura de pantalla.

**El validador lo exige: un archivo con «³/₈», «√49» o «x^2» se RECHAZA** y no entra al banco.
Arréglalo **antes** de subirlo, no después.

**Las fracciones.** Lo que importa es que se lean con claridad:

| Cómo la escribes | Qué pasa |
|---|---|
| apilada, con el editor de ecuaciones: el 3 sobre el 8 | **así es como la quiero** |
| «3/8» a tamaño normal | se acepta: se lee grande y sin esfuerzo |
| «³/₈» con el numerador arriba pequeño y el denominador abajo pequeño | **se rechaza**: sale diminuta |

Dentro de una expresión más larga (una ecuación, una fracción dentro de otra, una potencia de una
fracción) la fracción va **siempre apilada**: con barra no se entendería dónde empieza y dónde termina.

**Va con el editor de ecuaciones, siempre:**

- Raíces: **nunca** «√25» con el carácter suelto; la raíz lleva su barra sobre todo el radicando, y la
  raíz cúbica o enésima lleva su índice.
- Números mixtos: dos y un cuarto se escribe con la fracción apilada al lado del entero.
- Potencias con variable o con expresión en el exponente, ecuaciones, sistemas de ecuaciones, matrices,
  sumatorias, integrales, límites y desigualdades compuestas.
- Cualquier expresión que ocupe dos alturas (algo arriba y algo abajo).

**Va con superíndice y subíndice de Word, sin editor de ecuaciones:**

- Unidades y potencias sencillas dentro de una frase: m², cm³, 10³, x².
- Fórmulas químicas: H₂O, CO₂, C₆H₁₂O₆.
- Grados y ordinales: 25 °C, 1.°

**Se escribe como texto normal (no es una fórmula):**

- Las razones y proporciones en prosa: «3 de cada 8 estudiantes», «la razón es de 3 a 8».
- Los porcentajes y los decimales: 37,5 %, 0,375.
- Los números de respuesta cuando no llevan fracción ni raíz: 24, −6, 1 250.

**Del tamaño no te preocupes.** Inserta la ecuación y déjala como venga: al armar la cartilla el sistema
le pone el tamaño del texto que la rodea, de modo que la fracción se lee igual de grande que la frase en
la que está. No la agrandes a mano ni le cambies la fuente; si lo haces, se pierde al generar.

**Tres reglas que no se pueden saltar:**

19. La **misma expresión se escribe igual en todas partes**: si en el enunciado la fracción va apilada,
    en las cuatro opciones va apilada. Mezclar «3/8» en una opción y la fracción apilada en otra hace que
    el estudiante crea que son cosas distintas.
20. En el **glosario sí se admiten fórmulas**: superíndices, subíndices y ecuaciones del editor de Word
    (i² = −1, a² + b² = c²). Lo que no se puede meter ahí son imágenes ni objetos incrustados.
21. Nunca una fórmula **como imagen**. Si el original la trae como imagen, vuélvela a escribir con el
    editor de ecuaciones.

══════════════════════════════════════════════════════════════════════
4. CALIDAD DE LA PREGUNTA Y DE LA PRESENTACIÓN
══════════════════════════════════════════════════════════════════════

**La pregunta**

- El enunciado da **todo lo necesario** para responder y nada más: sin datos de adorno que no se usan.
- La situación es **concreta y verosímil**, con nombres y cantidades realistas del contexto colombiano.
- Las cuatro opciones miden lo mismo: una correcta y **tres errores que un estudiante cometería de
  verdad** (confundir el orden de una operación, invertir una relación, quedarse a mitad del
  procedimiento). Nada de opciones absurdas que se descartan de un vistazo.
- Las cuatro opciones tienen **largo parecido**: si la correcta es siempre la más larga, se adivina.
- Ordena las opciones con un criterio: de menor a mayor si son números, cronológico si son fechas.
- La justificación explica **por qué el contenido es correcto**, no por qué las otras están mal, y cabe
  en una o dos frases.

**El texto**

- Párrafos **justificados**. No uses saltos de línea a mano para cuadrar el texto ni espacios repetidos
  para alinear: la cartilla va a dos columnas y todo eso se desbarata.
- Sin sangrías manuales, sin tabulaciones y sin párrafos vacíos entre las opciones.
- Revisa la ortografía y la tildación. Lo que escribas se imprime tal cual.

**Las imágenes**

- Nítidas y con el texto legible **a 8,4 cm de ancho**, que es el ancho de una columna. Si es una gráfica
  con rótulos diminutos, no sirve: hay que rehacerla.
- Sin marcas de agua, sin bordes blancos sobrantes, sin capturas de pantalla con el fondo de la ventana.
- **El color se admite** desde el 07/11/2026, en las imágenes, en el texto y en las celdas de una tabla.
  Úsalo cuando el ejercicio lo necesite —banderas, mapas, reacciones químicas, gráficas de varias
  series—, porque esas cartillas se mandan a imprimir a color. Si el color no aporta nada, déjalo en
  gris: sale más barato de imprimir.
- Lo único que no vale es lo que no se vería sobre el papel: **texto casi blanco** y **celdas casi
  negras**. Y el **resaltado** de Word sigue prohibido: es una marca de trabajo, no contenido.
- Una sola imagen por párrafo, centrada y en línea con el texto.

**Las tablas**

- Con **bordes visibles** (estilo «Tabla con cuadrícula») y **una fila de encabezado** con los títulos.
- Sin tablas anidadas y sin celdas combinadas en los datos.
- Lo más estrechas posible: en la cartilla caben en 8,4 cm. Si tiene muchas columnas, divídela o
  reescríbela como texto.
- Los números y las palabras cortas los centra el sistema solo: no te preocupes por eso.

══════════════════════════════════════════════════════════════════════
5. VALORES QUE PUEDES USAR (son los del sistema; no inventes otros)
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

**Cuidado con Ciencias Sociales en 10° y 11°.** No todo lo de Ciencias Sociales es Ciencias Económicas y
Políticas. La historia, la geografía, la Constitución y la democracia van con la **submateria vacía**;
solo lleva «Ciencias Económicas y Políticas» lo que trate de economía, mercado, Estado o sistemas
políticos. Marcarlo todo como Económicas y Políticas deja sin ejercicios la sección de Ciencias Sociales
de esos grados y la cartilla no se puede armar.

**DBA**: toma el número de la **malla del grado** y escríbelo como «DBA 4»; si de verdad son varios,
sepáralos con coma: «DBA 3, DBA 5». Si la malla da varios para el mismo tema, elige el que corresponde al
contenido de esa pregunta. Si no lo sabes con certeza, déjalo vacío: es preferible vacío a equivocado.

Los DBA de **Inglés de 6°** (MEN) son estos:
{dba_ingles}

**Temática**: **obligatoria**, y es el filtro principal del buscador. Aquí se equivoca casi todo el mundo,
así que léelo con cuidado.

La temática tiene que ser **explicada y precisa**: al leerla, quien arma la cartilla debe saber qué evalúa
esa pregunta **sin abrirla**, y poder decidir si le sirve para una prueba concreta. Prefiero una temática
larga y clara antes que una etiqueta corta y ambigua.

- Dice **qué contenido** se evalúa y **qué se hace con él** (comparar, clasificar, calcular, interpretar).
- Si hace falta para distinguirla de otra parecida, añade la condición: «con distinto denominador»,
  «en el plano cartesiano», «a partir de una tabla de datos».
- Escríbela como una frase, **sin punto final** y con 150 caracteres como máximo.
- No metas los nombres propios ni las cantidades del enunciado: «Valeria», «36 estudiantes», «5⁄12» no
  van en la temática. El contexto sí; los datos concretos no.
- Si varias preguntas evalúan **exactamente** lo mismo, escríbeles la **misma temática, letra por letra**.

| Así SÍ | Así NO (demasiado vago) | Así NO (es el enunciado) |
|---|---|---|
| Adición de fracciones con distinto denominador | Fracciones | Andrés se comió 3 de 8 porciones de pizza |
| Potencias de la unidad imaginaria y su ciclo de cuatro valores | Números complejos | Ciclo de las potencias de i cuando el exponente es 7 |
| Ramas del poder público y sus funciones | Sociales | Destierro de un ciudadano por exceso de poder en Atenas |
| Diferencias entre células procariotas y eucariotas | Células | Comparación entre la bacteria del yogur y una célula de cebolla |

**Si el simulacro ya trae la temática y el contenido de la pregunta no cambia, consérvala tal cual.**

══════════════════════════════════════════════════════════════════════
6. SI EL ARCHIVO YA TRAE LA INFORMACIÓN  ← LO MÁS IMPORTANTE
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

Antes de darme cada archivo, repásalo contra las reglas del punto 2 y las de los puntos 3 y 4.

══════════════════════════════════════════════════════════════════════
7. CÓMO TRABAJAR
══════════════════════════════════════════════════════════════════════

- Si el simulacro **no** trae clave ni justificación, dedúcelas y escríbelas tú (si las trae, punto 6).
- Si una pregunta incumple alguna regla (tiene cinco opciones, dice «todas las anteriores», no termina en
  «?»), **corrígela** y avísame al final en una lista de «cambios que hice».
- Si una pregunta depende de un texto, una imagen o una tabla compartidos, agrúpala en un bloque de lectura
  con las demás que dependan de lo mismo. Nunca dejes un bloque de una sola pregunta.
- Si hay imágenes, déjalas indicadas así: «[IMAGEN: descripción de lo que debe ir aquí]», en su propio
  párrafo, y yo las pego en el Word.
- Al final, dime cuántos ejercicios quedaron de cada materia y de cada nivel.

**Lista de chequeo: pásala a cada archivo antes de dármelo.** Si algo falla, el sistema lo rechaza entero.

1.  Cuatro opciones A, B, C y D, cada una en su párrafo, ninguna dependiente de otra.
2.  El enunciado no empieza por un número y su último párrafo termina en «?».
3.  Ninguna fracción diminuta («³/₈»), ninguna «√» suelta, ningún «^».
4.  La misma expresión escrita igual en el enunciado y en las cuatro opciones.
5.  Los tres rótulos de tabla escritos tal cual, con los encabezados exactos y las columnas N° y Preg. vacías.
6.  La justificación no nombra ninguna letra.
7.  Grado, materia, submateria, pensamiento y competencia salen de las listas del punto 5, escritos igual.
8.  La temática explica qué evalúa la pregunta y no trae nombres ni cantidades del enunciado.
9.  Sin la línea ➤, sin viñetas automáticas, sin control de cambios, una sola fuente y un solo tamaño.
10. En los bloques y las partes, el crédito del recurso está puesto; en los ejercicios sueltos, no hay.

Empieza cuando te pase el simulacro."""
