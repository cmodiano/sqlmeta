"""Pydantic integration for sqlmeta.

This module provides functions to convert sqlmeta Table objects to
Pydantic BaseModel classes.

Example:
    >>> from sqlmeta import Table, SqlColumn
    >>> from sqlmeta.adapters.pydantic import to_pydantic
    >>>
    >>> table = Table("users", columns=[...])
    >>> UserModel = to_pydantic(table)
    >>> user = UserModel(id=1, email="test@example.com")
"""

from typing import Any, Dict, Optional, Type

try:
    from pydantic import BaseModel, Field, create_model

    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False


if not PYDANTIC_AVAILABLE:

    def to_pydantic(*args, **kwargs):
        raise ImportError(
            "Pydantic is not installed. " "Install it with: pip install sqlmeta[pydantic]"
        )

    def to_pydantic_schema(*args, **kwargs):
        raise ImportError(
            "Pydantic is not installed. " "Install it with: pip install sqlmeta[pydantic]"
        )

else:
    from sqlmeta import Table, SqlColumn

    def to_pydantic(
        table: Table, model_name: Optional[str] = None, use_title_case: bool = True
    ) -> Type[BaseModel]:
        """Convert sqlmeta Table to Pydantic BaseModel.

        Args:
            table: sqlmeta Table object
            model_name: Model name (defaults to table name in PascalCase)
            use_title_case: Convert snake_case to PascalCase

        Returns:
            Pydantic BaseModel class

        Example:
            >>> from sqlmeta import Table, SqlColumn
            >>>
            >>> table = Table("users", columns=[
            ...     SqlColumn("id", "INTEGER", is_primary_key=True),
            ...     SqlColumn("email", "VARCHAR(255)", is_nullable=False),
            ...     SqlColumn("name", "VARCHAR(100)"),
            ... ])
            >>>
            >>> UserModel = to_pydantic(table)
            >>> user = UserModel(id=1, email="test@example.com", name="John")
            >>> print(user.model_dump_json())
        """
        if model_name is None:
            if use_title_case:
                model_name = _to_pascal_case(table.name)
            else:
                model_name = table.name

        fields: Dict[str, Any] = {}

        for col in table.columns:
            python_type = _map_sql_type_to_python(col.data_type)

            # Make optional if nullable
            if col.nullable and not col.is_primary_key:
                python_type = Optional[python_type]

            # Create field with metadata
            field_kwargs = {}

            if col.default_value:
                field_kwargs["default"] = col.default_value
            elif col.nullable:
                field_kwargs["default"] = None
            else:
                # Required field
                pass

            if hasattr(col, "comment") and col.comment:
                field_kwargs["description"] = col.comment

            if field_kwargs:
                fields[col.name] = (python_type, Field(**field_kwargs))
            else:
                fields[col.name] = (python_type, ...)

        # Create Pydantic model
        pydantic_model = create_model(model_name, **fields)

        return pydantic_model

    def to_pydantic_schema(table: Table) -> Dict[str, Any]:
        """Convert sqlmeta Table to Pydantic JSON Schema.

        Args:
            table: sqlmeta Table object

        Returns:
            JSON Schema dictionary
        """
        model = to_pydantic(table)
        return model.model_json_schema()

    def _to_pascal_case(snake_str: str) -> str:
        """Convert snake_case to PascalCase."""
        components = snake_str.split("_")
        return "".join(x.title() for x in components)

    def _map_sql_type_to_python(sql_type: str) -> Type:
        """Map SQL type to Python type."""
        from datetime import datetime, date, time
        from decimal import Decimal

        sql_type_upper = sql_type.upper()

        # Integer types
        if any(t in sql_type_upper for t in ["INT", "SERIAL", "BIGINT", "SMALLINT"]):
            return int

        # Float types
        if any(t in sql_type_upper for t in ["FLOAT", "DOUBLE", "REAL"]):
            return float

        # Decimal types
        if any(t in sql_type_upper for t in ["NUMERIC", "DECIMAL", "MONEY"]):
            return Decimal

        # Boolean
        if "BOOL" in sql_type_upper:
            return bool

        # DateTime types
        if "TIMESTAMP" in sql_type_upper or "DATETIME" in sql_type_upper:
            return datetime

        if "DATE" in sql_type_upper:
            return date

        if "TIME" in sql_type_upper:
            return time

        # Binary types
        if any(t in sql_type_upper for t in ["BLOB", "BYTEA", "BINARY", "VARBINARY"]):
            return bytes

        # Default to string
        return str


__all__ = [
    "to_pydantic",
    "to_pydantic_schema",
]
