$ErrorActionPreference = 'Stop'

# Unregister from OpenCode
toolio uninstall

# Uninstall via pip
pip uninstall toolio -y
