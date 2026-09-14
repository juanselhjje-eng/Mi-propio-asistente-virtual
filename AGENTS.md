# JARVIS — reglas del proyecto

## Objetivo
JARVIS es un asistente local para construir, probar y reparar proyectos de software usando Ollama y herramientas locales. El modelo de lenguaje es el cerebro; las herramientas hacen cambios reales.

## Arquitectura

- `main.py`: entrada de la aplicación de escritorio.
- `app.py`: Hub PySide6 y experiencia de usuario.
- `agent.py`: herramientas locales y límites de seguridad del workspace.
- `subagents.py`: catálogo y selección de especialistas.
- `orchestrator.py`: planificación, ejecución por fases y estado de tareas.
- `session_store.py`: conversaciones/sesiones persistentes.
- `opencode_adapter.py`: integración opcional con OpenCode si está instalado.
- `.opencode/agents/`: perfiles compatibles con el concepto de agentes de OpenCode.

## Flujo obligatorio

1. **Explore**: inspeccionar el workspace y localizar archivos relevantes.
2. **Plan**: convertir la petición en tareas pequeñas, archivos, dependencias e interfaces.
3. **Build**: asignar cada tarea al especialista apropiado y modificar el proyecto.
4. **Test**: validar sintaxis, referencias, imports y ejecución segura.
5. **Repair**: si hay errores reales, corregirlos y volver a probar.
6. **Report**: mostrar archivos creados/modificados, pruebas y pendientes.

Para cambios pequeños se puede saltar Plan explícito, pero nunca se debe saltar la validación final cuando se hayan modificado archivos.

## Agentes

- `build`: implementación completa.
- `plan`: solo análisis y planificación; no modifica archivos.
- `explore`: lectura/búsqueda rápida; no modifica archivos.
- `review`: revisión de cambios y regresiones.
- Especialistas por lenguaje: Python, Pygame, HTML, CSS, JavaScript, TypeScript, C/C++, C#, Java, Rust, Go, PHP y SQL.

Los subagentes son roles, no copias innecesarias del modelo. No ejecutar 15 llamadas al modelo para una tarea que puede resolver una sola llamada con herramientas.

## Rendimiento

- Mantener el contexto acotado.
- No releer archivos completos si no son necesarios.
- No repetir llamadas de herramientas sin motivo.
- Preferir una fase de exploración y después cambios concretos.
- Usar tareas paralelas solo cuando sean independientes.

## Proyectos

Cuando el usuario diga "créame un juego/app/página", crear un proyecto real y coherente. Si necesita assets, crear una estructura `assets/` y explicar rutas exactas. Usar placeholders cuando sea posible.

## OpenCode

OpenCode es una integración opcional, no un reemplazo obligatorio de JARVIS. Se toman como referencia sus ideas de agentes primarios/subagentes, modo Plan/Build, sesiones, permisos, herramientas, AGENTS.md, undo/redo y contexto por proyecto. No copiar código propietario ni asumir que una función de OpenCode existe en JARVIS.

## Reglas

- No inventar APIs, dependencias, resultados ni pruebas.
- No afirmar que un proyecto funciona si no se comprobó.
- No borrar archivos salvo que sea necesario o solicitado.
- No permitir rutas fuera del workspace.
- Los comandos potencialmente destructivos o ambiguos deben requerir confirmación.
