"""CLI for the Reason Maintenance System."""

import argparse
import json
import sys
from pathlib import Path

from .network import Network
from .storage import Storage
from .import_beliefs import import_into_network


DEFAULT_DB = "rms.db"


def get_storage(args) -> Storage:
    db_path = getattr(args, "db", DEFAULT_DB)
    return Storage(db_path)


def cmd_init(args):
    """Initialize a new RMS database."""
    db_path = Path(args.db)
    if db_path.exists() and not args.force:
        print(f"Database already exists: {db_path}", file=sys.stderr)
        print("Use --force to reinitialize.", file=sys.stderr)
        sys.exit(1)
    store = Storage(db_path)
    store.close()
    print(f"Initialized RMS database: {db_path}")


def cmd_add(args):
    """Add a node to the network."""
    store = get_storage(args)
    net = store.load()

    justifications = []
    if args.sl:
        from . import Justification
        antecedents = [a.strip() for a in args.sl.split(",")]
        justifications.append(Justification(type="SL", antecedents=antecedents, label=args.label or ""))
    elif args.cp:
        from . import Justification
        antecedents = [a.strip() for a in args.cp.split(",")]
        justifications.append(Justification(type="CP", antecedents=antecedents, label=args.label or ""))

    try:
        node = net.add_node(
            id=args.node_id,
            text=args.text,
            justifications=justifications or None,
            source=args.source or "",
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    store.save(net)
    store.close()

    jtype = justifications[0].type if justifications else "premise"
    print(f"Added {args.node_id} [{node.truth_value}] ({jtype})")


def cmd_retract(args):
    """Retract a node."""
    store = get_storage(args)
    net = store.load()

    try:
        changed = net.retract(args.node_id)
    except KeyError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    store.save(net)
    store.close()

    if not changed:
        print(f"{args.node_id} is already OUT")
    else:
        print(f"Retracted: {', '.join(changed)}")


def cmd_assert(args):
    """Assert a node."""
    store = get_storage(args)
    net = store.load()

    try:
        changed = net.assert_node(args.node_id)
    except KeyError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    store.save(net)
    store.close()

    if not changed:
        print(f"{args.node_id} is already IN")
    else:
        print(f"Asserted: {', '.join(changed)}")


def cmd_status(args):
    """Show all nodes with truth values."""
    store = get_storage(args)
    net = store.load()
    store.close()

    if not net.nodes:
        print("No nodes in the network.")
        return

    for nid, node in sorted(net.nodes.items()):
        marker = "+" if node.truth_value == "IN" else "-"
        jcount = len(node.justifications)
        jinfo = f"  ({jcount} justification{'s' if jcount != 1 else ''})" if jcount else "  (premise)"
        print(f"  [{marker}] {nid}: {node.text}{jinfo}")

    in_count = sum(1 for n in net.nodes.values() if n.truth_value == "IN")
    print(f"\n{in_count}/{len(net.nodes)} IN")


def cmd_show(args):
    """Show details for a single node."""
    store = get_storage(args)
    net = store.load()
    store.close()

    if args.node_id not in net.nodes:
        print(f"Node '{args.node_id}' not found.", file=sys.stderr)
        sys.exit(1)

    node = net.nodes[args.node_id]
    print(f"ID:     {node.id}")
    print(f"Text:   {node.text}")
    print(f"Status: {node.truth_value}")
    if node.source:
        print(f"Source: {node.source}")
    if node.source_hash:
        print(f"Hash:   {node.source_hash}")

    if node.justifications:
        print(f"\nJustifications ({len(node.justifications)}):")
        for j in node.justifications:
            ants = ", ".join(j.antecedents)
            label = f" [{j.label}]" if j.label else ""
            print(f"  {j.type}({ants}){label}")
    else:
        print("\nPremise (no justifications)")

    if node.dependents:
        print(f"\nDependents: {', '.join(sorted(node.dependents))}")


def cmd_explain(args):
    """Explain why a node is IN or OUT."""
    store = get_storage(args)
    net = store.load()
    store.close()

    try:
        steps = net.explain(args.node_id)
    except KeyError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    for step in steps:
        nid = step["node"]
        tv = step["truth_value"]
        reason = step["reason"]
        marker = "+" if tv == "IN" else "-"
        line = f"  [{marker}] {nid}: {reason}"
        if "antecedents" in step:
            line += f" — antecedents: {', '.join(step['antecedents'])}"
        if "failed_antecedents" in step:
            line += f" — failed: {', '.join(step['failed_antecedents'])}"
        if step.get("label"):
            line += f" [{step['label']}]"
        print(line)


def cmd_nogood(args):
    """Record a contradiction."""
    store = get_storage(args)
    net = store.load()

    try:
        changed = net.add_nogood(args.node_ids)
    except KeyError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    store.save(net)
    store.close()

    ng = net.nogoods[-1]
    print(f"Recorded {ng.id}: {', '.join(ng.nodes)}")
    if changed:
        print(f"Retracted: {', '.join(changed)}")


def cmd_propagate(args):
    """Recompute all truth values."""
    store = get_storage(args)
    net = store.load()

    changed = []
    for node in net.nodes.values():
        if node.justifications:
            old = node.truth_value
            new = net._compute_truth(node)
            if old != new:
                node.truth_value = new
                changed.append(node.id)

    store.save(net)
    store.close()

    if changed:
        print(f"Updated: {', '.join(changed)}")
    else:
        print("All truth values are current.")


def cmd_log(args):
    """Show propagation history."""
    store = get_storage(args)
    net = store.load()
    store.close()

    if not net.log:
        print("No propagation events.")
        return

    entries = net.log
    if args.last:
        entries = entries[-args.last:]

    for entry in entries:
        print(f"  {entry['timestamp']}  {entry['action']:10s}  {entry['target']:20s}  {entry['value']}")


def cmd_import_beliefs(args):
    """Import a beliefs.md registry into the RMS network."""
    beliefs_path = Path(args.beliefs_file)
    if not beliefs_path.exists():
        print(f"File not found: {beliefs_path}", file=sys.stderr)
        sys.exit(1)

    beliefs_text = beliefs_path.read_text()

    nogoods_text = None
    if args.nogoods_file:
        nogoods_path = Path(args.nogoods_file)
        if nogoods_path.exists():
            nogoods_text = nogoods_path.read_text()
        else:
            print(f"Nogoods file not found: {nogoods_path}", file=sys.stderr)
            sys.exit(1)
    else:
        # Auto-detect nogoods.md next to beliefs.md
        auto_nogoods = beliefs_path.parent / "nogoods.md"
        if auto_nogoods.exists():
            nogoods_text = auto_nogoods.read_text()

    store = get_storage(args)
    net = store.load()

    result = import_into_network(net, beliefs_text, nogoods_text)

    store.save(net)
    store.close()

    print(f"Imported {result['claims_imported']} claims ({result['claims_retracted']} retracted)")
    if result['claims_skipped']:
        print(f"Skipped {result['claims_skipped']} (already in network)")
    if result['nogoods_imported']:
        print(f"Imported {result['nogoods_imported']} nogoods")


def cmd_export(args):
    """Export the network as JSON."""
    store = get_storage(args)
    net = store.load()
    store.close()

    data = {
        "nodes": {
            nid: {
                "text": n.text,
                "truth_value": n.truth_value,
                "justifications": [
                    {"type": j.type, "antecedents": j.antecedents, "label": j.label}
                    for j in n.justifications
                ],
                "source": n.source,
                "source_hash": n.source_hash,
                "date": n.date,
                "metadata": n.metadata,
            }
            for nid, n in sorted(net.nodes.items())
        },
        "nogoods": [
            {"id": ng.id, "nodes": ng.nodes, "discovered": ng.discovered, "resolution": ng.resolution}
            for ng in net.nogoods
        ],
    }
    print(json.dumps(data, indent=2))


def main():
    parser = argparse.ArgumentParser(
        prog="rms",
        description="Reason Maintenance System — automatic belief retraction and dependency-directed backtracking",
    )
    parser.add_argument("--db", default=DEFAULT_DB, help="Path to RMS database (default: rms.db)")
    sub = parser.add_subparsers(dest="command")

    # init
    p = sub.add_parser("init", help="Initialize a new RMS database")
    p.add_argument("--force", action="store_true", help="Overwrite existing database")

    # add
    p = sub.add_parser("add", help="Add a node")
    p.add_argument("node_id", help="Node identifier")
    p.add_argument("text", help="Node text")
    p.add_argument("--sl", metavar="A,B", help="SL justification: comma-separated antecedent IDs")
    p.add_argument("--cp", metavar="A,B", help="CP justification: comma-separated antecedent IDs")
    p.add_argument("--label", help="Justification label")
    p.add_argument("--source", help="Provenance (repo:path)")

    # retract
    p = sub.add_parser("retract", help="Retract a node (mark OUT + cascade)")
    p.add_argument("node_id", help="Node to retract")

    # assert
    p = sub.add_parser("assert", help="Assert a node (mark IN + cascade)")
    p.add_argument("node_id", help="Node to assert")

    # status
    sub.add_parser("status", help="Show all nodes with truth values")

    # show
    p = sub.add_parser("show", help="Show node details")
    p.add_argument("node_id", help="Node to show")

    # explain
    p = sub.add_parser("explain", help="Explain why a node is IN or OUT")
    p.add_argument("node_id", help="Node to explain")

    # nogood
    p = sub.add_parser("nogood", help="Record a contradiction")
    p.add_argument("node_ids", nargs="+", help="Node IDs that cannot all be IN")

    # propagate
    sub.add_parser("propagate", help="Recompute all truth values")

    # log
    p = sub.add_parser("log", help="Show propagation history")
    p.add_argument("--last", type=int, help="Show only last N entries")

    # import-beliefs
    p = sub.add_parser("import-beliefs", help="Import a beliefs.md registry")
    p.add_argument("beliefs_file", help="Path to beliefs.md")
    p.add_argument("--nogoods", dest="nogoods_file", help="Path to nogoods.md (auto-detected if next to beliefs.md)")

    # export
    sub.add_parser("export", help="Export network as JSON")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "init": cmd_init,
        "add": cmd_add,
        "retract": cmd_retract,
        "assert": cmd_assert,
        "status": cmd_status,
        "show": cmd_show,
        "explain": cmd_explain,
        "nogood": cmd_nogood,
        "propagate": cmd_propagate,
        "log": cmd_log,
        "import-beliefs": cmd_import_beliefs,
        "export": cmd_export,
    }
    commands[args.command](args)
