# Copyright (c) 2026 Eric Cooper.
"""Import guard — the package imports cleanly on every supported interpreter.

Mirrors Rulebook's import-everything guard: the cheapest signal that a stale or
broken import slipped in. It grows into the real test suite as the extraction
lands (most of Rulebook's tests/test_roles.py moves here).
"""

import role_capabilities


def test_package_imports_and_has_version():
    assert role_capabilities.__version__
