# ESTÁNDAR PRAXIS – THINKS
## Generador de cuadernillos tipo ICFES
### Documento maestro de formato · Versión 1.2

> **Cambios de la 1.1 frente a la 1.0**, acordados con PRAXIS – THINKS:
> columna `Grado` en la TABLA DE EXCEL de carga · reglas del validador sin ambigüedad (2.12) · una opción = un párrafo · línea de crédito obligatoria como fin del recurso · campos pedagógicos opcionales · códigos de materia por estructura · emparejamiento automático de sesiones · portada y Excel por tipo de material · submateria renombrada a **Ciencias Económicas y Políticas** · **Filosofía como materia propia** · en ICFES nunca se imprime ni se exporta información pedagógica · márgenes estrechos · tiempo automático · descarga con nombre · marcadores de «completar el texto» en Inglés · tipo `51` retirado · maquetación verificada en Word, con opciones verticales y preguntas que no se parten (3.5B) · cartilla en Word editable (3.6B) · colores por materia en la portada · ICFES siempre 4 h 30 min · Parte 7 cerrada.

> **Cambios de la 1.2 frente a la 1.1** (21/09/2026): enunciados, opciones y lecturas se imprimen **justificados** y se conserva la alineación que el autor aplique a mano (3.5B) · plantillas de carga con el estilo Normal justificado · tablas del ejercicio **centradas y compactas** en la cartilla, con sus bordes escritos en la propia tabla (2.11) · columnas de **9,12 cm** con 0,8 cm entre ellas (3.1) · **glosario opcional por pregunta**: TABLA DE GLOSARIO en el archivo de carga (2.7B, regla 29) y casilla «Incluir glosario» en la cartilla (3.5B, 5.3) · **grados 3°, 4° y 5°** (códigos `33`, `44`, `55`): Matemáticas y Lengua Castellana van sin submateria, Ciencias Naturales con submateria (1.2); E1 y E2 no aplican a primaria y la estructura libre permite agregar secciones (E4).

> Este documento define **cómo entran** los ejercicios al sistema y **cómo salen** la cartilla y el Excel.
> Es la base de todo el proyecto: si este documento está bien, el programa no puede equivocarse.
> Nada se programa hasta que esta versión quede aprobada.

---

# PARTE 0 · Principio de diseño

El sistema **no reescribe ni reinterpreta** los ejercicios. Copia el contenido original del Word tal como fue guardado y lo inserta en la plantilla de la cartilla. Lo único que el sistema modifica es:

1. El **número** de la pregunta.
2. El **orden de las opciones**, según la plantilla de respuestas.
3. Las **frases de referencia** de los bloques de lectura compartida.
4. La **portada** y los **títulos de materia**.
5. El **espaciado y la alineación** de los párrafos, y el formato de las tablas (3.5B).
6. El **glosario** de cada pregunta, que imprime solo si la cartilla lo pide (2.7B).
7. Lo que **no se imprime** y podría dañar el Word al juntar ejercicios: los hipervínculos quedan como texto normal; los campos (referencias cruzadas, fechas, numeraciones SEQ) quedan congelados con el resultado que se veía en el Word de carga; se quitan los marcadores (como `_GoBack`), los controles de contenido y los estilos de carácter del archivo de carga (su formato queda escrito en el texto); y cada imagen recibe su propio número interno.

Todo lo demás (texto, tablas, imágenes, superíndices, fórmulas) viaja intacto.

**Consecuencia:** la calidad de la cartilla depende de la calidad del archivo de carga. Por eso el validador es estricto: si el archivo no cumple el estándar, se rechaza y no entra al banco.

---

# PARTE 1 · Catálogos maestros

Los catálogos de **Grado, Materia, Tipo de material y Plantilla** son listas cerradas: forman el código de la cartilla y no admiten valores libres. El administrador puede agregar entradas desde la aplicación.

Los campos pedagógicos (Pensamiento, Competencia, DBA, Temática) **no** llevan lista cerrada. Ver sección 1.7.

## 1.1 Grado

| Grado | Código |
|---|---|
| 3° | 33 |
| 4° | 44 |
| 5° | 55 |
| 6° | 66 |
| 7° | 77 |
| 8° | 88 |
| 9° | 99 |
| 10° | 10 |
| 11° | 11 |
| ICFES | 13 |

Los grados 3°, 4° y 5° (primaria) se agregaron el 21/09/2026 siguiendo el mismo patrón de código. Los grados 1° y 2° no están habilitados.

## 1.2 Materia (segundo par del código de cartilla)

El rango **01–49** queda reservado para materias individuales (simulacros especiales). El rango **87–99** queda para agrupaciones y partes. Así nunca se cruzan.

### Jerarquía Materia → Submateria

Las **secciones de una estructura se definen por Submateria**, no por Materia. Una misma materia puede aportar varias secciones al mismo simulacro.

| Materia (columna D del Excel) | Submaterias (columna E) |
|---|---|
| Matemáticas | Matemáticas I · Matemáticas II |
| Lengua Castellana | Español · Comprensión Lectora · Lectura Crítica |
| Ciencias Naturales | Biología · Física · Química · Tecnología y Medio Ambiente |
| Ciencias Sociales | Ciencias Económicas y Políticas |
| Filosofía | — |
| Inglés | — |
| Informática | — |
| Educación Física | — |
| Educación Artística | — |
| Religión | — |
| Ética | — |
| Dibujo | — |
| Electricidad | — |
| Mecánica | — |

Cuando una materia no tiene submateria, la columna E del Excel va **vacía**.

**Primaria (3°, 4° y 5°).** Matemáticas y Lengua Castellana van **sin submateria**: se suben como «Matemáticas» o «Lengua Castellana», con la columna E vacía, y el validador rechaza una submateria en esas materias. Ciencias Naturales lleva submateria obligatoria, igual que en bachillerato. Las demás materias siguen la regla general.

### Filosofía es materia propia

**Decisión de la v1.1:** Filosofía es una **materia**, sin submaterias. Ciencias Sociales es otra materia, con una sola submateria: Ciencias Económicas y Políticas.

> **Cómo se escriba da igual (08/10/2026).** En la práctica se escriben de varias formas, según la prueba.
> El sistema las entiende todas y **guarda siempre la misma**, avisando qué entendió:
>
> | Si el archivo dice | Se guarda |
> |---|---|
> | Materia `Ciencias Económicas y Políticas`, sin submateria | Materia `Ciencias Sociales` · Submateria `Ciencias Económicas y Políticas` |
> | Materia `Ciencias Sociales` · Submateria `Filosofía` | Materia `Filosofía`, sin submateria |
> | Submateria `No aplica`, `Ninguna`, `—` o el nombre de la materia, en una materia sin submaterias | Submateria vacía |
> | DBA `No aplica`, `N/A`, `Ninguno`, `—` | DBA vacío (Filosofía, Ética o Informática no tienen DBA oficial) |
>
> Se guarda una sola forma **a propósito**: el emparejamiento con las secciones es por materia y submateria
> exactas, así que dos formas distintas del mismo tema harían que cada sección viera solo la mitad.
> Un error de verdad —`Biología` como submateria de `Matemáticas`— se sigue rechazando.

En la estructura E2, las tres secciones de sociales quedan así:

| Sección | Título impreso | Columna D | Columna E |
|---|---|---|---|
| Sociales general | CIENCIAS SOCIALES | Ciencias Sociales | *(vacía)* |
| Filosofía | FILOSOFÍA | Filosofía | *(vacía)* |
| Económicas y políticas | CIENCIAS ECONÓMICAS Y POLÍTICAS | Ciencias Sociales | Ciencias Económicas y Políticas |

Pendiente externo: confirmar que el software de calificación distingue Sociales general de Ciencias Económicas y Políticas por la submateria (ver Parte 7).

**Decisión del 07/10/2026 · 6° a 9° (estructura E1).** En esos grados **no hay** sección de Ciencias Económicas y
Políticas: la sección CIENCIAS SOCIALES toma **toda la materia**, con submateria o sin ella. Así, un ejercicio de
6° marcado «Ciencias Sociales · Ciencias Económicas y Políticas» se puede usar sin tener que corregir el archivo.
En E2 (10° y 11°) **no cambia nada**: allí cada una tiene su propia sección y se siguen separando por la submateria.

### Códigos · materia o submateria que da nombre al simulacro especial

| Materia | Código |
|---|---|
| Matemáticas I | 01 |
| Matemáticas II | 02 |
| Matemáticas (completa) | 03 |
| Lectura Crítica | 23 |
| Tecnología y Medio Ambiente | 24 |
| Español | 04 |
| Comprensión Lectora | 05 |
| Ciencias Sociales | 06 |
| Filosofía | 07 |
| Ciencias Económicas y Políticas | 08 |
| Biología | 09 |
| Física | 12 |
| Química | 13 |
| Inglés | 14 |
| Informática | 15 |
| Educación Física | 16 |
| Educación Artística | 17 |
| Religión | 18 |
| Ética | 19 |
| Mecánica | 20 |
| Electricidad | 21 |
| Dibujo | 22 |

> Se saltan los códigos `10` y `11` a propósito, para que ningún código de materia se lea igual que un código de grado. Reduce el riesgo de confusión al digitar.
>
> El rango `25`–`49` queda libre. El administrador agrega materias y submaterias nuevas desde la aplicación, tomando el siguiente código disponible.

### Agrupaciones y partes

| Agrupación | Código |
|---|---|
| Todas las materias | 99 |
| M-L-N-S-I (Matemáticas, Español, Naturales, Sociales, Inglés) | 98 |
| PARTE 1 | 91 |
| PARTE 2 | 92 |
| PARTE 2 (variante) | 93 |
| PARTE 3 | 94 |
| Mecánica (agrupación histórica) | 87 |
| Electricidad (agrupación histórica) | 88 |
| Dibujo (agrupación histórica) | 89 |

### Simulacro especial de dos o más materias

Cuando el simulacro combina materias sin corresponder a una agrupación existente (por ejemplo Matemáticas y Español para el día del idioma), se usa el código **97 · Combinado especial**. La composición exacta queda registrada en la estructura de la cartilla, no en el código.

Todos los códigos de esta sección se conservan en el catálogo, incluidos `93` y `98`.

### Código de materia según la estructura

| Estructura | Código de materia |
|---|---|
| E1 y E2 · PARTE 1 | `91` |
| E3 · PARTE 2 | `92` |
| E3 · PARTE 2 con una o más materias agregadas (pedido especial) | `93` |
| E7 · PARTE 3 | `94` |
| E5 y E6 · ICFES | `99` |
| E4 de una sola materia | El de la materia, `01`–`24`. En Matemáticas: `01` si es solo Matemáticas I, `02` si es solo Matemáticas II, `03` si mezcla las dos |
| E4 de varias materias | `97`, o `98` si es exactamente M-L-N-S-I |

El sistema **propone** el código según la estructura elegida y **rechaza** cualquier otro que no esté en esta tabla para esa estructura.

## 1.3 Tipo de material (tercer par)

| Tipo | Código |
|---|---|
| Simulacro / Periodo 1 | 11 |
| Simulacro / Periodo 2 | 22 |
| Simulacro / Periodo 3 | 33 |
| Simulacro / Periodo 4 | 44 |
| Simulacro especial | 55 |
| Sesión 1 – REAL ICFES | 71 |
| Sesión 2 – REAL ICFES | 72 |

El tipo `51` (Simulacro ICFES / Cartilla) se retiró en la v1.1: el simulacro ICFES se hace siempre con las dos sesiones `71` y `72`.

## 1.4 Plantilla de respuestas (cuarto par)

`01` a `05`. Cada una es una secuencia fija de letra correcta por número de pregunta, de 1 a 140, con letras `A` a `D`.

Se lee por prefijo: un examen de 25 preguntas usa las primeras 25 letras.

**Las cinco plantillas no se modifican.** Son las mismas de siempre y aplican a toda pregunta del sistema sin excepción.

## 1.5 Versión (quinto par)

`01` a `06` o más. Control interno. Distingue dos cartillas que comparten grado, materia, tipo y plantilla.

## 1.6 Nivel de dificultad

| En la línea ➤ | En la TABLA DE EXCEL y en el Excel de salida |
|---|---|
| BB | Básico |
| MM | Medio |
| AA | Avanzado |

**No aplica en pruebas ICFES.** Un ejercicio de grado `ICFES` (código `13`) se carga con el Nivel **vacío**; en cualquier otro grado el Nivel es **obligatorio**.

## 1.7 Pensamiento, Competencia, DBA, Temática

**No hay catálogo precargado.** Estos valores se escriben en el Word de carga y el sistema los toma tal como vienen.

Para que el buscador funcione, el sistema mantiene un **catálogo que se construye solo**:

1. La primera vez que aparece una temática, el sistema la registra.
2. De ahí en adelante, esa temática queda disponible como filtro de búsqueda.
3. Si un ejercicio nuevo trae un valor **parecido pero no idéntico** a uno ya registrado, el sistema pregunta antes de guardar: *«¿Es la misma que "Ecuaciones lineales" o es una nueva?»*. El archivo queda **pendiente** y no entra al banco hasta que la persona responde. Si responde «la misma», se guarda con la escritura ya registrada.
4. «Parecido» se define de forma exacta, sobre los valores ya normalizados y sin distinguir mayúsculas, tildes ni espacios sobrantes:
   - **Igual así escrito de otra forma** («operaciones con numeros naturales» y «Operaciones con números naturales»): es el mismo valor. El sistema adopta la escritura ya registrada **sin preguntar**.
   - **Difiere en pocas letras** según su largo (**1** hasta 7 caracteres, **2** hasta 15 y **3** de ahí en adelante): parece un error de escritura y el sistema **pregunta**. Así «Ecuaciones lineles» se detecta como error de «Ecuaciones lineales».
   - **Cualquier otra diferencia es otro valor**, aunque uno contenga al otro: «Fracciones equivalentes» y «Fracciones equivalentes representadas gráficamente» son dos temáticas distintas, igual que «Ángulos» y «Ángulos internos». El sistema no pregunta y las registra por separado.

Así nadie tiene que mantener listas a mano, y aun así la búsqueda no se fragmenta.

### Normalización automática al guardar

El sistema limpia estos detalles sin preguntar, porque no cambian el significado:

- Quita viñetas (`●`), guiones y numeración al inicio.
- Quita el punto final.
- Convierte espacios dobles en simples y elimina espacios al inicio y al final.
- Unifica el formato de DBA a `DBA n` (espacio, sin cero a la izquierda): `DBA3` y `DBA 03` se guardan como `DBA 3`.
- Si hay varios DBA, se separan con coma y espacio: `DBA 3, DBA 5`. Después de normalizar, la celda debe quedar vacía o con ese formato exacto; cualquier otro contenido se rechaza.
- Materia, Submateria y Nivel se comparan con el catálogo **sin distinguir mayúsculas, tildes ni espacios sobrantes**, y se guardan con la escritura del catálogo. Un valor que no esté en el catálogo se rechaza.

### Por qué importa

La búsqueda por temática es filtro obligatorio. Si «Ecuaciones lineales», «ecuaciones lineales» y «Ecuaciones lineales.» se guardan como tres valores distintos, el docente que filtre por una solo encontrará un tercio de los ejercicios disponibles. La normalización y el aviso de similitud evitan eso sin imponer un catálogo rígido.

---

# PARTE 1A · Tipos de simulacro y sesiones

Todo lo que el sistema genera cae en uno de tres casos. Los tres usan el mismo motor; lo único que cambia es la estructura.

## Caso 1 · Simulacro sencillo, de una sola materia

