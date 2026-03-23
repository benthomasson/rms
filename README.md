# Reasons

An implementation of Doyle's (1979) Truth Maintenance System. Tracks beliefs as nodes in a dependency network with automatic retraction cascades and restoration.

## Core Ideas

A **node** is a belief with a truth value: IN (believed) or OUT (retracted). Nodes can be **premises** (believed by default) or **derived** (believed because of justifications).

A **justification** is a reason for believing a node. Type SL (Support List) means the node is IN when all its antecedents are IN. A node can have multiple justifications — it's IN if *any* of them are valid.

When a node goes OUT, all dependents whose justifications become invalid go OUT too — this is the **retraction cascade**. When a retracted node comes back IN, dependents are automatically recomputed — **restoration without rederivation**.

A **nogood** records a contradiction: a set of nodes that cannot all be IN simultaneously. When a nogood is detected, the system uses **dependency-directed backtracking** to trace backward through the justification graph and retract the responsible *premise* with minimal disruption — not an arbitrary node.

Justifications support **non-monotonic reasoning** via the **outlist**: "believe X unless Y is believed." A justification is valid when all inlist nodes are IN *and* all outlist nodes are OUT. This enables default reasoning and **dialectical argumentation** — beliefs can be formally challenged and defended.

## Install

```bash
uv tool install -e ~/git/reasons
```

Or run directly:

```bash
cd ~/git/reasons
uv run reasons <command>
```

## Usage

```bash
# Initialize database
reasons init

# Add premises
reasons add source-uses-langgraph "Source code uses LangGraph" --source "agents-python:src/graph.py"
reasons add graph-has-cycles "Graph contains cycles"

# Add derived nodes with SL justifications
reasons add topology-is-static "Graph topology is static" --sl source-uses-langgraph --label "observed from source"
reasons add no-runtime-modification "No runtime graph modification" --sl topology-is-static

# See what's believed
reasons status
#   [+] graph-has-cycles: Graph contains cycles  (premise)
#   [+] no-runtime-modification: No runtime graph modification  (1 justification)
#   [+] source-uses-langgraph: Source code uses LangGraph  (premise)
#   [+] topology-is-static: Graph topology is static  (1 justification)
#
# 4/4 IN

# Retract a premise — cascade propagates
reasons retract source-uses-langgraph
# Retracted: source-uses-langgraph, topology-is-static, no-runtime-modification

reasons status
#   [+] graph-has-cycles: Graph contains cycles  (premise)
#   [-] no-runtime-modification: No runtime graph modification  (1 justification)
#   [-] source-uses-langgraph: Source code uses LangGraph  (premise)
#   [-] topology-is-static: Graph topology is static  (1 justification)
#
# 1/4 IN

# Restore — dependents come back automatically
reasons assert source-uses-langgraph
# Asserted: source-uses-langgraph, topology-is-static, no-runtime-modification

# Record a contradiction
reasons add graph-is-dynamic "Graph is dynamically modified"
reasons nogood topology-is-static graph-is-dynamic
# Recorded nogood-001: topology-is-static, graph-is-dynamic
# Retracted: graph-is-dynamic

# Explain why a node is IN or OUT
reasons explain no-runtime-modification
#   [+] no-runtime-modification: SL justification valid — antecedents: topology-is-static
#   [+] topology-is-static: SL justification valid — antecedents: source-uses-langgraph [observed from source]
#   [+] source-uses-langgraph: premise

# Show node details
reasons show topology-is-static

# View propagation history
reasons log

# Export as JSON
reasons export

# Import from a beliefs CLI registry
reasons import-beliefs ~/git/physics-pi-meta/beliefs.md
# Imported 39 claims (2 retracted)
# Imported 8 nogoods

# nogoods.md is auto-detected next to beliefs.md, or specify explicitly:
reasons import-beliefs ~/git/physics-pi-meta/beliefs.md --nogoods ~/git/physics-pi-meta/nogoods.md

# After import, cascading works on the imported dependency graph:
reasons retract beliefs-improve-accuracy
# Retracted: beliefs-improve-accuracy, engineering-intuition-unreliable, beliefs-beat-expert-prompting, ...

# Search for nodes
reasons search "tool-use"
#   [+] tool-use-calibration-determines-benefit: Whether beliefs help a model...  (5 dependents)
#   [+] tool-deference-failure-mode: Models with poor tool-use calibration...
# 7 results

# List premises (foundations of the argument)
reasons list --premises
# List nodes that others depend on
reasons list --has-dependents
# List only OUT nodes
reasons list --status OUT

# Export as readable markdown
reasons export-markdown -o beliefs.md

# Check for source file changes
reasons check-stale
# 5 fresh, 14 STALE (of 19 checked)

# Token-budgeted summary for context injection
reasons compact --budget 500

# Non-monotonic reasoning: believe X unless Y
reasons add default-approx "Newtonian approximation holds" --unless strong-field
reasons assert strong-field  # default-approx goes OUT automatically
reasons retract strong-field  # default-approx restored

# Backfill source hashes
reasons hash-sources
# 26 backfilled

# Trace assumptions — what premises does a conclusion rest on?
reasons trace no-single-best-configuration
# no-single-best-configuration rests on 1 premise(s):
#   [+] beliefs-improve-accuracy  (7 dependents)

# Challenge a belief — target goes OUT
reasons challenge velocity-constraint "Not derived — postulated"
# Challenged velocity-constraint with challenge-velocity-constraint
# Changed: velocity-constraint, acoustic-metric-schwarzschild, ...

# Defend against a challenge — target restored
reasons defend velocity-constraint challenge-velocity-constraint \
  "Follows from variational principle on elastic medium"
# Defended velocity-constraint with defense-challenge-velocity-constraint
# Changed: challenge-velocity-constraint, velocity-constraint, ...

# List challenged nodes
reasons list --challenged
```

