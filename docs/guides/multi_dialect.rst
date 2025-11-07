Multi-Dialect Support Guide
============================

This guide explains how to work with multiple SQL dialects in sqlmeta.

Setting Dialects
----------------

Always specify the dialect when creating objects:

.. code-block:: python

    from sqlmeta import Table, SqlColumn

    # PostgreSQL
    pg_table = Table(
        "users",
        dialect="postgresql",
        columns=[SqlColumn("id", "SERIAL", is_primary_key=True)]
    )

    # MySQL
    mysql_table = Table(
        "users",
        dialect="mysql",
        columns=[SqlColumn("id", "INT AUTO_INCREMENT", is_primary_key=True)]
    )

    # Oracle
    oracle_table = Table(
        "users",
        dialect="oracle",
        columns=[SqlColumn("id", "NUMBER GENERATED ALWAYS AS IDENTITY", is_primary_key=True)]
    )

Dialect-Specific Features
--------------------------

PostgreSQL
~~~~~~~~~~

.. code-block:: python

    from sqlmeta import Table, SqlColumn
    from sqlmeta.objects.extension import Extension
    from sqlmeta.objects.view import View

    # Extensions
    uuid_extension = Extension(
        name="uuid-ossp",
        schema="public",
        dialect="postgresql"
    )

    # Materialized views
    mat_view = View(
        name="user_stats",
        definition="SELECT user_id, COUNT(*) FROM posts GROUP BY user_id",
        materialized=True,
        dialect="postgresql"
    )

    # SERIAL types
    table = Table(
        "users",
        dialect="postgresql",
        columns=[
            SqlColumn("id", "SERIAL", is_primary_key=True),
            SqlColumn("uuid", "UUID", default_value="uuid_generate_v4()"),
        ]
    )

MySQL
~~~~~

.. code-block:: python

    from sqlmeta.objects.event import Event

    # Storage engines
    innodb_table = Table(
        "users",
        dialect="mysql",
        storage_engine="InnoDB",
        columns=[SqlColumn("id", "INT AUTO_INCREMENT", is_primary_key=True)]
    )

    # Events (scheduled tasks)
    cleanup_event = Event(
        name="cleanup_old_logs",
        schedule="EVERY 1 DAY",
        body="DELETE FROM logs WHERE created_at < DATE_SUB(NOW(), INTERVAL 30 DAY)",
        dialect="mysql"
    )

Oracle
~~~~~~

.. code-block:: python

    from sqlmeta.objects.package import Package
    from sqlmeta.objects.database_link import DatabaseLink

    # Packages
    pkg = Package(
        name="user_pkg",
        schema="public",
        spec="PROCEDURE update_user(p_id NUMBER, p_name VARCHAR2);",
        body="...",
        dialect="oracle"
    )

    # Database links
    db_link = DatabaseLink(
        name="remote_db",
        connect_string="user/pass@remote",
        dialect="oracle"
    )

SQL Server
~~~~~~~~~~

.. code-block:: python

    from sqlmeta.objects.linked_server import LinkedServer

    # Memory-optimized tables
    memory_table = Table(
        "sessions",
        dialect="mssql",
        memory_optimized=True,
        columns=[SqlColumn("id", "INT", is_primary_key=True)]
    )

    # Temporal tables
    temporal_table = Table(
        "employees",
        dialect="mssql",
        system_versioned=True,
        history_table="employees_history",
        columns=[
            SqlColumn("id", "INT", is_primary_key=True),
            SqlColumn("name", "VARCHAR(100)"),
        ]
    )

    # Linked servers
    linked = LinkedServer(
        name="REMOTE_SERVER",
        product_name="SQL Server",
        data_source="remote.server.com",
        dialect="mssql"
    )

Cross-Dialect Conversion
-------------------------

Convert table definitions between dialects:

.. code-block:: python

    def convert_dialect(table, target_dialect):
        """Convert a table to a different dialect."""
        # Export to dict
        table_dict = table.to_dict()

        # Update dialect
        table_dict['dialect'] = target_dialect

        # Update dialect-specific data types
        for col in table_dict['columns']:
            col['data_type'] = convert_type(
                col['data_type'],
                table.dialect,
                target_dialect
            )

        # Recreate table
        return Table.from_dict(table_dict)

    def convert_type(data_type, source_dialect, target_dialect):
        """Convert data type between dialects."""
        type_mappings = {
            ('postgresql', 'mysql'): {
                'SERIAL': 'INT AUTO_INCREMENT',
                'BOOLEAN': 'TINYINT(1)',
                'TEXT': 'LONGTEXT',
            },
            ('mysql', 'postgresql'): {
                'INT AUTO_INCREMENT': 'SERIAL',
                'TINYINT(1)': 'BOOLEAN',
                'LONGTEXT': 'TEXT',
            },
            # Add more mappings...
        }

        mapping = type_mappings.get((source_dialect, target_dialect), {})
        return mapping.get(data_type.upper(), data_type)

    # Example usage
    pg_table = Table("users", dialect="postgresql", columns=[
        SqlColumn("id", "SERIAL", is_primary_key=True),
        SqlColumn("active", "BOOLEAN"),
    ])

    mysql_table = convert_dialect(pg_table, "mysql")

Type Normalization
------------------

The type normalizer handles dialect-specific type variations:

.. code-block:: python

    from sqlmeta.comparison.type_normalizer import DataTypeNormalizer

    # PostgreSQL
    pg_normalizer = DataTypeNormalizer(dialect="postgresql")
    assert pg_normalizer.normalize("VARCHAR(255)") == "VARCHAR(255)"
    assert pg_normalizer.normalize("CHARACTER VARYING(255)") == "VARCHAR(255)"
    assert pg_normalizer.normalize("BOOL") == "BOOLEAN"

    # MySQL
    mysql_normalizer = DataTypeNormalizer(dialect="mysql")
    assert mysql_normalizer.normalize("INT") == "INTEGER"
    assert mysql_normalizer.normalize("TINYINT(1)") == "BOOLEAN"

Best Practices
--------------

1. **Always Specify Dialect**

   .. code-block:: python

       # Good
       table = Table("users", dialect="postgresql", columns=[...])

       # Bad - dialect may be guessed incorrectly
       table = Table("users", columns=[...])

2. **Use Dialect-Agnostic Types When Possible**

   .. code-block:: python

       # Use standard SQL types
       SqlColumn("name", "VARCHAR(100)")  # Works everywhere
       SqlColumn("created_at", "TIMESTAMP")  # Works everywhere

       # Avoid dialect-specific types unless necessary
       # SqlColumn("id", "SERIAL")  # PostgreSQL-specific

3. **Test with Multiple Dialects**

   If supporting multiple databases, test schema definitions with each dialect.

4. **Document Dialect Requirements**

   .. code-block:: python

       class UserSchema:
           """User table schema.

           Requires:
           - PostgreSQL 12+ for UUID support
           - MySQL 8+ for JSON columns
           """
           pass

5. **Use Dialect Detection**

   .. code-block:: python

       def get_table_for_dialect(dialect):
           """Get table definition for specific dialect."""
           if dialect == "postgresql":
               return pg_table
           elif dialect == "mysql":
               return mysql_table
           elif dialect == "oracle":
               return oracle_table
           else:
               raise ValueError(f"Unsupported dialect: {dialect}")

Comparison Across Dialects
---------------------------

Compare schemas from different databases:

.. code-block:: python

    from sqlmeta.comparison.comparator import ObjectComparator

    # Source is PostgreSQL
    pg_table = Table("users", dialect="postgresql", columns=[
        SqlColumn("id", "SERIAL", is_primary_key=True),
    ])

    # Target is MySQL
    mysql_table = Table("users", dialect="mysql", columns=[
        SqlColumn("id", "INT AUTO_INCREMENT", is_primary_key=True),
    ])

    # Compare (handles type normalization)
    comparator = ObjectComparator(dialect="generic")
    diff = comparator.compare_tables(pg_table, mysql_table)

    # No differences (SERIAL and INT AUTO_INCREMENT are both identity columns)
    assert not diff.has_diffs
