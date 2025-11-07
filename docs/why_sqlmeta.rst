Why sqlmeta?
============

**"Why not just use SQLAlchemy directly?"**

This is a common and fair question. While SQLAlchemy is an excellent tool for ORM and database operations, sqlmeta solves fundamentally different problems.

Schema Comparison & Drift Detection
------------------------------------

**SQLAlchemy** represents schemas *for your application* - it's designed to help your application interact with a database.

**sqlmeta** compares schemas *from different sources* - it's designed to detect and analyze differences:

* Compare SQL scripts against live databases
* Detect drift between dev, staging, and production environments
* Validate that migrations were applied correctly
* Compare schemas across different database vendors
* Generate reports on schema differences with severity levels

.. code-block:: python

    # This is what sqlmeta excels at - SQLAlchemy doesn't provide this
    from sqlmeta.comparison.comparator import ObjectComparator

    comparator = ObjectComparator(dialect="postgresql")
    diff = comparator.compare_tables(source_table, target_table)

    if diff.has_diffs:
        print(f"Schema drift detected! Severity: {diff.severity}")
        print(f"Missing columns: {diff.missing_columns}")
        print(f"Modified columns: {len(diff.modified_columns)}")

**Real-world scenario**: You deploy a service that depends on a specific database schema. How do you verify that production has the right schema? sqlmeta can compare your expected schema against the live database and tell you exactly what's different.

Lightweight & Serializable
---------------------------

**SQLAlchemy** metadata is tightly coupled to engines, connections, and sessions. It's designed for runtime database operations.

**sqlmeta** is pure data - just Python dataclasses and enums:

* **Zero dependencies** for core functionality (no database drivers required)
* **JSON serializable** - store schemas in files, databases, or APIs
* **Language agnostic** - share schema definitions between services in different languages
* **Version control friendly** - track schema changes in git as readable JSON/YAML

.. code-block:: python

    import json
    from sqlmeta import Table, SqlColumn

    # Define schema
    table = Table("users", columns=[
        SqlColumn("id", "INTEGER", is_primary_key=True),
        SqlColumn("email", "VARCHAR(255)"),
    ])

    # Serialize to JSON
    schema_json = json.dumps(table.to_dict(), indent=2)

    # Store anywhere - file, S3, database, Redis
    with open('schema.json', 'w') as f:
        f.write(schema_json)

    # Recreate from JSON anywhere, anytime
    with open('schema.json', 'r') as f:
        schema_dict = json.load(f)
    table_copy = Table.from_dict(schema_dict)

**Real-world scenario**: You have microservices in Python, Go, and Node.js that all need to know about the database schema. Store the schema as JSON and each service can read it, no Python required.

Broader Database Object Support
--------------------------------

**SQLAlchemy** focuses primarily on tables, columns, and constraints - the objects needed for ORM operations.

**sqlmeta** represents the *full database catalog*:

* **Stored procedures and functions** with parameters and return types
* **Packages** (Oracle)
* **Triggers** with timing, events, and full metadata
* **Database links** (Oracle) and **Linked servers** (SQL Server)
* **Foreign data wrappers** and **foreign servers** (PostgreSQL)
* **Extensions** (PostgreSQL)
* **Events** (MySQL scheduled tasks)
* **Synonyms** (Oracle, SQL Server)
* **Partitioning strategies** with full metadata
* **User-defined types**
* And much more...

.. code-block:: python

    from sqlmeta.objects.procedure import Procedure
    from sqlmeta.objects.trigger import Trigger
    from sqlmeta.objects.package import Package

    # Oracle package
    pkg = Package(
        name="user_management",
        schema="public",
        spec="PROCEDURE create_user(p_name VARCHAR2, p_email VARCHAR2);",
        body="...",
        dialect="oracle"
    )

    # MySQL event
    from sqlmeta.objects.event import Event
    cleanup = Event(
        name="daily_cleanup",
        schedule="EVERY 1 DAY",
        body="DELETE FROM logs WHERE created_at < DATE_SUB(NOW(), INTERVAL 30 DAY)",
        dialect="mysql"
    )

**Real-world scenario**: You're migrating from Oracle to PostgreSQL. You need to catalog all procedures, packages, and triggers to plan the migration. sqlmeta can represent all these objects in a uniform way.

Multi-Dialect Schema Translation
---------------------------------

**SQLAlchemy** supports multiple dialects for *runtime operations*, but schema definitions are still tied to specific database features.

**sqlmeta** is designed for *schema translation* - define once, generate for any dialect:

.. code-block:: python

    from sqlmeta import Table, SqlColumn

    # Define a dialect-agnostic schema
    users = Table("users", columns=[
        SqlColumn("id", "INTEGER", is_primary_key=True),
        SqlColumn("email", "VARCHAR(255)", is_nullable=False),
        SqlColumn("created_at", "TIMESTAMP"),
    ])

    # Generate DDL for different databases
    pg_ddl = users.to_sql(dialect="postgresql")
    # CREATE TABLE users (
    #     id SERIAL PRIMARY KEY,
    #     email VARCHAR(255) NOT NULL,
    #     created_at TIMESTAMP
    # );

    mysql_ddl = users.to_sql(dialect="mysql")
    # CREATE TABLE users (
    #     id INT AUTO_INCREMENT PRIMARY KEY,
    #     email VARCHAR(255) NOT NULL,
    #     created_at TIMESTAMP
    # );

