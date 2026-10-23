import pytest
from kindred.qloo_client import QlooClient, FixtureTransport

@pytest.fixture
def transport():
    return FixtureTransport()

@pytest.fixture
def client(transport):
    return QlooClient(transport)
