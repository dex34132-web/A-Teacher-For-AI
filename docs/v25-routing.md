# EVO V2.5 — Universal Agent Routing & Intelligence Layer

## Overview

EVO V2.5 introduces a **universal, agent-agnostic routing and intelligence layer** that transforms EVO from a direct-consumption learning engine into a **universal intelligence routing system**. It connects any AI system (agents, copilots, assistants, tools, IDEs, CLIs) to EVO's learning, knowledge, and lifecycle subsystems through a structured, efficient, safe, and explainable routing layer.

**Core principle**: Let the agent do the semantic thinking. Let EVO make the routing structured, efficient, safe, explainable, and cheap.

## Architecture

```
Any AI System                    EVO V2.5 Universal Router
 ┌─────────────┐              ┌─────────────────────────────────────┐
 │  Agent      │              │  INFORMATION MODEL                  │
 │  (Any AI)   │              │  InformationPacket (frozen, typed)  │
 │             │   Protocol   │  InformationType (14 types)         │
 │  "task done"│─────────────>│  SensitivityLevel (5 levels)        │
 │  "observe"  │              │  SourceType (AGENT/EVO/USER/EXT)    │
 │  "feedback" │              └──────────────┬──────────────────────┘
 └─────────────┘                             │
                                              ▼
                                    ┌─────────────────────────────────────┐
                                    │  ROUTING PIPELINE (9 stages)        │
                                    │                                     │
                                    │  1. Normalize                       │
                                    │  2. Classify                        │
                                    │  3. Scope                           │
                                    │  4. Security Check                  │
                                    │  5. Prioritize                      │
                                    │  6. Cost Estimation                 │
                                    │  7. Policy Evaluation               │
                                    │  8. Destination Selection           │
                                    │  9. Telemetry Recording             │
                                    └──────────────┬──────────────────────┘
                                              │
                                              ▼
                                    ┌─────────────────────────────────────┐
                                    │  DESTINATIONS                       │
                                    │                                     │
                                    │  AGENT_CONTEXT  (immediate)         │
                                    │  EVO_CONTEXT    (immediate)         │
                                    │  LEARNING       (deferred)          │
                                    │  RETRIEVAL      (deferred)          │
                                    │  KNOWLEDGE      (deferred)          │
                                    │  CONFLICT       (deferred)          │
                                    │  CONFIDENCE     (deferred)          │
                                    │  LIFECYCLE      (deferred)          │
                                    │  PROVENANCE     (deferred)          │
                                    │  OBSERVABILITY  (deferred)          │
                                    │  DISCARD        (terminal)          │
                                    │  DEFER          (terminal)          │
                                    │  BATCH          (terminal)          │
                                    │  CUSTOM         (extensible)        │
                                    └─────────────────────────────────────┘
```

## Key Concepts

### InformationPacket (frozen dataclass)

The universal unit of information flowing through the routing system.

```python
InformationPacket(
    content="test suite passed",
    information_type=InformationType.OUTCOME,
    sensitivity=SensitivityLevel.INTERNAL,
    source=SourceType.AGENT,
    priority=Priority.NORMAL.value,
    scope="project_evo",
    metadata={"test_count": 42, "pass_rate": 0.95},
)
```

**Properties**: `id`, `content`, `information_type`, `sensitivity`, `source`, `priority`, `scope`, `metadata`, `timestamp`, `confidence`, `parent_id`, `provenance`, `batch_id`

**Methods**: `is_instruction`, `is_data`, `is_sensitive`, `content_length`, `estimated_tokens`, `extend_provenance()`, `with_parent()`

**Immutability**: All fields are frozen. Use `extend_provenance()` or `with_parent()` for derived copies.

### InformationType (14 types)

