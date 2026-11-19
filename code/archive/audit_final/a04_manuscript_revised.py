"""Builds the scientifically revised manuscript for the audit package.

Since 2026-11-12 the revised content lives in the project's own build script (analysis_v3/s11_manuscript.py); the former
stand-alone copy kept here is superseded (backup of the pre-revision s11: audit_final/s11_manuscript_before_port_2026-11-12.py).
This wrapper runs s11 in the analysis folder and copies its output to
<package>/01_MANUSCRIPT/Manuscript_BMC_MIDM_SCIENTIFIC_REVISED.docx.
Usage: python a04_manuscript_revised.py [package_dir]   (env BRANCH3_WS / BRANCH3_OUT as in config.py)"""
import os, shutil, subprocess, sys
from pathlib import Path

A = Path(__file__).resolve().parents[1]
WS = Path(os.environ.get("BRANCH3_WS", A.parent))
OUT = Path(os.environ.get("BRANCH3_OUT", A / "outputs"))
PKG = Path(sys.argv[1]) if len(sys.argv) > 1 else WS / "BMC_MIDM_FEASIBILITY_FINAL_AUDIT_PACKAGE"
subprocess.run([sys.executable, "s11_manuscript.py"], cwd=A, check=True, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
dst = PKG / "01_MANUSCRIPT" / "Manuscript_BMC_MIDM_SCIENTIFIC_REVISED.docx"
dst.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(OUT / "Manuscript_BMC_MIDM.docx", dst)
print("saved", dst)
