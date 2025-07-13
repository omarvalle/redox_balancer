"""Shared test configuration and fixtures."""

import pytest
from pathlib import Path


def require_data_file(path: Path, reason: str = None):
    """Skip test if required data file is not present.
    
    Args:
        path: Path to required data file
        reason: Optional custom reason for skipping
    """
    if not path.exists():
        if reason:
            pytest.skip(reason)
        else:
            pytest.skip(f"Optional data file {path} not present")