# School Installation

## Development (local)

```powershell
git clone https://github.com/dex34132-web/lerev.git
cd school
pip install -e .
school install
```

## Windows — GUI Installer

Download `School-Setup.exe` and run it.

Requirements:
- Windows 10/11
- Python 3.11+ (installer will check)

The installer will:
1. Detect Python
2. Install School via pip
3. Register the OpenCode plugin
4. Verify the installation

## Windows — pip

```powershell
pip install school
school install
```

## Windows — Chocolatey

```powershell
choco install school
```

## macOS — Homebrew

```bash
brew install school
```

## macOS — pip

```bash
pip3 install school
school install
```

## Linux — Shell Installer

```bash
curl -fsSL https://school.dev/install.sh | sh
```

Or:

```bash
wget -qO- https://school.dev/install.sh | sh
```

## Linux — pip

```bash
pip3 install --user school
school install
```

## Verifying Installation

```bash
school doctor
```

Expected output:

```
SCHOOL DOCTOR
========================================

  [PASS] Python runtime: 3.12.1
  [PASS] SCHOOL package: v2.6.0
  [PASS] V2.6 memory system: available
  [PASS] V2.5 routing: available
  [PASS] Bridge: tier=installed_module
  [PASS] OpenCode config: /home/user/.config/opencode/opencode.jsonc
  [PASS] Plugin file: /home/user/.config/opencode/plugins/school.ts
  [PASS] Project memory: no data yet (will be created)

RESULT: SCHOOL IS READY
```

## Migration from LEREV

This project was formerly named **LEREV**; **School** is the canonical
identity. Legacy aliases are deliberately retained and clearly marked:

| Legacy (pre-rename) | Current equivalent |
|---------------------|--------------------|
| `lerev` CLI command | `school` (`lerev` kept as legacy alias) |
| `import lerev`, `python -m lerev.bridge` | `import school`, `python -m school.bridge` (shim kept) |
| `LEREV_HOME`, `EVO_HOME` env vars | `SCHOOL_HOME` (legacy names honoured as fallback) |
| `lerev-bridge` on PATH | `school-bridge` (legacy name honoured as fallback) |
| `plugins/lerev.ts` OpenCode plugin | `plugins/school.ts` (stale legacy file removed on install) |
| `.lerev/memory/`, `.evo/memory/` | `.school/memory/` (copied non-destructively on first use; sources never deleted) |

## Status

| Platform | Status |
|----------|--------|
| PyPI | release-ready, not published |
| npm | release-ready, not published |
| Chocolatey | release-ready, not published |
| Homebrew | release-ready, not published |
| Windows installer | release-ready, not built |
| Linux installer | release-ready |