import json
from pathlib import Path

import numpy as np


class MLP:
    """Red neuronal multicapa pequena, entrenable y guardable localmente."""

    def __init__(self, layer_sizes, seed=42):
        if len(layer_sizes) < 2 or any(int(x) < 1 for x in layer_sizes):
            raise ValueError("layer_sizes debe contener al menos entrada y salida")
        self.layer_sizes = [int(x) for x in layer_sizes]
        rng = np.random.default_rng(seed)
        self.weights = []
        self.biases = []
        for fan_in, fan_out in zip(self.layer_sizes[:-1], self.layer_sizes[1:]):
            self.weights.append((rng.standard_normal((fan_in, fan_out)) * np.sqrt(2.0 / fan_in)).astype(np.float64))
            self.biases.append(np.zeros((1, fan_out), dtype=np.float64))

    @staticmethod
    def _sigmoid(x):
        x = np.clip(x, -60, 60)
        return 1.0 / (1.0 + np.exp(-x))

    @staticmethod
    def _sigmoid_derivative(a):
        return a * (1.0 - a)

    def forward(self, x):
        a = np.asarray(x, dtype=np.float64)
        if a.ndim == 1:
            a = a.reshape(1, -1)
        activations = [a]
        pre_activations = []
        for i, (w, b) in enumerate(zip(self.weights, self.biases)):
            z = activations[-1] @ w + b
            pre_activations.append(z)
            if i == len(self.weights) - 1:
                a = self._sigmoid(z)
            else:
                a = np.tanh(z)
            activations.append(a)
        return activations, pre_activations

    def predict(self, x):
        return self.forward(x)[0][-1]

    def train(self, x, y, epochs=1000, learning_rate=0.05, validation_split=0.2, patience=80, seed=42):
        x = np.asarray(x, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64)
        if x.ndim != 2 or y.ndim != 2:
            raise ValueError("X e y deben ser matrices 2D")
        if len(x) != len(y):
            raise ValueError("X e y deben tener la misma cantidad de ejemplos")
        if x.shape[1] != self.layer_sizes[0] or y.shape[1] != self.layer_sizes[-1]:
            raise ValueError("Las dimensiones de X/y no coinciden con la red")

        rng = np.random.default_rng(seed)
        indices = rng.permutation(len(x))
        split = int(len(x) * (1.0 - validation_split)) if validation_split > 0 else len(x)
        split = min(max(split, 1), len(x))
        train_idx, val_idx = indices[:split], indices[split:]
        x_train, y_train = x[train_idx], y[train_idx]
        x_val, y_val = (x[val_idx], y[val_idx]) if len(val_idx) else (x_train, y_train)

        history = {"loss": [], "val_loss": [], "epoch": []}
        best = [w.copy() for w in self.weights], [b.copy() for b in self.biases]
        best_val = float("inf")
        wait = 0

        for epoch in range(1, int(epochs) + 1):
            order = rng.permutation(len(x_train))
            xb, yb = x_train[order], y_train[order]
            activations, _ = self.forward(xb)
            output = activations[-1]
            error = output - yb
            loss = float(np.mean(error ** 2))

            delta = error * self._sigmoid_derivative(output)
            grad_w = [None] * len(self.weights)
            grad_b = [None] * len(self.biases)
            for layer in range(len(self.weights) - 1, -1, -1):
                grad_w[layer] = activations[layer].T @ delta / len(xb)
                grad_b[layer] = np.mean(delta, axis=0, keepdims=True)
                if layer > 0:
                    delta = (delta @ self.weights[layer].T) * (1.0 - activations[layer] ** 2)

            for i in range(len(self.weights)):
                self.weights[i] -= learning_rate * grad_w[i]
                self.biases[i] -= learning_rate * grad_b[i]

            val_pred = self.predict(x_val)
            val_loss = float(np.mean((val_pred - y_val) ** 2))
            history["loss"].append(loss)
            history["val_loss"].append(val_loss)
            history["epoch"].append(epoch)

            if val_loss < best_val - 1e-10:
                best_val = val_loss
                best = [w.copy() for w in self.weights], [b.copy() for b in self.biases]
                wait = 0
            else:
                wait += 1
                if wait >= patience:
                    break

        self.weights, self.biases = best
        return history

    def save(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"layer_sizes": self.layer_sizes}
        arrays = {}
        for i, (w, b) in enumerate(zip(self.weights, self.biases)):
            arrays[f"w{i}"] = w
            arrays[f"b{i}"] = b
        np.savez(path, metadata=json.dumps(payload), **arrays)

    @classmethod
    def load(cls, path):
        data = np.load(path, allow_pickle=False)
        metadata = json.loads(str(data["metadata"]))
        model = cls(metadata["layer_sizes"])
        model.weights = [data[f"w{i}"].copy() for i in range(len(model.layer_sizes) - 1)]
        model.biases = [data[f"b{i}"].copy() for i in range(len(model.layer_sizes) - 1)]
        return model


def load_dataset(path):
    """Acepta JSON: {"x": [[...]], "y": [[...]]}."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "x" not in data or "y" not in data:
        raise ValueError("El dataset debe tener las claves x e y")
    return np.asarray(data["x"], dtype=np.float64), np.asarray(data["y"], dtype=np.float64)


def train_from_json(dataset_path, model_path, hidden_layers=(8, 8), epochs=1000, learning_rate=0.05, validation_split=0.2):
    x, y = load_dataset(dataset_path)
    output_size = y.shape[1]
    layers = [x.shape[1], *[int(v) for v in hidden_layers], output_size]
    model = MLP(layers)
    history = model.train(x, y, epochs=epochs, learning_rate=learning_rate, validation_split=validation_split)
    model.save(model_path)
    return {
        "model": str(model_path),
        "layers": layers,
        "examples": int(len(x)),
        "epochs_completed": len(history["epoch"]),
        "loss": history["loss"][-1],
        "validation_loss": history["val_loss"][-1],
        "history": history,
    }
