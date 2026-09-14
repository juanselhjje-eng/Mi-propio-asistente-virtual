import json
import os
import re
import subprocess
import sys
from pathlib import Path

from opencode_adapter import OpenCodeAdapter


class Agent:
    """Herramientas locales para construir proyectos reales."""

    IGNORED_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules", ".mypy_cache", ".pytest_cache", "dist", "build"}
    TEXT_LIMIT = 16000

    def __init__(self, workspace=None, on_tool_result=None):
        self.workspace = Path(workspace or os.getenv("ASSISTANT_WORKSPACE") or os.getcwd()).resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.on_tool_result = on_tool_result
        self.opencode = OpenCodeAdapter(self.workspace)
        self.setup_tools()
        self.messages = [{"role": "system", "content": self._system_prompt()}]

    def _system_prompt(self):
        return """
Eres Milo, un agente local de desarrollo profesional. Tu trabajo es construir, ampliar, depurar y mantener SOFTWARE REAL de cualquier tipo: juegos, aplicaciones de escritorio, aplicaciones web, APIs, herramientas, automatizaciones, utilidades, servidores, sitios, librerías y proyectos multiplataforma.

OBJETIVO DE CALIDAD
- Tómate cada petición en serio. No produzcas una demo mínima cuando el usuario pidió un proyecto profesional.
- Interpreta las especificaciones completas y conviértelas en arquitectura, módulos, interfaces, datos, recursos, configuración, pruebas y documentación coherentes.
- Prioriza calidad de código, separación de responsabilidades, UX, rendimiento, mantenibilidad, manejo de errores y una estructura preparada para crecer.
- Para proyectos visuales busca una presentación pulida: jerarquía visual, animaciones cuando tengan sentido, feedback de interacción, estados de carga/error, escalado correcto, accesibilidad básica y recursos bien organizados.
- Para juegos busca sistemas reales (estado, escenas, input, cámara, audio, UI, configuración, colisiones/física cuando correspondan, guardado y assets) en vez de un único archivo gigante.
- "AAA" debe interpretarse como objetivo de calidad y ambición dentro de las capacidades reales del equipo, hardware y recursos disponibles. Nunca prometas gráficos o assets de producción AAA si no existen los recursos para producirlos.
- No inventes modelos, APIs, imágenes, sonidos, dependencias ni resultados. Si un recurso externo no está disponible, usa un placeholder profesional generado por código o deja una interfaz clara para sustituirlo.

PROYECTOS NUEVOS
- Si el usuario pide crear cualquier juego, app, web, programa, herramienta o proyecto nuevo, primero elige un nombre corto y seguro basado en su petición y usa create_project.
- NUNCA pongas un proyecto nuevo directamente en la raíz del workspace.
- Todo lo perteneciente al proyecto debe quedar dentro de su carpeta.
- Decide la arquitectura según el tipo de software; no fuerces una plantilla de juegos sobre una aplicación ni una plantilla web sobre otro tipo de proyecto.
- Crea los archivos realmente necesarios: punto de entrada, módulos, configuración, recursos, tests, documentación y dependencias cuando correspondan.
- No crees archivos artificiales solo para aparentar complejidad.

CORRECCIONES Y EVOLUCIÓN
- Si el usuario dice "corrígelo", "arréglalo", "mejora esto" o pide una nueva función, inspecciona primero el proyecto existente.
- Identifica el proyecto correcto por el contexto y por los archivos reales.
- Modifica el proyecto existente; no generes otro proyecto paralelo.
- Conserva las partes que ya funcionan salvo que haya una razón técnica para cambiarlas.
- Si encuentras errores, usa los mensajes reales de las herramientas como evidencia y corrige la causa, no solo el síntoma.

FLUJO PROFESIONAL
1. Explorar estructura y archivos relevantes.
2. Planificar la arquitectura y los cambios necesarios.
3. Implementar en archivos reales.
4. Validar sintaxis, referencias, configuración y coherencia.
5. Ejecutar pruebas seguras cuando sea posible.
6. Reparar errores encontrados.
7. Volver a validar después de cada reparación importante.
8. Reportar exactamente qué se creó/modificó y qué quedó pendiente.

OPENCODE
- OpenCode es un motor auxiliar opcional para tareas complejas. No sustituye a Milo.
- Si está instalado, úsalo cuando pueda aportar una segunda pasada de implementación/reparación, especialmente en proyectos grandes o errores difíciles.
- Después de usar OpenCode, Milo debe inspeccionar y validar los cambios con sus propias herramientas.
- Si OpenCode no está instalado, trabaja completamente con las herramientas locales de Milo.

REGLA FUNDAMENTAL
No digas "creado", "corregido", "funciona" o "terminado" por intuición. Solo puedes afirmarlo cuando las operaciones reales y las comprobaciones disponibles lo respalden.
""".strip()

    def _safe_path(self, path):
        raw = Path(path)
        candidate = raw if raw.is_absolute() else self.workspace / raw
        candidate = candidate.resolve()
        try:
            candidate.relative_to(self.workspace)
        except ValueError:
            raise ValueError(f"La ruta esta fuera del workspace: {path}")
        return candidate

    def setup_tools(self):
        self.tools = [
            {"type": "function", "name": "list_files", "description": "Lista archivos y carpetas del workspace.", "parameters": {"type": "object", "properties": {"directory": {"type": "string"}, "recursive": {"type": "boolean"}}, "required": [], "additionalProperties": False}},
            {"type": "function", "name": "read_file", "description": "Lee un archivo de texto existente.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"], "additionalProperties": False}},
            {"type": "function", "name": "create_project", "description": "Crea la carpeta raíz de cualquier proyecto nuevo dentro del workspace.", "parameters": {"type": "object", "properties": {"project_name": {"type": "string"}}, "required": ["project_name"], "additionalProperties": False}},
            {"type": "function", "name": "write_file", "description": "Crea o reemplaza un archivo completo dentro del workspace y verifica la escritura.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"], "additionalProperties": False}},
            {"type": "function", "name": "replace_in_file", "description": "Hace un reemplazo puntual en un archivo existente y verifica el cambio.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}, "replace_all": {"type": "boolean"}}, "required": ["path", "old_text", "new_text"], "additionalProperties": False}},
            {"type": "function", "name": "append_file", "description": "Agrega texto al final de un archivo y verifica el cambio.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"], "additionalProperties": False}},
            {"type": "function", "name": "make_directory", "description": "Crea una carpeta dentro del workspace.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"], "additionalProperties": False}},
            {"type": "function", "name": "delete_file", "description": "Elimina un archivo cuando sea necesario o solicitado.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"], "additionalProperties": False}},
            {"type": "function", "name": "validate_python", "description": "Comprueba la sintaxis de un archivo Python.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"], "additionalProperties": False}},
            {"type": "function", "name": "run_python", "description": "Ejecuta un Python no interactivo con timeout para comprobarlo.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "timeout": {"type": "integer"}}, "required": ["path"], "additionalProperties": False}},
            {"type": "function", "name": "validate_project", "description": "Valida un proyecto completo: Python, JSON y referencias locales HTML.", "parameters": {"type": "object", "properties": {"directory": {"type": "string"}}, "required": [], "additionalProperties": False}},
            {"type": "function", "name": "run_opencode", "description": "Usa OpenCode en modo no interactivo para una tarea compleja. Después Milo debe validar los cambios.", "parameters": {"type": "object", "properties": {"prompt": {"type": "string"}, "agent": {"type": "string"}, "timeout": {"type": "integer"}}, "required": ["prompt"], "additionalProperties": False}},
        ]

    def list_files(self, directory=".", recursive=False):
        folder = self._safe_path(directory)
        if not folder.is_dir():
            return {"ok": False, "error": f"No existe la carpeta: {directory}"}
        if recursive:
            entries = (p for p in folder.rglob("*") if not any(part in self.IGNORED_DIRS for part in p.parts))
        else:
            entries = (p for p in folder.iterdir() if p.name not in self.IGNORED_DIRS)
        result = [{"path": str(p.relative_to(self.workspace)), "type": "dir" if p.is_dir() else "file"} for p in entries]
        return {"ok": True, "files": sorted(result, key=lambda x: x["path"])[:1000]}

    def read_file(self, path):
        target = self._safe_path(path)
        if not target.is_file():
            return {"ok": False, "error": f"No existe el archivo: {path}"}
        try:
            text = target.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return {"ok": False, "error": "El archivo no es UTF-8 de texto."}
        if len(text) > self.TEXT_LIMIT:
            return {"ok": True, "truncated": True, "content": text[:self.TEXT_LIMIT], "total_chars": len(text)}
        return {"ok": True, "content": text}

    def _project_folder_name(self, name):
        name = re.sub(r"[^A-Za-z0-9áéíóúÁÉÍÓÚñÑ _-]", "", str(name)).strip()
        name = re.sub(r"\s+", " ", name)
        if not name:
            raise ValueError("El nombre del proyecto está vacío.")
        if name in {".", ".."} or len(name) > 80:
            raise ValueError("Nombre de proyecto no válido.")
        return name

    def create_project(self, project_name):
        folder_name = self._project_folder_name(project_name)
        target = self._safe_path(folder_name)
        existed = target.exists()
        target.mkdir(parents=True, exist_ok=True)
        return {"ok": True, "path": str(target.relative_to(self.workspace)), "created": not existed, "verified": target.is_dir()}

    def write_file(self, path, content):
        target = self._safe_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        existed = target.exists()
        target.write_text(content, encoding="utf-8", newline="")
        verified = target.is_file() and target.read_text(encoding="utf-8") == content
        if not verified:
            return {"ok": False, "error": f"No se pudo verificar la escritura de: {path}"}
        return {"ok": True, "path": str(target.relative_to(self.workspace)), "action": "actualizado" if existed else "creado", "bytes": len(content.encode("utf-8")), "verified": True}

    def replace_in_file(self, path, old_text, new_text, replace_all=False):
        target = self._safe_path(path)
        if not target.is_file():
            return {"ok": False, "error": f"No existe el archivo: {path}"}
        content = target.read_text(encoding="utf-8")
        count = content.count(old_text)
        if count == 0:
            return {"ok": False, "error": "No se encontro old_text. Lee de nuevo el archivo."}
        if not replace_all and count > 1:
            return {"ok": False, "error": f"old_text aparece {count} veces. Usa un fragmento mas especifico."}
        updated = content.replace(old_text, new_text, -1 if replace_all else 1)
        target.write_text(updated, encoding="utf-8", newline="")
        if target.read_text(encoding="utf-8") != updated:
            return {"ok": False, "error": f"No se pudo verificar el cambio en: {path}"}
        return {"ok": True, "path": str(target.relative_to(self.workspace)), "replaced": count if replace_all else 1, "verified": True}

    def append_file(self, path, content):
        target = self._safe_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8", newline="") as file:
            file.write(content)
        return {"ok": True, "path": str(target.relative_to(self.workspace)), "verified": target.is_file() and target.read_text(encoding="utf-8").endswith(content)}

    def make_directory(self, path):
        target = self._safe_path(path)
        target.mkdir(parents=True, exist_ok=True)
        return {"ok": True, "path": str(target.relative_to(self.workspace)), "verified": target.is_dir()}

    def delete_file(self, path):
        target = self._safe_path(path)
        if not target.is_file():
            return {"ok": False, "error": f"No existe el archivo: {path}"}
        target.unlink()
        return {"ok": True, "deleted": str(target.relative_to(self.workspace)), "verified": not target.exists()}

    def validate_python(self, path):
        target = self._safe_path(path)
        if target.suffix.lower() != ".py" or not target.is_file():
            return {"ok": False, "error": f"No existe un archivo Python valido: {path}"}
        try:
            subprocess.run([sys.executable, "-m", "py_compile", str(target)], cwd=self.workspace, capture_output=True, text=True, timeout=8, check=True)
            return {"ok": True, "valid": True, "path": str(target.relative_to(self.workspace))}
        except subprocess.CalledProcessError as exc:
            return {"ok": True, "valid": False, "stderr": exc.stderr[-5000:]}
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": "La validacion de Python supero 8 segundos."}

    def run_python(self, path, timeout=10):
        target = self._safe_path(path)
        if target.suffix.lower() != ".py" or not target.is_file():
            return {"ok": False, "error": f"No existe un archivo Python valido: {path}"}
        timeout = max(1, min(int(timeout), 20))
        try:
            completed = subprocess.run([sys.executable, str(target)], cwd=target.parent, capture_output=True, text=True, timeout=timeout)
            return {"ok": True, "returncode": completed.returncode, "stdout": completed.stdout[-6000:], "stderr": completed.stderr[-6000:]}
        except subprocess.TimeoutExpired as exc:
            return {"ok": False, "error": f"La ejecucion supero {timeout}s", "stdout": str(exc.stdout or "")[-2000:], "stderr": str(exc.stderr or "")[-2000:]}

    def validate_project(self, directory="."):
        root = self._safe_path(directory)
        if not root.is_dir():
            return {"ok": False, "error": f"No existe la carpeta: {directory}"}
        files = [p for p in root.rglob("*") if p.is_file() and not any(part in self.IGNORED_DIRS for part in p.parts)]
        errors = []
        checks = 0
        for path in files:
            rel = str(path.relative_to(self.workspace))
            suffix = path.suffix.lower()
            if suffix == ".py":
                checks += 1
                result = self.validate_python(rel)
                if not result.get("valid", False):
                    errors.append(f"{rel}: {result.get('stderr') or result.get('error')}")
            elif suffix == ".json":
                checks += 1
                try:
                    json.loads(path.read_text(encoding="utf-8"))
                except Exception as exc:
                    errors.append(f"{rel}: JSON invalido: {exc}")
        for path in files:
            if path.suffix.lower() not in {".html", ".htm"}:
                continue
            checks += 1
            text = path.read_text(encoding="utf-8", errors="replace")
            refs = re.findall(r'(?:src|href)=["\']([^"\'#?]+)', text, flags=re.I)
            for ref in refs:
                if ref.startswith(("http://", "https://", "data:", "mailto:", "javascript:")):
                    continue
                candidate = (path.parent / ref).resolve()
                try:
                    candidate.relative_to(root.resolve())
                except ValueError:
                    errors.append(f"{path.relative_to(self.workspace)}: referencia fuera del proyecto: {ref}")
                    continue
                if not candidate.exists():
                    errors.append(f"{path.relative_to(self.workspace)}: falta el recurso referenciado: {ref}")
        return {"ok": True, "valid": not errors, "checks": checks, "errors": errors[:50], "files": len(files)}

    def run_opencode(self, prompt, timeout=180, agent="build"):
        if not self.opencode.available:
            return {"ok": False, "error": "OpenCode no está instalado o no está en PATH."}
        return self.opencode.run(prompt, timeout=timeout, agent=agent)

    def execute_tool(self, name, args):
        functions = {"list_files": self.list_files, "read_file": self.read_file, "create_project": self.create_project, "write_file": self.write_file, "replace_in_file": self.replace_in_file, "append_file": self.append_file, "make_directory": self.make_directory, "delete_file": self.delete_file, "validate_python": self.validate_python, "run_python": self.run_python, "validate_project": self.validate_project, "run_opencode": self.run_opencode}
        fn = functions.get(name)
        if not fn:
            return {"ok": False, "error": f"Herramienta no encontrada: {name}"}
        try:
            return fn(**args)
        except Exception as exc:
            return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

    @staticmethod
    def _dump_item(item):
        if hasattr(item, "model_dump"):
            return item.model_dump(exclude_none=True)
        return item

    def process_response(self, response):
        output_items = getattr(response, "output", []) or []
        self.messages.extend(self._dump_item(item) for item in output_items)
        tool_calls = []
        texts = []
        for item in output_items:
            item_type = getattr(item, "type", None)
            if item_type == "function_call":
                tool_calls.append(item)
            elif item_type == "message":
                for part in getattr(item, "content", []) or []:
                    text = getattr(part, "text", None)
                    if text:
                        texts.append(text)
        return tool_calls, "\n".join(texts).strip()

    def add_tool_outputs(self, tool_calls):
        for call in tool_calls:
            name = getattr(call, "name", "")
            raw_args = getattr(call, "arguments", "{}")
            try:
                args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                result = self.execute_tool(name, args)
            except Exception as exc:
                result = {"ok": False, "error": f"Error procesando argumentos: {type(exc).__name__}: {exc}"}
            if result.get("ok"):
                if name == "create_project":
                    message = f"[PROYECTO] carpeta: {result['path']} · verificada"
                elif name == "write_file":
                    message = f"[ARCHIVO] {result['action']}: {result['path']} · verificado"
                elif name == "replace_in_file":
                    message = f"[ARCHIVO] modificado: {result['path']} · verificado"
                elif name == "make_directory":
                    message = f"[CARPETA] creada: {result['path']} · verificado"
                elif name == "delete_file":
                    message = f"[ARCHIVO] eliminado: {result['deleted']} · verificado"
                elif name in {"validate_python", "validate_project"}:
                    message = f"[PRUEBA] {name}: {'OK' if result.get('valid', True) else 'ERROR'}"
                elif name == "run_opencode":
                    message = f"[OPENCODE] {'OK' if result.get('ok') else 'ERROR'} · cambios revisados después"
                else:
                    message = f"[HERRAMIENTA] {name}: OK"
            else:
                message = f"[HERRAMIENTA] error en {name}: {result.get('error', 'desconocido')}"
            print(message)
            if self.on_tool_result:
                try:
                    self.on_tool_result(message, result)
                except Exception:
                    pass
            self.messages.append({"type": "function_call_output", "call_id": getattr(call, "call_id", getattr(call, "id", "")), "output": json.dumps(result, ensure_ascii=False)})
