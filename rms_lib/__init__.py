"""Reason Maintenance System — data model based on Doyle (1979)."""

from dataclasses import dataclass, field


@dataclass
class Justification:
    """A reason for believing a node.

    Two types:
    - SL (Support List): node is IN iff ALL antecedents are IN
    - CP (Conditional Proof): node is IN iff assumptions are consistent
    """
    type: str  # "SL" or "CP"
    antecedents: list[str] = field(default_factory=list)  # node IDs
    label: str = ""


@dataclass
class Node:
    """A node in the dependency network.

    A node is IN if ANY of its justifications is valid.
    A premise has no justifications and is IN by default.
    """
    id: str
    text: str
    truth_value: str = "IN"  # IN or OUT
    justifications: list[Justification] = field(default_factory=list)
    dependents: set[str] = field(default_factory=set)  # reverse index
    source: str = ""
    source_hash: str = ""
    date: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass
class Nogood:
    """A recorded contradiction — these node IDs cannot all be IN simultaneously."""
    id: str
    nodes: list[str] = field(default_factory=list)
    discovered: str = ""
    resolution: str = ""
