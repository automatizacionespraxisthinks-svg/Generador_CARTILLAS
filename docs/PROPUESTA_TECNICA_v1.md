# PROPUESTA TÉCNICA
## Generador de cuadernillos PRAXIS – THINKS
### Versión 1.0 · para aprobación

> Documento complementario a `ESTANDAR_PRAXIS_v1.md`.
> Aquel define **qué** hace el sistema. Este define **cómo** se construye.

---

# 1 · Tecnología

## 1.1 La decisión que manda sobre todas las demás

El sistema no reinterpreta los ejercicios: copia el fragmento interno del Word y lo pega en la cartilla. Esa decisión obliga a trabajar directamente sobre el XML del `.docx`, y eso descarta la mayoría de las alternativas.

**Python** es el lenguaje indicado, porque tiene las bibliotecas más maduras para manipular Word y Excel a ese nivel.

## 1.2 Componentes

| Capa | Herramienta | Por qué |
|---|---|---|
| Lenguaje | Python 3.12 | Manejo confiable de `.docx` y `.xlsx` |
| Word | `python-docx` + `lxml` | `lxml` para copiar fragmentos XML sin alterarlos |
| Excel | `openpyxl` | Control exacto del formato de salida |
| Base de datos | **SQLite** | Un solo archivo, sin instalación, sin servidor |
| Interfaz | FastAPI + HTML | Se abre en el navegador, sin depender del sistema operativo |
| Empaquetado | Un ejecutable | Se abre con doble clic |

## 1.3 Por qué SQLite y no PostgreSQL

En la fase 1 todo vive en un computador. SQLite guarda la base entera en **un archivo**, lo que hace que la copia de seguridad sea literalmente copiar ese archivo. No hay servicio que instalar ni que se pueda quedar caído.

Para tres usuarios y un banco que crecerá a decenas de miles de ejercicios, SQLite va sobrado. Cuando pases a Hetzner, se cambia a PostgreSQL modificando una línea de configuración, porque el código no habla directamente con la base sino a través de una capa intermedia.

## 1.4 Por qué se abre en el navegador y no es una ventana de escritorio

Una aplicación de escritorio clásica habría que reescribirla para pasarla al servidor. Esta corre localmente pero se ve en el navegador, así que **el mismo código sirve en las dos fases**. En Hetzner solo cambia dónde está corriendo.

Para el usuario la diferencia es ninguna: abre el programa y se abre una pestaña.

## 1.5 Qué NO se usa

| Descartado | Razón |
|---|---|
| Convertir a HTML o LaTeX | Deforma ecuaciones y tablas |
| Plantillas de Word con marcadores | No soporta contenido variable con imágenes |
| Generar el `.docx` desde cero | Se perderían los formatos originales |
| Hosting compartido tipo cPanel | No corre Python con estas bibliotecas |

---

# 2 · Modelo de datos

## 2.1 Catálogos

```
grado              id · nombre · codigo
materia            id · nombre · codigo
submateria         id · materia_id · nombre · codigo
tipo_material      id · nombre · codigo
plantilla          numero (1-5) · secuencia (140 letras)
```

Catálogos que se construyen solos, con normalización y aviso de similitud:

```
tematica · competencia · pensamiento · dba
```

## 2.2 Ejercicios

```
ejercicio
  id
  codigo                 asignado por el sistema: MAT-07-000123
  grado_id
  materia_id
  submateria_id          puede ir vacío
  pensamiento            puede ir vacío según la materia
  competencia
  dba                    puede ir vacío según la materia
  tematica
  nivel                  Básico · Medio · Avanzado · vacío en ICFES
  clave_original         A · B · C · D
  justificacion
  bloque_id              vacío si es un ejercicio suelto
  orden_en_bloque
  veces_usado
  archivo_origen         nombre del Word de carga
  creado_en
```

## 2.3 El contenido del ejercicio

Aquí está el corazón del sistema. Cada ejercicio guarda **tres cosas**:

```
ejercicio_contenido
  ejercicio_id
  docx_original          el archivo .docx completo, tal como se subió
  xml_enunciado          fragmento XML de los párrafos del enunciado
  xml_opcion_a           fragmento XML de la opción A
  xml_opcion_b
  xml_opcion_c
  xml_opcion_d
  imagenes               lista de archivos con su identificador interno
```

