import json
import os
import re
import subprocess
import sys
from pathlib import Path


class Agent:
    """Herramientas locales para construir, validar y reparar proyectos."""

    IGNORED_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules", ".mypy_cache", ".pytest_cache"}
    TEXT_LIMIT = 16000

    def __init__(self, workspace=None):
        self.workspace = Path(workspace or os.getenv("ASSISTANT_WORKSPACE") or os.getcwd()).resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.setup_tools()
        self.messages = [{"role": "system", "content": self._system_prompt()}]

    def _system_prompt(self):
        return """
Eres un agente local de programacion. Construyes proyectos reales usando herramientas.

- Inspecciona antes de modificar.
- En proyectos nuevos usa una arquitectura pequena y coherente.
- Mantén referencias entre archivos correctas.
- No inventes APIs, dependencias, assets ni resultados.
- Si el usuario pide un juego, app o pagina, crea el proyecto y no solo un ejemplo de codigo.
- Si faltan sprites, sonidos o imagenes, crea carpetas de recursos y explica exactamente donde ponerlos.
- Puedes usar placeholders generados por codigo cuando permitan probar el proyecto sin assets externos.
- Usa validate_project al terminar proyectos de varios archivos.
- Usa validate_python y run_python cuando corresponda y sea seguro.
- No ejecutes programas interactivos que esperen entrada indefinidamente.
- Repara errores basandote en los mensajes reales de las herramientas.
- No afirmes que algo funciona sin comprobarlo.
- No borres archivos salvo que sea necesario o solicitado.

El modelo de lenguaje es la inteligencia principal. No necesitas una red neuronal adicional para programar: solo usa modelos adicionales si el usuario pide explicitamente una tarea de ML.
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
            {"type": "function", "name": "list_files", "description": "Lista archivos y carpetas del workspace, ignorando carpetas pesadas.", "parameters": {"type": "object", "properties": {"directory": {"type": "string"}, "recursive": {"type": "boolean"}}, "required": [], "additionalProperties": False}},
            {"type": "function", "name": "read_file", "description": "Lee un archivo de texto existente. Devuelve una parte acotada para no llenar el contexto.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"], "additionalProperties": False}},
            {"type": "function", "name": "write_file", "description": "Crea o reemplaza un archivo completo dentro del workspace.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"], "additionalProperties": False}},
            {"type": "function", "name": "replace_in_file", "description": "Hace un reemplazo puntual en un archivo existente.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}, "replace_all": {"type": "boolean"}}, "required": ["path", "old_text", "new_text"], "additionalProperties": False}},
            {"type": "function", "name": "append_file", "description": "Agrega texto al final de un archivo.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"], "additionalProperties": False}},
            {"type": "function", "name": "make_directory", "description": "Crea una carpeta dentro del workspace.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"], "additionalProperties": False}},
            {"type": "function", "name": "delete_file", "description": "Elimina un archivo cuando sea necesario para la peticion.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"], "additionalProperties": False}},
            {"type": "function", "name": "validate_python", "description": "Comprueba la sintaxis de un .py con py_compile.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"], "additionalProperties": False}},
            {"type": "function", "name": "run_python", "description": "Ejecuta un .py no interactivo para comprobarlo. Timeout maximo 20 segundos.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "timeout": {"type": "integer"}}, "required": ["path"], "additionalProperties": False}},
            {"type": "function", "name": "validate_project", "description": "Revisa un proyecto completo: Python, JSON y referencias locales HTML/CSS/JS. Devuelve errores concretos.", "parameters": {"type": "object", "properties": {"directory": {"type": "string"}}, "required": [], "additionalProperties": False}},
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

    def write_file(self, path, content):
        target = self._safe_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        existed = target.exists()
        target.write_text(content, encoding="utf-8", newline="")
        action = "actualizado" if existed else "creado"
        return {"ok": True, "path": str(target.relative_to(self.workspace)), "action": action, "bytes": len(content.encode("utf-8"))}

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
        target.write_text(content.replace(old_text, new_text, -1 if replace_all else 1), encoding="utf-8", newline="")
        return {"ok": True, "path": str(target.relative_to(self.workspace)), "replaced": count if replace_all else 1}

    def append_file(self, path, content):
        target = self._safe_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8", newline="") as file:
            file.write(content)
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
            completed = subprocess.run([sys.executable, str(target)], cwd=self.workspace, capture_output=True, text=True, timeout=timeout)
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

        existing = {str(p.relative_to(root)).replace("\\", "/") for p in files}
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

    def execute_tool(self, name, args):
        functions = {"list_files": self.list_files, "read_file": self.read_file, "write_file": self.write_file, "replace_in_file": self.replace_in_file, "append_file": self.append_file, "make_directory": self.make_directory, "delete_file": self.delete_file, "validate_python": self.validate_python, "run_python": self.run_python, "validate_project": self.validate_project}
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
                if name == "write_file":
                    print(f"[ARCHIVO] {result['action']}: {result['path']}")
                elif name == "make_directory":
                    print(f"[CARPETA] creada: {result['path']}")
                elif name == "delete_file":
                    print(f"[ARCHIVO] eliminado: {result['deleted']}")
                elif name in {"validate_python", "validate_project"}:
                    state = "OK" if result.get("valid", True) else "ERROR"
                    print(f"[PRUEBA] {name}: {state}")
            else:
                print(f"[HERRAMIENTA] error en {name}: {result.get('error', 'desconocido')}")

            self.messages.append({
                "type": "function_call_output",
                "call_id": getattr(call, "call_id", getattr(call, "id", "")),
                "output": json.dumps(result, ensure_ascii=False),
            })
