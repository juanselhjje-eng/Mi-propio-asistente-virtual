import json
from pathlib import Path

from agent import Agent
from ml_engine import MLP, train_from_json


class NeuralAgent(Agent):
    """Extiende el agente de proyectos con creacion y entrenamiento de redes neuronales."""

    def _system_prompt(self):
        base = super()._system_prompt()
        return base + """

CAPA DE INTELIGENCIA Y REDES NEURONALES:
18. Cuando el usuario pida una red neuronal, no la simules: crea el dataset, la arquitectura, el entrenamiento y el modelo guardado cuando corresponda.
19. Explica y usa conceptos reales: entradas, pesos, sesgos, capas, activacion, funcion de perdida, backpropagation, epochs, learning rate y validacion.
20. Una red neuronal entrenada no debe confundirse con el propio modelo de lenguaje. El LLM decide que hacer; la red entrenada es un modelo adicional para una tarea concreta.
21. Para entrenar, usa train_neural_network cuando el dataset este preparado. No inventes resultados de entrenamiento.
22. Si una red no aprende, inspecciona dimensiones, normalizacion, etiquetas, arquitectura, learning rate y cantidad de datos antes de cambiar cosas al azar.
23. Guarda los pesos entrenados en archivos .npz para poder cargarlos despues y continuar usandolos.
24. Para aprendizaje continuo, usa datos nuevos y vuelve a entrenar un modelo existente de forma controlada. No modifiques automaticamente los pesos solo por cualquier conversacion del usuario.
25. Antes de afirmar que una red funciona, ejecuta una prueba de prediccion o inspecciona su perdida de entrenamiento/validacion.
26. Si el usuario pide que una IA "se entrene sola", implementa un ciclo medible de datos -> entrenamiento -> validacion -> guardado -> evaluacion. No llames "aprendizaje" a generar codigo aleatorio.
""".strip()

    def setup_tools(self):
        super().setup_tools()
        self.tools.extend([
            {
                "type": "function",
                "name": "train_neural_network",
                "description": "Entrena una red neuronal multicapa local con un dataset JSON y guarda sus pesos. Usa backpropagation, perdida MSE, validacion y early stopping.",
                "parameters": {"type": "object", "properties": {
                    "dataset_path": {"type": "string", "description": "JSON con x e y."},
                    "model_path": {"type": "string", "description": "Ruta del modelo .npz."},
                    "hidden_layers": {"type": "array", "items": {"type": "integer"}},
                    "epochs": {"type": "integer"},
                    "learning_rate": {"type": "number"},
                    "validation_split": {"type": "number"}
                }, "required": ["dataset_path", "model_path"], "additionalProperties": False}
            },
            {
                "type": "function",
                "name": "predict_neural_network",
                "description": "Carga una red neuronal entrenada y hace predicciones con una lista de entradas.",
                "parameters": {"type": "object", "properties": {
                    "model_path": {"type": "string"},
                    "inputs": {"type": "array"}
                }, "required": ["model_path", "inputs"], "additionalProperties": False}
            },
            {
                "type": "function",
                "name": "inspect_neural_network",
                "description": "Inspecciona la arquitectura y los pesos de un modelo neuronal guardado.",
                "parameters": {"type": "object", "properties": {
                    "model_path": {"type": "string"}
                }, "required": ["model_path"], "additionalProperties": False}
            }
        ])

    def _model_path(self, path):
        target = self._safe_path(path)
        if target.suffix.lower() != ".npz":
            raise ValueError("Los modelos neuronales deben usar extension .npz")
        return target

    def train_neural_network(self, dataset_path, model_path, hidden_layers=None, epochs=1000, learning_rate=0.05, validation_split=0.2):
        dataset = self._safe_path(dataset_path)
        model = self._model_path(model_path)
        if not dataset.is_file():
            return {"ok": False, "error": f"No existe el dataset: {dataset_path}"}
        hidden_layers = hidden_layers or [8, 8]
        hidden_layers = [max(1, min(int(v), 256)) for v in hidden_layers[:5]]
        epochs = max(1, min(int(epochs), 10000))
        learning_rate = max(0.00001, min(float(learning_rate), 1.0))
        validation_split = max(0.0, min(float(validation_split), 0.5))
        try:
            result = train_from_json(
                dataset, model, tuple(hidden_layers), epochs,
                learning_rate, validation_split
            )
            result["ok"] = True
            return result
        except Exception as exc:
            return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

    def predict_neural_network(self, model_path, inputs):
        try:
            model = MLP.load(self._model_path(model_path))
            values = model.predict(inputs)
            return {"ok": True, "predictions": values.tolist(), "layers": model.layer_sizes}
        except Exception as exc:
            return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

    def inspect_neural_network(self, model_path):
        try:
            model = MLP.load(self._model_path(model_path))
            weights = []
            for i, (w, b) in enumerate(zip(model.weights, model.biases)):
                weights.append({
                    "layer": i,
                    "weights_shape": list(w.shape),
                    "bias_shape": list(b.shape),
                    "weight_mean": float(w.mean()),
                    "weight_std": float(w.std())
                })
            return {"ok": True, "layers": model.layer_sizes, "parameters": weights}
        except Exception as exc:
            return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

    def execute_tool(self, name, args):
        neural = {
            "train_neural_network": self.train_neural_network,
            "predict_neural_network": self.predict_neural_network,
            "inspect_neural_network": self.inspect_neural_network,
        }
        if name in neural:
            try:
                return neural[name](**args)
            except Exception as exc:
                return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
        return super().execute_tool(name, args)
