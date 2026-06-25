"""
Shared pytest fixtures for Beaver's Choice Paper Company tests.

Each test that needs database access receives an isolated in-memory SQLite
database via the `db` fixture.  The fixture monkey-patches the module-level
`project_starter.db_engine` so every helper function automatically uses the
in-memory database instead of the production file on disk.
"""
import os
import pytest
from sqlalchemy import create_engine

# Change to project root so init_database can find the CSV files.
os.chdir(os.path.dirname(os.path.dirname(__file__)))

import project_starter as ps  # noqa: E402 – import after chdir


@pytest.fixture
def db():
    """
    Provide a clean, fully-initialised in-memory database for one test.

    After the test the engine is disposed and the module-level db_engine is
    restored to the original value so other imports are not affected.
    """
    original_engine = ps.db_engine
    engine = create_engine("sqlite:///:memory:")
    ps.db_engine = engine
    ps.init_database(engine)
    yield engine
    engine.dispose()
    ps.db_engine = original_engine
