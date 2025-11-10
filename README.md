# sqlmeta

**Universal SQL metadata and schema representation for Python**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Coverage](https://img.shields.io/badge/Coverage-84%25-brightgreen.svg)](#testing)

## Overview

`sqlmeta` is a Python library that provides a dialect-agnostic representation of SQL database schemas and metadata. It enables you to work with database objects (tables, views, procedures, etc.) across different SQL dialects in a unified way, making it easy to:

- **Compare schemas** from different sources (parsed SQL scripts vs. live databases)
- **Detect schema drift** between environments
- **Convert between formats** (SQLAlchemy, Pydantic, raw SQL)
- **Generate migration scripts** by comparing source and target schemas
- **Parse and represent** complex database objects across PostgreSQL, MySQL, Oracle, SQL Server, and more

## Why sqlmeta?

**"Why not just use SQLAlchemy directly?"**

While SQLAlchemy is excellent for ORM and database operations, sqlmeta solves different problems:

### 1. **Schema Comparison & Drift Detection**
SQLAlchemy represents schemas for *your application*. sqlmeta compares schemas from *different sources*:
- Compare SQL scripts against live databases
- Detect drift between dev, staging, and production
- Validate that migrations were applied correctly
- Compare schemas across different database vendors

```python
# sqlmeta excels at this - SQLAlchemy doesn't provide this functionality
from sqlmeta.comparison.comparator import ObjectComparator

diff = comparator.compare_tables(source_table, target_table)
if diff.has_diffs:
    print(f"Schema drift detected! Severity: {diff.severity}")
    for col in diff.missing_columns:
        print(f"Missing column: {col}")
```

### 2. **Lightweight & Serializable**
SQLAlchemy metadata is tightly coupled to engines and sessions. sqlmeta is pure data:
- **Zero dependencies** for core functionality
- **JSON serializable** - store schemas in files, databases, or APIs
- **Language agnostic** - share schemas between Python, Go, Node.js services
- **Version control friendly** - track schema changes in git

```python
# sqlmeta schemas are just data
schema = table.to_dict()
with open('schema.json', 'w') as f:
    json.dump(schema, f)

# Recreate anywhere, anytime
table = Table.from_dict(schema)
```

### 3. **Broader Database Object Support**
SQLAlchemy focuses on tables for ORM. sqlmeta represents the full database:
- Stored procedures and packages (Oracle, SQL Server)
- Triggers with full metadata
- Database links and foreign data wrappers
- Extensions, events, synonyms
- Partitioning strategies
- And more...

### 4. **Multi-Dialect Schema Translation**
Maintain one schema definition, deploy to multiple databases:
```python
# Define once
base_schema = Table("users", columns=[...])

# Generate for each dialect
pg_ddl = base_schema.to_sql(dialect="postgresql")
mysql_ddl = base_schema.to_sql(dialect="mysql")
oracle_ddl = base_schema.to_sql(dialect="oracle")
```

### 5. **Integration Hub**
sqlmeta acts as a universal adapter between tools:
- Parse SQL scripts → convert to SQLAlchemy → generate Pydantic models
- Read from database A → compare with schema B → generate Alembic migrations
- Extract schema from SQLAlchemy → store in JSON → recreate in another language

### When to Use What?

| Use Case | Tool |
|----------|------|
| ORM for your application | **SQLAlchemy** |
| Schema comparison & drift detection | **sqlmeta** |
| Database queries and transactions | **SQLAlchemy** |
| Cross-database schema translation | **sqlmeta** |
| Schema versioning and serialization | **sqlmeta** |
| Integration between tools | **sqlmeta** |

**Use them together!** sqlmeta complements SQLAlchemy - it even includes bidirectional converters.

## Key Features

- **Dialect-agnostic schema representation** - Work with SQL metadata without worrying about database-specific quirks
- **Comprehensive object support** - Tables, views, procedures, triggers, sequences, indexes, partitions, and more
- **Schema comparison & drift detection** - Intelligent comparison with type normalization and severity levels
- **Framework integrations** - Convert to/from SQLAlchemy and Pydantic models
- **Type-aware comparison** - Handles data type variations across different SQL dialects
- **System-generated name handling** - Automatically detects and handles database-generated constraint names
- **Zero dependencies** - Core library has no required dependencies (adapters are optional)
- **Fully typed** - Complete type hints for better IDE support

## Installation

```bash
# Core library (no dependencies)
pip install sqlmeta

# With SQLAlchemy support
pip install sqlmeta[sqlalchemy]

# With Pydantic support
pip install sqlmeta[pydantic]

# With Alembic support
pip install sqlmeta[alembic]

# With all optional dependencies
pip install sqlmeta[all]

# For development
pip install sqlmeta[dev]
```

## Quick Start

### Creating Tables

```python
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
```

### Schema Comparison

```python
from sqlmeta.comparison.comparator import ObjectComparator

# Compare two table definitions
comparator = ObjectComparator(dialect="postgresql")
diff = comparator.compare_tables(source_table, target_table)

if diff.has_diffs:
    print(f"Severity: {diff.severity.value}")

    # Missing columns
    for col in diff.missing_columns:
        print(f"Missing column: {col}")

    # Modified columns
    for col_diff in diff.modified_columns:
        print(f"Column '{col_diff.column_name}' changed:")
        print(f"  Type: {col_diff.type_mismatch}")
        print(f"  Nullable: {col_diff.nullable_mismatch}")
```

### SQLAlchemy Integration

```python
from sqlalchemy import MetaData
from sqlmeta.adapters.sqlalchemy import to_sqlalchemy, from_sqlalchemy

# Convert sqlmeta Table to SQLAlchemy Table
metadata = MetaData()
sa_table = to_sqlalchemy(users_table, metadata)

# Convert SQLAlchemy Table back to sqlmeta Table
sqlmeta_table = from_sqlalchemy(sa_table)
```

### Pydantic Integration

```python
from sqlmeta.adapters.pydantic import to_pydantic

# Generate Pydantic model from table
UserModel = to_pydantic(users_table)

# Use the model
user = UserModel(id=1, email="user@example.com", name="John Doe")
print(user.model_dump_json())
```

### Serialization

```python
# Export to dictionary
table_dict = users_table.to_dict()

# Recreate from dictionary
users_table_copy = Table.from_dict(table_dict)

# Works with JSON
import json
json_str = json.dumps(table_dict)
```

## Supported Database Objects

`sqlmeta` supports a comprehensive set of database objects:

| Object Type | Support | Dialects |
|-------------|---------|----------|
| Tables | ✅ | All |
| Views | ✅ | All |
| Materialized Views | ✅ | PostgreSQL, Oracle |
| Indexes | ✅ | All |
| Sequences | ✅ | PostgreSQL, Oracle, SQL Server |
| Procedures | ✅ | All |
| Functions | ✅ | PostgreSQL, MySQL, SQL Server |
| Triggers | ✅ | All |
| Partitions | ✅ | PostgreSQL, MySQL, Oracle |
| Extensions | ✅ | PostgreSQL |
| Foreign Data Wrappers | ✅ | PostgreSQL |
| Foreign Servers | ✅ | PostgreSQL |
| Database Links | ✅ | Oracle |
| Linked Servers | ✅ | SQL Server |
| Packages | ✅ | Oracle |
| Synonyms | ✅ | Oracle, SQL Server |
| Events | ✅ | MySQL |
| User-Defined Types | ✅ | PostgreSQL, Oracle, SQL Server |

## Supported SQL Dialects

- **PostgreSQL** - Full support including extensions, foreign data wrappers, materialized views
- **MySQL** - Full support including events, storage engines, partitions
- **Oracle** - Full support including packages, database links, synonyms
- **SQL Server** - Full support including linked servers, temporal tables, memory-optimized tables
- **Generic SQL** - Fallback for other SQL databases

## Advanced Features

### Type Normalization

The comparison system automatically normalizes data types across dialects:

```python
from sqlmeta.comparison.type_normalizer import DataTypeNormalizer

normalizer = DataTypeNormalizer(dialect="postgresql")

# Normalizes VARCHAR variations
assert normalizer.normalize("VARCHAR(255)") == normalizer.normalize("CHARACTER VARYING(255)")

# Handles INTEGER variants
assert normalizer.normalize("INT") == normalizer.normalize("INTEGER")
```

### System-Generated Constraint Names

`sqlmeta` automatically detects system-generated constraint names and matches by structure instead:

```python
# Oracle: SYS_C0013220
# SQL Server: PK__users__3213E83F
# These are matched by constraint type and columns, not name
```

### Diff Severity Levels

Schema differences are categorized by severity:

- **ERROR** - Breaking changes (column removed, incompatible type change)
- **WARNING** - Non-breaking but important (nullable changed, constraint modified)
- **INFO** - Cosmetic differences (comments, formatting)

### Explicit Properties Tracking

Objects track which properties were explicitly set vs. defaults:

```python
table = Table("users", columns=[...])
table.explicit_properties["comment"]  # False if not set
```

## Use Cases

### 1. Schema Drift Detection

Compare your application's schema definition against a live database:

```python
from sqlmeta.comparison.comparator import ObjectComparator

comparator = ObjectComparator(dialect="postgresql")

# Compare all tables in two schemas
schema_diff = comparator.compare_schemas(source_schema, target_schema)

# Generate report
for table_diff in schema_diff.table_diffs:
    if table_diff.has_diffs:
        print(f"Table {table_diff.table_name}: {table_diff.severity.value}")
```

### 2. Migration Script Generation

```python
# Compare schemas and generate ALTER statements
diff = comparator.compare_tables(old_table, new_table)

for col in diff.missing_columns:
    print(f"ALTER TABLE {old_table.name} ADD COLUMN {col} {col.data_type};")

for col_diff in diff.modified_columns:
    if col_diff.type_mismatch:
        print(f"ALTER TABLE {old_table.name} ALTER COLUMN {col_diff.column_name} TYPE {col_diff.target_type};")
```

### 3. Multi-Database Support

Maintain schema definitions that work across different databases:

```python
# Define once
base_table = Table("users", columns=[...])

# Generate for different dialects
pg_ddl = base_table.to_sql(dialect="postgresql")
mysql_ddl = base_table.to_sql(dialect="mysql")
oracle_ddl = base_table.to_sql(dialect="oracle")
```

### 4. Documentation Generation

```python
# Generate schema documentation
for table in schema.tables:
    print(f"## {table.name}")
    if table.comment:
        print(f"{table.comment}\n")

    print("| Column | Type | Nullable | Default |")
    print("|--------|------|----------|---------|")
    for col in table.columns:
        print(f"| {col.name} | {col.data_type} | {col.nullable} | {col.default_value or '-'} |")
```

## Architecture

### Core Components

- **`sqlmeta.base`** - Base classes and enums (`SqlObject`, `SqlColumn`, `SqlConstraint`)
- **`sqlmeta.objects`** - Specific object types (Table, View, Procedure, etc.)
- **`sqlmeta.comparison`** - Schema comparison and drift detection
- **`sqlmeta.adapters`** - Framework integrations (SQLAlchemy, Pydantic)

### Design Principles

1. **Dialect awareness** - All objects carry dialect information that propagates to children
2. **Immutability preference** - Objects are designed to be created once and compared
3. **Type safety** - Full type hints throughout the codebase
4. **Zero dependencies** - Core library works standalone; adapters are optional
5. **Extensibility** - Easy to add new object types or dialects

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/cmodiano/sqlmeta.git
cd sqlmeta

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev,all]"
```

### Running Tests

```bash
# Run all tests with coverage
pytest

