"""Run with Blender --background --python build_model.py to rebuild this version."""
from pathlib import Path
import subprocess,sys,runpy
HERE=Path(__file__).resolve().parent
REVIEW=HERE.parents[2]/'reviews/large-rear-cap-2026-11-16'
PYTHON=Path('/private/tmp/march7-blender-mount/Blender.app/Contents/Resources/4.5/python/bin/python3.11')
subprocess.run([str(PYTHON),str(REVIEW/'build_geometry.py'),str(HERE)],check=True)
sys.argv=[str(REVIEW/'finalize_blend.py'),'--',str(HERE)]
runpy.run_path(str(REVIEW/'finalize_blend.py'),run_name='__main__')
