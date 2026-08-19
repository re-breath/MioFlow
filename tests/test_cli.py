import contextlib
import io
import os
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
os.environ["MIO_HOME"] = str(REPOSITORY)

from mioflow_ref import cli  # noqa: E402


class MioCliTests(unittest.TestCase):
    def capture(self, arguments):
        output = io.StringIO()
        errors = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            status = cli.main(arguments)
        return status, output.getvalue(), errors.getvalue()

    def test_manual_catalogue_has_documented_cp2k_command(self):
        commands = {item.name: item for item in cli._manual_commands()}
        self.assertGreater(len(commands), 150)
        self.assertIn("cp2kstart", commands)
        self.assertIn("Slurm", commands["cp2kstart"].description)
        self.assertIn("physical_cores", commands["cp2kstart"].usage)

    def test_default_list_is_documented_functions_not_script_paths(self):
        status, output, errors = self.capture(["list", "cp2k"])
        self.assertEqual(status, 0)
        self.assertEqual(errors, "")
        self.assertIn("cp2kstart", output)
        self.assertIn("自动选择 Slurm", output)
        self.assertNotIn("auto/auto_vasp", output)

    def test_script_catalogue_has_description(self):
        status, output, errors = self.capture(["scripts", "Ctrl_auto"])
        self.assertEqual(status, 0)
        self.assertEqual(errors, "")
        self.assertIn("auto/auto_vasp_nep1/Ctrl_auto_vasp_to_nep1", output)
        self.assertIn("VASP→NEP", output)

    def test_every_discovered_script_has_a_useful_description(self):
        scripts = cli._discover_scripts()
        self.assertGreater(len(scripts), 90)
        self.assertTrue(all(item.description for item in scripts))
        self.assertFalse(any("暂无简述" in item.description for item in scripts))

    def test_help_does_not_execute_script(self):
        status, output, errors = self.capture(
            ["help", "auto/auto_vasp_nep1/Ctrl_auto_vasp_to_nep1"]
        )
        self.assertEqual(status, 0)
        self.assertEqual(errors, "")
        self.assertIn("独立 Shell 脚本", output)
        self.assertIn("mio run", output)

    def test_ambiguous_script_basename_is_not_silently_selected(self):
        matches = cli._resolve_scripts("plot_select_structure")
        self.assertGreater(len(matches), 1)
        status, output, errors = self.capture(["help", "plot_select_structure"])
        self.assertEqual(status, 2)
        self.assertIn("不唯一", output + errors)


if __name__ == "__main__":
    unittest.main()
