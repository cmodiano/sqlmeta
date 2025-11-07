"""Tests for sqlmeta core functionality."""

import pytest
from sqlmeta import Table, SqlColumn, SqlConstraint, ConstraintType


def test_create_simple_table():
    """Test creating a simple table."""
    table = Table(
        name="users",
        columns=[
            SqlColumn("id", "INTEGER", is_primary_key=True),
            SqlColumn("email", "VARCHAR(255)", is_nullable=False),
        ],
    )

    assert table.name == "users"
    assert len(table.columns) == 2
    assert table.columns[0].name == "id"
    assert table.columns[0].is_primary_key is True


def test_table_to_dict():
    """Test table serialization to dictionary."""
    table = Table(
        name="users",
        schema="public",
        columns=[
            SqlColumn("id", "INTEGER", is_primary_key=True),
        ],
    )

    table_dict = table.to_dict()

    assert table_dict["name"] == "users"
    assert table_dict["schema"] == "public"
    assert len(table_dict["columns"]) == 1


def test_table_from_dict():
    """Test table deserialization from dictionary."""
    table_dict = {
        "name": "users",
        "schema": "public",
        "columns": [
            {
                "name": "id",
                "data_type": "INTEGER",
                "nullable": False,
                "default_value": None,
                "is_identity": False,
                "is_computed": False,
                "explicit_properties": {},
            }
        ],
        "constraints": [],
        "temporary": False,
        "tablespace": None,
        "comment": None,
        "storage_engine": None,
        "explicit_properties": {},
    }

    table = Table.from_dict(table_dict)

    assert table.name == "users"
    assert table.schema == "public"
    assert len(table.columns) == 1
