from __future__ import annotations

from sqlalchemy import Integer

import app.models  # noqa: F401
from app.core.database import Base


def test_all_models_have_integer_autoincrement_id() -> None:
    tables = Base.metadata.tables
    assert tables, "No tables discovered in metadata"

    for table_name, table in tables.items():
        assert "id" in table.columns, f"Table {table_name} must have id column"
        column = table.columns["id"]
        assert isinstance(column.type, Integer), f"Table {table_name}.id must be Integer"
        assert column.primary_key is True, f"Table {table_name}.id must be primary key"
        assert column.autoincrement in (True, "auto"), f"Table {table_name}.id must be auto-increment"
