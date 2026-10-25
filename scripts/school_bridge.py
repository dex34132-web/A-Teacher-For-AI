import subprocess, sys, os
script = os.path.join(os.path.dirname(__file__), "toolio_bridge.py")
sys.exit(subprocess.call([sys.executable, script] + sys.argv[1:]))
