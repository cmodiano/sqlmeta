Quick Start
===========

This guide will help you get started with sqlmeta quickly.

Creating Tables
---------------

.. code-block:: python

    from sqlmeta import Table, SqlColumn, SqlConstraint, ConstraintType

    # Define a simple table
    users_table = Table(
        name="users",
        schema="public",
        dialect="postgresql",
        columns=[
            SqlColumn("id", "SERIAL", is_primary_key=True),
            SqlColumn("email", "VARCHAR(255)", is_nullable=False),
            SqlColumn("name", "VARCHAR(100)", is_nullable=False),
            SqlColumn("created_at", "TIMESTAMP", default_value="CURRENT_TIMESTAMP"),
        ],
        constraints=[
            SqlConstraint(
                constraint_type=ConstraintType.UNIQUE,
                name="uq_users_email",
                column_names=["email"]
            )
        ]
    )

    # Generate CREATE TABLE statement
    print(users_table.create_statement)

Schema Comparison
-----------------

Compare two table definitions to detect differences:

.. code-block:: python

    from sqlmeta.comparison.comparator import ObjectComparator

    # Define source and target tables
    source_table = Table(
        name="users",
        columns=[
            SqlColumn("id", "INTEGER", is_primary_key=True),
            SqlColumn("name", "VARCHAR(100)"),
        ]
    )

    target_table = Table(
        name="users",
        columns=[
            SqlColumn("id", "INTEGER", is_primary_key=True),
            SqlColumn("name", "VARCHAR(100)"),
            SqlColumn("email", "VARCHAR(255)", is_nullable=False),
        ]
    )

    # Compare tables
    comparator = ObjectComparator(dialect="postgresql")
    diff = comparator.compare_tables(source_table, target_table)

    if diff.has_diffs:
        print(f"Severity: {diff.severity.value}")
        print(f"Missing columns: {diff.missing_columns}")
        print(f"Extra columns: {diff.extra_columns}")

        for col_diff in diff.modified_columns:
            print(f"Column '{col_diff.column_name}' changed:")
            if col_diff.type_mismatch:
                print(f"  Type: {col_diff.source_type} -> {col_diff.target_type}")
            if col_diff.nullable_mismatch:
                print(f"  Nullable changed")

SQLAlchemy Integration
----------------------

Convert between sqlmeta and SQLAlchemy:

.. code-block:: python

    from sqlalchemy import MetaData
    from sqlmeta.adapters.sqlalchemy import to_sqlalchemy, from_sqlalchemy

    # Convert sqlmeta Table to SQLAlchemy Table
    metadata = MetaData()
    sa_table = to_sqlalchemy(users_table, metadata)

    # Use with SQLAlchemy
    from sqlalchemy import create_engine
    engine = create_engine("postgresql://localhost/mydb")
    sa_table.create(engine)

    # Convert back to sqlmeta
    sqlmeta_table = from_sqlalchemy(sa_table)

Pydantic Integration
--------------------

Generate Pydantic models from tables:

.. code-block:: python

    from sqlmeta.adapters.pydantic import to_pydantic

    # Generate Pydantic model
    UserModel = to_pydantic(users_table)

    # Use the model
    user = UserModel(
        id=1,
        email="user@example.com",
        name="John Doe",
        created_at="2024-01-01T00:00:00"
    )

    # Serialize
    print(user.model_dump_json())

Alembic Integration
-------------------

Generate Alembic migrations:

.. code-block:: python

    from sqlmeta.adapters.alembic import generate_operations

    # Compare tables and generate operations
    operations = generate_operations(
        source_table=old_table,
        target_table=new_table,
        dialect="postgresql"
    )

    # Operations can be used in Alembic migration scripts
    for op in operations:
        print(op)

Serialization
-------------

Export and import table definitions:

.. code-block:: python

    import json

    # Export to dictionary
    table_dict = users_table.to_dict()

    # Save to JSON
    with open("schema.json", "w") as f:
        json.dump(table_dict, f, indent=2)

    # Load from JSON
    with open("schema.json", "r") as f:
        loaded_dict = json.load(f)

    # Recreate table
    users_table_copy = Table.from_dict(loaded_dict)

Working with Views
------------------

.. code-block:: python

    from sqlmeta.objects.view import View

    # Create a view
    users_view = View(
        name="active_users",
        schema="public",
        definition="SELECT * FROM users WHERE active = true",
        dialect="postgresql"
    )

    # Materialized view (PostgreSQL)
    mat_view = View(
        name="users_summary",
        schema="public",
        definition="SELECT COUNT(*) as total FROM users",
        materialized=True,
        dialect="postgresql"
    )

Working with Procedures
-----------------------

.. code-block:: python

    from sqlmeta.objects.procedure import Procedure

    # Create a stored procedure
    proc = Procedure(
        name="update_user_email",
        schema="public",
        body="""
        BEGIN
            UPDATE users SET email = p_email WHERE id = p_id;
        END;
        """,
        parameters=["p_id INTEGER", "p_email VARCHAR"],
        dialect="postgresql"
    )

Next Steps
----------

* Explore the :doc:`api/index` for detailed API documentation
* Read the :doc:`guides/index` for more advanced usage patterns
* Check out the examples in the GitHub repository
