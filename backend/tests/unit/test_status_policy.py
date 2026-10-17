from itertools import product

import pytest

from app.core.constants import STATUS_TRANSITIONS, IssueStatus
from app.core.exceptions import InvalidStatusTransitionError
from app.services.status_policy import StatusTransitionPolicy

policy = StatusTransitionPolicy()


@pytest.mark.parametrize(("current", "target"), list(product(IssueStatus, IssueStatus)))
def test_every_transition_matches_the_transition_table(
    current: IssueStatus, target: IssueStatus
) -> None:
    expected = target == current or target in STATUS_TRANSITIONS[current]

    assert policy.can_transition(current, target) is expected
    if expected:
        policy.ensure_can_transition(current, target)
    else:
        with pytest.raises(InvalidStatusTransitionError):
            policy.ensure_can_transition(current, target)


def test_closed_issue_must_be_reopened_before_work_resumes() -> None:
    assert policy.allowed_from(IssueStatus.CLOSED) == [IssueStatus.OPEN]
    assert not policy.can_transition(IssueStatus.CLOSED, IssueStatus.IN_PROGRESS)


def test_allowed_from_is_returned_in_declaration_order() -> None:
    assert policy.allowed_from(IssueStatus.OPEN) == [
        IssueStatus.IN_PROGRESS,
        IssueStatus.RESOLVED,
        IssueStatus.CLOSED,
    ]


def test_rejected_transition_reports_allowed_targets() -> None:
    with pytest.raises(InvalidStatusTransitionError) as exc_info:
        policy.ensure_can_transition(IssueStatus.CLOSED, IssueStatus.RESOLVED)

    assert exc_info.value.details == {"from": "closed", "to": "resolved", "allowed": ["open"]}


def test_policy_rules_are_injectable() -> None:
    strict = StatusTransitionPolicy({IssueStatus.OPEN: frozenset({IssueStatus.CLOSED})})

    assert strict.can_transition(IssueStatus.OPEN, IssueStatus.CLOSED)
    assert not strict.can_transition(IssueStatus.OPEN, IssueStatus.IN_PROGRESS)