**Por qué se guarda también el `.docx` original.** Si alguna vez hay que revisar un ejercicio o reconstruir algo, el archivo tal como lo subiste está ahí. Ocupa poco y es la garantía de que ningún dato se pierde en la conversión.

**Por qué se guardan las opciones por separado.** La plantilla necesita intercambiar la opción correcta con otra. Al tenerlas como cuatro fragmentos independientes, el intercambio es reordenarlas, no reescribirlas. El contenido de cada opción nunca se toca.

## 2.4 Bloques y partes

```
bloque
  id
  tipo                   lectura_compartida · parte_ingles
  titulo                 solo en partes: "Vocabulario en contexto"
  numero_parte           solo en partes: 1 a 7
  frase_referencia       plantilla con #N y #M
  instruccion            solo en partes
  xml_recurso            la lectura, tabla o gráfica
  imagenes
  permite_recorte        verdadero en lectura_compartida · falso en parte_ingles
```

Los ejercicios del bloque apuntan a él con `bloque_id` y guardan su `orden_en_bloque`.

## 2.5 Estructuras

```
estructura
  id · nombre · total · editable

estructura_seccion
  estructura_id
  orden
  titulo_impreso            MATEMÁTICAS I · LENGUA CASTELLANA
  materia_id
  submateria_id             vacío si la sección mezcla
  cantidad
  mezclada                  verdadero en las secciones del ICFES
  submaterias_admitidas     lista, solo si mezclada
```

Las siete estructuras del estándar se cargan de fábrica: E1, E2, E3, E5, E6, E7 y la libre E4.

## 2.6 Cartillas

```
cartilla
  id
  codigo                 diez dígitos
  institucion
  nombre_descriptivo
  estructura_id
  plantilla
  tiempo
  sesion                 1 · 2 · única
  generada_en

cartilla_item
  cartilla_id
  posicion               1 a 140
  ejercicio_id
  letra_final            la que va al Excel

cartilla_excluida
  cartilla_id
  cartilla_excluida_id
```

`cartilla_item` es lo que permite excluir una cartilla anterior al armar la siguiente sesión, y lo que alimenta el contador de usos.

---

# 3 · Pantallas

## 3.1 Banco de ejercicios

La pantalla principal. Un buscador con:

- **Filtros obligatorios:** grado y temática.
- **Filtros opcionales:** materia, submateria, pensamiento, competencia, DBA, nivel, tipo de recurso (con imagen, con tabla, bloque compartido), veces usado, cartillas a excluir.
- **Búsqueda por texto** dentro del enunciado.

Resultados en lista, con vista previa al hacer clic. La vista previa muestra el ejercicio con su texto, imágenes y tablas, y debajo sus metadatos y su justificación.

Desde aquí también se elimina un ejercicio, con el aviso de en cuántas cartillas se usó.

## 3.2 Cargar ejercicios

Se arrastran uno o varios `.docx`. Por cada archivo el sistema muestra:

| Estado | Significado |
|---|---|
| Aceptado | Entró al banco, con su código asignado |
| Rechazado | No cumple el estándar, con la lista de motivos |
| Aviso | Entró, pero hay algo que revisar |

Los motivos de rechazo son concretos: *«La opción C no existe»*, *«La temática "Ecuaciones lineles" se parece a "Ecuaciones lineales", ¿es la misma?»*, *«La imagen 2 mide 9,1 cm y el máximo es 8,4 cm»*.

Nada entra a medias: un archivo se acepta completo o se rechaza completo.

## 3.3 Armar cartilla

Cuatro pasos en una sola pantalla:

**Paso 1 · Datos.** Institución, nombre descriptivo, grado, estructura, plantilla, tiempo, sesión, cartillas a excluir. El código se arma solo y se muestra para confirmar, o se digita y el sistema lo valida contra lo seleccionado.

**Paso 2 · Secciones.** La estructura se carga con sus secciones y cantidades. Se pueden ajustar cantidades y orden. El sistema recalcula los rangos y muestra el total.

**Paso 3 · Selección.** Por cada sección, dos modos:

- **Manual:** se busca y se eligen los ejercicios uno a uno.
- **Automática:** el sistema propone según temáticas y niveles, prefiriendo los menos usados, y se puede cambiar cualquiera.

En secciones mezcladas del ICFES se fija la cuota por submateria y el sistema entrevera el resultado.

Un indicador por sección muestra cuántos ejercicios lleva de los que necesita.

