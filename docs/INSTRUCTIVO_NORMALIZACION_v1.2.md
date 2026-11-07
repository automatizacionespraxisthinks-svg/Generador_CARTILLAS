# INSTRUCTIVO DE NORMALIZACIÓN · v1.2
## Para pasar a Claude antes de subir ejercicios al sistema

> Copie todo el texto que está entre las líneas y péguelo como instrucción, junto con el ejercicio que va a normalizar.
> Base: `ESTANDAR_PRAXIS_v1.2.md`. Plantillas: `PLANTILLA_CARGA_1_EJERCICIO_v1.2.docx`, `PLANTILLA_CARGA_2_BLOQUE_LECTURA_v1.2.docx`, `PLANTILLA_CARGA_3_PARTE_INGLES_v1.2.docx`.

---

Vas a normalizar un ejercicio de selección múltiple para cargarlo a un sistema que arma cuadernillos tipo ICFES. El sistema copia el contenido del Word tal cual, sin reinterpretarlo, y **rechaza cualquier archivo que no cumpla estas reglas de forma exacta**.

> **Si lo que tienes es un simulacro completo** (veinte o treinta preguntas en un solo archivo, con sus tablas de clave y de datos al final), no uses este instructivo pregunta por pregunta: en el **Panel** del sistema hay un texto preparado para eso, con el botón «Copiar el texto». Ese reparte el simulacro en un archivo por ejercicio, agrupa los bloques y traslada los datos que el archivo ya trae.

> **Si el ejercicio viene de una cartilla ya impresa**, debajo de cada pregunta habrá una línea que empieza con **➤** (por ejemplo `➤ Relaciones ético-políticas // Culturalidad // DBA 8 // MM`). **Bórrala.** Esa línea la imprime la cartilla, no se carga: sus datos van en la TABLA DE EXCEL. Si se queda, el sistema la lee como una segunda pregunta sin opciones y rechaza el archivo.

## Qué tipo de archivo es

Cada archivo contiene **una sola** de estas unidades. El sistema la reconoce por el primer párrafo:

| Unidad | Primer párrafo |
|---|---|
| Ejercicio suelto | Directamente el enunciado |
| Bloque de lectura compartida | `Responde las preguntas #N a #M de acuerdo con la siguiente lectura.` (o `…siguiente información.`) |
| Parte de Inglés | `PARTE #P · [Título] — preguntas #N a #M` |

Si dos o más preguntas usan la misma lectura, tabla o gráfica, **deben** ir como bloque.

## Estructura del archivo

**Ejercicio suelto**

1. Enunciado y pregunta
2. Opciones A, B, C, D
3. El rótulo `TABLA DE RESPUESTAS` y su tabla
4. El rótulo `TABLA DE EXCEL` y su tabla
5. Opcional: el rótulo `TABLA DE GLOSARIO` y su tabla

**Bloque de lectura compartida**

1. Frase de referencia, en negrita
2. La lectura o el recurso, en uno o varios párrafos
3. **La línea de crédito (obligatoria)**: último párrafo del recurso, alineado a la derecha, todo en cursiva, 8 pt. Si no hay autor externo: `Texto elaborado para este simulacro. PRAXIS · THINKS.`
4. Las preguntas, una tras otra, cada una con sus cuatro opciones (mínimo 2 preguntas)
5. Las dos tablas, con una fila por pregunta, en orden
6. Opcional: la `TABLA DE GLOSARIO`

**Parte de Inglés**

1. Subtítulo en negrita: `PARTE #P · [Título de la parte] — preguntas #N a #M`
2. La instrucción de la parte: **exactamente un párrafo**
3. Si hay texto o recurso compartido: el recurso y su línea de crédito. Si no hay recurso, no se pone línea de crédito
4. Las preguntas con sus opciones (mínimo 2). Aquí el enunciado **puede ir vacío** y no necesita `?`
5. Las dos tablas, con una fila por pregunta
6. Opcional: la `TABLA DE GLOSARIO`

**Partes de «completar el texto»:** en el texto, cada espacio se marca con `(#1)`, `(#2)`, `(#3)`… en orden, uno por pregunta. Nunca escribas el número real: el sistema lo pone. Las preguntas de estas partes van sin enunciado, solo con sus cuatro opciones. Los avisos de «Avisos y anuncios» van como imagen PNG.

Los rótulos `TABLA DE RESPUESTAS`, `TABLA DE EXCEL` y `TABLA DE GLOSARIO` van en negrita, en mayúsculas, en párrafo propio, escritos exactamente así. `#P`, `#N` y `#M` se dejan tal cual: **nunca** escribas números ahí.

## Formato del documento

