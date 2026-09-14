# Milo — reglas del proyecto

## Objetivo
Milo es un asistente local para construir, probar y reparar proyectos de software usando Ollama y herramientas locales. El modelo de lenguaje razona; las herramientas hacen cambios reales.

## Arquitectura

- `main.py`: entrada de la aplicación de escritorio.
- `app.py`: Hub PySide6 y experiencia de usuario.
- `agent.py`: herramientas locales, creación de proyectos y límites del workspace.
- `subagents.py`: catálogo y selección de especialistas.
- `orchestrator.py`: planificación, ejecución por fases y estado de tareas.
- `session_store.py`: conversaciones/sesiones persistentes.
- `opencode_adapter.py`: integración opcional con OpenCode CLI.
- `.opencode/agents/`: perfiles compatibles con el concepto de agentes de OpenCode.

## Flujo obligatorio

1. **Explore**: inspeccionar el workspace y localizar archivos relevantes.
2. **Plan**: convertir la petición en tareas pequeñas, archivos, dependencias e interfaces.
3. **Build**: asignar cada tarea al especialista apropiado y modificar el proyecto.
4. **Test**: validar sintaxis, referencias, imports y ejecución segura.
5. **Repair**: si hay errores reales, corregirlos y volver a probar.
6. **Report**: mostrar archivos creados/modificados, pruebas y pendientes.

Para cambios pequeños se puede simplificar Plan, pero nunca se debe saltar la validación final cuando se hayan modificado archivos.

## Creación de proyectos

Cuando el usuario pida un juego, app, página o programa nuevo:

1. Elegir un nombre claro basado en la petición.
2. Crear una carpeta raíz propia con `create_project`.
3. Crear dentro de esa carpeta todos los archivos necesarios.
4. Mantener imports, rutas y assets coherentes.
5. Validar el proyecto antes de reportarlo como terminado.

Cuando el usuario pida corregir algo, primero localizar e inspeccionar el proyecto existente y modificarlo en lugar de crear otro proyecto paralelo.

## Agentes

- `build`: implementación completa.
- `plan`: solo análisis y planificación; no modifica archivos.
- `explore`: lectura/búsqueda rápida; no modifica archivos.
- `review`: revisión de cambios y regresiones.
- Especialistas por lenguaje: Python, Pygame, HTML, CSS, JavaScript, TypeScript, C/C++, C#, Java, Rust, Go, PHP y SQL.

Los subagentes son roles, no copias innecesarias del modelo. No ejecutar muchas llamadas al modelo para una tarea que puede resolver una sola llamada con herramientas.

## OpenCode

OpenCode es una integración opcional y un motor auxiliar para tareas complejas. Milo puede usar `opencode run --agent build` cuando OpenCode esté instalado. Después de cualquier ejecución de OpenCode, Milo debe inspeccionar y validar los cambios con sus propias herramientas.

Se toman como referencia sus ideas de agentes Plan/Build, sesiones, permisos, herramientas, `AGENTS.md`, undo/redo y contexto por proyecto. No copiar código propietario ni asumir capacidades que no estén disponibles localmente.

## Reglas

- No inventar APIs, dependencias, resultados ni pruebas.
- No afirmar que un proyecto funciona si no se comprobó.
- No borrar archivos salvo que sea necesario o solicitado.
- No permitir rutas fuera del workspace.
- Los comandos potencialmente destructivos o ambiguos deben requerir confirmación.