| Type | Description |
|------|-------------|
| `INSTRUCTION` | Agent command/directive |
| `TASK` | Task description or assignment |
| `OBSERVATION` | Agent observation or result |
| `DATA` | Raw data payload |
| `OUTCOME` | Task outcome (success/failure) |
| `EVIDENCE` | Supporting evidence or proof |
| `EXPERIENCE` | Agent experience or learning |
| `KNOWLEDGE` | Knowledge artifact |
| `FEEDBACK` | Agent feedback |
| `CONTEXT` | Contextual information |
| `TOOL_RESULT` | Tool execution result |
| `METADATA` | Metadata about something |
| `CONFLICT` | Conflict or disagreement |
| `UNKNOWN` | Unclassified |

### SensitivityLevel (5 levels)

| Level | Value | Description |
|-------|-------|-------------|
| `PUBLIC` | 0 | Non-sensitive, safe for logging |
| `INTERNAL` | 1 | Internal use only |
| `CONFIDENTIAL` | 2 | Restricted access |
| `SENSITIVE` | 3 | Privacy-sensitive data |
| `SECRET` | 4 | Highest sensitivity |

### RoutingPipeline (9 stages)

1. **Normalize** — Ensures all required fields are set, defaults applied
2. **Classify** — Determines `InformationType` if UNKNOWN, validates type
3. **Scope** — Assigns scope if empty, validates scope format
4. **Security Check** — Injection detection, policy enforcement, instruction boundary validation
5. **Prioritize** — Applies priority boosts, validates priority range
6. **Cost Estimation** — Estimates routing cost based on content size and type
7. **Policy Evaluation** — Checks against `SecurityPolicy`, sensitivity limits, blocked patterns
8. **Destination Selection** — Routes to appropriate destinations based on type, priority, cost
9. **Telemetry Recording** — Records routing metrics for observability

### RoutingDecision

```python
RoutingDecision(
    packet_id="uuid",
    destinations=(LEARNING, RETRIEVAL, PROVENANCE),
    strategy=RoutingStrategy.MULTI_DESTINATION,
    priority=Priority.NORMAL,
    cost_estimates=(CostEstimate(...),),
    metadata={},
)
```

**Strategies**: `DIRECT`, `CONDITIONAL`, `DEFERRED`, `BATCHED`, `DISCARD`, `MULTI_DESTINATION`

### Cost Model

```python
CostEstimate(
    cost_type=CostType.TOKEN,
    value=0.001,
    precision=CostPrecision.ESTIMATED,
)
```

**Cost Types**: `TOKEN`, `MODEL_CALL`, `LATENCY`, `PROCESSING`, `CONTEXT_POLLUTION`, `TOOL_CALL`

### UniversalRouter (main entry point)

```python
router = UniversalRouter()

# Route information
decision = router.submit_information(packet)

# Get routing decision without routing
decision = router.request_route(packet)

# Estimate cost
cost = router.estimate_cost(packet)

# Record result
router.record_routing_result(packet_id, success=True)

# Get stats
stats = router.get_stats()

# Clear all state
router.clear()
```

### Agent Protocol

```python
intent = RoutingIntent(
    operation=AgentOperation.REPORT_OUTCOME,
    payload="task completed successfully",
    priority=Priority.HIGH,
    confidence=0.9,
)

# Convert to packet
packet = intent.to_packet()

# Serialize
data = intent.to_dict()
json_str = intent.to_json()

# Parse
intent = RoutingIntent.from_dict(data)
intent = RoutingIntent.from_json(json_str)

# Protocol prompt (<100 tokens)
prompt = format_protocol_prompt()
```

### V2.6 Contracts (declared, not implemented)

```python
class AgentRoutingContract(ABC):
    """Contract for agent-side routing integration."""
    ...

class DestinationHandler(ABC):
    """Contract for destination implementations."""
    ...
```

### V2.4.2 Integration Bridge

```python
bridge = EVOIntegrationBridge()

# Connect to existing subsystems
bridge.connect_learning_memory(hybrid_memory)
bridge.connect_lifecycle(lifecycle_manager)

# Dispatch
bridge.dispatch(packet, decision)
```

