import pytest
from fastapi.testclient import TestClient

from backend.config.settings import Settings
from backend.domain.support import FrozenClock
from backend.main import create_app


@pytest.fixture
def clock():
    return FrozenClock()


@pytest.fixture
def settings(tmp_path):
    return Settings(database_url=f"sqlite:///{(tmp_path / 'test.db').as_posix()}", demo_mode=True)


@pytest.fixture
def app(settings, clock):
    application = create_app(settings, clock)
    yield application
    application.state.container.db.dispose()


@pytest.fixture
def container(app):
    return app.state.container


@pytest.fixture
def client(app):
    return TestClient(app, raise_server_exceptions=False)
