import os
import sys

# Ensure the project root is importable so `import video_agent` works whether the
# suite is launched via `python -m pytest` or the bare `pytest` console script
# (which sets sys.path[0] to the bin/ directory, not the project root).
sys.path.insert(0, os.path.dirname(__file__))
