"""Heroic library discovery and reversible per-game Wine DLL overrides.

Formats verified against Heroic 3934a83 (game_config.ts and storeManagers).
Never execute shortcut text or infer a game directory from the launcher binary.
"""

import copy
import json
import os
import re
import tempfile
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

APP_ID = "com.heroicgameslauncher.hgl"
ENV = "enviromentOptions"  # Heroic's on-disk spelling
DLL = "WINEDLLOVERRIDES"


def read_json(path, fallback=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return fallback


def roots(home):
    home = Path(home)
    return [p for p in (home / ".config/heroic",
                       home / f".var/app/{APP_ID}/config/heroic") if p.is_dir()]


def games(home, root=None):
    result = []
    for config in roots(home):
        if root is not None and config != Path(root):
            continue
        epic = read_json(config / "legendaryConfig/legendary/installed.json", {})
        # Older Heroic versions used Legendary's sibling config directory.
        if not epic:
            epic = read_json(config.parent / "legendary/installed.json", {})
        gog = read_json(config / "gog_store/installed.json", {})
        nile = read_json(config / "nile_config/nile/installed.json", [])
        records = [("legendary", str(key), value) for key, value in epic.items()] \
            if isinstance(epic, dict) else []
        if isinstance(gog, dict) and isinstance(gog.get("installed"), list):
            records += [("gog", str(v.get("appName", "")), v)
                        for v in gog["installed"] if isinstance(v, dict)]
        if isinstance(nile, list):
            records += [("nile", str(v.get("id", "")), v)
                        for v in nile if isinstance(v, dict)]
        for runner, app_name, record in records:
            if not isinstance(record, dict) or not re.fullmatch(r"[\w.-]+", app_name):
                continue
            platform = str(record.get("platform", "windows")).lower()
            if platform not in ("windows", "win32", "win64"):
                continue
            path = record.get("install_path") or record.get("path")
            if not isinstance(path, str) or not Path(path).is_absolute() or not Path(path).is_dir():
                continue
            result.append({
                "appid": None, "name": record.get("title") or Path(path).name,
                "path": str(Path(path).resolve()), "source": "heroic", "size_on_disk": 0,
                "heroic": {"runner": runner, "app_name": app_name,
                           "config_root": str(config), "flatpak": APP_ID in str(config)},
            })
    return result


def is_launcher(exe, options=""):
    text = f"{exe or ''} {options or ''}"
    binary = Path((exe or "").strip().strip('"')).name.lower()
    return "heroic://" in text or APP_ID in text or binary in ("heroic", "heroic.exe") \
        or ("heroic" in binary and binary.endswith(".appimage"))


def resolve(home, exe, options):
    match = re.search(r"heroic://launch[^\s\"']*", f"{exe or ''} {options or ''}")
    if not match:
        return None
    try:
        url = urlsplit(match.group())
    except ValueError:
        return None
    query = parse_qs(url.query)
    parts = [unquote(p) for p in url.path.split("/") if p]
    app_name = query.get("appName", [None])[0]
    runner = query.get("runner", [None])[0]
    if not app_name and parts:
        app_name = parts[-1]
        runner = parts[0] if len(parts) == 2 else None
    flatpak = APP_ID in f"{exe or ''} {options or ''}" or \
        Path((exe or "").strip().strip('"')).name == "flatpak"
    matches = [g for g in games(home) if g["heroic"]["app_name"] == app_name
               and (not runner or g["heroic"]["runner"] == runner)
               and g["heroic"]["flatpak"] == flatpak]
    return matches[0] if len(matches) == 1 else None


def for_path(home, path):
    matches = [g for g in games(home) if g["path"] == str(Path(path).resolve())]
    if len(matches) > 1:
        return {**matches[0]["heroic"], "ambiguous": True}
    return matches[0]["heroic"] if matches else None


def _config(meta):
    path = Path(meta["config_root"]) / "GamesConfig" / (meta["app_name"] + ".json")
    data = read_json(path, {}) if not path.exists() else read_json(path)
    if not isinstance(data, dict) or data.get("version", "v0") not in ("v0", "v0.1"):
        raise ValueError("Heroic's game settings could not be read. Open the game in Heroic first.")
    game = data.get(meta["app_name"], {})
    if not isinstance(game, dict):
        raise ValueError("Unsupported Heroic game settings.")
    data[meta["app_name"]] = game
    defaults_path = Path(meta["config_root"]) / "config.json"
    defaults = read_json(defaults_path) if defaults_path.exists() else {}
    if not isinstance(defaults, dict) or not isinstance(defaults.get("defaultSettings", {}), dict):
        raise ValueError("Heroic's default settings could not be read.")
    effective = game.get(ENV, defaults.get("defaultSettings", {}).get(ENV, []))
    if not isinstance(effective, list) or any(not isinstance(e, dict)
            or not isinstance(e.get("key"), str) or not isinstance(e.get("value"), str)
            for e in effective):
        raise ValueError("Unsupported Heroic environment variables.")
    if sum(e["key"] == DLL for e in effective) > 1:
        raise ValueError("Remove duplicate WINEDLLOVERRIDES entries in Heroic first.")
    return path, data, game, effective


def _dll(env):
    return next((e["value"] for e in env if e["key"] == DLL), "")


def key(meta):
    return str(Path(meta["config_root"]) / "GamesConfig" / (meta["app_name"] + ".json"))


def status(meta, records):
    try:
        if meta.get("ambiguous"):
            raise ValueError("Multiple Heroic installations manage this folder. Configure DLL overrides in Heroic manually.")
        _, _, _, env = _config(meta)
        record = records.get(key(meta))
        if record and _dll(env) != record["written"]:
            raise ValueError("Heroic's DLL overrides changed since setup. Check them in Heroic before restoring.")
        return {**meta, "overrides": _dll(env), "managed": key(meta) in records, "error": None}
    except ValueError as exc:
        return {**meta, "overrides": "", "managed": key(meta) in records, "error": str(exc)}


def running(proc=Path("/proc")):
    # Heroic caches settings and can overwrite external changes on exit.
    for path in proc.glob("[0-9]*/cmdline"):
        try:
            args = path.read_bytes().decode(errors="replace").split("\0")
        except OSError:
            continue
        if any(is_launcher(arg) or "/heroic/" in arg.lower() for arg in args):
            return True
    return False


def _write(path, data):
    if not path.parent.exists():
        owner = path.parent.parent.stat()
        path.parent.mkdir()
        os.chown(path.parent, owner.st_uid, owner.st_gid)
    fd, temp = tempfile.mkstemp(prefix=".optiscaler-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, indent=2)
            stream.write("\n")
        if path.exists():
            os.chmod(temp, path.stat().st_mode & 0o777)
            os.chown(temp, path.stat().st_uid, path.stat().st_gid)
        else:
            os.chown(temp, path.parent.stat().st_uid, path.parent.stat().st_gid)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def configure(meta, filenames, settings, restore=False):
    """Only modify the DLL variable; journal the original before touching Heroic."""
    if meta.get("ambiguous"):
        raise ValueError("Multiple Heroic installations manage this folder. Configure DLL overrides in Heroic manually.")
    if running():
        raise ValueError("Close Heroic completely (including its tray icon) and the game, then try again.")
    path, data, game, env = _config(meta)
    records = copy.deepcopy(settings.get("heroic_launch", {}))
    record = records.get(key(meta))
    if record and _dll(env) != record["written"]:
        raise ValueError("Heroic's DLL overrides changed since setup. Restore them in Heroic before retrying.")
    if restore and not record:
        return status(meta, records)
    original = record["original"] if record else copy.deepcopy(game.get(ENV))
    baseline = record["baseline"] if record else copy.deepcopy(env)
    other = [e for e in env if e["key"] != DLL]
    if restore:
        # Restore inheritance when the rest of the environment is unchanged.
        if other == [e for e in baseline if e["key"] != DLL]:
            if original is None:
                game.pop(ENV, None)
            else:
                game[ENV] = original
        else:
            game[ENV] = other + [e for e in (baseline if original is None else original) if e["key"] == DLL]
        _write(path, data)
        del records[key(meta)]
        settings.set("heroic_launch", records)
    else:
        stems = [Path(f).stem.lower() for f in filenames if f.lower().endswith(".dll")]
        if not stems:
            raise ValueError("This installation needs no Wine DLL override.")
        # Split combined assignments (dxgi,d3d11=b) so unrelated overrides survive.
        assignments = []
        for part in _dll(baseline).strip('"\'').split(";"):
            if not part.strip():
                continue
            names, sep, value = part.partition("=")
            if not sep:
                raise ValueError("Heroic's existing DLL overrides are not in a supported format.")
            keep = [n.strip() for n in names.split(",") if n.strip().lower() not in stems]
            if keep:
                assignments.append(f'{",".join(keep)}={value}')
        written = ";".join(assignments + [f"{s}=n,b" for s in dict.fromkeys(stems)])
        game[ENV] = other + [{"key": DLL, "value": written}]
        records[key(meta)] = {"original": original, "baseline": baseline, "written": written}
        settings.set("heroic_launch", records)
        try:
            _write(path, data)
        except Exception:
            if record is None:
                records.pop(key(meta), None)
            else:
                records[key(meta)] = record
            settings.set("heroic_launch", records)
            raise
    return status(meta, records)
