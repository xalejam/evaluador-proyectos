class EvaluadorError(Exception):
    """Base exception for all domain errors."""


class ProjectNotFoundError(EvaluadorError):
    def __init__(self, project_id: str):
        super().__init__(f"Project not found: {project_id}")
        self.project_id = project_id


class DuplicateProjectError(EvaluadorError):
    def __init__(self, project_id: str):
        super().__init__(f"Project already exists: {project_id}")
        self.project_id = project_id


class InvalidStatusTransitionError(EvaluadorError):
    def __init__(self, from_status: str, to_status: str):
        super().__init__(f"Invalid status transition: {from_status} → {to_status}")
        self.from_status = from_status
        self.to_status = to_status


class ValidationError(EvaluadorError):
    def __init__(self, field: str, reason: str):
        super().__init__(f"Validation failed for '{field}': {reason}")
        self.field = field
        self.reason = reason
