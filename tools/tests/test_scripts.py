import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


class Scripts(unittest.TestCase):
    def test_every_tool_loads_when_run_as_a_script(self):
        # `python3 tools/X.py` puts tools/ (not the repo root) on sys.path; -I reproduces that for run_path.
        for tool in ("contrast", "make_background", "check_site", "validate", "screens"):
            code = f"import runpy; runpy.run_path('tools/{tool}.py', run_name='loaded')"
            r = subprocess.run([sys.executable, "-I", "-c", code], cwd=REPO, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, f"{tool}: {r.stderr.strip().splitlines()[-1:]}")


if __name__ == "__main__":
    unittest.main()
