#!/usr/bin/env python3
"""Heroic discovery and reversible configuration against isolated library fixtures."""
import json
import asyncio
import logging
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "py_modules"))
from optiscaler import heroic, steam
from optiscaler.settings import Settings
from optiscaler.service import OptiScalerService


class HeroicTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name).resolve()
        self.root = self.home / f".var/app/{heroic.APP_ID}/config/heroic"
        self.game = self.home / "Games/A Game"
        (self.game / "Binaries/Win64").mkdir(parents=True)
        (self.game / "Binaries/Win64/Game.exe").touch()
        self.write(self.root / "legendaryConfig/legendary/installed.json", {
            "GameId": {"title": "A Game", "install_path": str(self.game), "platform": "Windows"}})
        self.meta = heroic.games(self.home)[0]["heroic"]
        self.config = self.root / "GamesConfig/GameId.json"
        self.original = {"version": "v0", "GameId": {"winePrefix": "/prefix", heroic.ENV: [
            {"key": "TEST", "value": "keep"},
            {"key": heroic.DLL, "value": "dxgi,d3d11=b;winhttp=n"}]}, "unknown": True}
        self.write(self.config, self.original)
        self.settings = Settings(self.home / "plugin/settings.json")
        self.proc = patch.object(heroic, "running", return_value=False)
        self.proc.start()
        self.addCleanup(self.proc.stop)

    @staticmethod
    def write(path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data))

    def read(self):
        return json.loads(self.config.read_text())

    def test_shortcut_formats_and_nested_executable(self):
        for uri in ('heroic://launch/legendary/GameId', 'heroic://launch/GameId',
                    'heroic://launch?appName=GameId&runner=legendary&gui=false'):
            result = steam.find_by_appid(self.home, "3000000000", '"flatpak"',
                                        str(self.home), "A Game",
                                        f'run {heroic.APP_ID} --no-gui "{uri}"')
            self.assertEqual(result["path"], str(self.game))
            self.assertEqual(result["appid"], "3000000000")
            self.assertEqual(steam.find_exe_dirs(result["path"])[0]["relative"], "Binaries/Win64")

    def test_stale_shortcut_does_not_select_launcher_or_home(self):
        self.assertIsNone(steam.find_by_appid(self.home, "3000000000", "/usr/bin/flatpak",
                          str(self.home), launch_options='run com.heroicgameslauncher.hgl heroic://launch/missing'))
        self.assertIsNone(steam.shortcut_folder("flatpak", str(self.home)))
        self.assertIsNone(steam.shortcut_folder("/usr/bin/heroic", str(self.home)))

    def test_native_gog_amazon_and_invalid_records(self):
        native = self.home / ".config/heroic"
        self.write(native / "gog_store/installed.json", {"installed": [
            {"appName": "123", "install_path": str(self.game), "platform": "windows"},
            {"appName": "linux", "install_path": str(self.game), "platform": "linux"}]})
        self.write(native / "nile_config/nile/installed.json", [{"id": "amzn1.game", "path": str(self.game)}])
        self.assertEqual({g["heroic"]["runner"] for g in heroic.games(self.home, native)}, {"gog", "nile"})
        found = heroic.resolve(self.home, "/opt/Heroic.AppImage", "heroic://launch/gog/123")
        self.assertFalse(found["heroic"]["flatpak"])
        self.write(native / "gog_store/installed.json", {"installed": "bad"})
        self.assertEqual(len(heroic.games(self.home, native)), 1)

    def test_merge_switch_proxy_and_restore(self):
        heroic.configure(self.meta, ["dxgi.dll", "dinput8.dll"], self.settings)
        result = self.read()
        self.assertEqual(result["GameId"]["winePrefix"], "/prefix")
        self.assertTrue(result["unknown"])
        self.assertEqual(heroic._dll(result["GameId"][heroic.ENV]), "d3d11=b;winhttp=n;dxgi=n,b;dinput8=n,b")
        heroic.configure(self.meta, ["winmm.dll"], self.settings)
        self.assertEqual(heroic._dll(self.read()["GameId"][heroic.ENV]), "dxgi,d3d11=b;winhttp=n;winmm=n,b")
        heroic.configure(self.meta, [], self.settings, restore=True)
        self.assertEqual(self.read(), self.original)
        self.assertFalse(self.settings.get("heroic_launch"))

    def test_inherited_environment_restored(self):
        self.write(self.config, {"GameId": {"winePrefix": "/prefix"}})
        self.write(self.root / "config.json", {"defaultSettings": {heroic.ENV: [
            {"key": "KEEP", "value": "1"}, {"key": heroic.DLL, "value": "winhttp=n"}]}})
        heroic.configure(self.meta, ["dxgi.dll"], self.settings)
        self.assertEqual(heroic._dll(self.read()["GameId"][heroic.ENV]), "winhttp=n;dxgi=n,b")
        heroic.configure(self.meta, [], self.settings, restore=True)
        self.assertNotIn(heroic.ENV, self.read()["GameId"])

    def test_other_user_changes_survive_restore(self):
        heroic.configure(self.meta, ["dxgi.dll"], self.settings)
        changed = self.read()
        changed["GameId"][heroic.ENV][0]["value"] = "changed"
        changed["GameId"]["winePrefix"] = "/other-prefix"
        self.write(self.config, changed)
        heroic.configure(self.meta, [], self.settings, restore=True)
        self.assertEqual(self.read()["GameId"][heroic.ENV][0]["value"], "changed")
        self.assertEqual(self.read()["GameId"]["winePrefix"], "/other-prefix")
        self.assertEqual(heroic._dll(self.read()["GameId"][heroic.ENV]), "dxgi,d3d11=b;winhttp=n")

    def test_conflicting_user_override_is_not_overwritten(self):
        heroic.configure(self.meta, ["dxgi.dll"], self.settings)
        changed = self.read()
        changed["GameId"][heroic.ENV][-1]["value"] = "user=n"
        self.write(self.config, changed)
        with self.assertRaisesRegex(ValueError, "changed since setup"):
            heroic.configure(self.meta, [], self.settings, restore=True)
        self.assertEqual(self.read(), changed)

    def test_running_or_malformed_config_not_modified(self):
        with patch.object(heroic, "running", return_value=True):
            with self.assertRaisesRegex(ValueError, "Close Heroic"):
                heroic.configure(self.meta, ["dxgi.dll"], self.settings)
        self.assertEqual(self.read(), self.original)
        self.config.write_text("{broken")
        with self.assertRaises(ValueError):
            heroic.configure(self.meta, ["dxgi.dll"], self.settings)
        self.assertEqual(self.config.read_text(), "{broken")

    def test_write_failure_rolls_back_journal(self):
        with patch.object(heroic, "_write", side_effect=OSError("read-only")):
            with self.assertRaises(OSError):
                heroic.configure(self.meta, ["dxgi.dll"], self.settings)
        self.assertFalse(self.settings.get("heroic_launch"))
        self.assertEqual(self.read(), self.original)

    def test_unsaved_shortcut_falls_back_to_saved_arguments(self):
        entry = {"exe": "flatpak", "launchoptions": f"run {heroic.APP_ID} heroic://launch/legendary/GameId"}
        with patch.object(steam, "shortcut_entry", return_value=(entry, None)):
            result = steam.find_by_appid(self.home, "3000000000", "flatpak", str(self.home))
            self.assertEqual(result["path"], str(self.game))

    def test_service_library_detail_and_configuration(self):
        service = OptiScalerService(Path(__file__).resolve().parents[1], self.home / "settings",
                                   self.home / "runtime", self.home, logging.getLogger("test"))
        async def check():
            libraries = await service.list_libraries()
            self.assertEqual(libraries[0]["source"], "heroic")
            listed = await service.list_all_games()
            self.assertEqual(listed[0]["name"], "A Game")
            self.assertEqual((await service.list_games(str(self.root), "heroic"))[0]["path"], str(self.game))
            detail = await service.get_game(str(self.game))
            self.assertTrue(detail["heroic"]["flatpak"])
            self.assertEqual(detail["target"], str(self.game / "Binaries/Win64"))
            result = await service.configure_heroic(str(self.game), str(self.home))
            self.assertFalse(result["ok"])
            self.assertIn("inside this game", result["error"])
            result = await service.configure_heroic(str(self.game), detail["target"])
            self.assertFalse(result["ok"])
            self.assertIn("Install OptiScaler", result["error"])
            with patch("optiscaler.service.installer.detect", return_value={"installed": True, "filename": "dxgi.dll"}), \
                    patch("optiscaler.service.reframework.status", return_value={"installed": True}):
                result = await service.configure_heroic(str(self.game), detail["target"])
            self.assertTrue(result["ok"], result)
            self.assertIn("dinput8=n,b", result["heroic"]["overrides"])
            self.assertTrue((await service.configure_heroic(str(self.game), detail["target"], True))["ok"])
            self.assertEqual(self.read(), self.original)
        asyncio.run(check())

    def test_ambiguous_install_does_not_fall_back_to_steam_settings(self):
        native = self.home / ".config/heroic"
        self.write(native / "legendaryConfig/legendary/installed.json", {
            "GameId": {"install_path": str(self.game)}})
        meta = heroic.for_path(self.home, self.game)
        self.assertTrue(meta["ambiguous"])
        self.assertIn("Multiple", heroic.status(meta, {})["error"])
        with self.assertRaisesRegex(ValueError, "Multiple"):
            heroic.configure(meta, ["dxgi.dll"], self.settings)


if __name__ == "__main__":
    unittest.main()
