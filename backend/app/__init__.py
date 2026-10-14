"""Solve Sphere API application package."""

import sys
from pathlib import Path

workspace_root = str(Path(__file__).resolve().parents[2])
if workspace_root not in sys.path:
	sys.path.insert(0, workspace_root)