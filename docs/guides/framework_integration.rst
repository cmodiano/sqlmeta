Framework Integration Guide
============================

This guide covers integration with popular Python frameworks.

SQLAlchemy Integration
-----------------------

Converting to SQLAlchemy
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from sqlalchemy import MetaData, create_engine
    from sqlmeta import Table, SqlColumn
    from sqlmeta.adapters.sqlalchemy import to_sqlalchemy

    # Define sqlmeta table
    table = Table("users", columns=[
        SqlColumn("id", "INTEGER", is_primary_key=True),
        SqlColumn("email", "VARCHAR(255)", is_nullable=False),
        SqlColumn("name", "VARCHAR(100)"),
    ])

    # Convert to SQLAlchemy
    metadata = MetaData()
    sa_table = to_sqlalchemy(table, metadata)

    # Use with SQLAlchemy
    engine = create_engine("postgresql://localhost/mydb")
    metadata.create_all(engine)

Converting from SQLAlchemy
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from sqlalchemy import Table as SATable, Column, Integer, String, MetaData
    from sqlmeta.adapters.sqlalchemy import from_sqlalchemy

    # Define SQLAlchemy table
    metadata = MetaData()
    sa_table = SATable(
        'users', metadata,
        Column('id', Integer, primary_key=True),
        Column('email', String(255), nullable=False),
        Column('name', String(100)),
    )

    # Convert to sqlmeta
    sqlmeta_table = from_sqlalchemy(sa_table)

    # Export to JSON
    import json
    with open('schema.json', 'w') as f:
        json.dump(sqlmeta_table.to_dict(), f, indent=2)

Pydantic Integration
--------------------

Generating Models
~~~~~~~~~~~~~~~~~

.. code-block:: python

    from sqlmeta import Table, SqlColumn
    from sqlmeta.adapters.pydantic import to_pydantic

    # Define table
    users_table = Table("users", columns=[
        SqlColumn("id", "INTEGER", is_primary_key=True),
        SqlColumn("email", "VARCHAR(255)", is_nullable=False),
        SqlColumn("name", "VARCHAR(100)"),
        SqlColumn("age", "INTEGER"),
    ])

    # Generate Pydantic model
    UserModel = to_pydantic(users_table)

    # Use the model
    user = UserModel(
        id=1,
        email="user@example.com",
        name="John Doe",
        age=30
    )

    # Validation
    print(user.model_dump_json())

Custom Model Names
~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # Custom model name
    CustomUser = to_pydantic(users_table, model_name="CustomUser")

    # Disable PascalCase conversion
    user_model = to_pydantic(users_table, use_title_case=False)

Schema Generation
~~~~~~~~~~~~~~~~~

.. code-block:: python

    from sqlmeta.adapters.pydantic import to_pydantic_schema

    # Generate JSON schema
    schema = to_pydantic_schema(users_table)

    # Use for API documentation
    print(json.dumps(schema, indent=2))

Alembic Integration
-------------------

Generating Operations
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from sqlmeta import Table, SqlColumn
    from sqlmeta.adapters.alembic import generate_operations

    # Define old and new schemas
    old_table = Table("users", columns=[
        SqlColumn("id", "INTEGER", is_primary_key=True),
        SqlColumn("name", "VARCHAR(100)"),
    ])

    new_table = Table("users", columns=[
        SqlColumn("id", "INTEGER", is_primary_key=True),
        SqlColumn("name", "VARCHAR(100)"),
        SqlColumn("email", "VARCHAR(255)", is_nullable=False),
    ])

    # Generate operations
    operations = generate_operations(
        source_table=old_table,
        target_table=new_table,
        dialect="postgresql"
    )

    # Use in Alembic migration
    def upgrade():
        for op in operations:
            op.execute()

Complete Migration Script
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from sqlmeta.adapters.alembic import generate_migration_script

    source_schema = [old_users_table, old_posts_table]
    target_schema = [new_users_table, new_posts_table, comments_table]

    script = generate_migration_script(
        source_tables=source_schema,
        target_tables=target_schema,
        dialect="postgresql",
        message="Add comments table and update users"
    )

    # Save to Alembic versions directory
    with open("alembic/versions/001_migration.py", "w") as f:
        f.write(script)

Using with Alembic Environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # In alembic/env.py
    from sqlmeta import Table
    from sqlmeta.adapters.sqlalchemy import to_sqlalchemy

    # Load your sqlmeta schema
    schema = load_schema()  # Your function to load schema

    # Convert to SQLAlchemy metadata
    target_metadata = MetaData()
    for table in schema:
        to_sqlalchemy(table, target_metadata)

    # Use with Alembic autogenerate
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        # ...
    )

Combined Example: Full Stack
-----------------------------

