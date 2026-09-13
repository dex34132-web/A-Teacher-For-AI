"""Tool factory helpers — creates tool instances with shared dependencies."""
from __future__ import annotations
from core.learner.feature_extractor import FeatureExtractor
from core.routing.v26.memory_manager import MemoryManager
from core.routing.v26.memory_store import MemoryStore
from core.routing.v26.tools.status import StatusTool
from core.routing.v26.tools.remember import RememberTool
from core.routing.v26.tools.recall import RecallTool
from core.routing.v26.tools.conflict import ConflictDetectionTool
from core.routing.v26.tools.confidence import ConfidenceTool
from core.routing.v26.tools.semantic_search import SemanticSearchTool
from core.routing.v26.tools.deduplicate import DeduplicateTool
from core.routing.v26.tools.knowledge import KnowledgeExtractionTool
from core.routing.v26.tools.lifecycle import LifecycleTool
from core.routing.v26.tools.diagnose import DiagnoseTool

def create_tools(extractor: FeatureExtractor | None = None) -> list:
    manager = MemoryManager()
    store = MemoryStore()
    if extractor is None:
        extractor = FeatureExtractor()
    return [
        StatusTool(),
        RememberTool(manager=manager),
        RecallTool(manager=manager),
        ConflictDetectionTool(manager=manager),
        ConfidenceTool(),
        SemanticSearchTool(store=store, extractor=extractor),
        DeduplicateTool(store=store, extractor=extractor),
        KnowledgeExtractionTool(manager=manager),
        LifecycleTool(manager=manager),
        DiagnoseTool(manager=manager),
    ]