# Run specific test file
pytest tests/test_table.py

# Run with verbose output
pytest -v
```

### Code Quality

```bash
# Format code
black sqlmeta tests

# Type checking
mypy sqlmeta

# Linting
ruff check sqlmeta
```

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests
5. Run the test suite
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Roadmap

- [ ] Additional dialect support (Snowflake, BigQuery, Redshift)
- [ ] Schema visualization tools
- [ ] Migration script generation
- [ ] Integration with popular ORMs (Django, Peewee)
- [ ] SQL parser integration for automatic schema extraction
- [ ] Web UI for schema comparison
- [ ] Support for more complex object types (domains, operators, casts)

## Related Projects

- [SQLAlchemy](https://www.sqlalchemy.org/) - Python SQL toolkit and ORM
- [Alembic](https://alembic.sqlalchemy.org/) - Database migration tool for SQLAlchemy
- [Pydantic](https://docs.pydantic.dev/) - Data validation using Python type hints

## Support

- **Documentation**: [https://sqlmeta.readthedocs.io](https://sqlmeta.readthedocs.io)
- **Issues**: [https://github.com/cmodiano/sqlmeta/issues](https://github.com/cmodiano/sqlmeta/issues)
- **Discussions**: [https://github.com/cmodiano/sqlmeta/discussions](https://github.com/cmodiano/sqlmeta/discussions)

## Acknowledgments

This project was extracted and enhanced from the [DBLift](https://github.com/cmodiano/dblift) project to provide a standalone, reusable library for SQL metadata representation.
