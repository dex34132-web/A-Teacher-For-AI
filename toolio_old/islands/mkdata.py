"""
Regenerate schoolio/islands/data.ts from the repository as it is right now.

Everything the site plots is counted here, from git, with commands you can
re-run yourself:

    git rev-list --count HEAD
    git log --pretty=format:%aI --shortstat
    git ls-files
    git log --name-only --pretty=format:%aI

No sampling, no estimates.
"""
import json
import os
import re
import subprocess
import sys

REPO = str(__import__("pathlib").Path(__file__).resolve().parents[2])
OUT = os.path.join(REPO, "schoolio", "islands", "data.ts")

TEXT_EXT = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs",
    ".css", ".html", ".md", ".txt", ".sh", ".ps1", ".toml",
    ".yaml", ".yml", ".json", ".nsi", ".rb", ".nuspec",
}
SKIP_PREFIX = (
    "schoolio/__q_",
    "schoolio/assets/",
)


def git(*args):
    p = subprocess.run(
        ["git"] + list(args), cwd=REPO, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    if p.returncode != 0:
        sys.stderr.write(p.stderr)
        raise SystemExit("git failed: " + " ".join(args))
    return p.stdout


def main():
    # ---- commits: date + lines changed -------------------------------
    raw = git("log", "--pretty=format:%x01%aI", "--shortstat")
    churn, dates = [], []
    for block in raw.split("\x01"):
        block = block.strip("\n")
        if not block:
            continue
        lines = [l.strip() for l in block.splitlines() if l.strip()]
        day = lines[0].strip()
        ins = dele = 0
        for l in lines[1:]:
            m = re.search(r"(\d+) insertion", l)
            if m:
                ins = int(m.group(1))
            m = re.search(r"(\d+) deletion", l)
            if m:
                dele = int(m.group(1))
        churn.append(ins + dele)
        dates.append(day)

    churn.reverse()
    dates.reverse()  # git log is newest-first; the plot reads oldest→newest

    # ---- every file: last commit date --------------------------------
    last_date = {}
    raw = git("log", "--name-only", "--pretty=format:%x01%aI")
    cur = None
    for line in raw.splitlines():
        if line.startswith("\x01"):
            cur = line[1:].strip()
            continue
        path = line.strip()
        if path and cur and path not in last_date:
            last_date[path] = cur

    files = [f for f in git("ls-files").splitlines() if f.strip()]

    # ---- tests --------------------------------------------------------
    test_names, test_counts, test_dates = [], [], []
    for f in files:
        base = os.path.basename(f)
        if not (base.startswith("test_") and f.endswith(".py")):
            continue
        full = os.path.join(REPO, f)
        try:
            with open(full, encoding="utf-8", errors="replace") as fh:
                body = fh.read()
        except OSError:
            continue
        n = len(re.findall(r"(?m)^\s*def test_", body))
        test_names.append(f)
        test_counts.append(n)
        test_dates.append(last_date.get(f, dates[-1]))

    # ---- source -------------------------------------------------------
    src_names, src_counts, src_dates = [], [], []
    for f in files:
        ext = os.path.splitext(f)[1].lower()
        if ext not in TEXT_EXT:
            continue
        if f.startswith(SKIP_PREFIX):
            continue
        if os.path.basename(f).startswith("__q_"):
            continue
        full = os.path.join(REPO, f)
        try:
            with open(full, encoding="utf-8", errors="replace") as fh:
                n = sum(1 for _ in fh)
        except OSError:
            continue
        src_names.append(f)
        src_counts.append(n)
        src_dates.append(last_date.get(f, dates[-1]))

    commit_count = len(churn)
    churn_total = sum(churn)
    file_count = len(src_names)
    total_lines = sum(src_counts)
    test_file_count = len(test_names)
    test_total = sum(test_counts)

    def arr(name, values, quote=False):
        if quote:
            body = ", ".join(json.dumps(v) for v in values)
        else:
            body = ", ".join(str(v) for v in values)
        return "export const %s = [%s] as const\n" % (name, body)

    out = []
    out.append("// Generated from the repository itself. Do not hand-edit.\n")
    out.append("// git rev-list --count HEAD | %d\n" % commit_count)
    out.append("// git ls-files (text files) | %d\n" % file_count)
    out.append("// test files | %d  test functions | %d\n\n" % (test_file_count, test_total))
    out.append(arr("COMMIT_CHURN", churn))
    out.append(arr("COMMIT_DATES", dates, True))
    out.append(arr("TEST_FUNCS", test_counts))
    out.append(arr("TEST_DATES", test_dates, True))
    out.append(arr("TEST_NAMES", test_names, True))
    out.append(arr("SRC_LINES", src_counts))
    out.append(arr("SRC_DATES", src_dates, True))
    out.append(arr("SRC_NAMES", src_names, True))
    out.append("\n")
    out.append("export const COMMIT_COUNT = %d\n" % commit_count)
    out.append("export const FILE_COUNT = %d\n" % file_count)
    out.append("export const TEST_FILE_COUNT = %d\n" % test_file_count)
    out.append("export const TOTAL_LINES = %d\n" % total_lines)
    out.append("export const TEST_FUNCS_TOTAL = %d\n" % test_total)
    out.append("export const CHURN_TOTAL = %d\n" % churn_total)
    out.append("export const FIRST_COMMIT = %s\n" % json.dumps(dates[0][:10]))
    out.append("export const LAST_COMMIT = %s\n" % json.dumps(dates[-1][:10]))
    out.append("export const WORKING_DAYS = %d\n" % len({d[:10] for d in dates}))

    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("".join(out))

    print("commits      ", commit_count)
    print("churn        ", churn_total)
    print("test files   ", test_file_count)
    print("test funcs   ", test_total)
    print("source files ", file_count)
    print("total lines  ", total_lines)
    print("first / last ", dates[0][:10], dates[-1][:10])
    print("working days ", len({d[:10] for d in dates}))
    print("written      ", OUT)


main()
