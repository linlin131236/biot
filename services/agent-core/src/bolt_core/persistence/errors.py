"""Shared persistence exceptions for control-plane record repositories."""

class PersistenceConflictError(RuntimeError):
    """A revision no longer matches the durable record."""


class TaskTerminalStateError(RuntimeError):
    """A terminal task cannot be reverted or changed by a later update."""


class RuntimeEventSequenceError(RuntimeError):
    """A runtime event sequence is not strictly monotonic and gapless."""


class RuntimeSessionClosedError(RuntimeError):
    """A closed runtime session cannot accept further events."""


class RuntimeSessionActionError(RuntimeError):
    """A terminal runtime session cannot accept another action."""
