import pytest


@pytest.fixture(autouse=True)
def reset_modules():
    yield
