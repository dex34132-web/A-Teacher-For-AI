#!/bin/sh
set -e

TEACHER_VERSION="2.6.0"
INSTALL_DIR="${HOME}/.local/bin"

echo "Teacher Installer"
echo "-----------------------------"

# Detect OS
OS=$(uname -s)
ARCH=$(uname -m)

echo "OS: ${OS}"
echo "Arch: ${ARCH}"

# Check Python
if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: Python 3.11+ is required but not found."
    echo "Please install Python: https://www.python.org/downloads/"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Python: ${PYTHON_VERSION}"

# Check pip
if ! command -v pip3 >/dev/null 2>&1; then
    echo "ERROR: pip3 is required but not found."
    exit 1
fi

# Install Teacher
echo "Installing Teacher..."
pip3 install --user teacher

# Ensure ~/.local/bin is on PATH (POSIX-compatible)
case ":${PATH}:" in
    *":${INSTALL_DIR}:"*) ;;
    *)
        echo "Adding ${INSTALL_DIR} to PATH..."
        if [ -f "${HOME}/.bashrc" ]; then
            echo "export PATH=\"${INSTALL_DIR}:\$PATH\"" >> "${HOME}/.bashrc"
        fi
        if [ -f "${HOME}/.zshrc" ]; then
            echo "export PATH=\"${INSTALL_DIR}:\$PATH\"" >> "${HOME}/.zshrc"
        fi
        export PATH="${INSTALL_DIR}:${PATH}"
        ;;
esac

# Register with OpenCode
if command -v teacher >/dev/null 2>&1; then
    echo "Registering with OpenCode..."
    teacher install
else
    echo "WARNING: teacher command not found on PATH."
    echo "Please run 'teacher install' manually after ensuring ~/.local/bin is on PATH."
fi

echo ""
echo "Installation complete!"
echo "Restart your terminal or run: source ~/.bashrc"
