from domain.exceptions import (
    DuplicateProjectError,
    EvaluadorError,
    InvalidStatusTransitionError,
    ProjectNotFoundError,
    ValidationError,
)


def test_exception_hierarchy():
    assert issubclass(ProjectNotFoundError, EvaluadorError)
    assert issubclass(DuplicateProjectError, EvaluadorError)
    assert issubclass(InvalidStatusTransitionError, EvaluadorError)
    assert issubclass(ValidationError, EvaluadorError)


def test_project_not_found_carries_id():
    exc = ProjectNotFoundError("MX-JDO-001")
    assert "MX-JDO-001" in str(exc)


def test_invalid_status_transition_carries_context():
    exc = InvalidStatusTransitionError("backlog", "implemented")
    assert "backlog" in str(exc)
    assert "implemented" in str(exc)
