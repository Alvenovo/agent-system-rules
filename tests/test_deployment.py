from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEPLOY = ROOT / "deploy-to-local.py"
VALIDATE = ROOT / "validate-rules.py"


class DeploymentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        base = Path(self.temp.name)
        self.repo = base / "repo"
        self.local = base / "local"
        self.data = base / "data"
        self.repo.mkdir()
        self.local.mkdir()
        (self.repo / "AGENTS.md").write_text(
            "# Source\n\n## 浏览器使用原则\n\n- shared\n",
            encoding="utf-8",
        )
        (self.repo / "cursor-overrides.md").write_text("- cursor\n", encoding="utf-8")
        (self.repo / "managed-files.json").write_text(
            json.dumps(
                {
                    "files": ["AGENTS.md", "cursor-user-rules.md"],
                    "directories": [],
                    "skills": [],
                    "cursor_rule_title": "Test Rule",
                }
            ),
            encoding="utf-8",
        )
        self.env = {
            **os.environ,
            "AGENT_RULES_ROOT": str(self.repo),
            "AGENT_RULES_LOCAL_ROOT": str(self.local),
            "AGENT_RULES_DATA_ROOT": str(self.data),
        }

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_script(self, script: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(script), *args],
            env=self.env,
            text=True,
            capture_output=True,
            check=check,
        )

    def test_deploy_verify_and_validate(self) -> None:
        result = self.run_script(DEPLOY)
        self.assertIn("cursor-verified", result.stdout)
        self.assertTrue((self.data / "deployment-state.json").is_file())
        self.assertTrue((self.local / "AGENTS.md").is_file())
        pending = self.run_script(VALIDATE, check=False)
        self.assertNotEqual(0, pending.returncode)
        self.assertIn("部署事务未完成", pending.stderr)

        self.run_script(DEPLOY, "--cursor-verified")
        self.assertFalse((self.data / "deployment-state.json").exists())
        self.assertTrue((self.data / "cursor-verification.json").is_file())

        result = self.run_script(VALIDATE)
        self.assertIn("Cursor verification receipt", result.stdout)

    def test_rollback_restores_previous_file(self) -> None:
        self.run_script(DEPLOY)
        self.run_script(DEPLOY, "--cursor-verified")
        previous = (self.local / "AGENTS.md").read_text(encoding="utf-8")
        (self.repo / "AGENTS.md").write_text(
            "# Changed\n\n## 浏览器使用原则\n\n- shared\n",
            encoding="utf-8",
        )

        self.run_script(DEPLOY)
        self.assertNotEqual(previous, (self.local / "AGENTS.md").read_text(encoding="utf-8"))
        self.run_script(DEPLOY, "--rollback")
        self.assertEqual(previous, (self.local / "AGENTS.md").read_text(encoding="utf-8"))

    def test_rejects_path_outside_managed_root(self) -> None:
        manifest = json.loads((self.repo / "managed-files.json").read_text(encoding="utf-8"))
        manifest["files"].append("../escape.txt")
        (self.repo / "managed-files.json").write_text(json.dumps(manifest), encoding="utf-8")
        result = self.run_script(DEPLOY, check=False)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("非法托管路径", result.stderr)


if __name__ == "__main__":
    unittest.main()
