#!/usr/bin/env python3
"""
Module 8 – Replication & Consistency
Inventory system with 1 Primary + 1 Secondary replica.

Scenarios:
  1. Successful replication (write primary → secondary catches up)
  2. Stale read (pause replication, write primary, secondary still old)
  3. Recovery / convergence (resume replication, both agree again)
"""

from __future__ import annotations

import argparse
import io
import sys
from contextlib import redirect_stdout
from pathlib import Path

from replica import ReplicatedInventory


SEPARATOR = "=" * 72


def banner(title: str) -> None:
    print()
    print(SEPARATOR)
    print(title)
    print(SEPARATOR)


def scenario_replication(system: ReplicatedInventory | None = None) -> ReplicatedInventory:
    """Update primary and show secondary eventually receives the same value."""
    banner("SCENARIO 1 – Successful replication")
    system = system or ReplicatedInventory()

    print("Initial state (stock starts at 10 on both replicas):")
    print(f"  {system.snapshot()}")
    print()

    p = system.read("primary")
    s = system.read("secondary")
    assert p == s == 10
    print()

    print("Client writes stock=7 to PRIMARY …")
    system.write(7)
    print()

    print("After replication:")
    print(f"  {system.snapshot()}")
    p = system.read("primary")
    s = system.read("secondary")
    assert p == s == 7
    print()
    print("CHECK: Primary got 7; Secondary eventually got 7; both return the same value.")
    return system


def scenario_stale_read(system: ReplicatedInventory | None = None) -> ReplicatedInventory:
    """
    Delay replication, update 10 → 9 on primary.
    Primary returns 9; secondary temporarily returns 10 (stale read).
    """
    banner("SCENARIO 2 – Stale read (replication delayed)")
    system = system or ReplicatedInventory()

    # Reset to the assignment's starting point for this test.
    system.primary.stock = 10
    system.primary.version = 0
    system.secondary.stock = 10
    system.secondary.version = 0
    system.pending = None
    system.replication_paused = False

    print("Start: both replicas at stock=10")
    print(f"  {system.snapshot()}")
    print()

    system.pause_replication()
    print()
    print("Client updates PRIMARY: stock 10 → 9 (replication still paused) …")
    system.write(9)
    print()

    print("Reads while secondary is behind:")
    primary_val = system.read("primary")
    secondary_val = system.read("secondary")
    print()
    print(f"  {system.snapshot()}")
    print()

    assert primary_val == 9
    assert secondary_val == 10
    print(
        "CHECK: Primary returns 9; Secondary temporarily returns older value 10 "
        "(stale read)."
    )
    return system


def scenario_recovery(system: ReplicatedInventory | None = None) -> ReplicatedInventory:
    """
    Resume replication after a stale secondary; both converge to 9.
    If called alone, sets up the stale state first.
    """
    banner("SCENARIO 3 – Recovery and convergence")

    if system is None:
        system = ReplicatedInventory()
        system.primary.stock = 10
        system.primary.version = 0
        system.secondary.stock = 10
        system.secondary.version = 0
        system.pause_replication()
        system.write(9)
        print("(set up stale secondary first)")
        print(f"  {system.snapshot()}")
        print()

    print("Before resume:")
    print(f"  {system.snapshot()}")
    assert system.read("primary") == 9
    assert system.read("secondary") == 10
    print()

    print("Resuming replication …")
    system.resume_replication()
    print()

    print("After convergence:")
    print(f"  {system.snapshot()}")
    p = system.read("primary")
    s = system.read("secondary")
    assert p == s == 9
    print()
    print("CHECK: Secondary updated to 9; both replicas return the same value again.")
    return system


def run_all() -> None:
    banner("Module 8 – Replication & Consistency  |  full demo")
    print("Inventory replicas: 1 Primary + 1 Secondary")
    print("Writes → Primary; replication → Secondary (can be paused)")

    system = ReplicatedInventory()
    scenario_replication(system)

    # Stale + recovery share one continuum so evidence shows the full arc.
    system = scenario_stale_read(ReplicatedInventory())
    scenario_recovery(system)

    banner("FINAL SNAPSHOT")
    print(system.snapshot())
    print()
    print("All scenarios completed successfully.")


def write_evidence(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    buf_all = io.StringIO()
    with redirect_stdout(buf_all):
        run_all()
    (out_dir / "00_full_run.txt").write_text(buf_all.getvalue())

    # Individual scenario files
    buf = io.StringIO()
    with redirect_stdout(buf):
        scenario_replication(ReplicatedInventory())
    (out_dir / "01_replication.txt").write_text(buf.getvalue())

    buf = io.StringIO()
    with redirect_stdout(buf):
        stale_system = scenario_stale_read(ReplicatedInventory())
    (out_dir / "02_stale_read.txt").write_text(buf.getvalue())

    buf = io.StringIO()
    with redirect_stdout(buf):
        # Continue from the stale state for a realistic recovery log,
        # and also show a standalone recovery path.
        scenario_recovery(stale_system)
    (out_dir / "03_recovery.txt").write_text(buf.getvalue())

    for name in (
        "00_full_run.txt",
        "01_replication.txt",
        "02_stale_read.txt",
        "03_recovery.txt",
    ):
        print(f"wrote {out_dir / name}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Module 8 replicated inventory simulation"
    )
    parser.add_argument(
        "--scenario",
        choices=("replication", "stale", "recovery", "all"),
        default="all",
        help="which demo to run (default: all)",
    )
    parser.add_argument(
        "--write-evidence",
        action="store_true",
        help="write evidence/*.txt from a fresh run of each scenario",
    )
    args = parser.parse_args(argv)

    if args.write_evidence:
        write_evidence(Path(__file__).resolve().parent / "evidence")
        return 0

    if args.scenario == "replication":
        scenario_replication()
    elif args.scenario == "stale":
        scenario_stale_read()
    elif args.scenario == "recovery":
        scenario_recovery()
    else:
        run_all()
    return 0


if __name__ == "__main__":
    sys.exit(main())
