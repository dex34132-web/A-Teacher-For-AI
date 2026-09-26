"""R2 regression tests: natural-language teacher_recall via semantic retrieval.

The R2 defect: MemoryManager.request_memory passed query_text to
MemoryStore.query WITHOUT an extractor, so the store fell back to
whole-query substring matching and natural-language questions returned
nothing even when the right memory was persisted.

These tests exercise the full desired pipeline:

    NL query -> scope/confidence/tags candidate filter
             -> TF-IDF semantic ranking (scored_query)
             -> security boundary
             -> context budget / limit
             -> deterministic MemoryResponse

Persistence tests use real bridge subprocesses (write -> process death ->
fresh process -> read), mirroring test_teacher_learn_persistence.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

from core.learner.feature_extractor import FeatureExtractor
from core.learner.similarity import cosine_similarity
from core.routing.v26.identity import (
    AgentIdentity,
    MemoryScope,
    ProjectIdentity,
    SessionIdentity,
)
from core.routing.v26.memory_manager import MemoryManager
from core.routing.v26.memory_store import MemoryStore
from core.routing.v26.memory_types import MemoryEntry, MemoryKind, MemoryRequest

REPO_ROOT = Path(__file__).resolve().parents[2]

ORION_FACTS = [
    "The fictional research vessel ORION-47 was commissioned in 2087.",
    "Its home port is Northglass.",
    "Northglass has exactly 17 docking platforms.",
    "Elian Voss commands ORION-47.",
]

DISTRACTORS = [
    "The garden contains 43 trees.",
    "The train departs at 08:30.",
    "The robot uses titanium.",
    "The city contains 12 bridges.",
    "The laboratory opened in 2031.",
]


def _entry(
    content: str,
    *,
    agent_id: str = "opencode",
    project_id: str | None = None,
    session_id: str | None = None,
    confidence: float = 0.7,
    memory_id: str | None = None,
) -> MemoryEntry:
    scope = MemoryScope(
        agent=AgentIdentity.create(agent_id=agent_id),
        project=(
            ProjectIdentity.create(project_id=project_id, name=project_id)
            if project_id
            else None
        ),
        session=SessionIdentity.create(
            session_id=session_id, project_id=project_id or "", agent_id=agent_id
        )
        if session_id
        else None,
    )
    return MemoryEntry(
        memory_id=memory_id or f"mem_{abs(hash(content)) % 10**12:012d}",
        content=content,
        kind=MemoryKind.EPISODIC,
        scope=scope,
        timestamp=1000.0,
        confidence=confidence,
    )


def _manager_with(contents: list[str], **entry_kwargs) -> MemoryManager:
    manager = MemoryManager()
    for i, text in enumerate(contents):
        manager.store_memory(_entry(text, memory_id=f"mem_{i:04d}", **entry_kwargs))
    return manager


def _ask(
    manager: MemoryManager,
    query: str,
    *,
    project_id: str | None = None,
    session_id: str | None = None,
    limit: int = 10,
    minimum_confidence: float = 0.0,
    context_budget: int = 4096,
) -> list[str]:
    request = MemoryRequest(
        agent=AgentIdentity.create(agent_id="opencode"),
        query=query,
        project=(
            ProjectIdentity.create(project_id=project_id, name=project_id)
            if project_id
            else None
        ),
        session=SessionIdentity.create(
            session_id=session_id, project_id=project_id or "", agent_id="opencode"
        )
        if session_id
        else None,
        limit=limit,
        minimum_confidence=minimum_confidence,
        context_budget=context_budget,
    )
    response = manager.request_memory(request)
    return [m.content for m in response.memories]


def _score(query: str, content: str, extractor: FeatureExtractor) -> float:
    """Direct TF-IDF cosine score (measurement helper for reports)."""
    return cosine_similarity(
        extractor.transform(query), extractor.transform(content), extractor
    )


# ---------------------------------------------------------------------------
# §5 / §17 Test 1 — natural-language questions
# ---------------------------------------------------------------------------


class TestNaturalLanguageQuestions:
    def test_question_when_commissioned(self) -> None:
        manager = _manager_with(ORION_FACTS)
        results = _ask(manager, "When was ORION-47 commissioned?")
        assert results, "NL question returned nothing"
        assert results[0] == ORION_FACTS[0], f"wrong top result: {results[0]}"

    def test_all_six_section5_questions_retrieve(self) -> None:
        manager = _manager_with(ORION_FACTS)
        cases = {
            "When was ORION-47 commissioned?": ORION_FACTS[0],
            "What year did ORION-47 enter service?": ORION_FACTS[0],
            "Where is ORION-47 based?": ORION_FACTS[1],
            "What is the vessel's home port?": ORION_FACTS[1],
            "How many docking platforms does Northglass have?": ORION_FACTS[2],
            "Who commands the vessel?": ORION_FACTS[3],
        }
        for query, expected in cases.items():
            results = _ask(manager, query)
            assert results, f"query returned nothing: {query}"
            assert expected in results, (
                f"expected memory not retrieved for {query!r}: {results}"
            )

    def test_rank1_for_lexically_overlapping_questions(self) -> None:
        manager = _manager_with(ORION_FACTS)
        # These share lexical tokens with their target fact -> rank 1.
        rank1_cases = {
            "When was ORION-47 commissioned?": ORION_FACTS[0],
            "What is the vessel's home port?": ORION_FACTS[1],
            "How many docking platforms does Northglass have?": ORION_FACTS[2],
            "Who commands the vessel?": ORION_FACTS[3],
        }
        for query, expected in rank1_cases.items():
            results = _ask(manager, query)
            assert results[0] == expected, (
                f"rank1 mismatch for {query!r}: got {results[0]!r}"
            )


# ---------------------------------------------------------------------------
# §6 — exact match regression
# ---------------------------------------------------------------------------


class TestExactMatchRegression:
    def test_exact_queries_still_work(self) -> None:
        manager = _manager_with(ORION_FACTS)
        exact_cases = {
            "ORION-47": ORION_FACTS,
            "Northglass": ORION_FACTS,
            "2087": [ORION_FACTS[0]],
            "Elian Voss": [ORION_FACTS[3]],
        }
        for query, allowed in exact_cases.items():
            results = _ask(manager, query)
            assert results, f"exact query returned nothing: {query}"
            assert results[0] in allowed, f"exact query {query!r} ranked {results[0]!r}"

    def test_exact_query_top_result_contains_token(self) -> None:
        manager = _manager_with(ORION_FACTS)
        results = _ask(manager, "ORION-47")
        assert "ORION-47" in results[0]


# ---------------------------------------------------------------------------
# §7 — paraphrase
# ---------------------------------------------------------------------------


class TestParaphrase:
    STORED = "The spacecraft launched from the northern platform in 2047."

    def test_paraphrase_retrieved(self) -> None:
        manager = _manager_with([self.STORED])
        queries = [
            "Where did the spacecraft launch?",
            "Which platform was used for launch?",
            "What was the launch site?",
            "When did the launch occur?",
        ]
        for query in queries:
            results = _ask(manager, query)
            assert self.STORED in results, f"paraphrase not retrieved: {query!r}"

    def test_overlapping_paraphrase_scores_positive(self) -> None:
        extractor = FeatureExtractor()
        score = _score("Which platform did the spacecraft use?", self.STORED, extractor)
        assert score > 0.0, "overlapping paraphrase should score > 0"

    def test_zero_overlap_paraphrase_still_returned(self) -> None:
        # Known limitation of lexical TF-IDF: zero lexical overlap => score 0.0,
        # but the memory must still be RETRIEVED (not lost).
        manager = _manager_with([self.STORED])
        results = _ask(manager, "What was the launch site?")
        assert self.STORED in results
        extractor = FeatureExtractor()
        assert _score("What was the launch site?", self.STORED, extractor) == 0.0


# ---------------------------------------------------------------------------
# §8 — distractor resistance
# ---------------------------------------------------------------------------


class TestDistractorResistance:
    def test_relevant_outranks_distractors(self) -> None:
        manager = _manager_with(DISTRACTORS + ORION_FACTS)
        query = "When was ORION-47 commissioned?"
        start = time.perf_counter()
        results = _ask(manager, query)
        latency_ms = (time.perf_counter() - start) * 1000

        assert ORION_FACTS[0] in results, "relevant memory missing"
        assert results[0] == ORION_FACTS[0], (
            f"relevant memory not rank 1: {results[0]!r}"
        )
        assert latency_ms < 1000.0, f"recall latency too high: {latency_ms:.1f}ms"

    def test_scores_measured(self) -> None:
        extractor = FeatureExtractor()
        query = "When was ORION-47 commissioned?"
        relevant = _score(query, ORION_FACTS[0], extractor)
        distractor_scores = [_score(query, d, extractor) for d in DISTRACTORS]
        assert relevant > max(distractor_scores), (
            f"relevant score {relevant} not above distractors {distractor_scores}"
        )


# ---------------------------------------------------------------------------
# §9 — multiple relevant memories, deterministic order
# ---------------------------------------------------------------------------


class TestMultipleRelevant:
    HISTORY = [
        "ORION-47 was commissioned in 2087.",
        "ORION-47 launched its first mission in 2090.",
        "ORION-47 was upgraded in 2094.",
    ]

    def test_multiple_relevant_returned(self) -> None:
        manager = _manager_with(self.HISTORY + DISTRACTORS)
        results = _ask(manager, "Tell me about the history of ORION-47.", limit=10)
        for memory in self.HISTORY:
            assert memory in results, f"missing history memory: {memory}"
        # All three history memories must outrank every distractor.
        last_history_pos = max(results.index(m) for m in self.HISTORY)
        for distractor in DISTRACTORS:
            if distractor in results:
                assert results.index(distractor) > last_history_pos, (
                    f"distractor outranked history: {distractor}"
                )

    def test_deterministic_ordering(self) -> None:
        manager = _manager_with(self.HISTORY + DISTRACTORS)
        runs = [
            _ask(manager, "Tell me about the history of ORION-47.", limit=10)
            for _ in range(5)
        ]
        assert all(run == runs[0] for run in runs), f"non-deterministic: {runs}"


# ---------------------------------------------------------------------------
# §10 — project isolation with semantic queries
# ---------------------------------------------------------------------------


class TestProjectIsolation:
    def test_semantic_query_does_not_cross_projects(self) -> None:
        manager = MemoryManager()
        manager.store_memory(
            _entry(
                "The project spacecraft is called ORION-47.",
                project_id="project-A",
                memory_id="mem_proj_a",
            )
        )
        manager.store_memory(
            _entry(
                "The project spacecraft is called VEGA-12.",
                project_id="project-B",
                memory_id="mem_proj_b",
            )
        )
        results = _ask(
            manager,
            "What is the project spacecraft called?",
            project_id="project-A",
        )
        assert results == ["The project spacecraft is called ORION-47."]

    def test_cross_project_empty_when_other_project_only(self) -> None:
        manager = MemoryManager()
        manager.store_memory(
            _entry("The project spacecraft is called VEGA-12.", project_id="project-B")
        )
        results = _ask(manager, "What is the project spacecraft called?", project_id="project-A")
        assert results == []


# ---------------------------------------------------------------------------
# §11 — session isolation with semantic queries (R3 unchanged)
# ---------------------------------------------------------------------------


class TestSessionIsolation:
    def test_semantic_query_does_not_cross_sessions(self) -> None:
        manager = MemoryManager()
        manager.store_memory(
            _entry(
                "The docking code is BLUEWATER-9.",
                project_id="p1",
                session_id="s1",
                memory_id="mem_s1",
            )
        )
        manager.store_memory(
            _entry(
                "The docking code is EMBERFIELD-3.",
                project_id="p1",
                session_id="s2",
                memory_id="mem_s2",
            )
        )
        results = _ask(
            manager,
            "What is the docking code?",
            project_id="p1",
            session_id="s1",
        )
        assert results == ["The docking code is BLUEWATER-9."]

    def test_inaccessible_session_semantic_match_excluded(self) -> None:
        manager = MemoryManager()
        manager.store_memory(
            _entry(
                "The docking code is BLUEWATER-9.",
                project_id="p1",
                session_id="s1",
            )
        )
        results = _ask(
            manager,
            "What is the docking code?",
            project_id="p1",
            session_id="s2",
        )
        assert results == [], "session scope bypassed by semantic ranking"


# ---------------------------------------------------------------------------
# §12 — confidence interaction
# ---------------------------------------------------------------------------


class TestConfidencePreserved:
    def test_confidence_filter_applies_before_semantic_ranking(self) -> None:
        manager = MemoryManager()
        # Best lexical match has LOW confidence; weaker match has HIGH.
        manager.store_memory(
            _entry(ORION_FACTS[0], confidence=0.2, memory_id="mem_low")
        )
        manager.store_memory(
            _entry("ORION-47 exists.", confidence=0.9, memory_id="mem_high")
        )
        results = _ask(manager, "When was ORION-47 commissioned?", minimum_confidence=0.5)
        assert results == ["ORION-47 exists."], (
            "minimum_confidence not applied to semantic candidates"
        )

    def test_confidence_values_not_inflated(self) -> None:
        manager = _manager_with(ORION_FACTS)
        request = MemoryRequest(
            agent=AgentIdentity.create(agent_id="opencode"),
            query="When was ORION-47 commissioned?",
        )
        response = manager.request_memory(request)
        assert response.memories
        for memory in response.memories:
            assert memory.confidence == 0.7, "confidence mutated by retrieval"


# ---------------------------------------------------------------------------
# §14 — fallback (existing substring path intact when no extractor)
# ---------------------------------------------------------------------------


class TestFallbackBehavior:
    def test_store_substring_fallback_without_extractor(self) -> None:
        store = MemoryStore()
        store.store(_entry(ORION_FACTS[0]))
        # Legacy branch: whole-query substring (unchanged behavior).
        assert store.query(query_text="commissioned") != []
        assert store.query(query_text="When was ORION-47 commissioned?") == []

    def test_store_semantic_branch_with_extractor(self) -> None:
        store = MemoryStore()
        store.store(_entry(ORION_FACTS[0]))
        results = store.query(
            query_text="When was ORION-47 commissioned?",
            extractor=FeatureExtractor(),
        )
        assert len(results) == 1

    def test_manager_default_uses_extractor(self) -> None:
        manager = _manager_with(ORION_FACTS)
        assert getattr(manager, "_extractor", None) is not None, (
            "MemoryManager must own a feature extractor"
        )


# ---------------------------------------------------------------------------
# §15 — context budget and limit still enforced after ranking
# ---------------------------------------------------------------------------


class TestBudgetAndLimit:
    def test_context_budget_enforced_after_semantic_ranking(self) -> None:
        long_facts = [f"{text} " + ("detail " * 100) for text in ORION_FACTS]
        manager = _manager_with(long_facts)
        request = MemoryRequest(
            agent=AgentIdentity.create(agent_id="opencode"),
            query="ORION-47 history",
            context_budget=60,
        )
        response = manager.request_memory(request)
        assert response.context_cost <= 60
        assert response.truncated or len(response.memories) < len(long_facts)

    def test_limit_enforced_after_semantic_ranking(self) -> None:
        manager = _manager_with(ORION_FACTS + DISTRACTORS)
        results = _ask(manager, "Tell me about ORION-47.", limit=2)
        assert len(results) <= 2


# ---------------------------------------------------------------------------
# §13 — determinism (same query, same state)
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_identical_ids_order_scores(self) -> None:
        manager = _manager_with(ORION_FACTS + DISTRACTORS)
        request_factory = lambda: MemoryRequest(  # noqa: E731
            agent=AgentIdentity.create(agent_id="opencode"),
            query="When was ORION-47 commissioned?",
        )
        provenances = [
            manager.request_memory(request_factory()).provenance
            for _ in range(5)
        ]
        assert all(p == provenances[0] for p in provenances)


# ---------------------------------------------------------------------------
# §17 Test 7 — persistence + semantic retrieval through real bridge processes
# ---------------------------------------------------------------------------


def _bridge(req: dict) -> dict:
    proc = subprocess.run(
        [sys.executable, "-m", "teacher.bridge"],
        input=json.dumps(req),
        capture_output=True,
        text=True,
        timeout=60,
        cwd=REPO_ROOT,
    )
    assert proc.returncode == 0, f"bridge failed: {proc.stderr}"
    return json.loads(proc.stdout)


class TestPersistencePlusSemanticRecall:
    def test_learn_process_death_nl_recall(self, tmp_path) -> None:
        worktree = str(tmp_path)
        learn = _bridge({
            "command": "learn",
            "worktree": worktree,
            "agent": "opencode",
            "project": "r2-project",
            "session": "ses_r2_a",
            "content": ORION_FACTS[0],
            "outcome": "SUCCESS",
        })
        assert learn.get("ok") is True, learn
        assert learn["result"]["stored"] is True, learn

        # Fresh process: natural-language recall of the durable memory.
        recall = _bridge({
            "command": "recall",
            "worktree": worktree,
            "agent": "opencode",
            "project": "r2-project",
            "session": "ses_r2_a",
            "query": "When was ORION-47 commissioned?",
        })
        assert recall.get("ok") is True, recall
        assert recall["total"] >= 1, (
            f"NL recall after process death found nothing: {recall}"
        )
        assert "ORION-47" in recall["memories"][0]["content"]

    def test_nl_recall_cross_session_still_blocked(self, tmp_path) -> None:
        """R3 unchanged: semantic retrieval must not bypass session scope."""
        worktree = str(tmp_path)
        _bridge({
            "command": "learn",
            "worktree": worktree,
            "agent": "opencode",
            "project": "r2-project",
            "session": "ses_r2_b",
            "content": ORION_FACTS[0],
            "outcome": "SUCCESS",
        })
        recall = _bridge({
            "command": "recall",
            "worktree": worktree,
            "agent": "opencode",
            "project": "r2-project",
            "session": "ses_r2_OTHER",
            "query": "When was ORION-47 commissioned?",
        })
        assert recall.get("ok") is True, recall
        assert recall["total"] == 0, "session scope bypassed via semantic recall"
