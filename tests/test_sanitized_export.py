import json
import os
from pathlib import Path

import pytest

from academic_workspace import sanitized_export
from academic_workspace.sanitized_export import export_template


def test_sanitized_export_uses_allowlist_and_excludes_private_lanes(tmp_path: Path):
    source = tmp_path / "workspace"
    (source / "academic-workspace" / "src").mkdir(parents=True)
    (source / "academic-workspace" / "src" / "example.py").write_text("print('ok')\n", encoding="utf-8")
    (source / "academic-workspace" / "ui").mkdir()
    (source / "academic-workspace" / "ui" / "server.py").write_text("print('ui')\n", encoding="utf-8")
    (source / "academic-workspace" / ".venv").mkdir()
    (source / "academic-workspace" / ".venv" / "secret.txt").write_text("secret", encoding="utf-8")
    (source / "Blackboard").mkdir()
    (source / "Blackboard" / "private.md").write_text("private", encoding="utf-8")
    output = tmp_path / "export"

    result = export_template(source, output)

    assert result.file_count > 0
    assert (output / "academic-workspace" / "src" / "example.py").is_file()
    assert (output / "academic-workspace" / "ui" / "server.py").is_file()
    assert not (output / "academic-workspace" / ".venv").exists()
    assert not (output / "Blackboard").exists()
    manifest = json.loads((output / "EXPORT-MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["private_lanes_excluded"]


def test_sanitized_export_rejects_private_markers(tmp_path: Path):
    source = tmp_path / "workspace"
    (source / "academic-workspace" / "src").mkdir(parents=True)
    bad_email = "student" + "@example.com"
    (source / "academic-workspace" / "src" / "bad.py").write_text(f"email = {bad_email!r}\n", encoding="utf-8")

    try:
        output = tmp_path / "export"
        export_template(source, output)
    except ValueError as error:
        assert "private" in str(error).lower()
        assert not output.exists()
    else:
        raise AssertionError("la exportación debía rechazar el marcador privado")


def test_sanitized_export_accepts_its_own_safe_placeholders(tmp_path: Path):
    source = tmp_path / "workspace"
    project = source / "academic-workspace"
    project.mkdir(parents=True)
    private_vault = "D:" + "/private/student/vault/material.md"
    private_profile = "C:" + "/Users/Alice/browser"
    (project / "README.md").write_text(
        f"Vault: {private_vault}\nProfile: {private_profile}\n",
        encoding="utf-8",
    )
    output = tmp_path / "export"

    export_template(source, output)

    exported = (output / "academic-workspace" / "README.md").read_text(encoding="utf-8")
    assert "D:/path/to/vault" in exported
    assert "C:/Users/<user>" in exported
    assert (output / "EXPORT-MANIFEST.json").is_file()


def test_sanitized_export_does_not_treat_token_named_variables_as_secrets(tmp_path: Path):
    source = tmp_path / "workspace"
    code = source / "academic-workspace" / "src" / "scanner.py"
    code.parent.mkdir(parents=True)
    code.write_text("user_token = '__SAFE_INTERNAL_MARKER__'\n", encoding="utf-8")

    result = export_template(source, tmp_path / "export")

    assert result.file_count > 0


def test_sanitized_export_still_rejects_assigned_secret_tokens(tmp_path: Path):
    source = tmp_path / "workspace"
    code = source / "academic-workspace" / "src" / "secret.py"
    code.parent.mkdir(parents=True)
    assigned_secret = "token" + " = " + "'actual-secret-value'\n"
    code.write_text(assigned_secret, encoding="utf-8")

    try:
        export_template(source, tmp_path / "export")
    except ValueError as error:
        assert "private" in str(error).lower()
    else:
        raise AssertionError("la exportación debía rechazar el token asignado")


@pytest.mark.parametrize("slash_count", (1, 2))
def test_sanitized_export_rejects_windows_user_paths_in_code(tmp_path: Path, slash_count: int):
    source = tmp_path / "workspace"
    code = source / "academic-workspace" / "src" / "personal.py"
    code.parent.mkdir(parents=True)
    slash = chr(92) * slash_count
    code.write_text(f"profile = r'C:{slash}Users{slash}Alice{slash}browser'\n", encoding="utf-8")

    try:
        export_template(source, tmp_path / "export")
    except ValueError as error:
        assert "private" in str(error).lower()
    else:
        raise AssertionError("la exportación debía rechazar la ruta personal")


def test_sanitized_export_rejects_symlinks_that_escape_the_project(tmp_path: Path):
    source = tmp_path / "workspace"
    root = source / "academic-workspace" / "src"
    root.mkdir(parents=True)
    outside = tmp_path / "outside.txt"
    outside.write_text("private outside\n", encoding="utf-8")
    link = root / "linked.txt"
    try:
        os.symlink(outside, link)
    except (NotImplementedError, OSError):
        pytest.skip("symlinks no disponibles en este entorno")

    with pytest.raises(ValueError, match="fuera del proyecto"):
        export_template(source, tmp_path / "export")


def test_sanitized_export_rejects_binary_ui_assets_that_cannot_be_privacy_scanned(tmp_path: Path):
    source = tmp_path / "workspace"
    asset = source / "academic-workspace" / "ui" / "icon.png"
    asset.parent.mkdir(parents=True)
    payload = bytes(range(256))
    asset.write_bytes(payload)

    with pytest.raises(ValueError, match="binario"):
        export_template(source, tmp_path / "export")


def test_sanitized_export_rejects_unknown_binary_files(tmp_path: Path):
    source = tmp_path / "workspace"
    asset = source / "academic-workspace" / "ui" / "blob.bin"
    asset.parent.mkdir(parents=True)
    asset.write_bytes(bytes(range(256)))

    with pytest.raises(ValueError, match="binario"):
        export_template(source, tmp_path / "export")


def test_sanitized_export_rejects_utf8_decodable_files_with_binary_controls(tmp_path: Path):
    source = tmp_path / "workspace"
    asset = source / "academic-workspace" / "ui" / "pixel.bmp"
    asset.parent.mkdir(parents=True)
    asset.write_bytes(b"BM" + b"\x00" * 32 + b"private metadata")

    with pytest.raises(ValueError, match="binario"):
        export_template(source, tmp_path / "export")


def test_sanitized_export_cleanup_failure_does_not_undo_committed_output(monkeypatch, tmp_path: Path):
    source = tmp_path / "workspace"
    code = source / "academic-workspace" / "src" / "example.py"
    code.parent.mkdir(parents=True)
    code.write_text("print('new')\n", encoding="utf-8")
    output = tmp_path / "export"
    output.mkdir()
    (output / "old.txt").write_text("old\n", encoding="utf-8")
    real_rmtree = sanitized_export.shutil.rmtree

    def guarded_rmtree(path, *args, **kwargs):
        if ".previous-" in str(path):
            raise PermissionError("cleanup blocked")
        return real_rmtree(path, *args, **kwargs)

    monkeypatch.setattr(sanitized_export.shutil, "rmtree", guarded_rmtree)

    result = export_template(source, output)

    assert result.output == output
    assert (output / "EXPORT-MANIFEST.json").is_file()