Una sola sección. Se usa para jornadas especiales: 30 preguntas de Matemáticas, 50 para el día del idioma, 35 para el día del boyacencismo, o un simulacro de Dibujo, Electricidad o Mecánica cuando la institución lo pide.

| Aspecto | Valor |
|---|---|
| Estructura | E4, libre |
| Secciones | Una |
| Título de sección | **Obligatorio**, también con una sola materia |
| Sesiones | Una |
| Código de materia | El de la materia, `01`–`24` |
| Tipo de material | `55` Simulacro especial, u otro que se defina |
| Cartillas generadas | Una |

## Caso 2 · Simulacro periódico, de varias materias

Varias secciones, cada una con su título, separadas y agrupadas. Es el caso de E1, E2, E3 y E7.

| Aspecto | Valor |
|---|---|
| Estructura | E1, E2, E3, E7 o libre |
| Secciones | Varias, agrupadas por submateria |
| Título de sección | Obligatorio, centrado, mayúsculas |
| Sesiones | **Una o dos**, según lo pida la institución |
| Tipo de material | `11`, `22`, `33`, `44` según el periodo |
| Cartillas generadas | Una por sesión |

Cuando el periódico va en dos sesiones, lo habitual es PARTE 1 en la primera y PARTE 2 o PARTE 3 en la segunda, cada una con su propio código de materia (`91`, `92`, `94`).

## Caso 3 · Simulacro ICFES

Replica la prueba real: dos sesiones, estructuras E5 y E6.

| Aspecto | Valor |
|---|---|
| Estructura | E5 (sesión 1) y E6 (sesión 2) |
| Secciones | Cinco y cuatro, con submaterias mezcladas |
| Sesiones | **Siempre dos** |
| Grado | `13` |
| Tipo de material | `71` y `72` |
| Cartillas generadas | Dos, una por sesión |
| Excel | Columnas F a J siempre vacías |
| Línea ➤ | No se imprime |

## Reglas de sesiones, comunes a los tres casos

1. **Una sesión es una cartilla.** Cada sesión tiene su propio código de diez dígitos, su propio Word y su propia hoja del Excel.
2. **La numeración reinicia en 1** en cada sesión.
3. **La plantilla se lee desde la posición 1** en cada sesión.
4. **No se repiten ejercicios entre sesiones.** El sistema **empareja solo** las dos sesiones y excluye los ejercicios de la primera, sin que nadie tenga que marcarla. Son pareja dos cartillas con el mismo grado, tipo, plantilla y versión cuya materia es `91` y `92`/`93`/`94`, o dos cartillas con el mismo grado, materia, plantilla y versión cuyo tipo es `71` y `72`. Además se pueden marcar a mano otras cartillas a excluir (por ejemplo, periodos anteriores).
5. Las dos sesiones comparten institución y nombre descriptivo, lo que permite verlas juntas en el histórico.

---

# PARTE 1B · Estructuras predefinidas

Una **estructura** es el orden y la cantidad de preguntas por materia de una cartilla. El sistema la usa para tres cosas: guiar la selección de ejercicios, numerar de forma continua y calcular la tabla de áreas de la portada.

## E1 · Periódico PARTE 1 · Grados 6° a 9° · 140 preguntas

No aplica a 3°, 4° y 5°: sus secciones usan Matemáticas I/II y Español/Comprensión Lectora, que en primaria no existen. Lo mismo vale para E2.

| Orden | Título impreso | Materia (col. D) | Submateria (col. E) | Rango | Preg. |
|---|---|---|---|---|---|
| 1 | MATEMÁTICAS I | Matemáticas | Matemáticas I | 1–15 | 15 |
| 2 | MATEMÁTICAS II | Matemáticas | Matemáticas II | 16–30 | 15 |
| 3 | LENGUA CASTELLANA | Lengua Castellana | Español | 31–44 | 14 |
| 4 | COMPRENSIÓN LECTORA | Lengua Castellana | Comprensión Lectora | 45–56 | 12 |
| 5 | CIENCIAS SOCIALES | Ciencias Sociales | *(vacía o Ciencias Económicas y Políticas)* | 57–76 | 20 |
| 6 | BIOLOGÍA | Ciencias Naturales | Biología | 77–88 | 12 |
| 7 | FÍSICA | Ciencias Naturales | Física | 89–100 | 12 |
| 8 | QUÍMICA | Ciencias Naturales | Química | 101–112 | 12 |
| 9 | INGLÉS | Inglés | *(vacía)* | 113–140 | 28 |
| | **Total** | | | | **140** |

## E2 · Periódico PARTE 1 · Grados 10° y 11° · 140 preguntas

| Orden | Título impreso | Materia (col. D) | Submateria (col. E) | Rango | Preg. |
|---|---|---|---|---|---|
| 1 | MATEMÁTICAS I | Matemáticas | Matemáticas I | 1–13 | 13 |
| 2 | MATEMÁTICAS II | Matemáticas | Matemáticas II | 14–26 | 13 |
| 3 | LENGUA CASTELLANA | Lengua Castellana | Español | 27–40 | 14 |
| 4 | COMPRENSIÓN LECTORA | Lengua Castellana | Comprensión Lectora | 41–50 | 10 |
| 5 | CIENCIAS SOCIALES | Ciencias Sociales | *(vacía)* | 51–60 | 10 |
| 6 | FILOSOFÍA | **Filosofía** | *(vacía)* | 61–72 | 12 |
| 7 | CIENCIAS ECONÓMICAS Y POLÍTICAS | Ciencias Sociales | Ciencias Económicas y Políticas | 73–82 | 10 |
| 8 | BIOLOGÍA | Ciencias Naturales | Biología | 83–92 | 10 |
| 9 | FÍSICA | Ciencias Naturales | Física | 93–102 | 10 |
| 10 | QUÍMICA | Ciencias Naturales | Química | 103–112 | 10 |
| 11 | INGLÉS | Inglés | *(vacía)* | 113–140 | 28 |
| | **Total** | | | | **140** |

## E3 · Periódico PARTE 2 · 80 preguntas

Todas las secciones son materias sin submateria, así que la columna E del Excel va vacía en toda la cartilla.

| Orden | Título impreso | Materia (col. D) | Submateria (col. E) | Rango | Preg. |
|---|---|---|---|---|---|
| 1 | INFORMÁTICA | Informática | *(vacía)* | 1–16 | 16 |
| 2 | EDUCACIÓN FÍSICA | Educación Física | *(vacía)* | 17–32 | 16 |
| 3 | EDUCACIÓN ARTÍSTICA | Educación Artística | *(vacía)* | 33–48 | 16 |
| 4 | RELIGIÓN | Religión | *(vacía)* | 49–64 | 16 |
| 5 | ÉTICA | Ética | *(vacía)* | 65–80 | 16 |
| | **Total** | | | | **80** |

## E5 y E6 · Simulacro ICFES · propuesta

Estas dos estructuras replican el cuadernillo estándar del Saber 11° según la **Guía de orientación del Examen Saber 11° 2026-1** del Icfes (diciembre de 2025).

Totales oficiales por prueba: Lectura Crítica 41 · Matemáticas 50 · Sociales y Ciudadanas 50 · Ciencias Naturales 58 · Inglés 55. **Total calificado: 254 preguntas.**

El Icfes reparte las pruebas en dos sesiones de 4 h 30 min. Lectura Crítica va completa en la sesión 1 e Inglés completo en la sesión 2; las otras tres se dividen por mitades entre las dos sesiones. El Icfes advierte que el reparto exacto puede variar según la versión del cuadernillo.

### E5 · Simulacro ICFES · Sesión 1 · 120 preguntas

Tipo de material `71` · Tiempo 4 h 30 min

| Orden | Título impreso | Materia (col. D) | Submateria (col. E) | Rango | Preg. |
|---|---|---|---|---|---|
| 1 | MATEMÁTICAS | Matemáticas | *(vacía)* | 1–25 | 25 |
| 2 | LECTURA CRÍTICA | Lengua Castellana | Lectura Crítica | 26–66 | 41 |
| 3 | SOCIALES Y CIUDADANAS | Ciencias Sociales | mezcladas | 67–91 | 25 |
| 4 | CIENCIAS NATURALES | Ciencias Naturales | mezcladas | 92–120 | 29 |
| | **Total** | | | | **120** |

### E6 · Simulacro ICFES · Sesión 2 · 134 preguntas

Tipo de material `72` · Tiempo 4 h 30 min

| Orden | Título impreso | Materia (col. D) | Submateria (col. E) | Rango | Preg. |
|---|---|---|---|---|---|
| 1 | MATEMÁTICAS | Matemáticas | *(vacía)* | 1–25 | 25 |
| 2 | SOCIALES Y CIUDADANAS | Ciencias Sociales | mezcladas | 26–50 | 25 |
| 3 | CIENCIAS NATURALES | Ciencias Naturales | mezcladas | 51–79 | 29 |
| 4 | INGLÉS | Inglés | *(vacía)* | 80–134 | 55 |
| | **Total** | | | | **134** |

El orden de las secciones replica el del cuadernillo real. En la sesión 1 el Icfes ubica Matemáticas antes de Lectura Crítica.

### Secciones de submaterias mezcladas

En el simulacro ICFES solo entran las cinco pruebas que el Icfes evalúa realmente: Matemáticas, Lectura Crítica, Sociales y Ciudadanas, Ciencias Naturales e Inglés.

**Matemáticas** va como una sola materia, sin submateria: los contenidos de Matemáticas I y II van mezclados pero el Excel registra solo `Matemáticas`.

**Sociales y Ciudadanas** y **Ciencias Naturales** sí conservan submateria, y sus ejercicios van **entreverados** dentro de la sección, tal como en la prueba real. SOCIALES Y CIUDADANAS es la única sección que mezcla **dos materias**: Ciencias Sociales (general y Económicas y Políticas) y Filosofía.

Combinaciones admitidas en cada sección (materia / submateria):

| Sección | Materia (col. D) | Submaterias admitidas (col. E) |
|---|---|---|
| SOCIALES Y CIUDADANAS | Ciencias Sociales · Filosofía | Ciencias Económicas y Políticas · *(vacía)* |
| CIENCIAS NATURALES | Ciencias Naturales | Biología · Física · Química · Tecnología y Medio Ambiente |
| MATEMÁTICAS | Matemáticas | *(vacía)* |
| LECTURA CRÍTICA | Lengua Castellana | Lectura Crítica |
| INGLÉS | Inglés | *(vacía)* |

Al armar la sección se puede fijar una **cuota por submateria** (por ejemplo, de las 29 de Ciencias Naturales: 8 de Biología, 8 de Física, 8 de Química y 5 de Tecnología y Medio Ambiente) o dejarla libre y elegir a mano. En los dos casos el sistema entrevera el resultado.

| | Simulacro periódico | Simulacro ICFES |
|---|---|---|
| Sección definida por | Submateria | **Materia o combinación de materias** |
| Submaterias dentro de la sección | Una sola | **Varias, mezcladas** |
| Orden de los ejercicios | Agrupados por submateria | Entreverados |

Consecuencias para el sistema:

- La sección se declara con la **lista de combinaciones materia / submateria admitidas**.
- La selección permite fijar cuántos ejercicios aporta cada submateria, por ejemplo 10 de Biología, 10 de Física y 9 de Química en los 29 de Ciencias Naturales.
- Una vez elegidos, el sistema los **entrevera** en lugar de agruparlos. El orden se puede reordenar a mano en la vista previa.
- Cada fila del Excel conserva la submateria real del ejercicio, aunque en la cartilla no aparezca agrupada.

### Reglas particulares del simulacro ICFES

| Regla | Valor |
|---|---|
| Columnas **Pensamiento, Competencia, DBA, Temática y Nivel** del Excel (F a J) | Siempre **vacías**, aunque el ejercicio traiga esos datos |
| Columna **Submateria** del Excel en la sección MATEMÁTICAS | Siempre **vacía** |
| Línea ➤ en la cartilla | **No se imprime** |
| Grado impreso en la portada | `Saber 11` |
| Ejercicios admitidos | Solo los cargados con grado `ICFES` |
| Código de grado | `13` |
| Numeración | Reinicia en 1 en cada sesión |
| Cartillas | Una por sesión, con código propio |

Ejemplos de código:

```
1399710101   ICFES · todas las materias · Sesión 1 REAL · Plantilla 1 · Versión 1
1399720101   ICFES · todas las materias · Sesión 2 REAL · Plantilla 1 · Versión 1
```

Las dos sesiones caben dentro de las 140 posiciones de las plantillas de respuestas (120 y 134), así que no hay que ampliar las plantillas.

## E7 · Periódico PARTE 3 · 116 preguntas

Código de materia `94`. Es la estructura E3 más tres secciones técnicas.

**Dibujo, Electricidad y Mecánica se incluyen solo cuando la institución las solicita**, y en la cantidad que pida. Las 12 preguntas de la tabla son el caso que suma 116; el orden y las cantidades se ajustan como cualquier otra estructura.

| Orden | Título impreso | Materia (col. D) | Submateria (col. E) | Rango | Preg. |
|---|---|---|---|---|---|
| 1 | INFORMÁTICA | Informática | *(vacía)* | 1–16 | 16 |
| 2 | EDUCACIÓN FÍSICA | Educación Física | *(vacía)* | 17–32 | 16 |
| 3 | EDUCACIÓN ARTÍSTICA | Educación Artística | *(vacía)* | 33–48 | 16 |
| 4 | RELIGIÓN | Religión | *(vacía)* | 49–64 | 16 |
| 5 | ÉTICA | Ética | *(vacía)* | 65–80 | 16 |
| 6 | DIBUJO | Dibujo | *(vacía)* | 81–92 | 12 |
| 7 | ELECTRICIDAD | Electricidad | *(vacía)* | 93–104 | 12 |
| 8 | MECÁNICA | Mecánica | *(vacía)* | 105–116 | 12 |
| | **Total** | | | | **116** |

> Los códigos `87`, `88` y `89` sirven para **simulacros independientes de 20 preguntas** de Mecánica, Electricidad y Dibujo. Dentro de E7 cada una aporta 12. Son dos usos distintos de la misma materia y no se contradicen.

## E4 · Estructura libre · simulacros especiales

Se arma en el momento: en el paso «Secciones» se agregan secciones con materia, submateria, título impreso y cantidad, en el orden deseado, y se quitan las que no tengan ejercicios elegidos. El sistema calcula los rangos y el tiempo, y solo ofrece la submateria que admite el grado (en 3° a 5°, Matemáticas y Lengua Castellana sin submateria; Ciencias Naturales con ella). También se agregan secciones en la PARTE 2 con materia agregada (código `93`).

**Primaria:** mientras no se defina una estructura fija de 3° a 5°, sus cartillas se arman con E4 (o con E3 y E7, que no usan submaterias).

Ejemplos: 30 preguntas de Matemáticas para un día especial · 50 preguntas de Español para el día del idioma · 35 preguntas de Ciencias Sociales para el día del boyacencismo.

## Reglas comunes a todas las estructuras

- Cada sección queda identificada por la pareja **Materia + Submateria**. Cuando la materia no tiene submateria, la columna E del Excel va vacía.
- Las estructuras E1, E2 y E3 son **fijas**: son la referencia estándar de la empresa.
- Al crear una cartilla, la estructura se carga completa y se puede **ajustar en dos cosas**: la **cantidad** de preguntas de cada sección y el **orden** de las secciones. No se agregan ni se quitan secciones; para eso está la estructura libre E4. **Única excepción:** a la E3 (PARTE 2) se le pueden **agregar** secciones al final cuando la institución hace un pedido especial; la cartilla pasa a llevar el código de materia `93`.
- Si se ajusta una cantidad, el sistema **recalcula todos los rangos** y muestra el nuevo total. La generación se bloquea si el total no coincide con el declarado.
- Los ajustes quedan guardados en esa cartilla y no modifican la estructura base.
- Al crear una cartilla se elige una estructura o se arma una libre.
- La numeración es **continua** dentro de la cartilla, de 1 hasta el total.
- Si la prueba tiene dos sesiones, cada sesión es una cartilla con su propio código y su numeración reinicia en 1.
- El sistema **impide generar** si alguna sección no tiene la cantidad exacta de ejercicios que exige la estructura.

