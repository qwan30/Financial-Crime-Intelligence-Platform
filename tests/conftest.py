from __future__ import annotations

import os
import uuid
from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.schema import CreateSchema, DropSchema


@pytest.fixture
def postgres_url(monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    base = os.getenv("TEST_DATABASE_URL")
    if not base:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL verification")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    schema = "canvas_test_" + uuid.uuid4().hex
    admin = create_engine(base)
    scoped = make_url(base).update_query_dict({"options": f"-csearch_path={schema}"})
    url = scoped.render_as_string(hide_password=False)
    scoped_engine = create_engine(url)
    created = False
    try:
        with admin.begin() as connection:
            connection.execute(CreateSchema(schema))
            created = True
        with scoped_engine.begin() as connection:
            connection.info["canvas_schema"] = schema
            config = Config("alembic.ini")
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
        yield url
    finally:
        scoped_engine.dispose()
        if created:
            with admin.begin() as connection:
                connection.execute(DropSchema(schema, cascade=True))
        admin.dispose()
