from fastapi import Request

from backend.container import Container


def get_container(request: Request) -> Container:
    return request.app.state.container


def request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)
