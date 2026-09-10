"""Semantic benchmark datasets for Phase 2 evaluation.

These datasets are specifically designed to test semantic understanding:
- Paraphrases: Same meaning, different words
- Synonyms: Different words with same meaning
- Different wording: Concept expressed in completely different terms
- Related-but-different: Semantically close but different answers
- Unrelated: Completely different topics

The key metric: V2 (semantic) should outperform V1 (TF-IDF) on these
datasets, especially on paraphrase and synonym tasks where lexical
overlap is low but meaning is preserved.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SemanticDataset:
    """A benchmark dataset targeting semantic understanding.

    Attributes:
        name: Human-readable name.
        description: What this dataset tests.
        training: Input-output pairs for training.
        test_paraphrase: Same concept, different wording (test paraphrase).
        test_synonym: Different words, same meaning.
        test_unrelated: Completely different topics.
    """

    name: str
    description: str
    training: list[tuple[str, str]]
    test_paraphrase: list[tuple[str, str]]
    test_synonym: list[tuple[str, str]]
    test_unrelated: list[tuple[str, str]]


# ---------------------------------------------------------------------------
# Dataset 1: Code Tasks with Paraphrases
# ---------------------------------------------------------------------------

CODE_PARAPHRASES = SemanticDataset(
    name="Code Paraphrases",
    description=(
        "Programming tasks where training and test use different phrasing "
        "for the same concept. Tests if learner recognizes paraphrases."
    ),
    training=[
        ("add element to a list", "list operations"),
        ("remove item from list", "list operations"),
        ("sort list by value", "list operations"),
        ("find item in dictionary", "dict operations"),
        ("create new dictionary entry", "dict operations"),
        ("merge two dictionaries", "dict operations"),
        ("read text from file", "file operations"),
        ("write content to file", "file operations"),
        ("check if file exists", "file operations"),
        ("convert string to lowercase", "string operations"),
        ("split string by comma", "string operations"),
        ("join list into string", "string operations"),
        ("send HTTP GET request", "http operations"),
        ("post JSON data", "http operations"),
        ("parse JSON response", "http operations"),
    ],
    test_paraphrase=[
        ("append item to a list", "list operations"),        # paraphrase
        ("delete entry from dictionary", "dict operations"), # paraphrase
        ("open and read a text file", "file operations"),    # paraphrase
        ("make lowercase string", "string operations"),       # paraphrase
        ("perform GET request to server", "http operations"),# paraphrase
    ],
    test_synonym=[
        ("insert element into array", "list operations"),    # synonym: array≈list
        ("lookup key in map", "dict operations"),             # synonym: map≈dictionary
        ("retrieve file contents", "file operations"),        # synonym: retrieve≈read
        ("downcase text", "string operations"),               # synonym: downcase≈lowercase
        ("issue GET to API endpoint", "http operations"),     # synonym: issue≈send
    ],
    test_unrelated=[
        ("sort the database table", "database operations"),  # different topic
        ("run unit test suite", "testing operations"),        # different topic
        ("deploy application to server", "deployment"),       # different topic
        ("configure logging level", "configuration"),         # different topic
        ("calculate average of numbers", "math operations"),  # different topic
    ],
)

# ---------------------------------------------------------------------------
# Dataset 2: Natural Language Tasks
# ---------------------------------------------------------------------------

NATURAL_LANGUAGE = SemanticDataset(
    name="Natural Language Paraphrases",
    description=(
        "Everyday tasks expressed in varied natural language. "
        "Tests paraphrase and synonym recognition."
    ),
    training=[
        ("how do I make a phone call", "communication"),
        ("send a text message", "communication"),
        ("write an email to someone", "communication"),
        ("find a restaurant nearby", "search"),
        ("look up a recipe online", "search"),
        ("search for movie showtimes", "search"),
        ("set an alarm for morning", "scheduling"),
        ("create a calendar reminder", "scheduling"),
        ("plan a meeting with team", "scheduling"),
        ("check the weather forecast", "information"),
        ("get directions to airport", "information"),
        ("find current stock price", "information"),
    ],
    test_paraphrase=[
        ("place a phone call", "communication"),             # paraphrase
        ("compose an email message", "communication"),       # paraphrase
        ("discover nearby eateries", "search"),              # paraphrase
        ("schedule a team meeting", "scheduling"),           # paraphrase
        ("check today's weather", "information"),            # paraphrase
    ],
    test_synonym=[
        ("ring someone up", "communication"),                # synonym: ring≈call
        ("browse for cooking instructions", "search"),       # synonym
        ("set a timer for dawn", "scheduling"),              # synonym: timer≈alarm, dawn≈morning
        ("look up weather report", "information"),           # synonym: look up≈check
        ("get a ride to the airport", "information"),        # related but different
    ],
    test_unrelated=[
        ("fix a flat tire", "maintenance"),                  # different topic
        ("cook pasta al dente", "cooking"),                  # different topic
        ("train for a marathon", "fitness"),                 # different topic
        ("assemble furniture pieces", "assembly"),           # different topic
        ("plan a birthday party", "planning"),               # different topic
    ],
)

# ---------------------------------------------------------------------------
# Dataset 3: Technical Tasks with Varied Wording
# ---------------------------------------------------------------------------

TECHNICAL_VARIED = SemanticDataset(
    name="Technical Varied Wording",
    description=(
        "Technical tasks where training and test use very different "
        "wording for the same concept. Stresses semantic understanding."
    ),
    training=[
        ("deploy microservice to kubernetes", "deployment"),
        ("containerize application with docker", "deployment"),
        ("set up continuous integration pipeline", "devops"),
        ("configure automated testing", "devops"),
        ("monitor application performance", "monitoring"),
        ("collect system metrics", "monitoring"),
        ("set up alerting rules", "monitoring"),
        ("optimize database queries", "optimization"),
        ("cache frequently accessed data", "optimization"),
        ("reduce API response latency", "optimization"),
    ],
    test_paraphrase=[
        ("release service on k8s cluster", "deployment"),    # paraphrase: k8s≈kubernetes
        ("dockerize the application", "deployment"),          # paraphrase
        ("establish CI/CD workflow", "devops"),               # paraphrase
        ("gather infrastructure metrics", "monitoring"),      # paraphrase
        ("speed up endpoint response times", "optimization"),# paraphrase
    ],
    test_synonym=[
        ("roll out containerized app", "deployment"),        # synonym: roll out≈deploy
        ("implement continuous delivery", "devops"),          # synonym: delivery≈integration
        ("observe service health", "monitoring"),             # synonym: observe≈monitor
        ("improve query execution speed", "optimization"),   # synonym: improve≈optimize
        ("add in-memory caching layer", "optimization"),     # synonym: in-memory≈cache
    ],
    test_unrelated=[
        ("write documentation for API", "documentation"),    # different topic
        ("set up access control rules", "security"),         # different topic
        ("migrate data to new schema", "migration"),         # different topic
        ("configure backup schedule", "operations"),         # different topic
        ("review pull request code", "review"),              # different topic
    ],
)

# ---------------------------------------------------------------------------
# Dataset 4: Mixed Difficulty (hard negatives)
# ---------------------------------------------------------------------------

MIXED_DIFFICULTY = SemanticDataset(
    name="Mixed Difficulty Hard Negatives",
    description=(
        "Training and test with varying difficulty. Includes easy "
        "paraphrases, hard synonyms, and tricky related-but-different pairs."
    ),
    training=[
        ("start a web server", "server"),
        ("listen on port 8080", "server"),
        ("handle incoming connections", "server"),
        ("process HTTP requests", "server"),
        ("create a database table", "database"),
        ("define schema columns", "database"),
        ("insert rows into table", "database"),
        ("query with SQL SELECT", "database"),
        ("run unit test assertions", "testing"),
        ("verify expected behavior", "testing"),
        ("check test coverage report", "testing"),
        ("mock external API calls", "testing"),
    ],
    test_paraphrase=[
        ("launch a web server process", "server"),           # paraphrase
        ("bind to port 8080", "server"),                      # paraphrase
        ("establish new table in DB", "database"),           # paraphrase
        ("execute SELECT statement", "database"),            # paraphrase
        ("validate function behavior", "testing"),           # paraphrase
    ],
    test_synonym=[
        ("spin up HTTP daemon", "server"),                   # synonym: spin up≈start, daemon≈server
        ("examine SQL query results", "database"),           # synonym: examine≈query
        ("assert expected outcomes", "testing"),             # synonym
        ("monitor code coverage", "testing"),                # synonym: monitor≈check
        ("stub remote service calls", "testing"),            # synonym: stub≈mock, remote≈external
    ],
    test_unrelated=[
        ("compress image file size", "optimization"),        # related but different category
        ("encrypt user passwords", "security"),              # different topic
        ("schedule background jobs", "scheduling"),          # different topic
        ("parse command line arguments", "cli"),             # different topic
        ("format output as JSON", "serialization"),          # different topic
    ],
)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def get_all_semantic_datasets() -> list[SemanticDataset]:
    """Return all semantic benchmark datasets."""
    return [
        CODE_PARAPHRASES,
        NATURAL_LANGUAGE,
        TECHNICAL_VARIED,
        MIXED_DIFFICULTY,
    ]