---

# PARTE 2 · FORMATO DE ENTRADA
## Archivo Word de carga de ejercicios

## 2.1 Regla general

Un archivo `.docx` contiene exactamente una de estas tres unidades, y el sistema reconoce cuál es por su **primer párrafo**:

| Unidad | Primer párrafo | Plantilla |
|---|---|---|
| Ejercicio suelto | Cualquier texto que no sea uno de los dos siguientes | `PLANTILLA_CARGA_1_EJERCICIO` |
| Bloque de lectura compartida | La frase de referencia exacta (2.8) | `PLANTILLA_CARGA_2_BLOQUE_LECTURA` |
| Parte de Inglés | El subtítulo `PARTE #P · …` (2.8B) | `PLANTILLA_CARGA_3_PARTE_INGLES` |

No se mezclan ejercicios sueltos independientes en un mismo archivo. Los ejercicios sueltos y los bloques existen en **todas** las materias; las partes, solo en Inglés.

La carga masiva se hace subiendo varios archivos `.docx` a la vez.

## 2.2 Configuración del documento de carga

| Parámetro | Valor obligatorio |
|---|---|
| Tamaño de página | Carta (21,59 × 27,94 cm) |
| Orientación | Vertical (**sin** el atributo `landscape`) |
| Márgenes | 1,27 cm en los cuatro lados |
| Columnas | **Una sola columna** |
| Fuente | Tahoma |
| Texto del ejercicio | **9 pt** |
| Texto dentro de tablas | **8 pt** |
| Interlineado | Sencillo |
| Estilo de párrafo | Sin espaciado |
| Alineación | **Justificada** (así viene el estilo Normal de las plantillas v1.2). Izquierda, centrada o derecha solo donde el autor la aplique a mano: se conserva en la cartilla (3.5B) |
| Color del texto | Negro (automático). Cualquier otro color se rechaza |

> El espaciado entre párrafos y los párrafos vacíos **no se validan**: el sistema los retira y aplica el espaciado propio de la cartilla. La sangría sí se conserva.

> El documento de carga va a **una columna** aunque la cartilla final vaya a dos. El sistema se encarga del reflujo. Esto evita que el autor intente maquetar a mano.

## 2.3 Estructura obligatoria del archivo

El archivo debe tener estos bloques, **en este orden exacto**:

```
[1] ENUNCIADO Y PREGUNTA
[2] OPCIONES A, B, C, D
[3] TABLA DE RESPUESTAS      ← encabezado literal, en mayúsculas
[4] TABLA DE EXCEL            ← encabezado literal, en mayúsculas
[5] TABLA DE GLOSARIO         ← opcional; si va, siempre al final
```

**La línea ➤ NO se escribe en el archivo de carga.** El sistema la genera automáticamente a partir de la TABLA DE EXCEL. Esto elimina el riesgo de que la línea ➤ y la tabla se contradigan.

---

## 2.4 Bloque [1] · Enunciado y pregunta

- **No se escribe el número de la pregunta.** El sistema lo asigna. Se rechaza todo párrafo del enunciado que empiece por un número seguido de `.`, `)` o `-` y un espacio (`79. `, `3) `).
- El enunciado arranca directamente con el texto y termina en el párrafo anterior a `A.`.
- Puede contener: texto, tablas, imágenes, superíndices y fórmulas (ver reglas abajo).
- La pregunta propiamente dicha va como **último párrafo del enunciado** y termina en `?`. Es obligatorio.
- **Excepción · Inglés:** en toda pregunta de Inglés (suelta, de bloque o de parte) no se exige `?`, porque muchas tareas son «completa la frase». En las partes, además, el enunciado puede ir vacío (la pregunta queda solo con sus opciones, como en «completar el texto»).

### Prohibido dentro del enunciado

- Referencias a otros números de pregunta: `(ejercicio 53)`, `ver pregunta 12`, `según la tabla de la pregunta anterior`.
  **Si dos preguntas comparten un recurso (tabla, gráfica, lectura), deben ir como bloque de lectura compartida.** Ver sección 2.8.
- Texto de trabajo o instrucciones de redacción. Todo lo que esté en el archivo se imprime.
- Referencias de posición: `la tabla de arriba`, `la imagen de la izquierda`. Use `la siguiente tabla`, `la imagen`.

---

## 2.5 Bloque [2] · Opciones de respuesta

Formato exacto de cada opción, como párrafo independiente:

```
A. texto de la opción
B. texto de la opción
C. texto de la opción
D. texto de la opción
```

Reglas:

- Siempre cuatro opciones, siempre A, B, C, D en ese orden. Sin excepciones.
- La letra y el punto van en **negrita**, seguidos de un espacio. El texto de la opción va en redonda, salvo el formato que el contenido necesite (superíndices, cursiva de un término).
- **Cada opción ocupa exactamente un párrafo.** Una opción empieza en el párrafo `A. ` y termina en ese mismo párrafo. Así el sistema sabe siempre dónde termina la `D` y dónde empieza la pregunta siguiente de un bloque.
- Si la opción es gráfica, la imagen va **en el mismo párrafo**, después de `A. `, en línea con el texto.
- No se permiten tablas en las opciones.
- **Las opciones deben ser intercambiables.** Como la plantilla de respuestas mueve la correcta a otra letra, no se permite:
  - `A y B son correctas`, `Ninguna de las anteriores`, `Todas las anteriores`.
  - Opciones que dependen del orden (`la primera`, `la anterior`).
  - El validador rechaza, sin distinguir mayúsculas ni tildes:
    - En cualquier parte de la opción: «todas las anteriores», «ninguna de las anteriores», «la primera opción» / «la última opción» (o respuesta, alternativa), y «opción anterior» / «respuestas anteriores».
    - Cuando la opción **no dice nada más que eso**: «las anteriores», «la anterior», «las dos anteriores», «ninguna es correcta», «todas son correctas», o solo letras unidas (`A y B`, `A, B y C`).
    - Letras citadas como respuesta: «A y B son correctas», «las opciones A y C».
  - Lo que **sí se permite**, porque habla del contenido y no de las otras opciones: «la primera ley de Newton», «cada nivel concentra la energía de los anteriores», «la vitamina A y B».
  - Una sola imagen que contenga las cuatro opciones con las letras dibujadas dentro. Si las opciones son gráficas, van **cuatro imágenes separadas**, una por opción.
- Valores numéricos en orden creciente **no** son un impedimento: el sistema los reordena y eso es aceptable en pruebas de selección múltiple.

---

## 2.6 Bloque [3] · TABLA DE RESPUESTAS

Encabezado literal, en párrafo propio, en negrita y mayúsculas:

```
TABLA DE RESPUESTAS
```

Tabla de 3 columnas, con fila de encabezado:

| N° | Clave | Justificación de la respuesta correcta |
|---|---|---|
| *(vacío)* | B | Texto de la justificación… |

Reglas:

- La columna **N°** se deja **vacía**. El sistema la llena con el número definitivo.
- **Clave:** una sola letra mayúscula, `A`, `B`, `C` o `D`. Es la letra **en el archivo de carga**, antes de aplicar la plantilla.
- **Justificación:** solo de la respuesta correcta. Texto plano.
  - **Prohibido mencionar letras de opción** (`la B es incorrecta porque…`). Al aplicar la plantilla, la letra cambia y la justificación quedaría equivocada. Se rechaza: `opción`, `literal`, `respuesta` o `alternativa` seguidas de `A`–`D`; un artículo y una letra seguidos de un juicio sobre ella (`la B es correcta`, `la C no es la respuesta`); `C)` fuera de un paréntesis abierto; y `A y B`, `A o B`. Símbolos y rótulos legítimos sí se permiten: `el C` (carbono), `(vitamina C)`, `(tipo B)`, `P(A ∩ B)`.
  - Se refiere al contenido: `la expresión con un solo signo…`, no `la opción B…`.
  - Sin imágenes. Solo texto y, si es indispensable, superíndices.
- En un bloque de lectura compartida, una fila por cada pregunta del bloque, en orden.

---

## 2.7 Bloque [4] · TABLA DE EXCEL

Encabezado literal, en párrafo propio, en negrita y mayúsculas:

```
TABLA DE EXCEL
```

Tabla de **10 columnas**, con fila de encabezado exacta:

| Preg. | Correcta | Grado | Materia | Submateria | Pensamiento | Competencia | DBA | Temática | Nivel |
|---|---|---|---|---|---|---|---|---|---|

Reglas:

- **Preg.** se deja **vacía**. La llena el sistema.
- **Correcta** debe coincidir con la Clave de la TABLA DE RESPUESTAS. Si no coinciden, el archivo se rechaza.
- **Grado** es obligatorio: `3°`, `4°`, `5°`, `6°`, `7°`, `8°`, `9°`, `10°`, `11°` o `ICFES`. También se acepta el código (`33`, `77`, `13`…). Al subir, la pantalla muestra el grado leído de cada archivo antes de guardarlo. El grado **no** va al Excel de salida.
- **Materia, Submateria, Pensamiento, Competencia, DBA, Temática** se escriben completos. El sistema los normaliza al guardar (Parte 1.7) y avisa si se parecen a un valor ya registrado.
- **Nivel** se escribe completo: `Básico`, `Medio` o `Avanzado`.
- En un bloque de lectura compartida, una fila por pregunta, en orden.

### Campos obligatorios y opcionales

Se carga **toda la información que traiga el ejercicio**. Lo que venga se usa; lo que venga vacío no se usa (no aparece en la línea ➤ ni en el Excel).

| Campo | Regla |
|---|---|
| Preg. | Siempre vacío |
| Correcta | Obligatorio |
| Grado | Obligatorio |
| Materia | Obligatorio, del catálogo |
| Submateria | Obligatoria en Matemáticas, Lengua Castellana y Ciencias Naturales, y debe pertenecer a la materia. En Ciencias Sociales es opcional (vacía = Ciencias Sociales general). En las demás materias va vacía. **Excepciones:** en grado `ICFES`, Matemáticas puede ir con o sin submateria; en `3°`, `4°` y `5°`, Matemáticas y Lengua Castellana van **sin** submateria (Ciencias Naturales sí la lleva) |
| Pensamiento | Opcional |
| Competencia | Opcional |
| DBA | Opcional; si se llena, con el formato de 1.7 |
| Temática | **Obligatoria** (es filtro obligatorio del buscador) |
| Nivel | Obligatorio en todos los grados excepto `ICFES`, donde va vacío |

En un bloque o una parte, **todas las filas** deben tener el mismo Grado, Materia y Submateria.

Fuera de estas reglas, **el archivo se rechaza**.

---

## 2.7B Bloque [5] · TABLA DE GLOSARIO (opcional)

Sirve para explicar palabras difíciles de una pregunta. **Solo se imprime si al armar la cartilla se marca la casilla «Incluir glosario»**; si no se marca, el ejercicio sale sin glosario.

Encabezado literal, en párrafo propio, en negrita y mayúsculas, **después de la TABLA DE EXCEL**:

```
TABLA DE GLOSARIO
```

Tabla de 3 columnas, con fila de encabezado exacta:

| Pregunta | Término | Significado |
|---|---|---|
| 1 | cambio | Dinero que se devuelve cuando se paga con un valor mayor al de la compra. |

Reglas:

- **Pregunta:** número de la pregunta **dentro del archivo**: `1` en un ejercicio suelto; `1`, `2`, `3`… en un bloque o una parte. Es obligatorio.
- **Término:** máximo 40 caracteres, escrito igual que en el texto de la pregunta (las mayúsculas no importan). En un bloque o una parte, el término puede estar en la lectura o el recurso compartido.
- **Significado:** máximo 150 caracteres, texto plano. Si no termina en punto, el sistema se lo pone al imprimir.
- Máximo **3 términos por pregunta**, sin repetir.
- **Admite fórmulas (07/10/2026)**: superíndices, subíndices y ecuaciones del editor de Word. En
  Matemáticas y en Ciencias un significado sin fórmula muchas veces no dice nada: «i² = −1» escrito
  «i2 = −1» es otra cosa. El sistema guarda **cómo está escrito** —no solo el texto— y lo imprime igual,
  al tamaño del glosario (8 pt).
- **No admite imágenes ni objetos incrustados**: no caben en una línea de 8 pt.
- Sin corchetes de plantilla ni texto de trabajo.
- Las filas completamente vacías se ignoran (la plantilla trae una). Si el ejercicio no lleva glosario, la tabla se deja vacía o se borra junto con su rótulo.
- El glosario no cambia la huella del ejercicio (regla 28): para agregarle glosario a un ejercicio que ya está en el banco, se elimina y se vuelve a subir (5.3B).

Cómo se imprime: 3.5B, «Glosario de la pregunta».

---

## 2.8 Bloques de lectura compartida

Un bloque es un recurso (lectura, tabla, gráfica, esquema) más las preguntas que dependen de él. **El bloque se usa siempre completo.**

### Estructura del archivo

```
[0] FRASE DE REFERENCIA        ← el sistema la reescribe
[0b] EL RECURSO COMPARTIDO      ← lectura, tabla, gráfica
[1] pregunta 1 del bloque + opciones
[1] pregunta 2 del bloque + opciones
    …
[3] TABLA DE RESPUESTAS         ← una fila por pregunta
[4] TABLA DE EXCEL              ← una fila por pregunta
```

### Cómo lee el sistema el archivo

1. El primer párrafo es la frase de referencia.
2. El recurso va desde el segundo párrafo hasta la **línea de crédito**, incluida. La línea de crédito es **obligatoria** en los bloques: es la que marca dónde termina la lectura.
3. Desde el párrafo siguiente empieza el enunciado de la primera pregunta. Cada pregunta termina en su párrafo `D.`; la siguiente empieza en el párrafo de después.

Un bloque tiene **mínimo 2 preguntas**. Al armar la cartilla se pueden quitar preguntas del bloque, siempre que queden al menos 2.

### Frase de referencia

Se escribe **exactamente** así, en negrita, como párrafo propio, con los marcadores `#N` y `#M`:

```
Responde las preguntas #N a #M de acuerdo con la siguiente lectura.
```

El sistema sustituye `#N` y `#M` por los números reales que le correspondan en la cartilla. Nunca se escriben números literales.

Para recursos que no son lectura, la variante permitida es:

```
Responde las preguntas #N a #M de acuerdo con la siguiente información.
```

### Separador entre preguntas del bloque

Entre una pregunta y la siguiente dentro del bloque, el sistema inserta el número. En el archivo de carga, cada pregunta arranca en párrafo nuevo sin número.

### Línea de crédito

Último párrafo del recurso, **alineado a la derecha, todo en cursiva, 8 pt**. Si el texto no tiene autor externo, se escribe:

```
Texto elaborado para este simulacro. PRAXIS · THINKS.
```

El sistema reconoce la línea de crédito **por su formato** (derecha + cursiva completa). Por eso ese formato está **prohibido en cualquier otro párrafo** del archivo.

---

## 2.8B Partes de Inglés

Una parte se carga completa en un solo archivo, con esta estructura:

```
[0]  SUBTÍTULO             PARTE #P · Título — preguntas #N a #M   (negrita)
[0b] INSTRUCCIÓN           exactamente un párrafo
[0c] RECURSO (opcional)    termina en su línea de crédito
[1]  preguntas + opciones  el enunciado puede ir vacío
[3]  TABLA DE RESPUESTAS
[4]  TABLA DE EXCEL
```

- `#P`, `#N` y `#M` se dejan tal cual. El sistema numera las partes en el orden en que quedan dentro de la sección de Inglés.
- El separador entre `#P` y el título es `·`; entre el título y `preguntas` es `—`. El sistema acepta también `-` o `–` y los reescribe como `—`.
- Si la parte tiene recurso, la línea de crédito es obligatoria. Si no hay línea de crédito, el sistema entiende que **no hay recurso** y que la primera pregunta empieza justo después de la instrucción.
- Una parte tiene mínimo 2 preguntas y **nunca** se recorta.

### Partes de «completar el texto»

En estas partes el recurso es un texto con espacios, y cada pregunta corresponde a un espacio. Los espacios se marcan con **marcadores relativos a la parte**: `(#1)`, `(#2)`, `(#3)`… El sistema los reescribe con el número real de la pregunta en la cartilla: `(#1)` → `(134)`.

- Debe haber **exactamente un marcador por pregunta**, en orden, de `(#1)` hasta `(#k)`, siendo *k* el número de preguntas de la parte. Si falta uno, sobra uno o están desordenados, el archivo se rechaza.
- Las preguntas de estas partes van con el enunciado vacío: solo sus cuatro opciones.
- Se prohíbe escribir números reales en el texto, igual que en los rangos `#N` y `#M`.

### Presentación de las partes en la cartilla

- Antes de cada subtítulo `PARTE n`, el sistema inserta una línea horizontal negra de **0,25 pt** (la más delgada que admite Word), del ancho de la columna, para separar las partes.
- El subtítulo va en negrita; la instrucción, en el párrafo siguiente, en cursiva. El subtítulo nunca queda solo al final de una columna.
- Los avisos de la parte «Avisos y anuncios» se cargan como imagen PNG (2.10).

---

## 2.9 Reglas de fórmulas y notación matemática

Esta es la regla más importante para que la cartilla salga como en los libros.

### 2.9.1 Superíndices y subíndices simples

Se hacen con **formato de texto de Word** (Inicio → Superíndice / Subíndice), en Tahoma.

Ejemplos: `5x²`, `H₂O`, `cos²θ`, `sen²θ + cos²θ = 1`

Ventajas: conservan la fuente del documento, se ven limpios y no se rompen nunca.

**Prohibido escribir `x2` o `sen2θ` sin formato de superíndice.** Es el error más frecuente, y el validador lo rechaza con esta regla exacta: en Matemáticas, Física, Química, Biología y Tecnología y Medio Ambiente, se rechaza toda letra, `)` o `θ` seguida inmediatamente de un dígito en texto normal (sin superíndice ni subíndice). Ejemplos rechazados: `x2`, `H2O`, `cos2θ`, `(a+b)2`.

Las escrituras legítimas que cumplen ese patrón (`B12`, `MP3`, `COVID19`…) se registran en una **lista de excepciones** editable desde la aplicación. Lo que está en la lista se acepta en todas las materias.

### 2.9.2 Fracciones  *(norma cambiada el 06/11/2026)*

Lo que decide es que **la fracción se lea con claridad**. La forma preferida es **apilada**, hecha con el editor de ecuaciones de Word: el numerador sobre la barra y el denominador debajo, como en un libro de texto. A tamaño normal con barra también se acepta, porque se lee grande y sin esfuerzo.

Lo que se rechaza, con la regla 18, es la fracción **diminuta**:

| Forma | Veredicto |
|---|---|
| fracción apilada del editor de ecuaciones | **preferida** |
| `3/8` a tamaño normal (con `/`, `⁄` o `∕`) | aceptada |
| `³/₈` con numerador en superíndice o denominador en subíndice | **rechazada** |

**Por qué cambió.** Hasta la v1.2 el estándar *exigía* `³/₈`, por caber en la columna sin alterar el interlineado. Impresa a 9 pt, esa fracción sale tan pequeña que cuesta leerla, y en un banco de ejercicios que se va a reutilizar durante años eso no compensa. La apilada cuesta unos milímetros de alto de renglón y se acepta ese costo; la escrita a tamaño normal no cuesta nada y también vale.

Siguen escribiéndose como texto normal, porque no son fracciones:

- Las razones en prosa: «3 de cada 8 estudiantes», «la razón es de 3 a 8».
- Los porcentajes y los decimales: 37,5 %, 0,375.
- Las unidades compuestas con letras: km/h, m/s.

### 2.9.3 Editor de ecuaciones de Word (OMML)

Se usa en **toda expresión que ocupe dos alturas** o que lleve un signo que no es un carácter corriente:

- Fracciones y números mixtos
- Raíces, de cualquier índice
- Sumatorias, productorias, integrales, límites
- Matrices y sistemas de ecuaciones
- Potencias cuyo exponente es una expresión

Además, el validador rechaza con la regla 18:

- El signo `√` escrito como carácter suelto: la raíz lleva su barra sobre todo el radicando.
- Las potencias escritas con símbolos: `x^2`, `2**3`. Van con superíndice de Word o con el editor.

La ecuación se inserta con **Insertar → Ecuación** y queda en Cambria Math dentro del objeto. Fuera de la ecuación todo sigue en Tahoma.

### 2.9.4 Prohibido siempre

| Formato | Razón |
|---|---|
| Microsoft Equation 3.0 | Obsoleto y bloqueado por seguridad en Word actual |
| MathType | Depende de un complemento; si no está instalado aparece un recuadro vacío |
| Ecuación como imagen | Se ve borrosa al imprimir y no escala a dos columnas |
| Fracción escrita como `3/4` en texto plano | Inconsistente con el resto de la cartilla. Se rechaza todo `número/número` en texto normal, en cualquier materia. Las fechas se escriben sin barra (`12 de mayo de 2024`) |

El validador rechaza automáticamente los archivos que contengan cualquiera de estos formatos. Equation 3.0 y MathType se detectan porque son **objetos incrustados**: se rechaza cualquier objeto incrustado (OLE), sea cual sea.

> **Límite del validador:** una ecuación pegada como imagen es, para la máquina, una imagen más; no se puede distinguir de una gráfica. Esa regla queda bajo responsabilidad del autor (lista de chequeo del instructivo).

---

## 2.10 Reglas de imágenes y gráficas

| Regla | Valor |
|---|---|
| Formato | PNG |
| Posición | **En línea con el texto** (nunca flotante) |
| Ancho máximo | **8,4 cm** |
| Resolución mínima | 300 ppp al tamaño final |
| Color | Escala de grises o blanco y negro |
| Fondo | Blanco, sin transparencia |

Reglas adicionales:

- Sin efectos artísticos, sombras, bordes decorativos ni marcos de Word. Estos generan archivos `.wdp` internos y oscurecen la imagen al imprimir en blanco y negro.
- Sin cuadros de texto (`text box`) alrededor de la imagen. Las etiquetas van dentro del PNG.
- Los rótulos dentro de la imagen deben ser legibles a 8,4 cm de ancho: mínimo 8 pt equivalente. *(No verificable por máquina: responsabilidad del autor.)*
- En el enunciado y en el recurso, la imagen va **en párrafo propio**, centrada, sin texto en ese párrafo. En las opciones va en el párrafo de la opción (2.5).
- Si la imagen lleva pie, va en párrafo propio inmediatamente debajo, centrado, 8 pt.

Cómo se verifica cada regla:

| Regla | Verificación exacta |
|---|---|
| PNG | Tipo real del archivo interno |
| En línea | Se rechaza toda imagen anclada (flotante) |
| Ancho | Ancho declarado en el Word ≤ 8,4 cm |
| 300 ppp | Píxeles de ancho ÷ ancho en pulgadas ≥ 300 |
| Escala de grises | Todos los píxeles con rojo = verde = azul |
| Sin transparencia | Sin canal alfa, o canal alfa totalmente opaco |
| Sin efectos | Se rechazan sombras, efectos artísticos, bordes de imagen y archivos `.wdp` |
| Sin cuadros de texto | Se rechaza todo cuadro de texto, forma o lienzo de dibujo |

> **Por qué 8,4 cm:** la columna de la cartilla mide 9,12 cm. Se dejan 0,72 cm de margen de seguridad para que ninguna imagen se desborde, ni siquiera si la maqueta cambia levemente.

---

## 2.11 Reglas de tablas dentro del ejercicio

| Regla | Valor |
|---|---|
| Ancho | 100 % de la columna, máximo 8,4 cm |
| Fuente | Tahoma 8 pt |
| Encabezado | **Negrita** (es lo que marca que la primera fila es el encabezado). El **centrado lo aplica el sistema** al armar la cartilla |
| Bordes | Sencillos, negros, 0,5 pt |
| Relleno | Blanco. Sin sombreados de color |
| Alineación vertical | Centrada |
| Filas | Marcar **«No dividir la fila entre páginas»** |

- Las celdas combinadas **se permiten**: no hay forma exacta de decidir cuándo son «innecesarias».
- Sin tablas anidadas.
- Máximo 4 columnas: más columnas no caben legibles en 8,4 cm.

Todas las reglas de la tabla anterior se verifican de forma exacta sobre el Word. «Relleno blanco» significa sin sombreado o con sombreado `FFFFFF`. La fila de encabezado es la primera.

**En la cartilla** la tabla sale **centrada en la columna y compacta**, con la primera fila centrada y las
**columnas de datos cortos también centradas** (07/10/2026): se centra una columna cuando **todas** sus
celdas con contenido son números o palabras cortas —hasta 12 caracteres y 2 palabras—, y esas celdas quedan
además a media altura. Se decide por columna y no por celda, porque centrar una celda suelta en una columna
de texto largo se ve desalineado; si la tabla tiene celdas combinadas no se toca nada. El resto del texto
conserva la alineación del autor: el sistema quita el espacio antes y después de los párrafos de cada celda, deja interlineado sencillo y 1 pt de margen arriba y abajo en cada celda, sin tocar la alineación del texto. Deja **6 pt de aire a los dos lados** de la tabla: como una tabla no tiene espaciado propio, el sistema se lo pone a los párrafos que la rodean (07/10/2026). Los bordes y márgenes de celda que vengan del estilo de tabla del Word de carga (por ejemplo «Tabla con cuadrícula» o «Table Grid») se escriben en la propia tabla, para que se vean igual aunque la cartilla no tenga ese estilo.

---

## 2.12 Resumen de validaciones automáticas de entrada

Cada regla es **exacta**: o se cumple o no se cumple. No hay advertencias que dejen entrar un archivo dudoso.

El archivo se **rechaza** si:

**Estructura**

1. No tiene exactamente un párrafo `TABLA DE RESPUESTAS` y uno `TABLA DE EXCEL`, cada uno seguido de su tabla; o la `TABLA DE GLOSARIO` (opcional) no va al final, después de la TABLA DE EXCEL.
2. La TABLA DE RESPUESTAS no tiene las 3 columnas, o la TABLA DE EXCEL no tiene las 10 columnas, con los nombres exactos.
3. El número de filas de las dos tablas no coincide con el número de preguntas detectadas.
4. Las columnas `N°` o `Preg.` traen algo escrito.
5. Una pregunta no tiene exactamente cuatro opciones `A.`, `B.`, `C.`, `D.`, en orden, cada una en un párrafo, con letra y punto en negrita.
6. Un bloque no empieza con la frase de referencia exacta, o una parte no empieza con el subtítulo exacto.
7. Un bloque no tiene línea de crédito o tiene menos de 2 preguntas. Una parte no tiene su párrafo de instrucción o tiene menos de 2 preguntas.
8. El formato de línea de crédito (derecha + cursiva) aparece en otro lugar.

**Datos**

9. La Clave y la columna Correcta no coinciden, o no son una sola letra `A`–`D`.
10. Grado, Materia, Submateria, DBA, Temática o Nivel incumplen las reglas de 1.7 y 2.7.
11. En un bloque o una parte, las filas no comparten Grado, Materia y Submateria.

**Contenido**

12. Un párrafo del enunciado empieza con un número de pregunta (2.4).
13. Una pregunta que no es de Inglés no termina en `?` (2.4).
14. Hay una referencia cruzada: `ejercicio`, `pregunta`, `punto` o `numeral` seguidos de un número; `pregunta anterior` o `pregunta siguiente`.
15. Hay una referencia de posición: `tabla`, `imagen`, `gráfica`, `figura`, `esquema` o `texto` seguidos de `de arriba`, `de abajo`, `de la izquierda` o `de la derecha`.
16. Una opción contiene expresiones prohibidas (2.5).
17. La justificación menciona una letra de opción (2.6) o contiene imágenes.
18. Hay `x2` sin superíndice o `3/4` en texto plano (2.9).
19. En una parte de «completar el texto», los marcadores `(#1)`…`(#k)` no están completos y en orden (2.8B).
20. Hay texto de trabajo: texto de plantilla entre corchetes (tres o más palabras, como `[texto de la opción]`; un intervalo como `[0, 1]` sí se permite), comentarios de Word, control de cambios, texto resaltado, texto oculto, texto de color (incluidos los colores del tema aclarados u oscurecidos), o una frase de la **lista de frases prohibidas** (editable; de fábrica, escritas exactamente así: `Qué NO debe aparecer`, `Nota para`, `NOTA:`, `TODO`, `PENDIENTE`, `REVISAR`, `BORRAR`). En minúscula son contenido legítimo («la pendiente de una recta», «una nota para aprobar»).

**Formato**

21. La página no es carta vertical con márgenes de 1,27 cm, o tiene más de una columna.
22. Hay texto en una fuente distinta de Tahoma fuera de las ecuaciones, incluidos los símbolos insertados con otra fuente (Insertar › Símbolo en Symbol o Wingdings).
23. Hay un tamaño de letra distinto de 9 pt, salvo 8 pt en tablas, en la línea de crédito y en el pie de imagen.
24. Hay un objeto incrustado (Equation 3.0, MathType u otro).
25. Una imagen incumple 2.10. Los ppp se calculan con la parte visible de la imagen si está recortada en Word.
26. Una tabla del ejercicio incumple 2.11.
27. Un párrafo impreso usa viñetas o numeración automática de Word. Los números o viñetas se escriben como texto (`I.`, `1.`, `•`), porque la numeración automática no se puede copiar a la cartilla sin alterarse.
28. El mismo contenido (mismas preguntas y opciones) ya está en el banco. Para corregir un ejercicio se elimina el anterior y se vuelve a subir (5.3B).

**Glosario**

29. La TABLA DE GLOSARIO incumple 2.7B: encabezados distintos de `Pregunta · Término · Significado`; número de pregunta que no está en el archivo; término o significado vacío o demasiado largo; término que no aparece en el texto de su pregunta; término repetido; más de 3 términos en una pregunta; o una imagen u objeto incrustado (las fórmulas sí se admiten).

Por cada motivo, el sistema indica **dónde** está: pregunta, párrafo y el texto exacto que lo causó.

El archivo queda **pendiente de confirmación** (no entra hasta que la persona responde) si:
- Una temática, competencia, pensamiento o DBA se parece a uno ya registrado sin ser idéntico (1.7).

El sistema **informa**, sin bloquear:
- Que una imagen mide entre 8,0 y 8,4 cm.
- Qué párrafos conservarán una alineación distinta de justificada (izquierda, centrada o derecha aplicada a mano), para que el autor confirme que es a propósito.

**No verificable por máquina** (responsabilidad del autor, en la lista de chequeo del instructivo):
- Ecuaciones pegadas como imagen.
- Legibilidad de los rótulos dentro de las imágenes.
- Que las opciones sean intercambiables en su sentido, más allá de las expresiones prohibidas.
- Que la justificación sea correcta.

