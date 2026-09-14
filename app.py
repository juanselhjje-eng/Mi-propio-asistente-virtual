import json
import os
import shutil
import sys
import uuid
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from runtime import run_request
from opencode_adapter import OpenCodeAdapter

try:
    from PySide6.QtCore import QObject, Qt, QThread, Signal, Slot, QEvent
    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import (
        QApplication, QComboBox, QDialog, QFormLayout, QFrame, QHBoxLayout, QLabel,
        QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMessageBox, QPushButton,
        QScrollArea, QVBoxLayout, QWidget, QTextEdit
    )
except ImportError as exc:
    raise SystemExit("Falta PySide6. Instala las dependencias con: python -m pip install -r requirements.txt") from exc

load_dotenv()

MODEL = os.getenv("OLLAMA_MODEL") or "qwen3:8b"
BASE_URL = os.getenv("OLLAMA_BASE_URL") or "http://localhost:11434/v1"
API_KEY = os.getenv("OLLAMA_API_KEY", "ollama")
APP_DIR = Path(__file__).resolve().parent
WORKSPACE = Path(os.getenv("ASSISTANT_WORKSPACE") or APP_DIR).resolve()
LEGACY_DATA_DIR = APP_DIR / ".jarvis_data"
DATA_DIR = Path(os.getenv("ASSISTANT_DATA_DIR") or (APP_DIR / ".milo_data"))
if not DATA_DIR.exists() and LEGACY_DATA_DIR.exists():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for old_file in LEGACY_DATA_DIR.glob("*.json"):
        shutil.copy2(old_file, DATA_DIR / old_file.name)
DATA_DIR.mkdir(parents=True, exist_ok=True)
CONVERSATIONS_FILE = DATA_DIR / "conversations.json"
SETTINGS_FILE = DATA_DIR / "settings.json"
DEFAULT_SETTINGS = {"language": "Español", "personality": "Preciso", "accent": "#2563EB"}


def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default.copy() if isinstance(default, dict) else default


def save_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


class AssistantWorker(QObject):
    finished = Signal(str, str)
    error = Signal(str)
    progress = Signal(str)

    def __init__(self, history, request, settings):
        super().__init__()
        self.history = history
        self.request = request
        self.settings = settings

    @Slot()
    def run(self):
        try:
            answer, mode = run_request(
                history=self.history,
                request=self.request,
                settings=self.settings,
                workspace=WORKSPACE,
                model=MODEL,
                base_url=BASE_URL,
                api_key=API_KEY,
                progress=self.progress.emit,
                tool_result=self._tool_result,
            )
            self.finished.emit(answer, mode)
        except Exception as exc:
            self.error.emit(f"{type(exc).__name__}: {exc}")

    def _tool_result(self, message, result):
        state = "OK" if result.get("ok") else "ERROR"
        self.progress.emit(f"{state} · {message}")


class MessageBubble(QFrame):
    def __init__(self, role, text, accent):
        super().__init__()
        self.setObjectName("userBubble" if role == "user" else "assistantBubble")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        title = QLabel("Tú" if role == "user" else "Milo")
        title.setObjectName("messageTitle")
        body = QLabel(text)
        body.setWordWrap(True)
        body.setTextInteractionFlags(Qt.TextSelectableByMouse)
        body.setObjectName("messageBody")
        layout.addWidget(title)
        layout.addWidget(body)
        self.setStyleSheet(
            f"#userBubble {{ background:#EFF6FF; border:1px solid #DBEAFE; border-radius:16px; }}"
            f"#assistantBubble {{ background:#FFFFFF; border:1px solid #E5E7EB; border-radius:16px; }}"
            f"#messageTitle {{ color:{accent}; font-weight:700; }} #messageBody {{ color:#172033; font-size:14px; }}"
        )


