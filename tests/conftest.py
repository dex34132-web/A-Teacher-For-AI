"""Shared pytest fixtures for the AI Learning Engine test suite."""

from __future__ import annotations

import pytest

from core.interfaces import (
    AdaptationEngine,
    Evaluator,
    KnowledgeBase,
    Learner,
    MemoryStore,
)


@pytest.fixture
def learner_cls() -> type[Learner]:
    return Learner


@pytest.fixture
def memory_store_cls() -> type[MemoryStore]:
    return MemoryStore


@pytest.fixture
def evaluator_cls() -> type[Evaluator]:
    return Evaluator


@pytest.fixture
def adaptation_engine_cls() -> type[AdaptationEngine]:
    return AdaptationEngine


@pytest.fixture
def knowledge_base_cls() -> type[KnowledgeBase]:
    return KnowledgeBase


@pytest.fixture
def all_interfaces(
    learner_cls: type[Learner],
    memory_store_cls: type[MemoryStore],
    evaluator_cls: type[Evaluator],
    adaptation_engine_cls: type[AdaptationEngine],
    knowledge_base_cls: type[KnowledgeBase],
) -> list[type]:
    return [
        learner_cls,
        memory_store_cls,
        evaluator_cls,
        adaptation_engine_cls,
        knowledge_base_cls,
    ]