## 2.13 Pensamiento y competencia por submateria (07/10/2026)

El **pensamiento depende de la submateria**, no solo de la materia. Vive en `PEDAGOGIA`
(`app/catalogos_base.py`) y de ahí lo toma el prompt del Panel.

| Materia · Submateria | Pensamiento | Competencia |
|---|---|---|
| Matemáticas (I y II) | Numérico-variacional · Geométrico-métrico · Aleatorio | Comunicación y representación · Razonamiento y argumentación · Planteamiento y resolución de problemas |
| Lengua Castellana · Español | Literatura · Producción textual | Comprensión e interpretación de textos literarios · Reconocimiento y uso de la estructura de la oración |
| Lengua Castellana · Comprensión Lectora y Lectura Crítica | Lectura crítica | Recupera información literal · Comprende el sentido local mediante inferencias · Comprende el sentido global mediante inferencias · Asume una posición crítica |
| Ciencias Sociales | Historia y cultura · Relaciones espaciales y ambientales · Relaciones ético-políticas | Temporalidad · Espacialidad · Culturalidad · Institucionalidad y derechos humanos |
| Ciencias Naturales · Biología | Entorno vivo | Uso comprensivo del conocimiento científico · Explicación de fenómenos · Indagación |
| Ciencias Naturales · Física y Química | Entorno físico | (las mismas) |
| Inglés | Lectura · Conversación · Escritura · Escucha · Monólogo | Competencia lingüística · Competencia pragmática · Competencia sociolingüística |

En las demás materias (Filosofía, Informática, Educación Física, Religión, Ética, Dibujo, Electricidad,
Mecánica, Educación Artística) el pensamiento y la competencia son **libres**: se usan los del plan de área.

El **DBA** se toma de la malla del grado y se escribe «DBA 4». Si la malla da varios para el mismo tema, se
elige el que corresponde al contenido de la pregunta; si no se sabe con certeza, se deja vacío.

> Esto **no lo valida** el sistema todavía: es la guía con la que se preparan los ejercicios. El validador
> sigue aceptando cualquier texto en esas dos columnas, para no rechazar lo que ya está cargado.

Esta tabla se publica en tres sitios, y los tres salen de `PEDAGOGIA`: el **prompt del Panel**, el
**instructivo de normalización** y la hoja «Pensamiento y competencia» del **Excel de códigos**.

---

# PARTE 3 · FORMATO DE SALIDA
## Cartilla en Word

## 3.0B Portada y cierre (07/10/2026)

La portada y el cierre **no están en el código**: viven en plantillas de Word, para poder retocarlas a mano.

| Plantilla | Para qué |
|---|---|
| `PLANTILLA_CARTILLA_BASE.docx` | **Portada completa**: ocupa toda la primera página, con la tabla de áreas. El cuerpo empieza en la página siguiente |
| `PLANTILLA_CARTILLA_MEDIA.docx` | **Media portada**: título, ilustración y los recuadros de datos arriba; las preguntas arrancan **debajo, en la misma página** |

Se eligen en el paso de revisión, antes de generar. Técnicamente, la diferencia es el corte entre la portada
y el cuerpo: `nextPage` en la completa y `continuous` en la media.

**Qué pone el sistema en la media portada**, texto por texto: el título, el periodo, el código de cartilla,
el grado, el total de preguntas y el tiempo. El título lo escribe quien arma la cartilla; si lo deja vacío,
se usa el nombre de su materia, y si la cartilla es de varias, «Simulacro de preparación estratégica».

**La ilustración se puede cambiar.** Cada cartilla puede traer su propia imagen (PNG, JPG o WEBP, hasta
6 MB), que reemplaza la de la plantilla. Se sube desde la misma pantalla y se puede quitar para volver a la
de la plantilla. El sistema reemplaza **el dibujo más grande de la portada**, que es la ilustración del tema;
el logo, los iconos y los recuadros no se tocan, para que la identidad de PRAXIS sea siempre la misma.

**Cierre con código QR.** Las dos plantillas terminan igual: el recuadro **«¡ESCANEA Y APRENDE!»** con el
código QR —el mismo para todas— y, debajo, «¡Prueba finalizada!», la frase de cierre y el bloque de derechos
reservados. El recuadro es la **forma original de PRAXIS**, con sus esquinas redondeadas y su borde grueso:
se copia tal cual de la cartilla de muestra en vez de rehacerla, para que salga exactamente como se diseñó.

> Las plantillas se rehacen con `python -m scripts.construir_plantillas_portada`, que parte de
> `plantillas/origen/`. Ahí están la portada completa original y el QR, para no depender de archivos sueltos.

## 3.1 Configuración de página

| Parámetro | Valor |
|---|---|
| Tamaño | Carta (21,59 × 27,94 cm) |
| Orientación | **Vertical** |
| Margen superior | 1,27 cm |
| Margen inferior | **1,55 cm** |
| Margen izquierdo | 1,27 cm |
| Margen derecho | 1,27 cm |
| Margen de encuadernación (gutter) | **0 cm** |
| Distancia del pie de página al borde | 0,5 cm |
| Encabezados y pies distintos en páginas pares e impares | Activado |
| Ancho útil de texto | 19,05 cm |
| Espacio entre columnas | 0,8 cm, con línea separadora |
| **Ancho de cada columna** | **9,12 cm** |

> **Márgenes estrechos (v1.1).** Son los márgenes «Estrecho» de Word: 1,27 cm, **sin margen de encuadernación**. Se aplican igual a la portada, al cuerpo y al cierre. Frente a la v1.0 cada columna gana 0,25 cm. En la v1.2 el espacio entre columnas baja de 1,27 a 0,8 cm y cada columna pasa de 8,89 a 9,12 cm.

> **Margen inferior de 1,55 cm (07/10/2026).** Es el único que no mide 1,27 cm. La **línea que separa las dos
> columnas** se dibuja hasta el borde inferior de la caja del último párrafo, y esa caja incluye los 14 pt de
> separación que van detrás de cada pregunta. Con 1,27 cm la línea se metía encima del número de página en
> varias hojas. Con 1,55 cm quedan 5 pt de holgura. Comprobado en el PDF de una cartilla de 26 páginas:
> ninguna línea separadora invade el pie.

> **Corrección necesaria:** la cartilla actual declara `orientación = horizontal` con medidas verticales. Es una contradicción interna que puede alterar la impresión. El sistema generará siempre orientación vertical.

La impresión tipo revista se hace con la función **Folleto** de la impresora, que toma dos páginas carta y las
imprime en una hoja de **11 × 17 pulgadas** (doble carta). El Word no necesita reordenar páginas: por eso el
cuadernillo tiene que terminar en un **múltiplo de 4 páginas** (3.7), que son las cuatro caras de cada hoja doblada.

**Color de impresión:** la **portada va a color**; el cuerpo y el cierre se imprimen en **blanco y negro**. Por eso nada del cuerpo usa color: texto negro, imágenes en escala de grises, tablas sin sombreado y títulos de sección en negro.

## 3.2 Secciones del documento

| Sección | Contenido | Columnas |
|---|---|---|
| 1 | Portada | 1 |
| 2 | Cuerpo de la prueba | 2 |
| 3 | Vocabulario, cierre, créditos, QR | 1 |

## 3.3 Pie de página

- Texto del pie, exacto: `PRAXIS – THINKS | Educación & Práctica`.
- Páginas impares: número de página a la izquierda, el texto del pie a la derecha.
- Páginas pares: el texto del pie a la izquierda, número de página a la derecha.
- El número se inserta con **campo automático de Word**, no como texto.
- La portada no lleva pie.

## 3.4 Portada

Elementos y origen del dato:

| Elemento | Origen |
|---|---|
| Título (`Simulacro de Preparación Estratégica`) | Configurable por plantilla |
| Imagen de portada | Configurable |
| `Simulacro N° _ \| …` | El número se digita; el resto sale del tipo de material (tabla abajo) |
| `Código Cartilla:` | Código completo de diez dígitos, validado |
| Grado | Del código: `3°` a `11°`; en grado `13` se imprime `Saber 11` |
| Tipo de prueba | Fijo: `Selección múltiple única respuesta` |
| **N° de preguntas** | **Calculado por el sistema** |
| Tiempo | **Calculado**: 2 minutos por pregunta (tabla abajo). Se puede corregir a mano antes de generar |
| Sesión | **No se imprime**: la sesión se identifica en el código |
| Institución | **No la pone el sistema**: se agrega a mano si se requiere |
| **Tabla Área / N. preguntas** | **Calculada por el sistema** |
| Instrucciones | Texto fijo, editable por plantilla |
| Logos y alianza | Configurable |

Colores de la tabla de áreas (solo en la portada, que va a color). Cada materia tiene su color; las submaterias usan el de su materia:

| Materia | Color |
|---|---|
| Matemáticas | Azul `#3F6FB5` |
| Lengua Castellana | Ocre `#B8860B` |
| Ciencias Naturales | Verde `#5E9632` |
| Ciencias Sociales | Naranja `#C8641E` |
| Filosofía | Verde azulado `#1F8A8A` |
| Inglés | Magenta `#A0289A` |
| Informática | Violeta `#6A4FB3` |
| Educación Física | Rojo `#C62828` |
| Educación Artística | Rosa `#D2457F` |
| Religión | Café `#8D5A2B` |
| Ética | Verde bosque `#2E7D5B` |
| Dibujo | Gris azulado `#4F6D7A` |
| Electricidad | Azul marino `#1A3A6B` |
| Mecánica | Gris `#555555` |

Una materia nueva recibe su color al crearla en la aplicación.

Línea `Simulacro N°` según el tipo de material (dos recuadros, como en la plantilla actual):

| Tipo | Texto impreso |
|---|---|
| `11` · `22` · `33` · `44` | `Simulacro N° X \| 1° Periodo` (2°, 3° o 4° según el tipo) |
| `71` · `72` | `Simulacro N° X \| Simulacro ICFES` |
| `55` | `Simulacro N° X \| Simulacro especial` |

La **tabla de áreas** se reconstruye con tantos renglones como secciones tenga la cartilla (4 en E5, 11 en E2…).

**Tiempo:** 2 minutos por pregunta, escrito en horas y minutos. `140` → `4 horas y 40 minutos` · `116` → `3 horas y 52 minutos` · `80` → `2 horas y 40 minutos` · `30` → `1 hora`. La persona puede corregirlo antes de generar.

**Excepción ICFES:** en las sesiones `71` y `72` se imprime siempre `4 horas y 30 minutos`, el tiempo de la prueba real, sin importar el número de preguntas.

> **Regla dura:** el total de preguntas de la portada y la suma de la tabla de áreas son **siempre** calculados por el sistema a partir de los ejercicios realmente incluidos. Nunca se digitan. Esto elimina la posibilidad de que la portada no coincida con el contenido.

## 3.5 Cuerpo de la prueba

### Títulos de sección

Párrafo propio, centrado, Tahoma negrita 12 pt, mayúsculas, con espacio antes y después.

Cada sección tiene un **título impreso** propio, que se define en la estructura y puede no coincidir con el nombre de la submateria. Es un tercer dato, independiente de Materia y Submateria.

```
MATEMÁTICAS I
LENGUA CASTELLANA     ← sección cuya submateria es Español
COMPRENSIÓN LECTORA
BIOLOGÍA
```

**Regla confirmada:** la sección de Español se imprime como `LENGUA CASTELLANA`. Las demás secciones usan el nombre de su submateria, o el de la materia cuando no tiene submateria.

El nombre que se imprime como título es el mismo que aparece en la tabla de áreas de la portada, **y en el mismo orden**. El sistema garantiza que coincidan.

### Separación entre secciones

- Una sección **nunca se mezcla con otra**. Todas sus preguntas van seguidas, entre su título y el título de la siguiente.
- El título **nunca queda huérfano** al final de una columna: si no caben al menos el título y las primeras líneas de su primera pregunta, la sección arranca en la columna siguiente.
- Una sección **no empieza en página nueva** por defecto. El objetivo es aprovechar el espacio.
- El título de sección se imprime **siempre**, también en un simulacro de una sola materia.

### Partes dentro de una sección

Algunas secciones se dividen en **partes**, cada una con su propio subtítulo y su línea de instrucción. Hoy solo Inglés las usa, y su reparto cambia según el tipo de prueba.

Formato del subtítulo, en negrita, alineado a la izquierda, con marcadores de rango:

```
PARTE 1 · Vocabulario en contexto — preguntas #N a #M
```

Debajo, la línea de instrucción de la parte, en redonda:

```
Lee cada descripción en inglés y elige la palabra que le corresponde. Las opciones son palabras sueltas.
```

El sistema sustituye `#N` y `#M` por los números reales, igual que en los bloques de lectura compartida. **Nunca se escriben números literales**, porque el rango cambia con la estructura.

### Una parte es un bloque indivisible

**Cada parte se copia y se pega completa. Ninguna parte se divide.**

Una parte se carga como un solo archivo Word, con su subtítulo, su línea de instrucción, su recurso compartido si lo tiene, y todas sus preguntas. En el banco se guarda como una unidad.

Reglas:

- Al armar la cartilla se toma la parte **entera o ninguna**. No se pueden elegir algunas preguntas sueltas de una parte.
- Las preguntas de una parte quedan **seguidas**, en el orden en que se cargaron. No se intercalan preguntas de otra parte ni de otra materia.
- El sistema **no** reordena las preguntas dentro de una parte.
- La cantidad de preguntas de la sección de Inglés es la suma de las partes elegidas. Si esa suma no llega al total de la estructura, el sistema **avisa cuántas faltan** y no completa por su cuenta.
- La numeración corre de forma continua a través de las partes, y el sistema reescribe los rangos `#N` y `#M` de cada subtítulo.

Es el mismo tratamiento de los bloques de lectura compartida, aplicado a una unidad más grande.

#### Inglés · simulacro periódico · 28 preguntas

Reconstruido de `Cartilla_7`:

| Parte | Título | Preguntas |
|---|---|---|
| 1 | Vocabulario en contexto | 5 |
| 2 | Avisos y anuncios | 4 |
| 3 | Conversaciones | 5 |
| 4 | Comprensión de lectura | 7 |
| 5 | Completar el texto | 7 |
| | **Total** | **28** |

Si se requiere, la tabla **VOCABULARIO** se agrega a mano en la sección de cierre (3.6).

#### Inglés · simulacro ICFES · 55 preguntas

Se conservan **las siete partes** de la prueba real del Icfes, todas **adaptadas a cuatro opciones `A`–`D`**. La habilidad evaluada en cada parte es la misma; lo único que cambia es el formato de respuesta, que se unifica con el resto del sistema.

| Parte | Título | Tarea | Opciones | Preg. |
|---|---|---|---|---|
| 1 | Vocabulario en contexto | Una descripción y la palabra que le corresponde | `A`–`D` | 6 |
| 2 | Avisos y anuncios | Decidir en qué lugar se ve cada aviso | `A`–`D` | 6 |
| 3 | Conversaciones | Completar conversaciones cortas | `A`–`D` | 7 |
| 4 | Completar el texto · estructura | Llenar espacios con la palabra de estructura correcta | `A`–`D` | 9 |
| 5 | Comprensión de lectura básica | Responder preguntas sobre un texto sencillo | `A`–`D` | 9 |
| 6 | Comprensión de lectura compleja | Responder preguntas sobre un texto exigente | `A`–`D` | 9 |
| 7 | Completar el texto · significado | Llenar espacios por significado y estructura | `A`–`D` | 9 |
| | **Total** | | | **55** |

