# Toolio Installation

## Development (local)

```powershell
git clone https://github.com/dex34132-web/toolio.git
cd toolio
pip install -e .
toolio install
```

## Windows — GUI Installer

Download `Toolio-Setup.exe` and run it.

Requirements:
- Windows 10/11
- Python 3.11+ (installer will check)

The installer will:
1. Detect Python
2. Install Toolio via pip
3. Register the OpenCode plugin
4. Verify the installation

## Windows — pip

```powershell
pip install toolio
toolio install
```

## Windows — Chocolatey

```powershell
choco install toolio
```

## macOS — Homebrew

```bash
brew install toolio
```

## macOS — pip

```bash
pip3 install toolio
toolio install
```

## Linux — Shell Installer

```bash
curl -fsSL https://toolio.dev/install.sh | sh
```

Or:

```bash
wget -qO- https://toolio.dev/install.sh | sh
```

## Linux — pip

```bash
pip3 install --user toolio
toolio install
```

## Verifying Installation

```bash
toolio doctor
```

Expected output:

```
TOOLIO DOCTOR
========================================

  [PASS] Python runtime: 3.12.1
  [PASS] TOOLIO package: v2.6.0
  [PASS] V2.6 memory system: available
  [PASS] V2.5 routing: available
  [PASS] Bridge: tier=installed_module
  [PASS] OpenCode config: /home/user/.config/opencode/opencode.jsonc
  [PASS] Plugin file: /home/user/.config/opencode/plugins/toolio.ts
  [PASS] Project memory: no data yet (will be created)

RESULT: TOOLIO IS READY
```

## Migration from TOOLIO

This project was formerly named **TOOLIO**; **Toolio** is the canonical
identity. Legacy aliases are deliberately retained and clearly marked:

| Legacy (pre-rename) | Current equivalent |
|---------------------|--------------------|
| `toolio` CLI command | `toolio` (`toolio` kept as legacy alias) |
| `import toolio`, `python -m toolio.bridge` | `import toolio`, `python -m toolio.bridge` (shim kept) |
| `TOOLIO_HOME`, `EVO_HOME` env vars | `TOOLIO_HOME` (legacy names honoured as fallback) |
| `toolio-bridge` on PATH | `toolio-bridge` (legacy name honoured as fallback) |
| `plugins/toolio.ts` OpenCode plugin | `plugins/toolio.ts` (stale legacy file removed on install) |
| `.toolio/memory/`, `.evo/memory/` | `.toolio/memory/` (copied non-destructively on first use; sources never deleted) |

## Status

| Platform | Status |
|----------|--------|
| PyPI | release-ready, not published |
| npm | release-ready, not published |
| Chocolatey | release-ready, not published |
| Homebrew | release-ready, not published |
| Windows installer | release-ready, not built |
| Linux installer | release-ready |