# Lerev Installation

## Windows — Recommended GUI Installer

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

## npm (for OpenCode plugin only)

```bash
npm install -g lerev
```

Or in your project:

```bash
npm install lerev
```

## Verifying Installation

```bash
lerev doctor
```

Expected output:

```
Lerev Doctor
────────────────────────────
Lerev runtime          PASS
Python/runtime         3.12 OK
Bridge                 PASS (tier: installed_module)
OpenCode               PASS
Plugin registration   PASS
Plugin resolution     PASS
Memory storage         SKIP — no memory data yet

Result: READY
```