- Página carta, vertical, márgenes de 1,27 cm en los cuatro lados
- Una sola columna
- Fuente **Tahoma** en todo el texto (solo las ecuaciones del editor van en Cambria Math). Los símbolos (θ, π, ≤, →) se escriben en Tahoma, no con Insertar › Símbolo en la fuente Symbol
- Guarda como «Documento de Word (.docx)», no como «Documento Open XML strict»
- **9 pt** en el texto; **8 pt** solo dentro de tablas, en la línea de crédito y en el pie de una imagen
- Texto **negro**. Ningún otro color
- Sin resaltado, sin comentarios, sin control de cambios, sin texto oculto
- Sin viñetas ni numeración automática de Word: si hace falta numerar, escribe `I.`, `1.` o `•` como texto
- El espaciado entre párrafos no importa: lo pone el sistema
- El texto va **justificado** (así viene en las plantillas v1.2). Si un párrafo debe ir a la izquierda, centrado o a la derecha (un poema, una cita, un diálogo), aplícalo con los botones de alineación de Word: el sistema lo conserva y te avisa cuáles son. Trabaja siempre sobre las plantillas v1.2: en las anteriores, «a la izquierda» no queda registrado y sale justificado
- Para versos, usa **Mayús + Enter** al final de cada línea: la cartilla no estira esas líneas
- Si pegas texto de otra fuente, usa **Pegar › Mantener solo texto**, para no arrastrar alineaciones ni formatos ajenos
- Los hipervínculos y las referencias cruzadas se imprimen como texto normal, tal como se ven en tu Word (en negro, sin subrayado)

## Enunciado

- **No escribas el número de la pregunta.** Ningún párrafo puede empezar con `12. `, `3) ` o `5- `.
- No incluyas referencias a otros números de pregunta: «(ejercicio 53)», «ver pregunta 12», «la pregunta anterior».
- No incluyas referencias de posición: «la tabla de arriba», «la imagen de la izquierda». Usa «la siguiente tabla», «la imagen».
- **No dejes texto de trabajo, notas ni instrucciones.** Todo lo que quede se imprime. Están prohibidos los textos de plantilla entre corchetes (`[texto de la opción]`; un intervalo como `[0, 1]` sí vale) y estas frases escritas exactamente así: `Qué NO debe aparecer`, `Nota para`, `NOTA:`, `TODO`, `PENDIENTE`, `REVISAR`, `BORRAR`.
- La pregunta va en el **último párrafo del enunciado** y termina en `?` (salvo en Inglés).

## Opciones

- Siempre cuatro, siempre `A.`, `B.`, `C.`, `D.`, en ese orden.
- La letra y el punto en **negrita**, seguidos de un espacio.
- **Cada opción ocupa exactamente un párrafo.** No partas una opción en dos párrafos.
- Si la opción es una imagen, la imagen va **en el mismo párrafo**, después de `A. `. Cuatro imágenes separadas, una por opción; nunca una sola imagen con las cuatro letras.
- No se permiten tablas en las opciones.
- Las opciones deben poder intercambiarse, porque el sistema las reordena. Están prohibidas: «A y B son correctas», «Ninguna de las anteriores», «Todas las anteriores», y opciones que terminan en «la anterior», ni «la primera opción» o «la última opción».

## Matemáticas y notación

- **Superíndices y subíndices** (x², H₂O, cos²θ) con el formato de texto de Word. En Matemáticas, Física, Química, Biología y Tecnología y Medio Ambiente, el sistema **rechaza** cualquier letra, `)` o `θ` seguida de un número sin ese formato: `x2`, `H2O`, `(a+b)2`.
- **Fracciones** en línea: numerador en superíndice, barra normal, denominador en subíndice (⁵/₆). El sistema **rechaza** cualquier `número/número` en texto normal, en cualquier materia. Las fechas se escriben sin barra: «12 de mayo de 2024».
- **Editor de ecuaciones de Word** para todas las fracciones (van apiladas, como en un libro), las raíces, las sumatorias, las integrales, las matrices y los números mixtos. Desde el 06/11/2026 el validador rechaza `3/8`, `3⁄8`, `³/₈`, `√49` y `x^2`.
- **Prohibido:** Microsoft Equation 3.0, MathType, cualquier objeto incrustado, y ecuaciones pegadas como imagen.

## Imágenes y gráficas

- Formato PNG, **en línea con el texto**, nunca flotantes
- Trabaja siempre sobre las plantillas: ya traen activada la opción «No comprimir las imágenes del archivo». Si empiezas un Word desde cero, actívala en Archivo › Opciones › Avanzadas › Tamaño y calidad de la imagen; si no, Word reduce las imágenes a 220 ppp al guardar y el archivo se rechaza
- Ancho máximo **8,4 cm** en el Word
- Resolución mínima **300 ppp** al tamaño en que quedó (por ejemplo, una imagen de 8,4 cm necesita al menos 993 píxeles de ancho)
- **Escala de grises** real (sin ningún píxel de color), fondo blanco, **sin transparencia**
- Sin sombras, efectos artísticos, bordes ni marcos de Word
- Sin cuadros de texto, formas ni lienzos de dibujo: los rótulos van dentro del PNG
- En el enunciado o en el recurso, la imagen va sola en su párrafo, centrada
- Si lleva pie, va en el párrafo siguiente, centrado, 8 pt

