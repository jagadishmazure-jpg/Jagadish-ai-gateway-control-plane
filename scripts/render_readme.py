"""Regenerate the README results block from a real run (results/*.json + live pytest count).

--check fails if the committed README differs from what a fresh run produces."""
import json
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from count_tests import run

ROOT = pathlib.Path(__file__).resolve().parents[1]
BEGIN, END = "<!-- BEGIN GENERATED -->", "<!-- END GENERATED -->"

def block():
    subprocess.run([sys.executable, "scripts/run_eval.py"], cwd=ROOT, check=True, capture_output=True)
    rc, passed, _failed, _ = run()
    if rc != 0:
        sys.exit("tests failed")
    res = json.loads((ROOT / "results" / "results.json").read_text())
    lines = [BEGIN, "", f"**Tests:** {passed} passing (`python scripts/count_tests.py`).", "",
             f"**Results** ({res['label']}, {res['sample']}):", "", "| Metric | Value |", "|---|---|"]
    for k, v in res["metrics"].items():
        lines.append(f"| {k} | {v} |")
    lines += ["", END]
    return "\n".join(lines)

if __name__ == "__main__":
    readme = ROOT / "README.md"
    txt = readme.read_text()
    a, b = txt.index(BEGIN), txt.index(END) + len(END)
    new = txt[:a] + block() + txt[b:]
    if "--check" in sys.argv:
        if new != txt:
            sys.exit("README results block is stale: run python scripts/render_readme.py")
        print("README results block matches a fresh run")
    else:
        readme.write_text(new)
        print("README updated")
