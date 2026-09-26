# Teacher Installation

## Development (local)

```powershell
git clone https://github.com/dex34132-web/lerev.git
cd teacher
pip install -e .
teacher install
```

## Windows — GUI Installer

Download `Teacher-Setup.exe` and run it.

Requirements:
- Windows 10/11
- Python 3.11+ (installer will check)

The installer will:
1. Detect Python
2. Install Teacher via pip
3. Register the OpenCode plugin
4. Verify the installation

## Windows — pip

```powershell
pip install teacher
teacher install
```

## Windows — Chocolatey

```powershell
choco install teacher
```

## macOS — Homebrew

```bash
brew install teacher
```

## macOS — pip

```bash
pip3 install teacher
teacher install
```

## Linux — Shell Installer

```bash
curl -fsSL https://teacher.dev/install.sh | sh
```

Or:

```bash
wget -qO- https://teacher.dev/install.sh | sh
```

## Linux — pip

```bash
pip3 install --user teacher
teacher install
```

## Verifying Installation

```bash
teacher doctor
```

Expected output:

```
TEACHER DOCTOR
========================================

  [PASS] Python runtime: 3.12.1
  [PASS] TEACHER package: v2.6.0
  [PASS] V2.6 memory system: available
  [PASS] V2.5 routing: available
  [PASS] Bridge: tier=installed_module
  [PASS] OpenCode config: /home/user/.config/opencode/opencode.jsonc
  [PASS] Plugin file: /home/user/.config/opencode/plugins/teacher.ts
  [PASS] Project memory: no data yet (will be created)

RESULT: TEACHER IS READY
```

## Migration from LEREV

This project was formerly named **LEREV**; **Teacher** is the canonical
identity. Legacy aliases are deliberately retained and clearly marked:

| Legacy (pre-rename) | Current equivalent |
|---------------------|--------------------|
| `lerev` CLI command | `teacher` (`lerev` kept as legacy alias) |
| `import lerev`, `python -m lerev.bridge` | `import teacher`, `python -m teacher.bridge` (shim kept) |
| `LEREV_HOME`, `EVO_HOME` env vars | `TEACHER_HOME` (legacy names honoured as fallback) |
| `lerev-bridge` on PATH | `teacher-bridge` (legacy name honoured as fallback) |
| `plugins/lerev.ts` OpenCode plugin | `plugins/teacher.ts` (stale legacy file removed on install) |
| `.lerev/memory/`, `.evo/memory/` | `.teacher/memory/` (copied non-destructively on first use; sources never deleted) |

## Status

| Platform | Status |
|----------|--------|
| PyPI | release-ready, not published |
| npm | release-ready, not published |
| Chocolatey | release-ready, not published |
| Homebrew | release-ready, not published |
| Windows installer | release-ready, not built |
| Linux installer | release-ready |