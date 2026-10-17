from collections.abc import Mapping

from app.core.constants import STATUS_TRANSITIONS, IssueStatus
from app.core.exceptions import InvalidStatusTransitionError


class StatusTransitionPolicy:
    """Decides which status changes are allowed. The rules are data (``STATUS_TRANSITIONS``),
    so changing the workflow doesn't require changing this class."""

    def __init__(
        self, transitions: Mapping[IssueStatus, frozenset[IssueStatus]] = STATUS_TRANSITIONS
    ) -> None:
        self._transitions = transitions

    def allowed_from(self, current: IssueStatus) -> list[IssueStatus]:
        """Statuses reachable from ``current``, in declaration order (stable for clients)."""
        allowed = self._transitions.get(current, frozenset())
        return [status for status in IssueStatus if status in allowed]

    def can_transition(self, current: IssueStatus, target: IssueStatus) -> bool:
        return target == current or target in self._transitions.get(current, frozenset())

    def ensure_can_transition(self, current: IssueStatus, target: IssueStatus) -> None:
        if not self.can_transition(current, target):
            raise InvalidStatusTransitionError(current, target, self.allowed_from(current))


DEFAULT_STATUS_POLICY = StatusTransitionPolicy()