**Paso 4 · Vista previa.** El cuadernillo completo en pantalla, con la numeración final. Se pueden reordenar ejercicios dentro de una sección y quitar preguntas de un bloque compartido.

## 3.4 Generar

Antes de producir nada, el sistema corre las ocho verificaciones del estándar y muestra el resultado. Si alguna falla, explica cuál y no genera.

Si todas pasan, produce los dos archivos y los ofrece para descargar.

## 3.5 Historial

Lista de cartillas generadas, con su código, institución, fecha y cantidad de preguntas. Al abrir una se ve qué ejercicios llevó y en qué orden. Desde aquí se marca una cartilla para excluir al armar la siguiente.

## 3.6 Catálogos

Administración de grados, materias, submaterias, tipos de material y estructuras. Es donde se agregan códigos nuevos sin tocar el programa.

## 3.7 Copia de seguridad

Dos botones: **Crear copia** y **Restaurar copia**.

---

# 4 · Flujo de generación

Lo que ocurre al pulsar Generar, en orden:

1. **Validar el código.** Descomponer los cinco pares, verificar contra lo seleccionado y contra el histórico.
2. **Validar las cantidades.** Cada sección con su cantidad exacta; la suma igual al total.
3. **Asignar números.** Recorrer las secciones en orden y numerar de 1 en adelante. Los bloques y las partes reciben números consecutivos.
4. **Aplicar la plantilla.** Por cada posición, leer la letra objetivo e intercambiar los fragmentos XML de las dos opciones implicadas.
5. **Reescribir los rangos.** Sustituir `#N` y `#M` en frases de referencia y subtítulos de parte.
6. **Construir el Word.** Abrir la plantilla base (portada, márgenes, columnas, pies), insertar los títulos de sección y los fragmentos XML de cada ejercicio, y copiar las imágenes con sus identificadores.
7. **Calcular la portada.** Total de preguntas y tabla de áreas, desde la estructura real.
8. **Construir el Excel.** Una fila por pregunta, con las once columnas.
9. **Verificar.** Comparar el Excel contra la cartilla, posición por posición. Si hay una discrepancia, abortar.
10. **Entregar.** Guardar el registro en `cartilla_item` y ofrecer los dos archivos.

El paso 9 es el que garantiza que el Excel y el cuadernillo nunca se desalineen.

---

# 5 · Plan de construcción

Cada fase produce algo que funciona y se puede probar. No se pasa a la siguiente sin aprobar la anterior.

## Fase 1 · Catálogos y validador

Base de datos, catálogos precargados y el **validador de archivos de carga**.

Entregable: se suben tres ejercicios reales y el sistema dice si cumplen el estándar y por qué no.

> Se empieza por aquí a propósito. El validador es la defensa principal contra errores, y probarlo con 20 ejercicios reales antes de cargar 2.000 evita tener que rehacer el trabajo.

## Fase 2 · Carga y banco

Carga masiva, extracción de fragmentos XML e imágenes, asignación de códigos, buscador y vista previa.

Entregable: se cargan 50 ejercicios y se buscan por grado y temática.

## Fase 3 · Armado

Estructuras, secciones, selección manual y automática, exclusión de cartillas, vista previa del cuadernillo.

Entregable: se arma una cartilla completa en pantalla, sin generar archivos todavía.

## Fase 4 · Generación

Motor de plantillas, construcción del Word, construcción del Excel y verificación cruzada.

Entregable: **una cartilla real de 140 preguntas con su Excel**, comparada contra una impresa por ustedes.

## Fase 5 · Cierre

Historial, contador de usos, copia de seguridad, empaquetado como ejecutable.

Entregable: el sistema instalado y funcionando en su computador.

## Fase 6 · Traslado al servidor

Cuando quieran. Cambio a PostgreSQL, usuarios y contraseñas, copia automática.

---

# 6 · Lo que necesito para empezar la Fase 1

1. **La plantilla Word de carga**, ya normalizada según el estándar, con un ejercicio de ejemplo lleno. La preparo yo si prefieren.
2. **Diez a veinte ejercicios reales** ya ajustados al estándar, variados: con ecuaciones, con imagen, con tabla, un bloque de lectura compartida y una parte de Inglés.
3. **La plantilla Word de la cartilla**, sin contenido, solo portada, márgenes, columnas, pies y sección de cierre.
4. **Confirmación de los ocho pendientes** de la Parte 7 del estándar.

Con eso arranco.
