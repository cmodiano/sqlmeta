"""SQLAlchemy integration for sqlmeta.

This module provides functions to convert between sqlmeta objects and
SQLAlchemy Table objects.

Example:
    >>> from sqlmeta import Table, SqlColumn
    >>> from sqlmeta.adapters.sqlalchemy import to_sqlalchemy
    >>> from sqlalchemy import MetaData
    >>>
    >>> table = Table("users", columns=[...])
    >>> metadata = MetaData()
    >>> sa_table = to_sqlalchemy(table, metadata)
"""

from typing import Optional, Type, Union

try:
    from sqlalchemy import (
        Boolean,
        Column as SAColumn,
        DateTime,
        ForeignKey,
        Integer,
        MetaData,
        Numeric,
        String,
        Table as SATable,
        Text,
        CheckConstraint,
        PrimaryKeyConstraint,
        UniqueConstraint,
    )
    from sqlalchemy.schema import CreateTable

    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False


if not SQLALCHEMY_AVAILABLE:

    def to_sqlalchemy(*args, **kwargs):
        raise ImportError(
            "SQLAlchemy is not installed. " "Install it with: pip install sqlmeta[sqlalchemy]"
        )

    def from_sqlalchemy(*args, **kwargs):
        raise ImportError(
            "SQLAlchemy is not installed. " "Install it with: pip install sqlmeta[sqlalchemy]"
        )

else:
    from sqlmeta import Table, SqlColumn, SqlConstraint
    from sqlmeta.base import ConstraintType

    def to_sqlalchemy(table: Table, metadata: Optional[MetaData] = None) -> SATable:
        """Convert sqlmeta Table to SQLAlchemy Table.

        Args:
            table: sqlmeta Table object
            metadata: SQLAlchemy MetaData instance (optional)

        Returns:
            SQLAlchemy Table object

        Example:
            >>> from sqlmeta import Table, SqlColumn
            >>> from sqlalchemy import MetaData
            >>>
            >>> table = Table("users", columns=[
            ...     SqlColumn("id", "INTEGER", is_primary_key=True),
            ...     SqlColumn("email", "VARCHAR(255)", is_nullable=False),
            ... ])
            >>>
            >>> metadata = MetaData()
            >>> sa_table = to_sqlalchemy(table, metadata)
        """
        if metadata is None:
            metadata = MetaData()

        columns = []

        # Convert columns
        for col in table.columns:
            sa_type = _map_sql_type_to_sa(col.data_type)

            sa_col = SAColumn(
                col.name,
                sa_type,
                nullable=col.nullable,
                primary_key=col.is_primary_key,
                unique=col.is_unique,
                default=col.default_value,
                comment=getattr(col, "comment", None),
                autoincrement=getattr(col, "is_identity", False),
            )
            columns.append(sa_col)

        # Convert constraints
        for constraint in table.constraints:
            if constraint.constraint_type == ConstraintType.PRIMARY_KEY:
                columns.append(PrimaryKeyConstraint(*constraint.columns, name=constraint.name))
            elif constraint.constraint_type == ConstraintType.UNIQUE:
                columns.append(UniqueConstraint(*constraint.columns, name=constraint.name))
            elif constraint.constraint_type == ConstraintType.CHECK:
                columns.append(CheckConstraint(constraint.check_expression, name=constraint.name))

        # Create SQLAlchemy table
        sa_table = SATable(
            table.name,
            metadata,
            *columns,
            schema=table.schema,
            comment=getattr(table, "comment", None),
        )

        return sa_table

    def from_sqlalchemy(sa_table: SATable) -> Table:
        """Convert SQLAlchemy Table to sqlmeta Table.

        Args:
            sa_table: SQLAlchemy Table object

        Returns:
            sqlmeta Table object
        """
        from sqlmeta import Table, SqlColumn, SqlConstraint

        columns = []
        constraints = []

        for sa_col in sa_table.columns:
            col = SqlColumn(
                name=sa_col.name,
                data_type=str(sa_col.type),
                is_nullable=sa_col.nullable,
                default_value=str(sa_col.default) if sa_col.default else None,
                is_primary_key=sa_col.primary_key,
                is_unique=sa_col.unique,
                comment=sa_col.comment,
            )
            columns.append(col)

        # Extract constraints
        for sa_constraint in sa_table.constraints:
            if isinstance(sa_constraint, PrimaryKeyConstraint):
                constraint = SqlConstraint(
                    constraint_type=ConstraintType.PRIMARY_KEY,
                    name=sa_constraint.name,
                    column_names=[col.name for col in sa_constraint.columns],
                )
                constraints.append(constraint)

        table = Table(
            name=sa_table.name,
            schema=sa_table.schema,
            columns=columns,
            constraints=constraints,
            comment=sa_table.comment,
        )

        return table

    def get_create_ddl(table: Table, dialect: str = "postgresql") -> str:
        """Get CREATE TABLE DDL for a sqlmeta Table.

        Args:
            table: sqlmeta Table object
            dialect: SQL dialect name

        Returns:
            CREATE TABLE DDL string
        """
        metadata = MetaData()
        sa_table = to_sqlalchemy(table, metadata)

        from sqlalchemy import create_engine
        from sqlalchemy.schema import CreateTable

        # Create mock engine for the dialect
        engine = create_engine(f"{dialect}://")

        create_stmt = CreateTable(sa_table)
        return str(create_stmt.compile(engine))

    def _map_sql_type_to_sa(sql_type: str):
        """Map SQL type string to SQLAlchemy type."""
        import re

        sql_type_upper = sql_type.upper()

        # Integer types
        if any(t in sql_type_upper for t in ["INT", "SERIAL", "BIGINT", "SMALLINT"]):
            return Integer()

        # String types
        if "VARCHAR" in sql_type_upper or "CHAR" in sql_type_upper:
            match = re.search(r"\((\d+)\)", sql_type)
            if match:
                return String(int(match.group(1)))
            return String()

        if "TEXT" in sql_type_upper or "CLOB" in sql_type_upper:
            return Text()

        # Boolean
        if "BOOL" in sql_type_upper:
            return Boolean()

        # Timestamp/DateTime
        if any(t in sql_type_upper for t in ["TIMESTAMP", "DATETIME", "DATE", "TIME"]):
            return DateTime()

        # Numeric/Decimal
        if any(t in sql_type_upper for t in ["NUMERIC", "DECIMAL", "FLOAT", "DOUBLE", "REAL"]):
            return Numeric()

        # Default to String
        return String()


__all__ = [
    "to_sqlalchemy",
    "from_sqlalchemy",
    "get_create_ddl",
]
