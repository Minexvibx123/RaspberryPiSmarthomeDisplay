"""Install plugin apps from a GitHub repository archive.

Plugins are ordinary Python code that runs with the panel's permissions, so this module only
downloads, validates and unpacks them (never imports anything) and leaves them disabled.
"""
from __future__ import annotations

import io
import json
import re
import shutil
import tempfile
import time
import zipfile
from pathlib import Path
from urllib.parse import urlparse

import requests

from app.plugins.api import PluginManifest

REPO_MARKER = ".homepanel-repo"
MAX_DOWNLOAD = 25 * 1024 * 1024
MAX_UNPACKED = 60 * 1024 * 1024
MAX_FILES = 800
_ID = re.compile(r"[a-z][a-z0-9_]{1,39}")
_NAME = re.compile(r"[A-Za-z0-9_.-]{1,100}")
_TRUSTED_HOSTS = ("github.com", "codeload.github.com")
_SKIPPED = ("__pycache__/", ".git/", ".github/")


class InstallError(Exception):
    """A user-presentable reason why a repository could not be installed."""


def _safe_name(value: str) -> bool:
    return bool(_NAME.fullmatch(value)) and not value.startswith(".") and ".." not in value


def parse_repo_url(url: str) -> tuple[str, str, str]:
    parsed = urlparse(url.strip())
    if parsed.scheme != "https" or (parsed.hostname or "").lower() not in ("github.com", "www.github.com"):
        raise InstallError("Es werden nur https-Adressen von github.com unterstützt.")
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) < 2:
        raise InstallError("Bitte eine Repository-Adresse wie https://github.com/benutzer/repo angeben.")
    owner, repo = parts[0], parts[1].removesuffix(".git")
    ref = parts[3] if len(parts) >= 4 and parts[2] == "tree" else "HEAD"
    if not all(_safe_name(part) for part in (owner, repo, ref)):
        raise InstallError("Die Repository-Adresse enthält ungültige Zeichen.")
    return owner, repo, ref


def download_archive(url: str) -> bytes:
    owner, repo, ref = parse_repo_url(url)
    archive = f"https://github.com/{owner}/{repo}/archive/{ref}.zip"
    try:
        with requests.get(archive, stream=True, timeout=(6, 25), allow_redirects=True) as response:
            if (urlparse(response.url).hostname or "") not in _TRUSTED_HOSTS:
                raise InstallError("Die Weiterleitung führt zu einem nicht vertrauenswürdigen Server.")
            if response.status_code == 404:
                raise InstallError("Repository oder Branch nicht gefunden (ist es öffentlich?).")
            response.raise_for_status()
            data = bytearray()
            for chunk in response.iter_content(65536):
                data.extend(chunk)
                if len(data) > MAX_DOWNLOAD:
                    raise InstallError("Das Repository ist größer als 25 MB.")
            return bytes(data)
    except requests.RequestException as exc:
        raise InstallError(f"Download fehlgeschlagen: {exc}") from exc


def _validated_members(archive: zipfile.ZipFile) -> list[zipfile.ZipInfo]:
    members = archive.infolist()
    if len(members) > MAX_FILES or sum(m.file_size for m in members) > MAX_UNPACKED:
        raise InstallError("Das Archiv ist zu groß oder enthält zu viele Dateien.")
    for member in members:
        name = member.filename
        if name.startswith(("/", "\\")) or "\\" in name or re.match(r"^[A-Za-z]:", name) \
                or ".." in Path(name).parts:
            raise InstallError(f"Unsicherer Dateipfad im Archiv: {name}")
        if ((member.external_attr >> 16) & 0o170000) == 0o120000:
            raise InstallError(f"Symbolische Verknüpfungen sind nicht erlaubt: {name}")
    return members


def inspect_archive(data: bytes) -> list[dict]:
    """Return the installable plugins inside an archive without writing anything."""
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise InstallError("Das heruntergeladene Archiv ist beschädigt.") from exc
    with archive:
        names = {m.filename for m in _validated_members(archive)}
        found = []
        for name in sorted(names):
            if name.rsplit("/", 1)[-1] != "manifest.json":
                continue
            prefix = name[: -len("manifest.json")]
            if prefix.count("/") > 3 or f"{prefix}plugin.py" not in names:
                continue
            try:
                manifest = PluginManifest.from_dict(json.loads(archive.read(name).decode("utf-8")))
                manifest.validate()
            except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
                continue
            if _ID.fullmatch(manifest.id):
                found.append({"id": manifest.id, "name": manifest.name, "version": manifest.version,
                              "author": manifest.author, "description": manifest.description, "prefix": prefix})
        if not found:
            raise InstallError("Im Repository wurde kein HomePanel-Plugin gefunden "
                               "(erwartet: Ordner mit manifest.json und plugin.py).")
        return found


def install_archive(data: bytes, plugins_root: Path, plugin_ids: list[str], source: str) -> list[str]:
    """Unpack the chosen plugins as disabled-by-default packages; returns the installed ids."""
    candidates = {c["id"]: c for c in inspect_archive(data)}
    chosen = [candidates[i] for i in plugin_ids if i in candidates]
    if not chosen:
        raise InstallError("Keines der gewählten Plugins ist im Archiv enthalten.")
    plugins_root = Path(plugins_root)
    for item in chosen:
        if (plugins_root / item["id"]).exists():
            raise InstallError(f"„{item['id']}“ ist bereits installiert. Entferne es zuerst.")
    installed = []
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for item in chosen:
            staging = Path(tempfile.mkdtemp(prefix=".install-", dir=plugins_root))
            try:
                for member in archive.infolist():
                    if not member.filename.startswith(item["prefix"]) or member.is_dir():
                        continue
                    relative = member.filename[len(item["prefix"]):]
                    if any(skip in f"/{relative}" for skip in _SKIPPED):
                        continue
                    target = (staging / relative).resolve()
                    if staging.resolve() not in target.parents:
                        raise InstallError(f"Unsicherer Dateipfad: {relative}")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(member) as source_file, open(target, "wb") as out:
                        shutil.copyfileobj(source_file, out)
                (staging / REPO_MARKER).write_text(
                    json.dumps({"source": source, "installed_at": time.time()}), encoding="utf-8")
                staging.rename(plugins_root / item["id"])
                installed.append(item["id"])
            finally:
                shutil.rmtree(staging, ignore_errors=True)
    return installed


def uninstall(plugin_dir: Path, plugins_root: Path) -> None:
    plugin_dir, plugins_root = Path(plugin_dir).resolve(), Path(plugins_root).resolve()
    if plugin_dir.parent != plugins_root or not (plugin_dir / REPO_MARKER).is_file():
        raise InstallError("Nur aus Repositories installierte Apps können gelöscht werden.")
    shutil.rmtree(plugin_dir)
