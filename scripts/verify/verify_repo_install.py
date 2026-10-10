"""Verification for repository installs: valid archives and every hostile case must be handled."""
from __future__ import annotations

import io
import json
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.plugins import installer  # noqa: E402
from app.plugins.installer import InstallError, REPO_MARKER  # noqa: E402


def make_zip(files: dict[str, str | bytes], symlink: str | None = None) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
        if symlink:
            info = zipfile.ZipInfo(symlink)
            info.external_attr = (0o120777 << 16)
            archive.writestr(info, "/etc/passwd")
    return buffer.getvalue()


def manifest(plugin_id: str, **extra) -> str:
    return json.dumps({"id": plugin_id, "name": plugin_id.title(), "version": "1.0.0", **extra})


def expect_error(callable_, text: str = "") -> None:
    try:
        callable_()
    except InstallError as exc:
        assert text in str(exc), str(exc)
        return
    raise AssertionError("expected InstallError")


assert installer.parse_repo_url("https://github.com/owner/repo") == ("owner", "repo", "HEAD")
assert installer.parse_repo_url("https://github.com/owner/repo.git") == ("owner", "repo", "HEAD")
assert installer.parse_repo_url("https://github.com/owner/repo/tree/dev") == ("owner", "repo", "dev")
for bad in ("http://github.com/o/r", "https://evil.example/o/r", "https://github.com.evil.io/o/r",
            "https://github.com/onlyowner", "file:///etc/passwd", "https://github.com/o/r/tree/../x"):
    expect_error(lambda url=bad: installer.parse_repo_url(url))

root = Path(tempfile.mkdtemp(prefix="homepanel_installer_"))
try:
    plugins = root / "plugins"
    plugins.mkdir()
    good = make_zip({
        "repo-main/plugins/hello_app/manifest.json": manifest("hello_app", enabled=True, category="apps"),
        "repo-main/plugins/hello_app/plugin.py": "class Plugin: pass\n",
        "repo-main/plugins/hello_app/__pycache__/x.pyc": b"skip",
        "repo-main/plugins/second/manifest.json": manifest("second"),
        "repo-main/plugins/second/plugin.py": "x = 1\n",
        "repo-main/README.md": "ignored",
    })
    found = installer.inspect_archive(good)
    assert sorted(item["id"] for item in found) == ["hello_app", "second"]
    installed = installer.install_archive(good, plugins, ["hello_app"], "https://github.com/o/r")
    assert installed == ["hello_app"]
    target = plugins / "hello_app"
    assert (target / "plugin.py").is_file() and (target / REPO_MARKER).is_file()
    assert not (target / "__pycache__").exists() and not (plugins / "second").exists()
    assert not [p for p in plugins.iterdir() if p.name.startswith(".install-")]
    expect_error(lambda: installer.install_archive(good, plugins, ["hello_app"], "x"), "bereits installiert")

    expect_error(lambda: installer.inspect_archive(b"not a zip"), "beschädigt")
    expect_error(lambda: installer.inspect_archive(make_zip({"a/readme.txt": "x"})), "kein HomePanel-Plugin")
    expect_error(lambda: installer.inspect_archive(make_zip({"a/manifest.json": manifest("only_manifest")})), "kein HomePanel-Plugin")
    expect_error(lambda: installer.inspect_archive(make_zip({
        "a/manifest.json": manifest("Bad-Id"), "a/plugin.py": "x"})), "kein HomePanel-Plugin")
    expect_error(lambda: installer.inspect_archive(make_zip({
        "a/manifest.json": manifest("evil"), "a/plugin.py": "x", "a/../../escape.py": "boom"})), "Unsicher")
    expect_error(lambda: installer.inspect_archive(make_zip({
        "a/manifest.json": manifest("evil"), "a/plugin.py": "x", "/abs/path.py": "boom"})), "Unsicher")
    expect_error(lambda: installer.inspect_archive(make_zip({
        "a/manifest.json": manifest("evil"), "a/plugin.py": "x"}, symlink="a/link")), "Symbolische")
    many = {f"a/f{i}.txt": "x" for i in range(installer.MAX_FILES + 1)}
    expect_error(lambda: installer.inspect_archive(make_zip(many)), "zu groß")
    assert not (root / "escape.py").exists()

    expect_error(lambda: installer.uninstall(plugins / "hello_app" / "..", plugins), "Nur aus Repositories")
    (plugins / "bundled").mkdir()
    expect_error(lambda: installer.uninstall(plugins / "bundled", plugins), "Nur aus Repositories")
    installer.uninstall(plugins / "hello_app", plugins)
    assert not (plugins / "hello_app").exists() and (plugins / "bundled").exists()
finally:
    shutil.rmtree(root, ignore_errors=True)

print("VERIFICATION PASSED")
