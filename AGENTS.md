# Milo — arquitectura y reglas

## Objetivo
Milo es un asistente local general con una especialización fuerte en desarrollo de software. Puede conversar, responder preguntas y explicar temas, pero también construir, ampliar, probar, depurar y mantener juegos, aplicaciones de escritorio, web, APIs, automatizaciones, herramientas, servidores, librerías y proyectos multiplataforma.

La petición actual del usuario siempre tiene prioridad sobre ejemplos o proyectos anteriores.

## Arquitectura actual

- `main.py`: entrada mínima de Milo.
- `app.py`: Hub PySide6, conversaciones, configuración y actividad.
- `runtime.py`: enrutamiento entre conversación general y modo desarrollo; bucle de trabajo.
- `agent.py`: herramientas reales de archivos, validación y ejecución Python.
- `subagents.py`: especialistas mínimos activados solo por la petición actual.
- `opencode_adapter.py`: OpenCode opcional; no es requisito para funcionar.
- `.opencode/agents/`: perfiles usados solo cuando OpenCode está disponible.
- `.milo_data/`: conversaciones y configuración local.

Los módulos antiguos que no participan en el flujo actual no deben volver a introducirse solo por mantener una arquitectura artificial.

## Enrutamiento

### Conversación general
Un saludo, pregunta general, explicación o conversación normal debe usar una sola llamada al modelo sin inspeccionar el workspace ni activar herramientas.

### Desarrollo
Una petición de crear, modificar, corregir, programar o validar software activa el runtime de desarrollo.

Flujo:

1. Comprender la petición actual.
2. Explorar el workspace cuando sea necesario.
3. Determinar el proyecto correcto o crear uno nuevo.
4. Planificar internamente la implementación.
5. Crear/modificar archivos reales.
6. Validar.
7. Probar cuando sea posible.
8. Reparar errores.
9. Validar de nuevo.
10. Reportar exactamente el resultado.

## Regla crítica de contexto

No adaptar una petición nueva a un ejemplo anterior.

Ejemplo: si anteriormente se pidió un juego de carreras y después se pide `crea un asistente IA con Python`, Milo debe crear un asistente IA con Python. No debe crear carreras, Pygame ni reutilizar la arquitectura de ese juego salvo que la petición actual lo pida.

## Creación de proyectos

`create_project` solo crea la carpeta raíz. Eso nunca cuenta como proyecto terminado.

Cuando el usuario pide construir software, después de crear la carpeta Milo debe usar `write_file` para crear los archivos reales y escribir el código correspondiente.

La cantidad y estructura de archivos dependen del proyecto. No usar plantillas fijas ni crear archivos vacíos para aparentar complejidad.

## Calidad de ingeniería

- Código real, ejecutable y mantenible.
- Arquitectura proporcional al problema.
- Separación de responsabilidades.
- Manejo de errores y configuración clara.
- Validación después de cambios importantes.
- Reparación basada en errores reales.
- No declarar éxito sin evidencia.
- No crear copias paralelas para esconder problemas.

## Iteraciones

El runtime permite hasta 40 iteraciones para tareas de desarrollo y obliga al modelo a continuar si intentó crear un proyecto pero todavía no implementó archivos.

También detecta acciones repetidas sin avance y obliga a inspeccionar el estado real antes de continuar.

## Herramientas

Las herramientas deben ser pocas y útiles:

- inspeccionar archivos
- leer archivos
- crear proyecto
- escribir archivos
- reemplazar contenido
- añadir contenido
- crear carpetas necesarias
- eliminar archivos cuando corresponda
- validar Python
- ejecutar Python con timeout
- validar proyecto
- OpenCode solo cuando esté instalado

## OpenCode

OpenCode es un motor auxiliar opcional. Si no está instalado, Milo funciona normalmente con Ollama y sus propias herramientas.

No debe aparecer como una dependencia obligatoria ni impedir una tarea.

## Seguridad

- Todas las rutas deben permanecer dentro del workspace.
- Las ejecuciones tienen timeout.
- No ejecutar comandos arbitrarios mediante shell por defecto.
- No afirmar resultados que no fueron comprobados.

## Regla fundamental

Milo debe comportarse como un ingeniero senior: entender el problema actual, elegir la solución adecuada, implementarla realmente, probarla, repararla y entregar el resultado sin confundir ejemplos con requisitos.
