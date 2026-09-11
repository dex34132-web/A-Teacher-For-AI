# ADR: EVO V2.5 — Universal Agent Routing & Intelligence Layer

## Status

Accepted — V2.5 Implementation Complete

## Context

EVO V2.4.2 was a direct-consumption learning engine: harness adapters fed information directly to learning subsystems. This worked for self-learning but created a 1:1 coupling between each harness and EVO's internals.

As EVO matures, it needs to connect to **any AI system** — not just harness adapters, but agents, copilots, assistants, tools, IDEs, CLIs. Each system produces different information types, has different priority needs, and requires different security boundaries.

The question: **How do we make EVO universal without rebuilding all subsystems?**

## Decision

Implement a **universal, agent-agnostic routing and intelligence layer** (V2.5) that sits between any AI system and EVO's existing subsystems.

**Core principle**: Let the agent do the semantic thinking. Let EVO make the routing structured, efficient, safe, explainable, and cheap.

### Key design choices:

1. **Frozen InformationPacket** — Immutable, typed information units prevent mutation bugs and enable safe caching
2. **14 InformationTypes** — Comprehensive classification covers all agent output patterns
3. **9-stage RoutingPipeline** — Deterministic pipeline with security checks at every stage
4. **13 pre-built destinations** — Maps to existing V2.4.2 subsystems + extensible for V2.6+
5. **Agent protocol** — `< 100 token` protocol prompt, JSON-serializable intents
6. **Cost model** — Token, latency, processing, context-pollution estimation
7. **Scope isolation** — Cache and batching respect project/session boundaries
8. **Security first** — Injection detection, instruction/data boundary, policy enforcement
9. **V2.6 contracts declared** — ABC contracts for future implementation without blocking V2.5
10. **Integration bridge** — Convenience methods to connect V2.5 routing to V2.4.2 subsystems

## Consequences

### Positive
- Any AI system can connect to EVO through a standard protocol
- V2.4.2 subsystems remain untouched and frozen
- Security is enforced at the routing layer, not per-adapter
- Cost tracking enables budget management
- Provenance tracking enables explainability
- Scope isolation prevents cross-project contamination

### Negative
- Adds a routing layer between agent and EVO (latency: ~0.77ms per route)
- Requires agents to adopt the protocol (or use the integration bridge)
- 17 new files in `core/routing/`

### Risks
- Mitigated: All V2.4.2 tests still pass (backward compatibility verified)
- Mitigated: 146 V2.5 tests cover functional, safety, adversarial, scalability
- Mitigated: Frozen dataclasses prevent mutation bugs

## Alternatives Considered

1. **Per-adapter integration** — Rejected: doesn't scale, N adapters × M subsystems
2. **Message queue** — Rejected: adds infrastructure dependency, overkill for current scale
3. **Graph-based routing** — Rejected: too complex for current needs, future option
4. **No routing layer** — Rejected: doesn't enable universal connectivity

## Evidence

- 146/146 V2.5 tests pass in 0.38s
- 85 V2.4.2 certification tests still pass (backward compatibility)
- Pipeline throughput: ~1,300 packets/second
- Cache hit rate: 85%+ for typical interactions
- Security: 13 injection patterns detected, instruction boundary enforced
- All bounded subsystems (cache, telemetry, provenance, context) have configurable max sizes