class SettingsDialog(QDialog):
    changed = Signal(dict)

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuración")
        self.setMinimumWidth(430)
        self.settings = settings.copy()
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.language = QComboBox(); self.language.addItems(["Español", "English"]); self.language.setCurrentText(self.settings.get("language", "Español"))
        self.personality = QComboBox(); self.personality.addItems(["Preciso", "Creativo", "Técnico", "Directo"]); self.personality.setCurrentText(self.settings.get("personality", "Preciso"))
        self.accent = QComboBox(); self.accent.addItems(["#2563EB", "#0EA5E9", "#1D4ED8", "#0284C7"]); self.accent.setCurrentText(self.settings.get("accent", "#2563EB"))
        form.addRow("Idioma", self.language); form.addRow("Personalidad", self.personality); form.addRow("Color", self.accent)
        layout.addLayout(form)
        note = QLabel("Milo decide automáticamente si una petición es conversación general o trabajo de desarrollo.")
        note.setWordWrap(True); layout.addWidget(note)
        save = QPushButton("Guardar configuración"); save.clicked.connect(self.accept); layout.addWidget(save)

    def accept(self):
        self.settings.update(language=self.language.currentText(), personality=self.personality.currentText(), accent=self.accent.currentText())
        self.changed.emit(self.settings)
        super().accept()


class AssistantWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Milo · Local Assistant Hub")
        self.resize(1440, 880)
        self.settings = load_json(SETTINGS_FILE, DEFAULT_SETTINGS)
        self.conversations = load_json(CONVERSATIONS_FILE, {})
        self.current_id = None
        self.thread = None
        self.worker = None
        self.build_ui()
        self.apply_theme()
        self.new_conversation()

    def build_ui(self):
        root = QWidget(); root.setObjectName("root")
        main = QHBoxLayout(root); main.setContentsMargins(0, 0, 0, 0); main.setSpacing(0)

        sidebar = QFrame(); sidebar.setObjectName("sidebar"); sidebar.setFixedWidth(285)
        side = QVBoxLayout(sidebar); side.setContentsMargins(14, 16, 14, 14)
        brand = QLabel("MILO"); brand.setObjectName("brand"); side.addWidget(brand)
        sub = QLabel("LOCAL ASSISTANT HUB"); sub.setObjectName("brandSub"); side.addWidget(sub); side.addSpacing(14)
        new_btn = QPushButton("＋  Nueva conversación"); new_btn.clicked.connect(self.new_conversation); new_btn.setObjectName("newChat"); side.addWidget(new_btn)
        search = QLineEdit(); search.setPlaceholderText("Buscar conversaciones…"); search.textChanged.connect(self.filter_history); side.addWidget(search)
        self.history_list = QListWidget(); self.history_list.itemClicked.connect(self.select_conversation); side.addWidget(self.history_list, 1)
        settings_btn = QPushButton("⚙  Configuración"); settings_btn.clicked.connect(self.open_settings); settings_btn.setObjectName("sideButton"); side.addWidget(settings_btn)
        opencode = OpenCodeAdapter(WORKSPACE)
        oc_state = "disponible" if opencode.available else "opcional · no instalado"
        status = QLabel(f"●  Ollama · {MODEL}\n●  OpenCode · {oc_state}"); status.setObjectName("status"); side.addWidget(status)
        main.addWidget(sidebar)

        center = QWidget(); center_layout = QVBoxLayout(center); center_layout.setContentsMargins(0, 0, 0, 0); center_layout.setSpacing(0)
        top = QFrame(); top.setObjectName("topbar"); top.setFixedHeight(64)
        top_l = QHBoxLayout(top); top_l.setContentsMargins(24, 10, 24, 10)
        self.chat_title = QLabel("Nueva conversación"); self.chat_title.setObjectName("chatTitle"); top_l.addWidget(self.chat_title); top_l.addStretch()
        self.mode_label = QLabel("General"); self.mode_label.setObjectName("modeChip"); top_l.addWidget(self.mode_label)
        center_layout.addWidget(top)

        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True); self.scroll.setFrameShape(QFrame.NoFrame)
        self.messages_widget = QWidget(); self.messages_layout = QVBoxLayout(self.messages_widget)
        self.messages_layout.setContentsMargins(40, 28, 40, 28); self.messages_layout.setSpacing(14); self.messages_layout.addStretch()
        self.scroll.setWidget(self.messages_widget); center_layout.addWidget(self.scroll, 1)

        composer = QFrame(); composer.setObjectName("composer"); cl = QVBoxLayout(composer); cl.setContentsMargins(24, 12, 24, 16)
        self.prompt = QTextEdit(); self.prompt.setPlaceholderText("Escribe lo que quieras… hablar, preguntar, crear o corregir."); self.prompt.setFixedHeight(92); self.prompt.installEventFilter(self); cl.addWidget(self.prompt)
        row = QHBoxLayout(); hint = QLabel("Enter para enviar · Shift+Enter para nueva línea"); hint.setObjectName("muted"); row.addWidget(hint); row.addStretch()
        self.send = QPushButton("Enviar  ↵"); self.send.setObjectName("send"); self.send.clicked.connect(self.send_prompt); row.addWidget(self.send); cl.addLayout(row)
        center_layout.addWidget(composer); main.addWidget(center, 1)

        inspector = QFrame(); inspector.setObjectName("inspector"); inspector.setFixedWidth(310)
        il = QVBoxLayout(inspector); il.setContentsMargins(16, 18, 16, 18)
        il.addWidget(QLabel("Centro de actividad", objectName="panelTitle"))
        self.project_status = QLabel("Listo"); self.project_status.setObjectName("statusCard"); self.project_status.setWordWrap(True); il.addWidget(self.project_status); il.addSpacing(12)
        il.addWidget(QLabel("ACTIVIDAD", objectName="section"))
        self.activity = QListWidget(); il.addWidget(self.activity, 1)
        il.addWidget(QLabel("WORKSPACE", objectName="section"))
        workspace_label = QLabel(str(WORKSPACE)); workspace_label.setObjectName("visionCard"); workspace_label.setWordWrap(True); il.addWidget(workspace_label)
        il.addWidget(QLabel("CAPACIDADES", objectName="section"))
        capabilities = QLabel("Conversación general\nDesarrollo de software\nProyectos multiarchivo\nValidación y reparación\nOllama local")
        capabilities.setObjectName("visionCard"); capabilities.setWordWrap(True); il.addWidget(capabilities)
        main.addWidget(inspector)
        self.setCentralWidget(root)

    def eventFilter(self, obj, event):
        if obj is self.prompt and event.type() == QEvent.KeyPress and event.key() in (Qt.Key_Return, Qt.Key_Enter) and not (event.modifiers() & Qt.ShiftModifier):
            self.send_prompt(); return True
        return super().eventFilter(obj, event)

    def apply_theme(self):
        accent = self.settings.get("accent", DEFAULT_SETTINGS["accent"])
        self.setStyleSheet(f"""
        QWidget {{ font-family: Segoe UI; }} #root {{ background:#F8FAFC; }}
        #sidebar {{ background:#F1F5F9; border-right:1px solid #E2E8F0; }}
        #brand {{ font-size:25px; font-weight:800; color:{accent}; }} #brandSub {{ font-size:10px; letter-spacing:2px; color:#64748B; }}
        QPushButton {{ border:1px solid #D7E0EC; border-radius:10px; padding:10px 14px; background:white; color:#172033; font-weight:600; }}
        QPushButton:hover {{ border-color:{accent}; background:#EFF6FF; }} #newChat {{ background:{accent}; color:white; border:none; }} #newChat:hover {{ background:#1D4ED8; }} #sideButton {{ text-align:left; }}
        QLineEdit, QTextEdit, QComboBox {{ background:white; border:1px solid #D9E2EF; border-radius:10px; padding:9px; color:#172033; }}
        QLineEdit:focus, QTextEdit:focus {{ border:1px solid {accent}; }}
        QListWidget {{ background:transparent; border:none; outline:none; }} QListWidget::item {{ padding:10px; border-radius:9px; color:#334155; }} QListWidget::item:selected {{ background:#DBEAFE; color:#1D4ED8; }}
        #topbar {{ background:white; border-bottom:1px solid #E2E8F0; }} #chatTitle {{ font-size:16px; font-weight:700; color:#172033; }}
        #composer {{ background:#F8FAFC; }} #send {{ background:{accent}; color:white; border:none; min-width:110px; }}
        #inspector {{ background:white; border-left:1px solid #E2E8F0; }} #panelTitle {{ font-size:16px; font-weight:700; color:#172033; }}
        #section {{ font-size:10px; font-weight:800; letter-spacing:1.5px; color:#64748B; }}
        #statusCard, #visionCard {{ background:#F8FAFC; border:1px solid #E2E8F0; border-radius:12px; padding:12px; color:#334155; }}
        #status {{ color:#16A34A; font-size:11px; }} #muted {{ color:#64748B; font-size:11px; }}
        #modeChip {{ background:#EFF6FF; color:{accent}; border:1px solid #DBEAFE; border-radius:12px; padding:7px 11px; font-size:11px; font-weight:700; }}
        """)

    def new_conversation(self):
        cid = uuid.uuid4().hex[:10]
        self.conversations[cid] = {"title": "Nueva conversación", "messages": [], "updated": datetime.now().isoformat()}
        self.current_id = cid; self.save_state(); self.refresh_history(); self.render_messages(); self.chat_title.setText("Nueva conversación")
        self.mode_label.setText("General"); self.prompt.clear(); self.project_status.setText("Listo"); self.activity.clear()

    def save_state(self):
        save_json(CONVERSATIONS_FILE, self.conversations); save_json(SETTINGS_FILE, self.settings)

    def refresh_history(self, filter_text=""):
        self.history_list.clear()
        items = sorted(self.conversations.items(), key=lambda kv: kv[1].get("updated", ""), reverse=True)
        for cid, data in items:
            title = data.get("title", "Nueva conversación")
            if filter_text.lower() not in title.lower(): continue
            item = QListWidgetItem(title); item.setData(Qt.UserRole, cid); self.history_list.addItem(item)

    def filter_history(self, text): self.refresh_history(text)

    def select_conversation(self, item):
        self.current_id = item.data(Qt.UserRole); data = self.conversations[self.current_id]
        self.chat_title.setText(data.get("title", "Conversación")); self.render_messages()

    def render_messages(self):
        while self.messages_layout.count() > 1:
            item = self.messages_layout.takeAt(0); widget = item.widget()
            if widget: widget.deleteLater()
        for message in self.conversations.get(self.current_id, {}).get("messages", []):
            bubble = MessageBubble(message["role"], message["content"], self.settings.get("accent", DEFAULT_SETTINGS["accent"]))
            self.messages_layout.insertWidget(self.messages_layout.count() - 1, bubble)
        self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().maximum())

    def send_prompt(self):
        if self.thread and self.thread.isRunning(): return
        text = self.prompt.toPlainText().strip()
        if not text or not self.current_id: return
        data = self.conversations[self.current_id]
        if not data["messages"]: data["title"] = text[:42] + ("…" if len(text) > 42 else "")
        data["messages"].append({"role": "user", "content": text}); data["updated"] = datetime.now().isoformat()
        self.save_state(); self.refresh_history(); self.render_messages(); self.prompt.clear()
        self.send.setEnabled(False); self.send.setText("Pensando…"); self.project_status.setText("Milo está procesando la petición…"); self.activity.clear()
        history = data["messages"][:-1]
        self.thread = QThread(); self.worker = AssistantWorker(history, text, self.settings.copy()); self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run); self.worker.progress.connect(self.on_progress); self.worker.finished.connect(self.on_finished); self.worker.error.connect(self.on_error); self.thread.start()

    @Slot(str)
    def on_progress(self, message):
        self.activity.addItem(message); self.activity.scrollToBottom()
        if "Modo desarrollo" in message: self.mode_label.setText("Desarrollo")
        elif "Conversación general" in message: self.mode_label.setText("General")

    def on_finished(self, answer, mode):
        data = self.conversations[self.current_id]; data["messages"].append({"role": "assistant", "content": answer}); data["updated"] = datetime.now().isoformat()
        self.save_state(); self.mode_label.setText(mode); self.activity.addItem("✓ Respuesta terminada"); self.project_status.setText("Listo"); self.render_messages(); self.finish_worker()

    def on_error(self, error):
        self.activity.addItem("✕ ERROR · " + error); self.project_status.setText("Milo no pudo completar la petición."); self.finish_worker(); QMessageBox.warning(self, "Error de Milo", error)

    def finish_worker(self):
        self.send.setEnabled(True); self.send.setText("Enviar  ↵")
        if self.thread:
            self.thread.quit(); self.thread.wait(1000)
        self.worker = None; self.thread = None

    def open_settings(self):
        dialog = SettingsDialog(self.settings, self); dialog.changed.connect(self.update_settings); dialog.exec()

    def update_settings(self, settings):
        self.settings = settings; self.save_state(); self.apply_theme(); self.render_messages()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Milo · Local Assistant Hub")
    app.setFont(QFont("Segoe UI", 10))
    window = AssistantWindow(); window.show()
    return app.exec()


if __name__ == "__main__":
    main()
