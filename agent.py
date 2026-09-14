import os
import json

class Agent:
    def __init__(self): 
        self.setup_tools()
        self.messages = [
            {"role": "system", "content": "Eres un asistente demasiado util halas español" }
        ]

    def setup_tools(self):
        self.tools = [
            {
                "type": "function",
                "name": "list_files_in_dir",
                "description": "Lista los archivos en un directorio especifico por le momento es el actual.",
                "parameters":{
                    "type": "object",
                    "properties":{
                        "directory":{
                            "type": "string",
                            "description": "Directorio para listar"
                        }
                    },
                    "required": []
                }
            },
            {
                "type": "function",
                "name": "read_file",
                "description": "Lee el contenido de un archivo en una ruta espcifica",
                "parameters":{
                    "type": "object",
                    "properties":{
                        "path":{
                            "type": "string",
                            "description": "la ruta del archivo a leer"
                        }
                    },
                    "required": ["path"]
                }
            },
            {
                "type": "function",
                "name": "edit_file",
                "description": "Edita o crea los archivo segun lo pedido. Si es un archivo nuevo, prev_text puede ir vacio.",
                "parameters":{
                    "type": "object",
                    "properties":{
                        "path":{
                            "type": "string",
                            "description": "El archivo que se va a editar o crear"
                        },
                        "prev_text":{
                            "type": "string",
                            "description": "El texto que se va a buscar para reemplazar (dejar vacio si es archivo nuevo)"
                        },
                        "new_text":{
                            "type": "string",
                            "description": "El texto que reemplazara o el texto para un archivo nuevo"
                        }
                    },
                    "required": ["path", "new_text"]
                }
            }
        ]

    # Sus herramientas
    def list_files_in_dir(self, directory="."):
        print("     Herramienta llamada: list_files_in_dir")
        try:
            files = os.listdir(directory)
            return {"files": files}
        except Exception as e:
            return {"error": str(e)}

    # Herramienta que lee archivos
    def read_file(self, path):
        print("     Herramienta llamada: read_file")
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            err = f"Error al leer el archivo {path}"
            print(err)
            return err

    # Herramienta editor de archivos y creador (REPARADA)
    def edit_file(self, path, new_text, prev_text=None):
        print("     Herramienta llamada: edit_file")
        try:
            # Asegura que si la IA inventa carpetas intermedias, estas se creen automáticamente
            dir_name = os.path.dirname(path)
            if dir_name and not os.path.exists(dir_name):
                os.makedirs(dir_name)

            existed = os.path.exists(path)
            
            if existed and prev_text:
                content = self.read_file(path)
                if prev_text not in content:
                    return f"Texto {prev_text} no se encuentra en el archivo"
                content = content.replace(prev_text, new_text)
            else:
                # Si el archivo es nuevo o no se pasa un texto previo a reemplazar, toma el texto nuevo completo
                content = new_text

            # SOLUCIÓN: Guardamos físicamente los cambios en la computadora
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            
            return f"Archivo {path} guardado exitosamente."
        except Exception as e:
            err = f"Error al crear o editar archivo {path}: {str(e)}"
            print(err)
            return err
        
    def process_response(self, response):
        self.messages += response.output
        called_any_tool = False

        for output in response.output:
            if output.type == "function_call":
                called_any_tool = True
                fn_name = output.name
                
                # CORRECCIÓN: Evitamos que rompa por el error de dedo joads -> loads
                args = json.loads(output.arguments) if isinstance(output.arguments, str) else output.arguments

                print(f"    - El modelo considera llamar a la herramienta {fn_name}")
                print(f"    - Argumentos: {args}")

                # Ejecución dinámica de la herramienta correspondiente
                if fn_name == "list_files_in_dir":
                    result = self.list_files_in_dir(**args)
                elif fn_name == "read_file":
                    result = self.read_file(**args)
                elif fn_name == "edit_file":
                    result = self.edit_file(**args)
                else:
                    result = {"error": f"Herramienta {fn_name} no encontrada."}

                # SOLUCIÓN: Agregamos el resultado de la función al historial de la IA para que sepa qué pasó
                self.messages.append({
                    "role": "tool",
                    "name": fn_name,
                    "content": json.dumps(result) if isinstance(result, (dict, list)) else str(result)
                })
            
            elif output.type == "message":
                 reply = "\n".join(part.text for part in output.content)
                 print(f"Asistente: {reply}")    

        # Retornamos si se llamó a alguna función para que el while True del main.py sepa si seguir iterando
        return called_any_tool