> **Reparto aprobado en la v1.1.** El Icfes no publica las cantidades exactas por parte; este reparto es el estándar de PRAXIS – THINKS.

Como cada parte es indivisible, **el reparto se materializa en el tamaño con que se cargan las partes al banco**. Una parte 4 cargada con 9 preguntas aporta siempre 9. Para que la sección sume 55, las siete partes disponibles deben sumar 55 entre ellas.

### Diferencias con la prueba real, adoptadas a propósito

| Aspecto | Prueba real del Icfes | Simulacro PRAXIS |
|---|---|---|
| Parte 1 | Emparejamiento con opciones `A`–`G` | Una descripción por pregunta, `A`–`D` |
| Partes 2 a 5 | Tres opciones `A`–`C` | Cuatro opciones `A`–`D` |
| Partes 6 y 7 | Cuatro opciones `A`–`D` | Igual |
| Ejemplo resuelto `0` | Uno al inicio de cada parte | **No se incluye**: la línea de instrucción de la parte es suficiente |

Esta adaptación permite que **todas las preguntas del sistema, sin excepción, tengan cuatro opciones `A`–`D`**, con lo que las cinco plantillas se aplican de forma uniforme en toda la cartilla, incluida la sección de Inglés. Ninguna plantilla se modifica.

---

## 3.5B · Regla única de opciones

**Toda pregunta del sistema tiene exactamente cuatro opciones, `A`, `B`, `C` y `D`.** No hay excepciones por materia, por grado, por parte ni por tipo de prueba.

Esta regla es la que permite que las cinco plantillas de respuestas funcionen sin casos especiales, sin sustituciones de letras y sin tablas auxiliares. Cada clave sale directamente de la plantilla declarada en el código de la cartilla.

El validador **rechaza** cualquier ejercicio que no cumpla, incluidos los de Inglés tomados del cuadernillo del Icfes, que traen tres o siete opciones y deben adaptarse a cuatro antes de subirse.

### Numeración

- Continua de 1 hasta el total, dentro de cada sesión.
- Si hay Sesión 1 y Sesión 2, cada una es una cartilla con su propio código y su numeración reinicia en 1.
- El número va en negrita, seguido de punto y espacio: `12. `
- Es texto fijo insertado por el sistema, no numeración automática de Word.

### Línea ➤ de información del ejercicio

Va **debajo de la última opción** de cada pregunta, en cursiva, Tahoma 6 pt.

Formato:

```
➤ Pensamiento // Competencia // DBA // Nivel
```

Reglas:

- **El sistema la genera** a partir de la TABLA DE EXCEL. Nunca se escribe a mano.
- Los campos vacíos **se omiten junto con su separador**. Ejemplo de Comprensión Lectora, donde no hay Pensamiento ni DBA:
  ```
  ➤ Comprende el sentido global mediante inferencias // MM
  ```
- El Nivel se escribe abreviado: `BB`, `MM`, `AA`.
- **En pruebas ICFES la línea ➤ no se imprime.**

### Maquetación y aprovechamiento del espacio

Verificado en Word con un cuadernillo de prueba (márgenes estrechos, Tahoma 9, opciones verticales): 38 preguntas variadas ocupan 2 páginas y media de cuerpo, y 130 preguntas, 10 páginas.

**Opciones: siempre verticales.** Una opción por línea, en orden A, B, C, D. Si una opción ocupa dos líneas, la segunda se alinea con el texto de la opción, no con la letra. No se usan opciones en fila ni en 2 × 2.

**Alineación.** El texto sale **justificado**, y se respeta la alineación que el autor aplicó a mano (poemas, citas, diálogos, fórmulas centradas):

| Elemento | Alineación |
|---|---|
| Enunciados, opciones, lecturas, recursos e instrucción de parte | **Justificada** |
| Párrafo al que el autor aplicó **Centrar** o **Alinear a la derecha** | Se conserva |
| Párrafo al que el autor aplicó **Alinear a la izquierda** | Se conserva (ver nota) |
| Imágenes y pies de imagen | Centrada |
| Línea de crédito | Derecha |
| Frase de referencia de un bloque | Justificada |
| Subtítulo de parte de Inglés | Izquierda |
| Títulos de sección | Centrada |
| Tablas | Centradas en la columna; cada celda conserva su alineación |
| Glosario | Justificado, al margen (sin sangría) |

> **Nota sobre «izquierda».** Word solo guarda «Alinear a la izquierda» en el párrafo cuando el estilo del documento no está ya a la izquierda (verificado en Word). Por eso las plantillas v1.2 traen el estilo Normal **justificado**: el Word de carga se ve igual que la cartilla, y lo que el autor alinee a la izquierda queda registrado. En archivos hechos con plantillas anteriores (estilo a la izquierda), lo que esté a la izquierda sale justificado; centrado y derecha se conservan siempre.
>
> En una línea justificada que termina con **Mayús + Enter** (versos, direcciones), Word no estira los espacios: la cartilla lleva activada esa opción.
>
> Al validar, el sistema informa qué párrafos conservarán una alineación distinta de justificada. Si se pega texto de otra fuente, se usa **Pegar › Mantener solo texto** para no arrastrar alineaciones ajenas.

**Espaciado** (lo pone el sistema; el del archivo de carga se descarta):

| Elemento | Antes | Después |
|---|---|---|
| Título de sección (12 pt, negrita) | 4 pt | 6 pt |
| Párrafo del enunciado | 0 | 2 pt |
| Última línea de la pregunta (la línea ➤ o, si lo hay, el glosario; en ICFES, la opción D o el glosario) | 0 | 14 pt (unos 5 mm hasta la pregunta siguiente) |
| Frase de referencia | 0 | 3 pt |
| **Imagen o tabla** | **6 pt** | **6 pt** |
| Línea de crédito | 2 pt | 5 pt |
| Subtítulo de parte de Inglés (con línea superior) | 4 pt | 1 pt |
| Instrucción de parte (cursiva) | 0 | 4 pt |
| Párrafos dentro de una tabla (interlineado sencillo) | 0 | 0 |
| Línea ➤ seguida del glosario | 0 | 1 pt |
| Glosario (8 pt) | 0 | 14 pt: es la última línea de la pregunta |

**Preguntas sin enunciado** («completar el texto» de Inglés): el número va en la misma línea que la opción A, y las opciones B, C y D van debajo, alineadas con la A. En los avisos, el número va encima de la imagen del aviso.

### Glosario de la pregunta

Se imprime solo si la cartilla tiene marcada la casilla **«Incluir glosario»**, que está en el paso de revisión, antes de generar (por defecto va desmarcada). Va **debajo de la línea ➤** (en ICFES, que no lleva línea ➤, debajo de la opción D), como última línea de la pregunta, en un solo párrafo de Tahoma 8 pt, justificado y alineado al margen, igual que la línea ➤:

```
➤ Numérico // Resolución de problemas // DBA 2 // BB
Glosario: cambio: Dinero que se devuelve cuando se paga con un valor mayor al de la compra.
```

«Glosario:» va en redonda; cada término, en negrita y seguido de dos puntos; cada significado, en redonda y terminado en punto. Ocupa una o dos líneas y no se separa de su pregunta. Al generar, la verificación cruzada comprueba que la cartilla tenga exactamente un glosario por cada pregunta que lo lleva, y ninguno si la casilla está desmarcada.

### Comportamiento de página

- **Una pregunta nunca se parte entre columnas ni entre páginas:** su número, enunciado, imagen o tabla, opciones, línea ➤ y glosario quedan juntos. Verificado en Word: no agrega páginas. Única excepción: si una pregunta sola es más alta que una columna, Word la continúa en la siguiente.
- La lectura de un bloque sí puede continuar en la columna siguiente, pero la frase de referencia nunca se separa del inicio de la lectura.
- **No se permite** que una imagen o tabla se separe del enunciado que la introduce. El sistema aplica «Conservar con el siguiente» al párrafo anterior a la imagen o tabla.
- **No se permite** que una fila de tabla se parta entre columnas.
- La frase de referencia de un bloque compartido nunca se separa del inicio de su lectura.

## 3.6 Cierre

Sección a una columna con: recuadro del QR, mensaje de cierre, créditos y aviso de derechos, tal como vienen en `PLANTILLA_CARTILLA_BASE.docx`.

La **tabla de vocabulario** de Inglés **no la genera el sistema**: se agrega a mano en el Word cuando se requiera.

**Función:** además de cerrar la cartilla, sirve de relleno para llegar al múltiplo de 4 páginas. El sistema informa cuántas páginas faltan y la persona decide qué bloques de cierre incluir. Nunca se recorta contenido de preguntas para ajustar páginas.

## 3.6B Entrega en Word editable

La cartilla se entrega como **Word (`.docx`) editable**, no como PDF, para que se puedan hacer ajustes finales. El documento no lleva protección ni restricciones de edición, y usa funciones normales de Word (texto, tablas, imágenes en línea, saltos y columnas), de modo que al editar el contenido se reacomoda solo.

Ajustes que se pueden hacer a mano sin afectar el Excel:

- Agregar el logo o el nombre de la institución en la portada.
- Agregar la tabla de vocabulario o bloques de relleno en el cierre.
- Insertar saltos de columna o de página, o ajustar espaciados, para completar el múltiplo de 4.
- Corregir un error de digitación **sin cambiar el sentido** de una pregunta ni de sus opciones.

**Lo que nunca se debe cambiar a mano**, porque el Excel de claves dejaría de coincidir con la cartilla:

- El orden de las preguntas o su número.
- El orden de las opciones o su letra.
- Agregar o quitar preguntas u opciones.

Si hace falta uno de esos cambios, se vuelve a armar la cartilla en el sistema y se genera de nuevo, con su Word y su Excel.

## 3.7 Ajuste a múltiplo de 4

Al generar, el sistema abre el Word recién creado **con Microsoft Word** (instalado en el equipo), lo repagina y cuenta sus páginas. En el paso de revisión informa el total y cuántas faltan para el siguiente múltiplo de 4, o que ya lo es.

- El conteo corre en un proceso aparte, con dos intentos y un límite de tiempo: si Word no está instalado o no responde, la cartilla se genera igual y la pantalla ofrece el botón **«Contar páginas»** para intentarlo de nuevo.
- El ajuste final lo hace la persona en el Word: se agregan bloques del cierre o un salto de página. **Nunca se quitan preguntas** para cuadrar las páginas.
- El número de páginas queda guardado con la cartilla.

## 3.8 Aprovechar el espacio de la hoja

**Decisión del 07/10/2026.** La hoja se aprovecha entera: no se deja espacio en blanco al final de una columna.

**Una pregunta se corta por donde haga falta.** El enunciado puede quedarse en una columna y las opciones
seguir en la siguiente, e incluso las opciones pueden repartirse (A y B arriba, C y D en la otra columna),
como en los cuadernillos del ICFES. Lo que **nunca** se separa:

| Va siempre junto | Por qué |
|---|---|
| Una imagen, y una tabla **con su última fila**, con lo que viene detrás | Lo que la interpreta («densidad = masa ÷ volumen», la pregunta) tiene que verse con la figura |
| El título de una sección con lo que viene detrás | No puede quedar solo al final de una columna |
| La cabecera de un bloque con su texto o su imagen | Son un conjunto |
| Las preguntas de un bloque, detrás de su recurso y en su orden | Son un conjunto |

Sí se puede cortar **antes** de una figura: la frase que la presenta se queda al final de la columna y la
imagen o la tabla abren la siguiente. Ahí estaban los huecos más grandes.

**Una tabla larga puede continuar en la columna siguiente (07/10/2026).** Con dos condiciones, que el
sistema escribe en cada fila:

| Marca de Word | Qué hace |
|---|---|
| `cantSplit` en todas las filas | El corte cae **entre** dos filas; ninguna fila se parte por la mitad |
| `tblHeader` en la primera fila | El encabezado **se repite** arriba de la continuación, para que la segunda parte no se quede sin los títulos de sus columnas |

El encabezado solo se marca en tablas de **más de dos filas**: una de dos no se parte. Las tablas que caben
siguen saliendo enteras — esto solo actúa cuando no caben. Comprobado con Word: una tabla de 12 filas a
mitad de columna pasaba de ocupar dos hojas a una sola.

Medido con Word en una cartilla real de 140 preguntas:

| | Antes | Ahora |
|---|---|---|
| Páginas | 28 | **25** |
| Espacio perdido | 3.252 pt (4,5 columnas) | **244 pt (0,3 columnas)** |
| Columnas con hueco de más de 100 pt | 15 | **1** |

**Reordenar (opcional).** Si aun así sobra espacio, el botón **«Aprovechar el espacio»** del paso de revisión
adelanta preguntas que quepan en los huecos:

- Mide con Word la altura exacta de cada pregunta (en un documento de páginas muy altas, para que ninguna se parta).
- Mira dónde quedó cada una en la cartilla real y cuánto le sobra a cada columna.
- Adelanta solo preguntas **sueltas de la misma sección**: nunca cambia nada de sección, no parte bloques y no
  quita ni agrega ninguna pregunta. Cambia el orden y, con él, la numeración y el Excel de claves.
- Cada tanda de cambios **se comprueba con Word**: si el resultado no es mejor, prueba con la mitad, y así hasta
  uno. Si nada mejora, el orden queda exactamente como estaba.
- Solo se puede en borrador, y sin Word no hace nada.

---

# PARTE 4 · FORMATO DE SALIDA
## Excel de claves

## 4.1 Archivo

- **Cada cartilla sale con su Excel.** Un simulacro de dos sesiones produce **dos Word y dos Excel**, uno por sesión.
- Una sola hoja por archivo, nombrada `Claves`.
- Una fila por pregunta.
- **Descarga:** al terminar la generación, la pantalla muestra el botón **Descargar** y un campo **Nombre del archivo**. El nombre propuesto es `<código> - <nombre descriptivo>`, y la persona lo puede cambiar. El Word y el Excel salen con el mismo nombre: `<nombre>.docx` y `<nombre>.xlsx`.
- El nombre no puede quedar vacío ni llevar los caracteres `\ / : * ? " < > |`. Si ya existe un archivo con ese nombre en la carpeta elegida, el sistema pregunta antes de reemplazarlo.
- En un simulacro de dos sesiones, cada sesión se descarga con su propio nombre.

## 4.2 Estructura

**Fila 1:** `CLAVES DE RESPUESTAS — una fila por pregunta de cada cartilla`
En la columna M de la fila 1, la nota: `La 'Cartilla' debe coincidir EXACTAMENTE con el cuadernillo del OMR y de la lista. Incluye aquí las claves de TODAS las cartillas/simulacros. Las columnas grises son opcionales.`

**Fila 2:** encabezados.

| Col | Encabezado | Contenido | Obligatorio |
|---|---|---|---|
| A | Cartilla | Código completo de la cartilla | Sí |
| B | Pregunta | Número dentro de la cartilla | Sí |
| C | Correcta | Letra **después** de aplicar la plantilla | Sí |
| D | Materia | Del catálogo | Sí |
| E | Submateria | Del catálogo | Según materia |
| F | Pensamiento | Del catálogo | Según materia |
| G | Competencia | Del catálogo | Según materia |
| H | DBA | Formato `DBA n` | Según materia |
| I | Temática | Del catálogo | Según materia |
| J | Nivel | `Básico` / `Medio` / `Avanzado` | No en ICFES |
| K | Justificación | Texto de la respuesta correcta | Sí |

**Fila 3 en adelante:** los datos, ordenados por número de pregunta ascendente.

## 4.3 Reglas críticas

