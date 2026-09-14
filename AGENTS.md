# Milo — arquitectura y reglas del proyecto

## Objetivo
Milo es un agente local profesional para construir, ampliar, probar, depurar y mantener software real de cualquier tipo: juegos, aplicaciones de escritorio, web, APIs, automatizaciones, herramientas, servidores, librerías y proyectos multiplataforma.

La inteligencia principal puede ejecutarse localmente con Ollama. Los motores auxiliares y proveedores externos son opcionales; Milo no debe depender de una API de pago para funcionar.

## Arquitectura

- `main.py`: entrada de la aplicación de escritorio.
- `app.py`: Hub PySide6, conversaciones, configuración y actividad.
- `agent.py`: herramientas locales, workspace y bucle de herramientas.
- `subagents.py`: especialistas por lenguaje y dominio.
- `orchestrator.py`: flujo Explore → Plan → Build → Test → Repair → Report.
- `session_store.py`: sesiones, mensajes, TODO, plan y proyecto activo.
- `project_state.py`: proyecto activo y snapshots/checkpoints.
- `validators.py`: validación genérica de proyectos.
- `permissions.py`: límites de lectura/escritura/ejecución/instalación/red/control de pantalla.
- `model_router.py`: selección de modelos local-first y sin dependencia de un proveedor concreto.
- `opencode_adapter.py`: integración opcional con OpenCode CLI.
- `.opencode/agents/`: perfiles compatibles con los conceptos de agentes de OpenCode.
- `.milo_data/`: datos locales, sesiones, configuración, estado y snapshots.

## Flujo obligatorio

1. **Explore**: inspeccionar workspace y proyecto activo.
2. **Plan**: convertir la petición en arquitectura, tareas, archivos, dependencias e interfaces.
3. **Build**: implementar con los especialistas adecuados.
4. **Test**: validar sintaxis, referencias, configuración y ejecución segura.
5. **Repair**: corregir errores reales y volver a probar.
6. **Review**: revisar regresiones y coherencia del resultado.
7. **Report**: informar exactamente qué cambió, qué se comprobó y qué quedó pendiente.

No se debe crear complejidad artificial. Una petición pequeña puede tener una solución pequeña; una petición profesional debe recibir una arquitectura proporcional.

## Calidad profesional

- Mantener separación de responsabilidades y módulos coherentes.
- Priorizar mantenibilidad, rendimiento, manejo de errores, seguridad y pruebas.
- Para interfaces: jerarquía visual, estados de carga/error, interacción clara, escalado y accesibilidad básica.
- Para juegos: escenas/estado, input, cámara, audio, UI, configuración, guardado, colisiones/física y assets cuando correspondan.
- Para aplicaciones: arquitectura por capas cuando aporte valor, configuración, persistencia, logging, validación de entradas y recuperación ante errores.
- Para proyectos web/API: separación frontend/backend cuando corresponda, rutas, validación, configuración segura y pruebas.
- "AAA" es un objetivo de calidad y ambición, no una promesa de assets comerciales o producción de un estudio profesional cuando faltan recursos.

## Modelos

- El modelo local es la opción por defecto.
- `qwen3:8b` puede ser el modelo general predeterminado.
- `qwen3-coder:30b` puede configurarse como modelo especializado si el hardware lo soporta.
- Otros proveedores/modelos son opcionales y solo se usan si el usuario los configura.
- Nunca afirmar que un modelo o API es gratuito sin verificarlo.

## Seguridad y permisos

- Nunca permitir rutas fuera del workspace.
- Lectura/escritura local: permitida dentro del workspace.
- Ejecución: limitada y con timeout.
- Instalación de dependencias, red y control de pantalla: desactivados por defecto hasta contar con un permiso explícito.
- Borrado: conservar evidencia/snapshot cuando sea posible y evitar operaciones destructivas ambiguas.
- Registrar las operaciones sensibles para poder auditar qué hizo el agente.

## Creación y corrección

Para un proyecto nuevo: crear una carpeta raíz propia y poner dentro todos sus archivos reales.

Para corregir: localizar primero el proyecto existente, leer los archivos relevantes, reproducir el error cuando sea seguro, corregir la causa y validar de nuevo. Nunca crear una copia paralela para ocultar un problema.

## OpenCode

OpenCode es auxiliar, no el núcleo de Milo. Puede ejecutar tareas complejas mediante `opencode run --agent build`. Después, Milo debe inspeccionar y validar los cambios.

Se toman como referencia sus conceptos de Plan/Build, sesiones, herramientas, permisos, AGENTS.md, contexto por proyecto y recuperación. No asumir capacidades que no estén instaladas.

## Regla fundamental

No afirmar "creado", "corregido", "funciona" o "terminado" sin evidencia de operaciones reales y validaciones disponibles.
