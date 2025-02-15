import unittest
from pathlib import Path
from unittest import mock
from hashlib import sha256
from os import remove
from click.testing import CliRunner
from pygit2 import Repository
from tartufo import cli, types
from tests import helpers


class ScanLocalRepoTests(unittest.TestCase):
    @mock.patch("tartufo.commands.scan_local_repo.GitRepoScanner")
    def test_scan_exits_gracefully_on_scan_exception(
        self, mock_scanner: mock.MagicMock
    ):
        mock_scanner.return_value.scan.side_effect = types.ScanException("Scan failed!")
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli.main, ["scan-local-repo", "."])
        self.assertGreater(result.exit_code, 0)
        self.assertEqual(result.output, "Scan failed!\n")

    @unittest.skipIf(
        helpers.BROKEN_USER_PATHS, "Skipping due to truncated Windows usernames"
    )
    def test_scan_exits_gracefully_when_target_is_not_git_repo(self):
        runner = CliRunner()
        with runner.isolated_filesystem() as run_path:
            result = runner.invoke(cli.main, ["scan-local-repo", "."])
            self.assertEqual(
                str(result.exception),
                f"Repository not found at {Path(run_path).resolve()}",
            )

    def test_new_file_shows_up(self):
        file_name = "secret_1.key"
        runner = CliRunner()
        # Add file with high entropy
        secret_key = sha256(b"hello world")
        with open(file_name, "a") as file:
            file.write(secret_key.hexdigest())
        repo = Repository(".")

        # Check that tartufo picks up on newly added files
        repo.index.add("tests/data/config/" + file_name)
        repo.index.write()  # This actually writes the index to disk. Without it, the tracked file is not actually staged.
        result = runner.invoke(cli.main, ["--entropy-sensitivity", "1", "pre-commit"])
        self.assertNotEqual(result.exit_code, 0)

        # Cleanup
        repo.index.remove("tests/data/config/" + file_name)
        repo.index.write()  # This actually writes the index to disk. Without it, secret.key will not removed from the index.
        remove(file_name)

    def test_new_unstaged_file_does_not_show_up(self):
        file_name = "secret_2.key"
        runner = CliRunner()
        # Add file with high entropy
        secret_key = sha256(b"hello world")
        with open(file_name, "a") as file:
            file.write(secret_key.hexdigest())
        result = runner.invoke(cli.main, ["--entropy-sensitivity", "1", "pre-commit"])
        self.assertEqual(result.exit_code, 0)

        # Cleanup
        remove(file_name)