1. La columna **Correcta** es la letra **final**, después de aplicar la plantilla. Nunca la del archivo de carga.
2. La columna **Cartilla** repite el mismo código en todas las filas de esa cartilla.
3. En pruebas ICFES (grado `13`), las columnas F a J van **vacías**, y la E va vacía en la sección MATEMÁTICAS. No se eliminan: el archivo siempre tiene las 11 columnas.
4. Fuera del ICFES, un campo que el ejercicio trajo vacío queda vacío.
5. La **Justificación** va en texto plano, sin saltos de línea internos, sin viñetas.
6. La **Temática** va sin viñeta `●` y sin punto final.
7. Sin filas en blanco intermedias.

## 4.4 Verificación automática antes de entregar

Antes de generar el archivo, el sistema comprueba que la columna **Correcta** coincide, pregunta por pregunta, con la plantilla de respuestas declarada en el código de la cartilla. Si hay una sola discrepancia, no se genera nada y se reporta el error.

---

# PARTE 4B · Entorno de ejecución

## 4B.0 Pantallas del sistema

| Pantalla | Para qué |
|---|---|
| **Panel** | Cuántas preguntas hay por grado, materia, submateria, nivel y tipo; cuántas están sin usar; las temáticas con su número de preguntas; y, por cada estructura, cuántas preguntas faltan en cada sección para poder armarla |
| **Cargar ejercicios** | Se revisan los archivos y **quedan en espera**: entran al banco cuando se pulsa «Guardar». Lo revisado y no guardado se puede descartar, y queda listado si se cierra el sistema |
| **Banco** | Buscar, ver y eliminar ejercicios ya guardados |
| **Crear simulacro** | Armar la cartilla: secciones, elección de ejercicios con buscador y vista previa, revisión y generación |
| **Formatos** | Descargar plantillas, ejemplos, instructivo y el Excel de códigos |
| **Catálogos** | Consultar los valores de fábrica |

Al guardar ejercicios nuevos, las demás pantallas vuelven a pedir sus datos: lo recién guardado se puede usar enseguida para armar cartillas.

**Eliminar un ejercicio del banco (07/10/2026).** Si alguna cartilla lo estaba usando, el sistema **también
se lo quita de ahí** y renumera sus preguntas; las cartillas ya generadas pierden su Word y su Excel, porque
dejan de corresponder a lo que tienen. Antes la referencia quedaba colgando y la cartilla **reventaba al
generarse**. Al eliminar, la respuesta dice qué cartillas quedaron afectadas.

**Eliminar una cartilla (07/10/2026).** Se puede eliminar cualquiera, esté en borrador o ya generada. Antes
de hacerlo la pantalla dice qué va a pasar, y la cartilla generada avisa aparte porque se lleva más cosas:

| | Borrador | Generada |
|---|---|---|
| Se borra la cartilla y sus secciones | Sí | Sí |
| Se borran su Word y su Excel guardados | No tiene | Sí |
| El uso que sumó a cada ejercicio | No sumó ninguno | **Se descuenta** |
| Los ejercicios del banco | No se tocan | No se tocan |

El uso se descuenta para que el banco siga diciendo la verdad sobre qué se ha usado y qué no: al generar,
cada ejercicio suma un uso; si esa cartilla desaparece, ese uso deja de existir.

### Secciones que toman toda una materia (07/10/2026)

En la **estructura libre (E4)** y en la PARTE 2 ampliada, al agregar una sección se puede elegir, en vez de
una submateria, la opción **«Todas las de… (mezcladas)»**. Esa sección acepta las preguntas de **cualquier
submateria** de esa materia.

Es lo que hace falta para una **prueba general de Matemáticas**: una sola sección que use preguntas de
Matemáticas I y de Matemáticas II. Lo mismo sirve para una de Lengua Castellana (Español, Comprensión
Lectora y Lectura Crítica) o de Ciencias Naturales (Biología, Física, Química y Tecnología y Medio Ambiente).

Por dentro es una sección **mezclada**, igual que las de los simulacros ICFES: guarda la lista de
combinaciones «Materia|Submateria» que admite, y el buscador y la selección automática trabajan sobre todas
ellas. Si el grado permite que la submateria vaya vacía, también se admite la materia sin submateria.

La opción solo aparece cuando la materia tiene **más de una** submateria en ese grado; en Inglés o en
Filosofía, que no tienen, no se ofrece.

**Secciones que mezclan varias materias.** El mismo desplegable ofrece arriba los **grupos de materias**
de `GRUPOS_MATERIA` (`app/catalogos_base.py`). Hoy hay uno: **«Sociales y ciudadanas (Ciencias Sociales +
Filosofía)»**, que es la sección del simulacro ICFES. Al elegirlo, la sección acepta Ciencias Sociales,
Ciencias Económicas y Políticas y Filosofía a la vez, y en la lista de candidatos cada ejercicio muestra
de qué materia es, con un filtro propio de Materia.

### Elección de ejercicios (paso 2 de «Crear simulacro»)

La pantalla tiene tres columnas: **temáticas y filtros**, **ejercicios que coinciden** y **vista previa o elegidos**.

**Buscador de temas (arriba del todo).** Es por donde se empieza. El docente escribe los temas que está
viendo en clase, tal como los diría, y el sistema los encuentra:

- **Varios temas a la vez**, separados por comas: `fracciones, diagrama circular, senos y cosenos`.
  Dentro de un tema tienen que estar todas sus palabras; basta con que coincida uno de los temas.
- **Sin tildes y sin mayúsculas**: «fotosintesis» encuentra «Fotosíntesis».
- **Singular o plural**: «fracciones» encuentra «Fracción como parte de un todo»; «células», «célula».
- Las palabras de enlace («de», «y», «la») no se exigen.
- Busca en la **temática, el código y el texto** del ejercicio (enunciado y opciones).
- Si lo que se busca **no está en la sección abierta**, dice en cuál de la cartilla sí está y cuántos hay,
  con un botón para saltar allá sin perder la búsqueda. Si no está en ninguna, también lo dice.

**Filtros dinámicos.** Debajo del buscador, en una fila: nivel, competencia, pensamiento, DBA, submateria,
tipo y recurso. Cada uno se despliega solo si hay de dónde escoger y muestra cuántas preguntas hay de cada
valor. Al lado, el orden de la lista.

**Buscador de temáticas (columna izquierda).** Está siempre a la vista. Lista **todas** las temáticas que
caben en la sección (grado, materia y submateria de esa sección), en orden alfabético, una por línea y con dos marcas:

| Marca | Significado |
|---|---|
| número al final | preguntas **disponibles** para elegir ahora |
| ✓ n | preguntas de esa temática que **ya están en la sección** |

- Se pueden marcar **varias** temáticas; las marcadas suben al principio de la lista.
- El campo «buscar temática…» filtra al instante, **sin tildes ni mayúsculas** (escribir «division» encuentra «División»).
- Una temática **agotada** (todas sus preguntas ya elegidas) sigue en la lista, en gris, con su ✓: así se ve de un
  vistazo qué se cubrió y qué falta. La lista **nunca cambia de contenido** al elegir: solo bajan los números.
- Si la sección no tiene ninguna pregunta en el banco, lo dice con todas las letras en vez de dejar la columna vacía.

**Los demás filtros** van debajo, plegados, y también muestran cuántas preguntas hay de cada valor: nivel, submateria,
competencia, pensamiento, DBA, tipo (suelto, bloque o parte), recurso (con imagen, con tabla, con glosario o sin
imagen), solo sin usar, ocultar los que ya van en la otra sesión del mismo simulacro, texto libre sobre el enunciado,
las opciones y el código, y el orden (menos usados, por temática, por nivel o más recientes).

Los filtros puestos aparecen **encima de la lista**, uno por uno, y se quitan pulsándolos; «Quitar todos» los limpia.
Los conteos de los filtros no se recortan al filtrar: siempre se ve lo que hay en toda la sección, para poder sumar
otra temática sin perder de vista el resto.

**El orden de un bloque no se toca.** Las preguntas de un bloque o de una parte se refieren al mismo texto
o a la misma imagen y están escritas para leerse seguidas, así que:

- Entran y salen **completas**, en el orden del archivo de carga.
- Se imprimen **seguidas y en ese orden**, siempre. Ni la selección automática, ni las flechas de la lista,
  ni el reordenador de maquetación (3.8) pueden partirlas ni intercalarles otra pregunta.
- Lo que sí se puede reordenar a mano o automáticamente son las preguntas **sueltas** y los bloques enteros.

> **Error corregido el 07/10/2026.** La selección automática volvía a calcular la última posición de la
> sección sobre una lista que todavía no incluía lo recién agregado, así que **cada unidad empezaba otra vez
> en la posición 1**. Con varias unidades —Inglés, que son todo partes— quedaban empatadas y en el Word las
> partes salían mezcladas. Ahora la cuenta de posiciones se lleva de corrido, y al imprimir, si dos
> posiciones empataran, el bloque manda: sus preguntas van juntas y en su orden.

**Lista de ejercicios.** Cada uno encabeza con su **temática**, y avisa «×n en la sección» cuando ya hay preguntas de
esa misma temática elegidas, para no repetir sin darse cuenta.

**Vista previa.** La tercera columna tiene dos pestañas: *Vista previa* y *Elegidos*. Al pulsar un ejercicio se ve
**completo** (enunciado, opciones, glosario, clave y justificación) y se agrega desde ahí; los ya elegidos también se
pueden abrir para revisarlos.

### Las ecuaciones se ven en la pantalla (08/10/2026)

La vista previa pegaba el **texto suelto** de la ecuación, y eso cambia lo que dice: «F₁/A₁ = F₂/A₂» se
leía «F1A1 = F2A2», que es un producto y no un cociente.

Ahora el sistema traduce la ecuación de Word (OMML) a **MathML**, que el navegador dibuja sin instalar
nada, y la pone **en su sitio** dentro del párrafo, no pegada al final. Están contempladas las
construcciones de la escuela: fracciones, potencias, subíndices, raíces, paréntesis, sumatorias e
integrales con sus límites, funciones, matrices, barras y acentos. Lo que no esté contemplado se dibuja
con su texto: nunca se pierde nada.

El Word de la cartilla **no pasa por esta traducción**: ahí la ecuación va tal cual, que es lo que Word
imprime.

### Pasar un simulacro al formato de carga

En el **Panel** hay un texto listo para copiar y pegar en una inteligencia artificial (Claude u otra),
seguido del simulacro que se quiera convertir. Devuelve los ejercicios en el formato exacto de carga: un
archivo por ejercicio, con su enunciado, sus cuatro opciones y las tres tablas (RESPUESTAS, EXCEL y
GLOSARIO).

El texto **no está escrito a mano**: se arma con los catálogos y con las constantes del propio validador,
así que no se puede desviar de lo que el sistema acepta.

| De dónde sale | Qué aporta |
|---|---|
| `GRADOS`, `MATERIAS`, `SUBMATERIAS`, `NIVELES` | Los valores que existen, y si la submateria es obligatoria, opcional o va vacía |
| `PEDAGOGIA` (2.13) | El pensamiento y la competencia de **cada submateria** |
| `DBA_INGLES_6` | Los ocho DBA de Inglés de 6°, para que la IA no los invente |
| `ENC_RESPUESTAS`, `ENC_EXCEL`, `ENC_GLOSARIO` del validador | Los encabezados de las tres tablas, letra por letra |
| El banco | Marca con ✓ los valores que ya se usan, para no cambiar de redacción |

**Lo más importante del texto: los simulacros que ya traen la información.** Casi todos vienen con sus dos
tablas al final (la clave con su justificación y la de datos pedagógicos) y con la **línea ➤** debajo de
cada pregunta. En ese caso no hay nada que inventar, solo reorganizar, y el texto dice exactamente de dónde
sale cada dato y qué hay que retocar:

| Hay que | Por qué |
|---|---|
| Vaciar las columnas **N°** y **Preg.** | Vienen numeradas 1, 2, 3… y el número lo pone el sistema |
| **Agregar la columna Grado** | La tabla original casi nunca la trae; está en la cabecera del archivo |
| **Borrar la línea ➤** | Es lo que *imprime* la cartilla, no algo que se cargue. Si se queda, el validador la lee como **una segunda pregunta sin opciones** y rechaza el archivo |
| Quitar el número del enunciado | Regla 12 |
| Cambiar los rótulos de las tablas | El original trae «Clave de respuestas» y «Tabla para Excel» |
| Escribir el nivel completo | En la línea ➤ viene abreviado: BB, MM, AA |
| Repartir el glosario | Suele venir en un archivo aparte, una línea por pregunta |
| Ponerle crédito al recurso de un bloque | Si no lo trae, es obligatorio (regla 7) |

Incluye las dieciocho reglas que rechazan un archivo, agrupadas en «la pregunta», «las tablas» y «el
archivo». Las que más se incumplen: la columna **N°** de RESPUESTAS y la **Preg.** de EXCEL van **vacías**
(el número lo pone el sistema); la **justificación no puede nombrar letras** de opción; y el **crédito** es
obligatorio en los bloques y está **prohibido** en los ejercicios sueltos. Al final le pide a la IA que
avise qué tuvo que corregir y cuántos ejercicios quedaron por materia y por nivel.

## 4B.1 Fase 1 · aplicación local

El sistema arranca como una **aplicación que corre en un computador**, sin servidor y sin internet.

| Aspecto | Fase 1 |
|---|---|
| Dónde corre | Un computador de la empresa |
| Internet | No se requiere |
| Usuario y contraseña | **No se piden** |
| Banco de ejercicios | Archivo de base de datos local |
| Imágenes | Carpeta local junto a la base de datos |
| Archivos de salida | Carpeta local que el usuario elige |

Se construye desde el principio pensando en el traslado posterior a un servidor, de modo que pasar a Hetzner o a otra plataforma sea configuración, no reescritura.

## 4B.2 Fase 2 · traslado al servidor

Cuando el sistema funcione bien, se sube a Hetzner o a otra plataforma y se activan:

- Usuario y contraseña para los tres usuarios.
- Banco compartido, accesible desde varios computadores.
- Copia de seguridad automática, además de la manual.

Nada del formato de entrada, del formato de salida ni de las reglas del motor cambia entre las dos fases.

## 4B.3 Copia de seguridad manual

Un botón **Crear copia de seguridad** genera un solo archivo comprimido con todo: la base de datos, las imágenes y los catálogos. Se guarda donde el usuario indique.

Un botón **Restaurar copia** deja el sistema exactamente como estaba en el momento de esa copia.

Recomendación: hacer una copia después de cada sesión de carga de ejercicios y guardarla fuera del computador.

## 4B.4 Trabajo simultáneo

Dos personas pueden armar cartillas al mismo tiempo. La única protección necesaria es que **el código de cartilla se reserve en el momento de iniciar la generación**, para que dos cartillas no salgan con el mismo código.

En la fase 1, con el sistema en un solo computador, este punto no se presenta.

---

# PARTE 5 · Reglas del motor

## 5.1 Código de cartilla

Estructura de cinco pares:

```
GG  MM  TT  PP  VV
│   │   │   │   └── Versión
│   │   │   └────── Plantilla de respuestas (01–05)
│   │   └────────── Tipo de material
│   └────────────── Materia
└────────────────── Grado
```

Ejemplo: `1199330101` = Grado 11 · Todas las materias · Periodo 3 · Plantilla 1 · Versión 1

### Validación cruzada

El usuario digita el código. Antes de generar, el sistema:

1. Descompone el código en sus cinco pares.
2. Verifica que cada par exista en su catálogo.
3. Verifica que **coincida con lo seleccionado en pantalla** (grado, materia, tipo, plantilla).
4. Verifica que el código **no exista ya** en el histórico. Si existe, avisa y sugiere la siguiente versión libre.

