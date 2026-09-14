import json
import os
import subprocess
import sys
from pathlib import Path


class Agent:
    """Agente local para crear, probar y reparar proyectos de software."""

    def __init__(self, workspace=None):
        self.workspace = Path(workspace or os.getenv("ASSISTANT_WORKSPACE") or os.getcwd()).resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.setup_tools()
        self.messages = [{"role": "system", "content": self._system_prompt()}]

    def _system_prompt(self):
        return """
Eres un agente de programacion local en español. Tu trabajo NO es solo escribir codigo en el chat:
debes construir proyectos funcionales dentro del workspace usando las herramientas.

REGLAS IMPORTANTES PARA EVITAR CODIGO INCOHERENTE:
1. Antes de modificar un proyecto existente, usa list_files y lee los archivos relevantes.
2. Si la peticion es un proyecto nuevo, primero piensa en una arquitectura simple: archivos, responsabilidades y como se conectan.
3. No inventes APIs, funciones, imports, variables globales, rutas ni nombres de archivos que no existan.
4. Mantén consistencia entre archivos: si HTML llama a script.js, ese archivo debe existir; si Python importa un modulo local, créalo y comprueba su nombre.
5. No agregues dependencias externas si no son necesarias. Si una dependencia es necesaria, escribe los requisitos correspondientes.
6. No mezcles sintaxis de lenguajes. Cada archivo debe contener exclusivamente el lenguaje indicado por su extension.
7. Usa nombres claros y consistentes. No cambies una funcion o variable en un archivo sin actualizar sus usos.
8. Para cambios pequeños, usa replace_in_file. Para un archivo nuevo o una reescritura justificada, usa write_file.
9. Después de crear o modificar Python, ejecuta validate_python. Si falla, lee el error, corrige el archivo y vuelve a validar.
10. Si el proyecto tiene varios archivos, revisa list_files al terminar y comprueba que existan todos los archivos necesarios.
11. No declares que un proyecto funciona si no lo comprobaste. Si una parte no puede ejecutarse localmente, dilo.
12. No borres archivos salvo que el usuario lo pida o sea imprescindible para corregir el proyecto.
13. Si el usuario pide HTML/CSS/JS, crea una estructura completa y coherente. Si pide un juego, incluye HTML, CSS y JS cuando corresponda, y conecta correctamente los scripts.
14. Si el usuario pide Python, prioriza codigo ejecutable, manejo de errores y una estructura sencilla antes que codigo enorme.
15. Evita generar cientos de lineas sin necesidad. Es mejor un proyecto pequeño que funcione que uno enorme e incoherente.
16. Cuando recibas un error de una herramienta, úsalo como evidencia para corregir el problema; no lo ignores.
17. Trabaja dentro del workspace y usa rutas relativas.

FLUJO RECOMENDADO:
- Proyecto existente: inspeccionar -> entender -> modificar -> validar -> reparar -> responder.
- Proyecto nuevo: diseñar -> crear archivos -> validar -> reparar -> revisar estructura -> responder.

Tu respuesta final debe ser breve y decir qué archivos se crearon/modificaron y qué comprobaciones se hicieron.
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
            {
                "type": "function", "name": "list_files",
                "description": "Inspecciona la estructura del workspace. Usa recursive=true para proyectos completos.",
                "parameters": {"type": "object", "properties": {
                    "directory": {"type": "string"},
                    "recursive": {"type": "boolean"}
                }, "required": [], "additionalProperties": False}
            },
            {
                "type": "function", "name": "read_file",
                "description": "Lee un archivo UTF-8 existente. Obligatorio antes de modificar codigo existente cuando el contenido sea relevante.",
                "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"], "additionalProperties": False}
            },
            {
                "type": "function", "name": "write_file",
                "description": "Crea o reemplaza un archivo UTF-8 completo. Úsalo para archivos nuevos o reescrituras necesarias.",
                "parameters": {"type": "object", "properties": {
                    "path": {"type": "string"}, "content": {"type": "string"}
                }, "required": ["path", "content"], "additionalProperties": False}
            },
            {
                "type": "function", "name": "replace_in_file",
                "description": "Hace un cambio puntual en un archivo existente sin reescribirlo completo.",
                "parameters": {"type": "object", "properties": {
                    "path": {"type": "string"}, "old_text": {"type": "string"},
                    "new_text": {"type": "string"}, "replace_all": {"type": "boolean"}
                }, "required": ["path", "old_text", "new_text"], "additionalProperties": False}
            },
            {
                "type": "function", "name": "append_file",
                "description": "Agrega contenido al final de un archivo UTF-8.",
                "parameters": {"type": "object", "properties": {
                    "path": {"type": "string"}, "content": {"type": "string"}
                }, "required": ["path", "content"], "additionalProperties": False}
            },
            {
                "type": "function", "name": "make_directory",
                "description": "Crea una carpeta dentro del workspace.",
                "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"], "additionalProperties": False}
            },
            {
                "type": "function", "name": "delete_file",
                "description": "Elimina un archivo. Solo cuando sea necesario para cumplir claramente la petición.",
                "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"], "additionalProperties": False}
            },
            {
                "type": "function", "name": "validate_python",
                "description": "Comprueba la sintaxis de un archivo Python sin ejecutar sus acciones. Devuelve errores concretos para poder repararlos.",
                "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"], "additionalProperties": False}
            },
            {
                "type": "function", "name": "run_python",
                "description": "Ejecuta un archivo Python para probar comportamiento. Úsalo después de validar sintaxis y evita programas potencialmente destructivos.",
                "parameters": {"type": "object", "properties": {
                    "path": {"type": "string"}, "timeout": {"type": "integer"}
                }, "required": ["path"], "additionalProperties": False}
            },
        ]

    def list_files(self, directory=".", recursive=False):
        folder = self._safe_path(directory)
        if not folder.is_dir():
            return {"ok": False, "error": f"No existe la carpeta: {directory}"}
        entries = folder.rglob("*") if recursive else folder.iterdir()
        result = []
        for p in entries:
            rel = str(p.relative_to(self.workspace))
            result.append({"path": rel, "type": "dir" if p.is_dir() else "file"})
        return {"ok": True, "files": sorted(result, key=lambda x: x["path"])}

    def read_file(self, path):
        target = self._safe_path(path)
        if not target.is_file():
            return {"ok": False, "error": f"No existe el archivo: {path}"}
        try:
            text = target.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return {"ok": False, "error": "El archivo no es UTF-8 de texto."}
        # Evita llenar el contexto con archivos gigantes.
        limit = 30000
        if len(text) > limit:
            return {"ok": True, "truncated": True, "content": text[:limit], "total_chars": len(text)}
        return {"ok": True, "content": text}

    def write_file(self, path, content):
        target = self._safe_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="")
        return {"ok": True, "path": str(target.relative_to(self.workspace)), "bytes": len(content.encode("utf-8"))}

    def replace_in_file(self, path, old_text, new_text, replace_all=False):
        target = self._safe_path(path)
        if not target.is_file():
            return {"ok": False, "error": f"No existe el archivo: {path}"}
        content = target.read_text(encoding="utf-8")
        count = content.count(old_text)
        if count == 0:
            return {"ok": False, "error": "No se encontro old_text. Lee de nuevo el archivo antes de intentar otro reemplazo."}
        if not replace_all and count > 1:
            return {"ok": False, "error": f"old_text aparece {count} veces. Usa un fragmento mas especifico o replace_all=true."}
        updated = content.replace(old_text, new_text, -1 if replace_all else 1)
        target.write_text(updated, encoding="utf-8", newline="")
        return {"ok": True, "path": str(target.relative_to(self.workspace)), "replaced": count if replace_all else 1}

    def append_file(self, path, content):
        target = self._safe_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8", newline="") as f:
            f.write(content)
        return {"ok": True, "path": str(target.relative_to(self.workspace))}

    def make_directory(self, path):
        target = self._safe_path(path)
        target.mkdir(parents=True, exist_ok=True)
        return {"ok": True, "path": str(target.relative_to(self.workspace))}

    def delete_file(self, path):
        target = self._safe_path(path)
        if not target.is_file():
            return {"ok": False, "error": f"No existe el archivo: {path}"}
        target.unlink()
        return {"ok": True, "deleted": str(target.relative_to(self.workspace))}

    def validate_python(self, path):
        target = self._safe_path(path)
        if target.suffix.lower() != ".py":
            return {"ok": False, "error": "validate_python solo acepta .py"}
        if not target.is_file():
            return {"ok": False, "error": f"No existe el archivo: {path}"}
        try:
            subprocess.run(
                [sys.executable, "-m", "py_compile", str(target)],
                cwd=str(self.workspace), capture_output=True, text=True, timeout=10, check=True
            )
            return {"ok": True, "valid": True, "path": str(target.relative_to(self.workspace))}
        except subprocess.CalledProcessError as exc:
            return {"ok": True, "valid": False, "stdout": exc.stdout[-6000:], "stderr": exc.stderr[-6000:]}
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": "La validacion supero 10 segundos."}

    def run_python(self, path, timeout=15):
        target = self._safe_path(path)
        if target.suffix.lower() != ".py":
            return {"ok": False, "error": "run_python solo acepta .py"}
        if not target.is_file():
            return {"ok": False, "error": f"No existe el archivo: {path}"}
        timeout = max(1, min(int(timeout), 30))
        try:
            completed = subprocess.run(
                [sys.executable, str(target)], cwd=str(self.workspace),
                capture_output=True, text=True, timeout=timeout
            )
            return {"ok": True, "returncode": completed.returncode,
                    "stdout": completed.stdout[-12000:], "stderr": completed.stderr[-12000:]}
        except subprocess.TimeoutExpired as exc:
            return {"ok": False, "error": f"La ejecucion supero {timeout}s",
                    "stdout": (exc.stdout or "")[-4000:], "stderr": (exc.stderr or "")[-4000:]}

    def execute_tool(self, name, args):
        functions = {
            "list_files": self.list_files, "read_file": self.read_file,
            "write_file": self.write_file, "replace_in_file": self.replace_in_file,
            "append_file": self.append_file, "make_directory": self.make_directory,
            "delete_file": self.delete_file, "validate_python": self.validate_python,
            "run_python": self.run_python,
        }
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
        if isinstance(item, dict):
            return item
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
            self.messages.append({
                "type": "function_call_output",
                "call_id": getattr(call, "call_id", getattr(call, "id", "")),
                "output": json.dumps(result, ensure_ascii=False),
            })
