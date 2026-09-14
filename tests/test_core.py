from pathlib import Path

from model_router import ModelRouter
from permissions import PermissionPolicy
from project_state import ProjectState
from validators import ProjectValidator


def test_model_router_is_local_first():
    profile = ModelRouter().choose("crear un proyecto")
    assert profile.provider == "ollama"
    assert profile.requires_api_key is False


def test_permissions_default_blocks_sensitive_operations():
    policy = PermissionPolicy()
    assert policy.check("read")
    assert policy.check("write")
    assert not policy.check("install")
    assert not policy.check("network")
    assert not policy.check("screen")


def test_project_validator_checks_json_and_files(tmp_path: Path):
    project = tmp_path / "demo"
    project.mkdir()
    (project / "package.json").write_text('{"name":"demo"}', encoding="utf-8")
    result = ProjectValidator().validate(project)
    assert result["ok"] is True
    assert result["file_count"] == 1


def test_project_state_snapshot(tmp_path: Path):
    data = tmp_path / "data"
    project = tmp_path / "project"
    project.mkdir()
    (project / "main.py").write_text("print('ok')", encoding="utf-8")
    state = ProjectState(data)
    state.set_active(project, "demo")
    snapshot = state.snapshot(project, "before_change")
    assert snapshot["ok"]
    assert Path(snapshot["path"]).is_dir()