Si algo no cuadra, la generación se bloquea.

Además, el par de materia debe corresponder a la estructura (1.2), y el sistema empareja las sesiones por código (Parte 1A).

### Compatibilidad con el formato anterior de 8 dígitos

Las cartillas históricas (`10913301`, `77913301`) llevan 8 dígitos, sin versión. El sistema las acepta en lectura y, al generarlas de nuevo, propone la versión `01` para completarlas a 10.

## 5.2 Aplicación de la plantilla de respuestas

Para cada pregunta en la posición *n* de la cartilla:

1. Se lee la letra objetivo de la plantilla en la posición *n*.
2. Se intercambia el contenido de la opción correcta con el contenido de la opción que ocupa la letra objetivo.
3. Las demás opciones conservan su posición.
4. La letra objetivo se registra en la columna **Correcta** del Excel.

La justificación no se modifica, porque por norma no menciona letras.

## 5.3 Datos de cartilla adicionales (no van en el código)

| Campo | Obligatorio |
|---|---|
| Institución | Sí |
| Nombre descriptivo | Sí |
| Fecha de generación | Automático |
| Tiempo de la prueba | Automático (2 min por pregunta), editable |
| Cartillas a excluir | No (la otra sesión se excluye sola) |
| Incluir glosario | No. Casilla, desmarcada por defecto (2.7B) |

## 5.3B Corrección y eliminación de ejercicios

**Los ejercicios se conservan siempre.** Solo se eliminan cuando tienen un error.

Flujo de corrección:

1. Se localiza el ejercicio en el banco.
2. Se **elimina**.
3. Se corrige el Word original y se **vuelve a subir**.
4. El ejercicio corregido entra como nuevo y recibe un código nuevo.

No hay edición dentro del sistema ni versiones de un mismo ejercicio. La fuente de verdad es siempre el Word de carga.

### Qué pasa si el ejercicio ya se usó

Los archivos Word y Excel ya generados **no se alteran**: son archivos guardados aparte y quedan tal como se imprimieron.

Lo que sí cambia es el registro interno de esa cartilla, que pierde la referencia al ejercicio eliminado. Esto tiene un efecto práctico: la función de **excluir una cartilla anterior** dejará de proteger ese ejercicio en particular. Los demás ejercicios de esa cartilla siguen protegidos.

Antes de eliminar, el sistema avisa en cuántas cartillas se usó el ejercicio.

### Eliminación de un bloque o de una parte

Un bloque de lectura compartida y una parte de Inglés se eliminan **completos**. No se puede borrar una pregunta suelta de dentro. Si una sola pregunta del bloque tiene un error, se elimina el bloque entero, se corrige y se vuelve a subir.

## 5.4 No repetición entre cartillas

Al armar una cartilla, se pueden marcar una o varias cartillas anteriores para **excluir**. Los ejercicios de esas cartillas desaparecen de la búsqueda y de la selección automática. Se usa para Sesión 1 frente a Sesión 2, y entre periodos de la misma institución.

El sistema guarda además un **contador de uso** por ejercicio. La selección automática prefiere los menos usados.

## 5.5 Selección automática y bloques

Un bloque de lectura se puede recortar dejando **mínimo 2 preguntas**; una parte de Inglés nunca se recorta.

Cuando una selección automática necesita *k* preguntas de una temática y el bloque disponible trae más, el sistema **no recorta solo**: informa cuántas preguntas trae el bloque y deja que la persona decida cuáles quitar.

Si el bloque trae menos de las que faltan, avisa cuántas quedan pendientes y no completa por su cuenta.

Esto aplica igual a los tres casos de uso, incluidos los simulacros de una sola materia.

## 5.5B Código de ejercicio

Formato: `PRE-GG-NNNNNN`

- `PRE`: prefijo de la submateria (o de la materia, si no tiene).
- `GG`: código de grado (`33`, `44`, `55`, `66`, `77`, `88`, `99`, `10`, `11`, `13`).
- `NNNNNN`: consecutivo por prefijo y grado. Nunca se reutiliza, aunque el ejercicio se elimine.

Un bloque o una parte recibe su propio código con `B` delante del consecutivo (`CLE-77-B00012`), y cada pregunta de adentro recibe su código normal.

| Materia / Submateria | Prefijo |
|---|---|
| Matemáticas (sin submateria: ICFES y 3° a 5°) | `MAT` |
| Lengua Castellana (sin submateria: 3° a 5°) | `LEN` |
| Matemáticas I | `MA1` |
| Matemáticas II | `MA2` |
| Español | `ESP` |
| Comprensión Lectora | `CLE` |
| Lectura Crítica | `LCR` |
| Biología | `BIO` |
| Física | `FIS` |
| Química | `QUI` |
| Tecnología y Medio Ambiente | `TMA` |
| Ciencias Sociales (general) | `SOC` |
| Filosofía (materia) | `FIL` |
| Ciencias Económicas y Políticas | `CEP` |
| Inglés | `ING` |
| Informática | `INF` |
| Educación Física | `EDF` |
| Educación Artística | `ART` |
| Religión | `REL` |
| Ética | `ETI` |
| Dibujo | `DIB` |
| Electricidad | `ELE` |
| Mecánica | `MEC` |

Las materias nuevas reciben su prefijo al crearlas en la aplicación.

## 5.6 Búsqueda

- Filtros obligatorios: **Grado** y **Temática**.
- Filtros opcionales: Materia, Submateria, Pensamiento, Competencia, DBA, Nivel, tipo de recurso (con imagen, con tabla, con lectura compartida), veces usado, cartillas a excluir.
- Búsqueda por texto dentro del enunciado.
- Vista previa del ejercicio antes de agregarlo y del cuadernillo completo antes de generar.

---

# PARTE 6 · Defectos detectados en `Cartilla_7.docx`

Revisión técnica del archivo real. Estos son los puntos que el sistema debe corregir de forma automática.

## 6.1 Configuración

| Hallazgo | Impacto | Corrección |
|---|---|---|
| Orientación declarada `horizontal` con medidas verticales | Puede alterar la impresión y la conversión a PDF | Generar siempre orientación vertical |
| Ancho de columna real: **8,64 cm** | Los archivos de ejercicio sueltos asumían 9,17 cm | Unificar todo a 8,4 cm máximo |
| Cuerpo del texto a **10 pt** (88.156 caracteres medidos) | Ocupa más espacio del necesario | Bajar a **9 pt** |

## 6.2 Imágenes

| Hallazgo | Cantidad |
|---|---|
| Imágenes que **exceden** el ancho de columna (8,78 a 9,21 cm) | 6 |
| Imágenes **flotantes** en el cuerpo de la prueba | 6 |
| Cuadros de texto | 72 |

Las imágenes que exceden el ancho se desbordan o se recortan. Las flotantes se desacomodan al reorganizar el documento.

## 6.3 Texto residual impreso

En la **pregunta 2** quedó impresa una instrucción de trabajo que no debía salir:

> *«Qué NO debe aparecer: números decorativos, flechas, símbolos matemáticos adicionales, colores, sombras, fondo distinto del blanco.»*

Es texto de proceso que llegó a la cartilla del estudiante. El validador debe detectar y rechazar párrafos con este tipo de contenido.

## 6.4 Referencias cruzadas entre preguntas

Las preguntas **54, 55 y 56** dicen `La tabla registra (ejercicio 53)`. Dependen de un recurso que está en otra pregunta, pero **no están declaradas como bloque compartido**.

Consecuencia: si el sistema renumera, la referencia queda equivocada.

**Corrección:** las preguntas 53 a 56 deben cargarse como un **bloque de lectura compartida**, con la tabla como recurso y la frase `Responde las preguntas #N a #M de acuerdo con la siguiente información.`

## 6.5 El orden de la portada no coincide con el del cuerpo

La tabla de áreas de la portada de `Cartilla_7` lista las secciones en este orden:

> Matemáticas I · Matemáticas II · Lengua Castellana · Comprensión Lectora · **Biología · Física · Química · Ciencias Sociales** · Inglés

Pero el cuerpo de la prueba va en otro orden:

> … Comprensión Lectora (45–56) · **Ciencias Sociales (57–76) · Biología (77–88) · Física (89–100) · Química (101–112)** · Inglés

Las cantidades sí cuadran (suman 140 en ambos lados), pero un estudiante que use la portada para ubicarse va a buscar Biología antes de Ciencias Sociales y no la va a encontrar ahí.

**Corrección:** la tabla de la portada se genera desde la estructura, en el mismo orden en que se imprimen las secciones. El desajuste desaparece solo.

## 6.6 Numeración embebida en Inglés

Los títulos de las partes de Inglés llevan números escritos a mano:

```
PARTE 1 · Vocabulario en contexto — preguntas 113 a 117
PARTE 2 · Avisos y anuncios — preguntas 118 a 121
```

**Corrección:** tratar cada parte como un bloque con frase de referencia y marcadores `#N` y `#M`, o registrar el título como recurso de bloque para que el sistema lo reescriba.

## 6.7 Inconsistencia en la línea ➤

El número de campos varía sin regla clara:

| Materia | Campos en ➤ |
|---|---|
| Matemáticas | 4 (Pensamiento, Competencia, DBA, Nivel) |
| Ciencias Sociales | 4 |
| Biología / Física | 3 (sin DBA en algunos, con DBA en otros) |
| Lengua Castellana | 3 |
| Comprensión Lectora | 2 |
| Inglés | 3 |

Además, las preguntas 74, 75 y 76 no traen DBA mientras que la 69 sí.

**Corrección:** el sistema genera la línea desde la TABLA DE EXCEL y omite solo los campos realmente vacíos. La regla queda uniforme y automática.

## 6.8 Fórmulas

- 112 superíndices/subíndices de texto: **correcto**, es el estándar adoptado.
- Solo 2 ecuaciones OMML en 140 preguntas: consistente con la regla de usar el editor solo para lo estructural.
- Las fracciones están en línea con superíndice y subíndice: se adoptó como estándar en la v1.2 y **se revocó el 06/11/2026** por ilegible; ahora van apiladas o a tamaño normal (ver 2.9.2).

## 6.9 Lo que ya está bien y se conserva

- Pies de página alternados par/impar con campo automático de página.
- ~~Margen de encuadernación de 0,5 cm.~~ Retirado en la v1.1: márgenes estrechos sin encuadernación (3.1).
- Tres secciones bien separadas: portada, cuerpo, cierre.
- Filas de tabla marcadas para no dividirse (106 casos).
- Las cantidades de la tabla de áreas de la portada suman exactamente las 140 preguntas del cuerpo.

---

# PARTE 7 · Estado de los pendientes

| # | Pendiente | Estado |
|---|---|---|
| 1 | El software de calificación distingue por submateria Sociales general de Ciencias Económicas y Políticas en E2 | **Abierto** · confirmar con el proveedor del software. No bloquea la construcción |
| 2 | Códigos de materia | Cerrado · se conservan todos (1.2) |
| 3 | Tamaño de las tablas del ejercicio | Cerrado · 8 pt |
| 4 | Reparto de las 55 preguntas de Inglés ICFES | Cerrado · se aprueba la propuesta (6+6+7+9+9+9+9) |
| 5 | Orden de Dibujo, Electricidad y Mecánica en E7 | Cerrado · el de la tabla; se puede ajustar al armar |
| 6 | Matemáticas y Lectura Crítica en el ICFES | Cerrado · ejercicios sueltos y bloques de lectura, como en todas las materias |
| 7 | Nombre de la submateria | Cerrado · **Ciencias Económicas y Políticas** |
| 8 | Orden de las secciones de cierre | Cerrado · el cierre sale fijo de la plantilla base; el vocabulario y el relleno se ajustan a mano |

---

# PARTE 8 · Verificación de consistencia

Revisión del modelo contra los tres casos de uso. Todas las sumas fueron comprobadas.

## Cuadre de las estructuras

| Estructura | Secciones | Suma | ¿Cuadra? |
|---|---|---|---|
| E1 · Periódico 6° a 9° | 9 | 15+15+14+12+20+12+12+12+28 | **140** |
| E2 · Periódico 10° y 11° | 11 | 13+13+14+10+10+12+10+10+10+10+28 | **140** |
| E3 · Periódico PARTE 2 | 5 | 16×5 | **80** |
| E5 · ICFES sesión 1 | 4 | 25+41+25+29 | **120** |
| E6 · ICFES sesión 2 | 4 | 25+25+29+55 | **134** |
| E7 · Periódico PARTE 3 | 8 | 16×5 + 12×3 | **116** |
| Inglés ICFES, por partes | 7 | 6+6+7+9+9+9+9 | **55** |
| Inglés periódico, por partes | 5 | 5+4+5+7+7 | **28** |

E5 y E6 suman 254, el total calificado de la prueba real.

Las dos sesiones del ICFES caben dentro de las 140 posiciones de las plantillas, así que ninguna plantilla se modifica.

## Cadena de datos, de la carga al Excel

| Dato | Nace en | Lo fija | Llega al Excel |
|---|---|---|---|
| Enunciado, opciones, imágenes | Word de carga | El autor | No |
| Clave original | TABLA DE RESPUESTAS | El autor | No, se transforma |
| **Correcta** | Plantilla + posición | El sistema | Columna C |
| Materia, Submateria | TABLA DE EXCEL | El autor | Columnas D, E |
| Pensamiento, Competencia, DBA, Temática | TABLA DE EXCEL | El autor | Columnas F–I |
| Nivel | TABLA DE EXCEL | El autor | Columna J |
| Grado | TABLA DE EXCEL | El autor | No |
| Justificación | TABLA DE RESPUESTAS | El autor | Columna K |
| **Pregunta** | Posición en la estructura | El sistema | Columna B |
| **Cartilla** | Código digitado y validado | El usuario | Columna A |
| Título de sección | Estructura | El administrador | No |
| Total y tabla de áreas de la portada | Estructura | El sistema | No |

En pruebas ICFES las columnas F a J salen vacías (1B).

Ningún dato de la columna A a la K se digita dos veces. Cada uno tiene una sola fuente.

## Unidades indivisibles

Tres cosas se copian completas y nunca se parten:

| Unidad | Alcance | Efecto en la numeración |
|---|---|---|
| Ejercicio suelto | Enunciado, recurso y cuatro opciones | Recibe un número |
| Bloque de lectura compartida | Frase de referencia, lectura y sus preguntas | Preguntas seguidas, rango reescrito |
| Parte de Inglés | Subtítulo, instrucción, recurso y sus preguntas | Preguntas seguidas, rango reescrito |

## Bloqueos antes de generar

El sistema no produce ningún archivo si ocurre alguna de estas:

1. Una sección no tiene la cantidad exacta de ejercicios que exige la estructura.
2. La suma de las secciones no coincide con el total declarado.
3. El código de cartilla no coincide con lo seleccionado en pantalla.
4. El código de cartilla ya existe en el histórico.
5. La columna Correcta del Excel no coincide con la plantilla en alguna posición.
6. Un ejercicio no tiene cuatro opciones.
7. Falta la institución o el nombre descriptivo.
8. La segunda sesión repite un ejercicio de la primera.

## Lo que el sistema decide solo

Solo cuatro cosas, y todas son deterministas y verificables a mano:

1. El número de cada pregunta, por su posición en la estructura.
2. La letra correcta, leyendo la plantilla en esa posición.
3. Los rangos `#N` y `#M` de bloques y partes.
4. El total y la tabla de áreas de la portada.

Todo lo demás viene del Word de carga o de lo que el usuario selecciona.

---

*Documento preparado para revisión. Una vez aprobado, se convierte en la especificación contra la cual se construye el sistema y contra la cual se normalizan los 2.000 ejercicios existentes.*
