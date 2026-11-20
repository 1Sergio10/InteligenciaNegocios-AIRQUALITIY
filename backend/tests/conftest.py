import os

os.environ["ALENTO_DATABASE_URL"] = "sqlite://"
os.environ["ALENTO_STATIC_DIR"] = "/nonexistent"

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c
