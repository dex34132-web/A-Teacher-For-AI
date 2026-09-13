# Lerev Installation

## Development (local)

```powershell
git clone https://github.com/dkshs/lerev.git
cd lerev
pip install -e .
lerev install
```

## Windows — GUI Installer

Download `Lerev-Setup.exe` and run it.

Requirements:
- Windows 10/11
- Python 3.11+ (installer will check)

The installer will:
1. Detect Python
2. Install Lerev via pip
3. Register the OpenCode plugin
4. Verify the installation

## Windows — pip

```powershell
pip install lerev
lerev install
```

## Windows — Chocolatey

```powershell
choco install lerev
```

## macOS — Homebrew

```bash
brew install lerev
```

## macOS — pip

```bash
pip3 install lerev
lerev install
```

## Linux — Shell Installer

```bash
curl -fsSL https://lerev.dev/install.sh | sh
```

Or:

```bash
wget -qO- https://lerev.dev/install.sh | sh
```

## Linux — pip

```bash
pip3 install --user lerev
lerev install
```

## Verifying Installation

```bash
lerev doctor
```

Expected output:

```
LEREV DOCTOR
========================================

  [PASS] Python runtime: 3.12.1
  [PASS] LEREV package: v2.6.0
  [PASS] V2.6 memory system: available
  [PASS] V2.5 routing: available
  [PASS] Bridge: tier=installed_module
  [PASS] OpenCode config: /home/user/.config/opencode/opencode.jsonc
  [PASS] Plugin registered: yes
  [PASS] Plugin file: /home/user/.config/opencode/node_modules/lerev
  [PASS] Project memory: no data yet (will be created)

RESULT: LEREV IS READY
```

## Status

| Platform | Status |
|----------|--------|
| PyPI | release-ready, not published |
| npm | release-ready, not published |
| Chocolatey | release-ready, not published |
| Homebrew | release-ready, not published |
| Windows installer | release-ready, not built |
| Linux installer | release-ready |