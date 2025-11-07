Migration Generation Guide
==========================

This guide shows how to generate migration scripts from schema comparisons.

Using Alembic Adapter
---------------------

Generate Alembic operations from table comparisons:

.. code-block:: python

    from sqlmeta import Table, SqlColumn
    from sqlmeta.adapters.alembic import generate_operations

    # Define source and target schemas
    old_table = Table("users", columns=[
        SqlColumn("id", "INTEGER", is_primary_key=True),
        SqlColumn("name", "VARCHAR(100)"),
    ])

    new_table = Table("users", columns=[
        SqlColumn("id", "INTEGER", is_primary_key=True),
        SqlColumn("name", "VARCHAR(100)"),
        SqlColumn("email", "VARCHAR(255)", is_nullable=False),
        SqlColumn("created_at", "TIMESTAMP"),
    ])

    # Generate operations
    operations = generate_operations(old_table, new_table, dialect="postgresql")

    # Operations can be used in Alembic migration scripts
    for op in operations:
        print(op)

Complete Migration Script
--------------------------

Generate a complete Alembic migration script:

.. code-block:: python

    from sqlmeta.adapters.alembic import generate_migration_script

    # Source and target schemas (list of tables)
    source_tables = [users_table, posts_table]
    target_tables = [users_table_v2, posts_table, comments_table]

    # Generate complete migration script
    script = generate_migration_script(
        source_tables=source_tables,
        target_tables=target_tables,
        dialect="postgresql",
        message="Add comments table and update users"
    )

    # Save to file
    with open("alembic/versions/001_migration.py", "w") as f:
        f.write(script)

Manual Migration Generation
----------------------------

Generate SQL ALTER statements manually:

.. code-block:: python

    from sqlmeta.comparison.comparator import ObjectComparator

    comparator = ObjectComparator(dialect="postgresql")
    diff = comparator.compare_tables(old_table, new_table)

    statements = []

    # Add columns
    for col_name in diff.missing_columns:
        col = next(c for c in new_table.columns if c.name == col_name)
        nullable = "NULL" if col.nullable else "NOT NULL"
        default = f"DEFAULT {col.default_value}" if col.default_value else ""
        statements.append(
            f"ALTER TABLE {new_table.name} "
            f"ADD COLUMN {col.name} {col.data_type} {nullable} {default};"
        )

    # Drop columns
    for col_name in diff.extra_columns:
        statements.append(
            f"ALTER TABLE {old_table.name} DROP COLUMN {col_name};"
        )

    # Modify columns
    for col_diff in diff.modified_columns:
        col = next(c for c in new_table.columns if c.name == col_diff.column_name)

        if col_diff.type_mismatch:
            statements.append(
                f"ALTER TABLE {new_table.name} "
                f"ALTER COLUMN {col.name} TYPE {col.data_type};"
            )

        if col_diff.nullable_mismatch:
            null_clause = "DROP NOT NULL" if col.nullable else "SET NOT NULL"
            statements.append(
                f"ALTER TABLE {new_table.name} "
                f"ALTER COLUMN {col.name} {null_clause};"
            )

    # Print all statements
    for stmt in statements:
        print(stmt)

Handling Different Dialects
----------------------------

Generate migrations for different SQL dialects:

PostgreSQL
~~~~~~~~~~

.. code-block:: python

    operations = generate_operations(
        old_table, new_table,
        dialect="postgresql"
    )

MySQL
~~~~~

.. code-block:: python

    operations = generate_operations(
        old_table, new_table,
        dialect="mysql"
    )

SQL Server
~~~~~~~~~~

.. code-block:: python

    operations = generate_operations(
        old_table, new_table,
        dialect="mssql"
    )

Best Practices
--------------

1. **Always Review Generated Migrations**

   Generated migrations should be reviewed before applying to ensure correctness.

2. **Test Migrations**

   Test migrations on a non-production database first.

3. **Handle Data Migration**

   Generated migrations handle schema changes but not data migration. Add custom
   data migration code as needed:

   .. code-block:: python

       def upgrade():
           # Schema migration
           op.add_column('users', sa.Column('email', sa.String(255)))

           # Data migration
           op.execute("UPDATE users SET email = name || '@example.com'")

4. **Use Transactions**

   Wrap migrations in transactions when supported:

   .. code-block:: python

       def upgrade():
           with op.get_context().autocommit_block():
               # Your migration operations
               pass

5. **Add Indexes After Data**

   When adding columns with indexes, create the column first, then the index:

   .. code-block:: python

       def upgrade():
           op.add_column('users', sa.Column('email', sa.String(255)))
           op.create_index('ix_users_email', 'users', ['email'])

Rollback Strategies
-------------------

Always ensure migrations are reversible:

.. code-block:: python

    # The generate_migration_script function automatically generates
    # both upgrade() and downgrade() functions

    script = generate_migration_script(
        source_tables=old_schema,
        target_tables=new_schema,
        dialect="postgresql"
    )

    # The script includes:
    # - upgrade(): source -> target
    # - downgrade(): target -> source

Example: Complete Workflow
---------------------------

.. code-block:: python

    from sqlmeta import Table, SqlColumn
    from sqlmeta.adapters.alembic import generate_migration_script

    # Step 1: Define current schema
    current_schema = [
        Table("users", columns=[
            SqlColumn("id", "INTEGER", is_primary_key=True),
            SqlColumn("name", "VARCHAR(100)"),
        ])
    ]

    # Step 2: Define desired schema
    desired_schema = [
        Table("users", columns=[
            SqlColumn("id", "INTEGER", is_primary_key=True),
            SqlColumn("name", "VARCHAR(100)"),
            SqlColumn("email", "VARCHAR(255)", is_nullable=False),
        ]),
        Table("posts", columns=[
            SqlColumn("id", "INTEGER", is_primary_key=True),
            SqlColumn("user_id", "INTEGER"),
            SqlColumn("title", "VARCHAR(200)"),
            SqlColumn("content", "TEXT"),
        ])
    ]

    # Step 3: Generate migration
    script = generate_migration_script(
        source_tables=current_schema,
        target_tables=desired_schema,
        dialect="postgresql",
        message="Add email to users and create posts table"
    )

    # Step 4: Save migration
    with open("migration_001.py", "w") as f:
        f.write(script)

    # Step 5: Review and apply
    print("Review the migration file and apply with:")
    print("alembic upgrade head")
