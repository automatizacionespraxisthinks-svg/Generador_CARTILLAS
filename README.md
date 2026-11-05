# Generador de cartillas · PRAXIS – THINKS

Sistema local para validar ejercicios en Word, guardarlos en un banco y generar cartillas tipo ICFES con su Excel de claves.
La especificación está en [docs/ESTANDAR_PRAXIS_v1.2.md](docs/ESTANDAR_PRAXIS_v1.2.md) y [docs/PROPUESTA_TECNICA_v1.md](docs/PROPUESTA_TECNICA_v1.md).

## Estado

| Fase | Contenido | Estado |
|---|---|---|
| 1 | Catálogos, base de datos y validador de archivos de carga | Lista |
| 2 | Carga al banco, buscador, vista previa, eliminación y copia de seguridad | **Lista para cargar ejercicios** |
| 3 | Armado de cartillas: código, secciones, selección manual y automática, vista previa | **Lista** |
| 4 | Generación del Word y del Excel de claves, con verificación cruzada | **Lista** |
| 5 | Ajuste a múltiplo de 4 **(listo)**; historial, restaurar copias de seguridad y ejecutable | En curso |

**Estándar v1.2** (21/09/2026): texto justificado que conserva la alineación aplicada a mano, tablas centradas y compactas, columnas de 9,12 cm y glosario opcional por pregunta (TABLA DE GLOSARIO + casilla «Incluir glosario»). Las plantillas de carga vigentes son las `_v1.2`. Desde el 21/09/2026 se aceptan también 3°, 4° y 5° (códigos 33, 44, 55).

## Cómo abrirlo

Doble clic en **`Iniciar Generador PRAXIS.bat`** (o `.venv\Scripts\python iniciar.py`). Se abre el navegador en `http://127.0.0.1:8765/#cargar`; la ventana negra debe quedar abierta mientras se usa.

La base de datos se crea sola en `datos/praxis.db` con los catálogos de fábrica.

## Carpetas

| Carpeta | Qué hay |
|---|---|
| `app/validador/` | Lectura del Word y las reglas del Estándar 2.12 |
| `app/banco.py`, `app/armado.py`, `app/generador.py` | Banco, armado y generación del Word y el Excel |
| `app/bd.py`, `app/semilla.py` | Tablas y catálogos de fábrica (`app/catalogos_base.py`) |
| `app/web/` | Pantallas en el navegador: Panel, Cargar ejercicios, Banco, Crear simulacro, Formatos y Catálogos |
| `plantillas/` | Plantilla base de la cartilla, plantillas de carga v1.2, ejemplos llenos, instructivo en Word, el Excel de códigos y las 5 plantillas de respuestas |
| `scripts/` | Generadores de plantillas y ejemplos, prototipo de maquetación en Word |
| `tests/` | Pruebas: `.venv\Scripts\python -m pytest tests` |

## Servidor (Docker / Dokploy)

El repositorio trae `Dockerfile`, `.dockerignore` y `docker-compose.yml`. En el servidor:

- La base queda en el volumen **`/data`** (`/data/praxis.db`). Sin volumen, cada redespliegue la borra.
- Variables: `PRAXIS_USUARIO` y `PRAXIS_CLAVE` piden usuario y clave al entrar (si se dejan vacías, la página queda abierta a cualquiera con el enlace). `PORT` (8000 por defecto).
- En Linux no hay Microsoft Word, así que **no se cuentan las páginas ni se reordena con Word** (ajuste a múltiplo de 4 y maquetación). La cartilla y el Excel se generan igual; el conteo de páginas se hace en el equipo local con Word.
- `GET /salud` responde sin clave, para el healthcheck.
- Copia de seguridad: botón de la pantalla (`/api/copia-seguridad`) o el volumen de Dokploy.

Probar en local: `docker compose up --build` (descomentar `ports` en `docker-compose.yml`) y abrir `http://localhost:8000`.
