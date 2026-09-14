import json
import os
import subprocess
import sys
from pathlib import Path


class Agent:
    """Agente local orientado a crear y modificar proyectos de software."""

    def __init__(self, workspace=None):
        self.workspace = Path(workspace or os.getenv("ASSISTANT_WORKSPACE") or os.getcwd()).resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.setup_tools()
        self.messages = [
            {
                "role": "system",
                "content": (
                    "Eres un asistente de programacion local en español. "
                    "Tu objetivo principal es convertir las peticiones del usuario en proyectos y archivos funcionales. "
                    "Puedes crear sitios HTML/CSS/JavaScript, juegos, programas Python y proyectos con multiples archivos. "
                    "Cuando el usuario pida crear algo, usa las herramientas de archivos en vez de limitarte a pegar codigo en el chat. "
                    "Primero inspecciona archivos existentes si necesitas modificarlos. Para proyectos nuevos, crea todos los archivos necesarios. "
                    "Puedes crear carpetas y ejecutar Python para comprobar errores. "
                    "No borres archivos ni reemplaces proyectos completos sin que la peticion lo justifique. "
                    "Usa rutas relativas al workspace siempre que sea posible. "
                    "Despues de usar herramientas, explica brevemente que creaste o modificaste."
                ),
            }
        ]

    def _safe_path(self, path):
        """Resuelve una ruta y evita salir del workspace."""
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
                "type": "function",
                "name": "list_files",
                "description": "Lista archivos y carpetas del workspace o de una subcarpeta.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "directory": {"type": "string", "description": "Ruta relativa al workspace. Por defecto ."},
                        "recursive": {"type": "boolean", "description": "Si true, lista tambien subcarpetas."},
                    },
                    "required": [],
                    "additionalProperties": False,
                },
            },
            {
                "type": "function",
                "name": "read_file",
                "description": "Lee un archivo de texto completo para poder analizarlo o modificarlo.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Ruta relativa al workspace."},
                    },
                    "required": ["path"],
                    "additionalProperties": False,
                },
            },
            {
                "type": "function",
                "name": "write_file",
                "description": "Crea un archivo nuevo o reemplaza completamente un archivo existente con el contenido indicado. Crea carpetas intermedias automaticamente.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Ruta relativa del archivo."},
                        "content": {"type": "string", "description": "Contenido completo del archivo."},
                    },
                    "required": ["path", "content"],
                    "additionalProperties": False,
                },
            },
            {
                "type": "function",
                "name": "replace_in_file",
                "description": "Reemplaza una parte concreta de un archivo existente. Es preferible a reescribir todo el archivo para cambios pequeños.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "old_text": {"type": "string"},
                        "new_text": {"type": "string"},
                        "replace_all": {"type": "boolean"},
                    },
                    "required": ["path", "old_text", "new_text"],
                    "additionalProperties": False,
                },
            },
            {
                "type": "function",
                "name": "append_file",
                "description": "Agrega texto al final de un archivo. Crea el archivo si no existe.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                    },
                    "required": ["path", "content"],
                    "additionalProperties": False,
                },
            },
            {
                "type": "function",
                "name": "make_directory",
                "description": "Crea una carpeta y todas sus carpetas padre necesarias.",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                    "additionalProperties": False,
                },
            },
            {
                "type": "function",
                "name": "delete_file",
                "description": "Elimina un archivo del workspace. Solo usar cuando la peticion lo requiera claramente.",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                    "additionalProperties": False,
                },
            },
            {
                "type": "function",
                "name": "run_python",
                "description": "Ejecuta un archivo Python del workspace para probarlo y devuelve stdout, stderr y codigo de salida. No usar para acciones destructivas.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Ruta del archivo .py dentro del workspace."},
                        "timeout": {"type": "integer", "description": "Tiempo maximo en segundos, entre 1 y 30."},
                    },
                    "required": ["path"],
                    "additionalProperties": False,
                },
            },
        ]

    def list_files(self, directory=".", recursive=False):
        folder = self._safe_path(directory)
        if not folder.is_dir():
            return {"error": f"No existe la carpeta: {directory}"}
        if recursive:
            entries = [str(p.relative_to(self.workspace)) for p in folder.rglob("*")]
        else:
            entries = [str(p.relative_to(self.workspace)) for p in folder.iterdir()]
        return {"workspace": str(self.workspace), "files": sorted(entries)}

    def read_file(self, path):
        target = self._safe_path(path)
        if not target.is_file():
            return {"error": f"No existe el archivo: {path}"}
        try:
            return target.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return {"error": "El archivo no es texto UTF-8. No se puede editar con read_file."}

    def write_file(self, path, content):
        target = self._safe_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="")
        return {"ok": True, "path": str(target.relative_to(self.workspace)), "bytes": len(content.encode("utf-8"))}

    def replace_in_file(self, path, old_text, new_text, replace_all=False):
        target = self._safe_path(path)
        if not target.is_file():
            return {"error": f"No existe el archivo: {path}"}
        content = target.read_text(encoding="utf-8")
        count = content.count(old_text)
        if count == 0:
            return {"error": "No se encontro old_text en el archivo."}
        if replace_all:
            updated = content.replace(old_text, new_text)
            replaced = count
        else:
            updated = content.replace(old_text, new_text, 1)
            replaced = 1
        target.write_text(updated, encoding="utf-8", newline="")
        return {"ok": True, "path": str(target.relative_to(self.workspace)), "replaced": replaced}

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
            return {"error": f"No existe el archivo: {path}"}
        target.unlink()
        return {"ok": True, "deleted": str(target.relative_to(self.workspace))}

    def run_python(self, path, timeout=15):
        target = self._safe_path(path)
        if target.suffix.lower() != ".py":
            return {"error": "run_python solo acepta archivos .py"}
        if not target.is_file():
            return {"error": f"No existe el archivo: {path}"}
        timeout = max(1, min(int(timeout), 30))
        try:
            completed = subprocess.run(
                [sys.executable, str(target)],
                cwd=str(self.workspace),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return {
                "returncode": completed.returncode,
                "stdout": completed.stdout[-12000:],
                "stderr": completed.stderr[-12000:],
            }
        except subprocess.TimeoutExpired as exc:
            return {"error": f"La ejecucion supero {timeout}s", "stdout": (exc.stdout or "")[-4000:], "stderr": (exc.stderr or "")[-4000:]}

    def execute_tool(self, name, args):
        functions = {
            "list_files": self.list_files,
            "read_file": self.read_file,
            "write_file": self.write_file,
            "replace_in_file": self.replace_in_file,
            "append_file": self.append_file,
            "make_directory": self.make_directory,
            "delete_file": self.delete_file,
            "run_python": self.run_python,
        }
        fn = functions.get(name)
        if not fn:
            return {"error": f"Herramienta no encontrada: {name}"}
        try:
            return fn(**args)
        except Exception as exc:
            return {"error": f"{type(exc).__name__}: {exc}"}

    @staticmethod
    def _dump_item(item):
        if hasattr(item, "model_dump"):
            return item.model_dump(exclude_none=True)
        if isinstance(item, dict):
            return item
        return json.loads(item.model_dump_json()) if hasattr(item, "model_dump_json") else item

    def process_response(self, response):
        """Procesa una respuesta de Responses API y devuelve (tool_calls, text)."""
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
        """Ejecuta llamadas y agrega function_call_output con el call_id correcto."""
        for call in tool_calls:
            name = getattr(call, "name", "")
            raw_args = getattr(call, "arguments", "{}")
            args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            print(f"    - Herramienta: {name}")
            print(f"    - Argumentos: {args}")
            result = self.execute_tool(name, args)
            self.messages.append(
                {
                    "type": "function_call_output",
                    "call_id": getattr(call, "call_id", getattr(call, "id", "")),
                    "output": json.dumps(result, ensure_ascii=False),
                }
            )
