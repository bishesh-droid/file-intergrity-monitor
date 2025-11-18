
import unittest
from click.testing import CliRunner
from fim.cli import cli
import os
import shutil

class TestMainCli(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()
        self.test_dir = "test_cli_dir"
        os.makedirs(self.test_dir, exist_ok=True)
        self.config_path = os.path.join(self.test_dir, "config.yaml")
        self.db_path = os.path.join(self.test_dir, "fim.db")
        self.monitored_dir = os.path.join(self.test_dir, "monitored")
        os.makedirs(self.monitored_dir, exist_ok=True)

        with open(self.config_path, "w") as f:
            f.write(f"""
include:
  - {self.monitored_dir}
exclude: []
hash_algorithm: sha256
log_level: INFO
verbose_console_output: false
""")

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_init_command(self):
        result = self.runner.invoke(cli, ["init", "--config", self.config_path, "--database", self.db_path, "--force"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("FIM baseline created successfully.", result.output)
        self.assertTrue(os.path.exists(self.db_path))

    def test_status_command_no_baseline(self):
        result = self.runner.invoke(cli, ["status", "--database", self.db_path])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Baseline database not found", result.output)

    def test_status_command_with_baseline(self):
        self.runner.invoke(cli, ["init", "--config", self.config_path, "--database", self.db_path, "--force"])
        result = self.runner.invoke(cli, ["status", "--database", self.db_path])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("FIM Baseline Status", result.output)

    def test_check_command_no_baseline(self):
        result = self.runner.invoke(cli, ["check", "--config", self.config_path, "--database", self.db_path])
        self.assertEqual(result.exit_code, 1)
        self.assertIn("Baseline database not found", result.output)

    def test_check_command_no_changes(self):
        with open(os.path.join(self.monitored_dir, "file1.txt"), "w") as f:
            f.write("hello")

        self.runner.invoke(cli, ["init", "--config", self.config_path, "--database", self.db_path, "--force"])
        result = self.runner.invoke(cli, ["check", "--config", self.config_path, "--database", self.db_path])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("No integrity violations detected", result.output)

    def test_check_command_with_changes(self):
        file1_path = os.path.join(self.monitored_dir, "file1.txt")
        with open(file1_path, "w") as f:
            f.write("hello")

        self.runner.invoke(cli, ["init", "--config", self.config_path, "--database", self.db_path, "--force"])

        with open(file1_path, "w") as f:
            f.write("world")

        result = self.runner.invoke(cli, ["check", "--config", self.config_path, "--database", self.db_path])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Modified Files", result.output)

if __name__ == '__main__':
    unittest.main()
