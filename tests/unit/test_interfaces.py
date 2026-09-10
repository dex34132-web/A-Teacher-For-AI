"""Tests that verify all core ABCs are properly abstract."""

from __future__ import annotations

from abc import ABC

import pytest

from core.interfaces import (
    AdaptationEngine,
    Evaluator,
    KnowledgeBase,
    Learner,
    MemoryStore,
)

ALL_INTERFACES: list[type[ABC]] = [
    Learner,
    MemoryStore,
    Evaluator,
    AdaptationEngine,
    KnowledgeBase,
]


class TestAbstractBaseClasses:
    @pytest.mark.parametrize("cls", ALL_INTERFACES, ids=lambda c: c.__name__)
    def test_is_abc(self, cls: type[ABC]) -> None:
        assert issubclass(cls, ABC)

    @pytest.mark.parametrize("cls", ALL_INTERFACES, ids=lambda c: c.__name__)
    def test_cannot_instantiate(self, cls: type[ABC]) -> None:
        with pytest.raises(TypeError):
            cls()  # type: ignore[abstract]


class TestLearnerInterface:
    def test_has_learn_method(self) -> None:
        assert hasattr(Learner, "learn")

    def test_has_reset_method(self) -> None:
        assert hasattr(Learner, "reset")

    def test_has_mode_property(self) -> None:
        assert hasattr(Learner, "mode")

    def test_has_parameters_property(self) -> None:
        assert hasattr(Learner, "parameters")

    def test_learn_is_abstract(self) -> None:
        assert getattr(Learner.learn, "__isabstractmethod__", False)

    def test_reset_is_abstract(self) -> None:
        assert getattr(Learner.reset, "__isabstractmethod__", False)


class TestMemoryStoreInterface:
    def test_has_store_method(self) -> None:
        assert hasattr(MemoryStore, "store")

    def test_has_retrieve_method(self) -> None:
        assert hasattr(MemoryStore, "retrieve")

    def test_has_delete_method(self) -> None:
        assert hasattr(MemoryStore, "delete")

    def test_has_exists_method(self) -> None:
        assert hasattr(MemoryStore, "exists")

    def test_has_count_method(self) -> None:
        assert hasattr(MemoryStore, "count")

    def test_has_clear_method(self) -> None:
        assert hasattr(MemoryStore, "clear")

    def test_store_is_abstract(self) -> None:
        assert getattr(MemoryStore.store, "__isabstractmethod__", False)

    def test_retrieve_is_abstract(self) -> None:
        assert getattr(MemoryStore.retrieve, "__isabstractmethod__", False)


class TestEvaluatorInterface:
    def test_has_evaluate_method(self) -> None:
        assert hasattr(Evaluator, "evaluate")

    def test_has_aggregate_method(self) -> None:
        assert hasattr(Evaluator, "aggregate")

    def test_has_metrics_property(self) -> None:
        assert hasattr(Evaluator, "metrics")

    def test_evaluate_is_abstract(self) -> None:
        assert getattr(Evaluator.evaluate, "__isabstractmethod__", False)

    def test_aggregate_is_abstract(self) -> None:
        assert getattr(Evaluator.aggregate, "__isabstractmethod__", False)


class TestAdaptationEngineInterface:
    def test_has_propose_method(self) -> None:
        assert hasattr(AdaptationEngine, "propose")

    def test_has_apply_method(self) -> None:
        assert hasattr(AdaptationEngine, "apply")

    def test_has_strategy_property(self) -> None:
        assert hasattr(AdaptationEngine, "strategy")

    def test_propose_is_abstract(self) -> None:
        assert getattr(AdaptationEngine.propose, "__isabstractmethod__", False)

    def test_apply_is_abstract(self) -> None:
        assert getattr(AdaptationEngine.apply, "__isabstractmethod__", False)


class TestKnowledgeBaseInterface:
    def test_has_add_method(self) -> None:
        assert hasattr(KnowledgeBase, "add")

    def test_has_query_method(self) -> None:
        assert hasattr(KnowledgeBase, "query")

    def test_has_update_method(self) -> None:
        assert hasattr(KnowledgeBase, "update")

    def test_has_remove_method(self) -> None:
        assert hasattr(KnowledgeBase, "remove")

    def test_has_count_method(self) -> None:
        assert hasattr(KnowledgeBase, "count")

    def test_has_clear_method(self) -> None:
        assert hasattr(KnowledgeBase, "clear")

    def test_add_is_abstract(self) -> None:
        assert getattr(KnowledgeBase.add, "__isabstractmethod__", False)

    def test_query_is_abstract(self) -> None:
        assert getattr(KnowledgeBase.query, "__isabstractmethod__", False)
