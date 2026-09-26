"""Legacy compatibility shim — LEREV was renamed to Teacher.

This package re-exports the Teacher API so pre-rename integrations keep
working: ``import lerev``, ``from lerev.cli import main``,
``python -m lerev.bridge``, and the ``lerev`` console script.

It is a deliberate legacy alias, not a second identity — new code should
import :mod:`teacher` instead. See docs/installation.md (Migration).
"""

from __future__ import annotations

from teacher import __version__

__all__ = ["__version__"]
