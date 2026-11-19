"""Verification of the audit package and its ZIP archives.

Checks: ZIP integrity (testzip) and that every ZIP member matches SHA256SUMS.txt; SHA-256 of every file in the package
folder against 08_FILE_MANIFEST.csv and SHA256SUMS.txt; every .csv parses (utf-8, rectangular, non-empty); every .py compiles;
every .docx opens with python-docx and every .xlsx with openpyxl; no absolute Windows path remains in the packaged scripts;
the claim matrix and the ledger contain no INCONSISTENT / NOT_REPRODUCIBLE rows.
Writes 07_AUDIT_AND_PROVENANCE/VERIFICATION_REPORT.md. Exit code 1 if any check fails.
Usage: python a07_verify.py [package_dir] [zip_dir]"""
import ast, csv, hashlib, io, os, re, sys, zipfile
from pathlib import Path

WS = Path(os.environ.get("BRANCH3_WS", Path(__file__).resolve().parents[2]))
PKG = Path(sys.argv[1]) if len(sys.argv) > 1 else WS / "BMC_MIDM_FEASIBILITY_FINAL_AUDIT_PACKAGE"
ZDIR = Path(sys.argv[2]) if len(sys.argv) > 2 else PKG.parent / "BMC_MIDM_FEASIBILITY_FINAL_AUDIT_ZIPS"
fails, lines = [], []
SELF = "07_AUDIT_AND_PROVENANCE/VERIFICATION_REPORT.md"   # written by this script; excluded from its own hash checks


def ok(section, msg, good=True):
    lines.append(f"- {'PASS' if good else 'FAIL'}: {section} — {msg}")
    if not good:
        fails.append(f"{section}: {msg}")


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


