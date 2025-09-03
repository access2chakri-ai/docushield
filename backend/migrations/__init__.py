"""
DocuShield Migrations Package
Contains database migration files and migration runner
"""

import sys
import os
from pathlib import Path

# Ensure the backend directory is in the Python path
backend_path = str(Path(__file__).parent.parent)
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# Make migrations package importable
__all__ = ['migration_runner']