**Real-world scenario**: You're building a product that customers can deploy on their choice of database (PostgreSQL, MySQL, or SQL Server). sqlmeta lets you maintain one schema definition and generate correct DDL for each database.

Integration Hub
---------------

**sqlmeta** acts as a universal adapter between different tools in the Python ecosystem:

* Parse SQL scripts → convert to SQLAlchemy → generate Pydantic models
* Extract schema from database A → compare with schema B → generate Alembic migrations
* Read from SQLAlchemy → store as JSON → recreate in another tool
* Load schema from JSON → generate FastAPI models → create database tables

.. code-block:: python

    from sqlmeta import Table
    from sqlmeta.adapters.sqlalchemy import to_sqlalchemy, from_sqlalchemy
    from sqlmeta.adapters.pydantic import to_pydantic
    from sqlmeta.adapters.alembic import generate_operations

    # Start with any source
    table = Table(...)  # or from SQL parser, or from database introspection

    # Convert to SQLAlchemy for database operations
    sa_table = to_sqlalchemy(table, metadata)

    # Generate Pydantic model for API
    UserModel = to_pydantic(table)

    # Compare with another schema and generate migration
    operations = generate_operations(old_table, table)

**Real-world scenario**: You're building a schema management tool that needs to work with multiple frameworks. sqlmeta provides a common format that can convert to/from each one.

When to Use What?
-----------------

.. list-table::
   :header-rows: 1
   :widths: 60 40

   * - Use Case
     - Tool
   * - ORM for your application
     - **SQLAlchemy**
   * - Schema comparison & drift detection
     - **sqlmeta**
   * - Database queries and transactions
     - **SQLAlchemy**
   * - Cross-database schema translation
     - **sqlmeta**
   * - Schema versioning and serialization
     - **sqlmeta**
   * - Representing procedures, triggers, packages
     - **sqlmeta**
   * - Integration hub between tools
     - **sqlmeta**
   * - Runtime database operations
     - **SQLAlchemy**

Use Them Together!
------------------

sqlmeta and SQLAlchemy are **complementary**, not competing tools:

.. code-block:: python

    from sqlmeta import Table, SqlColumn
    from sqlmeta.adapters.sqlalchemy import to_sqlalchemy
    from sqlalchemy import create_engine, MetaData
    from sqlalchemy.orm import sessionmaker

    # 1. Define schema in sqlmeta (serializable, versionable)
    users = Table("users", columns=[
        SqlColumn("id", "INTEGER", is_primary_key=True),
        SqlColumn("email", "VARCHAR(255)", is_nullable=False),
    ])

    # 2. Store in version control as JSON
    with open('schemas/users.json', 'w') as f:
        json.dump(users.to_dict(), f)

    # 3. Convert to SQLAlchemy for runtime operations
    metadata = MetaData()
    sa_table = to_sqlalchemy(users, metadata)

    # 4. Use SQLAlchemy for database operations
    engine = create_engine("postgresql://localhost/mydb")
    Session = sessionmaker(bind=engine)
    session = Session()

    # Now you have:
    # - Schema in git (sqlmeta JSON)
    # - Runtime database access (SQLAlchemy)
    # - Ability to compare schemas (sqlmeta)
    # - Ability to generate migrations (sqlmeta + Alembic)

Comparison with Other Tools
----------------------------

sqlmeta vs Alembic
~~~~~~~~~~~~~~~~~~

**Alembic** is a migration tool - it helps you *change* schemas over time.

**sqlmeta** helps you *understand and compare* schemas. You can use sqlmeta to generate Alembic migrations by comparing two schema states.

They work great together: sqlmeta detects what changed, Alembic applies the changes.

sqlmeta vs Django ORM
~~~~~~~~~~~~~~~~~~~~~

**Django ORM** is tightly integrated with the Django framework and focuses on Python-defined models.

**sqlmeta** is framework-agnostic and focuses on SQL-first schemas. It can represent schemas that exist independently of any application code.

sqlmeta vs schema-crawler / SchemaSpy
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

These are **schema documentation tools** - they extract and visualize existing schemas.

**sqlmeta** is a **schema manipulation library** - it helps you compare, transform, and migrate schemas programmatically.

Real-World Use Cases
--------------------

1. **CI/CD Schema Validation**

   In your deployment pipeline, compare the schema your application expects against the target database to catch issues before deployment.

2. **Multi-Tenant Schema Management**

   Maintain a canonical schema definition and verify all tenant databases match it. Detect and fix drift automatically.

3. **Database Migration Projects**

   Moving from Oracle to PostgreSQL? Catalog all database objects in sqlmeta format, then generate PostgreSQL-compatible DDL.

4. **Schema as Code**

   Store your database schema in git as JSON/YAML. Generate SQLAlchemy models, Pydantic models, and DDL from a single source of truth.

5. **Cross-Service Schema Sharing**

   Microservices in different languages need to know the database schema. Export once from sqlmeta, consume in Python, Go, Node.js, etc.

6. **Compliance and Auditing**

   Track schema changes over time by storing sqlmeta snapshots. Generate reports showing what changed and when.

Conclusion
----------

**Use SQLAlchemy when**: You need to interact with a database from your Python application.

**Use sqlmeta when**: You need to understand, compare, version, or translate database schemas.

**Use both when**: You want the best of both worlds - schema management with sqlmeta, database operations with SQLAlchemy.

sqlmeta fills a gap in the Python ecosystem by providing a lightweight, serializable, framework-agnostic way to work with SQL metadata. It's the missing piece between "define a schema" and "use a database."
