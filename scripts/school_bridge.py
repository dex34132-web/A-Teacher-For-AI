import runpy, os, sys
# Delegate to the renamed bridge
here = os.path.dirname(os.path.abspath(__file__))
target = os.path.join(here, "toolio_bridge.py")
if os.path.exists(target):
    runpy.run_path(target, run_name="__main__")
else:
    # fallback: invoke toolio bridge module
    sys.path.insert(0, os.path.dirname(here))
    from toolio.bridge import main
    main()
