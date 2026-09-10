"""Web access abstraction layer.

Provides provider-agnostic interfaces for web search, content fetching,
GitHub API access, documentation resolution, and source evaluation.
"""

from web.search.base import SearchProvider, SearchQuery, SearchResult
from web.fetch.base import ContentFetcher, FetchRequest, FetchResponse
from web.github.base import GitHubClient, GitHubRepo, GitHubFile
from web.documentation.base import DocResolver, DocQuery, DocResult
from web.source_evaluation.base import SourceEvaluator, SourceAssessment

__all__ = [
    "SearchProvider",
    "SearchQuery",
    "SearchResult",
    "ContentFetcher",
    "FetchRequest",
    "FetchResponse",
    "GitHubClient",
    "GitHubRepo",
    "GitHubFile",
    "DocResolver",
    "DocQuery",
    "DocResult",
    "SourceEvaluator",
    "SourceAssessment",
]
