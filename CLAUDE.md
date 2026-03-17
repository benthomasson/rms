# CLAUDE.md

## What This Is

A Reason Maintenance System (RMS) based on Doyle's 1979 Truth Maintenance System (TMS). Tracks beliefs as nodes in a dependency network with automatic retraction cascades and restoration.

## Key Concepts

- **Node**: A belief with a truth value (IN or OUT)
- **Premise**: A node with no justifications — IN by default
- **Justification**: Why a node is believed (SL = all antecedents must be IN; CP = assumptions must be consistent)
- **Retraction cascade**: When a node goes OUT, all dependents whose justifications become invalid also go OUT
- **Restoration**: When a retracted node comes back IN, dependents are automatically recomputed
- **Nogood**: A set of nodes that cannot all be IN simultaneously (contradiction)
- **Multiple justifications**: A node is IN if ANY justification is valid

## Project Structure

```
rms_lib/
  __init__.py    # Node, Justification, Nogood dataclasses
  network.py     # Network class — dependency graph + propagation
  storage.py     # SQLite persistence
  cli.py         # CLI entry point
tests/
  test_network.py  # 30 propagation tests
  test_storage.py  # 9 persistence tests
```

## Commands

```bash
uv run rms init                          # create rms.db
uv run rms add NODE "text" --sl a,b      # add with SL justification
uv run rms add NODE "text" --cp a,b      # add with CP justification
uv run rms add NODE "text"               # add as premise
uv run rms retract NODE                  # mark OUT + cascade
uv run rms assert NODE                   # mark IN + cascade
uv run rms status                        # show all nodes
uv run rms show NODE                     # node details
uv run rms explain NODE                  # trace why IN or OUT
uv run rms nogood A B                    # record contradiction
uv run rms propagate                     # recompute all truth values
uv run rms log                           # propagation history
uv run rms export                        # JSON export
```

## Running Tests

```bash
uv run --extra test pytest tests/ -v
```

## Design Decisions

- SQLite (not markdown) for ACID transactions during propagation cascades
- No STALE status — TMS uses IN/OUT only; staleness triggers retraction
- Retracted nodes stay in DB (Doyle's insight: enables restoration without rederivation)
- BFS propagation ensures all dependents are recomputed when a node changes
