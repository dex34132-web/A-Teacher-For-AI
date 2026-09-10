"""Deterministic test datasets for benchmarking the SimilarityLearner.

Each dataset is designed to test a specific capability of the learner.
All inputs are carefully chosen so that TF-IDF similarity can discriminate
between categories, while still requiring the learner to generalize.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Dataset:
    """A benchmark dataset.

    Attributes:
        name: Human-readable dataset name.
        description: What this dataset tests.
        training: Input-output pairs for training.
        test_known: Inputs seen during training (test memorization).
        test_unseen: Related but unseen inputs (test generalization).
    """

    name: str
    description: str
    training: list[tuple[str, str]]
    test_known: list[tuple[str, str]]
    test_unseen: list[tuple[str, str]]


# ---------------------------------------------------------------------------
# Dataset 1: Basic Classification
# ---------------------------------------------------------------------------

BASIC_CLASSIFICATION = Dataset(
    name="Basic Classification",
    description="Python concepts mapped to categories. Tests core classification.",
    training=[
        ("create a list of numbers", "list"),
        ("append item to list", "list"),
        ("iterate over list elements", "list"),
        ("list comprehension filter", "list"),
        ("sort a list in place", "list"),
        ("create a dictionary mapping", "dict"),
        ("lookup key in dictionary", "dict"),
        ("dictionary merge two dicts", "dict"),
        ("iterate over dictionary items", "dict"),
        ("dictionary comprehension", "dict"),
        ("concatenate two strings", "string"),
        ("string split by delimiter", "string"),
        ("format string with variables", "string"),
        ("string replace substring", "string"),
        ("uppercase a string", "string"),
        ("read file contents", "file_io"),
        ("write data to file", "file_io"),
        ("open file with context manager", "file_io"),
        ("check if file exists", "file_io"),
        ("list files in directory", "file_io"),
        ("define a function with parameters", "function"),
        ("call a function with args", "function"),
        ("return value from function", "function"),
        ("lambda function one liner", "function"),
        ("recursive function call", "function"),
    ],
    test_known=[
        ("create a list of numbers", "list"),
        ("concatenate two strings", "string"),
        ("lookup key in dictionary", "dict"),
    ],
    test_unseen=[
        ("remove item from list", "list"),
        ("filter list by condition", "list"),
        ("access dictionary value", "dict"),
        ("update dictionary key", "dict"),
        ("trim whitespace from string", "string"),
        ("check string contains substring", "string"),
        ("save data to a file", "file_io"),
        ("open and read a file", "file_io"),
        ("define function without arguments", "function"),
        ("nested function definition", "function"),
    ],
)

# ---------------------------------------------------------------------------
# Dataset 2: Similarity Test
# ---------------------------------------------------------------------------

SIMILARITY = Dataset(
    name="Similarity Groups",
    description="Related concepts in groups. Tests retrieval of similar examples.",
    training=[
        # Group: database operations
        ("query database for users", "database"),
        ("insert record into table", "database"),
        ("update row in database", "database"),
        ("delete entry from database", "database"),
        # Group: HTTP requests
        ("send GET request to API", "http"),
        ("POST json data to endpoint", "http"),
        ("check HTTP response status", "http"),
        ("set request headers", "http"),
        # Group: unit testing
        ("write test for function", "testing"),
        ("assert expected output", "testing"),
        ("mock external dependency", "testing"),
        ("run test suite", "testing"),
    ],
    test_known=[
        ("query database for users", "database"),
        ("send GET request to API", "http"),
    ],
    test_unseen=[
        ("fetch data from database", "database"),
        ("make HTTP call to server", "http"),
        ("create unit test case", "testing"),
        ("verify function output", "testing"),
    ],
)

# ---------------------------------------------------------------------------
# Dataset 3: Adaptation Test
# ---------------------------------------------------------------------------

ADAPTATION_TRAINING = Dataset(
    name="Adaptation - Initial",
    description="Initial mapping before answer changes.",
    training=[
        ("sort the list", "use sorted built-in"),
        ("count occurrences", "use collections.Counter"),
        ("read csv file", "use csv module"),
        ("parse json string", "use json.loads"),
        ("generate random number", "use random.randint"),
    ],
    test_known=[],
    test_unseen=[],
)

ADAPTATION_CHANGED = [
    ("sort the list", "use list.sort with key"),
    ("count occurrences", "use manual dict counting"),
    ("read csv file", "use pandas read_csv"),
    ("parse json string", "use rapidjson parser"),
    ("generate random number", "use secrets module"),
]

# ---------------------------------------------------------------------------
# Dataset 4: Regression Test
# ---------------------------------------------------------------------------

REGRESSION_LEARNING_ORDER = [
    # Phase 1: Learn category A
    ("binary search algorithm", "search"),
    ("linear search through array", "search"),
    ("hash table lookup", "search"),
    # Phase 2: Learn category B (should not break A)
    ("bubble sort algorithm", "sort"),
    ("merge sort implementation", "sort"),
    ("quick sort partition", "sort"),
    # Phase 3: Learn category C (should not break A or B)
    ("breadth first search", "graph"),
    ("depth first traversal", "graph"),
    ("dijkstra shortest path", "graph"),
]

REGRESSION_TEST_AFTER_ALL = [
    ("binary search algorithm", "search"),
    ("linear search through array", "search"),
    ("bubble sort algorithm", "sort"),
    ("merge sort implementation", "sort"),
    ("breadth first search", "graph"),
    ("depth first traversal", "graph"),
]

REGRESSION_TEST_UNSEEN = [
    ("hash map key lookup", "search"),
    ("insertion sort algorithm", "sort"),
    ("dijkstra path finding", "graph"),
]


def get_all_datasets() -> list[Dataset]:
    """Return the standard benchmark datasets."""
    return [
        BASIC_CLASSIFICATION,
        SIMILARITY,
    ]
