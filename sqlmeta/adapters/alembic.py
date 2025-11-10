"""Alembic integration for sqlmeta.

This module provides functions to integrate sqlmeta with Alembic for database migrations.
It enables comparing sqlmeta schemas with database schemas and generating Alembic operations.

Example:
    >>> from sqlmeta import Table, SqlColumn
    >>> from sqlmeta.adapters.alembic import generate_operations
    >>> from alembic.operations import Operations
    >>>
    >>> source_table = Table("users", columns=[...])
    >>> target_table = Table("users", columns=[...])
    >>> operations = generate_operations(source_table, target_table)
"""

from typing import List, Optional

try:
    from alembic.operations import Operations
    from alembic.operations.ops import (
        AddColumnOp,
        AlterColumnOp,
        CreateTableOp,
        DropColumnOp,
        DropTableOp,
        MigrationScript,
    )

    ALEMBIC_AVAILABLE = True
except ImportError:
    ALEMBIC_AVAILABLE = False


if not ALEMBIC_AVAILABLE:

    def generate_operations(*args, **kwargs):
        raise ImportError(
            "Alembic is not installed. " "Install it with: pip install sqlmeta[alembic]"
        )

    def to_alembic_table(*args, **kwargs):
        raise ImportError(
            "Alembic is not installed. " "Install it with: pip install sqlmeta[alembic]"
        )

    def generate_migration_script(*args, **kwargs):
        raise ImportError(
            "Alembic is not installed. " "Install it with: pip install sqlmeta[alembic]"
        )

