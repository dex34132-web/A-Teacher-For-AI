# Benchmarks

Performance benchmarks for the AI Learning Engine core components.

## Running Benchmarks

```bash
pytest tests/benchmarks/ -v --benchmark-only
```

## Adding a Benchmark

1. Create a new file `tests/benchmarks/test_<component>.py`
2. Use `pytest-benchmark` fixtures for timing
3. Keep benchmarks focused on a single operation
4. Record baseline results in `benchmarks/baselines/`
