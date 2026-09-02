from contextlib import contextmanager


class OrthoScopeError(Exception):
    status = 500
    kind = "internal"

    def __init__(self, message: str, *, stage: str | None = None, hint: str | None = None):
        super().__init__(message)
        self.message = message
        self.stage = stage
        self.hint = hint

    def as_dict(self) -> dict:
        return {
            "kind": self.kind,
            "stage": self.stage,
            "message": self.message,
            "hint": self.hint,
        }


class InvalidInput(OrthoScopeError):
    status = 400
    kind = "invalid_input"


class NotFound(OrthoScopeError):
    status = 404
    kind = "not_found"


class UpstreamError(OrthoScopeError):
    status = 502
    kind = "upstream"


class MissingDependency(OrthoScopeError):
    status = 500
    kind = "missing_dependency"


class PipelineError(OrthoScopeError):
    status = 500
    kind = "pipeline"


@contextmanager
def stage(name: str):
    try:
        yield
    except OrthoScopeError as e:
        if e.stage is None:
            e.stage = name
        raise
    except Exception as e:
        raise PipelineError(
            f"{type(e).__name__}: {e}" if str(e) else type(e).__name__,
            stage=name,
        ) from e