else:
    from sqlmeta import Table, SqlColumn
    from sqlmeta.comparison.comparator import ObjectComparator
    from sqlmeta.comparison.diff_models import TableDiff
    from sqlmeta.comparison.type_normalizer import DataTypeNormalizer

    def to_alembic_table(table: Table) -> CreateTableOp:
        """Convert sqlmeta Table to Alembic CreateTableOp.

        Args:
            table: sqlmeta Table object

        Returns:
            Alembic CreateTableOp object

        Example:
            >>> from sqlmeta import Table, SqlColumn
            >>>
            >>> table = Table("users", columns=[
            ...     SqlColumn("id", "INTEGER", is_primary_key=True),
            ...     SqlColumn("email", "VARCHAR(255)", is_nullable=False),
            ... ])
            >>>
            >>> create_op = to_alembic_table(table)
        """
        from sqlalchemy import Column, Integer, String, Boolean, MetaData
        from sqlalchemy.schema import Table as SATable

        # Convert to SQLAlchemy table first
        try:
            from sqlmeta.adapters.sqlalchemy import to_sqlalchemy

            metadata = MetaData()
            sa_table = to_sqlalchemy(table, metadata)

            # Create Alembic CreateTableOp from SQLAlchemy table
            return CreateTableOp.from_table(sa_table)
        except ImportError:
            raise ImportError(
                "SQLAlchemy is required for Alembic integration. "
                "Install it with: pip install sqlmeta[all]"
            )

    def generate_operations(
        source_table: Optional[Table], target_table: Optional[Table], dialect: Optional[str] = None
    ) -> List:
        """Generate Alembic operations from table comparison.

        Compares two table definitions and generates the necessary Alembic
        operations to migrate from source to target.

        Args:
            source_table: Current table definition (None if table doesn't exist)
            target_table: Desired table definition (None if dropping table)
            dialect: SQL dialect for comparison

        Returns:
            List of Alembic operation objects

        Example:
            >>> source = Table("users", columns=[
            ...     SqlColumn("id", "INTEGER", is_primary_key=True),
            ...     SqlColumn("name", "VARCHAR(100)"),
            ... ])
            >>> target = Table("users", columns=[
            ...     SqlColumn("id", "INTEGER", is_primary_key=True),
            ...     SqlColumn("name", "VARCHAR(100)"),
            ...     SqlColumn("email", "VARCHAR(255)", is_nullable=False),
            ... ])
            >>> ops = generate_operations(source, target, dialect="postgresql")
            >>> # Results in: [AddColumnOp(...)]
        """
        operations = []

        # Handle table creation
        if source_table is None and target_table is not None:
            operations.append(to_alembic_table(target_table))
            return operations

        # Handle table drop
        if source_table is not None and target_table is None:
            operations.append(DropTableOp(source_table.name, schema=source_table.schema))
            return operations

        # Handle table modification
        if source_table is not None and target_table is not None:
            normalizer = DataTypeNormalizer()
            comparison_dialect = (
                dialect
                or getattr(target_table, "dialect", None)
                or getattr(source_table, "dialect", None)
                or "postgresql"
            )
            comparator = ObjectComparator(normalizer)
            diff = comparator.compare_tables(source_table, target_table, comparison_dialect)

            if not diff.has_diffs:
                return operations

            # Generate operations for new columns that exist in target but not source
            for col_name in diff.extra_columns:
                target_col = next(c for c in target_table.columns if c.name == col_name)
                from sqlalchemy import Column
                from sqlmeta.adapters.sqlalchemy import _map_sql_type_to_sa

                operations.append(
                    AddColumnOp(
                        target_table.name,
                        Column(
                            target_col.name,
                            _map_sql_type_to_sa(target_col.data_type),
                            nullable=target_col.nullable,
                            server_default=target_col.default_value,
                        ),
                        schema=target_table.schema,
                    )
                )

            # Generate operations for columns that exist in source but not in target
            for col_name in diff.missing_columns:
                operations.append(
                    DropColumnOp(source_table.name, col_name, schema=source_table.schema)
                )

            # Generate operations for modified columns
            for col_diff in diff.modified_columns:
                target_col = next(c for c in target_table.columns if c.name == col_diff.column_name)

                # Prepare kwargs for AlterColumnOp
                alter_kwargs = {
                    "table_name": target_table.name,
                    "column_name": col_diff.column_name,
                    "schema": target_table.schema,
                }

                # Add modifications
                if col_diff.data_type_diff:
                    from sqlmeta.adapters.sqlalchemy import _map_sql_type_to_sa

                    alter_kwargs["type_"] = _map_sql_type_to_sa(target_col.data_type)

                if col_diff.nullable_diff:
                    alter_kwargs["nullable"] = target_col.nullable

                if col_diff.default_diff:
                    alter_kwargs["server_default"] = target_col.default_value

                operations.append(AlterColumnOp(**alter_kwargs))

        return operations

    def generate_migration_script(
        source_tables: List[Table],
        target_tables: List[Table],
        dialect: Optional[str] = None,
        message: str = "Auto-generated migration",
    ) -> str:
        """Generate a complete Alembic migration script.

        Compares two sets of tables and generates a complete migration script
        with upgrade() and downgrade() functions.

        Args:
            source_tables: Current schema tables
            target_tables: Desired schema tables
            dialect: SQL dialect for comparison
            message: Migration message/description

        Returns:
            String containing the migration script

        Example:
            >>> source = [Table("users", ...)]
            >>> target = [Table("users", ...), Table("posts", ...)]
            >>> script = generate_migration_script(source, target, "postgresql")
            >>> print(script)
        """
        # Build table mappings
        source_map = {t.name: t for t in source_tables}
        target_map = {t.name: t for t in target_tables}

        all_table_names = set(source_map.keys()) | set(target_map.keys())

        upgrade_ops = []
        downgrade_ops = []

        for table_name in sorted(all_table_names):
            source_table = source_map.get(table_name)
            target_table = target_map.get(table_name)

            # Generate upgrade operations
            ops = generate_operations(source_table, target_table, dialect)
            upgrade_ops.extend(ops)

            # Generate downgrade operations (reverse)
            reverse_ops = generate_operations(target_table, source_table, dialect)
            downgrade_ops.extend(reverse_ops)

        # Generate script content
        script = f'''"""
{message}

Revision ID: autogenerated
Revises:
Create Date: {_get_timestamp()}

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'autogenerated'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade schema."""
{_format_operations(upgrade_ops, indent=1)}


def downgrade() -> None:
    """Downgrade schema."""
{_format_operations(downgrade_ops, indent=1)}
'''
        return script

    def _get_timestamp() -> str:
        """Get current timestamp in Alembic format."""
        from datetime import datetime

        return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

    def _format_operations(operations: List, indent: int = 1) -> str:
        """Format operations as Python code.

        Args:
            operations: List of Alembic operations
            indent: Indentation level

        Returns:
            Formatted Python code
        """
        if not operations:
            return "    " * indent + "pass"

        lines = []
        indent_str = "    " * indent

        for op in operations:
            if isinstance(op, CreateTableOp):
                lines.append(f"{indent_str}op.create_table(")
                lines.append(f"{indent_str}    '{op.table_name}',")
                for col in op.columns:
                    lines.append(f"{indent_str}    {_format_column(col)},")
                if op.schema:
                    lines.append(f"{indent_str}    schema='{op.schema}'")
                lines.append(f"{indent_str})")

            elif isinstance(op, DropTableOp):
                schema_part = f", schema='{op.schema}'" if op.schema else ""
                lines.append(f"{indent_str}op.drop_table('{op.table_name}'{schema_part})")

            elif isinstance(op, AddColumnOp):
                schema_part = f", schema='{op.schema}'" if op.schema else ""
                lines.append(
                    f"{indent_str}op.add_column('{op.table_name}', "
                    f"{_format_column(op.column)}{schema_part})"
                )

            elif isinstance(op, DropColumnOp):
                schema_part = f", schema='{op.schema}'" if op.schema else ""
                lines.append(
                    f"{indent_str}op.drop_column('{op.table_name}', "
                    f"'{op.column_name}'{schema_part})"
                )

            elif isinstance(op, AlterColumnOp):
                schema_part = f", schema='{op.schema}'" if op.schema else ""
                kwargs = []
                if hasattr(op, "type_") and op.type_ is not None:
                    kwargs.append(f"type_={op.type_}")
                if hasattr(op, "nullable") and op.nullable is not None:
                    kwargs.append(f"nullable={op.nullable}")
                if hasattr(op, "server_default"):
                    kwargs.append(f"server_default={repr(op.server_default)}")

                lines.append(
                    f"{indent_str}op.alter_column('{op.table_name}', "
                    f"'{op.column_name}'{schema_part}"
                )
                for kwarg in kwargs:
                    lines.append(f"{indent_str}    {kwarg},")
                lines.append(f"{indent_str})")

        return "\n".join(lines) if lines else f"{indent_str}pass"

    def _format_column(column) -> str:
        """Format a SQLAlchemy column as Python code.

        Args:
            column: SQLAlchemy Column object

        Returns:
            Formatted Python code string
        """
        parts = [f"sa.Column('{column.name}', {column.type}"]

        if not column.nullable:
            parts.append("nullable=False")
        if column.default is not None:
            parts.append(f"default={repr(column.default)}")
        if column.primary_key:
            parts.append("primary_key=True")
        if column.unique:
            parts.append("unique=True")

        return ", ".join(parts) + ")"
