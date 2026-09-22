"""Marks the repository root for pytest.

With pytest's default (prepend) import mode, the directory holding a standalone
conftest.py is added to sys.path, which is what lets tests/test_core.py do
``import core`` and ``import seed``. The file is intentionally empty otherwise.
"""
