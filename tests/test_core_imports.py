"""Smoke tests that verify all core modules can be imported."""

from __future__ import annotations

import importlib

import pytest

CORE_MODULES: list[str] = [
    "core",
    "core.interfaces",
    "core.learner",
    "core.learner.base",
    "core.memory",
    "core.memory.base",
    "core.evaluator",
    "core.evaluator.base",
    "core.adaptation",
    "core.adaptation.base",
    "core.knowledge",
    "core.knowledge.base",
]


class TestCoreImports:
    @pytest.mark.parametrize("module_name", CORE_MODULES)
    def test_import_without_error(self, module_name: str) -> None:
        mod = importlib.import_module(module_name)
        assert mod is not None


class TestCoreInterfacesExports:
    def test_learner_is_exported(self) -> None:
        from core.interfaces import Learner

        assert Learner is not None

    def test_memory_store_is_exported(self) -> None:
        from core.interfaces import MemoryStore

        assert MemoryStore is not None

    def test_evaluator_is_exported(self) -> None:
        from core.interfaces import Evaluator

        assert Evaluator is not None

    def test_adaptation_engine_is_exported(self) -> None:
        from core.interfaces import AdaptationEngine

        assert AdaptationEngine is not None

    def test_knowledge_base_is_exported(self) -> None:
        from core.interfaces import KnowledgeBase

        assert KnowledgeBase is not None
