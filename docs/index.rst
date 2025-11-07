sqlmeta Documentation
=====================

**Universal SQL metadata and schema representation for Python**

``sqlmeta`` is a Python library that provides a dialect-agnostic representation of SQL database schemas and metadata. It enables you to work with database objects (tables, views, procedures, etc.) across different SQL dialects in a unified way.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   why_sqlmeta
   installation
   quickstart
   api/index
   guides/index
   changelog

Features
--------

* **Dialect-agnostic schema representation** - Work with SQL metadata without worrying about database-specific quirks
* **Comprehensive object support** - Tables, views, procedures, triggers, sequences, indexes, partitions, and more
* **Schema comparison & drift detection** - Intelligent comparison with type normalization and severity levels
* **Framework integrations** - Convert to/from SQLAlchemy, Pydantic, and Alembic
* **Type-aware comparison** - Handles data type variations across different SQL dialects
* **System-generated name handling** - Automatically detects and handles database-generated constraint names
* **Zero dependencies** - Core library has no required dependencies (adapters are optional)
* **Fully typed** - Complete type hints for better IDE support

Supported Databases
-------------------

* PostgreSQL (full support including extensions, foreign data wrappers, materialized views)
* MySQL (full support including events, storage engines, partitions)
* Oracle (full support including packages, database links, synonyms)
* SQL Server (full support including linked servers, temporal tables, memory-optimized tables)
* Generic SQL (fallback for other SQL databases)

Quick Example
-------------

.. code-block:: python

    from sqlmeta import Table, SqlColumn, SqlConstraint, ConstraintType

    # Define a table
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

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
