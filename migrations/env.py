from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from fincrime.storage.postgres import metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = metadata


def run_migrations_offline() -> None:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise ValueError("DATABASE_URL environment variable is required for migrations")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connection = config.attributes.get("connection", None)
    if connection is not None:
        schema = connection.info.get("canvas_schema", None)
        context_opts = {
            "connection": connection,
            "target_metadata": target_metadata,
        }
        if schema:
            context_opts["version_table_schema"] = schema
        context.configure(**context_opts)
        with context.begin_transaction():
            context.run_migrations()
    else:
        url = os.getenv("DATABASE_URL")
        if not url:
            raise ValueError("DATABASE_URL environment variable is required for migrations")
        connectable = create_engine(url, poolclass=pool.NullPool)

        with connectable.connect() as conn:
            context.configure(
                connection=conn,
                target_metadata=target_metadata,
            )
            with context.begin_transaction():
                context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