## Commands

| Command | Description |
|---------|-------------|
| `reasons init` | Create reasons.db |
| `reasons add ID "text"` | Add a premise |
| `reasons add ID "text" --sl a,b` | Add with SL justification (all antecedents must be IN) |
| `reasons add ID "text" --sl a --unless y` | Add with outlist (must be OUT for justification to hold) |
| `reasons add ID "text" --cp a,b` | Add with CP justification (assumptions must be consistent) |
| `reasons retract ID` | Mark OUT + cascade to dependents |
| `reasons assert ID` | Mark IN + cascade restoration |
| `reasons status` | Show all nodes with truth values |
| `reasons show ID` | Show node details, justifications, dependents |
| `reasons explain ID` | Trace why a node is IN or OUT |
| `reasons challenge ID "reason"` | Challenge a node — target goes OUT |
| `reasons defend TARGET CHALLENGE "reason"` | Defend against a challenge — target restored |
| `reasons nogood A B ...` | Record contradiction, backtrack to responsible premise |
| `reasons trace ID` | Trace backward to find all premises a node rests on |
| `reasons hash-sources` | Backfill source hashes for unhashed nodes (`--force` to re-hash all) |
| `reasons propagate` | Recompute all truth values |
| `reasons log` | Show propagation audit trail |
| `reasons search QUERY` | Search nodes by text or ID (case-insensitive) |
| `reasons list` | List with filters (`--status`, `--premises`, `--has-dependents`, `--challenged`) |
| `reasons import-beliefs FILE` | Import a beliefs.md registry (auto-detects nogoods.md) |
| `reasons export` | Export network as JSON |
| `reasons export-markdown` | Export as beliefs.md-compatible markdown (`-o FILE` to write) |
| `reasons check-stale` | Check IN nodes for source file hash changes |
| `reasons compact` | Token-budgeted summary (`--budget N`, `--no-truncate`) |

## Tests

```bash
uv run --extra test pytest tests/ -v
```

211 tests covering propagation, retraction cascades, restoration, multiple justifications, diamond dependencies, nogoods, dependency-directed backtracking, non-monotonic justifications (outlist), dialectical argumentation (challenge/defend), explain traces, SQLite round-trips, beliefs.md import, export-markdown, check-stale, hash-sources, compact, search, and list.

## References

Doyle, J. (1979). A Truth Maintenance System. *Artificial Intelligence*, 12(3), 231–272.
