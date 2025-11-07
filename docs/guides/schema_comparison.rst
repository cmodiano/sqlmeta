Schema Comparison Guide
=======================

This guide explains how to use sqlmeta for schema comparison and drift detection.

Basic Comparison
----------------

Compare two table definitions:

.. code-block:: python

    from sqlmeta import Table, SqlColumn
    from sqlmeta.comparison.comparator import ObjectComparator

    source = Table("users", columns=[
        SqlColumn("id", "INTEGER", is_primary_key=True),
        SqlColumn("name", "VARCHAR(100)"),
    ])

    target = Table("users", columns=[
        SqlColumn("id", "INTEGER", is_primary_key=True),
        SqlColumn("name", "VARCHAR(100)"),
        SqlColumn("email", "VARCHAR(255)", is_nullable=False),
    ])

    comparator = ObjectComparator(dialect="postgresql")
    diff = comparator.compare_tables(source, target)

Understanding Diff Results
---------------------------

The comparison returns a ``TableDiff`` object with detailed information:

.. code-block:: python

    if diff.has_diffs:
        print(f"Severity: {diff.severity.value}")

        # Missing columns (in target but not in source)
        for col_name in diff.missing_columns:
            print(f"Add column: {col_name}")

        # Extra columns (in source but not in target)
        for col_name in diff.extra_columns:
            print(f"Drop column: {col_name}")

        # Modified columns
        for col_diff in diff.modified_columns:
            print(f"Modify column: {col_diff.column_name}")
            if col_diff.type_mismatch:
                print(f"  Type: {col_diff.source_type} -> {col_diff.target_type}")
            if col_diff.nullable_mismatch:
                print(f"  Nullable: {col_diff.source_nullable} -> {col_diff.target_nullable}")

Severity Levels
---------------

Differences are categorized by severity:

* **ERROR** - Breaking changes (column removed, incompatible type change)
* **WARNING** - Non-breaking but important (nullable changed, constraint modified)
* **INFO** - Cosmetic differences (comments, formatting)

.. code-block:: python

    from sqlmeta.comparison.diff_models import DiffSeverity

    if diff.severity == DiffSeverity.ERROR:
        print("Breaking changes detected!")
    elif diff.severity == DiffSeverity.WARNING:
        print("Non-breaking changes detected")
    else:
        print("Only cosmetic changes")

Comparing Schemas
-----------------

Compare entire schemas with multiple tables:

.. code-block:: python

    from sqlmeta.comparison.diff_models import SchemaDiff

    source_tables = [table1, table2, table3]
    target_tables = [table1_modified, table2, table4]

    comparator = ObjectComparator(dialect="postgresql")
    schema_diff = comparator.compare_schemas(source_tables, target_tables)

    # Iterate through table diffs
    for table_diff in schema_diff.table_diffs:
        if table_diff.has_diffs:
            print(f"Table {table_diff.table_name}: {table_diff.severity.value}")

Type Normalization
------------------

The comparator automatically normalizes data types for accurate comparison:

.. code-block:: python

    from sqlmeta.comparison.type_normalizer import DataTypeNormalizer

    normalizer = DataTypeNormalizer(dialect="postgresql")

    # These are considered equivalent
    assert normalizer.normalize("VARCHAR(255)") == normalizer.normalize("CHARACTER VARYING(255)")
    assert normalizer.normalize("INT") == normalizer.normalize("INTEGER")
    assert normalizer.normalize("BOOL") == normalizer.normalize("BOOLEAN")

System-Generated Names
----------------------

The comparator automatically handles system-generated constraint names:

.. code-block:: python

    # Oracle: SYS_C0013220
    # SQL Server: PK__users__3213E83F
    # These are matched by constraint type and columns, not name

    source = Table("users", columns=[
        SqlColumn("id", "INTEGER", is_primary_key=True),
    ], constraints=[
        SqlConstraint(
            constraint_type=ConstraintType.PRIMARY_KEY,
            name="SYS_C0013220",  # System-generated
            column_names=["id"]
        )
    ])

    target = Table("users", columns=[
        SqlColumn("id", "INTEGER", is_primary_key=True),
    ], constraints=[
        SqlConstraint(
            constraint_type=ConstraintType.PRIMARY_KEY,
            name="pk_users",  # User-defined
            column_names=["id"]
        )
    ])

    diff = comparator.compare_tables(source, target)
    # No constraint difference detected (matched by structure)

Generating Reports
------------------

Generate human-readable comparison reports:

.. code-block:: python

    def generate_report(diff):
        """Generate a comparison report."""
        if not diff.has_diffs:
            return "No differences found"

        lines = [f"Table: {diff.table_name}", f"Severity: {diff.severity.value}", ""]

        if diff.missing_columns:
            lines.append("Columns to add:")
            for col in diff.missing_columns:
                lines.append(f"  + {col}")
            lines.append("")

        if diff.extra_columns:
            lines.append("Columns to remove:")
            for col in diff.extra_columns:
                lines.append(f"  - {col}")
            lines.append("")

        if diff.modified_columns:
            lines.append("Columns to modify:")
            for col_diff in diff.modified_columns:
                lines.append(f"  ~ {col_diff.column_name}")
                if col_diff.type_mismatch:
                    lines.append(f"    Type: {col_diff.source_type} -> {col_diff.target_type}")
                if col_diff.nullable_mismatch:
                    lines.append(f"    Nullable: {col_diff.source_nullable} -> {col_diff.target_nullable}")
            lines.append("")

        return "\n".join(lines)

    print(generate_report(diff))
