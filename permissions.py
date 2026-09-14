"""Permisos conservadores para operaciones del agente."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PermissionPolicy:
    """Por defecto permite desarrollo local, pero protege operaciones sensibles."""

    allow_read: bool = True
    allow_write: bool = True
    allow_run: bool = True
    allow_delete: bool = True
    allow_install: bool = False
    allow_network: bool = False
    allow_screen_control: bool = False
    audit_log: list[dict] = field(default_factory=list)

    def check(self, action: str, detail: str = "") -> bool:
        mapping = {
            "read": self.allow_read,
            "write": self.allow_write,
            "run": self.allow_run,
            "delete": self.allow_delete,
            "install": self.allow_install,
            "network": self.allow_network,
            "screen": self.allow_screen_control,
        }
        allowed = mapping.get(action, False)
        self.audit_log.append({"action": action, "allowed": allowed, "detail": detail})
        return allowed

    def as_dict(self) -> dict:
        return {
            "allow_read": self.allow_read,
            "allow_write": self.allow_write,
            "allow_run": self.allow_run,
            "allow_delete": self.allow_delete,
            "allow_install": self.allow_install,
            "allow_network": self.allow_network,
            "allow_screen_control": self.allow_screen_control,
        }
