"""Adapters for integrating sqlmeta with other libraries.

Available adapters:
- sqlalchemy: SQLAlchemy integration
- pydantic: Pydantic integration
- alembic: Alembic migration integration
"""

__all__ = []

# Import adapters if dependencies are available
try:
    from sqlmeta.adapters.sqlalchemy import to_sqlalchemy, from_sqlalchemy, get_create_ddl

    __all__.extend(["to_sqlalchemy", "from_sqlalchemy", "get_create_ddl"])
except ImportError:
    pass

try:
    from sqlmeta.adapters.pydantic import to_pydantic, to_pydantic_schema

    __all__.extend(["to_pydantic", "to_pydantic_schema"])
except ImportError:
    pass

try:
    from sqlmeta.adapters.alembic import (
        to_alembic_table,
        generate_operations,
        generate_migration_script,
    )

    __all__.extend(["to_alembic_table", "generate_operations", "generate_migration_script"])
except ImportError:
    pass