## Security

- **Injection detection**: 13 prompt-injection patterns
- **Instruction/data boundary**: Ensures data packets don't contain instructions
- **Policy enforcement**: Sensitivity limits, max content length, blocked patterns
- **Logging redaction**: Sensitive/secret content redacted in logs and telemetry
- **Scope isolation**: Cache and batching respect scope boundaries

## Performance

- **Pipeline throughput**: ~1,300 packets/second (pure Python)
- **Memory bounded**: All subsystems (cache, telemetry, provenance, context) have configurable max sizes
- **Cache hit rate**: 85%+ for typical agent interactions (scope-isolated)
- **No global state**: All routers, caches, bridges are independent instances

## Files

| File | Description |
|------|-------------|
| `core/routing/__init__.py` | Module exports (32 symbols) |
| `core/routing/information.py` | InformationPacket, InformationType, SensitivityLevel, SourceType |
| `core/routing/destinations.py` | DestinationType, Destination, 13 pre-built destinations |
| `core/routing/decision.py` | RoutingDecision, RoutingStrategy, helper constructors |
| `core/routing/cost.py` | CostEstimate, CostType, CostPrecision, estimation helpers |
| `core/routing/priority.py` | Priority (IntEnum), PriorityConfig |
| `core/routing/context.py` | ContextState, ContextBudget |
| `core/routing/security.py` | SecurityPolicy, injection detection, policy enforcement |
| `core/routing/provenance.py` | RoutingProvenance, ProvenanceTracker |
| `core/routing/telemetry.py` | TelemetryEvent, TelemetryRecord, TelemetryRecorder |
| `core/routing/efficiency.py` | EfficiencyController, value/cost estimation |
| `core/routing/cache.py` | RoutingCache, RoutingBatch, BatchEntry |
| `core/routing/pipeline.py` | RoutingPipeline (9-stage pipeline) |
| `core/routing/router.py` | UniversalRouter (main entry point) |
| `core/routing/protocol.py` | AgentOperation, RoutingIntent, protocol prompt |
| `core/routing/contracts.py` | AgentRoutingContract ABC, DestinationHandler ABC |
| `core/routing/integration.py` | EVOIntegrationBridge, convenience handlers |

## Tests

146 comprehensive tests covering:
- Information model (11 tests)
- Enums (3 tests)
- Destinations (4 tests)
- Cost model (5 tests)
- Priority (4 tests)
- Context (7 tests)
- Security (9 tests)
- RoutingDecision (4 tests)
- Efficiency (6 tests)
- Cache and batch (12 tests)
- Provenance (5 tests)
- Telemetry (4 tests)
- Routing pipeline (12 tests)
- UniversalRouter (13 tests)
- Agent protocol (7 tests)
- V2.6 contracts (2 tests)
- Integration bridge (6 tests)
- Backward compatibility (4 tests)
- Adversarial robustness (15 tests)
- Pipeline security (2 tests)
- Scalability (6 tests)
- V2.4.2 integration (2 tests)
- Multi-destination (1 test)
- Global state isolation (3 tests)
- No shared state leakage (2 tests)

Run: `python -m pytest tests/unit/test_routing_v25.py -v`

## V2.5 Boundary (strictly enforced)

**IN SCOPE (V2.5)**:
- Universal agent-agnostic routing
- Information model and classification
- Routing pipeline and destination selection
- Security (injection detection, policy enforcement)
- Cost model and efficiency controller
- Context awareness
- Caching and batching
- Provenance tracking and telemetry
- Agent protocol
- V2.6 contract declarations
- V2.4.2 integration bridge

**OUT OF SCOPE (future versions)**:
- Long-term agent memory (V2.6)
- Persistent agent memory (V2.6)
- Deep agent connection (V2.6)
- Model-specific adapters (V2.7+)
- OpenCode/Claude/Codex/Gemini integration (V2.7+)
- Neural networks, FT1.0
- Real-world agent field testing
