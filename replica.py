"""
Primary / Secondary inventory replicas with controllable replication delay.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Replica:
    name: str
    role: str  # "PRIMARY" or "SECONDARY"
    stock: int = 10
    version: int = 0

    def read(self) -> int:
        return self.stock

    def write(self, new_stock: int) -> None:
        if self.role != "PRIMARY":
            raise PermissionError(f"{self.name} is {self.role}; writes go to PRIMARY only")
        self.stock = new_stock
        self.version += 1

    def apply_from_primary(self, stock: int, version: int) -> None:
        if self.role != "SECONDARY":
            raise PermissionError(f"{self.name} is {self.role}; only SECONDARY receives replicas")
        self.stock = stock
        self.version = version


@dataclass
class ReplicatedInventory:
    """
    Tiny replicated inventory: writes hit Primary; Secondary is updated
    through an explicit replication step that can be paused (stale reads).
    """

    primary: Replica = field(default_factory=lambda: Replica("primary", "PRIMARY", stock=10))
    secondary: Replica = field(default_factory=lambda: Replica("secondary", "SECONDARY", stock=10))
    replication_paused: bool = False
    pending: Optional[tuple[int, int]] = None  # (stock, version) waiting to replicate
    log: List[str] = field(default_factory=list)

    def _log(self, message: str) -> None:
        self.log.append(message)
        print(message)

    def read(self, which: str = "primary") -> int:
        replica = self.primary if which == "primary" else self.secondary
        value = replica.read()
        self._log(
            f"[READ ] {replica.name:9} ({replica.role:9}) -> stock={value} "
            f"version={replica.version}"
        )
        return value

    def write(self, new_stock: int) -> None:
        old = self.primary.stock
        self.primary.write(new_stock)
        self._log(
            f"[WRITE] primary   (PRIMARY  ) stock {old} -> {new_stock} "
            f"version={self.primary.version}"
        )
        # Queue replication of the latest primary state.
        self.pending = (self.primary.stock, self.primary.version)
        if self.replication_paused:
            self._log(
                f"[REPL ] paused — secondary still at stock={self.secondary.stock} "
                f"version={self.secondary.version}; pending={self.pending}"
            )
        else:
            self.replicate_now()

    def pause_replication(self) -> None:
        self.replication_paused = True
        self._log("[CTRL ] replication PAUSED (secondary will go stale on next write)")

    def resume_replication(self) -> None:
        self.replication_paused = False
        self._log("[CTRL ] replication RESUMED")
        if self.pending is not None:
            self.replicate_now()

    def replicate_now(self) -> bool:
        """Push pending (or current primary) state to the secondary."""
        if self.pending is None:
            # Nothing queued — sync current primary state anyway.
            self.pending = (self.primary.stock, self.primary.version)

        stock, version = self.pending
        if (
            self.secondary.stock == stock
            and self.secondary.version == version
        ):
            self._log(
                f"[REPL ] secondary already in sync "
                f"(stock={stock} version={version})"
            )
            self.pending = None
            return False

        old_stock, old_ver = self.secondary.stock, self.secondary.version
        self.secondary.apply_from_primary(stock, version)
        self.pending = None
        self._log(
            f"[REPL ] secondary updated stock {old_stock}->{stock} "
            f"version {old_ver}->{version}"
        )
        return True

    def snapshot(self) -> str:
        return (
            f"primary={{stock={self.primary.stock}, version={self.primary.version}}}  "
            f"secondary={{stock={self.secondary.stock}, version={self.secondary.version}}}  "
            f"paused={self.replication_paused} pending={self.pending}"
        )
