# Compatibility shim – preserves module name for logging
import runpy

runpy.run_module("stages.discover", run_name=__name__)
