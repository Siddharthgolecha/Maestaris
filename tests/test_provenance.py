import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from maestaris_orchestration.provenance import validate_provenance


class ProvenanceTests(unittest.TestCase):
    def test_valid_bundle_and_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = root / "raw.bin"
            artifact.write_bytes(b"frozen raw bytes")
            digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
            manifest = root / "PROVENANCE.json"
            manifest.write_text(json.dumps({
                "schema": 1,
                "source": {"commit": "a" * 40},
                "artifacts": [{"path": "raw.bin", "sha256": digest, "kind": "raw"}],
                "reproduce": {"command": "python reproduce.py"},
            }), encoding="utf-8")
            self.assertEqual(validate_provenance(manifest), [])

    def test_detects_hash_mismatch_without_modifying_raw_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = root / "raw.bin"
            original = b"do not regenerate me"
            artifact.write_bytes(original)
            manifest = root / "PROVENANCE.json"
            manifest.write_text(json.dumps({
                "schema": 1,
                "source": {"commit": "b" * 40},
                "artifacts": [{"path": "raw.bin", "sha256": "0" * 64, "kind": "raw"}],
            }), encoding="utf-8")
            self.assertIn("sha256 mismatch: raw.bin", validate_provenance(manifest))
            self.assertEqual(artifact.read_bytes(), original)

    def test_rejects_path_escape_and_bad_kind(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / "PROVENANCE.json"
            manifest.write_text(json.dumps({
                "schema": 1,
                "source": {"commit": "c" * 40},
                "artifacts": [{"path": "../outside", "sha256": "0" * 64, "kind": "mystery"}],
            }), encoding="utf-8")
            errors = validate_provenance(manifest)
            self.assertTrue(any("kind" in error for error in errors))
            self.assertTrue(any("escapes" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