sums = {}
for ln in (PKG / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
    h, p = ln.split("  ", 1); sums[p] = h
man = list(csv.DictReader(open(PKG / "08_FILE_MANIFEST.csv", encoding="utf-8")))
ok("manifest", f"{len(man)} rows; SHA256SUMS has {len(sums)} entries", len(man) == len(sums) and all(r["package_path"] in sums for r in man))

# ---- package folder vs manifest
missing, mism, extra = [], [], []
for r in man:
    p = PKG / r["package_path"]
    if not p.exists():
        missing.append(r["package_path"]); continue
    if r["package_path"] != SELF and (sha_bytes(p.read_bytes()) != r["sha256"] or r["sha256"] != sums[r["package_path"]]):
        mism.append(r["package_path"])
listed = {r["package_path"] for r in man} | {"08_FILE_MANIFEST.csv", "09_EXCLUDED_FILES_MANIFEST.csv", "SHA256SUMS.txt", "ZIP_REPORT.txt", SELF}
for p in PKG.rglob("*"):
    if p.is_file() and p.relative_to(PKG).as_posix() not in listed:
        extra.append(p.relative_to(PKG).as_posix())
ok("SHA-256 (folder)", f"missing {len(missing)}, mismatched {len(mism)}, unlisted {len(extra)} {extra[:5]}", not (missing or mism or extra))

# ---- zips
for zp in sorted(ZDIR.glob("BMC_FEASIBILITY_*.zip")):
    with zipfile.ZipFile(zp) as z:
        bad = z.testzip(); names = z.namelist()
        zm = [n for n in names if n in sums and n != SELF and sha_bytes(z.read(n)) != sums[n]]
        unl = [n for n in names if n not in sums and n not in ("08_FILE_MANIFEST.csv", "09_EXCLUDED_FILES_MANIFEST.csv", "SHA256SUMS.txt", "ZIP_REPORT.txt")]
    size = zp.stat().st_size
    ok("ZIP " + zp.name, f"{size/1e6:.2f} MB, {len(names)} members, testzip {'OK' if bad is None else bad}, sha mismatches {len(zm)}, unlisted {len(unl)}, "
       f"{'<= 8 MB' if size <= 8_000_000 else '> 8 MB (<= 12 MB hard limit)' if size <= 12_000_000 else '> 12 MB'}",
       bad is None and not zm and not unl and size <= 12_000_000)
covered = set()
for zp in ZDIR.glob("BMC_FEASIBILITY_*.zip"):
    with zipfile.ZipFile(zp) as z:
        covered |= set(z.namelist())
notin = [p for p in sums if p not in covered]
ok("ZIP coverage", f"{len(notin)} manifest files missing from all ZIPs {notin[:5]}", not notin)

# ---- CSV parsing
bad_csv = []
for p in sorted(PKG.rglob("*.csv")):
    try:
        txt = p.read_bytes().decode("utf-8-sig")
        rows = list(csv.reader(io.StringIO(txt)))
        rows = [r for r in rows if r]
        if not rows:
            bad_csv.append((p.name, "empty")); continue
        w = len(rows[0]); ragged = [i + 1 for i, r in enumerate(rows) if len(r) != w]
        if ragged:
            bad_csv.append((p.name, f"ragged rows {ragged[:5]}"))
    except Exception as e:
        bad_csv.append((p.name, str(e)[:80]))
ok("CSV parsing", f"{sum(1 for _ in PKG.rglob('*.csv'))} files; problems: {bad_csv}", not bad_csv)
hdr_only = [p.relative_to(PKG).as_posix() for p in PKG.rglob("*.csv") if len([r for r in csv.reader(io.StringIO(p.read_text(encoding='utf-8-sig'))) if r]) == 1]
lines.append(f"- INFO: header-only CSV files (documented placeholders): {hdr_only}")

# ---- Python syntax + absolute paths
bad_py, abs_paths = [], []
for p in sorted(PKG.rglob("*.py")):
    try:
        ast.parse(p.read_text(encoding="utf-8"), filename=str(p))   # syntax check without writing byte-code
    except SyntaxError as e:
        bad_py.append((p.name, str(e)[:100]))
    for i, ln in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        s = ln.strip()
        if s.startswith("#") or "http" in s or "re.search(" in s:
            continue
        # a Windows drive path (D:\ or D:/) or a Unix home path; URLs (scheme://) are excluded above
        if re.search(r"(?<![A-Za-z/])[A-Za-z]:[\\/](?![\\/])|/Users/|/home/", ln):
            abs_paths.append(f"{p.name}:{i}")
ok("Python syntax", f"{sum(1 for _ in PKG.rglob('*.py'))} files; errors: {bad_py}", not bad_py)
ok("absolute paths in code", f"{abs_paths}", not abs_paths)

# ---- DOCX / XLSX open
from docx import Document
import openpyxl
bad_doc = []
for p in sorted(PKG.rglob("*.docx")):
    try:
        d = Document(str(p)); n = len(d.paragraphs)
        if n == 0:
            bad_doc.append((p.name, "no paragraphs"))
    except Exception as e:
        bad_doc.append((p.name, str(e)[:80]))
for p in sorted(PKG.rglob("*.xlsx")):
    try:
        wb = openpyxl.load_workbook(str(p), read_only=True); _ = wb.sheetnames
    except Exception as e:
        bad_doc.append((p.name, str(e)[:80]))
ok("DOCX/XLSX open", f"{sum(1 for _ in PKG.rglob('*.docx'))} docx, {sum(1 for _ in PKG.rglob('*.xlsx'))} xlsx; problems: {bad_doc}", not bad_doc)

# ---- claim matrix and ledger status
cm = list(csv.DictReader(open(PKG / "02_NUMERICAL_EVIDENCE" / "CLAIM_TO_EVIDENCE_FINAL.csv", encoding="utf-8-sig")))
cst = {}
for r in cm:
    cst[r["status"]] = cst.get(r["status"], 0) + 1
unsync = [r["claim_id"] for r in cm if r.get("in_manuscript_text") == "no"]
ok("claim matrix", f"{len(cm)} claims {cst}; numbers not found in manuscript text: {unsync}", not any(k in cst for k in ("INCONSISTENT", "NOT_REPRODUCIBLE")) and not unsync)
led = list(csv.DictReader(open(PKG / "07_AUDIT_AND_PROVENANCE" / "NUMERICAL_SOURCE_OF_TRUTH_LEDGER_REVISED.csv", encoding="utf-8-sig")))
lst = {}
for r in led:
    lst[r["verification_status"]] = lst.get(r["verification_status"], 0) + 1
nf = [r["claim_id"] for r in led if "NOT FOUND" in r["reported_value"]]
ok("numerical ledger", f"{len(led)} rows {lst}; reported value not found in text: {nf}",
   not any(k in lst for k in ("INCONSISTENT", "NOT_REPRODUCIBLE")) and not nf)

rep = PKG / "07_AUDIT_AND_PROVENANCE" / "VERIFICATION_REPORT.md"
rep.write_text("# Verification report (a07_verify.py)\n\n" + "\n".join(lines) + f"\n\n**Result: {'ALL CHECKS PASSED' if not fails else str(len(fails)) + ' FAILED'}**\n", encoding="utf-8")
print("\n".join(lines)); print("RESULT:", "ALL CHECKS PASSED" if not fails else fails)
sys.exit(1 if fails else 0)
