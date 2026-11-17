"""Desktop launch failures remain visible without requiring console streams."""

import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import types
import unittest
from unittest.mock import Mock, patch

import GuiMain


class GuiLauncherTests(unittest.TestCase):
    def desktop_module(self):
        return types.SimpleNamespace(run_gui=Mock(), run_gui_smoke=Mock())

    def test_normal_launch_passes_options_and_does_not_run_smoke(self):
        desktop = self.desktop_module()
        with patch.dict("sys.modules", {"desktop_ui": desktop}):
            self.assertEqual(GuiMain.main(["--name", " Tarin ", "--seed", "7", "--floors", "3"]), 0)
        desktop.run_gui.assert_called_once_with(name="Tarin", seed=7, floors=3)
        desktop.run_gui_smoke.assert_not_called()

    def test_blank_name_uses_default_name(self):
        desktop = self.desktop_module()
        with patch.dict("sys.modules", {"desktop_ui": desktop}):
            self.assertEqual(GuiMain.main(["--name", "  "]), 0)
        desktop.run_gui.assert_called_once_with(name="Adventurer", seed=None, floors=5)

    def test_windowed_startup_failure_uses_error_dialog_without_stderr(self):
        desktop = self.desktop_module()
        desktop.run_gui.side_effect = RuntimeError("display unavailable")
        showerror = Mock()
        with patch.dict("sys.modules", {"desktop_ui": desktop, "tkinter": types.SimpleNamespace(
                messagebox=types.SimpleNamespace(showerror=showerror))}), \
             patch.object(GuiMain.sys, "stderr", None):
            self.assertEqual(GuiMain.main([]), 1)
        showerror.assert_called_once_with("Catacombs of Thalinor",
                                         "The game could not start.\n\ndisplay unavailable")

    def test_smoke_success_requires_report_and_bypasses_regular_launch(self):
        desktop = self.desktop_module()
        with TemporaryDirectory() as directory:
            report_path = Path(directory) / "report.json"
            desktop.run_gui_smoke.side_effect = lambda path, **kwargs: path.write_text(
                json.dumps({"success": True, "checks": ["title_screen"]}), encoding="utf-8")
            with patch.dict("sys.modules", {"desktop_ui": desktop}):
                self.assertEqual(GuiMain.main(["--ui-smoke-report", str(report_path), "--seed", "7"]), 0)
            desktop.run_gui_smoke.assert_called_once_with(report_path, name="Adventurer", seed=7, floors=5)
        desktop.run_gui.assert_not_called()

    def test_failed_smoke_report_sets_nonzero_exit(self):
        desktop = self.desktop_module()
        with TemporaryDirectory() as directory:
            report_path = Path(directory) / "report.json"
            desktop.run_gui_smoke.side_effect = lambda path, **kwargs: path.write_text(
                json.dumps({"success": False, "checks": []}), encoding="utf-8")
            with patch.dict("sys.modules", {"desktop_ui": desktop}):
                self.assertEqual(GuiMain.main(["--ui-smoke-report", str(report_path)]), 1)

    def test_smoke_failure_writes_error_without_modal_dialog_or_console(self):
        desktop = self.desktop_module()
        desktop.run_gui_smoke.side_effect = RuntimeError("widget failed")
        with TemporaryDirectory() as directory:
            report_path = Path(directory) / "report.json"
            with patch.dict("sys.modules", {"desktop_ui": desktop}), \
                 patch.object(GuiMain, "_show_launch_error") as show_error, \
                 patch.object(GuiMain.sys, "stderr", None):
                self.assertEqual(GuiMain.main(["--ui-smoke-report", str(report_path)]), 1)
            report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertIs(report["success"], False)
        self.assertEqual(report["error"], "widget failed")
        self.assertIn("RuntimeError: widget failed", report["traceback"])
        show_error.assert_not_called()

    def test_smoke_switch_is_not_shown_in_game_help(self):
        with patch("sys.stdout", new_callable=io.StringIO) as output:
            with self.assertRaises(SystemExit) as result:
                GuiMain.main(["--help"])
        self.assertEqual(result.exception.code, 0)
        self.assertNotIn("ui-smoke-report", output.getvalue())


if __name__ == "__main__":
    unittest.main()