.. code-block:: python

    from sqlmeta import Table, SqlColumn, SqlConstraint, ConstraintType
    from sqlmeta.adapters.sqlalchemy import to_sqlalchemy
    from sqlmeta.adapters.pydantic import to_pydantic
    from sqlmeta.adapters.alembic import generate_operations
    from sqlalchemy import MetaData, create_engine
    from sqlalchemy.orm import sessionmaker

    # 1. Define schema in sqlmeta
    users_table = Table(
        "users",
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

    # 2. Create database schema with SQLAlchemy
    metadata = MetaData()
    sa_table = to_sqlalchemy(users_table, metadata)

    engine = create_engine("postgresql://localhost/mydb")
    metadata.create_all(engine)

    # 3. Generate Pydantic model for API
    UserModel = to_pydantic(users_table)

    # 4. Use in FastAPI
    from fastapi import FastAPI

    app = FastAPI()

    @app.post("/users/", response_model=UserModel)
    async def create_user(user: UserModel):
        # Save to database
        return user

    # 5. Later: Update schema and generate migration
    users_table_v2 = Table(
        "users",
        dialect="postgresql",
        columns=[
            SqlColumn("id", "SERIAL", is_primary_key=True),
            SqlColumn("email", "VARCHAR(255)", is_nullable=False),
            SqlColumn("name", "VARCHAR(100)", is_nullable=False),
            SqlColumn("created_at", "TIMESTAMP", default_value="CURRENT_TIMESTAMP"),
            SqlColumn("last_login", "TIMESTAMP"),  # New column
        ],
        constraints=[
            SqlConstraint(
                constraint_type=ConstraintType.UNIQUE,
                name="uq_users_email",
                column_names=["email"]
            )
        ]
    )

    # Generate Alembic migration
    operations = generate_operations(
        source_table=users_table,
        target_table=users_table_v2,
        dialect="postgresql"
    )

Django Integration (Custom)
----------------------------

While sqlmeta doesn't have a built-in Django adapter, you can integrate it:

.. code-block:: python

    from sqlmeta import Table, SqlColumn
    from django.db import models

    def to_django_model(table: Table, model_name: str = None):
        """Convert sqlmeta Table to Django model."""
        if model_name is None:
            model_name = table.name.title()

        fields = {}

        for col in table.columns:
            django_field = _map_to_django_field(col)
            fields[col.name] = django_field

        # Create model class dynamically
        model_class = type(
            model_name,
            (models.Model,),
            {
                **fields,
                '__module__': '__main__',
                'Meta': type('Meta', (), {
                    'db_table': table.name,
                    'app_label': 'myapp',
                })
            }
        )

        return model_class

    def _map_to_django_field(col):
        """Map sqlmeta column to Django field."""
        type_map = {
            'INTEGER': models.IntegerField,
            'VARCHAR': models.CharField,
            'TEXT': models.TextField,
            'TIMESTAMP': models.DateTimeField,
            'BOOLEAN': models.BooleanField,
        }

        base_type = col.data_type.split('(')[0].upper()
        field_class = type_map.get(base_type, models.CharField)

        kwargs = {}
        if col.is_primary_key:
            kwargs['primary_key'] = True
        if col.nullable:
            kwargs['null'] = True
        if col.default_value:
            kwargs['default'] = col.default_value

        # Handle CharField max_length
        if field_class == models.CharField:
            if '(' in col.data_type:
                length = col.data_type.split('(')[1].split(')')[0]
                kwargs['max_length'] = int(length)
            else:
                kwargs['max_length'] = 255

        return field_class(**kwargs)

Best Practices
--------------

1. **Single Source of Truth**

   Define your schema once in sqlmeta and generate everything else:

   .. code-block:: python

       # schema.py
       schema = [users_table, posts_table, comments_table]

       # Export to SQLAlchemy
       def get_sqlalchemy_metadata():
           metadata = MetaData()
           for table in schema:
               to_sqlalchemy(table, metadata)
           return metadata

       # Export to Pydantic
       def get_pydantic_models():
           return {
               'User': to_pydantic(users_table),
               'Post': to_pydantic(posts_table),
               'Comment': to_pydantic(comments_table),
           }

2. **Version Control Your Schema**

   Store schema definitions in version control:

   .. code-block:: python

       # schemas/v1.py
       users_v1 = Table(...)

       # schemas/v2.py
       users_v2 = Table(...)

       # Then generate migrations
       from schemas.v1 import users_v1
       from schemas.v2 import users_v2

       operations = generate_operations(users_v1, users_v2)

3. **Automate Schema Updates**

   Create scripts to regenerate models when schema changes:

   .. code-block:: bash

       #!/bin/bash
       # update_models.sh

       python generate_sqlalchemy.py
       python generate_pydantic.py
       python generate_migration.py

4. **Test Integrations**

   Test that conversions preserve schema semantics:

   .. code-block:: python

       def test_roundtrip():
           # sqlmeta -> SQLAlchemy -> sqlmeta
           sa_table = to_sqlalchemy(original_table, MetaData())
           roundtrip_table = from_sqlalchemy(sa_table)

           # Compare
           comparator = ObjectComparator()
           diff = comparator.compare_tables(original_table, roundtrip_table)
           assert not diff.has_diffs
