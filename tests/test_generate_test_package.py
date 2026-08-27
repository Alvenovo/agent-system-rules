from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "测试规则" / "scripts" / "generate_test_package.py"
SPEC = importlib.util.spec_from_file_location("generate_test_package", SCRIPT)
assert SPEC and SPEC.loader
GENERATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GENERATOR)


class GenerateTestPackageTests(unittest.TestCase):
    def load_example(self) -> dict:
        path = ROOT / "测试规则" / "templates" / "test-manifest.example.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def test_generate_and_check_package(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "input.json"
            output = root / "archive"
            source.write_text(json.dumps(self.load_example(), ensure_ascii=False), encoding="utf-8")

            GENERATOR.generate(source, output)
            GENERATOR.check(output)

            archived = json.loads((output / "source" / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(4, len(archived["artifacts"]))
            self.assertTrue((output / "证据").is_dir())
            for relative in archived["artifacts"]:
                self.assertTrue((output / relative).is_file())

    def test_wap_is_normalized_to_h5(self) -> None:
        data = self.load_example()
        data["cases"][0]["platform"] = "WAP"
        cases, _ = GENERATOR.validate(data)
        self.assertEqual("H5", cases[0]["platform"])

    def test_covered_item_requires_case_key(self) -> None:
        data = self.load_example()
        data["coverage"][0]["case_keys"] = []
        with self.assertRaises(SystemExit):
            GENERATOR.validate(data)


if __name__ == "__main__":
    unittest.main()
