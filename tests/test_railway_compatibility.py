"""Railway-specific contracts not validated by a successful Docker build."""
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class RailwayCompatibilityTests(unittest.TestCase):
    def test_dockerfile_does_not_declare_volumes(self):
        content = (ROOT / "Dockerfile").read_text(encoding="utf-8")
        self.assertNotRegex(
            content,
            re.compile(r"^[ \t]*VOLUME(?:[ \t]|$)", re.IGNORECASE | re.MULTILINE),
            "Railway rejects Docker VOLUME instructions. Attach persistent "
            "storage through the Railway service/template at /app/data instead.",
        )


if __name__ == "__main__":
    unittest.main()