## Tablas dentro del ejercicio

- Ancho máximo 8,4 cm, Tahoma 8 pt
- Primera fila de encabezado **en negrita**; el centrado lo pone el sistema al armar la cartilla
- Bordes sencillos negros de 0,5 pt
- Sin sombreados (fondo blanco)
- Alineación vertical centrada
- Máximo cuatro columnas, sin tablas anidadas
- «No dividir la fila entre páginas» marcado en **todas** las filas
- No dejes espacio de más dentro de las celdas: en la cartilla la tabla sale centrada y compacta

## TABLA DE RESPUESTAS

Tres columnas: `N°` · `Clave` · `Justificación de la respuesta correcta`.

- `N°` se deja **vacía**.
- `Clave` es una sola letra mayúscula: `A`, `B`, `C` o `D`.
- La justificación es solo de la respuesta correcta, en texto, sin imágenes.
- **La justificación no puede mencionar letras de opción.** Se rechaza «opción B», «literal C», «la A es correcta», «la D no es la respuesta», «B)», «A y C». Los símbolos sí valen: «el C», «(vitamina C)». Refiérete al contenido: «la expresión con un solo signo…».

## TABLA DE EXCEL

Diez columnas, con estos encabezados exactos:

`Preg.` · `Correcta` · `Grado` · `Materia` · `Submateria` · `Pensamiento` · `Competencia` · `DBA` · `Temática` · `Nivel`

| Columna | Qué va |
|---|---|
| `Preg.` | **Vacía** |
| `Correcta` | La misma letra de la `Clave` |
| `Grado` | `3°`, `4°`, `5°`, `6°`, `7°`, `8°`, `9°`, `10°`, `11°` o `ICFES`. Obligatorio |
| `Materia` | Del catálogo. Obligatoria |
| `Submateria` | Obligatoria en Matemáticas (`Matemáticas I` o `Matemáticas II`), Lengua Castellana (`Español`, `Comprensión Lectora`, `Lectura Crítica`) y Ciencias Naturales (`Biología`, `Física`, `Química`, `Tecnología y Medio Ambiente`). En Ciencias Sociales: `Ciencias Económicas y Políticas` o vacía (Sociales general). Filosofía es **materia**: `Materia = Filosofía`, submateria vacía. En las demás materias, vacía. En grado `ICFES`, Matemáticas puede ir sin submateria. **En 3°, 4° y 5°:** Matemáticas y Lengua Castellana van con la Submateria **vacía**; Ciencias Naturales sí lleva submateria |
| `Pensamiento` | El que corresponda a la **submateria**, de la tabla de abajo. Si el ejercicio ya lo trae, consérvalo |
| `Competencia` | La que corresponda a la materia, de la tabla de abajo. Si el ejercicio ya la trae, consérvala |
| `DBA` | Vacío si la materia no tiene DBA oficial (Filosofía, Ética, Informática…); también puedes escribir «No aplica» y el sistema lo deja vacío. Si lo tiene: `DBA 3`. Tómalo de la malla del grado; si la malla da varios para el mismo tema, escribe el que corresponde al contenido de esa pregunta. Si de verdad son dos: `DBA 3, DBA 5` |
| `Temática` | **Obligatoria** |
| `Nivel` | `Básico`, `Medio` o `Avanzado`. Obligatorio, **excepto** en grado `ICFES`, donde va vacío |

- Llena **toda la información que traiga el ejercicio**. Lo que quede vacío simplemente no se usa.
- Ningún valor lleva viñeta, guion, numeración al inicio ni punto final.
- En un bloque o una parte, todas las filas llevan el mismo Grado, Materia y Submateria.
- **Filosofía y Ciencias Económicas y Políticas**: escríbelas como quieras —`Ciencias Económicas y Políticas` en Materia, o `Ciencias Sociales` + esa submateria; `Filosofía` como materia, o dentro de Ciencias Sociales—. El sistema entiende las dos formas, guarda siempre la misma y te dice en los avisos qué entendió.

### Pensamiento y competencia, por submateria

El pensamiento depende de la **submateria**, no solo de la materia. Escríbelos exactamente así:

| Materia · Submateria | Pensamiento | Competencia |
|---|---|---|
| Matemáticas | Numérico-variacional · Geométrico-métrico · Aleatorio | Comunicación y representación · Razonamiento y argumentación · Planteamiento y resolución de problemas |
| Lengua Castellana · Español | Literatura · Producción textual | Comprensión e interpretación de textos literarios · Reconocimiento y uso de la estructura de la oración |
| Lengua Castellana · Comprensión Lectora | Lectura crítica | Recupera información literal · Comprende el sentido local mediante inferencias · Comprende el sentido global mediante inferencias · Asume una posición crítica |
| Lengua Castellana · Lectura Crítica | Lectura crítica | Recupera información literal · Comprende el sentido local mediante inferencias · Comprende el sentido global mediante inferencias · Asume una posición crítica |
| Ciencias Sociales | Historia y cultura · Relaciones espaciales y ambientales · Relaciones ético-políticas | Temporalidad · Espacialidad · Culturalidad · Institucionalidad y derechos humanos |
| Ciencias Naturales · Biología | Entorno vivo | Uso comprensivo del conocimiento científico · Explicación de fenómenos · Indagación |
| Ciencias Naturales · Física | Entorno físico | Uso comprensivo del conocimiento científico · Explicación de fenómenos · Indagación |
| Ciencias Naturales · Química | Entorno físico | Uso comprensivo del conocimiento científico · Explicación de fenómenos · Indagación |
| Ciencias Naturales · Tecnología y Medio Ambiente | Entorno físico · Entorno vivo | Uso comprensivo del conocimiento científico · Explicación de fenómenos · Indagación |
| Inglés | Lectura · Conversación · Escritura · Escucha · Monólogo | Competencia lingüística · Competencia pragmática · Competencia sociolingüística |

En las demás materias (Filosofía, Informática, Educación Física, Religión, Ética, Educación Artística, Dibujo, Electricidad, Mecánica) el pensamiento y la competencia son libres: usa los del plan de área, o déjalos vacíos.

## TABLA DE GLOSARIO (opcional)

Para explicar palabras difíciles de una pregunta. Solo se imprime si la cartilla marca la casilla «Incluir glosario». Va **al final**, después de la TABLA DE EXCEL. Tres columnas: `Pregunta` · `Término` · `Significado`.

| Columna | Qué va |
|---|---|
| `Pregunta` | El número de la pregunta **dentro del archivo**: `1` en un suelto; `1`, `2`, `3`… en un bloque o una parte |
| `Término` | Máximo 40 caracteres, escrito igual que en el texto de la pregunta (o de su lectura) |
| `Significado` | Máximo 150 caracteres |

- **Las fórmulas sí se pueden escribir**: superíndices, subíndices y ecuaciones del editor de Word («i² = −1», «H₂O», «a²+b²=c²»). El sistema las conserva y las imprime igual. Lo que **no** se puede poner en el glosario son imágenes ni objetos incrustados: no caben en una línea de 8 pt.
- Máximo **3 términos por pregunta**, sin repetir.
- Una fila por término. Las filas vacías se ignoran; si no hay glosario, deja la tabla vacía o bórrala con su rótulo.
- No definas las opciones de respuesta: el glosario ayuda a entender la pregunta, no a responderla.

## Antes de entregar, revisa

Lo que el sistema rechaza:

- ¿Quedó algún número de pregunta escrito a mano?
- ¿Quedó algún corchete, nota, resaltado, comentario o texto de color?
- ¿Cada pregunta tiene exactamente cuatro opciones, cada una en un solo párrafo?
- ¿Coinciden la `Clave` y la columna `Correcta`?
- ¿Tiene la TABLA DE EXCEL las 10 columnas, con el Grado lleno?
- ¿Tiene el bloque su línea de crédito?
- En «completar el texto», ¿están los marcadores `(#1)` a `(#k)` completos y en orden?
- ¿Alguna imagen pasa de 8,4 cm, es flotante, tiene color o transparencia?
- ¿Quedó algún `x2` sin superíndice o `3/4` en texto plano?
- ¿Menciona la justificación alguna letra de opción?
- ¿Quedó alguna referencia a otro número de ejercicio?
- Si lleva glosario: ¿cada término está escrito igual que en el texto, con máximo 3 por pregunta?

Lo que el sistema **no puede** revisar, y depende de ti:

- ¿Hay alguna ecuación pegada como imagen? Debe rehacerse con superíndices o con el editor de ecuaciones.
- ¿Se leen bien los rótulos de las imágenes a 8,4 cm de ancho?
- ¿Tienen sentido las cuatro opciones en cualquier orden?
- ¿Es correcta la justificación?
- ¿Los párrafos que el sistema avisa como «a la izquierda», «centrado» o «a la derecha» van así a propósito?

Entrega el archivo `.docx` normalizado y una lista de lo que tuviste que corregir.

---
